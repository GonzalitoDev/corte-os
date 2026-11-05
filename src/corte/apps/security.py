import getpass
import os
import re
import secrets
import string

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from ..common import ui  # noqa: E402
from ..common.system import run, run_privileged, which  # noqa: E402

COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345",
    "1234", "111111", "1234567", "dragon", "123123", "baseball",
    "abc123", "football", "monkey", "letmein", "shadow", "master",
    "corte", "corteos", "admin", "root", "contraseña", "hola123",
}


def password_strength(password):
    score = 0
    notes = []
    if len(password) >= 8:
        score += 1
    else:
        notes.append("usa al menos 8 caracteres")
    if len(password) >= 14:
        score += 1
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    else:
        notes.append("combina mayúsculas y minúsculas")
    if re.search(r"\d", password):
        score += 1
    else:
        notes.append("incluye números")
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    else:
        notes.append("incluye símbolos")
    if password.lower() in COMMON_PASSWORDS or password.lower().strip() == "":
        score = 0
        notes = ["esta contraseña es demasiado común"]
    if re.search(r"(.)\1{2,}", password):
        notes.append("evita caracteres repetidos")
        score = max(0, score - 1)
    if re.search(r"(123|abc|qwe|asd)", password.lower()):
        notes.append("evita secuencias predecibles")
        score = max(0, score - 1)
    score = max(0, min(5, score))
    labels = ["Muy débil", "Débil", "Aceptable", "Buena", "Fuerte", "Excelente"]
    return score, labels[score], notes


