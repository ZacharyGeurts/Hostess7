#!/usr/bin/env pythong
"""Exploring combat anatomy — mechanical & biological depth per body area for personhood combat."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
LIBRARY = INSTALL / "library" / "dewey"
SHELF = LIBRARY / "611-human-anatomy"
DOCTRINE = INSTALL / "data" / "exploring-combat-anatomy-doctrine.json"

PARTS: dict[str, dict[str, Any]] = {
    "hand": {
        "title": "Exploring the Hand",
        "book_id": "exploring_the_hand",
        "accent": (210, 165, 140),
        "tags": ["exploring", "anatomy", "biology", "mechanical", "combat", "personhood", "hand", "grip", "dexterity"],
        "joints": ["hand_l", "hand_r", "wrist_l", "wrist_r"],
        "biology": [
            "Carpals (8), metacarpals (5), phalanges (14 per hand) — short bones, long bones, sesamoids (thumb MCP).",
            "Thenar (thumb opposition), hypothenar, interossei, lumbricals — intrinsic grip power vs extrinsic forearm flexors/extensors.",
            "Median nerve — thumb opposition, index/middle precision; ulnar nerve — hypothenar, interossei, ring/pinky power.",
            "Digital arteries and veins — crush injury awareness; nail bed trauma; pulp space infections (educational).",
            "Skin mechanoreceptors — grip feedback, weapon texture, surface discrimination.",
        ],
        "mechanical": [
            "Thumb CMC saddle joint — opposition arc is the human mechanical advantage for tools and weapons.",
            "MCP collateral ligaments tighten in flexion — why hook grips resist peel-off.",
            "Power grip: flexor digitorum profundus + superficialis + thumb adductor — cylindrical closure force.",
            "Precision grip: FDP tips + thumb pad — minimum force maximum control (blade indexing, trigger discipline).",
            "Leverage: finger length affects torque at MCP; shorter digits favor power, longer favor reach in finger locks.",
        ],
        "combat": [
            "Striking surfaces: knuckles (MCP heads) — boxing wraps reduce metacarpal fracture risk; hammer fist uses hypothenar.",
            "Grips: power (baton, rifle stock), precision (knife handle, trigger), hook (clinch collar), pinch (joint manipulation).",
            "Weapon retention — wrap fingers and thumb; defeat peel by flexing MCP and adducting thumb.",
            "Grappling: finger locks (educational anatomy only), grip breaks, sleeve and wrist control entries.",
            "Hostess7 hand-core grips: open, power, precision, pinch, tripod, hook, lateral, sphere — train to combat proficiency floor.",
        ],
        "training": "hostess7-hand-core.py · humanoid-motion-secured limb identity hand_l/hand_r",
    },
    "wrist_forearm": {
        "title": "Exploring the Wrist and Forearm",
        "book_id": "exploring_the_wrist_and_forearm",
        "accent": (195, 150, 125),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "wrist", "forearm", "rotation", "block"],
        "joints": ["wrist_l", "wrist_r", "elbow_l", "elbow_r"],
        "biology": [
            "Radius and ulna — forearm rotation pair; radius crosses ulna in pronation.",
            "Wrist radiocarpal and midcarpal joints — flexion/extension, radial/ulnar deviation.",
            "TFCC (triangular fibrocartilage) — ulnar-side stability, load transmission.",
            "Flexor and extensor compartments — nine extensor zones clinically mapped.",
            "Median, ulnar, radial nerves traverse wrist — vulnerability in deflection.",
        ],
        "mechanical": [
            "Pronation/supination — 180° arc drives palm orientation for blocks and weapon presentation.",
            "Wrist as torque transmitter — stiff wrist for straight punches; relaxed for whipping hooks.",
            "Forearm lever — ulna stable, radius rotates; blocking uses both-bone rigidity.",
            "Flexor mass is stronger than extensors — curl grip survives longer than push-open in clinch.",
        ],
        "combat": [
            "Wrist locks and bent-arm entries — exploit flexion + rotation limits (educational).",
            "Forearm shield — radius/ulna bridge for high blocks and inside deflection.",
            "Knife edge of forearm — brachioradialis ridge for close striking.",
            "Gi/sleeve grips anchor at wrist and distal forearm — control precedes submission.",
            "Weaponized combat: wrist alignment for recoil management and retention.",
        ],
        "training": "motor_command wrist_l/wrist_r · rotate primitives in hand-core",
    },
    "elbow": {
        "title": "Exploring the Elbow",
        "book_id": "exploring_the_elbow",
        "accent": (180, 140, 120),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "elbow", "hinge", "armbar", "strike"],
        "joints": ["elbow_l", "elbow_r"],
        "biology": [
            "Hinge joint — humeroulnar primary flexion/extension; humeroradial and proximal radioulnar for rotation.",
            "Olecranon bursa and tip — ground contact in sprawl mechanics.",
            "Collateral ligaments — valgus/varus stability; arm bar stresses medial band.",
            "Brachial artery and median nerve in cubital fossa — awareness in hyperextension.",
        ],
        "mechanical": [
            "Elbow is a third-class lever in many strikes — speed at fist, force from shoulder and torso.",
            "Lockout vs slight flex — hyperextension risk in arm bars and over-throws.",
            "Carrying angle (5–15° valgus) — affects guard posture and elbow strike angle.",
        ],
        "combat": [
            "Muay Thai elbow — horizontal, upward, slashing arcs from hinge.",
            "Arm bar (juji gatame) — fulcrum at elbow, lever arm is forearm + body weight.",
            "Frame and post — elbow inside hip creates structural guard in bottom position.",
            "Sprawl — elbow extension drives hips back against shots.",
        ],
        "training": "humanoid-motion elbow zone amplitudes · muay_thai skill primitive",
    },
    "shoulder": {
        "title": "Exploring the Shoulder",
        "book_id": "exploring_the_shoulder",
        "accent": (170, 130, 115),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "shoulder", "throw", "mobility"],
        "joints": ["shoulder_l", "shoulder_r"],
        "biology": [
            "Ball-and-socket — glenohumeral with shallow socket; rotator cuff (SITS) dynamic stability.",
            "Scapulothoracic rhythm — every 2° GH motion pairs with 1° scap motion.",
            "Deltoid, pectoralis major, latissimus — prime movers for strike and throw.",
            "Labrum and biceps long head — overhead and kimura stress patterns.",
        ],
        "mechanical": [
            "Greatest ROM in body — abduction 180°, flexion 180°, rotation extensive.",
            "Kinetic chain: hip → torso → shoulder → elbow → hand for maximum strike velocity.",
            "Scapular retraction sets punching platform; protraction for long hooks.",
        ],
        "combat": [
            "Overhand and uppercut — shoulder flexion + internal rotation.",
            "Throws (judo, wrestling) — shoulder as axis for uchi mata, seoi nage.",
            "Kimura and americana — exploit rotation and extension limits.",
            "Clinch — overhooks and underhooks are shoulder dominance contests.",
        ],
        "training": "shoulder_l/r motor limits in body-core · expanded envelopes in motion-secured",
    },
    "spine": {
        "title": "Exploring the Spine",
        "book_id": "exploring_the_spine",
        "accent": (160, 125, 110),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "spine", "posture", "flexion"],
        "joints": ["spine_upper", "spine_mid", "spine_lower", "chest", "neck"],
        "biology": [
            "Cervical (7), thoracic (12), lumbar (5), sacrum, coccyx — curvature lordosis/kyphosis.",
            "Intervertebral discs — nucleus pulposus shock absorption; flexion loads anterior annulus.",
            "Erector spinae, multifidus, transversus abdominis — segmental stability.",
            "Spinal cord within vertebral canal — axial loading and flexion injury awareness.",
        ],
        "mechanical": [
            "Segmental flexion — touch toes distributes load across spine_upper/mid/lower.",
            "Rotation limited in thoracic vs lumbar — punching torque originates low, transmits up.",
            "Neutral spine vs flexed — sprawl and deadlift patterns protect discs under load.",
        ],
        "combat": [
            "Spinal flexion — touch toes, forward fold, shot entries with neutral head.",
            "Cat-cow wave — mobility for ground transitions and guard retention.",
            "Postural integrity under clinch — avoid cervical hyperextension in guillotine defense.",
            "Body lock and mat returns — spine alignment prevents counter throws.",
        ],
        "training": "bend_forward · touch_toes · humanoid-motion mobility skills",
    },
    "core": {
        "title": "Exploring the Core",
        "book_id": "exploring_the_core",
        "accent": (150, 120, 105),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "core", "breath", "power"],
        "joints": ["chest", "hip", "spine_mid", "spine_lower"],
        "biology": [
            "Rectus abdominis, obliques, transversus — trunk flexion, rotation, compression.",
            "Diaphragm — breathing and intra-abdominal pressure; exhale on strike.",
            "Quadratus lumborum, psoas — hip flexion and lateral stability.",
            "Thoracolumbar fascia — force transfer from legs to upper body.",
        ],
        "mechanical": [
            "Intra-abdominal pressure — stiffens core for impact absorption and strike delivery.",
            "Separation — hips lead, shoulders follow in rotational strikes (hook, kick).",
            "Anti-rotation — sprawls and single-leg defense require oblique bracing.",
        ],
        "combat": [
            "Breath discipline — kiai exhale, never hold breath under grappling pressure.",
            "Ground and pound — core posts on opponent, isolates strike arm.",
            "Knee-on-belly — core weight distribution pins without arm fatigue.",
            "Rotational power — boxing hook, round kick, discus motion in throws.",
        ],
        "training": "proprioception COM · balance receipts in body-core",
    },
    "hip_pelvis": {
        "title": "Exploring the Hip and Pelvis",
        "book_id": "exploring_the_hip_and_pelvis",
        "accent": (140, 115, 100),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "hip", "pelvis", "sprawl", "guard"],
        "joints": ["hip"],
        "biology": [
            "Acetabulum and femoral head — ball-and-socket with labrum.",
            "Gluteus maximus, medius, minimus — extension, abduction, pelvic stability.",
            "Hip flexors (iliopsoas, rectus femoris) — knee drive and guard closed.",
            "Inguinal ligament and femoral triangle — anatomical landmark for strikes (educational legal frame).",
        ],
        "mechanical": [
            "Hip flexion 120°+ — high kick chamber; extension drives sprawl and bridge.",
            "Abduction — horse stance width, lateral stability in clinch.",
            "Pelvis tilt — anterior for strikes, posterior for defensive shell.",
        ],
        "combat": [
            "Sprawl — hip extension defeats double-leg timing.",
            "Guard — hip flexion and abduction frame closed guard and triangles.",
            "Hip bump and bridge — escape bottom side control.",
            "Low kicks attack thigh nerves — combatant targets mobility (sport rules vs self-defense context).",
        ],
        "training": "hip motor_command · horse_stance · guard_pull primitives",
    },
    "knee": {
        "title": "Exploring the Knee",
        "book_id": "exploring_the_knee",
        "accent": (130, 110, 95),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "knee", "kick", "takedown"],
        "joints": ["knee_l", "knee_r"],
        "biology": [
            "Hinge with slight rotation when flexed — ACL/PCL cruciate stability.",
            "Menisci — load distribution; rotation with loaded flexion risks tear.",
            "Patella — sesamoid increases quadriceps leverage.",
            "Collateral ligaments — valgus/varus in leg checks.",
        ],
        "mechanical": [
            "Flexion 140° — chamber for kicks; minimal hyperextension (5°) — beware heel hooks.",
            "Ground reaction force through knee in lunges and shots.",
            "Valgus collapse — common ACL mechanism; train neutral knee over toe.",
        ],
        "combat": [
            "Muay Thai round kick — rotate hip, snap knee into strike surface.",
            "Clinch knees — short arc, point of knee to body.",
            "Single and double leg — knee penetration step.",
            "Leg checks — lift and rotate to block low kick.",
        ],
        "training": "knee_l/r limits · double_leg · round_kick motion skills",
    },
    "ankle_foot": {
        "title": "Exploring the Ankle and Foot",
        "book_id": "exploring_the_ankle_and_foot",
        "accent": (120, 105, 90),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "ankle", "foot", "balance", "root"],
        "joints": ["ankle_l", "ankle_r", "foot_l", "foot_r", "toe_l", "toe_r"],
        "biology": [
            "Talocrural joint — dorsiflexion/plantarflexion; subtalar inversion/eversion.",
            "Plantar fascia — arch support; barefoot training loads differently.",
            "Peroneal and tibialis — ankle stability in lateral movement.",
            "Toes — metatarsophalangeal flexion for grip on mat and ground.",
        ],
        "mechanical": [
            "Root — weight distribution forefoot/rearfoot; tai chi root step.",
            "Ankle stiffness for teep; mobility for pivot on round kick.",
            "Toe reach — touch toes chain terminates at toe_l/toe_r body image anchors.",
        ],
        "combat": [
            "Stance — bladed vs square; lead foot heel up for kicks.",
            "Foot sweeps (osoto gari, de ashi barai) — attack ankle balance.",
            "Calf kicks — compromise plantarflexion power.",
            "Ground — toes hook legs for guard and submissions.",
        ],
        "training": "touch_toes · foot_l/r positions · toe reach proprioception",
    },
    "neck_head": {
        "title": "Exploring the Neck and Head",
        "book_id": "exploring_the_neck_and_head",
        "accent": (110, 100, 85),
        "tags": ["exploring", "anatomy", "mechanical", "combat", "neck", "head", "awareness"],
        "joints": ["head", "neck"],
        "biology": [
            "Cervical vertebrae C1–C7 — atlas/axis allow head rotation.",
            "Sternocleidomastoid, trapezius — head control in clinch.",
            "Carotid and jugular — choke anatomy (blood vs air choke educational distinction).",
            "Brain housed in calvarium — concussion awareness; chin tuck protects jaw.",
        ],
        "mechanical": [
            "Head is heavy lever — small neck muscles move large mass; whiplash in clinch snaps.",
            "Chin tuck — aligns occiput with spine, reduces KO vulnerability.",
            "Eyes lead head lead body — OODA and striking accuracy.",
        ],
        "combat": [
            "Rear-naked choke — lateral forearm on carotids, bicep-hand trap (educational).",
            "Head position in wrestling — inside control, snap downs.",
            "Slip and roll — head off centerline, not leaning back.",
            "Forehead in clinch — Thai plum posture (sport-specific).",
        ],
        "training": "head/neck zone in motion-secured · boxing slip primitive",
    },
}


def _veh_mod() -> Any:
    path = INSTALL / "lib" / "field-exploring-vehicles.py"
    spec = importlib.util.spec_from_file_location("exploring_veh", path)
    if not spec or not spec.loader:
        raise ImportError("field-exploring-vehicles.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chapters() -> list[dict[str, Any]]:
    return [
        {"num": i + 1, "slug": slug, "title": title}
        for i, (slug, title) in enumerate([
            ("01-scope", "Personhood & combat scope"),
            ("02-biology", "Biology — structures & innervation"),
            ("03-mechanical", "Mechanical — levers & ROM"),
            ("04-combat", "Combat usage"),
            ("05-injury", "Injury awareness"),
            ("06-training", "Training lattice"),
            ("07-pairing", "Pairing with combat books"),
            ("08-ai-keys", "AI retrieval keys"),
        ])
    ]


def build_part_text(spec: dict[str, Any]) -> str:
    v = _veh_mod()
    doc = _load_doctrine()
    joints = ", ".join(spec.get("joints") or [])
    return "\n".join([
        f"# {spec['title']}",
        "", "![Cover](h7fig:cover)", "",
        f"**Mechanical and biological depth for personhood combat** — {spec['title'].replace('Exploring ', 'the ')}.",
        f"- **Updated:** {v._now()}",
        f"- **Dewey:** 611 — Human anatomy",
        f"- **Paired:** *Exploring Hand-to-Hand Combat* · *Exploring Weaponized Combat*",
        f"- **Disclaimer:** {doc.get('disclaimer', 'Educational only.')}",
        "", "---", "",
        v._section("1. Personhood & combat scope", v._bullet_list([
            "This book is for the **embodied person** — biology and mechanics of one body area for combat literacy.",
            f"Body-core joints: {joints or 'see limb registry'}.",
            "Not vehicle anatomy — see *Exploring Military Vehicles* for platforms.",
            "Hostess 7 reads through Ironclad + library truth gate before teaching from this page.",
        ])),
        v._section("2. Biology — structures & innervation", v._bullet_list(spec.get("biology") or [])),
        v._section("3. Mechanical — levers, ROM, kinetic chain", v._bullet_list(spec.get("mechanical") or [])),
        v._section("4. Combat usage", v._bullet_list(spec.get("combat") or [])),
        v._section("5. Injury awareness (educational)", v._bullet_list([
            "Know vulnerable structures — never target for harm outside lawful self-defense education.",
            "Pain vs structural damage — stop training on acute joint swelling or neuro symptoms.",
            "Rehabilitation returns ROM before power — pair with hostess7-biology clinical context.",
            "Concussion, hyperextension, and compression injuries — seek medical care when indicated.",
        ])),
        v._section("6. Training lattice", v._bullet_list([
            str(spec.get("training") or "hostess7-body-core · humanoid-motion-secured"),
            "Limb identity registry — range envelopes and body image tie per joint.",
            "Motion secure cycle — witness proprioception receipts during self-maintenance.",
            "Hand-to-hand skill load — primitives in humanoid-motion-doctrine for this zone.",
        ])),
        v._section("7. Pairing with combat books", v._table(
            ["Book", "Use with this volume"],
            [
                ["Exploring Hand-to-Hand Combat", "Technique families that load this anatomy"],
                ["Exploring Weaponized Combat", "Retention and grip when weapons involved"],
                ["hostess7-anatomy-book.py", "Clinical anatomy depth per organ system"],
            ],
        )),
        v._section("8. AI retrieval keys", v._bullet_list([
            f"book_id: `{spec['book_id']}`",
            f"tags: {', '.join(spec.get('tags') or [])}",
            "Index: `area`, `biology`, `mechanical`, `combat`, `joint`, `personhood`, `dewey:611`",
            "Facet search: `python3 lib/field-dewey-index.py search --tag anatomy --combat`",
        ])),
        "",
    ])


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def generate_book(part_key: str) -> dict[str, Any]:
    spec = PARTS.get(part_key)
    if not spec:
        return {"ok": False, "error": "unknown_part", "part": part_key}
    v = _veh_mod()
    text = build_part_text(spec)
    rep = v.pack_book(
        book_id=spec["book_id"],
        title=spec["title"],
        text=text,
        shelf=SHELF,
        dewey="611",
        dewey_label="Human anatomy",
        subject=f"combat anatomy — {part_key}",
        accent=spec["accent"],
    )
    pdf_name = f"Hostess7_{spec['title'].replace(' ', '_')}_Textbook.pdf"
    h7c_rel = f"{spec['book_id']}/{spec['book_id']}.h7c"
    pdf_ok = v._write_textbook_pdf(text, SHELF / pdf_name, spec["title"])
    manifest = v._write_book_manifest(
        shelf=SHELF,
        book_id=spec["book_id"],
        title=spec["title"],
        dewey="611",
        pdf_name=pdf_name,
        h7c_rel=h7c_rel,
        chapters=_chapters(),
        char_count=len(text),
    )
    v._update_shelf(
        SHELF,
        "611",
        "611-human-anatomy",
        {
            "id": spec["book_id"],
            "title": spec["title"],
            "author": "AmmoOS Field Library",
            "dewey": "611",
            "format": "h7c",
            "h7c": f"library/dewey/611-human-anatomy/{h7c_rel}",
            "pdf": f"library/dewey/611-human-anatomy/{pdf_name}",
            "manifest": f"library/dewey/611-human-anatomy/{spec['book_id']}/book-manifest.json",
            "cover": f"/world/assets/combinatronic/books/{spec['book_id']}.png",
            "book_kind": "exploring",
            "personhood": True,
            "combat_anatomy": True,
            "area": part_key,
            "ready": True,
        },
    )
    book_json_path = SHELF / spec["book_id"] / "book.json"
    if book_json_path.is_file():
        try:
            book_doc = json.loads(book_json_path.read_text(encoding="utf-8"))
            book_doc["personhood"] = True
            book_doc["combat_anatomy"] = True
            book_doc["combat_usage"] = True
            book_doc["area"] = part_key
            book_doc["tags"] = spec.get("tags") or []
            book_doc["keywords"] = book_doc["tags"]
            book_doc["joints"] = spec.get("joints") or []
            book_doc["paired_combat"] = ["exploring_hand_to_hand_combat", "exploring_weaponized_combat"]
            book_json_path.write_text(json.dumps(book_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass
    rep["pdf"] = pdf_name if pdf_ok else None
    rep["manifest"] = str(manifest)
    rep["char_count"] = len(text)
    return rep


def generate_all(*, part: str | None = None) -> dict[str, Any]:
    aliases = {
        "hand": "hand",
        "the_hand": "hand",
        "wrist": "wrist_forearm",
        "forearm": "wrist_forearm",
        "elbow": "elbow",
        "shoulder": "shoulder",
        "spine": "spine",
        "core": "core",
        "hip": "hip_pelvis",
        "pelvis": "hip_pelvis",
        "knee": "knee",
        "ankle": "ankle_foot",
        "foot": "ankle_foot",
        "neck": "neck_head",
        "head": "neck_head",
    }
    keys = list(PARTS.keys())
    if part:
        resolved = aliases.get(part, part)
        if resolved not in PARTS:
            for k, spec in PARTS.items():
                if spec["book_id"] == part or part in spec["book_id"]:
                    resolved = k
                    break
            else:
                return {"ok": False, "error": "unknown_part", "part": part}
        keys = [resolved]
    results = {k: generate_book(k) for k in keys}
    return {
        "ok": True,
        "count": len(results),
        "personhood": True,
        "combat_anatomy": True,
        "books": results,
        "format": "h7c",
        "updated": _veh_mod()._now(),
    }


def list_parts() -> list[dict[str, Any]]:
    return [
        {"part": k, "book_id": v["book_id"], "title": v["title"], "joints": v.get("joints")}
        for k, v in PARTS.items()
    ]


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower().replace("-", "_")
    if cmd == "all":
        print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "list":
        print(json.dumps(list_parts(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(generate_all(part=cmd), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())