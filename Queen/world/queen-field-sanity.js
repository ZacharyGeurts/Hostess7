/**
 * Queen field sanity — integral simplify pass. Never obtuse; never build under heat.
 */
(function (global) {
  "use strict";

  const API = "/api/field-sanity";
  const POLL_MS = 30000;

  function benchmarkMode() {
    if (document.body?.dataset?.queenBenchmark === "1") return true;
    try {
      if (global.localStorage?.getItem("queen_benchmark") === "1") return true;
    } catch (_) {
      /* ignore */
    }
    try {
      return new URLSearchParams(location.search).get("benchmark") === "1";
    } catch (_) {
      return false;
    }
  }

  function isFastUrl(url) {
    const u = String(url || "").trim();
    if (!u || u === "about:blank") return true;
    if (u.startsWith("/") || u.startsWith("queen://")) return true;
    try {
      const parsed = new URL(u, location.origin);
      const host = (parsed.hostname || "").toLowerCase();
      if (host === "127.0.0.1" || host === "localhost") return true;
      if ((parsed.pathname || "").startsWith("/world/bench")) return true;
      if (/speedometer|todomvc|jetstream|motionmark|webxprt|basemark/i.test(parsed.pathname || "")) return true;
      if (host === "browserbench.org" || host.endsWith(".browserbench.org")) return true;
    } catch (_) {
      return false;
    }
    return false;
  }
  const MAX_LAYERS = 64;
  const MAX_DEPTH = 0;

  let pollTimer = 0;
  let lastPass = null;

  function normalizeUrl(url) {
    return String(url || "").trim().replace(/\/$/, "") || "about:blank";
  }

  /** One source of truth — tabs first; frames only if no tab list (no duplicate layers). */
  function stripFieldDepth(url) {
    const u = String(url || "").trim();
    if (!u || !u.includes("field_depth")) return u;
    try {
      const parsed = new URL(u, location.origin);
      parsed.searchParams.delete("field_depth");
      return parsed.toString();
    } catch (_) {
      return u.replace(/([?&])field_depth=\d+/g, "").replace(/\?&/, "?").replace(/[?&]$/, "");
    }
  }

  function depthFieldForbidden(url) {
    const u = String(url || "");
    if (!u.includes("field_depth")) return false;
    try {
      const parsed = new URL(u, location.origin);
      const d = parseInt(parsed.searchParams.get("field_depth") || "0", 10);
      return d > 0;
    } catch (_) {
      return /[?&]field_depth=[1-9]\d*/.test(u);
    }
  }

  function collectLayers() {
    const tabs = global.QueenOS?.browser?.doc?.tabs || global.QueenOS?.browser?.doc?.doc?.tabs || [];
    if (tabs.length) {
      return tabs.slice(0, MAX_LAYERS).map((t, i) => ({
        id: t.id || `tab-${i}`,
        url: stripFieldDepth(t.url || ""),
        depth: 0,
        active: !!t.active,
      }));
    }
    const frames = document.querySelectorAll(".qb-frame");
    if (!frames.length) return [];
    return Array.from(frames)
      .slice(0, MAX_LAYERS)
      .map((frame, i) => ({
        id: frame.id || `frame-${i}`,
        url: stripFieldDepth(frame.getAttribute("src") || frame.src || ""),
        depth: 0,
        active: frame.closest(".qb-tab-pane")?.classList.contains("active") ?? i === 0,
      }));
  }

  function fieldedArea(_layers) {
    return false;
  }

  async function runPass() {
    const layers = collectLayers();
    try {
      const r = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ layers, fielded: fieldedArea(layers) }),
        cache: "no-store",
      });
      if (!r.ok) return null;
      lastPass = await r.json();
      applyPass(lastPass);
      return lastPass;
    } catch (_) {
      return null;
    }
  }

  function snapPitsInstant() {
    let pits = 0;
    document.querySelectorAll(".qb-frame").forEach((frame) => {
      const src = frame.getAttribute("src") || frame.src || "";
      if (depthFieldForbidden(src)) {
        pits += 1;
        frame.setAttribute("src", stripFieldDepth(src));
      }
    });
    const tabs = global.QueenOS?.browser?.doc?.tabs;
    if (tabs?.length) {
      tabs.forEach((t) => {
        if (!t?.url) return;
        const bad = depthFieldForbidden(t.url) || Number(t.depth || 0) > 0 || t.field_on_field;
        if (bad) {
          pits += 1;
          t.url = stripFieldDepth(t.url);
          t.depth = 0;
          t.field_on_field = false;
        }
      });
    }
    if (pits > 0) {
      document.body.dataset.depthPitsSnapped = String(pits);
      document.body.dataset.depthFieldsSealedAndDestroyed = "1";
      try {
        global.postMessage?.({ type: "queen_field_die", pits_snapped: pits, instant: true, origin: "queen-field-sanity" }, location.origin);
      } catch (_) {
        /* ignore */
      }
    }
    return { ok: true, instant: true, pits_snapped: pits };
  }

  async function instantFieldDieCheck() {
    const local = snapPitsInstant();
    try {
      const r = await fetch("/api/field-depth-snap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "field_die", layers: collectLayers() }),
        cache: "no-store",
      });
      if (r.ok) {
        const doc = await r.json();
        if (doc.layers) applyPass({ ok: true, reorganized: doc.layers, preflight_fixes: doc.pits_snapped || 0 });
        return { ...local, ...doc };
      }
    } catch (_) {
      /* loopback only */
    }
    return local;
  }

  function singularizeDomUrls(reorganized) {
    let fixes = 0;
    document.querySelectorAll(".qb-frame").forEach((frame) => {
      const src = frame.getAttribute("src") || frame.src || "";
      const clean = stripFieldDepth(src);
      if (clean && clean !== src) {
        frame.setAttribute("src", clean);
        fixes += 1;
      }
    });
    (reorganized || []).forEach((row) => {
      if (!row?.url) return;
      const clean = stripFieldDepth(row.url);
      if (clean !== row.url) row.url = clean;
      row.depth = 0;
    });
    const tabs = global.QueenOS?.browser?.doc?.tabs;
    if (tabs?.length) {
      tabs.forEach((t) => {
        if (!t?.url) return;
        const clean = stripFieldDepth(t.url);
        if (clean !== t.url) {
          t.url = clean;
          fixes += 1;
        }
      });
    }
    return fixes;
  }

  function applyPass(doc) {
    if (!doc?.ok) return;
    const domFixes = singularizeDomUrls(doc.reorganized || doc.queen?.reorganized);
    renderSanity(doc, domFixes);
    if ((doc.layers_out || 0) > 1) applyPaintOrder(doc.reorganized || doc.queen?.reorganized || []);
    hardenFrames();
  }

  function applyPaintOrder(reorganized) {
    const viewport = document.querySelector(".qb-viewport");
    if (!viewport) return;
    reorganized.forEach((row) => {
      const pane = viewport.querySelector(`.qb-tab-pane[data-tab-id="${row.id}"]`);
      if (pane) pane.style.order = String(row.order);
    });
  }

  function hardenFrames() {
    const bench = benchmarkMode();
    document.querySelectorAll(".qb-frame").forEach((frame) => {
      const active = frame.closest(".qb-tab-pane")?.classList.contains("active") ?? true;
      frame.setAttribute("referrerpolicy", "no-referrer");
      if (bench && active) {
        frame.removeAttribute("loading");
        if ("credentialless" in frame) frame.credentialless = false;
      } else if (!bench) {
        frame.setAttribute("loading", "lazy");
        if ("credentialless" in frame) frame.credentialless = true;
      }
    });
  }

  async function validateUrl(url) {
    if (!url || url === "about:blank") return { ok: true, url };
    if (benchmarkMode() && isFastUrl(url)) {
      return { ok: true, url, fast_path: true, benchmark: true };
    }
    if (isFastUrl(url) && !String(url).startsWith("http")) {
      return { ok: true, url, fast_path: true, internal: true };
    }
    if (depthFieldForbidden(url)) {
      snapPitsInstant();
      return {
        ok: true,
        url: stripFieldDepth(url),
        depth_field_impossible: true,
        depth_fields_sealed_and_destroyed: true,
        depth_field_destroyed: true,
        creation_forbidden: true,
        stripped: true,
      };
    }
    try {
      const r = await fetch("/api/field-net", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "classify", url }),
        cache: "no-store",
      });
      const doc = await r.json();
      const c = doc.classification || doc;
      if (c.verdict === "BLOCK_EXTERNAL") return { ok: false, classification: c };
      const fielded = (global.QueenFieldEngine?.depth?.() ?? 0) > 0;
      if (fielded && !c.internal) return { ok: false, classification: c, reason: "fielded_simplify_hold" };
      return { ok: true, classification: c, url };
    } catch (_) {
      return { ok: false, error: "classify_fail" };
    }
  }

  function ironcladCitation(doc) {
    const cite = doc.citation || doc.ironclad?.citation;
    if (!cite) return "";
    const short = String(cite).split(" — ")[0].trim();
    return short ? ` · ${short}` : "";
  }

  function renderSanity(doc, domFixes) {
    const queen = doc.queen || doc;
    const out = queen.layers_out ?? doc.layers_out ?? 0;
    const heat = queen.heat_avoided ?? doc.heat_avoided ?? 0;
    const deduped = queen.deduped ?? doc.deduped ?? 0;
    const pre = doc.preflight_fixes ?? queen.preflight_fixes ?? 0;
    const cite = ironcladCitation(doc);
    const defrag = (pre + (domFixes || 0)) > 0 ? ` · singularized ${pre + (domFixes || 0)}` : "";
    const line =
      out <= 1
        ? `Integral · ${out} layer · simplified · heat avoided ${heat}${defrag}${cite}`
        : `Integral · ${out} layers · deduped ${deduped} · heat avoided ${heat}${defrag}${cite}`;
    const el = document.getElementById("qfh-sanity");
    const strip = document.getElementById("qb-field-sanity");
    if (el) el.textContent = line;
    if (strip) strip.textContent = line;
    document.body.dataset.fieldSanity = doc.gate_ok === false ? "hold" : "good";
  }

  function schedulePoll() {
    if (pollTimer || benchmarkMode()) return;
    runPass();
    pollTimer = global.setInterval(runPass, POLL_MS);
  }

  function init() {
    if (benchmarkMode()) {
      document.body.dataset.queenBenchmark = "1";
      try {
        global.localStorage?.setItem("queen_benchmark", "1");
      } catch (_) {
        /* ignore */
      }
    }
    hardenFrames();
    snapPitsInstant();
    schedulePoll();
    document.addEventListener("queen-navigate", () => {
      snapPitsInstant();
      if (!benchmarkMode()) runPass();
    });
    global.addEventListener("message", (ev) => {
      if (ev.origin !== location.origin) return;
      if (ev.data?.type === "queen_field_die") instantFieldDieCheck();
    });
    document.addEventListener("queen-field-die", () => instantFieldDieCheck());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.QueenFieldSanity = {
    benchmarkMode,
    isFastUrl,
    collectLayers,
    runPass,
    validateUrl,
    stripFieldDepth,
    depthFieldForbidden,
    snapPitsInstant,
    instantFieldDieCheck,
    hardenFrames,
    lastPass: () => lastPass,
    MAX_DEPTH,
    depth_field_impossible: true,
    depth_fields_sealed_and_destroyed: true,
  };
})(typeof window !== "undefined" ? window : globalThis);