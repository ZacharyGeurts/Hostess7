/**
 * Hostess 7 AI Training Hub — neural lanes, sense wire, training surfaces.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const LANES = [
    { id: "training", title: "Training Viewer", hint: "Connected models graph · chambers", url: "http://127.0.0.1:9488/", api: null },
    { id: "brain", title: "Hostess Brain", hint: "Super intelligence · AI communique", url: "queen://hostess", api: "/api/field-brain" },
    { id: "guardian", title: "Neural Guardian", hint: "Truth · lie · deception discern", url: "http://127.0.0.1:9477/command#training", api: "/api/hostess7/training" },
    { id: "g16", title: "Grok16 Forever", hint: "Compiler · binutils · secure profiles", url: "queen://g16", api: "/api/power-sort" },
    { id: "pythong", title: "GPY-16 Runtime", hint: "pythong · PGVM · forge runtime", url: "queen://grokpy", api: null },
    { id: "growth", title: "Mastery & Growth", hint: "Facets · teach · assess", url: "http://127.0.0.1:9477/command#training", api: "/api/hostess7/training" },
  ];

  const SENSE = [
    { id: "eye", title: "Final_Eye · Vision NN", hint: "OCR · offense · encourage gate", url: "queen://eyeball", api: "/api/queen-eyeball" },
    { id: "ear", title: "Final Ear · Audio NN", hint: "Auditus · signal intel · GAC1", url: "/world/queen-final-ear-manager.html", api: "/api/queen-earball" },
    { id: "mouth", title: "Final Mouth · Voice NN", hint: "Loquor · GVC1 · thought-voice callosum", url: "/world/queen-final-mouth-manager.html", api: "/api/queen-mouthball" },
    { id: "wire", title: "Invincible Wire", hint: "Eye ↔ Ear ↔ Mouth quorum", url: "http://127.0.0.1:9477/api/sense-neural-wire", api: "/api/sense-neural-wire" },
    { id: "forge", title: "Queen Forge", hint: "Build deck · Hostess pipeline", url: "/gui/queen-build-deck.html", api: null },
  ];

  function panelPort() {
    return document.body?.dataset?.nexusPanelPort || "9477";
  }

  function panelBase() {
    return `http://127.0.0.1:${panelPort()}`;
  }

  async function fetchPanel(path) {
    const url = path.startsWith("http") ? path : `${panelBase()}${path.startsWith("/") ? path : `/${path}`}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path} HTTP ${res.status}`);
    return res.json();
  }

  function renderCards(container, items, statusMap) {
    if (!container) return;
    container.innerHTML = items
      .map((item) => {
        const st = statusMap[item.id] || {};
        const ok = st.ok !== false;
        return `<article class="qh7-card">
          <h3>${item.title}</h3>
          <p>${item.hint}${st.label ? ` · <em>${st.label}</em>` : ""}</p>
          <a href="${item.url}" target="_top">${ok ? "Open" : "Open (degraded)"} →</a>
        </article>`;
      })
      .join("");
  }

  async function refresh() {
    const status = $("qh7-status");
    if (status) status.textContent = "Loading neural posture…";
    const statusMap = {};
    try {
      const [brain, training, wire] = await Promise.all([
        fetchPanel("/api/field-brain").catch(() => ({})),
        fetchPanel("/api/hostess7/training").catch(() => ({})),
        fetchPanel("/api/sense-neural-wire").catch(() => ({})),
      ]);
      $("qh7-philosophy").textContent =
        brain.philosophy || brain.rule || "Truth-gated intelligence — adapt only above floor.";
      const floor = training.truth_adapt_floor || brain.truth_adapt_floor || 58;
      $("qh7-truth").textContent = `FLOOR ${floor}%`;
      $("qh7-metrics").innerHTML = [
        { label: "Truth floor", val: `${floor}%` },
        { label: "Series", val: String((brain.series || training.series || []).length || "—") },
        { label: "Sense wire", val: wire.ok !== false ? "held" : "open" },
      ]
        .map((m) => `<div class="qh7-metric"><strong>${m.val}</strong>${m.label}</div>`)
        .join("");
      statusMap.brain = { ok: brain.ok !== false, label: brain.schema || "" };
      statusMap.guardian = { ok: true, label: "discern" };
      statusMap.wire = { ok: wire.ok !== false, label: wire.schema || "" };
      $("qh7-ts").textContent = brain.updated || training.updated || new Date().toISOString();
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
    }
    renderCards($("qh7-lanes"), LANES, statusMap);
    renderCards($("qh7-sense"), SENSE, statusMap);
    if (status) status.textContent = "Live · Hostess 7 neural stack";
  }

  $("qh7-refresh")?.addEventListener("click", refresh);
  refresh();
})();