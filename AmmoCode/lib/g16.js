/**
 * AmmoCode g16 bridge — preconfigured for Grok16 5.0 belt_2_0 on any GUI surface.
 */
(function (global) {
  "use strict";

  const DEFAULTS = {
    pkgVersion: "Grok16-5.1.0",
    beltProfile: "belt_2_0",
    g16Version: "16.2.0",
    apiBase: "/api/ammocode",
    grok16Root: "",
  };

  function config(overrides) {
    const cfg = { ...DEFAULTS, ...(global.AmmoCodeG16Config || {}), ...(overrides || {}) };
    global.AmmoCodeG16Config = cfg;
    return cfg;
  }

  function profileForLanguage(lang, profiles) {
    const map = profiles || {};
    return map[lang] || map.default || cfg().beltProfile;
  }

  function cfg() {
    return global.AmmoCodeG16Config || config();
  }

  async function loadLanguages() {
    try {
      const r = await fetch("data/languages.json", { cache: "no-store" });
      if (r.ok) return r.json();
    } catch (_) {}
    return { languages: ["c", "cxx", "python", "ammolang", "field"], extensions: {}, profiles: { default: "belt_2_0" } };
  }

  async function discern(path, content) {
    const c = cfg();
    if (c.apiBase) {
      try {
        const r = await fetch(c.apiBase, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "discern", path, content }),
        });
        const j = await r.json();
        if (j.ok && j.language) return j.language;
      } catch (_) {}
    }
    if (path && global.AmmoCodeHighlight?.langFromPath) {
      return global.AmmoCodeHighlight.langFromPath(path);
    }
    return "plaintext";
  }

  async function ping() {
    const c = cfg();
    if (!c.apiBase) return { ok: false, error: "no_api" };
    try {
      const r = await fetch(c.apiBase, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "ping" }),
      });
      return r.json();
    } catch (e) {
      return { ok: false, error: String(e.message || e) };
    }
  }

  async function g16Action(action, payload) {
    const c = cfg();
    const r = await fetch(c.apiBase, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, profile: c.beltProfile, ...payload }),
    });
    return r.json();
  }

  async function loadFieldDoctrine() {
    try {
      const r = await fetch("data/ammocode-field-doctrine.json", { cache: "no-store" });
      if (r.ok) return r.json();
    } catch (_) {}
    return {
      policy: { ammocode_is_field: true, no_subfields: true, defield_if_resting_on_field: true },
    };
  }

  function resolveFieldPosture(surface) {
    const cached = global.AmmoCodeG16Config?.fieldPosture;
    if (cached) return cached;
    const s = String(surface || "plain").toLowerCase();
    const fieldSurfaces = new Set([
      "field", "fld", "nexus_field", "queen_field", "organized_field", "singular_field",
    ]);
    const resting = fieldSurfaces.has(s);
    if (resting) {
      return { posture: "defield", field: false, no_subfields: true, resting_on_field: true };
    }
    return { posture: "field", field: true, no_subfields: true, resting_on_field: false };
  }

  async function fetchFieldPosture(surface) {
    const c = cfg();
    if (!c.apiBase) return resolveFieldPosture(surface);
    try {
      const r = await fetch(c.apiBase, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "field_posture", surface: surface || "plain" }),
      });
      const j = await r.json();
      if (j.ok && j.ammocode_field) {
        global.AmmoCodeG16Config = { ...c, fieldPosture: j.ammocode_field };
        return j.ammocode_field;
      }
    } catch (_) {}
    return resolveFieldPosture(surface);
  }

  global.AmmoCodeG16 = {
    config,
    cfg,
    loadLanguages,
    loadFieldDoctrine,
    discern,
    profileForLanguage,
    resolveFieldPosture,
    fetchFieldPosture,
    g16Action,
    ping,
    DEFAULTS,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);