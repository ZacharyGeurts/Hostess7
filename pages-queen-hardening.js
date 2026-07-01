/**
 * GitHub Pages — Queen AmmoLang posture + hardened shell (zero-day hold).
 */
(function (global) {
  "use strict";

  var POSTURE = {
    schema: "ammolang-pages-hardening/v1",
    lane: "pages-surfaces",
    ironclad: true,
    zero_day_hold: true,
    rewrite: "AmmoLang ensure_protection · universal_boundary",
    slots: ["TIME", "MEMORY", "THERMO", "CONTEXT"],
    runtime_tax: 0,
  };

  function sealEval() {
    try {
      var native = global.eval;
      global.eval = function () {
        throw new Error("AmmoLang hold — eval blocked on Pages Queen");
      };
      Object.defineProperty(global, "eval", { configurable: false, writable: false, value: global.eval });
    } catch (_) {}
  }

  function blockDangerousProtocols(ev) {
    var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
    if (!a) return;
    var href = String(a.getAttribute("href") || "").trim().toLowerCase();
    if (href.indexOf("javascript:") === 0 || href.indexOf("data:text/html") === 0) {
      ev.preventDefault();
      ev.stopPropagation();
    }
  }

  function wireCspReport() {
    document.addEventListener(
      "securitypolicyviolation",
      function (e) {
        try {
          console.warn("[AmmoLang CSP]", e.violatedDirective, e.blockedURI);
        } catch (_) {}
      },
      true
    );
  }

  function exposePosture() {
    try {
      global.__H7_QUEEN_POSTURE__ = POSTURE;
    } catch (_) {}
    var strip = document.getElementById("qb-security-strip");
    if (strip && document.body && document.body.dataset.pagesRuntime === "1") {
      strip.textContent = "AmmoLang · ironclad · zero-day hold · Pages";
      strip.title = POSTURE.rewrite;
    }
  }

  sealEval();
  document.addEventListener("click", blockDangerousProtocols, true);
  wireCspReport();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", exposePosture);
  } else {
    exposePosture();
  }

  global.Hostess7QueenHardening = { posture: POSTURE };
})(typeof window !== "undefined" ? window : globalThis);