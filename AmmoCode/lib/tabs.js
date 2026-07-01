/**
 * AmmoCode tabs — multi-tab editor, age coloring (3h → solid red), per-file settings.
 * Age tick runs once per minute — no paint/highlight on tick (avoids UI freeze).
 */
(function (global) {
  "use strict";

  const AGE_MS = 3 * 60 * 60 * 1000;
  const TICK_MS = 60 * 1000;
  const FILE_SETTINGS_KEY = "ammocode-file-settings-v1";

  let tabs = [];
  let activeId = null;
  let editor = null;
  let tickTimer = null;
  let ctxMenu = null;
  let ctxTabId = null;
  let fileSettings = { paths: {} };

  function $(id) {
    return document.getElementById(id);
  }

  function uid() {
    return "t" + Math.random().toString(36).slice(2, 9);
  }

  function fileKey(tab) {
    if (!tab) return "";
    if (tab.path) return tab.path;
    if (tab.isPrimer) return `primer:${tab.language}`;
    return `untitled:${tab.id}`;
  }

  async function loadFileSettings() {
    try {
      if (global.AmmoCodeSettings?.load) {
        const j = await global.AmmoCodeSettings.load();
        if (j.ok) {
          const fa = global.AmmoCodeSettings.fileAgingFrom(j);
          const paths = fa.paths || fa;
          fileSettings = { paths: typeof paths === "object" ? paths : {} };
          return;
        }
      }
    } catch (_) {}
    try {
      const raw = localStorage.getItem(FILE_SETTINGS_KEY);
      if (raw) fileSettings = { paths: {}, ...JSON.parse(raw) };
    } catch (_) {
      fileSettings = { paths: {} };
    }
  }

  async function saveFileSettings() {
    try {
      if (global.AmmoCodeSettings?.save) {
        await global.AmmoCodeSettings.save({ fileDisableAging: fileSettings.paths || {} });
        return;
      }
    } catch (_) {}
    try {
      localStorage.setItem(FILE_SETTINGS_KEY, JSON.stringify(fileSettings));
    } catch (_) {}
  }

  function fileSetting(key, tab) {
    return fileSettings.paths[fileKey(tab)]?.[key];
  }

  function setFileSetting(key, value, tab) {
    const fk = fileKey(tab);
    if (!fileSettings.paths[fk]) fileSettings.paths[fk] = {};
    fileSettings.paths[fk][key] = value;
    saveFileSettings();
  }

  function agingDisabled(tab) {
    if (!editor?.state?.settings?.tabAging) return true;
    if (tab.disableAging) return true;
    if (fileSetting("disableAging", tab)) return true;
    return false;
  }

  function ageRatio(tab) {
    if (agingDisabled(tab)) return 0;
    const elapsed = Date.now() - (tab.lastEditAt || Date.now());
    return Math.min(1, Math.max(0, elapsed / AGE_MS));
  }

  function tabLabel(tab) {
    if (tab.path) return tab.path.split("/").pop();
    if (tab.isPrimer) return `AI Primer · ${tab.language}`;
    return "Welcome";
  }

  function createTab(opts) {
    const now = Date.now();
    return {
      id: opts?.id || uid(),
      path: opts?.path || "",
      language: opts?.language || "cxx",
      content: "",
      vaultHandle: opts?.vaultHandle || "",
      dirty: !!opts?.dirty,
      isPrimer: !!opts?.isPrimer,
      primerLang: opts?.primerLang || "",
      lastEditAt: opts?.lastEditAt ?? now,
      disableAging: !!opts?.disableAging,
      securityFindings: opts?.securityFindings || [],
      securityBlocked: !!opts?.securityBlocked,
      _plainBootstrap: opts?.content ?? "",
    };
  }

  async function sealTabContent(tab, text) {
    const vault = global.AmmoCodeMemoryVault;
    if (!vault?.store) {
      tab.content = text;
      return;
    }
    if (tab.vaultHandle) vault.release(tab.vaultHandle);
    const out = await vault.store(text, tab.vaultHandle || tab.id);
    if (out?.ok && out.handle) {
      tab.vaultHandle = out.handle;
      tab.content = "";
    } else {
      tab.content = text;
    }
  }

  async function openTabContent(tab) {
    if (tab._plainBootstrap != null && tab._plainBootstrap !== "") {
      const boot = tab._plainBootstrap;
      tab._plainBootstrap = "";
      await sealTabContent(tab, boot);
      return boot;
    }
    if (tab.vaultHandle && global.AmmoCodeMemoryVault?.fetch) {
      const got = await global.AmmoCodeMemoryVault.fetch(tab.vaultHandle);
      if (got?.ok) return got.plaintext || "";
      tab.vaultHandle = "";
    }
    return tab.content || "";
  }

  function releaseTabVault(tab) {
    if (!tab?.vaultHandle) return;
    global.AmmoCodeMemoryVault?.release?.(tab.vaultHandle);
    tab.vaultHandle = "";
    tab.content = "";
  }

  function getActive() {
    return tabs.find((t) => t.id === activeId) || null;
  }

  function pullFromEditor() {
    const tab = getActive();
    const st = editor?.state;
    const ed = $("ac-editor");
    if (!tab || !st || !ed) return;
    tab.path = st.path;
    tab.language = st.language;
    sealTabContent(tab, ed.value);
    tab.dirty = st.dirty;
    tab.isPrimer = st.isPrimer;
    tab.primerLang = st.primerLang;
    tab.securityFindings = st.securityFindings || [];
    tab.securityBlocked = st.securityBlocked;
    if (fileSetting("disableAging", tab)) tab.disableAging = true;
  }

  async function pushToEditor(tab) {
    const st = editor?.state;
    const ed = $("ac-editor");
    if (!tab || !st || !ed) return;
    st.path = tab.path;
    st.language = tab.language;
    st.dirty = tab.dirty;
    st.isPrimer = tab.isPrimer;
    st.primerLang = tab.primerLang || tab.language;
    st.securityFindings = tab.securityFindings || [];
    st.securityBlocked = tab.securityBlocked;
    ed.value = await openTabContent(tab);
    const sel = $("ac-lang");
    if (sel && sel.value !== tab.language) sel.value = tab.language;
    tab.disableAging = tab.disableAging || !!fileSetting("disableAging", tab);
    editor.paint?.();
  }

  async function switchTo(id) {
    if (id === activeId) return;
    pullFromEditor();
    const tab = tabs.find((t) => t.id === id);
    if (!tab) return;
    activeId = id;
    await pushToEditor(tab);
    renderTabs();
    editor?.runSecurityScan?.();
  }

  function newTab(opts) {
    pullFromEditor();
    const tab = createTab(opts);
    tabs.push(tab);
    activeId = tab.id;
    pushToEditor(tab);
    renderTabs();
    return tab;
  }

  function closeTab(id) {
    if (tabs.length <= 1) {
      const tab = getActive();
      if (tab) {
        releaseTabVault(tab);
        tab.path = "";
        tab.dirty = false;
        tab.isPrimer = false;
        tab.lastEditAt = Date.now();
        pushToEditor(tab);
        editor?.setLanguage?.(tab.language, { silent: true });
      }
      renderTabs();
      return;
    }
    const idx = tabs.findIndex((t) => t.id === id);
    if (idx < 0) return;
    releaseTabVault(tabs[idx]);
    tabs.splice(idx, 1);
    if (activeId === id) {
      activeId = tabs[Math.max(0, idx - 1)]?.id || tabs[0]?.id;
      pushToEditor(getActive());
      editor?.runSecurityScan?.();
    }
    renderTabs();
  }

  function touchActive(content) {
    const tab = getActive();
    if (!tab) return;
    tab.lastEditAt = Date.now();
    if (content !== undefined) sealTabContent(tab, content);
    scheduleAgePaint();
  }

  let agePaintQueued = false;
  function scheduleAgePaint() {
    if (agePaintQueued) return;
    agePaintQueued = true;
    requestAnimationFrame(() => {
      agePaintQueued = false;
      applyAgeStyles();
    });
  }

  function applyAgeStyles() {
    const host = $("ac-tabs");
    if (!host) return;
    host.querySelectorAll(".ac-tab[data-tab-id]").forEach((el) => {
      const tab = tabs.find((t) => t.id === el.dataset.tabId);
      if (!tab) return;
      const age = ageRatio(tab);
      el.style.setProperty("--tab-age", String(age));
      el.classList.toggle("no-age", agingDisabled(tab));
      el.classList.toggle("age-stale", !agingDisabled(tab) && age >= 1);
      const mins = Math.floor((Date.now() - tab.lastEditAt) / 60000);
      el.title = agingDisabled(tab)
        ? tabLabel(tab)
        : `${tabLabel(tab)} — idle ${mins}m (red at 3h)`;
    });
  }

  function updateActiveTabChrome() {
    const tab = getActive();
    const host = $("ac-tabs");
    if (!tab || !host) return;
    const el = host.querySelector(`[data-tab-id="${tab.id}"]`);
    if (!el) return;
    const text = el.querySelector(".ac-tab-text");
    if (text) text.textContent = tabLabel(tab);
    let dirty = el.querySelector(".ac-tab-dirty");
    if (tab.dirty && !dirty) {
      el.insertAdjacentHTML("afterbegin", '<span class="ac-tab-dirty">●</span>');
    } else if (!tab.dirty && dirty) {
      dirty.remove();
    }
  }

  function renderTabs() {
    const host = $("ac-tabs");
    if (!host) return;
    host.innerHTML = tabs.map((tab) => {
      const active = tab.id === activeId ? " active" : "";
      const dirty = tab.dirty ? '<span class="ac-tab-dirty">●</span>' : "";
      const noAge = agingDisabled(tab) ? " no-age" : "";
      const age = ageRatio(tab);
      const stale = !agingDisabled(tab) && age >= 1 ? " age-stale" : "";
      return `<button type="button" class="ac-tab${active}${noAge}${stale}" data-tab-id="${tab.id}" `
        + `style="--tab-age:${age}" title="${tabLabel(tab)}">`
        + `${dirty}<span class="ac-tab-text">${tabLabel(tab)}</span>`
        + `<span class="ac-tab-close" data-close="${tab.id}" aria-label="Close tab">×</span></button>`;
    }).join("")
      + '<button type="button" class="ac-tab-new" id="ac-tab-new" title="New tab">+</button>';

    host.querySelectorAll(".ac-tab[data-tab-id]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        if (e.target.closest("[data-close]")) return;
        switchTo(btn.dataset.tabId);
      });
      btn.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        showContextMenu(e.clientX, e.clientY, btn.dataset.tabId);
      });
    });
    host.querySelectorAll("[data-close]").forEach((x) => {
      x.addEventListener("click", (e) => {
        e.stopPropagation();
        closeTab(x.dataset.close);
      });
    });
    $("ac-tab-new")?.addEventListener("click", () => {
      newTab({ language: editor?.state?.language || "cxx" });
      editor?.setLanguage?.(editor?.state?.language || "cxx", { silent: true });
    });
    applyAgeStyles();
  }

  function ensureContextMenu() {
    if (ctxMenu) return ctxMenu;
    ctxMenu = document.createElement("div");
    ctxMenu.id = "ac-tab-ctx";
    ctxMenu.className = "ac-tab-ctx";
    ctxMenu.hidden = true;
    ctxMenu.innerHTML = [
      '<button type="button" data-ctx="no-age">Disable age color (this tab)</button>',
      '<button type="button" data-ctx="remember">Remember — no age color for this file</button>',
      '<button type="button" data-ctx="enable-age">Enable age color</button>',
      '<div class="ac-menu-sep"></div>',
      '<button type="button" data-ctx="close">Close tab</button>',
      '<button type="button" data-ctx="close-others">Close other tabs</button>',
    ].join("");
    document.body.appendChild(ctxMenu);
    ctxMenu.addEventListener("click", (e) => {
      const act = e.target.closest("[data-ctx]")?.dataset?.ctx;
      if (!act || !ctxTabId) return hideContextMenu();
      const tab = tabs.find((t) => t.id === ctxTabId);
      if (!tab) return hideContextMenu();
      if (act === "no-age") {
        tab.disableAging = true;
        renderTabs();
        toast("Age color off for this tab");
      } else if (act === "remember") {
        tab.disableAging = true;
        setFileSetting("disableAging", true, tab);
        renderTabs();
        toast(`Saved — no age color for ${fileKey(tab)}`);
      } else if (act === "enable-age") {
        tab.disableAging = false;
        setFileSetting("disableAging", false, tab);
        renderTabs();
        toast("Age color enabled");
      } else if (act === "close") {
        closeTab(ctxTabId);
      } else if (act === "close-others") {
        const keep = ctxTabId;
        tabs = tabs.filter((t) => t.id === keep);
        activeId = keep;
        pushToEditor(getActive());
        renderTabs();
      }
      hideContextMenu();
    });
    document.addEventListener("click", hideContextMenu);
    document.addEventListener("scroll", hideContextMenu, true);
    return ctxMenu;
  }

  function showContextMenu(x, y, tabId) {
    ctxTabId = tabId;
    const menu = ensureContextMenu();
    menu.hidden = false;
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
    const tab = tabs.find((t) => t.id === tabId);
    const disabled = tab && agingDisabled(tab);
    menu.querySelector('[data-ctx="no-age"]').hidden = !!disabled;
    menu.querySelector('[data-ctx="remember"]').hidden = !!disabled;
    menu.querySelector('[data-ctx="enable-age"]').hidden = !disabled;
  }

  function hideContextMenu() {
    if (ctxMenu) ctxMenu.hidden = true;
    ctxTabId = null;
  }

  function toast(msg) {
    editor?.toast?.(msg, true);
  }

  function startAgeTicker() {
    if (tickTimer) return;
    tickTimer = setInterval(applyAgeStyles, TICK_MS);
  }

  function stopAgeTicker() {
    if (tickTimer) clearInterval(tickTimer);
    tickTimer = null;
  }

  async function refreshVaultStatus() {
    const el = $("ac-st-memory");
    if (!el || !global.AmmoCodeMemoryVault?.status) return;
    const st = await global.AmmoCodeMemoryVault.status();
    el.textContent = st?.no_leak ? "vault sealed · 4-slot" : "vault warn";
    el.title = st?.motto || "4-slot running encode/decode — runtime tax 0";
  }

  async function init(editorApi) {
    editor = editorApi;
    await loadFileSettings();
    if (!tabs.length) {
      tabs.push(createTab({ language: editor?.state?.language || "cxx" }));
      activeId = tabs[0].id;
      await pushToEditor(tabs[0]);
    }
    renderTabs();
    startAgeTicker();
    refreshVaultStatus();
    setInterval(refreshVaultStatus, 60000);
  }

  function syncSettingsForm() {
    const st = editor?.state?.settings;
    if (!st) return;
    const aging = $("ac-set-tab-aging");
    const fs = $("ac-set-font");
    const ts = $("ac-set-tabsize");
    const ad = $("ac-set-autodetect");
    const ww = $("ac-set-wrap");
    if (aging) aging.checked = st.tabAging !== false;
    if (fs) fs.value = String(st.fontSize);
    if (ts) ts.value = String(st.tabSize);
    if (ad) ad.checked = !!st.autodetect;
    if (ww) ww.checked = !!st.wordWrap;
  }

  global.AmmoCodeTabs = {
    init,
    getActive,
    newTab,
    closeTab,
    switchTo,
    touchActive,
    pullFromEditor,
    pushToEditor,
    renderTabs,
    updateActiveTabChrome,
    fileKey,
    setFileSetting,
    fileSetting,
    syncSettingsForm,
    stopAgeTicker,
    AGE_MS,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);