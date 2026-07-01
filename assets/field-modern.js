/**
 * NEXUS Field Command Center — big chrome shell, legacy C2 shows the data.
 */
(function (global) {
  "use strict";

  const QUEEN_WORLD = "http://127.0.0.1:9481";
  const QUEEN_BROWSER = `${QUEEN_WORLD}/world/browser.html`;
  const DEFAULT_POLL_MS = 1200;
  const EMBED = "/field-legacy?embed=1";

  const TAB_ROUTES = {
    command: "command",
    us: "us",
    packets: "packets/monitor",
    threats: "threats/host-attack",
    signals: "signals",
    intel: "intel/honor",
    dns: "dns",
    outside: "outside",
    library: "library",
    system: "system/settings",
  };

  let activeTab = "command";
  let panelMeta = {};
  let pollMs = DEFAULT_POLL_MS;
  let fieldRaf = 0;
  let lastPoll = 0;
  let pollInFlight = false;

  function $(sel) {
    return document.querySelector(sel);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function fetchJson(url, ms) {
    const ctrl = new AbortController();
    const timer = global.setTimeout(() => ctrl.abort(), ms || 2500);
    return global.fetch(url, { cache: "no-store", signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null)
      .finally(() => global.clearTimeout(timer));
  }

  function toast(msg, ok) {
    const t = $("#fm-toast");
    if (!t) return;
    t.textContent = msg;
    t.style.borderColor = ok === false ? "#f43f5e" : "#34d399";
    t.hidden = false;
    global.setTimeout(() => { t.hidden = true; }, 2800);
  }

  function routeForTab(tab) {
    const btn = document.querySelector(`.fm-rail-btn[data-tab="${tab}"]`);
    if (btn?.dataset.route) return btn.dataset.route;
    return TAB_ROUTES[tab] || tab;
  }

  function embedUrl(route) {
    return `${EMBED}#${route}`;
  }

  function loadLegacyRoute(route) {
    const frame = $("#fm-c2-frame");
    if (!frame || !route) return;
    const url = embedUrl(route);
    let abs;
    try {
      abs = new URL(url, global.location.origin).href;
    } catch (_) {
      abs = url;
    }
    if (!frame.src || frame.src === "about:blank") {
      frame.src = abs;
      return;
    }
    try {
      const cur = new URL(frame.src);
      const nxt = new URL(abs);
      if (cur.pathname + cur.search !== nxt.pathname + nxt.search) {
        frame.src = abs;
        return;
      }
      if (cur.hash !== nxt.hash && frame.contentWindow) {
        frame.contentWindow.location.hash = nxt.hash;
      }
    } catch (_) {
      frame.src = abs;
    }
  }

  function resizeC2Viewport() {
    const main = $(".fm-main");
    const stage = $("#fm-c2-stage");
    const frame = $("#fm-c2-frame");
    const queenFrame = $("#fm-queen-frame");
    if (!main) return;
    const mainH = main.getBoundingClientRect().height;
    const milLayout = document.documentElement.classList.contains("mil-c2");
    if (!milLayout && mainH > 120) {
      main.style.height = `${Math.floor(mainH)}px`;
    } else if (milLayout) {
      main.style.height = "";
    }
    if (stage?.classList.contains("active") && frame) {
      frame.style.width = "100%";
      frame.style.height = "100%";
      frame.style.minHeight = `${Math.max(400, Math.floor(mainH))}px`;
    }
    const queenPane = document.querySelector('[data-pane="queen"].active');
    if (queenPane && queenFrame) {
      queenFrame.style.width = "100%";
      queenFrame.style.height = "100%";
    }
  }

  function setStage(mode) {
    const stage = $("#fm-c2-stage");
    const actions = $('[data-pane="actions"]');
    const queen = $('[data-pane="queen"]');
    const showC2 = mode === "c2";
    const showActions = mode === "actions";
    const showQueen = mode === "queen";

    if (stage) {
      stage.classList.toggle("active", showC2);
      stage.hidden = !showC2;
    }
    if (actions) {
      actions.classList.toggle("active", showActions);
      actions.hidden = !showActions;
    }
    if (queen) {
      queen.classList.toggle("active", showQueen);
      queen.hidden = !showQueen;
    }
  }

  function showTab(id) {
    activeTab = id;
    document.querySelectorAll(".fm-rail-btn").forEach((b) =>
      b.classList.toggle("active", b.dataset.tab === id));

    if (id === "actions") {
      setStage("actions");
      document.dispatchEvent(new CustomEvent("nexus-field-tab", { detail: { tab: "actions" } }));
      try { global.history.replaceState(null, "", "#actions"); } catch (_) {}
      global.requestAnimationFrame(resizeC2Viewport);
      return;
    }

    if (id === "queen") {
      setStage("queen");
      const f = $("#fm-queen-frame");
      if (f && !f.src) f.src = QUEEN_BROWSER;
      try { global.history.replaceState(null, "", "#queen"); } catch (_) {}
      document.dispatchEvent(new CustomEvent("nexus-field-tab", { detail: { tab: "queen" } }));
      global.requestAnimationFrame(resizeC2Viewport);
      return;
    }

    setStage("c2");
    loadLegacyRoute(routeForTab(id));

    try {
      global.history.replaceState(null, "", `#${id}`);
    } catch (_) {}
    document.dispatchEvent(new CustomEvent("nexus-field-tab", { detail: { tab: id } }));
    global.requestAnimationFrame(resizeC2Viewport);
  }

  function navigate(route) {
    const r = String(route || "").trim();
    if (!r) return;
    if (r === "actions" || r === "jockey") {
      showTab("actions");
      return;
    }
    const tab = r.split("/")[0];
    const btn = document.querySelector(`.fm-rail-btn[data-tab="${tab}"]`);
    if (btn) {
      showTab(tab);
      if (r.includes("/")) loadLegacyRoute(r);
      return;
    }
    setStage("c2");
    loadLegacyRoute(r);
  }

  function parseHash() {
    const h = (global.location.hash || "").replace(/^#/, "").trim() || "command";
    if (h === "jockey" || h === "actions") return "actions";
    if (h === "queen") return "queen";
    if (h.includes("/")) {
      const tab = h.split("/")[0];
      if (document.querySelector(`.fm-rail-btn[data-tab="${tab}"]`)) {
        global.setTimeout(() => loadLegacyRoute(h), 0);
        return tab;
      }
    }
    return document.querySelector(`.fm-rail-btn[data-tab="${h}"]`) ? h : "command";
  }

  function paintThreats(doc) {
    const top = $("#fm-threat-top");
    if (!top) return;
    const rs = doc?.root_sovereign || {};
    const ak = doc?.attack_kit || {};
    const gk = panelMeta.gatekeeper || doc?.gatekeeper || {};
    if (!doc && !panelMeta.field_command && !panelMeta.version) {
      top.innerHTML = '<span class="fm-pill">FIELD C2 LIVE</span>';
      return;
    }
    top.innerHTML = `
      <span class="fm-pill fm-pill--danger">GUARD ${esc(rs.verdict || "LIVE")}</span>
      <span class="fm-pill">HARM ${esc(gk.harm_candidates ?? ak.harm_candidates ?? 0)}</span>
      <span class="fm-pill">HOSTILE ${esc(ak.hostile_disabled || 0)}</span>
      <span class="fm-pill fm-pill--ok">STORE READY</span>`;
  }

  function applyFieldProfile(doc) {
    if (!doc || typeof doc !== "object") return;
    const root = document.documentElement;
    root.classList.add("mil-c2", "nexus-military-v8");
    if (doc.field_max) root.classList.add("field-max");
    if (doc.panel_refresh_ms) pollMs = Math.max(800, Number(doc.panel_refresh_ms) || DEFAULT_POLL_MS);
    const badge = $("#fm-field-badge");
    if (badge) {
      const q = doc.cpu_quota_pct;
      badge.textContent = doc.field_max ? `FIELD GREEN · ${q || 85}%` : "FIELD GREEN · LIVE";
    }
  }

  async function loadMeta() {
    if (pollInFlight) return;
    pollInFlight = true;
    try {
      const stored = await fetchJson("/api/status", 1500);
      if (stored && typeof stored === "object") {
        panelMeta = stored;
        applyFieldProfile(stored);
        const ver = stored.version || stored.panel_version;
        const vel = $("#fm-version");
        if (vel && ver) vel.textContent = `v${ver}`;
      }
      const threats = await fetchJson(`${QUEEN_WORLD}/api/root-threats`, 1800);
      paintThreats(threats);
    } finally {
      pollInFlight = false;
    }
  }

  function startSmoothFieldLoop() {
    if (fieldRaf) cancelAnimationFrame(fieldRaf);
    const tick = (ts) => {
      if (!document.hidden && ts - lastPoll >= pollMs && !pollInFlight) {
        lastPoll = ts;
        loadMeta();
      }
      fieldRaf = requestAnimationFrame(tick);
    };
    fieldRaf = requestAnimationFrame(tick);
  }

  async function refreshStore() {
    toast("Republishing field store…");
    await fetchJson("/api/field/field?publish=1", 120000);
    await loadMeta();
    if (activeTab !== "actions" && activeTab !== "queen") {
      loadLegacyRoute(routeForTab(activeTab));
    }
    toast("Field store refreshed", true);
  }

  function wireTabs() {
    const rail = document.querySelector(".fm-rail");
    if (rail) {
      function activateFromRail(ev) {
        const btn = ev.target.closest(".fm-rail-btn[data-tab]");
        if (!btn || !rail.contains(btn)) return;
        showTab(btn.dataset.tab);
      }
      rail.addEventListener("pointerup", activateFromRail);
      rail.addEventListener("click", activateFromRail);
      rail.addEventListener("keydown", (ev) => {
        if (ev.key !== "Enter" && ev.key !== " ") return;
        const btn = ev.target.closest(".fm-rail-btn[data-tab]");
        if (!btn) return;
        ev.preventDefault();
        showTab(btn.dataset.tab);
      });
    }
    global.addEventListener("hashchange", () => showTab(parseHash()));
  }

  function wireActions() {
    $("#fm-refresh")?.addEventListener("click", () => refreshStore());
    $("#fm-audit")?.addEventListener("click", () =>
      global.fetch(`${QUEEN_WORLD}/api/root-threats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "audit_root" }),
      }).then((r) => r.ok ? toast("Root audit complete", true) : toast("Audit failed", false)));
    $("#fm-rekill")?.addEventListener("click", () =>
      global.fetch("/api/attack-kit/rekill", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }).then((r) => r.ok ? toast("RE-KILL cycle", true) : toast("RE-KILL failed", false)));
    $("#fm-queen")?.addEventListener("click", () => {
      const port = global.location.port || "9477";
      const nexus = `http://127.0.0.1:${port}/field`;
      global.fetch(`${QUEEN_WORLD}/api/nexus-jump`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "jump", url: nexus, proc: "queen-browser" }),
      }).catch(() => {});
      global.fetch(`${QUEEN_WORLD}/api/queen-browser`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "new_tab", url: nexus }),
      }).catch(() => {});
      try {
        global.open(QUEEN_BROWSER, "queen-browser", "noopener,noreferrer");
      } catch (_) {
        global.location.href = QUEEN_BROWSER;
      }
    });
  }

  function boot() {
    wireTabs();
    wireActions();
    const hashTab = parseHash();
    showTab(hashTab);
    loadMeta();
    startSmoothFieldLoop();
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) loadMeta();
    });
    global.addEventListener("resize", resizeC2Viewport);
    if (global.ResizeObserver) {
      const ro = new ResizeObserver(() => resizeC2Viewport());
      const main = $(".fm-main");
      if (main) ro.observe(main);
    }
    global.requestAnimationFrame(resizeC2Viewport);
    global.setTimeout(resizeC2Viewport, 400);
    const c2 = $("#fm-c2-frame");
    if (c2) c2.addEventListener("load", resizeC2Viewport);
  }

  global.NexusField = {
    showTab,
    navigate,
    refresh: refreshStore,
    getData: () => ({ ...panelMeta }),
    getActiveTab: () => activeTab,
    listTabs: () => Array.from(document.querySelectorAll(".fm-rail-btn[data-tab]")).map((b) => ({
      id: b.dataset.tab,
      label: (b.querySelector(".fm-rail-label") || b).textContent.trim(),
      active: b.classList.contains("active"),
    })),
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);