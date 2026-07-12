/**
 * Queen front hook — first on the board before host plugins eat our surface.
 */
(function () {
  "use strict";

  const PASS_THROUGH = false;
  const OWNER = "nexus-front-hook";
  const ADMIN_SEL =
    "[data-admin-shield], [data-front-hook], .fm-shell, .qw-browser-shell, .dns-admin-engineer, #dns-admin-portal-panel";
  const ALLOWED_PLUGIN_HOOKS = new Set(["tab-beacon", "nexus-braille-a11y", "ai-integration-hook"]);

  const state = { owner: OWNER, passThrough: PASS_THROUGH, boarded: false, eventsOwned: 0 };

  function onAdminSurface(target) {
    return !!(target && target.closest && target.closest(ADMIN_SEL));
  }

  function ownEvent(ev) {
    if (!ev || ev.nexusFrontOwned) return;
    Object.defineProperty(ev, "nexusFrontOwned", { value: true, configurable: true });
    Object.defineProperty(ev, "nexusFrontOwner", { value: OWNER, configurable: true });
    state.eventsOwned += 1;
  }

  function frontCapture(ev) {
    ownEvent(ev);
  }

  function blockForeignMessage(ev) {
    if (PASS_THROUGH) return;
    if (!onAdminSurface(document.body)) return;
    if (ev.source === window) return;
    ev.stopImmediatePropagation();
    ev.preventDefault();
  }

  function patchPluginRuntime() {
    const wrap = function () {
      if (!window.NexusPlugins || window.NexusPlugins.__frontHookPatched) return;
      const orig = window.NexusPlugins.registerClientHook;
      if (typeof orig !== "function") return;
      window.NexusPlugins.registerClientHook = function (pluginId, fn) {
        if (!ALLOWED_PLUGIN_HOOKS.has(pluginId)) {
          console.warn("[front-hook] blocked plugin hook:", pluginId);
          return;
        }
        return orig.call(window.NexusPlugins, pluginId, fn);
      };
      window.NexusPlugins.__frontHookPatched = true;
    };
    wrap();
    const t = setInterval(() => {
      wrap();
      if (window.NexusPlugins && window.NexusPlugins.__frontHookPatched) clearInterval(t);
    }, 100);
    setTimeout(() => clearInterval(t), 8000);
  }

  function sealGlobals() {
    ["xdotool", "ydotool", "dotool", "wmctrl", "__keyboardHook", "__osInputBridge"].forEach((k) => {
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
    [
      "keydown", "keyup", "keypress",
      "pointerdown", "pointerup", "pointermove",
      "mousedown", "mouseup", "mousemove", "wheel",
      "touchstart", "touchend", "touchmove",
      "focusin", "focusout",
    ].forEach((type) => {
      window.addEventListener(type, frontCapture, true);
      document.addEventListener(type, frontCapture, true);
    });
    window.addEventListener("message", blockForeignMessage, true);
    sealGlobals();
    patchPluginRuntime();
    state.boarded = true;
    try {
      document.documentElement.setAttribute("data-nexus-front-hook", OWNER);
    } catch (_) { /* */ }
    return state;
  }

  board();

  window.NexusFrontHook = {
    owner: OWNER,
    passThrough: PASS_THROUGH,
    board,
    allowPluginHook(pluginId) { return ALLOWED_PLUGIN_HOOKS.has(pluginId); },
    state() { return { ...state }; },
  };
})();