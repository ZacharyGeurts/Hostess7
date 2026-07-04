/**
 * Hostess7 route cleanup — canonical desktop is /Hostess7/desktop/
 * Stale /field mirrors redirect; ALL RIGHTS RESERVED is the terms.
 */
(function (global) {
  "use strict";

  var CANONICAL =
    global.HOSTESS7_CANONICAL_DESKTOP ||
    "https://zacharygeurts.github.io/Hostess7/desktop/";
  var CANONICAL_COMMAND =
    global.HOSTESS7_CANONICAL_COMMAND ||
    "https://zacharygeurts.github.io/Hostess7/command/";

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
    if (onFieldRepo || onHostess7Field) {
      global.location.replace(CANONICAL);
      return;
    }
    if (segs[0] === "Hostess7" && segs[1] === "field-desktop") {
      global.location.replace(CANONICAL);
    }
  }

  cleanup();
})(typeof window !== "undefined" ? window : globalThis);