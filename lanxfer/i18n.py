"""Translations of the app's texts (English, Polish, German, French, Spanish).

Texts are written in English in the code. ``tr("Send files to {name}", name=n)``
looks the English template up in the current language's catalog
(lanxfer/locales/<code>.py), then fills in the values.

Messages made by the networking code (transfer.py, updates.py) stay in English,
so logs and the messages sent between computers are the same everywhere. They
are ``Msg`` objects: ordinary strings that remember their template and values,
so ``tr_msg()`` can show them in the user's language. A plain English string
that matches a catalog entry exactly (for example a reason sent by another
computer) is translated too.
"""

import importlib
import locale
import os

LANGUAGES = {  # code -> the language's own name, as shown in Settings
    "en": "English",
    "pl": "Polski",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
}
AUTO = "auto"

_language = "en"
_catalog: dict = {}


def _plural_index(lang: str, n: int) -> int:
    """Which plural form a language uses for ``n`` (index into a catalog tuple)."""
    if lang == "pl":  # 1 plik, 2-4 pliki, 5+ plików (but 12-14 plików)
        if n == 1:
            return 0
        return 1 if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 2
    if lang == "fr":  # 0 and 1 are singular
        return 0 if n in (0, 1) else 1
    return 0 if n == 1 else 1


PLURAL_FORMS = {"en": 2, "pl": 3, "de": 2, "fr": 2, "es": 2}


def system_language() -> str:
    """The supported language closest to the computer's own setting, else English."""
    candidates = []
    try:  # Qt knows the macOS/Windows UI language even when no locale variables are set
        from PySide6.QtCore import QLocale
        candidates += [name.replace("-", "_") for name in QLocale.system().uiLanguages()]
    except ImportError:
        pass
    candidates += [os.environ.get(v, "") for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except ValueError:
        pass
    for name in candidates:
        code = name.split(":")[0][:2].lower()
        if code in LANGUAGES:
            return code
    return "en"


def set_language(code: str) -> str:
    """Switch language ("auto" follows the system). Returns the language now in use."""
    global _language, _catalog
    if code == AUTO or code not in LANGUAGES:
        code = system_language()
    _language = code
    _catalog = {} if code == "en" else importlib.import_module(f"lanxfer.locales.{code}").MESSAGES
    return code


def current_language() -> str:
    return _language


def tr(template: str, plural: str | None = None, n: int | None = None, **values) -> str:
    """Translate an English template (and its plural) into the current language, then fill it in."""
    entry = _catalog.get(template)
    if isinstance(entry, tuple):
        text = entry[min(_plural_index(_language, n if n is not None else 1), len(entry) - 1)]
    elif isinstance(entry, str):
        text = entry
    else:  # English, or not translated yet
        text = plural if plural is not None and n != 1 else template
    return text.format(n=n, **values) if (values or n is not None) else text


class Msg(str):
    """An English message that remembers how it was made, so it can be shown in another language."""

    template: str
    plural: str | None
    n: int | None
    values: dict

    def __new__(cls, template: str, plural: str | None = None, n: int | None = None, **values):
        english = plural if plural is not None and n != 1 else template
        obj = super().__new__(cls, english.format(n=n, **values) if (values or n is not None) else english)
        obj.template, obj.plural, obj.n, obj.values = template, plural, n, values
        return obj


def tr_msg(text) -> str:
    """Show a message from the networking code (a Msg, or plain English) in the current language."""
    if isinstance(text, Msg):
        values = {k: tr_msg(v) if isinstance(v, str) else v for k, v in text.values.items()}
        return tr(text.template, text.plural, text.n, **values)
    if isinstance(text, str) and text in _catalog and isinstance(_catalog[text], str):
        return _catalog[text]
    return text


def decimal(value: float, digits: int = 1) -> str:
    """A number with the language's decimal separator (1.5 in English, 1,5 elsewhere)."""
    text = f"{value:.{digits}f}"
    return text if _language == "en" else text.replace(".", ",")
