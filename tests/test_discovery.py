"""Tests for reading network addresses on Linux and macOS."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lanxfer.discovery import parse_ifconfig, parse_ip_addr  # noqa: E402

MAC_IFCONFIG = """\
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
\tinet6 ::1 prefixlen 128
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tether 3c:22:fb:12:34:56
\tinet6 fe80::1c2b:aaaa:bbbb:cccc%en0 prefixlen 64 secured scopeid 0xe
\tinet 192.168.1.23 netmask 0xffffff00 broadcast 192.168.1.255
bridge100: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 10.20.0.1 netmask 0xfffff000
utun3: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1380
\tinet 10.8.0.2 --> 10.8.0.1 netmask 0xffffffff
"""

LINUX_IP_ADDR = """\
1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever
3: wlp3s0    inet 192.168.192.184/24 brd 192.168.192.255 scope global dynamic wlp3s0\\       valid_lft 80000sec
4: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\\       valid_lft forever
"""


class AddressParsingTests(unittest.TestCase):
    def test_macos_ifconfig(self):
        self.assertEqual(parse_ifconfig(MAC_IFCONFIG), {
            "127.0.0.1": "127.255.255.255",
            "192.168.1.23": "192.168.1.255",   # broadcast given
            "10.20.0.1": "10.20.15.255",       # worked out from the /20 netmask
            "10.8.0.2": "10.8.0.2",            # point-to-point VPN link
        })

    def test_linux_ip_addr(self):
        self.assertEqual(parse_ip_addr(LINUX_IP_ADDR), {
            "127.0.0.1": "127.255.255.255",
            "192.168.192.184": "192.168.192.255",
            "172.17.0.1": "172.17.255.255",
        })

    def test_garbage_gives_nothing(self):
        self.assertEqual(parse_ifconfig("command not found"), {})
        self.assertEqual(parse_ip_addr(""), {})


if __name__ == "__main__":
    unittest.main()
