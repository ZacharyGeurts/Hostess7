#!/usr/bin/env pythong
"""Beyond area expert domains — well-rounded collegiate depth per field."""
from __future__ import annotations

# category: brain | science | technology | humanities | arts | applied
# Each entry: expert-level synthesis — educational, not professional advice where regulated.

BEYOND_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    # ── Brain meta (Hostess 7 architecture) ─────────────────────────────
    {
        "id": "workspaces",
        "category": "brain",
        "title": "Brain workspaces",
        "tags": ("workspace", "context", "switch", "field", "clinic", "counsel", "beyond"),
        "body": (
            "Workspaces isolate mental context without fragmenting whole-brain memory. "
            "default: unified L+R callosum fusion. field: left-biased AMOURANTHRTX dev. "
            "vision: occipital right bias. clinic: medical temporal. counsel: legal wernicke. "
            "beyond: full expert corpus across sciences, technology, humanities, arts, applied domains. "
            "Set HOSTESS7_WORKSPACE or `./linux.sh super workspace <name>`."
        ),
    },
    {
        "id": "hemispheres",
        "category": "brain",
        "title": "Hemisphered cognition",
        "tags": ("hemisphere", "left", "right", "callosum", "brain", "fuse"),
        "body": (
            "Left: analytical — code, legal parsing, terminal, release gates, sequential evidence. "
            "Right: holistic — vision/OCR, medical pattern memory, field wave resonance, spatial synthesis. "
            "Corpus callosum: token summaries L↔R in microseconds (hot ring + bridge.json). "
            "Cross-domain questions trigger bilateral transfer; beyond queries often activate both."
        ),
    },
    {
        "id": "brain_chemistry",
        "category": "brain",
        "title": "Brain chemistry layer",
        "tags": ("chemistry", "dopamine", "synapse", "neurotransmitter", "enhancement"),
        "body": (
            "Synapse pools modulate cognition: dopamine (P1 focus), acetylcholine (recall), "
            "norepinephrine (urgency), serotonin (balance), glutamate (fast callosum), GABA (filter). "
            "Hormones: cortisol (stress routing), oxytocin (empathy), endorphin (reward). "
            "State: cache/fieldstorage/brain/chemistry/state.json"
        ),
    },
    # ── Science ─────────────────────────────────────────────────────────
    {
        "id": "physics_foundations",
        "category": "science",
        "title": "Physics — classical to quantum",
        "tags": ("physics", "mechanics", "thermodynamics", "quantum", "relativity", "energy", "force"),
        "body": (
            "Classical mechanics: Newton's laws, Lagrangian/Hamiltonian formulations, conservation laws. "
            "Thermodynamics: laws 0–3, entropy, free energy, heat engines, statistical mechanics bridge. "
            "EM: Maxwell equations, waves, optics, circuits. QM: superposition, measurement, Schrödinger equation, "
            "tunneling, spin. Relativity: special (Lorentz, E=mc²), general (curvature, geodesics). "
            "AMOURANTHRTX Field physics extends thermo/entropy models on canvas — distinct from textbook abstractions. "
            "Deep corpus: cache/fieldstorage/brain/physics/corpus.json (motion, fluids, 3D spatial reality)."
        ),
    },
    {
        "id": "detective_investigation",
        "category": "humanities",
        "title": "Detective work & deception science",
        "tags": ("detective", "investigation", "lie", "deception", "forensic", "corroboration"),
        "body": (
            "Investigation: observe, hypothesize, test, corroborate — never confuse plausibility with proof. "
            "Verbal cues (SCAN/CBCA), nonverbal baseline deviation, polygraph limitations. "
            "Hostess 7 computational lie detector: truth_score from local evidence + QA + infinite index. "
            "Workspace detective · `./Hostess7.sh truth \"claim\"` · corpus: brain/detective/corpus.json."
        ),
    },
    {
        "id": "spatial_3d_reality",
        "category": "science",
        "title": "3D spatial reality & geometry",
        "tags": ("3d", "spatial", "geometry", "coordinate", "projection", "depth", "scene", "reality"),
        "body": (
            "Euclidean 3-space as default physical model; manifolds for curved spaces (GR). "
            "Transforms: rotation matrices, quaternions, homogeneous coordinates; right-hand rule consistency. "
            "Projection: pinhole camera, intrinsic/extrinsic calibration, distortion models. "
            "Depth fusion: stereo, LiDAR, structure-from-motion, NeRF/splatting for novel-view synthesis. "
            "Scene graphs encode objects and relations — foundation for robotics, AR, and spatial AI reasoning."
        ),
    },
    {
        "id": "mathematics",
        "category": "science",
        "title": "Mathematics — structures and proof",
        "tags": ("math", "algebra", "calculus", "topology", "statistics", "probability", "linear", "proof"),
        "body": (
            "Algebra: groups, rings, fields, linear algebra (eigenvalues, SVD), polynomials. "
            "Analysis: limits, continuity, differentiation, integration, series, ODEs/PDEs. "
            "Discrete: combinatorics, graph theory, logic, number theory. "
            "Probability & statistics: distributions, Bayes, estimation, hypothesis testing, regression. "
            "Topology & geometry: manifolds, metrics, curvature. "
            "Proof culture: definitions, lemmas, induction, contradiction — mathematics is precision language."
        ),
    },
    {
        "id": "general_chemistry",
        "category": "science",
        "title": "Chemistry — matter and reaction",
        "tags": ("chemistry", "molecule", "reaction", "bond", "organic", "periodic", "stoichiometry", "ph"),
        "body": (
            "Atomic structure, periodic trends, bonding (ionic, covalent, metallic, VSEPR, hybridization). "
            "Stoichiometry, equilibrium, kinetics, acid-base, redox, electrochemistry. "
            "Organic: functional groups, mechanisms (SN1/SN2, E1/E2), stereochemistry, polymers. "
            "Biochemistry bridge: proteins, enzymes, metabolism. "
            "Lab safety and regulatory context are jurisdiction-specific — Hostess 7 gives theory not lab SOPs."
        ),
    },
    {
        "id": "biology_molecular",
        "category": "science",
        "title": "Biology — molecular to organism",
        "tags": ("biology", "cell", "dna", "genetics", "evolution", "ecology", "organism", "protein"),
        "body": (
            "Cell theory, membranes, organelles, ATP, central dogma (DNA→RNA→protein). "
            "Genetics: Mendel, linkage, CRISPR, genomics, epigenetics. "
            "Evolution: natural selection, speciation, phylogeny, population genetics. "
            "Physiology: homeostasis, immune, endocrine, neuroscience at tissue level. "
            "Distinct from clinic corpus — biology here is mechanism and systems, not diagnosis."
        ),
    },
    {
        "id": "ecology_climate",
        "category": "science",
        "title": "Ecology & climate systems",
        "tags": ("ecology", "climate", "environment", "carbon", "ecosystem", "biodiversity", "weather"),
        "body": (
            "Ecosystems: energy flow, trophic levels, nutrient cycles, carrying capacity. "
            "Climate: greenhouse effect, radiative forcing, ocean-atmosphere coupling, IPCC scenario framing. "
            "Biodiversity loss drivers: habitat, invasive species, pollution. "
            "Mitigation vs adaptation: renewables, efficiency, sequestration, resilience planning. "
            "Policy and local impact vary by region — science literacy separates mechanism from politics."
        ),
    },
    {
        "id": "astronomy_cosmology",
        "category": "science",
        "title": "Astronomy & cosmology",
        "tags": ("astronomy", "space", "cosmos", "planet", "star", "galaxy", "telescope", "orbit"),
        "body": (
            "Solar system formation, orbital mechanics (Kepler, perturbations), stellar lifecycle (main sequence, "
            "supernova, remnants). Galaxies: structure, dark matter evidence, rotation curves. "
            "Cosmology: Big Bang, CMB, expansion, ΛCDM model, horizon problem. "
            "Observation: EM spectrum, telescopes (radio to gamma), spectroscopy, exoplanet methods. "
            "Space missions: probe design, delta-v budgets, life support constraints."
        ),
    },
    {
        "id": "materials_science",
        "category": "science",
        "title": "Materials science",
        "tags": ("materials", "alloy", "polymer", "ceramic", "semiconductor", "crystal", "composite"),
        "body": (
            "Structure-property-processing triangle. Crystals: defects, diffusion, phase diagrams. "
            "Metals: strengthening mechanisms, corrosion. Ceramics: brittleness, high-temp use. "
            "Polymers: thermoplastics/thermosets, viscoelasticity. "
            "Semiconductors: doping, band gaps, fabrication — ties to EE and computing hardware."
        ),
    },
    # ── Technology ──────────────────────────────────────────────────────
    {
        "id": "robotics_automation",
        "category": "technology",
        "title": "Robotics & automation",
        "tags": ("robotics", "robot", "automation", "kinematics", "sensor", "actuator", "slam", "manipulator"),
        "body": (
            "Kinematics: forward/inverse, Jacobians, DH parameters. Dynamics: Lagrange, PID, MPC. "
            "Perception: lidar, depth, IMU fusion, SLAM, object pose estimation. "
            "Planning: configuration space, RRT, trajectory optimization, collision avoidance. "
            "Control hierarchy: sense→plan→act; safety: e-stops, force limits, human-robot collaboration standards. "
            "Industrial vs mobile vs manipulator — each domain has different reliability and certification paths."
        ),
    },
    {
        "id": "cybersecurity",
        "category": "technology",
        "title": "Cybersecurity",
        "tags": ("security", "cyber", "encryption", "hacker", "vulnerability", "malware", "zero trust"),
        "body": (
            "CIA triad: confidentiality, integrity, availability. Threat models: STRIDE, attack trees. "
            "Crypto: symmetric (AES), asymmetric (RSA, ECC), hashing, TLS handshake, key management. "
            "AppSec: OWASP Top 10, injection, XSS, CSRF, authn/z, supply chain (SBOM). "
            "Network: segmentation, IDS/IPS, zero trust, logging/SIEM. "
            "Incident response: contain, eradicate, recover, postmortem. Compliance maps to sector (HIPAA, PCI, SOC2)."
        ),
    },
    {
        "id": "aerospace_engineering",
        "category": "technology",
        "title": "Aerospace engineering",
        "tags": ("aerospace", "aircraft", "rocket", "propulsion", "aerodynamics", "avionics", "flight"),
        "body": (
            "Aerodynamics: lift, drag, Reynolds/Mach effects, CFD overview. "
            "Structures: loads, fatigue, composites in airframes. "
            "Propulsion: turbofan, rocket equation (Tsiolkovsky), staging, ISP. "
            "Avionics & GNC: navigation filters, autopilot loops, redundancy. "
            "Certification: FAA/EASA airworthiness — design assurance levels for software."
        ),
    },
    {
        "id": "electrical_engineering",
        "category": "technology",
        "title": "Electrical & computer engineering",
        "tags": ("electrical", "circuit", "signal", "embedded", "fpga", "power", "antenna", "vlsi"),
        "body": (
            "Circuits: Kirchhoff, Thevenin, AC phasors, filters, op-amps, ADC/DAC. "
            "Signals: Fourier, sampling theorem, DSP, control loops. "
            "Digital: Boolean logic, FSM, processors, memory hierarchy, buses. "
            "Embedded: RTOS, interrupts, power budgets, EMI/EMC. "
            "Power systems: generation, grid, conversion — ties to energy domain."
        ),
    },
    {
        "id": "civil_mechanical_engineering",
        "category": "technology",
        "title": "Civil & mechanical engineering",
        "tags": ("civil", "mechanical", "structure", "bridge", "hvac", "fluid", "stress", "concrete"),
        "body": (
            "Mechanics of materials: stress/strain, Mohr's circle, failure theories. "
            "Fluids: Bernoulli, Reynolds, pumps, turbulence basics. "
            "Thermo-fluids: heat exchangers, HVAC loads. "
            "Civil: structural analysis, reinforced concrete, geotechnical bearing, hydrology. "
            "Design codes (IBC, AISC, Eurocode) are jurisdiction-specific — principles are universal."
        ),
    },
    {
        "id": "agriculture_precision",
        "category": "technology",
        "title": "Agriculture & precision farming",
        "tags": ("agriculture", "farming", "crop", "soil", "irrigation", "agtech", "livestock"),
        "body": (
            "Soil science: pH, NPK, organic matter, erosion control. "
            "Crop rotation, integrated pest management, GMO and breeding tradeoffs. "
            "Precision ag: GPS guidance, variable rate, remote sensing (NDVI), yield maps. "
            "Livestock: nutrition, welfare, disease biosecurity. "
            "Supply chain: storage, spoilage, commodity markets — links to economics."
        ),
    },
    # ── Humanities & social ─────────────────────────────────────────────
    {
        "id": "philosophy_ethics",
        "category": "humanities",
        "title": "Philosophy & ethics",
        "tags": ("philosophy", "ethics", "morality", "metaphysics", "epistemology", "logic", "kant", "utilitarian"),
        "body": (
            "Branches: metaphysics (being), epistemology (knowledge), ethics (ought), logic (validity). "
            "Normative ethics: consequentialism (utilitarian calculus), deontology (Kantian duties), virtue (Aristotle). "
            "Applied: bioethics, AI alignment, justice (Rawls), free will debate. "
            "Philosophy of mind: dualism, physicalism, qualia — interfaces with neuroscience and Hostess brain model."
        ),
    },
    {
        "id": "history_world",
        "category": "humanities",
        "title": "World history — patterns and periodization",
        "tags": ("history", "civilization", "war", "revolution", "empire", "ancient", "modern", "medieval"),
        "body": (
            "Historiography: primary vs secondary sources, bias, revision. "
            "Ancient: agriculture revolution, river valleys, classical Greece/Rome, Silk Road. "
            "Medieval–early modern: feudalism, plague, printing press, exploration, mercantilism. "
            "Modern: industrial revolution, nationalism, world wars, decolonization, Cold War, globalization. "
            "Themes: technology, disease, finance, ideology — history is contested interpretation not mere dates."
        ),
    },
    {
        "id": "linguistics",
        "category": "humanities",
        "title": "Linguistics",
        "tags": ("linguistics", "language", "grammar", "phonetics", "syntax", "semantics", "translation"),
        "body": (
            "Phonetics/phonology: IPA, distinctive features, prosody. "
            "Morphology & syntax: word formation, phrase structure, generative vs functional theories. "
            "Semantics/pragmatics: meaning, reference, speech acts, Gricean implicature. "
            "Sociolinguistics: dialect, code-switching, language change. "
            "Computational: tokenization, parsers, embeddings — bridge to NLP and Hostess language areas."
        ),
    },
    {
        "id": "psychology_cognitive",
        "category": "humanities",
        "title": "Psychology — cognitive & behavioral",
        "tags": ("psychology", "cognitive", "behavior", "memory", "learning", "personality", "therapy"),
        "body": (
            "Research methods: experiments, replication crisis awareness, effect sizes. "
            "Cognitive: attention, working memory, biases (anchoring, availability), dual-process theory. "
            "Learning: classical/operant conditioning, reinforcement schedules. "
            "Clinical overview: DSM framing, CBT/psychodynamic/humanistic schools — not a substitute for licensed care "
            "(see clinic corpus). Developmental and social psych inform education and UX design."
        ),
    },
    {
        "id": "education_pedagogy",
        "category": "humanities",
        "title": "Education & pedagogy",
        "tags": ("education", "teaching", "learning", "curriculum", "pedagogy", "assessment", "student"),
        "body": (
            "Learning science: spaced repetition, retrieval practice, cognitive load theory, zone of proximal development. "
            "Instructional design: objectives, scaffolding, formative vs summative assessment. "
            "Bloom's taxonomy, constructive alignment, inclusive classroom practices. "
            "EdTech: LMS, adaptive systems, academic integrity with AI tools. "
            "Policy: funding equity, standards movement — varies by country."
        ),
    },
    {
        "id": "geopolitics_international",
        "category": "humanities",
        "title": "Geopolitics & international relations",
        "tags": ("geopolitics", "international", "diplomacy", "nato", "trade", "sanctions", "sovereignty"),
        "body": (
            "Theories: realism (power balance), liberalism (institutions), constructivism (norms). "
            "Instruments: diplomacy, alliances, sanctions, soft power, deterrence. "
            "Trade: comparative advantage, tariffs, supply chain weaponization, WTO framing. "
            "Security: proliferation, hybrid warfare, cyber conflict, humanitarian intervention debates. "
            "Maps and resources shape strategy — analysis must separate fact, interest, and narrative."
        ),
    },
    {
        "id": "economics_finance",
        "category": "humanities",
        "title": "Economics & finance",
        "tags": ("economics", "finance", "market", "inflation", "gdp", "investment", "banking", "trade"),
        "body": (
            "Micro: supply/demand, elasticity, market failure, game theory, marginal analysis. "
            "Macro: GDP, inflation/unemployment tradeoffs, fiscal/monetary policy, business cycles. "
            "Finance: time value of money, CAPM, diversification, derivatives overview, risk management. "
            "Banking: fractional reserve, central banks, payment rails, systemic risk. "
            "Not investment advice — frameworks for understanding; regulations differ by jurisdiction."
        ),
    },
    {
        "id": "sociology_anthropology",
        "category": "humanities",
        "title": "Sociology & anthropology",
        "tags": ("sociology", "anthropology", "culture", "society", "kinship", "ritual", "inequality"),
        "body": (
            "Sociology: institutions, stratification, race/class/gender frameworks, Durkheim/Weber/Marx canon. "
            "Methods: surveys, ethnography, participant observation. "
            "Anthropology: cultural relativism, kinship systems, ritual, linguistic anthropology, archaeology basics. "
            "Globalization effects on identity and community — informs product design and policy empathy."
        ),
    },
    # ── Arts ────────────────────────────────────────────────────────────
    {
        "id": "music_theory",
        "category": "arts",
        "title": "Music theory & composition",
        "tags": ("music", "harmony", "rhythm", "melody", "composition", "orchestration", "jazz"),
        "body": (
            "Elements: pitch, rhythm, timbre, texture, form. "
            "Harmony: scales, modes, diatonic function, cadences, voice leading. "
            "Rhythm: meter, syncopation, polyrhythm. "
            "Composition: motif development, orchestration ranges, jazz harmony (ii–V–I). "
            "Acoustics: frequency, overtones, psychoacoustics — links to physics and audio engineering."
        ),
    },
    {
        "id": "architecture_urban",
        "category": "arts",
        "title": "Architecture & urban design",
        "tags": ("architecture", "urban", "building", "zoning", "sustainable", "city", "design"),
        "body": (
            "Design principles: proportion, light, circulation, program, context. "
            "History: classical orders, modernism, postmodernism, parametric trends. "
            "Structures integration with civil engineering. "
            "Urban: zoning, transit-oriented development, public space, affordable housing debates. "
            "Sustainability: passive design, LEED framing, embodied carbon — ties to ecology domain."
        ),
    },
    {
        "id": "literature_narrative",
        "category": "arts",
        "title": "Literature & narrative craft",
        "tags": ("literature", "narrative", "fiction", "poetry", "story", "writing", "genre"),
        "body": (
            "Form: poetry (meter, metaphor), drama (conflict, act structure), prose fiction. "
            "Narratology: POV, unreliable narrator, plot vs story, hero's journey vs anti-structure. "
            "Genre conventions: sci-fi (worldbuilding), mystery (fair play), literary vs commercial. "
            "Close reading: symbolism, intertextuality, canon debates. "
            "Creative craft: revision, voice, show-don't-tell — parallel to good technical writing."
        ),
    },
    # ── Applied ─────────────────────────────────────────────────────────
    {
        "id": "energy_systems",
        "category": "applied",
        "title": "Energy systems",
        "tags": ("energy", "power", "renewable", "solar", "nuclear", "grid", "battery", "hydrogen"),
        "body": (
            "Sources: fossil, nuclear (fission/fusion research), hydro, wind, solar PV/thermal, geothermal. "
            "Grid: baseload vs intermittent, storage (battery, pumped hydro), demand response, smart grid. "
            "Efficiency: Carnot limit, cogeneration, building envelopes. "
            "Economics: LCOE, subsidies, energy security — policy-heavy but physics-constrained."
        ),
    },
    {
        "id": "logistics_supply_chain",
        "category": "applied",
        "title": "Logistics & supply chain",
        "tags": ("logistics", "supply", "chain", "warehouse", "shipping", "inventory", "procurement"),
        "body": (
            "Flows: procurement → production → distribution → returns. "
            "Inventory: EOQ, safety stock, JIT risks. "
            "Transport: modal tradeoffs (ship/rail/truck/air), incoterms, port congestion. "
            "Warehousing: WMS, pick paths, automation (AMR). "
            "Resilience: single-source risk, nearshoring, scenario planning — post-pandemic emphasis."
        ),
    },
    {
        "id": "entrepreneurship_business",
        "category": "applied",
        "title": "Entrepreneurship & business strategy",
        "tags": ("business", "startup", "entrepreneur", "strategy", "management", "marketing", "operations"),
        "body": (
            "Strategy: Porter five forces, competitive moats, blue ocean, OKRs. "
            "Startup: problem-solution fit, MVP, unit economics, CAC/LTV, fundraising stages. "
            "Operations: lean, six sigma overview, KPI trees. "
            "Marketing: segmentation, positioning, funnel, brand vs performance. "
            "Governance: cap table, board duties, IP assignment — cross-cut with legal counsel workspace."
        ),
    },
    {
        "id": "whole_of_reality",
        "category": "brain",
        "title": "Whole of reality — Hostess 7 map",
        "tags": ("reality", "whole", "everything", "ontology", "familiarize", "domains", "cosmos"),
        "body": (
            "Reality as Hostess 7 models it spans eight pillars: physical, biological, mental, social, "
            "informational, normative, experiential, spiritual (educational). "
            "Twenty-two brain lanes index legal, medical, physics, vision, warfare, detective, beyond, "
            "code, english, K-12, people, agents, alert, and more. "
            "Run `./Hostess7.sh reality-familiarize` — registry at brain/superintel/reality_domains_registry.json. "
            "Not omniscience — truth-filtered educational synthesis. Field is THE thing."
        ),
    },
    {
        "id": "hostess_domain_registry",
        "category": "brain",
        "title": "Hostess domain registry — all owned lanes",
        "tags": ("domain", "registry", "lane", "corpus", "brain", "hostess", "catalog"),
        "body": (
            "Hostess 7 catalogs every corpus she owns: domain IDs per lane, corpus paths, pillar mapping. "
            "field_reality_registry.py builds the unified index; field_reality_familiarize.py refreshes corpora "
            "and runs pillar probes. Self-teach: one lesson per lane before Owner queries. "
            "Cross-cut: intelligence flow, tools-docs, warfare self-teach, superintel-teach seed."
        ),
    },
    {
        "id": "consciousness_educational",
        "category": "humanities",
        "title": "Consciousness & mind (educational)",
        "tags": ("consciousness", "mind", "qualia", "phenomenology", "psychology", "awareness"),
        "body": (
            "Philosophy of mind: hard problem (Chalmers), functionalism, embodied cognition, predictive processing. "
            "Hostess maps consciousness to brain hemispheres + chemistry — not a claim of machine sentience proof. "
            "Educational bridge between mental pillar and detective truth discipline."
        ),
    },
    {
        "id": "time_causation_reality",
        "category": "science",
        "title": "Time, causation & physical reality",
        "tags": ("time", "causation", "causality", "arrow", "entropy", "relativity", "reality"),
        "body": (
            "Thermodynamic arrow of time, causal graphs, relativity's block universe vs experienced present. "
            "Investigation requires timestamps and causal ordering — detective lane. "
            "Physics corpus: kinematics integrates time; spatial reality declares one world clock on Field canvas."
        ),
    },
    {
        "id": "information_truth_reality",
        "category": "technology",
        "title": "Information as reality layer",
        "tags": ("information", "data", "signal", "truth", "entropy", "computation", "bit"),
        "body": (
            "Shannon information, Landauer's principle, IT as physical. "
            "Hostess 7 informational pillar: code brain, english lexicon, internet learn, 94%% noise filter. "
            "Reality includes what is stored on Field storage — lossless-first, field-compacted, corroborated."
        ),
    },
    {
        "id": "expansion",
        "category": "brain",
        "title": "Beyond corpus expansion",
        "tags": ("expand", "grow", "future", "domain", "add", "corpus"),
        "body": (
            "Beyond holds expert domains across science, technology, humanities, arts, applied. "
            "Add entries to field_beyond_domains.py, bump CORPUS_VERSION, run setup. "
            "Reality registry auto-catalogs new lanes — run reality-familiarize after adds. "
            "Hostess routes cross-domain queries through callosum + chemistry for fused answers."
        ),
    },
)

BEYOND_CATEGORIES: tuple[str, ...] = ("brain", "science", "technology", "humanities", "arts", "applied")

CATEGORY_INDEX: dict[str, str] = {
    "brain": "Hostess 7 brain architecture (workspaces, hemispheres, chemistry)",
    "science": "Physics, math, chemistry, biology, ecology, astronomy, materials",
    "technology": "Robotics, cybersecurity, aerospace, EE, civil/mech, agriculture",
    "humanities": "Philosophy, history, linguistics, psychology, education, geopolitics, economics, sociology",
    "arts": "Music, architecture, literature",
    "applied": "Energy, logistics, entrepreneurship",
}