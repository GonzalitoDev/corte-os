import argparse
import dataclasses
import json
import logging
import sys
import traceback

from ..common.paths import version
from .backend import InstallConfig, Installer, InstallerError, list_disks


def build_parser():
    parser = argparse.ArgumentParser(
        prog="corte-installer",
        description="Instalador de Corte OS. Sin argumentos abre la interfaz gráfica.",
    )
    parser.add_argument("--version", action="version", version=f"Corte Installer {version()}")
    parser.add_argument("--list-disks", action="store_true", help="Muestra los discos detectados en JSON.")
    parser.add_argument("--auto", action="store_true", help="Instalación automática sin interfaz.")
    parser.add_argument("--disk", help="Disco destino, por ejemplo /dev/vda.")
    parser.add_argument("--user", default="corte", help="Usuario a crear.")
    parser.add_argument("--password", default="", help="Contraseña del usuario.")
    parser.add_argument("--full-name", default="", help="Nombre completo del usuario.")
    parser.add_argument("--hostname", default="corte-os", help="Nombre del equipo.")
    parser.add_argument("--language", default="es", choices=["es", "en"], help="Idioma del sistema.")
    parser.add_argument("--keyboard", default="es", help="Distribución de teclado.")
    parser.add_argument("--timezone", default="Europe/Madrid", help="Zona horaria IANA.")
    parser.add_argument("--mode", default="auto", choices=["auto", "manual"], help="Modo de particionado.")
    parser.add_argument("--manual-root", default="", help="Partición raíz para el modo manual.")
    parser.add_argument("--manual-efi", default="", help="Partición EFI para el modo manual.")
    parser.add_argument("--no-autologin", action="store_true", help="Desactivar el inicio de sesión automático.")
    parser.add_argument("--reboot", action="store_true", help="Reiniciar al terminar.")
    parser.add_argument("--allow-any-disk", action="store_true", help="Permitir discos no verificados (avanzado).")
    return parser


def setup_logging():
    logger = logging.getLogger("corte-installer")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    try:
        file_handler = logging.FileHandler("/var/log/corte-installer.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass
    return logger


def run_auto(args):
    logger = setup_logging()
    if not args.disk:
        print("CORTE_INSTALL_ERROR falta --disk", flush=True)
        return 2
    config = InstallConfig(
        disk=args.disk,
        user=args.user,
        password=args.password,
        full_name=args.full_name,
        hostname=args.hostname,
        language=args.language,
        keyboard=args.keyboard,
        timezone=args.timezone,
        mode=args.mode,
        root_partition=args.manual_root,
        efi_partition=args.manual_efi,
        autologin=not args.no_autologin,
        reboot=args.reboot,
        allow_any_disk=args.allow_any_disk,
    )

    def progress(percent, message):
        print(f"[{percent:3d}%] {message}", flush=True)

    def log(message):
        logger.info(message)

    installer = Installer(config, progress=progress, log=log)
    try:
        warnings = installer.install()
    except InstallerError as exc:
        logger.error("Instalación abortada: %s", exc)
        print(f"CORTE_INSTALL_ERROR {exc}", flush=True)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Error inesperado:\n%s", traceback.format_exc())
        print(f"CORTE_INSTALL_ERROR {exc}", flush=True)
        return 1

    for warning in warnings:
        logger.warning(warning)
        print(f"AVISO: {warning}", flush=True)
    print("CORTE_INSTALL_OK", flush=True)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_disks:
        try:
            disks = [dataclasses.asdict(disk) for disk in list_disks()]
        except InstallerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(disks, indent=2, ensure_ascii=False))
        return 0

    if args.auto:
        return run_auto(args)

    from .gui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
