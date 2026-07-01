#!/usr/bin/env pythong
"""Exploring Vehicles & Exploring Military Vehicles — exhaustive field manuals for AI and humans."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
LIBRARY = INSTALL / "library" / "dewey"
VEH_SHELF = LIBRARY / "629-vehicles"
MIL_SHELF = LIBRARY / "355-military-science"
SKIP_COVER = os.environ.get("FIELD_SKIP_COVER", "1") == "1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


def _import_h7c() -> Any:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    spec = importlib.util.spec_from_file_location("field_h7c", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7c-compression.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body.strip()}\n"


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items)


# --- Exploring Vehicles taxonomy (every vehicle of motion) ---

HUMAN_POWERED = [
    "Walking aids: cane, walker, crutches, exoskeleton (passive/active assist)",
    "Wheelless: skis, snowshoes, sled, toboggan, bobsled, luge skeleton",
    "Single-wheel: unicycle, monowheel (motorized listed separately)",
    "Two-wheel: bicycle (road, mountain, BMX, tandem, cargo, recumbent, folding)",
    "Electric bicycle (pedelec, S-Pedelec where legal), e-scooter (stand-on)",
    "Three-wheel: tricycle, rickshaw, tadpole/trike recumbent, ice trike",
    "Four-wheel human: quadricycle, pedal car, wheelchair (manual), racing wheelchair",
    "Skate & roll: inline skates, roller skates, skateboard, longboard, scooter (kick)",
    "Water human-power: kayak, canoe, rowboat, scull, pedal boat, SUP paddle board",
    "Air human-power: hang glider, paraglider (foot-launch), human-powered aircraft (HPA)",
    "Hybrid human: row-cycle, amphibious pedal craft, ski-bike",
]

ANIMAL_POWERED = [
    "Horse: chariot, wagon, stagecoach, sleigh, howdah, caisson",
    "Ox: ox cart, bullock cart (South Asia, Africa)",
    "Camel: camel train, camel cavalry mount with kit",
    "Dog: dog sled, rig (Arctic)",
    "Reindeer: sled (Sámi, Siberia)",
    "Elephant: war/engineering mount (historical), logging transport",
    "Mule/donkey: pack trains, narrow trail logistics",
]

LAND_MOTOR = [
    "Micro: mobility scooter, golf cart, neighborhood electric vehicle (NEV)",
    "Motorcycle: standard, cruiser, sport, touring, dual-sport, dirt, trials",
    "Scooter (motor): Vespa-class, maxi-scooter, electric scooter (seated)",
    "Three-wheel motor: auto rickshaw, Can-Am Spyder-class, Morgan 3 Wheeler",
    "Car segments (ISO/market): mini, subcompact, compact, mid, full, luxury, sports",
    "Body styles: sedan, hatchback, wagon, coupe, convertible, SUV, crossover, pickup",
    "Light commercial: van (cargo/passenger), minibus, pickup, cab-chassis",
    "Medium/heavy truck: box truck, flatbed, tanker, dump, cement mixer, refuse",
    "Bus: city transit, articulated, double-decker, coach, school bus, BRT",
    "RV: Class A/B/C motorhome, camper van, caravan (towed)",
    "Agricultural: tractor, combine, sprayer, harvester, telehandler",
    "Construction: bulldozer, excavator, loader, grader, roller, backhoe",
    "Mining: haul truck, continuous miner support fleet",
    "Industrial: forklift, reach stacker, terminal tractor (yard goat)",
    "Emergency: ambulance, fire engine, police pursuit, rescue MRAP (civilian)",
    "Racing: Formula, NASCAR stock, rally, drag, kart, trophy truck",
    "Off-road: ATV, UTV/SxS, dune buggy, rock crawler, snowmobile",
]

RAIL = [
    "Heavy rail: freight locomotive (diesel-electric, electric), passenger locomotive",
    "Multiple unit: EMU, DMU, bi-level commuter, intercity",
    "High-speed: TGV, Shinkansen, ICE, CRH-class dedicated sets",
    "Metro/subway: steel-wheel metro, rubber-tire metro (Montreal-class)",
    "Light rail & tram: streetcar, modern LRV, heritage tram",
    "Monorail: straddle-beam, suspended",
    "People mover: airport APM, automated guideway transit (AGT)",
    "Heritage: steam locomotive, heritage diesel, narrow-gauge scenic",
    "Special: funicular, rack railway (cog), inclined elevator",
    "Freight cars: box, flat, gondola, hopper, tank, intermodal well, reefer",
    "Maintenance: ballast regulator, tamping machine, rail grinder",
]

WATER = [
    "Human/small craft: see human-powered",
    "Sail: sloop, ketch, cutter, catamaran, trimaran, junk, dhow",
    "Motor yacht & workboat: trawler, tug, pilot boat, fireboat",
    "Ferry: ro-ro, catamaran fast ferry, ice-class ferry",
    "Cargo ship: container (ULCV), bulk carrier, tanker (crude/LNG/LPG), car carrier",
    "Special: research vessel, icebreaker, dredger, crane barge",
    "Subsurface civilian: submarine (tourist/research), submersible, ROV/AUV",
    "Amphibious: hovercraft, seaplane (see air), swimming car (Amphicar-class)",
    "Underwater personal: DPV/scooter (diving)",
]

AIR = [
    "Lighter-than-air: hot-air balloon, gas balloon, airship/dirigible, blimp",
    "Glider/sailplane, hang glider, paraglider (powered: paramotor)",
    "Fixed-wing: single-engine piston, turboprop, business jet, narrowbody airliner, widebody",
    "Rotorcraft: helicopter (single/dual main rotor), autogyro, tiltrotor (V-22-class)",
    "eVTOL/urban air mobility (development class)",
    "Drone civil: multirotor, fixed-wing mapping, delivery testbeds",
    "Special: agricultural aircraft, firefighting tanker, aerial refueling (military cross-list)",
]

SPACE = [
    "Launch vehicle: liquid, solid, hybrid; reusable (Falcon-class) vs expendable",
    "Spacecraft: crew capsule, spaceplane, orbital module, lander",
    "Rover/probe: lunar rover, Mars rover, deep-space probe (propulsion stage)",
    "Station: orbital space station modules, commercial station (planned)",
    "Satellite bus: communication, Earth observation, navigation (GNSS)",
]

CABLE_SPECIAL = [
    "Aerial lift: gondola, chairlift, aerial tramway, funitel",
    "Elevator & escalator (vertical transport)",
    "Maglev: low-speed urban, high-speed intercity (Shanghai, L0-class)",
    "Personal rapid transit (PRT) pod (historical/experimental)",
    "Hyperloop (vacuum tube transport — engineering class)",
]

# Chapter 1 — prehistoric through steam (exhaustive timeline tables)
ERA_PREHISTORIC = [
    ["~2.6M–10k BCE", "Foot & carry", "No wheels; load on back/shoulder", "Nomadic foraging bands"],
    ["~40k BCE", "Sled / travois", "Drag over snow, grass, ice", "Arctic, steppe peoples"],
    ["~8k BCE", "Dugout canoe", "Hollowed log, paddle", "Rivers, coasts worldwide"],
    ["~5k BCE", "Raft & coracle", "Bundled reeds / hides", "Tigris-Euphrates, Nile, Ganges"],
    ["~4k BCE", "Log roller (theorized)", "Reduce friction moving stones", "Megalith transport"],
]

ERA_WHEEL_CHARIOT = [
    ["~3500 BCE", "Wheel & axle", "Solid wood disc, Mesopotamia", "Potter's wheel → cart wheel"],
    ["~2000 BCE", "Spoked wheel", "Lighter chariot wheel", "Egypt, Levant, Anatolia"],
    ["~1700 BCE", "War chariot", "Two-wheel, horse-drawn", "Hyksos, Hittite, Egyptian"],
    ["~800 BCE", "Iron rim (gradual)", "Durable wheel tyre precursor", "Celts, later Rome"],
    ["~500 BCE", "Persian royal road", "Relay stations, couriers", "Darius I — 2,600 km network"],
]

ERA_MARITIME_ANCIENT = [
    ["~3000 BCE", "Egyptian reed boats", "Papyrus / wood hull", "Nile trade"],
    ["~2000 BCE", "Minoan / Phoenician galley", "Oared + sail", "Mediterranean commerce"],
    ["~500 BCE", "Trireme", "Three banks of oars", "Athens, Carthage, Rome"],
    ["~100 CE", "Roman grain ship", "Square-rig, 300+ tons", "Alexandria → Ostia annona"],
    ["~800 CE", "Viking longship", "Clinker hull, sail + oar", "North Atlantic raids & trade"],
]

ERA_MEDIEVAL_EARLY = [
    ["~1100", "Horseshoe widespread", "Iron shoe, nailed", "European heavy haul"],
    ["~1200", "Compass navigation", "Magnetic bearing at sea", "Song/Yuan China → Europe"],
    ["~1400", "Caravel", "Lateen rig, Atlantic exploration", "Portugal — Cape route"],
    ["~1500", "Covered wagon", "Conestoga precursor patterns", "European inland freight"],
    ["~1600", "Stagecoach networks", "Scheduled passenger service", "England, France"],
]

ERA_CANAL_INDUSTRIAL = [
    ["1761", "Bridgewater Canal", "UK — coal to Manchester", "James Brindley"],
    ["1787", "Iron barge plate", "Metal hull sections", "Wilkinson, Coalbrookdale"],
    ["1804", "Steam locomotive (trial)", "Pen-y-Darren tramway", "Richard Trevithick"],
    ["1807", "Clermont steamboat", "Hudson River passenger", "Robert Fulton"],
    ["1814", "Puffing Billy", "Rack railway steam", "Wylam colliery, England"],
]

ERA_STEAM = [
    ["1825", "Stockton & Darlington", "First public steam railway", "George Stephenson"],
    ["1829", "Rocket", "Rainhill trials winner", "0-2-2, multi-tube boiler"],
    ["1838", "SS Great Western", "Atlantic steam crossing", "Isambard Kingdom Brunel"],
    ["1863", "Metropolitan Railway", "World's first underground metro", "London, steam then electric"],
    ["1886", "Benz Patent-Motorwagen", "Practical automobile ICE", "Karl Benz, Mannheim"],
    ["1896", "Stanley Steamer", "Steam car peak production", "Locomobile, Stanley brothers"],
]


def build_exploring_vehicles_text() -> str:
    lines = [
        "# Exploring Vehicles",
        "",
        "![Cover](h7fig:cover)",
        "",
        "**Every vehicle of motion ever created** — for Hostess 7 field counsel, operators, and AI retrieval.",
        "Human-powered through space; land, rail, water, air, cable, and special systems.",
        "",
        f"- **Edition:** exhaustive field manual",
        f"- **Updated:** {_now()}",
        "- **Scope:** global, historical, and production — bicycles through launch vehicles",
        "- **Not titled:** ~~General Exploring Vehicles~~ — this book is **Exploring Vehicles** only",
        "",
        "---",
        "",
        "## 1. History — prehistoric through steam",
        "",
        "Every modern vehicle descends from muscle, wind, animal traction, the wheel, and the steam engine.",
        "This chapter is the **exhaustive spine** Hostess 7 indexes before taxonomy chapters.",
        "",
        _section(
            "1a. Prehistoric & Neolithic transport",
            _table(["Era", "Vehicle / method", "Mechanism", "Region / note"], ERA_PREHISTORIC),
        ),
        _section(
            "1b. Wheel, axle, and chariot age",
            _table(["Date", "Innovation", "Detail", "Significance"], ERA_WHEEL_CHARIOT),
        ),
        _section(
            "1c. Ancient & classical maritime",
            _table(["Date", "Craft", "Rig / propulsion", "Role"], ERA_MARITIME_ANCIENT),
        ),
        _section(
            "1d. Medieval through early modern",
            _table(["Date", "Development", "Technology", "Impact"], ERA_MEDIEVAL_EARLY),
        ),
        _section(
            "1e. Canals & early industrial mobility",
            _table(["Year", "Milestone", "Description", "Operator / place"], ERA_CANAL_INDUSTRIAL),
        ),
        _section(
            "1f. Steam era — rail, sea, road",
            _table(["Year", "Vehicle / line", "Achievement", "People / place"], ERA_STEAM),
        ),
        _section(
            "1g. Propulsion transition (pre-electric)",
            _table(
                ["Phase", "Primary energy", "Dominant vehicles", "Limit"],
                [
                    ["Muscle", "Human / animal food", "Foot, litter, cart, chariot", "~15 km/h sustained"],
                    ["Wind", "Atmospheric", "Sail, lateen, square-rig", "Weather-dependent"],
                    ["Steam", "Coal, wood", "Locomotive, steamboat, steam tractor", "Boiler weight, water"],
                    ["ICE early", "Petroleum", "Motor car, motorcycle, bus", "Oil supply, emissions"],
                ],
            ),
        ),
        "",
        "## 2. Definition & physics",
        "",
        "A **vehicle** is a machine or craft for **propulsion** and **transport** of people, animals, or cargo.",
        "Motion requires: (1) a medium interface — wheel, track, rail, hull, wing, rotor, magnetic gap;",
        "(2) an energy source; (3) control — steering, brakes, trim, throttle.",
        "",
        "**ISO 3833** defines road vehicle types and terms. **STANAG** and national regulations overlap for military (see *Exploring Military Vehicles*).",
        "",
        _section("Contact with the ground", _bullet_list([
            "Rolling: wheel, tire, ball",
            "Sliding: ski, runner, steel wheel on rail",
            "Tracked: continuous track (caterpillar)",
            "Legged: walking machines (experimental/quadruped robots)",
            "Hover: air cushion (hovercraft)",
            "Magnetic levitation: electrodynamic or electromagnetic gap",
        ])),
        _section("3. Human-powered & muscle vehicles", _bullet_list(HUMAN_POWERED)),
        _section("4. Animal-powered transport", _bullet_list(ANIMAL_POWERED)),
        _section("5. Land motor vehicles", _bullet_list(LAND_MOTOR)),
        _section(
            "5a. Car classification reference (market segments)",
            _table(
                ["Segment", "Typical use", "Examples"],
                [
                    ["A / city car", "Urban", "Fiat 500-class, Smart"],
                    ["B / subcompact", "Economy", "Toyota Yaris, Honda Fit"],
                    ["C / compact", "Family", "Toyota Corolla, VW Golf"],
                    ["D / mid-size", "Fleet/family", "Toyota Camry, Honda Accord"],
                    ["E / executive", "Luxury", "Mercedes E-Class, BMW 5"],
                    ["F / full-size", "Chauffeur", "Mercedes S-Class, BMW 7"],
                    ["J / SUV", "Utility", "RAV4, CR-V, X5"],
                    ["M / MPV", "Multi-seat", "Odyssey, Sienna"],
                    ["S / sports", "Performance", "911, Corvette"],
                ],
            ),
        ),
        _section("6. Rail vehicles", _bullet_list(RAIL)),
        _section("7. Watercraft", _bullet_list(WATER)),
        _section("8. Aircraft", _bullet_list(AIR)),
        _section("9. Space vehicles", _bullet_list(SPACE)),
        _section("10. Cable, magnetic, and special systems", _bullet_list(CABLE_SPECIAL)),
        _section(
            "11. Propulsion & energy (reference)",
            _table(
                ["Energy", "Used in", "Notes"],
                [
                    ["Human muscle", "Bicycle, row, pedal", "Food energy; ~500 W sustained peak"],
                    ["Animal", "Carts, cavalry", "Hay/forage logistics"],
                    ["Petroleum ICE", "Cars, ships, aircraft", "Gasoline, diesel, jet fuel"],
                    ["Electric battery", "EV, e-bike, e-bus", "Grid or swap charging"],
                    ["Overhead wire/third rail", "Rail, trolleybus", "Catenary or slot"],
                    ["Hydrogen fuel cell", "Bus pilot, truck pilot", "H2 storage challenge"],
                    ["Nuclear", "Submarines, carriers, icebreakers", "Military-heavy"],
                    ["Wind", "Sail", "Apparent wind routing"],
                    ["Solar", "Solar car, UAV", "Supplemental or record attempts"],
                    ["Chemical rocket", "Launch vehicles", "LOX/kerosene, solid boosters"],
                ],
            ),
        ),
        _section(
            "12. Production & scale (verified public figures)",
            _bullet_list([
                "Bicycles: over 1 billion in use worldwide",
                "Flying Pigeon (China): most-produced bicycle model (tens of millions)",
                "Honda Super Cub: most-produced motor vehicle (motorcycle), 100M+ cumulative",
                "Toyota Corolla: most-produced car nameplate, 50M+ cumulative",
                "Cessna 172: most-produced fixed-wing aircraft",
                "Boeing 737: most-produced commercial jet airliner family",
                "Mil Mi-8: most-produced helicopter",
            ]),
        ),
        _section(
            "13. AI retrieval keys",
            "Use `vehicle_class`, `medium`, `propulsion`, `wheels`, `era` when indexing. "
            "Pair with Dewey **629** transportation. Cross-link military variants in *Exploring Military Vehicles*.",
        ),
        "",
        "## Appendix A — Medium index",
        "",
        _table(
            ["medium", "vehicle_count_hint", "dewey"],
            [
                ["land_human", str(len(HUMAN_POWERED)), "629.2"],
                ["land_animal", str(len(ANIMAL_POWERED)), "629.2"],
                ["land_motor", str(len(LAND_MOTOR)), "629.2"],
                ["rail", str(len(RAIL)), "625"],
                ["water", str(len(WATER)), "623"],
                ["air", str(len(AIR)), "629.13"],
                ["space", str(len(SPACE)), "629.4"],
                ["cable_special", str(len(CABLE_SPECIAL)), "629"],
            ],
        ),
        "",
        "---",
        "",
        "*Sources corroborated: ISO 3833, Wikipedia Vehicle taxonomy, FHWA vehicle types, field operator doctrine. "
        "Truth-gated expand — report errors to Hostess 7 library lane.*",
        "",
    ]
    return "\n".join(lines)


# --- Exploring Military Vehicles ---

MIL_LAND_COMBAT = [
    "Tank: MBT (Leopard 2, M1 Abrams, T-90, Type 99, Merkava, K2)",
    "Light tank / tankette (historical: FT-17, Panzer I; modern: 2S25 Sprut-class)",
    "IFV: Bradley, BMP-3, CV90, Puma, ZBD-04, Warrior",
    "APC: M113, BTR-80, Patria AMV, Boxer (APC role), Type 92",
    "MRAP: Cougar, MaxxPro, RG-33, Typhoon-K (regional variants)",
    "Recon: Fennek, BRDM-2, LAV-25, Scimitar (CVR(T))",
    "Self-propelled artillery: PzH 2000, M109, 2S19 Msta, PLZ-05",
    "MLRS: M270 HIMARS, BM-30 Smerch, PHL-03",
    "SPAAG: Gepard, Tunguska, Pantsir-S1 (land-based)",
    "Tank destroyer / wheeled AT: Centauro, M1128 Stryker MGS, Pandur",
    "Half-track (historical): Sd.Kfz series, M3 half-track",
    "Improvised: technical (pickup MG), gun truck, up-armored civilian",
]

MIL_LOGISTICS = [
    "Heavy truck: HEMTT, KamAZ, MAZ, Oshkosh FMTV, Tatrapan",
    "Medium: Unimog military, MAN HX, Iveco MTV",
    "Fuel tanker, water bowser, ammunition truck",
    "Tractor-trailer: heavy equipment transport (HET)",
    "Ambulance (Geneva marked), field hospital trucks",
    "Engineer: bridge layer (M60 AVLB, PMM-2), mine plow, dozer in uniform",
]

MIL_NAVAL = [
    "Aircraft carrier: CATOBAR, STOBAR, STOVL (Nimitz, Ford, Kuznetsov-class)",
    "Destroyer / frigate / corvette (AEGIS, Type 052D, FREMM)",
    "Cruiser (Ticonderoga-class legacy), littoral combat ship",
    "Submarine: SSN, SSBN, SSK (Virginia, Astute, Yasen, Type 093)",
    "Amphibious: LHD/LHA (Wasp, America), LST, LCAC hovercraft",
    "Patrol: FAC, OPV, riverine craft",
    "Mine warfare: MCM vessel, minesweeper",
    "Auxiliary: replenishment oiler (T-AO), hospital ship (USNS Mercy-class)",
]

MIL_AIR = [
    "Fighter: F-35, F-22, Su-35, J-20, Rafale, Typhoon, Gripen",
    "Strike/attack: A-10, Su-25, JH-7",
    "Bomber: B-52, B-2, B-21, Tu-160, H-6",
    "Transport: C-130, C-17, A400M, Il-76, Y-20",
    "Tanker: KC-135, KC-46, Il-78",
    "AWACS/AEW: E-3, E-7 Wedgetail, A-50, KJ-500",
    "Maritime patrol: P-8 Poseidon, P-3 Orion",
    "Helicopter: UH-60, CH-47, Mi-8/17, Ka-52, AH-64",
    "UAV/UCAV: MQ-9 Reaper, Bayraktar TB2, Shahed-136 (loitering munition)",
]

MIL_BY_ERA = [
    "Ancient–medieval: chariot, war elephant, siege tower, trireme",
    "WWI: Mark I tank, Renault FT, early aircraft, U-boat",
    "WWII: Tiger, T-34, Sherman, Jeep, Stuka, Spitfire, Iowa-class",
    "Cold War: T-72, M60, BTR, MiG-21, F-4, SSBN boomers",
    "Modern: networked IFV, stealth fighter, drone swarms, APS (active protection)",
]

MIL_SUBSURFACE = [
    "SSN: Virginia-class, Astute, Yasen-M, Suffren, Type 093",
    "SSBN: Ohio, Vanguard, Borei, Triomphant, Type 094",
    "SSK: Type 212A AIP, Kilo, Scorpène, Soryu",
    "UUV: REMUS, Bluefin, Poseidon (status-classified) — autonomous undersea",
    "SDV: SEAL Delivery Vehicle — swimmer lock-out",
]

MIL_SPACE = [
    "ICBM silo & TEL: Minuteman III, RS-24 Yars, DF-41, Agni-V",
    "SLBM: Trident II, Bulava, JL-2",
    "Military satellite buses: WGS, SBIRS, Yaogan, Gaofen mil-dual",
    "ASAT: USA-193 intercept (2008), Cosmos 1408 (2021) — policy-sensitive",
    "X-37B OTV: reusable military spaceplane",
    "Starship / super-heavy (dual-use launch — track as policy)",
]


def build_exploring_military_vehicles_text() -> str:
    lines = [
        "# Exploring Military Vehicles",
        "",
        "![Cover](h7fig:cover)",
        "",
        "**Global military vehicles** — land, sea, air, subsurface, and space; every major class and representative system.",
        "For operators, Hostess 7 IFF counsel, and AI exhaustive retrieval.",
        "",
        f"- **Updated:** {_now()}",
        "- **Scope:** worldwide — NATO, CSTO, neutral, and global south systems",
        "- **Law:** Geneva Conventions marking for medical/civilian-protected vehicles",
        "",
        "---",
        "",
        "## 1. History — military vehicles by era",
        "",
        _table(
            ["Era", "Land", "Sea", "Air"],
            [
                ["Ancient", "Chariot, elephant", "Trireme, quinquereme", "—"],
                ["Gunpowder", "Cannon carriage", "Ship of the line", "Balloon recon (1790s)"],
                ["WWI", "Mark I tank", "U-boat", "Sopwith Camel, Zeppelin"],
                ["WWII", "Tiger, T-34", "Bismarck, Essex CV", "Spitfire, B-17, Zero"],
                ["Cold War", "T-72, M60", "Typhoon SSBN", "F-4, MiG-21, U-2"],
                ["Modern", "T-14, KF-51", "Type 055 destroyer", "F-35, Su-57, TB2"],
            ],
        ),
        "",
        "## 2. Definition",
        "",
        "A **military vehicle** is designed or substantially used for **military transport or combat**.",
        "Most require **off-road mobility**, **armor**, or **tracks**. Amphibious variants cross land/water.",
        "Non-combat medical vehicles must be **clearly marked** and are protected under Geneva when respected.",
        "",
        _section("3. Land combat vehicles", _bullet_list(MIL_LAND_COMBAT)),
        _section(
            "3a. AFV comparison axes (AI index)",
            _table(
                ["Axis", "Question", "Example values"],
                [
                    ["Role", "Tank vs IFV vs APC", "MBT / IFV / APC / MRAP"],
                    ["Mobility", "Tracks vs wheels", "Tracked MBT / 8x8 Boxer"],
                    ["Armor", "Steel vs composite vs ERA", "RHA, NERA, Kontakt-5"],
                    ["Main armament", "Cannon / missile", "120 mm smoothbore, ATGM"],
                    ["Crew", "Headcount", "3–4 tank, 7–9 IFV"],
                    ["Origin", "Country block", "USA, Germany, Russia, China, …"],
                ],
            ),
        ),
        _section("4. Logistics & support trucks", _bullet_list(MIL_LOGISTICS)),
        _section("5. Naval military vessels", _bullet_list(MIL_NAVAL)),
        _section("6. Subsurface & undersea", _bullet_list(MIL_SUBSURFACE)),
        _section("7. Military aircraft & unmanned systems", _bullet_list(MIL_AIR)),
        _section("8. Historical eras (narrative)", _bullet_list(MIL_BY_ERA)),
        _section(
            "9. Global regions (representative fleets)",
            _table(
                ["Region", "Land example", "Naval example", "Air example"],
                [
                    ["United States", "M1 Abrams", "Nimitz/Ford CVN", "F-35A/C"],
                    ["United Kingdom", "Challenger 2", "Queen Elizabeth CV", "Typhoon"],
                    ["France", "Leclerc", "Charles de Gaulle", "Rafale"],
                    ["Germany", "Leopard 2", "Baden-Württemberg F125", "Eurofighter"],
                    ["Russia", "T-90M", "Admiral Kuznetsov", "Su-35S"],
                    ["China", "Type 99A", "Type 003 Fujian", "J-20"],
                    ["India", "Arjun", "INS Vikrant", "Tejas"],
                    ["Japan", "Type 10", "Izumo-class", "F-35A"],
                    ["South Korea", "K2 Black Panther", "Dokdo LPH", "KF-21"],
                    ["Israel", "Merkava IV", "Sa'ar corvette", "F-35I"],
                    ["Turkey", "Altay", "Anadolu LHD", "Bayraktar TB2"],
                    ["Ukraine", "T-64BM", "Gyurza gunboat", "Su-27 legacy"],
                    ["Brazil", "Guarani", "Tamandaré frigate", "Gripen E"],
                    ["Australia", "Boxer CRV", "Hobart destroyer", "F/A-18F"],
                ],
            ),
        ),
        _section(
            "10. Non-combat protected vehicles",
            _bullet_list([
                "Military ambulance (Red Cross/Crescent emblem)",
                "Mobile surgical hospital (field hospital)",
                "Chaplain/civilian aid convoys (protected when marked)",
                "POW transport (Geneva obligations)",
            ]),
        ),
        _section(
            "11. Improvised & irregular warfare",
            _bullet_list([
                "Technical: civilian pickup with crew-served weapon",
                "Up-armored civilian (Ukraine-style, Iraq-style)",
                "Suicide vehicle-borne IED (SVBIED) — threat class, not doctrine",
                "Captured/refurbished enemy kit (trophy AFVs)",
            ]),
        ),
        _section("12. Space & strategic (military)", _bullet_list(MIL_SPACE)),
        _section(
            "13. AI retrieval keys",
            "Index by `domain` (land/sea/air/space), `role`, `country`, `era`, `protected_status`. "
            "Dewey **355** military science. Pair civilian base vehicles with *Exploring Vehicles*.",
        ),
        "",
        "## Appendix — NATO designator patterns (selected)",
        "",
        _table(
            ["Pattern", "Meaning"],
            [
                ["M1xx", "US tracked AFV family"],
                ["BTR-xx", "Soviet/Russian wheeled APC lineage"],
                ["FV4xx", "British AFV lineage"],
                ["Type 0xx", "Chinese PLA designations"],
                ["CV9x", "Nordic IFV exports"],
            ],
        ),
        "",
        "---",
        "",
        "*Corroborate lethal and identification claims through field evidence and Hostess 7 truth gates. "
        "Educational exhaustive catalog — not targeting doctrine.*",
        "",
    ]
    return "\n".join(lines)


VEH_CHAPTERS = [
    {"num": 1, "slug": "01-prehistoric-steam", "title": "History — prehistoric through steam"},
    {"num": 2, "slug": "02-definition-physics", "title": "Definition & physics"},
    {"num": 3, "slug": "03-human-powered", "title": "Human-powered & muscle vehicles"},
    {"num": 4, "slug": "04-animal-powered", "title": "Animal-powered transport"},
    {"num": 5, "slug": "05-land-motor", "title": "Land motor vehicles"},
    {"num": 6, "slug": "06-rail", "title": "Rail vehicles"},
    {"num": 7, "slug": "07-watercraft", "title": "Watercraft"},
    {"num": 8, "slug": "08-aircraft", "title": "Aircraft"},
    {"num": 9, "slug": "09-space", "title": "Space vehicles"},
    {"num": 10, "slug": "10-cable-special", "title": "Cable, magnetic, and special systems"},
    {"num": 11, "slug": "11-propulsion", "title": "Propulsion & energy"},
    {"num": 12, "slug": "12-production-scale", "title": "Production & scale"},
    {"num": 13, "slug": "13-ai-retrieval", "title": "AI retrieval keys"},
]

MIL_CHAPTERS = [
    {"num": 1, "slug": "01-military-history", "title": "History — military vehicles by era"},
    {"num": 2, "slug": "02-definition", "title": "Definition"},
    {"num": 3, "slug": "03-land-combat", "title": "Land combat vehicles"},
    {"num": 4, "slug": "04-logistics", "title": "Logistics & support trucks"},
    {"num": 5, "slug": "05-naval", "title": "Naval military vessels"},
    {"num": 6, "slug": "06-subsurface", "title": "Subsurface & undersea"},
    {"num": 7, "slug": "07-air-unmanned", "title": "Military aircraft & unmanned systems"},
    {"num": 8, "slug": "08-eras", "title": "Historical eras"},
    {"num": 9, "slug": "09-global-regions", "title": "Global regions"},
    {"num": 10, "slug": "10-protected", "title": "Non-combat protected vehicles"},
    {"num": 11, "slug": "11-irregular", "title": "Improvised & irregular warfare"},
    {"num": 12, "slug": "12-space-strategic", "title": "Space & strategic"},
    {"num": 13, "slug": "13-ai-retrieval", "title": "AI retrieval keys"},
]


def _write_book_manifest(
    *,
    shelf: Path,
    book_id: str,
    title: str,
    dewey: str,
    pdf_name: str,
    h7c_rel: str,
    chapters: list[dict[str, Any]],
    char_count: int,
) -> Path:
    manifest = {
        "schema": "hostess7-exploring-book/v1",
        "id": book_id,
        "title": title,
        "author": "Hostess 7 · AmmoOS Field Library",
        "edition": "1.0.0-field",
        "year": 2026,
        "dewey": dewey,
        "shelf": shelf.name,
        "formats": {
            "pdf": pdf_name,
            "h7c": h7c_rel,
        },
        "updated": _now(),
        "char_count": char_count,
        "chapter_count": len(chapters),
        "chapters": chapters,
    }
    book_dir = shelf / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    path = book_dir / "book-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_textbook_pdf(text: str, out: Path, title: str) -> bool:
    """Build PDF via reportlab if available; never block on missing deps."""
    out.parent.mkdir(parents=True, exist_ok=True)
    script = f'''
import sys
from pathlib import Path
text = Path({repr(str(out) + ".src")}).read_text(encoding="utf-8")
title = {repr(title)}
out = Path({repr(str(out))})
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.units import inch
    import re
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out), pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 0.2*inch)]
    body = styles["BodyText"]
    for block in re.split(r"\\n\\n+", text):
        block = block.strip()
        if not block:
            continue
        safe = block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if block.startswith("# "):
            story.append(Paragraph(safe[2:], styles["Heading1"]))
        elif block.startswith("## "):
            story.append(Paragraph(safe[3:], styles["Heading2"]))
        elif block.startswith("|"):
            story.append(Paragraph(safe.replace("\\n", "<br/>"), body))
        elif block.startswith("- "):
            for line in block.split("\\n"):
                if line.startswith("- "):
                    story.append(Paragraph("• " + line[2:], body))
        else:
            story.append(Paragraph(safe.replace("\\n", "<br/>"), body))
        story.append(Spacer(1, 0.08*inch))
    doc.build(story)
    print("ok")
except Exception as e:
    print(f"fail:{{e}}", file=sys.stderr)
    sys.exit(1)
'''
    src = out.with_suffix(out.suffix + ".src")
    src.write_text(text, encoding="utf-8")
    venv_py = Path("/tmp/pdfvenv/bin/python")
    py = str(venv_py) if venv_py.is_file() else "python3"
    import subprocess

    try:
        r = subprocess.run(
            [py, "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0 and out.is_file() and out.stat().st_size > 500:
            src.unlink(missing_ok=True)
            return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False


def _cover_path(book_id: str, title: str, accent: tuple[int, int, int]) -> Path:
    out = INSTALL / "data" / "combinatronic-visuals" / "books" / f"{book_id}.png"
    if SKIP_COVER:
        return out
    vis_py = INSTALL / "lib" / "field-combinatronic-visuals.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        spec = importlib.util.spec_from_file_location("comb_vis", vis_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "render_book_cover"):
                mod.LANG_ACCENT[book_id] = accent  # type: ignore[attr-defined]
                mod.render_book_cover(book_id, label=title, command_count=0, out=out)
                return out
    except Exception:
        pass
    return out


def pack_book(
    *,
    book_id: str,
    title: str,
    text: str,
    shelf: Path,
    dewey: str,
    dewey_label: str,
    subject: str,
    accent: tuple[int, int, int],
) -> dict[str, Any]:
    h7c = _import_h7c()
    book_dir = shelf / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    h7c_path = book_dir / f"{book_id}.h7c"
    cover = _cover_path(book_id, title, accent)
    figures: dict[str, Any] = {}
    if cover.is_file():
        figures["cover"] = {
            "path": cover,
            "alt": title,
            "mime": "image/png",
            "plate_key": "cover",
            "accent": accent,
        }
    meta = {
        "id": book_id,
        "title": title,
        "author": "AmmoOS Field Library",
        "license": "Field",
        "subject": subject,
        "category": subject,
        "dewey": dewey,
        "book_kind": "exploring",
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    packed = h7c.pack_h7c(text, meta, use_optimizer=True, format_version=3, figures=figures or None)
    h7c_path.write_bytes(packed)
    ein = "H7C-EXPLORE-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    book_json = {
        "id": book_id,
        "title": title,
        "author": "AmmoOS Field Library",
        "dewey": dewey,
        "dewey_label": dewey_label,
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "book_kind": "exploring",
        "embedded_figures": ["cover"] if figures else [],
        "manual_reader": "/field-lang-manuals",
        "h7c": _rel(h7c_path),
        "field_path": _rel(h7c_path),
        "github_shelf": shelf.name,
        "cover": f"/world/assets/combinatronic/books/{book_id}.png",
        "updated": _now(),
    }
    (book_dir / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "book_id": book_id,
        "title": title,
        "h7c_path": str(h7c_path),
        "char_count": len(text),
        "ein": ein,
    }


def _update_shelf(shelf: Path, code: str, title: str, book_entry: dict[str, Any]) -> None:
    shelf_json = shelf / "shelf.json"
    doc = {}
    if shelf_json.is_file():
        try:
            doc = json.loads(shelf_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    books = [b for b in (doc.get("books") or []) if b.get("id") != book_entry["id"]]
    books.append(book_entry)
    doc.update({
        "schema": "dewey-shelf/v1",
        "shelf": shelf.name,
        "code": code,
        "title": title,
        "updated": _now(),
        "format_primary": "h7c",
        "book_count": len(books),
        "h7c_count": sum(1 for b in books if b.get("format") == "h7c"),
        "books": books,
    })
    shelf_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_vehicles() -> dict[str, Any]:
    VEH_SHELF.mkdir(parents=True, exist_ok=True)
    text = build_exploring_vehicles_text()
    rep = pack_book(
        book_id="exploring_vehicles",
        title="Exploring Vehicles",
        text=text,
        shelf=VEH_SHELF,
        dewey="629",
        dewey_label="Transportation & vehicle engineering",
        subject="vehicles — every vehicle of motion",
        accent=(30, 144, 255),
    )
    h7c_rel = "exploring_vehicles/exploring_vehicles.h7c"
    pdf_name = "Hostess7_Exploring_Vehicles_Textbook.pdf"
    pdf_ok = _write_textbook_pdf(text, VEH_SHELF / pdf_name, "Exploring Vehicles")
    manifest_path = _write_book_manifest(
        shelf=VEH_SHELF,
        book_id="exploring_vehicles",
        title="Exploring Vehicles",
        dewey="629",
        pdf_name=pdf_name,
        h7c_rel=h7c_rel,
        chapters=VEH_CHAPTERS,
        char_count=len(text),
    )
    _update_shelf(
        VEH_SHELF,
        "629",
        "629-vehicles",
        {
            "id": "exploring_vehicles",
            "title": "Exploring Vehicles",
            "author": "AmmoOS Field Library",
            "dewey": "629",
            "format": "h7c",
            "h7c": f"library/dewey/629-vehicles/{h7c_rel}",
            "pdf": f"library/dewey/629-vehicles/{pdf_name}",
            "manifest": "library/dewey/629-vehicles/exploring_vehicles/book-manifest.json",
            "cover": "/world/assets/combinatronic/books/exploring_vehicles.png",
            "ready": True,
        },
    )
    rep["pdf"] = pdf_name if pdf_ok else None
    rep["manifest"] = str(manifest_path)
    return rep


def generate_military_vehicles() -> dict[str, Any]:
    MIL_SHELF.mkdir(parents=True, exist_ok=True)
    text = build_exploring_military_vehicles_text()
    rep = pack_book(
        book_id="exploring_military_vehicles",
        title="Exploring Military Vehicles",
        text=text,
        shelf=MIL_SHELF,
        dewey="355",
        dewey_label="Military science",
        subject="military vehicles — global",
        accent=(180, 60, 50),
    )
    h7c_rel = "exploring_military_vehicles/exploring_military_vehicles.h7c"
    pdf_name = "Hostess7_Exploring_Military_Vehicles_Textbook.pdf"
    pdf_ok = _write_textbook_pdf(text, MIL_SHELF / pdf_name, "Exploring Military Vehicles")
    manifest_path = _write_book_manifest(
        shelf=MIL_SHELF,
        book_id="exploring_military_vehicles",
        title="Exploring Military Vehicles",
        dewey="355",
        pdf_name=pdf_name,
        h7c_rel=h7c_rel,
        chapters=MIL_CHAPTERS,
        char_count=len(text),
    )
    _update_shelf(
        MIL_SHELF,
        "355",
        "355-military-science",
        {
            "id": "exploring_military_vehicles",
            "title": "Exploring Military Vehicles",
            "author": "AmmoOS Field Library",
            "dewey": "355",
            "format": "h7c",
            "h7c": f"library/dewey/355-military-science/{h7c_rel}",
            "pdf": f"library/dewey/355-military-science/{pdf_name}",
            "manifest": "library/dewey/355-military-science/exploring_military_vehicles/book-manifest.json",
            "cover": "/world/assets/combinatronic/books/exploring_military_vehicles.png",
            "ready": True,
        },
    )
    rep["pdf"] = pdf_name if pdf_ok else None
    rep["manifest"] = str(manifest_path)
    return rep


def generate_all() -> dict[str, Any]:
    v = generate_vehicles()
    m = generate_military_vehicles()
    return {"ok": True, "exploring_vehicles": v, "exploring_military_vehicles": m, "updated": _now()}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if cmd in ("all", "both"):
        print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("vehicles", "exploring_vehicles"):
        print(json.dumps(generate_vehicles(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("military", "military_vehicles", "exploring_military_vehicles"):
        print(json.dumps(generate_military_vehicles(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "preview":
        print(build_exploring_vehicles_text()[:4000])
        print("\n---\n")
        print(build_exploring_military_vehicles_text()[:4000])
        return 0
    print(json.dumps({"error": "usage: field-exploring-vehicles.py [all|vehicles|military|preview]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())