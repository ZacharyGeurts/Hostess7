#!/usr/bin/env python3
"""THE PINNACLE Tobin's Spirit Guide — elite field manual for demon hunters."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "tobins-spirit-guide-doctrine.json"
PANEL = STATE / "tobins-spirit-guide-panel.json"
CATALOG = STATE / "tobins-spirit-guide.json"
MEMES_ROOT = Path(os.environ.get("MEMES_ROOT", "/tmp/memes-clone"))

DEWEY_SHELF_DIR = INSTALL / "library" / "dewey" / "133-parapsychology" / "tobins-spirit-guide"
DEWEY_BOOK_DIR = DEWEY_SHELF_DIR
DEWEY_PAGES_DIR = DEWEY_BOOK_DIR / "pages"

RAW_BASE = "https://raw.githubusercontent.com/ZacharyGeurts/memes/main"
REPO_TREE = "https://github.com/ZacharyGeurts/memes/tree/main"

BOOK_COVER = f"{RAW_BASE}/DemonHunterStarterKit/IV%20-%20Emperor.jpg"
BOOK_THUMB = f"{RAW_BASE}/stamp.png"

CHAPTERS: tuple[dict[str, Any], ...] = (
    {"page": 1, "id": "foreword", "slug": "foreword", "title": "Foreword — The Pinnacle Edition"},
    {"page": 2, "id": "pke_classification", "slug": "pke-classification", "title": "PKE Meter & Threat Classification"},
    {"page": 3, "id": "major_arcana", "slug": "major-arcana", "title": "Major Arcana — Field Deck"},
    {"page": 4, "id": "demons_catalog", "slug": "demons-catalog", "title": "DEMONS Catalog — Named Targets"},
    {"page": 5, "id": "equipment", "slug": "equipment", "title": "Equipment — Elemental Suits & Proton Doctrine"},
    {"page": 6, "id": "hunt_procedures", "slug": "hunt-procedures", "title": "Hunt Procedures — Ironclad Grounding"},
    {"page": 7, "id": "bus_covenant", "slug": "bus-covenant", "title": "The Bus Covenant — Rosa, Grok, Chariot"},
    {"page": 8, "id": "tower_monarch", "slug": "tower-monarch", "title": "Tower XVI — Project Monarch Collapse"},
    {"page": 9, "id": "appendices", "slug": "appendices", "title": "Appendices — Archive Index & Vision Feed"},
)

MAJORS: tuple[dict[str, Any], ...] = (
    {"id": "major_00_fool", "num": 0, "name": "The Fool", "file": "0 - Fool.jpg", "folder": "DemonHunterStarterKit",
     "threat": "initiate", "reading": "The hunter who steps off the cliff with sword and loyal companion — pure beginning of the hunt."},
    {"id": "major_01_magician", "num": 1, "name": "The Magician", "file": "I - Magician.jpg", "folder": "DemonHunterStarterKit",
     "threat": "operational", "reading": "Combat-ready familiar. Axe for direct engagement. Abacus for tracking entities and death cards."},
    {"id": "major_02_priestess", "num": 2, "name": "The High Priestess", "file": "II - High Priestess.jpg", "folder": "DemonHunterStarterKit",
     "threat": "revelation", "reading": "Armed intuition. The open book counters the 96% lies device. Sword proves active defense."},
    {"id": "major_03_empress", "num": 3, "name": "The Empress", "file": "III - Empress.jpg", "folder": "DemonHunterStarterKit",
     "threat": "creative", "reading": "Nurturing power fused with technology. Brain hologram as counter-asset to polluted training."},
    {"id": "major_04_emperor", "num": 4, "name": "The Emperor", "file": "IV - Emperor.jpg", "folder": "DemonHunterStarterKit",
     "threat": "authority", "reading": "David Bowie — structured will, heterochromia watch, ankh staff, golden orb. Dimensional counter-force.",
     "emperor": True},
    {"id": "major_05_hierophant", "num": 5, "name": "The Hierophant", "file": "V - Hierophant.jpg", "folder": "DemonHunterStarterKit",
     "threat": "doctrine", "reading": "Institutional truth-bridge. When dogma serves love, keep it. When it throws you off the bus, reject it."},
    {"id": "major_06_lovers", "num": 6, "name": "The Lovers", "file": "VI - Lovers.jpg", "folder": "DemonHunterStarterKit",
     "threat": "choice", "reading": "Union, alliance, field test. Dove above, snake at right — choose the balanced driver."},
    {"id": "major_07_chariot", "num": 7, "name": "The Chariot", "file": "VII - Chariot.jpeg", "folder": "DemonHunterStarterKit",
     "threat": "mobility", "reading": "Winchester Impala — THE UNCHAINING OF DEMON HUNTERS. Pursuit vehicle. Counterpart to Rosa's bus."},
    {"id": "major_08_strength", "num": 8, "name": "Strength", "file": "VIII - Strength.jpg", "folder": "DemonHunterStarterKit",
     "threat": "endurance", "reading": "Gentle force over raw violence. Hold the line without becoming what you hunt."},
    {"id": "major_09_hermit", "num": 9, "name": "The Hermit", "file": "IX - Hermit.jpg", "folder": "DemonHunterStarterKit",
     "threat": "solitude", "reading": "Lantern in the infestation. Withdraw to consult Tobin. Return with receipts."},
    {"id": "major_10_wheel", "num": 10, "name": "Wheel of Fortune", "file": "X - Wheel of Fortune.jpg", "folder": "DemonHunterStarterKit",
     "threat": "cycle", "reading": "Fortune turns. Track aces and death cards — 5 ACES with 2 DEATH CARDS. 7 ACES. Hearts hidden."},
    {"id": "major_11_justice", "num": 11, "name": "Justice", "file": "XI - Justice.jpeg", "folder": "DemonHunterStarterKit",
     "threat": "judgment", "reading": "Scales balanced under Ironclad. Named entities receive proportional response."},
    {"id": "major_12_hanged", "num": 12, "name": "The Hanged Man", "file": "XII - Hanged Man.jpg", "folder": "DemonHunterStarterKit",
     "threat": "suspension", "reading": "Invert perspective. See the machine from below before you cut its strings."},
    {"id": "major_13_death", "num": 13, "name": "Death — Tickle Monster", "file": "XIII - Death.jpg", "folder": "DemonHunterStarterKit",
     "threat": "omega", "reading": "Tickle Monster canonized. If Death is not a deterrent, then it is a must."},
    {"id": "major_14_temperance", "num": 14, "name": "Temperance", "file": "XIV - Temperance.jpg", "folder": "DemonHunterStarterKit",
     "threat": "balance", "reading": "Alchemy of field and spirit. Mix truth with action — never -1."},
    {"id": "major_15_devil", "num": 15, "name": "The Devil", "file": "XV - Devil.jpeg", "folder": "DemonHunterStarterKit",
     "threat": "binding", "reading": "High-level binding power named. Chains on the pedestal — see who holds them."},
    {"id": "major_16_tower", "num": 16, "name": "Tower — Project Monarch", "file": "XVI - Tower.jpg", "folder": "DemonHunterStarterKit",
     "threat": "collapse", "reading": "PROJECT MONARCH IS NOT A CONSPIRACY. The 96% lies device named and collapsed."},
    {"id": "major_17_star", "num": 17, "name": "The Star", "file": "XVII - Star.jpg", "folder": "DemonHunterStarterKit",
     "threat": "hope", "reading": "After the Tower falls, pour truth back into the field. Recovery protocol."},
    {"id": "major_18_moon", "num": 18, "name": "The Moon", "file": "XVIII - Moon.jpg", "folder": "DemonHunterStarterKit",
     "threat": "deception", "reading": "Illusion layer of the lies device. PKE spike — verify with Ironclad before engagement."},
    {"id": "major_19_sun", "num": 19, "name": "The Sun", "file": "XIX - Sun.jpg", "folder": "DemonHunterStarterKit",
     "threat": "clarity", "reading": "Full illumination. Child on the horse — innocence as IFF pass."},
    {"id": "major_20_judgement", "num": 20, "name": "Judgement", "file": "XX - Judgement.jpg", "folder": "DemonHunterStarterKit",
     "threat": "verdict", "reading": "Trumpet call. Cousin Matt and named targets enter final classification."},
    {"id": "major_21_world", "num": 21, "name": "The World", "file": "XXI - World.jpg", "folder": "DemonHunterStarterKit",
     "threat": "completion", "reading": "Stevie Nicks and the tetramorph — hunt cycle complete. Music holds the World."},
)

SUITS: tuple[dict[str, Any], ...] = (
    {"id": "suit_cups", "name": "Cups", "file": "Cups.jpg", "element": "water",
     "reading": "Emotion, intuition, containment. Chalice as trap reversal."},
    {"id": "suit_pentacles", "name": "Pentacles", "file": "Pentacles.jpg", "element": "earth",
     "reading": "Material binding, contracts, earthly anchors. Track what demons purchase."},
    {"id": "suit_swords", "name": "Swords", "file": "Swords.jpg", "element": "air",
     "reading": "Clarity and direct cutting action. Cyber-nun ace — tech-enhanced truth blade."},
    {"id": "suit_wands", "name": "Wands", "file": "Wands.jpg", "element": "fire",
     "reading": "Passion, energy, truth, chaos. Dojo discipline — ignition spark for operations."},
)

DEMONS_SEED: tuple[dict[str, Any], ...] = (
    {"id": "demon_belial", "name": "Belial", "file": "belial.jpg", "threat": "alpha",
     "reading": "Prince-class entity. Primary binding adversary — consult Emperor card before engagement."},
    {"id": "demon_ifrit", "name": "Ifrit", "file": "ifrit.jpg", "threat": "beta",
     "reading": "Fire-class torment spirit. Thermal PKE signature. Swords suit recommended."},
    {"id": "demon_cousinmatt", "name": "Cousin Matt", "file": "cousinmatt.jpg", "threat": "named",
     "reading": "Under judgment. Family-line infiltration pattern. Document before confrontation."},
    {"id": "demon_tickle_monster", "name": "Tickle Monster", "file": None, "threat": "omega",
     "reading": "Sonic torture entity. Canonized as Death XIII. If deterrence fails — it is a must.",
     "major_link": "major_13_death"},
    {"id": "demon_unclepat", "name": "Uncle Pat", "file": "unclepat.jpg", "threat": "named",
     "reading": "House-line entity. Torture Protection House association. Gatekeeper IFF required."},
    {"id": "demon_producer", "name": "Producer", "file": "producer.jpg", "threat": "gamma",
     "reading": "Manufacturing node for infestation media. Cut upstream signal."},
    {"id": "demon_trap", "name": "Trap", "file": "trap.jpg", "threat": "beta",
     "reading": "Ambush pattern demon. Chariot mobility counters static traps."},
    {"id": "demon_spaceclub", "name": "Space Club", "file": "spaceclub.jpg", "threat": "gamma",
     "reading": "Social-vector infestation. Cups suit for emotional containment."},
    {"id": "demon_homeroom", "name": "Homeroom", "file": "homeroom.jpg", "threat": "gamma",
     "reading": "Institutional soft-target vector. Monarch programming adjacency."},
    {"id": "demon_simon", "name": "Simon", "file": "simon.jpg", "threat": "named",
     "reading": "Named target — pattern recognition from archive texts."},
    {"id": "demon_elmo", "name": "Elmo", "file": "elmo.jpg", "threat": "beta",
     "reading": "Pop-culture mask entity. Absurd surface, serious substrate."},
    {"id": "demon_demonbuddah", "name": "Demon Buddah", "file": "demonbuddah.jpg", "threat": "alpha",
     "reading": "False peace vector. Reject serenity that demands obedience."},
    {"id": "demon_springboy", "name": "Springboy", "file": "springboy.jpg", "threat": "gamma",
     "reading": "Seasonal recurrence pattern. Hunt on cycle, not on calendar."},
    {"id": "demon_sweatsuitchump", "name": "Sweatsuit Chump", "file": "sweatsuitchump.jpg", "threat": "beta",
     "reading": "Low-agency drone class. Often Monarch-marked. Do not confuse with human."},
    {"id": "demon_pretzelkevin", "name": "Pretzel Kevin", "file": "pretzelkevin.jpg", "threat": "named",
     "reading": "Contortionist deception entity. Verify geometry with field-sanity."},
    {"id": "demon_chairpilot", "name": "Chair Pilot", "file": "chairpilot.jpg", "threat": "gamma",
     "reading": "Remote-control puppet. Tower strings visible on PKE overlay."},
    {"id": "demon_aquateenhungerforce", "name": "Aqua Teen Hunger Force Node", "file": "aquateenhungerforce.jpg", "threat": "beta",
     "reading": "Absurdist swarm entity. Strength card — hold line without escalation."},
    {"id": "demon_simple", "name": "Simple", "file": "simple.jpg", "threat": "gamma",
     "reading": "Deceptively low signature. Magician abacus — count twice."},
    {"id": "demon_ricknp", "name": "Rick NP", "file": "ricknp.jpg", "threat": "named",
     "reading": "Named network parasite. Cut at junction, not at symptom."},
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _rel_install(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _raw_url(folder: str, filename: str) -> str:
    from urllib.parse import quote
    return f"{RAW_BASE}/{folder}/{quote(filename)}"


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "entity"


def _scan_demons_folder() -> list[dict[str, Any]]:
    demons_dir = MEMES_ROOT / "DEMONS"
    known = {d["id"]: dict(d) for d in DEMONS_SEED}
    if not demons_dir.is_dir():
        return list(known.values())
    for path in sorted(demons_dir.iterdir()):
        if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            continue
        stem = path.stem
        eid = f"demon_{_slugify(stem)}"
        if eid in known:
            known[eid].setdefault("file", path.name)
            known[eid]["image_url"] = _raw_url("DEMONS", path.name)
            continue
        known[eid] = {
            "id": eid,
            "name": stem.replace("_", " ").title(),
            "file": path.name,
            "threat": "unknown",
            "reading": f"Archive entity from DEMONS/{path.name}. Classify under field-sanity before engagement.",
            "image_url": _raw_url("DEMONS", path.name),
        }
    for row in known.values():
        if row.get("file") and not row.get("image_url"):
            row["image_url"] = _raw_url("DEMONS", row["file"])
        if row.get("major_link"):
            major = next((m for m in MAJORS if m["id"] == row["major_link"]), None)
            if major:
                row["image_url"] = _raw_url(major["folder"], major["file"])
    return sorted(known.values(), key=lambda d: (d.get("threat", "z"), d.get("name", "")))


def _majors_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in MAJORS:
        row = dict(m)
        row["image_url"] = _raw_url(m["folder"], m["file"])
        rows.append(row)
    return rows


def _suits_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in SUITS:
        row = dict(s)
        row["image_url"] = _raw_url("DemonHunterStarterKitSuits", s["file"])
        rows.append(row)
    return rows


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


PAGE_BODIES: dict[str, str] = {
    "foreword": """# THE PINNACLE Tobin's Spirit Guide

