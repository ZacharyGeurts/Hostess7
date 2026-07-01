"""NEXUS hardware wire registry — detect and operate hooks for all field hardware."""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class HardwareWireClass:
    id: str
    label: str
    fd_markers: tuple[str, ...]
    middleman_procs: FrozenSet[str]
    hook_events: tuple[str, ...]


# Compositor, IME, browsers, and NEXUS field stack may hold hardware wires.
WIRE_ALLOWED = frozenset({
    "Xorg", "Xwayland", "gnome-shell", "kwin_x11", "kwin_wayland", "sway", "hyprland",
    "systemd-logind", "logind", "seatd",
    "ibus-daemon", "ibus-engine", "ibus-extension", "ibus-extension-", "ibus-x11", "ibus-wayland",
    "fcitx", "fcitx5",
    "threat-panel-http", "pythong", "python3", "python", "nexus-daemon", "nexus.sh",
    "nexus", "queen-browser", "fieldfox", "cursor", "firefox", "chrome", "chromium",
    "google-chrome", "google-chrome-stable", "brave", "brave-browser", "firefox-bin",
    "WebExtensions", "Isolated Web Co", "Socket Process", "RDD Process",
    "Privileged Cont", "Utility Process", "Renderer",
    "cinnamon", "cinnamon-sessio", "muffin", "mutter", "weston", "plasmashell",
    "kded5", "xfwm4", "openbox", "i3", "picom", "compton", "Xephyr",
    "pipewire", "pipewire-pulse", "wireplumber", "pulseaudio",
    "bluetoothd", "NetworkManager", "wpa_supplicant", "cupsd", "cups-browsed",
    "zenity", "yad", "kdialog", "dbus-daemon",
    "tcpdump", "nexus-packet",
})

NEXUS_BLOB_MARKERS = ("nexus", "queen", "fieldfox", "field-wave", "hostess7", "amouranthrtx")

INPUT_MIDDLEMAN = frozenset({
    "keylogger", "logkeys", "lkl", "kidlogger", "xinput", "showkey", "evtest",
    "intercept", "xbindkeys", "xbindkey", "xhotkey", "autokey", "skey", "keysniffer",
    "logkey", "pykeylogger", "pynput", "evemu-event", "evemu-record", "libinput-debug-events",
    "xev", "ydotool", "dotool", "xdotool", "xte", "xmacro", "xvkbd", "wmctrl",
    "remmina", "vnc", "x11vnc", "tigervnc", "teamviewer", "anydesk",
})

CLIPBOARD_MIDDLEMAN = frozenset({
    "copyq", "parcellite", "clipit", "clipman", "diodon", "greenclip", "klipper",
    "cliphist", "clipster", "gpaste", "clipmgr", "xclipboard", "autocutsel",
})

AUDIO_MIDDLEMAN = frozenset({
    "arecord", "parecord", "ecasound", "sox", "audacity", "ffmpeg", "ffplay",
    "gst-launch", "gst-launch-1.0", "pw-record", "pw-cat",
})

VIDEO_MIDDLEMAN = frozenset({
    "cheese", "guvcview", "fswebcam", "v4l2-ctl", "obs", "obs-studio", "obs-ffmpeg-mux",
    "wf-recorder", "gpu-screen-recorder", "kooha", "simplescreenrecorder",
    "recordmydesktop", "grim", "slurp", "wayshot", "spectacle", "peek", "scrot",
    "maim", "flameshot", "gnome-screenshot", "ksnip", "deepin-screenshot",
    "screengrab",
})

SERIAL_MIDDLEMAN = frozenset({
    "minicom", "screen", "cu", "microcom", "picocom", "gtkterm", "putty",
    "usbmon", "tshark", "wireshark",
})

NETWORK_MIDDLEMAN = frozenset({
    "wireshark", "tshark", "dumpcap", "bettercap", "mitmproxy", "mitmdump",
    "netsniff-ng", "tcpflow", "ngrep",
})

RF_MIDDLEMAN = frozenset({
    "rtl_fm", "rtl_sdr", "rtl_power", "gqrx", "sdrsharp", "hackrf_transfer",
    "rx_fm", "rx_sdr",
})

HARDWARE_CLASSES: tuple[HardwareWireClass, ...] = (
    HardwareWireClass(
        "input",
        "Keyboard / pointer / touch",
        ("/dev/input/event", "/dev/input/mice", "/dev/input/mouse", "/dev/input/by-path", "/dev/input/by-id"),
        INPUT_MIDDLEMAN,
        ("keydown", "keyup", "keypress", "beforeinput", "input", "pointerdown", "pointerup", "pointermove",
         "mousedown", "mouseup", "mousemove", "click", "dblclick", "wheel", "touchstart", "touchend", "touchmove"),
    ),
    HardwareWireClass(
        "audio",
        "Microphone / speaker / ALSA",
        ("/dev/snd/",),
        AUDIO_MIDDLEMAN,
        ("devicechange",),
    ),
    HardwareWireClass(
        "video",
        "Camera / V4L2",
        ("/dev/video",),
        VIDEO_MIDDLEMAN,
        ("devicechange",),
    ),
    HardwareWireClass(
        "gpu",
        "GPU / display (DRI)",
        (),
        frozenset({"glintercept", "apitrace", "renderdoc"}),
        ("devicechange",),
    ),
    HardwareWireClass(
        "serial",
        "USB serial / ACM",
        ("/dev/ttyUSB", "/dev/ttyACM", "/dev/serial"),
        SERIAL_MIDDLEMAN,
        (),
    ),
    HardwareWireClass(
        "network",
        "Packet capture / raw sockets",
        (),
        NETWORK_MIDDLEMAN,
        (),
    ),
    HardwareWireClass(
        "rf",
        "SDR / RTL dongle",
        (),
        RF_MIDDLEMAN,
        (),
    ),
    HardwareWireClass(
        "clipboard",
        "Clipboard / selection / secure vault wire",
        (),
        CLIPBOARD_MIDDLEMAN,
        ("copy", "cut", "paste", "beforeinput"),
    ),
)

BROWSER_DISPATCH_TYPES = (
    "KeyboardEvent", "MouseEvent", "PointerEvent", "TouchEvent", "WheelEvent", "InputEvent",
)

WIRE_CHAIN = [
    "hardware_bus",
    "nexus_hardware_wire",
    "compositor_or_nexus_engine",
    "nexus_front_hook",
    "panel_operator_only",
]