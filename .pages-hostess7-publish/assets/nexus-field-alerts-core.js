/**
 * NEXUS field alerts — single authoritative poll bus (above-military grade).
 * One poller, schema-validated, stale-aware, nav posture broadcast.
 */
(function (global) {
  "use strict";

  const API_ALERTS = "/api/jockey/alerts";
  const SCHEMA = "monitor-jockey-alerts/v1";
  const POLL_MS = 5000;
  const STALE_MS = 20000;

  let lastDoc = null;
  let lastOkAt = 0;
  let pollTimer = null;
  let pollInFlight = false;

  function dispatch(detail) {
    global.dispatchEvent(new CustomEvent("nexus-field-alerts", { detail }));
  }

  function updateNavPosture(doc, ok) {
    const warnHigh = String(doc?.threat_warn_level || "high").toLowerCase() === "high";
    const posture = warnHigh && !doc?.pending_count && !(doc?.jockey_alerts || []).length
      ? "alert"
      : String(doc?.posture || "calm").toLowerCase();
    const pending = doc?.pending_count ?? (doc?.jockey_alerts || []).length ?? 0;
    const h7N = doc?.h7_count ?? (doc?.alerts || []).length ?? 0;
    const harm = posture === "harm" || posture === "alert";
    const hot = warnHigh || harm || h7N > 0 || pending > 0;
    document.querySelectorAll(
      'nav.menu button[data-view="command"], nav.menu button[data-view="jockey"], .fm-rail-btn[data-tab="actions"]'
    ).forEach((btn) => {
      btn.classList.toggle("nav-alert-hot", hot);
      btn.classList.toggle("fm-rail-btn--hot", hot);
      btn.classList.toggle("nav-alert-harm", posture === "harm");
      btn.classList.toggle("fm-rail-btn--harm", posture === "harm");
      btn.classList.toggle("nav-alert-stale", !ok);
      btn.classList.toggle("fm-rail-btn--stale", !ok);
    });
    const badge = document.getElementById("fm-actions-badge");
    if (badge) {
      badge.textContent = pending > 0 ? String(pending) : "";
      badge.hidden = pending <= 0;
    }
  }

  async function poll() {
    if (document.hidden || pollInFlight) return;
    pollInFlight = true;
    try {
      const res = await fetch(API_ALERTS, { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) throw new Error(`alerts_http_${res.status}`);
      const doc = await res.json();
      if (String(doc.schema || "") !== SCHEMA) throw new Error("alerts_schema_mismatch");
      lastDoc = doc;
      lastOkAt = Date.now();
      updateNavPosture(doc, true);
      dispatch({ doc, ok: true, updated: doc.updated, stale: false });
    } catch (err) {
      const stale = !lastOkAt || Date.now() - lastOkAt > STALE_MS;
      updateNavPosture(lastDoc, false);
      dispatch({
        doc: lastDoc,
        ok: false,
        error: String(err.message || err),
        stale,
        lastOkAt,
      });
    } finally {
      pollInFlight = false;
    }
  }

  function start() {
    if (pollTimer) return;
    poll();
    pollTimer = setInterval(poll, POLL_MS);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) poll();
    });
  }

  global.NexusFieldAlerts = {
    start,
    refresh: poll,
    getLast: () => (lastDoc ? { ...lastDoc } : null),
    isStale: () => !lastOkAt || Date.now() - lastOkAt > STALE_MS,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window);