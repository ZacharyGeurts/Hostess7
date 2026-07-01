(function () {
  "use strict";

  const API = "/api/ammocode";
  const state = { path: "", language: "plaintext", profile: "belt_2_0", filetypes: null };

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
    el.className = "ac-out" + (ok === true ? " ok" : ok === false ? " err" : "");
  }

  function syncGutter() {
    const ed = $("ac-editor");
    const gut = $("ac-gutter");
    if (!ed || !gut) return;
    const lines = (ed.value.match(/\n/g) || []).length + 1;
    gut.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
    gut.scrollTop = ed.scrollTop;
  }

  async function loadFiletypes() {
    try {
      const r = await fetch("/api/filetypes");
      if (r.ok) state.filetypes = await r.json();
    } catch (_) {}
  }

  function langFromPath(path) {
    if (!path || !state.filetypes) return "plaintext";
    const ext = path.slice(path.lastIndexOf(".")).toLowerCase();
    return (state.filetypes.extensions || {})[ext] || "plaintext";
  }

  async function discern() {
    const content = $("ac-editor")?.value || "";
    const j = await api("discern", { path: state.path, content });
    if (j.ok && j.language) {
      state.language = j.language;
      $("ac-lang").textContent = j.language;
    }
  }

  async function openPath(path) {
    if (!path) return;
    const j = await api("read_file", { path });
    if (!j.ok) {
      setOutput(j.error || "read failed", false);
      return;
    }
    state.path = j.path;
    state.language = j.language || langFromPath(j.path);
    $("ac-editor").value = j.content || "";
    $("ac-path").textContent = j.path;
    $("ac-lang").textContent = state.language;
    syncGutter();
    setOutput(`loaded ${j.path} (${j.size} bytes)`, true);
  }

  async function runG16() {
    setOutput("running…");
    const content = $("ac-editor")?.value || "";
    let j;
    if (state.path) {
      j = await api("g16_run", { path: state.path, language: state.language });
    } else {
      j = await api("g16_build", { content, language: state.language, path: "untitled" });
    }
    const out = [j.stdout, j.stderr, j.message, j.compile?.stderr, j.compile?.detail]
      .filter(Boolean).join("\n");
    setOutput(out || JSON.stringify(j, null, 2), !!j.ok);
  }

  async function compileG16() {
    setOutput("compiling…");
    const content = $("ac-editor")?.value || "";
    const j = await api("g16_build", {
      content,
      path: state.path || "untitled",
      language: state.language,
    });
    const out = [j.stderr, j.detail, j.message, JSON.stringify(j.compile || {}, null, 2)]
      .filter(Boolean).join("\n");
    setOutput(out || JSON.stringify(j, null, 2), !!j.ok);
  }

  async function checkG16() {
    const j = await api("g16_check", {
      content: $("ac-editor")?.value || "",
      path: state.path,
      language: state.language,
    });
    setOutput(j.detail || JSON.stringify(j, null, 2), !!j.ok);
  }

  function bind() {
    $("ac-open")?.addEventListener("click", () => $("ac-file")?.click());
    $("ac-file")?.addEventListener("change", (e) => {
      const f = e.target.files?.[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        state.path = f.name;
        $("ac-editor").value = reader.result || "";
        $("ac-path").textContent = f.name;
        discern();
        syncGutter();
      };
      reader.readAsText(f);
    });
    $("ac-run")?.addEventListener("click", runG16);
    $("ac-compile")?.addEventListener("click", compileG16);
    $("ac-check")?.addEventListener("click", checkG16);
    $("ac-profile")?.addEventListener("change", (e) => {
      state.profile = e.target.value;
    });
    $("ac-editor")?.addEventListener("input", () => { syncGutter(); });
    $("ac-editor")?.addEventListener("scroll", syncGutter);
  }

  async function boot() {
    bind();
    await loadFiletypes();
    const ping = await api("ping", {});
    $("ac-g16").textContent = ping.grok16 ? "g16 ready" : "g16 missing";
    $("ac-ext-count").textContent = `${ping.extensions || 0} extensions`;
    const params = new URLSearchParams(location.search);
    const file = params.get("file");
    if (file) await openPath(file);
    else syncGutter();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();