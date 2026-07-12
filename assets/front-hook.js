/**
 * NEXUS Front Hook — first on the board; never pass input/display hooks downstream.
 * Capture-phase ownership before plugins, OS bridges, or foreign listeners attach.
 */
(function () {
  "use strict";

  const PASS_THROUGH = false;
  const OWNER = "nexus-front-hook";
  const ADMIN_SEL = "[data-admin-shield], [data-front-hook], .fm-shell, .dns-admin-engineer, #dns-admin-portal-panel";
  const ALLOWED_PLUGIN_HOOKS = new Set(["tab-beacon", "nexus-braille-a11y", "ai-integration-hook"]);

  const state = {
    owner: OWNER,
    passThrough: PASS_THROUGH,
    boarded: false,
    eventsOwned: 0,
  };

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
    /* Own at capture — do not stopImmediatePropagation; operator UI must still type.
       Downstream OS/plugin hooks are blocked via registerClientHook gate + daemon enforce. */
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
    const block = ["xdotool", "ydotool", "dotool", "wmctrl", "__keyboardHook", "__osInputBridge"];
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
    const types = [
      "keydown", "keyup", "keypress",
      "pointerdown", "pointerup", "pointermove",
      "mousedown", "mouseup", "mousemove", "wheel",
      "touchstart", "touchend", "touchmove",
      "focusin", "focusout",
    ];
    types.forEach((type) => {
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

  function allowPluginHook(pluginId) {
    return ALLOWED_PLUGIN_HOOKS.has(pluginId);
  }

  board();

  window.NexusFrontHook = {
    owner: OWNER,
    passThrough: PASS_THROUGH,
    board,
    allowPluginHook,
    aiIntegration: function () { return window.NexusAIIntegration || null; },
    humanIntegrationAllowed: function () { return false; },
    state: function () { return { ...state }; },
  };
})();