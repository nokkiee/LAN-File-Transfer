"""LAN File Transfer - send files between computers on the same Wi-Fi/LAN.

The same code runs on Windows, Linux and macOS; every build speaks the same
protocol (see protocol.py), so any combination of them can exchange files.
"""

import platform
import sys

APP_NAME = "LAN File Transfer"
APP_SLUG = "lan-file-transfer"
VERSION = "1.1.2"

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"


def os_label() -> str:
    if IS_WINDOWS:
        return "Windows"
    if IS_LINUX:
        return "Linux"
    if IS_MAC:
        return "macOS"
    return platform.system() or "Unknown"
