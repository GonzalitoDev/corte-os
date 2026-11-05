import contextlib
import sys
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import GLib, Gtk, Pango  # noqa: E402

from ..common import db  # noqa: E402
from ..common import ui  # noqa: E402


def now():
    return datetime.now().isoformat(timespec="seconds")


class NotesApp:
    def __init__(self):
        self.conn = db.connect("notes.db")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                created TEXT NOT NULL,
                updated TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self.current_id = None
        self.loading = False
        self.save_source = None
        self.notes = []

        self.window = ui.window("Corte Notes", "corte-notes", (1040, 680))
        self.window.set_titlebar(ui.header("Corte Notes", "Notas locales con SQLite", "corte-notes"))

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.window.add(root)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_size_request(300, -1)
        sidebar.get_style_context().add_class("corte-sidebar")
        sidebar.set_border_width(10)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Buscar notas...")
        self.search.connect("search-changed", lambda *_: self.refresh())
        top.pack_start(self.search, True, True, 0)
        new_button = ui.icon_button("list-add-symbolic", "Nueva nota", self.new_note)
        top.pack_start(new_button, False, False, 0)
        sidebar.pack_start(top, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-selected", self.on_row_selected)
        sidebar.pack_start(ui.scrolled(self.listbox), True, True, 0)

        self.count_label = ui.label("0 notas", "corte-hint")
        sidebar.pack_start(self.count_label, False, False, 0)
        root.pack_start(sidebar, False, False, 0)

        editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.get_style_context().add_class("corte-toolbar")
        toolbar.set_border_width(8)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Título de la nota")
        self.title_entry.connect("changed", self.schedule_save)
        toolbar.pack_start(self.title_entry, True, True, 0)
        toolbar.pack_start(
            ui.icon_button("document-save-symbolic", "Guardar", self.save, "Guardar"),
            False,
            False,
            0,
        )
        toolbar.pack_start(
            ui.icon_button("document-save-as-symbolic", "Exportar", self.export, "Exportar"),
            False,
            False,
            0,
        )
        toolbar.pack_start(
            ui.icon_button("user-trash-symbolic", "Eliminar", self.delete_note),
            False,
            False,
            0,
        )
        editor.pack_start(toolbar, False, False, 0)

        self.text = Gtk.TextView()
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text.set_left_margin(22)
        self.text.set_right_margin(22)
        self.text.set_top_margin(18)
        self.text.set_bottom_margin(18)
        self.text.set_monospace(False)
        self.buffer = self.text.get_buffer()
        self.buffer.connect("changed", self.schedule_save)
        editor.pack_start(ui.scrolled(self.text), True, True, 0)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status.set_border_width(6)
        self.status = ui.label("Listo", "corte-hint")
        status.pack_start(self.status, True, True, 0)
        editor.pack_start(status, False, False, 0)
        root.pack_start(editor, True, True, 0)

        self.window.connect("destroy", self.on_destroy)
        self.refresh()
        self.window.show_all()

    def refresh(self, select_id=None):
        query = self.search.get_text().strip()
        if query:
            rows = self.conn.execute(
                "SELECT id, title, body, updated FROM notes "
                "WHERE title LIKE ? OR body LIKE ? ORDER BY updated DESC",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, title, body, updated FROM notes ORDER BY updated DESC"
            ).fetchall()
        self.notes = rows

        for child in self.listbox.get_children():
            self.listbox.remove(child)

        for row in rows:
            title = row["title"].strip() or "Nota sin título"
            preview = " ".join(row["body"].split())[:70]
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            title_label = ui.label(title, "corte-note-title")
            title_label.set_ellipsize(Pango.EllipsizeMode.END)
            box.pack_start(title_label, False, False, 0)
            if preview:
                preview_label = ui.label(preview, "corte-hint")
                preview_label.set_ellipsize(Pango.EllipsizeMode.END)
                box.pack_start(preview_label, False, False, 0)
            list_row = Gtk.ListBoxRow()
            list_row.note_id = row["id"]
            list_row.add(box)
            self.listbox.add(list_row)

        self.count_label.set_text(f"{len(rows)} nota{'s' if len(rows) != 1 else ''}")

        if select_id is not None:
            self.select_note(select_id)
        elif self.current_id is not None:
            self.select_note(self.current_id)
        elif rows:
            self.select_note(rows[0]["id"])
        else:
            self.current_id = None
            self.loading = True
            self.title_entry.set_text("")
            self.buffer.set_text("")
            self.loading = False

    def select_note(self, note_id):
        for row in self.listbox.get_children():
            if getattr(row, "note_id", None) == note_id:
                self.listbox.select_row(row)
                return
        if self.listbox.get_children():
            self.listbox.select_row(self.listbox.get_children()[0])

    def on_row_selected(self, _listbox, row):
        if row is None:
            return
        note_id = getattr(row, "note_id", None)
        if note_id is None:
            return
        self.load_note(note_id)

    def load_note(self, note_id):
        row = self.conn.execute(
            "SELECT id, title, body FROM notes WHERE id=?", (note_id,)
        ).fetchone()
        if row is None:
            return
        self.current_id = note_id
        self.loading = True
        self.title_entry.set_text(row["title"])
        self.buffer.set_text(row["body"])
        self.loading = False
        self.status.set_text("Nota cargada")

    def new_note(self):
        stamp = now()
        cursor = self.conn.execute(
            "INSERT INTO notes (title, body, created, updated) VALUES (?, ?, ?, ?)",
            ("Nota sin título", "", stamp, stamp),
        )
        self.conn.commit()
        note_id = cursor.lastrowid
        self.search.set_text("")
        self.refresh(select_id=note_id)
        self.title_entry.grab_focus()
        self.title_entry.select_region(0, -1)

    def schedule_save(self, *_args):
        if self.loading or self.current_id is None:
            return
        if self.save_source is not None:
            GLib.source_remove(self.save_source)
        self.save_source = GLib.timeout_add(700, self.save)

    def save(self):
        self.save_source = None
        if self.current_id is None or self.loading:
            return False
        title = self.title_entry.get_text().strip() or "Nota sin título"
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        body = self.buffer.get_text(start, end, True)
        self.conn.execute(
            "UPDATE notes SET title=?, body=?, updated=? WHERE id=?",
            (title, body, now(), self.current_id),
        )
        self.conn.commit()
        self.status.set_text(f"Guardado a las {datetime.now().strftime('%H:%M:%S')}")
        return False

    def delete_note(self):
        if self.current_id is None:
            return
        title = self.title_entry.get_text().strip() or "esta nota"
        if not ui.confirm(self.window, f"¿Eliminar «{title}»?", "Eliminar nota", True):
            return
        self.conn.execute("DELETE FROM notes WHERE id=?", (self.current_id,))
        self.conn.commit()
        self.current_id = None
        self.refresh()

    def export(self):
        if self.current_id is None:
            ui.info(self.window, "Selecciona una nota antes de exportarla.")
            return
        dialog = Gtk.FileChooserDialog(
            title="Exportar nota",
            transient_for=self.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL, "Guardar", Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        title = self.title_entry.get_text().strip() or "nota"
        safe = "".join(c for c in title if c.isalnum() or c in " -_").strip() or "nota"
        dialog.set_current_name(f"{safe}.txt")
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(self.buffer.get_text(start, end, True))
                self.status.set_text(f"Exportado a {path}")
            except OSError as exc:
                ui.error(self.window, str(exc), "No se pudo exportar")
        dialog.destroy()

    def on_destroy(self, *_args):
        self.save()
        self.conn.close()

    def run(self):
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ui.init_theme()
    app = NotesApp()
    if argv:
        with contextlib.suppress(Exception):
            app.load_note(int(argv[0]))
    app.run()
    return 0
