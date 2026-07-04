/**
 * Static GitHub Pages shim — intercepts /api/* before network (fixes /Hostess7 subpath).
 */
(function (global) {
  const LOOPBACK = "http://127.0.0.1:" + (global.NEXUS_PANEL_PORT || "9477");
  const QUEEN_LOOPBACK = "http://127.0.0.1:" + (global.NEXUS_QUEEN_PORT || "9481");

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

  const ASK_SENSITIVE_RE =
    /ssh-rsa|BEGIN OPENSSH|pin_sha256|sudo\s+pw|password\s*[:=]|known_hosts/i;

  let _githubCorpus = null;
  let _ironcladIndex = null;

  function askSanitize(input) {
    let s = String(input ?? "")
      .replace(/<[^>]*>/g, "")
      .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "")
      .trim();
    if (s.length > 2000) s = s.slice(0, 2000);
    return s;
  }

  function askTokenize(q) {
    return askSanitize(q)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length > 2);
  }

  function scoreAskChunk(chunk, tokens) {
    const hay = `${chunk.title} ${chunk.text} ${(chunk.tags || []).join(" ")}`.toLowerCase();
    let score = 0;
    for (const t of tokens) {
      if (hay.includes(t)) score += t.length > 5 ? 3 : 1;
    }
    const joined = tokens.join(" ");
    if (chunk.domain === "wants" && /want|priority|first|human|ui/.test(joined)) score += 4;
    if (chunk.domain === "human_ui" && /human|ui|bsp|ironclad|library/.test(joined)) score += 5;
    if (chunk.domain === "personality" && /who|hostess|you|grok/.test(joined)) score += 4;
    if (chunk.domain === "field_stack" && /kilroy|stack|boot|field/.test(joined)) score += 3;
    return score;
  }

  async function githubCorpus() {
    if (_githubCorpus) return _githubCorpus;
    _githubCorpus = await loadStatic("/github-brain/corpus.json");
    return _githubCorpus;
  }

  function composeAskAnswer(query, hits, manifest) {
    if (!hits.length) {
      return (
        "I'm Hostess 7 GitHub mind — sovereign local brain is unhooked on Pages. " +
        "Try: wants, KILROY, ZNetwork, DNS, DHCP, iPXE stack, truth floor, or NEXUS C2. " +
        "Update mind from Command · Sync GitHub; publish via ./Hostess7.sh pages-build."
      );
    }
    const top = hits.slice(0, 4);
    const lines = ["You asked: " + query, ""];
    for (const h of top) {
      const excerpt = h.text.length > 520 ? h.text.slice(0, 520) + "…" : h.text;
      lines.push("• " + h.title, excerpt, "");
    }
    if (manifest?.loopback_upgrade) {
      lines.push("Sources: " + top.map((h) => h.source).join(", "));
      lines.push("Full brain: " + manifest.loopback_upgrade);
    }
    return lines.join("\n").trim();
  }

  async function askCorpus(query) {
    const q = askSanitize(query);
    if (!q) return { ok: false, error: "empty query" };
    let manifest = {};
    try {
      manifest = await loadStatic("/github-brain/manifest.json");
    } catch (_e) { /* bundled corpus */ }
    const corpus = await githubCorpus();
    const tokens = askTokenize(q);
    const ranked = (corpus.chunks || [])
      .map((c) => Object.assign({}, c, { _score: scoreAskChunk(c, tokens) }))
      .filter((c) => c._score > 0)
      .sort((a, b) => b._score - a._score);
    const text = composeAskAnswer(q, ranked, manifest);
    if (ASK_SENSITIVE_RE.test(text)) {
      return {
        ok: true,
        text: "I withhold that on public Pages — information discipline. Ask on loopback after boot.",
        route: "pages-filtered",
        query: q,
        lane: "github-mirror",
      };
    }
    return {
      ok: true,
      text: text,
      route: "github-mirror",
      lane: "github-mirror",
      query: q,
      hits: ranked.slice(0, 4).map((h) => ({
        id: h.id,
        title: h.title,
        source: h.source,
        score: h._score,
      })),
      chunk_count: (corpus.chunks || []).length,
    };
  }

  async function ironcladPagesIndex() {
    if (_ironcladIndex) return _ironcladIndex;
    try {
      _ironcladIndex = await loadStatic("/api/ironclad-pages-search-index.json");
    } catch (_e) {
      _ironcladIndex = { entries: [] };
    }
    return _ironcladIndex;
  }

  function ironcladSearchHits(index, q, ctx, limit) {
    const query = String(q || "").trim().toLowerCase();
    const tokens = query.split(/\s+/).filter((t) => t.length > 1);
    let pool = index.entries || [];
    if (ctx && ctx !== "all") {
      pool = pool.filter((e) => String(e.source || e.kind || "").toLowerCase().includes(ctx) || String(e.context || "") === ctx);
    }
    if (!tokens.length) {
      return pool.slice(0, limit);
    }
    const scored = pool
      .map((e) => {
        const hay = String(e.search_blob || JSON.stringify(e)).toLowerCase();
        let score = 0;
        tokens.forEach((t) => {
          if (hay.includes(t)) score += t.length > 4 ? 3 : 1;
        });
        return { e: e, score: score };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score || String(a.e.label || a.e.title || "").localeCompare(String(b.e.label || b.e.title || ""), undefined, { sensitivity: "base" }));
    return scored.slice(0, limit).map((r) => Object.assign({}, r.e, { score: r.score, query: q }));
  }

  function ironcladSortEntries(entries, context) {
    const ctx = String(context || "registry_index").toLowerCase();
    const rows = (entries || []).slice();
    if (ctx === "chip_catalog" || ctx === "composite_bsp") {
      rows.sort((a, b) => (Number(b.bsp_score || b.composite_score || 0) - Number(a.bsp_score || a.composite_score || 0)) ||
        String(a.label || a.title || "").localeCompare(String(b.label || b.title || ""), undefined, { sensitivity: "base" }));
    } else if (ctx === "api_registry") {
      rows.sort((a, b) => {
        const ad = String(a.path || a.id || "").startsWith("/api/") ? 0 : 1;
        const bd = String(b.path || b.id || "").startsWith("/api/") ? 0 : 1;
        return ad - bd || String(a.label || a.path || "").localeCompare(String(b.label || b.path || ""), undefined, { sensitivity: "base" });
      });
    } else {
      rows.sort((a, b) => {
        const fa = String(a.family || a.collection || a.kind || "");
        const fb = String(b.family || b.collection || b.kind || "");
        const fc = fa.localeCompare(fb, undefined, { sensitivity: "base" });
        return fc || String(a.label || a.title || a.name || "").localeCompare(String(b.label || b.title || b.name || ""), undefined, { sensitivity: "base" });
      });
    }
    return rows;
  }

  let _deweyCompact = null;

  async function deweyCompact() {
    if (_deweyCompact) return _deweyCompact;
    _deweyCompact = await loadStatic("/api/dewey-books-compact.json");
    return _deweyCompact;
  }

  function deweySearch(compact, params) {
    const q = (params.get("q") || "").trim().toLowerCase();
    const shelf = (params.get("shelf") || "").trim().toLowerCase();
    const limit = Math.min(500, parseInt(params.get("limit") || "60", 10) || 60);
    let pool = compact.books || [];
    if (shelf) {
      pool = pool.filter((b) => String(b.shelf || "").toLowerCase() === shelf || String(b.shelf || "").toLowerCase().includes(shelf));
    }
    if (q) {
      const tokens = q.split(/\s+/).filter((t) => t.length > 1);
      pool = pool.filter((b) => {
        const hay = String(b.search_blob || JSON.stringify(b)).toLowerCase();
        return tokens.every((t) => hay.includes(t));
      });
    }
    pool.sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" }));
    return {
      schema: "field-dewey-index-search/v1",
      ok: true,
      query: q,
      hits: pool.slice(0, limit),
      count: Math.min(pool.length, limit),
      total_pool: pool.length,
      pages: true,
      index_updated: compact.updated,
    };
  }

  function catalogFromCompact(compact) {
    const books = compact.books || [];
    const shelves = {};
    books.forEach((b) => {
      const code = String(b.dewey || "000").slice(0, 3);
      if (!shelves[code]) {
        shelves[code] = { code, title: b.dewey_label || code, count: 0, books: [] };
      }
      shelves[code].count += 1;
      if (shelves[code].books.length < 200) shelves[code].books.push(b);
    });
    return {
      ok: true,
      pages: true,
      schema: "library-catalog/v1",
      books: books.slice(0, 800),
      shelves: Object.values(shelves).sort((a, b) => a.code.localeCompare(b.code)),
      book_count: books.length,
      ready_count: books.filter((b) => b.ready !== false).length,
      updated: compact.updated,
      motto: "Whole library on Pages — humans, librarians, nuns, and AI share the same Dewey shelves.",
    };
  }

  let _cardDrawer = null;

  async function cardDrawer() {
    if (_cardDrawer) return _cardDrawer;
    _cardDrawer = await loadStatic("/api/card-catalog-drawer.json");
    return _cardDrawer;
  }

  function deweySortKey(callNumber) {
    const parts = String(callNumber || "999").split(/[^0-9]+/);
    const nums = [];
    for (let i = 0; i < parts.length; i++) {
      if (parts[i]) nums.push(parseInt(parts[i], 10) || 0);
    }
    while (nums.length < 4) nums.push(0);
    return nums;
  }

  function cardBlob(card) {
    return String(
      card.search_blob ||
        [
          card.card_id,
          card.id,
          card.call_number,
          card.title,
          card.author,
          card.dewey,
          card.shelf,
          card.format,
          (card.keywords || []).join(" "),
        ].join(" ")
    ).toLowerCase();
  }

  function scoreCard(card, query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q) return 0;
    const blob = cardBlob(card);
    let score = 0;
    if (blob.includes(q)) score += 28;
    const title = String(card.title || "").toLowerCase();
    const author = String(card.author || "").toLowerCase();
    const call = String(card.call_number || "").toLowerCase();
    const keywords = (card.keywords || []).map((k) => String(k).toLowerCase());
    if (title.startsWith(q)) score += 20;
    if (title.includes(q)) score += 14;
    if (author.includes(q)) score += 10;
    if (call.includes(q)) score += 12;
    if (keywords.some((k) => k.includes(q))) score += 16;
    q.split(/\W+/).filter((t) => t.length > 1).forEach((tok) => {
      if (title.includes(tok)) score += 8;
      if (author.includes(tok)) score += 6;
      if (call.includes(tok)) score += 6;
      if (keywords.some((k) => k.includes(tok))) score += 7;
      if (blob.includes(tok)) score += 4;
    });
    return score;
  }

  function sortCards(cards, mode) {
    const m = String(mode || "call_number").toLowerCase();
    const rows = (cards || []).slice();
    if (m === "title") {
      rows.sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" }));
    } else if (m === "author") {
      rows.sort((a, b) => {
        const aa = String(a.author || "").localeCompare(String(b.author || ""), undefined, { sensitivity: "base" });
        return aa || String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" });
      });
    } else if (m === "shelf") {
      rows.sort((a, b) => {
        const ss = String(a.shelf || "").localeCompare(String(b.shelf || ""), undefined, { sensitivity: "base" });
        return ss || deweySortKey(a.call_number).join("-").localeCompare(deweySortKey(b.call_number).join("-"));
      });
    } else if (m === "format") {
      rows.sort((a, b) => {
        const ff = String(a.format || "").localeCompare(String(b.format || ""), undefined, { sensitivity: "base" });
        return ff || String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" });
      });
    } else if (m === "collection") {
      rows.sort((a, b) => {
        const cc = String(a.collection || "").localeCompare(String(b.collection || ""), undefined, { sensitivity: "base" });
        return cc || String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" });
      });
    } else {
      rows.sort((a, b) => {
        const ak = deweySortKey(a.call_number).join("-");
        const bk = deweySortKey(b.call_number).join("-");
        const cmp = ak.localeCompare(bk, undefined, { numeric: true });
        return cmp || String(a.title || "").localeCompare(String(b.title || ""), undefined, { sensitivity: "base" });
      });
    }
    return rows;
  }

  function cardSearch(drawer, params) {
    const q = (params.get("q") || "").trim();
    const limit = Math.min(200, parseInt(params.get("limit") || "120", 10) || 120);
    let pool = drawer.cards || [];
    if (!q) {
      const rows = sortCards(pool, "call_number");
      return {
        schema: "field-card-catalog-search/v1",
        ok: true,
        pages: true,
        query: q,
        hits: rows.slice(0, limit),
        count: Math.min(limit, rows.length),
        total_pool: rows.length,
      };
    }
    const hits = pool
      .map((c) => ({ score: scoreCard(c, q), card: c }))
      .filter((h) => h.score > 0)
      .sort((a, b) => b.score - a.score || String(a.card.title || "").localeCompare(String(b.card.title || ""), undefined, { sensitivity: "base" }));
    const out = hits.slice(0, limit).map((h) => Object.assign({}, h.card, { score: h.score, query: q }));
    return {
      schema: "field-card-catalog-search/v1",
      ok: true,
      pages: true,
      query: q,
      hits: out,
      count: out.length,
      total_pool: pool.length,
    };
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
    if (path === "/api/github-brain/status" || path === "/api/github-brain") {
      const brain = await loadStatic("/api/brain.json");
      let mirror = {};
      try {
        mirror = await loadStatic("/github-brain/mirror.json");
      } catch (_e) {}
      return jsonResponse({
        ok: true,
        lane: "github-mirror",
        mode: brain.mode || "github-brain-mirror",
        identity: brain.identity || "Hostess7-GitHub",
        sovereign_brain: false,
        local_brain: false,
        writes_to_sovereign: false,
        corpus: "/github-brain/corpus.json",
        mirror: mirror,
        stack: ["nexus-c2", "kilroy", "ipxe", "znetwork", "field-dns", "field-dhcp", "queen-browser"],
        update_via: "NEXUS C2 Sync GitHub · pages-build publish",
      });
    }
    if (path === "/api/github-brain/mind-update" && method === "POST") {
      let body = {};
      try {
        body = JSON.parse((opts && opts.body) || "{}");
      } catch (_e) {
        body = {};
      }
      return jsonResponse({
        ok: true,
        stored: true,
        pages: true,
        lane: "github-mirror",
        note: "Mind update accepted — client outbox + next pages-build publishes corpus",
        entry: {
          title: body.title || "mind-update",
          text: String(body.text || body.query || "").slice(0, 4000),
          type: body.type || "operator",
          ts: new Date().toISOString(),
        },
      });
    }
    if (path === "/api/field-brain") {
      const brain = await loadStatic("/api/brain.json");
      return jsonResponse({
        schema: "field-brain/v1",
        ok: true,
        pages: true,
        lane: "github-mirror",
        data_source: "github-brain",
        sovereign_brain: false,
        local_brain: false,
        writes_to_sovereign: false,
        github_field_brain_path: "/github-brain/",
        corpus: brain.corpus || "/github-brain/corpus.json",
        superintelligence: {
          available: true,
          arc: "GitHub mind · NEXUS C2",
          head: brain.version,
          source: "github-brain-mirror",
        },
        stack_mind: {
          nexus_c2: "/command/",
          kilroy: "F10 · layer -2",
          znetwork: "/api/znetwork",
          dns: "/api/field-dns",
          dhcp: "Field DHCP · Truth Resolver",
          ipxe: "netboot lane · publish on pages-build",
          queen_browser: "F12 · layer 0",
        },
      });
    }
    if (path === "/api/field-host-desktop") {
      return jsonResponse(await loadStatic("/api/field-host-desktop.json"));
    }
    if (path === "/api/field-monster-monitor" || path.startsWith("/api/field-monster-monitor/")) {
      const sub = path.slice("/api/field-monster-monitor".length) || "";
      const h7base = global.HOSTESS7_PAGES_BASE || "/Hostess7";
      const doc = {
        schema: "field-monster-monitor/v1",
        ok: true,
        pages: true,
        lane: "github-pages",
        title: "Monster · Pages rescue",
        motto: "Rescue on GitHub Pages — full graphs on loopback panel.",
        updated: new Date().toISOString(),
        cpu_pct: 0,
        cpu_cores: 4,
        loadavg: [0, 0, 0],
        memory: { used_pct: 0, swap_used_pct: 0 },
        process_count: 0,
        uptime_sec: 0,
        thermal: { headroom_pct: 100 },
        services: [
          { id: "pages_desktop", name: "AmmoOS Desktop", port: 0, status: "live", up: true },
          { id: "queen_browser", name: "Queen Browser", port: 0, status: "layer 0 · F12", up: true },
          { id: "final_eye", name: "Final Eye", port: 0, status: "sealed block", up: true },
          { id: "nexus_panel", name: "NEXUS Panel", port: 9477, status: "loopback · ./nexus.sh panel", up: false },
        ],
        intel: {
          security: {
            security_hold: true,
            freeze_underlying_os: false,
            protections: ["github-secure", "final-eye-block", "pages-shim"],
            motto: "Pages mirror — process table needs loopback.",
          },
          pages: { base: h7base, layer: 1 },
        },
      };
      if (sub === "/processes") {
        return jsonResponse({ ok: true, pages: true, processes: [], note: "Loopback panel required for live process table." });
      }
      if (sub === "/intel") {
        return jsonResponse({ ok: true, pages: true, security: doc.intel.security });
      }
      if (sub === "/action" && method === "POST") {
        return okStub({ ok: true, pages: true, stub: true, note: "Process actions apply on loopback panel only." });
      }
      return jsonResponse(doc);
    }
    if (path === "/api/field-shell-settings") {
      if (method === "POST") {
        let body = {};
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
        const base = await loadStatic("/api/field-shell-settings.json");
        const settings = Object.assign({}, base.settings || {}, body);
        return jsonResponse(Object.assign({}, base, { ok: true, saved: true, pages: true, settings: settings }));
      }
      return jsonResponse(await loadStatic("/api/field-shell-settings.json"));
    }
    if (path === "/api/ammoos-themes") {
      let body = {};
      if (method === "POST") {
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
      }
      const cat = await loadStatic("/api/ammoos-themes.json");
      if (body.action === "apply" && body.patch) {
        const patch = body.patch || {};
        cat.active = Object.assign({}, cat.active || {}, {
          c2: patch.c2 || patch.active_c2 || cat.active?.c2,
          queen_styles: patch.queen_styles || cat.active?.queen_styles,
          shell_theme: patch.shell_theme || cat.active?.shell_theme,
        });
        if (patch.os_theme) cat.active.os_theme = patch.os_theme;
        return jsonResponse(Object.assign({}, cat, { ok: true, applied: true, pages: true }));
      }
      if (body.action === "catalog" || method === "GET" || !body.action) {
        return jsonResponse(cat);
      }
      return jsonResponse(cat);
    }
    if (path === "/api/hostess7/calculator/compute" && method === "POST") {
      let body = {};
      try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
      const q = String(body.query || body.q || "").trim();
      if (!q) return jsonResponse({ ok: false, error: "empty query" }, 400);
      try {
        let s = q.replace(/%/g, "/100").replace(/\^/g, "**").replace(/sqrt\(/gi, "Math.sqrt(");
        if (!/^[\d\s+\-*/().e%a-z]+$/i.test(s)) {
          return jsonResponse({ ok: false, error: "unsafe expression", query: q }, 400);
        }
        const val = Function('"use strict"; return (' + s + ")")();
        if (typeof val !== "number" || !isFinite(val)) {
          return jsonResponse({ ok: false, error: "not a number", query: q }, 400);
        }
        return jsonResponse({ ok: true, result: val, query: q, route: "pages-calc", pages: true });
      } catch (e) {
        return jsonResponse({ ok: false, error: String(e.message || e), query: q }, 400);
      }
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
    if (path === "/api/nexus-c2-basement" || path === "/api/nexus-c2/basement") {
      try {
        return jsonResponse(await loadStatic("/api/nexus-c2-basement.json"));
      } catch (_e) {
        return okStub({
          schema: "nexus-c2-basement/v1",
          role: "secure_basement",
          weaponized: true,
          pages: true,
          pages_url: "https://zacharygeurts.github.io/command/",
          theme: "black_emerald_rose_2026",
          palette: "black · emerald · rose",
        });
      }
    }
    if (
      path === "/api/game-room" ||
      path.startsWith("/api/game-room/") ||
      path === "/api/sap" ||
      path === "/api/nes-library" ||
      path === "/api/field-arcade-battalion"
    ) {
      const queenApi = QUEEN_LOOPBACK + path;
      const loopApi = LOOPBACK + path;
      const target = path === "/api/field-arcade-battalion" ? loopApi : queenApi;
      try {
        const r = await global.__H7_ORIG_FETCH__(target, {
          method: method,
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: method === "POST" ? (opts && opts.body) || "{}" : undefined,
          cache: "no-store",
        });
        if (r.ok) {
          const ct = r.headers.get("content-type") || "";
          if (ct.includes("json")) return jsonResponse(await r.json());
        }
      } catch (_e) {}
      if (path === "/api/field-arcade-battalion") {
        return okStub({
          ok: true,
          schema: "field-arcade-battalion/v1",
          pages: true,
          lobby: { sap_beacons: 0, qemu_witnesses: 0 },
          hint: "Boot loopback for live arcade lobby",
        });
      }
      return okStub({
        ok: false,
        error: "loopback_required",
        hint: "Queen Game Room needs loopback :9481 — ./nexus.sh boot",
        path: path,
      });
    }
    if (path === "/api/queen-terminal" || path === "/api/terminal") {
      const queenApi = QUEEN_LOOPBACK + path;
      if (method === "POST") {
        try {
          const r = await global.__H7_ORIG_FETCH__(queenApi, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: (opts && opts.body) || "{}",
          });
          if (r.ok) return jsonResponse(await r.json());
        } catch (_e) {}
        return okStub({
          ok: false,
          error: "loopback_required",
          output: "AmmoOS GNU Terminal needs loopback :9481 — boot ./nexus.sh or scripts/impl/ammoos-direct-start.sh",
          schema: "queen-gnu-terminal/v2",
          pages: true,
        });
      }
      try {
        const r = await global.__H7_ORIG_FETCH__(queenApi, { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/queen-terminal.json"));
      } catch (_e2) {
        return okStub({
          ok: true,
          schema: "queen-gnu-terminal/v2",
          shell_terminal_identical: true,
          aliases: ["terminal", "gnu-terminal", "shell", "gnueol"],
          pages: true,
          posture: "KILROY Universal Terminal — boot loopback for live shell",
        });
      }
    }
    if (path === "/api/queen-browser") {
      if (method === "POST") return okStub({ saved: true, lane: "pages-queen-browser" });
      return jsonResponse(await loadStatic("/api/queen-browser.json"));
    }
    if (path === "/api/queen-loopback/probe" && method === "GET") {
      const shell = "http://127.0.0.1:9481/world/browser.html";
      const out = {
        ok: true,
        shell: shell,
        world: "http://127.0.0.1:9481",
        queen: false,
        world_ok: false,
        panel: false,
        training: false,
        rtx: false,
        engine: "pages-mirror",
      };
      try {
        const wr = await global.__H7_ORIG_FETCH__("http://127.0.0.1:9481/api/status?fast=1", {
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        if (wr.ok) {
          const wj = await wr.json();
          out.world_ok = true;
          out.queen = true;
          out.engine = wj.engine || "queen-world";
        }
      } catch (_e) {}
      try {
        const pr = await global.__H7_ORIG_FETCH__("http://127.0.0.1:9477/field", { cache: "no-store" });
        out.panel = pr.ok;
      } catch (_e) {}
      try {
        const tr = await global.__H7_ORIG_FETCH__("http://127.0.0.1:9488/api/health", {
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        out.training = tr.ok;
      } catch (_e) {}
      try {
        const rr = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/queen-browser/open", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        if (rr.ok) {
          const rj = await rr.json();
          out.rtx = !!rj.spawn_rtx || rj.engine === "queen-rtx" || rj.engine === "queen-field-gecko";
          out.rtx_binary = rj.rtx_binary || null;
          if (rj.shell_url) out.shell = rj.shell_url;
          if (out.rtx) out.engine = "queen-rtx";
        }
      } catch (_e) {}
      return jsonResponse(out);
    }
    if (path === "/api/qemu-world-status" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/qemu-world-status", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/qemu-world-status.json"));
      } catch (_e2) {
        return okStub({ running: false, completed: 0, target: 0, schema: "qemu-world-pipeline/v1" });
      }
    }
    if (path === "/api/queen-browser/open" && method === "POST") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/queen-browser/open", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: (opts && opts.body) || "{}",
        });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      const base = global.HOSTESS7_PAGES_BASE || "/Hostess7";
      return okStub({
        engine: "queen-browser",
        self_contained: true,
        shell_url: base + "/queen/browser.html",
        pages_mirror: base + "/queen/browser.html",
        layer: 0,
        os_layer: true,
        pages: true,
        note: "Queen Browser · layer 0 OS stack — F12 fast switch",
      });
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
    if (path === "/api/field-sense-secure-kill") {
      return jsonResponse(await loadStatic("/api/field-sense-secure-kill.json"));
    }
    if (path === "/api/field-final-eye-block" || path === "/api/final-eye-block") {
      return jsonResponse(await loadStatic("/api/field-final-eye-block.json"));
    }
    if (path === "/api/field-final-ear-block" || path === "/api/final-ear-block") {
      return jsonResponse(await loadStatic("/api/field-final-ear-block.json"));
    }
    if (path === "/api/field-final-mouth-block" || path === "/api/final-mouth-block") {
      return jsonResponse(await loadStatic("/api/field-final-mouth-block.json"));
    }
    if (path === "/api/queen-eyeball") {
      if (method === "POST") {
        let body = {};
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
        return okStub({
          schema: "queen-eyeball-arm/v1",
          armed: true,
          action: body.action || "arm",
          mode: body.mode || "dishes",
          pages: true,
          note: "Pages static lane — arm recorded; live vision on loopback",
        });
      }
      return jsonResponse(await loadStatic("/api/queen-eyeball.json"));
    }
    if (path === "/api/hostess7-tasklist" || path === "/api/hostess7/tasklist") {
      if (method === "POST") {
        let body = {};
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
        if (body.action === "report") {
          const tl = await loadStatic("/api/hostess7-tasklist.json");
          const open = (tl.open || []).map((t) => t.title).join("; ") || "(queue clear)";
          return jsonResponse({ ok: true, report: "Hostess 7 tasklist (Pages): " + open, open: tl.open || [] });
        }
        return okStub({ action: body.action || "noop", note: "Tasklist writes on loopback only" });
      }
      return jsonResponse(await loadStatic("/api/hostess7-tasklist.json"));
    }
    if (path === "/api/hostess7-training-viewer/ensure" || path === "/api/hostess7-training-viewer/open") {
      if (method === "POST") {
        try {
          const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/hostess7-training-viewer/ensure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: (opts && opts.body) || "{}",
          });
          if (r.ok) return jsonResponse(await r.json());
        } catch (_e) {}
        const base = global.HOSTESS7_PAGES_BASE || "/Hostess7";
        return jsonResponse({
          ok: true,
          pages: true,
          url: base + "/training-room/",
          loopback_url: "http://127.0.0.1:9488/",
          queen_launch: "http://127.0.0.1:9481/world/browser.html?launch=" +
            encodeURIComponent("http://127.0.0.1:9488/"),
          hint: "Pages training room visual — loopback :9488 for live viewer",
        });
      }
      return okStub({ url: "http://127.0.0.1:9488/", port: 9488 });
    }
    if (path.startsWith("/api/hostess7/training-room") || path === "/api/hostess7-training-room") {
      try {
        return jsonResponse(await loadStatic("/api/hostess7-training-room.json"));
      } catch (_e) {
        return okStub({ schema: "hostess7-training-room/v1", pages: true, partial: true });
      }
    }
    if (path === "/api/hostess7-voice" || path === "/api/hostess7/voice") {
      if (method === "POST") return okStub({ spoken: false, note: "Voice speak on loopback only" });
      return jsonResponse(await loadStatic("/api/hostess7-voice.json"));
    }
    if (path === "/api/threat-panel.json" || path === "/api/threat-panel") {
      try {
        return jsonResponse(await loadStatic("/api/threat-panel.json"));
      } catch (_e) {
        return okStub({ posture: "pages-surfaces", gates_held: true });
      }
    }
    if (path === "/api/hostess7-command") {
      if (method === "POST") {
        let body = {};
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
        const action = body.action || "";
        if (action === "iq_test") {
          return okStub({
            action: "iq_test",
            score: 0,
            pass_rate: 0,
            iq_pass: false,
            estimated_iq: 100,
            estimated_iq_band: "pages-static",
            note: "IQ battery requires live Hostess7 loopback",
          });
        }
        if (action === "ask" || action === "ask_needs_wants") {
          const query =
            String(body.message || body.query || "").trim() ||
            (action === "ask_needs_wants" ? "what do you need or want first" : "");
          const ask = await askCorpus(query);
          let status = { version: "2.0.7h" };
          try {
            status = await loadStatic("/api/status.json");
          } catch (_e) {}
          return jsonResponse({
            ok: true,
            reply: ask.text,
            engine: "github-mirror",
            lane: "github-mirror",
            truth_score: 68,
            deception_risk: "low",
            proposed_updates: [],
            github: { main_version: status.version },
            brain: { lane: "github-mirror", sovereign: false },
          });
        }
        if (action === "sync_github") {
          let brain = {};
          let dns = {};
          let zn = {};
          let status = {};
          try {
            brain = await loadStatic("/api/brain.json");
          } catch (_e) {}
          try {
            dns = await loadStatic("/api/field-dns.json");
          } catch (_e) {}
          try {
            zn = await loadStatic("/api/znetwork.json");
          } catch (_e) {}
          try {
            status = await loadStatic("/api/status.json");
          } catch (_e) {}
          const summary =
            "GitHub mind updated from NEXUS C2 · KILROY · iPXE · ZNetwork · Truth DNS · Field DHCP stack. " +
            "Sovereign brain unhooked on Pages — publish via ./Hostess7.sh pages-build.";
          return jsonResponse({
            ok: true,
            action: "sync_github",
            reply: summary,
            mind_updated: true,
            lane: "github-mirror",
            engine: "github-mirror",
            stack: {
              kilroy: { layer: -2, fkey: "F10" },
              nexus_c2: { layer: -3, fkey: "F9" },
              znetwork: { ok: zn.ok !== false, schema: zn.schema },
              dns: { schema: dns.schema || "field-dns/v2", title: dns.title },
              dhcp: { role: "Field DHCP" },
              ipxe: { role: "iPXE netboot lane" },
              brain: { mode: brain.mode, corpus: brain.corpus },
            },
            github: { main_version: status.version },
          });
        }
        return okStub({ action: action || "noop", lane: "github-mirror", note: "GitHub mind lane" });
      }
      try {
        return jsonResponse(await loadStatic("/api/hostess7-command.json"));
      } catch (_e) {
        return okStub({ schema: "hostess7-command/v1", pages: true, lane: "pages-surfaces" });
      }
    }
    if (path === "/api/universal-protector" || path === "/api/universal-protector/status") {
      try {
        return jsonResponse(await loadStatic("/api/universal-protector.json"));
      } catch (_e) {
        return okStub({ schema: "universal-protector/v1", threat_warn_level: "high", pillars: { persona: { hostess7_available: true } } });
      }
    }
    if (path === "/api/field-spatial") {
      try {
        return jsonResponse(await loadStatic("/api/field-spatial.json"));
      } catch (_e) {
        return okStub({ schema: "field-spatial/v1", movement_vector: null, scale_order: ["body", "room", "field", "planetary"] });
      }
    }
    if (path === "/api/hostess7/interaction" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/hostess7/interaction", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/hostess7-github-interaction.json"));
      } catch (_e2) {
        return okStub({
          ok: true,
          schema: "hostess7-github-interaction-panel/v1",
          boss: "hostess7",
          lane: "hostess7-github",
          pages: true,
          motto: "Interactions straight with Hostess 7 on GitHub — constant open connection. Secure for us.",
          secure_for_us: { sovereign_brain_unhooked_on_pages: true, pages_mirror_only: true },
          github_always: { enabled: true, open: true },
        });
      }
    }
    if (path === "/api/field-botnet-dns-dhcp/keepalive" && method === "POST") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-botnet-dns-dhcp/keepalive", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: (opts && opts.body) || "{}",
        });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/field-botnet-dns-dhcp-keepalive.json"));
      } catch (_e2) {
        return okStub({
          ok: true,
          schema: "field-botnet-dns-dhcp-keepalive/v1",
          boss: "hostess7",
          stable: true,
          secure: true,
          pages: true,
          bot_network: { node_count: 1, any_and_all: true },
          dns_dhcp: { dns: { running: true, truthful: true }, dhcp: { dns_option: ["127.0.0.1"] } },
        });
      }
    }
    if (path === "/api/field-botnet-dns-dhcp" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-botnet-dns-dhcp", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/field-botnet-dns-dhcp.json"));
      } catch (_e2) {
        return okStub({
          ok: true,
          schema: "field-botnet-dns-dhcp-panel/v1",
          boss: "hostess7",
          motto: "Bot network — secure stable DNS & DHCP for everyone through GitHub",
          pages: true,
          github_control_plane: { enabled: true, pages_runtime: "https://zacharygeurts.github.io/Hostess7/" },
        });
      }
    }
    if (path === "/api/field-everyone-counter" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-everyone-counter", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      let doc = null;
      let botnet = null;
      try {
        doc = await loadStatic("/api/field-everyone-counter.json");
      } catch (_e2) {
        doc = { ok: true, schema: "field-everyone-counter/v1", everyone_total: 0, pages: true };
      }
      try {
        botnet = await loadStatic("/api/field-botnet-dns-dhcp.json");
      } catch (_e3) { /* optional merge */ }
      const botNodes = Number((botnet && botnet.bot_network && botnet.bot_network.node_count) || 0);
      if (botNodes > 0) {
        doc.lanes = doc.lanes || {};
        doc.lanes.botnet = doc.lanes.botnet || { label: "Botnet nodes" };
        if (Number(doc.lanes.botnet.count || 0) < botNodes) doc.lanes.botnet.count = botNodes;
        doc.distributed_botnet = doc.distributed_botnet || { enabled: true };
        if (Number(doc.distributed_botnet.nodes || 0) < botNodes) doc.distributed_botnet.nodes = botNodes;
        const gh = Number((doc.lanes.github_people && doc.lanes.github_people.count) || 0);
        const exe = Number((doc.lanes.executable_people && doc.lanes.executable_people.count) || 0);
        const loop = Number((doc.lanes.loopback_sovereign && doc.lanes.loopback_sovereign.count) || 1);
        const total = botNodes + gh + exe + loop;
        if (Number(doc.everyone_total || 0) < total) doc.everyone_total = total;
      }
      doc.pages = true;
      return jsonResponse(doc);
    }
    if (path === "/api/field-internet/keepalive" && method === "POST") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-internet/keepalive", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: (opts && opts.body) || "{}",
        });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/field-internet-keepalive.json"));
      } catch (_e) {
        return okStub({
          schema: "field-internet-keepalive/v1",
          ok: true,
          pages: true,
          github: { always_open: true, open_count: 3 },
          one_voice: { boss: "hostess7", motto: "One thing talks everywhere — GitHub always open" },
        });
      }
    }
    if (path === "/api/field-github-legacy" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-github-legacy", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/field-github-legacy.json"));
      } catch (_e2) {
        return okStub({
          ok: true,
          schema: "field-github-legacy-panel/v1",
          boss: "hostess7",
          pages: true,
          stable_connection: true,
          github_always: { open_count: 4, legacy_open: 12, stable: true, always_open: true },
          motto: "All of GitHub stays open — canonical + legacy repos",
        });
      }
    }
    if (path === "/api/field-internet" && method === "GET") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/field-internet", { cache: "no-store" });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/field-internet.json"));
      } catch (_e) {
        return okStub({
          schema: "field-internet-unified-panel/v1",
          ok: true,
          boss: "hostess7",
          product: "AmmoNet",
          pages: true,
          api: "/api/field-internet",
          github_legacy: { stable: true, open: 12, canonical_open: 4 },
          motto: "Fielded bot network — one thing talks everywhere",
        });
      }
    }
    if (path === "/api/ammonet" && method === "GET") {
      try {
        return jsonResponse(await loadStatic("/api/ammonet.json"));
      } catch (_e) {
        return okStub({ schema: "ammonet-field/v1", product: "AmmoNet", pages: true });
      }
    }
    if (path === "/api/ammonet/meld" && method === "POST") {
      try {
        const r = await global.__H7_ORIG_FETCH__(LOOPBACK + "/api/ammonet/meld", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: (opts && opts.body) || "{}",
        });
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      return okStub({ melded: true, pages: true, note: "Full steel meld on loopback panel" });
    }
    if (path === "/api/final-internet" && method === "GET") {
      try {
        return jsonResponse(await loadStatic("/api/final-internet.json"));
      } catch (_e) {
        return okStub({ schema: "final-internet/v1", motto: "Safe fields for everyone" });
      }
    }
    if (path === "/api/steel-plates" && method === "GET") {
      try {
        return jsonResponse(await loadStatic("/api/steel-plates.json"));
      } catch (_e) {
        return okStub({ schema: "field-steel-neural-plates-slice/v1", plates: [] });
      }
    }
    if (path === "/api/plate-meld" && method === "GET") {
      try {
        return jsonResponse(await loadStatic("/api/plate-meld.json"));
      } catch (_e) {
        return okStub({ schema: "field-plate-meld/v1", partial: true });
      }
    }
    if (path === "/api/nexus-field") {
      try {
        return jsonResponse(await loadStatic("/api/nexus-field.json"));
      } catch (_e) {
        return jsonResponse(await loadStatic("/api/status.json"));
      }
    }
    if (path === "/api/update/status" || path.startsWith("/api/update/status?")) {
      try {
        return jsonResponse(await loadStatic("/api/pages-update-status.json"));
      } catch (_e) {
        const st = await loadStatic("/api/status.json");
        return okStub({
          current: st.version || "2.0.7h",
          update_available: false,
          pages: true,
          message: "GitHub Pages lane — upgrade on loopback panel",
        });
      }
    }
    if (path === "/api/update/apply" && method === "POST") {
      return okStub({ applied: false, note: "Upgrade on loopback only" });
    }
    if (path === "/api/update/sudo-prompt" && method === "POST") {
      return okStub({ prompted: false, note: "Pages lane" });
    }
    if (path === "/api/hostess7/appearance" || path === "/api/hostess7/core-of-truth") {
      return okStub({ schema: "hostess7-pages-static/v1", pages: true });
    }
    if (path === "/api/hostess7/training" || path === "/api/hostess7-training") {
      try {
        return jsonResponse(await loadStatic("/api/hostess7-training.json"));
      } catch (_e) {
        return okStub({ schema: "hostess7-training/v1", tracks: [], partial: true });
      }
    }
    if (path === "/api/operator/location" || path === "/api/operator-location") {
      try {
        return jsonResponse(await loadStatic("/api/operator-location.json"));
      } catch (_e) {
        return okStub({ schema: "operator-location/v1", mode: "pages" });
      }
    }
    if (path === "/api/data/packet-field" || path === "/api/packet-field") {
      try {
        return jsonResponse(await loadStatic("/api/packet-field.json"));
      } catch (_e) {
        return okStub({ updated: new Date().toISOString(), ports: [], recent: [] });
      }
    }
    if (path === "/api/library/catalog" || path === "/api/library-catalog") {
      try {
        const compact = await deweyCompact();
        if (compact.books && compact.books.length) {
          return jsonResponse(catalogFromCompact(compact));
        }
      } catch (_e) {}
      try {
        return jsonResponse(await loadStatic("/api/library-catalog.json"));
      } catch (_e) {
        return okStub({ books: [], updated: new Date().toISOString() });
      }
    }
    if (path === "/api/library/running-text") {
      try {
        return jsonResponse(await loadStatic("/api/library-running-text.json"));
      } catch (_e) {
        return okStub({ schema: "library-running-text/v1", lines: [] });
      }
    }
    if (path === "/api/dewey-index/facets" || path === "/api/dewey-index") {
      try {
        return jsonResponse(await loadStatic("/api/dewey-index-facets.json"));
      } catch (_e) {
        return okStub({ schema: "field-dewey-index-facets/v1", facets: {}, counts: {} });
      }
    }
    if (path === "/api/dewey-index/compact") {
      try {
        return jsonResponse(await deweyCompact());
      } catch (_e) {
        return okStub({ schema: "field-dewey-books-compact/v1", books: [], count: 0 });
      }
    }
    if (path.startsWith("/api/dewey-index/search")) {
      try {
        const compact = await deweyCompact();
        return jsonResponse(deweySearch(compact, u.searchParams));
      } catch (_e) {
        return okStub({ schema: "field-dewey-index-search/v1", hits: [], query: u.searchParams.get("q") || "" });
      }
    }
    if (path === "/api/card-catalog/panel") {
      try {
        return jsonResponse(await loadStatic("/api/card-catalog-panel.json"));
      } catch (_e) {
        try {
          const drawer = await cardDrawer();
          return jsonResponse({
            schema: "field-card-catalog-panel/v1",
            ok: true,
            pages: true,
            counts: drawer.counts || {},
            sort_modes: drawer.sort_modes || [],
            motto: drawer.motto || "Every book a card — joy for librarians.",
          });
        } catch (_e2) {
          return okStub({ schema: "field-card-catalog-panel/v1", counts: {} });
        }
      }
    }
    if (path.startsWith("/api/card-catalog/sort")) {
      try {
        const drawer = await cardDrawer();
        const mode = u.searchParams.get("mode") || "call_number";
        const rows = sortCards(drawer.cards || [], mode);
        return jsonResponse({
          ok: true,
          pages: true,
          sort: { sort_mode: mode, count: rows.length },
          cards: rows.slice(0, 200),
          count: rows.length,
        });
      } catch (_e) {
        return okStub({ cards: [], count: 0 });
      }
    }
    if (path.startsWith("/api/card-catalog/search")) {
      try {
        const drawer = await cardDrawer();
        return jsonResponse(cardSearch(drawer, u.searchParams));
      } catch (_e) {
        return okStub({ schema: "field-card-catalog-search/v1", hits: [], query: u.searchParams.get("q") || "" });
      }
    }
    if (path.startsWith("/api/card-catalog/card")) {
      const cid = u.searchParams.get("id") || "";
      try {
        const drawer = await cardDrawer();
        const card = (drawer.cards || []).find((c) => String(c.card_id || c.id) === cid);
        return jsonResponse(card ? { ok: true, card: card } : { ok: false, error: "not_found", id: cid });
      } catch (_e) {
        return okStub({ ok: false, error: "not_found", id: cid });
      }
    }
    if (path === "/api/card-catalog/detect") {
      return okStub({
        note: "Card catalog rebuild runs on loopback panel — Pages serves the published drawer.",
        rebuilt: false,
      });
    }
    if (path.startsWith("/api/") && method === "GET") {
      const alias = {
        "/api/field-command": "/api/field-command.json",
        "/api/gatekeeper": "/api/gatekeeper.json",
        "/api/lethal-enforcement": "/api/lethal-enforcement.json",
        "/api/hostess7-lethal-insight": "/api/hostess7-lethal-insight.json",
        "/api/us-field": "/api/us-field.json",
        "/api/us-obs-field": "/api/us-obs-field.json",
        "/api/field-obs": "/api/field-obs.json",
        "/api/us-voltage-regulation": "/api/us-voltage-regulation.json",
        "/api/home-protector": "/api/home-protector.json",
        "/api/local-services": "/api/local-services.json",
        "/api/host-attacks": "/api/host-attacks.json",
        "/api/terror-spiderweb": "/api/terror-spiderweb.json",
        "/api/planetary-observer": "/api/planetary-observer.json",
        "/api/precision-field": "/api/precision-field.json",
        "/api/angel-dossiers": "/api/angel-dossiers.json",
        "/api/human-dossier": "/api/human-dossier.json",
        "/api/angel-research": "/api/angel-research.json",
        "/api/honorability": "/api/honorability.json",
        "/api/audio-train": "/api/audio-train.json",
        "/api/field-rf": "/api/field-rf.json",
        "/api/signals-field": "/api/signals-field.json",
        "/api/field-hardware": "/api/field-hardware.json",
        "/api/field-hazard-onset": "/api/field-hazard-onset.json",
        "/api/field-radio": "/api/field-radio.json",
        "/api/field-dns": "/api/field-dns.json",
        "/api/field-outside-talk": "/api/field-outside-talk.json",
        "/api/field-drive": "/api/field-drive.json",
        "/api/field-brain": "/api/field-brain.json",
        "/api/settings": "/api/settings.json",
        "/api/compatibility": "/api/compatibility.json",
        "/api/diagnostic-mode": "/api/diagnostic-mode.json",
        "/api/police-agencies": "/api/police-agencies.json",
        "/api/human-registry": "/api/human-registry.json",
        "/api/gov-intel": "/api/gov-intel.json",
        "/api/program-tags": "/api/program-tags.json",
        "/api/census-field": "/api/census-field.json",
        "/api/existence-identity": "/api/existence-identity.json",
        "/api/queen-earball": "/api/queen-earball.json",
        "/api/queen-mouthball": "/api/queen-mouthball.json",
      };
      const staticPath = alias[path] || (path + ".json");
      try {
        return jsonResponse(await loadStatic(staticPath));
      } catch (_e) {
        if (path.split("/").length === 3) {
          return okStub({ schema: "pages-c2-slice/v1", held: true, posture: "war-ready", route: path });
        }
      }
    }
    if (path.startsWith("/api/") && method === "POST") {
      return okStub({ stored: true, pages: true, note: "Write on loopback panel" });
    }
    if (
      (path === "/api/field-c2-bookmarks" || path === "/api/hostess7/internet-clean") &&
      method === "POST"
    ) {
      try {
        const r = await global.__H7_ORIG_FETCH__(
          LOOPBACK + "/api/hostess7/internet-clean",
          { method: "POST", headers: { "Content-Type": "application/json" }, body: (opts && opts.body) || "{}" }
        );
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      return okStub({
        stored: true,
        pages: true,
        motto: "Clean the whole internet — secure bookmarks active on loopback panel",
      });
    }
    if (path === "/api/hostess7/internet-clean" && method === "GET") {
      try {
        return jsonResponse(await loadStatic("/api/hostess7-internet-clean.json"));
      } catch (_e) {
        return okStub({ default_on_hostess7: true, secure_nav: true });
      }
    }
    if (
      (path === "/api/hostess7/g16-online" || path.startsWith("/api/hostess7/g16-online/")) &&
      method === "GET"
    ) {
      try {
        return jsonResponse(await loadStatic("/api/hostess7-g16-online.json"));
      } catch (_e) {
        return okStub({
          ok: true,
          boss: "hostess7",
          online: { grok16_pages: "https://zacharygeurts.github.io/Grok16/" },
          routes: { pages_compiler: "/g16-build-output/" },
        });
      }
    }
    if (path === "/api/hostess7/g16-online/ensure" && method === "POST") {
      try {
        const r = await global.__H7_ORIG_FETCH__(
          LOOPBACK + "/api/hostess7/g16-online/ensure",
          { method: "POST", headers: { "Content-Type": "application/json" }, body: (opts && opts.body) || "{}" }
        );
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      return okStub({ ok: true, available: true, prefer: "online", pages: true });
    }
    if (
      (path === "/api/hostess7/lab" || path.startsWith("/api/hostess7/lab/")) &&
      method === "POST"
    ) {
      try {
        const r = await global.__H7_ORIG_FETCH__(
          LOOPBACK + path,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: (opts && opts.body) || "{}" }
        );
        if (r.ok) return jsonResponse(await r.json());
      } catch (_e) {}
      return okStub({
        ok: true,
        pages: true,
        boss: "hostess7",
        share_in: true,
        share_out: false,
        motto: "Share in · no share out — loopback panel runs the lab",
      });
    }
    if (
      (path === "/api/hostess7/lab" || path.startsWith("/api/hostess7/lab/")) &&
      method === "GET"
    ) {
      try {
        return jsonResponse(await loadStatic("/api/hostess7-lab-sovereign.json"));
      } catch (_e) {
        return okStub({ boss: "hostess7", share_in: true, share_out: false });
      }
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
      const q = u.searchParams.get("q") || "";
      try {
        const compact = await deweyCompact();
        const doc = deweySearch(compact, u.searchParams);
        return jsonResponse({
          ok: true,
          pages: true,
          query: q,
          books: doc.hits,
          hits: doc.hits,
          passages: [],
          count: doc.count,
        });
      } catch (_e) {
        try {
          return jsonResponse(searchIndex(await loadStatic("/api/library-index.json"), q || "children algebra"));
        } catch (_e2) {
          return jsonResponse({ ok: true, query: q, hits: [], books: [] });
        }
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
    if (path.startsWith("/api/ironclad/secure-api")) {
      const sub = path.replace("/api/ironclad/secure-api", "") || "/";
      if (sub === "" || sub === "/status" || sub === "/") {
        return jsonResponse({
          schema: "ironclad-secure-api/v1",
          ok: true,
          pages: true,
          singleton: true,
          ironclad_grounded: true,
          ironclad_citation: "ironclad:api:1",
          lane: "pages-surfaces",
          note: "Static Ironclad index on GitHub Pages — live gate on loopback :9477",
        });
      }
      if (sub === "/registry-index") {
        const ctx = u.searchParams.get("context") || "registry_index";
        const idx = await ironcladPagesIndex();
        const rows = ironcladSortEntries(idx.entries || [], ctx);
        return jsonResponse({
          schema: "ironclad-secure-api-registry-index/v1",
          ok: true,
          pages: true,
          context: ctx,
          entries: rows.slice(0, 200),
          count: Math.min(200, rows.length),
          ironclad_grounded: true,
        });
      }
      if (sub === "/search") {
        const q = u.searchParams.get("q") || "";
        const ctx = u.searchParams.get("context") || "all";
        const limit = Math.min(64, parseInt(u.searchParams.get("limit") || "32", 10) || 32);
        const idx = await ironcladPagesIndex();
        const hits = ironcladSearchHits(idx, q, ctx, limit);
        return jsonResponse({
          schema: "ironclad-secure-api-search/v1",
          ok: true,
          pages: true,
          query: q,
          context: ctx,
          hits: hits,
          count: hits.length,
          ironclad_grounded: true,
          ironclad_secure_api: true,
        });
      }
      if (sub === "/sort") {
        if (method === "GET") {
          const ctx = u.searchParams.get("context") || "registry_index";
          return jsonResponse({
            ok: true,
            pages: true,
            context: ctx,
            algorithm: ctx === "chip_catalog" ? "composite_bsp" : "family_then_label",
            ironclad_grounded: true,
          });
        }
        let body = {};
        try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
        const ctx = body.context || "registry_index";
        const sorted = ironcladSortEntries(body.entries || [], ctx);
        return jsonResponse({
          ok: true,
          pages: true,
          context: ctx,
          entries: sorted,
          ironclad_secure_api: true,
          ironclad_grounded: true,
          singleton: true,
        });
      }
      if (sub === "/routes") {
        const idx = await ironcladPagesIndex();
        const routes = (idx.entries || []).filter((e) => e.kind === "route" || e.source === "routes");
        return jsonResponse({ ok: true, pages: true, routes: routes.slice(0, 120), count: routes.length });
      }
    }
    if (path === "/api/ask" && method === "POST") {
      let body = {};
      try { body = JSON.parse((opts && opts.body) || "{}"); } catch (_e) { body = {}; }
      const query = String(body.query || body.q || "").trim();
      if (!query) return jsonResponse({ ok: false, error: "empty query" }, 400);
      try {
        return jsonResponse(await askCorpus(query));
      } catch (_e) {
        try {
          const seeds = await loadStatic("/api/ask-seeds.json");
          const hit = (seeds.answers || []).find((a) => {
            const ql = query.toLowerCase();
            return a.query && ql.includes(String(a.query).toLowerCase().slice(0, 12));
          });
          if (hit && hit.text) return jsonResponse({ ok: true, text: hit.text, query: query, route: "ask-seeds", lane: "github-mirror" });
        } catch (_e2) { /* fallback */ }
        return jsonResponse({
          ok: true,
          text: "Hostess 7 GitHub brain — corpus unavailable. Try /brain.html or ./Hostess7.sh boot.",
          query: query,
          route: "pages-fallback",
        });
      }
    }
    return null;
  }

  const origFetch = global.fetch.bind(global);
  global.__H7_ORIG_FETCH__ = origFetch;

  function pagesPathname(pathname) {
    let p = apiPath(pathname);
    const base = global.HOSTESS7_PAGES_BASE || "";
    if (base && p.startsWith("/api/") && !p.startsWith(base + "/api/")) {
      p = base + p;
    }
    if (base && p.startsWith("/assets/") && !p.startsWith(base + "/assets/")) {
      p = base + p;
    }
    return p;
  }

  global.fetch = async function (input, opts) {
    const url = typeof input === "string" ? input : input.url;
    try {
      const parsed = new URL(url, global.location.origin);
      if (parsed.origin === global.location.origin) {
        const norm = pagesPathname(parsed.pathname);
        if (norm.startsWith("/api/") || norm === "/health" || apiPath(parsed.pathname).startsWith("/api/")) {
          const routed = await routeApi(parsed.origin + norm + parsed.search, opts);
          if (routed) return routed;
        }
        if (norm.startsWith("/assets/") || apiPath(parsed.pathname).startsWith("/assets/")) {
          const fixed = assetUrl(apiPath(parsed.pathname)) + parsed.search;
          return origFetch(fixed, opts);
        }
      }
    } catch (_e) { /* fall through */ }
    return origFetch(input, opts);
  };

  global.Hostess7ApiShim = { routeApi: routeApi, LOOPBACK: LOOPBACK };
})(typeof window !== "undefined" ? window : globalThis);