"""Persistent settings stored as JSON in the user's config folder."""

import json
import logging
import os
import socket
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import APP_NAME, APP_SLUG, IS_MAC, IS_WINDOWS
from .protocol import DEFAULT_TCP_PORT

log = logging.getLogger(__name__)


def config_dir() -> Path:
    override = os.environ.get("LANXFER_CONFIG_DIR")
    if override:
        path = Path(override)
    elif IS_WINDOWS:
        path = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    elif IS_MAC:
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_download_dir() -> str:
    downloads = Path.home() / "Downloads"
    return str((downloads if downloads.is_dir() else Path.home()) / APP_NAME)


@dataclass
class Settings:
    device_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    device_name: str = field(default_factory=lambda: socket.gethostname() or "My computer")
    download_dir: str = field(default_factory=default_download_dir)
    ask_before_receiving: bool = True
    tcp_port: int = DEFAULT_TCP_PORT
    manual_peers: list[str] = field(default_factory=list)
    theme: str = "system"  # "system", "light" or "dark"
    auto_install_updates: bool = False  # install updates from your other computers without asking
    language: str = "auto"  # "auto" (the system's language), "en", "pl", "de", "fr" or "es"

    @classmethod
    def load(cls) -> "Settings":
        path = config_dir() / "settings.json"
        data = {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            log.exception("Could not read %s, using defaults", path)
        known = {f.name for f in fields(cls)}
        settings = cls(**{k: v for k, v in data.items() if k in known})
        if not data:
            settings.save()
        return settings

    def save(self) -> None:
        path = config_dir() / "settings.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        os.replace(tmp, path)
