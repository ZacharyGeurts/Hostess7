/**
 * Field screen layers — F1..F12 = sovereign stack top → bottom.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * IRONCLAD — F-KEY STACK · EVERYTHING IN NEXUS C2 (:9477 host)
 *   F12 → Userland L2+ · cycle layers ≥ 3
 *   F11 → Layer 1 · Queen Browser (shell window inside C2)
 *   F10 → Layer −2 · DNS · KILROY lane
 *   F9  → Layer −3 · NEXUS C2 command deck
 *   F8  → Layer 0.5 · CHIPS presume path
 *   F7  → Layer 0 · Hardware · EOL Code
 *   F6  → Layer −1 · Field One · AmmoOS desktop (boot home · inside C2)
 *   F5  → Layer −2 · Botnet · DNS (alias F10)
 *   F4  → Layer −3 · NEXUS C2 (alias F9)
 *   F3  → CHIPS iron plate
 *   F2  → CHIPS presume path direct
 *   F1  → Ironclad CHIPS truth
 * Layer ≥ 3 in focus: full keyboard + controllers — our F-keys yield (F12 escapes).
 * Protected by field-screen-layer/v1 — comment-protect this block on every edit.
 * ═══════════════════════════════════════════════════════════════════════════
 */
(function (global) {
  "use strict";

  const LAYER_3_MIN = 3;
  const USERLAND_MIN = 2;

  const STACK_FKEYS = {
    F12: { z: 3, id: "userland_cycle", label: "Userland L2+", cycle: true },
    F11: { z: 1, id: "queen_browser", label: "Queen Browser", browser: true },
    F10: { z: -2, id: "dns_lane", label: "DNS · KILROY", stack: true, component: "field-botnet-dns-dhcp" },
    F9: { z: -3, id: "nexus_c2", label: "NEXUS C2", stack: true, component: "nexus-c2-command" },
    F8: { z: 0.5, id: "presume_path", label: "Presume path", panel: true, path: "/api/chips/presume-path" },
    F7: { z: 0, id: "hardware", label: "Hardware · EOL", panel: true, path: "/eol-code" },
    F6: { z: -1, id: "field_one", label: "Field One · AmmoOS", desktop: true },
    F5: { z: -2, id: "botnet", label: "Botnet · DNS", stack: true, component: "field-botnet-dns-dhcp" },
    F4: { z: -3, id: "nexus_c2_alt", label: "NEXUS C2", stack: true, component: "nexus-c2-command" },
    F3: { z: 0, id: "iron_plate", label: "Iron plate", panel: true, path: "/api/chips/plate-stack" },
    F2: { z: 0.5, id: "presume_direct", label: "Presume direct", panel: true, path: "/api/chips/presume-path" },
    F1: { z: 0, id: "ironclad_chips", label: "Ironclad CHIPS", queen: true, path: "/queen-chips-cores.html" },
  };

  const LAYER_3_PLUS_CYCLE = [
    { z: 3, id: "developer", label: "Developers L3", panel: true, path: "/api/field-steam-bridge", sovereignLayer: 3 },
    { z: 4, id: "queen_gameroom", label: "Queen Room", queen: true, path: "/queen-game-room.html", sovereignLayer: 4, fullscreen: true },
    { z: 5, id: "ammoos", label: "AmmoOS panels", panel: true, path: "/field", sovereignLayer: 5 },
    { z: 3, id: "arcade_battalion", label: "Arcade Battalion", panel: true, path: "/api/field-arcade-battalion", sovereignLayer: 3 },
    { z: 4, id: "combinatorics_studio", label: "Combinatorics", panel: true, path: "/combinatorics-studio/", sovereignLayer: 4 },
    { z: 3, id: "grok_lab", label: "Lab sovereign", panel: true, path: "/grok-lab", sovereignLayer: 3 },
    { z: 4, id: "controller_setup", label: "Arcade setup", queen: true, path: "/queen-game-room.html#arcade", sovereignLayer: 4 },
  ];

  const LAYER_META = {
    "-3": { label: "NEXUS C2", fkey: "F9", component: "nexus-c2-command", inside_c2: true },
    "-2": { label: "DNS · KILROY lane", fkey: "F10", component: "field-botnet-dns-dhcp", inside_c2: true },
    "-1": { label: "Field One · AmmoOS", fkey: "F6", component: "field-desktop", inside_c2: true },
    "0": { label: "OS Software · Hardware", fkey: "F7", inside_os: true, inside_c2: true },
    "1": { label: "Queen Browser", fkey: "F11", queen_browser: true, inside_c2: true },
    warehouse: { label: "Archival Warehouse", fkey: null, official: true, component: "ammoos-warehouse", inside_c2: true },
  };

  const STACK_LAYERS = [-3, -2];
  const FKEY_TO_LAYER = { F9: -3, F10: -2, F6: -1, F11: 1, F4: -3, F5: -2 };

  const state = {
    active: -1,
    sovereignLayer: -1,
    root: null,
    frames: {},
    wired: false,
    hud: null,
    fastSwitch: null,
    layer3CycleIdx: -1,
  };

  function iso() {
    return global.FieldLayerInputIsolation;
  }

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
    return "http://127.0.0.1:9481/world";
  }

  function layerUrl(layer) {
    const q = queenPagesBase();
    const p = panelBase();
    if (layer === -3) return p + "/command?embed=1";
    if (layer === -2) return p + "/command?embed=1#dns";
    if (layer === -1) return pagesRuntime() ? p + "/desktop/" : p + "/field";
    if (layer === "warehouse") return p + "/ammoos-warehouse/";
    if (layer === 1) return queenBrowserUrl();
    return null;
  }

  function resolveSpecUrl(spec) {
    if (!spec) return null;
    const base = spec.queen ? queenPagesBase() : panelBase();
    return spec.path ? base + spec.path : null;
  }

  function toast(msg) {
    global.FieldHostDesktop?.toast?.(msg);
  }

  function setSovereignLayer(z) {
    state.sovereignLayer = z;
    document.documentElement.dataset.fieldLayer = String(z);
    document.documentElement.dataset.fieldScreenLayer = String(z);
    document.documentElement.dataset.nexusC2 = "1";
    document.documentElement.dataset.nexusC2Stack = "ironclad";
    if (z >= LAYER_3_MIN) {
      document.documentElement.dataset.fieldLayerSovereign = "exclusive";
    } else {
      document.documentElement.removeAttribute("data-field-layer-sovereign");
      iso()?.clearExclusiveChrome?.();
    }
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
    const spec = Object.values(STACK_FKEYS).find(function (s) {
      return s.z === layer || (s.cycle && layer >= LAYER_3_MIN);
    });
    const label = spec?.label || LAYER_META[String(layer)]?.label || "Field One";
    hud.textContent = "Layer " + layer + " · " + label;
    hud.hidden = true;
  }

  function launchSurface(spec, fkey) {
    if (!spec) return;
    if (spec.desktop) {
      showDesktopLayer(-1);
      return;
    }
    const url = resolveSpecUrl(spec);
    if (!url) return;
    const assets = pagesRuntime()
      ? (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/assets"
      : "/assets";
    const layer = spec.sovereignLayer != null ? spec.sovereignLayer : typeof spec.z === "number" ? spec.z : -1;
    if (global.NexusFieldShell?.launch) {
      const win = global.NexusFieldShell.launch({
        id: spec.id,
        name: spec.label,
        exec: url,
        shell: true,
        icon_url: assets + "/queen-prog-chips.png",
        sovereignLayer: layer,
        userlandLayer: layer >= LAYER_3_MIN ? layer : USERLAND_MIN,
        os_layer: layer,
        exclusive_input: layer >= LAYER_3_MIN,
        allow_fullscreen: true,
      });
      setSovereignLayer(layer);
      state.active = layer;
      if (layer >= LAYER_3_MIN && win && win.id) {
        const el = document.getElementById(win.id);
        iso()?.applyExclusiveChrome?.(el, layer);
        if (spec.fullscreen) iso()?.requestFullscreen?.(el);
      }
      updateHud(layer);
      updateFastSwitch(layer);
      toast(spec.label);
      return;
    }
    if (spec.stack && typeof spec.z === "number") {
      switchTo(spec.z);
      return;
    }
    window.open(url, "_blank", "noopener");
    toast(spec.label);
  }

  function openHostess7() {
    launchSurface({
      z: "infinity",
      id: "hostess7",
      label: "Hostess 7",
      panel: true,
      path: "/brain.html",
      sovereignLayer: 3,
    }, "H7");
  }

  function cycleLayer3Plus() {
    const available = LAYER_3_PLUS_CYCLE;
    if (!available.length) return;
    let idx = state.layer3CycleIdx;
    if (state.sovereignLayer >= LAYER_3_MIN) {
      const hit = available.findIndex(function (e) {
        return e.id === state.activeId;
      });
      if (hit >= 0) idx = hit;
    }
    const next = (idx + 1) % available.length;
    state.layer3CycleIdx = next;
    const spec = available[next];
    state.activeId = spec.id;
    launchSurface(spec, "F11");
  }

  function handleStackFkey(fkey) {
    const spec = STACK_FKEYS[fkey];
    if (!spec) return;
    if (spec.cycle) {
      cycleLayer3Plus();
      return;
    }
    if (spec.browser) {
      openQueen();
      return;
    }
    if (spec.z === "infinity") {
      openHostess7();
      return;
    }
    if (spec.stack && typeof spec.z === "number") {
      switchTo(spec.z);
      return;
    }
    if (spec.desktop) {
      showDesktopLayer(-1);
      setSovereignLayer(-1);
      return;
    }
    launchSurface(spec, fkey);
  }

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
    panel.setAttribute("aria-label", "F1–F12 sovereign stack");
    panel.setAttribute("data-ironclad", "f1-f12-stack");
    ["F12", "F11", "F10", "F9", "F8", "F7", "F6"].forEach(function (fk) {
      const spec = STACK_FKEYS[fk];
      if (!spec) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "fsl-fast-btn";
      btn.dataset.fkey = fk;
      btn.title = spec.label;
      btn.innerHTML = '<span class="fsl-fast-label">' + spec.label + "</span>";
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        handleStackFkey(fk);
      });
      panel.appendChild(btn);
    });
    document.body.appendChild(panel);
    state.fastSwitch = panel;
    return panel;
  }

  function updateFastSwitch(layer) {
    ensureFastSwitchPanel();
    const panel = state.fastSwitch;
    if (!panel) return;
    panel.querySelectorAll(".fsl-fast-btn").forEach(function (btn) {
      const fk = btn.dataset.fkey;
      const spec = STACK_FKEYS[fk];
      const match =
        spec &&
        (spec.cycle
          ? layer >= LAYER_3_MIN
          : spec.z === layer || spec.z === state.sovereignLayer);
      btn.classList.toggle("fsl-fast-btn--active", !!match);
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
        (meta.component ? '<span class="fsl-component">' + meta.component + "</span>" : "");
      const iframe = document.createElement("iframe");
      iframe.className = "fsl-frame";
      iframe.title = meta.label;
      iframe.setAttribute(
        "sandbox",
        "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation fullscreen",
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
    setSovereignLayer(layer);
    const stack = ensureMount();
    stack.hidden = true;
    stack.setAttribute("aria-hidden", "true");
    setDesktopVisible(true);
    updateHud(layer);
    updateFastSwitch(layer);
    toast("Layer " + layer + " · AmmoOS · NEXUS C2");
  }

  function showStackLayer(layer) {
    state.active = layer;
    setSovereignLayer(layer);
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
    toast("Layer " + layer + " · " + (LAYER_META[String(layer)]?.label || "Field"));
  }

  function switchTo(layer) {
    if (layer === 0) {
      showDesktopLayer(0);
      return;
    }
    if (layer === -1) {
      showDesktopLayer(-1);
      return;
    }
    if (layer === -2 || layer === -3) {
      showStackLayer(layer);
      return;
    }
    showStackLayer(layer);
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
    if (!/^F([1-9]|1[0-2])$/.test(e.key)) return;

    if (iso()?.shouldYieldInput?.(e)) {
      if (e.key !== "F12") return;
    }

    if (e.key in STACK_FKEYS) {
      e.preventDefault();
      e.stopPropagation();
      handleStackFkey(e.key);
    }
  }

  function markInsideOs(active) {
    if (active) {
      state.active = 0;
      setSovereignLayer(0);
      updateHud(0);
      updateFastSwitch(0);
      return;
    }
    if (state.active === 0 || state.sovereignLayer >= LAYER_3_MIN) switchTo(-1);
  }

  function queenBrowserUrl() {
    if (pagesRuntime()) {
      return (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/queen/browser.html";
    }
    return queenPagesBase() + "/browser.html";
  }

  function openQueen() {
    const url = queenBrowserUrl();
    const assets = pagesRuntime()
      ? (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/assets"
      : "/assets";
    if (global.NexusFieldShell?.launch) {
      global.NexusFieldShell.launch({
        id: "queen-browser",
        name: "Queen Browser",
        exec: url,
        shell: true,
        icon_url: assets + "/queen-prog-browser.png",
      });
      focusQueenBrowser();
      return;
    }
    window.open(url, "_blank", "noopener");
    toast("Queen Browser");
  }

  function focusQueenBrowser() {
    setSovereignLayer(1);
    state.active = 1;
    document.documentElement.dataset.fieldQueenBrowser = "1";
    const wins = global.NexusFieldShell?.listWindows?.() || [];
    const qb = wins.find(function (w) {
      return w.appId === "queen-browser";
    });
    if (qb && global.NexusFieldShell?.focusWindow) {
      global.NexusFieldShell.focusWindow(qb.id);
    }
    setDesktopVisible(true);
    updateHud(1);
    updateFastSwitch(1);
  }

  function wire() {
    if (state.wired) return;
    document.addEventListener("keydown", onKeyDown, true);
    state.wired = true;
    switchTo(-1);
    updateHud(state.active);
    updateFastSwitch(state.active);
  }

  global.FieldScreenLayers = {
    switchTo: switchTo,
    openQueen: openQueen,
    focusQueenBrowser: focusQueenBrowser,
    openHostess7: openHostess7,
    cycleLayer3Plus: cycleLayer3Plus,
    markInsideOs: markInsideOs,
    layerUrl: layerUrl,
    launchSurface: launchSurface,
    current: function () {
      return state.active;
    },
    sovereignLayer: function () {
      return state.sovereignLayer;
    },
    wire: wire,
    LAYERS: LAYER_META,
    STACK_FKEYS: STACK_FKEYS,
    LAYER_3_PLUS_CYCLE: LAYER_3_PLUS_CYCLE,
    LAYER_3_MIN: LAYER_3_MIN,
    FKEY_TO_LAYER: FKEY_TO_LAYER,
    USERLAND_MIN: USERLAND_MIN,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);