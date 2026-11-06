"""Tests for translations: every language translates every text, with the same placeholders."""

import importlib
import string
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from i18n_strings import collect  # noqa: E402

from lanxfer import i18n  # noqa: E402
from lanxfer.i18n import Msg, tr, tr_msg  # noqa: E402

TEMPLATES = collect()


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class CatalogTests(unittest.TestCase):
    def test_every_language_translates_every_text(self):
        for code in i18n.LANGUAGES:
            if code == "en":
                continue
            with self.subTest(language=code):
                catalog = importlib.import_module(f"lanxfer.locales.{code}").MESSAGES
                missing = sorted(set(TEMPLATES) - set(catalog))
                unused = sorted(set(catalog) - set(TEMPLATES))
                self.assertEqual(missing, [], f"{code}: not translated")
                self.assertEqual(unused, [], f"{code}: translations no longer used by the code")

    def test_placeholders_and_plural_forms_match(self):
        for code in i18n.LANGUAGES:
            if code == "en":
                continue
            catalog = importlib.import_module(f"lanxfer.locales.{code}").MESSAGES
            for english, plural in TEMPLATES.items():
                value = catalog.get(english)
                if value is None:
                    continue
                with self.subTest(language=code, text=english):
                    expected = fields(english) | (fields(plural) if plural else set())
                    if plural:
                        self.assertIsInstance(value, tuple, "needs one entry per plural form")
                        self.assertEqual(len(value), i18n.PLURAL_FORMS[code])
                        forms = value
                    else:
                        self.assertIsInstance(value, str)
                        forms = (value,)
                    for form in forms:
                        self.assertEqual(fields(form), expected)
                        if fields(form):
                            form.format(**{k: 1 for k in fields(form)})  # must not raise

    def test_qt_markup_is_kept(self):
        for code in i18n.LANGUAGES:
            if code == "en":
                continue
            catalog = importlib.import_module(f"lanxfer.locales.{code}").MESSAGES
            for english, value in catalog.items():
                for tag in ("<b>", "</b>"):
                    for form in (value if isinstance(value, tuple) else (value,)):
                        self.assertEqual(english.count(tag), form.count(tag), f"{code}: {english!r}")


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_polish_plurals(self):
        i18n.set_language("pl")
        self.assertEqual([tr("{n} file", "{n} files", n=n) for n in (1, 2, 4, 5, 12, 22, 25)],
                         ["1 plik", "2 pliki", "4 pliki", "5 plików", "12 plików", "22 pliki", "25 plików"])

    def test_french_treats_zero_as_singular(self):
        i18n.set_language("fr")
        self.assertEqual(tr("{n} file", "{n} files", n=0), "0 fichier")
        self.assertEqual(tr("{n} file", "{n} files", n=2), "2 fichiers")

    def test_messages_stay_english_until_shown(self):
        i18n.set_language("de")
        m = Msg("Delivered to {name}", name="Laptop")
        self.assertEqual(m, "Delivered to Laptop")         # logs and the network see English
        self.assertEqual(tr_msg(m), "An Laptop zugestellt")  # the window shows German
        nested = Msg("The other computer could not save the files: {error}",
                     error=Msg("The connection to the other computer was lost."))
        self.assertEqual(tr_msg(nested), "Der andere Computer konnte die Dateien nicht speichern: "
                                         "Die Verbindung zum anderen Computer wurde unterbrochen.")
        # A reason sent by another computer arrives as plain English text:
        self.assertEqual(tr_msg("The other computer declined the files."),
                         "Der andere Computer hat die Dateien abgelehnt.")
        self.assertEqual(tr_msg("Something nobody translated"), "Something nobody translated")

    def test_english_and_unknown_languages(self):
        self.assertEqual(i18n.set_language("xx") in i18n.LANGUAGES, True)
        i18n.set_language("en")
        self.assertEqual(tr("{n} file", "{n} files", n=3), "3 files")
        self.assertEqual(i18n.decimal(1.25, 1), "1.2")
        i18n.set_language("es")
        self.assertEqual(i18n.decimal(1.5), "1,5")


if __name__ == "__main__":
    unittest.main()
