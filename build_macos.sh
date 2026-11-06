#!/usr/bin/env bash
# Build the macOS version on a Mac (Apple Silicon) -> dist/LAN-File-Transfer-macOS.zip
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt -r requirements-build.txt
.venv/bin/python tools/make_icon.py
rm -rf "dist/LAN File Transfer.app" dist/LAN-File-Transfer-macOS.zip
.venv/bin/pyinstaller --noconfirm --log-level WARN lan-file-transfer.spec
ditto -c -k --keepParent "dist/LAN File Transfer.app" dist/LAN-File-Transfer-macOS.zip
echo "Built: dist/LAN File Transfer.app and dist/LAN-File-Transfer-macOS.zip"
