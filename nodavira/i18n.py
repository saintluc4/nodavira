"""Local UI preferences and translation of application-owned messages only."""
import json
import locale
import os
import re
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


def default_language():
    try:
        name = locale.getlocale()[0] or ''
    except (ValueError, TypeError):
        name = ''
    return 'pt-BR' if name.lower().startswith(('pt', 'portuguese')) else 'en'


def preferences_path():
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData/Roaming')
    else:
        configured = os.environ.get('XDG_CONFIG_HOME', '')
        base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / '.config'
    return base / 'nodavira/preferences.json'


class Preferences:
    def __init__(self, path):
        self.path = Path(path)
        self.language = default_language()
        try:
            value = json.loads(self.path.read_text(encoding='utf-8')).get('language')
            if value in ('pt-BR', 'en'):
                self.language = value
        except (OSError, ValueError, AttributeError):
            pass

    def save(self, language):
        if language not in ('pt-BR', 'en'):
            raise ValueError('Idioma inválido.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.preferences-', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({'language': language}, stream)
            os.replace(temporary, self.path)
            self.language = language
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def translations():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return json.loads((root / 'static/en.json').read_text(encoding='utf-8'))


PATTERNS = [
    (r'Verificando (.*) · (.*) · (.*)', 'Verificando {name} · {protocol} · {family}', ('name', 'protocol', 'family')),
    (r'Passagem (\d+)/(\d+) · (.*) · (.*)', 'Passagem {pass}/{rounds} · {name} · {protocol}', ('pass', 'rounds', 'name', 'protocol')),
    (r'Domínio inválido: (.*)', 'Domínio inválido: {detail}', ('detail',)),
    (r'Não foi possível salvar automaticamente: (.*)\. Use Exportar\.', 'Não foi possível salvar automaticamente: {detail}. Use Exportar.', ('detail',)),
    (r'Erro no benchmark: (.*)', 'Erro no benchmark: {detail}', ('detail',)),
]


def translate(text, language):
    if language != 'en' or not isinstance(text, str):
        return text
    messages = translations()
    if text in messages:
        return messages[text]
    for pattern, key, fields in PATTERNS:
        match = re.fullmatch(pattern, text, flags=re.DOTALL)
        if match:
            return messages[key].format_map(dict(zip(fields, match.groups())))
    return text


def localize_report(report, language):
    # Do not mutate engine state, numeric data, IDs, names, addresses or status codes.
    result = dict(report, language=language)
    for key in ('message', 'save_error'):
        if key in result:
            result[key] = translate(result[key], language)
    for key in ('samples', 'diagnostics'):
        if key in result:
            result[key] = [dict(sample, detail=translate(sample.get('detail', ''), language))
                           for sample in result[key]]
    return result
