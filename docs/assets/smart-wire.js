/**
 * NEXUS Smart Wire — browser leg of the keyboard wire.
 * Blocks synthetic/injected keyboard events (middlemen); only trusted operator input passes.
 */
(function () {
  "use strict";

  const OWNER = "nexus-smart-wire";
  const WIRE_SEL = "[data-smart-wire], [data-front-hook], [data-admin-shield], .fm-shell";

  function onWireSurface(target) {
    return !!(target && target.closest && target.closest(WIRE_SEL));
  }

  function blockSyntheticInput(ev) {
    if (!onWireSurface(ev.target)) return;
    if (ev.isTrusted) return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
  }

  function blockInjectedComposition(ev) {
    if (!onWireSurface(ev.target)) return;
    if (ev.isTrusted) return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
  }

  function blockInjectedClipboard(ev) {
    if (!onWireSurface(ev.target)) return;
    if (ev.isTrusted) return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
  }

  function sealDispatch() {
    const orig = EventTarget.prototype.dispatchEvent;
    EventTarget.prototype.dispatchEvent = function (ev) {
      if (
        ev instanceof KeyboardEvent
        && onWireSurface(this)
        && !ev.isTrusted
      ) {
        console.warn("[smart-wire] blocked synthetic keyboard dispatch");
        return false;
      }
      return orig.call(this, ev);
    };
  }

  function board() {
    const inputTypes = [
      "keydown", "keyup", "keypress", "beforeinput", "input",
      "compositionstart", "compositionupdate", "compositionend",
      "copy", "cut", "paste",
    ];
    inputTypes.forEach((type) => {
      const handler = type.startsWith("composition")
        ? blockInjectedComposition
        : (type === "copy" || type === "cut" || type === "paste")
          ? blockInjectedClipboard
          : blockSyntheticInput;
      window.addEventListener(type, handler, true);
      document.addEventListener(type, handler, true);
    });
    sealDispatch();
    document.querySelectorAll(WIRE_SEL).forEach((n) => {
      n.setAttribute("data-smart-wire", OWNER);
    });
    if (document.documentElement) {
      document.documentElement.setAttribute("data-nexus-smart-wire", OWNER);
    }
  }

  if (window.NexusFrontHook && typeof window.NexusFrontHook.board === "function") {
    window.NexusFrontHook.board();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", board);
  } else {
    board();
  }

  window.NexusSmartWire = { owner: OWNER, board };
})();