/**
 * Queen media egress — block screen/mic/keystroke OUT unless operator local grant.
 * Safety first for Humans and AI. Presume hostile egress.
 */
(function () {
  "use strict";

  const SURFACE = "browser";
  const GRANT_KEY = "queen:local_capture_grant";
  const BLOCKED_MSG = "Queen egress locked — local operator grant required";

  const state = {
    grant: null,
    grantActive: false,
    egressLocked: true,
    blocked: { media: 0, webrtc: 0, keystroke: 0, clipboard: 0 },
  };

  function onBrowserSurface() {
    return document.body?.dataset?.queenSurface === SURFACE;
  }

  function isLoopbackUrl(url) {
    try {
      const u = new URL(url, location.origin);
      const h = (u.hostname || "").toLowerCase();
      return h === "127.0.0.1" || h === "localhost" || h === location.hostname;
    } catch {
      return false;
    }
  }

  async function refreshGrant() {
    if (!onBrowserSurface()) return state;
    try {
      const r = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "media_egress_status" }),
        cache: "no-store",
      });
      const j = await r.json();
      state.grant = j.grant || null;
      state.grantActive = !!j.grant_active;
      state.egressLocked = j.egress_lock !== false;
      globalThis.QueenCaptureGrant = state.grantActive ? state.grant : null;
      globalThis.NexusCaptureGrant = globalThis.QueenCaptureGrant;
      try {
        sessionStorage.setItem(GRANT_KEY, JSON.stringify({ active: state.grantActive, at: Date.now() }));
      } catch (_) { /* sealed */ }
    } catch (_) {
      state.grantActive = false;
      globalThis.QueenCaptureGrant = null;
    }
    return state;
  }

  function sealMediaDevices() {
    if (!navigator.mediaDevices) return;
    const deny = (label) => {
      state.blocked.media += 1;
      return Promise.reject(new DOMException(`${BLOCKED_MSG} (${label})`, "NotAllowedError"));
    };
    const origGum = navigator.mediaDevices.getUserMedia?.bind(navigator.mediaDevices);
    if (origGum) {
      navigator.mediaDevices.getUserMedia = function (constraints) {
        if (!onBrowserSurface() || state.grantActive) return origGum(constraints);
        return deny("mic/camera");
      };
    }
    const origGdm = navigator.mediaDevices.getDisplayMedia?.bind(navigator.mediaDevices);
    if (origGdm) {
      navigator.mediaDevices.getDisplayMedia = function (constraints) {
        if (!onBrowserSurface() || state.grantActive) return origGdm(constraints);
        return deny("display");
      };
    }
    const origEnum = navigator.mediaDevices.enumerateDevices?.bind(navigator.mediaDevices);
    if (origEnum) {
      navigator.mediaDevices.enumerateDevices = function () {
        if (onBrowserSurface() && !state.grantActive) {
          state.blocked.media += 1;
          return Promise.resolve([]);
        }
        return origEnum();
      };
    }
  }

  function sealWebRtc() {
    const Orig = globalThis.RTCPeerConnection;
    if (!Orig || !onBrowserSurface()) return;
    globalThis.RTCPeerConnection = function (config, constraints) {
      const ice = (config && config.iceServers) || [];
      const remoteIce = ice.some((s) => {
        const urls = [].concat(s.urls || s.url || []);
        return urls.some((u) => typeof u === "string" && !isLoopbackUrl(u));
      });
      if (!state.grantActive || remoteIce) {
        state.blocked.webrtc += 1;
        throw new DOMException(BLOCKED_MSG, "NotAllowedError");
      }
      return new Orig(config, constraints);
    };
    globalThis.RTCPeerConnection.prototype = Orig.prototype;
  }

  function sealClipboard() {
    if (!navigator.clipboard || !onBrowserSurface()) return;
    const origWrite = navigator.clipboard.writeText?.bind(navigator.clipboard);
    if (origWrite) {
      navigator.clipboard.writeText = async function (text) {
        if (!state.grantActive) {
          state.blocked.clipboard += 1;
          throw new DOMException(BLOCKED_MSG, "NotAllowedError");
        }
        return origWrite(text);
      };
    }
  }

  function sealKeystrokeEgress() {
    const INPUT = ["keydown", "keyup", "keypress", "beforeinput", "input", "copy", "cut", "paste"];
    INPUT.forEach((type) => {
      window.addEventListener(
        type,
        (ev) => {
          if (!onBrowserSurface() || ev.isTrusted) return;
          state.blocked.keystroke += 1;
          ev.stopImmediatePropagation();
          ev.preventDefault();
        },
        true,
      );
    });
    const origFetch = globalThis.fetch;
    if (typeof origFetch === "function") {
      globalThis.fetch = function (input, init) {
        const url = typeof input === "string" ? input : input?.url || "";
        if (onBrowserSurface() && url && !isLoopbackUrl(url) && init?.body) {
          const body = String(init.body);
          if (/key|keystroke|input|password|credential/i.test(body)) {
            state.blocked.keystroke += 1;
            return Promise.reject(new DOMException(BLOCKED_MSG, "SecurityError"));
          }
        }
        return origFetch.call(this, input, init);
      };
    }
    const origPm = window.postMessage.bind(window);
    window.postMessage = function (message, targetOrigin, transfer) {
      if (onBrowserSurface() && targetOrigin && targetOrigin !== location.origin && targetOrigin !== "*") {
        if (message && typeof message === "object" && /key|input|keystroke/i.test(JSON.stringify(message))) {
          state.blocked.keystroke += 1;
          return;
        }
      }
      return origPm(message, targetOrigin, transfer);
    };
  }

  function sealHookGlobals() {
    const block = [
      "__keyboardHook", "__osInputBridge", "__pointerHook", "__mediaHook",
      "__gamepadBridge", "NexusBoardHook", "NexusHumanIntegrate", "xdotool", "ydotool",
    ];
    block.forEach((k) => {
      try {
        Object.defineProperty(window, k, {
          get() { return undefined; },
          set() { return false; },
          configurable: false,
        });
      } catch (_) { /* sealed */ }
    });
  }

  async function board() {
    if (!onBrowserSurface()) return;
    document.body.setAttribute("data-media-egress", "locked");
    document.body.setAttribute("data-hardware-wire", "queen-media-egress");
    document.body.setAttribute("data-front-hook", "1");
    sealHookGlobals();
    sealMediaDevices();
    sealWebRtc();
    sealClipboard();
    sealKeystrokeEgress();
    await refreshGrant();
    setInterval(refreshGrant, 15000);
    document.body.dataset.mediaEgress = state.grantActive ? "local_grant" : "locked";
  }

  globalThis.QueenMediaEgress = {
    board,
    refreshGrant,
    state: () => ({ ...state }),
    requestLocalCapture: async (purpose) => {
      const r = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "capture_request", purpose: purpose || "obs_local" }),
      });
      const j = await r.json();
      await refreshGrant();
      return j;
    },
    revokeCapture: async () => {
      const r = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "capture_revoke" }),
      });
      await refreshGrant();
      return r.json();
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", board);
  } else {
    board();
  }
})();