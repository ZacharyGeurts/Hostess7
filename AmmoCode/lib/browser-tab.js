/**
 * AmmoCode browser tab — G16 runs in any web browser tab via loopback API.
 */
(function (global) {
  "use strict";

  const PORTS = [9555, 9477, 9556, 8080];

  async function probeApi(base) {
    try {
      const r = await fetch(`${base}/api/ammocode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "ping" }),
        signal: AbortSignal.timeout(1200),
      });
      if (!r.ok) return false;
      const j = await r.json();
      return j.ok === true || j.pong === true;
    } catch (_) {
      return false;
    }
  }

  async function resolveApiBase(explicit) {
    if (explicit) return explicit;
    const params = new URLSearchParams(location.search);
    const q = params.get("apiBase") || params.get("g16");
    if (q) return q.replace(/\/$/, "");
    const host = location.hostname || "127.0.0.1";
    if (location.protocol === "file:") {
      for (const p of PORTS) {
        const base = `http://127.0.0.1:${p}`;
        if (await probeApi(base)) return base;
      }
      return `http://127.0.0.1:${PORTS[0]}`;
    }
    const same = `${location.protocol}//${location.host}`;
    if (await probeApi(same)) return same;
    for (const p of PORTS) {
      const base = `http://${host}:${p}`;
      if (await probeApi(base)) return base;
    }
    return same;
  }

  async function boot(opts) {
    const apiBase = await resolveApiBase(opts?.apiBase);
    global.AmmoCodeG16?.config?.({
      apiBase,
      beltProfile: opts?.beltProfile || "belt_2_0",
      browserTab: true,
      pkgVersion: "Grok16-5.1.0",
    });
    document.body.dataset.acBrowserTab = "1";
    return { apiBase, ready: true };
  }

  global.AmmoCodeBrowserTab = { boot, resolveApiBase, probeApi, PORTS };
})(typeof globalThis !== "undefined" ? globalThis : window);