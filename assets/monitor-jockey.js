/**
 * Actions tab — operator response. Above-military response discipline.
 */
(function (global) {
  "use strict";

  const API_ACTIONS = "/api/jockey/actions";
  const POLL_MS = 10000;
  const VALID_TIERS = new Set(["watch", "urgent", "investigate", "lethal", "map", "defend", "intel", "assist", "rest", "trust"]);
  const VALID_SEVERITY = new Set(["HARM_CANDIDATE", "SUSPICIOUS", "MONITOR", "EPHEMERAL", "USER_OK", ""]);
  const ALLOWED_API = new Set([
    "/api/spiderweb/like",
    "/api/kill-codes/execute",
    "/api/attack-kit/kill",
    "/api/attack-kit/rekill",
    "/api/attack-kit/nokill",
    "/api/attack-kit/crush-hot",
    "/api/field-toolkit/sever",
    "/api/field-toolkit/human-threat",
    "/api/field-toolkit/regional-disable",
    "/api/field-toolkit/laser-corridor",
    "/api/lethal-enforcement/cycle",
  ]);
  const ALLOWED_JUMP = [
    "actions", "overview", "command", "library", "jockey", "us", "signals", "dns", "outside",
    "packets", "packets/monitor", "packets/inspect", "threats",
    "threats/home-protector", "threats/local-holes", "threats/host-attack",
    "threats/scour-net", "threats/spiderweb", "threats/human-dossier",
    "intel", "intel/honor", "intel/research", "system", "system/settings", "stack", "queen",
  ];

  function navigate(route) {
    const r = String(route || "").trim();
    if (!r) return;
    if (global.NexusField?.navigate) {
      global.NexusField.navigate(r);
      return;
    }
    if (global.showView) {
      global.showView(r);
      return;
    }
    if (r.includes("/")) {
      global.location.href = `/field-legacy#${r}`;
      return;
    }
    global.location.hash = r;
  }

  let pollTimer = null;
  let loadGen = 0;
  let focusAlert = null;
  let lastAlertsDoc = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function safeTier(tier) {
    const t = String(tier || "watch").toLowerCase();
    return VALID_TIERS.has(t) ? t : "watch";
  }

  function safeSeverity(sev) {
    const s = String(sev || "").toUpperCase();
    return VALID_SEVERITY.has(s) ? s : "MONITOR";
  }

  function jumpAllowed(route) {
    const r = String(route || "").trim();
    return ALLOWED_JUMP.includes(r);
  }

  async function fetchActions(alertId) {
    const url = alertId ? `${API_ACTIONS}?alert=${encodeURIComponent(alertId)}` : API_ACTIONS;
    const res = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!res.ok) throw new Error("actions " + res.status);
    const doc = await res.json();
    if (String(doc.schema || "") !== "monitor-jockey-actions/v1") {
      throw new Error("actions_schema_mismatch");
    }
    return doc;
  }

  function renderActionsGrid(doc) {
    const grid = $("jockey-actions-grid");
    if (!grid) return;
    const actions = doc.actions || [];
    if (!actions.length) {
      grid.innerHTML = '<p class="meta">No actions cataloged.</p>';
      return;
    }
    const focusId = focusAlert?.id || "";
    grid.innerHTML = actions.map((a) => {
      const tier = safeTier(a.tier);
      const highlight = focusId && (
        (a.id === "act:identify" && focusAlert?.unidentified) ||
        (String(a.id).startsWith("act:like:") && focusAlert?.entity_id) ||
        String(a.id || "").startsWith("kill:")
      );
      const bodyAttr = a.body ? esc(JSON.stringify(a.body)) : "";
      const api = ALLOWED_API.has(String(a.api || "")) ? esc(a.api) : "";
      const jump = jumpAllowed(a.jump) ? esc(a.jump) : "";
      return `<button type="button" class="jockey-action-btn tier-${tier}${highlight ? " is-highlight" : ""}" data-act-id="${esc(a.id)}" data-jump="${jump}" data-api="${api}" data-body="${bodyAttr}">
        <strong>${esc(a.label)}</strong>${a.detail ? `<span class="meta">${esc(a.detail)}</span>` : ""}
      </button>`;
    }).join("");
    grid.querySelectorAll(".jockey-action-btn").forEach((btn) => {
      btn.addEventListener("click", () => runAction(btn.dataset));
    });
  }

  async function runAction(ds) {
    if (ds.api && ALLOWED_API.has(ds.api)) {
      try {
        const body = ds.body ? JSON.parse(ds.body) : {};
        const res = await fetch(ds.api, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(body),
        });
        const doc = await res.json().catch(() => ({}));
        if (!res.ok || doc.friendly_refused) {
          alert(`Kill code blocked — ${doc.reason || doc.error || res.status}`);
          return;
        }
      } catch (e) {
        alert(`Kill code failed — ${e.message || e}`);
        return;
      }
    }
    if (ds.jump && jumpAllowed(ds.jump)) {
      navigate(ds.jump);
    }
  }

  async function loadKillCodesCatalog() {
    const grid = $("jockey-kill-codes-grid");
    if (!grid) return;
    try {
      const res = await fetch("/api/kill-codes", { cache: "no-store", credentials: "same-origin" });
      const doc = await res.json();
      const codes = (doc.codes || []).slice(0, 18);
      if (!codes.length) {
        grid.innerHTML = '<p class="meta">Kill code catalog empty.</p>';
        return;
      }
      grid.innerHTML = codes.map((c) => {
        const tier = safeTier(c.tier);
        const jump = c.jump && jumpAllowed(c.jump) ? esc(c.jump) : "";
        const body = { code: c.code, ...(c.body_template || {}) };
        if (c.suggested_ip) body.ip = c.suggested_ip;
        const canExec = c.api || c.removal_level || c.disablement;
        if (canExec) {
          return `<button type="button" class="jockey-kill-code tier-${tier}" data-api="/api/kill-codes/execute" data-body="${esc(JSON.stringify(body))}" data-jump="${jump}" title="${esc(c.plain || "")}">
            <code>${esc(c.code)}</code><strong>${esc(c.label)}</strong><span class="meta">${esc((c.plain || "").slice(0, 72))}</span>
          </button>`;
        }
        if (jump) {
          return `<button type="button" class="jockey-kill-code tier-${tier}" data-jump="${jump}" title="${esc(c.plain || "")}">
            <code>${esc(c.code)}</code><strong>${esc(c.label)}</strong>
          </button>`;
        }
        return "";
      }).filter(Boolean).join("");
      grid.querySelectorAll(".jockey-kill-code").forEach((btn) => {
        btn.addEventListener("click", () => runAction(btn.dataset));
      });
    } catch (e) {
      grid.innerHTML = `<p class="meta">Kill codes unavailable — ${esc(e.message)}</p>`;
    }
  }

  function renderPendingQueue(doc) {
    const queue = $("jockey-pending-queue");
    if (!queue) return;
    const pending = doc?.jockey_alerts || doc?.alerts || [];
    if (!pending.length) {
      queue.innerHTML = '<p class="jockey-queue-quiet">No pending instant alerts. Actions catalog ready for field response.</p>';
      return;
    }
    queue.innerHTML = pending.map((a) => {
      const sev = safeSeverity(a.severity);
      return `
      <article class="jockey-queue-item ${sev}" data-alert-id="${esc(a.id)}">
        <div class="jockey-queue-head">
          <strong>${esc(a.title)}</strong>
          <span class="jockey-queue-src">${esc(a.source || "")}${a.unidentified ? " · unidentified" : ""}</span>
        </div>
        <p>${esc((a.detail || "").slice(0, 220))}</p>
        <button type="button" class="jockey-queue-act" data-alert-id="${esc(a.id)}">Load actions for this alert</button>
      </article>`;
    }).join("");
    queue.querySelectorAll(".jockey-queue-act").forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = pending.find((x) => x.id === btn.dataset.alertId);
        openForAlert(item || { id: btn.dataset.alertId });
      });
    });
  }

  function renderFocusBanner() {
    const focus = $("jockey-actions-focus");
    if (!focus) return;
    if (!focusAlert) {
      focus.replaceChildren();
      return;
    }
    focus.innerHTML = `<p class="jockey-focus-banner"><strong>Focused:</strong> ${esc(focusAlert.title || focusAlert.id)} — ${focusAlert.unidentified ? "unidentified entity" : "field item"}</p>`;
  }

  async function loadPanel() {
    const gen = ++loadGen;
    const alertId = focusAlert?.id || null;
    renderFocusBanner();
    try {
      const actionsDoc = await fetchActions(alertId);
      if (gen !== loadGen) return;
      renderActionsGrid(actionsDoc);
      if (lastAlertsDoc) renderPendingQueue(lastAlertsDoc);
    } catch (e) {
      if (gen !== loadGen) return;
      const grid = $("jockey-actions-grid");
      if (grid) grid.innerHTML = `<p class="meta">Actions unavailable — ${esc(e.message)}</p>`;
    }
  }

  function openForAlert(alert) {
    focusAlert = alert?.id ? alert : null;
    loadPanel();
  }

  function isActionsActive() {
    const pane = document.querySelector('[data-pane="actions"]');
    return pane?.classList.contains("active") || $("view-jockey")?.classList.contains("active");
  }

  function onViewActive() {
    loadPanel();
    loadKillCodesCatalog();
    if (!pollTimer) pollTimer = setInterval(loadPanel, POLL_MS);
  }

  function onViewInactive() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function onFieldAlerts(ev) {
    const { doc, ok } = ev.detail || {};
    if (!ok || !doc) return;
    lastAlertsDoc = doc;
    if (isActionsActive()) {
      renderPendingQueue(doc);
    }
  }

  function init() {
    $("jockey-actions-refresh")?.addEventListener("click", () => loadPanel());
    $("jockey-actions-clear-focus")?.addEventListener("click", () => {
      focusAlert = null;
      loadPanel();
    });

    document.querySelectorAll("[data-fm-jump]").forEach((btn) => {
      btn.addEventListener("click", () => navigate(btn.getAttribute("data-fm-jump")));
    });

    document.addEventListener("nexus-field-tab", (ev) => {
      if (ev.detail?.tab === "actions") onViewActive();
      else onViewInactive();
    });
    document.addEventListener("nexus-view-activated", (ev) => {
      if (ev.detail?.view === "jockey") onViewActive();
      else if (!isActionsActive()) onViewInactive();
    });
    document.addEventListener("nexus-alert-acked", (ev) => {
      if (ev.detail?.response === "needs_action" && ev.detail?.alert) {
        focusAlert = ev.detail.alert;
      }
    });
    document.addEventListener("nexus-field-alerts", onFieldAlerts);

    const last = global.NexusFieldAlerts?.getLast?.();
    if (last) {
      lastAlertsDoc = last;
      if ($("view-jockey")?.classList.contains("active")) renderPendingQueue(last);
    }

    if (isActionsActive()) onViewActive();

    global.MonitorJockey = {
      openForAlert,
      refresh: () => loadPanel(),
      navigate,
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);