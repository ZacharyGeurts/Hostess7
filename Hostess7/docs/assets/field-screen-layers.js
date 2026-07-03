/**
 * Field screen layers — F9..F12 switch sovereign surfaces.
 * -3 NEXUS C2 · -2 KILROY kernel · -1 AmmoOS desktop · 1 inside OS · 2 Queen (outside)
 */
(function (global) {
  "use strict";

  const LAYER_META = {
    "-3": { label: "NEXUS C2", fkey: "F9" },
    "-2": { label: "KILROY Kernel", fkey: "F10" },
    "-1": { label: "AmmoOS Desktop", fkey: "F11" },
    "1": { label: "Inside OS", fkey: null },
    "2": { label: "Queen Browser", fkey: "F12", external: true },
  };

  const FKEY_TO_LAYER = { F9: -3, F10: -2, F11: -1, F12: 2 };
  const STACK_LAYERS = [-3, -2];

  const state = { active: -1, root: null, frames: {}, wired: false };

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function panelBase() {
    if (pagesRuntime()) return global.HOSTESS7_PAGES_BASE || "/Hostess7";
    const port = document.body?.dataset?.nexusPanelPort || "9477";
    return "http://127.0.0.1:" + port;
  }

  function queenWorldBase() {
    if (pagesRuntime()) return (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/queen";
    return "/Hostess7/queen/world";
  }

  function layerUrl(layer) {
    const q = queenWorldBase();
    const p = panelBase();
    if (layer === -3) return q + "/queen-nexus-c2.html";
    if (layer === -2) return q + "/kilroy-home.html";
    if (layer === -1) return pagesRuntime() ? p + "/desktop/" : p + "/field";
    if (layer === 2) return q + "/browser.html";
    return null;
  }

  function toast(msg) {
    global.FieldHostDesktop?.toast?.(msg);
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
        '<span class="fsl-label">' + meta.label + '</span>' +
        '<span class="fsl-z">Layer ' + layer + '</span>' +
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

  function showStackLayer(layer) {
    state.active = layer;
    document.documentElement.dataset.fieldScreenLayer = String(layer);
    const stack = ensureMount();
    const onDesktop = layer === -1;
    stack.hidden = onDesktop;
    stack.setAttribute("aria-hidden", onDesktop ? "true" : "false");
    STACK_LAYERS.forEach(function (n) {
      const entry = state.frames[n];
      if (!entry) return;
      const show = n === layer;
      entry.panel.hidden = !show;
      if (show) {
        const url = layerUrl(n);
        if (url && entry.iframe.src !== url) entry.iframe.src = url;
      }
    });
    if (onDesktop) global.NexusFieldShell?.showDesktop?.();
    toast("Layer " + layer + " · " + (LAYER_META[String(layer)]?.label || "AmmoOS"));
  }

  function openQueenLayer2() {
    const url = layerUrl(2);
    const features =
      "width=1280,height=840,menubar=no,toolbar=no,location=yes,resizable=yes,scrollbars=yes,status=yes";
    state.active = 2;
    document.documentElement.dataset.fieldScreenLayer = "2";

    if (global.FieldQueenNav?.openStandalone) {
      global.FieldQueenNav
        .openStandalone(
          { id: "queen-browser", name: "Queen Browser", exec: url, shell: true, c2_embedded: false },
          { focus_url: url }
        )
        .then(function () {
          toast("Queen Browser · Layer 2 (outside OS)");
        });
      return;
    }

    try {
      global.open(url, "QueenBrowser", features);
    } catch (_) {
      global.location.href = url;
    }
    toast("Queen Browser · Layer 2 (outside OS)");
  }

  function switchTo(layer) {
    if (layer === 2) {
      openQueenLayer2();
      return;
    }
    if (layer === 1) {
      state.active = 1;
      document.documentElement.dataset.fieldScreenLayer = "1";
      return;
    }
    if (layer === -1) {
      showStackLayer(-1);
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
    const layer = FKEY_TO_LAYER[e.key];
    if (!layer) return;
    if (!isFieldSurface()) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    e.preventDefault();
    e.stopPropagation();
    switchTo(layer);
  }

  function markInsideOs(active) {
    if (active) {
      state.active = 1;
      document.documentElement.dataset.fieldScreenLayer = "1";
      return;
    }
    if (state.active === 1) switchTo(-1);
  }

  function wire() {
    if (state.wired) return;
    document.addEventListener("keydown", onKeyDown, true);
    state.wired = true;
  }

  global.FieldScreenLayers = {
    switchTo: switchTo,
    openQueen: openQueenLayer2,
    markInsideOs: markInsideOs,
    layerUrl: layerUrl,
    current: function () {
      return state.active;
    },
    wire: wire,
    LAYERS: LAYER_META,
    FKEY_TO_LAYER: FKEY_TO_LAYER,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);