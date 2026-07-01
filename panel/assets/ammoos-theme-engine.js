/**
 * AmmoOS Theme Engine — canonical client index; Queen Styles delegates token apply here.
 */
(function (global) {
  "use strict";

  const API = "/api/ammoos-themes";
  const STORAGE_KEY = "queen-styles-v1";

  const COLOR_FIELDS = [
    ["bg", "Background"],
    ["surface", "Surface"],
    ["elevated", "Elevated"],
    ["panel", "Panel"],
    ["border", "Border"],
    ["text", "Text"],
    ["dim", "Dim"],
    ["accent", "Accent"],
    ["rose", "Rose"],
    ["gold", "Gold"],
    ["ok", "OK"],
    ["warn", "Warn"],
    ["danger", "Danger"],
  ];

  const TYPO_FIELDS = [
    ["ui_font", "UI font", "text"],
    ["mono_font", "Mono font", "text"],
    ["base_size", "Base size", "text"],
    ["line_height", "Line height", "text"],
  ];

  const WIDGET_FIELDS = [
    ["radius", "Corner radius", "text"],
    ["btn_radius", "Button radius", "text"],
    ["btn_padding", "Button padding", "text"],
    ["input_radius", "Input radius", "text"],
    ["pill_radius", "Pill radius", "text"],
    ["dropdown_radius", "Dropdown radius", "text"],
    ["shadow", "Shadow", "text"],
  ];

  const state = { catalog: null, ready: false };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "catalog" }),
      credentials: "same-origin",
    });
    if (!r.ok) throw new Error("themes HTTP " + r.status);
    return r.json();
  }

  async function fetchCatalog(force) {
    if (state.catalog && !force) return state.catalog;
    const doc = await api({ action: "catalog" });
    state.catalog = doc;
    state.ready = true;
    return doc;
  }

  function applyQueenTokens(theme) {
    if (!theme?.tokens) return;
    const root = document.documentElement;
    const c = theme.tokens.colors || {};
    const t = theme.tokens.typography || {};
    const w = theme.tokens.widgets || {};
    const ch = theme.tokens.chrome || {};

    const qm = {
      bg: c.bg,
      surface: c.surface,
      elevated: c.elevated,
      border: c.border,
      text: c.text,
      dim: c.dim,
      accent: c.accent,
      rose: c.rose,
      gold: c.gold,
      ok: c.ok,
      warn: c.warn,
      danger: c.danger,
      radius: w.radius,
      shadow: w.shadow,
      font: t.ui_font,
      mono: t.mono_font,
    };
    for (const [k, v] of Object.entries(qm)) {
      if (v != null) root.style.setProperty(`--qm-${k.replace(/_/g, "-")}`, String(v));
    }

    const world = {
      bg: c.bg || c.void,
      bg2: c.surface,
      void: c.void || c.bg,
      panel: c.panel || c.surface,
      border: c.border,
      phi: c.phi || c.accent,
      emerald: c.emerald || c.ok,
      thermo: c.thermo || c.warn,
      flow: c.flow || c.accent,
      gold: c.gold,
      aqua: c.aqua || c.accent,
      rose: c.rose,
      "rose-soft": c.rose_soft || c.rose,
      accent: c.accent,
      text: c.text,
      dim: c.dim,
      muted: c.dim,
      ok: c.ok,
      warn: c.warn,
      radius: w.radius,
      font: t.ui_font,
      mono: t.mono_font,
    };
    for (const [k, v] of Object.entries(world)) {
      if (v != null) root.style.setProperty(`--${k}`, String(v));
    }

    for (const [k, v] of Object.entries(c)) {
      if (v != null) root.style.setProperty(`--qb-${k.replace(/_/g, "-")}`, String(v));
    }

    if (w.btn_radius) root.style.setProperty("--qs-btn-radius", w.btn_radius);
    if (w.btn_padding) root.style.setProperty("--qs-btn-padding", w.btn_padding);
    if (w.input_radius) root.style.setProperty("--qs-input-radius", w.input_radius);
    if (w.pill_radius) root.style.setProperty("--qs-pill-radius", w.pill_radius);
    if (w.dropdown_radius) root.style.setProperty("--qs-dropdown-radius", w.dropdown_radius);
    if (ch.tab_height) root.style.setProperty("--qs-tab-height", ch.tab_height);
    if (ch.url_bar_height) root.style.setProperty("--qs-url-height", ch.url_bar_height);
    if (ch.corner_radius) root.style.setProperty("--qs-chrome-radius", ch.corner_radius);

    if (t.ui_font) {
      root.style.fontFamily = t.ui_font;
      if (document.body) document.body.style.fontFamily = t.ui_font;
    }
    if (t.base_size) root.style.fontSize = t.base_size;
    if (t.line_height && document.body) document.body.style.lineHeight = t.line_height;

    root.dataset.queenTheme = theme.id;
    if (document.body) document.body.dataset.queenTheme = theme.id;
    document.dispatchEvent(new CustomEvent("queen-styles-changed", { detail: { id: theme.id } }));
  }

  function applyC2Theme(id, meta) {
    const root = document.documentElement;
    const attr = meta?.data_attr || id;
    root.dataset.ammoosTheme = attr;
    root.dataset.osTheme = id === "nexus_c2" ? "" : id;
    const vars = meta?.vars || {};
    for (const [k, v] of Object.entries(vars)) {
      if (v != null) root.style.setProperty(k, String(v));
    }
    try {
      global.parent?.postMessage({ type: "nexus:theme", c2: id, attr }, "*");
    } catch (_) {}
  }

  function themeById(catalog, id) {
    const themes = catalog?.queen_styles?.themes || [];
    return themes.find((t) => t.id === id) || null;
  }

  function syncLocalQueenStore(activeId, custom) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ activeId, custom: custom || [] }));
    } catch (_) {}
  }

  async function apply(patch) {
    const doc = await api({ action: "apply", patch });
    state.catalog = doc;
    const active = doc.active || {};
    const c2 = doc.c2_themes?.[active.c2];
    if (c2) applyC2Theme(active.c2, c2);
    const qt = themeById(doc, active.queen_styles);
    if (qt) {
      applyQueenTokens(qt);
      syncLocalQueenStore(active.queen_styles, (doc.queen_styles?.themes || []).filter((t) => !t.built_in));
    }
    if (global.QueenStyles?.applyTheme && qt) {
      try {
        global.QueenStyles.applyTheme(active.queen_styles);
      } catch (_) {}
    }
    return doc;
  }

  async function boot() {
    try {
      const doc = await fetchCatalog();
      const active = doc.active || {};
      const c2 = doc.c2_themes?.[active.c2];
      if (c2) applyC2Theme(active.c2, c2);
      const qt = themeById(doc, active.queen_styles);
      if (qt) applyQueenTokens(qt);
    } catch (_) {}
  }

  function fieldGrid(fields, section, theme, editable) {
    return `<div class="at-grid">${fields
      .map(([key, label, kind]) => {
        const val = theme?.tokens?.[section]?.[key] ?? "";
        if (kind === "text") {
          return `<label class="at-field"><span>${label}</span><input type="text" data-at-section="${section}" data-at-key="${key}" value="${esc(val)}" ${editable ? "" : "disabled"} /></label>`;
        }
        const color = String(val || "#000000").startsWith("#") ? val : "#010302";
        return `<label class="at-field"><span>${label}</span><input type="color" data-at-section="${section}" data-at-key="${key}" value="${esc(color)}" ${editable ? "" : "disabled"} /></label>`;
      })
      .join("")}</div>`;
  }

  global.AmmoosThemes = {
    API,
    COLOR_FIELDS,
    TYPO_FIELDS,
    WIDGET_FIELDS,
    fetchCatalog,
    apply,
    applyQueenTokens,
    applyC2Theme,
    themeById,
    fieldGrid,
    esc,
    boot,
    getCatalog: () => state.catalog,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})(window);