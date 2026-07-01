/**
 * AmmoCode editor — language dropdown drives syntax + g16 profile. Embeddable anywhere.
 */
(function (global) {
  "use strict";

  const SETTINGS_KEY = "ammocode-settings-v1";

  const defaultSettings = () => ({
    fontSize: 13,
    tabSize: 4,
    wordWrap: false,
    autodetect: true,
    profile: "belt_2_0",
    theme: "ammo_emerald",
    tabAging: true,
  });

  const state = {
    path: "",
    language: "cxx",
    dirty: false,
    isPrimer: false,
    primerLang: "",
    langs: [],
    profiles: {},
    extensions: {},
    settings: defaultSettings(),
    securityFindings: [],
    securityBlocked: false,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function syncScroll() {
    const ed = $("ac-editor");
    const hi = $("ac-highlight");
    const gut = $("ac-gutter");
    if (!ed || !hi || !gut) return;
    hi.scrollTop = ed.scrollTop;
    hi.scrollLeft = ed.scrollLeft;
    gut.scrollTop = ed.scrollTop;
  }

  function renderGutter(text) {
    const gut = $("ac-gutter");
    if (!gut) return;
    if (global.AmmoCodeSecurity?.renderGutterSecurity && state.securityFindings?.length) {
      global.AmmoCodeSecurity.renderGutterSecurity(gut, text, state.securityFindings);
      return;
    }
    const n = Math.max(1, (text.match(/\n/g) || []).length + (text.length && !text.endsWith("\n") ? 1 : 0));
    gut.textContent = Array.from({ length: n }, (_, i) => String(i + 1)).join("\n");
  }

  async function runSecurityScan() {
    if (state.isPrimer) {
      state.securityFindings = [];
      state.securityBlocked = false;
      const pill = $("ac-sec-pill");
      if (pill) { pill.textContent = "primer"; pill.className = "pill"; }
      paint();
      return { ok: true, findings: [], blocked: false, finding_count: 0, primer: true };
    }
    const text = $("ac-editor")?.value || "";
    await global.AmmoCodeSecurity?.loadRegistry?.();
    const res = await global.AmmoCodeSecurity?.scan?.(text, state.language);
    state.securityFindings = res?.findings || [];
    state.securityBlocked = !!res?.blocked;
    const pill = $("ac-sec-pill");
    const status = $("ac-sec-status");
    if (pill) {
      pill.textContent = state.securityBlocked ? "⛔ blocked" : state.securityFindings.length ? "warn" : "secured";
      pill.className = "pill " + (state.securityBlocked ? "bad" : state.securityFindings.length ? "warn" : "ok");
    }
    if (status) {
      status.textContent = state.securityBlocked
        ? `${state.securityFindings.length} bad — hover ⛔ for use_instead`
        : state.securityFindings.length
          ? `${state.securityFindings.length} suggestion(s)`
          : "Transparent · hardened · combinatorics-aware";
    }
    const sum = $("ac-sec-summary");
    if (sum) {
      sum.textContent = state.securityBlocked
        ? `Blocked: ${state.securityFindings.length} finding(s)`
        : state.securityFindings.length
          ? `${state.securityFindings.length} finding(s) — hardened pass`
          : "Clean — hardened rewrite ready";
    }
    paint();
    return res;
  }

  function applySettings() {
    const s = state.settings;
    const wrap = document.querySelector(".ac-editor-wrap");
    const px = `${s.fontSize}px`;
    if (wrap) wrap.classList.toggle("wrap", !!s.wordWrap);
    ["ac-editor", "ac-highlight", "ac-gutter"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.style.fontSize = px;
      el.style.tabSize = String(s.tabSize);
    });
    document.body.dataset.acTheme = s.theme;
    $("ac-profile") && ($("ac-profile").value = s.profile);
    $("ac-theme") && ($("ac-theme").value = s.theme);
    global.AmmoCodeG16?.config?.({ beltProfile: s.profile });
    $("ac-g16-pill").textContent = `g16 · ${s.profile}`;
    const sp = $("ac-set-profile");
    const st = $("ac-set-theme");
    if (sp) sp.value = s.profile;
    if (st) st.value = s.theme;
  }

  async function loadSettings() {
    try {
      if (global.AmmoCodeSettings?.load) {
        const j = await global.AmmoCodeSettings.load();
        if (j.ok) {
          state.settings = global.AmmoCodeSettings.editorFrom(j);
          applySettings();
          return;
        }
      }
    } catch (_) {}
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (raw) state.settings = { ...defaultSettings(), ...JSON.parse(raw) };
    } catch (_) {
      state.settings = defaultSettings();
    }
    applySettings();
  }

  async function saveSettings() {
    applySettings();
    const patch = {
      fontSize: state.settings.fontSize,
      tabSize: state.settings.tabSize,
      wordWrap: state.settings.wordWrap,
      autodetect: state.settings.autodetect,
      profile: state.settings.profile,
      theme: state.settings.theme,
      tabAging: state.settings.tabAging,
    };
    try {
      if (global.AmmoCodeSettings?.save) {
        await global.AmmoCodeSettings.save(patch);
        return;
      }
    } catch (_) {}
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
    } catch (_) {}
  }

  function shouldApplyPrimer() {
    if (state.path) return false;
    const ed = $("ac-editor");
    const text = ed?.value || "";
    if (!text.trim()) return true;
    if (state.isPrimer) return true;
    if (global.AmmoCodePrimer?.isPrimerContent?.(text)) return true;
    return !state.dirty;
  }

  async function applyPrimer(lang, opts) {
    const next = lang || state.language || "cxx";
    const profile = opts?.profile
      || state.profiles[next]
      || state.settings.profile
      || "belt_2_0";
    const text = await global.AmmoCodePrimer?.get?.(next, profile);
    if (!text) return;
    const ed = $("ac-editor");
    if (ed) ed.value = text;
    state.isPrimer = true;
    state.primerLang = next;
    state.dirty = false;
    state.securityFindings = [];
    state.securityBlocked = false;
    updateStatus();
    paint();
    global.AmmoCodeTabs?.touchActive?.(text);
    global.AmmoCodeTabs?.renderTabs?.();
    if (!opts?.silent) {
      toast(`AI Primer · ${next} — copy & paste to your AI`, true);
    }
  }

  async function setLanguage(lang, opts) {
    const next = lang || "plaintext";
    const profileMayChange = !opts?.skipProfile && state.profiles[next];
    state.language = next;
    const sel = $("ac-lang");
    if (sel && sel.value !== next) sel.value = next;
    if (profileMayChange) {
      state.settings.profile = state.profiles[next];
      saveSettings();
    }
    const wantPrimer = opts?.applyPrimer !== false && shouldApplyPrimer();
    if (wantPrimer && global.AmmoCodePrimer) {
      await applyPrimer(next, { profile: state.settings.profile, silent: !!opts?.silent });
    } else {
      state.isPrimer = false;
      paint();
    }
    global.AmmoCodePlugins?.executeCommand?.("ammocode.languageChanged", next).catch(() => {});
  }

  function paint() {
    const ed = $("ac-editor");
    const hi = $("ac-highlight");
    if (!ed || !hi) return;
    const text = ed.value;
    renderGutter(text);
    ed.classList.toggle("ac-blocked", state.securityBlocked);
    document.querySelector(".ac-editor-wrap")?.classList.toggle("primer-mode", state.isPrimer);
    const highlightLang = state.isPrimer ? "plaintext" : state.language;
    hi.innerHTML = global.AmmoCodeHighlight
      ? global.AmmoCodeHighlight.highlight(text, highlightLang)
      : text.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    syncScroll();
    updateStatus();
  }

  function updateStatus() {
    const ed = $("ac-editor");
    const text = ed?.value || "";
    const lines = text.split("\n").length;
    const cols = (text.split("\n").pop() || "").length + 1;
    $("ac-st-lang").textContent = state.language;
    $("ac-st-g16").textContent = state.settings.profile;
    $("ac-st-pos").textContent = `Ln ${lines}, Col ${cols}`;
    $("ac-st-path").textContent = state.path
      ? state.path.split("/").pop()
      : state.isPrimer
        ? `AI Primer · ${state.language}`
        : "untitled";
    $("ac-st-dirty").textContent = state.dirty ? "● modified" : state.isPrimer ? "◎ primer" : "";
    $("ac-st-primer").textContent = state.isPrimer ? "copy → AI" : "";
    global.AmmoCodeTabs?.updateActiveTabChrome?.();
    const primerBtn = $("ac-copy-primer");
    if (primerBtn) primerBtn.hidden = !state.isPrimer;
  }

  function toast(msg, ok) {
    const el = $("ac-toast");
    if (!el) return;
    el.textContent = msg;
    el.style.borderColor = ok ? "#238636" : "#f85149";
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 4000);
  }

  async function clipboardWrite(text) {
    if (global.AmmoCodePrimer?.copyToClipboard) {
      return global.AmmoCodePrimer.copyToClipboard(text);
    }
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      return false;
    }
  }

  async function clipboardRead() {
    try {
      return await navigator.clipboard.readText();
    } catch (_) {
      return null;
    }
  }

  function flashClipBtn(id) {
    const btn = $(id);
    if (!btn) return;
    btn.classList.add("ok-flash");
    clearTimeout(flashClipBtn._t);
    flashClipBtn._t = setTimeout(() => btn.classList.remove("ok-flash"), 600);
  }

  async function copyFullText() {
    const text = $("ac-editor")?.value ?? "";
    if (!text.length) {
      toast("Nothing to copy", false);
      return;
    }
    const ok = await clipboardWrite(text);
    if (ok) flashClipBtn("ac-tab-copy");
    toast(ok ? `Copied ${text.length.toLocaleString()} characters` : "Copy failed", ok);
  }

  async function pasteFullText() {
    const text = await clipboardRead();
    if (text === null) {
      toast("Paste denied — allow clipboard access", false);
      return;
    }
    const ed = $("ac-editor");
    if (!ed) return;
    ed.value = text;
    state.dirty = true;
    state.isPrimer = !!global.AmmoCodePrimer?.isPrimerContent?.(text);
    if (state.isPrimer) state.primerLang = state.language;
    global.AmmoCodeTabs?.touchActive?.(text);
    paint();
    clearTimeout(runSecurityScan._deb);
    runSecurityScan._deb = setTimeout(() => runSecurityScan(), 200);
    flashClipBtn("ac-tab-paste");
    toast(`Pasted ${text.length.toLocaleString()} characters`, true);
  }

  function renderLanguageDropdown() {
    const sel = $("ac-lang");
    if (!sel) return;
    const ids = global.AmmoCodePlugins?.mergedLanguageIds?.(state.langs) || state.langs;
    const cur = state.language;
    sel.innerHTML = ['<option value="plaintext">Plain Text</option>']
      .concat(
        ids.map((l) => `<option value="${l}">${l}</option>`),
      )
      .join("");
    sel.value = ids.includes(cur) ? cur : "plaintext";
    sel.onchange = () => setLanguage(sel.value);
  }

  async function loadRegistry() {
    const doc = await global.AmmoCodeG16.loadLanguages();
    state.langs = doc.g16_discern || doc.languages || doc.universal?.all || [];
    state.profiles = doc.profiles || { default: "belt_2_0" };
    state.extensions = doc.extensions || {};
    try {
      const ir = await fetch("data/internet-filetypes.json", { cache: "no-store" });
      if (ir.ok) {
        const inet = await ir.json();
        state.extensions = { ...state.extensions, ...(inet.extensions || {}) };
      }
    } catch (_) {}
    if (global.AmmoCodeHighlight?.mergeExtensions) {
      global.AmmoCodeHighlight.mergeExtensions(state.extensions);
    }
    global.AmmoCodeG16.config({
      beltProfile: state.settings.profile,
      g16Version: doc.g16?.version || "16.2.0",
    });
    renderLanguageDropdown();
    $("ac-g16-pill").textContent = `g16 ${doc.g16?.version || ""} · ${state.settings.profile}`;
  }

  async function openPath(path, content) {
    state.path = path || "";
    let lang = state.language;
    if (state.settings.autodetect && path) {
      lang = await global.AmmoCodeG16.discern(path, content);
    } else if (path && global.AmmoCodeHighlight?.langFromPath) {
      lang = global.AmmoCodeHighlight.langFromPath(path);
    }
    if (content !== undefined) $("ac-editor").value = content;
    state.dirty = false;
    state.isPrimer = false;
    const tab = global.AmmoCodeTabs?.getActive?.();
    if (tab) {
      tab.path = state.path;
      tab.content = content !== undefined ? content : ($("ac-editor")?.value || "");
      tab.language = lang;
      tab.dirty = false;
      tab.isPrimer = false;
      global.AmmoCodeTabs?.touchActive?.(tab.content);
    }
    setLanguage(lang, { skipProfile: false, applyPrimer: false });
    global.AmmoCodeTabs?.renderTabs?.();
    toast(`Opened · ${lang}`, true);
  }

  async function saveFile() {
    if (!state.path) {
      toast("Use Open file or embed with a path", false);
      return;
    }
    try {
      const j = await global.AmmoCodeG16.g16Action("write", {
        path: state.path,
        content: $("ac-editor").value,
      });
      if (j.ok === false) throw new Error(j.error || "save failed");
      state.dirty = false;
      global.AmmoCodeTabs?.touchActive?.($("ac-editor")?.value);
      const tab = global.AmmoCodeTabs?.getActive?.();
      if (tab) tab.dirty = false;
      global.AmmoCodeTabs?.updateActiveTabChrome?.();
      updateStatus();
      toast("Saved", true);
    } catch (e) {
      toast(String(e.message || e), false);
    }
  }

  async function g16Check() {
    if (state.isPrimer) {
      toast("Replace primer with code first — or paste AI output here", false);
      return;
    }
    toast("g16 check…", true);
    try {
      const sec = await runSecurityScan();
      if (sec?.blocked) {
        const tip = (sec.findings || [])[0];
        throw new Error(`Bad: ${tip?.message || "unsafe"} — use ${tip?.use_instead || "safe alternative"} instead`);
      }
      const j = await global.AmmoCodeG16.g16Action("g16_check", {
        path: state.path,
        content: $("ac-editor").value,
        language: state.language,
        profile: state.settings.profile,
      });
      if (j.blocked || j.ok === false) throw new Error(j.message || j.detail || j.error || "check failed");
      toast(`g16 OK · ${j.lang || j.language || state.language}`, true);
    } catch (e) {
      toast(String(e.message || e).slice(0, 200), false);
    }
  }

  async function g16Build() {
    if (state.isPrimer) {
      toast("Replace primer with code first — or paste AI output here", false);
      return;
    }
    toast("Building…", true);
    try {
      const sec = await runSecurityScan();
      if (sec?.blocked) {
        const tip = (sec.findings || [])[0];
        throw new Error(`Blocked — ${tip?.message || "bad code"}. Use ${tip?.use_instead || "X"} instead.`);
      }
      const j = await global.AmmoCodeG16.g16Action("g16_build", {
        path: state.path,
        content: $("ac-editor").value,
        language: state.language,
        profile: state.settings.profile,
      });
      if (global.AmmoCodeCompileAlerts?.showBuildResult) {
        global.AmmoCodeCompileAlerts.showBuildResult(j, {
          outputEl: $("ac-output"),
          alertsEl: $("ac-compile-alerts"),
          editor: $("ac-editor"),
          onStatus: (msg, ok) => toast(msg, ok),
        });
        if (j?.content_changed) state.dirty = true;
        if (j.blocked) throw new Error(j.message || "blocked");
        toast(j?.alerts?.summary || j.message || (j.ok ? "Build OK" : "Build failed"), !!j.ok);
        return;
      }
      if (j.blocked || j.ok === false) throw new Error(j.message || j.error || "build failed");
      toast(j.message || `Build OK · ${j.compiler || "g16"}`, true);
    } catch (e) {
      toast(String(e.message || e).slice(0, 240), false);
    }
  }

  async function instaRewrite() {
    const ed = $("ac-editor");
    if (!ed) return;
    const out = await global.AmmoCodeSecurity?.instaRewrite?.(ed.value, state.language);
    if (out?.changed && out.content) {
      ed.value = out.content;
      state.dirty = true;
      await runSecurityScan();
      toast(`Insta-rewrite applied (${(out.applied || []).length} patch(es))`, true);
    } else {
      toast("Nothing to rewrite", true);
    }
  }

  function bindUi() {
    const ed = $("ac-editor");
    ed?.addEventListener("input", () => {
      state.dirty = true;
      if (state.isPrimer && !global.AmmoCodePrimer?.isPrimerContent?.(ed.value)) {
        state.isPrimer = false;
      }
      const tab = global.AmmoCodeTabs?.getActive?.();
      if (tab) {
        tab.dirty = true;
        tab.isPrimer = state.isPrimer;
      }
      global.AmmoCodeTabs?.touchActive?.(ed.value);
      paint();
      clearTimeout(runSecurityScan._deb);
      runSecurityScan._deb = setTimeout(() => runSecurityScan(), 400);
    });
    ed?.addEventListener("scroll", syncScroll);
    ed?.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveFile();
      }
    });

    ["ac-save", "ac-save-bar"].forEach((id) => $(id)?.addEventListener("click", saveFile));
    ["ac-g16-check", "ac-g16-bar"].forEach((id) => $(id)?.addEventListener("click", g16Check));
    ["ac-g16-build", "ac-build-bar"].forEach((id) => $(id)?.addEventListener("click", g16Build));
    $("ac-wrap")?.addEventListener("click", () => {
      state.settings.wordWrap = !state.settings.wordWrap;
      saveSettings();
    });
    $("ac-profile")?.addEventListener("change", async (e) => {
      state.settings.profile = e.target.value;
      saveSettings();
      if (state.isPrimer || shouldApplyPrimer()) {
        await applyPrimer(state.language, { profile: state.settings.profile });
      }
    });
    $("ac-theme")?.addEventListener("change", (e) => {
      state.settings.theme = e.target.value;
      saveSettings();
    });

    $("ac-open")?.addEventListener("click", () => $("ac-file-input")?.click());
    $("ac-screenshot")?.addEventListener("click", async () => {
      try {
        const out = await global.AmmoCodeScreenshot?.saveScreenshot?.(".ac-app");
        toast(out?.ok ? `Screenshot saved · ${out.filename}` : "Screenshot failed", !!out?.ok);
      } catch (e) {
        toast(String(e.message || e).slice(0, 120), false);
      }
    });
    $("ac-file-input")?.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const text = await file.text();
      await openPath(file.name, text);
    });

    function pickExtension(source) {
      const input = document.createElement("input");
      input.type = "file";
      input.webkitdirectory = true;
      input.addEventListener("change", async () => {
        try {
          await global.AmmoCodePlugins.loadUnpackedFolder([...input.files], source);
          renderLanguageDropdown();
          $("ac-ext-list").textContent = global.AmmoCodePlugins.listExtensions()
            .map((x) => `${x.publisher}/${x.id}`)
            .join(" · ") || "No extensions loaded";
          toast(`${source} extension loaded`, true);
        } catch (err) {
          toast(String(err.message || err), false);
        }
      });
      input.click();
    }
    $("ac-ext-vscode")?.addEventListener("click", () => pickExtension("vscode"));
    $("ac-ext-openvsx")?.addEventListener("click", () => pickExtension("openvsx"));

    $("ac-collab-bar")?.addEventListener("click", () => global.AmmoCodeFlyout?.toggle?.("collab"));
    ["ac-fly-sec-scan", "ac-sec-scan"].forEach((id) => $(id)?.addEventListener("click", () => runSecurityScan().then((r) => {
      toast(r?.blocked ? `⛔ ${r.finding_count} bad` : `Scan OK (${r?.finding_count || 0})`, !r?.blocked);
    })));
    ["ac-fly-sec-rewrite", "ac-sec-rewrite"].forEach((id) => $(id)?.addEventListener("click", instaRewrite));
    $("ac-fly-sec-status")?.addEventListener("click", () => refreshSecurityFieldStatus(true));
    $("ac-fly-defield")?.addEventListener("click", async () => {
      try {
        const r = await fetch(api(), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "defield_sg", force: true }),
        });
        const j = await r.json();
        toast(j.defielded ? "AmmoCode + SG defielded" : j.error || "defield failed", !!j.ok);
        await refreshSecurityFieldStatus(true);
      } catch (e) {
        toast(String(e.message || e), false);
      }
    });
    $("ac-fly-open")?.addEventListener("click", () => $("ac-file-input")?.click());
    $("ac-fly-save")?.addEventListener("click", saveFile);

    $("ac-copy-primer")?.addEventListener("click", copyFullText);
    $("ac-tab-copy")?.addEventListener("click", copyFullText);
    $("ac-tab-paste")?.addEventListener("click", pasteFullText);
    async function reloadPrimerClick() {
      await applyPrimer(state.language, { profile: state.settings.profile });
    }
    $("ac-reload-primer")?.addEventListener("click", reloadPrimerClick);
    $("ac-reload-primer-menu")?.addEventListener("click", reloadPrimerClick);
    $("ac-copy-primer-menu")?.addEventListener("click", () => $("ac-copy-primer")?.click());

    $("ac-new-tab")?.addEventListener("click", () => {
      global.AmmoCodeTabs?.newTab?.({ language: state.language });
      setLanguage(state.language, { silent: true });
    });
    $("ac-file-settings-btn")?.addEventListener("click", () => {
      document.querySelectorAll(".ac-menu").forEach((m) => { m.open = false; });
      const m = $("ac-file-settings-menu");
      if (m) {
        m.open = true;
        global.AmmoCodeTabs?.syncSettingsForm?.();
      }
    });
    function bindSettingInput(id, fn) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", fn);
      el.addEventListener("input", fn);
    }
    bindSettingInput("ac-set-font", () => {
      state.settings.fontSize = Math.min(28, Math.max(10, Number($("ac-set-font")?.value) || 13));
      saveSettings();
    });
    bindSettingInput("ac-set-tabsize", () => {
      state.settings.tabSize = Math.min(8, Math.max(2, Number($("ac-set-tabsize")?.value) || 4));
      saveSettings();
    });
    $("ac-set-wrap")?.addEventListener("change", (e) => {
      state.settings.wordWrap = e.target.checked;
      saveSettings();
    });
    $("ac-set-autodetect")?.addEventListener("change", (e) => {
      state.settings.autodetect = e.target.checked;
      saveSettings();
    });
    $("ac-set-tab-aging")?.addEventListener("change", (e) => {
      state.settings.tabAging = e.target.checked;
      saveSettings();
      global.AmmoCodeTabs?.renderTabs?.();
    });
    $("ac-set-profile")?.addEventListener("change", async (e) => {
      state.settings.profile = e.target.value;
      $("ac-profile") && ($("ac-profile").value = e.target.value);
      saveSettings();
      if (state.isPrimer || shouldApplyPrimer()) {
        await applyPrimer(state.language, { profile: state.settings.profile });
      }
    });
    $("ac-set-theme")?.addEventListener("change", (e) => {
      state.settings.theme = e.target.value;
      $("ac-theme") && ($("ac-theme").value = e.target.value);
      saveSettings();
    });
  }

  async function refreshSecurityFieldStatus(toastOnClick) {
    try {
      const r = await fetch(api(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "security_status" }),
      });
      const j = await r.json();
      const sg = j.sg_field || {};
      const fieldEl = $("ac-sec-field");
      const g16 = $("ac-g16-pill");
      const def = !!sg.defield_active;
      const acFielded = !!sg.ammocode_fielded;
      const sgOnly = !!sg.sg_fielded;
      const label = def ? "defield" : acFielded && sgOnly ? "both fielded" : acFielded ? "ammocode fielded" : sgOnly ? "sg fielded" : "clean";
      if (fieldEl) {
        fieldEl.textContent = `Field: ${label} · AmmoCode ${acFielded ? "field" : "defield"} · SG ${sgOnly ? "field" : "ok"} · pins ${j.pin_count ?? 0}`;
      }
      if (g16) {
        g16.textContent = def ? "g16 · defield" : "g16 · belt_2_0";
        g16.className = "pill " + (def ? "ok" : acFielded || sgOnly ? "warn" : "ok");
        g16.title = sg.defield_active ? "Defielded — AmmoCode + SG" : acFielded ? "AmmoCode fielded" : sgOnly ? "SG field stack active" : "Clean posture";
      }
      await global.AmmoCodeG16?.fetchFieldPosture?.("plain");
      const sum = $("ac-sec-summary");
      if (sum && toastOnClick) {
        sum.textContent = `MITM pins: ${j.pin_count ?? 0} · posture: ${label}`;
      }
      if (toastOnClick) toast(`Security: ${label}, ${j.pin_count ?? 0} pin(s)`, true);
    } catch (_) {}
  }

  function syncCollabPill() {
    const pill = $("ac-collab-pill");
    const st = global.AmmoCodeCollab?.state;
    if (!pill || !st) return;
    if (st.connected) {
      pill.textContent = `collab: ${st.peers?.length || 1}`;
      pill.className = "pill ok";
    } else {
      pill.textContent = "collab: off";
      pill.className = "pill";
    }
    $("ac-st-collab").textContent = st.connected ? `room ${st.roomId || ""}` : "invite-only";
  }

  async function init() {
    await loadSettings();
    bindUi();
    global.AmmoCodeFlyout?.init?.();
    const tabMode = new URLSearchParams(location.search).get("tab");
    if (global.AmmoCodeBrowserTab && tabMode && window.self === window.top) {
      await global.AmmoCodeBrowserTab.boot();
    }
    await global.AmmoCodeSecurity?.loadRegistry?.();
    await global.AmmoCodeCombinatorics?.loadPatterns?.();
    await global.AmmoCodePrimer?.loadRegistry?.();
    await loadRegistry();
    global.AmmoCodeCombinatorics?.renderPanel?.($("ac-comb-panel"));
    global.AmmoCodeCombinatorics?.runCycle?.(state.settings.profile).catch(() => {});
    await global.AmmoCodeCollab?.init?.();
    global.AmmoCodeZNetwork?.renderFlyout?.($("ac-flyout-znetwork"));
    await global.AmmoCodeZNetwork?.init?.();
    await global.AmmoCodeNetwork?.init?.();
    await global.AmmoCodeG16?.fetchFieldPosture?.("plain");
    await refreshSecurityFieldStatus(false);
    await global.AmmoCodeTabs?.init?.(api);
    global.AmmoCodeTabs?.syncSettingsForm?.();
    setInterval(syncCollabPill, 1500);
    const params = new URLSearchParams(location.search);
    const lang = params.get("lang");
    const path = params.get("path");
    if (path) {
      try {
        const r = await fetch(path);
        await openPath(path, await r.text());
      } catch (_) {
        await setLanguage(lang || "cxx", { silent: true });
      }
    } else {
      await setLanguage(lang || "cxx", { silent: true });
    }
    if (!state.isPrimer) await runSecurityScan();
  }

  function mount(root, opts) {
    if (!root) return;
    global.AmmoCodeG16.config(opts?.g16 || {});
    if (opts?.language) state.language = opts.language;
    if (opts?.content && $("ac-editor")) $("ac-editor").value = opts.content;
    if (opts?.path) state.path = opts.path;
    paint();
    return api;
  }

  const api = {
    mount, setLanguage, applyPrimer, copyFullText, pasteFullText,
    paint, toast, saveFile, runSecurityScan, state,
  };
  global.AmmoCodeEditor = api;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(typeof globalThis !== "undefined" ? globalThis : window);