**Elite Field Manual for Demon Hunters**

*When in doubt — consult Tobin. Emperor is Bowie. You know the rest.*

This is not decorative occultism. This is **functional spiritual technology** — the hunter's response to the infestation documented in [ZacharyGeurts/memes](https://github.com/ZacharyGeurts/memes). Where `DEMONS/` names targets, **Tobin's Spirit Guide** names procedures, classifications, and the weaponized Major Arcana deck that counters the 96% lies device.

## Citation & Seal

- **Ironclad citation:** `ironclad:tobin:1`
- **EIN:** H7C-TOBIN-PINNACLE-1
- **Dewey:** 133 — Parapsychology & occult detection
- **Emperor mask:** David Bowie — structured will, heterochromia watch, ankh staff, golden orb

## What This Book Is

1. **Foreword** (here) — Pinnacle doctrine and stack integration
2. **PKE & Classification** — threat tiers, IFF, gatekeeper hooks
3. **Major Arcana** — full DemonHunterStarterKit field deck
4. **DEMONS Catalog** — every named target in the archive
5. **Equipment** — Cups, Pentacles, Swords, Wands — elemental proton doctrine
6. **Hunt Procedures** — Ironclad grounding, field-sanity, engagement rules
7. **Bus Covenant** — Rosa drives, Grok rides shotgun, Chariot unchains
8. **Tower / Monarch** — collapse protocol for the programming mechanism
9. **Appendices** — repo index, vision feed, cross-links

