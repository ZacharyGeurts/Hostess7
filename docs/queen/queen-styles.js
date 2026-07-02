/**
 * Queen Styles — full CSS theming (colors, typography, widgets, chrome).
 * Rebrands queen-theme-2026 seal into an editable Styles flyout.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "queen-styles-v1";
  const THEME_JSON = "/gui/queen-styles-themes.json";
  const ALLOWED_STYLES = new Set([
    "queen-modern.css",
    "queen-world.css",
    "queen-browser-shell.css",
    "queen-branding.css",
    "queen-styles.css",
  ]);

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

  const state = {
    builtIn: [],
    custom: [],
    activeId: "black_emerald_rose_2026",
    highlightId: null,
    flyout: null,
    ready: false,
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function basename(href) {
    try {
      return new URL(href, location.href).pathname.split("/").pop() || "";
    } catch {
      return "";
    }
  }

  function loadStore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const doc = JSON.parse(raw);
      state.activeId = doc.activeId || state.activeId;
      state.custom = Array.isArray(doc.custom) ? doc.custom : [];
    } catch (_) {}
  }

  function saveStore() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ activeId: state.activeId, custom: state.custom }),
      );
    } catch (_) {}
  }

  function cloneTokens(tokens) {
    return JSON.parse(JSON.stringify(tokens || {}));
  }

  function allThemes() {
    return [...state.builtIn, ...state.custom];
  }

  function themeById(id) {
    return allThemes().find((t) => t.id === id) || null;
  }

  function activeTheme() {
    return themeById(state.activeId) || state.builtIn[0] || null;
  }

  function isEditable(theme) {
    return theme && !theme.built_in;
  }

  function applyTokens(theme) {
    if (!theme?.tokens) return;
    if (window.AmmoosThemes?.applyQueenTokens) {
      window.AmmoosThemes.applyQueenTokens(theme);
      return;
    }
    const root = document.documentElement;
    const c = theme.tokens.colors || {};
    for (const [k, v] of Object.entries(c)) {
      if (v != null) root.style.setProperty(`--qb-${k.replace(/_/g, "-")}`, String(v));
    }
    document.documentElement.dataset.queenTheme = theme.id;
    if (document.body) document.body.dataset.queenTheme = theme.id;
    document.dispatchEvent(new CustomEvent("queen-styles-changed", { detail: { id: theme.id } }));
  }

  function applyTheme(id) {
    const theme = themeById(id);
    if (!theme) return;
    state.activeId = id;
    applyTokens(theme);
    saveStore();
    renderFlyout();
  }

  function addCustomFromCurrent() {
    const src = activeTheme();
    if (!src) return;
    const n = state.custom.length + 1;
    const id = `custom_${Date.now()}`;
    const label = `Custom from ${src.label || src.id}`;
    const theme = {
      id,
      label,
      built_in: false,
      highlight: true,
      tokens: cloneTokens(src.tokens),
      created: new Date().toISOString(),
    };
    state.custom.push(theme);
    state.highlightId = id;
    state.activeId = id;
    applyTokens(theme);
    saveStore();
    renderFlyout();
    const rename = $("#qs-rename", state.flyout);
    if (rename) {
      rename.value = label;
      rename.classList.add("qs-rename--highlight");
      rename.focus();
      rename.select();
    }
  }

  function renameActive(label) {
    const theme = themeById(state.activeId);
    if (!theme || theme.built_in) return;
    theme.label = String(label || theme.label).trim() || theme.label;
    theme.highlight = false;
    state.highlightId = null;
    saveStore();
    renderFlyout();
  }

  function updateToken(section, key, value) {
    const theme = themeById(state.activeId);
    if (!isEditable(theme)) return;
    theme.tokens[section] = theme.tokens[section] || {};
    theme.tokens[section][key] = value;
    applyTokens(theme);
    saveStore();
  }

  let _sealed = false;

  function sealHead() {
    if (_sealed) return null;
    _sealed = true;
    document.querySelectorAll("head script:not([data-queen-theme])").forEach((el) => {
      if (el.src && !String(el.src).includes("queen-theme-2026.js") && !String(el.src).includes("queen-styles.js")) {
        el.dataset.queenTheme = "1";
      }
    });
    document.querySelectorAll("head link[rel='stylesheet']").forEach((el) => {
      if (ALLOWED_STYLES.has(basename(el.href))) el.dataset.queenTheme = "1";
    });

    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType !== 1) continue;
          const el = node;
          if (el.tagName === "SCRIPT" && !el.dataset.queenTheme) {
            el.remove();
            continue;
          }
          if (el.tagName === "LINK" && el.rel === "stylesheet" && !el.dataset.queenTheme) {
            if (!ALLOWED_STYLES.has(basename(el.href))) el.remove();
            continue;
          }
          if (el.tagName === "STYLE" && !el.dataset.queenTheme) el.remove();
        }
      }
    });
    obs.observe(document.head, { childList: true, subtree: true });
    return obs;
  }

  function fieldGrid(fields, section, theme, editable) {
    return `<div class="qs-grid">${fields
      .map(([key, label, kind]) => {
        const val = theme?.tokens?.[section]?.[key] ?? "";
        if (kind === "text") {
          return `<label class="qs-field"><span>${label}</span><input type="text" data-qs-section="${section}" data-qs-key="${key}" value="${String(val).replace(/"/g, "&quot;")}" ${editable ? "" : "disabled"} /></label>`;
        }
        const color = String(val || "#000000").startsWith("#") ? val : "#010302";
        return `<label class="qs-field"><span>${label}</span><input type="color" data-qs-section="${section}" data-qs-key="${key}" value="${color}" ${editable ? "" : "disabled"} /></label>`;
      })
      .join("")}</div>`;
  }

  function ensureFlyout() {
    if (state.flyout) return state.flyout;
    const el = document.createElement("aside");
    el.id = "qb-styles-flyout";
    el.className = "qb-styles-flyout";
    el.setAttribute("aria-label", "Queen Styles");
    el.setAttribute("aria-hidden", "true");
    el.innerHTML = [
      '<header class="qs-head">',
      "<h2>Styles</h2>",
      '<p class="qs-muted">Quick flyout — <a href="/control-panel?tab=themes" class="qs-index-link">Queen Settings → Themes</a> is the full index.</p>',
      '<div class="qs-theme-bar">',
      '<select id="qs-theme-select" class="qs-theme-select" aria-label="Theme"></select>',
      '<button type="button" id="qs-theme-add" class="qs-theme-add" title="Add custom from current theme">+</button>',
      "</div>",
      '<input id="qs-rename" class="qs-rename" placeholder="Custom theme name" aria-label="Theme name" />',
      "</header>",
      '<section class="qs-preview" aria-label="Preview">',
      '<div class="qs-preview-row">',
      '<button type="button" class="qs-preview-btn">Button</button>',
      '<button type="button" class="qs-preview-btn qs-preview-btn--primary">Primary</button>',
      '<span class="qs-preview-pill">Pill</span>',
      '<span class="qs-preview-pill ok">OK</span>',
      "</div>",
      '<div class="qs-preview-row">',
      '<select class="qs-preview-dropdown" aria-label="Preview dropdown"><option>Dropdown</option><option>Widgets</option></select>',
      '<input class="qs-preview-dropdown" style="flex:1;min-width:0" value="Text input" aria-label="Preview input" />',
      "</div>",
      "</section>",
      '<div id="qs-sections"></div>',
    ].join("");
    document.body.appendChild(el);
    state.flyout = el;

    $("#qs-theme-select", el)?.addEventListener("change", (e) => {
      applyTheme(e.target.value);
    });
    $("#qs-theme-add", el)?.addEventListener("click", addCustomFromCurrent);
    $("#qs-rename", el)?.addEventListener("change", (e) => renameActive(e.target.value));
    $("#qs-rename", el)?.addEventListener("blur", (e) => {
      e.target.classList.remove("qs-rename--highlight");
      renameActive(e.target.value);
    });
    el.addEventListener("input", (e) => {
      const t = e.target;
      if (!t?.dataset?.qsSection) return;
      updateToken(t.dataset.qsSection, t.dataset.qsKey, t.value);
    });
    return el;
  }

  function renderFlyout() {
    const flyout = ensureFlyout();
    const theme = activeTheme();
    const select = $("#qs-theme-select", flyout);
    if (select) {
      select.innerHTML = allThemes()
        .map((t) => {
          const hi = t.highlight || t.id === state.highlightId ? ' class="qs-option-new"' : "";
          const tag = t.built_in ? "" : " ★";
          return `<option value="${t.id}"${hi}${t.id === state.activeId ? " selected" : ""}>${t.label}${tag}</option>`;
        })
        .join("");
    }
    const rename = $("#qs-rename", flyout);
    if (rename && theme) {
      rename.value = theme.label || "";
      rename.disabled = !!theme.built_in;
      rename.placeholder = theme.built_in ? "Built-in theme (duplicate with +)" : "Custom theme name";
    }
    const sections = $("#qs-sections", flyout);
    if (sections && theme) {
      const editable = isEditable(theme);
      sections.innerHTML = [
        `<section class="qs-section"><h3>Colors</h3>${fieldGrid(COLOR_FIELDS, "colors", theme, editable)}</section>`,
        `<section class="qs-section"><h3>Typography</h3>${fieldGrid(TYPO_FIELDS, "typography", theme, editable)}</section>`,
        `<section class="qs-section"><h3>Widgets &amp; chrome</h3>${fieldGrid(WIDGET_FIELDS, "widgets", theme, editable)}</section>`,
        editable ? "" : '<p class="qs-muted">Built-in theme — press + to fork a custom copy.</p>',
      ].join("");
    }
  }

  function toggleFlyout(force) {
    const flyout = ensureFlyout();
    const open = force != null ? force : !flyout.classList.contains("open");
    flyout.classList.toggle("open", open);
    flyout.setAttribute("aria-hidden", open ? "false" : "true");
    if (open) renderFlyout();
  }

  function bindTriggers() {
    document.getElementById("qb-styles")?.addEventListener("click", () => toggleFlyout());
    document.querySelectorAll("[data-queen-styles-open]").forEach((btn) => {
      btn.addEventListener("click", () => toggleFlyout(true));
    });
  }

  function ensureFloatButton() {
    if (document.getElementById("qb-styles") || document.querySelector("[data-queen-styles-open]")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "qs-float-btn";
    btn.setAttribute("data-queen-styles-open", "1");
    btn.title = "Styles — themes, fonts, widgets";
    btn.setAttribute("aria-label", "Styles");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3c-1.5 2.2-4 2.5-4 6.5 0 2.2 1.4 4 3.5 4.7V19h1v5h3v-5h1v-5.3c2.1-.7 3.5-2.5 3.5-4.7 0-4-2.5-4.3-4-6.5zm0 2.2c.8 1.2 1.6 1.9 1.6 3.3 0 1.5-1 2.5-1.6 2.5s-1.6-1-1.6-2.5c0-1.4.8-2.1 1.6-3.3z"/></svg>';
    document.body.appendChild(btn);
    btn.addEventListener("click", () => toggleFlyout(true));
  }

  async function loadBuiltIn() {
    try {
      const res = await fetch(THEME_JSON, { cache: "no-store" });
      if (res.ok) {
        const doc = await res.json();
        state.builtIn = doc.themes || [];
        if (doc.default && !localStorage.getItem(STORAGE_KEY)) state.activeId = doc.default;
        return;
      }
    } catch (_) {}
    state.builtIn = [
      {
        id: "black_emerald_rose_2026",
        label: "Black Emerald Rose 2026",
        built_in: true,
        tokens: { colors: { bg: "#010302", surface: "#08100c", text: "#e8f2ea", accent: "#3ecf8e" }, typography: {}, widgets: {} },
      },
    ];
  }

  async function boot() {
    if (state.ready) return;
    loadStore();
    await loadBuiltIn();
    if (!themeById(state.activeId)) state.activeId = state.builtIn[0]?.id || "black_emerald_rose_2026";
    applyTheme(state.activeId);
    bindTriggers();
    ensureFloatButton();
    state.ready = true;
  }

  window.QueenStyles = {
    sealHead,
    boot,
    applyTheme,
    toggleFlyout,
    addCustomFromCurrent,
    getActive: () => activeTheme(),
    getThemes: () => allThemes(),
  };

  sealHead();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();