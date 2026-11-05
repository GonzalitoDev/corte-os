#!/usr/bin/env python3
import configparser
import json
import py_compile
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "__pycache__", "node_modules", "dist", "build/bootstrap", "build/chroot", "build/binary"}
TEXT_SUFFIXES = {
    ".py", ".sh", ".desktop", ".xml", ".md", ".html", ".css", ".js",
    ".json", ".service", ".conf", ".theme", ".gtkrc", ".svg", ".txt",
    ".yml", ".yaml",
}

errors = []
checked = 0


def iter_files():
    for path in ROOT.rglob("*"):
        if any(part in SKIP for part in path.parts):
            continue
        if path.is_file():
            yield path


def main():
    global checked
    for path in iter_files():
        suffix = path.suffix
        if suffix not in TEXT_SUFFIXES and path.name not in {
            "config", "corte", "corte-installer", "corte-ci-install", "VERSION"
        }:
            continue
        checked += 1
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"UTF-8 inválido: {path}: {exc}")
            continue
        if "\ufffd" in text:
            errors.append(f"Carácter de reemplazo en {path}")
        if suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"Python: {path}: {exc}")
        elif suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON: {path}: {exc}")
        elif suffix in (".xml", ".svg"):
            try:
                ET.fromstring(text)
            except ET.ParseError as exc:
                errors.append(f"XML/SVG: {path}: {exc}")
        elif suffix == ".desktop":
            parser = configparser.RawConfigParser()
            try:
                parser.read_string(text)
            except configparser.Error as exc:
                errors.append(f"Desktop: {path}: {exc}")
                continue
            if not parser.has_section("Desktop Entry"):
                errors.append(f"Desktop sin [Desktop Entry]: {path}")
                continue
            for key in ("Type", "Name", "Exec", "Icon"):
                if not parser.has_option("Desktop Entry", key):
                    errors.append(f"Desktop sin {key}: {path}")

    required = [
        ROOT / "VERSION",
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "LICENSE",
        ROOT / "build/build.sh",
        ROOT / "src/corte/__main__.py",
        ROOT / "src/corte/installer/backend.py",
        ROOT / "src/assets/logo.svg",
        ROOT / "src/assets/startpage.html",
        ROOT / "web/corte-os/index.html",
        ROOT / "web/corte-os/release.json",
        ROOT / "docs/INSTALL-VIRTUALBOX.md",
        ROOT / "docs/USER-MANUAL.md",
        ROOT / ".github/workflows/build-iso.yml",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Falta archivo requerido: {path}")

    if errors:
        print(f"Validación fallida ({len(errors)} errores, {checked} archivos revisados):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Validación OK: {checked} archivos revisados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