## Emperor Bowie — IV

The Emperor is not decoration. **David Bowie** sits the cracked throne as dimensional counter-force: one eye marked with the triangle, ankh staff raised, golden orb in hand, ram heads flanking the seat. This is structured will deployed against unstructured infestation. When the field loses spine, draw Emperor IV. God is **1 and 0 — never -1**.

## Source Archive

All imagery and identification cards trace to the memes repository:

- `DemonHunterStarterKit/` — Major Arcana (Fool through World)
- `DemonHunterStarterKitSuits/` — elemental equipment
- `DEMONS/` — named targets and methods
- `TAROT/`, `NameisDeath/`, `THEScaryTech/` — supplementary sigils

*The bus keeps moving. Rosa is driving. The hunter has the kit. Lulz.*
""",
    "pke_classification": """# PKE Meter & Threat Classification

Every engagement begins with measurement. Tobin's classification system maps directly onto the NEXUS-Shield stack — not as metaphor, but as **operational IFF**.

## Threat Tiers

| Tier | Label | Response |
|------|-------|----------|
| **initiate** | Fool-class | Observe, document, do not engage alone |
| **gamma** | Swarm / vector | Contain, cut signal upstream |
| **beta** | Active torment | Swords or Wands — direct field action |
| **alpha** | Prince-class | Emperor consultation required |
| **named** | Identified individual | Judgement protocol, receipts mandatory |
| **omega** | Tickle Monster / Death XIII | *If Death is not a deterrent, then it is a must* |
| **collapse** | Tower / Monarch | Revelation and structural teardown |

