/**
 * Hostess7 GitHub Pages — auto-boot Queen Browser + AmmoOS on every visit.
 */
(function () {
  "use strict";

  const BASE = window.HOSTESS7_PAGES_BASE || "";
  const queenFrame = document.getElementById("queen-frame");
  const ammoosFrame = document.getElementById("ammoos-frame");
  const queenLoad = document.getElementById("queen-loading");
  const ammoosLoad = document.getElementById("ammoos-loading");
  const badge = document.getElementById("runtime-badge");
  const split = document.getElementById("pages-split");
  const shell = document.getElementById("pages-shell");

  const QUEEN_URL = (BASE || "") + "/queen/browser.html?pages=1";
  const AMMOOS_URL = (BASE || "") + "/ammoos/?pages=1";

  let ready = { queen: false, ammoos: false };

  function markReady(layer) {
    ready[layer] = true;
    const el = layer === "queen" ? queenLoad : ammoosLoad;
    if (el) el.classList.add("hidden");
    if (ready.queen && ready.ammoos && badge) {
      badge.textContent = "Queen + AmmoOS live";
      badge.classList.add("live");
    }
  }

  function boot() {
    if (queenFrame) {
      queenFrame.src = QUEEN_URL;
      queenFrame.addEventListener("load", function () { markReady("queen"); }, { once: true });
    }
    if (ammoosFrame) {
      ammoosFrame.src = AMMOOS_URL;
      ammoosFrame.addEventListener("load", function () { markReady("ammoos"); }, { once: true });
    }
    setTimeout(function () {
      markReady("queen");
      markReady("ammoos");
    }, 12000);
  }

  if (split && shell) {
    let dragging = false;
    split.addEventListener("mousedown", function () {
      dragging = true;
      split.classList.add("dragging");
    });
    window.addEventListener("mouseup", function () {
      dragging = false;
      split.classList.remove("dragging");
    });
    window.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      const pct = Math.min(78, Math.max(28, (e.clientY / window.innerHeight) * 100));
      shell.style.setProperty("--split", pct + "%");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();