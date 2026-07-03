/**
 * GitHub Pages base path — /field (canonical) or /Hostess7 (legacy hub).
 */
(function (global) {
  "use strict";

  function detectBase() {
    const parts = global.location.pathname.split("/").filter(Boolean);
    if (parts[0] === "command") return "/command";
    if (parts[0] === "field") return "/field";
    if (parts[0] === "Hostess7") return "/Hostess7";
    if (parts.length === 0) return "";
    return "/" + parts[0];
  }

  const BASE = detectBase();
  const ASSET_HOST = BASE === "/command" ? "/Hostess7" : BASE;

  function withBase(path) {
    const p = String(path || "");
    if (!p.startsWith("/") || p.startsWith("//")) return p;
    if (p.startsWith("/api/") || p.startsWith("/assets/")) {
      return (ASSET_HOST || "") + p;
    }
    return (BASE || "") + p;
  }

  function stripBase(pathname) {
    const base = BASE.replace(/\/$/, "");
    if (base && pathname.startsWith(base + "/")) return pathname.slice(base.length) || "/";
    if (base && pathname === base) return "/";
    return pathname;
  }

  global.HOSTESS7_PAGES_BASE = BASE;
  global.H7_ASSET_HOST = ASSET_HOST;
  global.H7Base = withBase;
  global.H7Api = function (path) {
    return withBase(String(path || "").startsWith("/") ? path : "/" + path);
  };
  global.H7Page = function (path) {
    const p = String(path || "");
    if (p.startsWith("http")) return p;
    if (p.startsWith("/")) return (BASE || "") + p;
    return (BASE ? BASE + "/" : "/") + p;
  };
  global.H7StripBase = stripBase;
  global.NEXUS_C2_BASEMENT = BASE === "/command";
})(typeof window !== "undefined" ? window : globalThis);