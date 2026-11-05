import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gio, GLib, Gst, Gtk  # noqa: E402

from ..common import ui  # noqa: E402


def format_time(nanoseconds):
    if nanoseconds is None or nanoseconds < 0:
        return "00:00"
    seconds = int(nanoseconds / Gst.SECOND)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class MediaApp:
    def __init__(self, initial=None):
        Gst.init(None)
        self.playlist = []
        self.current_index = -1
        self.updating = False
        self.duration = 0

        self.window = ui.window("Corte Media", "corte-media", (1120, 720))
        header = ui.header("Corte Media", "Reproductor GStreamer", "corte-media")
        self.window.set_titlebar(header)
        header.pack_start(
            ui.icon_button("document-open-symbolic", "Abrir archivos", self.open_files),
            False,
            False,
            0,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.window.add(root)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(main, True, True, 0)

        self.video_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.video_box.set_size_request(-1, 440)
        self.video_box.get_style_context().add_class("corte-terminal")
        main.pack_start(self.video_box, True, True, 0)

        self.playbin = Gst.ElementFactory.make("playbin", "player")
        if self.playbin is None:
            raise RuntimeError("No se pudo crear el elemento playbin de GStreamer.")
        self.playbin.set_property("volume", 0.8)

        sink = Gst.ElementFactory.make("gtksink", "video-sink")
        if sink is not None:
            widget = sink.get_property("widget")
            if widget is not None:
                widget.set_size_request(-1, 420)
                self.video_box.pack_start(widget, True, True, 0)
                self.playbin.set_property("video-sink", sink)
        else:
            self.video_box.pack_start(
                ui.label("El complemento de vídeo no está disponible. Se usará una ventana externa.", "corte-empty"),
                True,
                True,
                0,
            )
            self.playbin.set_property("video-sink", Gst.ElementFactory.make("autovideosink"))

        self.video_box.show_all()

        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.1)
        self.seek.set_draw_value(False)
        self.seek.set_sensitive(False)
        self.seek.connect("value-changed", self.on_seek)
        main.pack_start(self.seek, False, False, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_border_width(10)
        self.play_button = ui.icon_button("media-playback-start-symbolic", "Reproducir", self.toggle_play)
        self.stop_button = ui.icon_button("media-playback-stop-symbolic", "Detener", self.stop)
        self.prev_button = ui.icon_button("media-skip-backward-symbolic", "Anterior", self.previous)
        self.next_button = ui.icon_button("media-skip-forward-symbolic", "Siguiente", self.next)
        controls.pack_start(self.prev_button, False, False, 0)
        controls.pack_start(self.play_button, False, False, 0)
        controls.pack_start(self.stop_button, False, False, 0)
        controls.pack_start(self.next_button, False, False, 0)
        self.time_label = ui.label("00:00 / 00:00", "corte-hint")
        controls.pack_start(self.time_label, False, False, 0)
        controls.pack_start(ui.label("Volumen", "corte-hint"), False, False, 0)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume.set_value(80)
        self.volume.set_size_request(130, -1)
        self.volume.set_draw_value(False)
        self.volume.connect("value-changed", self.on_volume)
        controls.pack_start(self.volume, False, False, 0)
        main.pack_start(controls, False, False, 0)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        side.set_size_request(300, -1)
        side.set_border_width(10)
        side.get_style_context().add_class("corte-sidebar")
        side.pack_start(ui.label("Lista de reproducción", "corte-section-title"), False, False, 0)
        side.pack_start(
            ui.button("Añadir archivos", self.open_files, "list-add-symbolic"),
            False,
            False,
            0,
        )
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_playlist_activated)
        side.pack_start(ui.scrolled(self.listbox), True, True, 0)
        side.pack_start(ui.button("Quitar de la lista", self.remove_selected, "list-remove-symbolic"), False, False, 0)
        root.pack_start(side, False, False, 0)

        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_bus_error)
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::state-changed", self.on_state_changed)
        bus.connect("message::duration-changed", lambda *_: self.update_duration())

        self.window.connect("destroy", self.on_destroy)
        self.window.show_all()

        if initial:
            for path in initial:
                self.add_file(path)
            if self.playlist:
                self.play_index(0)

        self.timer = GLib.timeout_add(500, self.update_position)

    def open_files(self):
        dialog = Gtk.FileChooserDialog(
            title="Abrir multimedia",
            transient_for=self.window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Abrir", Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        media_filter = Gtk.FileFilter()
        media_filter.set_name("Audio y vídeo")
        for pattern in ("*.mp3", "*.ogg", "*.flac", "*.wav", "*.m4a", "*.mp4", "*.mkv", "*.webm", "*.avi", "*.mov", "*.ogv"):
            media_filter.add_pattern(pattern)
        dialog.add_filter(media_filter)
        all_filter = Gtk.FileFilter()
        all_filter.set_name("Todos los archivos")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        if dialog.run() == Gtk.ResponseType.OK:
            paths = dialog.get_filenames()
            for path in paths:
                self.add_file(path)
            if paths and self.current_index < 0:
                self.play_index(0)
        dialog.destroy()

    def add_file(self, path):
        if path in self.playlist:
            return
        self.playlist.append(path)
        row = Gtk.ListBoxRow()
        row.path = path
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_border_width(6)
        box.pack_start(Gtk.Image.new_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.MENU), False, False, 0)
        label = ui.label(os.path.basename(path))
        label.set_ellipsize(3)
        box.pack_start(label, True, True, 0)
        row.add(box)
        self.listbox.add(row)
        self.listbox.show_all()

    def on_playlist_activated(self, _listbox, row):
        path = getattr(row, "path", None)
        if path is None:
            return
        try:
            index = self.playlist.index(path)
        except ValueError:
            return
        self.play_index(index)

    def remove_selected(self):
        row = self.listbox.get_selected_row()
        if row is None:
            return
        path = getattr(row, "path", None)
        if path in self.playlist:
            index = self.playlist.index(path)
            self.playlist.pop(index)
            self.listbox.remove(row)
            if self.current_index == index:
                self.stop()
            elif self.current_index > index:
                self.current_index -= 1

    def play_index(self, index):
        if index < 0 or index >= len(self.playlist):
            return
        self.current_index = index
        path = self.playlist[index]
        uri = Gio.File.new_for_path(path).get_uri()
        self.playbin.set_state(Gst.State.READY)
        self.playbin.set_property("uri", uri)
        self.playbin.set_state(Gst.State.PLAYING)
        self.play_button.set_tooltip_text("Pausar")
        self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
        self.window.set_title(f"{os.path.basename(path)} — Corte Media")
        self.seek.set_sensitive(True)

    def toggle_play(self):
        state = self.playbin.get_state(0)[1]
        if state == Gst.State.PLAYING:
            self.playbin.set_state(Gst.State.PAUSED)
            self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON))
        elif self.current_index >= 0:
            self.playbin.set_state(Gst.State.PLAYING)
            self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON))

    def stop(self):
        self.playbin.set_state(Gst.State.NULL)
        self.current_index = -1
        self.seek.set_sensitive(False)
        self.seek.set_value(0)
        self.time_label.set_text("00:00 / 00:00")
        self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON))
        self.window.set_title("Corte Media")

    def previous(self):
        if not self.playlist:
            return
        index = (self.current_index - 1) % len(self.playlist)
        self.play_index(index)

    def next(self):
        if not self.playlist:
            return
        index = (self.current_index + 1) % len(self.playlist)
        self.play_index(index)

    def on_seek(self, scale):
        if self.updating or self.duration <= 0:
            return
        position = int(scale.get_value() * Gst.SECOND)
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            position,
        )

    def on_volume(self, scale):
        self.playbin.set_property("volume", scale.get_value() / 100.0)

    def update_duration(self):
        success, duration = self.playbin.query_duration(Gst.Format.TIME)
        if success and duration > 0:
            self.duration = duration
            self.updating = True
            self.seek.set_range(0, duration / Gst.SECOND)
            self.updating = False

    def update_position(self):
        if self.current_index < 0:
            return True
        self.update_duration()
        success, position = self.playbin.query_position(Gst.Format.TIME)
        if success and self.duration > 0:
            self.updating = True
            self.seek.set_value(position / Gst.SECOND)
            self.updating = False
            self.time_label.set_text(
                f"{format_time(position)} / {format_time(self.duration)}"
            )
        return True

    def on_state_changed(self, _bus, message):
        _old, new, _pending = message.parse_state_changed()
        if new == Gst.State.PLAYING:
            self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
        elif new in (Gst.State.PAUSED, Gst.State.READY):
            self.play_button.set_image(Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON))

    def on_eos(self, *_args):
        if self.current_index + 1 < len(self.playlist):
            self.play_index(self.current_index + 1)
        else:
            self.stop()

    def on_bus_error(self, _bus, message):
        error, debug = message.parse_error()
        ui.error(
            self.window,
            f"{error.message}\n\n{debug or ''}".strip(),
            "Error de reproducción",
        )
        self.stop()

    def on_destroy(self, *_args):
        if hasattr(self, "timer"):
            GLib.source_remove(self.timer)
        self.playbin.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def run(self):
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ui.init_theme()
    app = MediaApp(argv)
    app.run()
    return 0
