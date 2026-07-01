#!/usr/bin/env pythong
"""Exploring Historic Battles — strength in numbers, armaments, and decisive factors."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-exploring-historic-battles-doctrine.json"
CORPUS_PATH = INSTALL / "data" / "hostess7-exploring-historic-battles-corpus.json"
LIBRARY = INSTALL / "library" / "dewey"
SERIES_DIR = LIBRARY / "900-history" / "exploring_historic_battles"
PANEL = STATE / "hostess7-exploring-historic-battles-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _battle(
    *,
    name: str,
    date: str,
    place: str,
    belligerents: str,
    forces: str,
    armaments: str,
    technology: str,
    decided_by: str,
    numbers_verdict: str,
) -> str:
    return f"""### {name}

| Field | Detail |
|-------|--------|
| **When** | {date} |
| **Where** | {place} |
| **Belligerents** | {belligerents} |
| **Forces (approx.)** | {forces} |
| **Armaments** | {armaments} |
| **Technology & doctrine** | {technology} |
| **What decided it** | {decided_by} |
| **Strength in numbers** | {numbers_verdict} |

"""


def compose_strength_in_numbers() -> str:
    return """## Strength in Numbers

**Strength in numbers** is the oldest proposition in war: that mass — more spears, more chariots, more rifles, more divisions — can overwhelm an enemy by sheer weight. It is often true. It is never sufficient by itself.

### The proposition

1. **Additive mass** — Two equal units side by side can concentrate fire or shock on one flank while the enemy cannot be everywhere at once.
2. **Absorptive mass** — Larger armies tolerate casualties that would annihilate smaller ones; attrition favors the big battalions if logistics keep pace.
3. **Psychological mass** — Visible numerical superiority breaks morale before contact (Jericho’s walls facing a migrating host; Persian hosts at Marathon seeing hoplite density).

### When numbers lie

| Factor | Effect on “more is better” |
|--------|---------------------------|
| **Terrain** | Thermopylae, Teutoburg Forest, and mountain passes convert numbers into a queue — only the front fights. |
| **Technology leap** | Chariot archery at Kadesh, Roman engineering at Alesia, gunpowder at Constantinople — one generation’s tool negates yesterday’s headcount. |
| **Command & cohesion** | Cannae required Hannibal’s orchestration; a larger Roman army became a smaller killing ground. |
| **Logistics** | Thutmose III at Megiddo marched fast; armies that outrun supply die regardless of muster rolls. |
| **Intelligence & deception** | Salamis was won in the strait, not on the open sea; numbers on paper did not match numbers that could row in the channel. |

### Lanchester’s intuition (modern formalization)

Frederick Lanchester (1916) modeled combat as exchange rates: in **linear** law, losses are proportional to enemy density (ancient melee); in **square** law, losses scale with the product of both forces (aimed fire, artillery). Strength in numbers wins under linear conditions when you can bring more swords to the same square yard. Under square law, concentration and local superiority matter more than national totals — which is why Cannae and envelopment remain textbooks.

### How to read this book

Every battle entry records:

- **Forces** — best scholarly estimates; ancient figures are often propaganda-inflated.
- **Armaments** — what actually killed: sling stone, bronze sword, sarissa, pilum, composite bow.
- **Technology** — siege craft, roads, signal fire, stirrup (where relevant), drill, fleet design.
- **What decided it** — the hinge: not “who had more,” but what broke equilibrium.
- **Strength in numbers** — verdict: did mass win, lose, or get negated?

Volumes proceed chronologically across four sealed editions (I–IV).
"""


def compose_volume_intro(*, volume: int) -> str:
    spans = {
        1: "before the walls of Jericho through Rome’s Rhine disaster (9 CE)",
        2: "late antiquity through the gunpowder revolution (312–1521 CE)",
        3: "early modern drill through industrial slaughter (1525–1918)",
        4: "mechanized total war through contemporary combined arms (1919–present)",
    }
    span = spans.get(volume, "")
    if volume == 1:
        return compose_strength_in_numbers()
    return f"""## Volume {volume} — Introduction

This sealed edition continues **Exploring Historic Battles** — same schema on every page: forces, armaments, technology, decisive factor, strength-in-numbers verdict.

**Span:** {span}

