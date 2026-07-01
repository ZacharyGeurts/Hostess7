/**
 * NEXUS panel plugin runtime — bottom dock on every tab, unlimited plugins.
 */
(function (global) {
  "use strict";

  const VIEW_IDS = [
    "command", "us", "honor", "field-rf", "monitor", "inspect", "library",
    "host-attack", "spiderweb", "dossier", "human-dossier", "research", "settings", "logs",
  ];

  const clientHooks = {};

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function ensureDocks() {
    VIEW_IDS.forEach((viewId) => {
      const section = document.getElementById(`view-${viewId}`);
      if (!section || section.querySelector(".nexus-plugins-dock")) return;
      const dock = document.createElement("div");
      dock.className = "nexus-plugins-dock";
      dock.dataset.view = viewId;
      dock.innerHTML = [
        '<div class="nexus-plugins-head">',
        '<span class="nexus-plugins-title">Plugins</span>',
        '<span class="nexus-plugins-meta" data-plugins-meta="' + esc(viewId) + '"></span>',
        "</div>",
        '<div class="nexus-plugins-body" data-plugins-body="' + esc(viewId) + '">',
        '<div class="nexus-plugins-empty">No plugins for this tab yet.</div>',
        "</div>",
      ].join("");
      section.appendChild(dock);
    });
  }

  function registerClientHook(pluginId, fn) {
    if (window.NexusFrontHook && typeof window.NexusFrontHook.allowPluginHook === "function") {
      if (!window.NexusFrontHook.allowPluginHook(pluginId)) return;
    }
    if (typeof fn === "function") clientHooks[pluginId] = fn;
  }

  function renderPluginCard(pluginId, row, viewId) {
    const accent = row.accent || "internet";
    const action = row.action || {};
    const actionHtml = action.jump
      ? `<button type="button" class="nexus-plugin-action" data-view-jump="${esc(action.jump)}">${esc(action.label || "Open →")}</button>`
      : "";
    return `<div class="nexus-plugin-card accent-${esc(accent)}" data-plugin="${esc(pluginId)}" data-view="${esc(viewId)}">
      <div class="nexus-plugin-card-head">
        <strong>${esc(row.label || pluginId)}</strong>
        <span class="nexus-plugin-id">${esc(pluginId)}</span>
      </div>
      <p class="nexus-plugin-text">${esc(row.text || "")}</p>
      ${actionHtml}
    </div>`;
  }

  function renderViewDock(viewId, pluginsData) {
    const body = document.querySelector(`[data-plugins-body="${viewId}"]`);
    const meta = document.querySelector(`[data-plugins-meta="${viewId}"]`);
    if (!body) return;

    const registry = pluginsData.registry || [];
    const outputs = pluginsData.outputs || {};
    const enabled = new Set(pluginsData.enabled || registry.filter((r) => r.enabled !== false).map((r) => r.id));

    const cards = [];
    registry.forEach((reg) => {
      if (!enabled.has(reg.id)) return;
      const slots = reg.slots || ["*"];
      if (!slots.includes("*") && !slots.includes("all") && !slots.includes(viewId)) return;
      const out = outputs[reg.id] || {};
      const row = (out.views || {})[viewId];
      if (!row) return;
      cards.push(renderPluginCard(reg.id, row, viewId));
      if (clientHooks[reg.id]) {
        try {
          clientHooks[reg.id](viewId, row, out, pluginsData);
        } catch (_) { /* plugin client hook */ }
      }
    });

    if (meta) {
      meta.textContent = cards.length ? `${cards.length} active` : "idle";
    }
    const summary = document.getElementById("summary-plugins");
    if (summary && viewId === "settings") {
      const total = (pluginsData.registry || []).length;
      const on = (pluginsData.enabled || []).length;
      summary.innerHTML = total
        ? `<strong>${on}</strong> of ${total} plugin(s) enabled · dock on every tab`
        : "No plugins installed";
    }
    body.innerHTML = cards.length
      ? cards.join("")
      : '<div class="nexus-plugins-empty">No plugins enabled for this tab.</div>';

    body.querySelectorAll("[data-view-jump]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (typeof global.showView === "function") global.showView(btn.dataset.viewJump);
      });
    });
  }

  function renderAll(data) {
    ensureDocks();
    const pluginsData = (data && data.plugins) || {};
    VIEW_IDS.forEach((viewId) => renderViewDock(viewId, pluginsData));
    renderPluginManager(pluginsData);
  }

  function renderPluginManager(pluginsData) {
    const mgr = document.getElementById("nexus-plugin-manager");
    if (!mgr) return;
    const registry = pluginsData.registry || [];
    if (!registry.length) {
      mgr.innerHTML = '<div class="empty">No plugins installed — drop folders under plugins/ with manifest.json.</div>';
      return;
    }
    mgr.innerHTML = `<table class="honor-table"><thead><tr><th>Plugin</th><th>Version</th><th>Slots</th><th>Status</th><th></th></tr></thead><tbody>
      ${registry.map((r) => `<tr>
        <td><strong>${esc(r.name || r.id)}</strong><div class="meta">${esc(r.description || "")}</div></td>
        <td>${esc(r.version || "—")}</td>
        <td>${esc((r.slots || ["*"]).join(", "))}</td>
        <td>${r.enabled !== false ? '<span class="severity-ok">ON</span>' : '<span class="meta">OFF</span>'}</td>
        <td><button type="button" class="nexus-plugin-toggle" data-plugin-id="${esc(r.id)}" data-enabled="${r.enabled !== false ? "0" : "1"}">${r.enabled !== false ? "Disable" : "Enable"}</button></td>
      </tr>`).join("")}
    </tbody></table>`;
    mgr.querySelectorAll(".nexus-plugin-toggle").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.pluginId;
        const on = btn.dataset.enabled === "1";
        btn.disabled = true;
        try {
          await fetch("/api/plugins/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, enabled: on }),
          });
          if (typeof global.refresh === "function") await global.refresh();
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function init() {
    ensureDocks();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", ensureDocks);
    }
  }

  init();

  global.NexusPlugins = {
    VIEW_IDS,
    ensureDocks,
    render: renderAll,
    registerClientHook,
  };
})(window);