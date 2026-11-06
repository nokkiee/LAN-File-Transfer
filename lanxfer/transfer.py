"""Sending and receiving files over TCP. No GUI code here.

Transfers run on background threads and only update plain attributes on
Transfer objects; the GUI polls them. Incoming offers are handed to a
``present`` callback; the connection thread waits until offer.answer() is called.
"""

import hashlib
import itertools
import logging
import os
import re
import select
import shutil
import socket
import stat
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import os_label
from .i18n import Msg, tr
from .pathsafe import plan_destinations, split_relpath, top_level_paths
from .protocol import (
    ABORT_MARKER, APP_ID, CHUNK_SIZE, DIGEST_SIZE, END_OF_FILE, MAX_CHUNK, PROTOCOL_VERSION,
    ProtocolError, RemoteCancelled, pack_u32, recv_exact, recv_frame, recv_u32, remote_stop, send_frame,
)

log = logging.getLogger(__name__)

DECISION_TIMEOUT = 120.0  # how long the receiver has to click Accept
IO_TIMEOUT = 60.0         # give up if the other side stalls this long

# Transfer states
WAITING, PREPARING, ACTIVE, DONE, FAILED, CANCELLED, DECLINED = (
    "waiting", "preparing", "active", "done", "failed", "cancelled", "declined")
FINISHED_STATES = {DONE, FAILED, CANCELLED, DECLINED}

_ids = itertools.count(1)


class Cancelled(Exception):
    pass


@dataclass
class Transfer:
    direction: str            # "send" or "receive"
    peer_name: str
    peer_ip: str
    kind: str = "files"       # "files" or "update" (a new version of the app itself)
    id: int = field(default_factory=lambda: next(_ids))
    state: str = WAITING
    message: str = ""
    items: list[str] = field(default_factory=list)   # top-level names (update: the new version)
    file_count: int = 0
    total_bytes: int = 0
    done_bytes: int = 0
    files_done: int = 0
    skipped: int = 0
    current_file: str = ""
    save_dir: str = ""        # receive: folder the files went into
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def is_finished(self) -> bool:
        return self.state in FINISHED_STATES

    def cancel(self) -> None:
        self.cancel_event.set()

    def _check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise Cancelled()

    def _finish(self, state: str, message: str = "") -> None:
        self.state = state
        self.message = message
        self.finished = time.monotonic()


@dataclass
class Offer:
    """An incoming request waiting for the user to accept or decline."""
    transfer: Transfer
    sender_name: str
    sender_os: str
    sender_ip: str
    items: list[dict]
    save_dir: str
    free_bytes: int | None
    withdrawn: bool = False   # sender gave up, or nobody answered in time
    _decided: threading.Event = field(default_factory=threading.Event, repr=False)
    _accepted: bool = False

    def answer(self, accept: bool) -> None:
        self._accepted = accept
        self._decided.set()


def wait_for_answer(conn: socket.socket, offer, timeout: float = DECISION_TIMEOUT) -> bool | None:
    """Block until offer.answer() is called. True/False, or None if the sender gave up first.

    ``offer`` is anything with ``_decided``, ``_accepted`` and ``withdrawn``.
    """
    deadline = time.monotonic() + timeout
    while not offer._decided.wait(0.25):
        readable, _, _ = select.select([conn], [], [], 0)
        if readable:  # the sender only talks now if it cancelled or vanished
            offer.withdrawn = True
            return None
        if time.monotonic() > deadline:
            offer.withdrawn = True
            return False
    return offer._accepted


def describe_error(exc: BaseException) -> str:
    """A message for the user. Our own messages are Msg objects, so the window can translate them."""
    if isinstance(exc, RemoteCancelled):
        return str(exc) or Msg("The other computer stopped the transfer.")
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return Msg("The other computer stopped responding.")
    if isinstance(exc, ConnectionRefusedError):
        return Msg("Could not connect. Is the app open on the other computer?")
    if isinstance(exc, (ConnectionError, BrokenPipeError)):
        return Msg("The connection to the other computer was lost.")
    if isinstance(exc, ProtocolError):
        detail = exc.args[0] if exc.args else ""
        return Msg("The other computer sent unexpected data ({detail}). Are both apps the same version?",
                   detail=detail)
    if exc.args and isinstance(exc.args[0], Msg):
        return exc.args[0]
    if isinstance(exc, OSError) and exc.strerror:
        return exc.strerror + (f": {exc.filename}" if exc.filename else "")
    return str(exc) or exc.__class__.__name__


