# LAN File Transfer

[![Latest release](https://img.shields.io/github/v/release/nokkiee/LAN-File-Transfer)](https://github.com/nokkiee/LAN-File-Transfer/releases/latest)
[![License: MIT](https://img.shields.io/github/license/nokkiee/LAN-File-Transfer)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://github.com/nokkiee/LAN-File-Transfer/actions/workflows/tests.yml)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/nokkiee/LAN-File-Transfer/releases/latest)
[![Last commit](https://img.shields.io/github/last-commit/nokkiee/LAN-File-Transfer)](https://github.com/nokkiee/LAN-File-Transfer/commits/main)
[![Code size](https://img.shields.io/github/languages/code-size/nokkiee/LAN-File-Transfer)](https://github.com/nokkiee/LAN-File-Transfer)
[![Tests](https://github.com/nokkiee/LAN-File-Transfer/actions/workflows/tests.yml/badge.svg)](https://github.com/nokkiee/LAN-File-Transfer/actions/workflows/tests.yml)
[![Build apps](https://github.com/nokkiee/LAN-File-Transfer/actions/workflows/build.yml/badge.svg)](https://github.com/nokkiee/LAN-File-Transfer/actions/workflows/build.yml)

Send files and folders between computers on the same Wi‑Fi. Works between
any mix of Windows, Linux and macOS. Nothing goes over the internet, and you
don't need an account.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshot-dark.png">
  <img src="docs/screenshot-light.png" alt="LAN File Transfer: nearby computers on the left, files to send on the right, transfers with progress below" width="800">
</picture>

## Download

Get the latest version from the [Releases page](https://github.com/nokkiee/LAN-File-Transfer/releases/latest):

| Computer | File to use |
|----------|-------------|
| Windows 10 / 11 | `LAN-File-Transfer-Windows.exe` |
| Linux (64-bit)  | `LAN-File-Transfer-Linux` |
| macOS 14 or newer, Apple Silicon (M1 and later) | `LAN-File-Transfer-macOS.zip` |

The Windows and Linux versions are single files with nothing to install: put
the right one on each computer and run it. On a Mac, unzip the file and drag
**LAN File Transfer** into *Applications*. Intel Macs aren't supported.

See [CHANGELOG.md](CHANGELOG.md) for what changed in each version.

## Using it

1. Open the app on **both** computers. After a few seconds each one shows the
   other under **“1. Choose the computer to send to”**.
2. Drag files or folders into **“2. Choose files and folders”**, or use
   *Add files…* / *Add folder…*.
3. Click **Send**. The other computer asks whether to accept. Once accepted,
   the files are saved to `Downloads/LAN File Transfer`. You can change that
   folder at the bottom of the window or in *Settings*.

Use the **◐ Auto / ☀ Light / ☾ Dark** button in the top-right corner (or *Settings*)
to choose the look. *Auto* follows your system's light/dark setting.

The app speaks **English, Polski, Deutsch, Français and Español**. It follows
your computer's language; to pick another one, open *Settings → Language* and
restart the app when it asks.

Each transfer you receive gets its own numbered folder, named with the order
it arrived in, the date and time, and how many files it holds, e.g.
`0007 2026-10-12 12.32.02 7 files`. Windows doesn't allow `:` in names, so the time uses
dots. **Open folder** next to a finished transfer opens exactly that folder.

Folders are sent with everything inside them. Every file is checked with a
SHA‑256 checksum, and if a name already exists the new copy gets a number
(`photo (1).jpg`), so nothing is overwritten.

If the other computer doesn't appear, use **Add computer by IP address…** and
type the IP shown at the top of the app on the other computer.

## If the connection breaks

If the Wi‑Fi drops, a computer goes to sleep, or the app is closed in the
middle of a transfer, the transfer shows **⏸ Interrupted** instead of failing.
Both computers remember it, even after they restart.

- Files that arrived in full stay in the transfer's folder, ready to use. The
  file that was cut off is kept as `name.part`.
- When the two computers see each other again, the sender continues by itself.
  It skips the files that already arrived and sends the rest of the cut-off
  file from where it stopped. Both sides first check that the part already
  there matches, and if the file changed in the meantime it's sent again in
  full. Nobody is asked to accept again, and everything ends up in the same
  numbered folder.
- Click **Resume** on the sending computer to try straight away. **Discard**
  stops the transfer for good: the files that arrived stay, and the unfinished
  `.part` file is deleted.

Interrupted transfers are kept for 30 days. Both computers need a version newer
than 1.3.0; with an older copy on either side, a broken transfer has to be sent
again.

## Updating your other computers over Wi‑Fi

New versions are built on this Linux computer and sent to the others from
inside the app:

1. Build the new version with `./build_all.sh`. It builds both apps and signs
   them; the signing happens automatically.
2. Open the app on this computer. A bar at the top shows **“Version … is
   ready for …”**. Click **Update** (or right‑click a computer → *Update*).
3. The other computer asks **Update now / Not now**. After you accept, it
   downloads the new version, checks it, replaces itself and restarts. If files
   are being transferred, it waits for them to finish first.

Each computer in the list shows its version, with the build date in brackets,
for example `1.1.0 (12 Oct 16:22)`.

Updates are only installed if they were signed on the computer that built
them, so another device on the network can't push a fake “update”. They also
have to be newer than what's installed. The private signing key is created
automatically the first time you build and kept at
`~/.local/share/lan-file-transfer-release/signing-key.pem`. If it's ever lost,
a new one is made, and you copy the next version to each computer by hand once.

**Macs** can't install updates over Wi‑Fi yet: download each new version from
the Releases page instead. The app on your other computers reminds you.

Copies older than 1.1.0 can't update themselves, so copy the latest version to them by hand
once. The app reminds you which computers need that. To skip the question and
install updates automatically, set `"auto_install_updates": true` in that
computer's `settings.json`.

## First launch

**Windows**
- *“Windows protected your PC”* (SmartScreen): click **More info → Run anyway**.
  This appears because the app isn't code-signed.
- *Windows Firewall* asks whether to allow the app: tick **Private networks**
  (and **Public networks** if your Wi‑Fi is set to Public), then click **Allow**.
  If you missed the prompt, open *Windows Security → Firewall & network
  protection → Allow an app through firewall* and tick *LAN-File-Transfer-Windows*.

**Linux**
- Make the file executable once: right‑click → *Properties* → *Allow executing
  as program*, or run `chmod +x LAN-File-Transfer-Linux`. Then double‑click it
  or run it from a terminal.
- The first time it runs, it adds **LAN File Transfer** to your applications
  menu.
- Most desktop Linux installs have no firewall enabled. If you use one, open
  TCP port 52525 and UDP port 52526:
  - Ubuntu (ufw): `sudo ufw allow 52525/tcp && sudo ufw allow 52526/udp`
  - Fedora (firewalld): `sudo firewall-cmd --permanent --add-port=52525/tcp --add-port=52526/udp && sudo firewall-cmd --reload`

**macOS**
- The first time you open it, macOS says it can't check the app for malicious
  software. That's because the app isn't registered with Apple, which costs a
  yearly fee. Click **Done**, then open *System Settings → Privacy & Security*,
  scroll down to the message about *LAN File Transfer* and click
  **Open Anyway**. This is only needed once. If macOS instead says the app is
  *damaged*, run this once in *Terminal*:
  `xattr -dr com.apple.quarantine "/Applications/LAN File Transfer.app"`
- When macOS asks whether *LAN File Transfer* may **find devices on your local
  network**, click **Allow**, or the computers can't see each other. If you
  missed it: *System Settings → Privacy & Security → Local Network* and turn
  on *LAN File Transfer*.
- If the macOS firewall is on and asks about incoming connections, click
  **Allow**.

## Troubleshooting

- **Computers don't see each other:** check that both are on the same Wi‑Fi
  network (not a guest network) and that the firewall allows the app (see
  above). Some routers have “AP/client isolation” turned on, which stops
  devices from talking to each other; turn it off in the router settings or
  connect both computers to the main network. You can always fall back to
  *Add computer by IP address…*.
- **Log file:** `%APPDATA%\LAN File Transfer\app.log` on Windows,
  `~/.config/lan-file-transfer/app.log` on Linux,
  `~/Library/Application Support/LAN File Transfer/app.log` on macOS.

## Security note

Transfers aren't encrypted, which is the usual trade-off for LAN tools like
this. Use it on networks you trust, such as your home Wi‑Fi. Nothing is ever
saved without you clicking **Accept** (unless you turn that off in Settings),
and incoming file names are sanitized so they can't write outside the receive
folder. See [SECURITY.md](SECURITY.md) for details and how to report a problem.

---

## For developers

Python 3.10+ and Qt (PySide6). The networking code (`lanxfer/discovery.py`,
`lanxfer/transfer.py`, `lanxfer/protocol.py`) has no GUI dependencies. Both
versions are built from the same source. `protocol.py` describes the wire
format.

```
main.py                     entry point
lanxfer/gui.py              the window
lanxfer/discovery.py        finding computers (UDP broadcast, port 52526)
lanxfer/transfer.py         sending/receiving (TCP, port 52525)
lanxfer/pathsafe.py         making received file names safe on each OS
lanxfer/updates.py          signed over-Wi-Fi app updates (push, verify, self-test, install)
tools/release.py            signing key, build stamp and dist/update-manifest.json
lanxfer/settings.py         settings.json
tests/test_core.py          unit/integration tests
tests/interop_peer.py       headless peer for cross-OS testing
```

Run from source: `pip install -r requirements.txt && python main.py`

Run the tests: `python -m unittest discover -s tests`

Build:
- Both apps, signed for over‑Wi‑Fi updates: `./build_all.sh` (what you normally want)
- Linux binary: `./build_linux.sh`
- Windows .exe on a Windows PC: double-click `build_windows.bat` (needs Python from python.org)
- Windows .exe from Linux: `./build_windows_on_linux.sh` (uses Wine; see the comment in
  `tools/wine_icu_stub.py` for the one workaround it needs)
- macOS app on a Mac: `./build_macos.sh` (makes `dist/LAN-File-Transfer-macOS.zip`)

The Linux binary runs on distributions at least as new as the one it was built
on. On an older distro, build it there with `./build_linux.sh`.

GitHub also builds all three apps automatically (*Build apps* on the Actions
tab) and checks that each one starts and receives a file. Those are unsigned
test builds; the Linux one is made on Ubuntu 22.04 so it runs on older
distributions too. Official Windows and Linux releases are built and signed
with `./build_all.sh`. The macOS app in a release is GitHub's build of the same
commit, since it isn't part of Wi‑Fi updates yet.

## License

[MIT](LICENSE). The downloadable apps also bundle third-party libraries under
their own licenses, mainly Qt for Python (PySide6, LGPL-3.0), `cryptography`
(Apache-2.0 / BSD) and Python itself (PSF License). Because this repo contains
the full source and build scripts, you can rebuild the apps with your own copy
of these libraries.
