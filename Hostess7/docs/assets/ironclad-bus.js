/**
 * Ironclad Bus — AmmoOS common sort + search client for every panel and Queen surface.
 * @g16 5.1.0 · Grok16/ironclad-secure-api · field-library-registry
 */
(function (global) {
  "use strict";

  const PANEL_ORIGIN = (function () {
    try {
      const p = new URL(global.location?.href || "/Hostess7/");
      if (p.port === "9477" || p.port === "") return p.origin;
    } catch (_) {}
    return "/Hostess7";
  })();

  const API = PANEL_ORIGIN + "/api/ironclad/secure-api";
  const ACCESS = PANEL_ORIGIN + "/api/ironclad/access";
  const H7 = PANEL_ORIGIN + "/api/ironclad/h7-access";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function fetchJson(url, opts) {
    const res = await fetch(url, Object.assign({ credentials: "same-origin", cache: "no-store" }, opts || {}));
    return res.json();
  }

  async function search(query, opts) {
    opts = opts || {};
    const q = String(query || "").trim();
    const ctx = opts.context || "all";
    const limit = opts.limit || 48;
    const url =
      API +
      "/search?q=" +
      encodeURIComponent(q) +
      "&context=" +
      encodeURIComponent(ctx) +
      "&limit=" +
      encodeURIComponent(limit);
    return fetchJson(url);
  }

  async function sort(entries, context) {
    return fetchJson(API + "/sort", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: entries || [], context: context || "registry_index" }),
    });
  }

  async function sortMeta(context) {
    return fetchJson(API + "/sort?context=" + encodeURIComponent(context || "registry_index"));
  }

  async function registryIndex(context) {
    return fetchJson(API + "/registry-index?context=" + encodeURIComponent(context || "registry_index"));
  }

  function hitLabel(hit) {
    return (
      hit.title ||
      hit.label ||
      hit.name ||
      hit.card_id ||
      hit.id ||
      hit.path ||
      "result"
    );
  }

  function hitUrl(hit) {
    const exec = hit.exec || hit.url || hit.href;
    if (exec) return exec;
    if (hit.path && String(hit.path).startsWith("/")) return PANEL_ORIGIN + hit.path;
    if (hit.source === "card_catalog" && hit.card_id) return PANEL_ORIGIN + "/field-card-catalog#" + hit.card_id;
    if (hit.source === "dewey_index" && hit.id) {
      const shelf = hit.shelf || "";
      return PANEL_ORIGIN + "/library-bookshelf?shelf=" + encodeURIComponent(shelf) + "&book=" + encodeURIComponent(hit.id);
    }
    if (hit.source === "registry" && hit.id) return PANEL_ORIGIN + "/command?embed=1#library";
    return "";
  }

  async function accessPosture() {
    return fetchJson(ACCESS);
  }

  async function h7Search(query, opts) {
    opts = opts || {};
    const q = String(query || "").trim();
    return fetchJson(H7 + "/search?q=" + encodeURIComponent(q) + "&limit=" + encodeURIComponent(opts.limit || 24));
  }

  async function h7Resolve(bookId) {
    return fetchJson(H7 + "/resolve?book_id=" + encodeURIComponent(String(bookId || "")));
  }

  async function fileSearch(query, opts) {
    return fetchJson(ACCESS, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "file_search", query: query, limit: (opts && opts.limit) || 64 }),
    });
  }

  global.IroncladBus = {
    API,
    ACCESS,
    H7,
    PANEL_ORIGIN,
    search,
    sort,
    sortMeta,
    registryIndex,
    accessPosture,
    h7Search,
    h7Resolve,
    fileSearch,
    hitLabel,
    hitUrl,
    esc,
  };
})(typeof window !== "undefined" ? window : globalThis);