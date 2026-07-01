/**
 * Queen Dashboard flyout — taskbar mouseover grid of diagnostic screens.
 */
(function () {
  "use strict";

  const HOVER_OPEN_MS = 180;
  const HOVER_CLOSE_MS = 420;
  const STORAGE_KEY = "queen-dashboard-flyout-v1";

  let anchor = null;
  let openTimer = null;
  let closeTimer = null;
  let loaded = false;
  let state = { columns: "3", screens: [], g16: null };

  function $(id) {
    return typeof id === "string" ? document.getElementById(id) : id;
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ columns: state.columns }));
    } catch (_) { /* ignore */ }
  }

  function loadPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const doc = JSON.parse(raw);
      if (doc.columns) state.columns = String(doc.columns);
    } catch (_) { /* ignore */ }
  }

  function setOpen(on) {
    if (!anchor) return;
    anchor.classList.toggle("qdf-open", !!on);
    if (on && !loaded) fetchScreens();
  }

  function scheduleOpen() {
    clearTimeout(closeTimer);
    clearTimeout(openTimer);
    openTimer = setTimeout(() => setOpen(true), HOVER_OPEN_MS);
  }

  function scheduleClose() {
    clearTimeout(openTimer);
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => setOpen(false), HOVER_CLOSE_MS);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function renderG16(g16) {
    const el = $("qdf-g16");
    if (!el || !g16) return;
    const prof = g16.profile || "field_opt";
    const ver = g16.g16_version || "?";
    const ready = g16.ready ? "g16 ready" : "g16 hold";
    el.textContent = `${prof} · ${ver} · ${ready}`;
    el.className = "qdf-g16 " + (g16.ready ? "ok" : "bad");
  }

  function renderGrid() {
    const grid = $("qdf-grid");
    if (!grid) return;
    grid.dataset.cols = state.columns;
    grid.innerHTML = "";
    state.screens.forEach((s) => {
      const tile = document.createElement("div");
      tile.className = "qdf-tile";
      tile.title = s.name || s.id;
      tile.dataset.url = s.url || s.drag_url || "";
      const iframe = document.createElement("iframe");
      iframe.src = s.url || "";
      iframe.loading = "lazy";
      iframe.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups allow-modals",
      );
      tile.appendChild(iframe);
      const label = document.createElement("span");
      label.className = "qdf-tile-label";
      label.textContent = s.name || s.id;
      tile.appendChild(label);
      tile.addEventListener("click", () => {
        const url = tile.dataset.url;
        if (!url) return;
        if (globalThis.QueenOS?.browser?.newTab) {
          globalThis.QueenOS.browser.newTab(url);
        } else {
          window.open(url, "_blank", "noopener");
        }
      });
      tile.addEventListener("dragstart", (ev) => {
        const url = s.drag_url || s.url;
        if (!url) return;
        ev.dataTransfer.setData("text/uri-list", url);
        ev.dataTransfer.setData(
          "application/x-queen-program",
          JSON.stringify({ url, name: s.name || s.id }),
        );
        ev.dataTransfer.effectAllowed = "copy";
      });
      tile.draggable = true;
      grid.appendChild(tile);
    });
  }

  async function fetchScreens() {
    try {
      const r = await fetch("/api/nexus-c2?flyout=1", { cache: "no-store" });
      const doc = await r.json();
      state.screens = doc.panels || doc.screens || [];
      state.g16 = doc.g16 || null;
      if (!state.columns || state.columns === "3") {
        state.columns = String(doc.flyout_columns || state.columns || "3");
      }
      loaded = true;
      renderG16(state.g16);
      renderGrid();
      const foot = $("qdf-foot");
      if (foot && (doc.c2_url || doc.dashboard_url)) {
        const c2 = doc.c2_url || doc.dashboard_url;
        foot.innerHTML =
          `${state.screens.length} C2 panel thumbnail(s) · ` +
          `<a href="${esc(c2)}">open AmmoOS C2</a> · ` +
          `drag into C2 grid`;
      }
    } catch (e) {
      const foot = $("qdf-foot");
      if (foot) foot.textContent = "Dashboard flyout unavailable — " + String(e);
    }
  }

  function buildAnchor(host) {
    anchor = document.createElement("div");
    anchor.className = "qdf-anchor";
    anchor.id = "qdf-anchor";
    anchor.innerHTML =
      '<button type="button" class="qdf-btn" id="qdf-btn" aria-haspopup="true" aria-expanded="false">C2</button>' +
      '<div class="qdf-flyout" id="qdf-flyout" role="dialog" aria-label="AmmoOS C2 panels">' +
      '<div class="qdf-head"><strong>AmmoOS C2</strong><span class="qdf-g16" id="qdf-g16">G16…</span></div>' +
      '<div class="qdf-toolbar"><label>Columns <select id="qdf-cols"><option value="auto">Auto</option>' +
      '<option value="2">2</option><option value="3" selected>3</option><option value="4">4</option></select></label>' +
      '<button type="button" id="qdf-reload">Reload</button></div>' +
      '<div class="qdf-grid" id="qdf-grid" data-cols="3"></div>' +
      '<p class="qdf-foot" id="qdf-foot">Hover taskbar · panel thumbnails · double-click for fullscreen</p>' +
      "</div>";
    host.appendChild(anchor);

    anchor.addEventListener("mouseenter", scheduleOpen);
    anchor.addEventListener("mouseleave", scheduleClose);
    anchor.addEventListener("focusin", scheduleOpen);
    anchor.addEventListener("focusout", (ev) => {
      if (!anchor.contains(ev.relatedTarget)) scheduleClose();
    });

    $("qdf-cols")?.addEventListener("change", (ev) => {
      state.columns = ev.target.value;
      save();
      renderGrid();
    });
    $("qdf-reload")?.addEventListener("click", () => {
      loaded = false;
      fetchScreens();
    });
  }

  function mount() {
    loadPrefs();
    const hosts = [
      document.getElementById("qd-tray-tools"),
      document.querySelector(".qb-brand-strip"),
      document.querySelector(".qb-row--bookmarks"),
      document.querySelector(".qd-taskbar"),
    ].filter(Boolean);
    const host = hosts[0];
    if (!host || document.getElementById("qdf-anchor")) return;
    buildAnchor(host);
    const sel = $("qdf-cols");
    if (sel) sel.value = state.columns;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  globalThis.QueenDashboardFlyout = { fetchScreens, setOpen, state };
})();