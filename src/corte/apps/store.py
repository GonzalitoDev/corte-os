import subprocess

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ..common import ui  # noqa: E402
from ..common.system import is_live, run, run_privileged  # noqa: E402

CATALOG = [
    {
        "id": "files",
        "name": "Corte Files",
        "description": "Explorador de archivos con papelera, copiar, mover y renombrar.",
        "category": "Incluidas",
        "icon": "corte-files",
        "included": True,
        "command": ["corte", "files"],
    },
    {
        "id": "browser",
        "name": "Corte Browser",
        "description": "Navegador WebKitGTK con página de inicio local.",
        "category": "Incluidas",
        "icon": "corte-browser",
        "included": True,
        "command": ["corte", "browser"],
    },
    {
        "id": "terminal",
        "name": "Corte Terminal",
        "description": "Terminal VTE con pestañas y shell Linux real.",
        "category": "Incluidas",
        "icon": "corte-terminal",
        "included": True,
        "command": ["corte", "terminal"],
    },
    {
        "id": "notes",
        "name": "Corte Notes",
        "description": "Notas guardadas en SQLite con búsqueda y autoguardado.",
        "category": "Incluidas",
        "icon": "corte-notes",
        "included": True,
        "command": ["corte", "notes"],
    },
    {
        "id": "calculator",
        "name": "Corte Calculator",
        "description": "Calculadora con historial persistente.",
        "category": "Incluidas",
        "icon": "corte-calculator",
        "included": True,
        "command": ["corte", "calculator"],
    },
    {
        "id": "monitor",
        "name": "Corte Monitor",
        "description": "CPU, RAM, discos y procesos en tiempo real.",
        "category": "Incluidas",
        "icon": "corte-monitor",
        "included": True,
        "command": ["corte", "monitor"],
    },
    {
        "id": "media",
        "name": "Corte Media",
        "description": "Reproductor GStreamer para audio y vídeo local.",
        "category": "Incluidas",
        "icon": "corte-media",
        "included": True,
        "command": ["corte", "media"],
    },
    {
        "id": "security",
        "name": "Corte Security",
        "description": "Firewall, puertos, contraseñas y revisión del sistema.",
        "category": "Incluidas",
        "icon": "corte-security",
        "included": True,
        "command": ["corte", "security"],
    },
    {
        "id": "settings",
        "name": "Corte Settings",
        "description": "Apariencia, pantalla, sonido, red, usuarios e información.",
        "category": "Incluidas",
        "icon": "corte-settings",
        "included": True,
        "command": ["corte", "settings"],
    },
    {
        "id": "notifications",
        "name": "Corte Notifications",
        "description": "Centro de notificaciones con historial de dunst.",
        "category": "Incluidas",
        "icon": "corte-notifications",
        "included": True,
        "command": ["corte", "notifications"],
    },
    {
        "id": "firefox",
        "name": "Firefox ESR",
        "description": "Navegador web completo de Mozilla con soporte extendido.",
        "category": "Internet",
        "package": "firefox-esr",
        "icon": "firefox-esr",
        "size": "≈ 70 MB",
        "command": ["firefox-esr"],
    },
    {
        "id": "gimp",
        "name": "GIMP",
        "description": "Editor de imágenes y fotografía avanzado.",
        "category": "Creatividad",
        "package": "gimp",
        "icon": "gimp",
        "size": "≈ 120 MB",
        "command": ["gimp"],
    },
    {
        "id": "libreoffice",
        "name": "LibreOffice",
        "description": "Suite de oficina: documentos, hojas de cálculo y presentaciones.",
        "category": "Productividad",
        "package": "libreoffice",
        "icon": "libreoffice-startcenter",
        "size": "≈ 400 MB",
        "command": ["libreoffice"],
    },
    {
        "id": "vlc",
        "name": "VLC",
        "description": "Reproductor multimedia con códecs adicionales.",
        "category": "Multimedia",
        "package": "vlc",
        "icon": "vlc",
        "size": "≈ 80 MB",
        "command": ["vlc"],
    },
    {
        "id": "htop",
        "name": "htop",
        "description": "Monitor de procesos interactivo para la terminal.",
        "category": "Sistema",
        "package": "htop",
        "icon": "utilities-system-monitor",
        "size": "≈ 1 MB",
    },
    {
        "id": "neofetch",
        "name": "neofetch",
        "description": "Información del sistema en la terminal.",
        "category": "Sistema",
        "package": "neofetch",
        "icon": "utilities-terminal",
        "size": "≈ 1 MB",
    },
    {
        "id": "clamav",
        "name": "ClamAV",
        "description": "Antivirus de código abierto con base de firmas local.",
        "category": "Seguridad",
        "package": "clamav",
        "icon": "security-high",
        "size": "≈ 300 MB con firmas",
    },
    {
        "id": "timeshift",
        "name": "Timeshift",
        "description": "Copias de seguridad y restauración del sistema.",
        "category": "Sistema",
        "package": "timeshift",
        "icon": "document-save",
        "size": "≈ 40 MB",
        "command": ["timeshift-gtk"],
    },
    {
        "id": "synaptic",
        "name": "Synaptic",
        "description": "Gestor gráfico avanzado de paquetes Debian.",
        "category": "Sistema",
        "package": "synaptic",
        "icon": "system-software-install",
        "size": "≈ 10 MB",
        "command": ["synaptic"],
    },
]


