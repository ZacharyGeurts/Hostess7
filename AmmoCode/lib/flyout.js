/**
 * AmmoCode 2027 — activity-bar flyout client menu.
 */
(function (global) {
  "use strict";

  const panels = ["collab", "network", "security", "combinatorics", "znetwork", "files"];
  let active = null;

  function $(id) {
    return document.getElementById(id);
  }

  function setActive(panel) {
    active = panel;
    panels.forEach((p) => {
      const btn = $(`ac-act-${p}`);
      const fly = $(`ac-flyout-${p}`);
      if (btn) btn.classList.toggle("active", p === panel);
      if (fly) fly.hidden = p !== panel;
    });
    const side = $("ac-sidebar");
    if (side) side.dataset.open = panel ? "1" : "0";
    if (panel === "znetwork") {
      global.AmmoCodeZNetwork?.renderFlyout?.($("ac-flyout-znetwork"));
    }
    if (panel === "network") {
      global.AmmoCodeNetwork?.renderPanel?.($("ac-flyout-network"));
    }
  }

  function toggle(panel) {
    setActive(active === panel ? null : panel);
  }

  function bind() {
    panels.forEach((p) => {
      $(`ac-act-${p}`)?.addEventListener("click", () => toggle(p));
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setActive(null);
    });
  }

  function init() {
    bind();
    setActive(null);
  }

  global.AmmoCodeFlyout = { init, setActive, toggle, panels };
})(typeof globalThis !== "undefined" ? globalThis : window);