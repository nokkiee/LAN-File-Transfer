#!/usr/bin/env bash
# Build both versions and sign them so the app can push the update over Wi-Fi.
# -> dist/LAN-File-Transfer-Linux, dist/LAN-File-Transfer-Windows.exe, dist/update-manifest.json
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt -r requirements-build.txt
.venv/bin/python tools/release.py prepare
./build_linux.sh
./build_windows_on_linux.sh
.venv/bin/python tools/release.py sign
echo
echo "Done. Open LAN File Transfer on this computer and click Update to send it to your other computers."
