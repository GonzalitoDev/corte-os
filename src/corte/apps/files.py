import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from ..common import ui  # noqa: E402
from ..common.system import human_bytes  # noqa: E402

ATTRS = ",".join(
    [
        "standard::name",
        "standard::display-name",
        "standard::icon",
        "standard::type",
        "standard::size",
        "standard::is-hidden",
        "time::modified",
    ]
)


def display_path(file):
    path = file.get_path()
    if path:
        return path
    return file.get_uri()


def unique_destination(destination):
    if not destination.query_exists(None):
        return destination
    parent = destination.get_parent()
    name = destination.get_basename() or "archivo"
    stem, suffix = os.path.splitext(name)
    if not suffix:
        stem, suffix = name, ""
    counter = 1
    while True:
        label = f"{stem} (copia)" if counter == 1 else f"{stem} (copia {counter})"
        candidate = parent.get_child(label + suffix)
        if not candidate.query_exists(None):
            return candidate
        counter += 1


def copy_tree(source, destination):
    info = source.query_info(
        "standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
    )
    if info.get_file_type() == Gio.FileType.DIRECTORY:
        if not destination.make_directory(None):
            raise RuntimeError("No se pudo crear el directorio de destino")
        enumerator = source.enumerate_children(
            "standard::name,standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
        )
        while True:
            child_info = enumerator.next_file(None)
            if child_info is None:
                break
            name = child_info.get_name()
            copy_tree(source.get_child(name), destination.get_child(name))
    else:
        if not source.copy(
            destination,
            Gio.FileCopyFlags.NO_FOLLOW_SYMLINKS,
            None,
            None,
        ):
            raise RuntimeError("No se pudo copiar el archivo")


def delete_tree(file):
    info = file.query_info(
        "standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
    )
    if info.get_file_type() == Gio.FileType.DIRECTORY:
        enumerator = file.enumerate_children(
            "standard::name,standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None
        )
        while True:
            child_info = enumerator.next_file(None)
            if child_info is None:
                break
            delete_tree(file.get_child(child_info.get_name()))
    if not file.delete(None):
        raise RuntimeError("No se pudo eliminar el archivo original")


def move_tree(source, destination):
    try:
        if source.move(
            destination,
            Gio.FileCopyFlags.NO_FOLLOW_SYMLINKS,
            None,
            None,
        ):
            return
    except GLib.Error:
        pass
    copy_tree(source, destination)
    delete_tree(source)


