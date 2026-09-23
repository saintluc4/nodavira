"""Build without changing PowerShell execution policy."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(ROOT/'scripts/generate_brand.py')], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(ROOT/'scripts/prepare_release.py')], cwd=ROOT, check=True)
env = dict(os.environ, PYTHONPATH=str(ROOT/'.deps'), PYINSTALLER_CONFIG_DIR=str(ROOT/'build/cache'))
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--name', 'Nodavira', '--paths', '.deps', '--add-data', 'static;static',
        '--icon', 'static/app.ico', '--version-file', 'packaging/windows-version.txt', '--collect-data', 'webview',
        '--hidden-import', 'webview.platforms.winforms',
        '--hidden-import', 'webview.platforms.edgechromium']
for package in ('cryptography', 'trio', 'pytest', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
                'qtpy', 'gi', 'cefpython3'):
    args += ['--exclude-module', package]
for package in ('dns', 'anyio', 'httpcore'):
    args += ['--collect-all', package]
for package in ('dnspython', 'httpx', 'httpcore', 'h2', 'hpack', 'hyperframe', 'pywebview', 'pythonnet'):
    args += ['--copy-metadata', package]
subprocess.run(args + ['app.py'], cwd=ROOT, env=env, check=True)
subprocess.run([sys.executable, str(ROOT/'scripts/package_release.py')], cwd=ROOT, check=True)
print('Pronto: dist/Nodavira.exe')
