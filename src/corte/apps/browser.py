import sys
import urllib.parse
import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, Gtk, WebKit2  # noqa: E402

from ..common import ui  # noqa: E402

START_PAGE = Path("/usr/share/corte/startpage.html")

ERROR_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#070b12;color:#e6edf7;
font-family:Inter,DejaVu Sans,sans-serif}}
.card{{max-width:620px;padding:34px;border:1px solid #263244;border-radius:18px;background:#101724}}
h1{{margin:0 0 10px;font-size:24px;color:#f87171}}
p{{color:#9aa7ba;line-height:1.6}}
code{{color:#22d3ee;background:#0b111b;padding:2px 6px;border-radius:6px}}
</style></head><body><div class="card">
<h1>No se pudo cargar la página</h1>
<p>{message}</p>
<p>Comprueba la dirección y la conexión de red. Corte OS funciona sin Internet,
pero el navegador necesita red para abrir sitios externos.</p>
<p><code>{uri}</code></p>
</div></body></html>"""


def normalize_url(text):
    text = text.strip()
    if not text:
        return str(START_PAGE.as_uri()) if START_PAGE.exists() else "about:blank"
    if "://" in text or text.startswith("about:") or text.startswith("file:"):
        return text
    if " " in text or "." not in text:
        return "https://duckduckgo.com/?q=" + urllib.parse.quote(text)
    return "https://" + text


class BrowserApp:
    def __init__(self, initial=None):
        self.window = ui.window("Corte Browser", "corte-browser", (1180, 780))
        header = ui.header("Corte Browser", "Navegador WebKitGTK", "corte-browser")
        self.window.set_titlebar(header)

        self.back_button = ui.icon_button("go-previous-symbolic", "Atrás", self.go_back)
        self.forward_button = ui.icon_button("go-next-symbolic", "Adelante", self.go_forward)
        self.reload_button = ui.icon_button("view-refresh-symbolic", "Recargar", self.reload)
        self.home_button = ui.icon_button("go-home-symbolic", "Inicio", self.go_home)
        header.pack_start(self.back_button, False, False, 0)
        header.pack_start(self.forward_button, False, False, 0)
        header.pack_start(self.reload_button, False, False, 0)
        header.pack_start(self.home_button, False, False, 0)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text("Dirección o búsqueda")
        self.url_entry.set_hexpand(True)
        self.url_entry.get_style_context().add_class("corte-mono-entry")
        self.url_entry.connect("activate", self.on_url_activated)
        title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title.set_size_request(620, -1)
        title.pack_start(self.url_entry, True, True, 0)
        header.set_custom_title(title)

        menu = Gtk.MenuButton()
        menu.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_border_width(6)
        for text, callback in (
            ("Acercar", lambda: self.zoom(0.1)),
            ("Alejar", lambda: self.zoom(-0.1)),
            ("Tamaño normal", lambda: self.set_zoom(1.0)),
            ("Abrir con navegador externo", self.open_external),
            ("Acerca de Corte Browser", self.about),
        ):
            button = Gtk.ModelButton()
            button.set_label(text)
            button.connect("clicked", lambda _b, cb=callback: (popover.popdown(), cb()))
            box.pack_start(button, False, False, 0)
        box.show_all()
        popover.add(box)
        menu.set_popover(popover)
        header.pack_end(menu, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(content)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        content.pack_start(self.progress, False, False, 0)

        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_property("enable-javascript", True)
        settings.set_property("enable-smooth-scrolling", True)
        settings.set_property("enable-page-cache", True)
        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("load-failed", self.on_load_failed)
        self.webview.connect("notify::title", self.on_title)
        self.webview.connect("notify::uri", self.on_uri)
        self.webview.connect("notify::estimated-load-progress", self.on_progress)
        content.pack_start(self.webview, True, True, 0)

        self.window.connect("key-press-event", self.on_key)
        self.window.connect("destroy", Gtk.main_quit)

        if initial:
            self.load(normalize_url(initial))
        elif START_PAGE.exists():
            self.load(START_PAGE.as_uri())
        else:
            self.load("about:blank")
        self.window.show_all()

    def load(self, uri):
        self.webview.load_uri(uri)

    def go_home(self):
        if START_PAGE.exists():
            self.load(START_PAGE.as_uri())
        else:
            self.load("about:blank")

    def go_back(self):
        if self.webview.can_go_back():
            self.webview.go_back()

    def go_forward(self):
        if self.webview.can_go_forward():
            self.webview.go_forward()

    def reload(self):
        self.webview.reload()

    def on_url_activated(self, _entry):
        self.load(normalize_url(self.url_entry.get_text()))

    def on_load_changed(self, _webview, event):
        if event == WebKit2.LoadEvent.STARTED:
            self.progress.set_fraction(0.0)
            self.update_nav()
        elif event == WebKit2.LoadEvent.FINISHED:
            self.progress.set_fraction(0.0)
            self.update_nav()

    def on_load_failed(self, _webview, _event, uri, error):
        message = error.message if error is not None else "Error desconocido"
        html = ERROR_PAGE.format(message=message, uri=uri)
        self.webview.load_html(html, "file:///")
        return True

    def on_title(self, *args):
        title = self.webview.get_title() or "Corte Browser"
        self.window.set_title(f"{title} — Corte Browser")

    def on_uri(self, *args):
        uri = self.webview.get_uri() or ""
        if uri and not uri.startswith("about:"):
            self.url_entry.set_text(uri)

    def on_progress(self, *args):
        fraction = self.webview.get_estimated_load_progress()
        self.progress.set_fraction(fraction)
        if fraction >= 1.0:
            self.progress.set_fraction(0.0)

    def update_nav(self):
        self.back_button.set_sensitive(self.webview.can_go_back())
        self.forward_button.set_sensitive(self.webview.can_go_forward())

    def zoom(self, delta):
        self.set_zoom(self.webview.get_zoom_level() + delta)

    def set_zoom(self, value):
        self.webview.set_zoom_level(max(0.5, min(2.5, value)))

    def open_external(self):
        uri = self.webview.get_uri()
        if uri:
            webbrowser.open(uri)

    def about(self):
        ui.info(
            self.window,
            "Corte Browser usa WebKitGTK 4.1.\n\n"
            "La página de inicio es local y funciona sin Internet. "
            "Los sitios externos necesitan conexión de red.",
            "Corte Browser",
        )

    def on_key(self, _window, event):
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        key = event.keyval
        if state & Gdk.ModifierType.CONTROL_MASK and key == Gdk.KEY_l:
            self.url_entry.grab_focus()
            self.url_entry.select_region(0, -1)
            return True
        if state & Gdk.ModifierType.CONTROL_MASK and key == Gdk.KEY_r:
            self.reload()
            return True
        if state & Gdk.ModifierType.ALT_MASK and key == Gdk.KEY_Left:
            self.go_back()
            return True
        if state & Gdk.ModifierType.ALT_MASK and key == Gdk.KEY_Right:
            self.go_forward()
            return True
        return False

    def run(self):
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ui.init_theme()
    app = BrowserApp(argv[0] if argv else None)
    app.run()
    return 0
