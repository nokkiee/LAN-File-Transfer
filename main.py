"""Start LAN File Transfer. The same file is the entry point on Windows, Linux and macOS."""

import json
import logging
import logging.handlers
import sys
from pathlib import Path

from lanxfer import APP_NAME, APP_SLUG, IS_LINUX, IS_WINDOWS, VERSION
from lanxfer.settings import Settings, config_dir


def setup_logging() -> None:
    handler = logging.handlers.RotatingFileHandler(config_dir() / "app.log", maxBytes=1_000_000,
                                                   backupCount=1, encoding="utf-8")
    handlers: list[logging.Handler] = [handler]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from lanxfer._build import BUILD
    logging.getLogger(__name__).info("%s %s (build %s) starting", APP_NAME, VERSION, BUILD)


def install_linux_menu_entry() -> None:
    """When run as the packaged Linux binary, add it to the applications menu."""
    from lanxfer import desktop_entry
    from lanxfer.icon import png_bytes

    try:
        desktop_entry.install(sys.executable, png_bytes(256))
    except OSError:
        logging.getLogger(__name__).warning("Could not create the applications menu entry", exc_info=True)


def run_self_test(report: str) -> int:
    """Run by a freshly downloaded update (and by the build checks) before it's used:
    load everything the app needs, then report which version this is."""
    import PySide6.QtWidgets  # noqa: F401
    from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: F401
    from PySide6.QtCore import QLibraryInfo, QTranslator

    import lanxfer.gui  # noqa: F401
    from lanxfer import i18n
    from lanxfer._build import BUILD

    for code in i18n.LANGUAGES:  # every translation must be part of the build
        i18n.set_language(code)
    qt_translations = QTranslator().load("qtbase_pl", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    Path(report).write_text(json.dumps({"version": VERSION, "build": BUILD, "qt_translations": qt_translations}),
                            encoding="utf-8")
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--self-test":
        return run_self_test(sys.argv[2])
    setup_logging()
    from lanxfer import updates
    updates.cleanup_after_update()
    if IS_WINDOWS:
        import ctypes
        try:  # own taskbar icon instead of Python's
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LANFileTransfer")
        except (AttributeError, OSError):
            pass

    from PySide6.QtCore import QLibraryInfo, QTranslator
    from PySide6.QtWidgets import QApplication

    from lanxfer import i18n
    from lanxfer.gui import MainWindow
    from lanxfer.icon import app_icon
    from lanxfer.theme import ThemeManager

    app = QApplication(sys.argv)
    settings = Settings.load()
    language = i18n.set_language(settings.language)
    # Qt's own texts (OK, Cancel, Yes, No, file dialogs) in the same language.
    qt_translator = QTranslator(app)
    if language != "en" and qt_translator.load(f"qtbase_{language}",
                                               QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_translator)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setDesktopFileName(APP_SLUG)
    app.setWindowIcon(app_icon())
    if IS_LINUX and getattr(sys, "frozen", False):
        install_linux_menu_entry()

    window = MainWindow(settings, ThemeManager(app, settings.theme))
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