def package_installed(package):
    result = run(["dpkg-query", "-W", "-f=${Status}", package])
    return result.returncode == 0 and "install ok installed" in result.stdout


class StoreApp:
    def __init__(self):
        self.window = ui.window("Corte Store", "corte-store", (1120, 760))
        self.window.set_titlebar(ui.header("Corte Store", "Aplicaciones incluidas y paquetes Debian", "corte-store"))

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_border_width(12)
        toolbar.get_style_context().add_class("corte-toolbar")
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Buscar aplicaciones...")
        self.search.connect("search-changed", lambda *_: self.rebuild())
        toolbar.pack_start(self.search, True, True, 0)
        self.category = Gtk.ComboBoxText()
        for category in ["Todas", "Incluidas", "Internet", "Multimedia", "Productividad", "Creatividad", "Sistema", "Seguridad"]:
            self.category.append_text(category)
        self.category.set_active(0)
        self.category.connect("changed", lambda *_: self.rebuild())
        toolbar.pack_start(self.category, False, False, 0)
        toolbar.pack_start(ui.button("Actualizar lista", self.update_index, "view-refresh-symbolic"), False, False, 0)
        root.pack_start(toolbar, False, False, 0)

        if is_live():
            banner = ui.label(
                "Modo live: las aplicaciones incluidas funcionan sin conexión. "
                "Los paquetes opcionales requieren Internet y no persisten al reiniciar.",
                "corte-banner",
                True,
            )
            banner.set_border_width(10)
            root.pack_start(banner, False, False, 0)

        self.scroller = ui.scrolled(Gtk.Box())
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(3)
        self.flow.set_row_spacing(12)
        self.flow.set_column_spacing(12)
        self.flow.set_border_width(14)
        self.scroller.remove(self.scroller.get_child())
        self.scroller.add(self.flow)
        root.pack_start(self.scroller, True, True, 0)

        self.status = ui.label("", "corte-hint")
        self.status.set_border_width(8)
        root.pack_start(self.status, False, False, 0)

        self.installed_cache = {}
        self.rebuild()
        self.window.connect("destroy", Gtk.main_quit)
        self.window.show_all()

    def rebuild(self):
        for child in self.flow.get_children():
            self.flow.remove(child)
        query = self.search.get_text().strip().lower()
        category = self.category.get_active_text()
        shown = 0
        for entry in CATALOG:
            if query and query not in entry["name"].lower() and query not in entry["description"].lower():
                continue
            if category not in (None, "Todas") and entry["category"] != category:
                continue
            self.flow.add(self.build_card(entry))
            shown += 1
        if shown == 0:
            self.flow.add(ui.label("No hay aplicaciones que coincidan.", "corte-empty"))
        self.flow.show_all()
        self.status.set_text(f"{shown} aplicación(es) · catálogo local de Corte OS")

    def build_card(self, entry):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_border_width(14)
        card.get_style_context().add_class("corte-stat")
        card.set_size_request(300, -1)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name(entry.get("icon", "application-x-executable"), Gtk.IconSize.DIALOG)
        icon.set_pixel_size(44)
        top.pack_start(icon, False, False, 0)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text.pack_start(ui.label(entry["name"], "corte-row-title"), False, False, 0)
        text.pack_start(ui.label(entry["category"], "corte-hint"), False, False, 0)
        top.pack_start(text, True, True, 0)
        card.pack_start(top, False, False, 0)

        description = ui.label(entry["description"], "corte-hint", True)
        description.set_size_request(270, -1)
        card.pack_start(description, False, False, 0)

        if entry.get("included"):
            card.pack_start(ui.label("Incluida en Corte OS", "corte-pill"), False, False, 0)
            action = ui.button("Abrir", lambda _b, e=entry: self.open_entry(e), "media-playback-start-symbolic")
            card.pack_end(action, False, False, 0)
            return card

        package = entry["package"]
        installed = self.installed_cache.get(package)
        if installed is None:
            installed = package_installed(package)
            self.installed_cache[package] = installed
        info = ui.label(
            f"{entry.get('size', '')} · {'Instalado' if installed else 'No instalado'}",
            "corte-hint",
        )
        card.pack_start(info, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        if installed:
            if entry.get("command"):
                row.pack_start(ui.button("Abrir", lambda _b, e=entry: self.open_entry(e), "media-playback-start-symbolic"), False, False, 0)
            row.pack_start(ui.button("Desinstalar", lambda _b, e=entry: self.remove_entry(e), "user-trash-symbolic", "destructive-action"), False, False, 0)
        else:
            row.pack_start(ui.button("Instalar", lambda _b, e=entry: self.install_entry(e), "document-save-symbolic", "suggested-action"), False, False, 0)
        card.pack_end(row, False, False, 0)
        return card

    def open_entry(self, entry):
        command = entry.get("command")
        if not command:
            ui.info(self.window, "Esta aplicación no define un comando de apertura. Ábrela desde el menú del sistema.")
            return
        try:
            subprocess.Popen(command)
        except OSError as exc:
            ui.error(self.window, str(exc), "No se pudo abrir la aplicación")

    def progress_dialog(self, title, message):
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.set_default_size(460, 130)
        content = dialog.get_content_area()
        content.set_border_width(18)
        content.set_spacing(10)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spinner = Gtk.Spinner()
        spinner.start()
        box.pack_start(spinner, False, False, 0)
        box.pack_start(ui.label(message, wrap=True), True, True, 0)
        content.add(box)
        dialog.show_all()
        return dialog

    def install_entry(self, entry):
        if not ui.confirm(
            self.window,
            f"Se instalará {entry['name']} desde los repositorios de Debian. "
            "Se necesita conexión a Internet y permisos de administrador.",
            "Instalar aplicación",
        ):
            return
        dialog = self.progress_dialog("Instalando", f"Instalando {entry['name']}...")
        command = ["apt-get", "install", "-y", entry["package"]]

        def work():
            return run_privileged(command, timeout=1800)

        def done(result):
            dialog.destroy()
            if result.returncode == 0:
                self.installed_cache.pop(entry["package"], None)
                ui.notify("Aplicación instalada", entry["name"], "normal", entry.get("icon", "corte-store"))
                self.rebuild()
            else:
                ui.error(
                    self.window,
                    (result.stderr or result.stdout or "apt-get devolvió un error.").strip(),
                    "No se pudo instalar",
                )

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "No se pudo instalar")

        ui.run_async(work, done, failed)

    def remove_entry(self, entry):
        if not ui.confirm(
            self.window,
            f"¿Desinstalar {entry['name']}? Los archivos personales no se eliminan.",
            "Desinstalar aplicación",
            True,
        ):
            return
        dialog = self.progress_dialog("Desinstalando", f"Desinstalando {entry['name']}...")
        command = ["apt-get", "remove", "-y", entry["package"]]

        def work():
            return run_privileged(command, timeout=1800)

        def done(result):
            dialog.destroy()
            if result.returncode == 0:
                self.installed_cache.pop(entry["package"], None)
                self.rebuild()
            else:
                ui.error(
                    self.window,
                    (result.stderr or result.stdout or "apt-get devolvió un error.").strip(),
                    "No se pudo desinstalar",
                )

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "No se pudo desinstalar")

        ui.run_async(work, done, failed)

    def update_index(self):
        dialog = self.progress_dialog("Actualizando", "Actualizando índices de paquetes Debian...")

        def work():
            return run_privileged(["apt-get", "update"], timeout=900)

        def done(result):
            dialog.destroy()
            if result.returncode == 0:
                self.installed_cache.clear()
                self.status.set_text("Índices actualizados.")
                self.rebuild()
            else:
                ui.error(
                    self.window,
                    (result.stderr or result.stdout or "apt-get update devolvió un error.").strip(),
                    "No se pudo actualizar",
                )

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "No se pudo actualizar")

        ui.run_async(work, done, failed)

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = StoreApp()
    app.run()
    return 0
