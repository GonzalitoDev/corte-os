#!/usr/bin/env bash
set -euo pipefail

ISO="${1:?Uso: boot-test.sh <iso>}"
LOG="${2:-$(mktemp -u /tmp/corte-boot-XXXX.log)}"

echo "[ci] Arrancando BIOS: $ISO"
echo "[ci] Log serie: $LOG"

set +e
timeout 1500 qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -machine accel=tcg \
    -vga std \
    -display none \
    -serial "file:$LOG" \
    -monitor none \
    -no-reboot \
    -netdev user,id=net0 \
    -device e1000,netdev=net0 \
    -drive "file=$ISO,media=cdrom,readonly=on" \
    -boot d
RC=$?
set -e

if grep -q "CORTE_LIVE_READY" "$LOG"; then
    echo "[ci] OK: el entorno live alcanzó el escritorio."
    exit 0
fi

echo "[ci] ERROR: no se detectó CORTE_LIVE_READY (qemu rc=$RC)."
tail -n 250 "$LOG" || true
exit 1
