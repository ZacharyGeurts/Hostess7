/**
 * Field Nav Spine — AmmoOS hub; every program flows out from /field and flows back.
 * @g16 5.1.0 · Grok16/field-stack-fabric · ironclad-secure-api
 */
(function (global) {
  "use strict";

  const PANEL_HOME = "/field";
  const QUEEN_HOME = "http://127.0.0.1:9481/world/browser.html";

  function panelOrigin() {
    return global.IroncladBus?.PANEL_ORIGIN || "http://127.0.0.1:9477";
  }

  function isHome() {
    const path = global.location?.pathname || "";
    return path === "/field" || path === "/field/" || path === "/" || path.endsWith("/browser.html");
  }

  function backUrl() {
    if (global.location?.port === "9481") return QUEEN_HOME;
    const ref = document.referrer || "";
    if (ref.includes(":9477/field")) return PANEL_HOME;
    return panelOrigin() + PANEL_HOME;
  }

  function ensureStyles() {
    if (document.getElementById("fns-style")) return;
    const link = document.createElement("link");
    link.id = "fns-style";
    link.rel = "stylesheet";
    link.href = "/assets/field-nav-spine.css?v=1";
    document.head.appendChild(link);
  }

  function mountTopBar() {
    if (isHome() || document.getElementById("fns-bar") || document.body?.dataset?.noNavSpine === "1") return;
    ensureStyles();
    const bar = document.createElement("header");
    bar.id = "fns-bar";
    bar.className = "fns-bar";
    bar.setAttribute("aria-label", "AmmoOS navigation");
    bar.innerHTML =
      '<a class="fns-back" href="' +
      backUrl() +
      '">← AmmoOS</a>' +
      '<span class="fns-title">' +
      (document.title || "Program") +
      "</span>" +
      '<a class="fns-queen" href="' +
      QUEEN_HOME +
      '" title="Queen Browser">Queen</a>';
    document.body.insertBefore(bar, document.body.firstChild);
    document.body.classList.add("fns-pad-top");
  }

  function loadIroncladChain() {
    if (global.IroncladBus && global.FieldIroncladTaskbar) return;
    const base = global.location?.port === "9481" ? panelOrigin() + "/assets/" : "/assets/";
    const chain = ["ironclad-bus.js", "field-ironclad-taskbar.js"];
    chain.forEach(function (file) {
      if (document.querySelector('script[src*="' + file + '"]')) return;
      const s = document.createElement("script");
      s.src = base + file + "?v=1";
      s.defer = true;
      document.head.appendChild(s);
    });
    if (!document.querySelector('link[href*="field-ironclad-taskbar.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = base + "field-ironclad-taskbar.css?v=1";
      document.head.appendChild(link);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    mountTopBar();
    if (document.body?.dataset?.ironcladTaskbar !== "0") loadIroncladChain();
  });

  global.FieldNavSpine = { mountTopBar, backUrl, panelOrigin, PANEL_HOME, QUEEN_HOME };
})(typeof window !== "undefined" ? window : globalThis);