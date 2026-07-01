/**
 * Hostess 7 2.0 boot — brain → KILROY → Queen/AmmoOS surfaces on GitHub Pages.
 */
(function () {
  "use strict";

  const BASE = window.HOSTESS7_PAGES_BASE || "";
  const STAGES = [
    { id: "hostess7", label: "Hostess 7", detail: "Sovereign brain · counsel · truth doctrine", ms: 1200 },
    { id: "kilroy", label: "KILROY", detail: "Field Die · ZNetwork hooks · syscall truth", ms: 1300 },
    { id: "brain", label: "GitHub Brain", detail: "Isolated corpus mirror · same knowledge", ms: 1100 },
    { id: "surfaces", label: "Stack Surfaces", detail: "Queen browser · desktop icons · field programs", ms: 1400 },
    { id: "done", label: "Boot complete", detail: "Desktop ready — Hostess 7 is the main project", ms: 500 },
  ];

  const bar = document.getElementById("boot-bar");
  const stageEl = document.getElementById("boot-stage");
  const detailEl = document.getElementById("boot-detail");
  const pctEl = document.getElementById("boot-pct");

  let idx = 0;

  function preload() {
    [
      BASE + "/api/field-host-desktop.json",
      BASE + "/api/field-shell-settings.json",
      BASE + "/data/hostess7-old-projects.json",
      BASE + "/desktop/",
      BASE + "/assets/field-host-desktop.css",
    ].forEach(function (u) {
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
    const pct = Math.min(100, Math.round(((idx + 1) / STAGES.length) * 100));
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
  setTimeout(tick, 350);
})();