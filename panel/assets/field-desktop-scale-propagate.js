/**
 * Propagate AmmoOS desktop UI scale to panel program iframes (not Queen Browser).
 */
(function (global) {
  "use strict";

  const MSG = "nexus:desktop-scale";

  function isQueenBrowserUrl(url) {
    if (!url) return false;
    const u = String(url).toLowerCase();
    return u.includes("/queen/browser") || u.includes("/world/browser") || u.includes("browser.html");
  }

  function broadcast(pct) {
    const scale = pct / 100;
    document.querySelectorAll(".nfs-win iframe").forEach(function (frame) {
      if (isQueenBrowserUrl(frame.src)) return;
      try {
        frame.contentWindow?.postMessage({ type: MSG, ui_scale: pct, scale: scale }, "*");
      } catch (_) {}
    });
  }

  function applyReceiver() {
    if (global.__H7_SCALE_RECEIVER__) return;
    global.__H7_SCALE_RECEIVER__ = true;
    global.addEventListener("message", function (ev) {
      const d = ev.data;
      if (!d || d.type !== MSG) return;
      const pct = parseInt(d.ui_scale, 10);
      if (!Number.isFinite(pct)) return;
      if (global.FieldDesktopScale?.apply) {
        global.FieldDesktopScale.apply({ ui_scale: pct }, { silent: true });
      }
    });
  }

  function wire(shell) {
    applyReceiver();
    const origRender = shell && shell._scaleOrigRender;
    if (!origRender && global.NexusFieldShell) {
      const nfs = global.NexusFieldShell;
      if (!nfs._scaleHooked && typeof global.FieldShellContext !== "undefined") {
        nfs._scaleHooked = true;
      }
    }
    function pulse() {
      const pct =
        parseInt(document.documentElement.dataset.desktopScale, 10) ||
        global.FieldDesktopScale?.DEFAULT_PCT ||
        125;
      broadcast(pct);
    }
    pulse();
    document.addEventListener("DOMContentLoaded", pulse);
    global.addEventListener("message", function (ev) {
      if (ev.data?.type === "nexus:settings" && ev.data.settings?.ui_scale) {
        broadcast(ev.data.settings.ui_scale);
      }
    });
    const obs = new MutationObserver(function () {
      pulse();
    });
    const root = document.getElementById("nfs-root");
    if (root) obs.observe(root, { childList: true, subtree: true });
    global.FieldDesktopScalePropagate = { broadcast: broadcast, wire: wire };
  }

  if (document.documentElement.dataset.ammoosDesktop === "1" || document.getElementById("nfs-root")) {
    wire();
  } else {
    document.addEventListener("DOMContentLoaded", wire);
  }
})(window);