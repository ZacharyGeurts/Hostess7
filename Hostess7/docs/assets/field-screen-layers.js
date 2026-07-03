/**
 * Field screen layers — F9..F12 switch sovereign surfaces.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * IRONCLAD — F9..F12 FAST SWITCH PANEL (DO NOT REMOVE)
 * Field One Only — AmmoOS anchors at layer -1 (boot home, no F-key).
 *   F9  → layer -3 · NEXUS C2
 *   F10 → layer -2 · DNS · KILROY lane
 *   F11 → Queen Browser · own browser space (shell window, not iframe stack)
 *   F12 → userland 2+ · repeat F12 cycles only layers that exist
 * Layer 0 = Broadcaster · AmmoNet · panel programs (themed menu chrome).
 * Protected by field-screen-layer/v1 — comment-protect this block on every edit.
 * ═══════════════════════════════════════════════════════════════════════════
 */
(function (global) {
  "use strict";

  /* DO NOT REMOVE — F-key layer map: F11 browser, F12 userland cycle. */
  const LAYER_META = {
    "-3": { label: "NEXUS C2", fkey: "F9", component: "queen-nexus-c2" },
    "-2": { label: "DNS · KILROY lane", fkey: "F10", component: "kilroy-home" },
    "-1": { label: "Field One · AmmoOS", fkey: null, component: "field-desktop" },
    "0": {
      label: "OS Software · Broadcaster · AmmoNet · Panels",
      fkey: null,
      inside_os: true,
      bundle: ["field-broadcaster", "ammonet-isp", "ammoos-ammonet-display"],
    },
    "1": { label: "Queen Browser", fkey: "F11", queen_browser: true, browser_space: true },
    warehouse: { label: "Archival Warehouse · Official", fkey: null, official: true, component: "ammoos-warehouse" },
  };

  /* DO NOT REMOVE — F9/F10 fixed; F11 Queen; F12 handled by cycleUserland(). */
  const FKEY_TO_LAYER = { F9: -3, F10: -2, F11: 1 };
  const FAST_SWITCH_LAYERS = [-3, -2, 1];
  const STACK_LAYERS = [-3, -2];
  const USERLAND_MIN = 2;

  const state = {
    active: -1,
    root: null,
    frames: {},
    wired: false,
    hud: null,
    fastSwitch: null,
    userlandCycleIdx: -1,
  };

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function panelBase() {
    if (pagesRuntime()) return global.HOSTESS7_PAGES_BASE || "/Hostess7";
    const port = document.body?.dataset?.nexusPanelPort || "9477";
    return "http://127.0.0.1:" + port;
  }

  function queenPagesBase() {
    if (pagesRuntime()) return (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/queen";
    return "/Hostess7/queen/world";
  }

  function layerUrl(layer) {
    const q = queenPagesBase();
    const p = panelBase();
    if (layer === 1) return q + "/browser.html";
    if (layer === -3) return q + "/queen-nexus-c2.html";
    if (layer === -2) return q + "/kilroy-home.html";
    if (layer === -1) return pagesRuntime() ? p + "/desktop/" : p + "/field";
    if (layer === "warehouse") return p + "/ammoos-warehouse/";
    return null;
  }

  function toast(msg) {
    global.FieldHostDesktop?.toast?.(msg);
  }

  function setDesktopVisible(visible) {
    const desktop = document.getElementById("hd-desktop");
    const monitor = document.getElementById("hd-monitor");
    document.documentElement.classList.toggle("fsl-desktop-hidden", !visible);
    if (desktop) {
      desktop.hidden = !visible;
      desktop.setAttribute("aria-hidden", visible ? "false" : "true");
    }
    if (monitor && !visible) monitor.hidden = true;
    if (visible) global.NexusFieldShell?.showDesktop?.();
  }

  function userlandLabel(layer) {
    return "Userland · L" + layer;
  }

  function updateHud(layer) {
    let hud = state.hud;
    if (!hud) {
      hud = document.getElementById("fsl-hud");
      if (!hud) {
        hud = document.createElement("div");
        hud.id = "fsl-hud";
        hud.className = "fsl-hud";
        hud.setAttribute("aria-live", "polite");
        document.body.appendChild(hud);
      }
      state.hud = hud;
    }
    const meta = LAYER_META[String(layer)] || {};
    const label = layer >= USERLAND_MIN ? userlandLabel(layer) : meta.label || "Field One";
    const fkey = meta.fkey ? " · " + meta.fkey : layer >= USERLAND_MIN ? " · F12" : "";
    hud.textContent = "Layer " + layer + " · " + label + fkey;
    hud.hidden = layer === -1 || layer === 0;
  }

  function listUserlandEntries() {
    const wins = global.NexusFieldShell?.listWindows?.() || [];
    return wins
      .filter(function (w) {
        return !w.minimized && (w.userlandLayer || 0) >= USERLAND_MIN;
      })
      .sort(function (a, b) {
        return (a.userlandLayer || 0) - (b.userlandLayer || 0);
      })
      .map(function (w) {
        return {
          layer: w.userlandLayer,
          id: w.id,
          label: w.name || "Program",
          win: w,
        };
      });
  }

  function focusUserlandEntry(entry) {
    const stack = ensureMount();
    stack.hidden = true;
    stack.setAttribute("aria-hidden", "true");
    setDesktopVisible(true);
    state.active = entry.layer;
    document.documentElement.dataset.fieldScreenLayer = String(entry.layer);
    document.documentElement.dataset.fieldLayer = String(entry.layer);
    global.NexusFieldShell?.focusWindow?.(entry.id);
    updateHud(entry.layer);
    updateFastSwitch(entry.layer);
    toast("Layer " + entry.layer + " · " + entry.label);
  }

  function cycleUserland() {
    const available = listUserlandEntries();
    if (!available.length) {
      toast("Userland · no layers active · Field One");
      return;
    }
    let idx = available.findIndex(function (e) {
      return e.layer === state.active;
    });
    if (idx < 0) idx = state.userlandCycleIdx;
    const next = (idx + 1) % available.length;
    state.userlandCycleIdx = next;
    focusUserlandEntry(available[next]);
  }

  /* DO NOT REMOVE — F9..F12 fast switch panel (click + keyboard). */
  function ensureFastSwitchPanel() {
    if (state.fastSwitch) return state.fastSwitch;
    let panel = document.getElementById("fsl-fast-switch");
    if (panel) {
      state.fastSwitch = panel;
      return panel;
    }
    panel = document.createElement("nav");
    panel.id = "fsl-fast-switch";
    panel.className = "fsl-fast-switch";
    panel.setAttribute("aria-label", "F9–F12 fast layer switch");
    panel.setAttribute("data-ironclad", "f9-f12-fast-switch");
    FAST_SWITCH_LAYERS.forEach(function (layer) {
      const meta = LAYER_META[String(layer)];
      if (!meta || !meta.fkey) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "fsl-fast-btn";
      btn.dataset.layer = String(layer);
      btn.title = meta.fkey + " · " + meta.label;
      btn.innerHTML =
        '<kbd class="fsl-fast-kbd">' + meta.fkey + "</kbd>" +
        '<span class="fsl-fast-label">' + meta.label + "</span>" +
        '<span class="fsl-fast-z">L' + layer + "</span>";
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        switchTo(layer);
      });
      panel.appendChild(btn);
    });
    const ulBtn = document.createElement("button");
    ulBtn.type = "button";
    ulBtn.className = "fsl-fast-btn";
    ulBtn.dataset.layer = "userland";
    ulBtn.title = "F12 · Userland cycle";
    ulBtn.innerHTML =
      '<kbd class="fsl-fast-kbd">F12</kbd>' +
      '<span class="fsl-fast-label">Userland</span>' +
      '<span class="fsl-fast-z">L2+</span>';
    ulBtn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      cycleUserland();
    });
    panel.appendChild(ulBtn);
    document.body.appendChild(panel);
    state.fastSwitch = panel;
    return panel;
  }

  function fastSwitchHighlight(layer) {
    if (layer === 0 || layer === -1) return null;
    if (layer >= USERLAND_MIN) return "userland";
    return layer;
  }

  function updateFastSwitch(layer) {
    ensureFastSwitchPanel();
    const panel = state.fastSwitch;
    if (!panel) return;
    const active = fastSwitchHighlight(layer);
    panel.querySelectorAll(".fsl-fast-btn").forEach(function (btn) {
      const raw = btn.dataset.layer;
      const match =
        raw === "userland"
          ? active === "userland"
          : Number(raw) === active;
      btn.classList.toggle("fsl-fast-btn--active", match);
      btn.setAttribute("aria-pressed", match ? "true" : "false");
    });
  }

  function ensureMount() {
    if (state.root) return state.root;
    let el = document.getElementById("field-screen-stack");
    if (!el) {
      el = document.createElement("div");
      el.id = "field-screen-stack";
      el.className = "fsl-root";
      el.hidden = true;
      el.setAttribute("aria-hidden", "true");
      document.body.appendChild(el);
    }
    state.root = el;
    STACK_LAYERS.forEach(function (layer) {
      if (state.frames[layer]) return;
      const meta = LAYER_META[String(layer)];
      const panel = document.createElement("div");
      panel.className = "fsl-layer";
      panel.dataset.layer = String(layer);
      panel.hidden = true;
      const bar = document.createElement("header");
      bar.className = "fsl-bar";
      bar.innerHTML =
        '<span class="fsl-label">' + meta.label + "</span>" +
        '<span class="fsl-z">Layer ' + layer + "</span>" +
        (meta.component ? '<span class="fsl-component">' + meta.component + "</span>" : "") +
        '<span class="fsl-lic"><strong>©</strong> All Rights Reserved · war-ready</span>' +
        '<kbd class="fsl-kbd">' + (meta.fkey || "") + "</kbd>";
      const iframe = document.createElement("iframe");
      iframe.className = "fsl-frame";
      iframe.title = meta.label;
      iframe.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation"
      );
  
      panel.appendChild(bar);
      panel.appendChild(iframe);
      el.appendChild(panel);
      state.frames[layer] = { panel: panel, iframe: iframe };
    });
    return el;
  }

  function showDesktopLayer(layer) {
    state.active = layer;
    document.documentElement.dataset.fieldScreenLayer = String(layer);
    document.documentElement.dataset.fieldLayer = String(layer);
    const stack = ensureMount();
    stack.hidden = true;
    stack.setAttribute("aria-hidden", "true");
    setDesktopVisible(true);
    updateHud(layer);
    updateFastSwitch(layer);
    const meta = LAYER_META[String(layer)] || {};
    const label = layer >= USERLAND_MIN ? userlandLabel(layer) : meta.label || "Field One";
    toast("Layer " + layer + " · " + label);
  }

  function showStackLayer(layer) {
    state.active = layer;
    document.documentElement.dataset.fieldScreenLayer = String(layer);
    document.documentElement.dataset.fieldLayer = String(layer);
    const stack = ensureMount();
    const onDesktop = layer === -1;
    stack.hidden = onDesktop;
    stack.setAttribute("aria-hidden", onDesktop ? "true" : "false");
    setDesktopVisible(onDesktop);
    STACK_LAYERS.forEach(function (n) {
      const entry = state.frames[n];
      if (!entry) return;
      const show = n === layer;
      entry.panel.hidden = !show;
      entry.panel.classList.toggle("fsl-layer--active", show);
      if (show) {
        const url = layerUrl(n);
        if (url && entry.iframe.getAttribute("src") !== url) entry.iframe.setAttribute("src", url);
      }
    });
    updateHud(layer);
    updateFastSwitch(layer);
    toast("Layer " + layer + " · " + (LAYER_META[String(layer)]?.label || "Field One"));
  }

  function switchTo(layer) {
    if (layer >= USERLAND_MIN) {
      const hit = listUserlandEntries().find(function (e) {
        return e.layer === layer;
      });
      if (hit) {
        focusUserlandEntry(hit);
        return;
      }
      showDesktopLayer(layer);
      return;
    }
    if (layer === 0) {
      showDesktopLayer(0);
      return;
    }
    if (layer === -1 || layer === -2 || layer === -3) {
      showStackLayer(layer);
      return;
    }
    if (layer === 1) {
      openQueen();
      return;
    }
    showStackLayer(layer);
  }

  function focusQueenBrowser() {
    state.active = 1;
    document.documentElement.dataset.fieldScreenLayer = "1";
    document.documentElement.dataset.fieldLayer = "1";
    const stack = ensureMount();
    stack.hidden = true;
    stack.setAttribute("aria-hidden", "true");
    setDesktopVisible(true);
    updateHud(1);
    updateFastSwitch(1);
  }

  function openQueen() {
    if (global.NexusFieldShell?.launch) {
      const base = queenPagesBase();
      const assets = pagesRuntime()
        ? (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/assets"
        : "/assets";
      global.NexusFieldShell.launch({
        id: "queen-browser",
        name: "Queen Browser",
        exec: base + "/browser.html",
        shell: true,
        icon_url: assets + "/queen-prog-browser.png",
      });
      focusQueenBrowser();
      toast("Queen Browser · own browser space");
      return;
    }
    focusQueenBrowser();
  }

  function isFieldSurface() {
    if (document.documentElement.dataset.ammoosDesktop === "1") return true;
    if (document.body?.dataset?.queenSurface === "browser") return true;
    if (document.body?.dataset?.pagesRuntime === "1") return true;
    return false;
  }

  function onKeyDown(e) {
    if (!isFieldSurface()) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (e.key === "F12") {
      e.preventDefault();
      e.stopPropagation();
      cycleUserland();
      return;
    }
    if (e.key === "F11") {
      e.preventDefault();
      e.stopPropagation();
      openQueen();
      return;
    }
    if (!(e.key in FKEY_TO_LAYER)) return;
    const layer = FKEY_TO_LAYER[e.key];
    e.preventDefault();
    e.stopPropagation();
    switchTo(layer);
  }

  function markInsideOs(active) {
    if (active) {
      state.active = 0;
      document.documentElement.dataset.fieldScreenLayer = "0";
      document.documentElement.dataset.fieldLayer = "0";
      updateHud(0);
      updateFastSwitch(0);
      return;
    }
    if (state.active === 0 || state.active >= USERLAND_MIN) switchTo(-1);
  }

  function wire() {
    if (state.wired) return;
    document.addEventListener("keydown", onKeyDown, true);
    ensureFastSwitchPanel();
    state.wired = true;
    switchTo(-1);
    updateHud(state.active);
    updateFastSwitch(state.active);
  }

  global.FieldScreenLayers = {
    switchTo: switchTo,
    openQueen: openQueen,
    focusQueenBrowser: focusQueenBrowser,
    cycleUserland: cycleUserland,
    markInsideOs: markInsideOs,
    layerUrl: layerUrl,
    listUserland: listUserlandEntries,
    current: function () {
      return state.active;
    },
    wire: wire,
    LAYERS: LAYER_META,
    FKEY_TO_LAYER: FKEY_TO_LAYER,
    FAST_SWITCH_LAYERS: FAST_SWITCH_LAYERS,
    USERLAND_MIN: USERLAND_MIN,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);