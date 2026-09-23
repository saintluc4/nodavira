"""Windows window host. DNS and exports continue to use the authenticated local API."""
import threading
import sys
from pathlib import Path


def run_window(url, state, server_finished, hidden=False, webview_module=None):
    if webview_module is None:
        import webview as webview_module
    webview = webview_module
    webview.settings.update(ALLOW_DOWNLOADS=True, ALLOW_FILE_URLS=False,
                            OPEN_EXTERNAL_LINKS_IN_BROWSER=True, IGNORE_SSL_ERRORS=False)
    state.set_desktop(mode="desktop")
    window = webview.create_window("Nodavira", url, width=1280, height=860,
                                   min_size=(900, 650), background_color="#f7f5fb",
                                   text_select=True, hidden=hidden)
    closed = threading.Event()

    def initialized(renderer):
        state.set_desktop(renderer=renderer)

    def loaded():
        state.set_desktop(loaded=True)

    def closing():
        state.stop.set()

    def on_closed():
        closed.set()

    def close_after_shutdown():
        while not closed.wait(.2):
            if server_finished.is_set():
                window.destroy()
                return

    window.events.initialized += initialized
    window.events.loaded += loaded
    window.events.closing += closing
    window.events.closed += on_closed
    threading.Thread(target=close_after_shutdown, daemon=True).start()
    try:
        # Refuse legacy IE/EdgeHTML fallback: the app needs a modern web engine.
        assets = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "static"
        webview.start(gui="edgechromium", private_mode=True, debug=False, icon=str(assets / "app.ico"))
    finally:
        closed.set()
        state.stop.set()
