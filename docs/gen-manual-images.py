#!/usr/bin/env pythong
"""Generate SVG diagrams for NEXUS-Shield io manual pages."""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "images"
OUT.mkdir(parents=True, exist_ok=True)

# Underlay F9 palette
C = {
    "bg": "#060806",
    "panel": "#141810",
    "panel2": "#1a1f14",
    "green": "#5a7a3a",
    "green_hi": "#7faa55",
    "brown": "#5c4332",
    "tan": "#a08050",
    "text": "#c5d4b0",
    "dim": "#6e7d62",
    "alert": "#c45c3a",
    "ok": "#6f9a52",
    "border": "#2a3324",
    "blue": "#4d8ab8",
}


def _svg_header(w: int, h: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img">\n'
        f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>\n'
    )


def _box(x, y, w, h, title, lines, fill=None, stroke=None):
    fill = fill or C["panel"]
    stroke = stroke or C["border"]
    body = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>',
        f'<text x="{x + 12}" y="{y + 22}" fill="{C["green_hi"]}" font-family="Segoe UI,system-ui,sans-serif" font-size="13" font-weight="600">{title}</text>',
    ]
    ty = y + 42
    for line in lines:
        body.append(
            f'<text x="{x + 12}" y="{ty}" fill="{C["text"]}" font-family="Consolas,monospace" font-size="11">{line}</text>'
        )
        ty += 16
    return "\n".join(body)


def _arrow(x1, y1, x2, y2, label=""):
    mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
    parts = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["green"]}" stroke-width="2" marker-end="url(#arrow)"/>',
    ]
    if label:
        parts.append(
            f'<text x="{mid_x}" y="{mid_y - 6}" text-anchor="middle" fill="{C["dim"]}" '
            f'font-family="Segoe UI,sans-serif" font-size="10">{label}</text>'
        )
    return "\n".join(parts)


def arch_diagram() -> str:
    w, h = 920, 420
    s = _svg_header(w, h)
    s += (
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L6,3 L0,6 Z" fill="{C["green"]}"/></marker></defs>\n'
    )
    s += _box(40, 60, 200, 110, "Operator", ["Browser · CLI", "nexus.sh · nexus trust"])
    s += _box(360, 40, 200, 150, "Panel HTTP :9477", [
        "/field · /underlay-f9",
        "/api/* JSON",
        "threat-panel-http.py",
    ], fill=C["panel2"])
    s += _box(680, 60, 200, 110, "Field stack", ["Queen · Final_Eye", "Hostess7 · ZNetwork"])
    s += _box(360, 240, 200, 130, "nexus-genius.service", [
        "nexus-daemon.sh",
        "watchers · vigil loop",
        "boot-impl on start",
    ])
    s += _box(40, 250, 200, 100, "State I/O", [
        "/var/lib/nexus-shield",
        "threat-panel.json",
    ], stroke=C["brown"])
    s += _box(680, 250, 200, 100, "Perimeter", [
        "nftables · gatekeeper",
        "firewall-trusted.tsv",
    ], stroke=C["alert"])
    s += _arrow(240, 115, 360, 115, "HTTP")
    s += _arrow(560, 115, 680, 115, "assist")
    s += _arrow(460, 190, 460, 240, "supervise")
    s += _arrow(240, 300, 360, 295, "read/write")
    s += _arrow(560, 305, 680, 300, "enforce")
    s += (
        f'<text x="460" y="395" text-anchor="middle" fill="{C["tan"]}" '
        f'font-family="Segoe UI,sans-serif" font-size="12">NEXUS-Shield 10.4.3 — loopback-first field C2</text>\n'
    )
    return s + "</svg>\n"


def boot_io_diagram() -> str:
    w, h = 900, 300
    s = _svg_header(w, h)
    s += (
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L6,3 L0,6 Z" fill="{C["green"]}"/></marker></defs>\n'
    )
    steps = [
        (40, "Reboot / start", ["systemd ExecStartPre", "nexus-boot-impl.sh"]),
        (220, "Boot impl", ["wire-stack · paths", "sense meld · front-hook"]),
        (400, "First install?", ["migrate state", "sign MANIFEST"]),
        (580, "Daemon", ["integrity verify", "panel + watchers"]),
        (760, "Browser", ["panel-launched.boot", "open /field"]),
    ]
    x = 30
    for i, (_ox, title, lines) in enumerate(steps):
        s += _box(x, 80, 150, 100, title, lines, fill=C["panel2"] if i % 2 else C["panel"])
        if i < len(steps) - 1:
            s += _arrow(x + 150, 130, x + 170, 130)
        x += 170
    s += _box(220, 210, 460, 70, "Markers", [
        "first-boot.complete — full impl once",
        "boot-impl.last — mode=refresh each boot",
    ], stroke=C["ok"])
    return s + "</svg>\n"


