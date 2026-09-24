"""Build architecture-independent Linux packages without executing target code.

The .deb includes pinned pure-Python dependencies. GTK/WebKit/Python come from
apt. Arch's PKGBUILD uses pacman's Python dependencies instead of vendoring.
Run makepkg on Arch to produce the pacman package; no cross-compilation claim.
"""
import argparse
import gzip
import hashlib
import importlib.metadata
import io
import os
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nodavira import __version__
from scripts.package_release import source_files

ARCH_DEPENDS = ["python>=3.11", "python-dnspython>=2.8", "python-httpx>=0.28",
                "python-h2>=4.3", "python-pywebview>=6.2.1", "python-gobject",
                "python-cairo", "gtk3", "webkit2gtk-4.1", "ca-certificates", "xdg-utils"]


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def collect_vendor(source, destination):
    """Only copy the explicitly pinned, pure-Python distributions by RECORD.

    Never copy a whole Windows .deps folder into a Linux package. Windows-only
    helper binaries included in pywebview's universal wheel are not needed.
    """
    source = Path(source).resolve()
    installed = {normalized(d.metadata["Name"]): d
                 for d in importlib.metadata.distributions(path=[str(source)])}
    for line in (ROOT / "requirements-linux-lock.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        dist = installed.get(normalized(name))
        if dist is None or dist.version != version:
            raise ValueError(f"Instale {name}=={version} em {source} antes de empacotar.")
        if "Root-Is-Purelib: true" not in (dist.read_text("WHEEL") or ""):
            raise ValueError(f"{name} não é uma distribuição Python independente de arquitetura.")
        for entry in dist.files or []:
            relative = PurePosixPath(str(entry).replace("\\", "/"))
            # pip-generated console scripts can legitimately live outside the target.
            if relative.is_absolute() or ".." in relative.parts:
                continue
            if "__pycache__" in relative.parts or relative.suffix.lower() in {
                ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".so", ".dylib"
            }:
                continue
            if relative.name in {"RECORD", "direct_url.json", "INSTALLER", "REQUESTED"}:
                continue
            original = Path(dist.locate_file(entry)).resolve()
            if not original.is_relative_to(source) or not original.is_file():
                raise ValueError(f"Arquivo de dependência inválido: {entry}")
            content = original.read_bytes()
            if content.startswith((b"\x7fELF", b"MZ")):
                raise ValueError(f"Binário nativo inesperado: {entry}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def install_tree(destination, vendor=None):
    """Stage a package filesystem. Also called by Arch's package() function."""
    destination = Path(destination)
    app = destination / "usr/share/nodavira"
    app.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "app.py", app / "app.py")
    for folder in ("nodavira", "static"):
        for source in sorted((ROOT / folder).rglob("*")):
            if (not source.is_file() or source.is_symlink() or "__pycache__" in source.parts
                    or source.suffix in {".pyc", ".pyo", ".ico"}):
                continue
            target = app / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    if vendor:
        collect_vendor(vendor, app / ".deps")
    pairs = {
        "packaging/linux/nodavira": "usr/bin/nodavira",
        "packaging/linux/io.github.saintluc4.nodavira.desktop":
            "usr/share/applications/io.github.saintluc4.nodavira.desktop",
        "static/favicon.svg": "usr/share/icons/hicolor/scalable/apps/io.github.saintluc4.nodavira.svg",
        "static/app.png": "usr/share/icons/hicolor/256x256/apps/io.github.saintluc4.nodavira.png",
        "LICENSE": "usr/share/licenses/nodavira/LICENSE",
        "THIRD_PARTY_NOTICES.md": "usr/share/doc/nodavira/THIRD_PARTY_NOTICES.md",
        "docs/LINUX.md": "usr/share/doc/nodavira/LINUX.md",
        "METHODOLOGY.md": "usr/share/doc/nodavira/METHODOLOGY.md",
    }
    for original, relative in pairs.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Normalize shell/desktop files even in Windows checkouts.
        target.write_bytes((ROOT / original).read_bytes().replace(b"\r\n", b"\n"))
    (destination / "usr/bin/nodavira").chmod(0o755)
    (destination / "usr/share/doc/nodavira/copyright").write_text(
        (ROOT / "LICENSE").read_text(encoding="utf-8") + "\n" +
        (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8"), encoding="utf-8")


def tar_bytes(entries, epoch=0):
    """Stable tar metadata, POSIX paths and explicit executable permissions."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        directories = set()
        for name, content, mode in sorted(entries):
            for parent in reversed(PurePosixPath(name).parents):
                if str(parent) == "." or str(parent) in directories:
                    continue
                info = tarfile.TarInfo(str(parent))
                info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, epoch
                archive.addfile(info)
                directories.add(str(parent))
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(content), mode, epoch
            archive.addfile(info, io.BytesIO(content))
    return gzip.compress(output.getvalue(), mtime=epoch)


def ar_bytes(members, epoch=0):
    result = bytearray(b"!<arch>\n")
    for name, content in members:
        header = f"{name + '/':<16}{epoch:<12}{0:<6}{0:<6}{'100644':<8}{len(content):<10}`\n"
        if len(header) != 60:
            raise ValueError("Invalid ar header")
        result.extend(header.encode("ascii"))
        result.extend(content)
        if len(content) % 2:
            result.extend(b"\n")
    return result


def build_deb(output, vendor, epoch):
    with tempfile.TemporaryDirectory(prefix="nodavira-deb-") as directory:
        stage = Path(directory)
        install_tree(stage, vendor)
        entries = [(p.relative_to(stage).as_posix(), p.read_bytes(),
                    0o755 if p.relative_to(stage).as_posix() == "usr/bin/nodavira" else 0o644)
                   for p in stage.rglob("*") if p.is_file()]
        size = (sum(len(data) for _, data, _ in entries) + 1023) // 1024
        control = (f"Package: nodavira\nVersion: {__version__}-1\nArchitecture: all\n"
                   "Maintainer: saintluc4 <saintluc4@users.noreply.github.com>\n"
                   "Section: net\nPriority: optional\n"
                   f"Installed-Size: {size}\n"
                   "Depends: python3 (>= 3.11), python3-gi, python3-gi-cairo, "
                   "gir1.2-gtk-3.0, gir1.2-webkit2-4.1, ca-certificates, xdg-utils\n"
                   "Homepage: https://github.com/saintluc4/nodavira\n"
                   "Description: Local DNS benchmark with a GTK desktop interface\n"
                   " Compare latency and failures over UDP, DNS over HTTPS and DNS over TLS.\n"
                   " Supports IPv4/IPv6 and JSON/CSV reports without changing system DNS.\n")
        checksums = "".join(f"{hashlib.md5(data).hexdigest()}  {name}\n" for name, data, _ in sorted(entries))
        output.write_bytes(ar_bytes([
            ("debian-binary", b"2.0\n"),
            ("control.tar.gz", tar_bytes([("control", control.encode(), 0o644),
                                          ("md5sums", checksums.encode(), 0o644)], epoch)),
            ("data.tar.gz", tar_bytes(entries, epoch)),
        ], epoch))


def build_source(output, epoch):
    entries = [(f"nodavira-{__version__}/{p.relative_to(ROOT).as_posix()}", p.read_bytes(), 0o644)
               for p in source_files()]
    output.write_bytes(tar_bytes(entries, epoch))


def arch_recipe(output, source):
    template = (ROOT / "packaging/arch/PKGBUILD.in").read_text(encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    recipe = template.replace("@VERSION@", __version__).replace("@SHA256@", digest)
    (output / "PKGBUILD").write_text(recipe, encoding="utf-8", newline="\n")
    # makepkg --printsrcinfo is the authoritative generator, run in Linux CI.
    # Do not manufacture .SRCINFO here or claim that an AUR entry exists.
    shutil.copyfile(source, output / source.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor", type=Path, help="Installed pure-Python dependencies for the .deb")
    parser.add_argument("--stage", type=Path, help="Stage only the application, for makepkg")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/linux")
    args = parser.parse_args()
    if args.stage:
        install_tree(args.stage, args.vendor)
        return
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.output / f"nodavira-{__version__}.tar.gz"
    build_source(source, epoch)
    arch_recipe(args.output / "aur", source)
    artifacts = [source]
    if args.vendor:
        binary = args.output / f"nodavira_{__version__}-1_all.deb"
        build_deb(binary, args.vendor, epoch)
        artifacts.append(binary)
    (args.output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in artifacts), encoding="utf-8")
    for artifact in artifacts:
        print(artifact)


if __name__ == "__main__":
    main()
