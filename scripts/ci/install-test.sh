#!/usr/bin/env bash
set -euo pipefail

ISO="${1:?Uso: install-test.sh <iso>}"
WORK="$(mktemp -d /tmp/corte-install-XXXX)"
LOG="$WORK/serial.log"
TARGET="$WORK/target.img"
TRIGGER="$WORK/trigger.img"
QEMU_PID=""

cleanup() {
    if [ -n "$QEMU_PID" ] && kill -0 "$QEMU_PID" 2>/dev/null; then
        kill "$QEMU_PID" 2>/dev/null || true
        wait "$QEMU_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

qemu-img create -f raw "$TARGET" 20G >/dev/null
dd if=/dev/zero of="$TRIGGER" bs=1M count=16 status=none
mkfs.vfat -n CORTE_CI "$TRIGGER" >/dev/null
cat > "$WORK/auto.json" <<'JSON'
{
  "disk": "/dev/sda",
  "user": "corte",
  "password": "corte",
  "hostname": "corte-os",
  "language": "es",
  "keyboard": "es",
  "timezone": "Europe/Madrid"
}
JSON
mcopy -i "$TRIGGER" "$WORK/auto.json" ::/auto.json

echo "[ci] Instalación automática en /dev/sda (disco virtual de 20G)"
qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -machine accel=tcg \
    -vga std \
    -display none \
    -serial "file:$LOG" \
    -monitor none \
    -netdev user,id=net0 \
    -device e1000,netdev=net0 \
    -drive "file=$ISO,media=cdrom,readonly=on" \
    -drive "file=$TARGET,format=raw,if=ide" \
    -drive "file=$TRIGGER,format=raw,if=ide" \
    -boot once=d,order=c &
QEMU_PID=$!

OK=0
for _ in $(seq 1 360); do
    if grep -q "CORTE_INSTALLED_BOOT_OK" "$LOG" 2>/dev/null; then
        OK=1
        break
    fi
    if grep -q "CORTE_INSTALL_FAILED" "$LOG" 2>/dev/null; then
        break
    fi
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
        break
    fi
    sleep 10
done

kill "$QEMU_PID" 2>/dev/null || true
wait "$QEMU_PID" 2>/dev/null || true
QEMU_PID=""

if [ "$OK" -eq 1 ]; then
    echo "[ci] OK: el sistema instalado arrancó desde el disco virtual."
    exit 0
fi

echo "[ci] ERROR: la instalación o el arranque posterior falló."
tail -n 350 "$LOG" || true
exit 1
