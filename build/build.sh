#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
BUILD="$ROOT/build"
CONFIG="$BUILD/config"
STAGE_LIB="$CONFIG/includes.chroot/usr/lib/corte"
STAGE_SHARE="$CONFIG/includes.chroot/usr/share/corte"
STAGE_DOC="$CONFIG/includes.chroot/usr/share/doc/corte-os"
STAGE_ICONS="$CONFIG/includes.chroot/usr/share/icons/hicolor/scalable/apps"
STAGE_THEMES="$CONFIG/includes.chroot/usr/share/themes"
STAGE_BACKGROUNDS="$CONFIG/includes.chroot/usr/share/backgrounds/corte"
STAGE_PIXMAPS="$CONFIG/includes.chroot/usr/share/pixmaps"
DIST="$ROOT/dist"

log() { printf '\033[1;36m[corte-os]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[corte-os] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    die "Ejecuta este script como root (sudo ./build/build.sh)."
fi

for tool in lb xorriso mksquashfs debootstrap; do
    command -v "$tool" >/dev/null 2>&1 || die "Falta la herramienta '$tool'. Instala las dependencias de docs/BUILD.md."
done

log "Corte OS $VERSION"
log "Generando configuración de live-build"
cd "$BUILD"
lb clean >/dev/null 2>&1 || true
bash "$CONFIG/auto/config"

log "Preparando fuentes en el árbol de live-build"

rm -rf "$STAGE_LIB" "$STAGE_SHARE" "$STAGE_DOC" "$STAGE_ICONS" "$STAGE_THEMES" "$STAGE_BACKGROUNDS" "$STAGE_PIXMAPS"
mkdir -p "$STAGE_LIB" "$STAGE_SHARE" "$STAGE_DOC" "$STAGE_ICONS" "$STAGE_THEMES" "$STAGE_BACKGROUNDS" "$STAGE_PIXMAPS"

cp -a "$ROOT/src/corte" "$STAGE_LIB/corte"
cp -a "$ROOT/src/assets/." "$STAGE_SHARE/"
cp -a "$ROOT/docs/." "$STAGE_DOC/"
cp -a "$ROOT/README.md" "$STAGE_DOC/README.md"
cp -a "$ROOT/CHANGELOG.md" "$STAGE_DOC/CHANGELOG.md"
cp -a "$ROOT/LICENSE" "$STAGE_DOC/LICENSE"
cp -a "$ROOT/src/assets/icons/apps/." "$STAGE_ICONS/"
cp -a "$ROOT/src/assets/themes/." "$STAGE_THEMES/"
cp -a "$ROOT/src/assets/backgrounds/." "$STAGE_BACKGROUNDS/"
cp -a "$ROOT/src/assets/logo.svg" "$STAGE_PIXMAPS/corte-logo.svg"
cp -a "$ROOT/src/assets/logo.svg" "$STAGE_ICONS/corte-logo.svg"
cp -a "$ROOT/VERSION" "$STAGE_SHARE/VERSION"

find "$STAGE_LIB" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$STAGE_LIB" -type f -name '*.pyc' -delete
find "$STAGE_SHARE" -type d -name '__pycache__' -prune -exec rm -rf {} +

python3 -m compileall -q "$STAGE_LIB/corte"

chmod 0755 "$CONFIG/auto/config"
chmod 0755 "$BUILD"/config/hooks/normal/*.hook.chroot
chmod 0755 "$CONFIG"/includes.chroot/usr/bin/* 2>/dev/null || true
chmod 0644 "$CONFIG"/includes.chroot/usr/share/applications/*.desktop 2>/dev/null || true

log "Construyendo la imagen (esto puede tardar entre 20 y 60 minutos)"
lb build

shopt -s nullglob
ISOS=( "$BUILD"/live-image-*.hybrid.iso )
[ "${#ISOS[@]}" -gt 0 ] || die "live-build no generó ninguna ISO."

mkdir -p "$DIST"
ISO="$DIST/CorteOS-${VERSION}-amd64.iso"
mv -f "${ISOS[0]}" "$ISO"
(
    cd "$DIST"
    sha256sum "$(basename "$ISO")" > "$(basename "$ISO").sha256"
    sha512sum "$(basename "$ISO")" > "$(basename "$ISO").sha512"
)

log "ISO generada: $ISO"
log "SHA-256: $(cut -d' ' -f1 "$ISO.sha256")"
log "Tamaño: $(du -h "$ISO" | cut -f1)"
