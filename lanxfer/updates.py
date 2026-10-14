"""Over-Wi-Fi updates: push a newer build of this app to your other computers.

How it fits together:
- tools/release.py (run by build_all.sh) signs dist/update-manifest.json with a
  private Ed25519 key that only exists on the computer that builds the app.
  Every app carries the matching public key (update_key.py).
- An app that finds a valid manifest next to itself (or in dist/ when run from
  source) can push updates. Every app announces its version via discovery.
- The receiving app refuses anything that isn't signed with that key, isn't
  newer than itself, or isn't built for its system. It asks the user once,
  downloads the file, checks it against the SHA-256 in the signed manifest,
  starts it once with --self-test, swaps it in and restarts.
"""

import base64
import glob
import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import IS_WINDOWS, VERSION, os_label, update_key
from ._build import BUILD
from .protocol import APP_ID, PROTOCOL_VERSION, ProtocolError, RemoteCancelled, recv_frame, remote_stop, send_frame
from .transfer import (
    ACTIVE, CANCELLED, DECLINED, DONE, FAILED, IO_TIMEOUT, Cancelled, Outgoing, Transfer, TransferManager,
    abort_politely, describe_error, finish_from_remote, recv_file_data, wait_for_answer,
)

log = logging.getLogger(__name__)

MANIFEST_NAME = "update-manifest.json"
INSTALL_TIMEOUT = 300.0  # how long the sender waits while the receiver verifies and installs


class UpdateError(Exception):
    pass


def version_key(version, build) -> tuple:
    """Comparable (version parts, build stamp); newer builds compare greater."""
    try:
        parts = tuple(int(p) for p in str(version).split("."))
    except ValueError:
        parts = ()
    try:
        stamp = int(build or 0)
    except (TypeError, ValueError):
        stamp = 0
    return parts, stamp


CURRENT = version_key(VERSION, BUILD)


def display_version(version: str, build) -> str:
    """"1.1.0 (12 Oct 16:22)": the build date tells apart builds of the same version."""
    try:
        stamp = int(build or 0)
    except (TypeError, ValueError):
        stamp = 0
    return f"{version} ({time.strftime('%d %b %H:%M', time.localtime(stamp))})" if stamp else version


def platform_key() -> str:
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    return f"{os_label().lower()}-{arch}"


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def executable() -> Path:
    return Path(sys.executable).resolve()


def can_install() -> bool:
    """Only the packaged app, in a folder it may write to, can replace itself."""
    return bool(update_key.PUBLIC_KEY) and is_packaged() and os.access(executable().parent, os.W_OK)


def identity_fields() -> dict:
    """Extra fields every app announces about itself (see discovery.py)."""
    return {"version": VERSION, "build": BUILD, "target": platform_key(), "updates": can_install()}


# ---------------------------------------------------------------------------
# Signed release manifests
# ---------------------------------------------------------------------------

def sign_payload(payload: dict, private_key) -> dict:
    """Used by tools/release.py. ``private_key`` is an Ed25519PrivateKey."""
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {"payload": text, "signature": base64.b64encode(private_key.sign(text.encode("utf-8"))).decode()}


