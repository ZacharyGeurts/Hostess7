/**
 * GitHub Pages — static AmmoCode editor (no loopback API).
 */
(function () {
  "use strict";
  var host = String(location.hostname || "");
  var pages = /github\.io$/i.test(host) || /[?&]pages=1/.test(location.search);
  if (!pages) return;

  window.AmmoCodeG16Config = {
    apiBase: "",
    pagesStatic: true,
    beltProfile: "belt_2_0",
    pkgVersion: "Grok16-5.1.0-pages",
  };

  document.documentElement.setAttribute("data-ammocode-pages", "1");
})();