/**
 * Six-tool display wall — 3×2 fit, drag reorder, drop icons to assign program.
 */
(function (global) {
  "use strict";

  const STORAGE = "ammo-six-tools-v2";
  const MAX_SLOTS = 6;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function resolveUrl(raw) {
    const s = String(raw || "").trim();
    if (!s) return null;
    if (s.startsWith("/")) return s;
    if (/^https?:\/\//i.test(s)) return s;
    return null;
  }

  function programUrl(app) {
    const exec = String(app?.exec || app?.url || "").trim();
    if (!exec) return null;
    if (exec.startsWith("/")) return exec;
    if (app?.view) return "/command?embed=1#" + app.view;
    if (/^https?:\/\/127\.0\.0\.1:9477/i.test(exec)) {
      try {
        return new URL(exec).pathname + new URL(exec).search + new URL(exec).hash;
      } catch (_) {
        return exec;
      }
    }
    return null;
  }

  function iconHtml(app) {
    const QIE = global.QueenIconEngine;
    if (QIE?.programIconHtml) {
      return QIE.programIconHtml(app, 28, { small: true, base: QIE.PANEL_ICONS });
    }
    const src = app.icon_url || "/assets/queen-favicon-48.png";
    return '<img src="' + esc(src) + '" alt="" width="28" height="28" class="fmd-dock-icon" />';
  }

  function mount(root, config) {
    if (!root) return;
    const cfg = config || {};
    const panels = (Array.isArray(cfg.panels) ? cfg.panels : []).slice(0, MAX_SLOTS);
    const programs = Array.isArray(cfg.programs) ? cfg.programs : [];
    const dockApps = Array.isArray(cfg.icon_dock)
      ? cfg.icon_dock
      : programs.filter(function (p) {
          return p.shell && programUrl(p) && !p.ghost && !p.clipboard_ghost && p.id !== "queen-browser";
        }).slice(0, 24);

    const byId = {};
    panels.forEach(function (p) { byId[p.id] = p; });
    programs.forEach(function (p) {
      if (p.id) byId["prog:" + p.id] = { id: p.id, title: p.name, url: programUrl(p) };
    });

    let slots = panels.map(function (p) {
      return { id: p.id, title: p.title || p.id, url: p.url };
    });
    while (slots.length < MAX_SLOTS) {
      slots.push({ id: "empty_" + slots.length, title: "Drop icon", url: "" });
    }
    slots = slots.slice(0, MAX_SLOTS);

    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE) || "{}");
      if (Array.isArray(saved.slots) && saved.slots.length === MAX_SLOTS) slots = saved.slots;
    } catch (_) {}

    function save() {
      try {
        localStorage.setItem(STORAGE, JSON.stringify({ slots: slots }));
      } catch (_) {}
    }

    function render() {
      const showDock = dockApps.length > 0;
      root.innerHTML =
        '<div class="fmd-root fmd-root--six">' +
        '<div class="fmd-grid fmd-grid--six" id="fmd-grid"></div>' +
        (showDock
          ? '<div class="fmd-dock" id="fmd-dock" aria-label="Program icons — drag onto a window"></div>'
          : "") +
        "</div>";

      const grid = root.querySelector("#fmd-grid");
      const dock = showDock ? root.querySelector("#fmd-dock") : null;

      grid.innerHTML = slots
        .map(function (slot, idx) {
          const url = resolveUrl(slot.url);
          const empty = !url;
          const title = slot.title || slot.id || "Tool " + (idx + 1);
          return (
            '<article class="fmd-panel fmd-panel--slot fmd-panel--page' + (empty ? " fmd-panel--empty" : "") + '" ' +
            'draggable="true" data-slot="' + idx + '" data-id="' + esc(slot.id) + '">' +
            '<div class="fmd-slot-label" title="Drag to reorder">' + esc(title) + "</div>" +
            (url
              ? '<div class="fmd-page-frame"><iframe class="fmd-view" src="' + esc(url) + '" title="' + esc(title) + '" loading="lazy"></iframe></div>'
              : '<div class="fmd-drop-hint">Drop program icon here</div>') +
            "</article>"
          );
        })
        .join("");

      if (dock) {
        dock.innerHTML = dockApps
          .map(function (app) {
            const url = programUrl(app);
            if (!url) return "";
            return (
              '<button type="button" class="fmd-dock-btn" draggable="true" ' +
              'data-app-id="' + esc(app.id) + '" data-url="' + esc(url) + '" ' +
              'title="' + esc(app.name || app.id) + '">' +
              iconHtml(app) +
              '<span>' + esc(app.name || app.id) + "</span></button>"
            );
          })
          .join("");
      }

      let dragSlot = null;
      let dragApp = null;

      grid.querySelectorAll(".fmd-panel").forEach(function (el) {
        el.addEventListener("dragstart", function (ev) {
          if (dragApp) return;
          dragSlot = Number(el.dataset.slot);
          el.classList.add("dragging");
          ev.dataTransfer?.setData("text/plain", "slot:" + dragSlot);
        });
        el.addEventListener("dragend", function () {
          el.classList.remove("dragging");
          dragSlot = null;
        });
        el.addEventListener("dragover", function (ev) {
          ev.preventDefault();
          el.classList.add("drop-target");
        });
        el.addEventListener("dragleave", function () {
          el.classList.remove("drop-target");
        });
        el.addEventListener("drop", function (ev) {
          ev.preventDefault();
          el.classList.remove("drop-target");
          const to = Number(el.dataset.slot);
          const raw = ev.dataTransfer?.getData("text/plain") || "";
          if (raw.startsWith("app:")) {
            const parts = raw.split(":");
            const appId = parts[1];
            const url = decodeURIComponent(parts.slice(2).join(":"));
            const app = dockApps.find(function (a) { return a.id === appId; });
            slots[to] = {
              id: appId || "custom",
              title: app?.name || appId || "Program",
              url: url,
            };
            save();
            render();
            return;
          }
          if (raw.startsWith("slot:")) {
            const from = Number(raw.replace("slot:", ""));
            if (from === to || from < 0 || to < 0) return;
            const tmp = slots[from];
            slots[from] = slots[to];
            slots[to] = tmp;
            save();
            render();
          }
        });
      });

      dock?.querySelectorAll(".fmd-dock-btn").forEach(function (btn) {
        btn.addEventListener("dragstart", function (ev) {
          dragApp = btn.dataset.appId;
          const url = btn.dataset.url || "";
          ev.dataTransfer?.setData("text/plain", "app:" + btn.dataset.appId + ":" + encodeURIComponent(url));
          btn.classList.add("dragging");
        });
        btn.addEventListener("dragend", function () {
          btn.classList.remove("dragging");
          dragApp = null;
        });
        btn.addEventListener("click", function () {
          const url = btn.dataset.url;
          const appId = btn.dataset.appId;
          const app = dockApps.find(function (a) { return a.id === appId; });
          const emptyIdx = slots.findIndex(function (s) { return !resolveUrl(s.url); });
          const idx = emptyIdx >= 0 ? emptyIdx : 0;
          slots[idx] = { id: appId, title: app?.name || appId, url: url };
          save();
          render();
        });
      });
    }

    render();
  }

  global.FieldMonitorDashboard = { mount: mount, addPanel: function () {} };
})(window);