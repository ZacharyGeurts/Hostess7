/**
 * EOL Code — Layer 0 BSP tree panel · self-running Ironclad generator witness.
 */
(function () {
  "use strict";

  const API = (function () {
    if (globalThis.H7Api) return globalThis.H7Api("/api/field-eol-code");
    return "/api/field-eol-code";
  })();

  const state = {
    panel: null,
    auto: false,
    autoTimer: null,
    lastGen: 0,
    expanded: new Set(),
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "panel" }),
      credentials: "same-origin",
      cache: "no-store",
    });
    const raw = await r.text();
    if (!raw.trim()) {
      return { ok: false, error: "empty_response", http_status: r.status, schema: "field-eol-code-panel/v1" };
    }
    try {
      const doc = JSON.parse(raw);
      if (!r.ok && doc.ok !== false) doc.ok = false;
      if (!r.ok) doc.http_status = r.status;
      return doc;
    } catch (_e) {
      return { ok: false, error: "bad_json", http_status: r.status, detail: raw.slice(0, 160) };
    }
  }

  function badge(status) {
    const s = status || "pending";
    return `<span class="eol-badge eol-badge--${esc(s)}">${esc(s)}</span>`;
  }

  function renderRuler(layers) {
    const el = $("eol-ruler");
    if (!el) return;
    el.innerHTML = (layers || [])
      .map((L) => {
        const z = L.z;
        const cls = z === 0 ? "z0" : z < 0 ? "neg" : "";
        return `<span class="${cls}">L${z} ${esc(L.label || L.id)}</span>`;
      })
      .join("");
  }

  function renderStats(summary, iron, gen) {
    const el = $("eol-stats");
    if (!el || !summary) return;
    el.innerHTML =
      `<span class="eol-stat">gen <strong>${gen || 0}</strong></span>` +
      `<span class="eol-stat">paths <strong>${summary.total_paths || 0}</strong></span>` +
      `<span class="eol-stat">EOL <strong>${summary.eol || 0}</strong></span>` +
      `<span class="eol-stat">not EOL <strong>${summary.not_eol_yet || 0}</strong></span>` +
      `<span class="eol-stat">dead end <strong>${summary.dead_end || 0}</strong></span>` +
      `<span class="eol-stat">cut cand. <strong>${summary.cut_candidates || 0}</strong></span>` +
      (iron
        ? `<span class="eol-stat">Ironclad <strong>${iron.sealed ? "sealed" : "watch"}</strong> ${iron.truth_percent || "—"}%</span>`
        : "");
  }

  function renderLayerBranch(branch, depth) {
    if (!branch) return "";
    const z = branch.layer;
    const collapsed = !state.expanded.has("L" + z);
    const head =
      `<div class="eol-layer-head" data-layer="${z}">` +
      `<span class="eol-layer-z${z < 0 ? " neg" : ""}">L${z}</span>` +
      `<span>${esc(branch.label)}</span>` +
      `<span class="eol-layer-meta">${branch.eol_count || 0} eol · ${branch.not_eol_count || 0} open · ${branch.dead_end_count || 0} dead</span>` +
      `</div>`;
    let nodes = "";
    if (!collapsed && branch.children && branch.children.length) {
      const show = branch.children.slice(0, 80);
      nodes =
        `<div class="eol-nodes">` +
        show
          .map(
            (n) =>
              `<div class="eol-node" title="${esc(n.path)}">` +
              badge(n.eol_status) +
              `<span class="eol-path">${esc(n.path || n.id)}</span>` +
              `<span class="eol-truth">${n.truth_percent || 0}% · e${n.edges || 0}</span>` +
              `</div>`,
          )
          .join("") +
        (branch.children.length > 80
          ? `<div class="eol-node eol-truth">… +${branch.children.length - 80} more (BSP sorted)</div>`
          : "") +
        `</div>`;
    }
    return `<div class="eol-layer">${head}${nodes}</div>`;
  }

  function renderTree(doc) {
    const el = $("eol-tree");
    if (!el) return;
    const root = doc.tree?.root;
    if (!root) {
      el.innerHTML = "<p class='eol-truth'>Scan pending…</p>";
      return;
    }
    if (!state.expanded.size) {
      (doc.layers || []).forEach((L) => state.expanded.add("L" + L.z));
    }
    el.innerHTML = (root.children || []).map((b) => renderLayerBranch(b, 0)).join("");
    el.querySelectorAll(".eol-layer-head").forEach((head) => {
      head.addEventListener("click", () => {
        const z = head.dataset.layer;
        const key = "L" + z;
        if (state.expanded.has(key)) state.expanded.delete(key);
        else state.expanded.add(key);
        renderTree(doc);
      });
    });
  }

  function renderLog(lines, isNew) {
    const el = $("eol-log");
    if (!el) return;
    const rows = (lines || []).slice(-60);
    el.innerHTML = rows
      .map((line, i) => {
        const cls = isNew && i >= rows.length - 5 ? " eol-log-line--new" : "";
        return `<p class="eol-log-line${cls}">${esc(line)}</p>`;
      })
      .join("");
    el.scrollTop = el.scrollHeight;
  }

  function renderWiring(wiring) {
    const el = $("eol-wiring");
    if (!el || !wiring) return;
    const gaps = wiring.gaps || [];
    const summary = wiring.summary || {};
    el.innerHTML =
      `<div class="eol-wiring-summary">` +
      `<span>paths <strong>${summary.code_paths || 0}</strong></span>` +
      `<span>wired <strong>${summary.wired || 0}</strong></span>` +
      `<span>gaps <strong>${summary.gap_count || gaps.length}</strong></span>` +
      `<span>icons miss <strong>${summary.missing_icons || 0}</strong></span>` +
      `<span>open-file <strong>${summary.open_file_dialogs || 0}</strong></span>` +
      `</div>` +
      gaps
        .slice(0, 120)
        .map(
          (g) =>
            `<div class="eol-wiring-row eol-wiring--${esc(g.kind || "gap")}">` +
            `<span class="eol-badge eol-badge--${esc(g.severity || "pending")}">${esc(g.kind || "gap")}</span>` +
            `<span class="eol-path">${esc(g.id || g.path || "")}</span>` +
            `<span class="eol-truth">${esc(g.hint || g.detail || "")}</span>` +
            `</div>`,
        )
        .join("");
  }

  function paint(doc, opts) {
    state.panel = doc;
    renderRuler(doc.layers);
    renderStats(doc.tree?.summary, doc.ironclad, doc.generation);
    renderTree(doc);
    renderWiring(doc.wiring);
    renderLog(doc.runtime?.log || [], opts && opts.newLog);
    if (globalThis.FieldRtxSmoothScroll) {
      FieldRtxSmoothScroll.wire($("eol-tree"), { infinite: true, wheelGain: 0.9 });
      FieldRtxSmoothScroll.wire($("eol-log"), { wheelGain: 0.85 });
      FieldRtxSmoothScroll.wire($("eol-wiring"), { wheelGain: 0.85 });
    }
    const gen = doc.generation || 0;
    if (gen !== state.lastGen) state.lastGen = gen;
  }

  async function refresh(refresh) {
    const doc = await api({ action: "panel", refresh: !!refresh });
    paint(doc, { newLog: false });
    return doc;
  }

  async function tick() {
    const doc = await api({ action: "tick" });
    const panel = await api({ action: "panel" });
    paint(panel, { newLog: true });
    if (doc.log && doc.log.length) {
      renderLog((state.panel?.runtime?.log || []).concat(doc.log), true);
    }
    return doc;
  }

  async function runBatch() {
    const doc = await api({ action: "run", ticks: 8 });
    await refresh(false);
    return doc;
  }

  function setAuto(on) {
    state.auto = on;
    const btn = $("eol-auto");
    if (btn) btn.classList.toggle("active", on);
    if (state.autoTimer) clearInterval(state.autoTimer);
    if (on) {
      state.autoTimer = setInterval(() => {
        tick().catch(() => {});
      }, 1200);
    }
  }

  function bind() {
    $("eol-tick")?.addEventListener("click", () => tick().catch((e) => renderLog([e.message], true)));
    $("eol-run")?.addEventListener("click", () => runBatch().catch((e) => renderLog([e.message], true)));
    $("eol-auto")?.addEventListener("click", () => setAuto(!state.auto));
    $("eol-refresh")?.addEventListener("click", () => refresh(true).catch((e) => renderLog([e.message], true)));
    $("eol-reset")?.addEventListener("click", async () => {
      await api({ action: "reset" });
      state.expanded.clear();
      state.lastGen = 0;
      await refresh(true);
    });
  }

  async function boot() {
    bind();
    try {
      await refresh(true);
      setAuto(true);
    } catch (e) {
      renderLog(["EOL generator boot: " + e.message], true);
    }
  }

  globalThis.FieldEolCode = { refresh, tick, runBatch, setAuto };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();