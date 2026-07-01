/* NEXUS-Shield v10.2 — Universal Protector status bar (autonomous being stack) */
(function (global) {
  "use strict";

  const REFRESH_MS = 15000;

  function ensureBanner() {
    if (document.getElementById("nexus-universal-protector")) return;
    const bar = document.createElement("div");
    bar.id = "nexus-universal-protector";
    bar.className = "nexus-universal-protector";
    bar.setAttribute("role", "status");
    bar.setAttribute("aria-live", "polite");
    bar.innerHTML =
      '<strong>Universal Protector</strong> — autonomous being stack · ' +
      '<span id="nexus-up-detail">Super Intelligence · spatial lattice · lethal armed · threat HIGH</span>';
    const anchor = document.getElementById("help-bar") || document.querySelector(".app-header");
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(bar, anchor);
    } else {
      document.body.prepend(bar);
    }
  }

  function fmtMovement(spatial) {
    if (!spatial || !spatial.movement_vector) return "spatial lattice idle";
    const mv = spatial.movement_vector;
    const parts = [];
    if (mv.approach) parts.push("approach");
    else if (mv.recede) parts.push("recede");
    else parts.push("stable");
    if (mv.geometry && mv.geometry !== "stable") parts.push(mv.geometry);
    if (mv.bearing_deg != null) parts.push(`${Math.round(mv.bearing_deg)}°`);
    const dt = spatial.delta_t;
    if (dt != null) parts.push(`Δt ${Number(dt).toFixed(2)}`);
    return parts.join(" · ");
  }

  async function refresh() {
    const detail = document.getElementById("nexus-up-detail");
    if (!detail) return;
    let up = null;
    let spatial = null;
    try {
      const [upRes, spRes] = await Promise.all([
        fetch("/api/universal-protector", { credentials: "same-origin" }),
        fetch("/api/field-spatial", { credentials: "same-origin" }),
      ]);
      if (upRes.ok) up = await upRes.json();
      if (spRes.ok) spatial = await spRes.json();
    } catch (_) {}

    const think = up?.pillars?.cognition?.think_tanks;
    const tanks = Array.isArray(think) ? think.length : 6;
    const ellie = up?.ellie || {};
    const posture = up?.threat_warn_level || "high";
    const ellieBit = ellie.verdict ? ` · ELLIE ${ellie.verdict}${ellie.score != null ? ` ${Number(ellie.score).toFixed(2)}` : ""}` : "";
    const movement = fmtMovement(spatial);
    const nets = spatial?.scale_order?.join("→") || "body→room→field→planetary";
    const motionSkill = up?.pillars?.motion?.active_label;
    const motionProf = up?.pillars?.motion?.proficiency;
    const motionBit = motionSkill
      ? ` · motion ${motionSkill}${motionProf != null ? ` ${Math.round(motionProf * 100)}%` : ""}`
      : "";
    const lives = up?.pillars?.creatable_lives || {};
    const vita = lives.vita_live ? "Vita✓" : "Vita…";
    const auditus = lives.auditus_live ? "Auditus✓" : "Auditus…";
    const sustain = lives.verdict || "life_hold";
    const rte = up?.pillars?.right_to_exist || {};
    const mandate = rte.mandate_sealed ? "mandate✓" : "mandate…";
    const h7 = up?.pillars?.hostess7_brain || {};
    const brain = h7.verified ? "H7✓" : (h7.corrupted ? "H7!" : "H7…");
    const livesBit = ` · ${brain} · ${vita} · ${auditus} · ${sustain} · ${mandate}`;
    detail.textContent =
      `think tanks ${tanks} · 3D/4D ${nets} · ${movement}${motionBit}${livesBit}${ellieBit} · threat ${posture} · lethal armed`;
  }

  function boot() {
    ensureBanner();
    refresh().catch(() => {});
    setInterval(() => refresh().catch(() => {}), REFRESH_MS);
  }

  global.NexusUniversalProtector = { boot, refresh };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);