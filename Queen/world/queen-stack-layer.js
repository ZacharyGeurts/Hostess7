/**
 * Queen — field stack layer strip (NEXUS C2 · ZNetwork · CANVAS · Queen · AmmoOS inside Queen).
 */
(function () {
  "use strict";

  function panelBase() {
    const port = document.body?.dataset?.nexusPanelPort || "9477";
    return `http://127.0.0.1:${port}`;
  }

  function $(id) {
    return document.getElementById(id);
  }

  function layerSummary(doc) {
    const layers = doc?.layers || [];
    const names = ["nexus_c2", "znetwork", "queen_canvas", "queen", "ammoos"];
    const bits = names.map((id) => {
      const row = layers.find((l) => l.id === id);
      const ok = row?.ok;
      const label = (row?.label || id).split(" ")[0];
      return `${ok ? "✓" : "·"} ${label}`;
    });
    return bits.join(" · ");
  }

  async function refresh() {
    const strip = $("qb-security-strip");
    if (!strip) return;
    try {
      const res = await fetch(`${panelBase()}/api/field-stack-layer`, { cache: "no-store" });
      const doc = await res.json();
      const hw = (doc.layers || []).find((l) => l.id === "hardware");
      const safe = doc.hardware_safe !== false && hw?.no_breaks !== false;
      strip.textContent = layerSummary(doc);
      strip.title = [
        doc.motto || "Field stack layers",
        safe ? "Hardware: no breaks" : "Hardware: check wire",
        doc.ammoos_inside_queen ? "AmmoOS inside Queen" : "AmmoOS placement check",
        "NEXUS C2 → ZNetwork → CANVAS → Queen → AmmoOS",
      ].join(" — ");
      strip.classList.toggle("qb-stack-ok", !!doc.ok);
      strip.classList.toggle("qb-stack-warn", !doc.ok);
    } catch {
      strip.textContent = "Stack offline";
      strip.title = "NEXUS C2 layer API unreachable — Queen still gate-held locally";
    }
  }

  function init() {
    if (document.body?.dataset?.queenSurface !== "browser") return;
    refresh();
    setInterval(refresh, 22000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();