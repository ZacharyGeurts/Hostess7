/**
 * Field Error Dashboard — central log + boot witness (loopback).
 * Pairs with field-performance-flyout; polls /api/field-error-dashboard.
 */
(function (global) {
  "use strict";

  const API = "/api/field-error-dashboard";
  const POLL_MS = 3000;
  let root = null;
  let pollTimer = null;
  let dragging = false;
  let dragOff = { x: 0, y: 0 };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;");
  }

  function ensureRoot() {
    if (root) return root;
    root = document.createElement("div");
    root.id = "fed-root";
    root.setAttribute("role", "complementary");
    root.setAttribute("aria-label", "Error dashboard");
    root.innerHTML = `
      <div class="fed-head" id="fed-head">
        <strong>Errors</strong>
        <span class="fed-sub" id="fed-sub">loopback witness</span>
        <button type="button" class="fed-close" id="fed-close" aria-label="Close">×</button>
      </div>
      <div class="fed-body" id="fed-body"></div>`;
    document.body.appendChild(root);
    const head = root.querySelector("#fed-head");
    const close = root.querySelector("#fed-close");
    close.addEventListener("click", () => hide());
    head.addEventListener("mousedown", (e) => {
      if (e.target === close) return;
      dragging = true;
      const r = root.getBoundingClientRect();
      dragOff = { x: e.clientX - r.left, y: e.clientY - r.top };
      e.preventDefault();
    });
    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      root.style.left = `${e.clientX - dragOff.x}px`;
      root.style.top = `${e.clientY - dragOff.y}px`;
      root.style.right = "auto";
      root.style.bottom = "auto";
    });
    document.addEventListener("mouseup", () => { dragging = false; });
    return root;
  }

  function render(doc) {
    const body = ensureRoot().querySelector("#fed-body");
    const counts = doc.counts || {};
    const perf = doc.performance || {};
    const stack = doc.stack || {};
    const errs = (doc.recent_events || []).filter((r) =>
      ["error", "warn", "timeout", "fail"].includes(String(r.level || "").toLowerCase())
    ).slice(-6);
    const boot = doc.boot_last || {};
    body.innerHTML = `
      <div class="fed-stat"><span>Central errors</span><span>${esc(counts.errors ?? 0)}</span></div>
      <div class="fed-stat"><span>Boot OK</span><span class="${boot.ok ? "fed-ok" : "fed-warn"}">${boot.ok ? "yes" : "no"}</span></div>
      <div class="fed-stat"><span>CPU</span><span>${esc(perf.cpu_pct ?? "—")}%</span></div>
      <div class="fed-stat"><span>Panel :9477</span><span class="${stack.panel?.up ? "fed-ok" : "fed-warn"}">${stack.panel?.up ? "up" : "down"}</span></div>
      <div class="fed-stat"><span>Queen :9481</span><span class="${stack.queen?.up ? "fed-ok" : "fed-warn"}">${stack.queen?.up ? "up" : "down"}</span></div>
      ${errs.length ? `<ul class="fed-list">${errs.map((r) => `<li>${esc(r.source)}: ${esc(r.message)}</li>`).join("")}</ul>` : "<p class='fed-ok'>No recent errors</p>"}`;
  }

  async function refresh() {
    try {
      const res = await fetch(API, { cache: "no-store" });
      if (!res.ok) return;
      render(await res.json());
    } catch (_) { /* loopback only */ }
  }

  function show() {
    ensureRoot().classList.add("fed-open");
    refresh();
    if (!pollTimer) pollTimer = setInterval(refresh, POLL_MS);
  }

  function hide() {
    if (root) root.classList.remove("fed-open");
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function toggle() {
    if (root && root.classList.contains("fed-open")) hide();
    else show();
  }

  global.FieldErrorDashboard = { show, hide, toggle, refresh };
})(typeof window !== "undefined" ? window : globalThis);