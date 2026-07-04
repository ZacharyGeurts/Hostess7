/**
 * AmmoOS 2.0 Pages — desktop lands with icons; Queen launches from icon only (no auto-window).
 */
(function () {
  "use strict";

  if (document.body) document.body.dataset.pagesRuntime = "1";
  document.documentElement.dataset.h7Boss = "hostess7";
  document.documentElement.dataset.h7InteractionLane = "hostess7-github";
  document.documentElement.dataset.battleStations = "1";
  if (document.body) document.body.dataset.battleStations = "1";

  function bootDesktop() {
    if (document.body) document.body.dataset.pagesRuntime = "1";
    if (window.FieldHostDesktop?.refresh) {
      window.FieldHostDesktop.refresh().catch(function () {
        window.FieldHostDesktop?.ensureStartbar?.();
      });
    } else {
      window.setTimeout(bootDesktop, 120);
    }
  }

  function ensureStartVisible() {
    if (document.getElementById("fsb-start")) return;
    window.FieldHostDesktop?.ensureStartbar?.();
    if (!document.getElementById("fsb-start") && window.FieldHostDesktop?.refresh) {
      window.FieldHostDesktop.refresh().catch(function () {});
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      bootDesktop();
      window.setTimeout(ensureStartVisible, 800);
      window.setTimeout(ensureStartVisible, 2200);
    });
  } else {
    bootDesktop();
    window.setTimeout(ensureStartVisible, 800);
  }
})();