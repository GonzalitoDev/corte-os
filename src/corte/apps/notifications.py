import html
import json
import re
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ..common import ui  # noqa: E402
from ..common.system import run, which  # noqa: E402


def strip_tags(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def timestamp(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return ""
    if value > 10**12:
        value = value / 1000.0
    elif value > 10**9:
        value = value
    else:
        return ""
    try:
        return datetime.fromtimestamp(value).strftime("%d/%m/%Y %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def field(item, name):
    value = item.get(name)
    if isinstance(value, dict):
        return value.get("data", "")
    return value or ""


class NotificationsApp:
    def __init__(self):
        self.window = ui.window("Corte Notifications", "corte-notifications", (860, 700))
        self.window.set_titlebar(ui.header("Corte Notifications", "Historial de notificaciones", "corte-notifications"))

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_border_width(10)
        toolbar.get_style_context().add_class("corte-toolbar")
        self.pause_button = ui.button("Pausar", self.toggle_pause, "media-playback-pause-symbolic")
        toolbar.pack_start(self.pause_button, False, False, 0)
        toolbar.pack_start(ui.button("Actualizar", self.refresh, "view-refresh-symbolic"), False, False, 0)
        toolbar.pack_start(ui.button("Cerrar todas", self.close_all, "window-close-symbolic"), False, False, 0)
        toolbar.pack_start(ui.button("Limpiar historial", self.clear_history, "edit-clear-symbolic"), False, False, 0)
        self.status = ui.label("", "corte-hint")
        toolbar.pack_start(self.status, True, True, 0)
        root.pack_start(toolbar, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        root.pack_start(ui.scrolled(self.listbox), True, True, 0)

        self.window.connect("destroy", Gtk.main_quit)
        self.refresh()
        self.window.show_all()

    def history(self):
        if not which("dunstctl"):
            return None, "dunstctl no está instalado."
        result = run(["dunstctl", "history"], timeout=10)
        if result.returncode != 0:
            return None, "No se pudo consultar dunst. Comprueba que el daemon de notificaciones está activo."
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return None, "dunstctl devolvió una respuesta no válida."
        data = payload.get("data") or []
        if data and isinstance(data[0], list):
            items = data[0]
        else:
            items = data
        return items, None

    def refresh(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        items, error = self.history()
        if error:
            self.status.set_text(error)
            self.listbox.add(ui.label(error, "corte-empty"))
            self.listbox.show_all()
            return
        if not items:
            self.status.set_text("No hay notificaciones en el historial.")
            self.listbox.add(ui.label("No hay notificaciones recientes.", "corte-empty"))
            self.listbox.show_all()
            return
        for item in items:
            summary = strip_tags(field(item, "summary"))
            body = strip_tags(field(item, "body"))
            appname = strip_tags(field(item, "appname")) or "Sistema"
            urgency = str(field(item, "urgency") or "NORMAL").lower()
            note_id = field(item, "id")
            when = timestamp(field(item, "timestamp"))
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            row.set_border_width(10)
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            title = ui.label(summary or "(sin título)", "corte-row-title")
            title.set_ellipsize(3)
            head.pack_start(title, True, True, 0)
            head.pack_start(ui.label(appname, "corte-hint"), False, False, 0)
            if urgency in ("critical", "crítica"):
                head.pack_start(ui.label("Crítica", "corte-status-bad"), False, False, 0)
            if when:
                head.pack_start(ui.label(when, "corte-hint"), False, False, 0)
            show = ui.icon_button("view-reveal-symbolic", "Mostrar de nuevo", lambda _b=None, n=note_id: self.show_notification(n))
            head.pack_start(show, False, False, 0)
            row.pack_start(head, False, False, 0)
            if body:
                body_label = ui.label(body, "corte-hint", True)
                body_label.set_ellipsize(3)
                row.pack_start(body_label, False, False, 0)
            container = Gtk.ListBoxRow()
            container.add(row)
            self.listbox.add(container)
        self.status.set_text(f"{len(items)} notificación(es) en el historial.")
        self.listbox.show_all()
        self.refresh_pause()

    def refresh_pause(self):
        result = run(["dunstctl", "is-paused"], timeout=5)
        paused = result.returncode == 0 and result.stdout.strip().lower() == "true"
        self.pause_button.set_label("Reanudar" if paused else "Pausar")
        self.pause_button.set_image(
            Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic" if paused else "media-playback-pause-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

    def toggle_pause(self):
        run(["dunstctl", "set-paused", "toggle"], timeout=5)
        self.refresh_pause()

    def show_notification(self, note_id):
        if note_id in (None, ""):
            return
        run(["dunstctl", "history-pop", str(note_id)], timeout=5)

    def close_all(self):
        run(["dunstctl", "close-all"], timeout=5)
        self.refresh()

    def clear_history(self):
        if not ui.confirm(self.window, "¿Borrar el historial de notificaciones de esta sesión?", "Limpiar historial"):
            return
        run(["dunstctl", "history-clear"], timeout=5)
        self.refresh()

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = NotificationsApp()
    app.run()
    return 0
