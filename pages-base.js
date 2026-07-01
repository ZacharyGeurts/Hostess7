/**
 * GitHub Pages base path — /Hostess7 on project sites, / on user sites.
 */
(function (global) {
  "use strict";

  function detectBase() {
    const parts = global.location.pathname.split("/").filter(Boolean);
    if (parts[0] === "Hostess7") return "/Hostess7";
    if (parts.length === 0) return "";
    return "/" + parts[0];
  }

  const BASE = detectBase();

  function withBase(path) {
    const p = String(path || "");
    if (!p.startsWith("/") || p.startsWith("//")) return p;
    return (BASE || "") + p;
  }

  global.HOSTESS7_PAGES_BASE = BASE;
  global.H7Base = withBase;

  const origFetch = global.fetch.bind(global);
  global.fetch = function (input, opts) {
    let url = typeof input === "string" ? input : input.url;
    try {
      const u = new URL(url, global.location.origin);
      if (u.origin === global.location.origin && u.pathname.startsWith("/api/")) {
        url = withBase(u.pathname) + u.search;
        input = typeof input === "string" ? url : new Request(url, input);
      } else if (u.origin === global.location.origin && u.pathname === "/health") {
        url = withBase("/api/health.json");
        input = typeof input === "string" ? url : new Request(url, input);
      }
    } catch (_e) {
      /* relative */
    }
    return origFetch(input, opts);
  };
})(typeof window !== "undefined" ? window : globalThis);