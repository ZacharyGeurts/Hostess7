#!/usr/bin/env pythong
"""Exploring Hand-to-Hand Combat & Exploring Weaponized Combat — personhood books, not vehicles."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
LIBRARY = INSTALL / "library" / "dewey"
SHELF = LIBRARY / "355-military-science"
DOCTRINE = INSTALL / "data" / "exploring-combat-personhood-doctrine.json"
MOTION_DOCTRINE = INSTALL / "data" / "humanoid-motion-doctrine.json"
COMBAT_DOCTRINE = INSTALL / "data" / "hostess7-combat-doctrine.json"


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _veh_mod() -> Any:
    path = INSTALL / "lib" / "field-exploring-vehicles.py"
    spec = importlib.util.spec_from_file_location("exploring_veh", path)
    if not spec or not spec.loader:
        raise ImportError("field-exploring-vehicles.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chapters(*pairs: tuple[str, str]) -> list[dict[str, Any]]:
    return [{"num": i + 1, "slug": slug, "title": title} for i, (slug, title) in enumerate(pairs)]


def _motion_skills_table() -> str:
    v = _veh_mod()
    doc = _load(MOTION_DOCTRINE, {})
    rows: list[list[str]] = []
    for skill in doc.get("skills") or []:
        fam = str(skill.get("family") or "—")
        prims = ", ".join(skill.get("primitives") or [])[:80]
        rows.append([skill.get("label") or skill.get("id"), fam, prims or "—"])
    return v._section(
        "Humanoid motion skill lattice",
        v._table(["Skill", "Family", "Primitives"], rows) if rows else "—",
    )


def build_hand_to_hand() -> str:
    v = _veh_mod()
    motion = _load(MOTION_DOCTRINE, {})
    combat = _load(COMBAT_DOCTRINE, {})
    families = motion.get("families") or {}
    fam_lines = [f"**{k}** — {desc}" for k, desc in families.items()]

    return "\n".join([
        "# Exploring Hand-to-Hand Combat",
        "", "![Cover](h7fig:cover)", "",
        "**For personhood — the embodied human, not vehicles.**",
        "Unarmed combat, grappling, and every martial family Hostess 7 trains on the humanoid motion lattice.",
        f"- **Updated:** {v._now()}",
        f"- **Paired book:** *Exploring Weaponized Combat* (firearms, knives, personal weapons)",
        f"- **Not in scope:** military vehicles — see *Exploring Military Vehicles*",
        f"- **Disclaimer:** {combat.get('disclaimer', 'Educational only.')}",
        "", "---", "",
        v._section("1. Personhood scope", v._bullet_list([
            "This book is for the **embodied person** — stance, limbs, proprioception, breath, balance.",
            "Vehicles, mounted weapons platforms, and armor carriages belong in the vehicles shelf.",
            "Hostess 7 reads this through Ironclad + library truth gate before teaching combat counsel.",
            "Motion training (`humanoid-motion-training.py`) loads skills named in this book.",
        ])),
        v._section("2. Foundations — stance to strategy", v._table(
            ["Concept", "Definition", "Training hook"],
            [
                ["Stance", "Base of support — foot placement, knee soft, hips square", "Horse stance, orthodox/southpaw"],
                ["Balance", "Center of mass over base; recover from perturbation", "Single-leg drills, ukemi"],
                ["Distance", "Measure between fighters — kicking, punching, clinch ranges", "Footwork ladders"],
                ["Timing", "Rhythm, feint, counter-window", "Double-end bag, reaction drills"],
                ["Lines", "Centerline, power line, structural weak axes", "Wing Chun centerline guard"],
                ["Breath", "Exhale on exertion; avoid breath-hold under stress", "Kiai discipline, recovery"],
            ],
        )),
        v._section("3. Mobility & flexibility", v._bullet_list([
            "Touch toes — hip hinge, spinal flexion, hamstring lengthen, toe reach",
            "Forward fold — sustained posterior chain loading",
            "Cat-cow — spinal wave, lumbar and cervical mobility",
            "All mobility skills tie to body zones: head → spine → hips → knees → ankles → toes",
        ])),
        v._section("4. Martial families (overview)", "\n".join(fam_lines)),
        v._section("5. Striking arts", v._table(
            ["Art", "Origin", "Signature techniques", "Ruleset notes"],
            [
                ["Boxing", "Western", "Jab, cross, hook, uppercut, slip, roll", "Ring, gloves, rounds"],
                ["Muay Thai", "Thailand", "Teep, round kick, elbow, clinch knee, check", "8-point striking"],
                ["Karate / Taekwondo", "Okinawa / Korea", "Linear strikes, kata, kicking", "Point vs full contact"],
                ["Krav Maga", "Israel", "Defense-V, groin kick, retzev — **lethal gate: corroborated threat only**", "Street-oriented; legal frame varies"],
            ],
        )),
        v._section("6. Kung fu & Chinese arts", v._table(
            ["Style", "Focus", "Motion primitives"],
            [
                ["Wing Chun", "Centerline, sticky hands", "Chain punch, pak sao, tan sao, biu jee, chi sao"],
                ["Hung Gar", "Five animals, iron bridge", "Tiger claw, horse stance, iron bridge"],
                ["Shaolin Quan", "Long fist, explosive movement", "Long fist, monkey step, iron palm, jump kick"],
                ["Tai Chi", "Root, yield, redirect", "Ward off, roll back, push, single whip"],
            ],
        )),
        v._section("7. Grappling — Brazilian Jiu-Jitsu & beyond", v._bullet_list([
            "**Brazilian Jiu-Jitsu (BJJ)** — guard, guard pull, pass guard, mount, side control, back control",
            "Submissions — armbar, triangle, rear-naked choke, kimura, americana (educational anatomy frame)",
            "Positional hierarchy — position before submission; escape priorities",
            "**Judo** — osoto gari, uchi mata, seoi nage, kuzushi, newaza pins",
            "**Wrestling** — single leg, double leg, snap down, sprawl, pin",
            "Ground vs stand — when to pull guard vs when to sprawl (sport vs self-defense context)",
        ])),
        v._section("8. MMA — mixed martial arts", v._bullet_list([
            "Integrates striking, clinch, takedown, ground-and-pound, submissions",
            "Cage awareness — cutting angle, wall walks, fence wrestling",
            "Skill load: jab-cross, double leg, guillotine, ground pound, sprawl",
            "Train on humanoid motion lattice — proficiency grows by ticks under gravity, not instant Matrix load",
        ])),
        v._section("9. Lawful self-defense & de-escalation", v._bullet_list([
            "Jurisdiction varies — proportionality, duty to retreat where applicable",
            "De-escalation first — voice, distance, exit path, bystander safety",
            "Imminent threat standard — educational framing, not operational orders",
            "Aftermath — medical aid, report, legal counsel; trauma-informed recovery",
        ])),
        v._section("10. Tactical awareness (unarmed)", v._table(
            ["Framework", "Steps", "Field use"],
            [
                ["OODA", "Observe → Orient → Decide → Act", "Break opponent loop with tempo change"],
                ["Cover vs concealment", "Stops rounds vs hides only", "Unarmed: use barriers for escape"],
                ["Situational awareness", "Exits, hands, groups, terrain", "Pre-fight cues — posture, targeting"],
                ["Multiple attackers", "Stacking, fence, escape wedge", "Footwork to single-file"],
            ],
        )),
        v._section("11. Conditioning for personhood", v._bullet_list([
            "Energy systems — aerobic base, alactic power, glycolytic repeatability",
            "Neck, grip, core — grappling durability",
            "Mobility maintenance — touch toes cycle ties to self-maintenance body_cycle",
            "Recovery — sleep, hydration, deload weeks; injury prevention over ego",
        ])),
        _motion_skills_table(),
        v._section("12. AI retrieval keys", v._bullet_list([
            "Index: `art`, `technique`, `family`, `primitive`, `zone`, `ruleset`, `legal_frame`, `personhood`",
            "Dewey **355** · book_id `exploring_hand_to_hand_combat`",
            "Pair: `exploring_weaponized_combat` · motion: `humanoid-motion-doctrine.json`",
            "Hostess 7 combat categories: foundations, striking, boxing, grappling_bjj, wrestling, mma, kung_fu, self_defense, tactical_awareness, fitness_conditioning",
        ])),
        "",
    ])


def build_weaponized() -> str:
    v = _veh_mod()
    combat = _load(COMBAT_DOCTRINE, {})

    return "\n".join([
        "# Exploring Weaponized Combat",
        "", "![Cover](h7fig:cover)", "",
        "**For personhood — personal weapons wielded by the embodied human, not vehicle mounts.**",
        "Firearms, knives, edged tools, impact weapons, and less-lethal recognition — whole understanding.",
        f"- **Updated:** {v._now()}",
        f"- **Paired book:** *Exploring Hand-to-Hand Combat* (unarmed and grappling arts)",
        f"- **Not in scope:** tanks, aircraft, naval platforms — see *Exploring Military Vehicles*",
        f"- **Disclaimer:** {combat.get('disclaimer', 'Educational only.')}",
        "", "---", "",
        v._section("1. Personhood scope", v._bullet_list([
            "This book covers **weapons the person carries and wields** — hands, holsters, belts, pockets.",
            "Vehicle-mounted ordnance, crew-served systems, and platform logistics are out of scope.",
            "Educational mechanics and recognition — **not** operational orders to harm.",
            "Every technique assumes lawful context where applicable; de-escalation preferred.",
        ])),
        v._section("2. Force continuum", v._table(
            ["Level", "Means", "Legal sensitivity"],
            [
                ["Presence", "Posture, voice, distance", "Lowest force"],
                ["Soft control", "Joint locks, escorts (trained roles)", "Policy-dependent"],
                ["Less-lethal", "OC spray, conducted energy device", "Misuse recognition; jurisdiction"],
                ["Edged / impact", "Knife, baton, improvised", "Proportionality critical"],
                ["Firearms", "Handgun, rifle, shotgun", "Highest scrutiny — lawful use only"],
            ],
        )),
        v._section("3. Edged weapons — knives & blades", v._table(
            ["Type", "Traits", "Recognition / safety"],
            [
                ["Folding knife", "Pocket carry, one-hand open (where legal)", "Lock type, blade length laws"],
                ["Fixed blade", "Stronger lockup, sheath carry", "Draw path, retention"],
                ["Kitchen / utility", "Improvised edge", "Environmental awareness"],
                ["Bayonet / fighting knife", "Historical and modern fighting forms", "Educational anatomy of thrust vs slash"],
                ["Multi-tool blade", "Utility first", "Not a fighting tool by design"],
            ],
        ) + "\n" + v._bullet_list([
            "Grip — saber, hammer, ice-pick (educational recognition)",
            "Lines of attack — high, low, diagonal; centerline vulnerability",
            "Distance — edge beats empty hand at contact; closing vs fleeing",
            "Pair with hand-to-hand — weapon retention and disarm **education only**",
        ])),
        v._section("4. Impact weapons", v._bullet_list([
            "Batons — straight, side-handle; target zones and policy frames",
            "Improvised — flashlight, keys, furniture; legal risk elevated",
            "Staff / stick arts — range advantage, two-handed power",
            "Shielding with objects — bag, chair, cart (escape-first doctrine)",
        ])),
        v._section("5. Firearms — whole understanding (personhood)", v._bullet_list([
            "**Purpose** — educational mechanics: how systems work, not combat orders",
            "**Safety rules** — treat every firearm as loaded; muzzle discipline; finger off trigger; know target and beyond",
            "**Handgun** — semi-auto vs revolver; magazine, slide, trigger, sights; concealed carry legal variance",
            "**Rifle** — carbine platforms; sight picture; zeroing concept; two-handed platform",
            "**Shotgun** — spread pattern by range; pump vs semi; home-defense **legal** framing only",
            "**Ammunition** — caliber, grain, hollow-point vs FMJ (educational); barrier penetration awareness",
            "**Malfunctions** — tap-rack-bang concept; stop if uncertain",
            "**Storage** — locked, separated, child-safe; owner responsibility",
        ])),
        v._section("6. Firearms table (recognition)", v._table(
            ["Platform", "Role", "Personhood carry notes"],
            [
                ["Compact handgun", "Concealed carry class", "Holster types — IWB, OWB; retention levels"],
                ["Full-size handgun", "Duty / home", "Grip fit, magazine capacity laws"],
                ["PDW / pistol-caliber carbine", "Personal defense", "Two-hand stability, brace laws vary"],
                ["Rifle (AR-pattern, bolt, lever)", "Sport, hunting, defense where legal", "Sling, optic co-witness"],
                ["Shotgun (pump/semi)", "Home, sport", "Length of pull, choke, minimum safe distance"],
            ],
        )),
        v._section("7. Less-lethal recognition", v._bullet_list([
            "OC spray (pepper) — Scoville, stream vs fog, cross-contamination, wind",
            "Conducted energy device (Taser-class) — probe spread, drive stun, failure modes",
            "Stun devices — contact pain compliance; misuse patterns",
            "Hostess 7 combat battery domain: `weapons_education` — recognition not deployment orders",
        ])),
        v._section("8. Weapon retention & transition", v._bullet_list([
            "Holster retention levels — snap, thumb break, SERPA debate (educational)",
            "Grappling with weapons — foul cover, hip carry vulnerability",
            "Transition — handgun to knife is policy and law constrained",
            "Always prefer de-escalation and escape when personhood safety allows",
        ])),
        v._section("9. Pairing with hand-to-hand", v._table(
            ["Scenario", "Hand-to-hand book", "This book"],
            [
                ["Clinch", "Knees, throws, wall work", "Retention, foul cover"],
                ["Ground", "BJJ positions", "Holster guard, back control weapon access"],
                ["Standoff", "Footwork, feints", "Distance, draw timing (lawful)"],
                ["Multiple threats", "Angle, escape wedge", "Capacity, reload awareness"],
            ],
        )),
        v._section("10. Ethics & law (educational)", v._bullet_list([
            "Proportionality — response matches threat level where law requires",
            "Brandishing, open carry, concealed carry — jurisdiction-specific",
            "Prohibited persons — educational awareness, not legal advice",
            "Aftermath — secure scene, aid injured, invoke counsel, document",
        ])),
        v._section("11. AI retrieval keys", v._bullet_list([
            "Index: `weapon_type`, `platform`, `caliber`, `edge`, `less_lethal`, `retention`, `legal_frame`, `personhood`",
            "Dewey **355** · book_id `exploring_weaponized_combat`",
            "Pair: `exploring_hand_to_hand_combat` · NOT `exploring_military_vehicles`",
            "Hostess 7 category: `weapons_education` · corroborated threat gates for lethal counsel",
        ])),
        "",
    ])


BOOKS: list[dict[str, Any]] = [
    {
        "book_id": "exploring_hand_to_hand_combat",
        "title": "Exploring Hand-to-Hand Combat",
        "builder": build_hand_to_hand,
        "accent": (120, 45, 40),
        "subject": "hand-to-hand combat — personhood martial arts and grappling",
        "tags": [
            "exploring", "combat", "personhood", "hand-to-hand", "martial-arts", "bjj",
            "grappling", "mma", "kung-fu", "boxing", "wrestling", "self-defense",
        ],
        "chapters": _chapters(
            ("01-personhood", "Personhood scope"),
            ("02-foundations", "Foundations"),
            ("03-mobility", "Mobility & flexibility"),
            ("04-families", "Martial families"),
            ("05-striking", "Striking arts"),
            ("06-kung-fu", "Kung fu & Chinese arts"),
            ("07-grappling-bjj", "Grappling & BJJ"),
            ("08-mma", "MMA"),
            ("09-self-defense", "Lawful self-defense"),
            ("10-tactical", "Tactical awareness"),
            ("11-conditioning", "Conditioning"),
            ("12-motion-lattice", "Humanoid motion lattice"),
            ("13-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_weaponized_combat",
        "title": "Exploring Weaponized Combat",
        "builder": build_weaponized,
        "accent": (80, 70, 90),
        "subject": "weaponized combat — personhood firearms knives edged impact less-lethal",
        "tags": [
            "exploring", "combat", "personhood", "weaponized", "firearms", "knives",
            "edged-weapons", "less-lethal", "weapons-education",
        ],
        "chapters": _chapters(
            ("01-personhood", "Personhood scope"),
            ("02-force-continuum", "Force continuum"),
            ("03-edged", "Edged weapons"),
            ("04-impact", "Impact weapons"),
            ("05-firearms", "Firearms fundamentals"),
            ("06-platforms", "Platform recognition"),
            ("07-less-lethal", "Less-lethal recognition"),
            ("08-retention", "Retention & transition"),
            ("09-pairing", "Pairing with hand-to-hand"),
            ("10-ethics-law", "Ethics & law"),
            ("11-ai-keys", "AI retrieval keys"),
        ),
    },
]


def generate_book(spec: dict[str, Any]) -> dict[str, Any]:
    v = _veh_mod()
    text = spec["builder"]()
    rep = v.pack_book(
        book_id=spec["book_id"],
        title=spec["title"],
        text=text,
        shelf=SHELF,
        dewey="355",
        dewey_label="Military science",
        subject=spec["subject"],
        accent=spec["accent"],
    )
    pdf_name = f"Hostess7_{spec['title'].replace(' ', '_').replace('-', '_')}_Textbook.pdf"
    h7c_rel = f"{spec['book_id']}/{spec['book_id']}.h7c"
    pdf_ok = v._write_textbook_pdf(text, SHELF / pdf_name, spec["title"])
    manifest = v._write_book_manifest(
        shelf=SHELF,
        book_id=spec["book_id"],
        title=spec["title"],
        dewey="355",
        pdf_name=pdf_name,
        h7c_rel=h7c_rel,
        chapters=spec["chapters"],
        char_count=len(text),
    )
    v._update_shelf(
        SHELF,
        "355",
        "355-military-science",
        {
            "id": spec["book_id"],
            "title": spec["title"],
            "author": "AmmoOS Field Library",
            "dewey": "355",
            "format": "h7c",
            "h7c": f"library/dewey/355-military-science/{h7c_rel}",
            "pdf": f"library/dewey/355-military-science/{pdf_name}",
            "manifest": f"library/dewey/355-military-science/{spec['book_id']}/book-manifest.json",
            "cover": f"/world/assets/combinatronic/books/{spec['book_id']}.png",
            "book_kind": "exploring",
            "personhood": True,
            "ready": True,
        },
    )
    rep["pdf"] = pdf_name if pdf_ok else None
    rep["manifest"] = str(manifest)
    rep["char_count"] = len(text)
    book_json_path = SHELF / spec["book_id"] / "book.json"
    if book_json_path.is_file():
        try:
            book_doc = json.loads(book_json_path.read_text(encoding="utf-8"))
            book_doc["personhood"] = True
            book_doc["tags"] = spec.get("tags") or []
            book_doc["keywords"] = book_doc["tags"]
            book_doc["subject"] = spec["subject"]
            book_doc["catalog_updated"] = v._now()
            book_json_path.write_text(json.dumps(book_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass
    return rep


def generate_all(*, book_id: str | None = None) -> dict[str, Any]:
    specs = BOOKS if not book_id else [b for b in BOOKS if b["book_id"] == book_id]
    if book_id and not specs:
        aliases = {
            "hand": "exploring_hand_to_hand_combat",
            "hand_to_hand": "exploring_hand_to_hand_combat",
            "weapon": "exploring_weaponized_combat",
            "weaponized": "exploring_weaponized_combat",
        }
        resolved = aliases.get(book_id, book_id)
        specs = [b for b in BOOKS if b["book_id"] == resolved]
    if book_id and not specs:
        return {"ok": False, "error": "unknown_book", "book_id": book_id}
    results = {}
    for spec in specs:
        results[spec["book_id"]] = generate_book(spec)
    return {
        "ok": True,
        "count": len(results),
        "personhood_only": True,
        "not_vehicles": True,
        "books": results,
        "format": "h7c",
        "updated": _veh_mod()._now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower().replace("-", "_")
    if cmd == "all":
        print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "list":
        print(json.dumps([
            {"book_id": b["book_id"], "title": b["title"], "personhood": True}
            for b in BOOKS
        ], ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(generate_all(book_id=cmd), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())