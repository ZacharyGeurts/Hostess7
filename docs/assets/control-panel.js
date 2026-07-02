/**
 * Queen Settings — Themes index + display comfort scale.
 */
(function () {
  "use strict";

  let shellDoc = null;
  let themeDoc = null;
  let activeTab = "themes";
  let themeSection = "presets";

  const AT = () => window.AmmoosThemes;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  async function fetchShell() {
    const res = await fetch("/api/field-shell-settings", { credentials: "same-origin" });
    if (!res.ok) throw new Error("settings " + res.status);
    shellDoc = await res.json();
    return shellDoc;
  }

  async function fetchThemes(force) {
    if (!AT()) throw new Error("theme engine not loaded");
    themeDoc = await AT().fetchCatalog(force);
    return themeDoc;
  }

  async function saveShell(patch) {
    const res = await fetch("/api/field-shell-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    shellDoc = await res.json();
    try {
      window.parent?.postMessage({ type: "nexus:settings", settings: shellDoc.settings }, "*");
    } catch (_) {}
    return shellDoc;
  }

  async function applyThemes(patch) {
    const doc = await AT().apply(patch);
    themeDoc = doc;
    return doc;
  }

  function renderDisplay() {
    const s = shellDoc.settings || {};
    const displays = shellDoc.displays || [];
    const scale = shellDoc.desktop_scale || {};
    const displayRows = displays.length
      ? displays
          .map(function (d) {
            return (
              '<div class="cp-row"><label>' +
              esc(d.name || d.id) +
              '</label><span>' +
              esc(d.resolution || "—") +
              " · " +
              esc(d.backend || "") +
              (d.primary ? " · primary" : "") +
              "</span></div>"
            );
          })
          .join("")
      : '<p class="cp-lead">Display probe pending</p>';

    return (
      '<section class="cp-section">' +
      "<h2>Display</h2>" +
      '<p class="cp-lead">Comfort scale for the C2 shell. Colors and chrome live under <strong>Themes</strong>.</p>' +
      '<div class="cp-card">' +
      displayRows +
      "</div>" +
      '<div class="cp-card">' +
      '<div class="cp-row"><label>Comfort scale</label>' +
      '<input type="range" id="cp-ui-scale" min="' +
      (scale.min_pct || 50) +
      '" max="' +
      (scale.max_pct || 200) +
      '" value="' +
      (s.ui_scale || scale.default_pct || 125) +
      '" />' +
      '<span id="cp-ui-scale-val">' +
      (s.ui_scale || scale.default_pct || 125) +
      '%</span></div>' +
      "</div>" +
      '<div class="cp-actions">' +
      '<button type="button" class="primary" id="cp-save-display">Apply comfort scale</button>' +
      "</div></section>"
    );
  }

  function themeNav() {
    const sections = themeDoc.sections || [
      { id: "presets", label: "Presets" },
      { id: "customize", label: "Customize" },
      { id: "surfaces", label: "Surfaces" },
      { id: "file_types", label: "File types" },
    ];
    return (
      '<nav class="at-subnav" aria-label="Theme sections">' +
      sections
        .map(function (sec) {
          const on = sec.id === themeSection ? " active" : "";
          return (
            '<button type="button" class="at-subnav-btn' +
            on +
            '" data-at-section="' +
            esc(sec.id) +
            '">' +
            esc(sec.label) +
            (sec.hint ? '<span class="at-subhint">' + esc(sec.hint) + "</span>" : "") +
            "</button>"
          );
        })
        .join("") +
      "</nav>"
    );
  }

  function renderPresets() {
    const active = themeDoc.active || {};
    const c2 = themeDoc.c2_themes || {};
    const queen = themeDoc.queen_styles?.themes || [];
    const editor = themeDoc.editor?.editor_themes || {};
    const shell = themeDoc.shell_themes || {};

    const c2Opts = Object.entries(c2)
      .map(function (pair) {
        const id = pair[0];
        const t = pair[1];
        return (
          '<option value="' +
          esc(id) +
          '"' +
          (active.c2 === id ? " selected" : "") +
          ">" +
          esc(t.label || id) +
          "</option>"
        );
      })
      .join("");

    const queenOpts = queen
      .map(function (t) {
        return (
          '<option value="' +
          esc(t.id) +
          '"' +
          (active.queen_styles === t.id ? " selected" : "") +
          ">" +
          esc(t.label || t.id) +
          (t.built_in ? "" : " ★") +
          "</option>"
        );
      })
      .join("");

    const editorOpts = Object.entries(editor)
      .map(function (pair) {
        return (
          '<option value="' +
          esc(pair[0]) +
          '"' +
          (active.editor === pair[0] ? " selected" : "") +
          ">" +
          esc(pair[1].label || pair[0]) +
          "</option>"
        );
      })
      .join("");

    const shellOpts = Object.entries({ "": { label: "Auto (detect host)" }, ...shell })
      .map(function (pair) {
        return (
          '<option value="' +
          esc(pair[0]) +
          '"' +
          ((active.shell_theme || "") === pair[0] ? " selected" : "") +
          ">" +
          esc(pair[1].label || pair[0] || "Auto") +
          "</option>"
        );
      })
      .join("");

    return (
      '<div class="cp-card">' +
      '<div class="cp-row"><label>C2 desktop theme</label><select id="at-c2">' +
      c2Opts +
      "</select></div>" +
      '<div class="cp-row"><label>Queen Styles</label><select id="at-queen">' +
      queenOpts +
      "</select></div>" +
      '<div class="cp-row"><label>Queen Code editor</label><select id="at-editor">' +
      editorOpts +
      "</select></div>" +
      '<div class="cp-row"><label>Taskbar skin</label><select id="at-shell">' +
      shellOpts +
      "</select></div>" +
      '<div class="cp-row"><label>Wallpaper</label><select id="at-wallpaper">' +
      ["default", "windows", "gnome", "kde", "macos", "field-dark"]
        .map(function (w) {
          return (
            '<option value="' +
            w +
            '"' +
            ((active.wallpaper || "default") === w ? " selected" : "") +
            ">" +
            w +
            "</option>"
          );
        })
        .join("") +
      "</select></div>" +
      "</div>" +
      '<section class="at-preview" aria-label="Live preview">' +
      '<div class="at-preview-row">' +
      '<button type="button" class="at-preview-btn">Button</button>' +
      '<button type="button" class="at-preview-btn primary">Primary</button>' +
      '<span class="at-preview-pill">Pill</span>' +
      "</div>" +
      '<div class="at-preview-row">' +
      '<select class="at-preview-input" aria-label="Preview dropdown"><option>Dropdown</option></select>' +
      '<input class="at-preview-input" value="Text input" aria-label="Preview input" />' +
      "</div></section>" +
      '<div class="cp-actions"><button type="button" class="primary" id="at-apply-presets">Apply presets</button></div>'
    );
  }

  function renderCustomize() {
    const activeId = themeDoc.active?.queen_styles;
    const theme = (themeDoc.queen_styles?.themes || []).find(function (t) {
      return t.id === activeId;
    });
    if (!theme) return '<p class="cp-lead">Select a Queen Styles preset first.</p>';
    const editable = !theme.built_in;
    const ATeng = AT();
    return (
      '<div class="cp-card">' +
      '<p class="cp-lead">' +
      (editable
        ? "Editing custom theme — changes apply live."
        : "Built-in theme — duplicate from Presets (+) or pick a ★ custom theme.") +
      "</p>" +
      '<div class="cp-row"><label>Theme name</label><input type="text" id="at-rename" value="' +
      esc(theme.label || "") +
      '" ' +
      (editable ? "" : "disabled") +
      " /></div>" +
      (editable
        ? '<div class="cp-actions" style="margin-top:0"><button type="button" id="at-fork">+ Duplicate as custom</button></div>'
        : '<div class="cp-actions" style="margin-top:0"><button type="button" id="at-fork">+ Fork custom copy</button></div>') +
      "</div>" +
      '<section class="at-custom-block"><h3>Colors</h3>' +
      ATeng.fieldGrid(ATeng.COLOR_FIELDS, "colors", theme, editable) +
      "</section>" +
      '<section class="at-custom-block"><h3>Typography</h3>' +
      ATeng.fieldGrid(ATeng.TYPO_FIELDS, "typography", theme, editable) +
      "</section>" +
      '<section class="at-custom-block"><h3>Widgets</h3>' +
      ATeng.fieldGrid(ATeng.WIDGET_FIELDS, "widgets", theme, editable) +
      "</section>" +
      (editable
        ? '<div class="cp-actions"><button type="button" class="primary" id="at-save-custom">Save custom theme</button></div>'
        : "")
    );
  }

  function renderSurfaces() {
    const programs = themeDoc.programs || [];
    const opts = (themeDoc.surface_options || [])
      .map(function (o) {
        return '<option value="' + esc(o.id) + '">' + esc(o.label) + "</option>";
      })
      .join("");
    const rows = programs.length
      ? programs
          .map(function (p) {
            const surf = p.user_surface || "auto";
            return (
              '<div class="cp-row at-prog-row">' +
              '<label title="' +
              esc(p.id) +
              '">' +
              esc(p.name) +
              "</label>" +
              '<select class="at-prog-surface" data-at-pid="' +
              esc(p.id) +
              '">' +
              (themeDoc.surface_options || [])
                .map(function (o) {
                  return (
                    '<option value="' +
                    esc(o.id) +
                    '"' +
                    (surf === o.id ? " selected" : "") +
                    ">" +
                    esc(o.label) +
                    "</option>"
                  );
                })
                .join("") +
              "</select></div>"
            );
          })
          .join("")
      : '<p class="cp-lead">Program catalog pending — open Queen Browser first.</p>';
    return (
      '<p class="cp-lead">Window ↔ Browser per program. Right-click any Queen program for the same properties flyout.</p>' +
      '<div class="cp-card">' +
      rows +
      "</div>" +
      '<div class="cp-actions"><button type="button" class="primary" id="at-save-surfaces">Save launch surfaces</button></div>'
    );
  }

  function renderFileTypes() {
    const types = themeDoc.file_types || [];
    const rows = types.length
      ? types
          .map(function (ft) {
            const ext = (ft.extensions || []).join(", ") || "—";
            return (
              '<details class="at-ft-row">' +
              '<summary><span class="at-ft-label">' +
              esc(ft.label) +
              '</span><span class="at-ft-ext">' +
              esc(ext) +
              "</span></summary>" +
              '<div class="at-ft-body">' +
              '<div class="cp-row"><label>Open with</label><input type="text" class="at-ft-open" data-at-tid="' +
              esc(ft.type_id) +
              '" value="' +
              esc(ft.open_with === "inherit" ? ft.default_open_with || "" : ft.open_with) +
              '" placeholder="queen-code, view, launch…" /></div>' +
              '<div class="cp-row"><label>Launch surface</label><select class="at-ft-surface" data-at-tid="' +
              esc(ft.type_id) +
              '">' +
              (themeDoc.surface_options || [])
                .map(function (o) {
                  return (
                    '<option value="' +
                    esc(o.id) +
                    '"' +
                    ((ft.surface || "auto") === o.id ? " selected" : "") +
                    ">" +
                    esc(o.label) +
                    "</option>"
                  );
                })
                .join("") +
              "</select></div>" +
              '<div class="cp-row"><label>Context menu</label><input type="checkbox" class="at-ft-ctx" data-at-tid="' +
              esc(ft.type_id) +
              '" ' +
              (ft.show_in_context !== false ? "checked" : "") +
              " /></div>" +
              '<p class="cp-hint-block">Right-click in View/Files uses these rules for Properties → File type &amp; launch.</p>' +
              "</div></details>"
            );
          })
          .join("")
      : '<p class="cp-lead">File type registry not loaded.</p>';
    return (
      '<p class="cp-lead">Per-extension right-click window properties — open-with, surface, and context visibility.</p>' +
      '<div class="cp-card at-ft-list">' +
      rows +
      "</div>" +
      '<div class="cp-actions"><button type="button" class="primary" id="at-save-filetypes">Save file type rules</button></div>'
    );
  }

  function renderThemes() {
    const sectionRenderers = {
      presets: renderPresets,
      customize: renderCustomize,
      surfaces: renderSurfaces,
      file_types: renderFileTypes,
    };
    return (
      '<section class="cp-section cp-section--themes">' +
      "<h2>Themes</h2>" +
      '<p class="cp-lead">' +
      esc(themeDoc.motto || "Single index for every Queen surface.") +
      "</p>" +
      themeNav() +
      '<div class="at-pane">' +
      (sectionRenderers[themeSection] || renderPresets)() +
      "</div></section>"
    );
  }

  function renderSystem() {
    const sov = shellDoc.sovereignty || {};
    return (
      '<section class="cp-section">' +
      "<h2>System</h2>" +
      '<p class="cp-lead">AmmoOS posture and field services.</p>' +
      '<div class="cp-card">' +
      '<div class="cp-row"><label>Queen version</label><span>' +
      esc(shellDoc.version || "—") +
      "</span></div>" +
      '<div class="cp-row"><label>Active C2 theme</label><span>' +
      esc(themeDoc.active?.c2 || "—") +
      "</span></div>" +
      '<div class="cp-row"><label>Queen Styles</label><span>' +
      esc(themeDoc.active?.queen_styles || "—") +
      "</span></div>" +
      '<div class="cp-row"><label>ZNetwork pipe</label><span>' +
      esc(sov.znetwork?.internet_pipe_percent ?? "—") +
      "%</span></div>" +
      "</div>" +
      '<div class="cp-actions">' +
      '<button type="button" id="cp-restart">Restart field services</button>' +
      "</div></section>"
    );
  }

  function bindDisplayHandlers() {
    $("cp-ui-scale")?.addEventListener("input", function (e) {
      const v = $("cp-ui-scale-val");
      if (v) v.textContent = e.target.value + "%";
      const patch = { ui_scale: parseInt(e.target.value, 10) };
      if (window.parent?.FieldDesktopScale?.apply) {
        window.parent.FieldDesktopScale.apply(patch);
      }
      try {
        window.parent?.postMessage(
          { type: "nexus:settings", settings: { ...shellDoc.settings, ...patch } },
          "*",
        );
      } catch (_) {}
    });
    $("cp-save-display")?.addEventListener("click", async function () {
      await saveShell({ ui_scale: parseInt($("cp-ui-scale")?.value || "125", 10) });
    });
  }

  function bindThemeHandlers() {
    document.querySelectorAll("[data-at-section]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        themeSection = btn.dataset.atSection || "presets";
        paint(activeTab);
      });
    });

    $("at-apply-presets")?.addEventListener("click", async function () {
      await applyThemes({
        active_c2: $("at-c2")?.value,
        active_queen_styles: $("at-queen")?.value,
        active_editor: $("at-editor")?.value,
        shell_theme: $("at-shell")?.value || "",
        wallpaper: $("at-wallpaper")?.value || "default",
      });
    });

    $("at-fork")?.addEventListener("click", async function () {
      const activeId = themeDoc.active?.queen_styles;
      const src = (themeDoc.queen_styles?.themes || []).find(function (t) {
        return t.id === activeId;
      });
      if (!src) return;
      const custom = JSON.parse(JSON.stringify(src));
      custom.id = "custom_" + Date.now();
      custom.label = "Custom from " + (src.label || src.id);
      custom.built_in = false;
      const customs = (themeDoc.queen_styles?.themes || []).filter(function (t) {
        return !t.built_in;
      });
      customs.push(custom);
      await applyThemes({ custom_queen_styles: customs, active_queen_styles: custom.id });
      themeSection = "customize";
      await paint("themes");
    });

    const pane = document.querySelector(".at-pane");
    pane?.addEventListener("input", function (ev) {
      const t = ev.target;
      if (!t?.dataset?.atSection) return;
      const activeId = themeDoc.active?.queen_styles;
      const themes = themeDoc.queen_styles?.themes || [];
      const theme = themes.find(function (x) {
        return x.id === activeId;
      });
      if (!theme || theme.built_in) return;
      theme.tokens = theme.tokens || {};
      theme.tokens[t.dataset.atSection] = theme.tokens[t.dataset.atSection] || {};
      theme.tokens[t.dataset.atSection][t.dataset.atKey] = t.value;
      AT()?.applyQueenTokens(theme);
    });

    $("at-save-custom")?.addEventListener("click", async function () {
      const activeId = themeDoc.active?.queen_styles;
      const themes = themeDoc.queen_styles?.themes || [];
      const theme = themes.find(function (x) {
        return x.id === activeId;
      });
      if (!theme) return;
      const rename = $("at-rename")?.value;
      if (rename) theme.label = rename;
      const customs = themes.filter(function (t) {
        return !t.built_in;
      });
      await applyThemes({ custom_queen_styles: customs, active_queen_styles: activeId });
    });

    $("at-save-surfaces")?.addEventListener("click", async function () {
      const selects = document.querySelectorAll(".at-prog-surface");
      for (const sel of selects) {
        const pid = sel.dataset.atPid;
        if (!pid) continue;
        await applyThemes({ program: { id: pid, surface: sel.value } });
      }
      await fetchThemes(true);
    });

    $("at-save-filetypes")?.addEventListener("click", async function () {
      const types = document.querySelectorAll(".at-ft-open");
      for (const inp of types) {
        const tid = inp.dataset.atTid;
        if (!tid) continue;
        const surface = document.querySelector('.at-ft-surface[data-at-tid="' + tid + '"]');
        const ctx = document.querySelector('.at-ft-ctx[data-at-tid="' + tid + '"]');
        await applyThemes({
          file_type: {
            type_id: tid,
            open_with: inp.value || "inherit",
            surface: surface?.value || "auto",
            show_in_context: !!ctx?.checked,
          },
        });
      }
      await fetchThemes(true);
    });
  }

  function bindSystemHandlers() {
    $("cp-restart")?.addEventListener("click", async function () {
      if (!confirm("Restart Queen field services?")) return;
      await fetch("/api/nexus/restart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy: "log" }),
      });
    });
  }

  async function paint(tab) {
    activeTab = tab;
    const main = $("cp-main");
    if (!main) return;
    document.querySelectorAll(".cp-nav [data-cp-tab]").forEach(function (b) {
      b.classList.toggle("active", b.dataset.cpTab === tab);
    });
    if (tab === "themes") {
      main.innerHTML = renderThemes();
      bindThemeHandlers();
    } else if (tab === "display") {
      main.innerHTML = renderDisplay();
      bindDisplayHandlers();
    } else {
      main.innerHTML = renderSystem();
      bindSystemHandlers();
    }
  }

  async function init() {
    const main = $("cp-main");
    try {
      const q = new URLSearchParams(location.search);
      activeTab = q.get("tab") || "themes";
      themeSection = q.get("section") || "presets";
      await fetchShell();
      await fetchThemes();
      await paint(activeTab);
    } catch (e) {
      if (main) main.innerHTML = "<p class='cp-lead'>Failed to load: " + esc(e.message) + "</p>";
    }
    document.querySelectorAll(".cp-nav [data-cp-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        paint(btn.dataset.cpTab);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();