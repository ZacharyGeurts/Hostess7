/**
 * Layer 3+ input isolation — third-party gets full window, keyboard, controllers.
 * F-keys from our stack do not steal input when layer ≥ 3 is focused.
 */
(function (global) {
  "use strict";

  const LAYER_3_MIN = 3;
  const ESCAPE_FKEY = "F12";

  function activeSovereignLayer() {
    const shell = global.NexusFieldShell?.getActiveWindow?.();
    if (shell && (shell.sovereignLayer != null || shell.userlandLayer != null)) {
      const z = shell.sovereignLayer != null ? shell.sovereignLayer : shell.userlandLayer;
      if (z >= LAYER_3_MIN) return z;
    }
    const dl = parseFloat(document.documentElement.dataset.fieldLayer || document.documentElement.dataset.fieldScreenLayer || "-1");
    if (!Number.isNaN(dl) && dl >= LAYER_3_MIN) return dl;
    return null;
  }

  function isExclusiveFocus() {
    return activeSovereignLayer() != null;
  }

  function shouldYieldInput(ev) {
    if (!isExclusiveFocus()) return false;
    if (ev && ev.key === ESCAPE_FKEY) return false;
    return true;
  }

  function applyExclusiveChrome(winEl, layer) {
    if (!winEl || layer < LAYER_3_MIN) return;
    winEl.classList.add("nfs-win--sovereign-exclusive");
    winEl.dataset.sovereignLayer = String(layer);
    winEl.dataset.fullInput = "1";
    document.documentElement.dataset.fieldLayerSovereign = "exclusive";
    document.documentElement.dataset.fieldLayer = String(layer);
  }

  function clearExclusiveChrome() {
    document.documentElement.removeAttribute("data-field-layer-sovereign");
    document.querySelectorAll(".nfs-win--sovereign-exclusive").forEach(function (el) {
      el.classList.remove("nfs-win--sovereign-exclusive");
      el.removeAttribute("data-full-input");
    });
  }

  function requestFullscreen(el) {
    const target = el || document.documentElement;
    if (target.requestFullscreen) return target.requestFullscreen();
    return Promise.resolve();
  }

  global.FieldLayerInputIsolation = {
    LAYER_3_MIN: LAYER_3_MIN,
    ESCAPE_FKEY: ESCAPE_FKEY,
    activeSovereignLayer: activeSovereignLayer,
    isExclusiveFocus: isExclusiveFocus,
    shouldYieldInput: shouldYieldInput,
    applyExclusiveChrome: applyExclusiveChrome,
    clearExclusiveChrome: clearExclusiveChrome,
    requestFullscreen: requestFullscreen,
  };
})(typeof window !== "undefined" ? window : globalThis);