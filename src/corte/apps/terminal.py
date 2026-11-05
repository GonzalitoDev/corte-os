import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")

from gi.repository import Gdk, GLib, Gtk, Pango, Vte  # noqa: E402

from ..common import ui  # noqa: E402

PALETTE = [
    "#070b12", "#f87171", "#4ade80", "#fbbf24",
    "#38bdf8", "#a78bfa", "#22d3ee", "#e6edf7",
    "#4b5563", "#fca5a5", "#86efac", "#fde68a",
    "#7dd3fc", "#c4b5fd", "#67e8f9", "#ffffff",
]


def rgba(value):
    color = Gdk.RGBA()
    color.parse(value)
    return color


class TerminalTab(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.app = app
        self.terminal = Vte.Terminal()
        self.terminal.set_scrollback_lines(20000)
        self.terminal.set_font(Pango.FontDescription("JetBrains Mono 10"))
        self.terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.terminal.set_mouse_autohide(True)
        self.terminal.set_colors(
            rgba("#e6edf7"), rgba("#070b12"), [rgba(color) for color in PALETTE]
        )
        self.terminal.connect("child-exited", self.on_child_exited)
        self.terminal.connect("button-press-event", self.on_button_press)
        scroller = Gtk.ScrolledWindow()
        scroller.set_shadow_type(Gtk.ShadowType.NONE)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.terminal)
        self.pack_start(scroller, True, True, 0)
        self.spawn()

    def spawn(self):
        try:
            self.terminal.spawn_async(
                Vte.PtyFlags.DEFAULT,
                os.path.expanduser("~"),
                ["/bin/bash", "-l"],
                None,
                GLib.SpawnFlags.DEFAULT,
                None,
                None,
                -1,
                None,
                self.on_spawned,
                None,
            )
        except Exception as exc:  # noqa: BLE001
            ui.error(self.app.window, str(exc), "No se pudo iniciar el terminal")

    def on_spawned(self, _terminal, pid, error, _data=None):
        if error is not None:
            ui.error(self.app.window, error.message, "No se pudo iniciar el terminal")

    def on_child_exited(self, *_args):
        self.app.close_tab(self)

    def on_button_press(self, terminal, event):
        if event.button != 3:
            return False
        menu = Gtk.Menu()
        copy_item = Gtk.MenuItem.new_with_label("Copiar")
        copy_item.connect("activate", lambda *_: terminal.copy_clipboard_format(Vte.Format.TEXT))
        paste_item = Gtk.MenuItem.new_with_label("Pegar")
        paste_item.connect("activate", lambda *_: terminal.paste_clipboard())
        all_item = Gtk.MenuItem.new_with_label("Seleccionar todo")
        all_item.connect("activate", lambda *_: terminal.select_all())
        clear_item = Gtk.MenuItem.new_with_label("Limpiar pantalla")
        clear_item.connect("activate", lambda *_: self.app.send_command(self, "clear\r"))
        for item in (copy_item, paste_item, all_item, Gtk.SeparatorMenuItem(), clear_item):
            menu.append(item)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True


class TerminalApp:
    def __init__(self):
        self.window = ui.window("Corte Terminal", "corte-terminal", (960, 620))
        header = ui.header("Corte Terminal", "Shell de Corte OS", "corte-terminal")
        self.window.set_titlebar(header)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.connect("page-added", lambda *_: self.notebook.set_show_tabs(self.notebook.get_n_pages() > 1))
        self.notebook.connect("page-removed", lambda *_: self.notebook.set_show_tabs(self.notebook.get_n_pages() > 1))
        self.window.add(self.notebook)

        header.pack_start(
            ui.icon_button("tab-new-symbolic", "Nueva pestaña", self.new_tab),
            False,
            False,
            0,
        )
        header.pack_end(
            ui.icon_button("edit-paste-symbolic", "Pegar", self.paste),
            False,
            False,
            0,
        )
        header.pack_end(
            ui.icon_button("edit-copy-symbolic", "Copiar", self.copy),
            False,
            False,
            0,
        )
        header.pack_end(
            ui.icon_button("edit-select-all-symbolic", "Seleccionar todo", self.select_all),
            False,
            False,
            0,
        )

        self.window.connect("destroy", Gtk.main_quit)
        self.new_tab()
        self.window.show_all()
        self.notebook.set_show_tabs(False)

    def current_tab(self):
        page = self.notebook.get_current_page()
        if page < 0:
            return None
        return self.notebook.get_nth_page(page)

    def new_tab(self):
        tab = TerminalTab(self)
        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        title = Gtk.Label(label="Terminal")
        close = Gtk.Button()
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        close.set_tooltip_text("Cerrar pestaña")
        close.connect("clicked", lambda *_: self.close_tab(tab))
        label_box.pack_start(title, True, True, 0)
        label_box.pack_start(close, False, False, 0)
        label_box.show_all()
        page = self.notebook.append_page(tab, label_box)
        self.notebook.set_tab_reorderable(tab, True)
        self.notebook.set_current_page(page)
        tab.terminal.grab_focus()
        return tab

    def close_tab(self, tab):
        page = self.notebook.page_num(tab)
        if page < 0:
            return
        self.notebook.remove_page(page)
        tab.destroy()
        if self.notebook.get_n_pages() == 0:
            self.new_tab()

    def send_command(self, tab, text):
        tab.terminal.feed_child(text.encode("utf-8"))

    def copy(self):
        tab = self.current_tab()
        if tab is not None:
            tab.terminal.copy_clipboard_format(Vte.Format.TEXT)

    def paste(self):
        tab = self.current_tab()
        if tab is not None:
            tab.terminal.paste_clipboard()

    def select_all(self):
        tab = self.current_tab()
        if tab is not None:
            tab.terminal.select_all()

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = TerminalApp()
    app.run()
    return 0
