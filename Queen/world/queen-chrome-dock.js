/**
 * Queen Browser — bottom chrome dock minimize / restore.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "queen.chrome.minimized";

  function $(id) {
    return document.getElementById(id);
  }

  function setMinimized(minimized) {
    const on = !!minimized;
    document.body.classList.toggle("qw-chrome-minimized", on);
    const restore = $("qb-chrome-restore");
    const chrome = $("qb-chrome");
    if (restore) {
      restore.hidden = !on;
      restore.setAttribute("aria-hidden", on ? "false" : "true");
    }
    if (chrome) chrome.setAttribute("aria-hidden", on ? "true" : "false");
    const minBtn = $("qb-chrome-min");
    if (minBtn) minBtn.setAttribute("aria-pressed", on ? "true" : "false");
    try {
      sessionStorage.setItem(STORAGE_KEY, on ? "1" : "0");
    } catch (_) {
      /* private mode */
    }
  }

  function wire() {
    const minBtn = $("qb-chrome-min");
    const restore = $("qb-chrome-restore");
    if (!minBtn || !restore) return;

    minBtn.addEventListener("click", (e) => {
      e.preventDefault();
      setMinimized(true);
    });

    restore.addEventListener("click", (e) => {
      e.preventDefault();
      setMinimized(false);
    });

    restore.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setMinimized(false);
      }
    });

    try {
      if (sessionStorage.getItem(STORAGE_KEY) === "1") setMinimized(true);
    } catch (_) {
      /* ignore */
    }
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", wire);
  }

  globalThis.QueenChromeDock = { setMinimized, wire };
})();