def abort_politely(sock: socket.socket, reason: str, in_file_data: bool = False, failed: bool = False) -> None:
    """Tell the other side we are stopping, without making it see a reset."""
    try:
        sock.settimeout(3)
        if in_file_data:
            sock.sendall(pack_u32(ABORT_MARKER))
        send_frame(sock, {"type": "cancel", "reason": reason, "failed": failed})
        sock.shutdown(socket.SHUT_WR)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and sock.recv(65536):
            pass
    except OSError:
        pass


def finish_from_remote(transfer: Transfer, exc: RemoteCancelled) -> None:
    transfer._finish(FAILED if exc.failed else CANCELLED, describe_error(exc))


# ---------------------------------------------------------------------------
# File data on the wire (shared by file transfers and app updates)
# ---------------------------------------------------------------------------

def send_file_data(sock: socket.socket, f, transfer: Transfer) -> None:
    """Stream an open file as chunks, an end marker and its SHA-256."""
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    digest = hashlib.sha256()
    while True:
        n = f.readinto(buf)
        if not n:
            break
        digest.update(view[:n])
        sock.sendall(pack_u32(n))
        sock.sendall(view[:n])
        transfer.done_bytes += n
        _check_receiver(sock)
        transfer._check_cancel()
    sock.sendall(pack_u32(END_OF_FILE) + digest.digest())


def recv_file_data(conn: socket.socket, f, transfer: Transfer, name: str) -> str:
    """Receive what send_file_data() sent into ``f``. Returns the SHA-256 (hex)."""
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    digest = hashlib.sha256()
    while True:
        length = recv_u32(conn)
        if length == END_OF_FILE:
            break
        if length == ABORT_MARKER:
            raise remote_stop(recv_frame(conn), Msg("The sender cancelled the transfer."))
        if length > MAX_CHUNK:
            raise ProtocolError("chunk too large")
        remaining = length
        while remaining:
            n = conn.recv_into(view, min(remaining, CHUNK_SIZE))
            if n == 0:
                raise ConnectionError("connection closed")
            f.write(view[:n])
            digest.update(view[:n])
            remaining -= n
            transfer.done_bytes += n
        transfer._check_cancel()
    if recv_exact(conn, DIGEST_SIZE) != digest.digest():
        raise ProtocolError(Msg("{name} was damaged in transit (checksum mismatch)", name=name))
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Receiving
# ---------------------------------------------------------------------------

