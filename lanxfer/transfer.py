"""Sending and receiving files over TCP. No GUI code here.

Transfers run on background threads and only update plain attributes on
Transfer objects; the GUI polls them. Incoming offers are handed to a
``present`` callback; the connection thread waits until offer.answer() is called.

File transfers survive a broken connection (see resume.py): both sides end up
INTERRUPTED instead of FAILED, and TransferManager.resume() sends the rest
later, including the rest of a file that was cut off halfway.
"""

import errno
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
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from . import os_label
from .i18n import Msg, tr
from .pathsafe import plan_destinations, split_relpath, top_level_paths
from .protocol import (
    ABORT_MARKER, APP_ID, CHUNK_SIZE, DIGEST_SIZE, END_OF_FILE, MAX_CHUNK, PROTOCOL_VERSION,
    ProtocolError, RemoteCancelled, pack_u32, recv_exact, recv_frame, recv_u32, remote_stop, send_frame,
)
from .resume import (
    COMPLETE, DISCARDED, OPEN, ReceiveRecord, SendRecord, SessionStore, new_session_id, part_path,
    remove_if_no_files, remove_partials, valid_session_id,
)

log = logging.getLogger(__name__)

DECISION_TIMEOUT = 120.0  # how long the receiver has to click Accept
IO_TIMEOUT = 60.0         # give up if the other side stalls this long
SLOW_DISK = 20_000_000    # bytes/s: the slowest we expect the other side to re-read a file that was cut off
RETRY_DELAYS = (3, 10, 30, 60)  # seconds between attempts to resume by itself

# Transfer states. INTERRUPTED: stopped by a broken connection or a closed app, and can be resumed.
WAITING, PREPARING, ACTIVE, DONE, FAILED, CANCELLED, DECLINED, INTERRUPTED = (
    "waiting", "preparing", "active", "done", "failed", "cancelled", "declined", "interrupted")
FINISHED_STATES = {DONE, FAILED, CANCELLED, DECLINED, INTERRUPTED}

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
    # Resuming (file transfers between apps that support it)
    session: str = ""         # random id both computers use for this transfer
    peer_id: str = ""         # the other computer's device id
    peer_port: int = 0
    resumable: bool = False   # an interruption ends as INTERRUPTED, not FAILED
    attempt: int = 0          # 0 at first, one more each time it's resumed
    pausing: bool = False     # stopping because this app is closing: keep it resumable
    retry_at: float = 0.0     # send: when to try resuming by itself (time.monotonic())
    retries: int = 0
    elapsed_before: float = 0.0
    entries: list[dict] | None = field(default=None, repr=False)  # send: the files exactly as offered
    _was_active: bool = field(default=False, repr=False)
    _running: bool = field(default=False, repr=False)  # send: a thread is still working on it

    @property
    def is_finished(self) -> bool:
        return self.state in FINISHED_STATES

    def cancel(self) -> None:
        self.cancel_event.set()

    def interrupt(self) -> None:
        """Stop because the app is closing. A resumable transfer continues next time."""
        self.pausing = True
        self.cancel_event.set()

    def elapsed(self) -> float:
        """Seconds spent transferring, over all attempts."""
        current = (self.finished or time.monotonic()) - self.started if self._was_active else 0.0
        return self.elapsed_before + current

    def _activate(self) -> None:
        self.state = ACTIVE
        self.message = ""
        self.started = time.monotonic()
        self._was_active = True

    def reopen(self) -> None:
        """Get an interrupted transfer ready for another attempt (the window keeps the same row)."""
        self.elapsed_before = self.elapsed()
        self._was_active = False
        self.state, self.message, self.finished = WAITING, "", None
        self.cancel_event = threading.Event()
        self.pausing = False
        self.done_bytes = self.files_done = self.skipped = 0
        self.current_file = ""
        self.attempt += 1

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


_NETWORK_ERRNOS = {getattr(errno, name) for name in (
    "ENETDOWN", "ENETUNREACH", "ENETRESET", "EHOSTDOWN", "EHOSTUNREACH", "ETIMEDOUT", "ECONNABORTED",
    "ECONNRESET", "EPIPE", "WSAENETDOWN", "WSAENETUNREACH", "WSAENETRESET", "WSAEHOSTDOWN",
    "WSAEHOSTUNREACH", "WSAETIMEDOUT", "WSAECONNABORTED", "WSAECONNRESET") if hasattr(errno, name)}


