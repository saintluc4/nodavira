"""Platform choices kept separate from the DNS measurement engine."""
import os
import sys
from pathlib import Path


def reports_directory(root, platform=None, environ=None, home=None):
    platform = sys.platform if platform is None else platform
    if platform.startswith("linux"):
        environ = os.environ if environ is None else environ
        home = Path.home() if home is None else Path(home)
        configured = environ.get("XDG_DATA_HOME", "")
        base = Path(configured) if configured and Path(configured).is_absolute() else home / ".local/share"
        return base / "nodavira/reports"
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(root)
    return base / "reports"


def window_options(assets, platform=None):
    platform = sys.platform if platform is None else platform
    assets = Path(assets)
    if platform == "win32":
        return {"gui": "edgechromium", "icon": str(assets / "app.ico")}
    if platform.startswith("linux"):
        return {"gui": "gtk", "icon": str(assets / "favicon.svg")}
    raise RuntimeError("A janela do Nodavira suporta Windows e Linux. Use --browser neste sistema.")


def startup_error(exc):
    if sys.platform == "win32":
        hint = ("A janela requer Microsoft Edge WebView2 Runtime e .NET Framework 4.6.2 ou superior.\n"
                "WebView2: https://developer.microsoft.com/microsoft-edge/webview2/\n"
                "Alternativa: Nodavira.exe --browser.")
    else:
        hint = ("A janela Linux requer uma sessão gráfica, GTK 3, PyGObject e WebKitGTK 4.1.\n"
                "Consulte docs/LINUX.md para instalar as dependências.\n"
                "Alternativa: nodavira --browser (ou python3 app.py --browser no código-fonte).")
    return f"Não foi possível iniciar o Nodavira.\n\n{hint}\n\nDetalhe: {type(exc).__name__}: {exc}"
