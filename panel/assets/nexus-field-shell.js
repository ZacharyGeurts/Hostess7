/**
 * NEXUS Field OS shell — AmmoOS borderless programs, taskbar, field switch, Monster rescue.
 * @g16 5.1.0 · Grok16/field-stack-fabric · field-host-desktop
 */
(function (global) {
  "use strict";

  const QUEEN_ICON = "/assets/ammoos-field-48.png";
  const PANEL = "";

  const YIELD_KEY = "nexus_field_yielded_to_host";

  const state = {
    settings: null,
    hostPolicy: null,
    windows: [],
    activeId: null,
    altOpen: false,
    altIndex: 0,
    programsById: {},
    zTop: 8100,
    yieldedToHost: false,
  };

  function desktopIconsEnabled() {
    if (state.hostPolicy?.desktop_icons_in_start) return false;
    return state.settings?.show_desktop_icons !== false;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function toast(msg) {
    global.FieldHostDesktop?.toast?.(msg);
  }

  function $(id) {
    return document.getElementById(id);
  }

  const QUEEN_BROWSER = "http://127.0.0.1:9481/world/browser.html";
  const PANEL_ORIGIN = "http://127.0.0.1:9477";

  function isPanelLoopback(url) {
    if (!url || url.startsWith("/")) return true;
    try {
      const p = new URL(url, PANEL_ORIGIN);
      return (p.hostname === "127.0.0.1" || p.hostname === "localhost") && p.port === "9477";
    } catch {
      return false;
    }
  }

  function isQueenLoopback(url) {
    try {
      const p = new URL(url, QUEEN_BROWSER);
      return (p.hostname === "127.0.0.1" || p.hostname === "localhost") && p.port === "9481";
    } catch {
      return false;
    }
  }

  function queenShellUrl(exec) {
    if (!exec || !isQueenLoopback(exec)) return exec;
    try {
      const p = new URL(exec, QUEEN_BROWSER);
      if (p.pathname.startsWith("/browse/view") || p.pathname === "/browse/view") return QUEEN_BROWSER;
      if (p.pathname.startsWith("/world/") && !p.pathname.endsWith("/browser.html")) return exec;
      if (p.pathname.endsWith("/browser.html")) return QUEEN_BROWSER;
    } catch (_) {}
    return exec;
  }

  function resolveUrl(app) {
    const exec = String(app?.exec || app?.url || "").trim();
    if (!exec) return "/field";
    if (app?.queenNavigate) return QUEEN_BROWSER;
    if (exec.startsWith("/")) return exec;
    if (app?.view) return "/command?embed=1#" + app.view;
    if (/^https?:\/\//i.test(exec)) {
      if (isPanelLoopback(exec)) return exec;
      if (isQueenLoopback(exec)) return queenShellUrl(exec);
      return QUEEN_BROWSER;
    }
    return exec;
  }

  function queueQueenNavigate(winId, targetUrl) {
    if (!winId || !targetUrl) return;
    const win = state.windows.find(function (w) {
      return w.id === winId;
    });
    if (win) win.queenNavigate = targetUrl;
    setTimeout(function () {
      const iframe = document.querySelector("#" + winId + " iframe");
      if (!iframe) return;
      function send() {
        try {
          iframe.contentWindow?.postMessage(
            { type: "queen:shell", action: "navigate", url: targetUrl },
            "*"
          );
        } catch (_) {}
      }
      if (iframe.contentWindow) send();
      else iframe.addEventListener("load", send, { once: true });
    }, 80);
  }

  function viewFromUrl(url) {
    const m = String(url || "").match(/#([^?&]+)/);
    return m ? m[1] : "";
  }

  function appKey(app) {
    const url = resolveUrl(app);
    const view = app.view || viewFromUrl(url);
    if (view && url.includes("/command")) return "nexus:" + view.split("/")[0];
    return app.id || url;
  }

  function findWindow(key) {
    return state.windows.find(function (w) {
      return w.key === key || w.appId === key || w.id === key;
    });
  }

  function applySettings(doc) {
    state.settings = (doc && doc.settings) || doc || {};
    const autoHide = state.settings.taskbar_auto_hide !== false;
    document.documentElement.classList.toggle("nfs-taskbar-hidden", autoHide);
    if (global.FieldDesktopScale?.apply) {
      global.FieldDesktopScale.apply(state.settings);
    } else {
      document.documentElement.style.setProperty(
        "--hd-icon-size",
        (state.settings.desktop_icon_size || 50) + "px"
      );
      const scale = (state.settings.ui_scale || 125) / 100;
      document.documentElement.style.fontSize = Math.round(16 * scale) + "px";
    }
    if (state.settings.theme_override) {
      const themeAliases = {
        gnome: "ammo-field",
        windows11: "ammo-c2",
        windows10: "ammo-c2",
        kde: "ammo-deep",
        macos: "ammo-rose",
      };
      const t = themeAliases[state.settings.theme_override] || state.settings.theme_override;
      document.documentElement.dataset.osTheme = t;
    }
  }

  async function loadSettings() {
    try {
      const res = await fetch("/api/field-shell-settings", { credentials: "same-origin" });
      if (!res.ok) throw new Error("settings " + res.status);
      applySettings(await res.json());
    } catch (_) {
      applySettings({ taskbar_auto_hide: false, taskbar_peek: true, ui_scale: 125, desktop_icon_size: 50 });
    }
  }

  async function saveSettings(patch) {
    try {
      const res = await fetch("/api/field-shell-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch || {}),
      });
      const doc = await res.json();
      applySettings(doc);
      return doc;
    } catch (e) {
      toast("Settings save failed: " + e.message);
      return null;
    }
  }

  function renderWindows() {
    const root = $("nfs-root");
    if (!root) return;
    root.innerHTML = state.windows
      .map(function (win) {
        const cls = [
          "nfs-win",
          win.id === state.activeId && !win.minimized ? "active" : "",
          win.minimized ? "minimized" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          '<div class="' +
          cls +
          '" id="' +
          esc(win.id) +
          '" data-win-id="' +
          esc(win.id) +
          '" style="z-index:' +
          win.z +
          '">' +
          '<iframe src="' +
          esc(win.url) +
          '" title="' +
          esc(win.name) +
          '" allow="clipboard-read; clipboard-write" loading="lazy"></iframe></div>'
        );
      })
      .join("");
  }

  function syncTaskbar() {
    const tasks = state.windows
      .filter(function (w) {
        return !w.minimized || w.id === state.activeId;
      })
      .map(function (w) {
        return {
          id: w.appId || w.key,
          name: w.name,
          icon_url: w.icon_url,
          exec: w.url,
          shellWin: w.id,
        };
      });
    global.FieldC2TaskManager?.sync?.(tasks, state.activeId);
    global.FieldStartbar?.syncShellTasks?.(tasks, state.activeId);
  }

  function focusWindow(id) {
    const win = state.windows.find(function (w) {
      return w.id === id;
    });
    if (!win) return;
    win.minimized = false;
    state.zTop += 1;
    win.z = state.zTop;
    state.activeId = win.id;
    renderWindows();
    syncTaskbar();
    global.FieldStartbar?.trackRunning?.({
      id: win.appId,
      name: win.name,
      icon_url: win.icon_url,
      exec: win.url,
    });
  }

  function minimizeWindow(id) {
    const win = state.windows.find(function (w) {
      return w.id === id;
    });
    if (!win) return;
    win.minimized = true;
    if (state.activeId === id) {
      const visible = state.windows.filter(function (w) {
        return !w.minimized;
      });
      state.activeId = visible.length ? visible[visible.length - 1].id : null;
    }
    renderWindows();
    syncTaskbar();
  }

  function closeWindow(id) {
    state.windows = state.windows.filter(function (w) {
      return w.id !== id;
    });
    if (state.activeId === id) {
      const last = state.windows[state.windows.length - 1];
      state.activeId = last && !last.minimized ? last.id : null;
      if (last && state.activeId) last.minimized = false;
    }
    renderWindows();
    syncTaskbar();
    if (!state.windows.length) showDesktop();
  }

  function showDesktop() {
    state.windows.forEach(function (w) {
      w.minimized = true;
    });
    state.activeId = null;
    renderWindows();
    syncTaskbar();
  }

  function launchPanelThumbnail(app, opts) {
    opts = opts || {};
    if (!app) return null;
    const url = opts.url || resolveUrl(app);
    const mon = document.getElementById("hd-monitor");
    if (mon && global.FieldMonitorDashboard && global.FieldMonitorDashboard.addPanel) {
      global.FieldMonitorDashboard.addPanel(mon, {
        id: app.id || appKey(app),
        title: app.name || "Panel",
        url: url,
        chromeless: app.chromeless !== false,
        panel_thumbnail: true,
      });
      toast((app.name || "Program") + " — panel thumbnail");
      return { id: app.id, mode: "panel_thumbnail", url: url };
    }
    const plain = Object.assign({}, app);
    delete plain.panel_thumbnail;
    delete plain.panel_only;
    return launch(plain, Object.assign({}, opts, { newWindow: true, _skipThumbnail: true }));
  }

  function launch(app, opts) {
    opts = opts || {};
    if (!app) return null;
    if (!opts._skipThumbnail && (app.panel_thumbnail || app.panel_only)) {
      return launchPanelThumbnail(app, opts);
    }
    const url = opts.url || resolveUrl(app);
    const key = appKey(app);
    const existing = findWindow(key);
    if (existing && !opts.newWindow) {
      focusWindow(existing.id);
      if (opts.view || app.view) {
        const iframe = document.querySelector('#' + existing.id + " iframe");
        const target = opts.view || app.view;
        if (iframe && url.includes("/command")) {
          try {
            iframe.contentWindow?.postMessage({ type: "nexus:navigate", view: target }, "*");
          } catch (_) {}
        }
      }
      return existing;
    }
    state.zTop += 1;
    const id = "nfs-win-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const win = {
      id: id,
      key: key,
      appId: app.id || key,
      name: app.name || "Program",
      icon_url: app.icon_url || QUEEN_ICON,
      url: url,
      minimized: false,
      z: state.zTop,
      queenNavigate: app.queenNavigate || null,
    };
    state.windows.push(win);
    state.activeId = id;
    renderWindows();
    syncTaskbar();
    global.FieldStartbar?.trackRunning?.(app);
    const navTarget = app.queenNavigate || (/^https?:\/\//i.test(app.exec || "") && !isPanelLoopback(app.exec) && !isQueenLoopback(app.exec) ? app.exec : null);
    if (navTarget && url === QUEEN_BROWSER) queueQueenNavigate(id, navTarget);
    return win;
  }

  function launchView(view, opts) {
    const base = view.split("/")[0];
    const app =
      state.programsById[base] ||
      state.programsById["nexus-" + base] ||
      {
        id: "nexus-" + base,
        name: base.replace(/-/g, " "),
        exec: "/command?embed=1#" + view,
        view: view,
        icon_url: QUEEN_ICON,
      };
    return launch({ ...app, view: view }, opts);
  }

  function toggleWindow(id) {
    const win = state.windows.find(function (w) {
      return w.id === id || w.appId === id || w.key === id;
    });
    if (!win) return;
    if (win.id === state.activeId && !win.minimized) minimizeWindow(win.id);
    else focusWindow(win.id);
  }

  function renderAltTab() {
    const overlay = $("nfs-alt-overlay");
    const grid = $("nfs-alt-grid");
    if (!overlay || !grid) return;
    const visible = state.windows.filter(function (w) {
      return !w.minimized || w.id === state.activeId;
    });
    if (!visible.length) {
      overlay.classList.remove("open");
      state.altOpen = false;
      return;
    }
    grid.innerHTML = visible
      .map(function (w, i) {
        return (
          '<button type="button" class="nfs-alt-card' +
          (w.id === state.activeId ? " active" : "") +
          '" data-alt-id="' +
          esc(w.id) +
          '">' +
          '<img src="' +
          esc(w.icon_url || QUEEN_ICON) +
          '" alt="" width="48" height="48" />' +
          "<span>" +
          esc(w.name) +
          "</span></button>"
        );
      })
      .join("");
    grid.querySelectorAll("[data-alt-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        focusWindow(btn.dataset.altId);
        closeAltTab();
      });
    });
    overlay.classList.add("open");
    state.altOpen = true;
    state.altIndex = visible.findIndex(function (w) {
      return w.id === state.activeId;
    });
    if (state.altIndex < 0) state.altIndex = 0;
  }

  function closeAltTab() {
    const overlay = $("nfs-alt-overlay");
    if (overlay) overlay.classList.remove("open");
    state.altOpen = false;
  }

  function cycleAltTab(backward) {
    const visible = state.windows.filter(function (w) {
      return !w.minimized;
    });
    if (!visible.length) return;
    let idx = visible.findIndex(function (w) {
      return w.id === state.activeId;
    });
    if (idx < 0) idx = 0;
    idx = backward ? (idx - 1 + visible.length) % visible.length : (idx + 1) % visible.length;
    focusWindow(visible[idx].id);
    if (state.altOpen) renderAltTab();
  }

  function openStartProperties() {
    const modal = $("nfs-props-modal");
    const body = $("nfs-props-body");
    if (!modal || !body) return;
    const s = state.settings || {};
    body.innerHTML =
      '<div class="nfs-modal-row"><label>Taskbar auto-hide</label><input type="checkbox" id="nfs-prop-autohide" ' +
      (s.taskbar_auto_hide !== false ? "checked" : "") +
      " /></div>" +
      '<div class="nfs-modal-row"><label>Peek on hover</label><input type="checkbox" id="nfs-prop-peek" ' +
      (s.taskbar_peek !== false ? "checked" : "") +
      " /></div>" +
      '<div class="nfs-modal-row"><label>UI scale</label><input type="range" id="nfs-prop-scale" min="' +
      (global.FieldDesktopScale?.MIN_PCT || 50) +
      '" max="' +
      (global.FieldDesktopScale?.MAX_PCT || 200) +
      '" value="' +
      (s.ui_scale || global.FieldDesktopScale?.DEFAULT_PCT || 125) +
      '" /></div>' +
      '<div class="nfs-modal-row"><label>Icon size</label><input type="range" id="nfs-prop-icons" min="32" max="72" value="' +
      (s.desktop_icon_size || 40) +
      '" /></div>' +
      '<div class="nfs-modal-row"><label>Theme</label><select id="nfs-prop-theme">' +
      [
        ["", "Auto"],
        ["ammo-field", "AmmoOS Field"],
        ["ammo-c2", "AmmoOS C2"],
        ["ammo-deep", "AmmoOS Deep"],
        ["ammo-rose", "AmmoOS Rose"],
      ]
        .map(function (row) {
          const t = row[0];
          const label = row[1];
          return (
            '<option value="' +
            esc(t) +
            '"' +
            ((s.theme_override || "") === t ? " selected" : "") +
            ">" +
            esc(label) +
            "</option>"
          );
        })
        .join("") +
      "</select></div>";
    modal.classList.add("open");
    $("nfs-props-save")?.addEventListener(
      "click",
      async function onSave() {
        $("nfs-props-save")?.removeEventListener("click", onSave);
        await saveSettings({
          taskbar_auto_hide: !!$("nfs-prop-autohide")?.checked,
          taskbar_peek: !!$("nfs-prop-peek")?.checked,
          ui_scale: parseInt($("nfs-prop-scale")?.value || "100", 10),
          desktop_icon_size: parseInt($("nfs-prop-icons")?.value || "40", 10),
          theme_override: $("nfs-prop-theme")?.value || "",
        });
        modal.classList.remove("open");
        toast("Start menu properties saved");
      },
      { once: true }
    );
  }

  function openDisplaySettings() {
    const modal = $("nfs-display-modal");
    const body = $("nfs-display-body");
    if (!modal || !body) return;
    body.innerHTML = "Loading displays…";
    modal.classList.add("open");
    fetch("/api/field-shell-settings", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (doc) {
        const displays = doc.displays || [];
        const s = doc.settings || {};
        let html =
          '<div class="nfs-modal-row"><label>UI scale</label><input type="range" id="nfs-disp-scale" min="' +
          (global.FieldDesktopScale?.MIN_PCT || 50) +
          '" max="' +
          (global.FieldDesktopScale?.MAX_PCT || 200) +
          '" value="' +
          (s.ui_scale || global.FieldDesktopScale?.DEFAULT_PCT || 125) +
          '" /></div>';
        displays.forEach(function (d, i) {
          html +=
            '<div class="nfs-modal-row"><label>' +
            esc(d.name || d.id) +
            '</label><span>' +
            esc(d.resolution || "—") +
            " · " +
            esc(d.backend || "") +
            "</span></div>";
        });
        html +=
          '<p style="color:#9aa8c0;font-size:11px;margin-top:12px">Host resolution changes use xrandr when available. UI scale applies inside Field desktop.</p>';
        body.innerHTML = html;
        $("nfs-display-save")?.addEventListener(
          "click",
          async function onDispSave() {
            $("nfs-display-save")?.removeEventListener("click", onDispSave);
            await saveSettings({ ui_scale: parseInt($("nfs-disp-scale")?.value || "100", 10) });
            modal.classList.remove("open");
            toast("Display settings applied");
          },
          { once: true }
        );
      })
      .catch(function () {
        body.textContent = "Could not load display info.";
      });
  }

  function openDesktopContext(x, y, app) {
    const ctx = $("nfs-desktop-ctx");
    if (!ctx) return;
    let items;
    if (app) {
      ctx.innerHTML =
        '<button type="button" data-dact="open">Open</button>' +
        '<button type="button" data-dact="pin">Pin to taskbar</button>' +
        '<button type="button" data-dact="props">Properties</button>';
    } else {
      ctx.innerHTML =
        '<button type="button" data-dact="refresh">Refresh</button>' +
        '<button type="button" data-dact="sort">Sort icons by name</button>' +
        (state.hostPolicy?.desktop_icons_in_start
          ? ""
          : '<button type="button" data-dact="icons">Toggle desktop icons</button>') +
        "<hr />" +
        '<button type="button" data-dact="display">Display settings</button>' +
        '<button type="button" data-dact="personalize">Personalize</button>' +
        '<button type="button" data-dact="control">Control Panel</button>' +
        "<hr />" +
        '<button type="button" data-dact="desktop">Show desktop</button>';
    }
    ctx.style.left = Math.min(x, innerWidth - 220) + "px";
    ctx.style.top = Math.min(y, innerHeight - 280) + "px";
    ctx.classList.add("open");
    ctx.onclick = function (ev) {
      const btn = ev.target.closest("[data-dact]");
      if (!btn) return;
      const act = btn.dataset.dact;
      ctx.classList.remove("open");
      if (act === "open" && app) launch(app);
      else if (act === "pin" && app) global.FieldStartbar?.trackRunning?.(app);
      else if (act === "props" && app) toast((app.name || "") + " · " + resolveUrl(app));
      else if (act === "refresh") global.FieldHostDesktop?.refresh?.();
      else if (act === "sort") {
        saveSettings({ sort_desktop: "name" }).then(function () {
          global.FieldHostDesktop?.refresh?.();
        });
      } else if (act === "icons") {
        saveSettings({ show_desktop_icons: !(state.settings?.show_desktop_icons !== false) });
        document.getElementById("hd-icons")?.classList.toggle("hidden", state.settings?.show_desktop_icons === false);
      } else if (act === "display") openDisplaySettings();
      else if (act === "personalize") launch({ id: "control-panel", name: "Control Panel", exec: "/control-panel?tab=personalize" });
      else if (act === "control") launch({ id: "control-panel", name: "Control Panel", exec: "/control-panel" });
      else if (act === "desktop") showDesktop();
    };
  }

  function isYieldedToHost() {
    return !!state.yieldedToHost || document.documentElement.classList.contains("field-yielded-to-host");
  }

  function applyYieldUi(on) {
    state.yieldedToHost = !!on;
    document.documentElement.classList.toggle("field-yielded-to-host", !!on);
    const chip = document.getElementById("nfs-yield-chip");
    if (chip) chip.classList.toggle("open", !!on);
    try {
      localStorage.setItem(YIELD_KEY, on ? "1" : "0");
    } catch (_) {}
  }

  function yieldToHost() {
    if (!confirm("Return to host OS? AmmoOS drops to background — security hold stays on, no freeze.")) return;
    showDesktop();
    closeAltTab();
    applyYieldUi(true);
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(function () {});
    }
    document.documentElement.classList.remove("nfs-kiosk");
    toast("Security hold active — host OS in front. Alt+Tab is yours.");
  }

  function returnFromHost() {
    applyYieldUi(false);
    document.documentElement.classList.add("nfs-kiosk");
    enterFullscreenDesktop();
    toast("AmmoOS restored — security hold unchanged.");
  }

  function restoreYieldFromStorage() {
    try {
      if (localStorage.getItem(YIELD_KEY) === "1") applyYieldUi(true);
    } catch (_) {}
  }

  function handlePower(action) {
    if (action === "yield-to-host" || action === "yield_to_host") {
      yieldToHost();
      return;
    }
    if (action === "return-from-host" || action === "return_from_host") {
      returnFromHost();
      return;
    }
    if (action === "monster") {
      global.FieldMonsterMonitor?.open?.();
      return;
    }
    if (action === "freeze-soft" || action === "freeze-mem" || action === "freeze_mem") {
      toast("Security hold — we no longer freeze the guest OS. Use Return to host OS.");
      global.FieldMonsterMonitor?.open?.();
      return;
    }
    if (action === "sign-out") {
      showDesktop();
      toast("Signed out — desktop shown");
      return;
    }
    if (action === "restart-nexus" || action === "restart") {
      if (!confirm("Restart NEXUS panel and services?")) return;
      fetch("/api/nexus/restart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy: "log" }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (j) {
          toast(j.ok ? "Restart requested" : j.error || "Restart failed");
        })
        .catch(function () {
          toast("Restart request failed");
        });
      return;
    }
    if (action === "close-os" || action === "close_os" || action === "quit-ammoos") {
      if (!confirm("Shut down AmmoOS? The host computer will stay on.")) return;
      fetch("/api/ammoos/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (j) {
          toast(j.message || (j.ok ? "AmmoOS closed" : j.error || "Close failed"));
          if (j.ok) {
            try {
              window.close();
            } catch (_) {}
          }
        })
        .catch(function () {
          toast("AmmoOS close request failed");
        });
      return;
    }
    if (action === "power-off" || action === "shutdown") {
      const bootOs = !!(state.hostPolicy?.boot_os || state.hostPolicy?.shell?.boot_os);
      if (!bootOs && state.hostPolicy?.window_mode !== false) {
        return handlePower("close-os");
      }
      if (!confirm("Shut down host?")) return;
      function requestShutdown(elevated) {
        return fetch("/api/field-host-freeze/shutdown", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: "disk", elevated: elevated, confirm: true }),
        }).then(function (r) {
          return r.json().then(function (j) {
            return { status: r.status, body: j };
          });
        });
      }
      requestShutdown(false)
        .then(function (res) {
          if (res.body && res.body.ok) {
            toast(res.body.message || "Shutdown requested");
            return;
          }
          if (res.body && res.body.error === "root_required") {
            return requestShutdown(true);
          }
          return fetch("/api/host/poweroff", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
            .then(function (r) {
              return r.json();
            })
            .then(function (j) {
              if (j.ok) toast(j.message || "Shutdown requested");
              else toast(j.error || res.body?.error || "Shutdown failed");
            });
        })
        .catch(function () {
          toast("Shutdown request failed");
        });
      return;
    }
    global.FieldHostDesktop?.handlePower?.(action);
  }

  function onMessage(ev) {
    const msg = ev.data;
    if (!msg || typeof msg !== "object") return;
    if (msg.type === "nexus:launch") {
      if (msg.url) {
        launch({ id: msg.id || "program", name: msg.name || "Program", exec: msg.url }, { newWindow: !!msg.newWindow });
      } else {
        launchView(msg.view || msg.id || "command", { newWindow: !!msg.newWindow });
      }
      return;
    }
    if (msg.type === "nexus:settings" && msg.settings) {
      applySettings({ settings: msg.settings });
      global.FieldDesktopScale?.apply?.(msg.settings);
      return;
    }
    if (msg.type === "nexus:focus") {
      const w = findWindow(msg.id || msg.view);
      if (w) focusWindow(w.id);
      return;
    }
    if (msg.type === "nexus:minimize") {
      if (state.activeId) minimizeWindow(state.activeId);
      return;
    }
    if (msg.type === "queen:shell") {
      if (msg.url) launch({ id: "queen-tab", name: "Queen", exec: msg.url });
    }
  }

  function mountShell(data) {
    state.hostPolicy = data?.policy || null;
    state.browserDisplay = data?.shell?.browser_display || {};
    const allPrograms = data?.programs_all || data?.programs || [];
    allPrograms.forEach(function (p) {
      state.programsById[p.id] = p;
      if (p.view) state.programsById[p.view.split("/")[0]] = p;
    });
    if (!document.getElementById("nfs-root")) {
      const wrap = document.createElement("div");
      wrap.innerHTML =
        '<div class="nfs-root" id="nfs-root" aria-live="polite"></div>' +
        '<div class="nfs-alt-overlay" id="nfs-alt-overlay"><div class="nfs-alt-grid" id="nfs-alt-grid"></div></div>' +
        '<div class="nfs-desktop-ctx" id="nfs-desktop-ctx" role="menu"></div>' +
        '<div class="nfs-props-modal" id="nfs-props-modal" role="dialog" aria-label="Taskbar properties">' +
        '<div class="nfs-modal-panel"><h2>Taskbar &amp; Start properties</h2><div id="nfs-props-body"></div>' +
        '<div class="nfs-modal-actions"><button type="button" id="nfs-props-cancel">Cancel</button>' +
        '<button type="button" class="primary" id="nfs-props-save">OK</button></div></div></div>' +
        '<div class="nfs-display-modal" id="nfs-display-modal" role="dialog" aria-label="Display settings">' +
        '<div class="nfs-modal-panel"><h2>Display</h2><div id="nfs-display-body"></div>' +
        '<div class="nfs-modal-actions"><button type="button" id="nfs-display-cancel">Cancel</button>' +
        '<button type="button" class="primary" id="nfs-display-save">Apply</button></div></div></div>' +
        '<button type="button" class="nfs-yield-chip" id="nfs-yield-chip" title="Restore AmmoOS">AmmoOS · security hold</button>';
      while (wrap.firstChild) document.body.appendChild(wrap.firstChild);
      $("nfs-yield-chip")?.addEventListener("click", returnFromHost);
      $("nfs-props-cancel")?.addEventListener("click", function () {
        $("nfs-props-modal")?.classList.remove("open");
      });
      $("nfs-display-cancel")?.addEventListener("click", function () {
        $("nfs-display-modal")?.classList.remove("open");
      });
      $("nfs-alt-overlay")?.addEventListener("click", function (ev) {
        if (ev.target.id === "nfs-alt-overlay") closeAltTab();
      });
    }

    const desktop = document.getElementById("hd-desktop");
    if (desktop) {
      desktop.addEventListener("contextmenu", function (ev) {
        if (ev.target.closest(".hd-icon") || ev.target.closest(".fsb-root") || ev.target.closest(".fsb-menu")) return;
        ev.preventDefault();
        openDesktopContext(ev.clientX, ev.clientY, null);
      });
      desktop.addEventListener("click", function (ev) {
        if (ev.target.closest(".hd-icon") || ev.target.closest(".fsb-root") || ev.target.closest(".fsb-menu")) return;
        if (state.windows.some(function (w) {
          return !w.minimized;
        })) showDesktop();
      });
    }

    document.addEventListener("keydown", function (ev) {
      if (isYieldedToHost()) return;
      if (!(state.settings?.alt_tab_enabled !== false)) return;
      if (ev.altKey && ev.key === "Tab") {
        ev.preventDefault();
        if (!state.altOpen) renderAltTab();
        else cycleAltTab(ev.shiftKey);
        return;
      }
      if (ev.key === "Escape") {
        closeAltTab();
        $("nfs-props-modal")?.classList.remove("open");
        $("nfs-display-modal")?.classList.remove("open");
        $("nfs-desktop-ctx")?.classList.remove("open");
      }
    });

    let peekTimer = null;
    document.addEventListener("mousemove", function (ev) {
      if (state.settings?.taskbar_auto_hide === false) return;
      if (state.settings?.taskbar_peek === false) return;
      if (ev.clientY >= innerHeight - 8) {
        document.documentElement.classList.add("nfs-taskbar-peek");
        clearTimeout(peekTimer);
        peekTimer = setTimeout(function () {
          document.documentElement.classList.remove("nfs-taskbar-peek");
        }, 1800);
      }
    });

    global.addEventListener("message", onMessage);
    enterFullscreenDesktop();
    bindFullscreenRetry();
    restoreYieldFromStorage();
    loadSettings().then(function () {
      bootDesktop(data);
    });
  }

  function enterFullscreenDesktop() {
    const root = document.documentElement;
    root.classList.add("nfs-fullscreen-desktop");
    root.classList.add("nfs-kiosk");
    try {
      if (!document.fullscreenElement && root.requestFullscreen) {
        root.requestFullscreen({ navigationUI: "hide" }).catch(function () {});
      }
    } catch (_) {}
  }

  function bindFullscreenRetry() {
    if (global.__nfsFsRetryBound) return;
    global.__nfsFsRetryBound = true;
    function retry() {
      if (!document.fullscreenElement) enterFullscreenDesktop();
    }
    document.addEventListener("pointerdown", retry, { once: true, capture: true });
    document.addEventListener("keydown", retry, { once: true, capture: true });
    setTimeout(retry, 400);
    setTimeout(retry, 1200);
  }

  function onBootSurface(data, app) {
    const launchUrl = String(data?.shell?.launch_url || data?.policy?.launch_url || "/field").trim() || "/field";
    const path = String(global.location?.pathname || "");
    if (path === launchUrl || path === "/field") return true;
    const exec = String(app?.exec || "").trim();
    if (exec === launchUrl || exec === "/field") return true;
    if (app?.id === "nexus-c2-desktop" && (path === "/field" || path.endsWith("/field"))) return true;
    return false;
  }

  function bootDesktop(data) {
    const boot = String(data?.shell?.boot_program ?? data?.policy?.boot_program ?? "").trim();
    const launchAtDesktop =
      data?.shell?.launch_at_c2_desktop !== false && data?.policy?.launch_at_c2_desktop !== false;
    if (boot && !launchAtDesktop) {
      const prog = (data?.programs || []).find(function (p) {
        return p.id === boot;
      });
      if (prog && !onBootSurface(data, prog)) {
        setTimeout(function () {
          launch(prog);
        }, 120);
      }
    }
    /* launch_at_c2_desktop: page is already /field — do not spawn a nested C2 window */
    const kiosk =
      data?.shell?.kiosk_launch !== false && data?.policy?.kiosk_launch !== false;
    const fs =
      kiosk ||
      state.settings?.fullscreen_desktop !== false ||
      data?.shell?.settings?.fullscreen_desktop !== false ||
      data?.shell?.fullscreen_desktop !== false ||
      data?.policy?.fullscreen_desktop !== false;
    if (fs) {
      enterFullscreenDesktop();
      bindFullscreenRetry();
    }
  }

  global.NexusFieldShell = {
    mount: mountShell,
    launch: launch,
    launchView: launchView,
    focus: focusWindow,
    minimize: minimizeWindow,
    close: closeWindow,
    toggle: toggleWindow,
    showDesktop: showDesktop,
    openStartProperties: openStartProperties,
    openDisplaySettings: openDisplaySettings,
    openDesktopContext: openDesktopContext,
    handlePower: handlePower,
    yieldToHost: yieldToHost,
    returnFromHost: returnFromHost,
    isYieldedToHost: isYieldedToHost,
    saveSettings: saveSettings,
    queueQueenNavigate: queueQueenNavigate,
    enterFullscreen: enterFullscreenDesktop,
    getSettings: function () {
      return state.settings;
    },
  };
})(window);