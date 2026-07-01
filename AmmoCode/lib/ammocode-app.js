/**
 * AmmoCode — NEXUS C2 shell · themeable syntax · G16 · secure settings
 */
(function () {
  "use strict";

  const API = "/api/ammocode";
  const LOCAL_KEY = "ammocode-stack-v6";

  const state = {
    path: "",
    language: "plaintext",
    profile: "belt_2_0",
    dirty: false,
    filetypes: null,
    editorThemes: {},
    syntaxThemes: {},
    settings: {
      fontSize: 13,
      tabSize: 4,
      wordWrap: false,
      autodetect: true,
      profile: "belt_2_0",
      theme: "nexus_c2",
      syntaxTheme: "nexus_c2",
      toolbarEnabled: {},
      iconSize: 24,
    },
    nondestructive: true,
    editorThemeKeys: [],
    syntaxThemeKeys: [],
  };

  const $ = (id) => document.getElementById(id);

  async function api(action, payload) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, profile: state.profile, ...payload }),
    });
    return r.json();
  }

  function setOutput(text, ok) {
    const el = $("ac-output");
    if (!el) return;
    el.textContent = text || "";
    el.className = "ac-output" + (ok === true ? " ok" : ok === false ? " err" : "");
  }

  function setStatus(msg) {
    const el = $("ac-status-msg");
    if (el) el.textContent = msg || "";
  }

  function editorText() {
    return $("ac-editor")?.value || "";
  }

  function paint() {
    const text = editorText();
    const hi = $("ac-highlight");
    const gut = $("ac-gutter");
    if (hi && global.AmmoCodeHighlight) {
      hi.innerHTML = global.AmmoCodeHighlight.highlight(text, state.language);
    }
    if (gut && global.AmmoCodeHighlight) {
      gut.textContent = global.AmmoCodeHighlight.gutterLines(text);
    }
    syncScroll();
  }

  function syncScroll() {
    const ed = $("ac-editor");
    const hi = $("ac-highlight");
    const gut = $("ac-gutter");
    if (!ed) return;
    if (hi) {
      hi.scrollTop = ed.scrollTop;
      hi.scrollLeft = ed.scrollLeft;
    }
    if (gut) gut.scrollTop = ed.scrollTop;
  }

  function applyEditorTheme(id) {
    const doc = document.documentElement;
    doc.classList.remove("ac-theme-nexus-c2", "ac-theme-queen-emerald", "ac-theme-one-dark", "ac-theme-dracula");
    const th = state.editorThemes[id];
    if (th?.css_class) doc.classList.add(th.css_class);
    if (th?.vars) {
      for (const [k, v] of Object.entries(th.vars)) doc.style.setProperty(k, v);
    }
    state.settings.theme = id;
  }

  function applySyntaxTheme(id) {
    const th = state.syntaxThemes[id];
    const doc = document.documentElement;
    if (!th?.tokens) return;
    for (const [tok, color] of Object.entries(th.tokens)) {
      doc.style.setProperty(`--ac-syn-${tok}`, color);
    }
    state.settings.syntaxTheme = id;
  }

  function applySettings() {
    const s = state.settings;
    state.profile = s.profile || state.profile;
    const wrap = document.querySelector(".ac-editor-wrap");
    if (wrap) wrap.classList.toggle("wrap", !!s.wordWrap);
    const px = `${s.fontSize}px`;
    document.documentElement.style.setProperty("--ac-editor-font", px);
    const ed = $("ac-editor");
    if (ed) {
      ed.style.tabSize = String(s.tabSize || 4);
      ed.wrap = s.wordWrap ? "soft" : "off";
    }
    global.AmmoCodeToolbar?.setActive("word_wrap", !!s.wordWrap);
    applyEditorTheme(s.theme || "nexus_c2");
    applySyntaxTheme(s.syntaxTheme || "nexus_c2");
    document.documentElement.style.setProperty("--ac-icon-size", `${s.iconSize || 24}px`);
    $("ac-lang").textContent = state.language;
    $("ac-profile-label").textContent = state.profile;
    paint();
  }

  async function persistSettings(patch) {
    Object.assign(state.settings, patch || {});
    try {
      if (global.AmmoCodeSettings?.save) {
        await global.AmmoCodeSettings.save(patch || state.settings);
      }
    } catch (_) {}
    try {
      localStorage.setItem(LOCAL_KEY, JSON.stringify(state.settings));
    } catch (_) {}
    applySettings();
    if (patch?.toolbarEnabled || patch?.iconSize != null) {
      global.AmmoCodeToolbar?.init({
        doctrine: global.AmmoCodeToolbar.state().doctrine,
        toolbarEnabled: state.settings.toolbarEnabled,
        iconSize: state.settings.iconSize,
        onAction: onToolbarAction,
      });
    }
  }

  async function loadThemes() {
    try {
      const r = await fetch("/api/syntax-themes", { cache: "no-store" });
      if (!r.ok) return;
      const j = await r.json();
      state.editorThemes = j.editor_themes || {};
      state.syntaxThemes = j.syntax_themes || {};
      state.editorThemeKeys = Object.keys(state.editorThemes);
      state.syntaxThemeKeys = Object.keys(state.syntaxThemes);
      const edSel = $("ac-set-editor-theme");
      const synSel = $("ac-set-syntax-theme");
      if (edSel) {
        edSel.innerHTML = "";
        for (const [k, v] of Object.entries(state.editorThemes)) {
          const o = document.createElement("option");
          o.value = k;
          o.textContent = v.label || k;
          edSel.appendChild(o);
        }
      }
      if (synSel) {
        synSel.innerHTML = "";
        for (const [k, v] of Object.entries(state.syntaxThemes)) {
          const o = document.createElement("option");
          o.value = k;
          o.textContent = v.label || k;
          synSel.appendChild(o);
        }
      }
    } catch (_) {}
  }

  async function loadSettings() {
    let merged = { ...state.settings };
    try {
      const raw = localStorage.getItem(LOCAL_KEY);
      if (raw) merged = { ...merged, ...JSON.parse(raw) };
    } catch (_) {}
    try {
      if (global.AmmoCodeSettings?.load) {
        const j = await global.AmmoCodeSettings.load({ importLegacy: true });
        if (j.ok && j.settings) {
          merged = { ...merged, ...global.AmmoCodeSettings.editorFrom(j) };
          if (j.settings.syntaxTheme) merged.syntaxTheme = j.settings.syntaxTheme;
          if (j.settings.toolbarEnabled) merged.toolbarEnabled = j.settings.toolbarEnabled;
          if (j.settings.iconSize) merged.iconSize = j.settings.iconSize;
        }
      }
    } catch (_) {}
    if (merged.theme === "ammo_emerald") merged.theme = "nexus_c2";
    state.settings = merged;
    state.profile = merged.profile || "belt_2_0";
    applySettings();
    $("ac-set-font")?.setAttribute("value", String(merged.fontSize));
    $("ac-set-tab")?.setAttribute("value", String(merged.tabSize));
    if ($("ac-set-wrap")) $("ac-set-wrap").checked = !!merged.wordWrap;
    if ($("ac-set-autodetect")) $("ac-set-autodetect").checked = merged.autodetect !== false;
    if ($("ac-set-profile")) $("ac-set-profile").value = merged.profile;
    if ($("ac-set-editor-theme")) $("ac-set-editor-theme").value = merged.theme;
    if ($("ac-set-syntax-theme")) $("ac-set-syntax-theme").value = merged.syntaxTheme;
    if ($("ac-set-icon-size")) $("ac-set-icon-size").value = String(merged.iconSize);
  }

  async function loadFiletypes() {
    try {
      const r = await fetch("/api/filetypes");
      if (r.ok) {
        state.filetypes = await r.json();
        if (global.AmmoCodeHighlight?.mergeExtensions && state.filetypes.extensions) {
          global.AmmoCodeHighlight.mergeExtensions(state.filetypes.extensions);
        }
        $("ac-ext-count").textContent = `${Object.keys(state.filetypes.extensions || {}).length} extensions`;
      }
    } catch (_) {}
  }

  function langFromPath(path) {
    if (!path) return "plaintext";
    if (global.AmmoCodeHighlight?.langFromPath) return global.AmmoCodeHighlight.langFromPath(path);
    const ext = path.slice(path.lastIndexOf(".")).toLowerCase();
    return (state.filetypes?.extensions || {})[ext] || "plaintext";
  }

  async function discern() {
    if (!state.settings.autodetect) return;
    const j = await api("discern", { path: state.path, content: editorText() });
    if (j.ok && j.language) {
      state.language = j.language;
      $("ac-lang").textContent = j.language;
      paint();
    }
  }

  function isLikelyBinary(bytes) {
    if (!bytes.length) return false;
    const sample = bytes.slice(0, Math.min(bytes.length, 8192));
    for (let i = 0; i < sample.length; i++) {
      if (sample[i] === 0) return true;
    }
    if (sample.length < 32) return false;
    let textish = 0;
    for (let i = 0; i < sample.length; i++) {
      const b = sample[i];
      if (b === 9 || b === 10 || b === 13 || (b >= 32 && b < 127) || b >= 128) textish++;
    }
    return textish / sample.length < 0.82;
  }

  function decodeBrowserFile(buffer, name) {
    const bytes = new Uint8Array(buffer);
    const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")).toLowerCase() : "";
    const forceText = !!(state.filetypes?.extensions || {})[ext] || [".nfo", ".ans", ".diz", ".asc"].includes(ext);
    if (isLikelyBinary(bytes) && !forceText) {
      return { error: "binary_file", text: "", encoding: "" };
    }
    const encodings = [
      ["utf-8", "utf-8"],
      ["utf-16le", "utf-16-le"],
      ["iso-8859-1", "latin-1"],
    ];
    for (const [enc, label] of encodings) {
      try {
        const dec = new TextDecoder(enc, { fatal: enc === "utf-8" });
        const text = dec.decode(bytes);
        if (enc === "utf-8" || !text.includes("\uFFFD")) {
          return { text, encoding: label };
        }
      } catch (_) {}
    }
    return { text: new TextDecoder("utf-8").decode(bytes), encoding: "utf-8-replace" };
  }

  async function openPath(path) {
    if (!path) return;
    const j = await api("read_file", { path });
    if (!j.ok) {
      const msg = j.error === "binary_file"
        ? "Binary file — AmmoCode opens text-era sources only"
        : (j.error || "read failed");
      setOutput(msg, false);
      return;
    }
    state.path = j.path;
    state.language = j.language || langFromPath(j.path);
    $("ac-editor").value = j.content || "";
    $("ac-path").textContent = j.path;
    $("ac-lang").textContent = state.language;
    state.dirty = false;
    paint();
    const meta = [j.encoding, j.era].filter(Boolean).join(" · ");
    setOutput(`loaded ${j.path} (${j.size} bytes${meta ? ` · ${meta}` : ""})`, true);
    setStatus(meta ? `ready · ${meta}` : "ready");
  }

  function exportDownload() {
    const text = editorText();
    const name = state.path ? state.path.split("/").pop() : "untitled.txt";
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
    state.dirty = false;
    setOutput(`exported ${name} — browser download only (non-destructive)`, true);
    setStatus("exported · disk unchanged");
  }

  async function g16Check() {
    setOutput("checking…");
    const j = await api("g16_check", {
      content: editorText(),
      path: state.path,
      language: state.language,
    });
    setOutput(j.detail || j.stderr || JSON.stringify(j, null, 2), !!j.ok);
  }

  async function g16Build() {
    setOutput("building…");
    const j = await api("g16_build", {
      content: editorText(),
      path: state.path || "untitled",
      language: state.language,
    });
    if (global.AmmoCodeCompileAlerts?.showBuildResult) {
      global.AmmoCodeCompileAlerts.showBuildResult(j, {
        outputEl: $("ac-output"),
        alertsEl: $("ac-compile-alerts"),
        editor: $("ac-editor"),
        onStatus: (msg, ok) => setStatus(msg, ok),
      });
      if (j?.content_changed) state.dirty = true;
      setStatus(j?.alerts?.summary || (j.ok ? "build ok" : "build failed"), !!j.ok);
      return;
    }
    const out = [j.stderr, j.detail, j.message, j.stdout].filter(Boolean).join("\n");
    setOutput(out || JSON.stringify(j, null, 2), !!j.ok);
  }

  async function g16Run() {
    setOutput("running…");
    let j;
    if (state.path) {
      j = await api("g16_run", { path: state.path, language: state.language });
    } else {
      j = await api("g16_build", {
        content: editorText(),
        language: state.language,
        path: "untitled",
      });
    }
    const out = [j.stdout, j.stderr, j.message, j.compile?.stderr].filter(Boolean).join("\n");
    setOutput(out || JSON.stringify(j, null, 2), !!j.ok);
  }

  function toggleDrawer(open) {
    const d = $("ac-drawer");
    const b = $("ac-drawer-backdrop");
    const on = open ?? !d?.classList.contains("open");
    d?.classList.toggle("open", on);
    b?.classList.toggle("open", on);
  }

  function toggleProfilePopover(open) {
    const p = $("ac-profile-popover");
    if (!p) return;
    const on = open ?? !p.classList.contains("open");
    p.classList.toggle("open", on);
  }

  function cycleTheme(which) {
    const keys = which === "syntax" ? state.syntaxThemeKeys : state.editorThemeKeys;
    if (!keys.length) return;
    const cur = which === "syntax" ? state.settings.syntaxTheme : state.settings.theme;
    const idx = keys.indexOf(cur);
    const next = keys[(idx + 1) % keys.length];
    if (which === "syntax") {
      applySyntaxTheme(next);
      persistSettings({ syntaxTheme: next });
      if ($("ac-set-syntax-theme")) $("ac-set-syntax-theme").value = next;
    } else {
      applyEditorTheme(next);
      persistSettings({ theme: next });
      if ($("ac-set-editor-theme")) $("ac-set-editor-theme").value = next;
    }
    paint();
    setStatus(`${which} theme: ${next}`);
  }

  function commentLine() {
    const ed = $("ac-editor");
    if (!ed) return;
    const sym = ["python", "shell", "yaml", "toml", "ruby", "perl"].includes(state.language) ? "#" : "//";
    const start = ed.selectionStart;
    const end = ed.selectionEnd;
    const val = ed.value;
    const lineStart = val.lastIndexOf("\n", start - 1) + 1;
    const lineEnd = val.indexOf("\n", end);
    const slice = val.slice(lineStart, lineEnd === -1 ? val.length : lineEnd);
    const uncomment = slice.split("\n").every((ln) => ln.trimStart().startsWith(sym));
    const lines = slice.split("\n").map((ln) => {
      const t = ln.trimStart();
      const pad = ln.slice(0, ln.length - t.length);
      if (uncomment && t.startsWith(sym)) return pad + t.slice(sym.length).trimStart();
      return pad + sym + " " + t;
    });
    ed.value = val.slice(0, lineStart) + lines.join("\n") + val.slice(lineEnd === -1 ? val.length : lineEnd);
    ed.focus();
    state.dirty = true;
    paint();
  }

  function findReplace(mode) {
    if (mode === "replace") {
      const q = prompt("Find:");
      if (q == null) return;
      const r = prompt("Replace with:");
      if (r == null) return;
      const ed = $("ac-editor");
      ed.value = ed.value.split(q).join(r);
      state.dirty = true;
      paint();
      return;
    }
    const q = prompt("Find:");
    if (!q) return;
    const ed = $("ac-editor");
    const idx = ed.value.indexOf(q, ed.selectionEnd);
    if (idx >= 0) {
      ed.focus();
      ed.setSelectionRange(idx, idx + q.length);
      setStatus(`found at ${idx}`);
    } else {
      setStatus("not found");
    }
  }

  function gotoLine() {
    const n = prompt("Go to line:");
    if (!n) return;
    const line = parseInt(n, 10);
    if (!line || line < 1) return;
    const ed = $("ac-editor");
    const lines = ed.value.split("\n");
    let pos = 0;
    for (let i = 0; i < line - 1 && i < lines.length; i++) pos += lines[i].length + 1;
    ed.focus();
    ed.setSelectionRange(pos, pos);
    const lh = parseFloat(getComputedStyle(ed).lineHeight) || 20;
    ed.scrollTop = (line - 1) * lh;
    syncScroll();
  }

  async function onToolbarAction(id, meta) {
    if (id === "toolbar_toggle") {
      const map = { ...state.settings.toolbarEnabled, [meta.id]: meta.enabled };
      await persistSettings({ toolbarEnabled: map });
      return;
    }

    const ed = $("ac-editor");

    switch (id) {
      case "new":
        ed.value = "";
        state.path = "";
        state.language = "plaintext";
        state.dirty = false;
        $("ac-path").textContent = "untitled";
        $("ac-lang").textContent = "plaintext";
        paint();
        setOutput("new buffer", true);
        break;
      case "open":
        $("ac-file")?.click();
        break;
      case "save":
      case "export":
        exportDownload();
        break;

      case "undo":
        document.execCommand("undo");
        paint();
        break;
      case "redo":
        document.execCommand("redo");
        paint();
        break;
      case "cut":
        document.execCommand("cut");
        break;
      case "copy":
        document.execCommand("copy");
        break;
      case "paste":
        document.execCommand("paste");
        paint();
        break;
      case "find":
        findReplace("find");
        break;
      case "replace":
        findReplace("replace");
        break;
      case "comment":
        commentLine();
        break;

      case "goto_line":
        gotoLine();
        break;
      case "g16_check":
        await g16Check();
        break;
      case "g16_build":
        await g16Build();
        break;
      case "g16_run":
        await g16Run();
        break;
      case "g16_profile":
        toggleProfilePopover();
        break;

      case "discern_lang":
        await discern();
        setStatus(`language: ${state.language}`);
        break;
      case "ironclad_verify":
        setOutput(
          "Ironclad verify — non-destructive · loopback-only · path-jail · no disk write API · no telemetry",
          true,
        );
        break;
      case "path_jail":
        setOutput(
          "Path jail: reads → home, SG, AmmoOS, /tmp · writes → Export only · run blocked inside AmmoCode tree",
          true,
        );
        break;
      case "word_wrap":
        await persistSettings({ wordWrap: !state.settings.wordWrap });
        break;
      case "font_dec":
        await persistSettings({ fontSize: Math.max(10, state.settings.fontSize - 1) });
        if ($("ac-set-font")) $("ac-set-font").value = state.settings.fontSize;
        break;
      case "font_inc":
        await persistSettings({ fontSize: Math.min(28, state.settings.fontSize + 1) });
        if ($("ac-set-font")) $("ac-set-font").value = state.settings.fontSize;
        break;

      case "fullscreen":
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
        else document.exitFullscreen?.();
        break;
      case "theme":
        cycleTheme("editor");
        break;
      case "syntax_theme":
        cycleTheme("syntax");
        break;
      case "settings":
        toggleDrawer(true);
        break;
      case "problems":
        await g16Check();
        break;
      default:
        setOutput(`action: ${id}`, true);
    }
  }

  function bindDrawer() {
    $("ac-drawer-close")?.addEventListener("click", () => toggleDrawer(false));
    $("ac-drawer-backdrop")?.addEventListener("click", () => toggleDrawer(false));
    $("ac-set-font")?.addEventListener("input", (e) => persistSettings({ fontSize: parseInt(e.target.value, 10) }));
    $("ac-set-tab")?.addEventListener("change", (e) => persistSettings({ tabSize: parseInt(e.target.value, 10) }));
    $("ac-set-wrap")?.addEventListener("change", (e) => persistSettings({ wordWrap: e.target.checked }));
    $("ac-set-autodetect")?.addEventListener("change", (e) => persistSettings({ autodetect: e.target.checked }));
    $("ac-set-profile")?.addEventListener("change", (e) => {
      state.profile = e.target.value;
      persistSettings({ profile: e.target.value });
      $("ac-profile-label").textContent = e.target.value;
      $("ac-popover-profile").value = e.target.value;
    });
    $("ac-set-editor-theme")?.addEventListener("change", (e) => persistSettings({ theme: e.target.value }));
    $("ac-set-syntax-theme")?.addEventListener("change", (e) => persistSettings({ syntaxTheme: e.target.value }));
    $("ac-set-icon-size")?.addEventListener("change", (e) => persistSettings({ iconSize: parseInt(e.target.value, 10) }));
    $("ac-output-clear")?.addEventListener("click", () => setOutput(""));
    $("ac-popover-profile")?.addEventListener("change", (e) => {
      state.profile = e.target.value;
      persistSettings({ profile: e.target.value });
      $("ac-profile-label").textContent = e.target.value;
      if ($("ac-set-profile")) $("ac-set-profile").value = e.target.value;
      toggleProfilePopover(false);
    });
  }

  function bindEditor() {
    const ed = $("ac-editor");
    ed?.addEventListener("input", () => {
      state.dirty = true;
      paint();
      if (state.settings.autodetect) discern();
    });
    ed?.addEventListener("scroll", syncScroll);
    ed?.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const ts = state.settings.tabSize || 4;
        const sp = " ".repeat(ts);
        const s = ed.selectionStart;
        ed.value = ed.value.slice(0, s) + sp + ed.value.slice(ed.selectionEnd);
        ed.selectionStart = ed.selectionEnd = s + sp.length;
        paint();
      }
      if (e.ctrlKey || e.metaKey) {
        if (e.key === "s") { e.preventDefault(); exportDownload(); }
        if (e.key === ",") { e.preventDefault(); toggleDrawer(true); }
        if (e.key === "f") { e.preventDefault(); findReplace("find"); }
      }
      if (e.key === "F5") { e.preventDefault(); g16Check(); }
      if (e.key === "F6") { e.preventDefault(); g16Build(); }
      if (e.key === "F7") { e.preventDefault(); g16Run(); }
    });
    $("ac-file")?.addEventListener("change", (e) => {
      const f = e.target.files?.[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        const decoded = decodeBrowserFile(reader.result, f.name);
        if (decoded.error === "binary_file") {
          setOutput("Binary file — AmmoCode opens text-era sources only", false);
          return;
        }
        const { text, encoding } = decoded;
        state.path = f.name;
        ed.value = text;
        state.language = langFromPath(f.name);
        $("ac-path").textContent = f.name;
        $("ac-lang").textContent = state.language;
        state.dirty = true;
        paint();
        discern();
        setOutput(`opened ${f.name} (${f.size} bytes · ${encoding})`, true);
      };
      reader.readAsArrayBuffer(f);
    });
  }

  async function boot() {
    document.documentElement.classList.add("ac-nexus-c2", "ac-theme-nexus-c2");
    global.AmmoCodeG16?.config?.({ apiBase: API, beltProfile: "belt_2_0" });
    bindDrawer();
    bindEditor();
    await loadThemes();
    await loadSettings();
    await loadFiletypes();
    const doctrine = await global.AmmoCodeToolbar?.loadDoctrine?.();
    global.AmmoCodeToolbar?.init?.({
      doctrine,
      toolbarEnabled: state.settings.toolbarEnabled,
      iconSize: state.settings.iconSize,
      onAction: onToolbarAction,
    });
    const ping = await api("ping", {});
    const g16El = $("ac-g16-pill");
    if (g16El) {
      g16El.textContent = ping.grok16 ? "g16 ready" : "g16 offline";
      g16El.className = "ac-pill " + (ping.grok16 ? "ok" : "warn");
    }
    $("ac-version").textContent = `v${ping.version || "6.1.0"}`;
    state.nondestructive = ping.nondestructive !== false;
    const ndPill = $("ac-nondestructive-pill");
    if (ndPill) {
      ndPill.textContent = state.nondestructive
        ? "non-destructive · export to save"
        : "destructive mode";
      ndPill.className = state.nondestructive ? "" : "warn";
    }
    if (ping.extensions) $("ac-ext-count").textContent = `${ping.extensions} extensions`;
    const params = new URLSearchParams(location.search);
    const file = params.get("file");
    if (file) await openPath(file);
    else paint();
    const saveHint = ping.save_model === "browser_export_only" ? " · export to save" : "";
    setStatus(`ready${saveHint} · loopback only`);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();