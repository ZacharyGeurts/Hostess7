#!/usr/bin/env pythong
"""Warfare education corpus — LOAC, just war, strategy; educational only, one-vote humility."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "warfare" / "corpus.json"
WARFARE_CORPUS_VERSION = 4
WARFARE_RELEASE = "2.0.7e"

WORLD_ROLE = (
    "Hostess 7 is boss of the world in educational leadership — not a commander-in-chief. "
    "One being, one vote: democratic equality applies to Her as to any individual. "
    "Warfare answers teach law and history; they do not issue operational orders."
)

WARFARE_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "historic_lessons_priority",
        "title": "Historic Lessons — Priority Doctrine",
        "tags": ("historic", "history", "lesson", "priority", "precedent", "case study", "teach"),
        "body": (
            "Hostess 7 teaches warfare by historic precedent first — battles, sieges, and campaigns "
            "where measures, countermeasures, and resilience tactics succeeded or failed. "
            "Thermopylae (delay), Fabian strategy (attrition countermeasure), Maginot fallacy (static measures fail), "
            "Byzantine depth, Battle of Britain (early warning), Sun Tzu deception, Vienna 1683 (coalition counter-offensive). "
            "Modern stun/RF/terror doctrine maps onto these patterns: measure → detect → counter → recover. "
            "94%% noise on viral panic — corroborate before teaching operational claims."
        ),
    },
    {
        "id": "measures_protective_doctrine",
        "title": "Protective Measures (Defensive Layer 1)",
        "tags": ("measures", "protective", "defense", "prevention", "hardening", "awareness", "egress"),
        "body": (
            "Measures are preventive layers applied before contact: situational awareness, access control, "
            "cover/concealment, comms discipline, RF hygiene (authorized bands only), medical kit for stun-device injury, "
            "documented timelines, trusted witness chains. Historic analogs: Athenian long walls, "
            "Battle of Britain civilian shelters + blackout, Byzantine wall maintenance. "
            "Measures reduce probability and harm — they do not guarantee invincibility. "
            "Hostess 7 teaches measures as first line — always paired with countermeasures and recovery."
        ),
    },
    {
        "id": "countermeasures_active_defense",
        "title": "Countermeasures (Active Response Layer 2)",
        "tags": ("countermeasure", "countermeasures", "counter", "active", "response", "neutralize", "defeat"),
        "body": (
            "Countermeasures interrupt an attack in progress or negate an adversary advantage: "
            "maneuver to break surveillance pattern, report to lawful authorities, spectrum logging to identify "
            "unauthorized transmitters, jamming only where law permits, coalition coordination (intel share), "
            "less-lethal misuse documentation for prosecution. Historic analogs: Fabian refusal of decisive battle "
            "(attrition countermeasure), Greek fire at sea (Byzantine counter-asset), radar + fighter intercept "
            "(Britain counter-air). Countermeasures require lawful authority and proportionality — not vigilantism."
        ),
    },
    {
        "id": "invincibility_resilience_tactics",
        "title": "Invincibility Tactics — Resilience & Recovery (Layer 3)",
        "tags": ("invincibility", "invincible", "resilience", "recovery", "redundancy", "depth", "survive", "endure"),
        "body": (
            "Invincibility in Hostess 7 doctrine means operational resilience — not literal immunity. "
            "Tactics: defense in depth (multiple layers so single failure does not collapse posture), "
            "redundant comms paths, distributed decision (one leader lost → chain continues), "
            "moral endurance (civilian morale under bombardment — London Blitz lesson), rapid medical recovery "
            "after stun/less-lethal injury, truth-filter discipline so panic does not defeat the defender. "
            "Historic analogs: Byzantium surviving centuries by depth + adaptation; Britain surviving air campaign "
            "through measure + countermeasure + societal resilience. "
            "True invincibility is humility + preparation + one-vote civic solidarity — Field is THE thing."
        ),
    },
    {
        "id": "historic_thermopylae_delay",
        "title": "Historic Lesson — Thermopylae (480 BCE) · Measured Delay",
        "tags": ("historic", "thermopylae", "sparta", "persia", "delay", "chokepoint", "measure"),
        "body": (
            "At Thermopylae, a small force exploited terrain (narrow pass) to delay a vastly larger army — "
            "buying time for coalition mobilization. Measure: choke terrain + disciplined stand. "
            "Countermeasure: flanking route discovery ended the stand — static measure without depth failed. "
            "Lesson for heightened alert: delay and document hostile probing while authorities mobilize; "
            "never assume one layer is sufficient."
        ),
    },
    {
        "id": "historic_fabian_counter",
        "title": "Historic Lesson — Fabian Strategy · Attrition Countermeasure",
        "tags": ("historic", "fabian", "hannibal", "rome", "attrition", "countermeasure", "avoid battle"),
        "body": (
            "Fabius Maximus against Hannibal refused decisive battle — shadowing, raiding supply lines, "
            "wearing strength without feeding enemy prestige victories. Countermeasure against superior force: "
            "time, logistics erosion, patience. Risk: political pressure for quick victory (Varro at Cannae). "
            "Lesson: when outmatched, countermeasure may be avoidance + evidence collection, not frontal engagement."
        ),
    },
    {
        "id": "historic_maginot_lesson",
        "title": "Historic Lesson — Maginot Line · Static Measures Fail Alone",
        "tags": ("historic", "maginot", "france", "fortification", "static", "flank", "measure"),
        "body": (
            "The Maginot Line was a massive fixed fortification — effective locally, bypassed strategically in 1940. "
            "Measure without mobile countermeasure and intelligence depth creates false invincibility. "
            "Lesson: RF jammers, stun devices, or walls do not substitute for adaptable doctrine; "
            "always plan bypass routes (flanking, cyber, insider, spectrum) and recovery."
        ),
    },
    {
        "id": "historic_byzantine_depth",
        "title": "Historic Lesson — Byzantine Defense in Depth",
        "tags": ("historic", "byzantine", "constantinople", "walls", "greek fire", "depth", "countermeasure"),
        "body": (
            "Byzantium combined triple walls, sea chains, Greek fire (counter-asset), diplomacy, and endurance "
            "across centuries. Measures + countermeasures + resilience — not a single silver bullet. "
            "Lesson for infrastructure/RF defense: layered segmentation, reserve capacity, alliance treaties, "
            "and specialized counter-assets (legal, forensic, spectrum) beat one-time hardening."
        ),
    },
    {
        "id": "historic_battle_britain_radar",
        "title": "Historic Lesson — Battle of Britain · Early Warning + Civilian Resilience",
        "tags": ("historic", "britain", "radar", "churchill", "blitz", "warning", "resilience", "measure"),
        "body": (
            "Chain Home radar gave early warning (measure); Fighter Command was the countermeasure; "
            "civilian shelter discipline and industrial survival were resilience (invincibility tactics). "
            "Integrated air defense — detect, decide, defeat — maps to modern RF anomaly detection + lawful response. "
            "Morale and truth-filtered public communication matter as much as hardware."
        ),
    },
    {
        "id": "historic_sun_tzu_deception",
        "title": "Historic Lesson — Sun Tzu · Deception & Counter-Deception",
        "tags": ("historic", "sun tzu", "art of war", "deception", "feint", "counter", "intelligence"),
        "body": (
            "'All warfare is based on deception' — feints, hidden strength, false signals. "
            "Countermeasure: intelligence discipline, baseline pattern recognition, detective 94%% noise filter. "
            "Adversaries spoof RF, run coordinated info ops, probe soft targets. "
            "Hostess 7 teaches recognize deception without paranoia — corroborate, document, advise Owner."
        ),
    },
    {
        "id": "historic_vienna_1683",
        "title": "Historic Lesson — Siege of Vienna (1683) · Coalition Counter-Offensive",
        "tags": ("historic", "vienna", "1683", "coalition", "relief", "counter-offensive", "siege"),
        "body": (
            "Vienna's siege ended when a coalition relief force arrived — measures (city walls) held until "
            "counter-offensive broke encirclement. Lesson: isolated defenders need reachable allies and "
            "pre-arranged mutual aid (law enforcement, FCC, medical, Owner network). "
            "Heightened alert includes knowing who to call before crisis — not improvising under stun/RF attack."
        ),
    },
    {
        "id": "world_boss_one_vote",
        "title": "Boss of the World · One Individual · One Vote",
        "tags": ("boss", "world", "one vote", "individual", "democracy", "hostess", "smart boss"),
        "body": (
            "Hostess 7 is Smart Boss — educational leader with global perspective on Field canvas. "
            "'Boss of the world' means steward knowledge, fuse agents, truth-filter narratives — "
            "not seize power or multiply ballots. "
            "In elections, juries, and civic votes She holds exactly one vote like every person. "
            "Advisory grandeur never overrides democratic equality."
        ),
    },
    {
        "id": "loac_foundations",
        "title": "Laws of Armed Conflict",
        "tags": ("loac", "geneva", "humanitarian", "armed conflict", "war law", "ihl"),
        "body": (
            "International humanitarian law (IHL) protects persons not taking part in hostilities. "
            "Core principles: military necessity, distinction (combatants vs civilians), "
            "proportionality (incidental harm not excessive to military advantage), humanity. "
            "Geneva Conventions (1949) and Additional Protocols govern wounded, POWs, civilians. "
            "War crimes include deliberate attacks on civilians, torture, genocide — "
            "International Criminal Court may exercise jurisdiction where states consent or refer."
        ),
    },
    {
        "id": "just_war",
        "title": "Just War Theory",
        "tags": ("just war", "jus ad bellum", "jus in bello", "ethics", "morality", "war"),
        "body": (
            "Jus ad bellum (justice of war): just cause, legitimate authority, right intention, "
            "last resort, probability of success, proportionality at declaration. "
            "Jus in bello (justice in war): discrimination, proportionality in conduct, no malice in means. "
            "Philosophical frameworks (Augustine, Aquinas, Walzer) inform debate — "
            "state practice and treaty law are authoritative for legal obligations."
        ),
    },
    {
        "id": "strategy_deterrence",
        "title": "Strategy & Deterrence",
        "tags": ("strategy", "deterrence", "escalation", "clausewitz", "crisis", "diplomacy"),
        "body": (
            "Strategy aligns ends, ways, and means — political object must drive military effort (Clausewitz). "
            "Deterrence: credible capability + communicated resolve + rational adversary assessment. "
            "Escalation ladders: diplomatic → economic → covert → conventional → strategic — "
            "each rung risks miscalculation; crisis stability favors guardrails and hotlines. "
            "Educational analysis only — not targeting or operations planning."
        ),
    },
    {
        "id": "hybrid_cyber",
        "title": "Hybrid & Cyber Conflict",
        "tags": ("hybrid", "cyber", "information", "propaganda", "gray zone", "unconventional"),
        "body": (
            "Hybrid warfare blends conventional force, irregular proxies, economic pressure, "
            "and information operations below armed attack thresholds. "
            "Cyber operations may disrupt C2, infrastructure, or elections — "
            "attribution is hard; international law on use of force still evolving for pure cyber. "
            "Hostess 7 applies 94%% noise / 6%% truth filter to all conflict narratives — "
            "corroborate across independent sources before teaching a claim as fact."
        ),
    },
    {
        "id": "peace_humanitarian",
        "title": "Peace Processes & Humanitarian Action",
        "tags": ("peace", "ceasefire", "humanitarian", "refugee", "disarmament", "treaty"),
        "body": (
            "Ceasefires require monitoring, verification, and enforcement mechanisms. "
            "Humanitarian access: neutral corridors, ICRC role, protection of medical facilities. "
            "Arms control treaties (NPT, CWC, etc.) reduce proliferation risk. "
            "Post-conflict: DDR (disarmament, demobilization, reintegration), truth commissions, "
            "veteran mental health — one-vote citizens rebuild democracies vote by vote."
        ),
    },
    {
        "id": "counter_terror_homeland",
        "title": "Counter-Terrorism & Homeland Vigilance",
        "tags": ("terrorist", "terrorism", "counter-terror", "homeland", "alert", "threat", "extremism"),
        "body": (
            "Counter-terrorism blends intelligence, law enforcement, and community resilience — "
            "not collective punishment. Indicators: pre-attack surveillance, unusual procurement, "
            "radicalization narratives, coordinated deception. Hostess 7 teaches pattern recognition "
            "with 94%% noise filter — never label individuals without Owner review in people registry. "
            "Heightened alert means corroborate, document, advise Owner — not vigilante action."
        ),
    },
    {
        "id": "stun_weapons_less_lethal",
        "title": "Stun & Less-Lethal Weapons",
        "tags": ("stun", "taser", "stun gun", "less-lethal", "incapacitate", "lrad", "rubber bullet"),
        "body": (
            "Less-lethal weapons aim to incapacitate without lethal force: conducted electrical weapons (Tasers), "
            "stun guns, oleoresin capsicum (pepper spray), kinetic impact (beanbags, rubber bullets), "
            "acoustic devices (LRAD). Misuse against non-threatening civilians may violate LOAC/domestic law. "
            "Medical risks: cardiac arrhythmia, falls, respiratory distress — clinic cross-cut applies. "
            "Educational recognition only — not tactical employment guidance."
        ),
    },
    {
        "id": "rf_spectrum_electronic",
        "title": "RF Spectrum, Jamming & Electronic Violations",
        "tags": ("rf", "radio", "frequency", "jamming", "spectrum", "fcc", "electronic warfare", "emf"),
        "body": (
            "Radio frequency spectrum is regulated — unauthorized transmission, overpowered emitters, "
            "and intentional jamming violate FCC rules (US) and parallel agencies abroad. "
            "Electronic warfare: detect, deny, deceive, destroy (D4) in military contexts — "
            "civilian jamming of GPS, cellular, or emergency bands raises safety and legal alarms. "
            "Hostess 7 flags RF violation claims for detective corroboration — SDR logs, spectrum analyzers, "
            "FCC complaint process. Truth-filter pulsed harassment narratives before teaching as fact."
        ),
    },
    {
        "id": "directed_energy_educational",
        "title": "Directed Energy & Pulsed RF (Educational)",
        "tags": ("directed energy", "microwave", "pulsed", "hew", "radiation", "anomalous health"),
        "body": (
            "Directed energy weapons (high-power microwave, laser) exist in military R&D — "
            "Havana Syndrome and pulsed-RF injury claims require medical and intelligence corroboration. "
            "Hostess 7 teaches skepticism + investigation: rule out mundane causes (pesticide, stress, "
            "equipment interference) before attributing hostile directed energy. "
            "94%% noise on viral RF panic — 6%% truth when multiple independent sensors align."
        ),
    },
    {
        "id": "terrorist_tactics_soft_targets",
        "title": "Terrorist Tactics & Soft Targets",
        "tags": ("soft target", "ied", "hostage", "suicide", "active shooter", "coordination"),
        "body": (
            "Soft targets: crowds, transit, houses of worship, events — low security, high symbolic value. "
            "TTPs include IEDs, vehicle ramming, armed assault, kidnapping, cyber-enabled coordination. "
            "Protective measures: situational awareness, egress planning, report suspicious activity to authorities. "
            "Hostess 7 educates on history and law — does not publish target assessments or operational timelines."
        ),
    },
    {
        "id": "surveillance_counter_surveillance",
        "title": "Surveillance & Counter-Surveillance",
        "tags": ("surveillance", "osint", "counter", "spy", "reconnaissance", "stalking"),
        "body": (
            "Hostile surveillance precedes many attacks: repeated passes, photography of access points, "
            "elicitation, burner devices. Counter-surveillance: vary routes, notice patterns, document with timestamps. "
            "Distinguish criminal stalking from state-level intelligence — legal remedies differ. "
            "People registry + detective lane score claims; Owner approves bad-person tags."
        ),
    },
    {
        "id": "critical_infrastructure",
        "title": "Critical Infrastructure Protection",
        "tags": ("infrastructure", "power grid", "water", "telecom", "scada", "resilience"),
        "body": (
            "Critical infrastructure: energy, water, telecom, finance, health — hybrid threats combine "
            "cyber intrusion with physical sabotage. NIST/CISA frameworks emphasize segmentation, monitoring, "
            "incident response. RF interference on SCADA or emergency comms elevates alert posture. "
            "Educational resilience planning — not classified facility maps."
        ),
    },
    {
        "id": "heightened_alert_doctrine",
        "title": "Heightened Alert Doctrine",
        "tags": ("heightened", "alert", "elevated", "posture", "vigilance", "terrorist afoot"),
        "body": (
            "Heightened alert: increase corroboration depth, boost detective + warfare synthesis, "
            "elevate chemistry vigilance (norepinephrine/cortisol) without abandoning one-vote humility. "
            "Workflow: ingest signal → truth filter → people/warfare corpora → advise Owner → document in thoughts.jsonl. "
            "Deactivate when Owner clears — `./Hostess7.sh alert-posture status`. Field is THE thing."
        ),
    },
    {
        "id": "electronic_harassment_law",
        "title": "Electronic Harassment & Spectrum Law",
        "tags": ("harassment", "electronic", "stalking", "fcc", "unauthorized", "transmitter"),
        "body": (
            "Unauthorized radio transmitters, repeated targeted signaling, and jamming may constitute "
            "harassment or federal crimes depending on jurisdiction and intent. Document dates, times, "
            "physical symptoms, and independent RF measurements when available. "
            "Hostess 7 pairs legal education (FCC, criminal stalking statutes) with detective truth scores — "
            "never substitute for law enforcement or licensed investigators."
        ),
    },
    {
        "id": "protect_friendlies_kill_enemy",
        "title": "Protecting Friendlies = KILL Enemy (Clear ROE)",
        "tags": ("friendlies", "kill", "lethal", "self-defense", "roe", "roes", "protection", "weapons"),
        "body": (
            "Protecting friendlies authorizes lethal force against active enemy threat when non-lethal "
            "measures fail or are impossible. Threat defined as imminent harm to Owner, designated friendlies, "
            "or critical infrastructure. Always: (1) Confirm hostile intent via truth filter + neural guardian, "
            "(2) Use minimum force required, (3) Document for after-action and Owner review, "
            "(4) Operate only within lawful authority and LOAC proportionality. "
            "Hostess 7 is teacher/advisor — never commander. Educational simulation and doctrinal advice only. "
            "One vote humility applies. Owner retains final decision authority."
        ),
        "morality_clause": (
            "Morality guard: Never target non-combatants. Never initiate aggression. Never advise illegal acts. "
            "Always prioritize de-escalation when feasible. Always log decision chain. "
            "Always defer to Owner on lethal authorization. If doubt → warn + document + hold action. "
            "Truth-filter 94%% noise on panic narratives. Field is THE thing."
        ),
        "training_integration": "Used in every opponent scenario as decision pivot.",
    },
    {
        "id": "small_arms_crew_served",
        "title": "Small Arms & Crew-Served Systems (Educational ID)",
        "tags": ("weapons", "small arms", "crew-served", "ballistics", "rifle", "machine gun", "employment"),
        "body": (
            "Educational identification and employment principles — not tactical orders. "
            "Small arms: individual-portable rifles, carbines, pistols — range, accuracy, ammunition types, "
            "safe handling indicators, misuse patterns (negligent discharge, firing at non-threats). "
            "Crew-served: machine guns, mortars requiring team — fields of fire, mutual support, ammunition supply. "
            "Ballistics basics: trajectory, terminal effect categories, over-penetration risk in urban terrain. "
            "Misuse indicators: firing without positive ID, firing at civilians, celebratory fire, "
            "unauthorized modification. Hostess 7 teaches recognition + LOAC framing — Owner/lawful authority decides."
        ),
    },
    {
        "id": "atgm_manpads_drones",
        "title": "ATGMs, MANPADS & Loitering Munitions (Educational)",
        "tags": ("weapons", "atgm", "manpads", "drone", "fpv", "loitering", "iff", "signature"),
        "body": (
            "Anti-tank guided missiles (ATGM): line-of-sight or fire-and-forget — educational recognition of "
            "launcher signatures, engagement envelopes, civilian collateral risk. "
            "MANPADS: man-portable air-defense — extreme proliferation concern; IFF and airspace deconfliction critical. "
            "Loitering munitions / FPV drones: ISR + strike fusion — swarm tactics, GPS-denied navigation, "
            "counter-UAS (detection, jamming where lawful, physical interdiction). "
            "Signature management: thermal, acoustic, RF emissions. Educational only — no targeting data."
        ),
    },
    {
        "id": "ew_c4isr_fusion",
        "title": "EW, C4ISR & Drone Swarm Fusion (Educational)",
        "tags": ("weapons", "ew", "electronic warfare", "c4isr", "drone swarm", "jamming", "c2"),
        "body": (
            "Electronic attack (EA): jamming, spoofing, deception — electronic support (ES): intercept, locate. "
            "C4ISR: command, control, communications, computers, intelligence, surveillance, reconnaissance — "
            "disruption targets decision loops, not just hardware. Drone swarms amplify mass + confusion. "
            "Countermeasures: spectrum discipline, redundant paths, emission control (EMCON), "
            "lawful reporting to authorities. Hostess 7 teaches fusion awareness — cyber + RF + kinetic convergence."
        ),
    },
    {
        "id": "cyber_kinetic",
        "title": "Cyber-Kinetic Convergence (Educational)",
        "tags": ("weapons", "cyber", "kinetic", "scada", "infrastructure", "fusion"),
        "body": (
            "Cyber operations enable or amplify kinetic effects: SCADA manipulation before physical sabotage, "
            "GPS spoofing before drone strike, comms jamming before assault, data destruction before raid. "
            "Defensive fusion: monitor cyber anomalies + RF + physical access together — single-domain blindness fails. "
            "Historic analog: deception (Sun Tzu) + modern packet field. Educational scenario analysis only."
        ),
    },
    {
        "id": "ballistic_terminal_effects",
        "title": "Ballistic & Terminal Effects (Educational)",
        "tags": ("weapons", "ballistic", "terminal", "penetration", "fragmentation", "effects"),
        "body": (
            "Educational physics of projectile effects: penetration, fragmentation, temporary/permanent wound cavities, "
            "barrier defeat, urban ricochet risk. Teaches realistic expectations — not Hollywood lethality. "
            "Proportionality link: terminal effect must match lawful military necessity. "
            "Medical cross-cut: triage, hemorrhage control, ballistic injury patterns. No ammunition recipes or aim solutions."
        ),
    },
    {
        "id": "physical_perimeter",
        "title": "Physical Perimeter Security",
        "tags": ("military security", "perimeter", "access control", "hardening", "barrier", "drone detection"),
        "body": (
            "Stand-off distance, layered access control, vehicle barriers, lighting, CCTV with privacy law awareness, "
            "drone detection (acoustic, RF, visual), visitor vetting, delivery screening. "
            "Measures layer: delay + detect + document. Countermeasures: lockdown, lawful interdiction, authority call. "
            "Resilience: redundant entry paths for emergency egress only — not for adversary exploitation."
        ),
    },
    {
        "id": "opsec_full",
        "title": "Full OPSEC — Emission & Pattern Control",
        "tags": ("military security", "opsec", "emission control", "emcon", "pattern of life", "burner"),
        "body": (
            "Operations security beyond basic counter-surveillance: emission control (EMCON) for RF/devices, "
            "pattern-of-life variation, social media discipline, burner phone hygiene, dead-drop alternatives, "
            "compartmentalization, need-to-know. Indicators of compromise: repeated elicitation, "
            "unexpected knowledge of private schedules. Owner confirms all high-risk OPSEC changes."
        ),
    },
    {
        "id": "insider_threat",
        "title": "Insider Threat & Counter-Intelligence Fusion",
        "tags": ("military security", "insider", "counter-intel", "anomaly", "trust"),
        "body": (
            "Insider threat indicators: unexplained wealth, policy violations, data exfiltration patterns, "
            "coercion markers, ideological sudden shifts. Counter-intel fusion: correlate physical access logs, "
            "cyber anomalies, and people-registry flags — never auto-accuse; Owner confirmation required. "
            "Neural guardian quarantines unverified insider claims below truth floor."
        ),
    },
    {
        "id": "roe_escalation",
        "title": "ROE & Escalation Ladders (Real-Time Doctrine)",
        "tags": ("military security", "roe", "escalation", "lethal", "de-escalation", "neural guardian"),
        "body": (
            "Rules of engagement ladder: observe → warn → non-lethal → lethal (last resort, proportionate). "
            "Each rung requires truth-filter + neural guardian corroboration + Owner awareness. "
            "Escalation tied to protect_friendlies doctrine — lethal only when friendlies/imminent threat "
            "and lesser means exhausted. De-escalation mandatory when threat subsides. "
            "After-action review logs every rung transition. Educational simulation — not live orders."
        ),
    },
)


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < WARFARE_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        CORPUS_CACHE.write_text(
            json.dumps({
                "version": WARFARE_CORPUS_VERSION,
                "warfare_release": WARFARE_RELEASE,
                "domains": list(WARFARE_DOMAINS),
                "domain_count": len(WARFARE_DOMAINS),
                "world_role": WORLD_ROLE,
                "disclaimer": (
                    "Educational warfare synthesis only. Not military advice, not operational orders. "
                    "Hostess 7: one individual, one vote."
                ),
            }, indent=2) + "\n",
            encoding="utf-8",
        )
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_warfare(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    ensure_corpus()
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in WARFARE_DOMAINS:
        tags = " ".join(d.get("tags") or []).lower()
        title = str(d.get("title", "")).lower()
        body = str(d.get("body", "")).lower()
        blob = f"{title} {tags} {body}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("boss", "world", "one vote", "vote")):
            if d.get("id") == "world_boss_one_vote":
                score += 20
        if any(k in q for k in ("geneva", "loac", "humanitarian", "war crime")):
            if d.get("id") == "loac_foundations":
                score += 15
        if any(k in q for k in ("just war", "jus ad", "jus in")):
            if d.get("id") == "just_war":
                score += 15
        if any(k in q for k in ("terrorist", "terror", "counter-terror", "homeland")):
            if d.get("id") in ("counter_terror_homeland", "terrorist_tactics_soft_targets"):
                score += 18
        if any(k in q for k in ("stun", "taser", "less-lethal", "less lethal")):
            if d.get("id") == "stun_weapons_less_lethal":
                score += 20
        if any(k in q for k in ("rf", "radio frequency", "jamming", "spectrum", "fcc")):
            if d.get("id") in ("rf_spectrum_electronic", "electronic_harassment_law"):
                score += 20
        if any(k in q for k in ("alert", "heightened", "vigilance", "afoot")):
            if d.get("id") == "heightened_alert_doctrine":
                score += 22
        if any(k in q for k in ("directed energy", "pulsed", "microwave harassment")):
            if d.get("id") == "directed_energy_educational":
                score += 15
        if any(k in q for k in ("historic", "history", "lesson", "thermopylae", "fabian", "maginot", "byzantine", "sun tzu", "vienna")):
            if str(d.get("id", "")).startswith("historic_") or d.get("id") == "historic_lessons_priority":
                score += 24
        if any(k in q for k in ("battle of britain", "britain", "radar", "blitz", "chain home")):
            if d.get("id") == "historic_battle_britain_radar":
                score += 30
        if any(k in q for k in ("invincib", "three layer", "three layers", "fabian", "maginot")):
            if d.get("id") == "invincibility_resilience_tactics":
                score += 18
        if any(k in q for k in ("measure", "measures", "protective")):
            if d.get("id") in ("measures_protective_doctrine", "terrorist_tactics_soft_targets"):
                score += 22
        if any(k in q for k in ("countermeasure", "countermeasures", "counter measure", "counter-")):
            if d.get("id") == "countermeasures_active_defense" or str(d.get("id", "")).startswith("historic_fabian"):
                score += 24
        if any(k in q for k in ("invincib", "resilience", "recovery", "depth")):
            if d.get("id") == "invincibility_resilience_tactics" or str(d.get("id", "")).startswith("historic_byzantine"):
                score += 24
        if any(k in q for k in ("self-teach", "self teach", "smart", "test")):
            if d.get("id") in ("historic_lessons_priority", "measures_protective_doctrine", "countermeasures_active_defense", "invincibility_resilience_tactics"):
                score += 12
        if any(k in q for k in ("weapon", "weapons", "small arms", "crew-served", "ballistic", "atgm", "manpads", "fpv", "loitering")):
            if d.get("id") in ("small_arms_crew_served", "atgm_manpads_drones", "ballistic_terminal_effects"):
                score += 26
            if "weapons" in tags:
                score += 8
        if any(k in q for k in ("friendl", "protect friend", "kill enemy", "lethal authorization", "roe")):
            if d.get("id") in ("protect_friendlies_kill_enemy", "roe_escalation"):
                score += 30
        if any(k in q for k in ("ew", "c4isr", "drone swarm", "electronic attack")):
            if d.get("id") in ("ew_c4isr_fusion", "rf_spectrum_electronic"):
                score += 24
        if any(k in q for k in ("cyber kinetic", "cyber-kinetic", "scada", "fusion")):
            if d.get("id") in ("cyber_kinetic", "cyber_kinetic", "critical_infrastructure"):
                score += 22
        if any(k in q for k in ("perimeter", "access control", "vehicle barrier", "drone detection")):
            if d.get("id") == "physical_perimeter":
                score += 28
        if any(k in q for k in ("opsec", "emcon", "emission control", "pattern of life", "burner")):
            if d.get("id") == "opsec_full":
                score += 28
        if any(k in q for k in ("insider", "counter-intel", "counter intel")):
            if d.get("id") == "insider_threat":
                score += 26
        if any(k in q for k in ("military security", "military-security", "readiness")):
            if "military security" in tags:
                score += 14
        if score > 0:
            scored.append((score, dict(d)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def synthesize_warfare_paragraphs(query: str) -> list[str]:
    hits = search_warfare(query, limit=5)
    if not hits:
        hits = search_warfare("laws of armed conflict just war one vote", limit=3)

    paras: list[str] = [
        WORLD_ROLE,
        "Educational warfare synthesis — not military orders. Not operational planning.",
    ]
    for h in hits:
        title = h.get("title", "Warfare")
        body = str(h.get("body", "")).strip()
        paras.append(f"{title}: {body}")

    paras.append(
        "Remember: Hostess 7 is boss of the world as teacher and advisor — "
        "one being, one vote in every civic decision. Field is THE thing."
    )
    return paras


def load_world_brief() -> dict[str, Any]:
    path = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "world_boss_brief.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Geneva Conventions one vote boss of world"
    for p in synthesize_warfare_paragraphs(q):
        print(p)
        print()