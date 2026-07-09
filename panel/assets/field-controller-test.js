/**
 * Deprecated — controller setup lives in Queen Room arcade deck only.
 * @see Queen/world/queen-controller-setup.js
 */
(function (global) {
  "use strict";
  const CANONICAL = "/queen-game-room.html#arcade";
  global.FieldControllerTest = {
    mount: function () {
      location.replace(CANONICAL);
    },
    wire: function () {
      location.replace(CANONICAL);
    },
    poll: function () {},
    ingest: function () {},
  };
})(typeof window !== "undefined" ? window : globalThis);