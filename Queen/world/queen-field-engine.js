/**
 * Queen — field web engine (plated viewport, nested field safety, CHIPS/cores via Webbrowser).
 * G16: no entropy hotspots — status poll 30s, bounded depth stack, no tight loops.
 */
(function (global) {
  "use strict";

  const POLL_MS = 30000;
  const CANONICAL_FIELD_LAYER = 1;
  const MAX_DEPTH = CANONICAL_FIELD_LAYER;
  const HOME_FRAG = "queen-field-home.html";
  const BLANK = new Set(["", "about:blank", "about:srcdoc"]);

  let pollTimer = 0;
  let chipsCache = null;

  function $(id) {
    return document.getElementById(id);
  }

  function fieldDepth() {
    /* Single field at layer 1 — Ironclad safety; no field-on-field stack. */
    return CANONICAL_FIELD_LAYER;
  }

  function isQueenHomeUrl(src) {
    if (!src || BLANK.has(src)) return true;
    try {
      const u = new URL(src, location.origin);
      return u.pathname.includes(HOME_FRAG) || u.pathname.endsWith("/world/") || u.pathname.endsWith("/world");
    } catch (_) {
      return false;
    }
  }

  function isSurfacedUrl(src) {
    if (!src || BLANK.has(src)) return false;
    if (isQueenHomeUrl(src)) return true;
    try {
      const u = new URL(src, location.origin);
      return !(u.origin === location.origin && u.pathname.includes(HOME_FRAG));
    } catch (_) {
      return true;
    }
  }

  function setPlateVisible(show) {
    const plate = $("qb-field-plate");
    const viewport = document.querySelector(".qb-viewport");
    if (plate) plate.classList.toggle("qb-field-plate--hidden", !show);
    if (viewport) viewport.classList.toggle("qb-viewport--surfaced", !show);
  }

  function syncFramePlate(frame) {
    if (!frame) return;
    const src = frame.getAttribute("src") || frame.src || "";
    setPlateVisible(!isSurfacedUrl(src));
  }

  function wireViewportFrames() {
    const viewport = document.querySelector(".qb-viewport");
    if (!viewport) return;

    const observe = () => {
      viewport.querySelectorAll(".qb-frame").forEach((frame) => {
        if (frame.dataset.qfeWired) return;
        frame.dataset.qfeWired = "1";
        frame.addEventListener("load", () => syncFramePlate(frame));
        syncFramePlate(frame);
      });
    };

    observe();
    const mo = new MutationObserver(observe);
    mo.observe(viewport, { childList: true, subtree: true });
  }

  function renderDepthLabels(depth) {
    const layer = depth >= CANONICAL_FIELD_LAYER ? CANONICAL_FIELD_LAYER : CANONICAL_FIELD_LAYER;
    const label = `layer ${layer} · single field · depth sealed and destroyed`;
    $("qb-field-depth") && ($("qb-field-depth").textContent = `Field depth · ${label}`);
    $("qfh-depth") && ($("qfh-depth").textContent = `Field depth · ${label}`);
    $("qfh-nested") &&
      ($("qfh-nested").textContent = "Depth fields sealed and destroyed — one amplitude at field layer 1");
    document.body.dataset.fieldDepth = String(CANONICAL_FIELD_LAYER);
    document.body.dataset.depthFieldImpossible = "1";
    document.body.dataset.depthFieldsSealedAndDestroyed = "1";
  }

  function renderChips(doc) {
    if (!doc || typeof doc !== "object") return;
    chipsCache = doc;
    const chips = doc.chips || {};
    const g16 = doc.grok16 || {};
    const headers = chips.headers || 0;
    const ready = doc.surface === "webbrowser" || doc.web_surface || chips.present;
    const profile = g16.profile || "field_opt";
    const line = ready
      ? `CHIPS · ${headers} headers · ${profile} · Webbrowser`
      : "CHIPS · wiring… · Webbrowser surface";
    $("qb-field-rtx") && ($("qb-field-rtx").textContent = line);
    $("qfh-rtx") && ($("qfh-rtx").textContent = line);
    $("qfh-rtx-card") &&
      ($("qfh-rtx-card").textContent = `${headers} headers · ${(chips.platforms || []).length} platforms · web`);
  }

  async function pollChips() {
    try {
      const r = await fetch("/api/chips", { cache: "no-store" });
      if (r.ok) renderChips(await r.json());
    } catch (_) {
      /* loopback only — quiet */
    }
  }

  function schedulePoll() {
    if (pollTimer) return;
    pollChips();
    pollTimer = global.setInterval(() => {
      pollChips();
      global.QueenFieldSanity?.runPass?.();
    }, POLL_MS);
  }

  function snapDimensionalPits() {
    if (global.QueenFieldSanity?.snapPitsInstant) {
      return global.QueenFieldSanity.snapPitsInstant();
    }
    let pits = 0;
    document.querySelectorAll(".qb-frame").forEach((frame) => {
      const src = frame.getAttribute("src") || frame.src || "";
      if (/[?&]field_depth=[1-9]\d*/.test(src)) {
        pits += 1;
        const clean = src.replace(/([?&])field_depth=\d+/g, "").replace(/\?&/, "?").replace(/[?&]$/, "");
        frame.setAttribute("src", clean);
      }
    });
    return { ok: true, instant: true, pits_snapped: pits };
  }

  function nestedFieldGuard() {
    snapDimensionalPits();
    const depth = fieldDepth();
    renderDepthLabels(depth);
    if (depth >= MAX_DEPTH) {
      document.body.classList.add("qb-field-depth-cap");
    }
    try {
      global.parent?.postMessage?.(
        { type: "queen_field_ping", depth, origin: "queen-field-engine" },
        location.origin,
      );
    } catch (_) {
      /* cross-origin parent — hold */
    }
  }

  const FIELD_MSG = new Set(["queen_field_ping", "queen_field_sanity", "queen_field_die"]);

  function onFieldMessage(ev) {
    if (ev.origin !== location.origin) return;
    const data = ev.data;
    if (!data || typeof data !== "object") return;
    if (data.origin && data.origin !== "queen-field-engine" && data.origin !== "queen-field-sanity") return;
    if (!FIELD_MSG.has(data.type)) return;
    if (data.type === "queen_field_die") {
      snapDimensionalPits();
      global.QueenFieldSanity?.instantFieldDieCheck?.();
      renderDepthLabels(CANONICAL_FIELD_LAYER);
      return;
    }
    if (data.type === "queen_field_ping" && typeof data.depth === "number" && data.depth > CANONICAL_FIELD_LAYER) {
      snapDimensionalPits();
      renderDepthLabels(CANONICAL_FIELD_LAYER);
    }
    if (data.type === "queen_field_sanity" && data.gate_ok === false) {
      document.body.dataset.fieldSanity = "hold";
    }
  }

  function init() {
    nestedFieldGuard();
    wireViewportFrames();
    schedulePoll();
    global.addEventListener("message", onFieldMessage);

    const plate = $("qb-field-plate");
    if (plate && !document.querySelector(".qb-viewport .qb-frame")) {
      setPlateVisible(true);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.QueenFieldEngine = {
    depth: fieldDepth,
    snapDimensionalPits,
    setPlateVisible,
    syncFramePlate,
    pollChips,
    pollRtx: pollChips,
    MAX_DEPTH,
  };
})(typeof window !== "undefined" ? window : globalThis);