# Changelog

All notable changes to LAN File Transfer are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.3.0] - 2026-11-06

### Added

- **Languages:** Polish, German, French and Spanish, besides English. The app follows the computer's language, or you choose one in *Settings → Language*. Plurals, decimal commas and month names follow the language, and Qt's own buttons and file dialogs are translated too. Messages sent between computers stay in English underneath, so each computer shows them in its own language.
- The numbered folders for received files are named in the app's language (for example `0012 2026-11-06 09.15.00 5 plików`).

## [1.2.0] - 2026-11-06

### Added

- **macOS version** for Apple Silicon Macs (M1 and later) on macOS 14 or newer. It works with the Windows and Linux versions in every direction. Received names are compared without regard to case, as on Windows, so `Readme.md` and `README.md` from Linux don't overwrite each other. Macs can't install updates over Wi‑Fi yet; download new versions from the Releases page.

## [1.1.2] - 2026-11-03

### Fixed

- Linux: after the app icon changes, the applications menu and dock show the new icon right away. Before, GNOME kept showing a cached copy of the old one until you logged out. The icon file's name now changes whenever the picture does.

## [1.1.1] - 2026-11-03

### Changed

- New app icon: a graphite tile with one white and one blue arrow, matching the app's grey look in both themes. The Linux applications-menu icon is replaced too.
- Minimum versions raised to the versions 1.1.0 was already built with: PySide6-Essentials 6.12.0, cryptography 50.0.2, PyInstaller 6.22.3.

### Repository

- A screenshot in the README (light and dark), and a link to the Releases page for downloads.
- An MIT license, contributing guide, security policy and code of conduct.
- Issue forms for bug reports and feature requests, and a pull request template.
- Private vulnerability reporting.
- Automatic tests on Windows and Linux (Python 3.10, 3.13 and 3.14) for every change.
- Automatic test builds of both apps, each checked to start before it's kept.
- Dependabot for dependency updates and security alerts.

## [1.1.0] - 2026-11-02

### Added

- **Updates over Wi‑Fi.** The computer that builds the app can push a new version to your other computers. Before installing, the receiving app checks that the update:
  - is signed (Ed25519) by the building computer,
  - is newer than the installed version (no downgrades),
  - is built for its system,
  - matches its checksum,
  - starts successfully once.

  It then replaces itself and restarts, waiting for running transfers to finish first. The receiving computer asks once (**Update now / Not now**).
- A bar at the top shows which computers can be updated, and which ones are too old to update themselves.
- Each computer in the list shows its version and build date, for example `1.1.0 (12 Oct 17:05)`.
- **Light and dark themes:** choose Auto, Light or Dark from the button in the top-right corner or in Settings. Auto follows the system setting as it changes.
- **A folder for every transfer.** Received files go into their own numbered folder, named with the date, time and number of files, for example `0012 2026-10-12 09.15.00 3 files`. **Open folder** opens exactly that folder.

### Changed

- Received files are no longer all saved directly in the receive folder; see the numbered folders above.
- Sending the same file twice now gives two separate folders instead of `name (1).ext`.
- The app looks the same on Windows and Linux (Qt Fusion style with its own colour palettes).

### Fixed

- A transfer cancelled before its first file arrived no longer leaves an empty folder behind.

## 1.0.0 - 2026-10-11

First version. Not published on GitHub.

- Send files and folders, including empty folders, between Windows and Linux computers on the same network.
- Computers find each other automatically (UDP broadcast). Each computer also answers the others directly, so discovery works even when broadcasts only get through in one direction.
- **Add computer by IP address…** for networks where discovery doesn't work.
- The receiver chooses **Accept** or **Decline**, with a 2-minute timeout and a warning when there isn't enough free space.
- Every file is checked with SHA‑256, and either side can cancel a transfer.
- Progress shows the percentage, speed, time left and current file.
- Received file names are made safe:
  - nothing can be written outside the receive folder,
  - names that aren't valid on Windows (`a:b.txt`, `CON`, trailing dots, names differing only in case) are fixed,
  - existing files are never overwritten.
- File modification times are kept.
- Settings: computer name, receive folder, and whether to ask before accepting.
- Single-file apps for Windows (`.exe`) and Linux. On Linux the app adds itself to the applications menu.

[Unreleased]: https://github.com/nokkiee/LAN-File-Transfer/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/nokkiee/LAN-File-Transfer/releases/tag/v1.3.0
[1.2.0]: https://github.com/nokkiee/LAN-File-Transfer/releases/tag/v1.2.0
[1.1.2]: https://github.com/nokkiee/LAN-File-Transfer/releases/tag/v1.1.2
[1.1.1]: https://github.com/nokkiee/LAN-File-Transfer/releases/tag/v1.1.1
[1.1.0]: https://github.com/nokkiee/LAN-File-Transfer/releases/tag/v1.1.0
