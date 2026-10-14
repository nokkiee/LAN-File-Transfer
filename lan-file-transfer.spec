# PyInstaller recipe shared by the Windows and Linux builds.
# Build with:  pyinstaller --noconfirm lan-file-transfer.spec   (after tools/make_icon.py)
import sys

windows = sys.platform.startswith("win")

a = Analysis(
    ["main.py"],
    excludes=["tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="LAN-File-Transfer-Windows" if windows else "LAN-File-Transfer-Linux",
    console=False,
    icon="build/icon.ico" if windows else None,
    upx=False,
    strip=not windows,
)