def connection_problem(exc: BaseException) -> bool:
    """The network went away (rather than a disk error or bad data): worth trying again later."""
    return isinstance(exc, (ConnectionError, TimeoutError)) or (
        isinstance(exc, OSError) and exc.errno in _NETWORK_ERRNOS)


def abort_politely(sock: socket.socket, reason: str, in_file_data: bool = False, failed: bool = False,
                   resumable: bool = False) -> None:
    """Tell the other side we are stopping, without making it see a reset."""
    try:
        sock.settimeout(3)
        if in_file_data:
            sock.sendall(pack_u32(ABORT_MARKER))
        frame = {"type": "cancel", "reason": reason, "failed": failed}
        if resumable:
            frame["resumable"] = True
        send_frame(sock, frame)
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

def send_file_data(sock: socket.socket, f, transfer: Transfer, digest=None) -> None:
    """Stream an open file (from where it is) as chunks, an end marker and its SHA-256.

    ``digest`` may already hold the start of the file, when only the rest is sent.
    """
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    digest = hashlib.sha256() if digest is None else digest
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


def recv_file_data(conn: socket.socket, f, transfer: Transfer, name: str, digest=None) -> str:
    """Receive what send_file_data() sent into ``f``. Returns the SHA-256 (hex)."""
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    digest = hashlib.sha256() if digest is None else digest
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


def hash_prefix(f, length: int, digest, transfer: Transfer) -> None:
    """Feed the first ``length`` bytes of an open file into ``digest`` (to check a file that was cut off)."""
    f.seek(0)
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    left = length
    while left:
        n = f.readinto(view[:min(left, CHUNK_SIZE)])
        if not n:
            break  # shorter than expected: the checksums won't match, so the file starts again
        digest.update(view[:n])
        left -= n
        transfer._check_cancel()


def what_arrived(items: list[dict], destinations: list[Path]) -> tuple[set[int], dict[int, int]]:
    """Which files of a transfer are already saved, and how much of the cut-off ones (from the disk)."""
    done, partial = set(), {}
    for index, (item, dest) in enumerate(zip(items, destinations)):
        if item["kind"] != "file":
            continue
        if dest.is_file():  # files only get their final name once they're complete and checked
            done.add(index)
            continue
        try:
            size = part_path(dest).stat().st_size
        except OSError:
            continue
        if size:
            partial[index] = size
    return done, partial


# ---------------------------------------------------------------------------
# Receiving
# ---------------------------------------------------------------------------

