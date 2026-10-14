#!/usr/bin/env bash
# Build the Windows .exe from Linux, using Wine and the official Windows build
# of Python (from NuGet). Everything stays inside build/wine/.
# -> dist/LAN-File-Transfer-Windows.exe
set -euo pipefail
cd "$(dirname "$0")"

PY_VERSION=3.13.16
WORK="$PWD/build/wine"
export WINEPREFIX="$WORK/prefix" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree=;mshtml="
PY="$WORK/python/python.exe"

command -v wine >/dev/null || { echo "Wine is not installed (sudo apt install wine)"; exit 1; }

if [ ! -f "$PY" ]; then
    mkdir -p "$WORK"
    curl -fL -o "$WORK/python.nupkg" "https://api.nuget.org/v3-flatcontainer/python/$PY_VERSION/python.$PY_VERSION.nupkg"
    rm -rf "$WORK/pkg" "$WORK/python"
    python3 -m zipfile -e "$WORK/python.nupkg" "$WORK/pkg"
    mv "$WORK/pkg/tools" "$WORK/python"
    rm -rf "$WORK/pkg"
fi
[ -d "$WINEPREFIX" ] || wineboot -i >/dev/null 2>&1
# Qt needs icuuc.dll, which Windows has but Wine lacks (see tools/wine_icu_stub.py)
ICU="$WINEPREFIX/drive_c/windows/system32/icuuc.dll"
[ -f "$ICU" ] || python3 tools/wine_icu_stub.py "$ICU"

wine "$PY" -m pip install -q --no-warn-script-location -r requirements.txt -r requirements-build.txt
wine "$PY" tools/make_icon.py
rm -f dist/LAN-File-Transfer-Windows.exe
wine "$PY" -m PyInstaller --noconfirm --log-level WARN --workpath build/pyinstaller-win lan-file-transfer.spec
echo "Built: dist/LAN-File-Transfer-Windows.exe"
