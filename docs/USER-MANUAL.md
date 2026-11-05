# Manual de usuario de Corte OS

Corte OS es una distribución Linux basada en Debian 12 con escritorio XFCE personalizado. Este manual describe las aplicaciones incluidas y las tareas habituales.

## Iniciar sesión y escritorio

- En el entorno live, el usuario es `corte` y la sesión se inicia automáticamente.
- En el sistema instalado, usa el usuario y la contraseña que creaste en Corte Installer.
- El panel inferior contiene: menú **Corte**, accesos a Files, Terminal, Browser, lista de ventanas, centro de notificaciones, bandeja del sistema, volumen, reloj/calendario y mostrar escritorio.
- El fondo, el tema y los iconos se pueden cambiar en **Corte Settings → Apariencia**.

### Atajos de teclado

| Atajo | Acción |
| --- | --- |
| `Super + Espacio` | Menú de aplicaciones |
| `Super + E` | Corte Files |
| `Super + Return` | Corte Terminal |
| `Super + B` | Corte Browser |
| `Super + I` | Corte Settings |
| `Super + L` | Bloquear la sesión |
| `Ctrl + Alt + T` | Nueva terminal |
| `Ctrl + Alt + Delete` | Cerrar sesión |
| `Print` | Captura de pantalla |

En XFCE, `Super` es la tecla Windows.

## Aplicaciones

### Corte Files

Explorador de archivos real.

- Navega con doble clic, Enter, los botones Atrás/Adelante/Subir/Inicio o la barra de ruta.
- Barra lateral: Inicio, Escritorio, Documentos, Descargas, Imágenes, Música, Vídeos, Papelera y Sistema.
- Botón derecho: abrir, renombrar, copiar, cortar, pegar, eliminar, propiedades.
- Eliminar envía a la papelera. En la papelera, eliminar borra de forma definitiva.
- **Vaciar papelera** usa `gio trash --empty`.
- **Mostrar archivos ocultos** está en el menú de tres puntos.
- La vista se actualiza automáticamente cuando cambia la carpeta.

Rutas habituales:

```text
~/Escritorio
~/Documentos
~/.local/share/corte     Datos de aplicaciones Corte
~/.config/corte          Configuración de aplicaciones Corte
```

### Corte Terminal

- Terminal VTE real con `/bin/bash`.
- Varias pestañas; cierra cada pestaña con la X.
- Botón derecho: copiar, pegar, seleccionar todo, limpiar pantalla.
- Puedes ejecutar cualquier comando Linux disponible en el sistema.

### Corte Notes

- Notas almacenadas en `~/.local/share/corte/notes.db` (SQLite).
- Búsqueda por título y contenido.
- Autoguardado al escribir; también puedes pulsar Guardar.
- Exportar a `.txt` con el botón Exportar.
- Eliminar con confirmación.

### Corte Calculator

