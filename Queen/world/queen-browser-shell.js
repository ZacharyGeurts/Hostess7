/**
 * Queen Browser Shell — tabbed OS surface.
 * Pinned Start tab · multi-iframe panes · pop-out windows · Alt+Tab · fullscreen · IFF postMessage guard.
 */
(function () {
  "use strict";

  const shell = {
    panes: new Map(),
    popouts: new Map(),
    tabCycle: [],
    cycleIdx: 0,
    viewportFs: false,
    ready: false,
    startOpen: false,
    startSide: "classic",
    desktopDoc: null,
    autoProxyExternal: true,
    keysEngaged: false,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function startUrl() {
    const raw = document.body?.dataset?.queenStart || "/world/kilroy-home.html";
    if (raw.startsWith("/")) return `${location.origin}${raw}`;
    return raw;
  }

  function panelPort() {
    return document.body?.dataset?.nexusPanelPort || "9477";
  }

  function panelBase() {
    return `http://127.0.0.1:${panelPort()}`;
  }

  function engageKeyboardSovereign() {
    if (shell.keysEngaged) return;
    fetch(`${panelBase()}/api/field-keyboard-sovereign/engage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      credentials: "omit",
    })
      .then((r) => r.json())
      .then((j) => {
        if (j.ok !== false) shell.keysEngaged = true;
      })
      .catch(() => {});
  }

  function releaseKeyboardSovereign(reason) {
    if (!shell.keysEngaged) return;
    const body = JSON.stringify({ reason: reason || "pagehide" });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(`${panelBase()}/api/field-keyboard-sovereign/release`, body);
    }
    shell.keysEngaged = false;
  }

  function wireZNetworkHooks() {
    if (document.body?.dataset?.znetworkHooks !== "1") return;
    engageKeyboardSovereign();
    fetch(`${panelBase()}/api/znetwork`, { cache: "no-store" }).catch(() => {});
    window.addEventListener("pagehide", () => releaseKeyboardSovereign("pagehide"));
    window.addEventListener("beforeunload", () => releaseKeyboardSovereign("unload"));
  }

  function openCadRescue() {
    const fieldUrl = `${panelBase()}/field`;
    globalThis.QueenOS?.browser?.newTab?.(fieldUrl);
    const status = $("qb-status");
    if (status) status.textContent = "Ctrl+Alt+Del · ZNetwork keyboard hook · AmmoOS rescue";
  }

  const SHELL_ACTIONS = new Set([
    "navigate", "new_tab", "attach_tab", "home", "command", "open_window", "open_program", "dock", "desktop_window",
  ]);

  function tabTip(t) {
    const title = t.title || t.url || "Tab";
    const pinned = t.pinned || t.role === "start" || t.role === "desktop" || t.role === "files";
    return pinned ? `${title} · pinned` : title;
  }

  function isCoreTab(t) {
    return t.role === "start" || t.role === "desktop" || t.role === "files";
  }

  function isLoopbackOrigin(origin) {
    try {
      const u = new URL(origin);
      return u.hostname === "127.0.0.1" || u.hostname === "localhost";
    } catch {
      return false;
    }
  }

  function isSafeShellUrl(url) {
    if (!url || typeof url !== "string") return false;
    const u = url.trim();
    if (!u || u.length > 8192) return false;
    const lower = u.toLowerCase();
    if (lower.startsWith("javascript:") || lower.startsWith("data:") || lower.startsWith("vbscript:")) {
      return false;
    }
    if (u.startsWith("/") || u.startsWith("queen://")) return true;
    try {
      const parsed = new URL(u, location.origin);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
      return true;
    } catch {
      return false;
    }
  }

  function ensureViewport() {
    const viewport = document.querySelector(".qb-viewport");
    if (!viewport) return null;
    let panes = viewport.querySelector(".qb-tab-panes");
    if (!panes) {
      const legacy = $("qb-frame");
      panes = document.createElement("div");
      panes.className = "qb-tab-panes";
      panes.id = "qb-tab-panes";
      if (legacy) {
        const pane = document.createElement("div");
        pane.className = "qb-tab-pane active";
        pane.dataset.tabId = "legacy";
        legacy.parentNode?.removeChild(legacy);
        pane.appendChild(legacy);
        panes.appendChild(pane);
        shell.panes.set("legacy", { pane, frame: legacy });
      }
      viewport.appendChild(panes);
    }
    return panes;
  }

  function getOrCreatePane(tabId) {
    if (shell.panes.has(tabId)) return shell.panes.get(tabId);
    const panes = ensureViewport();
    if (!panes) return null;
    const pane = document.createElement("div");
    pane.className = "qb-tab-pane";
    pane.dataset.tabId = tabId;
    const frame = document.createElement("iframe");
    frame.className = "qb-frame";
    frame.title = "Queen tab surface";
    frame.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation",
    );
    pane.appendChild(frame);
    panes.appendChild(pane);
    const entry = { pane, frame };
    shell.panes.set(tabId, entry);
    return entry;
  }

  function benchmarkMode() {
    return globalThis.QueenFieldSanity?.benchmarkMode?.() || document.body?.dataset?.queenBenchmark === "1";
  }

  function setActivePane(tabId) {
    const bench = benchmarkMode();
    document.querySelectorAll(".qb-tab-pane").forEach((p) => {
      const active = p.dataset.tabId === tabId;
      p.classList.toggle("active", active);
      if (bench && !active) {
        const frame = p.querySelector(".qb-frame");
        if (frame && frame.src && frame.src !== "about:blank") {
          frame.dataset.discardedSrc = frame.src;
          frame.src = "about:blank";
        }
      } else if (bench && active) {
        const frame = p.querySelector(".qb-frame");
        const restore = frame?.dataset?.discardedSrc;
        if (frame && restore && (!frame.src || frame.src === "about:blank")) {
          frame.src = restore;
        }
      }
    });
    shell.tabCycle = Array.from(shell.panes.keys()).filter((id) => !shell.popouts.has(id));
    const idx = shell.tabCycle.indexOf(tabId);
    if (idx >= 0) shell.cycleIdx = idx;
  }

  function isTopLevelBenchUrl(url) {
    if (!url) return false;
    try {
      const parsed = new URL(url, location.origin);
      const host = (parsed.hostname || "").toLowerCase();
      const path = (parsed.pathname || "").toLowerCase();
      if (host === "browserbench.org" || host.endsWith(".browserbench.org")) return true;
      return /speedometer|jetstream|motionmark|webxprt|todomvc/i.test(path);
    } catch (_) {
      return /speedometer|browserbench\.org|jetstream|motionmark/i.test(String(url));
    }
  }

  function maybeTopLevelBench(url) {
    if (!benchmarkMode() || !isTopLevelBenchUrl(url)) return false;
    window.location.assign(url);
    return true;
  }

  function isExternalUrl(url) {
    if (!url || url.startsWith("about:") || url.startsWith("/") || url.startsWith("queen://")) return false;
    try {
      const u = new URL(url, location.origin);
      return u.hostname !== "127.0.0.1" && u.hostname !== "localhost";
    } catch {
      return false;
    }
  }

  function shouldProxy(url, explicitProxy) {
    if (benchmarkMode()) return false;
    if (explicitProxy === true) return true;
    if (explicitProxy === false) return false;
    if (!isExternalUrl(url)) return false;
    return shell.autoProxyExternal !== false;
  }

  function frameUrl(url, proxy, compatMode) {
    if (!url) return "about:blank";
    const mode = compatMode || "auto";
    if (shouldProxy(url, proxy)) {
      return `/browse/view?url=${encodeURIComponent(url)}&compat=${encodeURIComponent(mode)}`;
    }
    return url;
  }

  function injectPageAgent(frame) {
    if (!frame) return;
    global.QueenPageInspector?.injectAgent?.(frame);
    frame.addEventListener(
      "load",
      () => {
        global.QueenPageInspector?.injectAgent?.(frame);
      },
      { once: false },
    );
  }

  function applyCompatToFrame(frame, profile) {
    if (!frame || !profile) return;
    const sandbox = profile.sandbox || profile.compat_profile?.sandbox;
    if (sandbox) frame.setAttribute("sandbox", sandbox);
    frame.dataset.compatMode = profile.effective_mode || profile.compat_mode || "auto";
    frame.dataset.compatEra = profile.compat_era || (profile.era && profile.era.id) || "es2026";
  }

  async function loadTab(tabId, url, opts) {
    if (maybeTopLevelBench(url)) return;
    const entry = getOrCreatePane(tabId);
    if (!entry) return;
    const doc = globalThis.QueenOS?.browser?.doc?.doc || globalThis.QueenOS?.browser?.doc;
    const tab = (doc?.tabs || []).find((t) => t.id === tabId);
    let compatMode = opts?.compatMode || tab?.compat_mode || "auto";
    if (benchmarkMode()) compatMode = "modern";
    const profile = opts?.compat || tab?.compat_profile || tab;
    applyCompatToFrame(entry.frame, profile);
    globalThis.QueenFieldSanity?.hardenFrames?.();
    const skipValidate = benchmarkMode() && globalThis.QueenFieldSanity?.isFastUrl?.(url);
    if (url && globalThis.QueenFieldSanity?.validateUrl && !skipValidate) {
      const gate = await globalThis.QueenFieldSanity.validateUrl(url);
      if (!gate.ok) {
        const statusEl = $("qb-status");
        if (statusEl) {
          statusEl.textContent = `Field sanity blocked · ${gate.reason || gate.classification?.verdict || "hold"}`;
        }
        url = startUrl();
      }
    }
    const proxy = benchmarkMode() ? false : (opts?.proxy ?? doc?.proxyMode);
    entry.frame.src = frameUrl(url, proxy, compatMode);
    injectPageAgent(entry.frame);
    delete entry.frame.dataset.discardedSrc;
    setActivePane(tabId);
    document.dispatchEvent(new CustomEvent("queen-navigate", { detail: { tabId, url } }));
    const pill = document.getElementById("qb-compat-pill");
    if (pill && tab) {
      pill.textContent = `${tab.compat_era || "es2026"} · ${tab.compat_mode || "auto"}`;
      pill.title = "Web compat — auto secures legacy code";
    }
  }

  function decorateTabsRender(html, tabs) {
    return (tabs || [])
      .map((t) => {
        const pinned = t.pinned || t.role === "start" || t.role === "desktop" || t.role === "files";
        const popped = shell.popouts.has(t.id);
        const roleCls =
          t.role === "files"
            ? " qb-tab--files"
            : t.role === "desktop" || t.role === "start" || t.pinned
              ? " qb-tab--start"
              : "";
        const cls = [
          "qb-tab",
          t.active ? " active" : "",
          pinned ? ` qb-tab-pinned${roleCls}` : "",
          popped ? " qb-tab-popped" : "",
        ].join("");
        const pinTitle = pinned ? "Unpin tab" : "Pin tab";
        const pinGlyph = pinned ? "📌" : "📍";
        const pinBtn = isCoreTab(t)
          ? ""
          : `<span class="qb-tab-pin" data-pin="${esc(t.id)}" title="${pinTitle}" aria-label="${pinTitle}">${pinGlyph}</span>`;
        return `
      <button type="button" class="${cls}" data-tab="${esc(t.id)}" title="${esc(tabTip(t))}">
        <span class="qb-tab-title">${esc(t.title || t.url)}</span>
        ${pinBtn}
        <span class="qb-tab-popout" data-popout="${esc(t.id)}" title="Snap to window" aria-label="Pop out tab"><svg class="qb-ico qb-ico--tab" aria-hidden="true"><use href="assets/branding/queen-chrome-icons.svg#popout"/></svg></span>
        <span class="qb-tab-fs" data-fs="${esc(t.id)}" title="Fullscreen viewport" aria-label="Fullscreen viewport"><svg class="qb-ico qb-ico--tab" aria-hidden="true"><use href="assets/branding/queen-chrome-icons.svg#tab-fs"/></svg></span>
        ${pinned ? "" : `<span class="qb-tab-close" data-close="${esc(t.id)}" aria-label="Close tab"><svg class="qb-ico qb-ico--tab" aria-hidden="true"><use href="assets/branding/queen-chrome-icons.svg#close"/></svg></span>`}
      </button>`;
      })
      .join("");
  }

  function bindTabChrome() {
    const bar = $("qb-tabs");
    if (!bar || bar.dataset.shellBound === "1") return;
    bar.dataset.shellBound = "1";
    bar.addEventListener("click", (e) => {
      const pin = e.target.closest("[data-pin]");
      if (pin) {
        e.stopPropagation();
        globalThis.QueenOS?.browser?.togglePinTab?.(pin.dataset.pin);
        return;
      }
      const pop = e.target.closest("[data-popout]");
      if (pop) {
        e.stopPropagation();
        popoutTab(pop.dataset.popout);
        return;
      }
      const fs = e.target.closest("[data-fs]");
      if (fs) {
        e.stopPropagation();
        toggleViewportFullscreen();
        return;
      }
      const close = e.target.closest("[data-close]");
      if (close) {
        e.stopPropagation();
        globalThis.QueenOS?.browser?.closeTab?.(close.dataset.close);
        return;
      }
      const tab = e.target.closest(".qb-tab");
      if (tab?.dataset.tab) {
        globalThis.QueenOS?.browser?.activateTab?.(tab.dataset.tab);
      }
    });
  }

  function popoutTab(tabId) {
    const doc = globalThis.QueenOS?.browser?.doc;
    const tab = (doc?.tabs || []).find((t) => t.id === tabId);
    if (!tab || tab.pinned) return;
    const entry = shell.panes.get(tabId);
    const url = entry?.frame?.src || tab.url;
    const w = window.open(
      `/world/queen-popout.html?tab=${encodeURIComponent(tabId)}&url=${encodeURIComponent(url)}&title=${encodeURIComponent(tab.title || "Queen")}`,
      `queen-tab-${tabId}`,
      "noopener=no,width=1100,height=720,menubar=no,toolbar=no,location=no,status=no",
    );
    if (!w) return;
    shell.popouts.set(tabId, w);
    entry?.pane?.classList.add("popped");
    const next = (doc.tabs || []).find((t) => t.id !== tabId && !shell.popouts.has(t.id));
    if (next) globalThis.QueenOS?.browser?.activateTab?.(next.id);
  }

  function attachTab(tabId) {
    const w = shell.popouts.get(tabId);
    if (w && !w.closed) w.close();
    shell.popouts.delete(tabId);
    const entry = shell.panes.get(tabId);
    entry?.pane?.classList.remove("popped");
    if (tabId) globalThis.QueenOS?.browser?.activateTab?.(tabId);
  }

  function toggleViewportFullscreen() {
    const viewport = document.querySelector(".qb-viewport");
    if (!viewport) return;
    shell.viewportFs = !shell.viewportFs;
    document.body.classList.toggle("qw-viewport-fs", shell.viewportFs);
    if (shell.viewportFs) viewport.requestFullscreen?.().catch(() => {});
    else if (document.fullscreenElement) document.exitFullscreen?.();
  }

  function cycleTabs(reverse) {
    const doc = globalThis.QueenOS?.browser?.doc;
    const ids = (doc?.tabs || []).map((t) => t.id).filter((id) => !shell.popouts.has(id));
    if (ids.length < 2) return;
    const cur = doc.tabs.find((t) => t.active)?.id;
    let idx = ids.indexOf(cur);
    idx = reverse ? (idx - 1 + ids.length) % ids.length : (idx + 1) % ids.length;
    globalThis.QueenOS?.browser?.activateTab?.(ids[idx]);
  }

  function activateStart() {
    const doc = globalThis.QueenOS?.browser?.doc;
    const start =
      (doc?.tabs || []).find((t) => t.pinned || t.role === "desktop" || t.role === "start") || doc?.tabs?.[0];
    if (start) globalThis.QueenOS?.browser?.activateTab?.(start.id);
  }

  function escMenu(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function fetchDesktopDoc() {
    if (shell.desktopDoc) return shell.desktopDoc;
    try {
      const r = await fetch("/api/queen-desktop", { cache: "no-store" });
      shell.desktopDoc = await r.json();
    } catch {
      shell.desktopDoc = { classic_programs: [], host_programs: [] };
    }
    return shell.desktopDoc;
  }

  function startProgramsFromDoc(doc) {
    if (!doc) return [];
    if (doc.desktop_icons_in_start && Array.isArray(doc.start_programs) && doc.start_programs.length) {
      return doc.start_programs;
    }
    return doc.classic_programs || [];
  }

  function bindStartItem(btn) {
    btn.addEventListener("click", () => {
      const url = btn.dataset.url;
      if (url) {
        globalThis.QueenOS?.browser?.newTab?.(url);
        toggleStartMenu(false);
      }
    });
    btn.addEventListener("dragstart", (ev) => {
      const url = btn.dataset.queenProgramUrl || btn.dataset.url;
      const name = btn.dataset.queenProgramName || btn.dataset.name || "Program";
      if (!url) return;
      ev.dataTransfer.setData("text/uri-list", url);
      ev.dataTransfer.setData(
        "application/x-queen-program",
        JSON.stringify({ url, name }),
      );
      ev.dataTransfer.effectAllowed = "copy";
    });
  }

  function renderStartProgramButton(p) {
    return (
      `<button type="button" class="qb-start-item" draggable="true"` +
      ` data-url="${escMenu(p.url || p.exec || "")}"` +
      ` data-queen-program-url="${escMenu(p.url || p.exec || "")}"` +
      ` data-queen-program-name="${escMenu(p.name)}"` +
      ` data-name="${escMenu(p.name)}">` +
      `<span>${escMenu(p.name)}</span></button>`
    );
  }

  function renderStartMenuItems(programs, folders) {
    const body = $("qb-start-menu-body");
    if (!body) return;
    const q = ($("qb-start-search")?.value || "").trim().toLowerCase();
    const folderList = Array.isArray(folders) && folders.length ? folders : null;
    if (folderList) {
      body.innerHTML = folderList
        .map((folder) => {
          const kids = (folder.children || []).filter(
            (p) => !q || (p.name || "").toLowerCase().includes(q) || (folder.title || "").toLowerCase().includes(q),
          );
          if (!kids.length && q && !(folder.title || "").toLowerCase().includes(q)) return "";
          return (
            `<section class="qb-start-folder" data-folder="${escMenu(folder.id)}">` +
            `<h3 class="qb-start-folder-title">${escMenu(folder.title)}</h3>` +
            `<div class="qb-start-folder-items">${kids.map(renderStartProgramButton).join("")}</div>` +
            `</section>`
          );
        })
        .join("");
    } else {
      const list = (programs || []).filter((p) => !q || (p.name || "").toLowerCase().includes(q));
      body.innerHTML = list.map(renderStartProgramButton).join("");
    }
    body.querySelectorAll(".qb-start-item").forEach(bindStartItem);
  }

  async function toggleStartMenu(force, side) {
    const menu = $("qb-start-menu");
    if (!menu) return;
    if (side) shell.startSide = side;
    shell.startOpen = force !== undefined ? force : !shell.startOpen;
    menu.hidden = !shell.startOpen;
    menu.setAttribute("aria-hidden", shell.startOpen ? "false" : "true");
    $("qb-start-classic")?.setAttribute("aria-expanded", shell.startOpen ? "true" : "false");
    if (shell.startOpen) {
      const doc = await fetchDesktopDoc();
      renderStartMenuItems(startProgramsFromDoc(doc), doc.start_menu_folders);
      setTimeout(() => $("qb-start-search")?.focus(), 60);
    }
  }

  function applyStartButtonMode(browserDoc) {
    const bootOs = !!(browserDoc?.boot_os || document.body?.dataset?.queenBootOs === "1");
    const mode = bootOs ? "full" : "classic";
    const pill = $("qb-start-pill");
    if (pill) pill.dataset.mode = mode;
    document.body.dataset.queenBootOs = bootOs ? "1" : "0";
    document.body.dataset.queenStartButton = mode;
    shell.startSide = "classic";
    const classic = $("qb-start-classic");
    const secured = $("qb-start-secured");
    const full = $("qb-start");
    secured?.setAttribute("hidden", "");
    if (bootOs) {
      classic?.setAttribute("hidden", "");
      full?.removeAttribute("hidden");
    } else {
      classic?.removeAttribute("hidden");
      full?.setAttribute("hidden", "");
    }
  }

  function onShellMessage(ev) {
    if (ev.origin !== location.origin && !isLoopbackOrigin(ev.origin)) return;
    const data = ev.data;
    if (!data || typeof data !== "object" || data.type !== "queen:shell") return;
    const action = data.action;
    if (!SHELL_ACTIONS.has(action)) return;
    if (action === "attach_tab") {
      attachTab(data.tab_id);
      return;
    }
    let url = data.url;
    if (action === "home") url = startUrl();
    if (action === "command") url = document.body?.dataset?.queenCommand || "http://127.0.0.1:9477/command";
    if (!isSafeShellUrl(url)) {
      const status = $("qb-status");
      if (status) status.textContent = "Blocked hostile shell message";
      return;
    }
    if (action === "navigate") globalThis.QueenOS?.browser?.navigate?.(url);
    if (action === "new_tab" || action === "command") globalThis.QueenOS?.browser?.newTab?.(url);
    if (action === "home") globalThis.QueenOS?.browser?.navigate?.(url);
    if (action === "open_window" || action === "open_program" || action === "desktop_window") {
      forwardOpenWindow(data.item || { url, name: data.title || data.name || "Program", icon: data.icon });
    }
    if (action === "dock" && data.dock) {
      const dockUrl = url || `${location.origin}/world/?dock=${encodeURIComponent(data.dock)}`;
      globalThis.QueenOS?.world?.setDockTab?.(data.dock);
      globalThis.QueenOS?.browser?.navigate?.(`/world/?dock=${encodeURIComponent(data.dock)}`);
      if (!globalThis.QueenOS?.world?.setDockTab) {
        globalThis.QueenOS?.browser?.newTab?.(dockUrl);
      }
    }
  }

  function desktopFrame() {
    const startTab = (globalThis.QueenOS?.browser?.doc?.tabs || []).find(
      (t) => t.role === "start" || t.role === "desktop" || (t.url || "").includes("queen-desktop"),
    );
    const tabId = startTab?.id;
    if (!tabId) return null;
    const entry = shell.panes.get(tabId);
    return entry?.frame?.contentWindow || null;
  }

  function forwardOpenWindow(item) {
    const url = item?.url;
    if (!isSafeShellUrl(url)) return;
    const win = desktopFrame();
    if (win) {
      try {
        win.postMessage({ type: "queen:desktop", action: "open_window", item }, location.origin);
        return;
      } catch (_) {}
    }
    globalThis.QueenOS?.browser?.newTab?.(url);
  }

  function handleLaunchQuery() {
    try {
      const params = new URLSearchParams(location.search);
      const launch = params.get("launch");
      if (!launch || !isSafeShellUrl(launch)) return;
      const title = params.get("title") || "Program";
      setTimeout(() => forwardOpenWindow({ url: launch, name: title, id: launch }), 400);
    } catch (_) {}
  }

  function wireSecurity() {
    window.addEventListener("message", onShellMessage);
    window.addEventListener("message", onDesktopMessage);
    document.addEventListener("securitypolicyviolation", (e) => {
      const status = $("qb-status");
      if (status) status.textContent = `CSP blocked: ${e.blockedURI || e.violatedDirective}`;
    });
  }

  function isCadChord(e) {
    const del = e.key === "Delete" || e.key === "Del";
    const esc = e.key === "Escape";
    if (e.ctrlKey && e.altKey && del) return true;
    if (e.ctrlKey && e.shiftKey && esc) return true;
    return false;
  }

  function wireKeyboard() {
    document.addEventListener("keydown", (e) => {
      if (isCadChord(e)) {
        e.preventDefault();
        e.stopPropagation();
        engageKeyboardSovereign();
        openCadRescue();
        return;
      }
      if (e.altKey && e.key === "Tab") {
        e.preventDefault();
        e.stopPropagation();
        cycleTabs(e.shiftKey);
        return;
      }
      if (e.altKey && e.key === "Enter") {
        e.preventDefault();
        toggleViewportFullscreen();
        return;
      }
      if (e.key === "F11") {
        e.preventDefault();
        toggleViewportFullscreen();
        return;
      }
      if (e.key === "F5") {
        e.preventDefault();
        $("qb-reload")?.click();
      }
    }, true);
    document.addEventListener("fullscreenchange", () => {
      shell.viewportFs = !!document.fullscreenElement;
      document.body.classList.toggle("qw-viewport-fs", shell.viewportFs);
    });
  }

  function wireStartButton() {
    $("qb-start")?.addEventListener("click", () => {
      activateStart();
      toggleStartMenu(true, "classic");
    });
    $("qb-start-classic")?.addEventListener("click", () => toggleStartMenu(undefined, "classic"));
    $("qb-start-search")?.addEventListener("input", async () => {
      const doc = await fetchDesktopDoc();
      renderStartMenuItems(startProgramsFromDoc(doc), doc.start_menu_folders);
    });
    document.addEventListener("click", (ev) => {
      if (!shell.startOpen) return;
      if (ev.target.closest(".qb-start-menu") || ev.target.closest(".qb-start-pill")) return;
      toggleStartMenu(false);
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && shell.startOpen) toggleStartMenu(false);
    });
    fetchDesktopDoc().then(() => {
      applyStartButtonMode(globalThis.QueenOS?.browser?.doc?.doc || globalThis.QueenOS?.browser?.doc || {});
    });
    $("qb-compat-pill")?.addEventListener("click", async () => {
      const modes = ["auto", "modern", "legacy_secure", "archaeology", "future"];
      const doc = globalThis.QueenOS?.browser?.doc?.doc || globalThis.QueenOS?.browser?.doc;
      const tab = (doc?.tabs || []).find((t) => t.active);
      if (!tab) return;
      const cur = tab.compat_mode || "auto";
      const next = modes[(modes.indexOf(cur) + 1) % modes.length];
      const r = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "set_compat", tab_id: tab.id, compat_mode: next }),
      });
      const j = await r.json();
      if (j.ok) {
        await globalThis.QueenOS?.browser?.refresh?.();
        const t = (j.status?.tabs || []).find((x) => x.id === tab.id);
        if (t) loadTab(t.id, t.url, { compatMode: t.compat_mode, compat: t.compat_profile });
      }
    });
  }

  function applyDesktopEmbedMode() {
    const params = new URLSearchParams(location.search);
    if (params.get("desktop_embed") !== "1") return;
    document.body.classList.add("qw-desktop-embed");
    $("qb-chrome")?.setAttribute("hidden", "");
    $("qb-chrome-restore")?.setAttribute("hidden", "");
    $("qm-threat-bar")?.setAttribute("hidden", "");
    const plate = $("qb-field-plate");
    if (plate) plate.setAttribute("aria-hidden", "true");
  }

  function applyShellMode() {
    document.body.classList.add("qw-browser-shell");
    applyDesktopEmbedMode();
    const strip = document.createElement("span");
    strip.className = "qb-security-strip";
    strip.id = "qb-security-strip";
    strip.textContent = "KILROY · ZNetwork hooks · Queen Browser shell";
    $("qb-gate-strip")?.prepend(strip);
  }

  function onDesktopMessage(ev) {
    if (ev.origin !== location.origin && !isLoopbackOrigin(ev.origin)) return;
    const data = ev.data;
    if (!data || data.type !== "queen:desktop") return;
    if (data.action === "toggle_start") {
      toggleStartMenu(undefined, data.side || "classic");
    }
  }

  function patchBrowser(browserApi) {
    if (!browserApi || browserApi._shellPatched) return;
    browserApi._shellPatched = true;

    const origRender = browserApi.renderTabs;
    if (origRender) {
      browserApi.renderTabs = function renderTabsShell(doc) {
        const bar = $("qb-tabs");
        if (bar) {
          bar.innerHTML = decorateTabsRender("", doc.tabs);
          bindTabChrome();
        }
      };
    }

    const origLoad = browserApi.loadFrame;
    browserApi.loadFrame = function loadFrameShell(url, opts) {
      const root = browserApi.doc;
      const active = (root?.tabs || []).find((t) => t.active) || root?.tabs?.[0];
      if (active) {
        loadTab(active.id, url, {
          proxy: opts?.proxy,
          compat: opts?.compat || active.compat_profile,
          compatMode: opts?.compatMode || active.compat_mode,
        });
      }
      const statusEl = $("qb-status");
      if (statusEl) statusEl.textContent = opts?.proxy ? `Proxy · ${url}` : url;
      const bar = $("qb-url");
      if (bar && document.activeElement !== bar) bar.value = url || "";
    };

    const origActivate = browserApi.activateTab;
    if (origActivate) {
      browserApi.activateTab = async function activateTabShell(tabId) {
        const out = await origActivate(tabId);
        if (out?.ok !== false) {
          const tab = (browserApi.doc?.tabs || []).find((t) => t.id === tabId);
          if (tab && !shell.popouts.has(tabId)) loadTab(tabId, tab.url);
        }
        return out;
      };
    }

    const origRefresh = browserApi.browserRefresh;
    if (origRefresh) {
      browserApi.browserRefresh = async function browserRefreshShell() {
        const doc = await origRefresh();
        browserApi.renderTabs(doc);
        applyStartButtonMode(doc);
        await fixDesktopEmbedTab(browserApi, doc);
        const active = (doc.tabs || []).find((t) => t.active) || doc.tabs?.[0];
        if (active && !shell.popouts.has(active.id)) loadTab(active.id, active.url);
        return doc;
      };
    }
  }

  async function fixDesktopEmbedTab(browserApi, doc) {
    if (!document.body.classList.contains("qw-desktop-embed")) return;
    const tabs = doc?.tabs || [];
    const active = tabs.find((t) => t.active) || tabs[0];
    if (!active || (active.role !== "desktop" && active.role !== "start")) return;
    const alt = tabs.find((t) => t.role === "files") || tabs.find((t) => !t.pinned && t.role !== "desktop" && t.role !== "start");
    if (alt && browserApi.activateTab) {
      await browserApi.activateTab(alt.id);
      return;
    }
    if (browserApi.newTab) await browserApi.newTab("https://duckduckgo.com/");
  }

  async function loadShieldPolicy() {
    try {
      const r = await fetch("/api/queen-page-shields", { cache: "no-store" });
      const doc = await r.json();
      shell.autoProxyExternal = doc?.policy?.auto_proxy_external !== false;
    } catch (_) {
      shell.autoProxyExternal = true;
    }
  }

  function init(browserFacade) {
    if (shell.ready) return;
    loadShieldPolicy();
    applyShellMode();
    ensureViewport();
    bindTabChrome();
    wireSecurity();
    wireKeyboard();
    wireZNetworkHooks();
    wireStartButton();
    globalThis.QueenBookmarksFlyout?.init?.();
    if (browserFacade) patchBrowser(browserFacade);
    handleLaunchQuery();
    shell.ready = true;
  }

  globalThis.QueenBrowserShell = {
    init,
    loadTab,
    popoutTab,
    attachTab,
    activateStart,
    toggleStartMenu,
    applyStartButtonMode,
    toggleViewportFullscreen,
    cycleTabs,
    decorateTabsRender,
  };
})();