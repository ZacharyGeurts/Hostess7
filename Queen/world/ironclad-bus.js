/**
 * Ironclad Bus (Queen) — AmmoOS federated search/sort via NEXUS panel :9477.
 * @g16 5.1.0 · Grok16/ironclad-secure-api · field-best-sort
 */
(function (global) {
  "use strict";

  const PANEL_ORIGIN = "http://127.0.0.1:9477";
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
    const res = await fetch(url, Object.assign({ mode: "cors", cache: "no-store" }, opts || {}));
    return res.json();
  }

  async function search(query, opts) {
    opts = opts || {};
    const q = String(query || "").trim();
    const url =
      API +
      "/search?q=" +
      encodeURIComponent(q) +
      "&context=" +
      encodeURIComponent(opts.context || "all") +
      "&limit=" +
      encodeURIComponent(opts.limit || 32);
    return fetchJson(url);
  }

  async function sort(entries, context) {
    return fetchJson(API + "/sort", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: entries || [], context: context || "registry_index" }),
    });
  }

  function hitLabel(hit) {
    return hit.title || hit.label || hit.name || hit.card_id || hit.id || hit.path || "result";
  }

  function hitUrl(hit) {
    const exec = hit.exec || hit.url || hit.href;
    if (exec) return exec;
    if (hit.path && String(hit.path).startsWith("/")) return PANEL_ORIGIN + hit.path;
    return "";
  }

  async function accessPosture() {
    return fetchJson(ACCESS);
  }

  async function h7Search(query, opts) {
    opts = opts || {};
    const q = String(query || "").trim();
    const url =
      H7 +
      "/search?q=" +
      encodeURIComponent(q) +
      "&limit=" +
      encodeURIComponent(opts.limit || 24);
    return fetchJson(url);
  }

  async function h7Resolve(bookId) {
    return fetchJson(H7 + "/resolve?book_id=" + encodeURIComponent(String(bookId || "")));
  }

  async function fileSearch(query, opts) {
    return fetchJson(ACCESS, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "file_search",
        query: query,
        limit: (opts && opts.limit) || 64,
      }),
    });
  }

  global.IroncladBus = {
    API,
    ACCESS,
    H7,
    PANEL_ORIGIN,
    search,
    sort,
    accessPosture,
    h7Search,
    h7Resolve,
    fileSearch,
    hitLabel,
    hitUrl,
    esc,
  };
})(typeof window !== "undefined" ? window : globalThis);