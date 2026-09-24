"""Exercise an installed Linux package and real GTK window without public DNS.

Run inside a graphical session or dbus-run-session -- xvfb-run -a. The test
resolver runs on an ephemeral localhost UDP port; no network configuration changes.
"""
import argparse
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.deps'),str(ROOT)]
import dns.message
import dns.rrset


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop',action='store_true')
    parser.add_argument('--command',nargs=argparse.REMAINDER,default=[sys.executable,str(ROOT/'app.py')])
    args=parser.parse_args()
    stop=threading.Event()
    resolver=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    resolver.bind(('127.0.0.1',0));resolver.settimeout(.2)

    def respond():
        while not stop.is_set():
            try:
                data,peer=resolver.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            query=dns.message.from_wire(data)
            response=dns.message.make_response(query)
            response.answer.append(dns.rrset.from_text(query.question[0].name.to_text(),60,'IN','A','192.0.2.10'))
            resolver.sendto(response.to_wire(),peer)

    thread=threading.Thread(target=respond,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='nodavira-smoke-') as directory:
            folder=Path(directory);session=folder/'session.json'
            env=dict(os.environ,XDG_DATA_HOME=str(folder/'data'),PYTHONDONTWRITEBYTECODE='1')
            command=args.command+['--session-file',str(session),
                                  '--hidden-window' if args.desktop else '--no-browser']
            with (folder/'process.log').open('w+',encoding='utf-8') as log:
                process=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=log)
                base=token=None

                def api(path,body=None):
                    request=urllib.request.Request(base+'/api/'+path,
                        data=json.dumps(body).encode() if body is not None else None,
                        headers={'X-Nodavira-Token':token,'Content-Type':'application/json'})
                    with urllib.request.urlopen(request,timeout=5) as response:
                        data=response.read()
                    return data if path.endswith('.csv') else json.loads(data)

                def until(predicate,timeout=30):
                    deadline=time.monotonic()+timeout
                    while time.monotonic()<deadline:
                        if process.poll() is not None:
                            raise RuntimeError(f'Application exited with {process.returncode}')
                        result=predicate()
                        if result:return result
                        time.sleep(.1)
                    raise TimeoutError('Application did not reach expected state')

                try:
                    until(session.is_file)
                    info=json.loads(session.read_text())
                    parsed=urlsplit(info['url']);base=f'{parsed.scheme}://{parsed.netloc}'
                    token=parse_qs(parsed.fragment)['token'][0]
                    if args.desktop:
                        until(lambda:api('status')['desktop']['loaded'])
                        assert api('status')['desktop']['renderer']=='gtkwebkit2'
                    try:
                        urllib.request.urlopen(base+'/api/status',timeout=5)
                        raise AssertionError('Unauthenticated request accepted')
                    except urllib.error.HTTPError as error:
                        assert error.code==403,error.code
                    api('start',{'domains':['example.com','iana.org'],'qtypes':['A'],
                        'rounds':2,'concurrency':2,'timeout_ms':500,
                        'resolvers':[{'name':'Loopback test','protocol':'udp','address':'127.0.0.1',
                                      'port':resolver.getsockname()[1]}]})
                    until(lambda:api('status')['state']!='running')
                    report=api('export.json')
                    assert report['state']=='complete',report['state']
                    assert report['completed']==4,report['completed']
                    assert report['rows'][0]['success']==4,report['rows']
                    assert len(api('export.csv').decode('utf-8-sig').splitlines())==5
                    saved=until(lambda:api('status').get('saved_to'))
                    assert Path(saved).is_relative_to(folder/'data/nodavira/reports'),saved
                    assert Path(saved).is_file()
                    with urllib.request.urlopen(base+'/notices.txt',timeout=5) as response:
                        assert b'MIT License' in response.read()
                    api('shutdown',{})
                    assert process.wait(timeout=15)==0
                    print('PASS: GTK window' if args.desktop else 'PASS: server',
                          '+ authentication + local UDP benchmark + JSON/CSV + XDG reports + shutdown')
                except Exception:
                    log.flush();log.seek(0)
                    diagnostic=re.sub(r'#token=[^\s]+','#token=[redacted]',log.read())
                    if token:diagnostic=diagnostic.replace(token,'[redacted]')
                    print(diagnostic[-12000:],file=sys.stderr)
                    raise
                finally:
                    if process.poll() is None:
                        if token:
                            try:api('shutdown',{})
                            except Exception:pass
                        try:process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.terminate();process.wait(timeout=5)
    finally:
        stop.set();resolver.close();thread.join(1)


if __name__=='__main__':main()
