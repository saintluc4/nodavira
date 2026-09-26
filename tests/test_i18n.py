import copy
import json
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.deps'), str(ROOT)]
from nodavira.i18n import Preferences, default_language, translate, localize_report, translations


class TranslationTests(unittest.TestCase):
    def test_preference_survives_restart_and_rejects_invalid_language(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'nested/preferences.json'
            prefs = Preferences(path)
            prefs.save('en')
            self.assertEqual(Preferences(path).language, 'en')
            with self.assertRaises(ValueError):
                prefs.save('../../other')
            self.assertEqual(json.loads(path.read_text()), {'language': 'en'})
            prefs.save('pt-BR')
            self.assertEqual(Preferences(path).language, 'pt-BR')
            self.assertFalse(list(path.parent.glob('.preferences-*')))

    def test_system_language_and_corrupt_file_fallback(self):
        for system, expected in [('pt_BR', 'pt-BR'), ('pt_PT','pt-BR'), ('en_US','en'), ('de_DE','en'), (None,'en')]:
            with patch('nodavira.i18n.locale.getlocale', return_value=(system, None)):
                self.assertEqual(default_language(), expected)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'preferences.json'
            path.write_text('{invalid')
            with patch('nodavira.i18n.default_language', return_value='en'):
                self.assertEqual(Preferences(path).language, 'en')

    def test_progress_and_validation_preserve_user_text(self):
        self.assertEqual(translate('Passagem 2/3 · Meu DNS · UDP', 'en'), 'Pass 2/3 · Meu DNS · UDP')
        self.assertEqual(translate('Verificando Meu DNS · DOH · IPv6', 'en'), 'Checking Meu DNS · DOH · IPv6')
        self.assertEqual(translate('Domínio inválido: <script>', 'en'), 'Invalid domain: <script>')
        self.assertEqual(translate('Selecione A e/ou AAAA.', 'en'), 'Select A and/or AAAA.')
        self.assertEqual(translate('raw external error', 'en'), 'raw external error')

    def test_report_translation_does_not_change_measurements_or_engine_state(self):
        original = {'message':'Benchmark concluído.', 'completed':4,
                    'rows':[{'name':'DNS do sistema','score_ms':12.34}],
                    'samples':[{'domain':'example.com','status':'timeout','ms':500.0,
                                'detail':'Tempo limite excedido'}]}
        before = copy.deepcopy(original)
        translated = localize_report(original, 'en')
        self.assertEqual(original, before)
        self.assertEqual(translated['rows'], original['rows'])
        self.assertEqual(translated['message'], 'Benchmark complete.')
        self.assertEqual(translated['samples'][0]['detail'], 'Request timed out')
        self.assertEqual(translated['samples'][0]['ms'], 500.0)
        self.assertEqual(translated['samples'][0]['status'], 'timeout')

    def test_interpolation_placeholders_match(self):
        for source, english in translations().items():
            self.assertEqual(set(re.findall(r'\{\w+\}', source)), set(re.findall(r'\{\w+\}', english)), source)

    def test_static_portuguese_text_and_dynamic_keys_have_translations(self):
        # Catch accidentally added untranslated UI strings, including accessibility text.
        known = translations()
        neutral = {'Nodavira', 'LOCAL', 'NODAVIRA', 'P95', 'HTTPS', 'TLS', 'DNS over HTTPS',
                   'DNS over TLS', 'Timeout (ms)', 'ms', 'IPv4 + IPv6', 'UDP / HTTPS / TLS',
                   'RFC 8484 · DoH ↗', 'RFC 7858 · DoT ↗', 'Português', 'English', '↓ JSON', '↓ CSV'}
        missing = []
        class Texts(HTMLParser):
            def handle_data(self, text):
                text = text.strip()
                if re.search('[A-Za-zÀ-ÿ]', text) and text not in neutral and text not in known and not re.fullmatch(r'Nodavira · v[\d.]+ ·', text):
                    missing.append(text)
            def handle_starttag(self, tag, attrs):
                for key, value in attrs:
                    if key in ('placeholder','aria-label') and value not in known and value not in neutral:
                        missing.append(value)
        Texts().feed((ROOT/'static/index.html').read_text(encoding='utf-8'))
        for key in re.findall(r"\bt\('([^']*)'", (ROOT/'static/app.js').read_text(encoding='utf-8')):
            if key not in known:
                missing.append(key)
        self.assertEqual(missing, [])


if __name__ == '__main__':
    unittest.main()