def state_io_diagram() -> str:
    w, h = 920, 480
    s = _svg_header(w, h)
    files = [
        ("threat-panel.json", "Panel publish — live C2 state"),
        ("firewall-trusted.tsv", "Trust memory — forever peers"),
        ("firewall-blocks.tsv", "Active blocks — KILL chain"),
        ("vigil.state", "Paranoia / vigil mode"),
        ("hostess7-training-panel.json", "Training tracks + mastery"),
        ("field-sense-package-panel.json", "Eye · Ear · ZOCR meld"),
        ("boot-impl.last", "Boot refresh receipt"),
        ("panel-launched.boot", "Browser open per boot_id"),
    ]
    s += _box(40, 30, 840, 50, "NEXUS_STATE_DIR", ["/var/lib/nexus-shield  (prod)  ·  .nexus-state  (dev checkout)"], fill=C["panel2"])
    y = 100
    for i, (name, desc) in enumerate(files):
        col = 0 if i < 4 else 1
        row = i if i < 4 else i - 4
        x = 40 + col * 430
        yy = 100 + row * 88
        s += _box(x, yy, 400, 72, name, [desc], fill=C["panel"])
    s += (
        f'<text x="460" y="460" text-anchor="middle" fill="{C["dim"]}" '
        f'font-family="Segoe UI,sans-serif" font-size="11">Atomic writes · flock on publish · never commit state to git</text>\n'
    )
    return s + "</svg>\n"


def api_io_diagram() -> str:
    w, h = 920, 520
    s = _svg_header(w, h)
    groups = [
        ("Core", ["/api/status", "/api/threat-panel.json", "/api/gatekeeper", "/api/settings"]),
        ("Field", ["/api/field-stack", "/api/field-underlay", "/api/field-bus", "/api/sense-package"]),
        ("Hostess7", ["/api/hostess7/training/bundle", "/api/hostess7/training/assess", "/api/hostess7/brain-guard"]),
        ("Perimeter", ["/api/packet-field", "/api/port-ddos", "/api/field-polkit", "/api/tristate-installer"]),
    ]
    x = 40
    for title, routes in groups:
        lines = routes[:4]
        s += _box(x, 50, 200, 140, title, lines, fill=C["panel2"])
        x += 215
    s += _box(40, 220, 840, 90, "HTTP verbs", [
        "GET — json snapshots (most /api/* routes)",
        "POST — actions: trust, block, curriculum-step, tristate commit, meld cycle",
    ], stroke=C["blue"])
    pages = [
        ("/field", "Main C2 panel"),
        ("/underlay-f9", "Tristate / Underlay F9"),
        ("/tristate-installer", "Redirect → underlay-f9"),
    ]
    px = 40
    for path, desc in pages:
        s += _box(px, 340, 260, 70, path, [desc])
        px += 280
    s += _box(40, 430, 840, 70, "CLI I/O", [
        "nexus status · trust · block · verify  —  ./nexus.sh [--no-browser]  —  nexus-install-gui.sh",
    ], stroke=C["tan"])
    return s + "</svg>\n"


def hero_banner() -> str:
    w, h = 1200, 320
    s = _svg_header(w, h)
    s += (
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{C["panel2"]}"/><stop offset="100%" stop-color="{C["bg"]}"/></linearGradient></defs>\n'
        f'<rect width="{w}" height="{h}" fill="url(#g)"/>\n'
        # shield shape simplified
        f'<path d="M600,40 L680,70 L680,160 Q600,240 520,160 L520,70 Z" fill="{C["panel"]}" stroke="{C["green_hi"]}" stroke-width="2"/>\n'
        f'<text x="600" y="130" text-anchor="middle" fill="{C["blue"]}" font-family="Consolas,monospace" font-size="28" font-weight="700">N</text>\n'
        f'<text x="600" y="200" text-anchor="middle" fill="{C["text"]}" font-family="Segoe UI,sans-serif" font-size="36" font-weight="700">NEXUS-Shield</text>\n'
        f'<text x="600" y="235" text-anchor="middle" fill="{C["green_hi"]}" font-family="Segoe UI,sans-serif" font-size="16">Universal Protector · v10.4.3 · Field I/O Manual</text>\n'
        f'<text x="600" y="275" text-anchor="middle" fill="{C["dim"]}" font-family="Segoe UI,sans-serif" font-size="13">Panel · API · State · Installers · Underlay F9</text>\n'
    )
    return s + "</svg>\n"


