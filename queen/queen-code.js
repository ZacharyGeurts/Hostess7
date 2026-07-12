/**
 * Queen Code — g16-aware viewer. No telemetry. Queen browser native.
 */
(function () {
  "use strict";

  const API = "/api/queen-code";
  const FILES_API = "/api/queen-file-browser";

  const SETTINGS_KEY = "queen-code-settings-v1";
  const RECENT_KEY = "queen-code-recent-v1";

  const defaultSettings = () => ({
    fontSize: 13,
    tabSize: 4,
    wordWrap: false,
    autodetect: true,
    trackRecent: true,
    profile: "belt_2_0",
    theme: "queen_emerald",
    compiler: "belt_2_0",
  });

  const state = {
    path: "",
    language: "plaintext",
    dirty: false,
    langs: [],
    g16: {},
    roots: [],
    settings: defaultSettings(),
    recent: [],
  };

  function $(id) {
    return document.getElementById(id);
  }

  async function codeApi(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  async function filesApi(body) {
    const r = await fetch(FILES_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  function syncScroll() {
    const ed = $("qc-editor");
    const hi = $("qc-highlight");
    const gut = $("qc-gutter");
    if (!ed || !hi || !gut) return;
    hi.scrollTop = ed.scrollTop;
    hi.scrollLeft = ed.scrollLeft;
    gut.scrollTop = ed.scrollTop;
  }

  function renderGutter(text) {
    const gut = $("qc-gutter");
    if (!gut) return;
    const n = Math.max(1, (text.match(/\n/g) || []).length + (text.length && !text.endsWith("\n") ? 1 : 0));
    const lines = [];
    for (let i = 1; i <= n; i += 1) lines.push(String(i));
    gut.textContent = lines.join("\n");
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (raw) state.settings = { ...defaultSettings(), ...JSON.parse(raw) };
    } catch (_) {
      state.settings = defaultSettings();
    }
    applySettings();
  }

  function saveSettings() {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
    applySettings();
  }

  function applySettings() {
    const s = state.settings;
    const wrap = document.querySelector(".qc-editor-wrap");
    const ed = $("qc-editor");
    const hi = $("qc-highlight");
    const gut = $("qc-gutter");
    const px = `${s.fontSize}px`;
    if (wrap) wrap.classList.toggle("wrap", !!s.wordWrap);
    [ed, hi, gut].forEach((el) => {
      if (!el) return;
      el.style.fontSize = px;
      el.style.tabSize = String(s.tabSize);
    });
    $("qc-set-font") && ($("qc-set-font").value = String(s.fontSize));
    $("qc-set-tab") && ($("qc-set-tab").value = String(s.tabSize));
    $("qc-set-wrap") && ($("qc-set-wrap").checked = !!s.wordWrap);
    $("qc-set-autodetect") && ($("qc-set-autodetect").checked = !!s.autodetect);
    $("qc-set-recent") && ($("qc-set-recent").checked = !!s.trackRecent);
    $("qc-set-profile") && ($("qc-set-profile").value = s.profile || s.compiler || "belt_2_0");
    $("qc-set-theme") && ($("qc-set-theme").value = s.theme || "queen_emerald");
    $("qc-menu-compiler") && ($("qc-menu-compiler").value = s.compiler || s.profile || "belt_2_0");
    document.body.dataset.qcTheme = s.theme || "queen_emerald";
  }

  function loadRecentLocal() {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      if (raw) state.recent = JSON.parse(raw) || [];
    } catch (_) {
      state.recent = [];
    }
  }

  function saveRecentLocal() {
    localStorage.setItem(RECENT_KEY, JSON.stringify(state.recent.slice(0, 24)));
    renderRecentMenu();
  }

  function pushRecent(path, language) {
    if (!state.settings.trackRecent || !path) return;
    state.recent = [{ path, language: language || state.language, ts: Date.now() },
      ...state.recent.filter((r) => r.path !== path)].slice(0, 24);
    saveRecentLocal();
  }

  function renderRecentMenu() {
    const el = $("qc-recent-list");
    if (!el) return;
    const items = state.recent || [];
    el.innerHTML = items.length
      ? items.map((r) =>
          `<button type="button" data-recent="${encodeURIComponent(r.path)}">${r.path.split("/").pop()}</button>`,
        ).join("")
      : `<span class="qc-menu-label">No recent files</span>`;
    el.querySelectorAll("[data-recent]").forEach((btn) => {
      btn.addEventListener("click", () => openFile(decodeURIComponent(btn.dataset.recent || "")));
    });
  }

  async function autodetectLanguage(path) {
    if (!state.settings.autodetect || !path) return state.language;
    const doc = await codeApi({ action: "discern", path });
    return doc.language || doc.g16_discern || state.language;
  }

  function paint() {
    const ed = $("qc-editor");
    const hi = $("qc-highlight");
    if (!ed || !hi) return;
    const text = ed.value;
    renderGutter(text);
    hi.innerHTML = window.QueenCodeHighlight
      ? window.QueenCodeHighlight.highlight(text, state.language)
      : text.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    syncScroll();
    updateStatus();
  }

  function updateStatus() {
    const ed = $("qc-editor");
    const text = ed?.value || "";
    const lines = text.split("\n").length;
    const cols = (text.split("\n").pop() || "").length + 1;
    $("qc-st-lang").textContent = state.language;
    $("qc-st-g16").textContent = state.g16.version || "g16";
    $("qc-st-pos").textContent = `Ln ${lines}, Col ${cols}`;
    $("qc-st-path").textContent = state.path ? state.path.split("/").pop() : "untitled";
    $("qc-st-dirty").textContent = state.dirty ? "● modified" : "";
    $("qc-tab-label").textContent = state.path ? state.path.split("/").pop() : "Welcome";
  }

  function toast(msg, ok) {
    const el = $("qc-toast");
    if (!el) return;
    el.textContent = msg;
    el.style.borderColor = ok ? "#238636" : "#f85149";
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 4000);
  }

  async function loadRegistry() {
    const doc = await codeApi({ action: "languages" });
    state.langs = doc.languages || [];
    state.g16 = doc.g16 || {};
    if (window.QueenCodeHighlight?.mergeExtensions && doc.extensions) {
      window.QueenCodeHighlight.mergeExtensions(doc.extensions);
    }
    const list = $("qc-lang-list");
    if (list) {
      list.innerHTML = (state.langs || [])
        .map((l) => `<span title="g16 discern">${l}</span>`)
        .join(" · ");
    }
    $("qc-g16-pill").textContent = `g16 ${doc.g16?.version || ""} · belt ${doc.g16?.belt_profile || "2.0"}`;
    $("qc-telemetry-pill").classList.add("ok");
    $("qc-telemetry-pill").textContent = "telemetry: off";
  }

  async function loadRoots() {
    const doc = await filesApi({ action: "roots" });
    state.roots = doc.roots || [];
    const tree = $("qc-tree");
    if (!tree) return;
    tree.innerHTML = "";
    for (const r of state.roots) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `📁 ${r.label}`;
      btn.addEventListener("click", () => browseRoot(r.path));
      tree.appendChild(btn);
    }
  }

  async function browseRoot(path) {
    const doc = await filesApi({ action: "list", path });
    const tree = $("qc-tree");
    if (!tree || !doc.ok) return;
    tree.innerHTML = "";
    const back = document.createElement("button");
    back.type = "button";
    back.textContent = "← roots";
    back.addEventListener("click", loadRoots);
    tree.appendChild(back);
    for (const e of doc.entries || []) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `${e.kind === "dir" ? "📁" : "📄"} ${e.name}`;
      btn.addEventListener("click", () => {
        if (e.kind === "dir") browseRoot(e.path);
        else openFile(e.path);
      });
      tree.appendChild(btn);
    }
  }

  async function openFile(path) {
    const doc = await codeApi({ action: "read", path });
    if (!doc.ok) {
      toast(doc.error || "read failed", false);
      return;
    }
    state.path = doc.path;
    state.language = doc.language || doc.g16_discern || "plaintext";
    state.dirty = false;
    $("qc-editor").value = doc.content || "";
    if (doc.recent) state.recent = doc.recent;
    pushRecent(state.path, state.language);
    paint();
    toast(`Opened · ${state.language} · g16 discern`, true);
  }

  async function saveFile() {
    if (!state.path) {
      toast("No path — open a file from explorer", false);
      return;
    }
    const content = $("qc-editor").value;
    const doc = await codeApi({ action: "write", path: state.path, content });
    if (!doc.ok) {
      toast(doc.error || "save failed", false);
      return;
    }
    state.dirty = false;
    updateStatus();
    toast("Saved", true);
  }

  function activeProfile() {
    return state.settings.compiler || state.settings.profile || "belt_2_0";
  }

  async function g16Check() {
    if (!state.path) {
      toast("Open a file first", false);
      return;
    }
    await saveFile();
    const doc = await codeApi({ action: "g16_check", path: state.path, profile: activeProfile() });
    if (doc.ok) toast(`g16 check OK · ${doc.language}`, true);
    else toast((doc.stderr || doc.error || "g16 check failed").slice(0, 200), false);
  }

  async function g16Build() {
    if (!state.path) {
      toast("Open a source file first", false);
      return;
    }
    await saveFile();
    toast("Building…", true);
    const doc = await codeApi({ action: "g16_build", path: state.path, profile: activeProfile() });
    if (doc.ok) toast(doc.message || `Build OK · ${doc.artifact || ""}`, true);
    else toast((doc.stderr || doc.error || "build failed").slice(0, 240), false);
  }

  async function g16Launch() {
    const launchPath = state.path?.endsWith(".launch") ? state.path : state.path?.replace(/\.[^.]+$/, ".launch");
    if (!launchPath) {
      toast("Open a .launch chamber or source with matching .launch", false);
      return;
    }
    toast("Launching chamber…", true);
    const doc = await filesApi({ action: "run_launch", path: launchPath, profile: activeProfile() });
    if (doc.ok) toast(doc.message || "Launch OK", true);
    else toast((doc.error || doc.stderr || "launch failed").slice(0, 240), false);
  }

  async function runPython() {
    if (!state.path) {
      toast("Open a .py file first", false);
      return;
    }
    await saveFile();
    const doc = await codeApi({ action: "g16_run_python", path: state.path, profile: activeProfile() });
    if (doc.ok) toast(`Python OK · ${(doc.stdout || "").slice(0, 120)}`, true);
    else toast((doc.stderr || doc.error || "run failed").slice(0, 240), false);
  }

  function bindMenus() {
    $("qc-menu-save")?.addEventListener("click", saveFile);
    $("qc-menu-g16")?.addEventListener("click", g16Check);
    $("qc-menu-open-files")?.addEventListener("click", () => $("qc-open-files")?.click());
    $("qc-menu-wrap")?.addEventListener("click", () => {
      state.settings.wordWrap = !state.settings.wordWrap;
      saveSettings();
    });
    $("qc-menu-font-inc")?.addEventListener("click", () => {
      state.settings.fontSize = Math.min(22, (state.settings.fontSize || 13) + 1);
      saveSettings();
    });
    $("qc-menu-font-dec")?.addEventListener("click", () => {
      state.settings.fontSize = Math.max(11, (state.settings.fontSize || 13) - 1);
      saveSettings();
    });
    $("qc-set-font")?.addEventListener("input", (e) => {
      state.settings.fontSize = parseInt(e.target.value, 10) || 13;
      saveSettings();
    });
    $("qc-set-tab")?.addEventListener("change", (e) => {
      state.settings.tabSize = parseInt(e.target.value, 10) || 4;
      saveSettings();
    });
    $("qc-set-wrap")?.addEventListener("change", (e) => {
      state.settings.wordWrap = !!e.target.checked;
      saveSettings();
    });
    $("qc-set-autodetect")?.addEventListener("change", (e) => {
      state.settings.autodetect = !!e.target.checked;
      saveSettings();
    });
    $("qc-set-recent")?.addEventListener("change", (e) => {
      state.settings.trackRecent = !!e.target.checked;
      saveSettings();
    });
    $("qc-set-profile")?.addEventListener("change", (e) => {
      state.settings.profile = e.target.value || "belt_2_0";
      state.settings.compiler = state.settings.profile;
      saveSettings();
    });
    $("qc-set-theme")?.addEventListener("change", (e) => {
      state.settings.theme = e.target.value || "queen_emerald";
      saveSettings();
    });
    $("qc-menu-compiler")?.addEventListener("change", (e) => {
      state.settings.compiler = e.target.value || "belt_2_0";
      state.settings.profile = state.settings.compiler;
      saveSettings();
    });
    $("qc-menu-build")?.addEventListener("click", g16Build);
    $("qc-menu-launch")?.addEventListener("click", g16Launch);
    $("qc-menu-run-py")?.addEventListener("click", runPython);
    $("qc-build")?.addEventListener("click", g16Build);
    $("qc-launch")?.addEventListener("click", g16Launch);
  }

  function bindEditor() {
    const ed = $("qc-editor");
    ed?.addEventListener("input", () => {
      state.dirty = true;
      paint();
    });
    ed?.addEventListener("scroll", syncScroll);
    ed?.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveFile();
      }
    });
    $("qc-save")?.addEventListener("click", saveFile);
    $("qc-act-g16")?.addEventListener("click", g16Check);
    document.querySelector(".qc-toolbar #qc-g16")?.addEventListener("click", g16Check);
    $("qc-open-files")?.addEventListener("click", () => {
      const url = `${location.origin}/world/queen-files.html`;
      try {
        if (parent?.QueenOS?.browser?.navigate) parent.QueenOS.browser.navigate(url);
        else location.href = url;
      } catch (_) {
        location.href = url;
      }
    });
    $("qc-open-browser")?.addEventListener("click", () => {
      const url = `${location.origin}/world/browser.html`;
      try {
        if (parent?.QueenOS?.browser?.navigate) parent.QueenOS.browser.navigate(url);
        else location.href = url;
      } catch (_) {
        location.href = url;
      }
    });
  }

  function welcomeText() {
    return [
      "// Queen Code — rewritten viewer for g16",
      "// No telemetry · loopback only · VSCodium-inspired layout",
      "//",
      "// Open a file from the explorer or Queen Files.",
      "// Languages: " + (state.langs || []).slice(0, 8).join(", ") + "…",
      "",
      "/* g16 discern drives syntax + compile check */",
    ].join("\n");
  }

  async function init() {
    loadSettings();
    loadRecentLocal();
    bindMenus();
    bindEditor();
    await loadRegistry();
    const recentDoc = await codeApi({ action: "recent" });
    if (recentDoc.files?.length) state.recent = recentDoc.files;
    renderRecentMenu();
    await loadRoots();
    const params = new URLSearchParams(location.search);
    const path = params.get("path");
    if (path) await openFile(path);
    else {
      $("qc-editor").value = welcomeText();
      state.language = "cxx";
      paint();
    }
  }

  init();
})();