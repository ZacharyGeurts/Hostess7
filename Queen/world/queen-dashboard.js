/**
 * Queen Dashboard — empty frame; drag programs in; frameless panels; column grid; dblclick fullscreen.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "queen-dashboard-v1";
  const $ = (id) => document.getElementById(id);

  const state = {
    columns: "auto",
    panels: [],
    fullscreenId: null,
    drag: null,
  };

  function uid() {
    return "p_" + Math.random().toString(36).slice(2, 10);
  }

  function status(msg) {
    const el = $("qdash-status");
    if (el) el.textContent = msg || "";
  }

  function save() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ columns: state.columns, panels: state.panels }),
      );
    } catch (_) { /* ignore */ }
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const doc = JSON.parse(raw);
      if (doc.columns) state.columns = String(doc.columns);
      if (Array.isArray(doc.panels)) state.panels = doc.panels;
    } catch (_) { /* ignore */ }
  }

  function resolveUrl(raw) {
    const s = String(raw || "").trim();
    if (!s) return null;
    if (s.startsWith("queen://")) {
      const path = s.replace(/^queen:\/\//, "");
      if (path === "terminal") return "/world/queen-gnu-terminal-embed.html";
      if (path === "files") return "/world/queen-files.html";
      if (path === "gameroom") return "/world/queen-game-room.html";
      if (path === "field-gimp" || path === "ammoos-image") {
        const port = document.body?.dataset?.nexusPanelPort || "9477";
        return `http://127.0.0.1:${port}/field-gimp`;
      }
      return `/world/?dock=${encodeURIComponent(path)}`;
    }
    if (s.startsWith("/")) return s;
    if (/^https?:\/\//i.test(s)) return s;
    return null;
  }

  function panelTitle(url) {
    try {
      const u = new URL(url, location.origin);
      const base = u.pathname.split("/").filter(Boolean).pop() || u.hostname;
      return decodeURIComponent(base.replace(/\.html$/, ""));
    } catch (_) {
      return "Panel";
    }
  }

  function updateEmpty() {
    const empty = $("qdash-empty");
    if (empty) empty.style.display = state.panels.length ? "none" : "flex";
  }

  function applyColumns() {
    const grid = $("qdash-grid");
    const sel = $("qdash-cols");
    if (!grid) return;
    const cols = state.columns === "auto" ? "auto" : state.columns;
    grid.dataset.cols = cols;
    if (sel) sel.value = String(state.columns);
  }

  function createIframe(url) {
    const iframe = document.createElement("iframe");
    iframe.className = "qdash-panel-view";
    iframe.src = url;
    iframe.title = panelTitle(url);
    iframe.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation",
    );
    return iframe;
  }

  function renderPanel(panel) {
    const el = document.createElement("div");
    el.className = "qdash-panel";
    el.dataset.id = panel.id;
    if (panel.free) {
      el.classList.add("qdash-free");
      if (panel.x != null) el.style.left = panel.x + "px";
      if (panel.y != null) el.style.top = panel.y + "px";
    }
    el.appendChild(createIframe(panel.url));
    const grip = document.createElement("div");
    grip.className = "qdash-panel-grip";
    grip.title = "Drag to move · double-click fullscreen · click to use panel";
    grip.addEventListener("pointerdown", (ev) => onPanelPointerDown(ev, panel.id));
    grip.addEventListener("dblclick", (ev) => onPanelDblClick(ev, panel.id));
    grip.addEventListener("click", (ev) => {
      if (state.drag?.moved) return;
      ev.stopPropagation();
      el.classList.add("qdash-active");
      status(`Using ${panel.title} — click grip again to move`);
      window.setTimeout(() => el.classList.remove("qdash-active"), 8000);
    });
    el.appendChild(grip);
    return el;
  }

  function renderAll() {
    const grid = $("qdash-grid");
    if (!grid) return;
    grid.innerHTML = "";
    state.panels.forEach((p) => grid.appendChild(renderPanel(p)));
    updateEmpty();
    applyColumns();
  }

  function addPanel(url, opts = {}) {
    const resolved = resolveUrl(url);
    if (!resolved) {
      status("Could not open — drop a program link or URL");
      return null;
    }
    const panel = {
      id: uid(),
      url: resolved,
      title: opts.title || panelTitle(resolved),
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

  function removePanel(id) {
    state.panels = state.panels.filter((p) => p.id !== id);
    if (state.fullscreenId === id) exitFullscreen();
    save();
    renderAll();
  }

  function enterFullscreen(id) {
    const panel = state.panels.find((p) => p.id === id);
    if (!panel) return;
    const win = $("qdash-window");
    const layer = $("qdash-fs-layer");
    const host = $("qdash-fs-panel");
    const gridEl = document.querySelector(`.qdash-panel[data-id="${id}"]`);
    const iframe = gridEl?.querySelector("iframe");
    if (!win || !layer || !host || !iframe) return;

    state.fullscreenId = id;
    host.innerHTML = "";
    host.appendChild(iframe);
    win.classList.add("qdash-fs-active");
    layer.hidden = false;
    status(`Fullscreen — ${panel.title}`);
  }

  function exitFullscreen() {
    if (!state.fullscreenId) return;
    const id = state.fullscreenId;
    const host = $("qdash-fs-panel");
    const iframe = host?.querySelector("iframe");
    const gridEl = document.querySelector(`.qdash-panel[data-id="${id}"]`);
    if (iframe && gridEl) gridEl.appendChild(iframe);

    $("qdash-window")?.classList.remove("qdash-fs-active");
    const layer = $("qdash-fs-layer");
    if (layer) layer.hidden = true;
    state.fullscreenId = null;
    status("Back to dashboard");
  }

  function toggleFullscreen(id) {
    if (state.fullscreenId === id) exitFullscreen();
    else {
      if (state.fullscreenId) exitFullscreen();
      enterFullscreen(id);
    }
  }

  function onPanelDblClick(ev, id) {
    if (state.drag?.moved) return;
    ev.preventDefault();
    ev.stopPropagation();
    toggleFullscreen(id);
  }

  function onPanelPointerDown(ev, id) {
    if (state.fullscreenId) return;
    if (ev.button !== 0) return;
    const panel = ev.currentTarget.closest(".qdash-panel");
    if (!panel) return;
    const grid = $("qdash-grid");
    if (!grid) return;

    const rect = panel.getBoundingClientRect();
    const gridRect = grid.getBoundingClientRect();
    state.drag = {
      id,
      startX: ev.clientX,
      startY: ev.clientY,
      moved: false,
      panelEl: panel,
      placeholder: null,
    };

    panel.classList.add("qdash-dragging");
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
        panel.classList.add("qdash-free");
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

      const target = document.elementFromPoint(e.clientX, e.clientY);
      document.querySelectorAll(".qdash-slot-target").forEach((n) => n.classList.remove("qdash-slot-target"));
      const slot = target?.closest?.(".qdash-panel:not(.qdash-dragging)");
      if (slot) slot.classList.add("qdash-slot-target");
    };

    const onUp = (e) => {
      panel.classList.remove("qdash-dragging");
      try {
        panel.releasePointerCapture(e.pointerId);
      } catch (_) { /* ignore */ }
      document.querySelectorAll(".qdash-slot-target").forEach((n) => n.classList.remove("qdash-slot-target"));

      if (state.drag?.moved) {
        const target = document.elementFromPoint(e.clientX, e.clientY);
        const swapEl = target?.closest?.(".qdash-panel:not(.qdash-dragging)");
        if (swapEl && swapEl.dataset.id !== id) {
          const a = state.panels.findIndex((x) => x.id === id);
          const b = state.panels.findIndex((x) => x.id === swapEl.dataset.id);
          if (a >= 0 && b >= 0) {
            const tmp = state.panels[a];
            state.panels[a] = state.panels[b];
            state.panels[b] = tmp;
            const pa = state.panels[a];
            const pb = state.panels[b];
            pa.free = false;
            pb.free = false;
            pa.x = pa.y = pb.x = pb.y = null;
            save();
            renderAll();
          }
        } else {
          save();
        }
      }
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
        if (doc.url) return doc.url;
      } catch (_) { /* ignore */ }
    }
    const uri = dt.getData("text/uri-list") || dt.getData("text/plain");
    const line = uri.split(/\r?\n/).find((l) => l && !l.startsWith("#"));
    return line || null;
  }

  function setupDrop() {
    const canvas = $("qdash-canvas");
    if (!canvas) return;

    canvas.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "copy";
      canvas.classList.add("qdash-dragover");
    });
    canvas.addEventListener("dragleave", () => canvas.classList.remove("qdash-dragover"));
    canvas.addEventListener("drop", (ev) => {
      ev.preventDefault();
      canvas.classList.remove("qdash-dragover");
      const url = parseDrop(ev.dataTransfer);
      if (url) addPanel(url);
    });
  }

  function setupProgramDragOut() {
    document.addEventListener("dragstart", (ev) => {
      const node = ev.target.closest("[data-queen-program-url]");
      if (!node) return;
      const url = node.getAttribute("data-queen-program-url");
      const name = node.getAttribute("data-queen-program-name") || "Program";
      if (!url) return;
      ev.dataTransfer.setData("text/uri-list", url);
      ev.dataTransfer.setData(
        "application/x-queen-program",
        JSON.stringify({ url, name }),
      );
      ev.dataTransfer.effectAllowed = "copy";
    });
  }

  function setupToolbar() {
    $("qdash-cols")?.addEventListener("change", (ev) => {
      state.columns = ev.target.value;
      save();
      applyColumns();
    });
    $("qdash-clear")?.addEventListener("click", () => {
      if (!state.panels.length) return;
      if (!confirm("Clear all dashboard panels?")) return;
      state.panels = [];
      exitFullscreen();
      save();
      renderAll();
      status("Dashboard cleared");
    });
    $("qdash-fs-panel")?.addEventListener("dblclick", () => {
      if (state.fullscreenId) exitFullscreen();
    });
    $("qdash-fs-layer")?.addEventListener("dblclick", (ev) => {
      if (ev.target.id === "qdash-fs-layer" || ev.target.classList.contains("qdash-fs-hint")) {
        exitFullscreen();
      }
    });
  }

  function ingestQuery() {
    const params = new URLSearchParams(location.search);
    const add = params.get("add") || params.get("url");
    if (add) addPanel(add);
  }

  async function loadDefaultScreens() {
    if (state.panels.length) return;
    try {
      const r = await fetch("/api/queen-dashboard", { cache: "no-store" });
      const doc = await r.json();
      const pinned = (doc.screens || []).filter((s) => s.pinned);
      const list = pinned.length ? pinned : (doc.screens || []).slice(0, 8);
      list.forEach((s) => {
        const url = s.drag_url || s.url;
        if (url) addPanel(url, { title: s.name });
      });
      if (doc.g16?.profile) {
        status(`G16 ${doc.g16.profile} · ${doc.g16.g16_version || ""} · ${list.length} diagnostic panels`);
      }
    } catch (_) {
      status("Ready — drag programs in");
    }
  }

  function init() {
    load();
    setupDrop();
    setupProgramDragOut();
    setupToolbar();
    renderAll();
    ingestQuery();
    if (!state.panels.length && !new URLSearchParams(location.search).get("add")) {
      loadDefaultScreens();
    } else {
      status(state.panels.length ? `${state.panels.length} panel(s)` : "Ready — drag programs in");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.QueenDashboard = { addPanel, removePanel, state };
})();