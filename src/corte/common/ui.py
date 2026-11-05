import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

EXTRA_CSS = """
.corte-page { padding: 18px; }
.corte-sidebar { background-color: #0a0f18; border-right: 1px solid #263244; }
.corte-sidebar row { padding: 8px 10px; border-radius: 8px; }
.corte-sidebar row:selected { background-color: #164e63; }
.corte-stat { background-color: #121926; border: 1px solid #263244; border-radius: 14px; padding: 14px; }
.corte-stat .value { font-size: 26px; font-weight: 800; color: #e6edf7; }
.corte-stat .name { font-size: 11px; color: #8a97ab; letter-spacing: 1px; }
.corte-display { font-size: 30px; font-weight: 700; padding: 14px; }
.corte-key { font-size: 15px; font-weight: 600; min-width: 48px; min-height: 42px; }
.corte-key.accent { color: #22d3ee; }
.corte-key.danger { color: #f87171; }
.corte-app-title { font-size: 22px; font-weight: 800; letter-spacing: 1px; }
.corte-hint { color: #8a97ab; font-size: 12px; }
.corte-code { font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; }
.corte-pill { background-color: #162133; border-radius: 999px; padding: 2px 9px; font-size: 11px; color: #9fc7d6; }
.corte-pill.online { color: #4ade80; }
.corte-pill.offline { color: #f87171; }
.corte-list-row { padding: 10px; border-bottom: 1px solid #1b2838; }
.corte-list-row:hover { background-color: #121b28; }
.corte-result { color: #22d3ee; }
.corte-note-title { font-weight: 700; }
.corte-empty { color: #8a97ab; font-size: 13px; padding: 20px; }
.corte-toolbar { padding: 6px; border-bottom: 1px solid #263244; }
.corte-banner { background-color: rgba(34, 211, 238, 0.08); border: 1px solid rgba(34, 211, 238, 0.24); border-radius: 12px; padding: 12px; }
.corte-danger-banner { background-color: rgba(248, 113, 113, 0.08); border: 1px solid rgba(248, 113, 113, 0.28); border-radius: 12px; padding: 12px; }
.corte-step { font-weight: 700; color: #22d3ee; }
.corte-mono-entry { font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; }
.corte-progress-log { font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; font-size: 11px; }
.corte-wallpaper { border: 2px solid transparent; border-radius: 10px; padding: 3px; }
.corte-wallpaper.selected { border-color: #22d3ee; }
.corte-wallpaper:hover { border-color: #35506a; }
.corte-row-title { font-weight: 700; }
.corte-path { color: #8a97ab; font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; font-size: 11px; }
.corte-nav button { border-radius: 8px; }
.corte-status-ok { color: #4ade80; font-weight: 700; }
.corte-status-bad { color: #f87171; font-weight: 700; }
.corte-status-warn { color: #fbbf24; font-weight: 700; }
.corte-tag { background-color: #0e1521; border: 1px solid #263244; border-radius: 8px; padding: 4px 8px; font-size: 11px; }
.corte-section-title { font-size: 15px; font-weight: 800; letter-spacing: 0.4px; }
.corte-scroll { background-color: transparent; }
.corte-terminal { background-color: #070b12; }
"""


def init_theme():
    try:
        Gtk.init(None)
    except Exception:
        pass
    settings = Gtk.Settings.get_default()
    if settings is not None:
        settings.set_property("gtk-application-prefer-dark-theme", True)
    provider = Gtk.CssProvider()
    provider.load_from_data(EXTRA_CSS.encode("utf-8"))
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def window(title, icon=None, default_size=(980, 680)):
    win = Gtk.Window()
    win.set_title(title)
    win.set_default_size(*default_size)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_border_width(0)
    if icon:
        win.set_icon_name(icon)
    win.connect("destroy", Gtk.main_quit)
    return win


def header(title, subtitle=None, icon=None):
    bar = Gtk.HeaderBar()
    bar.set_show_close_button(True)
    if subtitle or icon:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        if icon:
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
            image.set_pixel_size(28)
            box.pack_start(image, False, False, 0)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_label = Gtk.Label(label=title)
        title_label.set_halign(Gtk.Align.START)
        title_label.get_style_context().add_class("title")
        text_box.pack_start(title_label, False, False, 0)
        if subtitle:
            subtitle_label = Gtk.Label(label=subtitle)
            subtitle_label.set_halign(Gtk.Align.START)
            subtitle_label.get_style_context().add_class("dim-label")
            subtitle_label.set_ellipsize(Pango.EllipsizeMode.END)
            text_box.pack_start(subtitle_label, False, False, 0)
        box.pack_start(text_box, True, True, 0)
        bar.set_custom_title(box)
    else:
        bar.set_title(title)
    return bar


def icon_button(icon_name, tooltip, callback, label=None):
    button = Gtk.Button()
    if label:
        button.set_label(label)
        button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
        button.set_always_show_image(True)
    else:
        button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
        button.set_tooltip_text(tooltip)
    button.connect("clicked", lambda *_: callback())
    return button


def button(label, callback, icon=None, style=None):
    btn = Gtk.Button(label=label)
    if icon:
        btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        btn.set_always_show_image(True)
    if style:
        btn.get_style_context().add_class(style)
    btn.connect("clicked", lambda *_: callback())
    return btn


def label(text, style=None, wrap=False, xalign=0.0):
    widget = Gtk.Label(label=text)
    widget.set_xalign(xalign)
    widget.set_line_wrap(wrap)
    if style:
        widget.get_style_context().add_class(style)
    return widget


def scrolled(child, hscroll=False):
    window = Gtk.ScrolledWindow()
    window.set_shadow_type(Gtk.ShadowType.NONE)
    window.set_policy(
        Gtk.PolicyType.AUTOMATIC if hscroll else Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC,
    )
    window.add(child)
    window.get_style_context().add_class("corte-scroll")
    return window


def card(child, padding=14):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.set_border_width(padding)
    box.get_style_context().add_class("corte-stat")
    box.pack_start(child, True, True, 0)
    return box


def error(parent, message, title="Corte OS"):
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def info(parent, message, title="Corte OS"):
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.CLOSE,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def confirm(parent, message, title="Confirmar", destructive=False):
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.NONE,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    ok = dialog.add_button("Continuar", Gtk.ResponseType.OK)
    if destructive:
        ok.get_style_context().add_class("destructive-action")
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


def ask_text(parent, title, prompt, default="", secret=False):
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    dialog.add_button("Aceptar", Gtk.ResponseType.OK)
    dialog.set_default_size(420, 120)
    box = dialog.get_content_area()
    box.set_border_width(14)
    box.set_spacing(8)
    box.add(label(prompt))
    entry = Gtk.Entry()
    entry.set_text(default)
    if secret:
        entry.set_visibility(False)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
    entry.set_activates_default(True)
    box.add(entry)
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.show_all()
    response = dialog.run()
    text = entry.get_text()
    dialog.destroy()
    if response == Gtk.ResponseType.OK:
        return text
    return None


def run_async(func, on_success, on_error=None):
    def worker():
        try:
            result = func()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                GLib.idle_add(on_error, exc)
            return
        GLib.idle_add(on_success, result)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def add_shortcut(window, accel, callback):
    group = Gtk.AccelGroup()
    window.add_accel_group(group)
    key, mods = Gtk.accelerator_parse(accel)
    group.connect(key, mods, Gtk.AccelFlags.VISIBLE, lambda *_: callback())