class Receiver:
    """Accepts incoming connections and saves the offered files."""

    def __init__(self, identity: Callable[[], dict], save_dir: Callable[[], str],
                 present: Callable[[Offer], None], on_new_transfer: Callable[[Transfer], None],
                 store: SessionStore | None = None,
                 find_transfer: Callable[[str, str], Transfer | None] | None = None):
        self.identity = identity
        self.save_dir = save_dir
        self.present = present  # shows the offer; someone must call offer.answer()
        self.on_new_transfer = on_new_transfer
        self.store = store if store is not None else SessionStore()
        self.find_transfer = find_transfer or (lambda direction, session: None)
        # Other request types (e.g. "update"): handler(conn, peer_ip, first_message)
        self.extra_handlers: dict[str, Callable[[socket.socket, str, dict], None]] = {
            "discard": self._sender_discarded}
        self.port: int | None = None
        self._server: socket.socket | None = None
        self._reserved: set[str] = set()
        self._reserve_lock = threading.Lock()
        self._live: dict[str, tuple[socket.socket, Transfer, threading.Event]] = {}  # session -> connection
        self._live_lock = threading.Lock()

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
        name = str(sender.get("name") or peer_ip)[:100]
        sender_id = str(sender.get("id") or "")[:100]
        if offer_msg.get("version") != PROTOCOL_VERSION:
            send_frame(conn, {"type": "reject", "reason": Msg("The two apps are different versions. Please update both.")})
            return
        try:
            items = _validate_items(offer_msg.get("items"))
        except ValueError:
            send_frame(conn, {"type": "reject", "reason": Msg("The other computer refused the file list (invalid names).")})
            return

        session = valid_session_id(offer_msg.get("session")) if sender_id else None
        record = self.store.get("receive", session) if session else None
        if record is not None:
            if record.sender_id != sender_id:
                session = None  # not the computer that started it: an ordinary new transfer
            elif record.state == DISCARDED:
                send_frame(conn, {"type": "reject", "reason": Msg("The other computer stopped this transfer for good.")})
                return
            elif record.state == COMPLETE:
                self._confirm_complete(conn, record)
                return
            elif record.items == items and Path(record.folder).is_dir():
                self._resume(conn, peer_ip, name, items, record)
                return
            else:  # its folder was deleted or moved: start again as a new transfer
                remove_partials(record.paths())
                self.store.delete("receive", session)
        self._receive_new(conn, peer_ip, name, sender, items, session)

    def _receive_new(self, conn: socket.socket, peer_ip: str, name: str, sender: dict, items: list[dict],
                     session: str | None) -> None:
        transfer = Transfer("receive", name, peer_ip, session=session or "",
                            peer_id=str(sender.get("id") or "")[:100])
        save_dir = Path(os.path.abspath(self.save_dir()))  # the saved session must not depend on the cwd
        transfer.items = _top_level_names(items)
        transfer.file_count = sum(1 for i in items if i["kind"] == "file")
        transfer.total_bytes = sum(i["size"] for i in items if i["kind"] == "file")
        transfer.save_dir = str(save_dir)
        free = _free_space(save_dir)
        self.on_new_transfer(transfer)

        offer = Offer(transfer, name, str(sender.get("os") or "?"), peer_ip, items, str(save_dir), free)
        reserved: set[str] = set()
        folder: Path | None = None
        try:
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
            except (OSError, ValueError) as exc:
                log.warning("Receive from %s failed: %s", peer_ip, exc)
                if folder is not None:
                    remove_if_no_files(folder)
                transfer._finish(FAILED, describe_error(exc))
                if not connection_problem(exc):
                    abort_politely(conn, Msg("The other computer could not save the files: {error}",
                                             error=describe_error(exc)), failed=True)
                return
            record = None
            if session:  # written before accepting, so even a crash leaves it resumable
                record = ReceiveRecord(session, transfer.peer_id, name, str(folder), items,
                                       [d.relative_to(folder).as_posix() for d in destinations])
                self.store.save(record)
                transfer.resumable = True
            self._run(conn, transfer, items, destinations, folder, record, {},
                      {"type": "accept", "resumable": record is not None})
        except Exception as exc:  # a bug: at least don't leave the row waiting forever
            log.exception("Receiving from %s failed", peer_ip)
            if not transfer.is_finished:
                transfer._finish(FAILED, describe_error(exc))
        finally:
            with self._reserve_lock:
                self._reserved -= reserved

    def _resume(self, conn: socket.socket, peer_ip: str, name: str, items: list[dict],
                record: ReceiveRecord) -> None:
        """The sender is back for a transfer we accepted before: continue without asking."""
        if not self._take_over(record.session):
            return  # the old connection didn't let go in time; the sender tries again shortly
        folder = Path(record.folder)
        destinations = record.paths()
        done, partial = what_arrived(items, destinations)
        transfer = self.find_transfer("receive", record.session)
        reuse = transfer is not None and transfer.is_finished
        if reuse:
            transfer.reopen()  # the same row in the window
            transfer.peer_name, transfer.peer_ip = name, peer_ip
        else:
            transfer = Transfer("receive", name, peer_ip)
        transfer.session, transfer.peer_id, transfer.resumable = record.session, record.sender_id, True
        transfer.items = _top_level_names(items)
        transfer.file_count = sum(1 for i in items if i["kind"] == "file")
        transfer.total_bytes = sum(i["size"] for i in items if i["kind"] == "file")
        transfer.save_dir = str(folder)
        transfer.files_done = len(done)
        transfer.done_bytes = sum(items[i]["size"] for i in done) + sum(partial.values())
        if not reuse:
            self.on_new_transfer(transfer)
        log.info("Resuming a transfer from %s: %d of %d files already here", name, len(done), transfer.file_count)
        self._run(conn, transfer, items, destinations, folder, record, partial, {
            "type": "accept", "resumable": True,
            "have": {"done": sorted(done), "partial": {str(i): n for i, n in partial.items()}},
        })

    def _run(self, conn: socket.socket, transfer: Transfer, items: list[dict], destinations: list[Path],
             folder: Path, record: ReceiveRecord | None, partial: dict[int, int], accept: dict) -> None:
        """Accept, receive the files, and sort out how it ended."""
        finished = self._go_live(record.session, conn, transfer) if record else None

        def stop_for_good(state: str, message: str) -> None:
            if record is not None:
                self.store.save(record.closed(DISCARDED))
            remove_partials(destinations)
            remove_if_no_files(folder)  # e.g. cancelled before the first file arrived
            transfer._finish(state, message)

        try:
            send_frame(conn, accept)
            transfer._activate()
            for item, dest in zip(items, destinations):
                if item["kind"] == "dir":
                    dest.mkdir(parents=True, exist_ok=True)
            self._receive_files(conn, transfer, items, destinations, partial)
            if record is not None:
                self.store.save(record.closed(COMPLETE))
            if transfer.skipped:
                done = Msg("Saved to {folder} ({n} file could not be read on the other computer)",
                           "Saved to {folder} ({n} files could not be read on the other computer)",
                           n=transfer.skipped, folder=str(folder))
            else:
                done = Msg("Saved to {folder}", folder=str(folder))
            transfer._finish(DONE, done)
            send_frame(conn, {"type": "done"})
        except Cancelled:
            if transfer.pausing and record is not None:
                abort_politely(conn, Msg("The other computer closed the app."), resumable=True)
                transfer._finish(INTERRUPTED, Msg("This app was closed during the transfer."))
            else:
                stop_for_good(CANCELLED, Msg("You cancelled the transfer."))
                abort_politely(conn, Msg("The other computer cancelled the transfer."))
        except RemoteCancelled as exc:
            if exc.resumable and record is not None:
                transfer._finish(INTERRUPTED, describe_error(exc))
            else:
                stop_for_good(FAILED if exc.failed else CANCELLED, describe_error(exc))
        except (OSError, ProtocolError) as exc:
            if transfer.state == DONE:
                return  # only our final "done" didn't get through; the sender will ask again
            log.warning("Receive from %s failed: %s", transfer.peer_ip, exc)
            if record is not None and connection_problem(exc):
                transfer._finish(INTERRUPTED, describe_error(exc))
            else:
                stop_for_good(FAILED, describe_error(exc))
                if not connection_problem(exc):
                    abort_politely(conn, Msg("The other computer could not save the files: {error}",
                                             error=describe_error(exc)), failed=True)
        except Exception as exc:  # a bug: end it for good, rather than have the sender retry forever
            log.exception("Receiving from %s failed", transfer.peer_ip)
            stop_for_good(FAILED, describe_error(exc))
            abort_politely(conn, Msg("The other computer could not save the files: {error}",
                                     error=describe_error(exc)), failed=True)
        finally:
            if finished is not None:
                self._leave(record.session, finished)

    def _receive_files(self, conn: socket.socket, transfer: Transfer, items: list[dict],
                       destinations: list[Path], partial: dict[int, int]) -> None:
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
                if index in partial:  # the sender can't read it any more: drop what we kept of it
                    transfer.done_bytes -= partial.pop(index)
                    remove_partials([destinations[index]])
                continue
            if kind != "file":
                raise ProtocolError(f"unexpected message {kind!r}")

            dest = destinations[index]
            transfer.current_file = items[index]["path"]
            announced = int(msg.get("size") or 0)
            transfer.total_bytes += announced - items[index]["size"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = part_path(dest)
            had = partial.pop(index, 0)  # bytes of it we kept from an earlier attempt
            offset = msg.get("offset", 0)
            if not isinstance(offset, int) or isinstance(offset, bool) or offset not in (0, had):
                raise ProtocolError("bad resume offset")
            digest = hashlib.sha256()
            if offset:
                offset, digest = self._agree_on_prefix(conn, transfer, part, index, offset)
            transfer.done_bytes -= had - offset  # thrown away if the file starts again
            with open(part, "r+b" if offset else "wb") as f:
                if offset:
                    f.seek(offset)
                    f.truncate()
                recv_file_data(conn, f, transfer, dest.name, digest)
            os.replace(part, dest)
            mtime = msg.get("mtime")
            if isinstance(mtime, (int, float)):
                try:
                    os.utime(dest, (time.time(), mtime))
                except (OSError, OverflowError, ValueError):
                    pass
            transfer.files_done += 1

    @staticmethod
    def _agree_on_prefix(conn: socket.socket, transfer: Transfer, part: Path, index: int, offset: int):
        """Check that the part of a file we kept is the same as the start of the sender's copy.

        Returns the offset to continue from (0: the file changed, start again) and the digest so far.
        """
        digest = hashlib.sha256()
        transfer.message = Msg("Checking the part that already arrived")
        with open(part, "rb") as f:
            hash_prefix(f, offset, digest, transfer)
        send_frame(conn, {"type": "prefix", "index": index, "sha256": digest.hexdigest()})
        conn.settimeout(IO_TIMEOUT + offset / SLOW_DISK)  # the sender reads its copy at the same time
        reply = recv_frame(conn)
        conn.settimeout(IO_TIMEOUT)
        transfer.message = ""
        if reply.get("type") == "cancel":
            raise remote_stop(reply, Msg("The sender cancelled the transfer."))
        if reply.get("type") != "continue" or reply.get("offset") not in (0, offset):
            raise ProtocolError(f"unexpected message {reply.get('type')!r}")
        if not reply["offset"]:
            log.info("%s changed since it was cut off; receiving it again from the start", part.name)
            return 0, hashlib.sha256()
        return offset, digest

    def _confirm_complete(self, conn: socket.socket, record: ReceiveRecord) -> None:
        """The sender missed our final "done" last time: tell it everything is already here."""
        try:
            send_frame(conn, {"type": "accept", "resumable": True,
                              "have": {"done": list(range(record.item_count)), "partial": {}}})
            conn.settimeout(IO_TIMEOUT)
            if recv_frame(conn).get("type") == "end":
                send_frame(conn, {"type": "done"})
        except (OSError, ProtocolError):
            pass

    # -- one connection per session ---------------------------------------

    def _go_live(self, session: str, conn: socket.socket, transfer: Transfer) -> threading.Event:
        finished = threading.Event()
        with self._live_lock:
            self._live[session] = (conn, transfer, finished)
        return finished

    def _leave(self, session: str, finished: threading.Event) -> None:
        with self._live_lock:
            if session in self._live and self._live[session][2] is finished:
                del self._live[session]
        finished.set()

    def _take_over(self, session: str) -> bool:
        """The sender came back while we still hold its old connection (the network broke without
        this side noticing yet). Close the old one and wait until it has stopped writing."""
        with self._live_lock:
            live = self._live.get(session)
        if live is None:
            return True
        conn, transfer, finished = live
        log.info("A transfer was resumed while its old connection was still open; closing that one")
        transfer.interrupt()
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        return finished.wait(15)

    # -- giving up on a session -------------------------------------------

    def discard(self, record: ReceiveRecord) -> None:
        """Forget an interrupted transfer: delete the cut-off file, keep the ones that arrived."""
        self.store.save(record.closed(DISCARDED))
        remove_partials(record.paths())
        remove_if_no_files(Path(record.folder))

    def _sender_discarded(self, conn: socket.socket, peer_ip: str, msg: dict) -> None:
        """The sender won't resume an interrupted transfer."""
        session = valid_session_id(msg.get("session"))
        sender = msg.get("sender") if isinstance(msg.get("sender"), dict) else {}
        record = self.store.get("receive", session) if session else None
        if record is None or record.state != OPEN or record.sender_id != str(sender.get("id") or ""):
            return
        with self._live_lock:
            if session in self._live:
                return  # it's running again; that connection decides how it ends
        self.discard(record)
        transfer = self.find_transfer("receive", session)
        if transfer is not None and transfer.state == INTERRUPTED:
            transfer._finish(CANCELLED, Msg("The sender stopped this transfer for good."))


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

    def __init__(self, transfer: Transfer, ip: str, port: int, resumable: bool = False):
        self.transfer = transfer
        self.ip = ip
        self.port = port
        self.sock: socket.socket | None = None
        self.in_file_data = False
        self.resumable = resumable  # a broken connection leaves the transfer INTERRUPTED
        self.connected = False

    def offer(self, message: dict, waiting_text: str) -> dict | None:
        """Connect and send the opening message. The "accept" reply, or None if the other side declined."""
        t = self.transfer
        t.message = Msg("Connecting")
        try:
            self.sock = socket.create_connection((self.ip, self.port), timeout=8)
        except OSError as exc:
            raise OSError(Msg("Could not connect to {name}. Make sure the app is open there "
                              "and that its firewall allows it.", name=t.peer_name)) from exc
        self.connected = True
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(IO_TIMEOUT)
        send_frame(self.sock, message)
        t.state = WAITING
        t.message = waiting_text
        reply = _wait_for_frame(self.sock, t, DECISION_TIMEOUT + 30)
        if reply.get("type") == "reject":
            t._finish(DECLINED, reply.get("reason") or Msg("The other computer declined."))
            return None
        if reply.get("type") != "accept":
            raise ProtocolError(f"unexpected reply {reply.get('type')!r}")
        t._activate()
        return reply

    def stream(self, f, digest=None) -> None:
        self.in_file_data = True
        send_file_data(self.sock, f, self.transfer, digest)
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
            if t.pausing and self.resumable:
                if self.sock:
                    abort_politely(self.sock, Msg("The other computer closed the app."), self.in_file_data,
                                   resumable=True)
                t._finish(INTERRUPTED, Msg("This app was closed during the transfer."))
            else:
                t._finish(CANCELLED, Msg("You cancelled the transfer."))
                if self.sock:
                    abort_politely(self.sock, Msg("The sender cancelled the transfer."), self.in_file_data)
        except RemoteCancelled as exc:
            self._stopped_by_remote(exc)
        except (OSError, ProtocolError) as exc:
            log.warning("Send to %s failed: %s", self.ip, exc)
            remote = _pending_cancel(self.sock) if self.sock else None
            if remote:
                self._stopped_by_remote(remote)
            elif self.resumable and (not self.connected or connection_problem(exc)):
                t._finish(INTERRUPTED, describe_error(exc))
            else:
                if self.connected and not connection_problem(exc) and not isinstance(exc, ProtocolError):
                    abort_politely(self.sock, Msg("The other computer could not read the files: {error}",
                                                  error=describe_error(exc)), self.in_file_data, failed=True)
                t._finish(FAILED, describe_error(exc))
        except Exception as exc:  # a bug: at least don't leave the row waiting forever
            log.exception("Sending to %s failed", self.ip)
            t._finish(FAILED, describe_error(exc))
        finally:
            if self.sock:
                self.sock.close()

    def _stopped_by_remote(self, exc: RemoteCancelled) -> None:
        if exc.resumable and self.resumable:
            self.transfer._finish(INTERRUPTED, describe_error(exc))
        else:
            finish_from_remote(self.transfer, exc)


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


def send_files(transfer: Transfer, ip: str, port: int, paths: list[str], identity: dict,
               store: SessionStore | None = None) -> Outgoing:
    """Run a whole send operation; meant to be called on its own thread.

    If ``transfer.entries`` is set, this resumes an interrupted transfer and only
    sends what the receiver doesn't have yet.
    """
    resuming = transfer.entries is not None
    out = Outgoing(transfer, ip, port, resumable=resuming)

    def body() -> None:
        if resuming:
            entries = [_Entry(**e) for e in transfer.entries]
        else:
            transfer.state = PREPARING
            transfer.message = Msg("Preparing files")
            entries = build_manifest(paths)
            if not entries:
                raise OSError(Msg("Nothing to send - the selected files could not be found."))
            transfer.session = new_session_id()
        files = [e for e in entries if e.kind == "file"]
        transfer.items = _top_level_names([{"path": e.rel} for e in entries])
        transfer.file_count = len(files)
        transfer.total_bytes = sum(e.size for e in files)
        transfer._check_cancel()

        reply = out.offer({
            "app": APP_ID, "version": PROTOCOL_VERSION, "type": "offer", "session": transfer.session,
            "sender": {"id": identity["id"], "name": identity["name"], "os": os_label()},
            "items": [{"kind": e.kind, "path": e.rel, "size": e.size} for e in entries],
        }, Msg("Resuming") if resuming else Msg("Waiting for {name} to accept", name=transfer.peer_name))
        if reply is None:
            return

        done, partial = set(), {}
        out.resumable = transfer.resumable = reply.get("resumable") is True  # False: an app from before 1.4
        if transfer.resumable and resuming:
            done, partial = _parse_have(reply.get("have"), entries)
        elif transfer.resumable:
            transfer.entries = [asdict(e) for e in entries]
            if store is not None:
                store.save(SendRecord(transfer.session, transfer.peer_id, transfer.peer_name, ip, port,
                                      transfer.entries))
        transfer.retries = 0
        transfer.files_done = len(done)
        transfer.done_bytes = sum(entries[i].size for i in done) + sum(partial.values())

        for index, entry in enumerate(entries):
            if entry.kind != "file" or index in done:
                continue
            transfer._check_cancel()
            transfer.current_file = entry.rel
            had = partial.get(index, 0)  # bytes of it the receiver kept from an earlier attempt
            try:
                f = open(entry.source, "rb")
                size = os.fstat(f.fileno()).st_size
            except OSError as exc:
                send_frame(out.sock, {"type": "skip", "index": index, "reason": describe_error(exc)})
                transfer.skipped += 1
                transfer.total_bytes -= entry.size
                transfer.done_bytes -= had
                continue
            with f:
                transfer.total_bytes += size - entry.size
                mtime = os.fstat(f.fileno()).st_mtime
                offset = had if had <= size else 0
                header = {"type": "file", "index": index, "size": size, "mtime": mtime}
                if offset:
                    header["offset"] = offset
                send_frame(out.sock, header)
                digest = hashlib.sha256()
                if offset:
                    offset, digest = _agree_on_prefix(out.sock, transfer, f, offset)
                transfer.done_bytes -= had - offset
                f.seek(offset)
                out.stream(f, digest)
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
    return out


def _parse_have(have, entries: list[_Entry]) -> tuple[set[int], dict[int, int]]:
    """What the receiver says it already has, ignoring anything that doesn't fit our file list."""
    if not isinstance(have, dict):
        return set(), {}
    files = {i for i, e in enumerate(entries) if e.kind == "file"}
    raw_done = have.get("done") if isinstance(have.get("done"), list) else []
    done = {i for i in raw_done if isinstance(i, int) and i in files}
    partial = {}
    raw_partial = have.get("partial") if isinstance(have.get("partial"), dict) else {}
    for key, value in raw_partial.items():
        if (isinstance(key, str) and key.isdigit() and int(key) in files and int(key) not in done
                and isinstance(value, int) and not isinstance(value, bool) and value > 0):
            partial[int(key)] = value
    return done, partial


def _agree_on_prefix(sock: socket.socket, transfer: Transfer, f, offset: int):
    """Both computers read the part that already arrived; continue only if the two copies match.

    Returns the offset to continue from (0: the file changed since, send all of it) and the digest so far.
    """
    digest = hashlib.sha256()
    transfer.message = Msg("Checking the part that was already sent")
    hash_prefix(f, offset, digest, transfer)
    reply = _wait_for_frame(sock, transfer, IO_TIMEOUT + offset / SLOW_DISK)
    if reply.get("type") == "cancel":
        raise remote_stop(reply, Msg("The other computer stopped the transfer."))
    if reply.get("type") != "prefix":
        raise ProtocolError(f"unexpected reply {reply.get('type')!r}")
    if reply.get("sha256") != digest.hexdigest():
        log.info("A file changed since it was cut off; sending all of it again")
        offset, digest = 0, hashlib.sha256()
    send_frame(sock, {"type": "continue", "offset": offset})
    transfer.message = ""
    return offset, digest


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
                 present: Callable[[Offer], None], store_dir: Path | None = None):
        """``store_dir``: where interrupted transfers are remembered (None: only while running)."""
        self.identity = identity
        self.transfers: list[Transfer] = []
        self._lock = threading.Lock()
        self.store = SessionStore(store_dir)
        self.receiver = Receiver(identity, save_dir, present, self.add, self.store, self.find)
        self._restore()

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

    def find(self, direction: str, session: str) -> Transfer | None:
        with self._lock:
            return next((t for t in self.transfers if t.session == session and t.direction == direction
                         and t.kind == "files"), None)

    def active(self) -> list[Transfer]:
        return [t for t in self.snapshot() if not t.is_finished]

    # -- sending ----------------------------------------------------------

    def send(self, peer_name: str, ip: str, port: int, paths: list[str], peer_id: str = "") -> Transfer:
        transfer = Transfer("send", peer_name, ip, peer_id=peer_id, peer_port=port)
        transfer.items = [Path(p).name or p for p in paths]
        self.add(transfer)
        self._start_send(transfer, ip, port, list(paths))
        return transfer

    def resume(self, transfer: Transfer, ip: str | None = None, port: int | None = None) -> bool:
        """Send the rest of an interrupted transfer (to this address, else the last one known)."""
        if (transfer.direction != "send" or transfer.state != INTERRUPTED or transfer.entries is None
                or transfer._running):
            return False
        transfer.peer_ip, transfer.peer_port = ip or transfer.peer_ip, port or transfer.peer_port
        transfer.reopen()
        self._start_send(transfer, transfer.peer_ip, transfer.peer_port, [])
        return True

    def resume_waiting(self, online: dict[str, tuple[str, int]]) -> None:
        """Resume interrupted sends to computers that are online again ({device id: (ip, port)})."""
        now = time.monotonic()
        for t in self.snapshot():
            if (t.direction == "send" and t.state == INTERRUPTED and t.entries is not None
                    and t.peer_id in online and now >= t.retry_at):
                self.resume(t, *online[t.peer_id])

    def _start_send(self, transfer: Transfer, ip: str, port: int, paths: list[str]) -> None:
        identity = self.identity()
        transfer._running = True

        def run() -> None:
            try:
                out = send_files(transfer, ip, port, paths, identity, self.store)
                self._after_send(transfer, out, identity)
            finally:
                transfer._running = False

        threading.Thread(target=run, name=f"send-{transfer.id}", daemon=True).start()

    def _after_send(self, transfer: Transfer, out: Outgoing, identity: dict) -> None:
        if not transfer.session:
            return
        if transfer.state == INTERRUPTED:
            self._save_progress(transfer)
            transfer.retry_at = time.monotonic() + RETRY_DELAYS[min(transfer.retries, len(RETRY_DELAYS) - 1)]
            transfer.retries += 1
            return
        self.store.delete("send", transfer.session)
        transfer.entries = None
        if transfer.state == CANCELLED and out.resumable and not out.connected:
            # Cancelled while reconnecting: the receiver still waits for the rest.
            self._tell_discarded(transfer, transfer.peer_ip, transfer.peer_port, identity)

    def _save_progress(self, transfer: Transfer) -> None:
        record = self.store.get("send", transfer.session)
        if record is not None:
            record.files_done, record.done_bytes = transfer.files_done, transfer.done_bytes
            record.peer_name, record.peer_ip, record.peer_port = (transfer.peer_name, transfer.peer_ip,
                                                                  transfer.peer_port)
            self.store.save(record)

    @staticmethod
    def _tell_discarded(transfer: Transfer, ip: str, port: int, identity: dict) -> None:
        """Let the receiver delete its half-received file (best effort, in the background)."""
        message = {"app": APP_ID, "type": "discard", "session": transfer.session, "sender": {"id": identity["id"]}}

        def work() -> None:
            try:
                with socket.create_connection((ip, port), timeout=5) as sock:
                    send_frame(sock, message)
            except OSError:
                pass

        threading.Thread(target=work, name="discard", daemon=True).start()

    # -- interrupted transfers --------------------------------------------

    def interrupt(self, transfers: list[Transfer]) -> None:
        """Stop these because the app is closing; file transfers continue next time."""
        for t in transfers:
            t.interrupt()
            if t.direction == "send" and t.resumable:
                self._save_progress(t)

    def discard(self, transfer: Transfer, ip: str | None = None, port: int | None = None) -> None:
        """Give up on an interrupted transfer. The files that arrived stay where they are."""
        if transfer.state != INTERRUPTED:
            return
        if transfer.direction == "send":
            self.store.delete("send", transfer.session)
            if transfer.entries is not None:
                self._tell_discarded(transfer, ip or transfer.peer_ip, port or transfer.peer_port, self.identity())
            transfer.entries = None
        else:
            record = self.store.get("receive", transfer.session)
            if record is not None and record.state == OPEN:
                self.receiver.discard(record)
        transfer._finish(CANCELLED, Msg("You cancelled the transfer."))
        self.remove(transfer)

    def _restore(self) -> None:
        """Show the transfers that were interrupted the last time the app ran."""
        for record in self.store.all():
            try:
                if isinstance(record, SendRecord):
                    entries = [_Entry(**e) for e in record.entries]
                    t = Transfer("send", record.peer_name, record.peer_ip, peer_id=record.peer_id,
                                 peer_port=record.peer_port, entries=[asdict(e) for e in entries])
                    items = [{"kind": e.kind, "path": e.rel, "size": e.size} for e in entries]
                    t.files_done, t.done_bytes = record.files_done, record.done_bytes
                elif record.state == OPEN:
                    t = Transfer("receive", record.sender_name, "", peer_id=record.sender_id,
                                 save_dir=record.folder)
                    items = record.items
                    done, partial = what_arrived(items, record.paths())
                    t.files_done = len(done)
                    t.done_bytes = sum(items[i]["size"] for i in done) + sum(partial.values())
                else:
                    continue
                t.items = _top_level_names(items)
                t.file_count = sum(1 for i in items if i["kind"] == "file")
                t.total_bytes = sum(i["size"] for i in items if i["kind"] == "file")
            except (KeyError, TypeError, ValueError, AttributeError):
                log.warning("Forgetting a saved transfer that can't be read")
                self.store.delete(record.kind, record.session)
                continue
            t.session, t.resumable = record.session, True
            t._finish(INTERRUPTED, Msg("The transfer was interrupted."))
            self.add(t)
