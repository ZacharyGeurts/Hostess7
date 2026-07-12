/**
 * GitHub resilience wire — loopback authority when github.com push lane is down.
 * Pages/raw mirrors stay open; publish queues until ssh route returns.
 */
(function (global) {
  "use strict";

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    const base = (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
    return base + (path.startsWith("/") ? path : "/" + path);
  }

  function loopbackBase() {
    return (global.H7_LOOPBACK_AUTHORITY || "http://127.0.0.1:9477").replace(/\/$/, "");
  }

  async function probeResilience() {
    try {
      const r = await fetch(api("/api/field-github-resilience"), { cache: "no-store", credentials: "same-origin" });
      if (r.ok) return r.json();
    } catch (_) {}
    try {
      const r = await fetch(loopbackBase() + "/api/field-github-resilience", { cache: "no-store" });
      if (r.ok) return r.json();
    } catch (_) {}
    return {
      ok: true,
      degraded_ok: true,
      authority: loopbackBase(),
      github_push_ready: false,
    };
  }

  function authorityUrl(path) {
    const doc = global.H7_GITHUB_RESILIENCE || {};
    const base = (doc.authority || loopbackBase()).replace(/\/$/, "");
    const p = String(path || "").startsWith("/") ? path : "/" + (path || "");
    return base + p;
  }

  function wire() {
    global.H7_GITHUB_RESILIENCE = {
      probe: probeResilience,
      authorityUrl: authorityUrl,
      loopback: loopbackBase,
    };
    probeResilience().then(function (doc) {
      global.H7_GITHUB_RESILIENCE = Object.assign(global.H7_GITHUB_RESILIENCE, doc);
      if (doc.authority) global.H7_LOOPBACK_AUTHORITY = doc.authority;
      if (document.body) {
        document.body.dataset.h7GithubResilience = doc.github_push_ready ? "push" : "degraded";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);