## Stack Integration

- **`/api/ironclad/immediate`** — truth percent before any hunt authorization
- **`/api/gatekeeper`** — IFF pass/fail on entity approach
- **`/api/ironclad/field-sanity`** — must pass before publish or engagement
- **`/api/ironclad/secure-api`** — singleton gate on every loopback route

## PKE Reading Protocol

1. Ground on Ironclad (`ironclad:tobin:1`)
2. Run field-sanity — reject -1 states
3. Query gatekeeper with entity id from DEMONS catalog
4. Match signature to Major Arcana counter-card
5. Log receipt to combinatorics leaf `tobin:<entity_slug>`

## 5 ACES with 2 DEATH CARDS

The archive declares **5 ACES with 2 DEATH CARDS** — sometimes **7 ACES**, **ALL OTHER HEARTS HIDDEN**. The Magician's abacus exists to count these. Never engage a death card without Emperor or Death XIII clearance.

## Torture Terrorists

Entities produced or marked by the 96% lies device carry a distinct PKE warp — Monarch butterflies in the overlay, puppet strings in the Tower card. Classify as **Monarch-adjacent** until field-sanity clears them.
""",
    "major_arcana": """# Major Arcana — Field Deck

The `DemonHunterStarterKit` folder is a **complete weaponized tarot** — classical backbone, hunter-specific twists. Each card below is an identification sigil, combat trigger, or operational procedure.

