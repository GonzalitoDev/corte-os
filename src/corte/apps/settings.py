import getpass
import os
import pwd
import re
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from ..common import paths, ui  # noqa: E402
from ..common.system import (  # noqa: E402
    human_bytes,
    human_seconds,
    is_live,
    read_first,
    run,
    run_privileged,
)

WALLPAPER_DIRS = [Path("/usr/share/backgrounds/corte"), paths.share_dir() / "backgrounds"]
ICON_THEMES = ["Papirus-Dark", "Papirus", "Adwaita"]
GTK_THEMES = ["Corte-Dark", "Arc-Dark", "Adwaita-dark"]
WM_THEMES = ["Arc-Dark", "Default"]


def xfconf_get(channel, prop, default=""):
    result = run(["xfconf-query", "-c", channel, "-p", prop])
    if result.returncode == 0:
        return result.stdout.strip()
    return default


def xfconf_set(channel, prop, value, value_type="string"):
    result = run(["xfconf-query", "-c", channel, "-p", prop, "-s", str(value)])
    if result.returncode != 0:
        result = run(
            [
                "xfconf-query",
                "-c",
                channel,
                "-p",
                prop,
                "-n",
                "-t",
                value_type,
                "-s",
                str(value),
            ]
        )
    return result


def set_wallpaper(path):
    paths_found = run(["xfconf-query", "-c", "xfce4-desktop", "-l"])
    changed = 0
    if paths_found.returncode == 0:
        for line in paths_found.stdout.splitlines():
            if line.strip().endswith("last-image"):
                xfconf_set("xfce4-desktop", line.strip(), str(path))
                changed += 1
    if changed == 0:
        xfconf_set(
            "xfce4-desktop",
            "/backdrop/screen0/monitor0/workspace0/last-image",
            str(path),
        )
        xfconf_set(
            "xfce4-desktop",
            "/backdrop/screen0/monitor0/workspace0/image-style",
            "5",
            "int",
        )


