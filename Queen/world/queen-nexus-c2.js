/**
 * AmmoOS C2 — programmatic panel grid; chromeless thumbnails, no window chrome.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "queen-nexus-c2-v1";
  const API = "/api/nexus-c2";
  const $ = (id) => document.getElementById(id);

  const state = {
    columns: "auto",
    panels: [],
    fullscreenId: null,
    drag: null,
  };

  function uid() {
    return "c2_" + Math.random().toString(36).slice(2, 10);
  }

  function status(msg) {
    const el = $("qnc2-status");
    if (el) el.textContent = msg || "";
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ columns: state.columns, panels: state.panels }));
    } catch (_) {}
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const doc = JSON.parse(raw);
      if (doc.columns) state.columns = String(doc.columns);
      if (Array.isArray(doc.panels)) state.panels = doc.panels;
    } catch (_) {}
  }

  function resolveUrl(raw) {
    const s = String(raw || "").trim();
    if (!s) return null;
    if (s.startsWith("queen://")) {
      const path = s.replace(/^queen:\/\//, "");
      if (path === "terminal") return "/world/queen-gnu-terminal-embed.html";
      if (path === "files") return "/world/queen-files.html";
      if (path === "gameroom") return "/world/queen-game-room.html";
      if (path === "nexus-c2" || path === "c2") return "/world/queen-nexus-c2.html";
      if (path === "thermal" || path === "thermal-manager") return "/world/queen-thermal-manager.html";
      if (path === "final-ear" || path === "final-ear-manager" || path === "earball") return "/world/queen-final-ear-manager.html";
      if (path === "final-mouth" || path === "final-mouth-manager" || path === "mouthball") return "/world/queen-final-mouth-manager.html";
      if (path === "hostess7-hub" || path === "hostess7" || path === "hostess" || path === "ai-training") return "/world/queen-hostess7-hub.html";
      if (path === "command" || path === "field-command") return "http://127.0.0.1:9477/command";
      if (path === "os" || path === "start" || path === "desktop") return "/world/queen-start.html";
      const port = document.body?.dataset?.nexusPanelPort || "9477";
      if (path === "field-gimp" || path === "ammoos-image") return `http://127.0.0.1:${port}/field-gimp`;
      return `/world/?dock=${encodeURIComponent(path)}`;
    }
    if (s.startsWith("/")) return s;
    if (/^https?:\/\//i.test(s)) return s;
    return null;
  }

  function panelTitle(url) {
    try {
      const u = new URL(url, location.origin);
      return decodeURIComponent((u.pathname.split("/").filter(Boolean).pop() || u.hostname).replace(/\.html$/, ""));
    } catch (_) {
      return "Panel";
    }
  }

  function updateEmpty() {
    const empty = $("qnc2-empty");
    if (empty) empty.style.display = state.panels.length ? "none" : "flex";
  }

  function applyColumns() {
    const grid = $("qnc2-grid");
    const sel = $("qnc2-cols");
    if (!grid) return;
    grid.dataset.cols = state.columns === "auto" ? "auto" : state.columns;
    if (sel) sel.value = String(state.columns);
  }

  function createIframe(url) {
    const iframe = document.createElement("iframe");
    iframe.className = "qnc2-view";
    iframe.src = url;
    iframe.title = panelTitle(url);
    iframe.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation",
    );
    return iframe;
  }

  function renderPanel(panel) {
    const el = document.createElement("article");
    el.className = "qnc2-panel" + (panel.chromeless ? " chromeless" : "");
    el.dataset.id = panel.id;
    if (panel.free) {
      el.classList.add("qnc2-free");
      if (panel.x != null) el.style.left = panel.x + "px";
      if (panel.y != null) el.style.top = panel.y + "px";
    }
    const grip = document.createElement("div");
    grip.className = "qnc2-grip";
    grip.textContent = panel.title || panelTitle(panel.url);
    grip.title = "Drag · double-click fullscreen";
    grip.addEventListener("pointerdown", (ev) => onPanelPointerDown(ev, panel.id));
    grip.addEventListener("dblclick", (ev) => onPanelDblClick(ev, panel.id));
    el.appendChild(grip);
    el.appendChild(createIframe(panel.url));
    return el;
  }

  function renderAll() {
    const grid = $("qnc2-grid");
    if (!grid) return;
    grid.innerHTML = "";
    state.panels.forEach((p) => grid.appendChild(renderPanel(p)));
    updateEmpty();
    applyColumns();
  }

  function addPanel(url, opts = {}) {
    const resolved = resolveUrl(url);
    if (!resolved) {
      status("Could not open panel");
      return null;
    }
    const panel = {
      id: uid(),
      url: resolved,
      title: opts.title || panelTitle(resolved),
      chromeless: opts.chromeless !== false,
      free: false,
      x: null,
      y: null,
    };
    state.panels.push(panel);
    save();
    renderAll();
    status(`Added ${panel.title}`);
    return panel;
  }

  function enterFullscreen(id) {
    const panel = state.panels.find((p) => p.id === id);
    if (!panel) return;
    const shell = $("qnc2-window");
    const layer = $("qnc2-fs-layer");
    const host = $("qnc2-fs-panel");
    const gridEl = document.querySelector(`.qnc2-panel[data-id="${id}"]`);
    const iframe = gridEl?.querySelector("iframe");
    if (!shell || !layer || !host || !iframe) return;
    state.fullscreenId = id;
    host.innerHTML = "";
    host.appendChild(iframe);
    shell.classList.add("qnc2-fs-active");
    layer.hidden = false;
    status(`Fullscreen — ${panel.title}`);
  }

  function exitFullscreen() {
    if (!state.fullscreenId) return;
    const id = state.fullscreenId;
    const host = $("qnc2-fs-panel");
    const iframe = host?.querySelector("iframe");
    const gridEl = document.querySelector(`.qnc2-panel[data-id="${id}"]`);
    if (iframe && gridEl) {
      const grip = gridEl.querySelector(".qnc2-grip");
      if (grip) gridEl.insertBefore(iframe, grip);
      else gridEl.appendChild(iframe);
    }
    $("qnc2-window")?.classList.remove("qnc2-fs-active");
    const layer = $("qnc2-fs-layer");
    if (layer) layer.hidden = true;
    state.fullscreenId = null;
    status("Back to C2 grid");
  }

  function onPanelDblClick(ev, id) {
    if (state.drag?.moved) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (state.fullscreenId === id) exitFullscreen();
    else {
      if (state.fullscreenId) exitFullscreen();
      enterFullscreen(id);
    }
  }

  function onPanelPointerDown(ev, id) {
    if (state.fullscreenId || ev.button !== 0) return;
    const panel = ev.currentTarget.closest(".qnc2-panel");
    const grid = $("qnc2-grid");
    if (!panel || !grid) return;
    const rect = panel.getBoundingClientRect();
    const gridRect = grid.getBoundingClientRect();
    state.drag = { id, startX: ev.clientX, startY: ev.clientY, moved: false, panelEl: panel };
    panel.classList.add("qnc2-dragging");
    panel.setPointerCapture(ev.pointerId);

    const onMove = (e) => {
      if (!state.drag || state.drag.id !== id) return;
      const dx = e.clientX - state.drag.startX;
      const dy = e.clientY - state.drag.startY;
      if (Math.abs(dx) + Math.abs(dy) > 6) state.drag.moved = true;
      if (!state.drag.moved) return;
      const p = state.panels.find((x) => x.id === id);
      if (p && !p.free) {
        p.free = true;
        panel.classList.add("qnc2-free");
        grid.appendChild(panel);
        p.x = rect.left - gridRect.left + grid.scrollLeft;
        p.y = rect.top - gridRect.top + grid.scrollTop;
      }
      if (p) {
        p.x = (p.x ?? 0) + e.movementX;
        p.y = (p.y ?? 0) + e.movementY;
        panel.style.left = p.x + "px";
        panel.style.top = p.y + "px";
      }
    };

    const onUp = (e) => {
      panel.classList.remove("qnc2-dragging");
      try { panel.releasePointerCapture(e.pointerId); } catch (_) {}
      if (state.drag?.moved) save();
      state.drag = null;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  }

  function parseDrop(dt) {
    const queen = dt.getData("application/x-queen-program");
    if (queen) {
      try {
        const doc = JSON.parse(queen);
        if (doc.url) return doc;
      } catch (_) {}
    }
    const uri = dt.getData("text/uri-list") || dt.getData("text/plain");
    const line = uri.split(/\r?\n/).find((l) => l && !l.startsWith("#"));
    return line ? { url: line } : null;
  }

  function setupDrop() {
    const canvas = $("qnc2-canvas");
    if (!canvas) return;
    canvas.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "copy";
      canvas.classList.add("qnc2-dragover");
    });
    canvas.addEventListener("dragleave", () => canvas.classList.remove("qnc2-dragover"));
    canvas.addEventListener("drop", (ev) => {
      ev.preventDefault();
      canvas.classList.remove("qnc2-dragover");
      const doc = parseDrop(ev.dataTransfer);
      if (doc?.url) addPanel(doc.url, { title: doc.name, chromeless: doc.chromeless });
    });
  }

  function renderG16(g16) {
    const el = $("qnc2-g16");
    if (!el || !g16) return;
    const prof = g16.profile || "field_opt";
    const ver = g16.g16_version || "?";
    el.textContent = `${prof} · ${ver}`;
    el.className = "qnc2-g16 " + (g16.ready ? "ok" : "bad");
  }

  async function loadCatalog() {
    if (state.panels.length) return;
    try {
      const r = await fetch(API, { cache: "no-store" });
      const doc = await r.json();
      renderG16(doc.g16);
      const list = (doc.panels || doc.screens || []).filter((s) => s.pinned);
      const seed = list.length ? list : (doc.panels || doc.screens || []).slice(0, 10);
      seed.forEach((s) => {
        const url = s.drag_url || s.url;
        if (url) {
          state.panels.push({
            id: uid(),
            url,
            title: s.name || s.id,
            chromeless: s.chromeless !== false,
            free: false,
            x: null,
            y: null,
          });
        }
      });
      save();
      renderAll();
      status(`Programmatic C2 · ${seed.length} panel(s) · ${doc.theme || "nexus_military_v8"}`);
    } catch (_) {
      status("Ready — drag panel thumbnails in");
    }
  }

  function setupToolbar() {
    $("qnc2-cols")?.addEventListener("change", (ev) => {
      state.columns = ev.target.value;
      save();
      applyColumns();
    });
    $("qnc2-clear")?.addEventListener("click", () => {
      if (!state.panels.length || !confirm("Clear all C2 panels?")) return;
      state.panels = [];
      exitFullscreen();
      save();
      renderAll();
      status("C2 grid cleared");
    });
    $("qnc2-reload")?.addEventListener("click", () => {
      state.panels = [];
      save();
      loadCatalog();
    });
    $("qnc2-fs-layer")?.addEventListener("dblclick", (ev) => {
      if (ev.target.id === "qnc2-fs-layer" || ev.target.classList.contains("qnc2-fs-hint")) exitFullscreen();
    });
  }

  function init() {
    document.documentElement.classList.add("nexus-military-v8");
    load();
    setupDrop();
    setupToolbar();
    renderAll();
    const params = new URLSearchParams(location.search);
    const add = params.get("add") || params.get("url");
    if (add) addPanel(add);
    else if (!state.panels.length) loadCatalog();
    else status(`${state.panels.length} panel thumbnail(s)`);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.QueenNexusC2 = { addPanel, state, API };
  window.QueenDashboard = window.QueenNexusC2;
})();