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

  function iconHtml(app) {
    const QIE = window.QueenIconEngine;
    if (QIE?.programIconHtml) {
      return QIE.programIconHtml(app, 40, { base: QIE.PANEL_ICONS });
    }
    const src = app.icon_url || QUEEN_ICON;
    if (app.live) {
      return (
        '<span class="hd-icon-live-wrap">' +
        '<img src="' + esc(src) + '" alt="" width="40" height="40" class="hd-app-icon hd-app-icon--live" loading="lazy" decoding="async" />' +
        '<span class="hd-live-badge">LIVE</span></span>'
      );
    }
    return '<img src="' + esc(src) + '" alt="" width="40" height="40" class="hd-app-icon" loading="lazy" decoding="async" />';
  }

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!window.HOSTESS7_PAGES_BASE;
  }

  function panelOrigin() {
    if (pagesRuntime()) return window.HOSTESS7_PAGES_BASE || "";
    return "/Hostess7";
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

  function desktopIconList(doc) {
    const policy = doc?.policy || {};
    const fromApi = Array.isArray(doc?.desktop_icons) ? doc.desktop_icons : [];
    if (fromApi.length && !policy.desktop_icons_in_start) return fromApi;
    const programs = doc?.programs || [];
    const pinned = programs.filter(function (p) {
      return (
        p.pinned &&
        !p.ghost &&
        !p.clipboard_ghost &&
        p.id !== "nexus-c2-desktop" &&
        p.launcher_visible !== false
      );
    });
    if (pinned.length) return pinned;
    return programs.filter(function (p) {
      return p.shell && !p.ghost && !p.clipboard_ghost && p.id !== "queen-browser";
    }).slice(0, 32);
  }

  function renderDesktopIcons(doc) {
    const grid = document.getElementById("hd-icons");
    if (!grid) return;
    const policy = doc?.policy || {};
    const settings = doc?.shell?.settings || {};
    const show =
      policy.show_desktop_icons !== false &&
      settings.show_desktop_icons !== false &&
      !policy.desktop_icons_in_start;
    const icons = desktopIconList(doc);
    const sortKey = String(settings.sort_desktop || "name").toLowerCase();
    const sorted = icons.slice().sort(function (a, b) {
      if (sortKey === "category") {
        return (a.category || "").localeCompare(b.category || "") || (a.name || "").localeCompare(b.name || "");
      }
      return (a.name || "").localeCompare(b.name || "");
    });
    grid.innerHTML = sorted
      .map(function (app) {
        return (
          '<button type="button" class="hd-icon" data-app-id="' +
          esc(app.id) +
          '" title="' +
          esc(app.hint || app.name) +
          '">' +
          iconHtml(app) +
          "<span>" +
          esc(app.name) +
          "</span></button>"
        );
      })
      .join("");

    const byId = {};
    (doc?.programs || []).concat(sorted).forEach(function (a) {
      if (a?.id) byId[a.id] = a;
    });

    grid.querySelectorAll(".hd-icon").forEach(function (btn) {
      const app = byId[btn.dataset.appId];
      if (!app) return;
      let pressTimer = null;
      btn.addEventListener("click", function () {
        grid.querySelectorAll(".hd-icon").forEach(function (b) { b.classList.remove("selected"); });
        btn.classList.add("selected");
        state.selected = app;
        launchApp(app);
      });
      btn.addEventListener("dblclick", function () { launchApp(app); });
      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        if (window.NexusFieldShell?.openDesktopContext) {
          window.NexusFieldShell.openDesktopContext(ev.clientX, ev.clientY, app);
        }
      });
      btn.addEventListener("pointerdown", function (ev) {
        pressTimer = setTimeout(function () {
          pressTimer = null;
          if (window.NexusFieldShell?.openDesktopContext) {
            window.NexusFieldShell.openDesktopContext(ev.clientX, ev.clientY, app);
          }
        }, doc?.startbar?.long_press_ms || 480);
      });
      btn.addEventListener("pointerup", function () {
        if (pressTimer) clearTimeout(pressTimer);
      });
      btn.addEventListener("pointercancel", function () {
        if (pressTimer) clearTimeout(pressTimer);
      });
    });
    grid.classList.toggle("hidden", !show || !sorted.length);
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
    const root = document.documentElement;
    root.classList.add("nfs-fullscreen-desktop", "nfs-kiosk");
    try {
      if (!document.fullscreenElement && root.requestFullscreen) {
        root.requestFullscreen({ navigationUI: "hide" }).catch(function () {});
      }
    } catch (_) {}
  }

  function applyDesktop(doc) {
    state.data = doc;
    try { global.__H7_DESKTOP_DOC__ = doc; } catch (_) {}
    document.documentElement.dataset.osTheme = doc.theme || "ammo-field";
    const label = document.getElementById("hd-wall-label");
    if (label) {
      const g = doc.guest_os || {};
      const n = doc.program_count || (doc.programs || []).length;
      label.textContent = (doc.product || "AmmoOS") + " 2.0 · " + n + " programs · " + (g.system || "Field");
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
          ui_scale: shell.ui_scale || policy.desktop_ui_scale_default || 125,
          desktop_icon_size: shell.desktop_icon_size || policy.desktop_icon_size_default || 63,
        }, { silent: true });
      }

      if (window.NexusFieldShell) window.NexusFieldShell.mount(doc);

      const tm = document.getElementById("c2tm-mount");
      if (tm && window.FieldC2TaskManager) window.FieldC2TaskManager.mount(tm);

      engageKeyboardSovereign();
      if (pagesRuntime()) toast("AmmoOS desktop ready · click an icon to launch");
    } catch (e) {
      toast("Load failed: " + e.message);
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