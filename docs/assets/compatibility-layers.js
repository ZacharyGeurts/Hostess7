(function () {
  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function log(line) {
    const el = $("cl-log");
    if (!el) return;
    const ts = new Date().toLocaleTimeString();
    el.textContent = `[${ts}] ${line}\n` + el.textContent;
  }

  function setBusy(busy) {
    document.querySelectorAll(".cl-actions button").forEach((b) => {
      b.disabled = busy;
    });
    const badge = $("cl-badge");
    if (badge) badge.textContent = busy ? "Syncing…" : "Auto stack";
  }

  function renderStack(doc) {
    const stack = $("cl-stack");
    if (!stack) return;
    const layers = doc.layers || [];
    stack.innerHTML = layers
      .map((layer) => {
        const live = layer.live !== false && layer.ok !== false;
        const color = layer.color || "#94a3b8";
        return `
          <article class="cl-layer ${live ? "live" : "off"}" style="--layer-color: ${esc(color)}">
            <span class="cl-layer-glyph" aria-hidden="true">${esc(layer.glyph || "·")}</span>
            <div class="cl-layer-head">
              <div>
                <span class="cl-layer-index">L${layer.index ?? "?"}</span>
                <div class="cl-layer-label">${esc(layer.label)}</div>
              </div>
              <span class="cl-layer-pill ${live ? "on" : "off"}">${live ? "live" : "pending"}</span>
            </div>
            <p class="cl-layer-summary">${esc(layer.summary || "—")}</p>
          </article>`;
      })
      .join("");
  }

  function renderEffective(doc) {
    const grid = $("cl-effective-grid");
    if (!grid) return;
    const eff = doc.effective_profile || {};
    const tiles = [
      ["Pattern", eff.pattern_id || "—"],
      ["Belt", eff.belt_profile || "—"],
      ["Die slots", eff.die_slots ?? "—"],
      ["Runner", eff.runner || "—"],
      ["Ideal profile", eff.ideal_profile || "—"],
      ["Always optimal", eff.always_optimal ? (eff.degraded_gate ? "yes · gate degraded" : "yes") : "—"],
      ["Layers live", `${doc.live_layers ?? 0} / ${doc.total_layers ?? 6}`],
      [".launch seal", doc.launch_seal?.generation ?? "—"],
    ];
    grid.innerHTML = tiles
      .map(
        ([label, val]) =>
          `<div class="cl-eff-tile"><span>${esc(label)}</span><strong>${esc(String(val))}</strong></div>`
      )
      .join("");
  }

  async function loadStatus() {
    const res = await fetch("/api/compatibility");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const doc = await res.json();
    renderStack(doc);
    renderEffective(doc);
    return doc;
  }

  async function syncLayers(deep) {
    setBusy(true);
    log(deep ? "Deep refresh started…" : "Sync all layers…");
    try {
      const res = await fetch("/api/compatibility/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deep: !!deep }),
      });
      const doc = await res.json();
      renderStack(doc);
      renderEffective(doc);
      const refresh = doc.refresh || {};
      const steps = (refresh.steps || []).map((s) => s.step + (s.ok === false ? " ✗" : " ✓")).join(", ");
      const seal = doc.launch_seal?.generation;
      log(
        refresh.ok
          ? `Sync OK — ${steps || "layers updated"}${seal != null ? ` · .launch seal gen ${seal}` : ""}`
          : `Sync partial — ${steps || doc.error || "check log"}`
      );
    } catch (err) {
      log(`Sync failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  $("cl-sync")?.addEventListener("click", () => syncLayers(false));
  $("cl-deep")?.addEventListener("click", () => syncLayers(true));
  $("cl-reload")?.addEventListener("click", () => {
    setBusy(true);
    loadStatus()
      .then(() => log("Status reloaded"))
      .catch((e) => log(`Reload failed: ${e.message}`))
      .finally(() => setBusy(false));
  });

  loadStatus().catch((e) => {
    log(`Initial load: ${e.message}`);
    renderStack({ layers: [] });
  });
})();