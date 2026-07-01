/**
 * Static GitHub Pages shim — full Hostess7 /api/* surface (same routes as hostess7_web.py).
 */
(function (global) {
  const LOOPBACK = "http://127.0.0.1:8080";

  function jsonResponse(doc, status) {
    status = status || 200;
    return new Response(JSON.stringify(doc), {
      status: status,
      headers: { "Content-Type": "application/json" },
    });
  }

  async function loadStatic(path) {
    const r = await fetch(path, { cache: "no-store" });
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

  async function routeApi(url, opts) {
    const u = new URL(url, global.location.origin);
    const path = u.pathname.replace(/\/$/, "") || "/";
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
    if (path === "/api/hearing") {
      const q = u.searchParams.get("q") || "hearing listen speak";
      try {
        const idx = await loadStatic("/api/hearing-index.json");
        if (idx.hits && idx.hits.length) return jsonResponse(searchIndex(idx, q));
      } catch (_e) {
        /* fallback */
      }
      return jsonResponse({ ok: true, query: q, hits: [] });
    }
    if (path === "/api/world") {
      const q = u.searchParams.get("q") || "bible law nature";
      try {
        const idx = await loadStatic("/api/world-index.json");
        return jsonResponse(searchIndex(idx, q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/library/search") {
      const q = u.searchParams.get("q") || "children algebra";
      try {
        const idx = await loadStatic("/api/library-index.json");
        return jsonResponse(searchIndex(idx, q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/videogames") {
      const q = u.searchParams.get("q") || "mario zelda";
      try {
        const idx = await loadStatic("/api/videogames-index.json");
        return jsonResponse(searchIndex(idx, q));
      } catch (_e) {
        return jsonResponse({ ok: true, query: q, hits: [] });
      }
    }
    if (path === "/api/teach" && method === "POST") {
      let body = {};
      try {
        body = JSON.parse((opts && opts.body) || "{}");
      } catch (_e) {
        body = {};
      }
      const topic = String(body.topic || "").trim().slice(0, 200);
      const content = String(body.content || "").trim().slice(0, 8000);
      if (!topic) return jsonResponse({ ok: false, error: "topic required" }, 400);
      const key = "hostess7-github-brain-session";
      let session = [];
      try {
        session = JSON.parse(global.localStorage.getItem(key) || "[]");
      } catch (_e) {
        session = [];
      }
      session.push({ topic: topic, content: content, ts: new Date().toISOString(), lane: "github-mirror" });
      session = session.slice(-64);
      try {
        global.localStorage.setItem(key, JSON.stringify(session));
      } catch (_e) {
        /* private mode */
      }
      return jsonResponse({
        ok: true,
        topic: topic,
        stored: true,
        lane: "github-mirror",
        writes_to_sovereign: false,
        taught_count: session.length,
        note: "Session stored in browser only — sovereign brain untouched.",
      });
    }
    if (path === "/api/reflect" && (method === "POST" || method === "GET")) {
      return jsonResponse({
        ok: true,
        lane: "github-mirror",
        route: "github-mirror",
        note: "Reflect runs on sovereign loopback only. Pages mirror is read-only.",
        ts: new Date().toISOString(),
      });
    }
    if (path === "/api/ask" && method === "POST") {
      let body = {};
      try {
        body = JSON.parse((opts && opts.body) || "{}");
      } catch (_e) {
        body = {};
      }
      const query = global.Hostess7Brain
        ? global.Hostess7Brain.sanitize(body.query || "")
        : String(body.query || "").trim();
      if (!query) return jsonResponse({ ok: false, error: "empty query" }, 400);

      try {
        const lr = await fetch(LOOPBACK + "/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query }),
          mode: "cors",
        });
        if (lr.ok) return jsonResponse(await lr.json());
      } catch (_e) {
        /* pages brain */
      }

      try {
        const seeds = await loadStatic("/api/ask-seeds.json");
        const hit = (seeds.answers || []).find((a) => {
          const ql = query.toLowerCase();
          return a.query && (ql.includes(a.query.toLowerCase().slice(0, 12)) || a.query.toLowerCase().includes(ql.slice(0, 12)));
        });
        if (hit && hit.text) {
          return jsonResponse({ ok: true, text: hit.text, query: query, route: "ask-seeds" });
        }
      } catch (_e) {
        /* corpus */
      }

      if (global.Hostess7Brain && global.__H7_BRAIN__) {
        const res = await global.Hostess7Brain.askBrain(query, global.__H7_BRAIN__);
        return jsonResponse({ ok: res.ok, text: res.text, query: query, route: res.route, hits: res.hits });
      }
      return jsonResponse({
        ok: true,
        text: "Brain loading — try again in a moment.",
        query: query,
        route: "pages-wait",
      });
    }
    return null;
  }

  const origFetch = global.fetch.bind(global);
  global.fetch = async function (input, opts) {
    const url = typeof input === "string" ? input : input.url;
    try {
      const parsed = new URL(url, global.location.origin);
      if (parsed.origin === global.location.origin && parsed.pathname.startsWith("/api/")) {
        const routed = await routeApi(url, opts);
        if (routed) return routed;
      }
      if (parsed.pathname === "/health") {
        const routed = await routeApi("/health", opts);
        if (routed) return routed;
      }
    } catch (_e) {
      /* fall through */
    }
    return origFetch(input, opts);
  };

  global.Hostess7ApiShim = { routeApi: routeApi, LOOPBACK: LOOPBACK };
})(typeof window !== "undefined" ? window : globalThis);