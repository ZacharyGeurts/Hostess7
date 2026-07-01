/**
 * NEXUS AI Integration Hook — browser leg; human integration forbidden.
 * Field compiler + Grok build dispatch is loopback AI-token only (server-side).
 */
(function () {
  "use strict";

  const OWNER = "nexus-ai-integration-hook";
  const POLL_MS = 5000;

  const state = {
    owner: OWNER,
    boarded: false,
    secureChannel: false,
    humanIntegration: false,
    posture: null,
  };

  function sealHumanIntegration() {
    const block = [
      "NexusBoardHook", "NexusHumanIntegrate", "__boardHook", "__integrationBridge",
      "__keyboardHook", "__osInputBridge", "__pointerHook", "xdotool", "ydotool", "dotool", "wmctrl",
    ];
    block.forEach((k) => {
      try {
        if (k in window) delete window[k];
        Object.defineProperty(window, k, {
          get() { return undefined; },
          set() { return false; },
          configurable: false,
        });
      } catch (_) { /* sealed */ }
    });
  }

  function blockHumanIntegrationMessage(ev) {
    if (!ev || ev.source === window) return;
    const data = ev.data;
    if (!data || typeof data !== "object") return;
    const kind = String(data.kind || data.action || data.schema || "").toLowerCase();
    if (
      kind.includes("integrate") || kind.includes("board-hook") || kind.includes("board_hook")
      || kind.includes("ocr_drive") || kind.includes("human")
    ) {
      ev.stopImmediatePropagation();
      ev.preventDefault();
    }
  }

  function fetchPosture() {
    return fetch("/api/ai-integration", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }

  function applyPosture(doc) {
    if (!doc || typeof doc !== "object") return;
    state.posture = doc;
    state.secureChannel = !!doc.secure_channel;
    state.humanIntegration = false;
    const root = document.documentElement;
    root.setAttribute("data-nexus-ai-integration-hook", OWNER);
    root.toggleAttribute("data-nexus-ai-secure", state.secureChannel);
    root.setAttribute("data-human-integration", "forbidden");
  }

  function poll() {
    fetchPosture().then(applyPosture);
  }

  function board() {
    if (state.boarded) return state;
    sealHumanIntegration();
    window.addEventListener("message", blockHumanIntegrationMessage, true);
    poll();
    window.setInterval(poll, POLL_MS);
    state.boarded = true;
    return state;
  }

  if (window.NexusFrontHook && typeof window.NexusFrontHook.board === "function") {
    window.NexusFrontHook.board();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", board);
  } else {
    board();
  }

  window.NexusAIIntegration = {
    owner: OWNER,
    board,
    posture: function () { return state.posture ? { ...state.posture } : null; },
    secureChannel: function () { return state.secureChannel; },
    humanIntegrationAllowed: function () { return false; },
    state: function () { return { ...state }; },
  };
})();