class SettingsApp:
    def __init__(self):
        self.window = ui.window("Corte Settings", "corte-settings", (1100, 760))
        self.window.set_titlebar(ui.header("Corte Settings", "Configuración de Corte OS", "corte-settings"))

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.window.add(root)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(180)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        sidebar.set_size_request(230, -1)
        sidebar.get_style_context().add_class("corte-sidebar")
        root.pack_start(sidebar, False, False, 0)
        root.pack_start(self.stack, True, True, 0)

        self.build_appearance()
        self.build_display()
        self.build_sound()
        self.build_network()
        self.build_users()
        self.build_system()

        self.window.connect("destroy", Gtk.main_quit)
        self.window.show_all()

    def add_page(self, name, title, content):
        self.stack.add_titled(ui.scrolled(content), name, title)

    def page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(20)
        return box

    def section(self, parent, title):
        label = ui.label(title, "corte-section-title")
        parent.pack_start(label, False, False, 0)

    def build_appearance(self):
        box = self.page()
        self.section(box, "Fondo de pantalla")
        hint = ui.label(
            "Los fondos se aplican al escritorio XFCE al instante.",
            "corte-hint",
            True,
        )
        box.pack_start(hint, False, False, 0)

        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(3)
        flow.set_row_spacing(10)
        flow.set_column_spacing(10)
        self.wallpaper_buttons = []
        seen = set()
        for directory in WALLPAPER_DIRS:
            if not directory.is_dir():
                continue
            for wall in sorted(directory.glob("*.svg")):
                if wall.name in seen:
                    continue
                seen.add(wall.name)
                button = Gtk.Button()
                button.get_style_context().add_class("corte-wallpaper")
                preview = Gtk.Image.new_from_file(str(wall))
                preview.set_size_request(260, 146)
                label = ui.label(wall.stem.replace("corte-wallpaper-", "Fondo "), "corte-hint")
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                content.pack_start(preview, False, False, 0)
                content.pack_start(label, False, False, 0)
                button.add(content)
                button.connect("clicked", self.on_wallpaper, wall)
                button.wallpaper_path = wall
                self.wallpaper_buttons.append(button)
                flow.add(button)
        box.pack_start(flow, False, False, 0)

        self.section(box, "Temas")
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(16)
        grid.attach(ui.label("Tema GTK"), 0, 0, 1, 1)
        self.gtk_theme = Gtk.ComboBoxText()
        for theme in GTK_THEMES:
            self.gtk_theme.append_text(theme)
        current = xfconf_get("xsettings", "/Net/ThemeName", "Corte-Dark")
        self.gtk_theme.set_active(GTK_THEMES.index(current) if current in GTK_THEMES else 0)
        self.gtk_theme.connect("changed", self.on_gtk_theme)
        grid.attach(self.gtk_theme, 1, 0, 1, 1)

        grid.attach(ui.label("Iconos"), 0, 1, 1, 1)
        self.icon_theme = Gtk.ComboBoxText()
        for theme in ICON_THEMES:
            self.icon_theme.append_text(theme)
        current = xfconf_get("xsettings", "/Net/IconThemeName", "Papirus-Dark")
        self.icon_theme.set_active(ICON_THEMES.index(current) if current in ICON_THEMES else 0)
        self.icon_theme.connect("changed", self.on_icon_theme)
        grid.attach(self.icon_theme, 1, 1, 1, 1)

        grid.attach(ui.label("Ventanas"), 0, 2, 1, 1)
        self.wm_theme = Gtk.ComboBoxText()
        for theme in WM_THEMES:
            self.wm_theme.append_text(theme)
        current = xfconf_get("xfwm4", "/general/theme", "Arc-Dark")
        self.wm_theme.set_active(WM_THEMES.index(current) if current in WM_THEMES else 0)
        self.wm_theme.connect("changed", self.on_wm_theme)
        grid.attach(self.wm_theme, 1, 2, 1, 1)
        box.pack_start(grid, False, False, 0)

        self.appearance_status = ui.label("", "corte-hint")
        box.pack_start(self.appearance_status, False, False, 0)
        self.add_page("appearance", "Apariencia", box)

    def on_wallpaper(self, button, path):
        set_wallpaper(path)
        for item in self.wallpaper_buttons:
            item.get_style_context().remove_class("selected")
        button.get_style_context().add_class("selected")
        self.appearance_status.set_text(f"Fondo aplicado: {path.name}")

    def on_gtk_theme(self, combo):
        theme = combo.get_active_text()
        if not theme:
            return
        result = xfconf_set("xsettings", "/Net/ThemeName", theme)
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar el tema")
        self.appearance_status.set_text(f"Tema GTK: {theme}")

    def on_icon_theme(self, combo):
        theme = combo.get_active_text()
        if not theme:
            return
        result = xfconf_set("xsettings", "/Net/IconThemeName", theme)
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar los iconos")
        self.appearance_status.set_text(f"Iconos: {theme}")

    def on_wm_theme(self, combo):
        theme = combo.get_active_text()
        if not theme:
            return
        result = xfconf_set("xfwm4", "/general/theme", theme)
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar el tema de ventanas")
        self.appearance_status.set_text(f"Ventanas: {theme}")

    def build_display(self):
        box = self.page()
        self.section(box, "Pantalla")
        box.pack_start(
            ui.label(
                "Selecciona una resolución para cada salida conectada. Los cambios se aplican con xrandr.",
                "corte-hint",
                True,
            ),
            False,
            False,
            0,
        )
        self.display_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.pack_start(self.display_box, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(
            ui.button("Actualizar", self.refresh_display, "view-refresh-symbolic"),
            False,
            False,
            0,
        )
        row.pack_start(
            ui.button(
                "Abrir configuración de XFCE",
                lambda: subprocess.Popen(["xfce4-display-settings"]),
                "video-display-symbolic",
            ),
            False,
            False,
            0,
        )
        box.pack_start(row, False, False, 0)
        self.display_status = ui.label("", "corte-hint")
        box.pack_start(self.display_status, False, False, 0)
        self.outputs = {}
        self.refresh_display()
        self.add_page("display", "Pantalla", box)

    def refresh_display(self):
        for child in self.display_box.get_children():
            self.display_box.remove(child)
        self.outputs.clear()
        result = run(["xrandr", "--query"])
        if result.returncode != 0:
            self.display_box.pack_start(
                ui.label("xrandr no está disponible en esta sesión.", "corte-empty"),
                False,
                False,
                0,
            )
            self.display_box.show_all()
            return
        for line in result.stdout.splitlines():
            if " connected" not in line:
                continue
            parts = line.split()
            name = parts[0]
            modes = [part.rstrip("*") for part in parts[1:] if re.match(r"^\d+x\d+", part)]
            current_match = re.search(r"(\d+x\d+)\+", line)
            current = current_match.group(1) if current_match else (modes[0] if modes else "")
            modes = list(dict.fromkeys(modes))
            if not modes:
                continue
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.pack_start(ui.label(name, "corte-row-title"), False, False, 0)
            combo = Gtk.ComboBoxText()
            for mode in modes:
                combo.append_text(mode)
            if current in modes:
                combo.set_active(modes.index(current))
            combo.connect("changed", self.on_mode_changed, name)
            self.outputs[name] = combo
            row.pack_start(combo, False, False, 0)
            self.display_box.pack_start(row, False, False, 0)
        if not self.outputs:
            self.display_box.pack_start(
                ui.label("No se detectaron pantallas conectadas.", "corte-empty"),
                False,
                False,
                0,
            )
        self.display_box.show_all()

    def on_mode_changed(self, combo, name):
        mode = combo.get_active_text()
        if not mode:
            return
        result = run(["xrandr", "--output", name, "--mode", mode])
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar la resolución")
        else:
            self.display_status.set_text(f"{name}: {mode}")

    def build_sound(self):
        box = self.page()
        self.section(box, "Sonido")
        self.sound_device = ui.label("Dispositivo: —", "corte-hint")
        box.pack_start(self.sound_device, False, False, 0)

        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        volume_box.pack_start(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 150, 1)
        self.volume_scale.set_hexpand(True)
        self.volume_scale.set_draw_value(True)
        self.volume_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.volume_scale.connect("value-changed", self.on_volume_changed)
        volume_box.pack_start(self.volume_scale, True, True, 0)
        box.pack_start(volume_box, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Silenciar / activar", self.toggle_mute, "audio-volume-muted-symbolic"), False, False, 0)
        row.pack_start(ui.button("Actualizar", self.refresh_sound, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.button("Mezclador", lambda: subprocess.Popen(["pavucontrol"]), "multimedia-volume-control-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)
        self.sound_status = ui.label("", "corte-hint")
        box.pack_start(self.sound_status, False, False, 0)
        self.volume_loading = False
        self.refresh_sound()
        self.add_page("sound", "Sonido", box)

    def refresh_sound(self):
        info = run(["pactl", "info"])
        if info.returncode != 0:
            self.sound_device.set_text("PulseAudio no está disponible.")
            return
        sink = "—"
        for line in info.stdout.splitlines():
            if line.lower().startswith("default sink:"):
                sink = line.split(":", 1)[1].strip()
                break
        self.sound_device.set_text(f"Dispositivo: {sink}")
        volume = run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        if volume.returncode == 0:
            match = re.search(r"(\d+)%", volume.stdout)
            if match:
                self.volume_loading = True
                self.volume_scale.set_value(int(match.group(1)))
                self.volume_loading = False
        mute = run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
        if mute.returncode == 0:
            state = mute.stdout.strip().split(":", 1)[-1].strip()
            self.sound_status.set_text(f"Estado: {state}")

    def on_volume_changed(self, scale):
        if self.volume_loading:
            return
        value = int(scale.get_value())
        result = run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"])
        if result.returncode != 0:
            self.sound_status.set_text(result.stderr.strip() or "No se pudo cambiar el volumen.")
        else:
            self.sound_status.set_text(f"Volumen: {value}%")

    def toggle_mute(self):
        result = run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar el silencio")
        self.refresh_sound()

    def build_network(self):
        box = self.page()
        self.section(box, "Red")
        self.network_status = ui.label("—", "corte-hint", True)
        box.pack_start(self.network_status, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Actualizar", self.refresh_network, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.button("Activar Wi-Fi", lambda: self.set_wifi(True), "network-wireless-symbolic"), False, False, 0)
        row.pack_start(ui.button("Desactivar Wi-Fi", lambda: self.set_wifi(False), "network-wireless-offline-symbolic"), False, False, 0)
        row.pack_start(ui.button("Editor de conexiones", lambda: subprocess.Popen(["nm-connection-editor"]), "preferences-system-network-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)

        self.wifi_list = Gtk.ListBox()
        self.wifi_list.set_selection_mode(Gtk.SelectionMode.NONE)
        box.pack_start(ui.scrolled(self.wifi_list), True, True, 0)
        self.add_page("network", "Red", box)
        self.refresh_network()

    def refresh_network(self):
        for child in self.wifi_list.get_children():
            self.wifi_list.remove(child)
        devices = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
        if devices.returncode != 0:
            self.network_status.set_text("NetworkManager no está disponible.")
            return
        lines = []
        for line in devices.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 4:
                lines.append(" · ".join(parts[:4]))
        wifi = run(["nmcli", "radio", "wifi"])
        wifi_state = wifi.stdout.strip() if wifi.returncode == 0 else "desconocido"
        self.network_status.set_text(
            f"Wi-Fi: {wifi_state}\n" + ("\n".join(lines) if lines else "Sin dispositivos de red.")
        )
        if "enabled" not in wifi_state:
            return
        scan = run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
        if scan.returncode != 0:
            return
        seen = set()
        for line in scan.stdout.splitlines():
            parts = line.rsplit(":", 2)
            if len(parts) != 3:
                continue
            ssid, signal, security = parts
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            row = Gtk.ListBoxRow()
            row.ssid = ssid
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_border_width(8)
            icon = "network-wireless-signal-excellent-symbolic"
            try:
                value = int(signal)
                if value < 35:
                    icon = "network-wireless-signal-weak-symbolic"
                elif value < 65:
                    icon = "network-wireless-signal-ok-symbolic"
            except ValueError:
                pass
            box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON), False, False, 0)
            box.pack_start(ui.label(ssid, "corte-row-title"), True, True, 0)
            box.pack_start(ui.label(f"{signal}% · {security or 'abierta'}", "corte-hint"), False, False, 0)
            connect = ui.button("Conectar", lambda _b, s=ssid, sec=security: self.connect_wifi(s, sec), "network-transmit-receive-symbolic")
            box.pack_start(connect, False, False, 0)
            row.add(box)
            self.wifi_list.add(row)
        if not seen:
            self.wifi_list.pack_start(
                ui.label("No se detectaron redes Wi-Fi. Comprueba el adaptador o activa el Wi-Fi.", "corte-empty"),
                False,
                False,
                0,
            )
        self.wifi_list.show_all()

    def set_wifi(self, enabled):
        command = ["nmcli", "radio", "wifi", "on" if enabled else "off"]
        result = run(command)
        if result.returncode != 0:
            result = run_privileged(command)
        if result.returncode != 0:
            ui.error(self.window, result.stderr, "No se pudo cambiar el Wi-Fi")
        self.refresh_network()

    def connect_wifi(self, ssid, security):
        password = None
        if security and security not in ("--", ""):
            password = ui.ask_text(self.window, "Contraseña Wi-Fi", f"Contraseña para {ssid}")
            if password is None:
                return
        command = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            command += ["password", password]
        result = run(command, timeout=60)
        if result.returncode != 0:
            result = run_privileged(command, timeout=60)
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip() or result.stdout.strip(), "No se pudo conectar")
        else:
            self.network_status.set_text(f"Conectado a {ssid}")
        self.refresh_network()

    def build_users(self):
        box = self.page()
        self.section(box, "Usuarios")
        self.user_status = ui.label("", "corte-hint")
        box.pack_start(self.user_status, False, False, 0)
        self.user_list = Gtk.ListBox()
        self.user_list.set_selection_mode(Gtk.SelectionMode.NONE)
        box.pack_start(ui.scrolled(self.user_list), True, True, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Actualizar", self.refresh_users, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.button("Crear usuario", self.create_user, "list-add-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)
        self.refresh_users()
        self.add_page("users", "Usuarios", box)

    def refresh_users(self):
        for child in self.user_list.get_children():
            self.user_list.remove(child)
        current = getpass.getuser()
        for account in pwd.getpwall():
            if account.pw_uid < 1000 or account.pw_shell.endswith(("/nologin", "/false")):
                continue
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_border_width(8)
            image = Gtk.Image.new_from_icon_name("avatar-default-symbolic", Gtk.IconSize.DND)
            row.pack_start(image, False, False, 0)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            name = account.pw_gecos.split(",")[0] or account.pw_name
            text.pack_start(ui.label(f"{name} ({account.pw_name})", "corte-row-title"), False, False, 0)
            admin = " · administrador" if account.pw_gid == 27 or self.in_group(account.pw_name, "sudo") else ""
            text.pack_start(ui.label(f"UID {account.pw_uid}{admin}", "corte-hint"), False, False, 0)
            row.pack_start(text, True, True, 0)
            if account.pw_name == current:
                row.pack_start(ui.label("Sesión actual", "corte-pill"), False, False, 0)
            row.pack_start(ui.button("Cambiar contraseña", lambda _b, u=account.pw_name: self.change_password(u), "dialog-password-symbolic"), False, False, 0)
            if account.pw_name != current and account.pw_name != "root":
                row.pack_start(ui.button("Eliminar", lambda _b, u=account.pw_name: self.delete_user(u), "user-trash-symbolic", "destructive-action"), False, False, 0)
            self.user_list.add(row)
        self.user_list.show_all()

    def in_group(self, user, group):
        result = run(["id", "-nG", user])
        return result.returncode == 0 and group in result.stdout.split()

    def password_dialog(self, title, prompt):
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Aceptar", Gtk.ResponseType.OK)
        dialog.set_default_size(420, 160)
        content = dialog.get_content_area()
        content.set_border_width(14)
        content.set_spacing(8)
        content.add(ui.label(prompt))
        first = Gtk.Entry()
        first.set_visibility(False)
        first.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        first.set_placeholder_text("Contraseña")
        second = Gtk.Entry()
        second.set_visibility(False)
        second.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        second.set_placeholder_text("Repite la contraseña")
        content.add(first)
        content.add(second)
        dialog.show_all()
        if dialog.run() != Gtk.ResponseType.OK:
            dialog.destroy()
            return None
        password = first.get_text()
        confirm = second.get_text()
        dialog.destroy()
        if len(password) < 4:
            ui.error(self.window, "La contraseña debe tener al menos 4 caracteres.")
            return None
        if password != confirm:
            ui.error(self.window, "Las contraseñas no coinciden.")
            return None
        return password

    def change_password(self, user):
        password = self.password_dialog("Cambiar contraseña", f"Nueva contraseña para {user}")
        if password is None:
            return
        result = run_privileged(["chpasswd"], input_text=f"{user}:{password}\n", timeout=30)
        if result.returncode == 0:
            self.user_status.set_text(f"Contraseña actualizada para {user}.")
            ui.notify("Contraseña actualizada", user, "normal", "corte-settings")
        else:
            ui.error(self.window, result.stderr.strip() or "No se pudo cambiar la contraseña.", "Error")

    def create_user(self):
        dialog = Gtk.Dialog(title="Crear usuario", transient_for=self.window, modal=True)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Crear", Gtk.ResponseType.OK)
        dialog.set_default_size(460, 260)
        content = dialog.get_content_area()
        content.set_border_width(14)
        content.set_spacing(8)
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(10)
        entries = {}
        for index, (key, title, password) in enumerate(
            [
                ("username", "Usuario", False),
                ("fullname", "Nombre completo", False),
                ("password", "Contraseña", True),
            ]
        ):
            grid.attach(ui.label(title), 0, index, 1, 1)
            entry = Gtk.Entry()
            if password:
                entry.set_visibility(False)
                entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            entries[key] = entry
            grid.attach(entry, 1, index, 1, 1)
        admin = Gtk.CheckButton(label="Permitir administración con sudo")
        admin.set_active(False)
        grid.attach(admin, 0, 3, 2, 1)
        content.add(grid)
        dialog.show_all()
        if dialog.run() != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        username = entries["username"].get_text().strip()
        fullname = entries["fullname"].get_text().strip() or username
        password = entries["password"].get_text()
        is_admin = admin.get_active()
        dialog.destroy()
        if not re.match(r"^[a-z_][a-z0-9_-]{2,31}$", username):
            ui.error(self.window, "Usuario no válido. Usa minúsculas, números, guion o guion bajo (3-32 caracteres).")
            return
        if len(password) < 4:
            ui.error(self.window, "La contraseña debe tener al menos 4 caracteres.")
            return
        result = run_privileged(
            ["useradd", "-m", "-s", "/bin/bash", "-c", fullname, username], timeout=30
        )
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip(), "No se pudo crear el usuario")
            return
        if is_admin:
            run_privileged(["usermod", "-aG", "sudo", username], timeout=30)
        run_privileged(
            ["usermod", "-aG", "audio,video,plugdev,netdev,cdrom", username], timeout=30
        )
        result = run_privileged(["chpasswd"], input_text=f"{username}:{password}\n", timeout=30)
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip(), "No se pudo asignar la contraseña")
        self.user_status.set_text(f"Usuario {username} creado.")
        self.refresh_users()

    def delete_user(self, user):
        if not ui.confirm(
            self.window,
            f"¿Eliminar el usuario {user} y su carpeta personal? Esta acción no se puede deshacer.",
            "Eliminar usuario",
            True,
        ):
            return
        result = run_privileged(["userdel", "-r", user], timeout=30)
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip(), "No se pudo eliminar el usuario")
        else:
            self.user_status.set_text(f"Usuario {user} eliminado.")
        self.refresh_users()

    def build_system(self):
        box = self.page()
        self.section(box, "Información del sistema")
        self.system_grid = Gtk.Grid()
        self.system_grid.set_row_spacing(8)
        self.system_grid.set_column_spacing(20)
        box.pack_start(self.system_grid, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(ui.button("Actualizar", self.refresh_system, "view-refresh-symbolic"), False, False, 0)
        row.pack_start(ui.button("Abrir Corte Monitor", lambda: subprocess.Popen(["corte", "monitor"]), "corte-monitor"), False, False, 0)
        row.pack_start(ui.button("Abrir terminal", lambda: subprocess.Popen(["corte", "terminal"]), "corte-terminal"), False, False, 0)
        row.pack_start(ui.button("Copiar información", self.copy_system, "edit-copy-symbolic"), False, False, 0)
        box.pack_start(row, False, False, 0)
        self.system_text = ""
        self.refresh_system()

        self.section(box, "Instalador")
        if is_live():
            box.pack_start(
                ui.label(
                    "Estás usando el entorno live. Puedes instalar Corte OS en un disco virtual.",
                    "corte-hint",
                    True,
                ),
                False,
                False,
                0,
            )
            box.pack_start(
                ui.button("Abrir Corte Installer", lambda: subprocess.Popen(["corte-installer"]), "corte-installer", "suggested-action"),
                False,
                False,
                0,
            )
        else:
            box.pack_start(
                ui.label(
                    "Corte OS ya está instalado en este equipo. El instalador solo está disponible desde la ISO live.",
                    "corte-hint",
                    True,
                ),
                False,
                False,
                0,
            )
        self.add_page("system", "Sistema", box)

    def refresh_system(self):
        for child in self.system_grid.get_children():
            self.system_grid.remove(child)
        os_release = {}
        for line in read_first("/etc/os-release").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip().strip('"')
        memory = read_first("/proc/meminfo").splitlines()
        mem_total = "—"
        for line in memory:
            if line.startswith("MemTotal:"):
                mem_total = human_bytes(int(line.split()[1]) * 1024)
                break
        try:
            uptime = human_seconds(float(read_first("/proc/uptime").split()[0]))
        except (ValueError, IndexError):
            uptime = "—"
        rows = [
            ("Sistema", os_release.get("PRETTY_NAME", "Corte OS")),
            ("Desarrollador", os_release.get("DEVELOPER", "gonzita")),
            ("Kernel", read_first("/proc/sys/kernel/osrelease").strip() or os.uname().release),
            ("Equipo", os.uname().nodename),
            ("Arquitectura", os.uname().machine),
            ("Memoria total", mem_total),
            ("Tiempo encendido", uptime),
            ("Sesión", os.environ.get("XDG_SESSION_TYPE", "—")),
            ("Escritorio", os.environ.get("XDG_CURRENT_DESKTOP", "XFCE")),
        ]
        self.system_text = "\n".join(f"{key}: {value}" for key, value in rows)
        for index, (key, value) in enumerate(rows):
            self.system_grid.attach(ui.label(key, "corte-hint"), 0, index, 1, 1)
            label = ui.label(value)
            label.set_selectable(True)
            self.system_grid.attach(label, 1, index, 1, 1)
        self.system_grid.show_all()

    def copy_system(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.system_text, -1)
        clipboard.store()
        ui.notify("Información copiada", "Los datos del sistema están en el portapapeles.", "low", "corte-settings")

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = SettingsApp()
    app.run()
    return 0
