#!/usr/bin/env bash
set -euo pipefail

ISO="${1:?Uso: make-release-json.sh <iso>}"
TAG="${2:-v$(cat VERSION)}"
OUT="${3:-web/corte-os/release.json}"

[ -f "$ISO" ] || { echo "No existe $ISO" >&2; exit 1; }

VERSION="$(cat VERSION)"
SIZE="$(stat -c%s "$ISO")"
SHA256="$(sha256sum "$ISO" | cut -d' ' -f1)"
SHA512="$(sha512sum "$ISO" | cut -d' ' -f1)"
REPO="${GITHUB_REPOSITORY:-Corte-Editor/corte-os}"
URL="https://github.com/${REPO}/releases/download/${TAG}/$(basename "$ISO")"

python3 - "$OUT" "$VERSION" "$SIZE" "$SHA256" "$SHA512" "$URL" <<'PY'
import datetime
import json
import sys

(out, version, size, sha256, sha512, url) = sys.argv[1:7]
data = {
    "version": version,
    "developer": "gonzita",
    "released": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "summary": "Beta de Corte OS para VirtualBox: escritorio propio, aplicaciones y Corte Installer.",
    "iso": {
        "filename": f"CorteOS-{version}-amd64.iso",
        "size": int(size),
        "sha256": sha256,
        "sha512": sha512,
        "url": url,
    },
    "screenshots": [],
    "notes": [
        "Desarrollado por gonzita.",
        "Incluye SOURCES.md y solo software libre de main/contrib.",
        "Es una beta: puede tener fallos; probala en una m?quina virtual.",
        "Base Debian 12 con arranque BIOS y UEFI.",
        "Escritorio XFCE personalizado y aplicaciones Corte.",
        "Corte Installer con modo automático y manual.",
    ],
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print(out)
PY
