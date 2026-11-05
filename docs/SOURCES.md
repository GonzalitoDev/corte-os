# Fuentes y licencias de Corte OS

Corte OS es una distribución Linux independiente basada en Debian 12 (bookworm). No está afiliada, patrocinada ni respaldada por Debian, XFCE, GNOME, Mozilla, Oracle ni ninguna otra organización mencionada.

## Código propio de Corte OS

- Repositorio: https://github.com/GonzalitoDev/corte-os
- Etiqueta de esta versión: v0.1.2
- Licencia: MIT. El texto completo está en `/usr/share/doc/corte-os/LICENSE`.
- Incluye scripts de construcción, instalador, aplicaciones Python/GTK, servicios y recursos gráficos propios.
- El código fuente propio está disponible públicamente en el repositorio anterior.

## Debian y componentes de terceros

- Paquetes binarios: Debian 12 bookworm, componentes `main` y `contrib`.
- Fuentes oficiales de Debian: https://deb.debian.org/debian/ y https://sources.debian.org/
- Cada paquete incluye su aviso de copyright y su licencia en `/usr/share/doc/<paquete>/copyright`.
- Componentes principales incluidos:
  - Linux kernel: GPL-2.0.
  - Base Debian: diversas licencias libres.
  - XFCE: GPL/LGPL.
  - GTK 3: LGPL.
  - WebKitGTK: LGPL/BSD.
  - GStreamer: LGPL.
  - VTE: LGPL.
  - Python: PSF.
  - Papirus Icon Theme: GPL.
  - Arc Theme: GPL.
  - Fuentes Inter y JetBrains Mono: SIL Open Font License.
  - Resto de paquetes: las licencias indicadas en sus archivos de copyright.

El código fuente correspondiente de los paquetes Debian está disponible en los repositorios oficiales de Debian. No se han modificado los paquetes Debian incluidos; las modificaciones y el código nuevo de Corte OS están publicados en el repositorio del proyecto.

## Firmware

Esta ISO incluye únicamente software libre de `main` y `contrib`, más el paquete `firmware-linux-free`. No incluye paquetes de firmware de `non-free-firmware`, como `intel-microcode` o `amd64-microcode`.

Algunos adaptadores Wi-Fi, de vídeo o de audio pueden necesitar firmware propietario que no se distribuye en esta ISO. El usuario puede instalarlo por su cuenta desde los repositorios de Debian si lo necesita y acepta su licencia.

## VirtualBox

Corte OS es compatible con Oracle VirtualBox, pero no incluye ni redistribuye VirtualBox, sus Guest Additions ni software propietario de Oracle. VirtualBox se rige por su propia licencia y se descarga por separado desde Oracle.

## Marcas

Debian es una marca de Software in the Public Interest, Inc. Corte OS es un proyecto independiente y no está afiliado a Debian. Los nombres de otros productos y proyectos pertenecen a sus respectivos titulares. El uso de estos nombres es descriptivo.

## Garantía y estado

Corte OS 0.1.2 es una beta. Se proporciona «tal cual», sin garantía de ningún tipo. Probalo en una máquina virtual y no lo uses para datos importantes.

## Incidencias y contacto

Para reportar errores o consultar el código: https://github.com/GonzalitoDev/corte-os/issues

Esta documentación se incluye dentro de la ISO en `/usr/share/doc/corte-os/SOURCES.md`.