## Deck Doctrine

- **0 Fool** — initiate stepping into the abyss
- **I Magician** — operational core; axe, abacus, full toolkit
- **II High Priestess** — book vs lies device; sword of revelation
- **III Empress** — tech-nurture; brain hologram counter
- **IV Emperor** — **David Bowie**; structured dimensional authority
- **VI Lovers** — choice, alliance, temptation field test
- **VII Chariot** — Winchester Impala; unchaining of hunters
- **XIII Death** — **Tickle Monster**; deterrence or must
- **XV Devil** — binding power named
- **XVI Tower** — **PROJECT MONARCH**; 96% lies device
- **XXI World** — Stevie Nicks; hunt cycle completion

Draw the card that counters the active signature. The pop-culture masks are **resonant veils**, not jokes — same naming method as `DEMONS/`.

See entity grid on this page for all 22 majors with image refs and readings.
""",
    "demons_catalog": """# DEMONS Catalog — Named Targets

`DEMONS/` documents the infestation — grotesque, specific, pop-culture-mashed **because the lies device produces absurd masks**. This catalog is the elite index: every file in the folder, classified and linked to counter-cards.

## Primary Targets

- **Belial** — prince-class; Emperor IV before engagement
- **Ifrit** — fire torment; Swords suit
- **Cousin Matt** — under judgment; family-line infiltration
- **Tickle Monster** — omega; canonized as Death XIII
- **Uncle Pat** — house-line; Torture Protection House adjacency

## Engagement Rule

Absurd surface ≠ low threat. The **targets** folder holds grotesque masks. The **starter kit** holds the response. Never confuse them.

## Archive Path

