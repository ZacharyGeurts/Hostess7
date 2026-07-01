/**
 * Static GitHub Pages shim — intercepts /api/* before network (fixes /Hostess7 subpath).
 */
(function (global) {
  const LOOPBACK = "http://127.0.0.1:8080";

  function apiPath(pathname) {
    if (global.H7StripBase) return global.H7StripBase(pathname);
    return pathname;
  }

  function assetUrl(path) {
    if (global.H7Base) return global.H7Base(path);
    return path;
  }

  function jsonResponse(doc, status) {
    status = status || 200;
    return new Response(JSON.stringify(doc), {
      status: status,
      headers: { "Content-Type": "application/json" },
    });
  }

  async function loadStatic(path) {
    const r = await global.__H7_ORIG_FETCH__(assetUrl(path), { cache: "no-store" });
    if (!r.ok) throw new Error(path + " " + r.status);
    return r.json();
  }

  function searchIndex(indexDoc, q) {
    const query = String(q || "").toLowerCase();
    const hits = (indexDoc.hits || []).filter((h) => {
      const hay = JSON.stringify(h).toLowerCase();
      return query.split(/\s+/).some((t) => t.length > 2 && hay.includes(t));
    });
    return { ok: true, query: q, hits: hits.slice(0, 12) };
  }

  function okStub(extra) {
    return jsonResponse(Object.assign({ ok: true, pages: true, lane: "pages-surfaces" }, extra || {}));
  }

  async function routeApi(url, opts) {
    const u = new URL(url, global.location.origin);
    const path = apiPath(u.pathname.replace(/\/$/, "") || "/");
    const method = (opts && opts.method) || "GET";

    if (path === "/health" || path === "/api/health") {
      return jsonResponse(await loadStatic("/api/health.json"));
    }
    if (path === "/api/status") {
      return jsonResponse(await loadStatic("/api/status.json"));
    }
    if (path === "/api/status/full") {
      return jsonResponse(await loadStatic("/api/status-full.json"));
    }
    if (path === "/api/brain") {
      return jsonResponse(await loadStatic("/api/brain.json"));
    }
    if (path === "/api/field-host-desktop") {
      return jsonResponse(await loadStatic("/api/field-host-desktop.json"));
    }
    if (path === "/api/field-shell-settings") {
      if (method === "POST") return okStub({ saved: true });
      return jsonResponse(await loadStatic("/api/field-shell-settings.json"));
    }
    if (path === "/api/znetwork") {
      return jsonResponse(await loadStatic("/api/znetwork.json"));
    }
    if (path === "/api/field-keyboard-sovereign") {
      return jsonResponse(await loadStatic("/api/field-keyboard-sovereign.json"));
    }
    if (path === "/api/field-keyboard-sovereign/engage" && method === "POST") {
      return jsonResponse(await loadStatic("/api/field-keyboard-sovereign-engage.json"));
    }
    if (path === "/api/field-keyboard-sovereign/release" && method === "POST") {
      return jsonResponse(await loadStatic("/api/field-keyboard-sovereign-release.json"));
    }
    if (path === "/api/nexus-c2") {
      return jsonResponse(await loadStatic("/api/nexus-c2.json"));
    }
    if (path === "/api/queen-browser") {
      if (method === "POST") return okStub({ saved: true, lane: "pages-queen-browser" });
      return jsonResponse(await loadStatic("/api/queen-browser.json"));
    }
    if (path === "/api/queen-boot") {
      return jsonResponse(await loadStatic("/api/queen-boot.json"));
    }
    if (path === "/api/queen-page-shields") {
      if (method === "POST") return okStub({ stored: true, shields: true });
      return jsonResponse(await loadStatic("/api/queen-page-shields.json"));
    }
    if (path === "/api/github-secure") {
      return jsonResponse(await loadStatic("/api/github-secure.json"));
    }
    if (path === "/api/field-c2-bookmarks" && method === "POST") {
      return okStub({ stored: true });
    }
    if (path === "/api/field-taskbar-pins" && method === "POST") {
      return okStub({ stored: true });
    }
    if (path === "/api/ammoos/close" && method === "POST") {
      return okStub({ closed: false, note: "Pages runtime — desktop stays live" });
    }
    if (path === "/api/nexus/restart" && method === "POST") {
      return okStub({ restarted: false, note: "Restart on loopback only" });
    }
    if (path === "/api/hearing") {
      const q = u.searchParams.get("q") || "hearing listen speak";
      try {
        const idx = await loadStatic("/api/hearing-index.json");
        if (idx.hits && idx.hits.length) return jsonResponse(searchIndex(idx, q));
      } catch (_e) { /* fallback */ }
      return jsonResponse({ ok: true, query: q, hits: [] });
    }
    if (path === "/api/world") {
      const q = u.searchParams.get("q") || "bible law nature";
      try {
        return jsonResponse(searchIndex(await loadStatic("/api/world-index.json"), q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/library/search") {
      const q = u.searchParams.get("q") || "children algebra";
      try {
        return jsonResponse(searchIndex(await loadStatic("/api/library-index.json"), q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/videogames") {
      const q = u.searchParams.get("q") || "mario zelda";
      try {
        return jsonResponse(searchIndex(await loadStatic("/api/videogames-index.json"), q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/teach" && method === "POST") {
      return okStub({ stored: true, lane: "github-mirror", writes_to_sovereign: false });
    }
    if (path === "/api/reflect") {
      return okStub({ route: "github-mirror", note: "Reflect on loopback only" });
    }
    if (path === "/api/ask" && method === "POST") {
      let body = {};
      try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
      const query = String(body.query || "").trim();
      if (!query) return jsonResponse({ ok: false, error: "empty query" }, 400);
      try {
        const seeds = await loadStatic("/api/ask-seeds.json");
        const hit = (seeds.answers || []).find((a) => {
          const ql = query.toLowerCase();
          return a.query && ql.includes(String(a.query).toLowerCase().slice(0, 12));
        });
        if (hit && hit.text) return jsonResponse({ ok: true, text: hit.text, query: query, route: "ask-seeds" });
      } catch (_e) { /* corpus */ }
      return jsonResponse({ ok: true, text: "Hostess 7 Pages — Queen + AmmoOS live.", query: query, route: "pages" });
    }
    return null;
  }

  const origFetch = global.fetch.bind(global);
  global.__H7_ORIG_FETCH__ = origFetch;

  global.fetch = async function (input, opts) {
    const url = typeof input === "string" ? input : input.url;
    try {
      const parsed = new URL(url, global.location.origin);
      if (parsed.origin === global.location.origin) {
        const norm = apiPath(parsed.pathname);
        if (norm.startsWith("/api/") || norm === "/health") {
          const routed = await routeApi(parsed.origin + norm + parsed.search, opts);
          if (routed) return routed;
        }
        if (norm.startsWith("/assets/")) {
          const fixed = assetUrl(norm) + parsed.search;
          return origFetch(fixed, opts);
        }
      }
    } catch (_e) { /* fall through */ }
    return origFetch(input, opts);
  };

  global.Hostess7ApiShim = { routeApi: routeApi, LOOPBACK: LOOPBACK };
})(typeof window !== "undefined" ? window : globalThis);