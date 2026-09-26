"""End-to-end verification of the self-contained binary in an isolated folder."""
import hashlib
import os
import json
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
verification_root=ROOT/'build/package-verification'
verification_root.mkdir(parents=True,exist_ok=True)
folder=Path(tempfile.mkdtemp(prefix='nodavira-',dir=verification_root))
binary=folder/'Nodavira.exe'
shutil.copyfile(ROOT/'dist/Nodavira.exe',binary)
session=folder/f'session-{time.time_ns()}.json'
process=subprocess.Popen([str(binary),'--hidden-window','--session-file',str(session)],cwd=folder,
                         env=dict(os.environ, APPDATA=str(folder/'preferences')),
                         creationflags=subprocess.CREATE_NO_WINDOW)
token=None


def api(path,body=None):
    request=urllib.request.Request(base+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,
                                  headers={'X-Nodavira-Token':token,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as response:
        data=response.read()
        return data if path.endswith('.csv') else json.loads(data)


def finish():
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        status=api('status')
        if status['state']!='running':return status
        time.sleep(.25)
    raise RuntimeError('Benchmark did not finish')


try:
    deadline=time.monotonic()+30
    while not session.exists() and time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Executable exited before startup')
        time.sleep(.2)
    info=json.loads(session.read_text())
    parsed=urlsplit(info['url']);base=f'{parsed.scheme}://{parsed.netloc}'
    token=parse_qs(parsed.fragment)['token'][0]
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        desktop=api('status').get('desktop',{})
        if desktop.get('loaded'):
            break
        time.sleep(.2)
    assert desktop=={'mode':'desktop','renderer':'edgechromium','loaded':True},desktop
    with urllib.request.urlopen(base+'/notices.txt', timeout=10) as response:
        bundled_notices=response.read()
    assert bundled_notices==(ROOT/'static/notices.txt').read_bytes(), 'Bundled license notices differ'
    config=api('config')
    api('preferences', {'language':'en'})
    assert api('config')['language']=='en'
    assert api('status')['message']=='Ready to start'
    for asset in ('en.json','i18n.js'):
        with urllib.request.urlopen(base+'/'+asset, timeout=10) as response:
            assert response.read()==(ROOT/'static'/asset).read_bytes()
    resolvers=[r for r in config['resolvers'] if r['name']=='Cloudflare']
    negative=dict(next(r for r in resolvers if r['protocol']=='dot' and r['family']=='IPv4'))
    negative.update(name='TLS hostname validation (negative control)',hostname='invalid.example.org')
    api('start',{'resolvers':resolvers+[negative],'domains':['example.com','python.org'],
                 'rounds':2,'concurrency':2,'timeout_ms':2500,'seed':20260922})
    result=finish()
    assert result['state']=='complete',result
    actual=api('export.json')
    assert actual['completed']==48,actual['completed']
    assert actual['language']=='en'
    assert actual['message']=='Benchmark complete.'
    for row in actual['rows']:
        if row['name'].startswith('TLS hostname'):
            assert not row['available'] and row['score_ms'] is None,row
            assert 'SSLCertVerificationError' in row['diagnostic_errors'],row
        else:
            assert row['available'] and row['success']>=7,row
    exported=api('export.csv').decode('utf-8-sig')
    assert len(exported.splitlines())==49
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        saved=api('status')
        if saved.get('saved_to') or saved.get('save_error'):break
        time.sleep(.1)
    assert saved.get('saved_to'),saved.get('save_error','Report was not saved')
    api('start',{'resolvers':resolvers,'domains':config['domains'],'rounds':3,'concurrency':2})
    api('stop',{})
    cancelled=finish()
    assert cancelled['state']=='cancelled',cancelled['state']
    report={'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'desktop':desktop,'bundled_notices_bytes':len(bundled_notices),
            'completed_queries':actual['completed'],'csv_lines':49,'cancellation':cancelled['state'],
            'rows':[{k:r[k] for k in ('name','protocol','family','success','count','available','diagnostic_errors','http_versions')} for r in actual['rows']]}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/packaged-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
finally:
    if token:
        try:api('shutdown',{})
        except Exception:pass
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