class FilesApp:
    def __init__(self, initial=None):
        self.show_hidden = False
        self.current = None
        self.history = []
        self.history_index = -1
        self.monitor = None
        self.monitor_source = None
        self.clipboard = []
        self.clipboard_mode = None

        self.window = ui.window("Corte Files", "corte-files", (1180, 720))
        header = ui.header("Corte Files", "Explorador de archivos", "corte-files")
        self.window.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.window.add(root)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_size_request(210, -1)
        sidebar.set_border_width(10)
        sidebar.get_style_context().add_class("corte-sidebar")

        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        logo = Gtk.Image.new_from_icon_name("corte-files", Gtk.IconSize.DND)
        brand.pack_start(logo, False, False, 0)
        brand.pack_start(ui.label("Corte Files", "corte-row-title"), True, True, 0)
        sidebar.pack_start(brand, False, False, 0)

        self.places = Gtk.ListBox()
        self.places.set_selection_mode(Gtk.SelectionMode.NONE)
        self.places.connect("row-selected", self.on_place_selected)
        sidebar.pack_start(ui.scrolled(self.places), True, True, 0)
        root.pack_start(sidebar, False, False, 0)
        self.build_places()

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(content, True, True, 0)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.get_style_context().add_class("corte-toolbar")
        toolbar.set_border_width(7)
        toolbar.get_style_context().add_class("corte-nav")
        self.back_button = ui.icon_button("go-previous-symbolic", "Atrás", self.go_back)
        self.forward_button = ui.icon_button("go-next-symbolic", "Adelante", self.go_forward)
        self.up_button = ui.icon_button("go-up-symbolic", "Subir", self.go_up)
        self.home_button = ui.icon_button("go-home-symbolic", "Inicio", self.go_home)
        toolbar.pack_start(self.back_button, False, False, 0)
        toolbar.pack_start(self.forward_button, False, False, 0)
        toolbar.pack_start(self.up_button, False, False, 0)
        toolbar.pack_start(self.home_button, False, False, 0)

        self.path_entry = Gtk.Entry()
        self.path_entry.set_placeholder_text("Ruta o URI")
        self.path_entry.connect("activate", self.on_path_activated)
        toolbar.pack_start(self.path_entry, True, True, 0)

        toolbar.pack_start(
            ui.icon_button("view-refresh-symbolic", "Actualizar", self.reload),
            False,
            False,
            0,
        )
        toolbar.pack_start(
            ui.icon_button("folder-new-symbolic", "Nueva carpeta", self.new_folder),
            False,
            False,
            0,
        )
        menu_button = Gtk.MenuButton()
        menu_button.set_image(
            Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        )
        menu_button.set_tooltip_text("Más acciones")
        menu_button.set_popover(self.build_menu())
        toolbar.pack_start(menu_button, False, False, 0)
        content.pack_start(toolbar, False, False, 0)

        self.store = Gtk.ListStore(str, str, str, str, str, object, bool)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_enable_tree_lines(False)
        self.tree.set_headers_visible(True)
        self.tree.connect("row-activated", self.on_row_activated)
        self.tree.connect("button-press-event", self.on_tree_button)
        self.tree.connect("key-press-event", self.on_tree_key)

        icon_renderer = Gtk.CellRendererPixbuf()
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn("Nombre")
        name_column.pack_start(icon_renderer, False)
        name_column.pack_start(name_renderer, True)
        name_column.add_attribute(icon_renderer, "icon-name", 0)
        name_column.add_attribute(name_renderer, "text", 1)
        name_column.set_expand(True)
        name_column.set_resizable(True)
        name_column.set_min_width(280)
        self.tree.append_column(name_column)

        for title, index, width in (
            ("Tamaño", 2, 100),
            ("Tipo", 3, 170),
            ("Modificado", 4, 150),
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            column.set_min_width(width)
            self.tree.append_column(column)

        content.pack_start(ui.scrolled(self.tree, True), True, True, 0)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status.set_border_width(6)
        self.status = ui.label("", "corte-hint")
        status.pack_start(self.status, True, True, 0)
        content.pack_start(status, False, False, 0)

        self.window.connect("destroy", self.on_destroy)
        self.window.show_all()
        self.update_nav_buttons()

        if initial:
            if initial in ("trash", "trash:///", "papelera"):
                self.navigate(Gio.File.new_for_uri("trash:///"))
            elif initial.startswith("~"):
                self.navigate(Gio.File.new_for_path(os.path.expanduser(initial)))
            elif "://" in initial:
                self.navigate(Gio.File.new_for_uri(initial))
            else:
                self.navigate(Gio.File.new_for_path(initial))
        else:
            self.navigate(Gio.File.new_for_path(GLib.get_home_dir()))

    def build_places(self):
        home = GLib.get_home_dir()
        entries = [
            ("Inicio", "user-home-symbolic", home),
            ("Escritorio", "user-desktop-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or os.path.join(home, "Escritorio")),
            ("Documentos", "folder-documents-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) or os.path.join(home, "Documentos")),
            ("Descargas", "folder-download-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or os.path.join(home, "Descargas")),
            ("Imágenes", "folder-pictures-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or os.path.join(home, "Imágenes")),
            ("Música", "folder-music-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC) or os.path.join(home, "Música")),
            ("Vídeos", "folder-videos-symbolic", GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) or os.path.join(home, "Vídeos")),
            ("Papelera", "user-trash-symbolic", "trash:///"),
            ("Sistema", "drive-harddisk-symbolic", "/"),
        ]
        for label, icon, target in entries:
            row = Gtk.ListBoxRow()
            row.target = target
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            box.set_border_width(5)
            box.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            box.pack_start(ui.label(label), True, True, 0)
            row.add(box)
            self.places.add(row)
        self.places.show_all()

    def build_menu(self):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_border_width(6)
        actions = [
            ("Nueva carpeta", "folder-new-symbolic", self.new_folder),
            ("Renombrar", "document-edit-symbolic", self.rename_selected),
            ("Copiar", "edit-copy-symbolic", self.copy_selected),
            ("Cortar", "edit-cut-symbolic", self.cut_selected),
            ("Pegar", "edit-paste-symbolic", self.paste),
            ("Eliminar", "user-trash-symbolic", self.delete_selected),
            ("Propiedades", "dialog-information-symbolic", self.show_properties),
            ("Vaciar papelera", "user-trash-full-symbolic", self.empty_trash),
        ]
        for text, icon, callback in actions:
            button = Gtk.ModelButton()
            button.set_label(text)
            button.connect("clicked", lambda _b, cb=callback: (popover.popdown(), cb()))
            box.pack_start(button, False, False, 0)
        toggle = Gtk.CheckButton(label="Mostrar archivos ocultos")
        toggle.set_active(self.show_hidden)
        toggle.connect("toggled", self.on_hidden_toggled)
        box.pack_start(toggle, False, False, 0)
        box.show_all()
        popover.add(box)
        return popover

    def on_place_selected(self, _listbox, row):
        if row is None:
            return
        target = getattr(row, "target", None)
        if target == "trash:///":
            self.navigate(Gio.File.new_for_uri(target))
        else:
            self.navigate(Gio.File.new_for_path(target))

    def navigate(self, file, add_history=True):
        if file is None:
            return
        try:
            info = file.query_info(
                "standard::type,standard::is-symlink",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
            if info.get_file_type() != Gio.FileType.DIRECTORY:
                self.open_file(file)
                return
        except GLib.Error as exc:
            ui.error(self.window, f"No se puede abrir {display_path(file)}\n{exc.message}", "Corte Files")
            return

        if add_history:
            if self.history_index < len(self.history) - 1:
                self.history = self.history[: self.history_index + 1]
            self.history.append(file)
            self.history_index = len(self.history) - 1

        self.current = file
        self.path_entry.set_text(display_path(file))
        self.setup_monitor()
        self.load_directory()
        self.update_nav_buttons()

    def load_directory(self):
        if self.current is None:
            return
        self.store.clear()
        count_dirs = 0
        count_files = 0
        entries = []
        try:
            enumerator = self.current.enumerate_children(
                ATTRS, Gio.FileQueryInfoFlags.NONE, None
            )
            while True:
                info = enumerator.next_file(None)
                if info is None:
                    break
                name = info.get_name()
                if not self.show_hidden and info.get_is_hidden():
                    continue
                if not self.show_hidden and name.startswith("."):
                    continue
                entries.append(info)
        except GLib.Error as exc:
            ui.error(self.window, f"No se pudo leer la carpeta.\n{exc.message}", "Corte Files")
            return

        def sort_key(info):
            return (info.get_file_type() != Gio.FileType.DIRECTORY, info.get_display_name().lower())

        entries.sort(key=sort_key)
        for info in entries:
            is_dir = info.get_file_type() == Gio.FileType.DIRECTORY
            icon = info.get_icon()
            icon_name = icon.to_string() if icon is not None else ("folder" if is_dir else "text-x-generic")
            size = "—" if is_dir else human_bytes(info.get_size())
            if is_dir:
                kind = "Carpeta"
                count_dirs += 1
            else:
                kind = info.get_content_type() or "Archivo"
                count_files += 1
            modified = "—"
            date_time = info.get_modification_date_time()
            if date_time is not None:
                modified = date_time.format("%d/%m/%Y %H:%M")
            file = self.current.get_child(info.get_name())
            self.store.append(
                [icon_name, info.get_display_name(), size, kind, modified, file, is_dir]
            )

        location = display_path(self.current)
        self.status.set_text(
            f"{count_dirs} carpeta(s) · {count_files} archivo(s) · {location}"
        )
        self.window.set_title(f"Corte Files — {location}")

    def setup_monitor(self):
        if self.monitor_source is not None:
            GLib.source_remove(self.monitor_source)
            self.monitor_source = None
        if self.monitor is not None:
            self.monitor.cancel()
            self.monitor = None
        if self.current is None:
            return
        try:
            self.monitor = self.current.monitor_directory(Gio.FileMonitorFlags.NONE, None)
            self.monitor.connect("changed", self.on_directory_changed)
        except GLib.Error:
            self.monitor = None

    def on_directory_changed(self, *_args):
        if self.monitor_source is not None:
            GLib.source_remove(self.monitor_source)
        self.monitor_source = GLib.timeout_add(450, self.reload_from_monitor)

    def reload_from_monitor(self):
        self.monitor_source = None
        self.load_directory()
        return False

    def reload(self):
        self.load_directory()

    def update_nav_buttons(self):
        self.back_button.set_sensitive(self.history_index > 0)
        self.forward_button.set_sensitive(self.history_index < len(self.history) - 1)
        parent = self.current.get_parent() if self.current is not None else None
        self.up_button.set_sensitive(parent is not None)

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.navigate(self.history[self.history_index], add_history=False)

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.navigate(self.history[self.history_index], add_history=False)

    def go_up(self):
        if self.current is None:
            return
        parent = self.current.get_parent()
        if parent is not None:
            self.navigate(parent)

    def go_home(self):
        self.navigate(Gio.File.new_for_path(GLib.get_home_dir()))

    def on_path_activated(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        if "://" in text:
            self.navigate(Gio.File.new_for_uri(text))
        else:
            self.navigate(Gio.File.new_for_path(os.path.expanduser(text)))

    def selected_files(self):
        selection = self.tree.get_selection()
        model, paths = selection.get_selected_rows()
        files = []
        for tree_path in paths:
            tree_iter = model.get_iter(tree_path)
            files.append(model.get_value(tree_iter, 5))
        return files

    def on_row_activated(self, _tree, tree_path, _column):
        tree_iter = self.store.get_iter(tree_path)
        file = self.store.get_value(tree_iter, 5)
        is_dir = self.store.get_value(tree_iter, 6)
        if is_dir:
            self.navigate(file)
        else:
            self.open_file(file)

    def open_file(self, file):
        try:
            Gio.AppInfo.launch_default_for_uri(file.get_uri(), None)
        except GLib.Error as exc:
            ui.error(self.window, f"No hay una aplicación para abrir este archivo.\n{exc.message}", "Corte Files")

    def on_tree_button(self, tree, event):
        if event.button != 3:
            return False
        result = tree.get_path_at_pos(int(event.x), int(event.y))
        if result is not None:
            path = result[0]
            tree.get_selection().select_path(path)
        menu = Gtk.Menu()
        selected = bool(self.selected_files())
        entries = [
            ("Abrir", self.open_selected, selected),
            ("Renombrar", self.rename_selected, selected),
            ("Copiar", self.copy_selected, selected),
            ("Cortar", self.cut_selected, selected),
            ("Pegar", self.paste, bool(self.clipboard)),
            ("Eliminar", self.delete_selected, selected),
            ("Propiedades", self.show_properties, selected),
            ("Vaciar papelera", self.empty_trash, True),
        ]
        for text, callback, sensitive in entries:
            item = Gtk.MenuItem.new_with_label(text)
            item.set_sensitive(sensitive)
            item.connect("activate", lambda _i, cb=callback: cb())
            menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())
        hidden = Gtk.CheckMenuItem.new_with_label("Mostrar archivos ocultos")
        hidden.set_active(self.show_hidden)
        hidden.connect("toggled", self.on_hidden_toggled)
        menu.append(hidden)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def on_tree_key(self, _tree, event):
        if event.keyval == Gdk.KEY_Delete:
            self.delete_selected()
            return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            files = self.selected_files()
            if files:
                selection = self.tree.get_selection()
                _model, paths = selection.get_selected_rows()
                if paths:
                    self.on_row_activated(self.tree, paths[0], None)
            return True
        return False

    def on_hidden_toggled(self, widget):
        self.show_hidden = widget.get_active()
        self.load_directory()

    def new_folder(self):
        if self.current is not None and self.current.get_uri().startswith("trash:"):
            ui.error(self.window, "No se pueden crear carpetas dentro de la papelera.", "Corte Files")
            return
        name = ui.ask_text(self.window, "Nueva carpeta", "Nombre de la carpeta", "Nueva carpeta")
        if not name:
            return
        if "/" in name or name in (".", ".."):
            ui.error(self.window, "El nombre no es válido.", "Nueva carpeta")
            return
        target = self.current.get_child(name)
        try:
            target.make_directory(None)
            self.reload()
        except GLib.Error as exc:
            ui.error(self.window, exc.message, "No se pudo crear la carpeta")

    def rename_selected(self):
        if self.current is not None and self.current.get_uri().startswith("trash:"):
            ui.error(self.window, "No se pueden renombrar elementos desde la papelera.", "Corte Files")
            return
        files = self.selected_files()
        if len(files) != 1:
            ui.info(self.window, "Selecciona un solo archivo para renombrarlo.")
            return
        source = files[0]
        current_name = source.get_basename()
        new_name = ui.ask_text(self.window, "Renombrar", "Nuevo nombre", current_name)
        if not new_name or new_name == current_name:
            return
        if "/" in new_name:
            ui.error(self.window, "El nombre no puede contener '/'.", "Renombrar")
            return
        try:
            source.move(source.get_parent().get_child(new_name), Gio.FileCopyFlags.NONE, None, None)
            self.reload()
        except GLib.Error as exc:
            ui.error(self.window, exc.message, "No se pudo renombrar")

    def copy_selected(self):
        files = self.selected_files()
        if not files:
            return
        self.clipboard = files
        self.clipboard_mode = "copy"
        self.status.set_text(f"{len(files)} elemento(s) listos para copiar")

    def cut_selected(self):
        files = self.selected_files()
        if not files:
            return
        self.clipboard = files
        self.clipboard_mode = "cut"
        self.status.set_text(f"{len(files)} elemento(s) listos para mover")

    def paste(self):
        if not self.clipboard or self.current is None:
            return
        if self.current.get_uri().startswith("trash:"):
            ui.error(self.window, "No se puede pegar dentro de la papelera.", "Corte Files")
            return
        if self.clipboard_mode == "cut" and any(
            source.get_uri() == self.current.get_uri() for source in self.clipboard
        ):
            ui.error(self.window, "No puedes mover una carpeta dentro de sí misma.", "Pegar")
            return
        errors = []
        current_uri = self.current.get_uri().rstrip("/")
        for source in self.clipboard:
            source_uri = source.get_uri().rstrip("/")
            if current_uri == source_uri or current_uri.startswith(source_uri + "/"):
                errors.append(f"{source.get_basename()}: no se puede copiar una carpeta dentro de s? misma")
                continue
            destination = unique_destination(self.current.get_child(source.get_basename()))
            try:
                if self.clipboard_mode == "cut":
                    move_tree(source, destination)
                else:
                    copy_tree(source, destination)
            except (GLib.Error, RuntimeError) as exc:
                errors.append(f"{source.get_basename()}: {exc}")
        if self.clipboard_mode == "cut":
            self.clipboard = []
            self.clipboard_mode = None
        if errors:
            ui.error(self.window, "\n".join(errors[:8]), "Algunos elementos no se pudieron pegar")
        self.reload()

    def delete_selected(self):
        files = self.selected_files()
        if not files:
            return
        in_trash = self.current is not None and self.current.get_uri().startswith("trash:")
        action = "eliminar definitivamente" if in_trash else "mover a la papelera"
        if not ui.confirm(
            self.window,
            f"¿Vas a {action} {len(files)} elemento(s)?",
            "Eliminar",
            True,
        ):
            return
        errors = []
        for file in files:
            try:
                if in_trash:
                    file.delete(None)
                else:
                    file.trash(None)
            except GLib.Error as exc:
                errors.append(f"{file.get_basename()}: {exc.message}")
        if errors:
            ui.error(self.window, "\n".join(errors[:8]), "No se pudo eliminar todo")
        self.reload()

    def empty_trash(self):
        if not ui.confirm(self.window, "¿Vaciar la papelera de forma permanente?", "Vaciar papelera", True):
            return
        try:
            result = subprocess.run(
                ["gio", "trash", "--empty"], capture_output=True, text=True
            )
        except OSError as exc:
            ui.error(self.window, str(exc), "No se pudo vaciar la papelera")
            return
        if result.returncode != 0:
            ui.error(self.window, result.stderr.strip() or "gio devolvió un error.", "No se pudo vaciar la papelera")
        self.reload()

    def open_selected(self):
        files = self.selected_files()
        for file in files:
            try:
                info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, None)
                if info.get_file_type() == Gio.FileType.DIRECTORY:
                    self.navigate(file)
                    return
                self.open_file(file)
            except GLib.Error as exc:
                ui.error(self.window, exc.message, "No se pudo abrir")

    def show_properties(self):
        files = self.selected_files()
        if len(files) != 1:
            ui.info(self.window, "Selecciona un solo elemento para ver sus propiedades.")
            return
        file = files[0]
        try:
            info = file.query_info(
                "standard::name,standard::display-name,standard::type,standard::size,standard::content-type,time::modified,standard::is-symlink",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
        except GLib.Error as exc:
            ui.error(self.window, exc.message, "Propiedades")
            return
        is_dir = info.get_file_type() == Gio.FileType.DIRECTORY
        modified = "—"
        date_time = info.get_modification_date_time()
        if date_time is not None:
            modified = date_time.format("%d/%m/%Y %H:%M:%S")
        lines = [
            f"Nombre: {info.get_display_name()}",
            f"Tipo: {'Carpeta' if is_dir else (info.get_content_type() or 'Archivo')}",
        ]
        if not is_dir:
            lines.append(f"Tamaño: {human_bytes(info.get_size())}")
        lines.extend([f"Modificado: {modified}", f"Ruta: {display_path(file)}"])
        ui.info(self.window, "\n".join(lines), "Propiedades")

    def on_destroy(self, *_args):
        if self.monitor is not None:
            self.monitor.cancel()
        Gtk.main_quit()

    def run(self):
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ui.init_theme()
    app = FilesApp(argv[0] if argv else None)
    app.run()
    return 0
