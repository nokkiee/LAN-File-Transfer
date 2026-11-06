"""Translation catalogs: one module per language, each with a MESSAGES dict.

Keys are the English templates used in the code (see lanxfer/i18n.py). A value
is the translation, or for texts with a number, a tuple with one entry per
plural form (Polish has three: 1 plik, 2 pliki, 5 plików).
tests/test_i18n.py checks that every language translates every text.
"""