class Receiver:
    """Accepts incoming connections and saves the offered files."""

    def __init__(self, identity: Callable[[], dict], save_dir: Callable[[], str],
                 present: Callable[[Offer], None], on_new_transfer: Callable[[Transfer], None]):
        self.identity = identity
        self.save_dir = save_dir
        self.present = present  # shows the offer; someone must call offer.answer()
        self.on_new_transfer = on_new_transfer
        # Other request types (e.g. "update"): handler(conn, peer_ip, first_message)
        self.extra_handlers: dict[str, Callable[[socket.socket, str, dict], None]] = {}
        self.port: int | None = None
        self._server: socket.socket | None = None
        self._reserved: set[str] = set()
        self._reserve_lock = threading.Lock()

    def start(self, preferred_port: int, attempts: int = 10) -> int:
        last_error: OSError | None = None
        for port in range(preferred_port, preferred_port + attempts):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if not hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind(("", port))
                server.listen(8)
            except OSError as exc:
                server.close()
                last_error = exc
                continue
            self._server = server
            self.port = port
            threading.Thread(target=self._accept_loop, name="receiver", daemon=True).start()
            return port
        raise OSError(f"No free port between {preferred_port} and {preferred_port + attempts - 1}: {last_error}")

    def stop(self) -> None:
        if self._server:
            try:
                self._server.shutdown(socket.SHUT_RDWR)  # wakes accept() on Linux
            except OSError:
                pass
            self._server.close()

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, addr = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn, addr[0]), daemon=True).start()

    def _handle(self, conn: socket.socket, peer_ip: str) -> None:
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn.settimeout(30)
            try:
                first = recv_frame(conn)
            except (OSError, ProtocolError):
                return
            if first.get("app") != APP_ID:
                return
            kind = first.get("type")
            if kind == "ping":
                try:
                    send_frame(conn, {"app": APP_ID, "type": "pong", **self.identity()})
                except OSError:
                    pass
                return
            handler = self._receive if kind == "offer" else self.extra_handlers.get(kind)
            if handler:
                try:
                    handler(conn, peer_ip, first)
                except Exception:
                    log.exception("Unexpected error while handling %r from %s", kind, peer_ip)

    def _receive(self, conn: socket.socket, peer_ip: str, offer_msg: dict) -> None:
        sender = offer_msg.get("sender") if isinstance(offer_msg.get("sender"), dict) else {}
        transfer = Transfer("receive", str(sender.get("name") or peer_ip)[:100], peer_ip)
        if offer_msg.get("version") != PROTOCOL_VERSION:
            send_frame(conn, {"type": "reject", "reason": Msg("The two apps are different versions. Please update both.")})
            return
        try:
            items = _validate_items(offer_msg.get("items"))
        except ValueError:
            send_frame(conn, {"type": "reject", "reason": Msg("The other computer refused the file list (invalid names).")})
            return

        save_dir = Path(self.save_dir())
        transfer.items = _top_level_names(items)
        transfer.file_count = sum(1 for i in items if i["kind"] == "file")
        transfer.total_bytes = sum(i["size"] for i in items if i["kind"] == "file")
        transfer.save_dir = str(save_dir)
        free = _free_space(save_dir)
        self.on_new_transfer(transfer)

        offer = Offer(transfer, transfer.peer_name, str(sender.get("os") or "?"), peer_ip, items,
                      str(save_dir), free)
        reserved: set[str] = set()
        folder: Path | None = None

        def finish(state: str, message: str) -> None:
            if folder is not None:
                _remove_if_no_files(folder)  # e.g. cancelled before the first file arrived
            transfer._finish(state, message)

        try:
            transfer.message = Msg("Waiting for you to accept")
            self.present(offer)
            answer = wait_for_answer(conn, offer)
            if answer is None:
                transfer._finish(CANCELLED, Msg("The sender cancelled before you answered."))
                return
            if not answer:
                answered = offer._decided.is_set()
                transfer._finish(DECLINED, Msg("You declined these files.") if answered else Msg("Not answered in time."))
                send_frame(conn, {"type": "reject", "reason": Msg("The other computer declined the files.") if answered
                                  else Msg("Nobody answered on the other computer.")})
                return
            save_dir.mkdir(parents=True, exist_ok=True)
            with self._reserve_lock:
                folder = make_transfer_folder(save_dir, transfer.file_count)
                transfer.save_dir = str(folder)
                destinations = plan_destinations(items, folder, reserved=self._reserved)
                reserved = {str(p).casefold() for p in top_level_paths(folder, destinations)}
                self._reserved |= reserved
            send_frame(conn, {"type": "accept"})
            transfer.state = ACTIVE
            transfer.message = ""
            transfer.started = time.monotonic()
            for item, dest in zip(items, destinations):
                if item["kind"] == "dir":
                    dest.mkdir(parents=True, exist_ok=True)
            self._receive_files(conn, transfer, items, destinations)
            send_frame(conn, {"type": "done"})
            if transfer.skipped:
                done = Msg("Saved to {folder} ({n} file could not be read on the other computer)",
                           "Saved to {folder} ({n} files could not be read on the other computer)",
                           n=transfer.skipped, folder=str(folder))
            else:
                done = Msg("Saved to {folder}", folder=str(folder))
            transfer._finish(DONE, done)
        except Cancelled:
            finish(CANCELLED, Msg("You cancelled the transfer."))
            abort_politely(conn, Msg("The other computer cancelled the transfer."))
        except RemoteCancelled as exc:
            finish(FAILED if exc.failed else CANCELLED, describe_error(exc))
        except OSError as exc:
            log.warning("Receive from %s failed: %s", peer_ip, exc)
            finish(FAILED, describe_error(exc))
            if not isinstance(exc, (ConnectionError, socket.timeout, TimeoutError)):
                abort_politely(conn, Msg("The other computer could not save the files: {error}",
                                         error=describe_error(exc)), failed=True)
        except ProtocolError as exc:
            finish(FAILED, describe_error(exc))
        finally:
            with self._reserve_lock:
                self._reserved -= reserved

    def _receive_files(self, conn: socket.socket, transfer: Transfer, items: list[dict],
                       destinations: list[Path]) -> None:
        conn.settimeout(IO_TIMEOUT)
        while True:
            transfer._check_cancel()
            msg = recv_frame(conn)
            kind = msg.get("type")
            if kind == "end":
                return
            if kind == "cancel":
                raise remote_stop(msg, Msg("The sender cancelled the transfer."))
            index = msg.get("index")
            if not isinstance(index, int) or not 0 <= index < len(items) or items[index]["kind"] != "file":
                raise ProtocolError("bad file index")
            if kind == "skip":
                transfer.skipped += 1
                transfer.total_bytes -= items[index]["size"]
                continue
            if kind != "file":
                raise ProtocolError(f"unexpected message {kind!r}")

            dest = destinations[index]
            transfer.current_file = items[index]["path"]
            announced = int(msg.get("size") or 0)
            transfer.total_bytes += announced - items[index]["size"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_name(dest.name + ".part")
            try:
                with open(part, "wb") as f:
                    recv_file_data(conn, f, transfer, dest.name)
                os.replace(part, dest)
            except BaseException:
                try:
                    part.unlink()
                except OSError:
                    pass
                raise
            mtime = msg.get("mtime")
            if isinstance(mtime, (int, float)):
                try:
                    os.utime(dest, (time.time(), mtime))
                except (OSError, OverflowError, ValueError):
                    pass
            transfer.files_done += 1


_NUMBERED = re.compile(r"(\d{4,}) ")


def make_transfer_folder(base: Path, file_count: int, when: float | None = None) -> Path:
    """Create the folder for one incoming transfer, e.g. "0007 2026-10-12 12.32.02 7 files".

    Numbers keep counting up from the highest folder already there. The time
    uses dots because Windows doesn't allow ":" in names.
    """
    numbers = []
    for entry in base.iterdir():
        match = _NUMBERED.match(entry.name)
        if match and entry.is_dir():
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    clock = time.strftime("%Y-%m-%d %H.%M.%S", time.localtime(when))
    files = tr("{n} file", "{n} files", n=file_count)  # in the app's language, since it's shown in folders
    while True:
        folder = base / f"{number:04d} {clock} {files}"
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            number += 1


def _remove_if_no_files(folder: Path) -> None:
    """Delete a transfer folder that ended up without any files (cancelled early)."""
    try:
        if any(f for _, _, f in os.walk(folder)):
            return
        shutil.rmtree(folder)
    except OSError:
        pass


def _validate_items(raw) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("no items")
    items = []
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("kind") not in ("file", "dir"):
            raise ValueError("bad item")
        path, size = entry.get("path"), entry.get("size", 0)
        if not isinstance(path, str) or not isinstance(size, int) or size < 0:
            raise ValueError("bad item")
        split_relpath(path)  # rejects absolute paths and "..", before the user is asked
        items.append({"kind": entry["kind"], "path": path, "size": size if entry["kind"] == "file" else 0})
    return items


def _top_level_names(items: list[dict]) -> list[str]:
    seen = {}
    for item in items:
        seen.setdefault(item["path"].split("/")[0], None)
    return list(seen)


def _free_space(path: Path) -> int | None:
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

class Outgoing:
    """One outgoing connection: connect, offer, stream, and uniform error handling.

    Usage: Outgoing(transfer, ip, port).run(body), where body() uses
    offer() / stream() / final_reply() and finishes the transfer when done.
    """

    def __init__(self, transfer: Transfer, ip: str, port: int):
        self.transfer = transfer
        self.ip = ip
        self.port = port
        self.sock: socket.socket | None = None
        self.in_file_data = False

    def offer(self, message: dict, waiting_text: str) -> bool:
        """Connect and send the opening message. False if the other side declined."""
        t = self.transfer
        t.message = Msg("Connecting")
        try:
            self.sock = socket.create_connection((self.ip, self.port), timeout=8)
        except OSError as exc:
            raise OSError(Msg("Could not connect to {name}. Make sure the app is open there "
                              "and that its firewall allows it.", name=t.peer_name)) from exc
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(IO_TIMEOUT)
        send_frame(self.sock, message)
        t.state = WAITING
        t.message = waiting_text
        reply = _wait_for_frame(self.sock, t, DECISION_TIMEOUT + 30)
        if reply.get("type") == "reject":
            t._finish(DECLINED, reply.get("reason") or Msg("The other computer declined."))
            return False
        if reply.get("type") != "accept":
            raise ProtocolError(f"unexpected reply {reply.get('type')!r}")
        t.state = ACTIVE
        t.message = ""
        t.started = time.monotonic()
        return True

    def stream(self, f) -> None:
        self.in_file_data = True
        send_file_data(self.sock, f, self.transfer)
        self.in_file_data = False

    def final_reply(self, timeout: float) -> dict:
        reply = _wait_for_frame(self.sock, self.transfer, timeout)
        if reply.get("type") == "cancel":
            raise remote_stop(reply, Msg("The other computer stopped the transfer."))
        if reply.get("type") != "done":
            raise ProtocolError(f"unexpected reply {reply.get('type')!r}")
        return reply

    def run(self, body: Callable[[], None]) -> None:
        t = self.transfer
        try:
            body()
        except Cancelled:
            t._finish(CANCELLED, Msg("You cancelled the transfer."))
            if self.sock:
                abort_politely(self.sock, Msg("The sender cancelled the transfer."), self.in_file_data)
        except RemoteCancelled as exc:
            finish_from_remote(t, exc)
        except (OSError, ProtocolError) as exc:
            log.warning("Send to %s failed: %s", self.ip, exc)
            remote = _pending_cancel(self.sock) if self.sock else None
            if remote:
                finish_from_remote(t, remote)
            else:
                t._finish(FAILED, describe_error(exc))
        finally:
            if self.sock:
                self.sock.close()


def build_manifest(paths: list[str]) -> list["_Entry"]:
    """Expand the chosen files/folders into a flat list (folders recursively)."""
    entries: list[_Entry] = []
    used_top: set[str] = set()

    def top_name(path: Path) -> str:
        name = path.name or path.drive.rstrip(":\\/") or "files"
        candidate, n = name, 1
        while candidate.casefold() in used_top:
            n += 1
            stem, ext = (name, "") if path.is_dir() else os.path.splitext(name)
            candidate = f"{stem} ({n}){ext}"
        used_top.add(candidate.casefold())
        return candidate

    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            root = top_name(path)
            entries.append(_Entry("dir", root, str(path)))
            for dirpath, dirnames, filenames in os.walk(path):
                rel_dir = Path(dirpath).relative_to(path).as_posix()
                prefix = root if rel_dir == "." else f"{root}/{rel_dir}"
                dirnames[:] = sorted(d for d in dirnames if not os.path.islink(os.path.join(dirpath, d)))
                for d in dirnames:
                    entries.append(_Entry("dir", f"{prefix}/{d}", os.path.join(dirpath, d)))
                for name in sorted(filenames):
                    full = os.path.join(dirpath, name)
                    try:
                        st = os.stat(full)
                    except OSError:
                        continue
                    if stat.S_ISREG(st.st_mode):
                        entries.append(_Entry("file", f"{prefix}/{name}", full, st.st_size))
        elif path.is_file():
            entries.append(_Entry("file", top_name(path), str(path), path.stat().st_size))
    return entries


@dataclass
class _Entry:
    kind: str
    rel: str      # protocol path, "/"-separated
    source: str   # local absolute path
    size: int = 0


def send_files(transfer: Transfer, ip: str, port: int, paths: list[str], identity: dict) -> None:
    """Run a whole send operation; meant to be called on its own thread."""
    out = Outgoing(transfer, ip, port)

    def body() -> None:
        transfer.state = PREPARING
        transfer.message = Msg("Preparing files")
        entries = build_manifest(paths)
        files = [e for e in entries if e.kind == "file"]
        if not entries:
            raise OSError(Msg("Nothing to send - the selected files could not be found."))
        transfer.items = _top_level_names([{"path": e.rel} for e in entries])
        transfer.file_count = len(files)
        transfer.total_bytes = sum(e.size for e in files)
        transfer._check_cancel()

        accepted = out.offer({
            "app": APP_ID, "version": PROTOCOL_VERSION, "type": "offer",
            "sender": {"id": identity["id"], "name": identity["name"], "os": os_label()},
            "items": [{"kind": e.kind, "path": e.rel, "size": e.size} for e in entries],
        }, Msg("Waiting for {name} to accept", name=transfer.peer_name))
        if not accepted:
            return

        for index, entry in enumerate(entries):
            if entry.kind != "file":
                continue
            transfer._check_cancel()
            transfer.current_file = entry.rel
            try:
                f = open(entry.source, "rb")
                size = os.fstat(f.fileno()).st_size
            except OSError as exc:
                send_frame(out.sock, {"type": "skip", "index": index, "reason": describe_error(exc)})
                transfer.skipped += 1
                transfer.total_bytes -= entry.size
                continue
            with f:
                transfer.total_bytes += size - entry.size
                mtime = os.fstat(f.fileno()).st_mtime
                send_frame(out.sock, {"type": "file", "index": index, "size": size, "mtime": mtime})
                out.stream(f)
            transfer.files_done += 1

        send_frame(out.sock, {"type": "end"})
        transfer.current_file = ""
        transfer.message = Msg("Waiting for the other computer to finish saving")
        out.final_reply(IO_TIMEOUT)
        if transfer.skipped:
            transfer._finish(DONE, Msg("Delivered to {name} ({n} file could not be read and was skipped)",
                                       "Delivered to {name} ({n} files could not be read and were skipped)",
                                       n=transfer.skipped, name=transfer.peer_name))
        else:
            transfer._finish(DONE, Msg("Delivered to {name}", name=transfer.peer_name))

    out.run(body)


def _wait_for_frame(sock: socket.socket, transfer: Transfer, timeout: float) -> dict:
    """Wait for a reply while still reacting quickly to the Cancel button."""
    deadline = time.monotonic() + timeout
    while True:
        transfer._check_cancel()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        readable, _, _ = select.select([sock], [], [], min(0.25, remaining))
        if readable:
            return recv_frame(sock)


def _check_receiver(sock: socket.socket) -> None:
    """Between chunks, see whether the receiver asked us to stop."""
    readable, _, _ = select.select([sock], [], [], 0)
    if readable:
        msg = recv_frame(sock)
        if msg.get("type") == "cancel":
            raise remote_stop(msg, Msg("The other computer stopped the transfer."))


def _pending_cancel(sock: socket.socket) -> RemoteCancelled | None:
    """After a send error, check whether the receiver explained why."""
    try:
        readable, _, _ = select.select([sock], [], [], 0.5)
        if readable:
            sock.settimeout(1)
            msg = recv_frame(sock)
            if msg.get("type") == "cancel":
                return remote_stop(msg, Msg("The other computer stopped the transfer."))
    except (OSError, ProtocolError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# Glue used by the GUI (and tests)
# ---------------------------------------------------------------------------

class TransferManager:
    def __init__(self, identity: Callable[[], dict], save_dir: Callable[[], str],
                 present: Callable[[Offer], None]):
        self.identity = identity
        self.transfers: list[Transfer] = []
        self._lock = threading.Lock()
        self.receiver = Receiver(identity, save_dir, present, self.add)

    def add(self, transfer: Transfer) -> None:
        with self._lock:
            self.transfers.append(transfer)

    def snapshot(self) -> list[Transfer]:
        with self._lock:
            return list(self.transfers)

    def remove(self, transfer: Transfer) -> None:
        with self._lock:
            if transfer in self.transfers:
                self.transfers.remove(transfer)

    def send(self, peer_name: str, ip: str, port: int, paths: list[str]) -> Transfer:
        transfer = Transfer("send", peer_name, ip)
        transfer.items = [Path(p).name or p for p in paths]
        self.add(transfer)
        threading.Thread(target=send_files, args=(transfer, ip, port, list(paths), self.identity()),
                         name=f"send-{transfer.id}", daemon=True).start()
        return transfer

    def active(self) -> list[Transfer]:
        return [t for t in self.snapshot() if not t.is_finished]
