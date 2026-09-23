"""Assemble public artifacts from explicit allowlists, never from the entire workspace."""
import hashlib
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ['README.md', 'METHODOLOGY.md', 'TESTING.md', 'THIRD_PARTY_NOTICES.md', 'BRAND.md', 'CONTRIBUTING.md',
             'requirements.txt', 'requirements-lock.txt', 'requirements-build.txt']
SOURCE_FILES = DOCUMENTS + ['LICENSE', '.gitignore', '.gitattributes', 'app.py', 'build.py', 'build.ps1']
SOURCE_DIRECTORIES = ['nodavira', 'static', 'tests', 'scripts', 'packaging', 'licenses', 'brand', '.github']


def source_files(root=ROOT):
    files = [root/name for name in SOURCE_FILES]
    for directory in SOURCE_DIRECTORIES:
        files.extend(path for path in (root/directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix not in ('.pyc', '.pyo') and not path.is_symlink())
    return sorted(files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='store_true', help='Gerar ZIP completo dos arquivos públicos do repositório')
    args = parser.parse_args()
    dist = ROOT/'dist'
    binary = dist/'Nodavira.exe'
    if args.source:
        with ZipFile(ROOT/'Nodavira-Source.zip', 'w', ZIP_DEFLATED) as archive:
            for path in source_files():
                archive.write(path, path.relative_to(ROOT))
        print('Código, recursos e documentação: Nodavira-Source.zip')
    if binary.is_file():
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        (dist/'SHA256.txt').write_text(f'{digest}  Nodavira.exe\n', encoding='utf-8')
        print(f'Arquivo para a Release: dist/Nodavira.exe. SHA-256: {digest}')
    elif not args.source:
        raise SystemExit('Compile Nodavira.exe antes de preparar a Release, ou use --source para o código.')


if __name__ == '__main__':
    main()
