"""Prepare and sign a release so the app can push it to your other computers.

    python tools/release.py prepare   # before building: signing key + build stamp
    python tools/release.py sign      # after building: writes dist/update-manifest.json

build_all.sh runs both. The private signing key is created automatically the
first time and kept outside the project (see KEY_PATH); only its public half
goes into the app (lanxfer/update_key.py).
"""

import base64
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from lanxfer import APP_SLUG, VERSION  # noqa: E402
from lanxfer.protocol import APP_ID  # noqa: E402

KEY_PATH = Path(os.environ.get("LANXFER_SIGNING_KEY")
                or Path.home() / ".local" / "share" / f"{APP_SLUG}-release" / "signing-key.pem")
PUBLIC_KEY_FILE = ROOT / "lanxfer" / "update_key.py"
BUILD_FILE = ROOT / "lanxfer" / "_build.py"
DIST = ROOT / "dist"
MANIFEST = DIST / "update-manifest.json"
ARCH = {"amd64": "x86_64", "aarch64": "arm64"}.get(platform.machine().lower(), platform.machine().lower())
BUILDS = {  # platform key -> file in dist/
    f"linux-{ARCH}": "LAN-File-Transfer-Linux",
    "windows-x86_64": "LAN-File-Transfer-Windows.exe",
}


def read_public_key_file() -> str:
    scope: dict = {}
    exec(PUBLIC_KEY_FILE.read_text(encoding="utf-8"), scope)
    return scope.get("PUBLIC_KEY", "")


def load_or_create_key() -> Ed25519PrivateKey:
    if KEY_PATH.exists():
        return serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)
    if read_public_key_file():
        print(f"WARNING: the signing key {KEY_PATH} is missing, so a new one is being made.\n"
              "Apps built before now will refuse updates from this computer; copy the new\n"
              "version to each of them by hand once.", file=sys.stderr)
    key = Ed25519PrivateKey.generate()
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEY_PATH.parent, 0o700)
    fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
    print(f"Created the update signing key: {KEY_PATH}")
    return key


def prepare() -> None:
    key = load_or_create_key()
    public = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    if read_public_key_file() != public:
        PUBLIC_KEY_FILE.write_text(
            "# Public half of the key that signs app updates. Written by tools/release.py the\n"
            "# first time the apps are built; the private half never leaves that computer.\n"
            f'PUBLIC_KEY = "{public}"\n', encoding="utf-8")
    stamp = int(time.time())
    BUILD_FILE.write_text("# Written by tools/release.py when the apps are built; 0 means \"not a release build\".\n"
                          f"BUILD = {stamp}\n", encoding="utf-8")
    print(f"Version {VERSION}, build {stamp}")


def sign() -> None:
    from lanxfer.updates import sign_payload

    scope: dict = {}
    exec(BUILD_FILE.read_text(encoding="utf-8"), scope)
    build = scope["BUILD"]
    stamped_at = BUILD_FILE.stat().st_mtime
    builds = {}
    for target, name in BUILDS.items():
        path = DIST / name
        if not path.exists():
            continue
        if path.stat().st_mtime < stamped_at:
            print(f"Skipping {name}: it was built before the current build stamp.", file=sys.stderr)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        builds[target] = {"file": name, "size": path.stat().st_size, "sha256": digest}
    if not builds:
        sys.exit("Nothing to sign - build the apps first.")
    payload = {"app": APP_ID, "version": VERSION, "build": build, "builds": builds}
    MANIFEST.write_text(json.dumps(sign_payload(payload, load_or_create_key()), indent=2), encoding="utf-8")
    print(f"Signed version {VERSION} (build {build}) for: {', '.join(builds)}")


if __name__ == "__main__":
    {"prepare": prepare, "sign": sign}[sys.argv[1]]()
