import json
import os
import re
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..common.paths import version

TARGET = Path("/target")
LIVE_MOUNTS = ("/run/live/medium", "/lib/live/mount/medium")
SAFE_MODELS = re.compile(r"(VBOX|VIRTUALBOX|QEMU|VMWARE|VIRTUAL|HARDDISK|VIRTIO)", re.IGNORECASE)
LANGUAGES = {"es": "es_ES.UTF-8", "en": "en_US.UTF-8"}
KEYBOARDS = {"es", "latam", "us", "gb", "fr", "de", "it", "pt", "br"}


class InstallerError(RuntimeError):
    pass


@dataclass
class Disk:
    name: str
    path: str
    size: int
    model: str
    tran: str
    removable: bool
    rota: bool
    mountpoints: list = field(default_factory=list)
    live: bool = False

    @property
    def size_gib(self):
        return self.size / (1024**3)


@dataclass
class InstallConfig:
    disk: str
    user: str
    password: str
    hostname: str = "corte-os"
    language: str = "es"
    keyboard: str = "es"
    timezone: str = "Europe/Madrid"
    mode: str = "auto"
    root_partition: str = ""
    efi_partition: str = ""
    autologin: bool = True
    reboot: bool = False
    allow_any_disk: bool = False
    full_name: str = ""


