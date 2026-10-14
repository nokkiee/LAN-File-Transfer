"""Headless peer for cross-OS testing (e.g. Linux Python <-> Windows Python).

    python interop_peer.py receive <port> <save_dir>        # accepts one transfer, prints the result
    python interop_peer.py send <ip> <port> <path> [...]    # sends, prints the result
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer import os_label  # noqa: E402
from lanxfer.transfer import TransferManager  # noqa: E402


def main() -> None:
    mode = sys.argv[1]
    ident = {"id": f"interop-{mode}", "name": f"{os_label()} {mode}er", "os": os_label(), "port": 0}
    if mode == "receive":
        port, save_dir = int(sys.argv[2]), sys.argv[3]
        manager = TransferManager(lambda: ident, lambda: save_dir, lambda offer: offer.answer(True))
        manager.receiver.start(port, attempts=1)
        print("listening", flush=True)
        while not (manager.snapshot() and manager.snapshot()[0].is_finished):
            time.sleep(0.05)
    else:
        ip, port, paths = sys.argv[2], int(sys.argv[3]), sys.argv[4:]
        manager = TransferManager(lambda: ident, lambda: ".", lambda offer: offer.answer(False))
        transfer = manager.send("peer", ip, port, paths)
        while not transfer.is_finished:
            time.sleep(0.05)
    t = manager.snapshot()[0]
    print(json.dumps({"os": os_label(), "state": t.state, "message": t.message, "files": t.files_done,
                      "bytes": t.done_bytes, "from": t.peer_name}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
