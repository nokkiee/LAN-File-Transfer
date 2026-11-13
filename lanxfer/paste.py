"""Turn what was copied into files to send, for Ctrl+V in the file list.

Copied files are sent as they are. A copied image or piece of text is first
saved as a file in the "pasted" folder (in the app's settings folder, not a temp
folder, so an interrupted send can still find it after a restart). Pasted files
are deleted again when they're removed from the list, or at a later start once
no send that could still be resumed needs them.
"""

import os
import time
from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QImage, QPixmap

from .i18n import tr

GNOME_FILES = "x-special/gnome-copied-files"  # what GNOME Files puts on the clipboard
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
KEEP_UNUSED = 24 * 3600  # seconds; spares a file another running copy of the app has just pasted


def paths_from_clipboard(mime: QMimeData | None, folder: Path) -> list[str]:
    """The files to add for what was copied, saving an image or text into ``folder``.

    Returns [] when there's nothing usable. Raises OSError if saving fails.
    """
    if mime is None:
        return []
    files = _existing([u.toLocalFile() for u in mime.urls() if u.isLocalFile()]) if mime.hasUrls() else []
    if not files and mime.hasFormat(GNOME_FILES):
        lines = bytes(mime.data(GNOME_FILES)).decode("utf-8", "replace").splitlines()
        files = _existing([QUrl(line).toLocalFile() for line in lines[1:] if line.startswith("file:")])
    if files:
        return files  # a web address with the picture ("Copy image") falls through to the picture
    png = bytes(mime.data("image/png")) if mime.hasFormat("image/png") else b""
    if png.startswith(PNG_MAGIC):
        return [_save(folder, tr("Pasted image"), ".png", png)]
    if mime.hasImage():
        image = mime.imageData()
        if isinstance(image, QPixmap):
            image = image.toImage()
        if isinstance(image, QImage) and not image.isNull():
            return [_save(folder, tr("Pasted image"), ".png", image=image)]
    text = mime.text() if mime.hasText() else ""
    if text.strip():
        return _paths_in(text) or [_save(folder, tr("Pasted text"), ".txt", text.encode("utf-8"))]
    return []


def _existing(paths: list[str]) -> list[str]:
    return [os.path.abspath(p) for p in paths if p and os.path.exists(p)]


def _paths_in(text: str) -> list[str]:
    """The files named by copied text that is nothing but file paths (e.g. Windows "Copy as path")."""
    paths = []
    for line in filter(None, (line.strip().strip('"') for line in text.splitlines())):
        path = QUrl(line).toLocalFile() if line.startswith("file:") else line
        if not (os.path.isabs(path) and os.path.exists(path)):
            return []
        paths.append(path)
    return _existing(paths)


def _save(folder: Path, what: str, ext: str, data: bytes = b"", image: QImage | None = None) -> str:
    """Write a new file named like "Pasted image 2026-11-13 14.05.22.png" and return its path."""
    folder = Path(os.path.abspath(folder))
    folder.mkdir(parents=True, exist_ok=True)
    stem, n = f"{what} {time.strftime('%Y-%m-%d %H.%M.%S')}", 0
    while True:
        path = folder / (f"{stem}{ext}" if n == 0 else f"{stem} ({n}){ext}")
        try:
            with open(path, "xb") as f:
                if image is None:
                    f.write(data)
            break
        except FileExistsError:
            n += 1
    if image is not None and not image.save(str(path), "PNG"):
        path.unlink(missing_ok=True)
        raise OSError(f"could not write {path}")
    return str(path)


def is_pasted(path: str, folder: Path) -> bool:
    return os.path.normcase(os.path.dirname(os.path.abspath(path))) == os.path.normcase(os.path.abspath(folder))


def forget(paths: list[str], folder: Path) -> None:
    """Delete the pasted files among ``paths`` (they were taken off the list before being sent)."""
    for path in paths:
        if is_pasted(path, folder):
            try:
                os.unlink(path)
            except OSError:
                pass


def prune(folder: Path, keep: set[str]) -> None:
    """Delete pasted files that no send can still need (``keep``: the files of sends that can be resumed)."""
    keep = {os.path.normcase(os.path.abspath(p)) for p in keep}
    try:
        names = os.listdir(folder)
    except OSError:
        return
    now = time.time()
    for name in names:
        path = os.path.join(os.path.abspath(folder), name)
        try:
            if (os.path.normcase(path) not in keep and os.path.isfile(path)
                    and now - os.path.getmtime(path) > KEEP_UNUSED):
                os.unlink(path)
        except OSError:
            pass
