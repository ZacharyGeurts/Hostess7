/**
 * Queen Page Inspector — shell panel, element picker, shields manager.
 */
(function () {
  "use strict";

  const API = "/api/queen-page-shields";
  const state = {
    open: false,
    tab: "element",
    picker: false,
    selection: null,
    rules: [],
    activeFrame: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  function activeFrame() {
    const pane = document.querySelector(".qb-tab-pane.active");
    return pane?.querySelector(".qb-frame") || $("qb-frame");
  }

  function injectAgent(frame) {
    if (!frame?.contentDocument) return false;
    try {
      const doc = frame.contentDocument;
      if (doc.getElementById("queen-page-agent")) return true;
      const s = doc.createElement("script");
      s.id = "queen-page-agent";
      s.src = `${location.origin}/world/queen-page-agent.js`;
      s.async = false;
      doc.documentElement.appendChild(s);
      return true;
    } catch (_) {
      return false;
    }
  }

  function postToFrame(frame, msg) {
    try {
      frame?.contentWindow?.postMessage(msg, "*");
    } catch (_) {}
  }

  function ensureDrawer() {
    if ($("qpi-drawer")) return;
    const el = document.createElement("aside");
    el.id = "qpi-drawer";
    el.className = "qpi-drawer";
    el.setAttribute("aria-label", "Queen page inspector");
    el.innerHTML = `
      <header class="qpi-head">
        <h2>Page Inspector</h2>
        <button type="button" class="qpi-btn qpi-btn--rose" id="qpi-picker" title="Pick element (Ctrl+Shift+I)">Pick</button>
        <button type="button" class="qpi-btn" id="qpi-reload">Reload shields</button>
        <button type="button" class="qpi-btn" id="qpi-close" aria-label="Close">×</button>
      </header>
      <nav class="qpi-tabs" aria-label="Inspector views">
        <button type="button" class="qpi-tab on" data-tab="element">Element</button>
        <button type="button" class="qpi-tab" data-tab="styles">Styles</button>
        <button type="button" class="qpi-tab" data-tab="shields">Shields</button>
        <button type="button" class="qpi-tab" data-tab="dom">DOM</button>
      </nav>
      <div class="qpi-body">
        <section class="qpi-pane on" id="qpi-pane-element"></section>
        <section class="qpi-pane" id="qpi-pane-styles"></section>
        <section class="qpi-pane" id="qpi-pane-shields"></section>
        <section class="qpi-pane" id="qpi-pane-dom"></section>
      </div>
      <p class="qpi-status" id="qpi-status">Right-click any page · Never see ad space again</p>
    `;
    document.body.appendChild(el);
    el.querySelector("#qpi-close")?.addEventListener("click", () => toggle(false));
    el.querySelector("#qpi-picker")?.addEventListener("click", () => togglePicker());
    el.querySelector("#qpi-reload")?.addEventListener("click", () => reloadShields());
    el.querySelectorAll(".qpi-tab").forEach((btn) => {
      btn.addEventListener("click", () => setTab(btn.dataset.tab));
    });
  }

  function setTab(tab) {
    state.tab = tab;
    document.querySelectorAll(".qpi-tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
    document.querySelectorAll(".qpi-pane").forEach((p) => p.classList.toggle("on", p.id === `qpi-pane-${tab}`));
  }

  function toggle(on) {
    ensureDrawer();
    state.open = on !== undefined ? on : !state.open;
    $("qpi-drawer")?.classList.toggle("open", state.open);
    $("qpi-inspect-btn")?.classList.toggle("on", state.open);
    if (state.open) refreshRules();
  }

  function togglePicker() {
    state.picker = !state.picker;
    $("qpi-picker")?.classList.toggle("on", state.picker);
    const frame = activeFrame();
    state.activeFrame = frame;
    injectAgent(frame);
    postToFrame(frame, { type: "queen:page-agent", action: "picker", enabled: state.picker });
    $("qpi-status").textContent = state.picker
      ? "Click an element in the page to inspect"
      : "Picker off — right-click for context menu";
  }

  function reloadShields() {
    const frame = activeFrame();
    injectAgent(frame);
    postToFrame(frame, { type: "queen:page-agent", action: "reload_shields" });
    refreshRules();
  }

  async function refreshRules() {
    const frame = activeFrame();
    let host = "";
    try {
      host = new URL(frame?.contentWindow?.location?.href || frame?.src || location.href).hostname;
    } catch (_) {}
    const out = await api({ action: "list", host });
    if (out.ok) {
      state.rules = out.rules || [];
      renderShields();
      $("qpi-status").textContent = `${state.rules.length} shield rules · ${host || "page"}`;
    }
  }

  function renderSelection() {
    const sel = state.selection;
    const elPane = $("qpi-pane-element");
    const stPane = $("qpi-pane-styles");
    const domPane = $("qpi-pane-dom");
    if (!sel) {
      elPane.innerHTML = '<p class="qpi-empty">Right-click an element or use Pick mode.</p>';
      stPane.innerHTML = "";
      domPane.innerHTML = "";
      return;
    }
    const fp = sel.fingerprint || {};
    const rect = sel.rect || {};
    elPane.innerHTML = `
      <dl class="qpi-kv">
        <dt>Selector</dt><dd>${esc(sel.selector)}</dd>
        <dt>Tag</dt><dd>${esc(fp.tag)}</dd>
        <dt>Size</dt><dd>${Math.round(rect.width || fp.width_bucket || 0)}×${Math.round(rect.height || fp.height_bucket || 0)}</dd>
        <dt>Role</dt><dd>${esc(fp.role || "—")}</dd>
        <dt>Ad signals</dt><dd>${esc((fp.ad_signals || []).join(", ") || "none")}</dd>
        <dt>Path</dt><dd>${esc(fp.structural_path || "")}</dd>
      </dl>
      <div class="qpi-box-model">
        <span>x ${Math.round(rect.x || 0)}</span>
        <span>y ${Math.round(rect.y || 0)}</span>
        <span>w ${Math.round(rect.width || 0)}</span>
        <span>h ${Math.round(rect.height || 0)}</span>
      </div>
      <button type="button" class="qpi-btn" id="qpi-block-sel">Never see again</button>
      <button type="button" class="qpi-btn qpi-btn--rose" id="qpi-block-ad">Block ad space</button>
    `;
    elPane.querySelector("#qpi-block-sel")?.addEventListener("click", () => blockSelection(false));
    elPane.querySelector("#qpi-block-ad")?.addEventListener("click", () => blockSelection(true));

    const styles = [];
    if (fp.stable_classes?.length) styles.push(`classes: ${fp.stable_classes.join(" ")}`);
    if (fp.text_sample) styles.push(`text: ${fp.text_sample}`);
    stPane.innerHTML = `<pre class="qpi-pre">${esc(styles.join("\n") || "No computed styles from frame — use Pick on live page.")}</pre>`;
    domPane.innerHTML = `<pre class="qpi-pre">${esc(sel.html || "")}</pre>`;
  }

  async function blockSelection(adSpace) {
    const sel = state.selection;
    if (!sel) return;
    const frame = activeFrame();
    let url = frame?.src || "";
    try {
      url = frame?.contentWindow?.location?.href || url;
    } catch (_) {}
    const out = await api({
      action: adSpace ? "block_ad_space" : "block",
      url,
      selector: sel.selector,
      fingerprint: sel.fingerprint,
      ad_space: adSpace,
    });
    if (out.ok) {
      reloadShields();
      $("qpi-status").textContent = adSpace ? "Ad space blocked forever" : "Element blocked forever";
    }
  }

  function renderShields() {
    const pane = $("qpi-pane-shields");
    if (!state.rules.length) {
      pane.innerHTML = '<p class="qpi-empty">No shields yet — right-click ads → Never see ad space again.</p>';
      return;
    }
    pane.innerHTML = state.rules
      .map(
        (r) => `
      <div class="qpi-rule" data-id="${esc(r.id)}">
        <strong>${esc(r.label || r.kind)}</strong>
        <code>${esc(r.selector || r.fingerprint?.structural_path || "")}</code>
        <div class="qpi-rule-actions">
          <button type="button" class="qpi-btn qpi-unblock" data-id="${esc(r.id)}">Unblock</button>
        </div>
      </div>`,
      )
      .join("");
    pane.querySelectorAll(".qpi-unblock").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api({ action: "remove", rule_id: btn.dataset.id });
        refreshRules();
        reloadShields();
      });
    });
  }

  function onFrameMessage(ev) {
    const d = ev.data || {};
    if (d.source !== "queen-page-agent") return;
    if (d.type === "queen:inspector" && d.action === "select") {
      state.selection = d;
      if (state.open) renderSelection();
      if (!state.open) toggle(true);
      setTab("element");
      $("qpi-status").textContent = `Selected ${d.selector || d.fingerprint?.tag || "element"}`;
    }
    if (d.type === "queen:shields") {
      if (d.action === "ad_blocked") $("qpi-status").textContent = "Ad space removed — rule saved";
      if (d.action === "blocked") $("qpi-status").textContent = "Element blocked — rule saved";
      refreshRules();
    }
  }

  function injectAllFrames() {
    document.querySelectorAll(".qb-frame").forEach((f) => injectAgent(f));
  }

  function bind() {
    ensureDrawer();
    $("qpi-inspect-btn")?.addEventListener("click", () => toggle());
    window.addEventListener("message", onFrameMessage);
    document.addEventListener("queen-navigate", () => {
      setTimeout(injectAllFrames, 400);
    });
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "i") {
        e.preventDefault();
        toggle();
        if (state.open) togglePicker();
      }
      if (e.key === "Escape" && state.picker) togglePicker();
    });
    setTimeout(injectAllFrames, 800);
    refreshRules();
  }

  global.QueenPageInspector = {
    toggle,
    togglePicker,
    injectAgent,
    injectAllFrames,
    refreshRules,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();