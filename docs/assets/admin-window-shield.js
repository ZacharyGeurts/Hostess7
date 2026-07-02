/**
 * Admin window shield — front hook layer; anti-capture, anti-pry on operator admin UI.
 * Requires front-hook.js boarded first — never pass hooks downstream.
 */
(function () {
  "use strict";

  if (window.NexusFrontHook && typeof window.NexusFrontHook.board === "function") {
    window.NexusFrontHook.board();
  }

  const ROOT_SEL = "[data-admin-shield], [data-front-hook], .fm-shell, .dns-admin-engineer, #dns-admin-portal-panel, .update-sudo-zone";
  const STYLE_ID = "nexus-admin-shield-style";

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const css = document.createElement("style");
    css.id = STYLE_ID;
    css.textContent = `
      #nexus-admin-shield-veil {
        position: fixed; inset: 0; z-index: 2147483646;
        background: #000; opacity: 0.98; pointer-events: none;
        transition: opacity 0.12s ease;
      }
      #nexus-admin-shield-veil.hidden { opacity: 0; visibility: hidden; }
      [data-admin-shield] input[type="password"],
      [data-admin-shield] .admin-secret {
        -webkit-text-security: disc;
        user-select: none;
      }
      .fm-shell.admin-shield-active { isolation: isolate; }
    `;
    document.head.appendChild(css);
  }

  function veil() {
    let el = document.getElementById("nexus-admin-shield-veil");
    if (!el) {
      el = document.createElement("div");
      el.id = "nexus-admin-shield-veil";
      el.setAttribute("aria-hidden", "true");
      document.body.appendChild(el);
    }
    return el;
  }

  function setVeil(on) {
    const v = veil();
    v.classList.toggle("hidden", !on);
    document.documentElement.classList.toggle("admin-shield-veiled", !!on);
  }

  function inAdminSurface(target) {
    if (!target || !target.closest) return false;
    return !!target.closest(ROOT_SEL);
  }

  function blockClipboard(ev) {
    if (!inAdminSurface(ev.target)) return;
    ev.preventDefault();
    ev.stopPropagation();
  }

  function blockContextMenu(ev) {
    if (!inAdminSurface(ev.target)) return;
    ev.preventDefault();
  }

  function onVisibility() {
    setVeil(document.hidden);
  }

  function onBlur() {
    if (!document.hasFocus()) setVeil(true);
  }

  function onFocus() {
    if (document.hasFocus() && !document.hidden) setVeil(false);
  }

  function onPrintScreen(ev) {
    if (ev.key === "PrintScreen" || ev.code === "PrintScreen") {
      setVeil(true);
      setTimeout(() => { if (document.hasFocus() && !document.hidden) setVeil(false); }, 2500);
    }
  }

  function stripDangerousGlobals() {
    try {
      if (typeof window.xdotool === "object") delete window.xdotool;
      if (typeof window.ydotool === "object") delete window.ydotool;
    } catch (_) { /* sealed */ }
  }

  function markAdminNodes() {
    document.querySelectorAll(".fm-shell, .dns-admin-engineer, #dns-admin-portal-panel").forEach((n) => {
      n.setAttribute("data-admin-shield", "1");
      n.setAttribute("data-front-hook", "nexus");
    });
    const shell = document.querySelector(".fm-shell");
    if (shell) shell.classList.add("admin-shield-active");
  }

  function init() {
    injectStyles();
    markAdminNodes();
    stripDangerousGlobals();
    setVeil(document.hidden);

    document.addEventListener("visibilitychange", onVisibility, true);
    window.addEventListener("blur", onBlur, true);
    window.addEventListener("focus", onFocus, true);
    document.addEventListener("contextmenu", blockContextMenu, true);
    document.addEventListener("copy", blockClipboard, true);
    document.addEventListener("cut", blockClipboard, true);
    document.addEventListener("keydown", onPrintScreen, true);

    if (navigator.clipboard && navigator.clipboard.readText) {
      const orig = navigator.clipboard.readText.bind(navigator.clipboard);
      navigator.clipboard.readText = function () {
        return Promise.reject(new DOMException("Admin shield: clipboard read blocked", "NotAllowedError"));
      };
      void orig;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.NexusAdminWindowShield = { setVeil, refresh: markAdminNodes };
})();