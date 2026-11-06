"""Wire protocol shared by the Windows, Linux and macOS versions.

Discovery (UDP, port DISCOVERY_PORT): small JSON datagrams
    {"app": "lanxfer", "v": 1, "type": "hello"|"here"|"bye", "id", "name", "os", "port"}
"hello" is broadcast every few seconds; anyone who hears it answers with a
unicast "here", so a peer is found even if broadcasts only work one way.

Transfer (TCP, port DEFAULT_TCP_PORT): length-prefixed JSON frames
    [u32 big-endian length][UTF-8 JSON]

    sender -> {"type": "offer", "session": id, "items": [{"kind": "dir"|"file", "path": "a/b.txt", "size": n}, ...]}
    receiver -> {"type": "accept", "resumable": true} | {"type": "reject", "reason": ...}
    for each file item:
        sender -> {"type": "file", "index": i, "size": n, "mtime": t}
        sender -> chunks: [u32 n][n bytes] ... [u32 0] then the 32-byte SHA-256 of the data
        (or {"type": "skip", "index": i, "reason": ...} if the file became unreadable)
    sender -> {"type": "end"}
    receiver -> {"type": "done"}

Either side can stop a transfer: the sender sends ABORT_MARKER in place of a
chunk length (or a frame between files) followed by {"type": "cancel"}; the
receiver sends {"type": "cancel", "failed": bool} which the sender checks for
between chunks. Paths always use "/" and are relative; the receiver sanitizes them.

Resuming (see resume.py). "session" is 32 random hex digits. If the connection
breaks, or a cancel says "resumable": true (the app was closed), both sides keep
the session. The sender later sends the same offer again; a receiver that knows
the session accepts without asking and says what it already has:
    receiver -> {"type": "accept", "resumable": true, "have": {"done": [i, ...], "partial": {"i": bytes}}}
The sender skips the files in "done". For a "partial" file it sends "offset": k
in its "file" message; both sides then read the first k bytes of their copy and
    receiver -> {"type": "prefix", "index": i, "sha256": hex of its first k bytes}
    sender -> {"type": "continue", "offset": k}   (or 0 if the bytes differ: start the file again)
and the chunks carry the rest of the file. The SHA-256 after the chunks still
covers the whole file. When the sender gives up on a session without being
connected, it tells the receiver with {"type": "discard", "session": id, "sender": {"id"}}.
Apps from before resuming ignore these fields, and then nothing is resumed.

App updates (see updates.py) use the same connection format:
    sender -> {"type": "update", "release": {signed manifest}, "target": "windows-x86_64"}
    receiver -> accept/reject, then the file as {"type": "file", "size": n} + chunks,
    receiver -> {"type": "done"} once the new version is verified and installed.
"""

import json
import socket
import struct

APP_ID = "lanxfer"
PROTOCOL_VERSION = 1

DEFAULT_TCP_PORT = 52525
DISCOVERY_PORT = 52526

CHUNK_SIZE = 1024 * 1024
MAX_CHUNK = 16 * 1024 * 1024
MAX_FRAME = 64 * 1024 * 1024
DIGEST_SIZE = 32
END_OF_FILE = 0
ABORT_MARKER = 0xFFFFFFFF

_U32 = struct.Struct("!I")


class ProtocolError(Exception):
    """The other side sent something this version does not understand."""


class RemoteCancelled(Exception):
    """The other computer stopped the transfer (failed=True: because something went wrong there)."""

    def __init__(self, reason: str = "", failed: bool = False, resumable: bool = False):
        super().__init__(reason)
        self.failed = failed
        self.resumable = resumable  # it stopped only because the app was closed: continue later


def remote_stop(msg: dict, default: str) -> RemoteCancelled:
    """Turn a received {"type": "cancel"} frame into an exception."""
    return RemoteCancelled(str(msg.get("reason") or default), failed=bool(msg.get("failed")),
                           resumable=msg.get("resumable") is True)


def pack_u32(value: int) -> bytes:
    return _U32.pack(value)


def send_frame(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sock.sendall(_U32.pack(len(data)) + data)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray(n)
    view = memoryview(buf)
    got = 0
    while got < n:
        count = sock.recv_into(view[got:], n - got)
        if count == 0:
            raise ConnectionError("The connection to the other computer was lost")
        got += count
    return bytes(buf)


def recv_u32(sock: socket.socket) -> int:
    return _U32.unpack(recv_exact(sock, 4))[0]


def recv_frame(sock: socket.socket) -> dict:
    length = recv_u32(sock)
    if length > MAX_FRAME:
        raise ProtocolError("Received a message that is too large")
    try:
        obj = json.loads(recv_exact(sock, length).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("Received a malformed message") from exc
    if not isinstance(obj, dict):
        raise ProtocolError("Received a malformed message")
    return obj