def verify_release(envelope, public_key: str | None = None) -> dict:
    """Check the signature and shape of a release; returns its payload."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    key = update_key.PUBLIC_KEY if public_key is None else public_key
    if not key:
        raise UpdateError("Updates aren't set up in this copy of the app.")
    try:
        text = envelope["payload"]
        signature = base64.b64decode(envelope["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(signature, text.encode("utf-8"))
    except InvalidSignature:
        raise UpdateError("The update isn't signed by your computer, so it was refused.") from None
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UpdateError("The update information is damaged.") from exc
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise UpdateError("The update information is damaged.") from exc
    _check_payload(payload)
    return payload


def _check_payload(payload) -> None:
    bad = UpdateError("The update information is damaged.")
    if not isinstance(payload, dict) or payload.get("app") != APP_ID:
        raise bad
    version, build, builds = payload.get("version"), payload.get("build"), payload.get("builds")
    if not isinstance(version, str) or not isinstance(build, int) or not isinstance(builds, dict):
        raise bad
    if not version_key(version, build)[0]:
        raise bad
    for entry in builds.values():
        if not (isinstance(entry, dict) and isinstance(entry.get("file"), str)
                and isinstance(entry.get("size"), int) and isinstance(entry.get("sha256"), str)
                and len(entry["sha256"]) == 64):
            raise bad
        if entry["file"] != os.path.basename(entry["file"]) or entry["file"] in ("", ".", ".."):
            raise bad


@dataclass
class Release:
    folder: Path
    envelope: dict
    version: str
    build: int
    builds: dict[str, dict]   # platform key -> {"file", "size", "sha256"}

    @property
    def key(self) -> tuple:
        return version_key(self.version, self.build)

    @property
    def label(self) -> str:
        return display_version(self.version, self.build)

    def path(self, target: str) -> Path:
        return self.folder / self.builds[target]["file"]


def release_folder() -> Path:
    if is_packaged():
        return executable().parent
    return Path(__file__).resolve().parent.parent / "dist"


def load_release(folder: Path, public_key: str | None = None) -> Release | None:
    """The signed release in ``folder``, limited to builds whose files are present."""
    try:
        envelope = json.loads((folder / MANIFEST_NAME).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.warning("Could not read %s: %s", folder / MANIFEST_NAME, exc)
        return None
    try:
        payload = verify_release(envelope, public_key)
    except UpdateError as exc:
        log.warning("Ignoring %s: %s", folder / MANIFEST_NAME, exc)
        return None
    builds = {}
    for target, entry in payload["builds"].items():
        try:
            if (folder / entry["file"]).stat().st_size == entry["size"]:
                builds[target] = entry
        except OSError:
            pass
    if not builds:
        return None
    return Release(folder, envelope, payload["version"], payload["build"], builds)


def peer_needs_update(peer, release: Release | None) -> bool:
    return bool(release and peer.updatable and peer.target in release.builds
                and release.key > version_key(peer.version, peer.build))


# ---------------------------------------------------------------------------
# Installing on this computer
# ---------------------------------------------------------------------------

def download_path() -> Path:
    exe = executable()
    return exe.with_name(f"{exe.stem}.update{exe.suffix}")


def self_test(path: Path, timeout: float = 180) -> tuple[str, int] | None:
    """Start the downloaded app once with --self-test. Returns the (version, build) it reports."""
    report = path.with_name(path.name + ".selftest")
    _remove(report)
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
    flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
    try:
        code = subprocess.run([str(path), "--self-test", str(report)], env=env, timeout=timeout,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=flags).returncode
        data = json.loads(report.read_text(encoding="utf-8"))
        return (data["version"], data["build"]) if code == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        log.warning("Self-test of %s failed: %s", path, exc)
        return None
    finally:
        _remove(report)


def install(new_file: Path) -> None:
    """Put ``new_file`` in place of the running app."""
    exe = executable()
    if IS_WINDOWS:
        # A running .exe can't be overwritten, but it can be renamed out of the way.
        old = exe.with_name(f"{exe.name}.{int(time.time())}.old")
        os.replace(exe, old)
        try:
            os.replace(new_file, exe)
        except OSError:
            os.replace(old, exe)
            raise
    else:
        os.chmod(new_file, 0o755)
        os.replace(new_file, exe)


def cleanup_after_update() -> None:
    """Remove what a previous update left behind (the old .exe on Windows).

    Right after an update the old version may still be closing, so keep trying
    in the background for a little while.
    """
    if not is_packaged():
        return
    exe = executable()
    _remove(download_path())

    def sweep() -> None:
        for _ in range(15):
            leftovers = glob.glob(glob.escape(str(exe)) + ".*.old")
            for leftover in leftovers:
                _remove(Path(leftover))
            if not glob.glob(glob.escape(str(exe)) + ".*.old"):
                return
            time.sleep(2)

    threading.Thread(target=sweep, name="update-cleanup", daemon=True).start()


def launch_installed_app() -> None:
    """Start the (new) app as a fresh, independent process."""
    env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1")
    if IS_WINDOWS:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([str(executable())], env=env, creationflags=flags, close_fds=True)
    else:
        subprocess.Popen([str(executable())], env=env, start_new_session=True, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Sending and receiving updates
# ---------------------------------------------------------------------------

@dataclass
class UpdateOffer:
    """An incoming update waiting for the user to accept or decline."""
    transfer: Transfer
    sender_name: str
    sender_ip: str
    from_version: str
    to_version: str
    withdrawn: bool = False
    _decided: threading.Event = field(default_factory=threading.Event, repr=False)
    _accepted: bool = False

    def answer(self, accept: bool) -> None:
        self._accepted = accept
        self._decided.set()


class UpdateService:
    def __init__(self, manager: TransferManager, present: Callable[[UpdateOffer], None],
                 on_installed: Callable[[str], None], auto_install: Callable[[], bool] = lambda: False):
        self.manager = manager
        self.present = present            # shows the offer; someone must call offer.answer()
        self.on_installed = on_installed  # the new version is in place; restart when convenient
        self.auto_install = auto_install
        # Swappable for tests:
        self.public_key = update_key.PUBLIC_KEY
        self.current = CURRENT
        self.target = platform_key()
        self.installable = can_install
        self.download_path = download_path
        self.self_test = self_test
        self.install = install
        self.release_folder = release_folder
        self._release: Release | None = None
        self._release_stamp = None
        manager.receiver.extra_handlers["update"] = self._handle

    # -- publishing -------------------------------------------------------

    def local_release(self) -> Release | None:
        """A signed release next to this app (or in dist/), if there is one."""
        folder = self.release_folder()
        stamps = []
        for name in (MANIFEST_NAME, *(e["file"] for e in (self._release.builds.values() if self._release else []))):
            try:
                st = (folder / name).stat()
                stamps.append((name, st.st_mtime_ns, st.st_size))
            except OSError:
                stamps.append((name, None, None))
        if stamps != self._release_stamp:
            self._release_stamp = stamps
            self._release = load_release(folder, self.public_key)
        return self._release

    def push(self, peer, release: Release) -> Transfer:
        transfer = Transfer("send", peer.name, peer.ip, kind="update")
        transfer.items = [release.label]
        transfer.file_count = 1
        transfer.total_bytes = release.builds[peer.target]["size"]
        self.manager.add(transfer)
        threading.Thread(target=self._send, args=(transfer, peer.ip, peer.port, release, peer.target),
                         name=f"update-{transfer.id}", daemon=True).start()
        return transfer

    def _send(self, transfer: Transfer, ip: str, port: int, release: Release, target: str) -> None:
        out = Outgoing(transfer, ip, port)
        identity = self.manager.identity()

        def body() -> None:
            accepted = out.offer({
                "app": APP_ID, "version": PROTOCOL_VERSION, "type": "update",
                "sender": {"id": identity["id"], "name": identity["name"], "os": os_label()},
                "release": release.envelope, "target": target,
            }, f"Waiting for {transfer.peer_name} to accept the update")
            if not accepted:
                return
            with open(release.path(target), "rb") as f:
                send_frame(out.sock, {"type": "file", "size": os.fstat(f.fileno()).st_size})
                out.stream(f)
            transfer.files_done = 1
            transfer.message = f"{transfer.peer_name} is checking and installing the update"
            out.final_reply(INSTALL_TIMEOUT)
            transfer._finish(DONE, f"{transfer.peer_name} now has version {release.label} and is restarting.")

        out.run(body)

    # -- receiving --------------------------------------------------------

    def _handle(self, conn, peer_ip: str, msg: dict) -> None:
        sender = msg.get("sender") if isinstance(msg.get("sender"), dict) else {}
        name = str(sender.get("name") or peer_ip)[:100]

        def refuse(reason: str) -> None:
            log.info("Refused an update from %s: %s", peer_ip, reason)
            send_frame(conn, {"type": "reject", "reason": reason})

        if not self.installable():
            return refuse("That copy of the app can't update itself (it isn't the packaged app, or its "
                          "folder is read-only). Copy the new version there by hand.")
        try:
            payload = verify_release(msg.get("release"), self.public_key)
        except UpdateError as exc:
            return refuse(str(exc))
        entry = payload["builds"].get(self.target)
        if entry is None:
            return refuse(f"The update has no version for {self.target}.")
        new_label = display_version(payload["version"], payload["build"])
        if version_key(payload["version"], payload["build"]) <= self.current:
            return refuse(f"That computer already has version {display_version(VERSION, BUILD)} or newer.")

        transfer = Transfer("receive", name, peer_ip, kind="update", items=[new_label],
                            file_count=1, total_bytes=entry["size"])
        self.manager.add(transfer)
        offer = UpdateOffer(transfer, name, peer_ip, display_version(VERSION, BUILD), new_label)
        download = self.download_path()
        try:
            transfer.message = "Waiting for you to accept the update"
            if self.auto_install():
                offer.answer(True)
            else:
                self.present(offer)
            answer = wait_for_answer(conn, offer)
            if answer is None:
                transfer._finish(CANCELLED, "The sender cancelled before you answered.")
                return
            if not answer:
                answered = offer._decided.is_set()
                transfer._finish(DECLINED, "You chose not to update now." if answered else "Not answered in time.")
                send_frame(conn, {"type": "reject", "reason": "The other computer chose not to update now."
                                  if answered else "Nobody answered on the other computer."})
                return
            send_frame(conn, {"type": "accept"})
            transfer.state = ACTIVE
            transfer.message = ""
            transfer.started = time.monotonic()
            conn.settimeout(IO_TIMEOUT)
            header = recv_frame(conn)
            if header.get("type") == "cancel":
                raise remote_stop(header, "The sender cancelled the update.")
            if header.get("type") != "file" or header.get("size") != entry["size"]:
                raise ProtocolError("unexpected update data")
            with open(download, "wb") as f:
                digest = recv_file_data(conn, f, transfer, entry["file"])
            if digest != entry["sha256"]:
                raise UpdateError("The downloaded update doesn't match its signature, so it was discarded.")
            transfer.files_done = 1
            transfer.message = "Checking that the new version starts"
            if not IS_WINDOWS:
                os.chmod(download, 0o755)
            if self.self_test(download) != (payload["version"], payload["build"]):
                raise UpdateError("The new version didn't start correctly on this computer, "
                                  "so the current version was kept.")
            self.install(download)
            send_frame(conn, {"type": "done"})
            log.info("Installed version %s (build %s) from %s", payload["version"], payload["build"], name)
            transfer._finish(DONE, f"Version {new_label} installed. Restarting…")
            self.on_installed(new_label)
        except Cancelled:
            transfer._finish(CANCELLED, "You cancelled the update.")
            abort_politely(conn, "The other computer cancelled the update.")
        except RemoteCancelled as exc:
            finish_from_remote(transfer, exc)
        except UpdateError as exc:
            log.warning("Update from %s failed: %s", peer_ip, exc)
            transfer._finish(FAILED, str(exc))
            abort_politely(conn, f"The update failed on the other computer: {exc}", failed=True)
        except OSError as exc:
            log.warning("Update from %s failed: %s", peer_ip, exc)
            transfer._finish(FAILED, describe_error(exc))
            if not isinstance(exc, (ConnectionError, TimeoutError)):
                abort_politely(conn, f"The update failed on the other computer: {describe_error(exc)}",
                               failed=True)
        except ProtocolError as exc:
            transfer._finish(FAILED, describe_error(exc))
        finally:
            _remove(download)
