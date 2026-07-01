/**
 * NEXUS C2 → KILROY → AmmoOS Desktop → Queen — boot sequence for GitHub Pages.
 */
(function () {
  "use strict";

  const BASE = window.HOSTESS7_PAGES_BASE || "";
  const STAGES = [
    { id: "nexus", label: "NEXUS C2", detail: "G16 field_opt · programmatic command surface", ms: 1400 },
    { id: "kilroy", label: "KILROY", detail: "Field Die · ZNetwork hooks · syscall truth", ms: 1600 },
    { id: "ammoos", label: "AmmoOS", detail: "Desktop shell · taskbar · field programs", ms: 1400 },
    { id: "queen", label: "Queen Browser", detail: "RTX shell · bookmarks · secured navigation", ms: 1200 },
    { id: "done", label: "Boot complete", detail: "Desktop ready — launching Queen", ms: 600 },
  ];

  const bar = document.getElementById("boot-bar");
  const stageEl = document.getElementById("boot-stage");
  const detailEl = document.getElementById("boot-detail");
  const pctEl = document.getElementById("boot-pct");

  let idx = 0;
  let pct = 0;

  function preload() {
    const urls = [
      BASE + "/api/field-host-desktop.json",
      BASE + "/api/field-shell-settings.json",
      BASE + "/ammoos/",
      BASE + "/queen/browser.html",
    ];
    urls.forEach(function (u) {
      fetch(u, { cache: "force-cache" }).catch(function () {});
    });
  }

  function tick() {
    if (idx >= STAGES.length) {
      finish();
      return;
    }
    const s = STAGES[idx];
    if (stageEl) stageEl.textContent = s.label;
    if (detailEl) detailEl.textContent = s.detail;
    pct = Math.min(100, Math.round(((idx + 1) / STAGES.length) * 100));
    if (bar) bar.style.width = pct + "%";
    if (pctEl) pctEl.textContent = pct + "%";
    idx += 1;
    setTimeout(tick, s.ms);
  }

  function finish() {
    try { sessionStorage.setItem("hostess7-pages-booted", "1"); } catch (_e) {}
    window.location.replace(BASE + "/desktop/");
  }

  preload();
  setTimeout(tick, 400);
})();