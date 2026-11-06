"""Write build/icon.ico, build/icon.icns and build/icon.png (used by the PyInstaller builds)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from lanxfer.icon import icns_bytes, ico_bytes, png_bytes  # noqa: E402

app = QGuiApplication(sys.argv)
out = ROOT / "build"
out.mkdir(exist_ok=True)
(out / "icon.ico").write_bytes(ico_bytes())
(out / "icon.icns").write_bytes(icns_bytes())
(out / "icon.png").write_bytes(png_bytes(256))
print(f"wrote {out / 'icon.ico'}, {out / 'icon.icns'} and {out / 'icon.png'}")
