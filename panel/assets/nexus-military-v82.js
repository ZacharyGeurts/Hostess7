/* NEXUS-Shield v8.2 — QOL experience smoothing */
(function (global) {
  function panelVersion() {
    return global.lastPanelData?.version || global.NEXUS_FIELD?.version || null;
  }
  const BUILD = "military-v82";

  function ensureChrome() {
    const html = document.documentElement;
    html.classList.add("nexus-v82");
    if (!document.getElementById("nexus-field-progress")) {
      const bar = document.createElement("div");
      bar.id = "nexus-field-progress";
      bar.className = "nexus-field-progress";
      bar.setAttribute("aria-hidden", "true");
      document.body.appendChild(bar);
    }
    if (!document.getElementById("nexus-toast-host")) {
      const host = document.createElement("div");
      host.id = "nexus-toast-host";
      host.className = "nexus-toast-host";
      host.setAttribute("aria-live", "polite");
      document.body.appendChild(host);
    }
    ensureKillChainBadge();
  }

  function ensureKillChainBadge() {
    const bar = document.getElementById("nexus-ops-bar");
    if (!bar || document.getElementById("nexus-kill-chain-badge")) return;
    const badge = document.createElement("span");
    badge.id = "nexus-kill-chain-badge";
    badge.className = "nexus-kill-chain-badge idle";
    badge.textContent = "KILL · AUTOKILL · RE-KILL";
    badge.title = "Kill chain active — autokill certain + RE-KILL validated returners (unchanged v8.2)";
    bar.appendChild(badge);
  }

  function updateKillChainBadge(data) {
    const badge = document.getElementById("nexus-kill-chain-badge");
    if (!badge || !data) return;
    const ak = data.attack_kit || {};
    const killed = Number(ak.disabled_count || data.field_command?.attack_kit_killed || 0);
    const hot = Number(ak.crush_hot_count || ak.hot_count || 0);
    const active = killed > 0 || hot > 0 || data.settings?.autokill !== false;
    badge.classList.toggle("idle", !active);
    if (active) {
      badge.textContent = `KILL ON · ${killed} killed · RE-KILL armed`;
    } else {
      badge.textContent = "KILL · AUTOKILL · RE-KILL";
    }
  }

  function setFetching(on) {
    document.documentElement.classList.toggle("panel-fetching", !!on);
  }

  function toast(message, kind) {
    const host = document.getElementById("nexus-toast-host");
    if (!host || !message) return;
    const el = document.createElement("div");
    el.className = `nexus-toast ${kind || ""}`.trim();
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      setTimeout(() => el.remove(), 220);
    }, 3200);
  }

  function hookRefresh() {
    const orig = global.refresh;
    if (typeof orig !== "function" || orig.__nexusV82) return false;
    global.refresh = async function nexusRefreshV82() {
      setFetching(true);
      try {
        return await orig.apply(this, arguments);
      } finally {
        setFetching(false);
        if (global.lastPanelData) updateKillChainBadge(global.lastPanelData);
      }
    };
    global.refresh.__nexusV82 = true;
    return true;
  }

  function hookPaintPanel() {
    const orig = global.paintPanel;
    if (typeof orig !== "function" || orig.__nexusV82) return false;
    global.paintPanel = function nexusPaintV82(data) {
      const out = orig.apply(this, arguments);
      updateKillChainBadge(data);
      stampV82();
      return out;
    };
    global.paintPanel.__nexusV82 = true;
    return true;
  }

  function hookShowView() {
    const orig = global.showView;
    if (typeof orig !== "function" || orig.__nexusV82) return false;
    global.showView = function nexusShowViewV82(route, opts) {
      const view = document.querySelector(".view.active");
      if (view) view.classList.add("view-leaving");
      const p = orig.apply(this, arguments);
      const settle = () => {
        document.querySelectorAll(".view.view-leaving").forEach((v) => v.classList.remove("view-leaving"));
        const active = document.querySelector(".view.active");
        if (active) {
          active.classList.remove("view-enter");
          void active.offsetWidth;
          active.classList.add("view-enter");
        }
        global.NexusMilitaryV8?.onViewChange?.(location.hash);
      };
      if (p && typeof p.then === "function") return p.then((r) => { settle(); return r; });
      settle();
      return p;
    };
    global.showView.__nexusV82 = true;
    return true;
  }

  function stampV82() {
    const ver = panelVersion();
    if (ver && global.NexusMilitaryV8?.stampVersion) global.NexusMilitaryV8.stampVersion(ver);
    const status = document.getElementById("nexus-ops-status");
    if (status && ver && !status.dataset.v82) {
      status.dataset.v82 = "1";
      const base = status.textContent || "";
      if (!base.includes(`v${ver}`)) status.textContent = `${base} · v${ver}`;
    }
  }

  function boot() {
    ensureChrome();
    stampV82();
    const t = setInterval(() => {
      if (hookRefresh() && hookPaintPanel() && hookShowView()) clearInterval(t);
    }, 80);
    setTimeout(() => clearInterval(t), 8000);
  }

  global.NexusMilitaryV82 = {
    panelVersion,
    BUILD,
    boot,
    toast,
    setFetching,
    updateKillChainBadge,
  };
  global.NexusToast = { show: toast };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);