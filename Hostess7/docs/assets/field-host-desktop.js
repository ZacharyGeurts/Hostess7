/**
 * Field Host Desktop — AmmoOS 2.0: desktop icons, taskbar, optional six-tool wall, shell windows.
 */
(function () {
  "use strict";

  const state = { data: null, keysEngaged: false, selected: null };

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
  const DESKTOP_FOUR_IDS = ["view", "queen-terminal", "queen-browser", "field-broadcaster"];
  const DESKTOP_ICON_PX = 96;

  function iconHtml(app, size) {
    size = size || DESKTOP_ICON_PX;
    const QIE = window.QueenIconEngine;
    if (QIE?.programIconHtml) {
      return QIE.programIconHtml(app, size, { base: QIE.PANEL_ICONS });
    }
    const src = app.icon_url || QUEEN_ICON;
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
    return "/Hostess7";
  }

  function pagesAssetBase() {
    if (pagesRuntime()) return (window.HOSTESS7_PAGES_BASE || "/Hostess7") + "/assets";
    return "/assets";
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
    const exec = app.exec || app.url || "";
    if (app.shell !== false && (app.shell || exec.includes("embed=1") || app.view)) {
      if (shellLaunch(app)) {
        toast("Opened · " + (app.name || exec));
        return;
      }
    }
    // Always prefer our Queen browser (standard web engine we own via GDI/RTX) for pages — never host Firefox.
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

  function desktopFourFallback() {
    const base = pagesRuntime() ? (window.HOSTESS7_PAGES_BASE || "/Hostess7") : "";
    const assets = pagesAssetBase();
    return [
      { id: "view", name: "View", hint: "Files & folders", icon: "queen-prog-view", exec: base + "/queen/view.html", icon_url: assets + "/queen-prog-view.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "queen-terminal", name: "Terminal", hint: "Queen terminal", icon: "queen-prog-terminal", exec: base + "/queen/?dock=terminal", icon_url: assets + "/queen-prog-terminal.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "queen-browser", name: "Queen Browser", hint: "Queen web engine", icon: "queen-prog-browser", exec: base + "/queen/browser.html", icon_url: assets + "/queen-prog-browser.png", pinned: true, shell: true, category: "NEXUS · Queen" },
      { id: "field-broadcaster", name: "Broadcaster", hint: "Field broadcaster", icon: "queen-prog-field", exec: base + "/field-broadcaster", icon_url: assets + "/queen-prog-field.png", pinned: true, shell: true, live: true, category: "NEXUS · Media" },
    ];
  }

  function desktopIconList(doc) {
    const programs = doc?.programs || [];
    const byId = {};
    programs.forEach(function (p) {
      if (p?.id) byId[p.id] = p;
    });
    const fromApi = Array.isArray(doc?.desktop_icons) ? doc.desktop_icons : [];
    const four = DESKTOP_FOUR_IDS.map(function (id) {
      return byId[id] || fromApi.find(function (p) { return p.id === id; });
    }).filter(Boolean);
    if (four.length === DESKTOP_FOUR_IDS.length) return four;
    return desktopFourFallback();
  }

  function renderDesktopIcons(doc) {
    const grid = document.getElementById("hd-icons");
    if (!grid) return;

    // Force exactly 4 big cartoony icons. Always. Clean stack, no overlap, no other data.
    grid.innerHTML = '';
    grid.style.display = 'flex';
    grid.style.flexDirection = 'column';
    grid.style.gap = '12px';
    grid.style.padding = '12px 8px';
    grid.style.alignItems = 'flex-start';

    const FOUR = desktopIconList(doc);

    FOUR.forEach(function (app) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'hd-icon hd-icon-cartoony';
      btn.dataset.appId = app.id;
      btn.title = app.hint || app.name;

      const iconWrap = document.createElement('div');
      iconWrap.className = 'hd-icon-glyph';
      iconWrap.innerHTML = iconHtml(app, DESKTOP_ICON_PX);

      const label = document.createElement('span');
      label.style.cssText = 'font-size:11px; color:#e0f0ff; text-shadow:0 1px 2px rgba(0,0,0,0.9); margin-top:1px;';
      label.textContent = app.name;

      btn.style.cssText = 'background:transparent; border:1px solid rgba(120,255,180,0.25); padding:4px 2px; border-radius:4px; display:flex; flex-direction:column; align-items:center; width:100px;';
      btn.appendChild(iconWrap);
      btn.appendChild(label);

      btn.addEventListener('click', function (e) {
        e.stopImmediatePropagation();
        grid.querySelectorAll('.hd-icon').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        state.selected = app;

        if (app.id === 'queen-browser') {
          openQueenBrowserClean();
        } else {
          launchApp(app);
        }
      });

      btn.addEventListener('dblclick', function (e) {
        e.stopImmediatePropagation();
        if (app.id === 'queen-browser') openQueenBrowserClean();
        else launchApp(app);
      });

      btn.addEventListener('contextmenu', function (ev) {
        ev.preventDefault();
        const m = document.createElement('div');
        m.style.cssText = 'position:fixed;z-index:99999;background:#0a0f0a;border:1px solid #4ade80;color:#c8ffda;padding:4px 0;font-size:11px;min-width:140px';
        m.innerHTML = '<div style="padding:3px 8px;font-weight:700;border-bottom:1px solid #334155">' + esc(app.name) + '</div>' +
          '<div data-a="open" style="padding:3px 8px;cursor:pointer">Open</div>' +
          '<div data-a="queen" style="padding:3px 8px;cursor:pointer">Open Queen Window</div>';
        m.style.left = ev.clientX + 'px';
        m.style.top = ev.clientY + 'px';
        document.body.appendChild(m);
        m.onclick = function (me) {
          const a = me.target.getAttribute('data-a');
          document.body.removeChild(m);
          if (a === 'open' || !a) {
            if (app.id === 'queen-browser') openQueenBrowserClean(); else launchApp(app);
          } else if (a === 'queen') {
            openQueenBrowserClean();
          }
        };
        setTimeout(function () { document.addEventListener('click', () => { if (m.parentNode) m.parentNode.removeChild(m); }, {once: true}); }, 50);
      });

      grid.appendChild(btn);
    });

    grid.classList.remove('hidden');
  }

  function openQueenBrowserClean() {
    // Open Queen as a normal separate browser window with the main page loaded.
    // "Main 127 page" -> the Queen browser shell (our controlled browser).
    const base = pagesRuntime() ? (window.HOSTESS7_PAGES_BASE || "/Hostess7") : "/Hostess7/queen/world";
    const url = pagesRuntime() ? base + "/queen/browser.html" : base + "/browser.html";
    const features = 'width=1280,height=820,menubar=yes,toolbar=yes,location=yes,resizable=yes,scrollbars=yes,status=yes';
    let w;
    try {
      w = window.open(url, 'QueenBrowser', features);
    } catch (e) {}
    if (!w) {
      // fallback
      w = window.open(url, '_blank');
    }
    // Dock / track on our simulated taskbar if possible
    try {
      const qapp = { id: 'queen', name: 'Queen Browser', url: url };
      if (window.FieldStartbar && window.FieldStartbar.trackRunning) window.FieldStartbar.trackRunning(qapp);
      if (window.FieldStartbar && window.FieldStartbar.launchApp) window.FieldStartbar.launchApp(qapp);
    } catch (_) {}
    toast('Queen opened in new window');
  }

  function engageKeyboardSovereign() {
    if (state.keysEngaged) return;
    fetch("/api/field-keyboard-sovereign/engage", {
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
      navigator.sendBeacon("/api/field-keyboard-sovereign/release", body);
    } else {
      fetch("/api/field-keyboard-sovereign/release", {
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
    document.documentElement.dataset.osTheme = doc.theme || "ammo-field";
    const label = document.getElementById("hd-wall-label");
    if (label) {
      label.textContent = "AmmoOS 2.0 — View · Terminal · Browser · Broadcaster · Classic Start";
    }
    renderDesktopIcons(doc);
  }

  async function refresh() {
    const loading = document.getElementById("hd-loading");
    if (loading) loading.classList.remove("hidden");
    fillViewport();
    try {
      const res = await fetch("/api/field-host-desktop", { credentials: "same-origin" });
      if (!res.ok) throw new Error("desktop API " + res.status);
      const doc = await res.json();
      applyDesktop(doc);

      const mon = document.getElementById("hd-monitor");
      const policy = doc?.policy || {};
      const showWall = policy.six_tool_wall === true && policy.six_tool_wall_on_boot !== false;
      if (mon) {
        mon.classList.toggle("hd-monitor--hidden", !showWall);
        mon.hidden = !showWall;
        mon.innerHTML = "";
      }
      const dash = doc?.monitor_dashboard || {};
      if (showWall && mon && window.FieldMonitorDashboard) {
        window.FieldMonitorDashboard.mount(mon, Object.assign({}, dash, {
          programs: doc.programs || [],
          icon_dock: doc.icon_dock || [],
        }));
      }

      const sb = document.getElementById("fsb-mount");
      if (sb && window.FieldStartbar) window.FieldStartbar.mount(sb, doc);

      if (window.FieldDesktopScale) {
        const shell = doc?.shell?.settings || {};
        window.FieldDesktopScale.apply({
          ui_scale: shell.ui_scale || policy.desktop_ui_scale_default || 200,
          desktop_icon_size: shell.desktop_icon_size || policy.desktop_icon_size_default || 96,
        }, { silent: true });
      }

      if (window.NexusFieldShell) window.NexusFieldShell.mount(doc);

      const tm = document.getElementById("c2tm-mount");
      if (tm && window.FieldC2TaskManager) window.FieldC2TaskManager.mount(tm);

      engageKeyboardSovereign();
      if (pagesRuntime()) toast("AmmoOS desktop ready · click an icon to launch");
    } catch (e) {
      // Static GitHub Pages fallback for Hostess7/desktop/ — this IS our AmmoOS OS desktop.
      // Only 4 big cartoony icons. Classic Start button for the rest. Queen browser (our own, using GDI/RTX).
      const staticDoc = {
        product: "AmmoOS",
        version: "2.0",
        programs: desktopFourFallback(),
        desktop_icons: desktopFourFallback(),
        policy: { desktop_icons_in_start: false, show_desktop_icons: true, six_tool_wall: false, desktop_ui_scale_default: 200, desktop_icon_size_default: 96 },
        shell: { settings: { desktop_icon_size: 96, ui_scale: 200, sort_desktop: "manual" } },
        startbar: { start_label: "Start", classic: true },
        guest_os: { system: "Field" },
        secure_routing: "NEXUS C2 + H7/Field Tech (all GitHub/X via our router, no middlemen)"
      };
      applyDesktop(staticDoc);

      const sb = document.getElementById("fsb-mount");
      if (sb && window.FieldStartbar) window.FieldStartbar.mount(sb, staticDoc);

      if (pagesRuntime()) toast("AmmoOS desktop ready — 4 cartoony icons · Classic Start · 200% taskbar");
    } finally {
      if (loading) loading.classList.add("hidden");
    }
  }

  window.FieldHostDesktop = {
    refresh: refresh,
    applyDesktop: applyDesktop,
    toast: toast,
    launchApp: launchApp,
    renderDesktopIcons: renderDesktopIcons,
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