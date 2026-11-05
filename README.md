# Corte OS

Sistema operativo Linux propio, ligero y sin dependencia de Internet, construido sobre Debian 12 (bookworm) para x86_64 y pensado para ejecutarse e instalarse en Oracle VirtualBox.

P?gina publicada: https://corte-os.vercel.app/

Corte OS no es una simulación web. Es una distribución Linux real con kernel, arranque GRUB, entorno gráfico XFCE personalizado, aplicaciones nativas GTK, instalador propio y utilidades de sistema.

## Estado de esta entrega

Esta entrega contiene el código fuente completo de la Etapa 1 y la base para las etapas siguientes.

| Área | Estado |
| --- | --- |
| Definición de la distribución y scripts de construcción | Implementado, pendiente de compilar |
| Sesión gráfica XFCE con identidad Corte | Implementado |
| Corte Installer (GTK + backend real + modo automático) | Implementado, pendiente de probar en VM |
| Aplicaciones base | Implementadas |
| Centro de notificaciones | Implementado sobre dunst |
| Corte Arcade y juegos | Etapa 2 |
| ISO firmada y publicada | Pendiente de compilar y verificar |
| Página de descarga para Corte Editor | Implementada, pendiente de enlazar a un release real |

Importante: este equipo de desarrollo es Windows y no dispone de WSL, Docker ni virtualización habilitada, por lo que aquí no se ha podido generar ni arrancar la ISO. El repositorio incluye un flujo de integración continua que compila la ISO, la arranca en QEMU y ejecuta una instalación automática de prueba antes de publicar cualquier artefacto. No se debe publicar una ISO hasta que ese flujo pase.

## Base técnica

- Base: Debian 12 bookworm, amd64.
- Arranque: BIOS (syslinux) y UEFI (GRUB EFI), ISO híbrida.
- Kernel: linux-image-amd64 de Debian.
- Entorno gráfico: XFCE 4.18 con tema, iconos, panel, fondos y sesión propios.
- Aplicaciones: Python 3 + GTK 3 + PyGObject.
- Almacenamiento local: SQLite.
- Navegador: WebKitGTK 4.1.
- Multimedia: GStreamer.
- Instalador: Corte Installer, Python + GTK, con backend `parted`, `unsquashfs`, `chroot` y GRUB.
- Construcción: live-build dentro de Debian 12, Docker o GitHub Actions.

## Requisitos de la máquina anfitriona

Para compilar:

- Linux x86_64 (Debian 12 o Ubuntu 22.04+), root/sudo, 20 GB libres, 4 GB de RAM.
- O Docker con privilegios.
- O GitHub Actions usando el workflow incluido.

Para usar:

- Oracle VirtualBox 7.x.
- 2 GB de RAM, 2 vCPU, disco virtual de 20 GB, vídeo VMSVGA, red NAT.
- BIOS y UEFI compatibles.

## Construcción

### Opción A: Linux nativo

```bash
sudo apt-get update
sudo apt-get install -y live-build xorriso qemu-system-x86 ovmf squashfs-tools
sudo ./build/build.sh
```

La ISO se genera en `dist/CorteOS-<version>-amd64.iso` junto a su SHA-256.

### Opción B: Docker

```bash
docker build -t corte-os-builder -f build/Dockerfile .
docker run --rm --privileged -v "$PWD:/work" corte-os-builder /work/build/build.sh
```

### Opción C: GitHub Actions

El workflow `.github/workflows/build-iso.yml` compila, arranca la ISO en QEMU, prueba la instalación automática en un disco virtual, calcula el SHA-256 y publica el artefacto. Solo si todas las pruebas pasan se puede publicar el release.

Los detalles completos están en [docs/BUILD.md](docs/BUILD.md).

## Prueba en VirtualBox

1. Crear una máquina virtual: Linux / Debian (64-bit), 2048 MB de RAM, 2 CPU, 20 GB de disco.
2. En Almacenamiento, montar `CorteOS-<version>-amd64.iso` en la unidad óptica.
3. En Sistema, habilitar EFI solo si se quiere probar UEFI; para BIOS dejar deshabilitado.
4. En Pantalla, seleccionar controlador VMSVGA y 128 MB de vídeo.
5. Arrancar la máquina y probar el entorno live.
6. Abrir **Corte Installer** desde el escritorio o el menú y seguir el asistente.
7. Reiniciar y arrancar desde el disco instalado.

La guía paso a paso está en [docs/INSTALL-VIRTUALBOX.md](docs/INSTALL-VIRTUALBOX.md).

## Aplicaciones incluidas

- Corte Browser: navegador WebKitGTK con barra de direcciones, historial y página de inicio local.
- Corte Files: explorador de archivos con navegación, copiar, mover, renombrar, papelera y propiedades.
- Corte Terminal: terminal VTE real con shell del sistema.
- Corte Store: catálogo local de aplicaciones incluidas y paquetes opcionales mediante APT.
- Corte Settings: apariencia, resolución, sonido, red, usuarios, contraseña e información del sistema.
- Corte Notes: notas con SQLite, búsqueda y autoguardado.
- Corte Calculator: calculadora con historial en SQLite.
- Corte Monitor: CPU, RAM, discos y procesos con posibilidad de finalizar procesos.
- Corte Media: reproductor GStreamer para audio y vídeo local.
- Corte Security: firewall UFW, puertos abiertos, análisis de contraseñas y revisión básica del sistema.
- Corte Notifications: centro de notificaciones basado en el historial de dunst.
- Corte Installer: instalador gráfico con detección de discos, modo automático/manual, usuario, contraseña y GRUB.

Corte Arcade y los juegos se añaden en la Etapa 2, sobre la base ya funcional.

## Estructura

```text
build/            Sistema live-build, hooks, paquetes y scripts de compilación
src/corte/        Paquete Python de Corte OS (apps, escritorio, instalador)
src/assets/       Logos, fondos e iconos propios en SVG
docs/             Manuales de construcción, instalación, usuario y web
web/corte-os/     Página de descarga para Corte Editor
scripts/          Utilidades de pruebas y empaquetado
.github/          Integración continua de compilación y pruebas
dist/             ISO y sumas generadas (no versionado)
```

## Seguridad y alcance

- El instalador solo acepta discos completos que no sean el medio live. Rechaza discos del sistema anfitrión y exige confirmación explícita.
- En VirtualBox el disco objetivo es el disco virtual de la VM, nunca un disco físico del anfitrión.
- El usuario live tiene sudo sin contraseña para poder instalar; ese permiso se elimina del sistema instalado.
- No se incluyen enlaces de descarga ficticios. La página web lee un `release.json` real generado por el flujo de publicación.
- Las aplicaciones no simulan resultados: leen y escriben en el sistema real, muestran errores reales y no ocultan funciones no disponibles.

## Licencia

El código propio de Corte OS se distribuye bajo licencia MIT. Los componentes de terceros conservan sus licencias originales. Consulta [LICENSE](LICENSE).
