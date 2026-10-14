#!/usr/bin/env bash
# Build the Linux version -> dist/LAN-File-Transfer-Linux
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt -r requirements-build.txt
.venv/bin/python tools/make_icon.py
rm -f dist/LAN-File-Transfer-Linux  # unlink first: the app may be running from here
.venv/bin/pyinstaller --noconfirm --log-level WARN lan-file-transfer.spec
echo "Built: dist/LAN-File-Transfer-Linux"
