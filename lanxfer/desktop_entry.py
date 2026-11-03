"""The Linux applications-menu entry and icon for the packaged app.

The icon file's name includes a short hash of the picture. When the icon
design changes, the name changes too, so desktops like GNOME can't keep showing
a cached copy of the old icon. With a fixed name they do, until you log out.
"""

import hashlib
import logging
import os
import shutil
import subprocess
from pathlib import Path

from . import APP_NAME, APP_SLUG

log = logging.getLogger(__name__)


def default_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def icon_name(icon_png: bytes) -> str:
    return f"{APP_SLUG}-{hashlib.sha256(icon_png).hexdigest()[:8]}"


def install(exe: str, icon_png: bytes, data_home: Path | None = None) -> None:
    """Create or update the menu entry for ``exe`` with the given 256x256 PNG icon."""
    data_home = data_home or default_data_home()
    theme_dir = data_home / "icons" / "hicolor"
    icon_dir = theme_dir / "256x256" / "apps"
    name = icon_name(icon_png)
    icon_path = icon_dir / f"{name}.png"

    icons_changed = False
    if not icon_path.exists():
        icon_dir.mkdir(parents=True, exist_ok=True)
        icon_path.write_bytes(icon_png)
        icons_changed = True
    # Remove icons from earlier designs, including the old fixed-name one.
    for old in [icon_dir / f"{APP_SLUG}.png", *icon_dir.glob(f"{APP_SLUG}-*.png")]:
        if old != icon_path and old.exists():
            old.unlink()
            icons_changed = True
    if icons_changed:
        _refresh_icon_cache(theme_dir)

    quoted_exe = exe.replace('"', '\\"')
    entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Send files to another computer on the same Wi-Fi\n"
        f'Exec="{quoted_exe}"\n'
        f"Icon={name}\n"
        "Terminal=false\n"
        "Categories=Network;FileTransfer;Utility;\n"
        f"StartupWMClass={APP_SLUG}\n"
    )
    desktop_path = data_home / "applications" / f"{APP_SLUG}.desktop"
    if not desktop_path.exists() or desktop_path.read_text(encoding="utf-8") != entry:
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_path.write_text(entry, encoding="utf-8")


def _refresh_icon_cache(theme_dir: Path) -> None:
    """Make sure desktops notice the new icon file."""
    try:
        os.utime(theme_dir)  # a newer folder date tells GTK not to trust an older cache
    except OSError:
        pass
    if not (theme_dir / "icon-theme.cache").exists():
        return
    # If some other program created a cache here, rebuild it so the new icon is listed.
    tool = shutil.which("gtk4-update-icon-cache") or shutil.which("gtk-update-icon-cache")
    if tool:
        try:
            subprocess.run([tool, "-q", "-f", "-t", str(theme_dir)], timeout=20, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            log.warning("Could not refresh the icon cache in %s", theme_dir, exc_info=True)
