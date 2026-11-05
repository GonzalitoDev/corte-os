# Hoja de ruta de Corte OS

## Etapa 1 — Base arrancable e instalable (0.1.0)

Estado: código implementado; pendiente de compilar y verificar la ISO en un entorno Linux.

Incluido:

- Debian 12 bookworm amd64.
- Arranque BIOS y UEFI.
- XFCE personalizado con tema, iconos, fondos, panel y sesión.
- Corte Installer con modo automático, manual, usuario, contraseña y GRUB.
- Aplicaciones base: Files, Terminal, Notes, Calculator, Monitor, Settings, Store, Browser, Media, Security y Notifications.
- Corte Welcome.
- Servicios y marcadores de prueba.
- Workflow de CI con QEMU y pruebas de instalación.
- Página de descarga.

Pendiente inmediato:

- Compilar la ISO en Debian/Ubuntu o GitHub Actions.
- Corregir cualquier fallo de arranque detectado.
- Probar la instalación en VirtualBox BIOS y UEFI.
- Obtener capturas reales.
- Calcular y publicar SHA-256/SHA-512.

## Etapa 2 — Corte Arcade (0.2.0)

- Launcher Corte Arcade.
- Snake.
- Tetris.
- Buscaminas.
- Ajedrez (python-chess + tablero GTK).
- Sudoku.
- Juego de plataformas 2D.
- Mini Minecraft 2D.
- Supervivencia.
- Carreras 2D.
- Récords y puntuaciones en SQLite.
- Integración en el menú, panel y escritorio.

## Etapa 3 — Pulido (0.3.0)

- Optimización de RAM y arranque.
- Soporte de VirtualBox Guest Additions o alternativa de integración.
- Fondo de arranque Plymouth.
- Primer arranque guiado.
- Centro de actualizaciones.
- Copias de seguridad.
- Traducción completa español/inglés.
- Accesibilidad y escalado HiDPI.
- Documentación ampliada.

## Etapa 4 — Publicación

- Compilación reproducible en CI.
- Pruebas de instalación BIOS/UEFI automatizadas.
- Firma y sumas de verificación.
- Release de GitHub con la ISO.
- Publicación de la página en Corte Editor.
- Manual de instalación y capturas reales.

## Reglas del proyecto

- No publicar una ISO sin arranque e instalación verificados.
- No incluir enlaces de descarga ficticios.
- No simular funciones de aplicaciones.
- No romper las funciones existentes de Corte Editor.
- Documentar cada versión en `CHANGELOG.md`.
