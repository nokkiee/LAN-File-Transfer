"""Tests for the Linux applications-menu entry (no Qt needed)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer import desktop_entry  # noqa: E402


class DesktopEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.icons = self.home / "icons" / "hicolor" / "256x256" / "apps"
        self.desktop = self.home / "applications" / "lan-file-transfer.desktop"

    def tearDown(self):
        self.tmp.cleanup()

    def icon_line(self) -> str:
        return next(line for line in self.desktop.read_text().splitlines() if line.startswith("Icon="))

    def test_new_design_gets_new_name_and_old_icons_are_removed(self):
        self.icons.mkdir(parents=True)
        (self.icons / "lan-file-transfer.png").write_bytes(b"icon from 1.1.1 and older")
        (self.icons / "other-app.png").write_bytes(b"not ours")

        desktop_entry.install("/apps/LAN File Transfer", b"design one", self.home)
        first = desktop_entry.icon_name(b"design one")
        self.assertEqual(self.icon_line(), f"Icon={first}")
        self.assertEqual(sorted(p.name for p in self.icons.iterdir()), [f"{first}.png", "other-app.png"])
        self.assertIn('Exec="/apps/LAN File Transfer"', self.desktop.read_text())

        desktop_entry.install("/apps/LAN File Transfer", b"design two", self.home)
        second = desktop_entry.icon_name(b"design two")
        self.assertNotEqual(first, second)
        self.assertEqual(self.icon_line(), f"Icon={second}")
        self.assertEqual(sorted(p.name for p in self.icons.iterdir()), [f"{second}.png", "other-app.png"])
        self.assertEqual((self.icons / f"{second}.png").read_bytes(), b"design two")

    def test_unchanged_design_leaves_files_alone(self):
        desktop_entry.install("/apps/app", b"same", self.home)
        icon = self.icons / f"{desktop_entry.icon_name(b'same')}.png"
        before = (icon.stat().st_mtime_ns, self.desktop.stat().st_mtime_ns)
        desktop_entry.install("/apps/app", b"same", self.home)
        self.assertEqual((icon.stat().st_mtime_ns, self.desktop.stat().st_mtime_ns), before)


if __name__ == "__main__":
    unittest.main()
