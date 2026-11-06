# PyInstaller recipe shared by the Windows, Linux and macOS builds.
# Build with:  pyinstaller --noconfirm lan-file-transfer.spec   (after tools/make_icon.py)
#   Windows -> dist/LAN-File-Transfer-Windows.exe   (one file)
#   Linux   -> dist/LAN-File-Transfer-Linux         (one file)
#   macOS   -> dist/LAN File Transfer.app           (an app bundle, Apple Silicon)
import sys

from PyInstaller.utils.hooks import collect_submodules

sys.path.insert(0, SPECPATH)
from lanxfer import APP_NAME, VERSION  # noqa: E402

windows = sys.platform.startswith("win")
mac = sys.platform == "darwin"

a = Analysis(
    ["main.py"],
    # The translation catalogs are imported by name at run time, so list them explicitly.
    hiddenimports=collect_submodules("lanxfer.locales"),
    excludes=["tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick"],
)
pyz = PYZ(a.pure)

if mac:
    # Apps on macOS are folders (bundles), so this is a one-folder build wrapped in a .app.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME, console=False, upx=False,
              target_arch="arm64")
    coll = COLLECT(exe, a.binaries, a.datas, upx=False, name=APP_NAME)
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon="build/icon.icns",
        bundle_identifier="io.github.nokkiee.lan-file-transfer",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "14.0",  # what Qt for Python 6.12 needs
            "LSApplicationCategoryType": "public.app-category.utilities",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # follow the system's dark mode
            # Shown when macOS asks whether the app may use the local network.
            "NSLocalNetworkUsageDescription":
                "LAN File Transfer finds your other computers on this network and sends files to them.",
        },
    )
else:
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
