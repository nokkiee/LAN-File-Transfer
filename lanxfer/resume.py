"""What the app remembers about interrupted transfers, so they can continue later.

Every file transfer gets a random session id. Once the receiver accepts it,
both computers write a small record:

  * the sender keeps the exact file list it offered and who it was for;
  * the receiver keeps the folder the files go into and each file's place in it.

The receiver doesn't need to write down its progress: a file that arrived in
full has its final name, and the one that was cut off is still "<name>.part".
When the sender comes back with the same session id, the receiver looks at the
disk and answers with what it already has.

Records are JSON files in <config folder>/transfers/ (or kept in memory only,
for tests and command-line tools) and are forgotten after KEEP_FOR. A finished
or abandoned receive is remembered for the same time as a short "complete" or
"discarded" note, so a late resume can be answered correctly instead of asking
the user about files they already have.
"""

import json
import logging
import os
import re
import secrets
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .pathsafe import split_relpath

log = logging.getLogger(__name__)

KEEP_FOR = 30 * 24 * 3600  # seconds

OPEN, COMPLETE, DISCARDED = "open", "complete", "discarded"

_SESSION_ID = re.compile(r"[0-9a-f]{32}")


def new_session_id() -> str:
    return secrets.token_hex(16)


def valid_session_id(value) -> str | None:
    """The id if it looks like one of ours (it's used in file names), else None."""
    return value if isinstance(value, str) and _SESSION_ID.fullmatch(value) else None


def part_path(dest: Path) -> Path:
    """Where a file is written while it arrives."""
    return dest.with_name(dest.name + ".part")


@dataclass
class SendRecord:
    session: str
    peer_id: str
    peer_name: str
    peer_ip: str
    peer_port: int
    entries: list[dict]        # {"kind", "rel", "source", "size"}, exactly as offered
    created: float = field(default_factory=time.time)
    files_done: int = 0        # progress when it was interrupted, for the window
    done_bytes: int = 0

    kind = "send"


@dataclass
class ReceiveRecord:
    session: str
    sender_id: str
    sender_name: str
    folder: str                # the numbered folder, e.g. ".../0012 2026-11-06 09.15.00 3 files"
    items: list[dict]          # the offered items, as validated
    dests: list[str]           # where each item goes, relative to folder, "/"-separated
    created: float = field(default_factory=time.time)
    state: str = OPEN
    item_count: int = 0

    kind = "receive"

    def paths(self) -> list[Path]:
        folder = Path(self.folder)
        return [folder.joinpath(*split_relpath(rel)) for rel in self.dests]

    def closed(self, state: str) -> "ReceiveRecord":
        """A short note that this session is over (COMPLETE or DISCARDED)."""
        return ReceiveRecord(self.session, self.sender_id, self.sender_name, self.folder, [], [],
                             self.created, state, len(self.items) or self.item_count)


def remove_partials(paths: list[Path]) -> None:
    for dest in paths:
        try:
            part_path(dest).unlink()
        except OSError:
            pass


def remove_if_no_files(folder: Path) -> None:
    """Delete a transfer folder that ended up without any files."""
    try:
        if any(f for _, _, f in os.walk(folder)):
            return
        shutil.rmtree(folder)
    except OSError:
        pass


class SessionStore:
    """Records of resumable transfers, written through to ``folder`` if one is given."""

    def __init__(self, folder: Path | None = None):
        self.folder = folder
        self._records: dict[tuple[str, str], SendRecord | ReceiveRecord] = {}
        self._lock = threading.Lock()
        if folder is not None:
            self._load()

    def _path(self, kind: str, session: str) -> Path:
        return self.folder / f"{kind}-{session}.json"

    def _load(self) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            files = sorted(self.folder.glob("*.json"))
        except OSError:
            log.exception("Could not read saved transfers in %s", self.folder)
            return
        now = time.time()
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                kind = path.name.split("-", 1)[0]
                record = SendRecord(**data) if kind == "send" else ReceiveRecord(**data)
                if valid_session_id(record.session) is None or path.name != f"{kind}-{record.session}.json":
                    raise ValueError("bad session id")
                if isinstance(record, ReceiveRecord):
                    record.paths()  # every saved place must be inside its folder
            except (OSError, ValueError, TypeError):
                log.warning("Ignoring unreadable saved transfer %s", path.name)
                _unlink(path)
                continue
            if now - record.created > KEEP_FOR:
                self._expire(record, path)
                continue
            self._records[(kind, record.session)] = record

    def _expire(self, record, path: Path) -> None:
        log.info("Forgetting %s transfer %s (too old to resume)", record.kind, record.session)
        if isinstance(record, ReceiveRecord) and record.state == OPEN:
            remove_partials(record.paths())
            remove_if_no_files(Path(record.folder))
        _unlink(path)

    def save(self, record: SendRecord | ReceiveRecord) -> None:
        with self._lock:
            self._records[(record.kind, record.session)] = record
            if self.folder is None:
                return
            path = self._path(record.kind, record.session)
            tmp = path.with_suffix(".tmp")
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                tmp.write_text(json.dumps(asdict(record), ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, path)
            except OSError:
                log.exception("Could not save transfer %s", record.session)

    def get(self, kind: str, session: str):
        with self._lock:
            return self._records.get((kind, session))

    def delete(self, kind: str, session: str) -> None:
        with self._lock:
            self._records.pop((kind, session), None)
            if self.folder is not None:
                _unlink(self._path(kind, session))

    def all(self) -> list:
        with self._lock:
            return sorted(self._records.values(), key=lambda r: r.created)


def _unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass
