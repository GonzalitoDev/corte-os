# Instalar Corte OS en Oracle VirtualBox

Esta guía cubre la creación de la máquina virtual, la prueba del entorno live y la instalación en el disco virtual.

## 1. Requisitos

- Oracle VirtualBox 7.x.
- ISO `CorteOS-<version>-amd64.iso` y su archivo `.sha256`.
- 2 GB de RAM (mínimo 1.5 GB).
- 2 núcleos de CPU.
- Disco virtual de 20 GB.
- 128 MB de vídeo, controlador VMSVGA.

## 2. Verificar la ISO (recomendado)

Linux/macOS:

```bash
sha256sum -c CorteOS-0.1.0-amd64.iso.sha256
```

Windows PowerShell:

```powershell
Get-FileHash .\CorteOS-0.1.0-amd64.iso -Algorithm SHA256
```

Compara el resultado con el SHA-256 publicado en la página de descarga. Si no coincide, no uses la ISO.

## 3. Crear la máquina virtual

### Automatizar la creación desde PowerShell (opcional)

Con VirtualBox instalado y `VBoxManage` disponible:

```powershell
.\scripts\virtualbox-test.ps1 -Iso .\dist\CorteOS-0.1.0-amd64.iso
```

El script crea una VM Debian 64-bit con 2 GB de RAM, 2 CPU, disco VDI de 20 GB, vídeo VMSVGA y red NAT, monta la ISO y la arranca. No modifica discos físicos del anfitrión. Para probar UEFI añade `-Efi`.

### Crear la máquina virtual manualmente

1. VirtualBox → **Nueva**.
2. Nombre: `Corte OS`.
3. Tipo: **Linux**. Versión: **Debian (64-bit)**.
4. RAM: **2048 MB**.
5. CPU: **2**.
6. Disco duro: **Crear un disco duro virtual ahora**, tipo VDI, asignación dinámica, **20 GB**.
7. Finaliza el asistente.

Ajustes adicionales:

- **Sistema → Placa base**: chipset PIIX3, orden de arranque con óptica primero. Habilita **EFI** solo si quieres probar UEFI; para BIOS déjalo desactivado.
- **Pantalla**: controlador **VMSVGA**, memoria de vídeo **128 MB**, aceleración 3D desactivada (Corte OS funciona sin ella).
- **Red**: adaptador **NAT**.
- **Audio**: controlador Intel HD Audio o AC'97.

## 4. Montar la ISO

1. Selecciona la VM y abre **Configuración → Almacenamiento**.
2. En **Controlador: IDE/SATA**, pulsa el icono de disco y elige **Elegir un archivo…**.
3. Selecciona `CorteOS-<version>-amd64.iso`.
4. Asegúrate de que la unidad óptica está conectada y marcada como primera en el orden de arranque.

## 5. Arrancar en modo live

1. Pulsa **Iniciar**.
2. En el menú de GRUB elige **Corte OS** (o deja que arranque solo).
3. Espera a que aparezca el escritorio. La primera vez puede tardar más por la emulación de vídeo.
4. Si aparece **Corte Welcome**, puedes cerrarlo o abrir el instalador desde ahí.

El entorno live no guarda cambios al reiniciar. Es ideal para probar el sistema antes de instalar.

## 6. Probar el escritorio

- Menú de aplicaciones: botón **Corte** en el panel inferior o **Super + Espacio**.
- Archivos: **Super + E**.
- Terminal: **Super + Return**.
- Navegador: **Super + B**.
- Ajustes: **Super + I**.
- Fondo, tema y resolución: **Corte Settings**.
- Monitor: **Corte Monitor**.
- Seguridad: **Corte Security**.

## 7. Instalar Corte OS

1. Abre **Corte Installer** desde el escritorio, el menú o **Corte Welcome**.
2. **Bienvenida**: elige el idioma y pulsa Siguiente.
3. **Teclado**: selecciona la distribución y prueba a escribir.
4. **Disco**:
   - **Automático**: selecciona el disco virtual y se crearán las particiones necesarias (BIOS + EFI + raíz).
   - **Manual**: abre GParted, prepara las particiones y selecciona la raíz y la EFI. El instalador las formateará.
   - Solo aparecen discos virtuales o extraíbles verificados. El medio live se excluye.
5. **Usuario**: nombre completo, usuario, contraseña, nombre del equipo, zona horaria e inicio automático.
6. **Resumen**: revisa los datos y marca la confirmación de borrado.
7. Pulsa **Instalar**. El instalador:
   - particiona y formatea el disco;
   - copia el sistema desde la ISO;
   - configura locale, teclado, zona horaria y usuario;
   - instala GRUB para BIOS y UEFI;
   - actualiza initramfs y prepara el arranque.
8. Al terminar, pulsa **Reiniciar ahora**.

## 8. Primer arranque desde el disco

1. En VirtualBox, abre **Dispositivos → Unidad óptica → Expulsar** o desconecta la ISO.
2. Reinicia la VM.
3. Debe aparecer GRUB con **Corte OS**.
4. Inicia sesión con el usuario y la contraseña creados. Si activaste el inicio automático, entrará directamente.

## 9. Integraci?n con VirtualBox

Corte OS 0.1.0 no incluye VirtualBox Guest Additions. El escritorio funciona con el controlador VMSVGA y la red NAT, pero las carpetas compartidas, el portapapeles bidireccional y el redimensionado autom?tico de la ventana no est?n garantizados. La resoluci?n se puede cambiar desde **Corte Settings ? Pantalla** con xrandr.

## 10. Comprobar el sistema instalado

```bash
cat /etc/os-release
uname -r
df -h
corte --version
```

Abre **Corte Settings → Sistema** para ver la información completa.

## Problemas frecuentes

### Pantalla negra al arrancar

- Cambia el controlador de vídeo a **VMSVGA**.
- Desactiva la aceleración 3D.
- En GRUB, edita la entrada y elimina `quiet splash` para ver mensajes.

### UEFI no arranca

- Comprueba que la VM tiene EFI habilitado y que la ISO se montó correctamente.
- El instalador crea `/boot/efi/EFI/CorteOS` y una entrada de respaldo `EFI/BOOT/BOOTX64.EFI`.
- Si el firmware no guarda la entrada NVRAM, la ruta de respaldo debería arrancar igualmente.

### El instalador no muestra discos

- Comprueba que añadiste un disco virtual de al menos 8 GB.
- Apaga la VM, revisa **Almacenamiento** y arranca de nuevo.
- Si el disco tiene particiones montadas, desmóntalas desde el entorno live.
- No uses la opción de disco físico del anfitrión.

### La instalación termina pero no arranca

- Expulsa la ISO.
- Revisa el orden de arranque.
- Arranca el modo live y revisa `/var/log/corte-installer.log`.
- En BIOS, la partición `bios_grub` debe existir. En UEFI, la partición FAT32 con flag `esp`.

### Sin Internet

- VirtualBox → **Configuración → Red → Adaptador 1 → NAT**.
- En el sistema: `nmcli device status`, `ip addr`, `ping -c 3 1.1.1.1`.
- Corte OS no incluye firmware propietario para todos los adaptadores Wi-Fi; en una VM usa NAT por cable.

## Desinstalar / volver atrás

Corte OS vive únicamente en el disco virtual. Para eliminarlo:

1. Apaga la VM.
2. VirtualBox → **Archivo → Administrador de medios virtuales**.
3. Elimina el disco virtual asociado.
4. Elimina la máquina virtual.

No se modifica el disco físico del anfitrión.
