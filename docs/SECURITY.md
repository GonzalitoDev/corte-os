# Seguridad de Corte OS

## Principios

- Corte OS no incluye telemetría, cuentas en la nube ni envío de datos.
- Las aplicaciones trabajan con archivos locales y muestran errores reales.
- El instalador solo funciona desde el entorno live y solo muestra discos virtuales o extraíbles verificados.
- El usuario live tiene `sudo` sin contraseña para poder instalar. Ese permiso se elimina del sistema instalado.
- La contraseña del usuario se guarda con el mecanismo de Debian (`/etc/shadow`), nunca en texto plano en la configuración de Corte OS.

## Instalación segura

1. `live_media_device()` identifica el dispositivo del medio live en `/proc/mounts`.
2. `list_disks()` excluye el medio live, discos `loop`, `zram` y `ram`.
3. Solo se aceptan discos virtuales reconocibles (`VBOX`, `QEMU`, `VMWARE`, `VIRTUAL`, `HARDDISK`, `VIRTIO`) o extraíbles USB.
4. El disco debe tener al menos 8 GB y no tener particiones montadas.
5. El modo manual permite elegir particiones, pero también las formatea; no permite instalar sobre una partición montada.
6. Antes de escribir, se desmontan las particiones del disco objetivo.
7. El instalador no toca otros discos. En VirtualBox, el disco virtual es el único disco visible salvo que el usuario añada discos físicos a la VM.

El modo `--allow-any-disk` existe para pruebas automatizadas y usos avanzados. No se expone en la interfaz gráfica.

## Cortafuegos y red

- UFW está instalado pero no se activa automáticamente. Se puede activar desde **Corte Security**.
- NetworkManager gestiona las conexiones. No se abren puertos de escucha propios.
- No se incluye servidor SSH por defecto.
- Las aplicaciones que necesitan red (navegador, tienda, actualizaciones) la usan solo cuando el usuario las abre.

## Contraseñas

- El instalador exige una contraseña de al menos 4 caracteres en modo automático y 8 en la interfaz gráfica. Se recomienda usar 12 o más.
- Corte Security incluye un analizador local y un generador con `secrets`.
- El cambio de contraseña usa `chpasswd` con autorización de administrador.
- El portapapeles no se limpia automáticamente; el texto copiado puede persistir hasta cerrar la sesión.

## Actualizaciones

- La ISO no se actualiza sola.
- Corte Security puede consultar actualizaciones con `apt-get -s upgrade` y actualizar índices.
- Las actualizaciones de paquetes se hacen con APT y requieren autorización de administrador.
- Una ISO publicada debe incluir su SHA-256 y, preferiblemente, SHA-512.

## Limitaciones conocidas

- No hay cifrado de disco en la versión 0.1.0.
- No hay arranque seguro (Secure Boot) firmado.
- ClamAV es opcional y sus firmas requieren Internet para actualizarse.
- El navegador usa WebKitGTK; su seguridad depende de las actualizaciones de Debian.
- El entorno live no guarda cambios y no debe usarse para datos sensibles.
- No se ha realizado una auditoría externa. No publiques una ISO como “segura” sin pruebas y revisión.

## Verificación de la descarga

Antes de instalar:

```bash
sha256sum -c CorteOS-<version>-amd64.iso.sha256
sha512sum -c CorteOS-<version>-amd64.iso.sha512
```

Compara con los valores publicados en la página de descarga. Si no coinciden, elimina el archivo y vuelve a descargarlo.

## Reportar problemas

Incluye:

- Versión de Corte OS (`cat /etc/corte/version`).
- Versión del kernel (`uname -a`).
- Configuración de la VM (BIOS/UEFI, RAM, disco, controlador de vídeo).
- Registro `/var/log/corte-installer.log` si el problema es de instalación.
- Pasos reproducibles y mensaje de error exacto.

No publiques contraseñas, claves SSH ni datos personales en los informes.
