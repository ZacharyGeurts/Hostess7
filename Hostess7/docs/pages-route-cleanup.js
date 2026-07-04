/**
 * Hostess7 route cleanup — canonical desktop is sovereign AmmoDrive on loopback,
 * Pages mirror at /Hostess7/desktop/. Stale /field repo FIRED.
 */
(function (global) {
  "use strict";

  var LOOPBACK = global.H7_LOOPBACK_AUTHORITY || global.ZACHUB_LOOPBACK || "http://127.0.0.1:9477";
  var ON_LOOPBACK =
    global.location &&
    (global.location.hostname === "127.0.0.1" || global.location.hostname === "localhost");

  var CANONICAL =
    global.HOSTESS7_CANONICAL_DESKTOP ||
    (ON_LOOPBACK ? LOOPBACK + "/field" : "https://zacharygeurts.github.io/Hostess7/desktop/");
  var CANONICAL_COMMAND =
    global.HOSTESS7_CANONICAL_COMMAND ||
    (ON_LOOPBACK ? LOOPBACK + "/command/" : "https://zacharygeurts.github.io/Hostess7/command/");
  var SOVEREIGN =
    global.ZACHUB_SOVEREIGN_DESKTOP || global.HOSTESS7_SOVEREIGN_DESKTOP || LOOPBACK + "/field";

  function parts() {
    return global.location.pathname.split("/").filter(Boolean);
  }

  function cleanup() {
    var segs = parts();
    var host = global.location.hostname || "";
    var onFieldRepo =
      segs[0] === "field" &&
      host.indexOf("github.io") >= 0 &&
      segs.indexOf("Hostess7") < 0;
    var onHostess7Field =
      segs[0] === "Hostess7" && segs[1] === "field" && segs.length === 2;
    var onHostess7FieldDesktop =
      segs[0] === "Hostess7" && segs[1] === "field-desktop";
    if (onFieldRepo || onHostess7Field || onHostess7FieldDesktop) {
      global.location.replace(ON_LOOPBACK ? SOVEREIGN : CANONICAL);
      return;
    }
    if (ON_LOOPBACK && segs[0] === "Hostess7" && segs[1] === "desktop" && segs.length === 2) {
      global.location.replace(SOVEREIGN);
    }
  }

  global.HOSTESS7_ROUTE_CLEANUP = {
    canonical: CANONICAL,
    sovereign: SOVEREIGN,
    command: CANONICAL_COMMAND,
    cleanup: cleanup,
  };

  cleanup();
})(typeof window !== "undefined" ? window : globalThis);