"""Collect installed dependency versions and license notices without network access."""
import importlib.metadata
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--update-lock', action='store_true', help='Atualizar explicitamente as versões fixadas')
args = parser.parse_args()
target = ROOT/'licenses'
target.mkdir(exist_ok=True)
distributions = sorted(importlib.metadata.distributions(path=[str(ROOT/'.deps')]), key=lambda d:d.metadata['Name'].lower())
lines=[]
for distribution in distributions:
    name = distribution.metadata['Name']
    lines.append(f'{name}=={distribution.version}')
    for entry in distribution.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice', 'authors')) for part in entry.parts):
            source=Path(distribution.locate_file(entry))
            if source.is_file():
                destination=target/(name+'-'+source.name)
                shutil.copyfile(source,destination)
actual = '\n'.join(lines)+'\n'
if args.update_lock:
    (ROOT/'requirements-lock.txt').write_text(actual,encoding='utf-8')
elif not lines or actual != (ROOT/'requirements-lock.txt').read_text(encoding='utf-8'):
    raise SystemExit('As dependências de .deps diferem de requirements-lock.txt. Instale as versões fixadas antes de compilar.')
(ROOT/'build').mkdir(exist_ok=True)
(ROOT/'build/runtime-dependencies.txt').write_text(actual,encoding='utf-8')
for source in (Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE'):
    if source.is_file(): shutil.copyfile(source,target/'Python-LICENSE.txt')
try:
    distribution=importlib.metadata.distribution('pyinstaller')
    for entry in distribution.files or []:
        if entry.name.lower().startswith(('copying','license')):
            source=Path(distribution.locate_file(entry))
            if source.is_file(): shutil.copyfile(source,target/('PyInstaller-'+source.name))
except importlib.metadata.PackageNotFoundError:
    pass
notices = ['Nodavira — licença do projeto\n\n', (ROOT/'LICENSE').read_text(encoding='utf-8'),
           '\n\n', (ROOT/'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')]
for license_file in sorted(target.iterdir()):
    if license_file.is_file():
        notices.append(f'\n\n{"=" * 72}\n{license_file.name}\n{"=" * 72}\n\n'
                       + license_file.read_text(encoding='utf-8'))
(ROOT/'static/notices.txt').write_text(''.join(notices), encoding='utf-8')
print(f'Licenças coletadas: {len(list(target.iterdir()))}')
