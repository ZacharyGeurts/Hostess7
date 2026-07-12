/**
 * GitHub Pages — AmmoNet / Final Internet strip + module quick-launch
 */
(function (global) {
  "use strict";

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function base() {
    return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
  }

  function ensureStrip() {
    if (!pagesRuntime() || document.getElementById("h7-ammonet-strip")) return;
    const strip = document.createElement("div");
    strip.id = "h7-ammonet-strip";
    strip.className = "h7-ammonet-strip";
    strip.setAttribute("role", "navigation");
    strip.innerHTML =
      '<span class="h7-ammonet-strip__brand"><strong>AmmoNet</strong> v4.0.1 · Hostess 7 brain</span>' +
      '<a href="' + base() + '/ammonet/">ISP Hub</a>' +
      '<a href="' + base() + '/final-internet/">Safe Fields</a>' +
      '<a href="' + base() + '/brain.html">Brain</a>' +
      '<a href="' + base() + '/command/">C2</a>' +
      '<a href="' + base() + '/desktop/">AmmoOS</a>' +
      '<a href="' + base() + '/ammocode/">AmmoCode</a>' +
      '<a href="' + base() + '/threat-panel/">Borders</a>' +
      '<a href="' + base() + '/training-room/">Training</a>' +
      '<a href="' + base() + '/field-znetwork-vault/">Vault</a>' +
      '<a href="' + base() + '/hub/">Hub</a>' +
      '<span class="h7-ammonet-strip__count" id="h7-ammonet-strip-count"></span>';
    const style = document.createElement("style");
    style.textContent =
      ":root{--h7-ammonet-h:36px}" +
      "html.h7-final-internet body{padding-bottom:calc(var(--fsb-h,44px) + var(--h7-ammonet-h) + env(safe-area-inset-bottom,0))}" +
      ".h7-ammonet-strip{position:fixed;bottom:0;left:0;right:0;z-index:99980;" +
      "min-height:var(--h7-ammonet-h);display:flex;flex-wrap:nowrap;gap:10px 16px;overflow-x:auto;" +
      "align-items:center;padding:6px 14px;padding-bottom:calc(6px + env(safe-area-inset-bottom,0));" +
      "background:rgba(6,12,22,0.96);border-top:1px solid rgba(212,184,106,0.35);" +
      "font:12px system-ui,sans-serif;color:#c8d6ea;scrollbar-width:thin}" +
      ".h7-ammonet-strip__brand{color:#d4b86a;margin-right:8px;white-space:nowrap}" +
      ".h7-ammonet-strip a{color:#9ab8ff;text-decoration:none;white-space:nowrap}" +
      ".h7-ammonet-strip a:hover{color:#f0d060}" +
      ".h7-ammonet-strip__count{margin-left:auto;color:rgba(154,184,255,0.75);font-size:11px;white-space:nowrap}";
    document.head.appendChild(style);
    document.body.appendChild(strip);
  }

  async function stampFinalInternet() {
    try {
      const r = await fetch("/api/final-internet", { cache: "no-store" });
      if (!r.ok) return;
      const doc = await r.json();
      const brand = document.querySelector("#h7-ammonet-strip .h7-ammonet-strip__brand");
      if (brand && doc.motto) {
        brand.title = doc.motto;
      }
    } catch (_) {}
    try {
      const r = await fetch("/api/field-internet", { cache: "no-store" });
      if (r.ok) {
        const doc = await r.json();
        const gh = (doc.github_always || {}).live || {};
        const countEl = document.getElementById("h7-ammonet-strip-count");
        if (countEl && gh.open_count) {
          countEl.textContent = "GitHub " + gh.open_count + " open · unified";
        }
        const brand = document.querySelector("#h7-ammonet-strip .h7-ammonet-strip__brand");
        if (brand && doc.motto) brand.title = doc.motto;
      }
    } catch (_) {}
    try {
      const r = await fetch("/api/ammonet", { cache: "no-store" });
      if (!r.ok) return;
      const doc = await r.json();
      const countEl = document.getElementById("h7-ammonet-strip-count");
      if (countEl) {
        const ver = doc.version ? "v" + doc.version + " · " : "";
        const tail = doc.surface_count ? doc.surface_count + " surfaces live" : "";
        if (ver || tail) countEl.textContent = ver + tail;
      }
      const brand = document.querySelector("#h7-ammonet-strip .h7-ammonet-strip__brand");
      if (brand && doc.motto && !brand.title) brand.title = doc.motto;
    } catch (_) {}
    try {
      const r = await fetch(base() + "/api/hostess7-ammonet-wire.json", { cache: "no-store" });
      if (!r.ok) return;
      const doc = await r.json();
      const countEl = document.getElementById("h7-ammonet-strip-count");
      const wired =
        doc.wired_count != null
          ? doc.wired_count
          : (doc.stack && doc.stack.wired_count) != null
            ? doc.stack.wired_count
            : null;
      const bordersOk =
        doc.borders_ok != null
          ? doc.borders_ok
          : !!(doc.borders && doc.borders.ok);
      if (countEl && wired != null) {
        const border = bordersOk ? "borders sealed" : "borders open";
        countEl.textContent =
          (countEl.textContent ? countEl.textContent + " · " : "") +
          wired +
          " stack wired · " +
          border;
      }
    } catch (_) {}
  }

  function boot() {
    if (!pagesRuntime()) return;
    /* AmmoOS desktop owns the sole taskbar — no second bottom strip here. */
    if (document.documentElement.dataset.ammoosDesktop === "1") return;
    if (/\/desktop\/?$/.test(global.location.pathname || "")) return;
    document.documentElement.classList.add("h7-final-internet");
    ensureStrip();
    stampFinalInternet();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.Hostess7AmmoNetWire = { boot: boot };
})(typeof window !== "undefined" ? window : globalThis);