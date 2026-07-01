/** @deprecated Use queen-os.js — thin delegate for backward compatibility */
(function () {
  "use strict";
  if (globalThis.QueenOS) return;
  const s = document.createElement("script");
  s.src = "queen-os.js";
  document.head.appendChild(s);
})();