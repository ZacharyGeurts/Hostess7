/**
 * Queen AI Surface — attach operable metadata for agents reading the UI.
 * No icon cache; reads library index only.
 */
(function (global) {
  "use strict";

  function applyRootMeta() {
    const surface = document.body?.dataset?.queenSurface || "queen";
    document.documentElement.dataset.queenAiSurface = surface;
    document.body?.setAttribute("data-queen-ai-surface", surface);
  }

  async function enrichFromLibrary() {
    const engine = global.QueenIconEngine;
    if (!engine?.loadLibraryIndex) return;
    await engine.loadLibraryIndex();
    document.querySelectorAll("[data-queen-program-url]").forEach((el) => {
      const url = el.dataset.queenProgramUrl || "";
      const name = el.dataset.queenProgramName || el.textContent?.trim() || "";
      el.setAttribute("data-queen-ai-operate", "open_url");
      el.setAttribute("data-queen-ai-command", url);
      el.setAttribute("data-queen-ai-name", name);
    });
    document.querySelectorAll("[data-queen-icon-ref]").forEach((el) => {
      const ref = el.dataset.queenIconRef;
      const hit = engine.lookupEntry?.(ref);
      if (!hit) return;
      el.setAttribute("data-queen-ai-name", hit.name || "");
      if (hit.kind) el.setAttribute("data-queen-ai-kind", hit.kind);
    });
  }

  function boot() {
    applyRootMeta();
    enrichFromLibrary();
    document.addEventListener("queen-navigate", () => enrichFromLibrary());
    const obs = new MutationObserver(() => enrichFromLibrary());
    if (document.body) obs.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.QueenAiSurface = { enrichFromLibrary, applyRootMeta };
})(typeof window !== "undefined" ? window : globalThis);