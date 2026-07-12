/**
 * Queen Root Threats HUD — sovereign guard + attack kit from /api/root-threats
 */
(function (global) {
  "use strict";

  const CACHE_KEY = "queen-root-threats-v1";
  const POLL_MS = 8000;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function paint(doc) {
    const bar = $("qm-threat-bar");
    if (!bar || !doc) return;
    const rs = doc.root_sovereign || {};
    const ak = doc.attack_kit || {};
    const kc = doc.kill_chain || {};
    const fv = doc.field_virus || {};

    const guardCls = rs.guard_live ? "qm-pill--armed" : "qm-pill--warn";
    const covenantCls = rs.covenant_sealed ? "qm-pill--ok" : "qm-pill--warn";

    bar.innerHTML = `
      <span class="qm-brand">ROOT THREATS</span>
      <span class="qm-pill ${guardCls}" title="Invisible root sovereignty guard">GUARD ${esc(rs.verdict || "…")}</span>
      <span class="qm-pill ${covenantCls}" title="Operator covenant">COVENANT ${rs.covenant_sealed ? "SEALED" : "OPEN"}</span>
      <span class="qm-pill qm-pill--armed" title="AUTOKILL at certainty">AUTOKILL ${esc(kc.autokill || "armed")}</span>
      <span class="qm-pill qm-pill--armed" title="RE-KILL cycle">RE-KILL ${esc(ak.rekill_hits || 0)}</span>
      <span class="qm-pill" title="Permanently disabled hosts">HOSTILE ${esc(ak.hostile_disabled || 0)}</span>
      <span class="qm-pill" title="Field virus gate">VIRUS ${esc(fv.verdict || "WATCH")}</span>
      <span class="qm-pill" title="Root kills with prejudice">KILLS ${esc(rs.kills_total || 0)}</span>
      <div class="qm-threat-actions">
        <button type="button" class="qm-btn" data-rt="audit">Audit root</button>
        <button type="button" class="qm-btn qm-btn--danger" data-rt="rekill">RE-KILL</button>
        <button type="button" class="qm-btn qm-btn--danger" data-rt="crush">Crush hot</button>
        <button type="button" class="qm-btn qm-btn--primary" data-rt="nexus">AmmoOS C2</button>
      </div>`;

    bar.querySelectorAll("[data-rt]").forEach((btn) => {
      btn.addEventListener("click", () => act(btn.getAttribute("data-rt")));
    });
  }

  function cacheRead() {
    try {
      const raw = sessionStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) {
      return null;
    }
  }

  function cacheWrite(doc) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(doc));
    } catch (_) {}
  }

  function fetchStatus() {
    return global.fetch("/api/root-threats", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }

  function postAction(action) {
    return global.fetch("/api/root-threats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    })
      .then((r) => (r.ok ? r.json() : { ok: false }))
      .catch(() => ({ ok: false }));
  }

  function act(kind) {
    if (kind === "nexus") {
      const port = 9477;
      const url = `http://127.0.0.1:${port}/field`;
      if (global.parent && global.parent !== global) {
        global.parent.postMessage({ type: "queen:shell", action: "new_tab", url }, global.location.origin);
      } else {
        global.location.href = url;
      }
      return;
    }
    const map = { audit: "audit_root", rekill: "rekill", crush: "crush_hot" };
    const action = map[kind];
    if (!action) return;
    const bar = $("qm-threat-bar");
    if (bar) bar.style.opacity = "0.7";
    postAction(action).then((out) => {
      if (bar) bar.style.opacity = "";
      if (out && out.ok !== false) refresh();
      const status = $("qb-status");
      if (status) status.textContent = out.ok ? `${action} complete` : `${action} failed`;
    });
  }

  function refresh() {
    return fetchStatus().then((doc) => {
      if (doc) {
        cacheWrite(doc);
        paint(doc);
      }
      return doc;
    });
  }

  function boot() {
    const cached = cacheRead();
    if (cached) paint(cached);
    refresh();
    setInterval(refresh, POLL_MS);
  }

  global.QueenRootThreats = { boot, refresh, paint };
})(window);