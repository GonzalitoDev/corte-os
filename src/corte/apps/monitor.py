import os
import platform
import socket
import time
from collections import deque

import cairo
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk  # noqa: E402

try:
    import psutil
except ImportError:
    psutil = None

from ..common import ui  # noqa: E402
from ..common.system import human_bytes, human_seconds, read_first, run_privileged  # noqa: E402


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


class HistoryGraph(Gtk.DrawingArea):
    def __init__(self, color, title):
        super().__init__()
        self.color = color
        self.title = title
        self.values = deque(maxlen=60)
        self.set_size_request(-1, 150)
        self.connect("draw", self.on_draw)

    def push(self, value):
        self.values.append(max(0.0, min(100.0, float(value))))
        self.queue_draw()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        r, g, b = hex_rgb(self.color)
        cr.set_source_rgba(0.043, 0.063, 0.106, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.set_line_width(1)
        for index in range(1, 4):
            y = height * index / 4
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()
        for index in range(1, 8):
            x = width * index / 8
            cr.move_to(x, 0)
            cr.line_to(x, height)
            cr.stroke()
        if len(self.values) < 2:
            cr.set_source_rgba(0.55, 0.63, 0.74, 0.8)
            cr.select_font_face("Inter")
            cr.set_font_size(12)
            cr.move_to(12, 22)
            cr.show_text("Recopilando datos...")
            return False
        points = []
        count = len(self.values)
        for index, value in enumerate(self.values):
            x = width * index / max(1, count - 1)
            y = height - (value / 100.0) * height
            points.append((x, y))
        gradient = cairo.LinearGradient(0, 0, 0, height)
        gradient.add_color_stop_rgba(0, r, g, b, 0.38)
        gradient.add_color_stop_rgba(1, r, g, b, 0.02)
        cr.set_source(gradient)
        cr.move_to(points[0][0], height)
        for x, y in points:
            cr.line_to(x, y)
        cr.line_to(points[-1][0], height)
        cr.close_path()
        cr.fill()
        cr.set_source_rgba(r, g, b, 0.95)
        cr.set_line_width(2.0)
        cr.move_to(*points[0])
        for point in points[1:]:
            cr.line_to(*point)
        cr.stroke()
        last = self.values[-1]
        cr.set_source_rgba(0.9, 0.94, 0.98, 0.95)
        cr.select_font_face("Inter")
        cr.set_font_size(20)
        cr.move_to(12, 30)
        cr.show_text(f"{last:.1f}%")
        cr.set_source_rgba(0.55, 0.63, 0.74, 0.9)
        cr.set_font_size(11)
        cr.move_to(12, 48)
        cr.show_text(self.title.upper())
        return False


class MonitorApp:
    def __init__(self):
        if psutil is None:
            raise RuntimeError("Falta python3-psutil para ejecutar Corte Monitor.")

        self.window = ui.window("Corte Monitor", "corte-monitor", (1060, 720))
        self.window.set_titlebar(ui.header("Corte Monitor", "CPU, memoria, discos y procesos", "corte-monitor"))

        notebook = Gtk.Notebook()
        notebook.set_scrollable(True)
        self.window.add(notebook)

        overview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        overview.set_border_width(16)
        notebook.append_page(ui.scrolled(overview), Gtk.Label(label="Resumen"))

        cards = Gtk.Grid()
        cards.set_column_spacing(12)
        cards.set_row_spacing(12)
        cards.set_column_homogeneous(True)
        overview.pack_start(cards, False, False, 0)

        self.cpu_stat = self.make_stat("CPU", "—", "0%")
        self.ram_stat = self.make_stat("MEMORIA", "—", "0%")
        self.disk_stat = self.make_stat("DISCO", "—", "0%")
        self.uptime_stat = self.make_stat("SISTEMA", "—", "—")
        cards.attach(self.cpu_stat[0], 0, 0, 1, 1)
        cards.attach(self.ram_stat[0], 1, 0, 1, 1)
        cards.attach(self.disk_stat[0], 2, 0, 1, 1)
        cards.attach(self.uptime_stat[0], 3, 0, 1, 1)

        graphs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        graphs.set_homogeneous(True)
        self.cpu_graph = HistoryGraph("#22d3ee", "CPU")
        self.ram_graph = HistoryGraph("#a78bfa", "RAM")
        cpu_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cpu_frame.pack_start(ui.label("CPU", "corte-section-title"), False, False, 0)
        cpu_frame.pack_start(self.cpu_graph, True, True, 0)
        ram_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ram_frame.pack_start(ui.label("Memoria RAM", "corte-section-title"), False, False, 0)
        ram_frame.pack_start(self.ram_graph, True, True, 0)
        graphs.pack_start(cpu_frame, True, True, 0)
        graphs.pack_start(ram_frame, True, True, 0)
        overview.pack_start(graphs, True, True, 0)

        details = Gtk.Grid()
        details.set_column_spacing(24)
        details.set_row_spacing(8)
        details.set_border_width(4)
        overview.pack_start(details, False, False, 0)
        self.info_labels = {}
        for index, (key, title) in enumerate(
            [
                ("host", "Equipo"),
                ("kernel", "Kernel"),
                ("cpu", "Procesador"),
                ("cores", "Núcleos"),
                ("swap", "Swap"),
                ("load", "Carga media"),
            ]
        ):
            details.attach(ui.label(title, "corte-hint"), 0, index, 1, 1)
            value = ui.label("—")
            value.set_selectable(True)
            details.attach(value, 1, index, 1, 1)
            self.info_labels[key] = value

        processes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        processes.set_border_width(10)
        notebook.append_page(processes, Gtk.Label(label="Procesos"))

        process_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        process_toolbar.pack_start(
            ui.button("Actualizar", self.refresh_processes, "view-refresh-symbolic"),
            False,
            False,
            0,
        )
        process_toolbar.pack_start(
            ui.button("Finalizar proceso", self.kill_process, "process-stop-symbolic", "destructive-action"),
            False,
            False,
            0,
        )
        self.process_status = ui.label("", "corte-hint")
        process_toolbar.pack_start(self.process_status, True, True, 0)
        processes.pack_start(process_toolbar, False, False, 0)

        self.process_store = Gtk.ListStore(int, str, str, str, str, str)
        self.process_tree = Gtk.TreeView(model=self.process_store)
        for title, index, width in (
            ("PID", 0, 80),
            ("Proceso", 1, 260),
            ("Usuario", 2, 140),
            ("CPU %", 3, 80),
            ("RAM %", 4, 80),
            ("Estado", 5, 120),
        ):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_resizable(True)
            column.set_min_width(width)
            self.process_tree.append_column(column)
        processes.pack_start(ui.scrolled(self.process_tree, True), True, True, 0)

        disks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        disks.set_border_width(14)
        notebook.append_page(ui.scrolled(disks), Gtk.Label(label="Discos"))
        self.disk_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        disks.pack_start(self.disk_list, False, False, 0)
        disks.pack_start(
            ui.button("Actualizar discos", self.refresh_disks, "view-refresh-symbolic"),
            False,
            False,
            0,
        )

        self.window.connect("destroy", self.on_destroy)
        self.refresh_all()
        self.window.show_all()
        self.timer = GLib.timeout_add(1000, self.tick)
        self.process_timer = GLib.timeout_add(3000, self.refresh_processes)
        self.disk_timer = GLib.timeout_add(10000, self.refresh_disks)

    def make_stat(self, title, value, sub):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.set_border_width(14)
        card.get_style_context().add_class("corte-stat")
        name = ui.label(title, "name")
        name.get_style_context().add_class("corte-hint")
        value_label = ui.label(value, "value")
        value_label.get_style_context().add_class("value")
        sub_label = ui.label(sub, "corte-hint")
        card.pack_start(name, False, False, 0)
        card.pack_start(value_label, False, False, 0)
        card.pack_start(sub_label, False, False, 0)
        return card, value_label, sub_label

    def refresh_all(self):
        self.tick()
        self.refresh_processes()
        self.refresh_disks()

    def tick(self):
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_text = f"{human_bytes(disk.used)} / {human_bytes(disk.total)}"
        except OSError:
            disk_percent = 0
            disk_text = "No disponible"

        self.cpu_graph.push(cpu)
        self.ram_graph.push(memory.percent)

        self.cpu_stat[1].set_text(f"{cpu:.0f}%")
        self.cpu_stat[2].set_text(
            f"{psutil.cpu_count(logical=True) or 0} hilos · {psutil.cpu_count(logical=False) or 0} núcleos"
        )
        self.ram_stat[1].set_text(f"{memory.percent:.0f}%")
        self.ram_stat[2].set_text(f"{human_bytes(memory.used)} / {human_bytes(memory.total)}")
        self.disk_stat[1].set_text(f"{disk_percent:.0f}%")
        self.disk_stat[2].set_text(disk_text)
        uptime = time.time() - psutil.boot_time()
        self.uptime_stat[1].set_text(human_seconds(uptime))
        self.uptime_stat[2].set_text(platform.node() or socket.gethostname())

        self.info_labels["host"].set_text(socket.gethostname())
        self.info_labels["kernel"].set_text(platform.release())
        model = "—"
        for line in read_first("/proc/cpuinfo").splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
        self.info_labels["cpu"].set_text(model)
        self.info_labels["cores"].set_text(
            f"{psutil.cpu_count(logical=True)} lógicos / {psutil.cpu_count(logical=False)} físicos"
        )
        self.info_labels["swap"].set_text(
            f"{human_bytes(swap.used)} / {human_bytes(swap.total)}" if swap.total else "Sin swap"
        )
        try:
            load = os.getloadavg()
            self.info_labels["load"].set_text(f"{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}")
        except OSError:
            self.info_labels["load"].set_text("—")
        self.window.set_title(f"Corte Monitor — CPU {cpu:.0f}% · RAM {memory.percent:.0f}%")
        return True

    def refresh_processes(self):
        self.process_store.clear()
        rows = []
        for process in psutil.process_iter(
            ["pid", "name", "username", "cpu_percent", "memory_percent", "status"]
        ):
            try:
                info = process.info
                rows.append(
                    (
                        int(info["pid"] or 0),
                        info["name"] or "—",
                        info["username"] or "—",
                        f"{info['cpu_percent'] or 0:.1f}",
                        f"{info['memory_percent'] or 0:.1f}",
                        info["status"] or "—",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        rows.sort(key=lambda item: (-float(item[3]), -float(item[4])))
        for row in rows[:500]:
            self.process_store.append(row)
        self.process_status.set_text(f"{len(rows)} procesos · actualizado {time.strftime('%H:%M:%S')}")
        return True

    def kill_process(self):
        selection = self.process_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            ui.info(self.window, "Selecciona un proceso en la lista.")
            return
        pid = model.get_value(tree_iter, 0)
        name = model.get_value(tree_iter, 1)
        if not ui.confirm(
            self.window,
            f"¿Enviar SIGTERM al proceso {name} (PID {pid})?",
            "Finalizar proceso",
            True,
        ):
            return
        try:
            psutil.Process(pid).terminate()
        except psutil.AccessDenied:
            result = run_privileged(["kill", "-TERM", str(pid)], timeout=10)
            if result.returncode != 0:
                ui.error(self.window, result.stderr.strip() or "Permiso denegado.", "No se pudo finalizar")
        except psutil.NoSuchProcess:
            pass
        except Exception as exc:  # noqa: BLE001
            ui.error(self.window, str(exc), "No se pudo finalizar")
        self.refresh_processes()

    def refresh_disks(self):
        for child in self.disk_list.get_children():
            self.disk_list.remove(child)
        seen = set()
        for partition in psutil.disk_partitions(all=False):
            if partition.mountpoint in seen:
                continue
            seen.add(partition.mountpoint)
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except (PermissionError, OSError):
                continue
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.set_border_width(12)
            card.get_style_context().add_class("corte-stat")
            title = ui.label(partition.mountpoint, "corte-row-title")
            card.pack_start(title, False, False, 0)
            detail = ui.label(
                f"{partition.device} · {partition.fstype or 'desconocido'} · "
                f"{human_bytes(usage.used)} de {human_bytes(usage.total)} ({usage.percent:.0f}%)",
                "corte-hint",
            )
            card.pack_start(detail, False, False, 0)
            bar = Gtk.ProgressBar()
            bar.set_fraction(usage.percent / 100.0)
            bar.set_show_text(False)
            card.pack_start(bar, False, False, 0)
            self.disk_list.pack_start(card, False, False, 0)
        if not self.disk_list.get_children():
            self.disk_list.pack_start(ui.label("No se detectaron discos.", "corte-empty"), False, False, 0)
        self.disk_list.show_all()
        return True

    def on_destroy(self, *_args):
        if hasattr(self, "timer"):
            GLib.source_remove(self.timer)
        if hasattr(self, "process_timer"):
            GLib.source_remove(self.process_timer)
        if hasattr(self, "disk_timer"):
            GLib.source_remove(self.disk_timer)
        Gtk.main_quit()

    def run(self):
        Gtk.main()


def main(argv=None):
    ui.init_theme()
    app = MonitorApp()
    app.run()
    return 0
