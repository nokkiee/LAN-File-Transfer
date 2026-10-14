"""Tests for over-Wi-Fi app updates (signing, version checks, push/install flow)."""

import base64
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from lanxfer import transfer as tx  # noqa: E402
from lanxfer import updates  # noqa: E402
from lanxfer.discovery import Peer  # noqa: E402
from lanxfer.protocol import APP_ID  # noqa: E402

TARGET = "windows-x86_64"


def public_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def wait_until(predicate, timeout=20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def make_release(folder: Path, key, version="2.0.0", build=200, content=None, target=TARGET) -> dict:
    content = content if content is not None else os.urandom(3 * 1024 * 1024 + 7)
    (folder / "App.exe").write_bytes(content)
    payload = {"app": APP_ID, "version": version, "build": build, "builds": {
        target: {"file": "App.exe", "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}}}
    envelope = updates.sign_payload(payload, key)
    (folder / updates.MANIFEST_NAME).write_text(json.dumps(envelope), encoding="utf-8")
    return envelope


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.payload = {"app": APP_ID, "version": "1.2.0", "build": 5,
                        "builds": {TARGET: {"file": "a.exe", "size": 3, "sha256": "0" * 64}}}

    def test_valid_signature(self):
        envelope = updates.sign_payload(self.payload, self.key)
        self.assertEqual(updates.verify_release(envelope, public_b64(self.key)), self.payload)

    def test_tampered_payload_is_refused(self):
        envelope = updates.sign_payload(self.payload, self.key)
        envelope["payload"] = envelope["payload"].replace("1.2.0", "9.9.9")
        with self.assertRaisesRegex(updates.UpdateError, "isn't signed"):
            updates.verify_release(envelope, public_b64(self.key))

    def test_other_key_is_refused(self):
        envelope = updates.sign_payload(self.payload, Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(updates.UpdateError, "isn't signed"):
            updates.verify_release(envelope, public_b64(self.key))

    def test_garbage_and_missing_key(self):
        for junk in (None, {}, {"payload": "x"}, {"payload": "x", "signature": "!!"}, "text"):
            with self.assertRaises(updates.UpdateError):
                updates.verify_release(junk, public_b64(self.key))
        with self.assertRaisesRegex(updates.UpdateError, "set up"):
            updates.verify_release(updates.sign_payload(self.payload, self.key), "")

    def test_file_names_with_paths_are_refused(self):
        self.payload["builds"][TARGET]["file"] = "../evil.exe"
        with self.assertRaises(updates.UpdateError):
            updates.verify_release(updates.sign_payload(self.payload, self.key), public_b64(self.key))

    def test_version_order(self):
        vk = updates.version_key
        self.assertGreater(vk("1.1.0", 5), vk("1.1.0", 4))
        self.assertGreater(vk("1.1.0", 0), vk("1.0.9", 999))
        self.assertGreater(vk("1.10.0", 0), vk("1.9.0", 0))
        self.assertGreater(vk("1.0.0", 0), vk("", 0))


class ReleaseTests(unittest.TestCase):
    def test_load_release_and_needs_update(self):
        key = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            make_release(folder, key)
            release = updates.load_release(folder, public_b64(key))
            self.assertEqual((release.version, release.build), ("2.0.0", 200))
            old = Peer("p", "PC", "Windows", "1.2.3.4", 1, 0, version="1.1.0", build=9, target=TARGET, updatable=True)
            self.assertTrue(updates.peer_needs_update(old, release))
            for change in ({"version": "2.0.0", "build": 200}, {"updatable": False}, {"target": "linux-arm64"}):
                peer = Peer(**{**old.__dict__, **change})
                self.assertFalse(updates.peer_needs_update(peer, release), change)
            (folder / "App.exe").write_bytes(b"shorter")
            self.assertIsNone(updates.load_release(folder, public_b64(key)))
            self.assertIsNone(updates.load_release(folder, public_b64(Ed25519PrivateKey.generate())))


class PushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.pub_dir, self.inst_dir = root / "pub", root / "inst"
        self.pub_dir.mkdir()
        self.inst_dir.mkdir()
        self.key = Ed25519PrivateKey.generate()
        self.answer = True
        self.installed: list[bytes] = []
        self.restarts: list[str] = []
        self.self_test_result = "match"

        ident = {"id": "recv", "name": "Receiver", "os": "Windows", "port": 0}
        self.recv_mgr = tx.TransferManager(lambda: ident, lambda: str(root / "files"), lambda o: o.answer(True))
        self.recv = updates.UpdateService(self.recv_mgr, lambda offer: offer.answer(self.answer),
                                          self.restarts.append)
        self.recv.public_key = public_b64(self.key)
        self.recv.current = updates.version_key("1.1.0", 100)
        self.recv.target = TARGET
        self.recv.installable = lambda: True
        self.recv.download_path = lambda: self.inst_dir / "App.update.exe"
        self.recv.self_test = self._fake_self_test
        self.recv.install = lambda path: self.installed.append(path.read_bytes())
        self.port = self.recv_mgr.receiver.start(47200)

        sender_ident = {"id": "send", "name": "Publisher", "os": "Linux", "port": 0}
        self.send_mgr = tx.TransferManager(lambda: sender_ident, lambda: str(root / "x"), lambda o: o.answer(False))
        self.send = updates.UpdateService(self.send_mgr, lambda o: o.answer(False), lambda v: None)
        self.send.public_key = public_b64(self.key)
        self.send.release_folder = lambda: self.pub_dir
        self.peer = Peer("recv", "Receiver", "Windows", "127.0.0.1", self.port, 0,
                         version="1.1.0", build=100, target=TARGET, updatable=True)

    def _fake_self_test(self, path):
        if self.self_test_result == "match":
            return ("2.0.0", 200)
        return None

    def tearDown(self):
        self.recv_mgr.receiver.stop()
        self.tmp.cleanup()

    def push(self) -> tx.Transfer:
        release = self.send.local_release()
        self.assertIsNotNone(release)
        t = self.send.push(self.peer, release)
        self.assertTrue(wait_until(lambda: t.is_finished), t)
        return t

    def received(self):
        items = self.recv_mgr.snapshot()
        return items[0] if items else None

    def test_successful_update(self):
        make_release(self.pub_dir, self.key)
        t = self.push()
        self.assertEqual(t.state, tx.DONE, t.message)
        self.assertEqual(self.installed, [(self.pub_dir / "App.exe").read_bytes()])
        self.assertEqual(self.restarts, [updates.display_version("2.0.0", 200)])
        self.assertEqual(self.received().state, tx.DONE)
        self.assertFalse((self.inst_dir / "App.update.exe").exists())

    def test_declined(self):
        self.answer = False
        make_release(self.pub_dir, self.key)
        t = self.push()
        self.assertEqual(t.state, tx.DECLINED)
        self.assertEqual(self.installed, [])

    def test_wrong_key_is_refused_before_asking(self):
        evil_key = Ed25519PrivateKey.generate()
        make_release(self.pub_dir, evil_key)
        self.send.public_key = public_b64(evil_key)  # a rogue device that trusts its own key
        t = self.push()
        self.assertEqual(t.state, tx.DECLINED)
        self.assertIn("isn't signed", t.message)
        self.assertIsNone(self.received())  # the user was never asked
        self.assertEqual(self.installed, [])

    def test_not_newer_is_refused(self):
        make_release(self.pub_dir, self.key, version="1.1.0", build=100)
        t = self.push()
        self.assertEqual(t.state, tx.DECLINED)
        self.assertIn("already has", t.message)

    def test_wrong_system_is_refused(self):
        make_release(self.pub_dir, self.key, target="linux-x86_64")
        self.peer.target = "linux-x86_64"
        t = self.push()
        self.assertEqual(t.state, tx.DECLINED)
        self.assertIn("no version for", t.message)

    def test_file_swapped_after_signing_is_discarded(self):
        make_release(self.pub_dir, self.key)
        size = (self.pub_dir / "App.exe").stat().st_size
        (self.pub_dir / "App.exe").write_bytes(os.urandom(size))  # same size, different bytes
        t = self.push()
        self.assertEqual(t.state, tx.FAILED)
        self.assertIn("doesn't match", t.message)
        self.assertEqual(self.installed, [])
        self.assertFalse((self.inst_dir / "App.update.exe").exists())

    def test_failed_self_test_keeps_current_version(self):
        self.self_test_result = "broken"
        make_release(self.pub_dir, self.key)
        t = self.push()
        self.assertEqual(t.state, tx.FAILED)
        self.assertIn("kept", t.message)
        self.assertEqual(self.installed, [])
        self.assertEqual(self.restarts, [])

    def test_not_installable_is_refused(self):
        self.recv.installable = lambda: False
        make_release(self.pub_dir, self.key)
        t = self.push()
        self.assertEqual(t.state, tx.DECLINED)
        self.assertIn("by hand", t.message)


if __name__ == "__main__":
    unittest.main()
