<div align="center">

# Queen Browser

![Queen](https://img.shields.io/badge/Queen-Browser-3ecf8e?style=for-the-badge)
![AmmoOS](https://img.shields.io/badge/pairs-AmmoOS_2.0.0--beta4-22c55e?style=for-the-badge)

**Secured browser shell — AmmoOS field OS lives inside the Start tab.**

[AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · [Stack nav](https://zacharygeurts.github.io/ZacharyGeurts/stack.html) · [Manual](https://zacharygeurts.github.io/Queen/)

</div>

## Taskbar icon

The operator taskbar / start menu uses this asset (`panel/assets/ammoos-field.png` in the AmmoOS tree):

<p align="center">
  <img src="assets/queen-taskbar-icon.png" alt="Queen / AmmoOS taskbar icon" width="128" height="128" />
</p>

Configured in `Queen/gui/queen-theme-2026.json` → `branding.taskbar_icon`.

---

## Role in the stack

| Piece | What Queen is |
|-------|----------------|
| **Queen Browser** | Operator shell — tabs, gates, import, loopback-only egress |
| **Queen CANVAS** | RTX display renderer (`CANVAS.comp`) — **not** a GUI product |
| **AmmoOS inside** | Start tab embeds `http://127.0.0.1:9477/field` |

```
ZNetwork → Queen CANVAS → Queen Browser (:9481) → AmmoOS inside Start tab
```

Full stack: [STACK-NAV.md](https://github.com/ZacharyGeurts/AmmoOS/blob/main/STACK-NAV.md)

---

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9481/world/browser.html | Queen Browser chrome |
| http://127.0.0.1:9481/world/queen-game-room.html | Game Room |
| http://127.0.0.1:9481/world/queen-system-info.html | Emulator info + CHIPS |
| http://127.0.0.1:9481/world/queen-browser-guide.html | Operator guide |

NEXUS C2 and host desktop remain on **AmmoOS** `:9477`.

---

## Install (from AmmoOS)

Queen ships inside [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) `Queen/`. This repo is the **navigation hub** + branding assets.

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS && ./scripts/wire-stack.sh
./Queen/scripts/run-queen.sh
# or: ./Queen/build-field.sh && ./Queen/build/rtx/bin/Linux/queen-browser --queen
```

---

## Build (full tree)

```bash
cd Queen
./clone-all.sh
./build-field.sh
./build/rtx/bin/Linux/queen-browser --queen --extended-field
```

Vendor engines: FFmpeg (mandatory), Ladybird, Servo — see `Queen/README.md` in AmmoOS.

---

## Related repos

| Repo | Link |
|------|------|
| **AmmoOS** (leader) | https://github.com/ZacharyGeurts/AmmoOS |
| ZNetwork | https://github.com/ZacharyGeurts/ZNetwork |
| KILROY | https://github.com/ZacharyGeurts/KILROY |
| Display example | https://zacharygeurts.github.io/ZacharyGeurts/display-example.html |

---

## License

Ships with AmmoOS stack — see `Queen/LICENSE` in the canonical tree.