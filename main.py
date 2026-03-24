#!/usr/bin/env python3
# macstats: Minimal macOS menu bar stats app in Python
# - One menubar item shows selected stats (CPU, RAM, Network, Disk, Battery, experimental GPU)
# - App menu contains checkboxes to show/hide modules; "Save Settings" persists your choices
# - Built with rumps (Cocoa menu bar wrapper) and psutil for system metrics
#
# Requirements:
#   pip install rumps psutil
#
# Run:
#   python3 main.py
#
# Packaging (optional):
#   python3 setup.py py2app
#
# Notes:ck
# - GPU is marked experimental. Accurate GPU utilization on macOS isn't exposed via psutil.
#   You can try powermetrics (Apple Silicon, requires sudo) and adapt the placeholder in get_gpu().
# - On first run, a config file is created at ~/.macstats/config.json

import os
import sys
import json
import time
import shutil
import socket
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Tuple

import rumps
import psutil

# ---------------------------------------------------------------------------
# Version — read from bundled VERSION file so it stays in sync with releases
# ---------------------------------------------------------------------------
def _read_version() -> str:
    """Read version from the VERSION file, whether running from source or a bundle."""
    # When frozen by PyInstaller, sys._MEIPASS points to the bundle root
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    version_file = base / 'VERSION'
    try:
        return version_file.read_text().strip()
    except Exception:
        return '0.0.0'

APP_VERSION = _read_version()
GITHUB_REPO = 'codewithbro95/macstats'  # update if you rename the repo

APP_NAME = "MacStats"
CONFIG_DIR = Path.home() / ".macstats"
CONFIG_PATH = CONFIG_DIR / "config.json"

# ---------------------------------------------------------------------------
# Update checker
# ---------------------------------------------------------------------------
def _parse_version(v: str):
    """Return a tuple of ints for semver comparison, e.g. '1.2.3' → (1, 2, 3)."""
    v = v.lstrip('v')
    try:
        return tuple(int(x) for x in v.split('.'))
    except ValueError:
        return (0, 0, 0)

def check_for_update_bg(notify_no_update: bool = True):
    """Check GitHub Releases API for a newer version. Run on a background thread."""
    url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': f'{APP_NAME}/{APP_VERSION}'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        latest_tag = data.get('tag_name', '')
        latest_ver = latest_tag.lstrip('v')
        html_url = data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases')

        if _parse_version(latest_ver) > _parse_version(APP_VERSION):
            # Show notification on the main thread
            rumps.notification(
                title=APP_NAME,
                subtitle=f'Update available: v{latest_ver}',
                message='Click to open the download page.',
                action_button='Download',
            )
            # Open URL — rumps notifications don't have callbacks in all macOS versions,
            # so we open via subprocess as a fallback after a short delay.
            subprocess.Popen(['open', html_url])
        else:
            if notify_no_update:
                rumps.notification(
                    title=APP_NAME,
                    subtitle='You\'re up to date!',
                    message=f'Current version: v{APP_VERSION}',
                )
    except urllib.error.URLError:
        if notify_no_update:
            rumps.notification(
                title=APP_NAME,
                subtitle='Update check failed',
                message='Could not reach GitHub. Check your internet connection.',
            )
    except Exception:
        pass  # silently swallow unexpected errors

DEFAULT_CONFIG = {
    "modules": {
        "cpu": True,
        "mem": True,
        "net": True,
        "disk": False,
        "battery": True,
        "gpu": False  # experimental placeholder
    },
    "update_interval_sec": 1.0
}

SEPARATOR = " | "

def human_bytes(n: float) -> str:
    # Use powers of 1024 for friendliness
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n) < 1024.0:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"

def human_rate(bytes_per_sec: float) -> str:
    return f"{human_bytes(bytes_per_sec)}/s"

def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                # Gentle upgrade: ensure keys exist
                merged = DEFAULT_CONFIG.copy()
                merged["modules"] = {**DEFAULT_CONFIG["modules"], **cfg.get("modules", {})}
                merged["update_interval_sec"] = cfg.get("update_interval_sec", DEFAULT_CONFIG["update_interval_sec"])
                return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(CONFIG_PATH)

