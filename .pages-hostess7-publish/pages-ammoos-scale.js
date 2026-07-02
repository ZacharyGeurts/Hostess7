/**
 * AmmoOS C2 desktop — apply 125% UI (+25%) on load. Does not affect Queen Browser.
 */
(function () {
  "use strict";

  var DESKTOP_SCALE = 125;
  var DESKTOP_ICON = 63;

  function applyEarly() {
    var root = document.documentElement;
    root.dataset.ammoosDesktop = "1";
    if (window.FieldDesktopScale && window.FieldDesktopScale.apply) {
      window.FieldDesktopScale.apply(
        { ui_scale: DESKTOP_SCALE, desktop_icon_size: DESKTOP_ICON },
        { silent: true }
      );
      return;
    }
    var scale = DESKTOP_SCALE / 100;
    root.classList.add("fds-scaled", "fds-quality");
    root.dataset.desktopScale = String(DESKTOP_SCALE);
    root.style.setProperty("--fds-scale", String(scale));
    root.style.setProperty("--fds-ui-scale-pct", String(DESKTOP_SCALE));
    root.style.setProperty("--fsb-h", Math.round(44 * scale) + "px");
    root.style.setProperty("--hd-icon-size", DESKTOP_ICON + "px");
    root.style.setProperty("--fds-base-font", Math.round(16 * scale) + "px");
    root.style.fontSize = Math.round(16 * scale) + "px";
  }

  applyEarly();
  document.addEventListener("DOMContentLoaded", applyEarly);
})();