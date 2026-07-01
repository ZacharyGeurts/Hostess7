/**
 * Queen Field Chrome — AmmoOS nav spine + Ironclad taskbar on Queen program pages.
 * @g16 5.1.0 · Grok16/field-stack-fabric · ironclad-secure-api
 */
(function (global) {
  "use strict";

  const PANEL_HOME = "http://127.0.0.1:9477/field";
  const QUEEN_HOME = "/world/browser.html";

  function isHome() {
    const p = global.location?.pathname || "";
    return p.endsWith("/browser.html") || p.endsWith("/queen-desktop.html");
  }

  function mountNav() {
    if (isHome() || document.getElementById("qfc-nav") || document.body?.dataset?.noQueenChrome === "1") return;
    const bar = document.createElement("header");
    bar.id = "qfc-nav";
    bar.className = "qfc-nav";
    bar.innerHTML =
      '<a class="qfc-back" href="' +
      PANEL_HOME +
      '" target="_top">← AmmoOS</a>' +
      '<span class="qfc-title">' +
      (document.title || "Queen") +
      '</span><a class="qfc-queen" href="' +
      QUEEN_HOME +
      '" target="_top">Queen Home</a>';
    if (!document.getElementById("qfc-nav-style")) {
      const st = document.createElement("style");
      st.id = "qfc-nav-style";
      st.textContent =
        ".qfc-nav{position:fixed;top:0;left:0;right:0;z-index:9000;height:34px;display:flex;align-items:center;gap:10px;padding:0 10px;background:rgba(4,8,6,.94);border-bottom:1px solid rgba(61,214,140,.25);font:12px system-ui,sans-serif;color:#e8f2ea}" +
        "body.qfc-pad{padding-top:34px}.qfc-back{color:#3dd68c;text-decoration:none;font-weight:600}.qfc-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#8aa896}.qfc-queen{color:#e8a0c8;text-decoration:none;font-size:11px}";
      document.head.appendChild(st);
    }
    document.body.insertBefore(bar, document.body.firstChild);
    document.body.classList.add("qfc-pad");
  }

  function mountTaskbar() {
    if (document.getElementById("fitb-mount") || document.getElementById("qd-taskbar-start")) return;
    if (!global.IroncladBus || !global.FieldIroncladTaskbar?.mountStandalone) return;
    if (!document.hasFocus()) return;
    global.FieldIroncladTaskbar.mountStandalone();
  }

  function loadPanelTaskbar() {
    if (document.querySelector('script[src*="field-ironclad-taskbar.js"]')) {
      mountTaskbar();
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = global.IroncladBus.PANEL_ORIGIN + "/assets/field-ironclad-taskbar.css?v=1";
    document.head.appendChild(link);
    const s = document.createElement("script");
    s.src = global.IroncladBus.PANEL_ORIGIN + "/assets/field-ironclad-taskbar.js?v=1";
    s.defer = true;
    s.onload = mountTaskbar;
    document.head.appendChild(s);
  }

  document.addEventListener("DOMContentLoaded", function () {
    mountNav();
    if (!document.querySelector('script[src*="ironclad-bus.js"]')) {
      const s = document.createElement("script");
      s.src = "ironclad-bus.js";
      s.defer = true;
      s.onload = loadPanelTaskbar;
      document.head.appendChild(s);
    } else {
      loadPanelTaskbar();
    }
  });

  global.QueenFieldChrome = { mountNav, PANEL_HOME, QUEEN_HOME };
})(typeof window !== "undefined" ? window : globalThis);