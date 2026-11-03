"""The app icon, drawn in code so no image files have to be shipped."""

import struct

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap


def icon_image(size: int) -> QImage:
    """Graphite tile in the app's dark-theme greys, with one white and one blue arrow."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    m = size * 0.06
    rect = QRectF(m, m, size - 2 * m, size - 2 * m)
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0, QColor("#3a3d44"))
    grad.setColorAt(1, QColor("#25272c"))
    # The thin lighter edge keeps the tile visible on dark taskbars.
    p.setPen(QPen(QColor("#4a4e57"), max(1.0, size * 0.012)))
    p.setBrush(grad)
    p.drawRoundedRect(rect, size * 0.22, size * 0.22)

    s = size
    head = s * 0.12
    p.setBrush(Qt.BrushStyle.NoBrush)
    # -> on top in the theme's text colour, <- below in its highlight blue
    for y, x0, x1, color in ((0.37, 0.27, 0.73, "#e6e7ea"), (0.63, 0.73, 0.27, "#3b82f6")):
        pen = QPen(QColor(color), max(1.5, s * 0.085))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QPainterPath(QPointF(s * x0, s * y))
        path.lineTo(s * x1, s * y)
        direction = 1 if x1 > x0 else -1
        tip = QPointF(s * x1, s * y)
        path.moveTo(tip.x() - direction * head, tip.y() - head)
        path.lineTo(tip)
        path.lineTo(tip.x() - direction * head, tip.y() + head)
        p.drawPath(path)
    p.end()
    return img


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(icon_image(size)))
    return icon


def png_bytes(size: int) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    icon_image(size).save(buf, "PNG")
    buf.close()
    return bytes(data.data())


def ico_bytes(sizes=(16, 24, 32, 48, 64, 128, 256)) -> bytes:
    """A multi-resolution Windows .ico (PNG-compressed entries)."""
    images = [png_bytes(s) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for size, data in zip(sizes, images):
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + entries + b"".join(images)
