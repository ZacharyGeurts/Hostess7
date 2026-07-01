/**
 * AmmoCode toolbar — doctrine-driven icons, settings checkboxes, G16-ready actions
 */
(function (global) {
  "use strict";

  const GROUP_ORDER = ["file", "edit", "g16", "secure", "view", "tools", "network", "app"];
  const ICON_SIZES = [16, 20, 24, 32];

  const state = {
    doctrine: null,
    themes: null,
    enabled: {},
    iconSize: 24,
    onAction: null,
  };

  function iconPath(id, size) {
    const base = state.doctrine?.icon_base || "assets/icons/toolbar";
    const s = ICON_SIZES.includes(size) ? size : 24;
    return `${base}/${id}-${s}.png`;
  }

  function defaultEnabled(id) {
    return (state.doctrine?.default_enabled || []).includes(id);
  }

  function isEnabled(id) {
    if (Object.prototype.hasOwnProperty.call(state.enabled, id)) {
      return !!state.enabled[id];
    }
    return defaultEnabled(id);
  }

  function setEnabled(map) {
    state.enabled = { ...(map || {}) };
  }

  function enabledMap() {
    const items = state.doctrine?.items || [];
    const out = {};
    for (const it of items) {
      out[it.id] = isEnabled(it.id);
    }
    return out;
  }

  function groupedItems() {
    const items = (state.doctrine?.items || []).filter((it) => isEnabled(it.id));
    const groups = {};
    for (const it of items) {
      const g = it.group || "app";
      if (!groups[g]) groups[g] = [];
      groups[g].push(it);
    }
    return GROUP_ORDER.filter((g) => groups[g]?.length).map((g) => ({ group: g, items: groups[g] }));
  }

  function render(container) {
    if (!container || !state.doctrine) return;
    container.innerHTML = "";
    const groups = groupedItems();
    groups.forEach((grp, gi) => {
      if (gi > 0) {
        const sep = document.createElement("span");
        sep.className = "ac-tb-sep";
        sep.setAttribute("role", "separator");
        container.appendChild(sep);
      }
      for (const it of grp.items) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ac-tb-btn";
        btn.id = `ac-tb-${it.id}`;
        btn.title = it.label + (it.shortcut ? ` (${it.shortcut})` : "");
        btn.setAttribute("aria-label", it.label);
        if (it.secure) btn.dataset.secure = "1";
        if (it.g16) btn.dataset.g16 = "1";
        const img = document.createElement("img");
        img.src = iconPath(it.id, state.iconSize);
        img.alt = "";
        img.width = state.iconSize;
        img.height = state.iconSize;
        img.loading = "lazy";
        btn.appendChild(img);
        btn.addEventListener("click", () => {
          if (typeof state.onAction === "function") state.onAction(it.id, it);
        });
        container.appendChild(btn);
      }
    });
  }

  function renderCheckboxes(container) {
    if (!container || !state.doctrine) return;
    container.innerHTML = "";
    const byGroup = {};
    for (const it of state.doctrine.items || []) {
      const g = it.group || "app";
      if (!byGroup[g]) byGroup[g] = [];
      byGroup[g].push(it);
    }
    for (const g of GROUP_ORDER) {
      const list = byGroup[g];
      if (!list?.length) continue;
      const sec = document.createElement("div");
      sec.className = "ac-drawer-section";
      const h = document.createElement("h3");
      h.textContent = g;
      sec.appendChild(h);
      const grid = document.createElement("div");
      grid.className = "ac-tb-grid";
      for (const it of list) {
        const lbl = document.createElement("label");
        lbl.className = "ac-check";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.dataset.toolId = it.id;
        cb.checked = isEnabled(it.id);
        cb.addEventListener("change", () => {
          state.enabled[it.id] = cb.checked;
          if (typeof state.onAction === "function") {
            state.onAction("toolbar_toggle", { id: it.id, enabled: cb.checked });
          }
        });
        lbl.appendChild(cb);
        lbl.appendChild(document.createTextNode(it.label));
        grid.appendChild(lbl);
      }
      sec.appendChild(grid);
      container.appendChild(sec);
    }
  }

  function setActive(id, on) {
    const el = document.getElementById(`ac-tb-${id}`);
    if (el) el.classList.toggle("active", !!on);
  }

  async function loadDoctrine() {
    try {
      const r = await fetch("/api/toolbar", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        state.doctrine = j;
        return j;
      }
    } catch (_) {}
    return null;
  }

  function init(opts) {
    state.doctrine = opts?.doctrine || state.doctrine;
    state.enabled = { ...(opts?.toolbarEnabled || {}) };
    state.iconSize = opts?.iconSize || 24;
    state.onAction = opts?.onAction || null;
    document.documentElement.style.setProperty("--ac-icon-size", `${state.iconSize}px`);
    const bar = document.getElementById("ac-toolbar");
    if (bar) render(bar);
    const checks = document.getElementById("ac-toolbar-checks");
    if (checks) renderCheckboxes(checks);
  }

  global.AmmoCodeToolbar = {
    loadDoctrine,
    init,
    render,
    renderCheckboxes,
    setEnabled,
    enabledMap,
    isEnabled,
    setActive,
    iconPath,
    state: () => ({ ...state }),
  };
})(typeof globalThis !== "undefined" ? globalThis : window);