/**
 * GitHub Pages base path — /field (canonical) or /Hostess7 (legacy hub).
 */
(function (global) {
  "use strict";

  function detectBase() {
    const parts = global.location.pathname.split("/").filter(Boolean);
    if (parts[0] === "field") return "/field";
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

  function stripBase(pathname) {
    const base = BASE.replace(/\/$/, "");
    if (base && pathname.startsWith(base + "/")) return pathname.slice(base.length) || "/";
    if (base && pathname === base) return "/";
    return pathname;
  }

  global.HOSTESS7_PAGES_BASE = BASE;
  global.H7Base = withBase;
  global.H7StripBase = stripBase;
})(typeof window !== "undefined" ? window : globalThis);