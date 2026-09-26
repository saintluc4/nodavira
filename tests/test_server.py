import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.deps'), str(ROOT)]
from nodavira.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server, cls.state = make_server(ROOT/'static', cls.temp.name)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
        cls.temp.cleanup()

    def request(self, path='/api/status', token=True, body=None, headers=None):
        request_headers = {'X-Nodavira-Token': self.state.token} if token else {}
        request_headers.update(headers or {})
        request = urllib.request.Request(self.base+path, data=json.dumps(body).encode() if body is not None else None, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def test_authorized_status(self):
        status, body, _ = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['state'], 'idle')

    def test_api_rejects_missing_token(self):
        self.assertEqual(self.request(token=False)[0], 403)

    def test_api_rejects_foreign_origin(self):
        self.assertEqual(self.request(headers={'Origin':'https://example.com'})[0], 403)

    def test_api_rejects_dns_rebinding_host(self):
        self.assertEqual(self.request(headers={'Host':'attacker.example'})[0], 403)

    def test_invalid_configuration_rejected_without_starting(self):
        self.assertEqual(self.request('/api/start', body={'resolvers':[]})[0], 400)
        self.assertIsNone(self.state.worker)

    def test_static_security_headers_and_no_path_traversal(self):
        status, body, headers = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'Nodavira', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(self.request('/../app.py')[0], 404)

    def test_json_export_is_parseable(self):
        status, body, headers = self.request('/api/export.json')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(json.loads(body)['state'], 'idle')

    def test_language_api_requires_auth_and_validates_values(self):
        self.assertEqual(self.request('/api/preferences', token=False, body={'language':'en'})[0], 403)
        self.assertEqual(self.request('/api/preferences', body={'language':'fr'})[0], 400)
        self.assertEqual(self.request('/api/preferences', body={'language':['en']})[0], 400)
        self.assertEqual(self.request('/api/preferences', body={'language':'en'})[0], 200)
        self.assertEqual(json.loads(self.request('/api/config')[1])['language'], 'en')
        self.assertEqual(json.loads(self.request()[1])['message'], 'Ready to start')
        status, body, _ = self.request('/api/start', body={'resolvers':[]}, headers={'X-Nodavira-Language':'en'})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)['error'], 'Select between 1 and 32 servers.')
        self.assertEqual(json.loads(self.request(headers={'X-Nodavira-Language':'pt-BR'})[1])['message'], 'Pronto para começar')
        self.assertEqual(self.request('/api/preferences', body={'language':'pt-BR'})[0], 200)

    def test_translation_assets_are_packaged_and_served(self):
        self.assertEqual(self.request('/i18n.js')[0], 200)
        self.assertEqual(json.loads(self.request('/en.json')[1])['Idioma'], 'Language')


if __name__ == '__main__': unittest.main()