def field_switch_safety_diagram() -> str:
    w, h = 920, 360
    s = _svg_header(w, h)
    s += (
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L6,3 L0,6 Z" fill="{C["green"]}"/></marker></defs>\n'
    )
    s += _box(40, 40, 200, 90, "Arrive", ["posture · scan", "always allowed"], fill=C["panel2"])
    s += _box(260, 40, 200, 90, "Transform", ["WRDT dry-run", "wave shed if warm"], fill=C["panel"])
    s += _box(480, 40, 200, 90, "Commit", ["underlay lock", "blocked only at crit"], fill=C["panel2"])
    s += _box(700, 40, 180, 90, "Reboot", ["KILROY Field", "crit gate only"], stroke=C["ok"])
    s += _arrow(240, 85, 260, 85)
    s += _arrow(460, 85, 480, 85)
    s += _arrow(680, 85, 700, 85)
    s += _box(40, 160, 400, 100, "No surprise slowdowns", [
        "NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN=1",
        "quota holds at field-max unless crit",
        "wave shed — not quota cuts at warn",
    ], stroke=C["ok"])
    s += _box(460, 160, 420, 100, "Thermal + conversion", [
        "field-switch-safety.py preflight",
        "conversion_ok · slowdown_guard",
        "non-destructive · same paths",
    ], stroke=C["blue"])
    s += _box(40, 280, 840, 60, "Markers", [
        "hotspot_advisory → wave shed  |  thermal_crit → defer commit/reboot  |  refresh stays light",
    ], fill=C["panel2"])
    return s + "</svg>\n"


def field_thermal_guard_diagram() -> str:
    w, h = 920, 400
    s = _svg_header(w, h)
    s += (
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L6,3 L0,6 Z" fill="{C["green"]}"/></marker></defs>\n'
    )
    s += _box(40, 40, 220, 100, "FieldWave update", [
        "entropyFabricPredict",
        "allow_update(num_ops)",
        "record_ops on pass",
    ], fill=C["panel2"])
    s += _box(300, 40, 220, 100, "Work budget", [
        "joules_per_field_op proxy",
        "max_joules_per_second",
        "1s rolling window",
    ], stroke=C["ok"])
    s += _box(560, 40, 320, 100, "Global redata", [
        "safe_global_redata — chunked",
        "max_global_redata_chunk",
        "NO monolithic blast",
    ], stroke=C["alert"])
    s += _arrow(260, 90, 300, 90)
    s += _arrow(520, 90, 560, 90)
    s += _box(40, 170, 400, 110, "Back-off path", [
        "projected_power > budget → sleep 5ms",
        "skip chunk this pass · quality scaling",
        "cold path: one atomic + timestamp",
    ], stroke=C["brown"])
    s += _box(460, 170, 420, 110, "NEXUS-Shield observability", [
        "hwmon + RAPL anomaly → gatekeeper tighten",
        "field thermal headroom X% log",
        "boot-test redata on first + refresh",
    ], stroke=C["blue"])
    s += _box(40, 310, 840, 70, "Landauer", [
        "kT ln 2 per bit erased — field entropy paths budget irreversible work before hard-drive global refresh",
    ], fill=C["panel2"])
    return s + "</svg>\n"


def main():
    files = {
        "hero-banner.svg": hero_banner(),
        "io-architecture.svg": arch_diagram(),
        "io-boot-flow.svg": boot_io_diagram(),
        "io-state-files.svg": state_io_diagram(),
        "io-api-surface.svg": api_io_diagram(),
        "field-switch-safety.svg": field_switch_safety_diagram(),
        "field-thermal-guard.svg": field_thermal_guard_diagram(),
    }
    for name, content in files.items():
        path = OUT / name
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()