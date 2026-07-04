/**
 * Battle Stations — general quarters on every GitHub Pages surface.
 */
(function () {
  "use strict";

  document.documentElement.dataset.battleStations = "1";
  if (document.body) document.body.dataset.battleStations = "1";

  function reinforce() {
    if (window.FieldHostDesktop?.refresh) {
      window.FieldHostDesktop.refresh().catch(function () {
        window.FieldHostDesktop?.ensureStartbar?.();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.setTimeout(reinforce, 600);
      window.setTimeout(reinforce, 2000);
    });
  } else {
    window.setTimeout(reinforce, 600);
  }
})();