class Installer:
    def __init__(self, config, progress=None, log=None):
        self.config = config
        self.progress = progress or (lambda percent, message: None)
        self.log = log or (lambda message: None)
        self.warnings = []
        self.grub_bios_ok = False
        self.grub_efi_ok = False
        self.root_part = ""
        self.efi_part = ""
        self.root_uuid = ""
        self.efi_uuid = ""

    def info(self, message):
        self.log(message)
        self.progress(0, message)

    def step(self, percent, message):
        self.progress(percent, message)
        self.log(message)

    def check_environment(self):
        if os.geteuid() != 0:
            raise InstallerError("Corte Installer debe ejecutarse con permisos de administrador.")
        if not any(Path(mount).exists() for mount in LIVE_MOUNTS):
            raise InstallerError(
                "Corte Installer solo está disponible desde el entorno live de la ISO. "
                "No se ejecutará en un sistema instalado."
            )
        for tool in ("mount", "cp", "umount"):
            if shutil.which(tool) is None:
                raise InstallerError(f"Falta la herramienta {tool} en el entorno live.")
        if not Path("/usr/sbin/grub-install").exists() and not Path("/usr/bin/grub-install").exists():
            raise InstallerError("Falta grub-install.")
        if self.config.mode not in ("auto", "manual"):
            raise InstallerError("Modo de instalación no válido.")
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,62}$", self.config.hostname):
            raise InstallerError("El nombre del equipo no es válido.")
        if not re.match(r"^[a-z_][a-z0-9_-]{2,31}$", self.config.user):
            raise InstallerError("El nombre de usuario no es válido.")
        if len(self.config.password) < 4:
            raise InstallerError("La contraseña debe tener al menos 4 caracteres.")
        if self.config.language not in LANGUAGES:
            raise InstallerError("Idioma no soportado.")
        if self.config.keyboard not in KEYBOARDS:
            raise InstallerError("Distribución de teclado no soportada.")
        if not Path("/usr/share/zoneinfo") / self.config.timezone:
            raise InstallerError("Zona horaria no válida.")

        disk = Path(self.config.disk)
        if not disk.exists():
            raise InstallerError(f"El disco {self.config.disk} no existe.")
        if not stat.S_ISBLK(os.stat(disk).st_mode):
            raise InstallerError(f"{self.config.disk} no es un dispositivo de bloque.")
        if self.is_live_disk(self.config.disk):
            raise InstallerError("El disco seleccionado es el medio live. Elige otro disco.")
        if self.disk_mounted(self.config.disk):
            raise InstallerError("El disco seleccionado tiene particiones montadas. Desmonta antes de continuar.")
        disks = {item.path: item for item in list_disks()}
        selected = disks.get(self.config.disk)
        if selected is None:
            raise InstallerError("El disco seleccionado no aparece en lsblk.")
        if selected.size < 8 * 1024**3:
            raise InstallerError("El disco debe tener al menos 8 GB.")
        if not self.config.allow_any_disk and not is_safe_disk(selected):
            raise InstallerError(
                "Por seguridad, Corte Installer solo acepta discos virtuales o extraíbles. "
                "Si realmente quieres usar este disco, activa la opción avanzada de disco no verificado."
            )

        if self.config.mode == "manual":
            if not self.config.root_partition:
                raise InstallerError("Selecciona una partición raíz para la instalación manual.")
            if not Path(self.config.root_partition).exists():
                raise InstallerError("La partición raíz seleccionada no existe.")
            if self.config.efi_partition and not Path(self.config.efi_partition).exists():
                raise InstallerError("La partición EFI seleccionada no existe.")

    def is_live_disk(self, disk):
        live_device = live_media_device()
        if not live_device:
            return False
        if disk == live_device:
            return True
        result = run(["lsblk", "-J", "-b", "-o", "PATH,MOUNTPOINTS"], timeout=20)
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False
        for item in payload.get("blockdevices", []):
            if item.get("path") != disk:
                continue
            if self._has_live_mount(item):
                return True
        return False

    def _has_live_mount(self, item):
        mountpoints = item.get("mountpoints") or []
        if isinstance(mountpoints, str):
            mountpoints = [mountpoints]
        for mountpoint in mountpoints:
            if mountpoint and any(str(mountpoint).startswith(prefix) for prefix in LIVE_MOUNTS):
                return True
        for child in item.get("children") or []:
            if self._has_live_mount(child):
                return True
        return False

    def disk_mounted(self, disk):
        result = run(["lsblk", "-ln", "-o", "MOUNTPOINT", disk], timeout=20)
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            value = line.strip()
            if value.startswith("/"):
                return True
        return False

    def run_step(self, percent, message):
        self.step(percent, message)

    def install(self):
        self.check_environment()
        self.run_step(3, "Preparando instalación")
        self.unmount_disk()
        self.run_step(8, "Particionando el disco")
        if self.config.mode == "auto":
            self.partition_auto()
        else:
            self.partition_manual()
        self.run_step(24, "Formateando particiones")
        self.format_partitions()
        self.run_step(32, "Montando el sistema de archivos")
        self.mount_target()
        self.run_step(38, "Copiando el sistema Corte OS")
        self.copy_rootfs()
        self.mount_efi()
        self.run_step(58, "Configurando el sistema")
        self.configure_system()
        self.run_step(82, "Instalando el gestor de arranque GRUB")
        self.install_grub()
        self.run_step(92, "Actualizando initramfs")
        self.update_initramfs()
        self.run_step(97, "Finalizando")
        self.finish()
        self.run_step(100, "Instalación completada")
        return self.warnings

    def unmount_disk(self):
        result = run(["lsblk", "-ln", "-o", "PATH,MOUNTPOINT", self.config.disk], timeout=20)
        if result.returncode != 0:
            return
        mounts = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].strip():
                mounts.append(parts[1].strip())
        for mountpoint in sorted(mounts, reverse=True):
            res = run(["umount", "-R", mountpoint], timeout=60)
            if res.returncode != 0:
                raise InstallerError(f"No se pudo desmontar {mountpoint}: {res.stderr.strip()}")
        self.forced_command(["swapoff", "-a"], check=False)

    def partition_auto(self):
        disk = self.config.disk
        self.forced_command(["wipefs", "-a", disk])
        self.forced_command(["parted", "-s", disk, "mklabel", "gpt"])
        self.forced_command(["parted", "-s", disk, "mkpart", "bios-grub", "1MiB", "2MiB"])
        self.forced_command(["parted", "-s", disk, "set", "1", "bios_grub", "on"])
        self.forced_command(["parted", "-s", disk, "mkpart", "ESP", "fat32", "2MiB", "514MiB"])
        self.forced_command(["parted", "-s", disk, "set", "2", "esp", "on"])
        self.forced_command(["parted", "-s", disk, "mkpart", "CorteRoot", "ext4", "514MiB", "100%"])
        self.forced_command(["partprobe", disk], check=False)
        self.forced_command(["udevadm", "settle"], check=False)
        self.root_part = part_path(disk, 3)
        self.efi_part = part_path(disk, 2)
        self.wait_for_partitions()

    def partition_manual(self):
        self.root_part = self.config.root_partition
        self.efi_part = self.config.efi_partition
        if not self.efi_part:
            self.efi_part = self.find_efi_partition()
        if self.efi_part and self.root_part == self.efi_part:
            raise InstallerError("La partici?n ra?z y la EFI no pueden ser la misma.")
        for partition in (self.root_part, self.efi_part):
            if partition and not partition.startswith(self.config.disk):
                raise InstallerError(
                    f"La partici?n {partition} no pertenece al disco {self.config.disk}."
                )
        if self.efi_part:
            self.forced_command(["umount", "-R", self.efi_part], check=False)
            self.forced_command(["wipefs", "-a", self.efi_part])
        if self.root_part:
            self.forced_command(["umount", "-R", self.root_part], check=False)
            self.forced_command(["wipefs", "-a", self.root_part])

    def find_efi_partition(self):
        result = run(["lsblk", "-J", "-b", "-o", "PATH,FSTYPE,MOUNTPOINTS", self.config.disk], timeout=20)
        if result.returncode != 0:
            return ""
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ""
        for item in payload.get("blockdevices", []):
            for child in item.get("children") or []:
                if (child.get("fstype") or "").lower() in ("vfat", "fat32", "fat"):
                    return child.get("path", "")
        return ""

    def wait_for_partitions(self):
        for _ in range(50):
            if self.root_part and Path(self.root_part).exists() and self.efi_part and Path(self.efi_part).exists():
                return
            time.sleep(0.2)
        raise InstallerError("Las particiones no aparecieron después de particionar el disco.")

    def format_partitions(self):
        if not self.root_part or not Path(self.root_part).exists():
            raise InstallerError("No hay una partición raíz válida.")
        self.forced_command(["mkfs.ext4", "-F", "-L", "CORTE_ROOT", self.root_part])
        if self.efi_part:
            self.forced_command(["mkfs.vfat", "-F32", "-n", "CORTE_ESP", self.efi_part])

    def mount_target(self):
        if TARGET.exists():
            self.forced_command(["umount", "-R", str(TARGET)], check=False)
        TARGET.mkdir(parents=True, exist_ok=True)
        self.forced_command(["mount", "-o", "noatime", self.root_part, str(TARGET)])
        if not os.path.ismount(TARGET):
            raise InstallerError("No se pudo montar la partición raíz en /target.")

    def mount_efi(self):
        if not self.efi_part:
            return
        efi_target = TARGET / "boot/efi"
        efi_target.mkdir(parents=True, exist_ok=True)
        if not os.path.ismount(efi_target):
            self.forced_command(["mount", self.efi_part, str(efi_target)])

    def clear_target(self):
        if not os.path.ismount(TARGET):
            raise InstallerError("Se ha perdido el punto de montaje /target.")
        for child in TARGET.iterdir():
            if os.path.ismount(child):
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

    def copy_rootfs(self):
        squashfs = find_squashfs()
        if squashfs is None:
            raise InstallerError("No se encontró filesystem.squashfs en el medio live.")
        self.clear_target()
        source_mount = Path("/mnt/corte-source")
        source_mount.mkdir(parents=True, exist_ok=True)
        if os.path.ismount(source_mount):
            run(["umount", str(source_mount)], timeout=60, check=False)
        mounted = False
        try:
            result = run(
                ["mount", "-o", "loop,ro", "-t", "squashfs", str(squashfs), str(source_mount)],
                timeout=180,
            )
            if result.returncode == 0:
                mounted = True
                copy = run(
                    ["cp", "-a", f"{source_mount}/.", f"{TARGET}/"],
                    timeout=3600,
                )
                if copy.returncode != 0:
                    raise InstallerError(
                        f"No se pudo copiar el sistema: {(copy.stderr or copy.stdout).strip()}"
                    )
                return
            unsquashfs = shutil.which("unsquashfs")
            if unsquashfs:
                result = run(
                    [unsquashfs, "-f", "-d", str(TARGET), str(squashfs)],
                    timeout=3600,
                )
                if result.returncode != 0:
                    raise InstallerError(
                        f"No se pudo copiar el sistema: {(result.stderr or result.stdout).strip()}"
                    )
                return
            raise InstallerError(
                "No se pudo montar filesystem.squashfs y unsquashfs no está disponible. "
                f"Detalle: {(result.stderr or result.stdout).strip()}"
            )
        finally:
            if mounted:
                run(["umount", str(source_mount)], timeout=120, check=False)

    def configure_system(self):
        self.bind_mounts()
        try:
            config = self.config
            version_value = version()
            write_target("/etc/hostname", config.hostname + "\n")
            write_target(
                "/etc/hosts",
                "127.0.0.1 localhost\n"
                f"127.0.1.1 {config.hostname}\n"
                "::1 localhost ip6-localhost ip6-loopback\n"
                "ff02::1 ip6-allnodes\n"
                "ff02::2 ip6-allrouters\n",
            )
            write_target("/etc/corte/version", version_value + "\n")
            write_target(
                "/etc/corte/installed",
                f"version={version_value}\ninstalled_at={datetime.now().isoformat(timespec='seconds')}\n"
                f"disk={config.disk}\nuser={config.user}\n",
            )
            write_target("/etc/timezone", config.timezone + "\n")
            timezone_link = TARGET / "etc/localtime"
            if timezone_link.exists() or timezone_link.is_symlink():
                timezone_link.unlink()
            timezone_link.symlink_to(f"/usr/share/zoneinfo/{config.timezone}")

            locale = LANGUAGES[config.language]
            locale_gen = TARGET / "etc/locale.gen"
            existing = locale_gen.read_text(encoding="utf-8", errors="replace") if locale_gen.exists() else ""
            lines = []
            for line in existing.splitlines():
                if line.startswith("#") and ("es_ES.UTF-8" in line or "en_US.UTF-8" in line):
                    line = line.lstrip("# ")
                lines.append(line)
            for value in ("es_ES.UTF-8 UTF-8", "en_US.UTF-8 UTF-8"):
                if value not in lines:
                    lines.append(value)
            write_target("/etc/locale.gen", "\n".join(lines) + "\n")
            self.chroot(["locale-gen"], timeout=300)
            self.chroot(["update-locale", f"LANG={locale}", f"LC_ALL={locale}"], timeout=60)

            write_target(
                "/etc/default/keyboard",
                'XKBMODEL="pc105"\n'
                f'XKBLAYOUT="{config.keyboard}"\n'
                'XKBVARIANT=""\n'
                'XKBOPTIONS="grp:alt_shift_toggle"\n'
                'BACKSPACE="guess"\n',
            )

            self.manage_user()
            self.write_lightdm()
            self.write_fstab()
            self.write_grub_default()
            self.disable_live_services()
            self.cleanup_live_files()
            managed = run(
                ["systemctl", "--root=/target", "enable", "lightdm.service"], timeout=60
            )
            if managed.returncode != 0:
                raise InstallerError(
                    "No se pudo habilitar LightDM en el sistema instalado: "
                    f"{(managed.stderr or managed.stdout).strip()}"
                )
            run(
                ["systemctl", "--root=/target", "set-default", "graphical.target"],
                timeout=60,
                check=False,
            )
            run(["systemd-machine-id-setup", "--root=/target"], timeout=60, check=False)
        except Exception:
            raise

    def manage_user(self):
        config = self.config
        user = config.user
        fullname = config.full_name or user
        if not self.user_exists(user):
            self.chroot(["useradd", "-m", "-s", "/bin/bash", "-c", fullname, user], timeout=120)
        home = TARGET / "home" / user
        if not home.exists():
            skel = TARGET / "etc/skel"
            if skel.exists():
                shutil.copytree(skel, home)
            else:
                home.mkdir(parents=True, exist_ok=True)
        uid, gid = self.target_ids(user)
        if uid is not None:
            run(["chown", "-R", f"{uid}:{gid}", str(home)], timeout=120, check=False)
        self.chroot(
            ["usermod", "-aG", "sudo,audio,video,plugdev,netdev,cdrom", user],
            timeout=60,
        )
        result = self.chroot(
            ["chpasswd"],
            input_text=f"{user}:{config.password}\n",
            timeout=60,
        )
        if result.returncode != 0:
            raise InstallerError("No se pudo asignar la contraseña del usuario.")
        if user != "corte" and self.user_exists("corte"):
            self.chroot(["userdel", "-r", "corte"], timeout=120, check=False)
        if user == "corte":
            self.chroot(["usermod", "-aG", "sudo,audio,video,plugdev,netdev,cdrom", "corte"], timeout=60)

    def target_ids(self, user):
        passwd = TARGET / "etc/passwd"
        if not passwd.exists():
            return None, None
        for line in passwd.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[0] == user:
                return parts[2], parts[3]
        return None, None

    def user_exists(self, user):
        uid, _gid = self.target_ids(user)
        return uid is not None

    def write_lightdm(self):
        user = self.config.user
        autologin = f"autologin-user={user}\nautologin-user-timeout=0\n" if self.config.autologin else ""
        content = (
            "[Seat:*]\n"
            + autologin
            + "user-session=xfce\n"
            "greeter-session=lightdm-gtk-greeter\n"
            "greeter-hide-users=false\n"
            "allow-guest=false\n"
        )
        write_target("/etc/lightdm/lightdm.conf", content)
        write_target("/etc/lightdm/lightdm.conf.d/50-corte.conf", content)
        live_conf = TARGET / "etc/lightdm/lightdm.conf.d/01_live.conf"
        if live_conf.exists():
            live_conf.unlink()

    def write_fstab(self):
        self.root_uuid = uuid_of(self.root_part)
        root_spec = f"UUID={self.root_uuid}" if self.root_uuid else self.root_part
        lines = [
            f"{root_spec} / ext4 defaults,noatime 0 1",
        ]
        if self.efi_part:
            self.efi_uuid = uuid_of(self.efi_part)
            efi_spec = f"UUID={self.efi_uuid}" if self.efi_uuid else self.efi_part
            lines.append(f"{efi_spec} /boot/efi vfat umask=0077 0 1")
        swapfile = TARGET / "swapfile"
        try:
            self.forced_command(["fallocate", "-l", "1G", str(swapfile)])
            self.forced_command(["chmod", "600", str(swapfile)])
            self.forced_command(["mkswap", str(swapfile)])
            lines.append("/swapfile none swap sw 0 0")
        except InstallerError as exc:
            self.warnings.append(f"No se pudo crear swapfile: {exc}")
        write_target("/etc/fstab", "\n".join(lines) + "\n")

    def write_grub_default(self):
        write_target(
            "/etc/default/grub",
            'GRUB_DEFAULT=0\n'
            'GRUB_TIMEOUT=3\n'
            'GRUB_DISTRIBUTOR="Corte OS"\n'
            'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n'
            'GRUB_CMDLINE_LINUX=""\n'
            'GRUB_DISABLE_OS_PROBER=true\n'
            'GRUB_TERMINAL=console\n',
        )

    def disable_live_services(self):
        for service in (
            "corte-ci-install.service",
            "corte-live-ready.service",
        ):
            for wants in TARGET.glob(f"etc/systemd/system/*.wants/{service}"):
                wants.unlink(missing_ok=True)
        live_conf = TARGET / "etc/lightdm/lightdm.conf.d/01_live.conf"
        if live_conf.exists():
            live_conf.unlink()

    def cleanup_live_files(self):
        for path in (
            TARGET / "etc/sudoers.d/90-corte-live",
            TARGET / "etc/sudoers.d/live",
        ):
            if path.exists():
                path.unlink()
        for path in (TARGET / "var/lib/apt/lists").glob("*"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    def install_grub(self):
        disk = self.config.disk
        bios_error = ""
        efi_error = ""
        result = self.chroot(
            ["grub-install", "--target=i386-pc", "--recheck", disk],
            timeout=300,
            check=False,
        )
        if result.returncode == 0:
            self.grub_bios_ok = True
        else:
            bios_error = (result.stderr or result.stdout).strip()

        efi_result = self.chroot(
            [
                "grub-install",
                "--target=x86_64-efi",
                "--efi-directory=/boot/efi",
                "--bootloader-id=CorteOS",
                "--no-nvram",
                "--recheck",
            ],
            timeout=300,
            check=False,
        )
        if efi_result.returncode == 0:
            self.grub_efi_ok = True
            self.chroot(
                [
                    "grub-install",
                    "--target=x86_64-efi",
                    "--efi-directory=/boot/efi",
                    "--removable",
                    "--no-nvram",
                    "--recheck",
                ],
                timeout=300,
                check=False,
            )
        else:
            efi_error = (efi_result.stderr or efi_result.stdout).strip()

        if not self.grub_bios_ok and not self.grub_efi_ok:
            raise InstallerError(
                "No se pudo instalar GRUB por BIOS ni por UEFI.\n"
                f"BIOS: {bios_error}\nUEFI: {efi_error}"
            )
        if not self.grub_bios_ok:
            self.warnings.append(f"GRUB BIOS no se instaló: {bios_error}")
        if not self.grub_efi_ok:
            self.warnings.append(f"GRUB UEFI no se instaló: {efi_error}")

        result = self.chroot(["update-grub"], timeout=300, check=False)
        if result.returncode != 0:
            raise InstallerError(f"update-grub falló: {(result.stderr or result.stdout).strip()}")
        if self.grub_efi_ok:
            fallback_dir = TARGET / "boot/efi/EFI/BOOT"
            if fallback_dir.exists():
                self.log("Entrada EFI de respaldo instalada en EFI/BOOT.")

    def update_initramfs(self):
        result = self.chroot(["update-initramfs", "-u", "-k", "all"], timeout=900, check=False)
        if result.returncode != 0:
            raise InstallerError(f"No se pudo actualizar initramfs: {(result.stderr or result.stdout).strip()}")

    def finish(self):
        self.sync()
        self.unbind_mounts()
        self.unmount_target()
        if self.config.reboot:
            self.log("Reiniciando el equipo...")
            run(["sync"], timeout=60)
            run(["reboot", "-f"], timeout=30, check=False)

    def bind_mounts(self):
        for entry in ("dev", "dev/pts", "proc", "sys"):
            target = TARGET / entry
            target.mkdir(parents=True, exist_ok=True)
            if os.path.ismount(target):
                continue
            result = run(["mount", "--bind", f"/{entry}", str(target)], timeout=60)
            if result.returncode != 0:
                raise InstallerError(f"No se pudo enlazar /{entry}: {result.stderr.strip()}")

    def unbind_mounts(self):
        for entry in ("sys", "proc", "dev/pts", "dev"):
            target = TARGET / entry
            if os.path.ismount(target):
                run(["umount", "-l", str(target)], timeout=60, check=False)

    def unmount_target(self):
        for target in (
            TARGET / "boot/efi",
            TARGET / "run",
            TARGET / "sys",
            TARGET / "proc",
            TARGET / "dev/pts",
            TARGET / "dev",
            TARGET,
        ):
            if os.path.ismount(target):
                run(["umount", "-l", str(target)], timeout=120, check=False)

    def sync(self):
        run(["sync"], timeout=120, check=False)

    def chroot(self, args, input_text=None, timeout=300, check=True):
        command = ["chroot", str(TARGET), *args]
        result = run(command, input_text=input_text, timeout=timeout)
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise InstallerError(f"Falló {' '.join(args)}: {detail}")
        return result

    def forced_command(self, args, check=True):
        result = run(args, timeout=3600)
        if check and result.returncode != 0:
            raise InstallerError(f"Falló {' '.join(args)}: {(result.stderr or result.stdout).strip()}")
        return result


def is_safe_disk(disk):
    if disk.removable:
        return True
    if disk.tran.lower() in ("usb", "virtio"):
        return True
    return bool(SAFE_MODELS.search(disk.model or ""))


def run(args, input_text=None, timeout=None, check=False):
    return subprocess.run(
        list(args),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def part_path(disk, number):
    if re.search(r"\d$", disk):
        return f"{disk}p{number}"
    return f"{disk}{number}"


def uuid_of(partition):
    result = run(["blkid", "-s", "UUID", "-o", "value", partition], timeout=20)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def live_media_device():
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 2:
                    continue
                source, mountpoint = parts[0], parts[1]
                if mountpoint.rstrip("/") in [item.rstrip("/") for item in LIVE_MOUNTS]:
                    if not source.startswith("/dev/"):
                        continue
                    parent = run(
                        ["lsblk", "-no", "PKNAME", source], timeout=10
                    ).stdout.strip()
                    return f"/dev/{parent}" if parent else source
    except OSError:
        pass
    return ""


def list_disks():
    result = run(
        [
            "lsblk",
            "-J",
            "-b",
            "-o",
            "NAME,PATH,TYPE,SIZE,MODEL,TRAN,RM,ROTA,MOUNTPOINTS",
        ],
        timeout=20,
    )
    if result.returncode != 0:
        raise InstallerError("No se pudo ejecutar lsblk.")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InstallerError("lsblk devolvió datos no válidos.") from exc
    live = live_media_device()
    disks = []
    for item in payload.get("blockdevices", []):
        if item.get("type") != "disk":
            continue
        path = item.get("path") or f"/dev/{item.get('name')}"
        if item.get("name", "").startswith(("loop", "zram", "ram")):
            continue
        mountpoints = item.get("mountpoints") or []
        if isinstance(mountpoints, str):
            mountpoints = [mountpoints]
        disk = Disk(
            name=item.get("name", ""),
            path=path,
            size=int(item.get("size") or 0),
            model=(item.get("model") or "").strip(),
            tran=(item.get("tran") or "").strip(),
            removable=bool(item.get("rm")),
            rota=bool(item.get("rota")),
            mountpoints=[m for m in mountpoints if m],
            live=(path == live),
        )
        disks.append(disk)
    return disks


def find_squashfs():
    candidates = [
        Path("/run/live/medium/live/filesystem.squashfs"),
        Path("/lib/live/mount/medium/live/filesystem.squashfs"),
        Path("/run/live/rootfs/filesystem.squashfs"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for base in (Path("/run/live"), Path("/lib/live")):
        if base.exists():
            matches = list(base.rglob("filesystem.squashfs"))
            if matches:
                return matches[0]
    return None


def write_target(relative, content):
    path = TARGET / relative.lstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