- Operadores `+ - * / // % **`, paréntesis, constantes `pi`, `e`, `tau`.
- Funciones `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `log`, `ln`, `abs`, `round`.
- Historial persistente en `~/.local/share/corte/calculator.db`.
- Pulsa una entrada del historial para reutilizar el resultado.
- Evalúa expresiones de forma segura; no ejecuta código.

### Corte Monitor

- **Resumen**: uso de CPU y RAM con gráficas de 60 segundos, disco raíz, tiempo encendido, modelo de CPU, núcleos, swap y carga media.
- **Procesos**: lista de procesos con PID, usuario, CPU, RAM y estado. Selecciona uno y pulsa **Finalizar proceso** para enviar `SIGTERM`. Si no tienes permiso, solicita autorización de administrador.
- **Discos**: uso de cada punto de montaje.
- Los datos se actualizan automáticamente.

### Corte Media

- Reproductor GStreamer para audio y vídeo local.
- **Abrir archivos** admite selección múltiple y crea una lista de reproducción.
- Controles: anterior, reproducir/pausar, detener, siguiente, barra de posición, tiempo y volumen.
- Al terminar una pista, pasa a la siguiente.
- Formatos: los soportados por GStreamer (MP3, OGG, FLAC, WAV, MP4, MKV, WebM, AVI, MOV, etc.).
- Si un códec no está disponible, se muestra el error real de GStreamer.

### Corte Browser

- Navegador basado en WebKitGTK 4.1.
- Página de inicio local que funciona sin Internet.
- Barra de dirección: acepta URL o búsqueda (usa DuckDuckGo cuando hay red).
- Botones Atrás, Adelante, Recargar, Inicio. Menú con zoom y apertura externa.
- `Ctrl+L` enfoca la barra; `Ctrl+R` recarga; `Alt+Izquierda/Derecha` navega.
- Si no hay red, muestra una página de error local; no simula resultados.

### Corte Store

- Catálogo de aplicaciones incluidas y paquetes Debian opcionales.
- Las aplicaciones incluidas se abren directamente.
- Los paquetes opcionales se instalan con `apt-get` desde los repositorios Debian. Requiere Internet y autorización de administrador.
- Puedes desinstalar paquetes opcionales.
- **Actualizar lista** ejecuta `apt-get update`.
- En modo live, las instalaciones no persisten al reiniciar.
- No hay pagos, cuentas ni descargas simuladas.

### Corte Settings

- **Apariencia**: fondos de pantalla, tema GTK, iconos y tema de ventanas. Se aplican con `xfconf`.
- **Pantalla**: resoluciones detectadas por `xrandr`, por salida conectada.
- **Sonido**: volumen y silencio con PulseAudio; botón para abrir el mezclador.
- **Red**: estado de NetworkManager, activar/desactivar Wi-Fi, listar redes, conectar con contraseña y abrir el editor de conexiones.
- **Usuarios**: lista de usuarios, cambio de contraseña, creación y eliminación. Requiere autorización de administrador.
- **Sistema**: versión, kernel, equipo, arquitectura, memoria, tiempo encendido, sesión y escritorio; botones para abrir Monitor/Terminal y copiar la información.
- **Instalador**: solo disponible en modo live.

### Corte Security

- **Resumen**: puntuación basada en el estado real de UFW, actualizaciones pendientes, ClamAV y última revisión SUID.
- **Firewall**: consulta y activa/desactiva UFW. Muestra las reglas.
- **Puertos**: puertos en escucha según `ss -tulpn`.
- **Contraseñas**: analizador local, generador y cambio de contraseña. El análisis no se guarda ni se envía.
- **Sistema**: comprobación de actualizaciones, índices APT, búsqueda de archivos SUID y escaneo con ClamAV si está instalado.
- Limitaciones: no es un antivirus completo, no sustituye una auditoría y no bloquea ataques en tiempo real.

### Corte Notifications

- Historial de notificaciones de dunst.
- Pausar/reanudar notificaciones, cerrar todas, limpiar historial y volver a mostrar una notificación.
- El historial es de la sesión actual; no se guarda en disco.

### Corte Installer

Solo se ejecuta desde la ISO live. Instala en un disco virtual o extraíble verificado. Consulta `INSTALL-VIRTUALBOX.md`.

## Configuración y datos

| Ruta | Contenido |
| --- | --- |
| `~/.local/share/corte/notes.db` | Notas |
| `~/.local/share/corte/calculator.db` | Historial de calculadora |
| `~/.config/corte/welcome-seen` | Bienvenida mostrada |
| `~/.config/xfce4/` | Configuración del escritorio |
| `~/.config/dunst/dunstrc` | Notificaciones |
| `/etc/corte/version` | Versión del sistema |
| `/etc/corte/installed` | Marca del sistema instalado |
| `/var/log/corte-installer.log` | Registro del instalador |

## Actualizaciones

Corte OS no se actualiza solo. Para actualizar paquetes:

```bash
sudo apt-get update
sudo apt-get upgrade
```

En modo live, los cambios se pierden al reiniciar. La actualización de la ISO completa se publica como una nueva versión.

## Solución de problemas

### Una aplicación no abre

Abre una terminal y ejecuta el comando correspondiente para ver el error:

```bash
corte files
corte browser
corte settings
corte-installer
```

### No hay sonido

```bash
pactl info
pactl list short sinks
alsamixer
```

Comprueba el dispositivo en **Corte Settings → Sonido** y que la VM tenga audio habilitado.

### No hay red

```bash
nmcli device status
ip addr
ping -c 3 1.1.1.1
```

En VirtualBox usa NAT. El Wi-Fi en una VM requiere configuración especial del anfitrión.

### La papelera no vacía

```bash
gio trash --list
gio trash --empty
```

### Recuperar espacio

```bash
sudo apt-get clean
rm -rf ~/.cache/*
```

## Teclado y accesibilidad

- La distribución se elige en el instalador y se guarda en `/etc/default/keyboard`.
- XFCE permite ajustar tamaño de fuente, tema y contraste desde **Ajustes → Apariencia**.
- El tema Corte Dark usa colores de alto contraste sobre fondo oscuro.
