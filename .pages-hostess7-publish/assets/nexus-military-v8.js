/* NEXUS-Shield v8.0 — Military Grade C2 layer */
(function (global) {
  const MISSION = {
    command: { code: "OP-H7", title: "Hostess 7 · Super Intelligence", flow: ["command", "threats/map", "packets/inspect", "threats/local-holes"] },
    us: { code: "OP-US", title: "US · Host Identity", flow: ["us", "packets/monitor", "intel/honor", "threats/kill"] },
    packets: { code: "OP-PKT", title: "Packets · Gatekeeper", flow: ["packets/monitor", "packets/inspect", "command", "dns"] },
    threats: { code: "OP-THR", title: "Threats · Kill Chain", flow: ["threats/home-protector", "threats/local-holes", "threats/host-attack", "threats/human-dossier", "intel/field-rf"] },
    intel: { code: "OP-INT", title: "Intel · Trust & People", flow: ["intel/honor", "intel/people", "intel/field-rf", "intel/research"] },
    signals: { code: "OP-SIG", title: "Signals · Antenna", flow: ["signals", "intel/field-rf", "packets/monitor", "dns"] },
    dns: { code: "OP-DNS", title: "DNS & DHCP · Planetary", flow: ["dns", "packets/monitor", "outside", "us"] },
    outside: { code: "OP-OUT", title: "Outside · Egress Gate", flow: ["outside", "library", "dns", "packets/monitor"] },
    library: { code: "OP-LIB", title: "Library · Field Books", flow: ["library", "outside", "intel/research", "command"] },
    system: { code: "OP-SYS", title: "System · Settings & Logs", flow: ["system/settings", "system/logs", "command", "packets/monitor"] },
  };

  function resolveVersion(fallback) {
    const cached = global.NEXUS_FIELD?.version || global.lastPanelData?.version;
    if (cached) return String(cached);
    return fallback || "…";
  }

  function stampVersion(ver) {
    const v = ver || resolveVersion("…");
    const title = document.getElementById("nexus-version-title");
    const btn = document.getElementById("nexus-version-btn");
    const edition = global.NEXUS_FIELD?.edition || "Universal Protector";
    if (title) title.textContent = `NEXUS-Shield v${v} · ${edition}`;
    document.title = `NEXUS-Shield v${v} · ${edition}`;
    const sub = document.getElementById("nexus-brand-sub");
    if (sub && !sub.dataset.upStamped) {
      sub.textContent = `${edition} · 3D/4D spatial lattice · Hostess 7 · threat HIGH`;
      sub.dataset.upStamped = "1";
    }
    if (btn) btn.textContent = `v${v}`;
  }

  function ensureOpsBar() {
    if (document.getElementById("nexus-ops-bar")) return;
    const nav = document.querySelector("nav.menu");
    if (!nav) return;
    const bar = document.createElement("div");
    bar.id = "nexus-ops-bar";
    bar.className = "nexus-ops-bar";
    bar.innerHTML = '<span class="ops-label">OPS FLOW</span><div class="ops-chain" id="nexus-ops-chain"></div><span class="ops-status" id="nexus-ops-status">MILITARY C2</span>';
    nav.parentNode.insertBefore(bar, nav.nextSibling);
  }

  function updateOpsBar(panel, sub) {
    ensureOpsBar();
    const spec = MISSION[panel] || MISSION.command;
    const chain = document.getElementById("nexus-ops-chain");
    const status = document.getElementById("nexus-ops-status");
    if (!chain) return;
    const route = sub && sub !== panel ? `${panel}/${sub}` : panel;
    chain.innerHTML = (spec.flow || []).map((step, i) => {
      const active = step === route || step.startsWith(panel) ? " active" : "";
      const arrow = i ? '<span class="ops-arrow">▸</span>' : "";
      const label = step.split("/").pop().replace(/-/g, " ");
      return `${arrow}<button type="button" class="ops-step${active}" data-view-jump="${step}">${label}</button>`;
    }).join("");
    if (status) status.innerHTML = `<strong>${spec.code}</strong> · ${spec.title}`;
  }

  function injectMissionBrief(viewEl, panel) {
    if (!viewEl || viewEl.querySelector(".nexus-mission-brief")) return;
    const spec = MISSION[panel] || MISSION.command;
    const brief = document.createElement("div");
    brief.className = "nexus-mission-brief";
    brief.innerHTML = `
      <div class="mission-head">
        <div>
          <div class="mission-code">${spec.code} · MILITARY GRADE</div>
          <div class="mission-title">${spec.title}</div>
        </div>
        <span class="mission-classification">FIELD C2</span>
      </div>
      <p class="mission-objective">Operator task: read live field data, follow OPS FLOW arrows, left-click this brief for tasks, right-click any tab for jump menu.</p>
      <div class="mission-hint">Left-click · expand tasks · Right-click tab · ops context menu</div>`;
    brief.addEventListener("click", () => brief.classList.toggle("expanded"));
    viewEl.insertBefore(brief, viewEl.firstChild);
  }

  function onViewChange(route) {
    const raw = (route || location.hash || "#command").replace("#", "") || "command";
    const parts = raw.split("/");
    const panel = parts[0] || "command";
    const sub = parts[1] || panel;
    updateOpsBar(panel, sub);
    const view = document.getElementById(`view-${sub}`) || document.getElementById(`view-${panel}`);
    if (view) injectMissionBrief(view, panel);
  }

  function hookShowView() {
    const orig = global.showView;
    if (typeof orig !== "function") return false;
    global.showView = function (route, opts) {
      const p = orig.apply(this, arguments);
      if (p && typeof p.then === "function") {
        return p.then((r) => { onViewChange(route); return r; });
      }
      onViewChange(route);
      return p;
    };
    return true;
  }

  function boot() {
    stampVersion(resolveVersion());
    global.NexusField?.fetchField?.().then((d) => {
      if (d?.version) stampVersion(d.version);
    });
    ensureOpsBar();
    onViewChange(location.hash);
    if (!hookShowView()) {
      const t = setInterval(() => { if (hookShowView()) clearInterval(t); }, 200);
    }
    global.addEventListener("hashchange", () => onViewChange(location.hash));
  }

  global.NexusMilitaryV8 = { stampVersion, onViewChange, boot };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);