class SecurityApp:
    def __init__(self):
        self.firewall_active = None
        self.updates_count = None
        self.clamav_installed = bool(which("clamscan"))
        self.suid_files = None

        self.window = ui.window("Corte Security", "corte-security", (1080, 760))
        self.window.set_titlebar(ui.header("Corte Security", "Revisión local de seguridad", "corte-security"))

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        self.window.add(notebook)

        self.overview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.overview.set_border_width(16)
        notebook.append_page(ui.scrolled(self.overview), Gtk.Label(label="Resumen"))

        self.score_label = ui.label("—", "corte-app-title")
        self.score_detail = ui.label("", "corte-hint", True)
        banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        banner.set_border_width(16)
        banner.get_style_context().add_class("corte-banner")
        banner.pack_start(ui.label("Estado de seguridad", "corte-section-title"), False, False, 0)
        banner.pack_start(self.score_label, False, False, 0)
        banner.pack_start(self.score_detail, False, False, 0)
        self.overview.pack_start(banner, False, False, 0)

        self.checks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.overview.pack_start(self.checks_box, False, False, 0)
        self.overview.pack_start(
            ui.button("Volver a comprobar", self.refresh_overview, "view-refresh-symbolic"),
            False,
            False,
            0,
        )

        self.build_firewall(notebook)
        self.build_ports(notebook)
        self.build_password(notebook)
        self.build_system(notebook)

        self.window.connect("destroy", Gtk.main_quit)
        self.window.show_all()
        self.refresh_overview()
        self.refresh_firewall()
        self.refresh_ports()

    def build_firewall(self, notebook):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        notebook.append_page(ui.scrolled(box), Gtk.Label(label="Firewall"))
        box.pack_start(ui.label("Cortafuegos UFW", "corte-section-title"), False, False, 0)
        self.firewall_status = ui.label("Comprobando...", "corte-hint", True)
        box.pack_start(self.firewall_status, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Activar", lambda: self.set_firewall(True), "security-high-symbolic", "suggested-action"), False, False, 0)
        row.pack_start(ui.button("Desactivar", lambda: self.set_firewall(False), "security-low-symbolic", "destructive-action"), False, False, 0)
        row.pack_start(ui.button("Actualizar", lambda: self.refresh_firewall(True), "view-refresh-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)
        self.firewall_rules = Gtk.TextView()
        self.firewall_rules.set_editable(False)
        self.firewall_rules.get_style_context().add_class("corte-code")
        box.pack_start(ui.scrolled(self.firewall_rules), True, True, 0)

    def refresh_firewall(self, authorize=False):
        if authorize:
            result = run_privileged(["ufw", "status", "verbose"], timeout=20)
        else:
            result = run(["sudo", "-n", "ufw", "status", "verbose"], timeout=20)
        if result.returncode != 0:
            self.firewall_status.set_text(
                "No se pudo consultar UFW. En el sistema live se usa sudo sin contraseña; "
                "en el sistema instalado se pedirá autorización."
            )
            self.firewall_active = None
            return
        self.firewall_status.set_text(result.stdout.strip().splitlines()[0] if result.stdout.strip() else "Sin salida")
        self.firewall_active = "Status: active" in result.stdout
        buffer = self.firewall_rules.get_buffer()
        buffer.set_text(result.stdout)
        self.update_overview_checks()

    def set_firewall(self, enabled):
        if not ui.confirm(
            self.window,
            f"¿{'Activar' if enabled else 'Desactivar'} el cortafuegos UFW?",
            "Cortafuegos",
            not enabled,
        ):
            return
        command = ["ufw", "--force", "enable"] if enabled else ["ufw", "disable"]
        result = run_privileged(command, timeout=60)
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip() or result.stdout.strip(), "No se pudo cambiar UFW")
        self.refresh_firewall(True)
        self.refresh_overview()

    def build_ports(self, notebook):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(14)
        notebook.append_page(box, Gtk.Label(label="Puertos"))
        box.pack_start(ui.label("Puertos en escucha", "corte-section-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Lista obtenida con 'ss -tulpn'. Algunos nombres de proceso pueden requerir permisos de administrador.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        self.port_store = Gtk.ListStore(str, str, str, str)
        tree = Gtk.TreeView(model=self.port_store)
        for title, index in (("Proto", 0), ("Local", 1), ("Estado", 2), ("Proceso", 3)):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            tree.append_column(column)
        box.pack_start(ui.scrolled(tree, True), True, True, 0)
        box.pack_start(ui.button("Actualizar puertos", self.refresh_ports, "view-refresh-symbolic"), False, False, 0)

    def refresh_ports(self):
        self.port_store.clear()
        result = run(["ss", "-tulpn"])
        if result.returncode != 0:
            self.port_store.append(["—", "ss no disponible", "—", "—"])
            return
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue
            proto = parts[0]
            local = parts[4]
            state = parts[1] if len(parts) > 5 else "LISTEN"
            process = " ".join(parts[6:]) if len(parts) > 6 else "—"
            self.port_store.append([proto, local, state, process])

    def build_password(self, notebook):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(18)
        notebook.append_page(ui.scrolled(box), Gtk.Label(label="Contraseñas"))
        box.pack_start(ui.label("Analizador de contraseñas", "corte-section-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "El análisis se hace en memoria y no se guarda ni se envía a ningún sitio.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password_entry.set_placeholder_text("Escribe una contraseña")
        self.password_entry.connect("changed", self.on_password_changed)
        box.pack_start(self.password_entry, False, False, 0)
        self.strength_bar = Gtk.ProgressBar()
        box.pack_start(self.strength_bar, False, False, 0)
        self.strength_label = ui.label("—", "corte-hint", True)
        box.pack_start(self.strength_label, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Generar contraseña", self.generate_password, "dialog-password-symbolic"), False, False, 0)
        row.pack_start(ui.button("Copiar", self.copy_password, "edit-copy-symbolic"), False, False, 0)
        row.pack_start(ui.button("Cambiar mi contraseña", self.change_my_password, "system-lock-screen-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)

    def on_password_changed(self, entry):
        password = entry.get_text()
        if not password:
            self.strength_bar.set_fraction(0)
            self.strength_label.set_text("—")
            return
        score, label, notes = password_strength(password)
        self.strength_bar.set_fraction(score / 5)
        text = f"{label}"
        if notes:
            text += " · " + "; ".join(notes)
        self.strength_label.set_text(text)

    def generate_password(self):
        alphabet = string.ascii_letters + string.digits + "!@#$%&*+-_=?"
        password = "".join(secrets.choice(alphabet) for _ in range(20))
        while not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password) and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password)):
            password = "".join(secrets.choice(alphabet) for _ in range(20))
        self.password_entry.set_text(password)
        self.password_entry.set_visibility(True)

    def copy_password(self):
        password = self.password_entry.get_text()
        if not password:
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(password, -1)
        clipboard.store()
        ui.notify("Contraseña copiada", "Se borrará del portapapeles al cerrar la sesión.", "low", "corte-security")

    def change_my_password(self):
        user = getpass.getuser()
        dialog = Gtk.Dialog(title="Cambiar contraseña", transient_for=self.window, modal=True)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Cambiar", Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        content.set_border_width(14)
        content.set_spacing(8)
        entries = []
        for text in ("Nueva contraseña", "Repetir nueva contraseña"):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.pack_start(ui.label(text), False, False, 0)
            entry = Gtk.Entry()
            entry.set_visibility(False)
            entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            entries.append(entry)
            box.pack_start(entry, True, True, 0)
            content.add(box)
        content.add(
            ui.label(
                "La autorización de administrador se solicita al sistema; no se guarda la contraseña.",
                "corte-hint",
                True,
            )
        )
        dialog.show_all()
        if dialog.run() != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        new, repeated = [entry.get_text() for entry in entries]
        dialog.destroy()
        if new != repeated:
            ui.error(self.window, "Las contraseñas nuevas no coinciden.")
            return
        if len(new) < 8:
            ui.error(self.window, "La nueva contraseña debe tener al menos 8 caracteres.")
            return
        result = run_privileged(["chpasswd"], input_text=f"{user}:{new}\n", timeout=30)
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip() or result.stdout.strip(), "No se pudo cambiar la contraseña")
        else:
            ui.notify("Contraseña actualizada", user, "normal", "corte-security")

    def build_system(self, notebook):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        notebook.append_page(ui.scrolled(box), Gtk.Label(label="Sistema"))

        box.pack_start(ui.label("Actualizaciones", "corte-section-title"), False, False, 0)
        self.updates_label = ui.label("Sin comprobar", "corte-hint", True)
        box.pack_start(self.updates_label, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Comprobar", self.check_updates, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.button("Actualizar índices", self.update_index, "folder-download-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)

        box.pack_start(ui.label("Archivos SUID", "corte-section-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Los binarios SUID se ejecutan con permisos elevados. Revisar la lista ayuda a detectar cambios extraños.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Analizar SUID", self.scan_suid, "system-search-symbolic"), False, False, 0)
        self.suid_label = ui.label("Sin analizar", "corte-hint", True)
        row.pack_start(self.suid_label, True, True, 0)
        box.pack_start(row, False, False, 0)
        self.suid_view = Gtk.TextView()
        self.suid_view.set_editable(False)
        self.suid_view.get_style_context().add_class("corte-code")
        self.suid_view.set_size_request(-1, 180)
        box.pack_start(ui.scrolled(self.suid_view), False, False, 0)

        box.pack_start(ui.label("Antivirus", "corte-section-title"), False, False, 0)
        self.clamav_label = ui.label(
            "ClamAV instalado." if self.clamav_installed else "ClamAV no está instalado. Puedes instalarlo desde Corte Store.",
            "corte-hint",
            True,
        )
        box.pack_start(self.clamav_label, False, False, 0)
        if self.clamav_installed:
            box.pack_start(ui.button("Escanear carpeta personal", self.scan_home, "security-high-symbolic"), False, False, 0)
        self.clamav_output = Gtk.TextView()
        self.clamav_output.set_editable(False)
        self.clamav_output.get_style_context().add_class("corte-code")
        box.pack_start(ui.scrolled(self.clamav_output), True, True, 0)

    def check_updates(self):
        result = run(["apt-get", "-s", "upgrade"], timeout=120)
        if result.returncode != 0:
            self.updates_label.set_text("No se pudo consultar APT. ¿Faltan los índices?")
            return
        count = 0
        for line in result.stdout.splitlines():
            if line.startswith("Inst "):
                count += 1
        self.updates_count = count
        self.updates_label.set_text(f"{count} actualización(es) pendiente(s).")
        self.update_overview_checks()

    def update_index(self):
        dialog = self.progress_dialog("Actualizando", "Ejecutando apt-get update...")

        def work():
            return run_privileged(["apt-get", "update"], timeout=900)

        def done(result):
            dialog.destroy()
            if result.returncode == 0:
                self.updates_label.set_text("Índices actualizados. Pulsa Comprobar.")
            else:
                ui.error(self.window, result.stderr.strip() or result.stdout.strip(), "No se pudo actualizar")
            self.refresh_overview()

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "No se pudo actualizar")

        ui.run_async(work, done, failed)

    def scan_suid(self):
        dialog = self.progress_dialog("Analizando", "Buscando archivos con permiso SUID...")

        def work():
            return run(
                ["bash", "-c", "find / -xdev -perm -4000 -type f 2>/dev/null"],
                timeout=1800,
            )

        def done(result):
            dialog.destroy()
            if result.returncode != 0:
                ui.error(self.window, result.stderr.strip(), "No se pudo analizar")
                return
            files = [line for line in result.stdout.splitlines() if line.strip()]
            self.suid_files = files
            self.suid_label.set_text(f"{len(files)} archivo(s) SUID encontrados.")
            buffer = self.suid_view.get_buffer()
            buffer.set_text("\n".join(files[:200]))
            self.update_overview_checks()

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "No se pudo analizar")

        ui.run_async(work, done, failed)

    def scan_home(self):
        dialog = self.progress_dialog("Escaneando", "Ejecutando clamscan sobre la carpeta personal...")
        home = os.path.expanduser("~")

        def work():
            return run(["clamscan", "-r", "--infected", home], timeout=3600)

        def done(result):
            dialog.destroy()
            buffer = self.clamav_output.get_buffer()
            buffer.set_text(result.stdout + "\n" + result.stderr)
            if result.returncode not in (0, 1):
                ui.error(self.window, result.stderr.strip() or "clamscan devolvió un error.", "ClamAV")
            else:
                ui.notify("Análisis completado", "Revisa el resultado en Corte Security.", "normal", "corte-security")

        def failed(exc):
            dialog.destroy()
            ui.error(self.window, str(exc), "ClamAV")

        ui.run_async(work, done, failed)

    def progress_dialog(self, title, message):
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.set_default_size(440, 120)
        content = dialog.get_content_area()
        content.set_border_width(18)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        spinner = Gtk.Spinner()
        spinner.start()
        row.pack_start(spinner, False, False, 0)
        row.pack_start(ui.label(message, wrap=True), True, True, 0)
        content.add(row)
        dialog.show_all()
        return dialog

    def refresh_overview(self):
        self.refresh_firewall()
        self.check_updates()
        self.clamav_installed = bool(which("clamscan"))
        self.update_overview_checks()

    def update_overview_checks(self):
        for child in self.checks_box.get_children():
            self.checks_box.remove(child)
        checks = []
        if self.firewall_active is None:
            checks.append(("Cortafuegos", "Desconocido", "corte-status-warn"))
        elif self.firewall_active:
            checks.append(("Cortafuegos", "Activo", "corte-status-ok"))
        else:
            checks.append(("Cortafuegos", "Inactivo", "corte-status-bad"))
        if self.updates_count is None:
            checks.append(("Actualizaciones", "Sin comprobar", "corte-status-warn"))
        elif self.updates_count == 0:
            checks.append(("Actualizaciones", "Al día", "corte-status-ok"))
        else:
            checks.append(("Actualizaciones", f"{self.updates_count} pendientes", "corte-status-warn"))
        checks.append(
            ("Antivirus", "Instalado" if self.clamav_installed else "No instalado", "corte-status-ok" if self.clamav_installed else "corte-status-warn")
        )
        if self.suid_files is None:
            checks.append(("Revisión SUID", "Sin analizar", "corte-status-warn"))
        else:
            checks.append(("Revisión SUID", f"{len(self.suid_files)} archivos", "corte-status-ok"))
        score = 0
        if self.firewall_active:
            score += 40
        if self.updates_count == 0:
            score += 30
        elif self.updates_count is not None:
            score += 10
        if self.clamav_installed:
            score += 15
        if self.suid_files is not None:
            score += 15
        self.score_label.set_text(f"{score} / 100")
        self.score_label.get_style_context().remove_class("corte-status-bad")
        self.score_label.get_style_context().remove_class("corte-status-warn")
        if score >= 75:
            self.score_label.get_style_context().add_class("corte-status-ok")
        elif score >= 40:
            self.score_label.get_style_context().add_class("corte-status-warn")
        else:
            self.score_label.get_style_context().add_class("corte-status-bad")
        self.score_detail.set_text(
            "Puntuación calculada con el estado real de UFW, actualizaciones, ClamAV y la última revisión SUID. "
            "No sustituye a una auditoría profesional."
        )
        for title, value, style in checks:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.set_border_width(8)
            row.get_style_context().add_class("corte-stat")
            row.pack_start(ui.label(title, "corte-row-title"), True, True, 0)
            value_label = ui.label(value, style)
            row.pack_start(value_label, False, False, 0)
            self.checks_box.pack_start(row, False, False, 0)
        self.checks_box.show_all()

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = SecurityApp()
    app.run()
    return 0