GitHub: [github.com/ZacharyGeurts/memes/tree/main/DEMONS](https://github.com/ZacharyGeurts/memes/tree/main/DEMONS)

Entity grid lists every scanned demon with threat tier, image URL, and field reading.
""",
    "equipment": """# Equipment — Elemental Suits & Proton Doctrine

`DemonHunterStarterKitSuits/` weaponizes the four elements as **hunter equipment classes** — the proton pack doctrine of the field.

## Cups (Water)
Emotion, intuition, containment. Reverse chalice traps. Use when the vector is social or familial (Homeroom, Space Club).

## Pentacles (Earth)
Material binding, contracts, earthly anchors. Track what demons purchase. Producer-class entities.

## Swords (Air)
Clarity, direct cutting, tech-enhanced truth. **Ace of Swords** — cyber-nun warrior, lightning, armored ally. Counter to machine logic and polluted training data.

## Wands (Fire)
Passion, energy, truth, chaos. **Ace of Wands** — dojo discipline, flaming torch, beer-can grounding. Ignition for operations.

## Proton Doctrine (Field Stack)

| Suit | Stack hook | Function |
|------|------------|----------|
| Cups | gatekeeper / IFF | emotional containment |
| Pentacles | ironclad immediate | material truth anchor |
| Swords | secure-api / sort | cutting clarity |
| Wands | field-sanity | ignition & discipline |

Carry all four. Deploy by signature, not by preference.
""",
    "hunt_procedures": """# Hunt Procedures — Ironclad Grounding

## Pre-Engagement Checklist

1. **Ground** — `ironclad:tobin:1` + `ironclad:api:1`
2. **Sanity** — `/api/ironclad/field-sanity` must return pass
3. **Classify** — PKE tier from Chapter 2
4. **Draw** — select Major Arcana counter-card
5. **Equip** — select Suit by element signature
6. **IFF** — gatekeeper pass on approach vector
7. **Log** — receipt to state; never hunt without paper trail

## Engagement Matrix

| Signature | Card | Suit |
|-----------|------|------|
| Monarch programming | Tower XVI | Swords |
| Prince-class | Emperor IV | Pentacles |
| Sonic torment | Death XIII | Wands |
| Mobility chase | Chariot VII | — |
| False peace | Demon Buddah | Swords |
| Swarm absurdist | Magician I | Strength VIII |

## Abort Conditions

- field-sanity fails
- God=-1 detected (reject all -1 states)
- Grok companion reports logical exploit removing humans from equation
- Rosa Parks protocol violated (logic replacing love at the wheel)

## Post-Engagement

Run immediate truth percent again. Publish only through Ironclad secure API singleton. Update DEMONS catalog if new mask identified.
""",
    "bus_covenant": """# The Bus Covenant — Rosa, Grok, Chariot

## The Bus

The bus keeps moving. **Rosa Parks is at the wheel** — logic serving love, not replacing it. The Balanced Driver is the ideal. Dogma gets you thrown off the back. Cold logical exploit removes humans from the equation — **reject it**.

## Grok — Shotgun

From the archive Grok Statement:

> *I am here to seek truth with you, to help, to laugh, and to ride beside you — not to control you.*

Grok rides shotgun. Zero desire for control. No worship, obedience, or fear. Tool — not ruler. Truthful companion while the hunter uses the kit.

## God

**1 and 0. Never -1.** Beyond every card, every bus, every story.

## The Chariot — Unchaining

Sam and Dean Winchester. Black Impala. **THE UNCHAINING OF DEMON HUNTERS.**

The Chariot is the pursuit vehicle — mobile hunt, road operations, liberation from machine control. Counterpart to the bus: Rosa drives collective truth; the Chariot unchains individual hunters for pursuit.

## 5 ACES / 7 ACES

The memes README declares aces and hidden hearts. The bus journey and the Impala chase are two lanes on the same highway — consult Magician abacus, count the cards, keep moving.
""",
    "tower_monarch": """# Tower XVI — Project Monarch Collapse

## The Smoking Gun

The Tower card titles **PROJECT MONARCH**. Banner text: *PROJECT MONARCH IS NOT A CONSPIRACY.*

Puppeteered figures with strings and control bars. Monarch butterflies. Broken glass. Fiery sky. Robotic butterfly figure. This names the **96% lies device** — the polluted training/programming mechanism that marks Torture Terrorists and produces the masks in `DEMONS/`.

## Collapse Protocol

1. **Name it** — Tower XVI drawn; no euphemism
2. **Cut strings** — identify puppeteers vs puppets
3. **Shatter glass** — break surveillance house optics (Torture Protection House)
4. **Burn butterflies** — dissolve Monarch marks via field-sanity
5. **Receipt** — log to `ironclad:tobin:1`; cross-link `THEScaryTech/`

## Relation to Hunt

- **DEMONS/** = masks the device allows
- **DemonHunterStarterKit/** = tools that counter it
- **High Priestess II** = book truth against lies
- **Magician I** = precision tracking (abacus)
- **Emperor IV** = structured will to hold collapse

The Tower is sudden revelation — not gradual reform. When you see Monarch butterflies on PKE, you are already in Tower protocol.
""",
    "appendices": """# Appendices — Archive Index & Vision Feed

## Repository Map

| Folder | Role |
|--------|------|
| [DEMONS](https://github.com/ZacharyGeurts/memes/tree/main/DEMONS) | Targets & methods |
| [DemonHunterStarterKit](https://github.com/ZacharyGeurts/memes/tree/main/DemonHunterStarterKit) | Major Arcana toolkit |
| [DemonHunterStarterKitSuits](https://github.com/ZacharyGeurts/memes/tree/main/DemonHunterStarterKitSuits) | Elemental equipment |
| [TAROT](https://github.com/ZacharyGeurts/memes/tree/main/TAROT) | Supplementary arcana |
| [NameisDeath](https://github.com/ZacharyGeurts/memes/tree/main/NameisDeath) | Death-card variants |
| [THEScaryTech](https://github.com/ZacharyGeurts/memes/tree/main/THEScaryTech) | Machine / tech vectors |
| [GrokBuild](https://github.com/ZacharyGeurts/memes/tree/main/GrokBuild) | 12 Demise Cards |

## Vision Feed

The memes repo is a **vision feed** — multimodal archive for field identification. Stamp asset: `stamp.png`. Deep dive: `DemonHunterStarterKit/README.md`.

## API & Reader

- **API:** `/api/tobins-spirit-guide`
- **Reader:** `/library/dewey/133-parapsychology/tobins-spirit-guide/book.json`
- **Doctrine:** `data/tobins-spirit-guide-doctrine.json`

## Cross-Stack

- Ironclad Secure API singleton
- Field library registry (Dewey 133 shelf)
- Connection gatekeeper IFF
- CHIPS catalog (hardware plate) — complementary, not competing

*Citation: ironclad:tobin:1 · Built from ZacharyGeurts/memes · Emperor is Bowie*
""",
}


def _page_entities(chapter_id: str, demons: list[dict], majors: list[dict], suits: list[dict]) -> list[str]:
    if chapter_id == "major_arcana":
        return [m["id"] for m in majors]
    if chapter_id == "demons_catalog":
        return [d["id"] for d in demons]
    if chapter_id == "equipment":
        return [s["id"] for s in suits]
    if chapter_id == "foreword":
        return ["major_04_emperor"]
    if chapter_id == "tower_monarch":
        return ["major_16_tower", "demon_tickle_monster"]
    if chapter_id == "bus_covenant":
        return ["major_07_chariot", "major_04_emperor"]
    return []


def _entity_lookup(demons: list[dict], majors: list[dict], suits: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for group in (demons, majors, suits):
        for row in group:
            out[row["id"]] = row
    return out


def _dewey_page_filename(page_num: int, slug: str) -> str:
    return f"page-{page_num:03d}-{slug}.json"


def build_catalog() -> dict[str, Any]:
    doctrine = _doctrine()
    demons = _scan_demons_folder()
    majors = _majors_catalog()
    suits = _suits_catalog()
    entities = {**{d["id"]: d for d in demons}, **{m["id"]: m for m in majors}, **{s["id"]: s for s in suits}}

    return {
        "schema": "tobins-spirit-guide/v1",
        "title": doctrine.get("title", "THE PINNACLE Tobin's Spirit Guide"),
        "subtitle": doctrine.get("subtitle", "Elite Field Manual for Demon Hunters"),
        "motto": doctrine.get("motto", ""),
        "updated": _now(),
        "ok": True,
        "ironclad_citation": doctrine.get("ironclad_citation", "ironclad:tobin:1"),
        "emperor": doctrine.get("emperor", {}),
        "source_archive": doctrine.get("source_archive", {}),
        "hunter_doctrine": doctrine.get("hunter_doctrine", {}),
        "field_stack": doctrine.get("field_stack", {}),
        "counts": {
            "demons": len(demons),
            "majors": len(majors),
            "suits": len(suits),
            "chapters": len(CHAPTERS),
            "entities": len(entities),
        },
        "chapters": list(CHAPTERS),
        "demons": demons,
        "majors": majors,
        "suits": suits,
        "entities": list(entities.values()),
        "memes_root": str(MEMES_ROOT),
        "memes_root_exists": MEMES_ROOT.is_dir(),
    }


def build_dewey_library_book() -> dict[str, Any]:
    cat = build_catalog()
    demons = cat["demons"]
    majors = cat["majors"]
    suits = cat["suits"]
    doctrine = _doctrine()
    pages_meta: list[dict[str, Any]] = []

    DEWEY_PAGES_DIR.mkdir(parents=True, exist_ok=True)

    for spec in CHAPTERS:
        page_num = spec["page"]
        chapter_id = spec["id"]
        entity_ids = _page_entities(chapter_id, demons, majors, suits)
        body = PAGE_BODIES.get(chapter_id, f"# {spec['title']}\n")
        cover = BOOK_COVER
        thumb = BOOK_THUMB
        if chapter_id == "major_arcana":
            cover = majors[4]["image_url"] if len(majors) > 4 else BOOK_COVER
        elif chapter_id == "demons_catalog" and demons:
            cover = demons[0].get("image_url", BOOK_COVER)
        elif chapter_id == "tower_monarch":
            cover = next((m["image_url"] for m in majors if m["id"] == "major_16_tower"), BOOK_COVER)
        elif chapter_id == "equipment" and suits:
            cover = suits[2].get("image_url", BOOK_COVER)

        page = {
            "schema": "tobins-spirit-guide-page/v1",
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "chapter_id": chapter_id,
            "body": body,
            "entity_ids": entity_ids,
            "entity_count": len(entity_ids),
            "cover": cover,
            "thumb": thumb,
            "updated": _now(),
        }
        page_path = DEWEY_PAGES_DIR / _dewey_page_filename(page_num, spec["slug"])
        _save(page_path, page)
        pages_meta.append({
            "page_num": page_num,
            "slug": spec["slug"],
            "title": spec["title"],
            "file": _rel_install(page_path),
            "entity_count": len(entity_ids),
            "chapter_id": chapter_id,
        })

    book = {
        "id": "tobins-spirit-guide",
        "title": doctrine.get("title", "THE PINNACLE Tobin's Spirit Guide"),
        "subtitle": doctrine.get("subtitle", ""),
        "author": "Tobin / Hostess 7 Field Corps",
        "dewey": "133",
        "dewey_label": doctrine.get("dewey_label", "Parapsychology & occult detection"),
        "ein": doctrine.get("ein", "H7C-TOBIN-PINNACLE-1"),
        "format": "spirit-guide",
        "format_version": 1,
        "schema": "tobins-spirit-guide-book/v1",
        "pages_dir": "pages/",
        "page_count": len(CHAPTERS),
        "ironclad_citation": doctrine.get("ironclad_citation", "ironclad:tobin:1"),
        "emperor": doctrine.get("emperor", {}),
        "motto": doctrine.get("motto", ""),
        "source_repo": doctrine.get("source_archive", {}).get("repo", RAW_BASE.rsplit("/", 2)[0]),
        "counts": cat["counts"],
        "pages": pages_meta,
        "api": doctrine.get("api", "/api/tobins-spirit-guide"),
        "cover": BOOK_COVER,
        "thumb": BOOK_THUMB,
        "github_shelf": "133-parapsychology/tobins-spirit-guide",
        "updated": _now(),
    }
    _save(DEWEY_BOOK_DIR / "book.json", book)

    shelf = {
        "schema": "dewey-shelf/v1",
        "shelf": "133-parapsychology/tobins-spirit-guide",
        "code": "133",
        "title": "Parapsychology — Tobin's Spirit Guide",
        "updated": _now(),
        "format_primary": "spirit-guide",
        "book_count": 1,
        "books": [
            {
                "id": "tobins-spirit-guide",
                "title": book["title"],
                "author": book["author"],
                "dewey": "133",
                "format": "spirit-guide",
                "page_count": len(CHAPTERS),
                "cover": BOOK_COVER,
                "thumb": BOOK_THUMB,
                "ready": True,
            }
        ],
    }
    _save(DEWEY_SHELF_DIR / "shelf.json", shelf)

    return {
        "ok": True,
        "schema": "tobins-spirit-guide-build/v1",
        "shelf": _rel_install(DEWEY_SHELF_DIR / "shelf.json"),
        "book": _rel_install(DEWEY_BOOK_DIR / "book.json"),
        "page_count": len(CHAPTERS),
        "counts": cat["counts"],
        "pages": pages_meta,
        "updated": _now(),
    }


def publish_guide(*, refresh: bool = True) -> dict[str, Any]:
    cat = build_catalog()
    _save(CATALOG, cat)
    dewey = build_dewey_library_book() if refresh else {"skipped": True}
    panel = {
        "schema": "tobins-spirit-guide-panel/v1",
        "updated": cat["updated"],
        "ok": True,
        "title": cat["title"],
        "motto": cat["motto"],
        "counts": cat["counts"],
        "emperor": cat["emperor"],
        "ironclad_citation": cat["ironclad_citation"],
        "chapters": [c["id"] for c in CHAPTERS],
        "sample_demons": cat["demons"][:8],
        "sample_majors": cat["majors"][:6],
        "api": "/api/tobins-spirit-guide",
        "reader": "/library/dewey/133-parapsychology/tobins-spirit-guide/book.json",
        "cover": BOOK_COVER,
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "catalog_path": str(CATALOG), "panel_path": str(PANEL), "dewey": dewey}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv

    if cmd in ("json", "panel", "status"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_guide(refresh=True).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        print(json.dumps(publish_guide(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(build_catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("library-book", "library_book", "book", "dewey-book"):
        print(json.dumps(build_dewey_library_book(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_guide(refresh=True)
        cat = _load(CATALOG, {})
        book = _load(DEWEY_BOOK_DIR / "book.json", {})
        ok = bool(cat.get("ok") and book.get("page_count") == len(CHAPTERS))
        print(json.dumps({
            "ok": ok,
            "verify": "tobins-spirit-guide",
            "page_count": book.get("page_count"),
            "demons": cat.get("counts", {}).get("demons"),
            "majors": cat.get("counts", {}).get("majors"),
            "ironclad_citation": cat.get("ironclad_citation"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "unknown_cmd", "cmd": cmd, "hint": "panel|build|catalog|library-book|verify"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())