"""Start a built app off-screen, send it a file over the network, and check it arrived.

Used by the Build apps workflow on Windows, Linux and macOS:

    python tests/smoke_app.py <path to the app's executable>
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer.discovery import ping  # noqa: E402
from lanxfer.transfer import DONE, TransferManager  # noqa: E402

APP_ID = "smoke-test-app"


def find_app_port(proc: subprocess.Popen, timeout: float = 120) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            sys.exit(f"The app exited early (code {proc.returncode}).")
        for port in range(52525, 52535):
            info = ping("127.0.0.1", port, timeout=1)
            if info and info.get("id") == APP_ID:
                print(f"The app is running: version {info.get('version')} on {info.get('os')}, port {port}")
                return port
        time.sleep(1)
    sys.exit("The app never started listening.")


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform.startswith("win"):
        # The one-file .exe runs as two processes; end both.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(15)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> None:
    exe = sys.argv[1]
    work = Path(tempfile.mkdtemp(prefix="lanxfer-smoke-"))
    config, inbox = work / "config", work / "inbox"
    config.mkdir()
    (config / "settings.json").write_text(json.dumps({
        "device_id": APP_ID, "device_name": "Smoke test", "download_dir": str(inbox),
        "ask_before_receiving": False,
    }), encoding="utf-8")
    env = dict(os.environ, LANXFER_CONFIG_DIR=str(config), QT_QPA_PLATFORM="offscreen",
               XDG_DATA_HOME=str(work / "share"))
    proc = subprocess.Popen([exe], env=env)
    try:
        port = find_app_port(proc)
        payload = work / "hello.bin"
        payload.write_bytes(os.urandom(3_000_000))
        sender = TransferManager(lambda: {"id": "smoke-sender", "name": "CI", "os": "CI", "port": 0},
                                 lambda: str(work), lambda offer: offer.answer(False))
        transfer = sender.send("Smoke test", "127.0.0.1", port, [str(payload)])
        while not transfer.is_finished:
            time.sleep(0.1)
        if transfer.state != DONE:
            sys.exit(f"The transfer failed: {transfer.state} - {transfer.message}")
        received = list(inbox.glob("*/hello.bin"))
        if not received or received[0].read_bytes() != payload.read_bytes():
            sys.exit(f"The file didn't arrive intact (found: {received}).")
        print(f"Received {received[0].relative_to(inbox)} intact.")
    finally:
        stop(proc)
        log = config / "app.log"
        if log.exists():
            print("--- app.log ---")
            print(log.read_text(encoding="utf-8", errors="replace")[-3000:])


if __name__ == "__main__":
    main()
