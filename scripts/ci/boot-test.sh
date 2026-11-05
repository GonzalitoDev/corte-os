#!/usr/bin/env bash
set -euo pipefail

ISO="${1:?Uso: boot-test.sh <iso>}"
LOG="${2:-$(mktemp -u /tmp/corte-boot-XXXX.log)}"

echo "[ci] Arrancando BIOS: $ISO"
echo "[ci] Log serie: $LOG"

qemu-system-x86_64 \
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
    -boot d &
QPID=$!

OK=0
for _ in $(seq 1 750); do
    if grep -q "CORTE_LIVE_READY" "$LOG" 2>/dev/null; then
        OK=1
        break
    fi
    if ! kill -0 "$QPID" 2>/dev/null; then
        break
    fi
    sleep 2
done

kill "$QPID" 2>/dev/null || true
wait "$QPID" 2>/dev/null || true

if [ "$OK" -eq 1 ]; then
    echo "[ci] OK: el entorno live alcanzó el escritorio."
    exit 0
fi

echo "[ci] ERROR: no se detectó CORTE_LIVE_READY."
tail -n 250 "$LOG" || true
exit 1
