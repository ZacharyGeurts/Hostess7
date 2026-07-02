/* NEXUS RTX Zero — sole-project panel mode: Aqua chrome, cache-first, idle = zero cost */
(function (global) {
  "use strict";

  const BUILD = "rtx-zero-v1";
  const STORAGE_KEY = "nexus_rtx_zero";

  function queryEnabled() {
    try {
      const q = new URLSearchParams(global.location.search);
      if (q.get("rtx") === "1" || q.get("zero") === "1" || q.get("mode") === "rtx") return true;
      if (q.get("rtx") === "0") return false;
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch (_) {
      return false;
    }
  }

  function setEnabled(on) {
    try {
      localStorage.setItem(STORAGE_KEY, on ? "1" : "0");
    } catch (_) {}
    document.documentElement.classList.toggle("nexus-rtx-zero", !!on);
  }

  function ensureBadge() {
    const h1 = document.querySelector("header.app-header h1");
    if (!h1 || document.getElementById("nexus-rtx-zero-badge")) return;
    const badge = document.createElement("span");
    badge.id = "nexus-rtx-zero-badge";
    badge.title = "RTX Zero panel — Aqua chrome, cache-first refresh, canvases idle when hidden";
    badge.textContent = "RTX · ZERO COST";
    h1.appendChild(badge);
  }

  function applyPollScale(data) {
    if (!document.documentElement.classList.contains("nexus-rtx-zero")) return;
    const base = Number(data?.poll_ms) || Number(global.panelPollMs) || 5000;
    const scale = Number(data?.panel_zero_cost_poll_scale) || 1.25;
    const next = Math.round(base * scale);
    if (typeof global.panelPollMs === "number" && global.panelPollMs < next) {
      global.panelPollMs = next;
      if (typeof global.schedulePanelRefresh === "function") global.schedulePanelRefresh();
    }
  }

  function hookPaint() {
    const orig = global.paintPanel;
    if (typeof orig !== "function" || orig.__rtxZero) return;
    global.paintPanel = function rtxPaintPanel(data) {
      if (data?.panel_rtx_zero) setEnabled(true);
      applyPollScale(data);
      document.documentElement.classList.toggle("panel-zero-cost-idle", !!global.document.hidden);
      const out = orig.apply(this, arguments);
      ensureBadge();
      return out;
    };
    global.paintPanel.__rtxZero = true;
  }

  function hookRefresh() {
    const orig = global.refresh;
    if (typeof orig !== "function" || orig.__rtxZero) return;
    global.refresh = async function rtxRefresh() {
      if (document.hidden) {
        document.documentElement.classList.add("panel-zero-cost-idle");
        return;
      }
      document.documentElement.classList.remove("panel-zero-cost-idle");
      return orig.apply(this, arguments);
    };
    global.refresh.__rtxZero = true;
  }

  function boot() {
    if (queryEnabled()) {
      document.documentElement.classList.add("nexus-rtx-zero");
    }
    ensureBadge();
    hookPaint();
    hookRefresh();
    document.addEventListener("visibilitychange", () => {
      document.documentElement.classList.toggle("panel-zero-cost-idle", document.hidden);
    });
  }

  function paused() {
    return document.hidden || document.documentElement.classList.contains("panel-zero-cost-idle");
  }

  global.NexusRtxZero = {
    BUILD,
    enabled: () => document.documentElement.classList.contains("nexus-rtx-zero"),
    enable: () => setEnabled(true),
    disable: () => setEnabled(false),
    paused,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);