Cross-reference **Volume I** for the full *Strength in Numbers* doctrine (Lanchester, terrain, logistics, deception).
"""


def compose_volume_one_battles() -> str:
    battles = [
        _battle(
            name="Jebel Sahaba — Nile Valley skirmish (prehistory)",
            date="c. 13,000–11,000 BCE",
            place="Jebel Sahaba, Upper Egypt",
            belligerents="Hunter-gatherer bands (distinct cultural groups)",
            forces="Dozens engaged; cemetery records ~40+ individuals with perimortem projectile wounds",
            armaments="Microlithic stone points (arrows & spears); no metal",
            technology="No fortification; mobility and ambush; early evidence of organized group violence",
            decided_by="Archaeology shows repeated projectile trauma — likely raid or reprisal cycle, not a single ‘battle’ in the classical sense. Control of Nile resources and fishing grounds.",
            numbers_verdict="Negated — tiny bands; decisive factor was surprise and projectile reach, not mass.",
        ),
        _battle(
            name="Neolithic Jericho — before the biblical siege",
            date="c. 8000–7000 BCE (PPNA/PPNB walls)",
            place="Tell es-Sultan (Jericho)",
            belligerents="Sedentary cultivators vs raiding or rival settlements",
            forces="Settlement ~2,000–3,000 inhabitants; attackers unknown",
            armaments="Stone axes, clubs; sling stones; wooden spears",
            technology="**Stone revetment wall** (~4m) with **tower** — earliest known town fortification; collective labor as ‘technology’",
            decided_by="Walls transformed raid economics: attackers needed siege patience most Neolithic bands lacked. Defense favored prepared sedentary numbers behind elevation.",
            numbers_verdict="Numbers mattered **inside** the wall; technology (fortification) multiplied effective strength.",
        ),
        _battle(
            name="Siege of Jericho (Late Bronze / Israelite narrative)",
            date="Traditionally ~1406 BCE (scholarly debate: 13th c. BCE)",
            place="Tell es-Sultan",
            belligerents="Israelite confederation (Joshua) vs Canaanite city-state of Jericho",
            forces="Biblical narrative: Israel ~40,000 fighting men muster; Jericho garrison perhaps hundreds–2,000 inside walls",
            armaments="Bronze weapons (limited); slings; spears; ram’s-horn signals",
            technology="Fortified **casemate walls**; Israelite tradition: divine siege instruction, seven-day investiture, final assault after wall failure (textual/earthquake hypotheses in archaeology)",
            decided_by="**Morale + shock + wall breach** (whether earthquake, undermining, or symbolic collapse). Psychological warfare (trumpets, procession) preceding assault. Garrison liquidation ended resistance.",
            numbers_verdict="Attacker mass favored **if** walls fell; until breach, defender’s **multiplier** (walls) negated numerical inferiority.",
        ),
        _battle(
            name="Battle of Megiddo (Thutmose III)",
            date="9 May 1457 BCE (Egyptian regnal chronology)",
            place="Megiddo (Canaan)",
            belligerents="New Kingdom Egypt vs Canaanite coalition",
            forces="Egypt ~10,000–20,000; coalition similar order (chariot arms decisive)",
            armaments="Bronze **khopesh**, spear, bow; **war chariot** (two-man: driver + archer); javelins",
            technology="Chariotry as mobile fire platform; Thutmose’s **forced march** through narrow Aruna pass — risky column, rapid arrival",
            decided_by="Egyptian **command audacity** (narrow pass) + chariot superiority + coalition failure to hold chokepoint. Siege of Megiddo followed; city surrendered after months.",
            numbers_verdict="Rough parity; **speed and chokepoint control** beat raw muster.",
        ),
        _battle(
            name="Battle of Kadesh",
            date="1274 BCE",
            place="Orontes River, Kadesh (Syria)",
            belligerents="Ramesses II (Egypt) vs Muwatalli II (Hittite Empire)",
            forces="Each side ~20,000 infantry + ~2,000–3,000 chariots (Egyptian sources inflate; Hittite reserve hidden)",
            armaments="Composite bow; bronze spear and sword; **three-man Hittite chariots** (fighter, shield-bearer, driver) vs lighter Egyptian two-man",
            technology="Chariot doctrine; **Hittite deception** (feigned retreat); Egyptian **divisional separation** (Amun/Re/Ptah)",
            decided_by="Ramesses’s personal rally of Amun division; Hittite failure to destroy routed Egyptians completely; stalemate → later **Egypt–Hittite peace treaty** (first surviving great-power treaty).",
            numbers_verdict="Hittites had local superiority and surprise; **leadership and reserves** prevented Egyptian annihilation — numbers alone did not hold the field.",
        ),
        _battle(
            name="Battle of Qarqar (Assyrian expansion checked)",
            date="853 BCE",
            place="Qarqar, Syria",
            belligerents="Shalmaneser III (Assyria) vs Damascus-led Levantine coalition (incl. Ahab of Israel per Kurkh Monolith)",
            forces="Assyria ~100,000 claimed (likely inflated); coalition ~60,000–70,000 claimed",
            armaments="Iron beginning to supplement bronze; chariots; infantry phalanx precursors",
            technology="Assyrian combined arms; coalition **allied concentration** rare in Levant",
            decided_by="Coalition held field; Assyrian inscription claims victory but **failed to take Damascus** — political stalemate. Demonstrates anti-Assyrian **numbers in alliance**.",
            numbers_verdict="Allied mass **matched** Assyrian projection; decisive factor = coalition cohesion, not individual city size.",
        ),
        _battle(
            name="Battle of Marathon",
            date="12 September 490 BCE",
            place="Marathon plain, Attica",
            belligerents="Athens (+ Plataea) vs Achaemenid Persia",
            forces="Greeks ~9,000–10,000 hoplites; Persians ~15,000–25,000 (incl. cavalry & archers)",
            armaments="**Hoplite panoply**: bronze cuirass, aspis shield, doru spear, xiphos; Persian wicker shields, arrow volleys, cavalry",
            technology="Greek **heavy infantry density**; double-envelopment sprint; Persian cavalry temporarily absent",
            decided_by="Miltiades’s **weighted center + thin wings** that enveloped Persian flanks; hoplite shock charge into arrow infantry. Cavalry re-embarkation failure.",
            numbers_verdict="Persians had nominal superiority; **tactics + armor + terrain** negated numbers.",
        ),
        _battle(
            name="Battle of Thermopylae",
            date="August 480 BCE",
            place="Thermopylae pass",
            belligerents="Leonidas’s Spartans & allies vs Xerxes’s Persia",
            forces="Greeks ~7,000 (300 Spartans core); Persians ~100,000–300,000 (ancient sources; modern ~70,000–300,000 range)",
            armaments="Hoplite spear-wall; Persian arrows, wicker shields, **Immortals** (elite infantry)",
            technology="Pass constriction; **phalanx**; Greek naval parallel at Artemisium",
            decided_by="**Terrain funnel** for days; Ephialtes’s betrayal revealed Anopaia path; encirclement ended stand. Buying time for Greek coalition morale.",
            numbers_verdict="Classic case: **numbers meaningless** until geometry neutralized.",
        ),
        _battle(
            name="Battle of Salamis",
            date="September 480 BCE",
            place="Saronic Gulf",
            belligerents="Greek trireme fleet vs Persian & Phoenician fleet",
            forces="Greeks ~370 triremes; Persians ~600–800 triremes",
            armaments="**Bronze-rodded ram**; marines; archers; grappling in confined waters",
            technology="Trireme rowed by oarsmen; **narrow channel** negates line-of-battle width",
            decided_by="Themistocles drew Xerxes into **confined waters**; heavier Greek ramming in crowded channel; Persian admirals could not deploy numbers.",
            numbers_verdict="Persian **fleet mass negated by terrain** — local superiority at point of contact.",
        ),
        _battle(
            name="Battle of Plataea",
            date="479 BCE",
            place="Plataea, Boeotia",
            belligerents="Greek coalition vs Persia (Mardonius)",
            forces="Greeks ~38,000 hoplites; Persians ~70,000–120,000 (incl. allies)",
            armaments="Hoplite phalanx vs Persian infantry & cavalry",
            technology="Spartan drill; **logistics** (Greek supply vs Persian lines)",
            decided_by="Mardonius’s death; Persian camp stormed after cavalry failed to break phalanx. Coalition **discipline** after Salamis confidence.",
            numbers_verdict="Persian numbers did not overcome **hoplite cohesion** on favorable ground.",
        ),
        _battle(
            name="Battle of Leuctra",
            date="371 BCE",
            place="Leuctra, Boeotia",
            belligerents="Thebes (Epaminondas) vs Sparta",
            forces="Thebans ~6,000–7,000; Spartans ~10,000–11,000",
            armaments="Spear phalanx; **Sacred Band** (elite 300); Spartan hoplite supremacy broken",
            technology="**Oblique order** — Epaminondas’s deep left wing (50 ranks) vs shallow right; first deliberate tactical asymmetry",
            decided_by="Concentrated **Theban left** shattered Spartan right; Cleombrotus killed. Doctrine beat Spartan prestige numbers.",
            numbers_verdict="Sparta had more men; **local 50:1 depth** created numerical superiority where it mattered.",
        ),
        _battle(
            name="Battle of Gaugamela (Arbela)",
            date="1 October 331 BCE",
            place="Gaugamela, Mesopotamia",
            belligerents="Alexander III (Macedon) vs Darius III (Persia)",
            forces="Macedon ~47,000; Persia ~50,000–100,000 cavalry + infantry + scythed chariots",
            armaments="**Sarissa** pike phalanx; Companion cavalry; Persian scythed chariots, bow infantry",
            technology="Macedonian **combined arms**; disciplined wheel to avoid chariot charge; Darius’s **chariot scythes** obsolete vs gaps",
            decided_by="Alexander’s **decisive wedge** toward Darius; royal flight collapsed army. Open plain favored Persian numbers but not Macedonian **drill**.",
            numbers_verdict="Persian mass failed against **concentration + king-kill psychology**.",
        ),
        _battle(
            name="Battle of Cannae",
            date="2 August 216 BCE",
            place="Cannae, Apulia",
            belligerents="Hannibal (Carthage) vs Rome (Paullus & Varro)",
            forces="Carthage ~50,000; Rome ~86,000 (largest Roman army to date)",
            armaments="Spanish & Gallic swords; Numidian cavalry; Roman **gladius** + pilum",
            technology="**Double envelopment** (Hannibal); Roman **deep center** that advanced into pocket",
            decided_by="Hannibal’s **weak center, strong wings**; cavalry routed Roman horse, encircled infantry. ~50,000–70,000 Roman casualties.",
            numbers_verdict="Rome had **more men**; Carthage had **better geometry** — ultimate numbers negation.",
        ),
        _battle(
            name="Battle of Zama",
            date="202 BCE",
            place="Near Carthage (North Africa)",
            belligerents="Scipio Africanus (Rome) vs Hannibal",
            forces="Rome ~35,000 + Numidian cavalry; Hannibal ~40,000 (incl. veterans + new levies)",
            armaments="Roman maniples; **elephants** (Hannibal) neutralized by lanes; cavalry decisive",
            technology="Scipio’s **elephant corridors**; Massinissa’s Numidian horse superiority",
            decided_by="Cavalry wing victory; Roman infantry held Hannibal’s veterans until cavalry rear attack. **Alliance politics** (Numidia) supplied numbers Rome lacked at Cannae.",
            numbers_verdict="Rough parity; **cavalry mass + preparation** decided — not infantry totals.",
        ),
        _battle(
            name="Siege of Alesia",
            date="September 52 BCE",
            place="Alesia (Gaul)",
            belligerents="Julius Caesar vs Vercingetorix (Gauls)",
            forces="Romans ~60,000 besiegers; Gauls ~80,000 in town + **relief army ~250,000**",
            armaments="Roman **siege engines**, pilum, gladius; Gallic spears, cavalry",
            technology="**Double circumvallation** (inner + outer walls); Roman engineering multiplied effective manpower",
            decided_by="Caesar’s **fortification math** — fought inner and outer rings simultaneously; relief failed to breach. Starvation forced Vercingetorix surrender.",
            numbers_verdict="Gauls had **overwhelming relief numbers**; Roman **engineering + interior lines** negated them.",
        ),
        _battle(
            name="Battle of the Teutoburg Forest",
            date="9 CE",
            place="Teutoburg Forest, Germania",
            belligerents="Arminius (Germanic tribes) vs Publius Quinctilius Varus (Rome)",
            forces="Romans ~15,000–20,000 (three legions + auxilia); Germans ~10,000–12,000 in stages",
            armaments="Roman pilum, gladius, lorica segmentata; German spears, **ambush terrain**",
            technology="No open-field drill space; **forest nullifies formation**; Roman march column",
            decided_by="**Ambush over days**; Varus’s column stretched; Arminius intimate knowledge of Roman psychology. Three legion standards lost — border retreated to Rhine.",
            numbers_verdict="Romans may have had **greater mass**; **terrain + surprise** made numbers irrelevant — eternal lesson.",
        ),
    ]
    return "## Volume I — Battles from Before Jericho to the Roman Rhine\n\n" + "\n".join(battles)


def compose_volume_two_battles() -> str:
    battles = [
        _battle(name="Battle of the Milvian Bridge", date="28 October 312 CE", place="Milvian Bridge, Rome",
                belligerents="Constantine I vs Maxentius", forces="Constantine ~40,000; Maxentius ~75,000–100,000 (incl. Praetorians)",
                armaments="Late Roman **spatha**, spear, cavalry; Maxentius’s heavy infantry at river",
                technology="Mobile field army; bridge chokepoint; Constantine’s **cavalry shock** before infantry grind",
                decided_by="Maxentius’s army trapped against Tiber; retreat collapsed on bridge; imperial rival drowned. Political Christianity narrative layered on tactical win.",
                numbers_verdict="Maxentius had **greater mass**; **terrain + rout** destroyed numerical advantage."),
        _battle(name="Battle of Adrianople", date="9 August 378 CE", place="Adrianople, Thrace",
                belligerents="Eastern Rome (Valens) vs Gothic coalition (Fritigern)", forces="Romans ~15,000–30,000; Goths ~10,000–20,000 warriors + wagons",
                armaments="Roman **comitatenses**, archers; Gothic cavalry and infantry with **heavy wagons laager**",
                technology="Gothic **cavalry supremacy** without stirrup yet decisive; Roman failure to wait for Western reinforcements",
                decided_by="Valens attacked before Gratian arrived; Gothic cavalry encircled Roman infantry; emperor killed. End of Western infantry mystique.",
                numbers_verdict="Romans may have had parity or edge; **premature attack + horse** negated numbers."),
        _battle(name="Battle of the Catalaunian Plains (Châlons)", date="20 June 451 CE", place="Champagne, Gaul",
                belligerents="Roman–Visigothic coalition (Aetius) vs Huns (Attila)", forces="Coalition ~50,000; Huns & allies similar",
                armaments="Late Roman sword infantry; **Visigothic cavalry**; Hunnic horse archers, siege train",
                technology="Coalition **allied concentration** rare; Attila’s siege of Orléans lifted",
                decided_by="Fierce day battle; Visigoth king Theodoric I killed; Attila withdrew to camp — tactical draw, **strategic coalition win**. Hunnic threat checked in Gaul.",
                numbers_verdict="Parity; **allied mass** matched steppe host — neither side annihilated."),
        _battle(name="Battle of Yarmouk", date="20 August 636 CE", place="Yarmouk River, Syria",
                belligerents="Rashidun Caliphate (Khalid ibn al-Walid) vs Byzantine Empire (Heraclius)",
                forces="Arabs ~25,000–40,000; Byzantines ~100,000–150,000 (chroniclers; modern estimates lower)",
                armaments="Arab **sword + spear** infantry; light cavalry; Byzantine **cataphracts**, archers",
                technology="Desert **mobility & cohesion**; Byzantine exhaustion after Persian wars; **six-day** battle of attrition",
                decided_by="Khalid’s **reserve discipline**; Byzantine collapse after command confusion and desertion. Levant lost to Islam.",
                numbers_verdict="Byzantines had **paper superiority**; **morale, leadership, fatigue** negated muster."),
        _battle(name="Battle of Tours (Poitiers)", date="October 732 CE", place="Near Tours, Francia",
                belligerents="Franks (Charles Martel) vs Umayyad Caliphate (Abd al-Rahman)",
                forces="Franks ~15,000–20,000; Arabs ~20,000–80,000 (sources vary wildly)",
                armaments="Frankish **heavy infantry shield wall** on ridge; Arab cavalry, javelins",
                technology="**Defensive hilltop**; Frankish refusal to break formation; Arab cavalry could not crack infantry line",
                decided_by="Abd al-Rahman killed; raiding army withdrew to Iberia. Frankish infantry doctrine held — Umayyad expansion into Gaul halted.",
                numbers_verdict="Arabs may have outnumbered; **terrain + infantry mass on ground** decided."),
        _battle(name="Battle of Hastings", date="14 October 1066", place="Senlac Hill, England",
                belligerents="Normans (William) vs Anglo-Saxons (Harold Godwinson)", forces="Normans ~7,000–12,000; English ~7,000–8,000 on ridge",
                armaments="Norman **cavalry, archers, infantry**; English **shield wall**, axes, spears",
                technology="**Combined arms** feigned retreats; English hilltop; **feigned flight** drew breaks in wall",
                decided_by="Harold killed; wall broke after day-long attrition; Norman cavalry exploited gaps. Norman Conquest sealed.",
                numbers_verdict="Rough parity; **combined arms + tactical deception** beat static defense."),
        _battle(name="Battle of Manzikert", date="26 August 1071", place="Manzikert, Anatolia",
                belligerents="Byzantium (Romanus IV) vs Seljuk Turks (Alp Arslan)", forces="Byzantines ~40,000; Seljuks ~20,000–40,000",
                armaments="Byzantine mixed infantry/cavalry; **Turkish horse archers**, encirclement",
                technology="Seljuk **mobility & feigned retreat** on Anatolian plain; Byzantine treachery (Andronicus Ducas withdrew)",
                decided_by="Emperor captured; Byzantine army routed. Anatolia opened to Turkic settlement — strategic catastrophe.",
                numbers_verdict="Byzantines had **greater numbers**; **mobility + betrayal** annihilated advantage."),
        _battle(name="Battle of Hattin", date="4 July 1187", place="Horns of Hattin, Galilee",
                belligerents="Ayyubids (Saladin) vs Kingdom of Jerusalem (Guy of Lusignan)", forces="Saladin ~30,000; Crusaders ~20,000 incl. knights",
                armaments="Crusader **heavy cavalry, crossbows**; Ayyubid cavalry, **archers**, javelins",
                technology="**Water denial** on arid march; double hill encirclement (Horns); Crusader knights unhorsed in heat",
                decided_by="Crusader column marched to Tiberias without water; surrounded on horns; mass surrender. Jerusalem fell months later.",
                numbers_verdict="Crusaders outnumbered; **logistics + encirclement** made numbers irrelevant."),
        _battle(name="Battle of Ain Jalut", date="3 September 1260", place="Ain Jalut, Palestine",
                belligerents="Mamluks (Qutuz & Baibars) vs Mongols (Kitbuqa)", forces="Mamluks ~20,000–30,000; Mongols ~10,000–20,000",
                armaments="Mamluk **heavy cavalry**, bows; Mongol horse archers, **Chinese siege engineers** absent here",
                technology="Mamluk **disciplined counter-feint**; first major Mongol defeat in Levant; **Qutuz hidden reserve**",
                decided_by="Baibars’s flank attack; Kitbuqa killed. Mongol westward expansion **stopped** — strength in numbers met equal cavalry state.",
                numbers_verdict="Mamluks had **local superiority**; decisive factor = **trained cavalry mass**, not infantry."),
        _battle(name="Battle of Bannockburn", date="23–24 June 1314", place="Bannockburn, Scotland",
                belligerents="Scotland (Robert Bruce) vs England (Edward II)", forces="Scots ~6,000–10,000; English ~20,000+",
                armaments="Scottish **schiltrons** (spear rings); English longbow, heavy cavalry",
                technology="**Pike/spear hedge** vs cavalry; Bruce’s **pit traps** and narrow ground on second day",
                decided_by="English cavalry failed to break schiltrons; Edward fled. Scottish independence affirmed.",
                numbers_verdict="English **numerical edge** failed against **formation + ground**."),
        _battle(name="Battle of Crécy", date="26 August 1346", place="Crécy-en-Ponthieu, France",
                belligerents="England (Edward III) vs France (Philip VI)", forces="English ~10,000–15,000; French ~20,000–35,000",
                armaments="English **longbow** (~6,000 archers); Genoese crossbows; French heavy cavalry charges",
                technology="**Rate of fire** (longbow vs crossbow reload in rain); dismounted English men-at-arms; **arrow storm**",
                decided_by="French knights charged through mud up hill into arrow barrage — waves destroyed. Beginning of infantry missile dominance.",
                numbers_verdict="French had **more men**; **technology (longbow) + position** negated chivalric mass."),
        _battle(name="Battle of Poitiers (1356)", date="19 September 1356", place="Near Poitiers, France",
                belligerents="England (Black Prince) vs France (John II)", forces="English ~6,000–8,000; French ~11,000–20,000",
                armaments="Longbow, dismounted men-at-arms; French knights, crossbow",
                technology="English **defensive hedge**; **flanking march** through woods (Captal de Buch)",
                decided_by="French encircled; King John captured. **Hundred Years War** ransom politics.",
                numbers_verdict="French **2:1 advantage** lost to **envelopment** — Cannae echo with bows."),
        _battle(name="Battle of Agincourt", date="25 October 1415", place="Agincourt, France",
                belligerents="England (Henry V) vs France (constable d’Albret)", forces="English ~6,000–8,500; French ~12,000–36,000",
                armaments="English longbow; French **plate armor** knights, crossbow",
                technology="**Muddy narrow front** between woods; French plate immobilized in mud; arrow penetration at close range",
                decided_by="French columns could not deploy; knights piled up; English archers used mallets on trapped nobility. National myth for both sides.",
                numbers_verdict="Classic: French **mass became liability** in confined kill zone."),
        _battle(name="Siege of Constantinople (1453)", date="6 April – 29 May 1453", place="Constantinople",
                belligerents="Ottomans (Mehmed II) vs Byzantines (Constantine XI)", forces="Ottomans ~80,000–170,000; defenders ~7,000–10,000 + civilians",
                armaments="Byzantine walls, **Greek fire** tradition; Ottoman **cannon** (Urban’s great bombards), Janissaries",
                technology="**Gunpowder siege artillery** breached Theodosian walls; Ottoman fleet hauled overland into Golden Horn",
                decided_by="Wall breach at Kerkoporta gate (small door left open); Janissary assault. **Medieval empire ended** — cannon age begins.",
                numbers_verdict="Ottomans had **overwhelming numbers** AND **technology leap** — both mattered."),
        _battle(name="Battle of Flodden", date="9 September 1513", place="Branxton, Northumberland",
                belligerents="Scotland (James IV) vs England (Earl of Surrey)", forces="Scots ~25,000–35,000; English ~20,000–26,000",
                armaments="Scottish **pike** schiltrons; English **bill & bow**",
                technology="Pike vs combined billhook; **artillery** on Scottish side underused in mud; downhill English approach",
                decided_by="Scottish pike advanced into wet ground; flanking English bills broke formations; James IV killed. Last great medieval Scottish invasion ended.",
                numbers_verdict="Scots had slight edge; **weapon mix + ground** favored English combined arms."),
    ]
    return "## Volume II — Late Antiquity to the Gunpowder Threshold\n\n" + "\n".join(battles)


def compose_volume_three_battles() -> str:
    battles = [
        _battle(name="Battle of Pavia", date="24 February 1525", place="Pavia, Lombardy",
                belligerents="Habsburg Spain/Holy Roman Empire vs France (Francis I)", forces="Imperial ~23,000; French ~28,000 incl. Swiss pikes",
                armaments="**Arquebus** volleys; Swiss **pike blocks**; French gendarmes (heavy cavalry)",
                technology="**Gunpowder small arms** integrated with pike; Spanish **tercio** prototype; park hunting forest limits cavalry",
                decided_by="Imperial arquebusiers destroyed French cavalry; Francis I captured. **Knightly charge obsolete** vs disciplined shot.",
                numbers_verdict="French had **more troops**; **firepower doctrine** decided."),
        _battle(name="Battle of Lepanto", date="7 October 1571", place="Gulf of Patras, Ionian Sea",
                belligerents="Holy League vs Ottoman Empire", forces="League ~212 galleys; Ottomans ~251 galleys",
                armaments="**Galley cannon**, arquebus marines; Ottoman Janissary infantry at oars",
                technology="League **galeasses** (heavy gun platforms); boarding vs artillery duel; rowed warships",
                decided_by="League center held; Ottoman left collapsed; Ali Pasha killed. Ottoman naval momentum in Mediterranean **checked** (not ended).",
                numbers_verdict="Ottomans had **more hulls**; **gun platforms + coalition** won local fire superiority."),
        _battle(name="Battle of Breitenfeld", date="17 September 1631", place="Breitenfeld, Saxony",
                belligerents="Sweden (Gustavus Adolphus) vs Holy Roman Empire (Tilly)", forces="Swedish–Saxon ~42,000; Imperial ~35,000",
                armaments="Swedish **leather cannon**, **salvo** muskets; Imperial tercios",
                technology="**Combined arms Gustavus model**: cavalry, infantry salvos, mobile artillery; Saxon flank collapse then Swedish salvage",
                decided_by="Swedish **flexible line** refused broken wing; cavalry + artillery destroyed Imperial tercios. Protestant survival in Thirty Years War.",
                numbers_verdict="Swedes had **slight edge**; **doctrine + fire discipline** multiplied effect."),
        _battle(name="Battle of Naseby", date="14 June 1645", place="Naseby, Northamptonshire",
                belligerents="Parliament (Fairfax & Cromwell) vs Royalists (Charles I)", forces="Parliament ~14,000; Royalists ~9,000",
                armaments="**Musket + pike** New Model Army; Royalist cavalry under Prince Rupert",
                technology="Cromwell’s **Ironsides** disciplined charge; Parliament **reserve** not looting",
                decided_by="Rupert’s cavalry pursued too far; Cromwell hit exposed Royalist left; king’s infantry destroyed. **English Civil War** turned.",
                numbers_verdict="Parliament had **numbers**; **cavalry discipline** was hinge."),
        _battle(name="Battle of Vienna (1683)", date="12 September 1683", place="Vienna, Austria",
                belligerents="Holy League (Jan III Sobieski) vs Ottomans (Kara Mustafa)", forces="Relief ~70,000–80,000; Ottoman siege ~150,000 incl. camp",
                armaments="Winged **Hussars**, musket infantry; Ottoman Janissaries, siege lines",
                technology="**Star fort** defense held city; Polish **cavalry charge** from Kahlenberg hill",
                decided_by="Largest cavalry charge in history broke Ottoman camp; Kara Mustafa failed to assault city earlier. Ottoman retreat from Central Europe.",
                numbers_verdict="Ottomans had **siege mass**; failed to **concentrate** before relief — numbers without decision."),
        _battle(name="Battle of Blenheim", date="13 August 1704", place="Blenheim (Blindheim), Bavaria",
                belligerents="Grand Alliance (Marlborough & Eugene) vs France & Bavaria", forces="Alliance ~52,000; Franco-Bavarian ~56,000",
                armaments="Flintlock **musket** transition; dragoon, cannon",
                technology="Marlborough’s **forced march** from Low Countries; **double envelopment**",
                decided_by="Eugene held right; Marlborough smashed weak French center; Tallard captured. France’s Bavarian ally knocked out of war.",
                numbers_verdict="French had **slight edge**; **maneuver + synchronized attack** created local superiority."),
        _battle(name="Battle of Plassey", date="23 June 1757", place="Plassey, Bengal",
                belligerents="British East India Company (Clive) vs Bengal (Siraj ud-Daulah)", forces="British ~3,000; Bengalis ~50,000",
                armaments="Company **sepoy muskets**, cannon; Indian cavalry, elephants",
                technology="**Monsoon rain** soaked Indian powder; **Mir Jafar’s treachery** (non-firing wing)",
                decided_by="British line held; conspirators held troops back; Siraj fled. **Colonial India** born from betrayal more than firepower.",
                numbers_verdict="Indians had **massive numbers**; **political fracture** negated them entirely."),
        _battle(name="Battles of Saratoga (Freeman’s Farm & Bemis Heights)", date="19 September & 7 October 1777", place="Saratoga, New York",
                belligerents="United States vs Great Britain (Burgoyne)", forces="Americans growing to ~15,000; British ~7,000–9,000",
                armaments="Musket, **rifle** skirmishers (Morgan), field guns",
                technology="American **entrenchments**; British **overextended** supply down Lake Champlain",
                decided_by="Burgoyne surrounded; surrender 17 October. French alliance triggered — war became global.",
                numbers_verdict="Americans achieved **local superiority** through accumulation; British **logistics** destroyed effective mass."),
        _battle(name="Battle of Valmy", date="20 September 1792", place="Valmy, France",
                belligerents="Revolutionary France vs Prussia & Austria", forces="French ~36,000; Allies ~34,000",
                armaments="**Cannonade** at distance; French **levée en masse** infantry",
                technology="**Artillery duel** in rain; allied failure to press attack — “cannonade of Valmy”",
                decided_by="Allied withdrawal; French morale triumph. **First Republic** survived — mass conscription validated.",
                numbers_verdict="Parity; **morale + nationalism** counted as force multiplier."),
        _battle(name="Battle of Austerlitz", date="2 December 1805", place="Austerlitz, Moravia",
                belligerents="France (Napoleon) vs Russia & Austria", forces="French ~68,000; Allies ~85,000",
                armaments="12-pounder **grand battery**; column vs line",
                technology="Napoleon’s **deliberately weak right** bait; **sun in allies’ eyes**; rapid **central breakthrough**",
                decided_by="Allies split; Napoleon seized Pratzen heights; allied center routed. **War of Third Coalition** ended.",
                numbers_verdict="Allies had **more men**; **deception + timing** created winning mass at center."),
        _battle(name="Battle of Trafalgar", date="21 October 1805", place="Cape Trafalgar, Atlantic",
                belligerents="Royal Navy (Nelson) vs Franco-Spanish fleet", forces="British 27 ships; Combined 33 ships",
                armaments="**32-pounder** broadsides, carronades; marines",
                technology="British **two-column crossing** of T; **rate of fire** & gunnery training",
                decided_by="Nelson broke enemy line in two places; capture of 21 ships; Nelson killed. Invasion threat to Britain ended.",
                numbers_verdict="Combined fleet **larger**; British **tactical concentration** halved local odds."),
        _battle(name="Battle of Waterloo", date="18 June 1815", place="Waterloo, Belgium",
                belligerents="Anglo-Allied (Wellington) + Prussians (Blücher) vs France (Napoleon)", forces="Wellington ~68,000; Napoleon ~72,000; Prussians ~50,000 arriving",
                armaments="Musket volleys; **cavalry charges**; artillery",
                technology="**Reverse slope** defense hid infantry; **Prussian clock** — Blücher’s arrival on right",
                decided_by="French failed to break center before Prussians; Imperial Guard final attack repulsed. Napoleonic era ended.",
                numbers_verdict="Napoleon had **daylight edge**; **allied cumulative numbers** (Prussians) decided war."),
        _battle(name="Battle of Gettysburg", date="1–3 July 1863", place="Gettysburg, Pennsylvania",
                belligerents="Union (Meade) vs Confederacy (Lee)", forces="Union ~83,000–104,000; Confederates ~75,000",
                armaments="**Rifled musket**, cannon; Confederate Pickett’s charge infantry",
                technology="**Interior lines** on Cemetery Ridge; **rail/logistics** Union advantage",
                decided_by="Day 3 Pickett’s Charge destroyed; Lee withdrew. High-water mark of Confederacy.",
                numbers_verdict="Rough parity; **defensive firepower** made attacker mass suicidal."),
        _battle(name="Battle of Königgrätz (Sadowa)", date="3 July 1866", place="Bohemia",
                belligerents="Prussia vs Austria", forces="Prussia ~220,000; Austria ~215,000",
                armaments="**Needle gun** (Dreyse) faster than muzzle-loading Lorenz",
                technology="Prussian **staff railways**; **Moltke’s converging armies**",
                decided_by="Austrian **army separation**; Prussian II Army hit flank. German unification path cleared.",
                numbers_verdict="Parity; **mobility + fire rate** beat linear mass."),
        _battle(name="Battle of Sedan", date="1 September 1870", place="Sedan, France",
                belligerents="Prussia vs France (Napoleon III)", forces="Prussians ~200,000; French ~120,000 encircled",
                armaments="**Krupp breech-loading artillery**; Chassepot vs Dreyse",
                technology="**Rail mobilization**; **Moltke encirclement**",
                decided_by="French army pocketed; emperor surrendered. Second Empire collapsed.",
                numbers_verdict="Prussian **converging superior mass** at point of encirclement."),
        _battle(name="Battle of Omdurman", date="2 September 1898", place="Omdurman, Sudan",
                belligerents="Britain (Kitchener) vs Mahdist Sudan", forces="British–Egyptian ~26,000; Mahdists ~52,000",
                armaments="**Maxim machine guns**, Lee-Metford rifles; spears, swords, few rifles",
                technology="**Firepower asymmetry** — colonial maximum",
                decided_by="Mahdist charges destroyed in open; ~10,000 Sudanese dead vs ~48 British. Reconquest of Sudan.",
                numbers_verdict="Mahdists had **2:1 numbers**; **technology made numbers irrelevant**."),
        _battle(name="Battle of Tsushima", date="27–28 May 1905", place="Tsushima Strait",
                belligerents="Japan (Tōgō) vs Russia (Rozhestvensky)", forces="Japanese ~4 battleships + escorts; Russian Baltic Fleet long voyage",
                armaments="**12-inch naval rifles**, torpedoes; obsolescent Russian gunnery",
                technology="Japanese **crossing T**; **spotting, training, maintenance** after Port Arthur experience",
                decided_by="Russian fleet annihilated; national humiliation. First Asian naval victory over European great power.",
                numbers_verdict="Rough fleet parity; **quality + preparation** multiplied Japanese effect."),
        _battle(name="First Battle of the Marne", date="6–12 September 1914", place="Marne River, France",
                belligerents="France & Britain vs Germany", forces="Each side ~1,000,000+ engaged",
                armaments="Bolt-action rifle, **machine gun**, **75mm field gun**",
                technology="**Rail reinforcement** (French taxis mythologized); **entrenchment begins**",
                decided_by="German right wing exhausted; gap between armies; retreat to Aisne — **race to sea**. Schlieffen plan failed.",
                numbers_verdict="Mass industrial armies; **logistics + exhaustion** stopped German **numerical weight** in France."),
        _battle(name="Battle of Verdun", date="21 February – 18 December 1916", place="Verdun, France",
                belligerents="France vs Germany", forces="Millions rotated through (~700k+ casualties combined)",
                armaments="Artillery **king**; flamethrowers, gas; fortress ring",
                technology="**Artillery preparation**; **rotating French defense** (Pétain: “Ils ne passeront pas”)",
                decided_by="Attrition slugfest; German **Falkenhayn** failed to bleed France out decisively. Symbol of French survival.",
                numbers_verdict="Both sides fed **mass** into grinder; **firepower** negated infantry numbers repeatedly."),
        _battle(name="Battle of the Somme", date="1 July – 18 November 1916", place="Somme, France",
                belligerents="Britain & France vs Germany", forces="Allied ~1,000,000+ committed; German defense in depth",
                armaments="Artillery, **machine gun**, first **tanks** (15 September)",
                technology="Week-long bombardment failed to cut wire; **creeping barrage** later; tank debut",
                decided_by="1 July 1916 worst day in British Army history (~57,000 casualties); limited gains. Industrial war logic exposed.",
                numbers_verdict="Allied **massive numbers** bought meters — **square law** of machine guns."),
        _battle(name="Battle of Amiens", date="8–12 August 1918", place="Amiens, France",
                belligerents="Allied coalition vs Germany", forces="Allied ~104,000 attack; German morale cracking",
                armaments="Tanks, aircraft, **combined arms**",
                technology="**Hundred Days Offensive** model; secrecy, **infiltration tactics** adopted",
                decided_by="Black Day of German Army; Ludendorff: war must end. **Combined arms** broke trench deadlock.",
                numbers_verdict="Allied **concentration + technology** finally multiplied numbers effectively."),
    ]
    return "## Volume III — Pike, Shot, and Industrial Slaughter\n\n" + "\n".join(battles)


def compose_volume_four_battles() -> str:
    battles = [
        _battle(name="Invasion of Poland (campaign)", date="1 September – 6 October 1939", place="Poland",
                belligerents="Germany & USSR vs Poland", forces="Germans ~1.5M; Poles ~1M; Soviet second front",
                armaments="**Panzer** divisions, **Stuka** dive bombers; Polish cavalry, obsolete fortifications",
                technology="**Blitzkrieg**: combined arms, radio, **deep penetration**; Soviet Molotov-Ribbentrop partition",
                decided_by="**Pincer** from west and east; Warsaw surrendered. Poland eliminated in five weeks.",
                numbers_verdict="Axis had **superior mass + doctrine**; Poland could not fight two fronts."),
        _battle(name="Battle of Britain", date="10 July – 31 October 1940", place="British airspace",
                belligerents="RAF vs Luftwaffe", forces="RAF ~1,900 fighters available; Luftwaffe ~2,500+ aircraft",
                armaments="**Spitfire, Hurricane**; **Bf 109**; radar, AA guns",
                technology="**Radar Chain Home**; **fighter control**; German shift to cities (Blitz) saved RAF airfields",
                decided_by="Luftwaffe failed to destroy Fighter Command; **invasion (Sea Lion) cancelled**. First strategic air defeat of Nazi Germany.",
                numbers_verdict="Rough parity in airframes; **system (radar + endurance)** multiplied RAF numbers."),
        _battle(name="Attack on Pearl Harbor", date="7 December 1941", place="Pearl Harbor, Hawaii",
                belligerents="Japan vs United States", forces="Japanese carrier strike ~350 aircraft; US Pacific Fleet at anchor",
                armaments="**Type 91 torpedo** (modified for shallow harbor), bombs; battleships Oklahoma, Arizona",
                technology="**Carrier aviation** vs battleship-centric fleet; surprise",
                decided_by="Battleship force crippled; **carriers absent** (at sea). US entered WWII — strategic Japanese failure to destroy carriers.",
                numbers_verdict="Japanese **local superiority** at moment of strike; **wrong target priority** lost war-winning chance."),
        _battle(name="Battle of Midway", date="4–7 June 1942", place="Midway Atoll, Pacific",
                belligerents="United States (Nimitz) vs Japan (Yamamoto)", forces="US 3 carriers; Japan 4 carriers (Akagi, Kaga, Soryu, Hiryu lost)",
                armaments="**Dive bombers** (SBD Dauntless), torpedo bombers; Zero fighters",
                technology="**Code-breaking (MAGIC)**; carrier duel; **five-minute** dive-bombing catastrophe for Japan",
                decided_by="US sank four Japanese fleet carriers; Yamamoto’s initiative **never recovered**. Pacific turning point.",
                numbers_verdict="Japanese had **theater superiority** before battle; **intelligence + decisive strike** negated fleet mass."),
        _battle(name="Battle of Stalingrad", date="23 August 1942 – 2 February 1943", place="Stalingrad, USSR",
                belligerents="Germany (6th Army) vs Soviet Union", forces="Axis ~330,000 encircled; Soviets millions in campaign",
                armaments="**Urban combat**, snipers, tanks; **Luftwaffe** supply by air failed",
                technology="**Rat war** in ruins; Operation Uranus **double encirclement**",
                decided_by="Paulus surrounded; **airlift collapse**; surrender. German Eastern front never recovered morale or manpower peak.",
                numbers_verdict="Germans had **local superiority** until Soviets **massed at encirclement** — numbers returned on Soviet terms."),
        _battle(name="Second Battle of El Alamein", date="23 October – 11 November 1942", place="El Alamein, Egypt",
                belligerents="Britain (Montgomery) vs Germany/Italy (Rommel)", forces="Allies ~195,000; Axis ~116,000",
                armaments="Sherman tanks, artillery, **minefields**; Afrika Korps 88mm",
                technology="**Ultra intelligence**; overwhelming **materiel** (Grant/Sherman); attrition prepared",
                decided_by="Rommel **permanent retreat** from Egypt; Torch landings overlapped. Suez and oil routes secured.",
                numbers_verdict="Allied **material superiority** — strength in numbers **and** industry."),
        _battle(name="Battle of Kursk", date="5 July – 23 August 1943", place="Kursk salient, USSR",
                belligerents="Germany vs Soviet Union", forces="Largest tank battle: ~6,000 tanks engaged; millions of troops",
                armaments="**Tiger, Panther**; Soviet **T-34**; minefields miles deep",
                technology="Soviet **defense in depth**; **Prokhorovka** armor clash; intelligence from Lucy spy ring",
                decided_by="German **Citadel** stalled; Soviet counteroffensives. Last major German offensive in East.",
                numbers_verdict="Soviet **mass + prepared defense** absorbed elite German **quality**."),
        _battle(name="D-Day (Operation Overlord)", date="6 June 1944", place="Normandy, France",
                belligerents="Allied expeditionary force vs Germany", forces="~156,000 landed first day; ~2M follow-on in Normandy campaign",
                armaments="Landing craft, **mulberry harbors**, airborne divisions, naval bombardment",
                technology="**Deception (Fortitude)**; air superiority; **combined arms** at beachhead scale",
                decided_by="Beaches held (Omaha hardest); **logistics victory** over Atlantic Wall. Second front opened.",
                numbers_verdict="Allied **amphibious mass** with air/sea control — numbers could finally deploy."),
        _battle(name="Battle of the Bulge (Ardennes)", date="16 December 1944 – 25 January 1945", place="Ardennes, Belgium/Luxembourg",
                belligerents="Germany vs United States", forces="German ~410,000 attack; US pockets at Bastogne",
                armaments="**Tiger II**, infantry; US **artillery, air** when weather cleared",
                technology="German **fuel shortage**; **101st Airborne** hold; Patton relief",
                decided_by="Last German gamble failed; **airpower + logistics** restored Allied lines. War shortened but costly.",
                numbers_verdict="Germans achieved **local surprise superiority**; **Allied depth** restored mass advantage."),
        _battle(name="Battle of Berlin", date="16 April – 2 May 1945", place="Berlin",
                belligerents="Soviet Union vs Germany", forces="Soviets ~2.5M; defenders ~766,000 incl. Volkssturm",
                armaments="**Katyusha**, assault guns; **Panzerfaust**, rubble fighting",
                technology="**Urban encirclement**; Hitler suicide 30 April; flag on Reichstag",
                decided_by="Total Soviet **mass** met desperate defense. European war ended.",
                numbers_verdict="Overwhelming Soviet **numbers + artillery** — classic siege of capitol."),
        _battle(name="Battle of Inchon", date="15 September 1950", place="Inchon, Korea",
                belligerents="UN (MacArthur) vs North Korea", forces="UN amphibious ~75,000; NK rear echelon cut",
                armaments="Naval gunfire, Marines; NK **T-34** earlier in war",
                technology="**Amphibious daring** (tidal mud flats); **chromite** operation",
                decided_by="NK supply lines severed; Seoul recaptured. NK army collapsed until Chinese intervention.",
                numbers_verdict="UN had **inferior land mass** in theater; **amphibious maneuver** created winning local numbers."),
        _battle(name="Siege of Dien Bien Phu", date="13 March – 7 May 1954", place="Dien Bien Phu, Vietnam",
                belligerents="France vs Viet Minh (Giap)", forces="French ~15,000 in valley; Viet Minh ~50,000+",
                armaments="French **air supply**; Viet Minh **artillery in tunnels** on hills",
                technology="Giap’s **siege artillery** dragged into mountains; **airfield destroyed**",
                decided_by="French positions overrun; colonial war ended. **Decolonization** template.",
                numbers_verdict="Viet Minh had **mass + superior siege geometry**; French **interior valley** negated their own tech."),
        _battle(name="Battle of Ia Drang", date="14–18 November 1965", place="Ia Drang Valley, Vietnam",
                belligerents="United States vs North Vietnam", forces="US 1st Cavalry ~450 per landing zone; NVA ~2,000+",
                armaments="**Huey** air mobility, artillery, **B-52** Arc Light; NVA AK-47, mortars",
                technology="**Helicopter assault** new doctrine; Moore’s **LZ X-Ray** hold; **LZ Albany** ambush disaster",
                decided_by="US held X-Ray with airpower; NVA learned to **grab American belt**. First major US–NVA clash.",
                numbers_verdict="NVA had **local numbers**; US **firepower multiplier** held — each side drew lessons."),
        _battle(name="Yom Kippur War (Sinai bridgehead battles)", date="6–25 October 1973", place="Sinai & Golan",
                belligerents="Israel vs Egypt & Syria", forces="Egypt ~800,000 mobilized; Israel ~300,000 mobilized",
                armaments="**Sagger ATGM**, SAM-6; Israeli armor, **air force**",
                technology="Arab **surprise**; Israeli **reserve mobilization**; Sharon’s **cross-canal** raid",
                decided_by="Initial Arab gains; Israeli recovery and encirclement of 3rd Army. **Peace process** (Camp David) seeded.",
                numbers_verdict="Arabs had **opening mass**; Israeli **mobilization depth** restored parity."),
        _battle(name="Falklands War (land campaign)", date="21 May – 14 June 1982", place="Falkland Islands",
                belligerents="Britain vs Argentina", forces="British task force ~10,000 land; Argentines ~13,000 garrison",
                armaments="**Exocet** missiles (naval phase); bayonet charges, **NLAW** era precursor infantry",
                technology="**8,000-mile logistics**; **night attacks**; Exocet sank Sheffield",
                decided_by="British took Stanley; Argentine surrender. Expeditionary warfare at extreme range.",
                numbers_verdict="Argentine **local garrison mass**; British **professional training + naval air** decided."),
        _battle(name="Gulf War (100-hour ground campaign)", date="24–28 February 1991", place="Kuwait & southern Iraq",
                belligerents="Coalition vs Iraq", forces="Coalition ~700,000; Iraq ~540,000 in theater",
                armaments="**M1 Abrams**, Apache, precision **GPS** (limited), cluster munitions",
                technology="**AirLand Battle**; **left hook** envelopment; **air campaign** first (42 days)",
                decided_by="Iraqi army destroyed on Highway 80; ceasefire. Demonstration of **information + precision** era.",
                numbers_verdict="Coalition **mass + technology** — both mattered; Iraqi mass could not maneuver."),
        _battle(name="Battle of Fallujah (Second)", date="7 November – 23 December 2004", place="Fallujah, Iraq",
                belligerents="United States & Iraq vs insurgents", forces="Coalition ~10,000–15,000; insurgents ~3,000–4,000 embedded",
                armaments="Urban **CQB**, tanks in streets, **UAV** ISR; IEDs, snipers",
                technology="**House-by-house** clearance; media scrutiny; combined USMC/Army",
                decided_by="City cleared at high cost; insurgency displaced. Template for **urban combined arms** in GWOT.",
                numbers_verdict="Coalition had **numbers + firepower**; **urban density** multiplied defender effect."),
        _battle(name="Russo-Ukrainian War (Kharkiv & Kherson counteroffensives)", date="September–November 2022", place="Ukraine",
                belligerents="Ukraine vs Russia", forces="Variable brigades; Russian lines overextended",
                armaments="**HIMARS**, drones, Western artillery; Russian mass artillery, mobilized manpower",
                technology="**ISR saturation** (drones); **precision strikes** on logistics; **OPSEC** for concentration",
                decided_by="Ukrainian **maneuver** retook territory; Russian **mass** failed without coherent C2. Contemporary lesson: numbers without precision bleed.",
                numbers_verdict="Russia had **theater mass**; **Ukrainian concentration + intelligence** created local superiority."),
    ]
    return "## Volume IV — Mechanized War to the Present\n\n" + "\n".join(battles)


def compose_series_complete() -> str:
    return """## Series Complete — Four Volumes

