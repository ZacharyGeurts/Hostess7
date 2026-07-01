#!/usr/bin/env pythong
"""NEXUS panel system tray — left or right click opens tab picker."""
from __future__ import annotations

import atexit
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3  # noqa: E402

    HAS_APPINDICATOR = True
except (ImportError, ValueError):
    HAS_APPINDICATOR = False

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PORT = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
APP_ID_NEXUS = "nexus-shield-panel"
APP_ID_ZNETWORK = "znetwork-field-panel"
LAST_TAB_FILE = STATE / "panel-tray-last-tab.json"
TRAY_MODE_FILE = STATE / "znetwork-tray-mode.json"
OPERATOR_FILE = STATE / "znetwork-operator.json"
TRAY_LOCK = STATE / "panel-tray.lock"
PID_FILE = STATE / "panel-tray.pid"
_SERVE_LOCK_HANDLE = None

ZNETWORK_TAB_CHOICES: list[tuple[str, str]] = [
    ("ZNetwork · Secure Vault", "__vault__"),
    ("ZNetwork · Status", "system/settings"),
    ("ZNetwork · Connection", "packets/monitor"),
    ("ZNetwork · DNS truth", "dns"),
    ("ZNetwork · Gatekeeper", "threats/home-protector"),
    ("Command Center", "command"),
    ("Packets · Live", "packets/monitor"),
    ("Threats · Map", "threats/host-attack"),
    ("Revert tray to NEXUS", "__revert_tray__"),
]

TAB_CHOICES: list[tuple[str, str]] = [
    ("Command Center", "command"),
    ("Actions", "actions"),
    ("ZNetwork · Status", "system/settings"),
    ("US field", "us"),
    ("Packets · Live", "packets/monitor"),
    ("Packets · DPI", "packets/inspect"),
    ("Threats · Home", "threats/home-protector"),
    ("Threats · Map", "threats/host-attack"),
    ("Threats · Kill orders", "threats/human-dossier"),
    ("Intel · Honor", "intel/honor"),
    ("Intel · Field RF", "intel/field-rf"),
    ("Intel · Research", "intel/research"),
    ("Signals", "signals"),
    ("DNS", "dns"),
    ("Outside", "outside"),
    ("Library · Books", "library"),
    ("System · Settings", "system/settings"),
    ("System · Logs", "system/logs"),
]


def _panel_base() -> str:
    return f"http://127.0.0.1:{PORT}/field"


def _tray_mode() -> str:
    env_mode = os.environ.get("NEXUS_TRAY_MODE", "").strip().lower()
    if env_mode in ("znetwork", "nexus"):
        return env_mode
    try:
        doc = json.loads(TRAY_MODE_FILE.read_text(encoding="utf-8"))
        if doc.get("active") and str(doc.get("mode", "")).lower() == "znetwork":
            return "znetwork"
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    try:
        op = json.loads(OPERATOR_FILE.read_text(encoding="utf-8"))
        if str(op.get("choice", "")).lower() == "yes" and (
            op.get("running") is True or str(op.get("running")).lower() == "true"
        ):
            return "znetwork"
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return "nexus"


def _tab_choices() -> list[tuple[str, str]]:
    return ZNETWORK_TAB_CHOICES if _tray_mode() == "znetwork" else TAB_CHOICES


def _app_id() -> str:
    return APP_ID_ZNETWORK if _tray_mode() == "znetwork" else APP_ID_NEXUS


def _tray_title() -> str:
    if _tray_mode() == "znetwork":
        try:
            doc = json.loads(TRAY_MODE_FILE.read_text(encoding="utf-8"))
            title = str(doc.get("title") or "").strip()
            if title:
                return title
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return "Bypassed OS Networking"
    return "NEXUS Field Command Center — click or right-click for tabs"


def _tray_icon_source() -> Path:
    if _tray_mode() == "znetwork":
        for rel in (
            "panel/assets/znetwork-tray-24.png",
            "panel/assets/znetwork-tray-32.png",
            "panel/assets/znetwork-tray-22.png",
        ):
            p = INSTALL / rel
            if p.is_file() and p.stat().st_size > 0:
                return p
        return INSTALL / "panel" / "assets" / "znetwork-tray-24.png"
    for rel in (
        "panel/assets/queen-tray-24.png",
        "panel/assets/nexus-tray-us-24.png",
        "panel/assets/queen-tray.png",
        "panel/assets/nexus-tray-us.png",
        "Queen/world/assets/branding/amouranth-gentle.png",
        "panel/assets/nexus-shield.png",
        "assets/nexus-shield.png",
    ):
        p = INSTALL / rel
        if p.is_file() and p.stat().st_size > 0:
            return p
    return INSTALL / "panel" / "assets" / "nexus-shield.png"


