"""Tests for the transfer engine (no GUI). Run: python -m unittest discover tests"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer import transfer as tx  # noqa: E402
from lanxfer.discovery import ping  # noqa: E402
from lanxfer.pathsafe import clean_name, plan_destinations, split_relpath  # noqa: E402


def wait_until(predicate, timeout=20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def tree(root: Path) -> dict[str, bytes | None]:
    out = {}
    for path in sorted(root.rglob("*")):
        out[path.relative_to(root).as_posix()] = path.read_bytes() if path.is_file() else None
    return out


class PathSafetyTests(unittest.TestCase):
    def test_rejects_escaping_paths(self):
        for bad in ["../x", "a/../../x", "/etc/passwd", "a//b", "", "./a"]:
            with self.assertRaises(ValueError, msg=bad):
                split_relpath(bad)

    def test_windows_names_are_cleaned(self):
        self.assertEqual(clean_name('a:b?.txt', windows=True), "a_b_.txt")
        self.assertEqual(clean_name("CON.txt", windows=True), "_CON.txt")
        self.assertEqual(clean_name("trailing. ", windows=True), "trailing")
        self.assertEqual(clean_name("back\\slash", windows=True), "back_slash")
        self.assertEqual(clean_name("a:b?.txt", windows=False), "a:b?.txt")

    def test_existing_and_case_collisions_get_numbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "Photos").mkdir()
            (base / "notes.txt").write_text("x")
            items = [
                {"kind": "dir", "path": "Photos"},
                {"kind": "file", "path": "Photos/a.jpg"},
                {"kind": "file", "path": "notes.txt"},
                {"kind": "file", "path": "Readme.md"},
                {"kind": "file", "path": "README.md"},
            ]
            dests = plan_destinations(items, base, windows=True)
            names = [d.relative_to(base).as_posix() for d in dests]
            self.assertEqual(names, ["Photos (1)", "Photos (1)/a.jpg", "notes (1).txt", "Readme.md", "README (1).md"])


class MacNameTests(unittest.TestCase):
    """macOS ignores case (and accent encoding) in names but allows ":"."""

    def test_case_and_accent_variants_are_kept_apart(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            items = [{"kind": "file", "path": p} for p in
                     ("Readme.md", "README.md", "caf\u00e9.txt", "cafe\u0301.txt")]
            dests = plan_destinations(items, base, windows=False, case_insensitive=True)
            names = [d.name for d in dests]
            self.assertEqual(names[:2], ["Readme.md", "README (1).md"])
            self.assertEqual(names[2], "caf\u00e9.txt")
            self.assertTrue(names[3].endswith(" (1).txt"))

    @unittest.skipIf(sys.platform.startswith("win"), "on Windows \"a:\" is read as a drive letter")
    def test_colon_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            [dest] = plan_destinations([{"kind": "file", "path": "a:b.txt"}], Path(tmp), windows=False,
                                       case_insensitive=True)
            self.assertEqual(dest.name, "a:b.txt")  # fine on macOS, only Windows needs it changed

    def test_linux_keeps_case_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = [{"kind": "file", "path": p} for p in ("Readme.md", "README.md")]
            dests = plan_destinations(items, Path(tmp), windows=False, case_insensitive=False)
            self.assertEqual([d.name for d in dests], ["Readme.md", "README.md"])


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.src = root / "src"
        self.dst = root / "dst"
        self.src.mkdir()
        self.answer = True
        self.on_offer = None
        self.offers = []

        def present(offer):
            self.offers.append(offer)
            if self.on_offer:
                self.on_offer(offer)
            if self.answer is not None:
                offer.answer(self.answer)

        ident = {"id": "receiver-id", "name": "Receiver", "os": "Test", "port": 0}
        self.receiver = tx.TransferManager(lambda: ident, lambda: str(self.dst), present)
        self.port = self.receiver.receiver.start(47000)
        ident["port"] = self.port
        sender_ident = {"id": "sender-id", "name": "Sender", "os": "Test", "port": 0}
        self.sender = tx.TransferManager(lambda: sender_ident, lambda: str(root / "unused"), lambda o: None)

    def tearDown(self):
        self.receiver.receiver.stop()
        self.tmp.cleanup()

    def send(self, *paths) -> tx.Transfer:
        t = self.sender.send("Receiver", "127.0.0.1", self.port, [str(p) for p in paths])
        self.assertTrue(wait_until(lambda: t.is_finished), f"send did not finish: {t}")
        return t

    def received(self) -> tx.Transfer:
        self.assertTrue(wait_until(lambda: self.receiver.snapshot() and self.receiver.snapshot()[0].is_finished))
        return self.receiver.snapshot()[0]

    def folders(self) -> list[Path]:
        return sorted(p for p in self.dst.iterdir() if p.is_dir())

    def test_numbering_continues_after_existing_folders(self):
        self.dst.mkdir()
        (self.dst / "0041 09.00.00 3 files").mkdir()
        (self.dst / "holiday photos").mkdir()
        (self.dst / "0099 not a folder.txt").write_text("x")
        folder = tx.make_transfer_folder(self.dst, 1, when=time.mktime((2026, 1, 1, 12, 32, 2, 0, 0, -1)))
        self.assertEqual(folder.name, "0042 2026-01-01 12.32.02 1 file")

    def test_ping(self):
        info = ping("127.0.0.1", self.port)
        self.assertEqual(info["name"], "Receiver")

    def test_folder_and_files_round_trip(self):
        folder = self.src / "My Folder"
        (folder / "sub" / "deeper").mkdir(parents=True)
        (folder / "empty dir").mkdir()
        (folder / "sub" / "deeper" / "data.bin").write_bytes(os.urandom(3 * 1024 * 1024 + 123))
        (folder / "zero.txt").write_bytes(b"")
        (folder / "ünïcødé 名前.txt").write_text("héllo", encoding="utf-8")
        single = self.src / "single.dat"
        single.write_bytes(os.urandom(5000))
        mtime = 1_600_000_000
        os.utime(single, (mtime, mtime))

        t = self.send(folder, single)
        r = self.received()
        self.assertEqual(t.state, tx.DONE, t.message)
        self.assertEqual(r.state, tx.DONE, r.message)
        [inbox] = self.folders()
        self.assertRegex(inbox.name, r"^0001 \d{4}-\d\d-\d\d \d\d\.\d\d\.\d\d 4 files$")
        self.assertEqual(r.save_dir, str(inbox))
        self.assertEqual(tree(inbox / "My Folder"), tree(folder))
        self.assertEqual((inbox / "single.dat").read_bytes(), single.read_bytes())
        self.assertEqual(int((inbox / "single.dat").stat().st_mtime), mtime)
        self.assertEqual(r.files_done, 4)
        self.assertEqual(r.done_bytes, r.total_bytes)
        self.assertFalse(list(self.dst.rglob("*.part")))

        # Every transfer gets its own numbered folder.
        self.send(single)
        second = self.folders()[1]
        self.assertRegex(second.name, r"^0002 .* 1 file$")
        self.assertTrue((second / "single.dat").exists())

    def test_declined(self):
        self.answer = False
        (self.src / "a.txt").write_text("a")
        t = self.send(self.src / "a.txt")
        self.assertEqual(t.state, tx.DECLINED)
        self.assertFalse(self.dst.exists() and any(self.dst.iterdir()))

    def test_receiver_cancels(self):
        (self.src / "big.bin").write_bytes(os.urandom(8 * 1024 * 1024))
        self.on_offer = lambda offer: offer.transfer.cancel()
        t = self.send(self.src / "big.bin")
        r = self.received()
        self.assertEqual(r.state, tx.CANCELLED)
        self.assertEqual(t.state, tx.CANCELLED, t.message)
        self.assertIn("cancel", t.message.lower())
        self.assertFalse(list(self.dst.rglob("*")))

    def test_sender_cancels(self):
        (self.src / "big.bin").write_bytes(os.urandom(8 * 1024 * 1024))
        self.on_offer = lambda offer: self.sender.snapshot()[0].cancel()
        t = self.send(self.src / "big.bin")
        r = self.received()
        self.assertEqual(t.state, tx.CANCELLED)
        self.assertEqual(r.state, tx.CANCELLED, r.message)
        self.assertFalse(list(self.dst.rglob("*")))

    def test_sender_withdraws_before_answer(self):
        self.answer = None  # nobody clicks anything
        (self.src / "a.txt").write_text("a")
        t = self.sender.send("Receiver", "127.0.0.1", self.port, [str(self.src / "a.txt")])
        self.assertTrue(wait_until(lambda: self.offers))
        t.cancel()
        r = self.received()
        self.assertEqual(r.state, tx.CANCELLED)
        self.assertTrue(self.offers[0].withdrawn)

    def test_connection_refused(self):
        (self.src / "a.txt").write_text("a")
        t = self.sender.send("Nobody", "127.0.0.1", 1, [str(self.src / "a.txt")])
        self.assertTrue(wait_until(lambda: t.is_finished))
        self.assertEqual(t.state, tx.FAILED)

    def test_concurrent_transfers_get_distinct_names(self):
        (self.src / "same.txt").write_text("one")
        ts = [self.sender.send("Receiver", "127.0.0.1", self.port, [str(self.src / "same.txt")]) for _ in range(3)]
        self.assertTrue(wait_until(lambda: all(t.is_finished for t in ts)))
        folders = self.folders()
        self.assertEqual([f.name[:4] for f in folders], ["0001", "0002", "0003"])
        self.assertTrue(all((f / "same.txt").read_text() == "one" for f in folders))


if __name__ == "__main__":
    unittest.main()
