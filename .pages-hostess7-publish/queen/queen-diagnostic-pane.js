/**
 * Queen diagnostic pane — frameless JSON/API viewer for dashboard thumbnails.
 */
(function () {
  "use strict";

  const params = new URLSearchParams(location.search);
  const apiPath = params.get("api") || "/api/field-sanity";
  const usePanel = params.get("panel") === "1" || params.get("panel") === "true";
  const chromeless = params.get("chromeless") === "1" || params.get("chromeless") === "true";
  const refreshMs = Math.max(0, parseInt(params.get("refresh") || "0", 10) || 0);
  const title = params.get("title") || apiPath.replace(/^\/api\//, "").replace(/\?.*$/, "");
  if (chromeless) document.documentElement.classList.add("qdp-chromeless");

  function panelPort() {
    try {
      return window.parent?.document?.body?.dataset?.nexusPanelPort || "9477";
    } catch {
      return "9477";
    }
  }

  function apiUrl() {
    if (apiPath.startsWith("http")) return apiPath;
    const base = usePanel
      ? `http://127.0.0.1:${panelPort()}`
      : location.origin;
    return base + (apiPath.startsWith("/") ? apiPath : `/${apiPath}`);
  }

  function verdict(doc) {
    if (!doc || typeof doc !== "object") return { text: "—", cls: "" };
    if (doc.ok === false || doc.error) return { text: doc.error || "HOLD", cls: "bad" };
    const v =
      doc.verdict ||
      doc.queen_verdict ||
      doc.classification?.verdict ||
      (doc.gate_ok === false ? "GATE_HOLD" : null) ||
      (doc.ok === true ? "OK" : null);
    if (!v) return { text: "LIVE", cls: "ok" };
    const s = String(v).toUpperCase();
    if (/BLOCK|HOLD|FAIL|CRIT|QUARANT/.test(s)) return { text: v, cls: "bad" };
    if (/WARN|DEFER|YELLOW/.test(s)) return { text: v, cls: "warn" };
    return { text: v, cls: "ok" };
  }

  async function load() {
    const body = document.getElementById("qdp-body");
    const ver = document.getElementById("qdp-verdict");
    const head = document.getElementById("qdp-title");
    if (head) head.textContent = title;
    try {
      const r = await fetch(apiUrl(), { cache: "no-store" });
      const text = await r.text();
      let doc;
      try {
        doc = JSON.parse(text);
        body.textContent = JSON.stringify(doc, null, 2);
      } catch {
        doc = { raw: text.slice(0, 8000) };
        body.textContent = text.slice(0, 12000);
      }
      const vd = verdict(doc);
      if (ver) {
        ver.textContent = vd.text;
        ver.className = "qdp-verdict " + (vd.cls || "");
      }
    } catch (e) {
      if (body) body.textContent = String(e);
      if (ver) {
        ver.textContent = "UNREACHABLE";
        ver.className = "qdp-verdict bad";
      }
    }
  }

  document.getElementById("qdp-refresh")?.addEventListener("click", load);
  load();
  if (refreshMs > 0) setInterval(load, refreshMs);
})();