| Vol | Span | Battles indexed |
|-----|------|-----------------|
| **I** | Prehistory – 9 CE | 16 (Jericho through Teutoburg) |
| **II** | 312 – 1521 CE | 16 (Milvian Bridge through Flodden) |
| **III** | 1525 – 1918 | 20 (Pavia through Amiens) |
| **IV** | 1919 – present | 18 (Poland 1939 through Ukraine 2022) |

**70 battles** across human history — each with forces, armaments, technology, decisive factor, and strength-in-numbers verdict.

Later append-only editions may add battles (Granicus, Issus, Actium, Rocroi, Normandy breakout, etc.) without rewriting these sealed volumes.
"""


_VOLUME_DISPATCH: dict[int, tuple[Any, ...]] = {
    1: (lambda: compose_volume_intro(volume=1), compose_volume_one_battles),
    2: (lambda: compose_volume_intro(volume=2), compose_volume_two_battles),
    3: (lambda: compose_volume_intro(volume=3), compose_volume_three_battles),
    4: (lambda: compose_volume_intro(volume=4), compose_volume_four_battles, compose_series_complete),
}


def compose_full_body(*, volume: int = 1) -> str:
    parts = list(_VOLUME_DISPATCH.get(volume, _VOLUME_DISPATCH[1]))
    rendered = [p() if callable(p) else p for p in parts]
    rendered.append(
        f"\n---\n\n*Exploring Historic Battles · Volume {volume} · Grok (xAI) with Hostess 7 · sealed append-only.*\n"
    )
    return "\n\n".join(rendered)


def edition_slug(*, volume: int = 1, dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return f"exploring_historic_battles_vol{volume}_{dt.year}_{dt.month:02d}_{dt.day:02d}"


def pack_volume(*, volume: int = 1) -> dict[str, Any]:
    doctrine = load_doctrine()
    maker = _import_mod("book_maker", "lib/hostess7-book-maker.py")
    if not maker or not hasattr(maker, "pack_book"):
        return {"ok": False, "error": "book_maker_missing"}

    slug = edition_slug(volume=volume)
    title = f"Exploring Historic Battles — Volume {volume}"
    body = compose_full_body(volume=volume)

    rep = maker.pack_book(
        title=title,
        body=body,
        author=doctrine.get("author", "grok"),
        co_author=doctrine.get("co_author", "Hostess 7"),
        owner=doctrine.get("owner", "ZacharyGeurts"),
        dewey=doctrine.get("dewey", "355.48"),
        dewey_label=doctrine.get("dewey_label", "Military science — battles"),
        shelf=doctrine.get("shelf", "900-history"),
        book_id=slug,
        book_kind=doctrine.get("book_kind", "exploring_historic_battles"),
    )

    flat_dir = LIBRARY / doctrine.get("shelf", "900-history") / slug
    book_dir = SERIES_DIR / slug
    book_dir.mkdir(parents=True, exist_ok=True)
    if flat_dir.is_dir() and flat_dir.resolve() != book_dir.resolve():
        for item in flat_dir.iterdir():
            dest = book_dir / item.name
            if dest.exists():
                dest.unlink()
            item.rename(dest)
        try:
            flat_dir.rmdir()
        except OSError:
            pass

    h7c_name = f"{slug}.h7c"
    h7c_rel = f"library/dewey/900-history/exploring_historic_battles/{slug}/{h7c_name}"
    rep["h7c"] = h7c_rel
    for meta_name in ("book.json", "book-manifest.json", "book-information-index.json"):
        meta_path = book_dir / meta_name
        if meta_path.is_file():
            try:
                doc = json.loads(meta_path.read_text(encoding="utf-8"))
                if "h7c" in doc:
                    doc["h7c"] = h7c_rel
                    doc["field_path"] = h7c_rel
                if meta_name == "book-information-index.json" and "catalog" in doc:
                    doc["catalog"]["h7c"] = h7c_rel
                meta_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except (OSError, json.JSONDecodeError):
                pass

    corpus = _load(CORPUS_PATH, {
        "schema": "hostess7-exploring-historic-battles-corpus/v1",
        "series_id": doctrine.get("series_id"),
        "editions": [],
        "latest_edition_id": None,
    })
    prior = None
    for e in sorted(corpus.get("editions") or [], key=lambda x: x.get("volume", 0), reverse=True):
        if e.get("volume", 0) < volume:
            prior = e.get("edition_id")
            break

    idx_mod = _import_mod("book_info", "lib/field-book-information-index.py")
    if idx_mod and hasattr(idx_mod, "read_index") and hasattr(idx_mod, "write_index"):
        doc = idx_mod.read_index(slug) or {}
        doc["series"] = {
            "id": doctrine.get("series_id", "exploring_historic_battles"),
            "title": doctrine.get("series_title", "Exploring Historic Battles"),
            "volume": volume,
            "prior_edition": prior,
            "series_complete": volume == 4,
        }
        doc["tags"] = list(set((doc.get("tags") or []) + [
            "historic_battles", "strength_in_numbers", "military_history", f"volume_{volume}",
        ]))
        if volume == 4:
            doc["tags"].append("series_complete")
        idx_mod.write_index(book_dir, doc)

    edition_row = {
        "edition_id": slug,
        "volume": volume,
        "title": title,
        "written_at": rep.get("written_at"),
        "h7c": rep.get("h7c"),
        "char_count": rep.get("char_count"),
        "prior_edition": prior,
    }
    corpus["editions"] = [e for e in corpus.get("editions") or [] if e.get("volume") != volume]
    corpus["editions"].append(edition_row)
    corpus["editions"].sort(key=lambda x: x.get("volume", 0))
    corpus["latest_edition_id"] = slug
    corpus["series_complete"] = all(
        any(e.get("volume") == v for e in corpus["editions"])
        for v in (1, 2, 3, 4)
    )
    corpus["updated"] = _now()
    _save(CORPUS_PATH, corpus)

    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "hostess7-exploring-historic-battles-series/v1",
        "series_id": doctrine.get("series_id"),
        "title": doctrine.get("series_title"),
        "protection": doctrine.get("protection", {}),
        "latest_edition_id": slug,
        "edition_count": len(corpus["editions"]),
        "series_complete": corpus.get("series_complete", False),
        "editions": corpus["editions"],
        "updated": _now(),
    }
    (SERIES_DIR / "series-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return {**rep, "series_id": doctrine.get("series_id"), "volume": volume, "edition_id": slug, "prior_edition": prior}


def pack_all_volumes() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for vol in (1, 2, 3, 4):
        rep = pack_volume(volume=vol)
        if not rep.get("ok"):
            return {"ok": False, "volume": vol, "error": rep.get("error"), "results": results}
        results.append({
            "volume": vol,
            "edition_id": rep.get("edition_id"),
            "char_count": rep.get("char_count"),
            "h7c": rep.get("h7c"),
        })
    return {"ok": True, "series_complete": True, "volumes": results, "updated": _now()}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    corpus = _load(CORPUS_PATH, {})
    out = {
        "schema": "hostess7-exploring-historic-battles-panel/v1",
        "updated": _now(),
        "series_id": doctrine.get("series_id"),
        "series_title": doctrine.get("series_title"),
        "motto": doctrine.get("motto"),
        "edition_count": len(corpus.get("editions") or []),
        "latest_edition_id": corpus.get("latest_edition_id"),
        "volumes_planned": doctrine.get("volumes") or [],
        "dewey": doctrine.get("dewey"),
        "shelf": doctrine.get("shelf"),
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploring Historic Battles")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--volume", type=int, default=1)
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("compose", "preview"):
        print(compose_full_body(volume=args.volume))
        return 0
    if cmd in ("pack", "write", "edition"):
        rep = pack_volume(volume=args.volume)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd in ("pack_all", "packall", "complete"):
        rep = pack_all_volumes()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd == "index":
        corpus = _load(CORPUS_PATH, {})
        print(json.dumps(corpus, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-exploring-historic-battles.py [panel|compose|pack|pack_all|index]",
        "series": "Exploring Historic Battles",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())