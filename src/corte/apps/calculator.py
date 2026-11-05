import ast
import math
import operator
import sys
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ..common import db, ui  # noqa: E402

BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "round": round,
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


class CalculatorError(ValueError):
    pass


def evaluate(expression):
    expression = expression.strip()
    if not expression:
        raise CalculatorError("Escribe una operación.")
    if len(expression) > 500:
        raise CalculatorError("La expresión es demasiado larga.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("Sintaxis no válida.") from exc
    return _eval_node(tree.body, 0)


def _eval_node(node, depth):
    if depth > 40:
        raise CalculatorError("Expresión demasiado profunda.")
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise CalculatorError("Valor no permitido.")
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise CalculatorError(f"Nombre desconocido: {node.id}")
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
        left = _eval_node(node.left, depth + 1)
        right = _eval_node(node.right, depth + 1)
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000:
                raise CalculatorError("Exponente demasiado grande.")
            if abs(left) > 1e12:
                raise CalculatorError("Base demasiado grande.")
        try:
            result = BIN_OPS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("División entre cero.") from exc
        except OverflowError as exc:
            raise CalculatorError("Resultado fuera de rango.") from exc
        return result
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in FUNCTIONS:
            raise CalculatorError(f"Función desconocida: {node.func.id}")
        if node.keywords:
            raise CalculatorError("No se admiten argumentos con nombre.")
        if len(node.args) != 1:
            raise CalculatorError("Cada función necesita un argumento.")
        value = _eval_node(node.args[0], depth + 1)
        try:
            return FUNCTIONS[node.func.id](value)
        except (ValueError, OverflowError) as exc:
            raise CalculatorError("Argumento no válido para la función.") from exc
    raise CalculatorError("Operación no permitida.")


def format_number(value):
    if isinstance(value, complex):
        raise CalculatorError("El resultado no es real.")
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CalculatorError("Resultado no definido.")
        rounded = round(value, 10)
        if rounded.is_integer() and abs(rounded) < 1e15:
            return str(int(rounded))
        return f"{rounded:.10g}"
    return str(value)


class CalculatorApp:
    def __init__(self):
        self.conn = db.connect("calculator.db")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expression TEXT NOT NULL,
                result TEXT NOT NULL,
                created TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

        self.window = ui.window("Corte Calculator", "corte-calculator", (920, 660))
        self.window.set_titlebar(ui.header("Corte Calculator", "Cálculo local con historial", "corte-calculator"))

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.window.add(root)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left.set_border_width(14)
        root.pack_start(left, True, True, 0)

        self.display = Gtk.Entry()
        self.display.set_alignment(1.0)
        self.display.set_placeholder_text("0")
        self.display.get_style_context().add_class("corte-display")
        self.display.get_style_context().add_class("corte-mono-entry")
        self.display.connect("activate", lambda *_: self.calculate())
        left.pack_start(self.display, False, False, 0)

        self.status = ui.label("Listo", "corte-hint")
        left.pack_start(self.status, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        left.pack_start(grid, True, True, 0)

        buttons = [
            ("C", "clear", "danger"),
            ("⌫", "back", ""),
            ("(", "(", ""),
            (")", ")", ""),
            ("÷", "/", "accent"),
            ("7", "7", ""),
            ("8", "8", ""),
            ("9", "9", ""),
            ("×", "*", "accent"),
            ("√", "sqrt(", ""),
            ("4", "4", ""),
            ("5", "5", ""),
            ("6", "6", ""),
            ("−", "-", "accent"),
            ("x²", "**2", ""),
            ("1", "1", ""),
            ("2", "2", ""),
            ("3", "3", ""),
            ("+", "+", "accent"),
            ("π", "pi", ""),
            ("0", "0", ""),
            (".", ".", ""),
            ("%", "%", ""),
            ("=", "equals", "accent"),
            ("e", "e", ""),
        ]

        for index, (text, action, style) in enumerate(buttons):
            button = Gtk.Button(label=text)
            button.get_style_context().add_class("corte-key")
            if style:
                button.get_style_context().add_class(style)
            button.connect("clicked", lambda _b, a=action: self.press(a))
            grid.attach(button, index % 5, index // 5, 1, 1)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_size_request(300, -1)
        right.get_style_context().add_class("corte-sidebar")
        right.set_border_width(12)
        title = ui.label("Historial", "corte-section-title")
        right.pack_start(title, False, False, 0)
        clear = ui.button("Limpiar", self.clear_history, "edit-clear-symbolic")
        right.pack_start(clear, False, False, 0)
        self.history = Gtk.ListBox()
        self.history.set_selection_mode(Gtk.SelectionMode.NONE)
        right.pack_start(ui.scrolled(self.history), True, True, 0)
        root.pack_start(right, False, False, 0)

        self.refresh_history()
        self.window.show_all()
        self.display.grab_focus()

    def press(self, action):
        if action == "clear":
            self.display.set_text("")
            self.status.set_text("Listo")
            return
        if action == "back":
            text = self.display.get_text()
            self.display.set_text(text[:-1])
            return
        if action == "equals":
            self.calculate()
            return
        text = self.display.get_text()
        self.display.set_text(text + action)
        self.display.set_position(-1)

    def calculate(self):
        expression = self.display.get_text().strip()
        try:
            result = format_number(evaluate(expression))
        except CalculatorError as exc:
            self.status.set_text(str(exc))
            self.status.get_style_context().add_class("corte-danger")
            return
        except Exception:
            self.status.set_text("No se pudo calcular la expresión.")
            return
        self.status.get_style_context().remove_class("corte-danger")
        self.status.set_text(f"{expression} = {result}")
        self.display.set_text(result)
        self.conn.execute(
            "INSERT INTO history (expression, result, created) VALUES (?, ?, ?)",
            (expression, result, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()
        self.refresh_history()

    def refresh_history(self):
        for child in self.history.get_children():
            self.history.remove(child)
        rows = self.conn.execute(
            "SELECT expression, result FROM history ORDER BY id DESC LIMIT 60"
        ).fetchall()
        for row in rows:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            box.set_border_width(6)
            expr = ui.label(row["expression"], "corte-hint")
            expr.set_ellipsize(3)
            result = ui.label(row["result"], "corte-result")
            box.pack_start(expr, False, False, 0)
            box.pack_start(result, False, False, 0)
            list_row = Gtk.ListBoxRow()
            list_row.result = row["result"]
            list_row.add(box)
            list_row.connect("activate", self.on_history_activated)
            self.history.add(list_row)
        self.history.show_all()

    def on_history_activated(self, row):
        self.display.set_text(getattr(row, "result", ""))
        self.display.set_position(-1)

    def clear_history(self):
        if not ui.confirm(self.window, "¿Borrar todo el historial?", "Limpiar historial"):
            return
        self.conn.execute("DELETE FROM history")
        self.conn.commit()
        self.refresh_history()

    def run(self):
        self.window.connect("destroy", lambda *_: self.conn.close())
        Gtk.main()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ui.init_theme()
    app = CalculatorApp()
    if argv:
        app.display.set_text(" ".join(argv))
        app.calculate()
    app.run()
    return 0
