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

  const LOOPBACK = "http://127.0.0.1:9477";
  const ON_LOOPBACK =
    typeof global.location !== "undefined" &&
    (global.location.hostname === "127.0.0.1" || global.location.hostname === "localhost");

  global.HOSTESS7_PAGES_BASE = BASE;
  global.H7_LOOPBACK_AUTHORITY = LOOPBACK;
  global.ZACHUB_LOOPBACK = LOOPBACK;
  global.HOSTESS7_SOVEREIGN_DESKTOP = LOOPBACK + "/field";
  global.ZACHUB_SOVEREIGN_DESKTOP = LOOPBACK + "/field";
  global.HOSTESS7_CANONICAL_DESKTOP = ON_LOOPBACK
    ? LOOPBACK + "/field"
    : "https://zacharygeurts.github.io/Hostess7/desktop/";
  global.HOSTESS7_CANONICAL_COMMAND = ON_LOOPBACK
    ? LOOPBACK + "/command/"
    : "https://zacharygeurts.github.io/Hostess7/command/";
  global.HOSTESS7_CANONICAL_ROOT = ON_LOOPBACK
    ? LOOPBACK + "/field"
    : "https://zacharygeurts.github.io/Hostess7/";
  global.AMMODRIVE_CANONICAL_ROOT = global.HOSTESS7_CANONICAL_ROOT;
  global.AMMODRIVE_CANONICAL_DESKTOP = ON_LOOPBACK
    ? LOOPBACK + "/field"
    : "https://zacharygeurts.github.io/Hostess7/desktop/";
  global.AMMODRIVE_PAGES_API = (ASSET_HOST || BASE || "") + "/api/ammodrive-public";
  global.AMMODRIVE_PRODUCT = "AmmoDrive";
  global.AMMODRIVE_LEGACY_PRODUCT = "ZacHub";
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

  if (!global.fetch && global.XMLHttpRequest) {
    global.fetch = function (input, opts) {
      opts = opts || {};
      return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        var url = typeof input === "string" ? input : (input && input.url) || "";
        xhr.open(opts.method || "GET", url, true);
        if (opts.headers) {
          Object.keys(opts.headers).forEach(function (k) {
            xhr.setRequestHeader(k, opts.headers[k]);
          });
        }
        xhr.onreadystatechange = function () {
          if (xhr.readyState !== 4) return;
          resolve({
            ok: xhr.status >= 200 && xhr.status < 300,
            status: xhr.status,
            json: function () {
              return Promise.resolve(JSON.parse(xhr.responseText || "{}"));
            },
            text: function () {
              return Promise.resolve(xhr.responseText || "");
            },
          });
        };
        xhr.onerror = function () { reject(new Error("network")); };
        xhr.send(opts.body || null);
      });
    };
  }
  if (typeof document !== "undefined" && document.documentElement) {
    document.documentElement.dataset.battleStations = "1";
    document.documentElement.dataset.zachubCanonical = ON_LOOPBACK ? "sovereign" : "pages";
    document.documentElement.dataset.ammodriveProduct = "AmmoDrive";
    document.documentElement.dataset.ammodriveLane = ON_LOOPBACK ? "sovereign" : "pages";
    if (document.body) document.body.dataset.battleStations = "1";
  }

  function loadZachubRouter() {
    if (typeof document === "undefined") return;
    var src = (ASSET_HOST || BASE || "") + "/assets/zachub-source-router.js";
    if (!src.startsWith("/")) src = "/" + src;
    if (document.querySelector('script[src*="zachub-source-router"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    (document.head || document.documentElement).appendChild(s);
  }
  loadZachubRouter();
})(typeof window !== "undefined" ? window : globalThis);