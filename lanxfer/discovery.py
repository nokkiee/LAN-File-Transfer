"""Find other computers running the app on the local network (UDP broadcast)."""

import ipaddress
import json
import logging
import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

from . import IS_LINUX, IS_MAC, IS_WINDOWS
from .i18n import Msg
from .protocol import APP_ID, DEFAULT_TCP_PORT, DISCOVERY_PORT, PROTOCOL_VERSION, recv_frame, send_frame

log = logging.getLogger(__name__)

ANNOUNCE_INTERVAL = 2.5
PEER_TIMEOUT = 10.0


@dataclass
class Peer:
    id: str
    name: str
    os: str
    ip: str
    port: int
    last_seen: float
    manual: bool = False
    version: str = ""        # empty: an old app that predates automatic updates
    build: int = 0
    target: str = ""         # e.g. "windows-x86_64", which build it needs
    updatable: bool = False  # it can install updates pushed to it


def _usable(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (addr.is_loopback or addr.is_link_local or addr.is_unspecified or addr.is_multicast)


def _primary_ip() -> str | None:
    # Connecting a UDP socket sends nothing; it just asks the OS which local
    # address it would use to reach that destination.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.254.254.254", 1))
            return s.getsockname()[0]
        except OSError:
            return None


def parse_ip_addr(text: str) -> dict[str, str]:
    """{address: broadcast} from Linux's `ip -4 -o addr show`."""
    found = {}
    for ip, prefix in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", text):
        found[ip] = str(ipaddress.ip_interface(f"{ip}/{prefix}").network.broadcast_address)
    return found


def parse_ifconfig(text: str) -> dict[str, str]:
    """{address: broadcast} from macOS's `ifconfig` (netmask is printed in hex)."""
    found = {}
    pattern = r"inet (\d+\.\d+\.\d+\.\d+)(?: --> \S+)? netmask (0x[0-9a-fA-F]+)(?: broadcast (\d+\.\d+\.\d+\.\d+))?"
    for ip, mask, bcast in re.findall(pattern, text):
        prefix = bin(int(mask, 16)).count("1")
        found[ip] = bcast or str(ipaddress.ip_interface(f"{ip}/{prefix}").network.broadcast_address)
    return found


def _command_output(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def local_interfaces() -> list[tuple[str, str]]:
    """(local IPv4 address, its broadcast address) for every usable interface."""
    found: dict[str, str] = {}
    try:
        if IS_LINUX:
            found.update(parse_ip_addr(_command_output(["ip", "-4", "-o", "addr", "show"])))
        elif IS_MAC:
            found.update(parse_ifconfig(_command_output(["/sbin/ifconfig"])))
    except ValueError:
        pass
    candidates = []
    if not IS_MAC:  # on macOS this lookup can hang for seconds on mDNS, and ifconfig already listed everything
        try:
            candidates += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
        except OSError:
            pass
    primary = _primary_ip()
    if primary:
        candidates.insert(0, primary)
    for ip in candidates:
        # Windows offers no portable way to read the netmask; /24 is what
        # nearly every home router uses, and we also send to 255.255.255.255.
        found.setdefault(ip, str(ipaddress.ip_interface(f"{ip}/24").network.broadcast_address))
    ordered = sorted(found.items(), key=lambda kv: kv[0] != primary)
    return [(ip, bcast) for ip, bcast in ordered if _usable(ip)]


def parse_address(text: str) -> tuple[str, int]:
    """'192.168.1.5' or '192.168.1.5:52525' -> (ip, port). Raises ValueError."""
    text = text.strip()
    host, _, port = text.partition(":")
    ipaddress.IPv4Address(host)
    return host, int(port) if port else DEFAULT_TCP_PORT


def ping(ip: str, port: int, timeout: float = 2.0) -> dict | None:
    """Ask a computer directly (TCP) who it is. Returns its identity or None."""
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            send_frame(sock, {"app": APP_ID, "version": PROTOCOL_VERSION, "type": "ping"})
            reply = recv_frame(sock)
    except (OSError, ValueError):
        return None
    if reply.get("app") != APP_ID or reply.get("type") != "pong":
        return None
    return reply


class Discovery:
    def __init__(self, identity: Callable[[], dict], on_peers_changed: Callable[[], None] | None = None,
                 port: int = DISCOVERY_PORT):
        self.identity = identity  # returns {"id", "name", "os", "port"}
        self.on_peers_changed = on_peers_changed or (lambda: None)
        self.port = port
        self.manual_addresses: set[tuple[str, int]] = set()
        self._peers: dict[str, Peer] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._sock: socket.socket | None = None
        self._interfaces: list[tuple[str, str]] = []
        self._interfaces_checked = 0.0
        self._replied: dict[str, float] = {}
        self.error: str | None = None

    # -- public API -------------------------------------------------------

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if IS_WINDOWS and hasattr(socket, "SIO_UDP_CONNRESET"):
            # Otherwise one unreachable peer makes recvfrom() fail on Windows.
            sock.ioctl(socket.SIO_UDP_CONNRESET, False)
        try:
            sock.bind(("", self.port))
        except OSError as exc:
            self.error = Msg("Automatic discovery is unavailable (UDP port {port}: {error}).",
                             port=self.port, error=str(exc))
            log.error(self.error)
            sock.close()
        else:
            self._sock = sock
            threading.Thread(target=self._listen_loop, name="discovery-listen", daemon=True).start()
        threading.Thread(target=self._announce_loop, name="discovery-announce", daemon=True).start()

    def stop(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        try:
            self._broadcast("bye")
        except OSError:
            pass
        if self._sock:
            self._sock.close()

    def peers(self) -> list[Peer]:
        with self._lock:
            return sorted(self._peers.values(), key=lambda p: p.name.lower())

    def my_addresses(self) -> list[str]:
        return [ip for ip, _ in self._current_interfaces()]

    def add_manual(self, ip: str, port: int) -> Peer | None:
        """Contact a computer by address. Returns the peer if it answered."""
        info = ping(ip, port)
        if info is None:
            return None
        self.manual_addresses.add((ip, port))
        return self._update_peer(info, ip, manual=True)

    def forget(self, peer_id: str) -> None:
        with self._lock:
            peer = self._peers.pop(peer_id, None)
        if peer:
            self.manual_addresses.discard((peer.ip, peer.port))
            self.on_peers_changed()

    # -- internals --------------------------------------------------------

    def _message(self, kind: str) -> bytes:
        msg = {"app": APP_ID, "v": PROTOCOL_VERSION, "type": kind, **self.identity()}
        return json.dumps(msg).encode("utf-8")

    def _current_interfaces(self) -> list[tuple[str, str]]:
        if time.monotonic() - self._interfaces_checked > 15 or not self._interfaces:
            self._interfaces = local_interfaces()
            self._interfaces_checked = time.monotonic()
        return self._interfaces

    def _broadcast(self, kind: str) -> None:
        data = self._message(kind)
        interfaces = self._current_interfaces()
        if self._sock:
            # Sent from the discovery port itself, so the "here" replies coming
            # back to that port count as responses for Windows Firewall even
            # when the network is set to Public.
            for target in {bcast for _, bcast in interfaces} | {"255.255.255.255"}:
                try:
                    self._sock.sendto(data, (target, self.port))
                except OSError:
                    pass
        for local_ip, _ in interfaces:
            # One socket per interface: binding to the interface address makes
            # Windows send the broadcast out of that adapter.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                try:
                    s.bind((local_ip, 0))
                except OSError:
                    continue
                try:
                    s.sendto(data, ("255.255.255.255", self.port))
                except OSError:
                    pass
        for ip, _ in list(self.manual_addresses):
            self._unicast(kind, ip)

    def _unicast(self, kind: str, ip: str) -> None:
        sock = self._sock
        if sock is None:
            return
        try:
            sock.sendto(self._message(kind), (ip, self.port))
        except OSError:
            pass

    def _announce_loop(self) -> None:
        tick = 0
        while not self._stop.is_set():
            try:
                self._broadcast("hello")
            except Exception:
                log.exception("Discovery broadcast failed")
            # Manual peers are also checked over TCP, which works even when a
            # firewall or router drops UDP.
            if tick % 2 == 0:
                for ip, port in list(self.manual_addresses):
                    threading.Thread(target=self._check_manual, args=(ip, port), daemon=True).start()
            self._expire()
            tick += 1
            self._stop.wait(ANNOUNCE_INTERVAL)

    def _check_manual(self, ip: str, port: int) -> None:
        info = ping(ip, port)
        if info is not None and not self._stop.is_set():
            self._update_peer(info, ip, manual=True)

    def _listen_loop(self) -> None:
        my_id = self.identity()["id"]
        while not self._stop.is_set():
            try:
                data, (ip, _) = self._sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                if self._stop.is_set():
                    return
                continue
            if not isinstance(msg, dict) or msg.get("app") != APP_ID or msg.get("id") == my_id:
                continue
            kind = msg.get("type")
            if kind == "bye":
                with self._lock:
                    removed = self._peers.pop(str(msg.get("id")), None)
                if removed:
                    self.on_peers_changed()
            elif kind in ("hello", "here"):
                self._update_peer(msg, ip)
                # A hello can arrive several times per round (one per route);
                # answer each sender at most once a second.
                if kind == "hello" and time.monotonic() - self._replied.get(ip, 0) > 1:
                    self._replied[ip] = time.monotonic()
                    self._unicast("here", ip)

    def _update_peer(self, info: dict, ip: str, manual: bool = False) -> Peer | None:
        try:
            peer_id = str(info["id"])
            name = str(info.get("name") or ip)[:100]
            os_name = str(info.get("os") or "?")[:30]
            port = int(info.get("port") or DEFAULT_TCP_PORT)
            version = str(info.get("version") or "")[:20]
            build = int(info.get("build") or 0)
            target = str(info.get("target") or "")[:40]
        except (KeyError, TypeError, ValueError):
            return None
        updatable = info.get("updates") is True
        if peer_id == self.identity()["id"]:
            return None
        with self._lock:
            old = self._peers.get(peer_id)
            peer = Peer(peer_id, name, os_name, ip, port, time.monotonic(),
                        manual=manual or (old.manual if old else False),
                        version=version, build=build, target=target, updatable=updatable)
            changed = old is None or (old.name, old.ip, old.port, old.os, old.version, old.build, old.updatable) != (
                name, ip, port, os_name, version, build, updatable)
            self._peers[peer_id] = peer
        if old is None or (old.version, old.build) != (version, build):
            log.info("Found %s (%s, version %s build %s) at %s:%s%s", name, os_name, version or "?", build,
                     ip, port, " [added by IP]" if manual else "")
        if changed:
            self.on_peers_changed()
        return peer

    def _expire(self) -> None:
        now = time.monotonic()
        with self._lock:
            stale = [pid for pid, p in self._peers.items() if now - p.last_seen > PEER_TIMEOUT]
            for pid in stale:
                del self._peers[pid]
        if stale:
            self.on_peers_changed()
