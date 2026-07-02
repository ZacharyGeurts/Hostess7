/**
 * NEXUS Hardware Wire — browser leg for all field hardware hooks.
 * Detects synthetic injection; operates trusted hooks on wire surfaces (field, fast, safe).
 * Human integration paths are never exempt — AI integrates server-side only.
 */
(function () {
  "use strict";

  const OWNER = "nexus-hardware-wire";
  const WIRE_SEL = "[data-hardware-wire], [data-smart-wire], [data-front-hook], [data-admin-shield], [data-queen-surface=\"browser\"], .qw-browser-shell, .fm-shell";

  const INPUT_EVENTS = [
    "keydown", "keyup", "keypress", "beforeinput", "input",
    "compositionstart", "compositionupdate", "compositionend",
    "copy", "cut", "paste",
    "pointerdown", "pointerup", "pointermove", "pointercancel",
    "mousedown", "mouseup", "mousemove", "click", "dblclick", "contextmenu",
    "wheel", "touchstart", "touchend", "touchmove", "touchcancel",
    "gamepadconnected", "gamepaddisconnected",
  ];

  const state = {
    owner: OWNER,
    boarded: false,
    eventsBlocked: 0,
    mediaGated: 0,
  };

  function onWireSurface(target) {
    return !!(target && target.closest && target.closest(WIRE_SEL));
  }

  function blockUntrusted(ev) {
    if (!onWireSurface(ev.target)) return;
    if (ev.isTrusted) return;
    state.eventsBlocked += 1;
    ev.stopImmediatePropagation();
    ev.preventDefault();
  }

  function sealDispatch() {
    const orig = EventTarget.prototype.dispatchEvent;
    const blocked = new Set([
      "KeyboardEvent", "MouseEvent", "PointerEvent", "TouchEvent", "WheelEvent", "InputEvent",
    ]);
    EventTarget.prototype.dispatchEvent = function (ev) {
      if (blocked.has(ev && ev.constructor && ev.constructor.name) && onWireSurface(this) && !ev.isTrusted) {
        state.eventsBlocked += 1;
        console.warn("[hardware-wire] blocked synthetic dispatch:", ev.constructor.name);
        return false;
      }
      return orig.call(this, ev);
    };
  }

  function operateMediaDevices() {
    if (!navigator.mediaDevices) return;
    const origEnum = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
    navigator.mediaDevices.enumerateDevices = function () {
      if (onWireSurface(document.body)) {
        state.mediaGated += 1;
        return Promise.resolve([]);
      }
      return origEnum();
    };
    const origGum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = function (constraints) {
      if (onWireSurface(document.body)) {
        state.mediaGated += 1;
        return Promise.reject(new DOMException("NEXUS hardware wire operates media on field surfaces", "NotAllowedError"));
      }
      return origGum(constraints);
    };
    if (navigator.mediaDevices.getDisplayMedia) {
      const origGdm = navigator.mediaDevices.getDisplayMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getDisplayMedia = function (constraints) {
        if (onWireSurface(document.body)) {
          state.mediaGated += 1;
          return Promise.reject(new DOMException("NEXUS hardware wire operates display capture", "NotAllowedError"));
        }
        return origGdm(constraints);
      };
    }
  }

  function operateGamepad() {
    if (!navigator.getGamepads) return;
    const orig = navigator.getGamepads.bind(navigator);
    navigator.getGamepads = function () {
      if (onWireSurface(document.body)) {
        return [];
      }
      return orig();
    };
  }

  function sealGlobals() {
    const block = [
      "xdotool", "ydotool", "dotool", "wmctrl", "__keyboardHook", "__osInputBridge",
      "__pointerHook", "__mediaHook", "__gamepadBridge", "NexusBoardHook", "NexusHumanIntegrate",
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

  function board() {
    if (state.boarded) return state;
    INPUT_EVENTS.forEach((type) => {
      window.addEventListener(type, blockUntrusted, true);
      document.addEventListener(type, blockUntrusted, true);
    });
    sealDispatch();
    operateMediaDevices();
    operateGamepad();
    sealGlobals();
    document.querySelectorAll(WIRE_SEL).forEach((n) => {
      n.setAttribute("data-hardware-wire", OWNER);
    });
    if (document.documentElement) {
      document.documentElement.setAttribute("data-nexus-hardware-wire", OWNER);
    }
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

  window.NexusHardwareWire = { owner: OWNER, board, state: function () { return { ...state }; } };
  window.NexusSmartWire = window.NexusHardwareWire;
})();