(function () {
  "use strict";
  function pagesBase() {
    return document.body?.dataset?.pagesRuntime === "1" || window.HOSTESS7_PAGES_BASE
      ? window.HOSTESS7_PAGES_BASE || "/Hostess7"
      : "";
  }
  function fixLinks() {
    const base = pagesBase();
    if (!base) return;
    ["aw-local-updater", "aw-desktop", "aw-ironclad"].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      const href = el.getAttribute("href") || "";
      if (href.startsWith("/")) el.setAttribute("href", base + href);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fixLinks);
  else fixLinks();
})();