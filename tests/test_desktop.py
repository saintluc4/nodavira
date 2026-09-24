import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'.deps'), str(ROOT)]
from nodavira.desktop import run_window
from nodavira.server import AppState


class Event:
    def __init__(self): self.callbacks=[]
    def __iadd__(self, callback):
        self.callbacks.append(callback)
        return self
    def fire(self, *args):
        for callback in self.callbacks: callback(*args)


class FakeWindow:
    def __init__(self):
        self.events=type('Events', (), {name:Event() for name in ('initialized','loaded','closing','closed')})()
        self.destroyed=threading.Event()
    def destroy(self):
        self.events.closing.fire()
        self.events.closed.fire()
        self.destroyed.set()


class FakeWebview:
    def __init__(self, shutdown=None, fail=False):
        self.settings={}
        self.window=FakeWindow()
        self.shutdown=shutdown
        self.fail=fail
    def create_window(self, *args, **kwargs):
        self.creation=(args,kwargs)
        return self.window
    def start(self, **kwargs):
        self.options=kwargs
        if self.fail: raise RuntimeError('WebView2 unavailable')
        self.window.events.initialized.fire('gtkwebkit2' if kwargs['gui']=='gtk' else 'edgechromium')
        self.window.events.loaded.fire()
        if self.shutdown:
            self.shutdown.set()
            if not self.window.destroyed.wait(2): raise RuntimeError('Window did not close')
        else:
            self.window.destroy()


class DesktopTests(unittest.TestCase):
    def test_window_loads_without_exposing_custom_python_api(self):
        state=AppState(ROOT/'reports')
        ui=FakeWebview()
        run_window('http://127.0.0.1:1234/#token=test',state,threading.Event(),webview_module=ui,platform='win32')
        self.assertEqual(state.snapshot()['desktop'],{'mode':'desktop','renderer':'edgechromium','loaded':True})
        self.assertNotIn('js_api',ui.creation[1])
        self.assertEqual(ui.options['gui'],'edgechromium')
        self.assertFalse(ui.settings['IGNORE_SSL_ERRORS'])
        self.assertFalse(ui.settings['ALLOW_FILE_URLS'])
        self.assertTrue(ui.settings['ALLOW_DOWNLOADS'])
        self.assertTrue(state.stop.is_set())

    def test_linux_window_uses_gtk_and_preserves_security_and_shutdown(self):
        finished=threading.Event()
        ui=FakeWebview(shutdown=finished)
        state=AppState(ROOT/'reports')
        run_window('http://127.0.0.1:1234/#token=test',state,finished,
                   hidden=True,webview_module=ui,platform='linux')
        self.assertEqual(state.snapshot()['desktop'],
                         {'mode':'desktop','renderer':'gtkwebkit2','loaded':True})
        self.assertTrue(ui.options['private_mode'])
        self.assertTrue(ui.options['icon'].endswith('favicon.svg'))
        self.assertFalse(ui.settings['IGNORE_SSL_ERRORS'])
        self.assertNotIn('js_api',ui.creation[1])
        self.assertTrue(ui.window.destroyed.is_set())
        self.assertTrue(state.stop.is_set())

    def test_api_shutdown_closes_window(self):
        finished=threading.Event()
        ui=FakeWebview(shutdown=finished)
        state=AppState(ROOT/'reports')
        run_window('http://127.0.0.1:1234/',state,finished,hidden=True,webview_module=ui)
        self.assertTrue(ui.window.destroyed.is_set())
        self.assertTrue(state.stop.is_set())

    def test_window_initialization_failure_cancels_workers(self):
        state=AppState(ROOT/'reports')
        with self.assertRaises(RuntimeError):
            run_window('http://127.0.0.1:1234/',state,threading.Event(),webview_module=FakeWebview(fail=True))
        self.assertTrue(state.stop.is_set())
