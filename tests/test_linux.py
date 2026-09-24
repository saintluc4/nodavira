import io
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.deps'), str(ROOT)]
from nodavira.platforms import reports_directory
from nodavira.config import catalog
from scripts.package_linux import ar_bytes, install_tree, tar_bytes, collect_vendor


class LinuxTests(unittest.TestCase):
    def test_reports_use_absolute_xdg_path_and_reject_relative_values(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            data = home / 'custom data'
            for environ, expected in [({}, home/'.local/share'),
                                      ({'XDG_DATA_HOME': ''}, home/'.local/share'),
                                      ({'XDG_DATA_HOME': 'relative'}, home/'.local/share'),
                                      ({'XDG_DATA_HOME': str(data)}, data)]:
                with self.subTest(environ=environ):
                    path=reports_directory(ROOT, 'linux', environ, home)
                    self.assertEqual(path, expected/'nodavira/reports')
                    self.assertNotEqual(path, ROOT/'reports')

    def test_windows_source_reports_location_is_preserved(self):
        self.assertEqual(reports_directory(ROOT, 'win32'), ROOT/'reports')

    def test_linux_stub_is_preserved_without_guessing_upstream(self):
        with patch('nodavira.config.dns.resolver.Resolver') as resolver:
            resolver.return_value.nameservers=['127.0.0.53', '1.1.1.1']
            entries=catalog()
        self.assertEqual(entries[0]['address'], '127.0.0.53')
        self.assertEqual(entries[0]['name'], 'DNS do sistema')
        self.assertNotIn('Windows', entries[0]['policy'])
        self.assertEqual(sum(r['address']=='1.1.1.1' and r['protocol']=='udp' for r in entries), 1)

    def test_staged_package_has_launcher_icons_notices_and_no_private_data(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory)
            install_tree(stage)
            launcher=(stage/'usr/bin/nodavira').read_bytes()
            self.assertTrue(launcher.startswith(b'#!/bin/sh\n'))
            self.assertIn(b'"$@"', launcher)
            self.assertNotIn(b'\r', launcher)
            self.assertTrue((stage/'usr/share/nodavira/static/notices.txt').is_file())
            self.assertTrue((stage/'usr/share/applications/io.github.saintluc4.nodavira.desktop').is_file())
            for path in stage.rglob('*'):
                self.assertFalse(set(path.relative_to(stage).parts) & {'build','reports','__pycache__','.git'})
                self.assertFalse(path.name.startswith('session'))

    def test_tar_and_ar_preserve_linux_permissions_and_ownership(self):
        compressed=tar_bytes([('usr/bin/nodavira',b'#!/bin/sh\n',0o755)])
        self.assertEqual(compressed[9],255)  # host-independent gzip OS byte
        with tarfile.open(fileobj=io.BytesIO(compressed),mode='r:gz') as archive:
            entry=archive.getmember('usr/bin/nodavira')
            self.assertEqual(entry.mode,0o755)
            self.assertEqual((entry.uid,entry.gid),(0,0))
            self.assertEqual(archive.getmember('usr/bin').mode,0o755)
        result=ar_bytes([('debian-binary',b'2.0\n'),('data.tar.gz',compressed)])
        self.assertEqual(result[:8],b'!<arch>\n')
        offset=8
        names=[]
        while offset<len(result):
            header=result[offset:offset+60]
            self.assertEqual(header[-2:],b'`\n')
            size=int(header[48:58]);names.append(header[:16].decode().strip().rstrip('/'))
            offset+=60+size+(size%2)
        self.assertEqual(names,['debian-binary','data.tar.gz'])
        self.assertEqual(offset,len(result))

    def test_missing_vendor_dependencies_fail_instead_of_shipping_incomplete_package(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Instale'):
                collect_vendor(Path(directory),Path(directory)/'output')


if __name__=='__main__':
    unittest.main()
