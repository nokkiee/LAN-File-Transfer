# Contributing to LAN File Transfer

Thanks for helping out! Bug reports, ideas and pull requests are all welcome.

Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting a bug

Open an issue and include:

- both computers' operating systems (for example *Windows 11 → Ubuntu 24.04*)
- the app version on each, shown in the device list or under *Settings*
- what you did, what you expected, and what happened instead
- the log file from the computer where it went wrong:
  - Windows: `%APPDATA%\LAN File Transfer\app.log`
  - Linux: `~/.config/lan-file-transfer/app.log`
  - macOS: `~/Library/Application Support/LAN File Transfer/app.log`

If the computers can't see each other, first check *Troubleshooting* in the
[README](README.md). Most of these problems come from firewall settings or the
router's "client isolation" feature.

**Security problems** (for example a way to write files outside the receive
folder, or to get an unsigned update installed) shouldn't be described in a
public issue. Report them privately instead, as described in
[SECURITY.md](SECURITY.md).

## Suggesting a feature

Open an issue describing the problem it solves. The app's goal is to stay
simple: two computers, same Wi‑Fi, no accounts and no internet. Ideas that keep
it that way are easiest to accept.

## Working on the code

You need Python 3.10 or newer.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python main.py                        # run the app from source
.venv/bin/python -m unittest discover -s tests  # run the tests
```

Running two copies on the same computer needs separate settings. Start the second copy with
`LANXFER_CONFIG_DIR=/some/other/folder` set.

How the code is organised:

- `lanxfer/discovery.py`, `transfer.py`, `protocol.py`, `pathsafe.py` and
  `updates.py` hold all the networking and file handling. They have **no GUI
  code**, so they can be tested without a screen. Keep it that way.
- `lanxfer/gui.py` is the window. It only reads the state of transfers and
  calls into the modules above.
- `tests/interop_peer.py` is a headless sender/receiver for testing Windows ↔
  Linux transfers.

### Things to be careful with

- **Windows and Linux must keep working together.** If you change anything in
  `protocol.py` or what goes over the network, check that an unchanged version
  can still talk to yours. If it can't, raise `PROTOCOL_VERSION`. Test a real
  Windows ↔ Linux transfer if you can (`tests/interop_peer.py` helps).
- **File names from the other computer are untrusted.** Everything received
  goes through `pathsafe.py`, so nothing can be written outside the receive
  folder and names that are invalid on Windows get fixed. Add a test for any
  change there.
- **Update checks must never get weaker.** An update is only installed if it's
  signed, newer than the installed version, built for that system, matches its
  checksum and passes its self-test. Pull requests that loosen any of these
  won't be accepted.

### Translations

Texts are written in English in the code and wrapped in `tr("...")` (in the
window) or `Msg("...")` (in the networking code, so messages stay English in
logs and between computers). The translations live in `lanxfer/locales/`, one
file per language, keyed by the English text.

- After adding or changing a text, add it to **every** language file. The
  tests (`tests/test_i18n.py`) fail if a translation is missing or no longer
  used, or if its `{placeholders}` or plural forms don't match.
  `python tools/i18n_strings.py` lists all the texts.
- Texts with a number use plural forms: Polish needs three (1 plik, 2 pliki,
  5 plików), the others two.
- To add a language, create `lanxfer/locales/<code>.py`, then add it to
  `LANGUAGES` and `PLURAL_FORMS` in `lanxfer/i18n.py`, with its plural rule in
  `_plural_index` if it isn't the usual "1 = singular".

### Pull requests

- Keep each pull request focused on one thing.
- Make sure `python -m unittest discover -s tests` passes, and add tests for
  new behaviour in the networking and file-handling code.
  GitHub runs the tests automatically on Windows, Linux and macOS for every pull request.
- Match the style of the surrounding code: plain Python, standard library where
  possible, short comments that explain *why*.
- Say which systems you tested on (Windows, Linux, macOS).
- Don't commit built files (`dist/`, `build/`) or anything secret.

## Releases

Releases, the files on the Releases page, are built and signed by the
maintainer with `./build_all.sh`. The signing key never leaves the maintainer's
computer, so contributors don't need it and can't produce signed updates. That's
intentional. You can still build unsigned copies for testing with
`./build_linux.sh` or `build_windows.bat`.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
