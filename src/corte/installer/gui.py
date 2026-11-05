import re
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

from ..common import ui  # noqa: E402
from ..common.system import is_live, run  # noqa: E402
from .backend import InstallConfig, Installer, InstallerError, is_safe_disk, list_disks  # noqa: E402

LANGUAGES = [("es", "Español"), ("en", "English")]
KEYBOARDS = [
    ("es", "Español (España)"),
    ("latam", "Español (Latinoamérica)"),
    ("us", "Inglés (EE. UU.)"),
    ("gb", "Inglés (Reino Unido)"),
    ("fr", "Francés"),
    ("de", "Alemán"),
    ("it", "Italiano"),
    ("pt", "Portugués"),
    ("br", "Portugués (Brasil)"),
]
TIMEZONES = [
    ("Europe/Madrid", "Europa/Madrid"),
    ("Europe/London", "Europa/Londres"),
    ("America/Mexico_City", "América/Ciudad de México"),
    ("America/Bogota", "América/Bogotá"),
    ("America/Argentina/Buenos_Aires", "América/Buenos Aires"),
    ("America/Santiago", "América/Santiago"),
    ("America/New_York", "América/Nueva York"),
    ("UTC", "UTC"),
]


class InstallerGui:
    def __init__(self):
        self.assistant = Gtk.Assistant()
        self.assistant.set_title("Corte Installer")
        self.assistant.set_default_size(940, 700)
        self.assistant.set_position(Gtk.WindowPosition.CENTER)
        self.assistant.set_icon_name("corte-installer")
        self.assistant.connect("destroy", Gtk.main_quit)
        self.assistant.connect("prepare", self.on_prepare)
        self.assistant.connect("apply", self.on_apply)

        self.disks = []
        self.selected_disk = None
        self.disk_buttons = []
        self.manual_mode = False
        self.installing = False
        self.install_ok = False

        self.build_welcome()
        self.build_keyboard()
        self.build_disk()
        self.build_user()
        self.build_summary()
        self.build_progress()
        self.build_finish()

        self.assistant.show_all()
        self.refresh_disks()

    def add_page(self, widget, page_type, title, complete=True):
        self.assistant.append_page(widget, page_type)
        page = self.assistant.get_nth_page(self.assistant.get_n_pages() - 1)
        self.assistant.set_page_title(page, title)
        self.assistant.set_page_complete(page, complete)
        return page

    def page_box(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(22)
        return box

    def build_welcome(self):
        box = self.page_box()
        logo = Gtk.Image.new_from_file("/usr/share/corte/logo.svg")
        logo.set_pixel_size(112)
        logo.set_halign(Gtk.Align.START)
        box.pack_start(logo, False, False, 0)
        box.pack_start(ui.label("Instalar Corte OS", "corte-app-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Este asistente instalará Corte OS en un disco virtual o extraíble. "
                "El proceso puede tardar varios minutos y requiere conexión eléctrica estable.",
                wrap=True,
            ),
            False,
            False,
            0,
        )
        warning = ui.label(
            "El disco elegido se borrará por completo. Corte Installer no toca el medio live "
            "ni discos no verificados. Si usas VirtualBox, el disco objetivo es el disco virtual "
            "de la máquina, nunca un disco físico del anfitrión.",
            "corte-danger-banner",
            True,
        )
        warning.set_border_width(12)
        box.pack_start(warning, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(12)
        grid.attach(ui.label("Idioma de instalación"), 0, 0, 1, 1)
        self.language = Gtk.ComboBoxText()
        for code, name in LANGUAGES:
            self.language.append(code, name)
        self.language.set_active_id("es")
        grid.attach(self.language, 1, 0, 1, 1)
        box.pack_start(grid, False, False, 0)
        self.add_page(box, Gtk.AssistantPageType.INTRO, "Bienvenida")

    def build_keyboard(self):
        box = self.page_box()
        box.pack_start(ui.label("Distribución del teclado", "corte-app-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Selecciona la distribución que corresponde a tu teclado. "
                "Podrás cambiarla después desde la configuración del sistema.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        self.keyboard = Gtk.ComboBoxText()
        for code, name in KEYBOARDS:
            self.keyboard.append(code, name)
        self.keyboard.set_active_id("es")
        box.pack_start(self.keyboard, False, False, 0)
        box.pack_start(ui.label("Prueba de escritura", "corte-section-title"), False, False, 0)
        self.keyboard_test = Gtk.Entry()
        self.keyboard_test.set_placeholder_text("Escribe aquí para comprobar el teclado")
        box.pack_start(self.keyboard_test, False, False, 0)
        self.add_page(box, Gtk.AssistantPageType.CONTENT, "Teclado")

    def build_disk(self):
        box = self.page_box()
        box.pack_start(ui.label("Disco de instalación", "corte-app-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Solo se muestran discos virtuales o extraíbles detectados de forma segura. "
                "El medio live queda excluido automáticamente.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )

        self.disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(self.disk_box, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Actualizar discos", self.refresh_disks, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.label("Modo:", "corte-hint"), False, False, 0)
        self.auto_radio = Gtk.RadioButton.new_with_label_from_widget(None, "Automático (borrar disco)")
        self.manual_radio = Gtk.RadioButton.new_with_label_from_widget(self.auto_radio, "Manual (elegir particiones)")
        self.auto_radio.set_active(True)
        self.auto_radio.connect("toggled", self.on_mode_toggled)
        row.pack_start(self.auto_radio, False, False, 0)
        row.pack_start(self.manual_radio, False, False, 0)
        box.pack_start(row, False, False, 0)

        self.manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.manual_box.set_border_width(12)
        self.manual_box.get_style_context().add_class("corte-banner")
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(12)
        grid.attach(ui.label("Partición raíz (se formateará)"), 0, 0, 1, 1)
        self.root_combo = Gtk.ComboBoxText()
        grid.attach(self.root_combo, 1, 0, 1, 1)
        grid.attach(ui.label("Partición EFI (opcional)"), 0, 1, 1, 1)
        self.efi_combo = Gtk.ComboBoxText()
        grid.attach(self.efi_combo, 1, 1, 1, 1)
        self.manual_box.pack_start(grid, False, False, 0)
        manual_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        manual_actions.pack_start(ui.button("Abrir GParted", self.open_gparted, "drive-harddisk-symbolic"), False, False, 0)
        manual_actions.pack_start(ui.button("Recargar particiones", self.load_partitions, "view-refresh-symbolic"), False, False, 0)
        manual_actions.pack_start(
            ui.label(
                "Crea o elige las particiones en GParted; después vuelve aquí. "
                "La partición raíz y la EFI se formatearán, así que no guardes datos en ellas.",
                "corte-hint",
                True,
            ),
            True,
            True,
            0,
        )
        self.manual_box.pack_start(manual_actions, False, False, 0)
        self.manual_box.set_visible(False)
        box.pack_start(self.manual_box, False, False, 0)

        self.disk_hint = ui.label("", "corte-hint", True)
        box.pack_start(self.disk_hint, False, False, 0)
        self.disk_page = self.add_page(box, Gtk.AssistantPageType.CONTENT, "Disco", False)

    def build_user(self):
        box = self.page_box()
        box.pack_start(ui.label("Tu cuenta", "corte-app-title"), False, False, 0)
        box.pack_start(
            ui.label(
                "Crea el usuario administrador del sistema instalado. El usuario live temporal "
                "se elimina y sus permisos sin contraseña no se copian.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(12)
        self.fullname = Gtk.Entry()
        self.fullname.set_placeholder_text("Nombre y apellidos")
        self.username = Gtk.Entry()
        self.username.set_text("corte")
        self.username.set_placeholder_text("usuario")
        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        self.password.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password.set_placeholder_text("Contraseña")
        self.password_confirm = Gtk.Entry()
        self.password_confirm.set_visibility(False)
        self.password_confirm.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.password_confirm.set_placeholder_text("Repite la contraseña")
        self.hostname = Gtk.Entry()
        self.hostname.set_text("corte-os")
        fields = [
            ("Nombre completo", self.fullname),
            ("Usuario", self.username),
            ("Contraseña", self.password),
            ("Repetir contraseña", self.password_confirm),
            ("Nombre del equipo", self.hostname),
        ]
        for index, (title, widget) in enumerate(fields):
            grid.attach(ui.label(title), 0, index, 1, 1)
            grid.attach(widget, 1, index, 1, 1)
        box.pack_start(grid, False, False, 0)

        lower = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lower.pack_start(ui.label("Zona horaria"), False, False, 0)
        self.timezone = Gtk.ComboBoxText()
        for code, name in TIMEZONES:
            self.timezone.append(code, name)
        self.timezone.set_active_id("Europe/Madrid")
        lower.pack_start(self.timezone, False, False, 0)
        self.autologin = Gtk.CheckButton(label="Iniciar sesión automáticamente")
        self.autologin.set_active(True)
        lower.pack_start(self.autologin, False, False, 0)
        box.pack_start(lower, False, False, 0)

        self.user_hint = ui.label("", "corte-hint", True)
        box.pack_start(self.user_hint, False, False, 0)
        self.user_page = self.add_page(box, Gtk.AssistantPageType.CONTENT, "Usuario", False)

    def build_summary(self):
        box = self.page_box()
        box.pack_start(ui.label("Resumen de la instalación", "corte-app-title"), False, False, 0)
        self.summary_view = Gtk.TextView()
        self.summary_view.set_editable(False)
        self.summary_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.summary_view.get_style_context().add_class("corte-code")
        self.summary_view.set_size_request(-1, 260)
        box.pack_start(ui.scrolled(self.summary_view), True, True, 0)
        warning = ui.label(
            "Al pulsar Instalar se borrarán las particiones seleccionadas y se escribirá Corte OS. "
            "Esta acción no se puede deshacer.",
            "corte-danger-banner",
            True,
        )
        warning.set_border_width(12)
        box.pack_start(warning, False, False, 0)
        self.confirm_check = Gtk.CheckButton(
            label="Entiendo que se borrará el disco o las particiones seleccionadas"
        )
        self.confirm_check.connect("toggled", self.on_confirm_toggled)
        box.pack_start(self.confirm_check, False, False, 0)
        self.summary_page = self.add_page(box, Gtk.AssistantPageType.CONFIRM, "Resumen", False)

    def build_progress(self):
        box = self.page_box()
        box.pack_start(ui.label("Instalando Corte OS", "corte-app-title"), False, False, 0)
        self.progress_label = ui.label("Preparando...", "corte-hint", True)
        box.pack_start(self.progress_label, False, False, 0)
        self.progress = Gtk.ProgressBar()
        box.pack_start(self.progress, False, False, 0)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.get_style_context().add_class("corte-progress-log")
        box.pack_start(ui.scrolled(self.log_view), True, True, 0)
        self.progress_page = self.add_page(box, Gtk.AssistantPageType.PROGRESS, "Instalación", False)

    def build_finish(self):
        box = self.page_box()
        box.pack_start(ui.label("Corte OS está instalado", "corte-app-title"), False, False, 0)
        self.finish_label = ui.label(
            "La instalación terminó correctamente. Reinicia la máquina para arrancar desde el disco instalado.",
            "corte-hint",
            True,
        )
        box.pack_start(self.finish_label, False, False, 0)
        self.finish_warnings = Gtk.TextView()
        self.finish_warnings.set_editable(False)
        self.finish_warnings.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.finish_warnings.get_style_context().add_class("corte-code")
        self.finish_warnings.set_size_request(-1, 150)
        box.pack_start(ui.scrolled(self.finish_warnings), True, True, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Reiniciar ahora", self.reboot, "system-reboot-symbolic", "suggested-action"), False, False, 0)
        row.pack_start(ui.button("Cerrar", lambda: self.assistant.destroy(), "window-close-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)
        self.finish_page = self.add_page(box, Gtk.AssistantPageType.SUMMARY, "Listo", True)

    def refresh_disks(self):
        for child in self.disk_box.get_children():
            self.disk_box.remove(child)
        self.disk_buttons = []
        self.selected_disk = None
        try:
            all_disks = list_disks()
        except InstallerError as exc:
            self.disk_hint.set_text(str(exc))
            return
        self.disks = [
            disk for disk in all_disks if not disk.live and is_safe_disk(disk)
        ]
        if not self.disks:
            self.disk_hint.set_text(
                "No se detectaron discos virtuales o extraíbles compatibles. "
                "Comprueba que la máquina virtual tiene un disco conectado."
            )
            self.assistant.set_page_complete(self.disk_page, False)
            return
        group = None
        for disk in self.disks:
            label = (
                f"{disk.path}  ·  {disk.size_gib:.0f} GB  ·  "
                f"{disk.model or 'disco virtual'}"
                f"{' · USB' if disk.removable else ''}"
            )
            button = Gtk.RadioButton.new_with_label_from_widget(group, label)
            if group is None:
                group = button
            button.disk = disk
            button.connect("toggled", self.on_disk_toggled, disk)
            self.disk_box.pack_start(button, False, False, 0)
            self.disk_buttons.append(button)
        self.disk_buttons[0].set_active(True)
        self.selected_disk = self.disks[0]
        self.disk_hint.set_text(
            f"{len(self.disks)} disco(s) seguro(s) detectado(s). El medio live no aparece."
        )
        self.disk_box.show_all()
        self.load_partitions()
        self.assistant.set_page_complete(self.disk_page, True)

    def on_disk_toggled(self, button, disk):
        if button.get_active():
            self.selected_disk = disk
            self.load_partitions()

    def on_mode_toggled(self, *_args):
        self.manual_mode = self.manual_radio.get_active()
        self.manual_box.set_visible(self.manual_mode)
        if self.manual_mode:
            self.load_partitions()
        self.update_disk_complete()

    def update_disk_complete(self):
        complete = self.selected_disk is not None
        if self.manual_mode:
            complete = complete and bool(self.root_combo.get_active_id())
        self.assistant.set_page_complete(self.disk_page, complete)

    def load_partitions(self):
        self.root_combo.remove_all()
        self.efi_combo.remove_all()
        self.efi_combo.append("", "Sin partición EFI")
        if self.selected_disk is None:
            return
        result = run(
            [
                "lsblk",
                "-J",
                "-b",
                "-o",
                "PATH,SIZE,FSTYPE,TYPE,MOUNTPOINTS",
                self.selected_disk.path,
            ],
            timeout=20,
        )
        if result.returncode != 0:
            return
        try:
            import json

            payload = json.loads(result.stdout)
        except (ValueError, ImportError):
            return
        partitions = []
        for item in payload.get("blockdevices", []):
            for child in item.get("children") or []:
                if child.get("type") != "part":
                    continue
                path = child.get("path", "")
                if not path:
                    continue
                size = int(child.get("size") or 0) / (1024**3)
                fstype = child.get("fstype") or "sin formato"
                partitions.append((path, f"{path} · {size:.1f} GB · {fstype}", fstype))
        if not partitions:
            self.root_combo.append("", "Sin particiones disponibles")
            self.root_combo.set_active_id("")
            self.efi_combo.set_active_id("")
            return
        for path, label, _fstype in partitions:
            self.root_combo.append(path, label)
        for path, label, fstype in partitions:
            if fstype.lower() in ("vfat", "fat32", "fat", "esp"):
                self.efi_combo.append(path, label)
        self.root_combo.set_active(0)
        self.efi_combo.set_active(0)
        self.update_disk_complete()

    def open_gparted(self):
        if self.selected_disk is None:
            return
        try:
            subprocess.Popen(["gparted", self.selected_disk.path])
            ui.info(
                self.assistant,
                "GParted se abrió en otra ventana. Crea o prepara las particiones y pulsa "
                "«Recargar particiones» al terminar. Corte Installer formateará las particiones elegidas.",
                "GParted",
            )
        except OSError as exc:
            ui.error(self.assistant, str(exc), "No se pudo abrir GParted")

    def on_confirm_toggled(self, checkbox):
        self.assistant.set_page_complete(self.summary_page, checkbox.get_active())

    def on_prepare(self, assistant, page):
        if page is self.disk_page:
            self.update_disk_complete()
        elif page is self.user_page:
            self.validate_user_page()
        elif page is self.summary_page:
            self.update_summary()
            assistant.set_page_complete(page, self.confirm_check.get_active())
        elif page is self.progress_page:
            assistant.set_page_complete(page, self.install_ok)

    def validate_user_page(self):
        username = self.username.get_text().strip()
        password = self.password.get_text()
        confirm = self.password_confirm.get_text()
        hostname = self.hostname.get_text().strip()
        messages = []
        if not re.match(r"^[a-z_][a-z0-9_-]{2,31}$", username):
            messages.append("Usuario no válido (minúsculas, números, guion o guion bajo).")
        if len(password) < 8:
            messages.append("La contraseña debe tener al menos 8 caracteres.")
        if password != confirm:
            messages.append("Las contraseñas no coinciden.")
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,62}$", hostname):
            messages.append("El nombre del equipo no es válido.")
        self.user_hint.set_text(" ".join(messages) if messages else "La cuenta es válida.")
        self.assistant.set_page_complete(self.user_page, not messages)

    def update_summary(self):
        disk = self.selected_disk
        lines = [
            f"Idioma: {self.language.get_active_id()}",
            f"Teclado: {self.keyboard.get_active_id()}",
            f"Zona horaria: {self.timezone.get_active_id()}",
            "",
            f"Modo: {'manual' if self.manual_mode else 'automático'}",
        ]
        if disk is not None:
            lines.append(
                f"Disco: {disk.path} · {disk.size_gib:.0f} GB · {disk.model or 'disco virtual'}"
            )
        if self.manual_mode:
            lines.append(f"Partición raíz: {self.root_combo.get_active_id() or 'no seleccionada'}")
            lines.append(f"Partición EFI: {self.efi_combo.get_active_id() or 'ninguna'}")
        lines += [
            "",
            f"Usuario: {self.username.get_text().strip()}",
            f"Nombre completo: {self.fullname.get_text().strip() or '(sin especificar)'}",
            f"Equipo: {self.hostname.get_text().strip()}",
            f"Inicio de sesión automático: {'sí' if self.autologin.get_active() else 'no'}",
        ]
        self.summary_view.get_buffer().set_text("\n".join(lines))

    def on_apply(self, assistant):
        if assistant.get_current_page() != 4:
            return
        if self.installing:
            return
        if not self.confirm_check.get_active():
            ui.error(self.assistant, "Marca la confirmación de borrado antes de instalar.")
            return
        if self.selected_disk is None:
            ui.error(self.assistant, "Selecciona un disco de instalación.")
            return
        config = InstallConfig(
            disk=self.selected_disk.path,
            user=self.username.get_text().strip(),
            password=self.password.get_text(),
            full_name=self.fullname.get_text().strip(),
            hostname=self.hostname.get_text().strip(),
            language=self.language.get_active_id() or "es",
            keyboard=self.keyboard.get_active_id() or "es",
            timezone=self.timezone.get_active_id() or "Europe/Madrid",
            mode="manual" if self.manual_mode else "auto",
            root_partition=self.root_combo.get_active_id() or "" if self.manual_mode else "",
            efi_partition=self.efi_combo.get_active_id() or "" if self.manual_mode else "",
            autologin=self.autologin.get_active(),
            reboot=False,
        )
        self.installing = True
        self.install_ok = False
        self.assistant.set_deletable(False)
        self.confirm_check.set_sensitive(False)
        self.log_view.get_buffer().set_text("")
        self.progress.set_fraction(0)
        self.assistant.set_page_complete(self.progress_page, False)
        self.assistant.set_current_page(5)

        installer = Installer(
            config,
            progress=lambda percent, message: GLib.idle_add(self.on_progress, percent, message),
            log=lambda message: GLib.idle_add(self.append_log, message),
        )

        def work():
            try:
                warnings = installer.install()
            except Exception as exc:  # noqa: BLE001
                GLib.idle_add(self.on_error, exc)
                return
            GLib.idle_add(self.on_done, warnings)

        threading.Thread(target=work, daemon=True).start()

    def on_progress(self, percent, message):
        self.progress.set_fraction(max(0.0, min(1.0, percent / 100.0)))
        self.progress_label.set_text(f"{percent}% · {message}")
        return False

    def append_log(self, message):
        buffer = self.log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), message + "\n")
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.log_view.scroll_mark_onscreen(mark)
        try:
            with open("/var/log/corte-installer.log", "a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass
        return False

    def on_done(self, warnings):
        self.installing = False
        self.install_ok = True
        self.assistant.set_deletable(True)
        self.progress.set_fraction(1.0)
        self.progress_label.set_text("100% · Instalación completada")
        self.finish_label.set_text(
            "La instalación terminó correctamente. Reinicia la máquina para arrancar desde el disco instalado."
        )
        text = "\n".join(warnings) if warnings else "Sin advertencias."
        self.finish_warnings.get_buffer().set_text(text)
        self.assistant.set_page_complete(self.progress_page, True)
        self.assistant.set_current_page(6)
        return False

    def on_error(self, exc):
        self.installing = False
        self.install_ok = False
        self.assistant.set_deletable(True)
        self.confirm_check.set_sensitive(True)
        self.append_log(f"ERROR: {exc}")
        self.progress_label.set_text("La instalación falló.")
        self.assistant.set_page_complete(self.progress_page, False)
        ui.error(
            self.assistant,
            f"{exc}\n\nRevisa /var/log/corte-installer.log para más detalles. "
            "El disco puede haber quedado parcialmente modificado.",
            "Instalación no completada",
        )
        return False

    def reboot(self):
        try:
            subprocess.Popen(["reboot", "-f"])
        except OSError as exc:
            ui.error(self.assistant, str(exc), "No se pudo reiniciar")

    def run(self):
        Gtk.main()


def run_gui():
    if not is_live():
        ui.init_theme()
        dialog = Gtk.MessageDialog(
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Corte Installer no está disponible",
        )
        dialog.format_secondary_text(
            "El instalador solo se puede ejecutar desde el entorno live de la ISO de Corte OS. "
            "No se modificará ningún disco."
        )
        dialog.run()
        dialog.destroy()
        return 1
    ui.init_theme()
    app = InstallerGui()
    app.run()
    return 0
