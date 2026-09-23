import re
import sys
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.package_release import source_files


class ReleaseTests(unittest.TestCase):
    def test_public_source_excludes_local_sessions_reports_and_binaries(self):
        files=[path.relative_to(ROOT) for path in source_files()]
        self.assertIn(Path('README.md'),files)
        self.assertIn(Path('.gitignore'),files)
        self.assertIn(Path('nodavira/desktop.py'),files)
        for path in files:
            self.assertTrue((ROOT/path).is_file(),str(path))
            self.assertFalse(set(path.parts)&{'.deps','.venv','reports','build','dist','__pycache__'},str(path))
            self.assertNotIn(path.suffix,{'.exe','.zip','.pyc'},str(path))
            self.assertFalse(path.name.startswith('session'),str(path))

    def test_readme_relative_links_resolve_in_source(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',readme):
            if '://' not in target and not target.startswith('#'):
                self.assertTrue((ROOT/target.split('#')[0]).exists(),target)

    def test_source_export_works_without_a_built_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout=Path(directory)
            for path in source_files():
                destination=checkout/path.relative_to(ROOT)
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,destination)
            result=subprocess.run([sys.executable,'scripts/package_release.py','--source'],
                                  cwd=checkout,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse((checkout/'dist').exists())
            with ZipFile(checkout/'Nodavira-Source.zip') as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read('brand/mark.svg'),(ROOT/'brand/mark.svg').read_bytes())
                self.assertIn('CONTRIBUTING.md',archive.namelist())


if __name__=='__main__':unittest.main()
