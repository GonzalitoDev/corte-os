import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ..common import paths, ui  # noqa: E402
from ..common.system import is_live  # noqa: E402


class ManualWindow:
    def __init__(self, parent, path):
        self.window = Gtk.Window()
        self.window.set_title(f"{path.name} — Corte OS")
        self.window.set_default_size(860, 680)
        self.window.set_transient_for(parent)
        self.window.set_titlebar(ui.header("Manual de Corte OS", path.name, "corte-welcome"))
        text = Gtk.TextView()
        text.set_editable(False)
        text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text.set_left_margin(20)
        text.set_right_margin(20)
        text.set_top_margin(16)
        text.set_bottom_margin(16)
        text.get_style_context().add_class("corte-code")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            content = f"No se pudo leer el manual:\n{exc}"
        text.get_buffer().set_text(content)
        self.window.add(ui.scrolled(text))
        self.window.show_all()


class WelcomeApp:
    def __init__(self, force=False):
        self.force = force
        self.window = ui.window("Bienvenido a Corte OS", "corte-welcome", (760, 600))
        self.window.set_resizable(False)
        self.window.set_titlebar(ui.header("Bienvenido a Corte OS", "Tu sistema operativo ligero", "corte-welcome"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(24)
        self.window.add(box)

        logo_path = Path("/usr/share/corte/logo.svg")
        if logo_path.exists():
            logo = Gtk.Image.new_from_file(str(logo_path))
            logo.set_pixel_size(96)
        else:
            logo = Gtk.Image.new_from_icon_name("corte-welcome", Gtk.IconSize.DIALOG)
        box.pack_start(logo, False, False, 0)

        title = ui.label("CORTE OS", "corte-app-title", xalign=0.5)
        title.set_halign(Gtk.Align.CENTER)
        box.pack_start(title, False, False, 0)
        subtitle = ui.label(f"Versión {paths.version()} · Base Debian 12", "corte-hint", xalign=0.5)
        subtitle.set_halign(Gtk.Align.CENTER)
        box.pack_start(subtitle, False, False, 0)

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hero.set_border_width(14)
        hero.get_style_context().add_class("corte-banner")
        hero.pack_start(
            ui.label(
                "Corte OS está listo para usar. Puedes explorar el escritorio en modo live "
                "o instalar el sistema en el disco virtual de esta máquina.",
                wrap=True,
            ),
            False,
            False,
            0,
        )
        hero.pack_start(
            ui.label(
                "La instalación solo modifica el disco que elijas. No toca los discos del equipo anfitrión.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        box.pack_start(hero, False, False, 0)

        actions = Gtk.Grid()
        actions.set_column_spacing(10)
        actions.set_row_spacing(10)
        actions.set_column_homogeneous(True)
        actions.attach(ui.button("Abrir Corte Installer", self.open_installer, "corte-installer", "suggested-action"), 0, 0, 1, 1)
        actions.attach(ui.button("Explorar archivos", lambda: self.launch("files"), "corte-files"), 1, 0, 1, 1)
        actions.attach(ui.button("Ver ajustes", lambda: self.launch("settings"), "corte-settings"), 0, 1, 1, 1)
        actions.attach(ui.button("Manual de usuario", self.open_manual, "help-browser-symbolic"), 1, 1, 1, 1)
        box.pack_start(actions, False, False, 0)

        tips = ui.label(
            "Consejos\n"
            "· Super + Espacio abre el menú de aplicaciones.\n"
            "· Super + E abre Corte Files; Super + Return abre la terminal.\n"
            "· Todas las aplicaciones funcionan sin Internet. El navegador y Corte Store "
            "necesitan red para contenido externo.\n"
            "· En modo live, los cambios no se guardan al reiniciar. Instala para conservarlos.",
            "corte-hint",
            True,
        )
        box.pack_start(tips, False, False, 0)

        self.remember = Gtk.CheckButton(label="No volver a mostrar al iniciar sesión")
        self.remember.set_active(not self.force)
        box.pack_start(self.remember, False, False, 0)

        close = ui.button("Continuar al escritorio", self.close, "go-next-symbolic")
        box.pack_start(close, False, False, 0)

        self.window.connect("destroy", self.on_destroy)
        self.window.show_all()

    def launch(self, app):
        subprocess.Popen(["corte", app])

    def open_installer(self):
        if not is_live():
            ui.info(self.window, "El instalador solo está disponible desde la ISO live.")
            return
        subprocess.Popen(["corte-installer"])

    def open_manual(self):
        path = paths.docs_dir() / "USER-MANUAL.md"
        ManualWindow(self.window, path)

    def close(self):
        self.window.destroy()

    def on_destroy(self, *_args):
        if self.remember.get_active():
            try:
                (paths.config_dir() / "welcome-seen").write_text("1\n", encoding="utf-8")
            except OSError:
                pass
        Gtk.main_quit()

    def run(self):
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    force = "--force" in argv
    marker = paths.config_dir() / "welcome-seen"
    if marker.exists() and not force:
        return 0
    ui.init_theme()
    app = WelcomeApp(force)
    app.run()
    return 0
