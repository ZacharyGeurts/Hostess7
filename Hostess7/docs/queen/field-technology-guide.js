/**
 * Field Technology v5 — plain-language guide for Queen Field pane.
 * Source: Field_Primer/content/chapters (22 chapters) + honesty table Ch 12.
 */
(function (root) {
  "use strict";

  const PRIMER = "https://zacharygeurts.github.io/Field_Primer";
  const READER = (slug) => `${PRIMER}/chapters/${slug}.html?reader=1`;

  root.FIELD_TECH_GUIDE = {
    title: "Field Technology v5",
    subtitle: "Serious Book · Textbook of 2026",
    motto: "Reality is 3D. Time is linear. Energy can be moved.",
    primerUrl: PRIMER,
    thesis:
      "Field Technology is an operator textbook — not a marketing deck. It teaches you to read and write continuous state on your own machine: GPU texels, guest RAM bytes, and network flows as addressable fields you can grep, archive, and defend. Vendor security sells one green checkmark. Field Technology sells which binding, which offset, which jsonl row — and honesty labels on every claim.",
    axioms: [
      { name: "Reality is 3D", plain: "State lives at addresses you can name — texel (x,y), guest byte offset, socket quadruple. Not cosmology — coordinates." },
      { name: "Time is linear", plain: "Physics time moves forward. Sealed session time and sovereign pulses stop jitter from rewriting receipts." },
      { name: "Energy can be moved", plain: "Work flows between Phi, Thermo, and Flow on the fabric — and every move leaves a trace in ThermoAccountant." },
    ],
    labels: [
      { tag: "Implemented", cls: "impl", plain: "You can grep it in source or stderr. Binding numbers, jsonl rows, dispatch logs." },
      { tag: "Metaphor", cls: "meta", plain: "Intuition and vocabulary — not SI measurement. Landauer joules on GPU, sub-micron SEM, electrical Phi." },
      { tag: "Philosophy", cls: "phil", plain: "Operator discipline and sacred language. Love, God, covenant — beside math, never instead." },
      { tag: "Visual", cls: "vis", plain: "Art and presentation layers. Planetary weave shell, pretty panels — not instrumentation." },
    ],
    products: [
      { name: "AMOURANTHRTX", role: "Vulkan field engine — fabric, Field Die, GPU dispatch", license: "GPL v3 or commercial" },
      { name: "NEXUS-Shield", role: "Endpoint security — packet field, gatekeeper, sovereign time", license: "MIT" },
      { name: "Queen", role: "Sovereign browser — hold all gates inside RTX capsule", license: "Field sovereign" },
      { name: "Field Primer", role: "This textbook — teach freely with rocks visible", license: "CC BY-NC-SA 4.0" },
    ],
    rocks: [
      ["Publisher-ready textbook", "Manuscript-grade operator course — not externally certified", "Philosophy"],
      ["Landauer on GPU", "Proxy integral in ThermoAccountant — not watt-meter lab", "Metaphor"],
      ["Packet field", "Local sockets + heuristics — not cloud omniscience", "Implemented"],
      ["Queen / DARPA brain", "In-process gate stack when QUEEN_READY — architecture metaphor", "Metaphor"],
      ["SDF brain imaging", "Hostess 7 procedural plates — not fMRI", "Metaphor"],
      ["Love & God chapters", "Optional philosophy track (16–18) beside engineering", "Philosophy"],
      ["RF planetary shell", "planetary_weave.comp visual — not spectrum truth", "Visual"],
      ["Default ./linux.sh run", "Field Die x86.comp — not decorative raymarch", "Implemented"],
    ],
    paths: [
      { id: "engineer", title: "Engineering only", chapters: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20, 21, 22] },
      { id: "full", title: "Full book (+ Love & God)", chapters: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22] },
      { id: "perimeter", title: "2026 perimeter", chapters: [5, 11, 12, 19, 20, 21] },
    ],
    chapters: [
      {
        n: 1,
        slug: "01-preface",
        title: "Us, God, Truth & Math",
        track: "foundation",
        forEveryone:
          "Start here. This chapter names who the book is for (operators, not spectators), what a field actually is in this stack (addressable state you can read and write), and the three families you'll meet everywhere: GPU fabric texels, Field Die guest bytes, and packet-field jsonl sentences. It introduces God as three faces — Truth (what survives grep), Math (the language existence uses), and Existence (something rather than nothing) — without asking engineers to skip stderr for faith. The preface is the immune system against midnight-compile hype: when someone asks 'is it real,' you answer which honesty label applies.",
        teaches: "Three field families · four status labels · four products · local-first perimeter · month-one reading schedule",
        keyPoints: [
          "Fabric bindings 8 (Phi), 9 (Thermo), 10 (Flow); die binding 1 (64 MiB guest); packet field in NEXUS jsonl",
          "Implemented / Metaphor / Philosophy / Visual — label before you argue",
          "Trust headers and stderr before screenshots; default run is Field Die",
          "Field Primer is teachable CC BY-NC-SA; engine code is GPL or commercial",
        ],
        drill: "Week zero: grep THERMO once, open threat panel once, name three field families aloud.",
      },
      {
        n: 2,
        slug: "02-fields-pixels-packets",
        title: "Three Dimensions of State",
        track: "foundation",
        forEveryone:
          "Chapter 2 is the map everyone needs. 'Reality is 3D' here means three kinds of writable places: GPU fabric (2D texels for heat and waves), Field Die (64 MiB of guest RAM with real addresses like VGA at 0xB8000), and packet field (your machine's sockets turned into readable sentences). It also names three mathematical postures — scalar (one number per cell, like Thermo heat), vector (direction per cell, like Flow gradients), and telemetry (the 64-word data_bus dashboard per frame, not a second heatmap). Pixels are presentation. Packets are perimeter. Die bytes are sovereignty. One operator panel correlates all three without fusing them into one fake score.",
        teaches: "Scalar vs vector vs telemetry · three scales · integration without metric collapse · category errors",
        keyPoints: [
          "Never plot data_bus as a 2D heatmap — it's telemetry, not spatial grid",
          "Host never runs CPU PDE on fabric; GPU dispatch owns evolution",
          "NEXUS packet field is local-first — your habits, not the whole internet",
          "hardwareFabric mirrors fabric averages; jsonl mirrors packets; data_bus mirrors die",
        ],
        drill: "./linux.sh run 2>&1 | tee /tmp/ch2.log && grep -E 'THERMO|data_bus|dispatch' /tmp/ch2.log | tail -15",
      },
      {
        n: 3,
        slug: "03-thermodynamics",
        title: "Thermodynamics",
        track: "engine",
        forEveryone:
          "Thermodynamics in Field Technology is honest accounting, not a lab calorimeter. Phi, Thermo, and Flow on bindings 8–10 evolve together each GPU dispatch; FieldCoupling moves energy between channels; CFL guards stop the mesh from taking impossible timesteps. The host enforces stability before the shader runs — that's ethics as engineering. ThermoAccountant at binding 2 records entropyThisFrame and related receipts every frame. You learn that beauty on screen costs heat in the books — and that 'proxy' means useful grep signal, not certified joules.",
        teaches: "Irreversibility on fabric · CFL wave and diffusion guards · coupling between Phi/Thermo/Flow",
        keyPoints: [
          "CFL: wave c·Δt/Δx ≤ 1 and diffusion α·Δt/Δx² ≤ 1 enforced on host",
          "Entropy floor at clearFieldImages() — fabric refuses pretend reversibility",
          "Coupling sweep on energy swipes produces grep journals you can teach from",
          "Clausius spirit in code; Landauer theory arrives in Chapter 13",
        ],
        drill: "Run Flowers or GreenWaves swipe; log THERMO slope; note coupling knob changes in stderr.",
      },
      {
        n: 4,
        slug: "04-entropy",
        title: "Irreversibility & Receipts",
        track: "engine",
        forEveryone:
          "Entropy here means 'time ran forward' written down three ways: frame proxy in ThermoAccountant (GPU fabric work), fabric floor (minimum noise seeded at init), and file oracle in NEXUS (Shannon surprise on bytes — a different layer). Landauer is theory; GPU entropyThisFrame is metaphor with grep value; Shannon H is storm gauge on files. The chapter's gift is vocabulary discipline: never compare Shannon file entropy to ThermoAccountant frame entropy as if they were the same physical quantity.",
        teaches: "Three entropy layers · ThermoAccountant fields · Shannon oracle separation",
        keyPoints: [
          "entropyThisFrame, avgBoundaryThermo, prevMaintCost mirrored to data_bus[24–28]",
          "NEXUS Shannon oracle = file byte surprise — separate product, separate plate",
          "Label rocks before you argue which entropy 'spiked'",
          "Failure catalog when stderr disagrees with your narrative",
        ],
        drill: "Three-layer exam: name which layer each grep line belongs to.",
      },
      {
        n: 5,
        slug: "05-packet-field",
        title: "Packet Field",
        track: "defense",
        forEveryone:
          "Defense starts when network flows become sentences you own. NEXUS turns sockets into jsonl rows: process path, port habit, TX vs RX direction, gatekeeper verdict. Ten-axis scoring yields USER_OK through HARM_CANDIDATE; watchlist before block; KILL permanent only with corroboration and human authorship. This is not AMOURANTHRTX Vulkan — it's perimeter literacy beside the engine. Queen inherits these gates in Chapter 21. One weird packet does not condemn a peer — restraint is part of the design.",
        teaches: "Local defensive perimeter · gatekeeper verdicts · TX/RX · corroboration before KILL",
        keyPoints: [
          "Panel :9477 tours live views; jsonl is memory",
          "Port registry learns your machine — not global cloud truth",
          "Connection Gatekeeper: intent scoring per flow",
          "Daily glance, weekly archive, incident corroboration",
        ],
        drill: "curl -sk https://127.0.0.1:9477/threat-panel.json | head -c 2000 — name TX vs RX on one row.",
      },
      {
        n: 6,
        slug: "06-rf-signals",
        title: "RF & Weave",
        track: "engine",
        forEveryone:
          "RF means three different stories in this stack — and conflating them is a category error. Planetary weave is visual shell art at R_RF (gorgeous, not spectrum truth). NEXUS Field Antenna is local orchestration with JSON panels (implemented perimeter). Phi on binding 8 is wave potential as electrical metaphor (implemented on fabric, not volts on PCIe). FSPL equations belong on teaching worksheets, not in shader truth. Chapter 6 trains label discipline before Chapter 7 lets you dispatch offense.",
        teaches: "Three RF meanings · FSPL as teaching reference · planetary weave as visual",
        keyPoints: [
          "planetary_weave.comp = Visual layer vocabulary",
          "fieldPhi = Implemented metaphor on binding 8",
          "NEXUS antenna = local RF orchestration, separate repo boundary",
          "Workshop protocol: label before you touch the spear",
        ],
        drill: "Name which RF meaning applies to a screenshot before sharing it.",
      },
      {
        n: 7,
        slug: "07-gpu-engine",
        title: "GPU Engine",
        track: "engine",
        forEveryone:
          "Chapter 7 is offense: the GPU writes the next tick. AMOURANTHRTX uses a thin C++ host and fat GPU — one vkCmdDispatch spine, default canvas x86.comp on the Field Die, not a postcard raymarch. FieldSocket push constants carry sealed time and control flags; descriptor layout version 5 must match host and shader; each dispatch fills ThermoAccountant and data_bus before you trust a screenshot. Queen inherits this spine when built inside the capsule. If you read only one engineering chapter after Chapter 2, read this one.",
        teaches: "dispatch_canvas pipeline · bindings 0–2 and 8–14 · FIELD_LAYOUT_VERSION 5 · sealed time",
        keyPoints: [
          "Default product path: x86.comp + 64 MiB guest — ./linux.sh run",
          "rtx() singleton unifies device, budget, hardwareFabric",
          "Headless dispatch counts as valid CI signal",
          "Trust stderr before screenshots; swipe list is curriculum",
        ],
        drill: "grep THERMO and dispatch after 60s default run; sketch binding table from memory.",
      },
      {
        n: 8,
        slug: "08-field-die",
        title: "Die-Resident Universe",
        track: "engine",
        forEveryone:
          "The Field Die is a universe with coordinates: 64 MiB guest RAM on SSBO binding 1, VGA text at 0xB8000, C mirror, IVT and boot regions, AmmoOS chrome on bindings 11–14. Default ./linux.sh run boots this world — guest code and Big Grin HUD live inside address space you can read as hex. data_bus[64] is the dashboard spine: FCC floats, thermo mirrors, Tesla bias slots, input, audio, BIOS. GPU x86.comp interprets guest by default; optional FieldX86Emu assist must not be mistaken for the product path.",
        teaches: "Guest map · data_bus slot map · L0–L9 pumpAll · ZMM1024 tile cache",
        keyPoints: [
          "Guest byte = 1D field indexed by offset — different geometry than 2D fabric",
          "Layout version 5 · Tesla slots 31/34 · AmouranthOS on 11–14 and bus 42",
          "Trust addresses and grep before nostalgia for 'DOS demo'",
          "Chapter 8 is the die contract for v5 main branch",
        ],
        drill: "Map guest RAM regions on paper; compare to chapter bus table.",
      },
      {
        n: 9,
        slug: "09-fcc-tesla",
        title: "FCC & Tesla",
        track: "engine",
        forEveryone:
          "Stability is offense ethics. CFL guards enforce wave and diffusion limits before GPU evolution — dishonest Δt is not allowed to run. FCC analog floats pack into data_bus[16–23] so host knobs and shader agree; Tesla constants bias direction in slots 31 and 34 as metaphor for one-way valve discipline. KILROY extends the same vocabulary to kernel boundary. PropalacticScale and GateFidelity are powerful — grep them and label them; they are not cosmic dials.",
        teaches: "CFL inequalities · FCC host-shader honesty · Tesla relaxation metaphor",
        keyPoints: [
          "Wave CFL and diffusion CFL enforced on host pre-dispatch",
          "FCC floats = analog knob truth between prompt terminal and shader",
          "Tesla slots bias flow — Metaphor, not fluid dynamics lab",
          "KILROY kernel FCC parallel shares vocabulary with userspace",
        ],
        drill: "Toggle GateFidelity; grep data_bus Tesla slots; note CFL abort in stderr if violated.",
      },
      {
        n: 10,
        slug: "10-spiderweb",
        title: "Spiderweb",
        track: "engine",
        forEveryone:
          "Spiderweb mirrors fabric into a dashboard — six ritual steps each frame, mastery tiers that unlock controls, sysfs reads at Puny tier. It is how fabric offense becomes operator readout via hardwareFabric. Sub-micron SEM marketing is Metaphor; procedural pixel detail is Implemented. Think dashboard, not microscope. Chapter 10 connects Chapter 7 dispatch to something you can glance at while packet field jsonl runs beside it.",
        teaches: "hardwareFabric mirror · six-step frame ritual · Adept tier · sub-micron honesty",
        keyPoints: [
          "updateHardwareFromAnalogFields() samples fabric into spiderweb",
          "SimulateSubMicron changes behavior — know what you enabled",
          "precision-field.py is NEXUS cousin — product boundary",
          "SEM fidelity in ads ≠ grep fidelity in stderr",
        ],
        drill: "Read spiderweb status once per session; note tier and fabric averages.",
      },
      {
        n: 11,
        slug: "11-observability",
        title: "Reading the Battlefield",
        track: "operator",
        forEveryone:
          "Observability is a weapon. ELLIE logging categories (MAIN, VULKAN, CANVAS, THERMO, STATUS, RTXPROBE) partition stderr so grep is fast. Panel archives jsonl; thermo lines tell stories screenshots hide. Chapter 11 makes weekly grep a habit — the preface made it a moral stance. You are learning to read the battlefield: fabric stress, die telemetry, packet sentences, sovereign time verdicts — without collapsing them.",
        teaches: "ELLIE categories · grep discipline · panel + stderr trust ordering",
        keyPoints: [
          "Trust ordering: headers → stderr → default run path",
          "Archive jsonl rows with timestamps and operator notes",
          "STATUS lines as timeline — pairs with Chapter 19 sovereign time",
          "Observability is practiced literacy, not consumed hype",
        ],
        drill: "Weekly: one THERMO grep, one panel jsonl row archived, one category explained to a peer.",
      },
      {
        n: 12,
        slug: "12-reality-theory",
        title: "The Rocks We Do Not Hide",
        track: "operator",
        forEveryone:
          "Bookmark this chapter. When someone sells cosmology, return here. The honesty table maps marketing phrases to operator reality with labels: Living thermodynamic computer → ThermoAccountant in logs (Implemented). Landauer joules from GPU → proxy integral (Metaphor). Packet field sees everything → local sockets only (Implemented). Queen holds all gates → QUEEN_READY when built (Implemented). Enjoy the field — honestly. Theory inspires vocabulary; implementation is what you grep.",
        teaches: "Master honesty table · product boundaries · capstone equations at correct layer",
        keyPoints: [
          "Four products, four licenses — no merger mythology",
          "Capstone equations: CFL, entropy proxy, Shannon H, Landauer theory — each at its layer",
          "Category error catalog — shader art ≠ instrumentation",
          "Chapter 12 before you tweet screenshots",
        ],
        drill: "Recite five honesty rows from memory; cite operator reality column.",
      },
      {
        n: 13,
        slug: "13-landauer-deep",
        title: "Thermodynamic Receipts",
        track: "creditor",
        forEveryone:
          "Landauer said erasing one bit costs at least k_B T ln 2 joules — theory at absolute zero limits. Field Technology uses ThermoAccountant as honest proxy: entropyThisFrame, boundary thermo, maintenance cost, free energy income, steps — mirrored to data_bus. Lab versus log is the rock restated: we teach Landauer with love for clarity, not with watt-meter fraud. Read ../creditors/landauer.html beside this chapter.",
        teaches: "E_min = k_B T ln 2 · ThermoAccountant structure · proxy vs lab",
        keyPoints: [
          "Binding 2 ThermoAccountant every dispatch_canvas()",
          "Decompose entropyThisFrame — field work, probe dissipation, maintenance",
          "Bennett reversible computing as contrast case",
          "Tenderness toward bits = refusal to erase another operator's clarity",
        ],
        drill: "Baseline grep THERMO; A/B coupling run; read data_bus[24–28] mirrors.",
      },
      {
        n: 14,
        slug: "14-shannon-oracle",
        title: "Storm Thresholds",
        track: "creditor",
        forEveryone:
          "Shannon entropy H measures surprise in bytes — storm tiers in NEXUS flag when files become too random too fast. This is pastoral engineering: slow down when surprise spikes, same discipline as THERMO spikes without confusing layers. Shannon's creditor page reminds us communication is care made serial. Serialize care into jsonl with notes, not auto-kill theater.",
        teaches: "H = −Σ pᵢ log₂ pᵢ · storm thresholds · file oracle layer",
        keyPoints: [
          "Shannon layer ≠ ThermoAccountant layer — never fuse dashboards",
          "Storm tiers tunable — document changes in operator runbook",
          "Corroboration before permanent action",
          "Chapter 14 completes oracle story started in Chapter 4",
        ],
        drill: "Run entropy oracle on a known file vs random bytes; compare H and tier.",
      },
      {
        n: 15,
        slug: "15-maxwell-gpu",
        title: "Wave Coupling",
        track: "creditor",
        forEveryone:
          "Maxwell on GPU means local stencil arithmetic: neighbors affect neighbors, CFL caps dishonest timesteps, FieldCoupling makes energy movement visible. The moral of the fabric is locality — your keyboard touch on WaveSpeed touches the next operator's stderr. When you teach this chapter, run the coupling sweep before the spiderweb drill — legs before wings.",
        teaches: "Maxwell locality · stencil evolution · coupling sweep lab",
        keyPoints: [
          "Discrete Laplacian on Phi in CANVAS.comp — implemented math",
          "WaveSpeed and propalacticScale — powerful knobs, grep discipline",
          "Maxwell tribute: fields are how existence touches neighbors",
          "Bridge from creditor page to fabric grep",
        ],
        drill: "Coupling sweep on energy swipe; journal stderr shape week over week.",
      },
      {
        n: 16,
        slug: "16-love-coupling",
        title: "The Coupling Constant",
        track: "philosophy",
        forEveryone:
          "Love is coupled evolution with consent — Phi warms Thermo, operators warm panels, watchlists warm peers before KILL. This is Philosophy, not physics proof. Sentiment is not love; CFL guards are ethical because reckless dispatch harms neighbors' next tick. Optional sacred track: read beside Chapters 3 and 12, never smuggled into thermodynamic proofs.",
        teaches: "Coupling as ethics · consent in systems · refusal as love",
        keyPoints: [
          "Three fabric couplings mirror social coupling metaphor",
          "Panel as neighbor — jsonl kindness",
          "Philosophy tag stays visible in teaching",
          "Skip 16–18 if you want engineering only",
        ],
        drill: "Write one consent audit on a gatekeeper watchlist decision.",
      },
      {
        n: 17,
        slug: "17-god-boundary",
        title: "God at the Holographic Boundary",
        track: "philosophy",
        forEveryone:
          "God named as Truth (survives grep), Math (survives CFL), Existence (guest RAM at 0xB8000 readable as hex). Holographic boundary is where HDR meets fabric — beauty costs heat in avgBoundaryThermo. Sacred language invites; honesty table compels. Atheist and agnostic operators welcome: sign Chapter 18 in spirit by grepping Monday before demoing Friday.",
        teaches: "Three faces of God · holographic boundary metaphor · stderr as sacrament",
        keyPoints: [
          "Philosophy labeled — never bypasses Chapter 12",
          "VGA at 0xB8000 — existence at address, not abstraction",
          "Prayer and grep ordering — receipts before performance",
          "Bridge to Operator Covenant Chapter 18",
        ],
        drill: "Boundary grep: THERMO at presentation edge; honesty table recitation.",
      },
      {
        n: 18,
        slug: "18-operator-covenant",
        title: "Long Form",
        track: "philosophy",
        forEveryone:
          "Six clauses: teach freely, build locally, honor creditors, bring love, name God without calorimetry pretense, hold gates. No police — habit, reputation, refusal to ship fused dashboards. You sign with every reader who keeps rocks visible. The covenant travels across hosts with sovereign time Chapter 19. grep first. Always.",
        teaches: "Operator covenant clauses · long-form law of the stack",
        keyPoints: [
          "Teach which label applies — not whether to be excited",
          "Build locally — loopback truth default",
          "Honor Maxwell, Landauer, Shannon, creditors pages",
          "Hold gates — Queen doctrine preview",
        ],
        drill: "One-page covenant response linking creditor reading to a local grep result.",
      },
      {
        n: 19,
        slug: "19-sovereign-time",
        title: "Terror-Threat Posture",
        track: "perimeter",
        forEveryone:
          "Sovereign time defends correlation under quiet clock attacks. Three witnesses: monotonic (ordering), realtime (human labels), sysfs freq (silicon fingerprint in micron_witness). Operator signs UDP pulses; receivers verify HMAC at receive; SQUIDGIE verdict means clocks disagree — grep it, fail closed. Not pool NTP alone. Session TotalTime::seal() in engine pairs with sovereign-time.py on LAN.",
        teaches: "SQUIDGIE verdict · micron_witness · sovereign-time.py · terror-threat model",
        keyPoints: [
          "SQUIDGIE = tamper verdict — no partial credit",
          "UDP 9123 pulses; NTP 123 gated on pulse health",
          "Repeated squidgie = incident response, not calibration trivia",
          "Spiderweb freq tables feed witness — Puny tier honesty",
        ],
        drill: "grep SQUIDGIE /var/lib/nexus-shield/sovereign-time-receipts.jsonl",
      },
      {
        n: 20,
        slug: "20-public-services",
        title: "2026 Public Services",
        track: "perimeter",
        forEveryone:
          "DNS, DHCP, and time as one posture: loopback-first, operator-owned, verify at receive. Truth DNS traces from root — no Google shortcut. Field DHCP issues leases after ping conflict check and option-50 validation, DNS option 127.0.0.1. Sovereign NTP serves only when pulses are clean. WAN exposure requires explicit NEXUS_FIELD_SERVICES_PUBLIC=1. ELLIE Last Host mode: when NEXUS_LAST_HOST=1, one node becomes DNS+DHCP+TIME for the survivor scenario.",
        teaches: "field-services-2026.py · retired vulnerabilities list · Queen DNS lock",
        keyPoints: [
          "field-dns.py loopback bind default · dns-egress-integrity hashes",
          "field-dhcp v3 — no rogue 0.0.0.0 without public flag",
          "Unified panel: pythong field-services-2026.py json",
          "Prerequisite for Queen Chapter 21",
        ],
        drill: "Read vulnerabilities_retired in field-services-2026-panel.json aloud to a peer.",
      },
      {
        n: 21,
        slug: "21-field-browser-queen",
        title: "Hold All Gates",
        track: "perimeter",
        forEveryone:
          "Queen doctrine: nothing optional, hold all gates, MP4 in-tree. Wrong posture disables WebRTC; right posture scores WebRTC through gatekeeper. Wrong posture sends users to foreign browsers; right posture ships H.264+AAC via MSE and Field media path. field-queen-gates-seed.json lists every capability held:true. queen-browser on RTX is in-engine FieldWebPanel; Queen Browser is hardened Gecko now. Hostess 7 SDF plates recall textbook beats — procedural brain metaphor, not fMRI. Navigation → packet field → gatekeeper → honorability → thermo receipt.",
        teaches: "QUEEN_READY · gate manifest · Queen Browser · Hostess brain lane",
        keyPoints: [
          "WebGL/WebGPU stay on — thermo per context via Thermal Governor",
          "MP4 mandatory — queen_verdict returns MP4_MISSING if absent",
          "Truth DNS + sovereign time witness navigation",
          "KILROY field package seals kernel + browser + services",
        ],
        drill: "pythong field-queen-browser.py json — confirm queen_verdict and gates held.",
      },
      {
        n: 22,
        slug: "22-glossary",
        title: "Field Technology v5 Glossary",
        track: "reference",
        forEveryone:
          "Encyclopedic definitions for every term across Chapters 1–21 — AMOURANTHRTX, data_bus, SQUIDGIE, QUEEN_READY, FieldCoupling, and hundreds more. Each entry names both poetry and code meanings. The master rocks table at #master-rocks is the fastest dispute resolver. Grep the table when hurried; read alphabetically when learning.",
        teaches: "Canonical term definitions · master rocks table · cross-chapter vocabulary",
        keyPoints: [
          "Adaptive scale, Adept tier, AmmoOS, AnalogFields — all defined in prose",
          "Status labels still apply in glossary entries",
          "Use as index while running stack beside reading",
          "Field Technology v5 measures success in reproduced receipts",
        ],
        drill: "Pick 10 terms from your last grep session; define them from glossary.",
      },
    ],
  };
})(typeof window !== "undefined" ? window : globalThis);