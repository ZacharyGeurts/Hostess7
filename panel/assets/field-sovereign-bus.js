/**
 * Field Sovereign Bus — single /api/sovereign-time witness on every fetch.
 * Slowdowns ≥ policy_ms are threats; confirmations gate sensitive actions.
 */
(function (global) {
  "use strict";

  const STAMP_API = "/api/sovereign-time";
  const SLOW_MS = 800;

  const state = {
    lastAt: "",
    lastMs: 0,
    threats: 0,
    policyMs: SLOW_MS,
  };

  function shortUtc(doc) {
    const t = doc?.derived_utc || doc?.sovereign_at || "";
    return t.length >= 19 ? t.slice(11, 19) : t || "—";
  }

  async function stamp(action, elapsedMs, ok, detail) {
    try {
      const res = await fetch(STAMP_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action,
          elapsed_ms: elapsedMs,
          ok: ok !== false,
          detail: detail || "",
        }),
        credentials: "same-origin",
      });
      const doc = await res.json();
      state.lastAt = doc.derived_utc || doc.sovereign_at || state.lastAt;
      state.lastMs = doc.elapsed_ms != null ? doc.elapsed_ms : elapsedMs;
      if (doc.policy_ms) state.policyMs = doc.policy_ms;
      if (doc.threat || doc.confirm_required) {
        state.threats += 1;
        const msg =
          "Sovereign slowdown · " +
          Math.round(elapsedMs) +
          "ms ≥ " +
          (doc.policy_ms || SLOW_MS) +
          "ms · " +
          (action || "api");
        if (doc.confirm_required && !global.__SOVEREIGN_SKIP_CONFIRM__) {
          const okConfirm = global.confirm(msg + "\n\nContinue? (threat witness logged)");
          if (!okConfirm) throw new Error("sovereign_confirm_denied");
        } else if (global.FieldHostDesktop?.toast) {
          global.FieldHostDesktop.toast(msg);
        }
      }
      return doc;
    } catch (e) {
      if (e.message === "sovereign_confirm_denied") throw e;
      return { ok: false, error: String(e.message || e) };
    }
  }

  async function sovereignFetch(input, init) {
    const url = typeof input === "string" ? input : input.url;
    const action = (init && init.sovereignAction) || url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    const t0 = performance.now();
    const res = await fetch(input, init);
    const elapsed = performance.now() - t0;
    await stamp(action, elapsed, res.ok, res.status + "");
    return res;
  }

  async function timeStatus() {
    const res = await fetch(STAMP_API, { credentials: "same-origin", cache: "no-store" });
    return res.json();
  }

  function mountChip(el) {
    if (!el) return;
    timeStatus()
      .then(function (doc) {
        el.textContent = shortUtc(doc);
        el.title = "Sovereign · " + (doc.derived_utc || "") + " · policy " + (doc.max_skew_ms || "—") + "ms skew";
      })
      .catch(function () {
        el.textContent = "—";
      });
  }

  global.FieldSovereignBus = {
    fetch: sovereignFetch,
    stamp: stamp,
    status: timeStatus,
    mountChip: mountChip,
    state: function () { return Object.assign({}, state); },
    shortUtc: shortUtc,
  };
})(typeof window !== "undefined" ? window : globalThis);