class MacStatsApp(rumps.App):
    def __init__(self):
        super(MacStatsApp, self).__init__(APP_NAME, quit_button=None)
        self.icon = None  # pure text title

        # State
        self.cfg = load_config()
        self.enabled = dict(self.cfg["modules"])
        self.update_interval = float(self.cfg.get("update_interval_sec", 1.0))

        # Network counters for rate calculation
        self._prev_net = None  # type: Tuple[int,int,float] | None

        # Build menu with checkable modules
        self.module_items: Dict[str, rumps.MenuItem] = {}
        self.menu = [
            rumps.MenuItem("MacStats", callback=None),
            None,  # separator
        ]

        def add_toggle(key: str, label: str):
            item = rumps.MenuItem(label, callback=lambda sender, k=key: self._toggle_module(k, sender))
            item.state = self.enabled.get(key, False)
            self.module_items[key] = item
            self.menu.add(item)

        add_toggle("cpu", "CPU usage")
        add_toggle("mem", "Memory usage")
        add_toggle("net", "Network rate")
        add_toggle("disk", "Disk free")
        add_toggle("battery", "Battery")
        add_toggle("gpu", "GPU (experimental)")

        self.menu.add(None)  # separator
        self.menu.add(rumps.MenuItem("Refresh now", callback=self._refresh_now))
        self.menu.add(rumps.MenuItem("Save settings", callback=self._save_settings))
        self.menu.add(None)  # separator
        self.menu.add(rumps.MenuItem(f"v{APP_VERSION}", callback=None))  # version display
        self.menu.add(rumps.MenuItem("Check for Update", callback=self._check_update))
        self.menu.add(rumps.MenuItem("Quit", callback=self._quit))

        # Timer for updates
        self.timer = rumps.Timer(self._tick, self.update_interval)
        self.timer.start()

        # Initial title
        self._update_title()

    #  Module toggling and persistence 
    def _toggle_module(self, key: str, sender: rumps.MenuItem):
        sender.state = not sender.state
        self.enabled[key] = bool(sender.state)
        self._update_title()

    def _save_settings(self, _):
        self.cfg["modules"] = dict(self.enabled)
        self.cfg["update_interval_sec"] = self.update_interval
        save_config(self.cfg)
        rumps.notification(title=APP_NAME, subtitle="Settings saved", message=str(CONFIG_PATH))

    #  App control 
    def _quit(self, _):
        rumps.quit_application()

    def _check_update(self, _):
        """Kick off an update check in a background thread so the UI stays responsive."""
        t = threading.Thread(target=check_for_update_bg, kwargs={'notify_no_update': True}, daemon=True)
        t.start()

    def _refresh_now(self, _):
        self._update_title(force=True)

    #  Timer tick 
    def _tick(self, _):
        self._update_title()

    #  Compose title 
    def _update_title(self, force: bool=False):
        parts = []

        try:
            if self.enabled.get("cpu"):
                parts.append(self.get_cpu())
        except Exception:
            parts.append("CPU ?")

        try:
            if self.enabled.get("mem"):
                parts.append(self.get_mem())
        except Exception:
            parts.append("RAM ?")

        try:
            if self.enabled.get("net"):
                parts.append(self.get_net_rate())
        except Exception:
            parts.append("Net ?")

        try:
            if self.enabled.get("disk"):
                parts.append(self.get_disk())
        except Exception:
            parts.append("Disk ?")

        try:
            if self.enabled.get("battery"):
                parts.append(self.get_battery())
        except Exception:
            parts.append("Bat ?")

        try:
            if self.enabled.get("gpu"):
                parts.append(self.get_gpu())
        except Exception:
            parts.append("GPU ?")

        s = SEPARATOR.join([p for p in parts if p])
        # Keep the title reasonably short to prevent overflow
        if len(s) > 120:
            s = s[:117] + "..."
        self.title = s if s else APP_NAME

    #  Metrics implementations 
    def get_cpu(self) -> str:
        # psutil.cpu_percent measures since last call; using interval=0 returns last computed value
        pct = psutil.cpu_percent(interval=None)
        # If pct is 0 at first call, compute a tiny sample so it's not misleading
        if pct == 0.0:
            pct = psutil.cpu_percent(interval=0.05)
        return f"CPU {pct:.0f}%"

    def get_mem(self) -> str:
        vm = psutil.virtual_memory()
        return f"RAM {vm.percent:.0f}%"

    def get_net_rate(self) -> str:
        now = time.time()
        nio = psutil.net_io_counters()
        sent = nio.bytes_sent
        recv = nio.bytes_recv
        if self._prev_net is None:
            self._prev_net = (sent, recv, now)
            return "↑0/s ↓0/s"
        prev_sent, prev_recv, prev_t = self._prev_net
        dt = max(1e-3, now - prev_t)
        up = (sent - prev_sent) / dt
        down = (recv - prev_recv) / dt
        self._prev_net = (sent, recv, now)
        return f"↑{human_rate(up)} ↓{human_rate(down)}"

    def get_disk(self) -> str:
        du = psutil.disk_usage("/")
        # show free space
        return f"Disk {human_bytes(du.free)} free"

    def get_battery(self) -> str:
        bat = psutil.sensors_battery()
        if bat is None:
            return "AC power"
        icon = "⚡︎" if bat.power_plugged else ""
        return f"Bat {bat.percent:.0f}%{icon}"

    def get_gpu(self) -> str:
        # Experimental placeholder. Try powermetrics on Apple Silicon if available.
        # Running powermetrics generally requires sudo for detailed samplers.
        pm = shutil.which("powermetrics")
        if not pm:
            return "GPU n/a"
        try:
            # A very short sample; if it fails without sudo, we just return n/a
            # Note: You can extend this parser to extract a useful number.
            out = subprocess.run(
                [pm, "-n", "1", "--samplers", "gpu_power"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1.5,
                check=False,
                text=True
            )
            if out.returncode != 0:
                return "GPU n/a"
            # Heuristic parse: look for a line with 'GPU' and a percent/residency if present
            pct = None
            for line in out.stdout.splitlines():
                line_low = line.lower()
                if "gpu" in line_low and "%" in line_low:
                    # extract the first number followed by %
                    import re
                    m = re.search(r'(\d+(?:\.\d+)?)\s*%', line_low)
                    if m:
                        pct = float(m.group(1))
                        break
            return f"GPU {pct:.0f}%" if pct is not None else "GPU n/a"
        except Exception:
            return "GPU n/a"


if __name__ == "__main__":
    MacStatsApp().run()
