#!/usr/bin/env pythong
"""Exploring subject books — biology, math, history, engineering, geography, chemistry, combat."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
LIBRARY = INSTALL / "library" / "dewey"


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


def build_exploring_biology() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring Biology",
        "", "![Cover](h7fig:cover)", "",
        "**Life sciences through human medicine** — for Hostess 7 field counsel and AI retrieval.",
        f"- **Updated:** {v._now()}",
        "- **Scope:** cell → organism → ecology → human anatomy & physiology",
        "- **Disclaimer:** Educational only — not medical advice.",
        "", "---", "",
        v._section("1. Foundations", v._bullet_list([
            "Cell theory — all life from cells; Hooke, Schwann, Schleiden",
            "Levels of organization — molecule, organelle, cell, tissue, organ, system, organism",
            "Homeostasis — negative feedback; thermoregulation, glucose, pH",
            "Scientific method — hypothesis, experiment, peer review",
        ])),
        v._section("2. Cell biology", v._table(
            ["Organelle", "Role", "Mnemonic hook"],
            [
                ["Nucleus", "DNA, transcription", "Control center"],
                ["Mitochondria", "ATP, aerobic respiration", "Powerhouse"],
                ["Ribosome", "Translation", "Protein factory"],
                ["ER / Golgi", "Fold, sort, ship proteins", "Assembly line"],
                ["Lysosome", "Digestion, autophagy", "Recycling"],
                ["Chloroplast", "Photosynthesis (plants)", "Solar panel"],
            ],
        )),
        v._section("3. Genetics", v._bullet_list([
            "DNA double helix — A-T, G-C base pairing",
            "Central dogma — DNA → RNA → protein",
            "Mendel — dominance, segregation, independent assortment",
            "CRISPR — guided nuclease editing (policy-sensitive applications)",
        ])),
        v._section("4. Human systems (overview)", v._table(
            ["System", "Primary organs", "Core function"],
            [
                ["Integumentary", "Skin, hair, nails", "Barrier, thermoregulation"],
                ["Skeletal", "Bones, joints", "Support, mineral store"],
                ["Muscular", "Skeletal, cardiac, smooth", "Movement, pump"],
                ["Nervous", "Brain, spinal cord, nerves", "Integration, reflex"],
                ["Endocrine", "Glands", "Hormonal signaling"],
                ["Cardiovascular", "Heart, vessels", "Transport"],
                ["Respiratory", "Lungs, airways", "Gas exchange"],
                ["Digestive", "GI tract, liver, pancreas", "Nutrient processing"],
                ["Immune", "Lymph, WBC", "Defense"],
                ["Reproductive", "Gonads, ducts", "Gametes"],
            ],
        )),
        v._section("5. Microbiology & immunity", v._bullet_list([
            "Prokaryote vs eukaryote — bacteria, archaea, viruses (acellular)",
            "Innate vs adaptive immunity — barriers, inflammation, antibodies, T/B cells",
            "Vaccination — memory response, herd immunity concept",
        ])),
        v._section("6. AI retrieval keys", "Index: `domain`, `system`, `organ`, `process`, `pathogen`. Dewey **570**. Pair *Exploring Chemistry*."),
        "",
    ])


def build_exploring_mathematics() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring Mathematics",
        "", "![Cover](h7fig:cover)", "",
        "**From arithmetic through calculus and linear algebra** — field manual for operators and AI.",
        f"- **Updated:** {v._now()}",
        "", "---", "",
        v._section("1. Number systems", v._table(
            ["Set", "Examples", "Use"],
            [["ℕ", "1, 2, 3…", "Counting"], ["ℤ", "…−1, 0, 1…", "Difference"], ["ℚ", "p/q", "Ratio"],
             ["ℝ", "π, √2", "Continuous measure"], ["ℂ", "a+bi", "Engineering, quantum"]],
        )),
        v._section("2. Algebra", v._bullet_list([
            "Variables, expressions, equations, inequalities",
            "Polynomials — factor, quadratic formula",
            "Functions — domain, range, composition, inverse",
            "Logarithms & exponentials — ln, e^x, growth/decay",
        ])),
        v._section("3. Geometry & trigonometry", v._bullet_list([
            "Euclidean axioms — points, lines, angles, congruence",
            "Pythagorean theorem — a²+b²=c²",
            "sin, cos, tan — unit circle, radians",
            "Vectors in ℝ² and ℝ³",
        ])),
        v._section("4. Calculus", v._table(
            ["Topic", "Core idea", "Symbol"],
            [["Limit", "Approach without necessarily reaching", "lim"],
             ["Derivative", "Instantaneous rate of change", "d/dx"],
             ["Integral", "Accumulation, area under curve", "∫"],
             ["FTC", "Derivative and integral invert (conditions)", "Part I & II"]],
        )),
        v._section("5. Linear algebra", v._bullet_list([
            "Matrices, determinants, eigenvalues",
            "Linear transformations — rotation, scale, shear",
            "Applications — graphics, ML weights, physics",
        ])),
        v._section("6. AI retrieval keys", "Index: `branch`, `theorem`, `symbol`, `application`. Dewey **510**."),
        "",
    ])


def build_exploring_history() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring History",
        "", "![Cover](h7fig:cover)", "",
        "**World history spine** — eras, civilizations, and load-bearing turning points.",
        f"- **Updated:** {v._now()}",
        "", "---", "",
        v._section("1. Method", v._bullet_list([
            "Primary vs secondary sources — provenance matters",
            "Periodization — convenience with argued boundaries",
            "Historiography — interpretation changes with evidence",
        ])),
        v._section("2. Eras (global spine)", v._table(
            ["Era", "Span (approx)", "Hallmark"],
            [
                ["Prehistory", "to ~3500 BCE", "Stone tools, migration, agriculture dawn"],
                ["Ancient", "~3500 BCE–500 CE", "States, writing, empires"],
                ["Medieval", "~500–1500", "Feudalism, trade routes, plague"],
                ["Early modern", "~1500–1800", "Print, exploration, revolution"],
                ["Modern", "~1800–1945", "Industrial, world wars"],
                ["Contemporary", "1945–present", "Cold War, decolonization, digital"],
            ],
        )),
        v._section("3. Civilization anchors", v._bullet_list([
            "Mesopotamia — law, wheel, city",
            "Egypt — Nile agriculture, monuments",
            "Indus & China — urban planning, bureaucracy",
            "Greece & Rome — citizenship, law, engineering",
            "Islamic golden age — algebra, medicine, translation",
            "Americas — Maya, Aztec, Inca independently",
        ])),
        v._section("4. Load-bearing years (examples)", v._table(
            ["Year", "Event", "Why it matters"],
            [
                ["1440", "Gutenberg press", "Mass literacy, Reformation enable"],
                ["1492", "Columbian exchange", "Global biology & economy rewired"],
                ["1789", "French Revolution", "Nation-state, rights discourse"],
                ["1914", "WWI begins", "Modern industrial total war"],
                ["1945", "UN, atomic age", "New world order"],
                ["1989", "Berlin Wall falls", "Cold War fracture"],
            ],
        )),
        v._section("5. AI retrieval keys", "Index: `era`, `region`, `civilization`, `year`, `source_type`. Dewey **900**."),
        "",
    ])


def build_exploring_engineering() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring Engineering",
        "", "![Cover](h7fig:cover)", "",
        "**Mechanical, electrical, civil, and field-stack engineering** — exhaustive primer.",
        f"- **Updated:** {v._now()}",
        "", "---", "",
        v._section("1. Disciplines", v._table(
            ["Branch", "Focus", "Example artifact"],
            [["Mechanical", "Force, motion, heat", "Engine, gearbox"],
             ["Electrical", "Charge, field, circuit", "Motor, grid"],
             ["Civil", "Structures, water, transport", "Bridge, dam"],
             ["Chemical", "Process, reaction", "Refinery"],
             ["Software", "Logic, systems", "Compiler, OS"],
             ["Field", "Plate, combinatorics, Grok16", "AmmoOS stack"]],
        )),
        v._section("2. Core laws", v._bullet_list([
            "Newton's laws — inertia, F=ma, action-reaction",
            "Thermodynamics — energy conservation, entropy",
            "Ohm's law — V=IR",
            "Bernoulli — fluid pressure vs velocity",
            "Hooke — elastic deformation",
        ])),
        v._section("3. Materials", v._bullet_list([
            "Steel, aluminum, titanium, composites, ceramics",
            "Fatigue, creep, fracture — failure modes",
            "Safety factor — design margin",
        ])),
        v._section("4. Field stack engineering", v._bullet_list([
            "Ironclad — truth gates before adapt",
            "CHIPs — Grok16 field_opt silicon emulation",
            "Plate meld — uninterruptable truth between plates",
            "Thermal guard — Landauer-aware incremental redata",
        ])),
        v._section("5. AI retrieval keys", "Index: `discipline`, `law`, `material`, `failure_mode`. Dewey **620**."),
        "",
    ])


def build_exploring_geography() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring Geography",
        "", "![Cover](h7fig:cover)", "",
        "**Physical and human geography** — landforms, climate, population, borders.",
        f"- **Updated:** {v._now()}",
        "", "---", "",
        v._section("1. Physical geography", v._bullet_list([
            "Lithosphere — plates, earthquakes, volcanoes, orogeny",
            "Hydrosphere — oceans, rivers, water cycle",
            "Atmosphere — layers, weather vs climate, Hadley cells",
            "Biosphere — biomes — tundra, taiga, desert, savanna, rainforest",
        ])),
        v._section("2. Human geography", v._table(
            ["Theme", "Questions", "Tools"],
            [
                ["Population", "Growth, migration, density", "Census, demography"],
                ["Urban", "Cities, sprawl, infrastructure", "GIS, zoning"],
                ["Political", "Borders, sovereignty, conflict", "Maps, treaties"],
                ["Economic", "Trade, resources, development", "GDP, supply chains"],
                ["Cultural", "Language, religion, diffusion", "Ethnography"],
            ],
        )),
        v._section("3. Cartography", v._bullet_list([
            "Projections — Mercator, Robinson, local UTM",
            "Scale, contour, legend, datum (WGS84)",
            "Remote sensing — satellite, LiDAR, SAR",
        ])),
        v._section("4. AI retrieval keys", "Index: `region`, `biome`, `theme`, `coordinate`. Dewey **910**."),
        "",
    ])


def build_exploring_chemistry() -> str:
    v = _veh_mod()
    return "\n".join([
        "# Exploring Chemistry",
        "", "![Cover](h7fig:cover)", "",
        "**Atoms through organic chemistry** — periodic table, reactions, stoichiometry.",
        f"- **Updated:** {v._now()}",
        "", "---", "",
        v._section("1. Atomic structure", v._bullet_list([
            "Proton, neutron, electron — atomic number Z, mass A",
            "Isotopes — same Z, different neutron count",
            "Electron configuration — shells, orbitals, Aufbau",
        ])),
        v._section("2. Periodic table regions", v._table(
            ["Region", "Traits", "Examples"],
            [
                ["Alkali metals", "Soft, +1 ion", "Li, Na, K"],
                ["Halogens", "Reactive nonmetals", "F, Cl, Br"],
                ["Noble gases", "Inert full shell", "He, Ne, Ar"],
                ["Transition metals", "Variable oxidation", "Fe, Cu, Zn"],
                ["Lanthanides/actinides", "f-block", "U, Pu"],
            ],
        )),
        v._section("3. Bonding & reactions", v._bullet_list([
            "Ionic, covalent, metallic, hydrogen bonds",
            "Balancing equations — conservation of mass",
            "Acid-base — pH, neutralization",
            "Redox — oxidation states, electron transfer",
            "Thermochemistry — enthalpy, exo vs endo",
        ])),
        v._section("4. Organic overview", v._bullet_list([
            "Hydrocarbons — alkane, alkene, alkyne, aromatic",
            "Functional groups — alcohol, carbonyl, carboxyl, amine",
            "Polymers — addition vs condensation",
        ])),
        v._section("5. AI retrieval keys", "Index: `element`, `bond`, `reaction_type`, `functional_group`. Dewey **540**. Pair *Exploring Biology*."),
        "",
    ])


def _combat_personhood_mod() -> Any:
    path = INSTALL / "lib" / "field-exploring-combat-personhood.py"
    spec = importlib.util.spec_from_file_location("exploring_combat_ph", path)
    if not spec or not spec.loader:
        raise ImportError("field-exploring-combat-personhood.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SUBJECTS: list[dict[str, Any]] = [
    {
        "book_id": "exploring_biology",
        "title": "Exploring Biology",
        "builder": build_exploring_biology,
        "shelf": LIBRARY / "500-science",
        "shelf_code": "500",
        "shelf_title": "500-science",
        "dewey": "570",
        "dewey_label": "Biology",
        "subject": "biology — life sciences",
        "accent": (60, 160, 90),
        "chapters": _chapters(
            ("01-foundations", "Foundations"),
            ("02-cell", "Cell biology"),
            ("03-genetics", "Genetics"),
            ("04-human-systems", "Human systems"),
            ("05-micro-immunity", "Microbiology & immunity"),
            ("06-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_chemistry",
        "title": "Exploring Chemistry",
        "builder": build_exploring_chemistry,
        "shelf": LIBRARY / "500-science",
        "shelf_code": "500",
        "shelf_title": "500-science",
        "dewey": "540",
        "dewey_label": "Chemistry",
        "subject": "chemistry — atoms through organic",
        "accent": (200, 80, 180),
        "chapters": _chapters(
            ("01-atoms", "Atomic structure"),
            ("02-periodic", "Periodic table"),
            ("03-reactions", "Bonding & reactions"),
            ("04-organic", "Organic overview"),
            ("05-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_mathematics",
        "title": "Exploring Mathematics",
        "builder": build_exploring_mathematics,
        "shelf": LIBRARY / "510-mathematics",
        "shelf_code": "510",
        "shelf_title": "510-mathematics",
        "dewey": "510",
        "dewey_label": "Mathematics",
        "subject": "mathematics — arithmetic through linear algebra",
        "accent": (70, 130, 220),
        "chapters": _chapters(
            ("01-numbers", "Number systems"),
            ("02-algebra", "Algebra"),
            ("03-geometry", "Geometry & trigonometry"),
            ("04-calculus", "Calculus"),
            ("05-linear", "Linear algebra"),
            ("06-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_history",
        "title": "Exploring History",
        "builder": build_exploring_history,
        "shelf": LIBRARY / "900-history",
        "shelf_code": "900",
        "shelf_title": "900-history",
        "dewey": "900",
        "dewey_label": "History",
        "subject": "history — world spine",
        "accent": (160, 120, 60),
        "chapters": _chapters(
            ("01-method", "Method"),
            ("02-eras", "Eras"),
            ("03-civilizations", "Civilization anchors"),
            ("04-turning-points", "Load-bearing years"),
            ("05-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_engineering",
        "title": "Exploring Engineering",
        "builder": build_exploring_engineering,
        "shelf": LIBRARY / "600-technology",
        "shelf_code": "600",
        "shelf_title": "600-technology",
        "dewey": "620",
        "dewey_label": "Engineering",
        "subject": "engineering — mechanical through field stack",
        "accent": (120, 120, 130),
        "chapters": _chapters(
            ("01-disciplines", "Disciplines"),
            ("02-laws", "Core laws"),
            ("03-materials", "Materials"),
            ("04-field-stack", "Field stack engineering"),
            ("05-ai-keys", "AI retrieval keys"),
        ),
    },
    {
        "book_id": "exploring_geography",
        "title": "Exploring Geography",
        "builder": build_exploring_geography,
        "shelf": LIBRARY / "910-education",
        "shelf_code": "910",
        "shelf_title": "910-education",
        "dewey": "910",
        "dewey_label": "Geography",
        "subject": "geography — physical and human",
        "accent": (50, 150, 130),
        "chapters": _chapters(
            ("01-physical", "Physical geography"),
            ("02-human", "Human geography"),
            ("03-cartography", "Cartography"),
            ("04-ai-keys", "AI retrieval keys"),
        ),
    },
]


def generate_subject(spec: dict[str, Any]) -> dict[str, Any]:
    v = _veh_mod()
    text = spec["builder"]()
    rep = v.pack_book(
        book_id=spec["book_id"],
        title=spec["title"],
        text=text,
        shelf=spec["shelf"],
        dewey=spec["dewey"],
        dewey_label=spec["dewey_label"],
        subject=spec["subject"],
        accent=spec["accent"],
    )
    pdf_name = f"Hostess7_{spec['title'].replace(' ', '_')}_Textbook.pdf"
    h7c_rel = f"{spec['book_id']}/{spec['book_id']}.h7c"
    pdf_ok = v._write_textbook_pdf(text, spec["shelf"] / pdf_name, spec["title"])
    manifest = v._write_book_manifest(
        shelf=spec["shelf"],
        book_id=spec["book_id"],
        title=spec["title"],
        dewey=spec["dewey"],
        pdf_name=pdf_name,
        h7c_rel=h7c_rel,
        chapters=spec["chapters"],
        char_count=len(text),
    )
    v._update_shelf(
        spec["shelf"],
        spec["shelf_code"],
        spec["shelf_title"],
        {
            "id": spec["book_id"],
            "title": spec["title"],
            "author": "AmmoOS Field Library",
            "dewey": spec["dewey"],
            "format": "h7c",
            "h7c": f"library/dewey/{spec['shelf_title']}/{h7c_rel}",
            "pdf": f"library/dewey/{spec['shelf_title']}/{pdf_name}",
            "manifest": f"library/dewey/{spec['shelf_title']}/{spec['book_id']}/book-manifest.json",
            "cover": f"/world/assets/combinatronic/books/{spec['book_id']}.png",
            "book_kind": "exploring",
            "ready": True,
        },
    )
    rep["pdf"] = pdf_name if pdf_ok else None
    rep["manifest"] = str(manifest)
    return rep


def generate_all(*, book_id: str | None = None) -> dict[str, Any]:
    specs = SUBJECTS if not book_id else [s for s in SUBJECTS if s["book_id"] == book_id]
    if book_id and not specs:
        combat_aliases = {"hand", "hand_to_hand", "weapon", "weaponized", "exploring_hand_to_hand_combat", "exploring_weaponized_combat"}
        if book_id in combat_aliases or book_id.startswith("exploring_") and "combat" in book_id:
            return _combat_personhood_mod().generate_all(book_id=book_id)
        return {"ok": False, "error": "unknown_subject", "book_id": book_id}
    results = {}
    for spec in specs:
        results[spec["book_id"]] = generate_subject(spec)
    if not book_id:
        combat = _combat_personhood_mod().generate_all()
        if combat.get("ok"):
            results.update(combat.get("books") or {})
    return {"ok": True, "count": len(results), "books": results, "format": "h7c", "updated": _veh_mod()._now()}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if cmd == "all":
        print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "list":
        print(json.dumps([{"book_id": s["book_id"], "title": s["title"], "shelf": s["shelf_title"]} for s in SUBJECTS], indent=2))
        return 0
    print(json.dumps(generate_all(book_id=cmd), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())