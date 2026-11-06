"""Light and dark appearance.

The app always uses Qt's Fusion style with its own palettes, so it looks the
same on Windows, Linux and macOS, and the theme switch behaves identically on all three.
"System" follows the operating system's light/dark setting, live.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

THEMES = {"system": "Same as system", "light": "Light", "dark": "Dark"}

_LIGHT = {
    "Window": "#f3f4f6", "WindowText": "#111827", "Base": "#ffffff", "AlternateBase": "#f1f3f6",
    "Text": "#111827", "Button": "#e8eaee", "ButtonText": "#111827", "BrightText": "#dc2626",
    "Highlight": "#2563eb", "HighlightedText": "#ffffff", "ToolTipBase": "#ffffff",
    "ToolTipText": "#111827", "PlaceholderText": "#8a909c", "Link": "#2563eb",
    "Light": "#ffffff", "Midlight": "#eceef2", "Mid": "#c4c8d0", "Dark": "#9aa0aa", "Shadow": "#5f6570",
}
_DARK = {
    "Window": "#1f2125", "WindowText": "#e6e7ea", "Base": "#2a2d32", "AlternateBase": "#30333a",
    "Text": "#e6e7ea", "Button": "#33363d", "ButtonText": "#e6e7ea", "BrightText": "#f87171",
    "Highlight": "#3b82f6", "HighlightedText": "#ffffff", "ToolTipBase": "#2a2d32",
    "ToolTipText": "#e6e7ea", "PlaceholderText": "#868b94", "Link": "#60a5fa",
    "Light": "#41454d", "Midlight": "#383b42", "Mid": "#4a4e57", "Dark": "#16181b", "Shadow": "#0b0c0e",
}
_DISABLED = {"light": "#a0a5ae", "dark": "#6b7079"}


def system_is_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def is_dark(theme: str) -> bool:
    return theme == "dark" or (theme == "system" and system_is_dark())


def build_palette(dark: bool) -> QPalette:
    palette = QPalette()
    for role, color in (_DARK if dark else _LIGHT).items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    disabled = QColor(_DISABLED["dark" if dark else "light"])
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#7b8494"))
    return palette


class ThemeManager:
    def __init__(self, app: QApplication, theme: str):
        self.app = app
        self.theme = theme if theme in THEMES else "system"
        app.setStyle("Fusion")
        app.styleHints().colorSchemeChanged.connect(lambda _: self.theme == "system" and self.apply())
        self.apply()

    def set(self, theme: str) -> None:
        self.theme = theme if theme in THEMES else "system"
        self.apply()

    def apply(self) -> None:
        self.app.setPalette(build_palette(is_dark(self.theme)))
