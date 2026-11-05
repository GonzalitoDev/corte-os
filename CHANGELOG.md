# Registro de cambios

Todas las versiones siguen versionado semántico. Fechas en formato ISO 8601.

## [0.1.0] - 2026-11-04

### Añadido

- Base Debian 12 bookworm amd64 con arranque BIOS y UEFI.
- Configuración live-build reproducible y contenedor de construcción.
- Identidad visual Corte OS: logo, fondos, tema GTK oscuro, iconos de aplicaciones y panel XFCE.
- Sesión de escritorio XFCE personalizada con panel inferior, menú, reloj, calendario, papelera y área de notificaciones.
- Corte Installer con interfaz GTK, detección de discos, modo automático y manual, creación de usuario, contraseña, zona horaria, teclado, fstab y GRUB BIOS/UEFI.
- Modo de instalación automática para pruebas de integración.
- Corte Browser, Corte Files, Corte Terminal, Corte Store, Corte Settings, Corte Notes, Corte Calculator, Corte Monitor, Corte Media, Corte Security y Corte Notifications.
- Servicios de arranque para marcadores de prueba en serie.
- Workflow de GitHub Actions con compilación de ISO, prueba de arranque e instalación automática en QEMU.
- Página de descarga para Corte Editor con lectura de metadatos reales de release.
- Documentación de construcción, instalación en VirtualBox y manual de usuario.

### Pendiente para 0.2.0

- Corte Arcade: Snake, Tetris, Buscaminas, Ajedrez, Sudoku, plataformas 2D, mini Minecraft 2D, supervivencia y carreras 2D.
- Sistema de puntuaciones y récords en SQLite.
- Primer arranque guiado y asistente de bienvenida.
- Firma de la ISO y publicación del release real.
