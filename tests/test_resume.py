"""Tests for continuing transfers after the connection breaks. Run: python -m unittest discover tests

The connection is broken for real: the sender talks to the receiver through a
small relay that drops both sockets (or only the sender's) after a set number
of bytes, like Wi-Fi going away in the middle of a file.
"""

import json
import os
import select
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer import transfer as tx  # noqa: E402
from lanxfer.protocol import APP_ID, recv_frame, send_frame  # noqa: E402
from lanxfer.resume import COMPLETE, DISCARDED  # noqa: E402

MB = 1024 * 1024


def wait_until(predicate, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def tree(root: Path) -> dict[str, bytes | None]:
    return {p.relative_to(root).as_posix(): (p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def reset(sock: socket.socket) -> None:
    """Close with a reset, as when the network goes away (no polite goodbye)."""
    try:
        linger = struct.pack("hh" if sys.platform.startswith("win") else "ii", 1, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
    except OSError:
        pass
    try:
        sock.shutdown(socket.SHUT_RDWR)  # also wakes the relay thread reading it, so it really closes
    except OSError:
        pass
    sock.close()


class Relay:
    """A TCP relay to the receiver that can break the connection after ``cut_after`` bytes.

    keep_receiver_side=True drops only the sender's socket, so the receiver still
    thinks it's connected (what happens when a laptop sleeps or Wi-Fi drops out).
    ``rate`` slows it down (bytes per second) so tests can act in the middle of a file.
    Each connection is relayed by one thread, which alone uses and closes its sockets.
    """

    def __init__(self, target_port: int, cut_after: int | None = None, keep_receiver_side: bool = False,
                 rate: float | None = None):
        self.target_port = target_port
        self.cut_after = cut_after
        self.keep_receiver_side = keep_receiver_side
        self.rate = rate
        self.forwarded = 0  # bytes from the sender to the receiver
        self.held: list[socket.socket] = []
        self.closed = False
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def close(self) -> None:
        self.closed = True
        self.server.close()
        for sock in self.held:
            sock.close()

    def _accept(self) -> None:
        while True:
            try:
                client, _ = self.server.accept()
            except OSError:
                return
            threading.Thread(target=self._relay, args=(client,), daemon=True).start()

    def _relay(self, client: socket.socket) -> None:
        upstream = socket.create_connection(("127.0.0.1", self.target_port))
        open_ends = [client, upstream]
        keep = False
        try:
            while open_ends and not self.closed:
                readable, _, _ = select.select(open_ends, [], [], 0.2)
                for src in readable:
                    dst, forward = (upstream, True) if src is client else (client, False)
                    limit = 64 * 1024
                    if forward and self.cut_after is not None:
                        limit = min(limit, self.cut_after - self.forwarded)
                        if limit <= 0:  # break the connection, like the network going away
                            reset(client)
                            if self.keep_receiver_side:
                                keep = True
                                self.held.append(upstream)  # never closed: the receiver hears nothing
                            else:
                                reset(upstream)
                            return
                    data = src.recv(limit)
                    if not data:
                        open_ends.remove(src)
                        try:
                            dst.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    dst.sendall(data)
                    if forward:
                        self.forwarded += len(data)
                        if self.rate:
                            time.sleep(len(data) / self.rate)
        except OSError:
            pass
        finally:
            client.close()
            if not keep:
                upstream.close()


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / "src"
        self.dst = self.root / "dst"
        self.src.mkdir()
        self.offers = []
        self.relays: list[Relay] = []
        self.managers: list[tx.TransferManager] = []
        self.start_managers()

    def start_managers(self, stores: bool = False) -> None:
        def present(offer):
            self.offers.append(offer)
            offer.answer(True)

        self.receiver_ident = {"id": "receiver-id", "name": "Receiver", "os": "Test", "port": 0}
        self.sender_ident = {"id": "sender-id", "name": "Sender", "os": "Test", "port": 0}
        self.receiver = tx.TransferManager(lambda: self.receiver_ident, lambda: str(self.dst), present,
                                           store_dir=self.root / "recv-store" if stores else None)
        self.port = self.receiver.receiver.start(47100)
        self.sender = tx.TransferManager(lambda: self.sender_ident, lambda: str(self.root / "unused"),
                                         lambda o: o.answer(False),
                                         store_dir=self.root / "send-store" if stores else None)
        self.managers += [self.receiver, self.sender]

    def tearDown(self):
        for relay in self.relays:
            relay.close()
        for manager in self.managers:
            manager.receiver.stop()
        time.sleep(0.05)
        self.tmp.cleanup()

    # -- helpers ----------------------------------------------------------

    def relay(self, **kwargs) -> Relay:
        relay = Relay(self.port, **kwargs)
        self.relays.append(relay)
        return relay

    def make_files(self) -> Path:
        folder = self.src / "Holiday"
        (folder / "videos").mkdir(parents=True)
        (folder / "a.jpg").write_bytes(os.urandom(2 * MB))
        (folder / "videos" / "big.mp4").write_bytes(os.urandom(8 * MB + 17))
        (folder / "z.txt").write_bytes(os.urandom(1 * MB))
        return folder

    def send(self, port: int, *paths) -> tx.Transfer:
        return self.sender.send("Receiver", "127.0.0.1", port, [str(p) for p in paths], peer_id="receiver-id")

    def finish(self, t: tx.Transfer) -> None:
        self.assertTrue(wait_until(lambda: t.is_finished and not t._running), f"did not finish: {t}")

    def incoming(self) -> tx.Transfer:
        self.assertTrue(wait_until(lambda: self.receiver.snapshot()))
        r = self.receiver.snapshot()[0]
        self.assertTrue(wait_until(lambda: r.is_finished), f"receiver did not finish: {r}")
        return r

    def interrupted_send(self, **relay_args) -> tuple[tx.Transfer, tx.Transfer, Path]:
        """Send the test files and break the connection partway through big.mp4."""
        folder = self.make_files()
        relay = self.relay(cut_after=5 * MB, **relay_args)
        t = self.send(relay.port, folder)
        self.finish(t)
        self.assertEqual(t.state, tx.INTERRUPTED, t.message)
        r = self.receiver.snapshot()[0]
        if not relay_args.get("keep_receiver_side"):
            self.assertTrue(wait_until(lambda: r.is_finished))
            self.assertEqual(r.state, tx.INTERRUPTED, r.message)
        return t, r, folder

    def inbox(self) -> Path:
        [inbox] = [p for p in self.dst.iterdir() if p.is_dir()]
        return inbox

    def assert_complete(self, t: tx.Transfer, r: tx.Transfer, folder: Path) -> None:
        self.finish(t)
        self.assertEqual(t.state, tx.DONE, t.message)
        self.assertTrue(wait_until(lambda: r.state == tx.DONE), r.message)
        inbox = self.inbox()  # still exactly one numbered folder
        self.assertEqual(tree(inbox / folder.name), tree(folder))
        self.assertFalse(list(self.dst.rglob("*.part")))
        self.assertEqual(r.files_done, 3)
        self.assertEqual(r.done_bytes, r.total_bytes)
        self.assertEqual(t.done_bytes, t.total_bytes)

    # -- tests ------------------------------------------------------------

    def test_continues_where_the_connection_broke(self):
        t, r, folder = self.interrupted_send()
        inbox = self.inbox()
        self.assertEqual((inbox / "Holiday" / "a.jpg").read_bytes(), (folder / "a.jpg").read_bytes())
        part = inbox / "Holiday" / "videos" / "big.mp4.part"
        self.assertTrue(part.exists(), "the cut-off file is kept")
        kept = part.stat().st_size
        self.assertGreater(kept, 0)
        self.assertTrue((inbox / "Holiday" / "z.txt").exists())  # sent before videos/
        self.assertEqual(r.files_done, 2)

        second = self.relay()  # count what the second attempt sends
        self.assertTrue(self.sender.resume(t, "127.0.0.1", second.port))
        self.assert_complete(t, r, folder)
        self.assertEqual(len(self.offers), 1, "a resumed transfer isn't asked about again")
        self.assertEqual(len(self.receiver.snapshot()), 1, "it continues in the same row")
        self.assertEqual((t.attempt, r.attempt), (1, 1))
        total = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
        self.assertLess(second.forwarded, total - 3 * MB - kept + 64 * 1024, "only the rest was sent")

    def test_file_that_changed_meanwhile_is_sent_again_whole(self):
        t, r, folder = self.interrupted_send()
        big = folder / "videos" / "big.mp4"
        data = bytearray(big.read_bytes())
        data[:10] = b"0123456789"  # same size, different start
        big.write_bytes(bytes(data))
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.assert_complete(t, r, folder)

    def test_file_that_got_shorter_is_sent_again_whole(self):
        t, r, folder = self.interrupted_send()
        big = folder / "videos" / "big.mp4"
        big.write_bytes(big.read_bytes()[:1000])
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.assert_complete(t, r, folder)

    def test_cut_off_file_that_can_no_longer_be_read(self):
        t, r, folder = self.interrupted_send()
        (folder / "videos" / "big.mp4").unlink()
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.finish(t)
        self.assertEqual(t.state, tx.DONE, t.message)
        self.assertTrue(wait_until(lambda: r.state == tx.DONE))
        self.assertEqual((t.skipped, r.skipped), (1, 1))
        self.assertFalse(list(self.dst.rglob("*.part")), "no half file is left behind")
        self.assertEqual(r.done_bytes, r.total_bytes)

    def test_receiver_that_still_thinks_it_is_connected(self):
        # Only the sender notices the break; the receiver's old connection is still open.
        t, r, folder = self.interrupted_send(keep_receiver_side=True)
        self.assertEqual(r.state, tx.ACTIVE)
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.assert_complete(t, r, folder)
        self.assertEqual(len(self.receiver.snapshot()), 1)

    def test_sender_app_closed(self):
        folder = self.make_files()
        t = self.send(self.relay(rate=20 * MB).port, folder)
        self.assertTrue(wait_until(lambda: t.done_bytes > 3 * MB))
        self.sender.interrupt([t])
        self.finish(t)
        r = self.incoming()
        self.assertEqual(t.state, tx.INTERRUPTED, t.message)
        self.assertEqual(r.state, tx.INTERRUPTED, r.message)
        self.assertEqual(r.message, "The other computer closed the app.")
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.assert_complete(t, r, folder)

    def test_receiver_app_closed(self):
        folder = self.make_files()
        t = self.send(self.relay(rate=20 * MB).port, folder)
        self.assertTrue(wait_until(lambda: self.receiver.snapshot() and self.receiver.snapshot()[0].done_bytes > 3 * MB))
        r = self.receiver.snapshot()[0]
        self.receiver.interrupt([r])
        self.finish(t)
        self.assertTrue(wait_until(lambda: r.is_finished))
        self.assertEqual(r.state, tx.INTERRUPTED, r.message)
        self.assertEqual(t.state, tx.INTERRUPTED, t.message)
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.assert_complete(t, r, folder)

    def test_resumes_by_itself_when_the_computer_is_back(self):
        t, r, folder = self.interrupted_send()
        self.assertGreater(t.retry_at, time.monotonic(), "waits a moment before trying again")
        self.sender.resume_waiting({})  # the receiver isn't online
        self.sender.resume_waiting({"someone-else": ("127.0.0.1", self.port)})
        self.assertEqual(t.state, tx.INTERRUPTED)
        t.retry_at = 0
        self.sender.resume_waiting({"receiver-id": ("127.0.0.1", self.port)})
        self.assert_complete(t, r, folder)

    def test_retries_wait_longer_each_time(self):
        t, r, folder = self.interrupted_send()
        self.receiver.receiver.stop()  # the receiver's app is gone
        delays = []
        for _ in range(3):
            t.retry_at = 0
            self.sender.resume_waiting({"receiver-id": ("127.0.0.1", self.port)})
            self.finish(t)
            self.assertEqual(t.state, tx.INTERRUPTED, t.message)
            delays.append(t.retry_at - t.finished)  # (Windows takes ~2 s to refuse a connection)
        self.assertEqual([round(d) for d in delays], [10, 30, 60])

    def test_cancel_stops_it_for_good(self):
        t, r, folder = self.interrupted_send()
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.relay(rate=10 * MB).port))
        self.assertTrue(wait_until(lambda: t.state == tx.ACTIVE and r.state == tx.ACTIVE))
        t.cancel()
        self.finish(t)
        self.assertTrue(wait_until(lambda: r.is_finished))
        self.assertEqual((t.state, r.state), (tx.CANCELLED, tx.CANCELLED))
        self.assertFalse(list(self.dst.rglob("*.part")), "the cut-off file is deleted")
        self.assertTrue((self.inbox() / "Holiday" / "a.jpg").exists(), "the files that arrived stay")
        self.assertFalse(self.sender.resume(t, "127.0.0.1", self.port))
        self.assertEqual(self.receiver.store.get("receive", t.session).state, DISCARDED)

    def test_receiver_discards(self):
        t, r, folder = self.interrupted_send()
        self.receiver.discard(r)
        self.assertNotIn(r, self.receiver.snapshot())
        self.assertFalse(list(self.dst.rglob("*.part")))
        self.assertTrue((self.inbox() / "Holiday" / "a.jpg").exists())
        # The sender doesn't know yet; when it comes back it's told no, instead of the user being asked again.
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.finish(t)
        self.assertEqual(t.state, tx.DECLINED)
        self.assertEqual(t.message, "The other computer stopped this transfer for good.")
        self.assertEqual(len(self.offers), 1)
        self.assertIsNone(self.sender.store.get("send", t.session))

    def test_sender_discards_and_tells_the_receiver(self):
        t, r, folder = self.interrupted_send()
        self.sender.discard(t, "127.0.0.1", self.port)
        self.assertNotIn(t, self.sender.snapshot())
        self.assertTrue(wait_until(lambda: r.state == tx.CANCELLED), r.state)
        self.assertEqual(r.message, "The sender stopped this transfer for good.")
        self.assertFalse(list(self.dst.rglob("*.part")))
        self.assertTrue((self.inbox() / "Holiday" / "a.jpg").exists())

    def test_discard_from_another_computer_is_ignored(self):
        t, r, folder = self.interrupted_send()
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            send_frame(sock, {"app": APP_ID, "type": "discard", "session": t.session, "sender": {"id": "intruder"}})
        time.sleep(0.3)
        self.assertEqual(r.state, tx.INTERRUPTED)
        self.assertTrue(list(self.dst.rglob("*.part")))

    def test_resume_from_another_computer_is_a_new_transfer(self):
        t, r, folder = self.interrupted_send()
        self.sender_ident["id"] = "someone-else"  # same session id, different computer
        self.assertTrue(self.sender.resume(t, "127.0.0.1", self.port))
        self.finish(t)
        self.assertEqual(len(self.offers), 2, "asked like any new transfer")
        self.assertEqual(len([p for p in self.dst.iterdir() if p.is_dir()]), 2, "into a new folder")

    def test_continues_after_both_apps_restart(self):
        for manager in self.managers:
            manager.receiver.stop()
        self.managers.clear()
        self.start_managers(stores=True)
        t, r, folder = self.interrupted_send()

        # Quit both apps, then open them again with the same settings folders.
        for manager in self.managers:
            manager.receiver.stop()
        self.managers.clear()
        self.start_managers(stores=True)
        [t2] = self.sender.snapshot()
        [r2] = self.receiver.snapshot()
        self.assertEqual((t2.state, r2.state), (tx.INTERRUPTED, tx.INTERRUPTED))
        self.assertEqual((t2.session, r2.session), (t.session, t.session))
        self.assertEqual((t2.peer_id, t2.items, t2.file_count), ("receiver-id", ["Holiday"], 3))
        self.assertEqual((r2.peer_name, r2.items, r2.save_dir), ("Sender", ["Holiday"], str(self.inbox())))
        self.assertEqual(r2.files_done, 2)
        self.assertGreater(r2.done_bytes, 3 * MB)

        t2.retry_at = 0
        self.sender.resume_waiting({"receiver-id": ("127.0.0.1", self.port)})  # right away after a restart
        self.assert_complete(t2, r2, folder)
        self.assertEqual(len(self.offers), 1)
        self.assertEqual(list((self.root / "send-store").iterdir()), [])
        [note] = (self.root / "recv-store").iterdir()
        self.assertEqual(json.loads(note.read_text())["state"], COMPLETE)

    def test_sender_that_missed_the_final_reply(self):
        # The receiver saved everything, but its "done" never reached the sender.
        (self.src / "a.txt").write_text("a")
        t = self.send(self.port, self.src / "a.txt")
        self.finish(t)
        self.assertEqual(t.state, tx.DONE)
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            send_frame(sock, {"app": APP_ID, "version": 1, "type": "offer", "session": t.session,
                              "sender": {"id": "sender-id", "name": "Sender", "os": "Test"},
                              "items": [{"kind": "file", "path": "a.txt", "size": 1}]})
            reply = recv_frame(sock)
            self.assertEqual(reply["have"]["done"], [0])
            send_frame(sock, {"type": "end"})
            self.assertEqual(recv_frame(sock)["type"], "done")
        self.assertEqual(len(self.offers), 1)

    def test_relative_download_folder(self):
        (self.src / "a.txt").write_text("a")
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            manager = tx.TransferManager(lambda: self.receiver_ident, lambda: "inbox", lambda o: o.answer(True))
            self.managers.append(manager)
            t = self.send(manager.receiver.start(47200), self.src / "a.txt")
            self.finish(t)
        finally:
            os.chdir(cwd)
        self.assertEqual(t.state, tx.DONE, t.message)
        [record] = manager.store.all()
        self.assertTrue(Path(record.folder).is_absolute())
        self.assertTrue(Path(record.folder).resolve().is_relative_to((self.root / "inbox").resolve()))  # macOS: /private

    def test_old_sender_without_sessions(self):
        # An app from before resuming: works as before, and nothing is kept after a break.
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            send_frame(sock, {"app": APP_ID, "version": 1, "type": "offer",
                              "sender": {"id": "old-app", "name": "Old", "os": "Test"},
                              "items": [{"kind": "file", "path": "f.bin", "size": 4 * MB}]})
            reply = recv_frame(sock)
            self.assertEqual(reply, {"type": "accept", "resumable": False})
            send_frame(sock, {"type": "file", "index": 0, "size": 4 * MB, "mtime": 0})
            sock.sendall(struct.pack("!I", MB) + os.urandom(MB))
            r = self.receiver.snapshot()[0]
            self.assertTrue(wait_until(lambda: r.done_bytes == MB))
            reset(sock)
        r = self.incoming()
        self.assertEqual(r.state, tx.FAILED)
        self.assertFalse(list(self.dst.rglob("*")), "the partial file and empty folder are removed")
        self.assertEqual(self.receiver.store.all(), [])

    def test_old_receiver_without_sessions(self):
        # A receiver from before resuming accepts without "resumable": a break is a plain failure.
        server = socket.create_server(("127.0.0.1", 0))
        port = server.getsockname()[1]

        def old_app():
            conn, _ = server.accept()
            recv_frame(conn)
            send_frame(conn, {"type": "accept"})
            recv_frame(conn)
            conn.recv(65536)
            reset(conn)

        threading.Thread(target=old_app, daemon=True).start()
        (self.src / "f.bin").write_bytes(os.urandom(4 * MB))
        t = self.send(port, self.src / "f.bin")
        self.finish(t)
        server.close()
        self.assertEqual(t.state, tx.FAILED)
        self.assertFalse(t.resumable)
        self.assertFalse(self.sender.resume(t))
        self.assertEqual(self.sender.store.all(), [])


class StoreTests(unittest.TestCase):
    def test_old_records_are_forgotten_and_their_partial_files_deleted(self):
        from lanxfer.resume import KEEP_FOR, ReceiveRecord, SendRecord, SessionStore, new_session_id
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "0001 x 2 files"
            folder.mkdir()
            (folder / "done.txt").write_text("kept")
            (folder / "cut.bin.part").write_bytes(b"x" * 10)
            store = SessionStore(root / "store")
            old = time.time() - KEEP_FOR - 60
            store.save(ReceiveRecord(new_session_id(), "s", "S", str(folder),
                                     [{"kind": "file", "path": "done.txt", "size": 4},
                                      {"kind": "file", "path": "cut.bin", "size": 20}],
                                     ["done.txt", "cut.bin"], created=old))
            store.save(SendRecord(new_session_id(), "p", "P", "1.2.3.4", 1, [], created=old))
            fresh = SendRecord(new_session_id(), "p", "P", "1.2.3.4", 1, [])
            store.save(fresh)
            (root / "store" / "receive-nonsense.json").write_text("{")
            reloaded = SessionStore(root / "store")
            self.assertEqual([r.session for r in reloaded.all()], [fresh.session])
            self.assertFalse((folder / "cut.bin.part").exists())
            self.assertTrue((folder / "done.txt").exists())
            self.assertEqual(sorted(p.name for p in (root / "store").iterdir()), [f"send-{fresh.session}.json"])

    def test_saved_places_must_stay_inside_their_folder(self):
        from lanxfer.resume import ReceiveRecord, SessionStore, new_session_id
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = Path(tmp) / "store"
            store_dir.mkdir()
            session = new_session_id()
            record = ReceiveRecord(session, "s", "S", tmp, [{"kind": "file", "path": "a", "size": 1}], ["../a"])
            (store_dir / f"receive-{session}.json").write_text(json.dumps(record.__dict__))
            self.assertEqual(SessionStore(store_dir).all(), [])


if __name__ == "__main__":
    unittest.main()