def _icon_stamp(src: Path) -> str:
    try:
        st = src.stat()
        return f"{src}:{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        return ""


def _install_xdg_tray_icon(icon: Path) -> str:
    """Install 22/24/32 px tray icons so AppIndicator picks max taskbar resolution."""
    try:
        import importlib.util

        mod_path = INSTALL / "lib" / "panel-tray-icon.py"
        spec = importlib.util.spec_from_file_location("panel_tray_icon", mod_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if _tray_mode() == "znetwork" and hasattr(mod, "install_znetwork_xdg_icons"):
                mod.install_znetwork_xdg_icons(INSTALL)
                if icon.is_file() and icon.stat().st_size > 0:
                    return str(icon.resolve())
                return APP_ID_ZNETWORK
            mod.install_xdg_tray_icons(INSTALL)
            if icon.is_file() and icon.stat().st_size > 0:
                return str(icon.resolve())
            return APP_ID_NEXUS
    except Exception:
        pass
    home = Path(os.environ.get("HOME", "/home/default"))
    theme_icon = home / ".local/share/icons/hicolor/32x32/apps/nexus-shield-panel.png"
    try:
        theme_icon.parent.mkdir(parents=True, exist_ok=True)
        if icon.is_file() and icon.stat().st_size > 0:
            theme_icon.write_bytes(icon.read_bytes())
            subprocess.run(
                ["gtk-update-icon-cache", str(theme_icon.parent.parent)],
                capture_output=True,
                timeout=8,
            )
            return APP_ID_NEXUS
    except (OSError, subprocess.TimeoutExpired):
        pass
    return str(icon)


def _revert_tray_to_nexus() -> None:
    revert_py = INSTALL / "lib" / "znetwork-orchestrator.py"
    if revert_py.is_file():
        env = os.environ.copy()
        env.setdefault("NEXUS_INSTALL_ROOT", str(INSTALL))
        env.setdefault("NEXUS_STATE_DIR", str(STATE))
        py = shutil.which("pythong") or sys.executable
        try:
            subprocess.run([py, str(revert_py), "tray-revert"], env=env, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _ensure_tray_icon(*, force: bool = False) -> Path:
    znet = _tray_mode() == "znetwork"
    icon = STATE / ("znetwork-tray.png" if znet else "nexus-tray.png")
    icon.parent.mkdir(parents=True, exist_ok=True)
    try:
        import importlib.util

        mod_path = INSTALL / "lib" / "panel-tray-icon.py"
        spec = importlib.util.spec_from_file_location("panel_tray_icon", mod_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if znet and hasattr(mod, "build_znetwork_tray_icons"):
                return mod.build_znetwork_tray_icons(INSTALL, STATE, force=force)
            return mod.build_tray_icons(INSTALL, STATE, force=force)
    except Exception:
        pass
    src = _tray_icon_source()
    stamp_file = STATE / "nexus-tray-icon.stamp"
    stamp = _icon_stamp(src)
    if src.is_file():
        try:
            if (
                not force
                and icon.is_file()
                and icon.stat().st_size > 0
                and stamp_file.is_file()
                and stamp_file.read_text(encoding="utf-8", errors="replace").strip() == stamp
            ):
                return icon
            from PIL import Image

            img = Image.open(src).convert("RGBA").resize((24, 24), Image.Resampling.LANCZOS)
            img.save(icon, format="PNG")
            if stamp:
                stamp_file.write_text(stamp + "\n", encoding="utf-8")
            return icon
        except Exception:
            if icon.is_file() and icon.stat().st_size > 0:
                return icon
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(12, 2), (22, 8), (18, 22), (6, 22), (2, 8)], fill=(201, 162, 39, 255))
        draw.rectangle([(7, 7), (16, 11)], fill=(59, 130, 246, 255))
        img.save(icon, format="PNG")
    except Exception:
        icon.write_bytes(b"")
    return icon


def _save_last_tab(route: str) -> None:
    try:
        LAST_TAB_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_TAB_FILE.write_text(
            json.dumps({"route": route, "url": f"{_panel_base()}#{route}"}, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _load_last_tab() -> str:
    try:
        doc = json.loads(LAST_TAB_FILE.read_text(encoding="utf-8"))
        return str(doc.get("route") or "command")
    except (OSError, json.JSONDecodeError, TypeError):
        return "command"


def open_tab(route: str = "command") -> None:
    route = (route or "command").strip().lstrip("#")
    if route == "__revert_tray__":
        _revert_tray_to_nexus()
        return
    if route == "__vault__":
        route = "/field-znetwork-vault"
    _save_last_tab(route)
    opener = INSTALL / "lib" / "queen-panel-open.py"
    if not opener.is_file():
        return
    env = os.environ.copy()
    env.setdefault("NEXUS_INSTALL_ROOT", str(INSTALL))
    env.setdefault("NEXUS_STATE_DIR", str(STATE))
    queen = INSTALL / "Queen"
    if not queen.is_dir():
        for candidate in (
            INSTALL.parent / "Queen",
            Path(os.environ.get("SG_ROOT", str(INSTALL.parent))) / "Queen",
            Path(os.environ.get("SG_ROOT", str(INSTALL.parent))) / "NewLatest" / "Queen",
        ):
            if candidate.is_dir():
                queen = candidate
                break
    env.setdefault("QUEEN_ROOT", str(queen))
    env.setdefault("NEXUS_THREAT_PANEL_PORT", PORT)
    env.setdefault("QUEEN_WORLD_PORT", "9481")
    py = shutil.which("pythong") or sys.executable
    panel_url = (
        f"http://127.0.0.1:{PORT}{route}"
        if route.startswith("/field-")
        else ""
    )
    opener_argv = [py, str(opener), "url", panel_url] if panel_url else [py, str(opener), "nexus", route]
    try:
        subprocess.run(
            opener_argv,
            env=env,
            timeout=25,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


class TabPickerPopup(Gtk.Window):
    """Fast-track tab list — single click opens browser tab; no quit/cancel chrome."""

    def __init__(self) -> None:
        super().__init__(title="NEXUS-Shield — Tab")
        self.set_default_size(360, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        try:
            utility = getattr(Gtk, "WindowTypeHint", None)
            if utility is not None:
                self.set_type_hint(utility.UTILITY)
        except (AttributeError, TypeError):
            pass
        self.connect("delete-event", lambda *_: False)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        hint = Gtk.Label(label="Click a tab — opens immediately in Queen browser")
        hint.set_xalign(0)
        hint.set_line_wrap(True)
        outer.pack_start(hint, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(300)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        for label, route in _tab_choices():
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(8)
            box.set_margin_end(8)
            title = Gtk.Label(label=label)
            title.set_xalign(0)
            title.get_style_context().add_class("title")
            route_lbl = Gtk.Label(label=route)
            route_lbl.set_xalign(0)
            route_lbl.get_style_context().add_class("dim-label")
            box.pack_start(title, False, False, 0)
            box.pack_start(route_lbl, False, False, 0)
            row.add(box)
            row.route = route  # type: ignore[attr-defined]
            self.listbox.add(row)
        self.listbox.connect("row-activated", self._on_row_activated)
        scroll.add(self.listbox)
        outer.pack_start(scroll, True, True, 0)

        last_row = next(
            (row for row in self.listbox.get_children() if getattr(row, "route", None) == _load_last_tab()),
            None,
        )
        if last_row:
            self.listbox.select_row(last_row)
        self.add(outer)

    def _on_row_activated(self, _listbox, row) -> None:  # noqa: ANN001
        open_tab(str(getattr(row, "route", "command")))
        self.destroy()


def _populate_tray_flyout(menu: Gtk.Menu) -> None:
    """Fill tray menu with tab rows — dbus/AppIndicator needs each item shown individually."""
    for child in list(menu.get_children()):
        menu.remove(child)
        child.destroy()
    last = _load_last_tab()
    for label, route in _tab_choices():
        title = f"★ {label}" if route == last else label
        item = Gtk.MenuItem.new_with_label(title)
        item.connect("activate", lambda _w, r=route: open_tab(r))
        item.show()
        menu.append(item)


def build_tray_flyout_menu() -> Gtk.Menu:
    """Native tray flyout — menu anchored to the taskbar icon, not a popup window."""
    menu = Gtk.Menu()
    _populate_tray_flyout(menu)
    menu.show()
    return menu


def show_tab_picker(status_icon=None, button: int = 0, activate_time: int = 0) -> None:
    """Show the tray flyout menu (StatusIcon fallback path)."""
    menu = build_tray_flyout_menu()
    if status_icon is not None:
        menu.popup(None, None, status_icon.position_popup, status_icon, button, activate_time)
    else:
        menu.popup(None, None, None, None, button, activate_time)


class NexusTray:
    def __init__(self) -> None:
        force_icon = os.environ.get("NEXUS_TRAY_ICON_REFRESH", "0") == "1"
        icon_file = _ensure_tray_icon(force=force_icon)
        icon_ref = _install_xdg_tray_icon(icon_file)
        self._status_icon = None
        self._indicator = None
        self._flyout_menu = Gtk.Menu()
        self._flyout_menu.connect("show", self._refresh_flyout_menu)

        if HAS_APPINDICATOR and self._try_app_indicator(icon_ref):
            return
        self._try_status_icon(str(icon_file))

    def _refresh_flyout_menu(self, *_args) -> None:
        _populate_tray_flyout(self._flyout_menu)

    def _try_status_icon(self, icon_path: str) -> bool:
        try:
            icon = Gtk.StatusIcon()
            if Path(icon_path).is_file() and Path(icon_path).stat().st_size:
                icon.set_from_file(icon_path)
            else:
                icon.set_from_icon_name("security-high")
            icon.set_tooltip_text(_tray_title())
            icon.set_visible(True)
            icon.connect("activate", lambda ic, *_: show_tab_picker(ic, 1, Gtk.get_current_event_time()))
            icon.connect("popup-menu", lambda ic, btn, t: show_tab_picker(ic, btn, t))
            self._status_icon = icon
            return True
        except Exception:
            return False

    def _try_app_indicator(self, icon_ref: str) -> bool:
        try:
            icon_name = icon_ref
            if Path(icon_ref).is_file():
                if not Path(icon_ref).stat().st_size:
                    icon_name = "security-high"
            self._indicator = AyatanaAppIndicator3.Indicator.new(
                _app_id(),
                icon_name,
                AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
            self._indicator.set_title(_tray_title())
            _populate_tray_flyout(self._flyout_menu)
            self._indicator.set_menu(self._flyout_menu)
            return True
        except Exception:
            return False


def _release_tray_lock() -> None:
    global _SERVE_LOCK_HANDLE
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    if _SERVE_LOCK_HANDLE is not None:
        try:
            fcntl.flock(_SERVE_LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
            _SERVE_LOCK_HANDLE.close()
        except OSError:
            pass
        _SERVE_LOCK_HANDLE = None


def _pid_running_tray(pid: int) -> bool:
    """True only for a live python panel-tray.py daemon (not stale/bash PIDs)."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace")
    if "panel-tray.py open" in cmd:
        return False
    return "panel-tray.py" in cmd and "python" in cmd


def _tray_log(msg: str) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / "panel-tray.log").open("a", encoding="utf-8") as handle:
            handle.write(msg + "\n")
    except OSError:
        pass


def _acquire_tray_lock() -> bool:
    """Single GTK tray instance — second start exits quietly."""
    global _SERVE_LOCK_HANDLE
    STATE.mkdir(parents=True, exist_ok=True)
    if PID_FILE.is_file():
        try:
            old = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
            if _pid_running_tray(old):
                return False
        except (OSError, ValueError):
            pass
        PID_FILE.unlink(missing_ok=True)
    try:
        handle = open(TRAY_LOCK, "w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    except OSError:
        return False
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    _SERVE_LOCK_HANDLE = handle
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    atexit.register(_release_tray_lock)

    def _on_signal(_signum: int, _frame: object) -> None:
        _release_tray_lock()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    return True


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "open":
        open_tab(sys.argv[2] if len(sys.argv) > 2 else _load_last_tab())
        return 0
    if not _acquire_tray_lock():
        _tray_log(f"panel-tray lock held — exiting pid={os.getpid()}")
        return 0
    _tray_log(
        f"panel-tray started pid={os.getpid()} mode={_tray_mode()} "
        f"app_id={_app_id()} display={os.environ.get('DISPLAY', '')}"
    )
    Gtk.init(sys.argv)
    NexusTray()
    try:
        Gtk.main()
    finally:
        _tray_log(f"panel-tray stopping pid={os.getpid()}")
        _release_tray_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())