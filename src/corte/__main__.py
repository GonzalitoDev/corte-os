import importlib
import sys

from gi.repository import GLib

from .common.paths import developer, version

APPS = {
    "files": "corte.apps.files",
    "terminal": "corte.apps.terminal",
    "notes": "corte.apps.notes",
    "calculator": "corte.apps.calculator",
    "monitor": "corte.apps.monitor",
    "settings": "corte.apps.settings",
    "store": "corte.apps.store",
    "browser": "corte.apps.browser",
    "media": "corte.apps.media",
    "security": "corte.apps.security",
    "notifications": "corte.apps.notifications",
    "welcome": "corte.apps.welcome",
}

HELP = """Corte OS

Desarrollado por gonzita.

Uso:
  corte <aplicacion> [argumentos]
  corte --help
  corte --version

Aplicaciones:
  files          Explorador de archivos
  terminal       Terminal Linux
  notes          Bloc de notas
  calculator     Calculadora
  monitor        Monitor del sistema
  settings       Configuración
  store          Tienda de aplicaciones
  browser        Navegador web
  media          Reproductor multimedia
  security       Herramientas de seguridad
  notifications  Centro de notificaciones
  welcome        Bienvenida
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP, end="")
        return 0

    if argv[0] in ("-v", "--version", "version"):
        print(f"Corte OS {version()} - desarrollador: {developer()}")
        return 0

    name = argv.pop(0)
    module_name = APPS.get(name)
    if module_name is None:
        print(f"corte: aplicación desconocida: {name}", file=sys.stderr)
        print("Ejecuta 'corte --help' para ver las aplicaciones disponibles.", file=sys.stderr)
        return 2

    GLib.set_prgname(f"corte-{name}")
    module = importlib.import_module(module_name)
    result = module.main(argv)
    return 0 if result is None else int(result)


if __name__ == "__main__":
    raise SystemExit(main())
