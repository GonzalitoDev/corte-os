# Construir Corte OS

Corte OS se construye con `live-build` sobre Debian 12 (bookworm). El resultado es una ISO híbrida `amd64` que arranca por BIOS y UEFI.

## Requisitos del entorno de construcción

- Linux x86_64 (Debian 12 o Ubuntu 22.04/24.04).
- Acceso root o `sudo`.
- 20 GB de espacio libre.
- 4 GB de RAM recomendados.
- Conexión a Internet durante la compilación para descargar paquetes Debian.

Paquetes del anfitrión en Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y \
  live-build debootstrap xorriso squashfs-tools \
  isolinux syslinux syslinux-common syslinux-efi \
  grub-pc-bin grub-efi-amd64-bin \
  mtools dosfstools parted e2fsprogs rsync \
  qemu-system-x86 qemu-utils ovmf \
  python3 ca-certificates curl
```

En Windows se puede usar Docker Desktop o WSL2 con una distribución Debian/Ubuntu. El contenedor necesita `--privileged` porque `live-build` monta sistemas de archivos y crea el chroot.

## Compilación nativa

```bash
sudo ./build/build.sh
```

El script:

1. Copia el código de `src/corte` y los recursos de `src/assets` al árbol de `live-build`.
2. Valida la sintaxis Python con `compileall`.
3. Ejecuta `lb clean`, `lb config` y `lb build`.
4. Mueve la ISO a `dist/CorteOS-<version>-amd64.iso`.
5. Genera `dist/CorteOS-<version>-amd64.iso.sha256` y `.sha512`.

## Compilación con Docker

```bash
docker build -t corte-os-builder -f build/Dockerfile .
docker run --rm --privileged -v "$PWD:/work" corte-os-builder /work/build/build.sh
```

En PowerShell:

```powershell
docker build -t corte-os-builder -f build/Dockerfile .
docker run --rm --privileged -v "${PWD}:/work" corte-os-builder /work/build/build.sh
```

## Compilación y pruebas con GitHub Actions

El workflow `.github/workflows/build-iso.yml` se ejecuta en cada push y en cada tag `v*`. Realiza:

1. Compilación de la ISO.
2. Arranque de la ISO en QEMU con BIOS.
3. Comprobación del marcador `CORTE_LIVE_READY`.
4. Instalación automática en un disco virtual de 20 GB.
5. Arranque desde el disco instalado y comprobación de `CORTE_INSTALLED_BOOT_OK`.
6. Cálculo de SHA-256 y SHA-512.
7. Subida del artefacto de la ISO.
8. Publicación de un release de GitHub solo si todas las pruebas pasan.

Para publicar, crea un tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

El flujo está diseñado para no publicar una ISO que no haya arrancado e instalado correctamente. Si el entorno no permite virtualización anidada, QEMU usará emulación TCG; las pruebas tardan más pero siguen siendo válidas.

## Pruebas manuales de la ISO

Arranque con BIOS:

```bash
qemu-system-x86_64 -m 2048 -smp 2 \
  -drive file=dist/CorteOS-0.1.0-amd64.iso,media=cdrom \
  -boot d
```

Arranque con UEFI:

```bash
qemu-system-x86_64 -m 2048 -smp 2 \
  -bios /usr/share/OVMF/OVMF_CODE.fd \
  -drive file=dist/CorteOS-0.1.0-amd64.iso,media=cdrom \
  -boot d
```

Instalación automática de prueba:

```bash
qemu-img create -f raw /tmp/corte-target.img 20G
qemu-system-x86_64 -m 2048 -smp 2 \
  -drive file=dist/CorteOS-0.1.0-amd64.iso,media=cdrom \
  -drive file=/tmp/corte-target.img,format=raw,if=virtio \
  -boot d
```

Dentro del entorno live, el instalador también puede probarse en modo consola:

```bash
sudo corte-installer --auto --yes \
  --disk /dev/vda --user corte --password corte \
  --hostname corte-os --language es --keyboard es \
  --timezone Europe/Madrid --reboot
```

No ejecutes ese comando sobre un disco que no sea el disco virtual de la máquina.

## Solución de problemas

### `lb build` falla al descargar paquetes

Comprueba los mirrors en `build/config/auto/config`. Para redes con proxy, configura `http_proxy` y `https_proxy` en el entorno antes de compilar.

### Faltan paquetes de arranque

Asegúrate de que el anfitrión tiene `isolinux`, `syslinux-efi`, `grub-pc-bin` y `grub-efi-amd64-bin`. El contenedor `build/Dockerfile` los incluye.

### La ISO supera los 2 GiB de GitHub Releases

GitHub permite como máximo 2 GiB por archivo de release. Si la ISO se acerca al límite:

- Reduce paquetes opcionales de `build/config/package-lists/corte.list.chroot`.
- Mantén `--compression xz` en `build/config/auto/config`.
- Elimina documentación pesada o firmas de antivirus del sistema live.
- Puedes publicar la ISO en otro almacenamiento compatible y usar su URL en `release.json`, siempre que el SHA-256 sea verificable.

### La instalación no arranca después de reiniciar

- Comprueba que la ISO está expulsada o que el orden de arranque prioriza el disco.
- En BIOS, verifica que existe la partición `bios_grub` (la crea el modo automático).
- En UEFI, verifica `/boot/efi/EFI/CorteOS/grubx64.efi` y `/boot/efi/EFI/BOOT/BOOTX64.EFI`.
- Revisa `/var/log/corte-installer.log` desde el entorno live.

### El instalador no ve el disco

- El disco debe ser mayor de 8 GB.
- Debe ser un disco virtual o extraíble con modelo reconocible (`VBOX HARDDISK`, `QEMU HARDDISK`, VMware, USB).
- El medio live se excluye automáticamente.
- Los discos con particiones montadas se rechazan por seguridad.

### Sin red en VirtualBox

- Usa adaptador NAT.
- Comprueba `nmcli device` y `ip addr`.
- El Wi-Fi dentro de una VM no funciona salvo que el adaptador esté puenteado y el anfitrión lo permita. Corte OS muestra el estado real, no redes simuladas.

## Estructura del sistema live-build

```text
build/
  build.sh                       Orquestador
  Dockerfile                     Entorno reproducible
  config/
    auto/config                  Opciones de lb config
    package-lists/corte.list.*   Paquetes
    includes.chroot/             Archivos del sistema (etc, usr, skel)
    hooks/normal/                Ajustes dentro del chroot
```

Las fuentes Python se copian en tiempo de compilación a `/usr/lib/corte` y los recursos a `/usr/share/corte`, `/usr/share/themes`, `/usr/share/backgrounds` y `/usr/share/icons`.
