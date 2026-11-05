import os
from pathlib import Path

APP_ID = "corte-os"
APP_NAME = "Corte OS"


def _xdg(env_name, fallback):
    value = os.environ.get(env_name)
    if value:
        return Path(value) / "corte"
    return Path.home() / fallback / "corte"


def data_dir():
    path = _xdg("XDG_DATA_HOME", ".local/share")
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir():
    path = _xdg("XDG_CONFIG_HOME", ".config")
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir():
    path = _xdg("XDG_CACHE_HOME", ".cache")
    path.mkdir(parents=True, exist_ok=True)
    return path


def database(name):
    return data_dir() / name


def version():
    for candidate in (
        Path("/usr/share/corte/VERSION"),
        Path(__file__).resolve().parents[3] / "VERSION",
    ):
        try:
            return candidate.read_text(encoding="utf-8").strip() or "0.1.0"
        except OSError:
            continue
    return "0.1.0"


def share_dir():
    candidate = Path("/usr/share/corte")
    if candidate.is_dir():
        return candidate
    return Path(__file__).resolve().parents[2] / "assets"


def docs_dir():
    candidate = Path("/usr/share/doc/corte-os")
    if candidate.is_dir():
        return candidate
    return Path(__file__).resolve().parents[3] / "docs"
