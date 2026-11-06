"""List every text the app translates: the English templates passed to tr() and Msg().

    python tools/i18n_strings.py        # prints them, one per line
Used by tests/test_i18n.py to check that every language translates all of them.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect() -> dict[str, str | None]:
    """{english template: english plural or None}"""
    found: dict[str, str | None] = {}
    for path in sorted((ROOT / "lanxfer").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            if name not in ("tr", "Msg") or not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                continue
            plural = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                plural = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "plural" and isinstance(kw.value, ast.Constant):
                    plural = kw.value.value
            found[first.value] = plural if plural is not None else found.get(first.value)
    # Texts translated through a variable rather than a literal (read from the source, so no Qt is needed):
    themes = _constant(ROOT / "lanxfer" / "theme.py", "THEMES")
    months = _constant(ROOT / "lanxfer" / "updates.py", "MONTHS")
    for text in [*themes.values(), *months, "B", "KB", "MB", "GB", "TB"]:
        found.setdefault(text, None)
    return found


def _constant(path: Path, name: str):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise LookupError(f"{name} not found in {path}")


if __name__ == "__main__":
    for template, plural in collect().items():
        print(repr(template) + (f"  | plural: {plural!r}" if plural else ""))
