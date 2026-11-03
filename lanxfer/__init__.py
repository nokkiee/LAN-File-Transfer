"""LAN File Transfer - send files between computers on the same Wi-Fi/LAN.

The same code runs on Windows and Linux; both builds speak the same protocol
(see protocol.py), so any combination of the two can exchange files.
"""

import platform
import sys

APP_NAME = "LAN File Transfer"
APP_SLUG = "lan-file-transfer"
VERSION = "1.1.1"

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")


def os_label() -> str:
    if IS_WINDOWS:
        return "Windows"
    if IS_LINUX:
        return "Linux"
    if sys.platform == "darwin":
        return "macOS"
    return platform.system() or "Unknown"
