/**
 * Field Host Desktop — AmmoOS 2.0: desktop icons, taskbar, optional six-tool wall, shell windows.
 */
(function () {
  "use strict";

  const state = { data: null, keysEngaged: false, selected: null, internetCleanDone: false };

  function apiUrl(path) {
    if (global.H7Api) return global.H7Api(path);
    if (global.H7Base) return global.H7Base(path);
    return path;
  }

  function pageUrl(path) {
    if (global.H7Page) return global.H7Page(path);
    if (global.HOSTESS7_PAGES_BASE && String(path || "").startsWith("/")) {
      return global.HOSTESS7_PAGES_BASE + path;
    }
    return path;
  }

  function toast(msg) {
    const el = document.getElementById("hd-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(function () { el.classList.remove("show"); }, 2600);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const QUEEN_ICON = "/assets/ammoos-field-48.png";
  function applyWallpaper(wp) {
    const key = String(wp || "none").toLowerCase();
    const root = document.documentElement;
    root.dataset.ammoosWarehouse = "";
    root.dataset.wallpaper = key === "none" || key === "flat" ? "none" : key;
    const deco = document.getElementById("hd-warehouse-deco");
    if (deco) deco.hidden = true;
    const label = document.getElementById("hd-wall-label");
    if (label) label.textContent = "Field One · AmmoOS · Layer −1";
  }

  const DESKTOP_DEFAULT_IDS = [
    "view",
    "queen-terminal",
    "mspaint",
    "field-popcorn",
    "ammocode",
    "hostess7-folder",
    "queen-browser",
    "field-broadcaster",
    "queen-gameroom",
    "queen-chips",
    "nexus-compatibility",
  ];
  const DESKTOP_PIN_KEY = "field-desktop-pins-v1";
  const DESKTOP_ICON_PX = 96;

  function iconHtml(app, size) {
    size = size || DESKTOP_ICON_PX;
    const src = app.icon_url || (pagesRuntime() ? pagesAssetBase() + "/queen-prog-" + (app.icon || app.id || "view").replace(/^queen-prog-/, "") + ".png" : null) || QUEEN_ICON;
    if (pagesRuntime() && app.icon_url) {
      return '<img src="' + esc(src) + '" alt="" width="' + size + '" height="' + size + '" class="hd-app-icon" loading="lazy" decoding="async" onerror="this.src=\'' + esc(pagesAssetBase() + "/ammoos-field-48.png") + '\'" />';
    }
    const QIE = window.QueenIconEngine;
    if (QIE?.programIconHtml && !pagesRuntime()) {
      return QIE.programIconHtml(app, size, { base: pagesRuntime() ? pagesAssetBase() + "/" : QIE.PANEL_ICONS });
    }
    if (app.live) {
      return (
        '<span class="hd-icon-live-wrap">' +
        '<img src="' + esc(src) + '" alt="" width="' + size + '" height="' + size + '" class="hd-app-icon hd-app-icon--live" loading="lazy" decoding="async" />' +
        '<span class="hd-live-badge">LIVE</span></span>'
      );
    }
    return '<img src="' + esc(src) + '" alt="" width="' + size + '" height="' + size + '" class="hd-app-icon" loading="lazy" decoding="async" />';
  }

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!window.HOSTESS7_PAGES_BASE;
  }

  function panelOrigin() {
    if (pagesRuntime()) return window.HOSTESS7_PAGES_BASE || "";
    return "http://127.0.0.1:9477";
  }

  function pagesAssetBase() {
    if (pagesRuntime()) return (window.HOSTESS7_PAGES_BASE || "/Hostess7") + "/assets";
    return "/assets";
  }

  function gnuTerminalExec() {
    if (pagesRuntime()) {
      return (window.HOSTESS7_PAGES_BASE || "/Hostess7") + "/field-gnu-terminal-embed.html";
    }
    return panelOrigin() + "/field-gnu-terminal-embed.html";
  }

  function inQueenFrame() {
    try {
      return window.parent !== window;
    } catch {
      return window.parent !== window;
    }
  }

  function queenShell(action, url) {
    const base = panelOrigin();
    const full =
      url && url.startsWith("/") ? base + url : url && url.startsWith("http") ? url : base + "/desktop/";
    try {
      window.parent.postMessage({ type: "queen:shell", action: action, url: full }, "*");
      return true;
    } catch {
      return false;
    }
  }

  function shellLaunch(app) {
    if (window.NexusFieldShell?.launch) {
      window.NexusFieldShell.launch(app);
      return true;
    }
    return false;
  }

  function launchApp(app) {
    if (window.FieldQueenNav?.isStandaloneQueenApp?.(app)) {
      window.FieldQueenNav.openStandalone(app);
      return;
    }
    if (window.FieldQueenNav?.needsEnsureLaunch?.(app)) {
      window.FieldQueenNav.ensureProgramLaunch(app).then(function (doc) {
        if (doc && doc.ok === false) {
          toast("Program unavailable · " + (app.name || app.id));
          return;
        }
        launchAppInner(app);
      });
      return;
    }
    launchAppInner(app);
  }

  function launchAppInner(app) {
    let exec = app.exec || app.url || "";
    if (window.FieldQueenNav?.secureUrl) {
      exec = window.FieldQueenNav.secureUrl(exec, { id: app.id });
    }
    if (app.shell !== false && (app.shell || exec.includes("embed=1") || app.view)) {
      if (shellLaunch(app)) {
        toast("Opened · " + (app.name || exec));
        return;
      }
    }
    // Always route web through Queen Browser — never a host browser.
    if (inQueenFrame() && exec.startsWith("/")) {
      const action = exec.includes("/desktop") || exec.includes("/field") ? "home" : "new_tab";
      if (queenShell(action, exec)) {
        toast("Opened in Queen · " + (app.name || exec));
        window.FieldStartbar?.trackRunning?.(app);
        return;
      }
    }
    if (inQueenFrame() && /^https?:\/\//i.test(exec)) {
      if (queenShell("new_tab", exec)) {
        toast("Opened in Queen tab");
        return;
      }
    }
    if (shellLaunch(app)) {
      toast("Opened · " + (app.name || exec));
      return;
    }
    window.FieldStartbar?.launchApp?.(app);
    window.FieldStartbar?.trackRunning?.(app);
  }

  function loadDesktopPins() {
    try {
      const raw = localStorage.getItem(DESKTOP_PIN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveDesktopPins(ids) {
    try {
      localStorage.setItem(DESKTOP_PIN_KEY, JSON.stringify(ids));
    } catch (_) { /* ignore */ }
  }

  function normalizeDesktopApp(app, id) {
    if (!app) return null;
    const row = Object.assign({}, app);
    if (id === "queen-terminal") {
      row.exec = gnuTerminalExec();
      row.name = "AmmoOS Terminal";
      row.hint = row.hint || "GNU Terminal · AmmoOS panel · Layer 0";
      row.os_layer = 0;
      row.category = "AmmoOS · Layer 0";
    }
    if (id === "field-popcorn") {
      row.icon = "queen-prog-popcorn";
      row.icon_url = pagesAssetBase() + "/queen-prog-popcorn.png";
      row.os_layer = 0;
      row.exec = row.exec || pageUrl("/field-popcorn");
    }
    if (id === "ammocode") {
      row.icon = "queen-prog-ammocode";
      row.icon_url = pagesAssetBase() + "/queen-prog-ammocode.png";
      row.os_layer = 0;
      row.exec = row.exec || pageUrl("/ammocode");
      row.name = "AmmoCode";
      row.hint = row.hint || "Syntax editor · Layer 0";
    }
    if (id === "hostess7-folder") {
      row.kind = "desktop_folder";
      row.icon = "queen-prog-hostess";
      row.icon_url = pagesAssetBase() + "/queen-prog-hostess.png";
      row.os_layer = 0;
    }
    return row;
  }

  function isDesktopFolder(app) {
    return !!(app && (app.kind === "desktop_folder" || (app.folder_children && app.folder_children.length)));
  }

  function openDesktopFolder(app) {
    const kids = app.folder_children || [];
    if (!kids.length) {
      toast("Folder empty · " + (app.name || app.id));
      return;
    }
    let pop = document.getElementById("hd-folder-pop");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "hd-folder-pop";
      pop.className = "hd-folder-pop";
      pop.setAttribute("role", "dialog");
      pop.setAttribute("aria-label", app.name || "Folder");
      document.body.appendChild(pop);
    }
    pop.innerHTML =
      '<div class="hd-folder-head"><strong>' + esc(app.name || "Folder") + '</strong>' +
      '<button type="button" class="hd-folder-close" aria-label="Close">×</button></div>' +
      '<div class="hd-folder-grid">' +
      kids.map(function (child) {
        return (
          '<button type="button" class="hd-folder-item" data-app-id="' + esc(child.id) + '">' +
          iconHtml(child, 48) +
          '<span>' + esc(child.name) + "</span></button>"
        );
      }).join("") +
      "</div>";
    pop.classList.add("open");
    pop.querySelector(".hd-folder-close")?.addEventListener("click", function () {
      pop.classList.remove("open");
    });
    pop.querySelectorAll(".hd-folder-item").forEach(function (btn) {
      btn.addEventListener("dblclick", function () {
        const cid = btn.dataset.appId;
        const child = kids.find(function (c) { return c.id === cid; });
        if (child) {
          pop.classList.remove("open");
          openDesktopApp(child);
        }
      });
    });
  }

  function desktopDefaultFallback() {
    const base = pagesRuntime() ? (window.HOSTESS7_PAGES_BASE || "/Hostess7") : "";
    const assets = pagesAssetBase();
    const world = pagesRuntime() ? base + "/queen" : "http://127.0.0.1:9481/world";
    const rows = [
      { id: "view", name: "View", hint: "Files & folders", icon: "queen-prog-view", exec: base + "/queen/view.html", icon_url: assets + "/queen-prog-view.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "queen-terminal", name: "AmmoOS Terminal", hint: "Field GNU Terminal · code preview · truth · Layer 0", icon: "queen-prog-terminal", exec: gnuTerminalExec(), icon_url: assets + "/queen-prog-terminal.png", pinned: true, shell: true, os_layer: 0, category: "AmmoOS · Layer 0" },
      { id: "field-popcorn", name: "Popcorn", hint: "Media player · Layer 0", icon: "queen-prog-popcorn", exec: base + "/field-popcorn", icon_url: assets + "/queen-prog-popcorn.png", pinned: true, shell: true, os_layer: 0, category: "AmmoOS · Layer 0" },
      { id: "ammocode", name: "AmmoCode", hint: "Syntax editor · Layer 0", icon: "queen-prog-ammocode", exec: base + "/ammocode", icon_url: assets + "/queen-prog-ammocode.png", pinned: true, shell: true, os_layer: 0, category: "AmmoOS · Layer 0" },
      { id: "hostess7-folder", name: "Hostess 7", kind: "desktop_folder", hint: "Hostess 7 panels", icon: "queen-prog-hostess", icon_url: assets + "/queen-prog-hostess.png", pinned: true, os_layer: 0, category: "AmmoOS · Layer 0", folder_children: [] },
      { id: "queen-browser", name: "Queen Browser", hint: "Queen web engine", icon: "queen-prog-browser", exec: base + "/queen/browser.html", icon_url: assets + "/queen-prog-browser.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "field-broadcaster", name: "Broadcaster", hint: "OBS rebranded · Layer 0 · Final_Eye Ear Mouth", icon: "queen-prog-broadcaster", exec: base + "/field-broadcaster", icon_url: assets + "/queen-prog-broadcaster.png", pinned: true, shell: true, live: true, os_layer: 0, ensure_api: "/api/field-broadcaster/launch", category: "AmmoOS · Media" },
      { id: "queen-gameroom", name: "Game Room", hint: "Queen Game Room · cartridges · arcade", icon: "queen-prog-gameroom", exec: world + "/queen-game-room.html", icon_url: assets + "/queen-prog-gameroom.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "queen-chips", name: "CHIPS", hint: "Emulators · chip cores · combinatronic", icon: "queen-prog-chips", exec: world + "/queen-chips-cores.html", icon_url: assets + "/queen-prog-chips.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "nexus-compatibility", name: "Compatibility Layers", hint: "Wine · DOS · retro layers", icon: "queen-prog-g16", exec: base + "/compatibility", icon_url: assets + "/queen-prog-g16.png", pinned: true, shell: true, category: "NEXUS · Tools" },
    ];
    return DESKTOP_DEFAULT_IDS.map(function (id) {
      return normalizeDesktopApp(rows.find(function (r) { return r.id === id; }), id);
    }).filter(Boolean);
  }

  function desktopIconList(doc) {
    const programs = doc?.programs || [];
    const byId = {};
    programs.forEach(function (p) {
      if (p?.id) byId[p.id] = p;
    });
    const fromApi = Array.isArray(doc?.desktop_icons) ? doc.desktop_icons : [];
    const serverIds = new Set(fromApi.map(function (p) { return p.id; }).filter(Boolean));
    const local = loadDesktopPins();
    if (Array.isArray(local)) {
      local.forEach(function (id) { serverIds.add(id); });
    }
    const ordered = [];
    fromApi.forEach(function (p) {
      if (p?.id && !ordered.find(function (x) { return x.id === p.id; })) ordered.push(p.id);
    });
    DESKTOP_DEFAULT_IDS.forEach(function (id) {
      if (!ordered.includes(id) && (serverIds.has(id) || byId[id])) ordered.push(id);
    });
    serverIds.forEach(function (id) {
      if (!ordered.includes(id)) ordered.push(id);
    });
    const list = ordered.map(function (id) {
      const app = byId[id] || fromApi.find(function (p) { return p.id === id; });
      return normalizeDesktopApp(app, id);
    }).filter(Boolean);
    if (list.length) {
      return list.map(function (app) {
        return Object.assign({}, app, { pinned: serverIds.has(app.id) || app.pinned });
      });
    }
    return desktopDefaultFallback();
  }

  function toggleDesktopPin(app) {
    if (!app?.id) return;
    const list = desktopIconList(state.data || {});
    const ids = list.map(function (p) { return p.id; });
    const idx = ids.indexOf(app.id);
    if (idx >= 0) ids.splice(idx, 1);
    else ids.push(app.id);
    saveDesktopPins(ids);
    renderDesktopIcons(state.data);
    toast(idx >= 0 ? "Unpinned · " + (app.name || app.id) : "Pinned to desktop · " + (app.name || app.id));
  }

  function openDesktopApp(app) {
    if (app.id === "queen-browser") openQueenBrowserClean();
    else if (app.id === "queen-terminal") launchGnuTerminal(app);
    else launchApp(app);
  }

  function renderDesktopIcons(doc) {
    const grid = document.getElementById("hd-icons");
    if (!grid) return;

    grid.innerHTML = "";
    grid.className = "hd-icons hd-icons--classic";

    const icons = desktopIconList(doc);
    icons.forEach(function (app) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "hd-icon hd-icon-cartoony" +
        (app.pinned ? " pinned" : "") +
        (isDesktopFolder(app) ? " hd-icon--folder" : "") +
        (app.os_layer === 0 ? " hd-icon--layer0" : "");
      btn.dataset.appId = app.id;
      btn.title = (app.hint || app.name) + (app.os_layer === 0 ? " · Layer 0" : "");

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "hd-icon-pin";
      pinBtn.setAttribute("aria-label", app.pinned ? "Unpin from desktop" : "Pin to desktop");
      pinBtn.textContent = "📌";
      pinBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        toggleDesktopPin(app);
      });

      const iconWrap = document.createElement("div");
      iconWrap.className = "hd-icon-glyph";
      iconWrap.innerHTML = iconHtml(app, DESKTOP_ICON_PX);

      const label = document.createElement("span");
      label.className = "hd-icon-label";
      label.textContent = app.name;

      btn.appendChild(pinBtn);
      btn.appendChild(iconWrap);
      btn.appendChild(label);

      btn.addEventListener("click", function (e) {
        e.stopImmediatePropagation();
        grid.querySelectorAll(".hd-icon").forEach(function (b) { b.classList.remove("selected"); });
        btn.classList.add("selected");
        state.selected = app;
      });

      btn.addEventListener("dblclick", function (e) {
        e.stopImmediatePropagation();
        if (isDesktopFolder(app)) openDesktopFolder(app);
        else openDesktopApp(app);
      });

      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        if (window.FieldStartbar?.openCtx) {
          const items = [
            { label: "Open", action: "desktop-open" },
            { label: "Open Queen window", action: "desktop-queen" },
            { label: app.pinned ? "Unpin from desktop" : "Pin to desktop", action: "desktop-pin" },
            { label: "Pin to taskbar", action: "pin" },
            { label: "Properties", action: "menu-props" },
          ];
          if (global.FieldDos40Menu?.contextExtras) {
            items.push.apply(items, global.FieldDos40Menu.contextExtras());
          }
          window.FieldStartbar.openCtx(ev.clientX, ev.clientY, items, app, ev);
          return;
        }
        toast("Right-click · " + app.name);
      });

      grid.appendChild(btn);
    });

    grid.classList.remove("hidden");
  }

  function launchGnuTerminal(app) {
    const exec = gnuTerminalExec();
    const termApp = Object.assign({}, app || {}, {
      id: "queen-terminal",
      exec: exec,
      shell: true,
      name: "AmmoOS Terminal",
      os_layer: 0,
      category: "AmmoOS · Shell",
    });
    if (shellLaunch(termApp)) {
      toast("AmmoOS Terminal · GNU panel");
      return;
    }
    if (pagesRuntime()) {
      window.location.href = pageUrl(exec);
      return;
    }
    launchApp(termApp);
  }

  function openQueenBrowserClean() {
    const base = pagesRuntime() ? (window.HOSTESS7_PAGES_BASE || "/Hostess7") : "";
    const exec = base
      ? base + "/queen/browser.html"
      : "http://127.0.0.1:9481/world/browser.html";
    const app = {
      id: "queen-browser",
      name: "Queen Browser",
      exec: exec,
      shell: true,
      icon_url: pagesAssetBase() + "/queen-prog-browser.png",
    };
    if (window.FieldScreenLayers?.openQueen) {
      window.FieldScreenLayers.openQueen();
      toast("Queen Browser · own browser space");
      return;
    }
    if (shellLaunch(app)) {
      toast("Queen Browser · own browser space");
      return;
    }
    toast("Queen Browser unavailable");
  }

  function engageKeyboardSovereign() {
    if (state.keysEngaged) return;
    fetch(apiUrl("/api/field-keyboard-sovereign/engage"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      credentials: "same-origin",
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok !== false) state.keysEngaged = true;
      })
      .catch(function () {});
  }

  function releaseKeyboardSovereign(reason) {
    if (!state.keysEngaged) return;
    const body = JSON.stringify({ reason: reason || "pagehide" });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(apiUrl("/api/field-keyboard-sovereign/release"), body);
    } else {
      fetch(apiUrl("/api/field-keyboard-sovereign/release"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
        credentials: "same-origin",
        keepalive: true,
      }).catch(function () {});
    }
    state.keysEngaged = false;
  }

  function fillViewport() {
    // Only style classes for "desktop mode". Do NOT auto requestFullscreen.
    // Clicking should launch apps, not toggle FS. We provide a separate button.
    const root = document.documentElement;
    root.classList.add("nfs-fullscreen-desktop", "nfs-kiosk");
  }

  function toggleFullscreenDesktop() {
    const root = document.documentElement;
    const isFs = !!document.fullscreenElement;
    if (isFs) {
      document.exitFullscreen && document.exitFullscreen().catch(() => {});
      root.classList.remove("nfs-kiosk");
    } else {
      root.classList.add("nfs-kiosk");
      if (root.requestFullscreen) {
        root.requestFullscreen({ navigationUI: "hide" }).catch(() => {});
      }
    }
  }

  function applyDesktop(doc) {
    state.data = doc;
    try { global.__H7_DESKTOP_DOC__ = doc; } catch (_) {}
    document.documentElement.dataset.osTheme = doc.theme || "ammoos";
    document.documentElement.dataset.fieldScreenLayer = "-1";
    document.documentElement.dataset.fieldLayer = "-1";
    global.FieldScreenLayers?.switchTo?.(-1);
    applyWallpaper(doc?.shell?.settings?.wallpaper || "none");
    renderDesktopIcons(doc);
  }

  function runInternetCleanIfDefault(policy) {
    policy = policy || {};
    const on =
      policy.internet_clean_on_boot !== false &&
      (policy.auto_import_bookmarks !== false || policy.secure_bookmarks_default !== false);
    if (!on || state.internetCleanDone || pagesRuntime()) return;
    state.internetCleanDone = true;
    fetch(apiUrl("/api/hostess7/internet-clean"), {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(function (r) { return r.json(); })
      .then(function (doc) {
        if (doc && doc.ok !== false) {
          const s = doc.summary || {};
          const n = s.bookmarks_secured || 0;
          const q = s.telemetry_quarantined || 0;
          if (n || q) toast("Internet clean · " + n + " secure bookmarks · " + q + " telemetry stripped");
        }
      })
      .catch(function () {});
  }

  function mountStartbar(doc) {
    const sb = document.getElementById("fsb-mount");
    if (!sb || !window.FieldStartbar?.mount) return false;
    try {
      window.FieldStartbar.mount(sb, doc);
      return !!document.getElementById("fsb-start");
    } catch (_) {
      return false;
    }
  }

  function mountDesktopChrome(doc) {
    const policy = doc?.policy || {};
    mountStartbar(doc);

    try {
      const mon = document.getElementById("hd-monitor");
      const showWall = policy.six_tool_wall === true && policy.six_tool_wall_on_boot !== false;
      if (mon) {
        mon.classList.add("hd-monitor--hidden");
        mon.hidden = true;
        mon.innerHTML = "";
        if (showWall && window.FieldMonitorDashboard) {
          mon.classList.remove("hd-monitor--hidden");
          mon.hidden = false;
          window.FieldMonitorDashboard.mount(mon, Object.assign({}, doc?.monitor_dashboard || {}, {
            programs: doc.programs || [],
            icon_dock: doc.icon_dock || [],
          }));
        }
      }
    } catch (_) {}

    try {
      const showAmmoNetBottom = policy.ammonet_bar_bottom !== false && policy.ammonet_display_right === false;
      if (showAmmoNetBottom && window.FieldAmmoNetDisplay?.mountBottom) {
        window.FieldAmmoNetDisplay.mountBottom();
      }
    } catch (_) {}

    try {
      if (window.FieldDesktopScale) {
        const shell = doc?.shell?.settings || {};
        window.FieldDesktopScale.apply({
          ui_scale: shell.ui_scale || policy.desktop_ui_scale_default || 200,
          desktop_icon_size: shell.desktop_icon_size || policy.desktop_icon_size_default || 96,
        }, { silent: true });
      }
    } catch (_) {}

    try {
      if (window.NexusFieldShell) window.NexusFieldShell.mount(doc);
    } catch (_) {}

    try {
      const tm = document.getElementById("c2tm-mount");
      if (tm && window.FieldC2TaskManager) window.FieldC2TaskManager.mount(tm);
    } catch (_) {}
  }

  async function fetchDesktopDoc() {
    const res = await fetch(apiUrl("/api/field-host-desktop"), { credentials: "same-origin" });
    if (res.ok) return res.json();
    if (pagesRuntime()) {
      const jres = await fetch(apiUrl("/api/field-host-desktop.json"), { credentials: "same-origin" });
      if (jres.ok) return jres.json();
    }
    throw new Error("desktop API " + res.status);
  }

  function ensureStartbar() {
    if (document.getElementById("fsb-start")) return true;
    const doc = state.data || global.__H7_DESKTOP_DOC__;
    if (doc) return mountStartbar(doc);
    return false;
  }

  async function refresh() {
    const loading = document.getElementById("hd-loading");
    if (loading) loading.classList.remove("hidden");
    fillViewport();
    try {
      const doc = await fetchDesktopDoc();
      applyDesktop(doc);
      mountDesktopChrome(doc);
      engageKeyboardSovereign();
      runInternetCleanIfDefault(doc?.policy || {});
      if (pagesRuntime()) toast("AmmoOS desktop ready · click an icon to launch");
    } catch (e) {
      // Static GitHub Pages fallback for Hostess7/desktop/ — this IS our AmmoOS OS desktop.
      // Only 4 big cartoony icons. Classic Start button for the rest. Queen browser (our own, using GDI/RTX).
      const staticDoc = {
        product: "AmmoOS",
        version: "2.0",
        programs: desktopDefaultFallback(),
        desktop_icons: desktopDefaultFallback(),
        policy: { desktop_icons_in_start: false, show_desktop_icons: true, battle_stations: true, six_tool_wall: true, six_tool_wall_on_boot: true, ammonet_display_right: false, ammonet_bar_bottom: true, monitor_dashboard_right: false, desktop_ui_scale_default: 200, desktop_icon_size_default: 96 },
        shell: { settings: { desktop_icon_size: 96, ui_scale: 200, sort_desktop: "manual" } },
        startbar: { start_label: "Start", classic: true },
        guest_os: { system: "Field" },
        secure_routing: "NEXUS C2 + H7/Field Tech (all GitHub/X via our router, no middlemen)"
      };
      applyDesktop(staticDoc);
      mountDesktopChrome(staticDoc);
      if (pagesRuntime()) toast("AmmoOS desktop ready · Classic icons · Start menu");
    } finally {
      if (loading) loading.classList.add("hidden");
    }
  }

  window.FieldHostDesktop = {
    refresh: refresh,
    applyDesktop: applyDesktop,
    applyWallpaper: applyWallpaper,
    toast: toast,
    launchApp: launchApp,
    renderDesktopIcons: renderDesktopIcons,
    toggleDesktopPin: toggleDesktopPin,
    openQueenBrowserClean: openQueenBrowserClean,
    ensureStartbar: ensureStartbar,
    mountStartbar: mountStartbar,
  };

  window.addEventListener("pagehide", function () {
    releaseKeyboardSovereign("pagehide");
  });
  window.addEventListener("beforeunload", function () {
    releaseKeyboardSovereign("beforeunload");
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refresh);
  } else {
    refresh();
  }
})(typeof window !== "undefined" ? window : globalThis);