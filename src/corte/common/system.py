import os
import shutil
import subprocess
from pathlib import Path


def run(args, input_text=None, timeout=None, check=False, cwd=None, env=None):
    return subprocess.run(
        list(args),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
        cwd=cwd,
        env=env,
    )


def which(name):
    return shutil.which(name)


def run_privileged(args, input_text=None, timeout=None):
    if os.geteuid() == 0:
        return run(args, input_text=input_text, timeout=timeout)

    if which("sudo"):
        result = run(["sudo", "-n", *args], input_text=input_text, timeout=timeout)
        if result.returncode == 0:
            return result
        text = (result.stderr or "").lower()
        if "password" not in text and "not allowed" not in text:
            return result

    if which("pkexec"):
        return run(["pkexec", *args], input_text=input_text, timeout=timeout)

    return run(args, input_text=input_text, timeout=timeout)


def is_live():
    if Path("/run/live/medium").exists() or Path("/lib/live/mount/medium").exists():
        return True
    try:
        cmdline = Path("/proc/cmdline").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "boot=live" in cmdline


def human_bytes(value):
    value = float(value)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    if index == 0:
        return f"{int(value)} {units[index]}"
    return f"{value:.1f} {units[index]}"


def human_seconds(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days} d")
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if not parts:
        parts.append(f"{seconds} s")
    return " ".join(parts)


def read_first(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default


def notify(summary, body="", urgency="normal", icon="corte-welcome"):
    if not which("notify-send"):
        return
    try:
        subprocess.run(
            ["notify-send", "-a", "Corte OS", "-i", icon, "-u", urgency, summary, body],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def open_uri(uri):
    if which("xdg-open"):
        return subprocess.Popen(["xdg-open", uri])
    return None
