/**
 * AmmoNet bar — bottom anchor on AmmoOS desktop; taskbar + classic Start sit above.
 */
(function (global) {
  "use strict";

  const PANEL_ID = "ammoos-ammonet-display";
  const STRIP_ID = "h7-ammonet-strip";

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

  function stripLinks() {
    const base = panelBase();
    return (
      '<a href="' + esc(base + "/ammonet/") + '">ISP Hub</a>' +
      '<a href="' + esc(base + "/final-internet/") + '">Safe Fields</a>' +
      '<a href="' + esc(base + "/command/") + '">C2</a>' +
      '<a href="' + esc(base + "/desktop/") + '">AmmoOS</a>' +
      '<a href="' + esc(base + "/queen/browser.html") + '">Queen</a>' +
      '<a href="' + esc(base + "/field-znetwork-vault/") + '">Vault</a>'
    );
  }

  function buildStrip() {
    const assets = pagesRuntime() ? panelBase() + "/assets" : "/assets";
    return (
      '<div id="' +
      STRIP_ID +
      '" class="h7-ammonet-strip" role="navigation" aria-label="AmmoNet">' +
      '<img class="h7-ammonet-strip__icon" src="' +
      esc(assets + "/nexus-field-48.png") +
      '" alt="" width="18" height="18" />' +
      '<span class="h7-ammonet-strip__brand"><strong>AmmoNet</strong> · Layer 0</span>' +
      '<nav class="h7-ammonet-strip__links" aria-label="AmmoNet quick links">' +
      stripLinks() +
      "</nav>" +
      '<span class="h7-ammonet-strip__count" id="h7-ammonet-strip-count"></span>' +
      '<button type="button" class="h7-ammonet-strip__min" id="h7-ammonet-min" title="Minimize to taskbar" aria-label="Minimize AmmoNet">—</button>' +
      "</div>"
    );
  }

  function wireStrip(strip) {
    strip.querySelector("#h7-ammonet-min")?.addEventListener("click", function (ev) {
      ev.stopPropagation();
      minimize();
    });
    stampStatus();
  }

  async function stampStatus() {
    const countEl = document.getElementById("h7-ammonet-strip-count");
    if (!countEl) return;
    try {
      const r = await fetch(panelBase() + "/api/ammonet", { cache: "no-store", credentials: "same-origin" });
      if (r.ok) {
        const doc = await r.json();
        if (doc.surface_count) countEl.textContent = doc.surface_count + " surfaces";
        const brand = document.querySelector("#" + STRIP_ID + " .h7-ammonet-strip__brand");
        if (brand && doc.motto) brand.title = doc.motto;
      }
    } catch (_) {}
  }

  function enableLayout() {
    document.documentElement.classList.add("h7-final-internet");
    global.FieldScreenLayers?.markInsideOs?.(true);
  }

  function mountBottom() {
    if (state.mounted && !state.minimized) return;
    let strip = document.getElementById(STRIP_ID);
    if (!strip) {
      const mount = document.getElementById("h7-ammonet-mount") || document.getElementById("fsb-mount") || document.body;
      mount.insertAdjacentHTML("beforeend", buildStrip());
      strip = document.getElementById(STRIP_ID);
      wireStrip(strip);
    }
    strip.hidden = false;
    strip.classList.remove("h7-ammonet-strip--hidden");
    state.mounted = true;
    state.minimized = false;
    enableLayout();
    syncTaskbar(true);
  }

  /** @deprecated right-rail display — use mountBottom */
  function mount(monEl) {
    mountBottom();
    if (monEl) {
      monEl.hidden = true;
      monEl.classList.add("hd-monitor--hidden");
      monEl.innerHTML = "";
    }
  }

  function minimize() {
    state.minimized = true;
    const strip = document.getElementById(STRIP_ID);
    if (strip) {
      strip.hidden = true;
      strip.classList.add("h7-ammonet-strip--hidden");
    }
    syncTaskbar(false);
    global.FieldHostDesktop?.toast?.("AmmoNet · minimized to taskbar");
  }

  function restore() {
    mountBottom();
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
    mountBottom: mountBottom,
    minimize: minimize,
    restore: restore,
    toggle: toggle,
    isMinimized: isMinimized,
    PANEL_ID: PANEL_ID,
    taskApp: taskApp,
  };
})(typeof window !== "undefined" ? window : globalThis);