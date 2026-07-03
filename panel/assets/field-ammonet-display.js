/**
 * AmmoNet display panel — right rail on AmmoOS desktop, layer 0, minimize to taskbar.
 */
(function (global) {
  "use strict";

  const PANEL_ID = "ammoos-ammonet-display";

  const state = { minimized: false, mounted: false };

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function panelBase() {
    if (pagesRuntime()) return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
    return "http://127.0.0.1:9477";
  }

  function ammonetUrl() {
    if (pagesRuntime()) return panelBase() + "/ammonet/";
    return panelBase() + "/ammonet-field";
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function taskApp() {
    const assets = pagesRuntime() ? panelBase() + "/assets" : "/assets";
    return {
      id: PANEL_ID,
      name: "AmmoNet",
      exec: ammonetUrl(),
      icon_url: assets + "/nexus-field-48.png",
      shellWin: PANEL_ID,
      os_layer: 0,
      pinned: true,
      live: true,
    };
  }

  function syncTaskbar(active) {
    const app = taskApp();
    if (active) global.FieldStartbar?.trackRunning?.(app);
    global.FieldStartbar?.syncShellTasks?.(
      [app].concat(
        (global.NexusFieldShell?.listWindows?.() || [])
          .filter(function (w) {
            return !w.minimized;
          })
          .map(function (w) {
            return {
              id: w.appId || w.key,
              name: w.name,
              icon_url: w.icon_url,
              exec: w.url,
              shellWin: w.id,
            };
          })
      ),
      active ? PANEL_ID : null
    );
  }

  function wireChrome(root) {
    root.querySelector(".h7ad-min")?.addEventListener("click", function (ev) {
      ev.stopPropagation();
      minimize();
    });
    root.querySelector(".h7ad-close")?.addEventListener("click", function (ev) {
      ev.stopPropagation();
      minimize();
    });
    root.querySelector(".h7ad-restore")?.addEventListener("click", function () {
      restore();
    });
  }

  function buildChrome() {
    const theme = document.documentElement.dataset.osTheme || document.documentElement.dataset.ammoosTheme || "ammoos";
    return (
      '<div class="h7ad-root" data-os-layer="0" data-theme="' +
      esc(theme) +
      '">' +
      '<header class="h7ad-chrome" role="banner">' +
      '<img class="h7ad-icon" src="' +
      esc((pagesRuntime() ? panelBase() + "/assets" : "/assets") + "/nexus-field-48.png") +
      '" alt="" width="20" height="20" />' +
      '<span class="h7ad-title">AmmoNet · Layer 0</span>' +
      '<nav class="h7ad-menus" aria-label="AmmoNet menus">' +
      '<button type="button" class="h7ad-menu-btn" data-nav="hub">ISP Hub</button>' +
      '<button type="button" class="h7ad-menu-btn" data-nav="fields">Safe Fields</button>' +
      '<button type="button" class="h7ad-menu-btn" data-nav="vault">Vault</button>' +
      "</nav>" +
      '<button type="button" class="h7ad-win h7ad-min" title="Minimize to taskbar" aria-label="Minimize">—</button>' +
      '<button type="button" class="h7ad-win h7ad-close" title="Minimize to taskbar" aria-label="Close panel">×</button>' +
      "</header>" +
      '<div class="h7ad-frame"><iframe class="h7ad-view" title="AmmoNet ISP Hub" loading="lazy"></iframe></div>' +
      "</div>"
    );
  }

  function navFrame(root, kind) {
    const frame = root.querySelector(".h7ad-view");
    if (!frame) return;
    const base = panelBase();
    if (kind === "fields") frame.src = pagesRuntime() ? base + "/final-internet/" : base + "/final-internet";
    else if (kind === "vault") frame.src = pagesRuntime() ? base + "/field-znetwork-vault/" : base + "/field-znetwork-vault";
    else frame.src = ammonetUrl();
  }

  function mount(monEl) {
    if (!monEl) return;
    state.mounted = true;
    state.minimized = false;
    monEl.hidden = false;
    monEl.classList.remove("hd-monitor--hidden");
    monEl.setAttribute("aria-label", "AmmoNet · Layer 0 display");
    monEl.innerHTML = buildChrome();
    const root = monEl.querySelector(".h7ad-root");
    const frame = monEl.querySelector(".h7ad-view");
    if (frame) frame.src = ammonetUrl();
    wireChrome(monEl);
    root?.querySelectorAll(".h7ad-menu-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        navFrame(monEl, btn.dataset.nav);
      });
    });
    global.FieldScreenLayers?.markInsideOs?.(true);
    global.FieldInternetUnified?.wire?.();
    syncTaskbar(true);
  }

  function minimize() {
    state.minimized = true;
    const mon = document.getElementById("hd-monitor");
    if (mon) {
      mon.classList.add("hd-monitor--hidden");
      mon.hidden = true;
    }
    syncTaskbar(false);
    global.FieldHostDesktop?.toast?.("AmmoNet · minimized to taskbar");
  }

  function restore() {
    state.minimized = false;
    const mon = document.getElementById("hd-monitor");
    if (!mon) return;
    if (!state.mounted) mount(mon);
    mon.classList.remove("hd-monitor--hidden");
    mon.hidden = false;
    global.FieldScreenLayers?.markInsideOs?.(true);
    syncTaskbar(true);
    global.FieldHostDesktop?.toast?.("AmmoNet · Layer 0");
  }

  function toggle() {
    if (state.minimized) restore();
    else minimize();
  }

  function isMinimized() {
    return state.minimized;
  }

  global.FieldAmmoNetDisplay = {
    mount: mount,
    minimize: minimize,
    restore: restore,
    toggle: toggle,
    isMinimized: isMinimized,
    PANEL_ID: PANEL_ID,
    taskApp: taskApp,
  };
})(typeof window !== "undefined" ? window : globalThis);