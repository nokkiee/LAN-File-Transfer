"""Tests for pasting into the file list: copied files, images and text become files to send."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QByteArray, QBuffer, QMimeData, QUrl  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage  # noqa: E402

from lanxfer import paste  # noqa: E402

app = QGuiApplication.instance() or QGuiApplication([])


def red_image(width=40, height=30) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    return image


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


class PasteTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="lanxfer-paste-"))
        self.pasted = self.work / "pasted"
        self.file = self.work / "photo.jpg"
        self.file.write_bytes(b"jpeg")
        self.folder = self.work / "album"
        self.folder.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.work, ignore_errors=True)

    def paste(self, mime: QMimeData) -> list[str]:
        return paste.paths_from_clipboard(mime, self.pasted)

    def test_copied_files_are_added_as_they_are(self):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.file)), QUrl.fromLocalFile(str(self.folder))])
        mime.setImageData(red_image())  # Finder also puts the file's icon on the clipboard
        mime.setText("photo.jpg")
        self.assertEqual(self.paste(mime), [str(self.file), str(self.folder)])
        self.assertFalse(self.pasted.exists())

    def test_files_copied_in_gnome_files(self):
        for action in ("copy", "cut"):
            mime = QMimeData()
            data = f"{action}\n{QUrl.fromLocalFile(str(self.file)).toString()}\n" \
                   f"{QUrl.fromLocalFile(str(self.folder)).toString()}"
            mime.setData(paste.GNOME_FILES, QByteArray(data.encode()))
            self.assertEqual(self.paste(mime), [str(self.file), str(self.folder)])
        self.assertTrue(self.file.exists(), "a cut file is only sent, never moved")

    def test_a_copied_image_is_saved_as_png(self):
        mime = QMimeData()
        mime.setImageData(red_image())
        [path] = self.paste(mime)
        self.assertEqual(Path(path).parent, self.pasted)
        self.assertRegex(Path(path).name, r"^Pasted image \d{4}-\d\d-\d\d \d\d\.\d\d\.\d\d\.png$")
        loaded = QImage(path)
        self.assertEqual((loaded.width(), loaded.height()), (40, 30))
        self.assertEqual(loaded.pixelColor(5, 5), QColor("red"))

    def test_png_bytes_are_kept_exactly(self):
        data = png_bytes(red_image(7, 9))
        mime = QMimeData()
        mime.setData("image/png", QByteArray(data))
        [path] = self.paste(mime)
        self.assertEqual(Path(path).read_bytes(), data)

    def test_a_web_address_with_the_picture_gives_the_picture(self):
        mime = QMimeData()  # a browser's "Copy image"
        mime.setUrls([QUrl("https://example.com/cat.png")])
        mime.setImageData(red_image())
        [path] = self.paste(mime)
        self.assertTrue(path.endswith(".png"))

    def test_copied_text_is_saved_as_a_text_file(self):
        mime = QMimeData()
        mime.setText("Zażółć gęślą jaźń\nhttps://example.com\n")
        [path] = self.paste(mime)
        self.assertTrue(Path(path).name.startswith("Pasted text "))
        self.assertTrue(path.endswith(".txt"))
        self.assertEqual(Path(path).read_text(encoding="utf-8"), "Zażółć gęślą jaźń\nhttps://example.com\n")

    def test_copied_paths_add_the_files_themselves(self):
        mime = QMimeData()  # e.g. Windows Explorer's "Copy as path", one per line, in quotes
        mime.setText(f'"{self.file}"\r\n{QUrl.fromLocalFile(str(self.folder)).toString()}\r\n')
        self.assertEqual(self.paste(mime), [str(self.file), str(self.folder)])
        mime.setText(f"{self.file}\n{self.work / 'missing.txt'}")
        [path] = self.paste(mime)  # not all of them exist: it's just text
        self.assertTrue(path.endswith(".txt"))

    def test_nothing_usable_gives_nothing(self):
        self.assertEqual(self.paste(QMimeData()), [])
        self.assertEqual(paste.paths_from_clipboard(None, self.pasted), [])
        mime = QMimeData()
        mime.setText("   \n")
        mime.setUrls([QUrl.fromLocalFile(str(self.work / "gone.txt"))])
        self.assertEqual(self.paste(mime), [])
        self.assertFalse(self.pasted.exists())

    def test_pasting_twice_makes_two_files(self):
        mime = QMimeData()
        mime.setImageData(red_image())
        first, second, third = self.paste(mime), self.paste(mime), self.paste(mime)
        self.assertEqual(len({*first, *second, *third}), 3)
        self.assertTrue(all(os.path.getsize(p) > 0 for p in [*first, *second, *third]))

    def test_saving_fails_cleanly(self):
        self.pasted.write_text("a file where the folder should be")
        mime = QMimeData()
        mime.setImageData(red_image())
        with self.assertRaises(OSError):
            self.paste(mime)

    def test_forget_deletes_only_pasted_files(self):
        mime = QMimeData()
        mime.setImageData(red_image())
        [pasted] = self.paste(mime)
        paste.forget([pasted, str(self.file), str(self.folder)], self.pasted)
        self.assertFalse(os.path.exists(pasted))
        self.assertTrue(self.file.exists())
        self.assertTrue(self.folder.exists())

    def test_prune_keeps_what_a_resumable_send_needs(self):
        self.pasted.mkdir()
        old = time.time() - paste.KEEP_UNUSED - 60
        needed, unused, recent = (self.pasted / n for n in ("needed.png", "unused.png", "recent.png"))
        for f in (needed, unused, recent):
            f.write_bytes(b"x")
        for f in (needed, unused):
            os.utime(f, (old, old))
        paste.prune(self.pasted, {str(needed)})
        self.assertTrue(needed.exists())
        self.assertFalse(unused.exists())
        self.assertTrue(recent.exists(), "might belong to another copy of the app that is running")
        paste.prune(self.work / "no such folder", set())  # nothing to do, no error


if __name__ == "__main__":
    unittest.main()
