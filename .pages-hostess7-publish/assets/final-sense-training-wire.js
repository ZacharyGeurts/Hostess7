/**
 * Sense training wires — shared matrix + per-tab session UI for Eye, Ear, Mouth.
 */
(function (global) {
  "use strict";

  const TRAIN_API = "/api/hostess7/training";
  const TRACK_MAP = {
    "final-eye": "final_eye",
    "final-ear": "final_ear",
    "final-mouth": "final_mouth",
  };

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function pct(n) {
    return Math.round(Math.max(0, Math.min(1, Number(n) || 0)) * 100);
  }

  function levelClass(level) {
    const l = String(level || "pending").toLowerCase();
    if (l === "mastered") return "level-mastered";
    if (l === "complete" || l === "fluent") return "level-complete";
    if (l === "training") return "level-training";
    return "level-pending";
  }

  function drawMiniWire(canvas, graph, focusGroup) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width = Math.max(280, canvas.clientWidth) * 2;
    const h = canvas.height = Math.max(140, canvas.clientHeight) * 2;
    ctx.fillStyle = "#060a12";
    ctx.fillRect(0, 0, w, h);
    const nodes = (graph && graph.nodes) || [];
    const edges = (graph && graph.edges) || [];
    const focus = nodes.filter((n) => {
      if (!focusGroup) return true;
      const g = n.group || "";
      return g.startsWith("sense") || n.id.includes("sense") || n.id.includes("final_") || g === "training_track" && String(n.id).includes("final");
    });
    if (!focus.length) {
      ctx.fillStyle = "#8fb4d9";
      ctx.font = "22px system-ui,sans-serif";
      ctx.fillText("Sense wires load after Assess", 16, h / 2);
      return;
    }
    const xs = focus.map((n) => n.x || 0);
    const ys = focus.map((n) => n.z || n.y || 0);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = 36;
    const sx = (x) => pad + ((x - minX) / Math.max(maxX - minX, 1)) * (w - pad * 2);
    const sy = (y) => pad + ((y - minY) / Math.max(maxY - minY, 1)) * (h - pad * 2);
    const byId = new Map(focus.map((n) => [n.id, n]));
    const focusIds = new Set(focus.map((n) => n.id));
    ctx.strokeStyle = "rgba(56, 189, 248, 0.35)";
    ctx.lineWidth = 2;
    edges.forEach((e) => {
      if (!focusIds.has(e.from) && !focusIds.has(e.to)) return;
      const a = byId.get(e.from) || nodes.find((n) => n.id === e.from);
      const b = byId.get(e.to) || nodes.find((n) => n.id === e.to);
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(sx(a.x), sy(a.z || a.y));
      ctx.lineTo(sx(b.x), sy(b.z || b.y));
      ctx.stroke();
    });
    focus.forEach((n) => {
      const x = sx(n.x);
      const y = sy(n.z || n.y);
      const r = n.id === "hostess7_core" || n.id === "sense_package_hub" ? 12 : 7;
      ctx.fillStyle = n.color || "#60a5fa";
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function renderSessions(container, trackId, trackData, doctrine) {
    if (!container) return;
    const sess = (doctrine?.sessions || {})[trackId] || {};
    const steps = trackData?.steps || [];
    const score = pct(trackData?.score);
    const passed = trackData?.passed ?? "—";
    const total = trackData?.total ?? (sess.steps || []).length;
    container.innerHTML = `
      <div class="sense-stats">
        <span>Session <strong>${esc(sess.label || trackId)}</strong></span>
        <span>Score <strong>${score}%</strong></span>
        <span>Steps <strong>${passed}/${total}</strong></span>
        <span class="h7-badge ${levelClass(trackData?.level)}">${esc(trackData?.level || "pending")}</span>
      </div>
      <ul class="sense-track-list">${(steps.length ? steps : (sess.steps || [])).map((s) =>
        `<li>${s.ok ? "✓" : "·"} <strong>${esc(s.label || s.id)}</strong> <span class="meta">${esc(s.detail || s.action || "")}</span></li>`
      ).join("")}</ul>
      <div class="sense-actions">
        <button type="button" class="primary sense-train-run" data-sense-track="${esc(trackId)}">Run full session</button>
        <button type="button" class="sense-train-matrix" data-view-jump="training">Open matrix →</button>
        <button type="button" class="sense-train-wire-all" data-sense-wire="sense_neural_wire">Wire all three</button>
      </div>`;
    container.querySelector(".sense-train-run")?.addEventListener("click", async (ev) => {
      const btn = ev.currentTarget;
      const panelKey = container.closest(".sense-tab-wrap")?.id?.replace("view-", "") || "";
      btn.disabled = true;
      try {
        const r = await fetch(`${TRAIN_API}/track/${trackId}`, { method: "POST" });
        const j = await r.json();
        await fetchBundle();
        await refreshTab(panelKey);
        global.NexusTraining?.refresh?.(true);
        const logId = { final_eye: "fe-train-log", final_ear: "fer-train-log", final_mouth: "fm-train-log" }[trackId];
        const log = logId ? document.getElementById(logId) : null;
        if (log) log.textContent = JSON.stringify(j, null, 2);
      } finally {
        btn.disabled = false;
      }
    });
    container.querySelector(".sense-train-wire-all")?.addEventListener("click", async (ev) => {
      const btn = ev.currentTarget;
      const panelKey = container.closest(".sense-tab-wrap")?.id?.replace("view-", "") || "";
      btn.disabled = true;
      try {
        await fetch(`${TRAIN_API}/track/sense_neural_wire`, { method: "POST" });
        await fetchBundle();
        await refreshTab(panelKey);
        global.NexusTraining?.refresh?.(true);
      } finally {
        btn.disabled = false;
      }
    });
  }

  let lastBundle = null;

  async function fetchBundle() {
    const r = await fetch(`${TRAIN_API}/bundle`, { cache: "no-store" });
    if (!r.ok) throw new Error("bundle failed");
    lastBundle = await r.json();
    return lastBundle;
  }

  const PREFIX = { "final-eye": "fe", "final-ear": "fer", "final-mouth": "fm" };

  async function refreshTab(panelKey) {
    const trackId = TRACK_MAP[panelKey] || panelKey;
    const prefix = PREFIX[panelKey];
    if (!prefix) return;
    try {
      const bundle = lastBundle || (await fetchBundle());
      const tracks = (bundle.assessment || {}).tracks || {};
      const trackData = tracks[trackId] || (bundle.sense_training?.tracks || {})[trackId];
      const doctrine = (bundle.sense_training || {}).doctrine || {};
      renderSessions(document.getElementById(`${prefix}-training-sessions`), trackId, trackData, doctrine);
      drawMiniWire(document.getElementById(`${prefix}-training-wire`), bundle.wireframe || {}, "sense");
    } catch (_) {}
  }

  function initForPanel(panelKey) {
    const prefix = PREFIX[panelKey];
    if (!prefix) return;
    const canvas = document.getElementById(`${prefix}-training-wire`);
    if (canvas && !canvas.dataset.ro) {
      const ro = new ResizeObserver(() => {
        if (lastBundle?.wireframe) drawMiniWire(canvas, lastBundle.wireframe, "sense");
      });
      ro.observe(canvas);
      canvas.dataset.ro = "1";
    }
    refreshTab(panelKey);
  }

  function renderMatrixSense(bundle) {
    const el = document.getElementById("h7-sense-training");
    if (!el) return;
    const st = bundle.sense_training || {};
    const tracks = st.tracks || (bundle.assessment || {}).tracks || {};
    const rows = ["final_eye", "final_ear", "final_mouth", "sense_neural_wire"]
      .map((id) => [id, tracks[id]])
      .filter(([, t]) => t);
    const doctrine = st.doctrine || {};
    const sessIds = ["final_eye", "final_ear", "final_mouth", "sense_neural_wire"];
    if (!rows.length) {
      el.innerHTML = `<p class="h7-sub">Sense training wires — run Assess, then train Final Eye, Ear, or Mouth from their tabs or here. <span style="color:#e8c878">Music theory steps are woven into each sense session (ear · mouth · brain especially).</span></p>
        <ul class="sense-track-list" style="margin:8px 0">${sessIds.map((id) => {
          const s = (doctrine.sessions || {})[id] || {};
          const label = s.label || id.replace(/_/g, " ");
          const steps = (s.steps || []).length;
          return `<li><strong>${esc(label)}</strong> <span class="meta">${steps} step${steps === 1 ? "" : "s"}</span></li>`;
        }).join("")}</ul>
        <div class="h7-quick-actions" style="margin-top:8px">
          <button type="button" data-view-jump="final-eye">Final Eye tab</button>
          <button type="button" data-view-jump="final-ear">Final Ear tab</button>
          <button type="button" data-view-jump="final-mouth">Final Mouth tab</button>
          <button type="button" class="h7-sense-track-train" data-track="sense_neural_wire">Wire all three</button>
        </div>`;
      el.querySelector(".h7-sense-track-train")?.addEventListener("click", async (ev) => {
        const btn = ev.currentTarget;
        btn.disabled = true;
        try {
          await fetch(`${TRAIN_API}/track/sense_neural_wire`, { method: "POST" });
          global.NexusTraining?.refresh?.(true);
        } finally {
          btn.disabled = false;
        }
      });
      return;
    }
    el.innerHTML = `<p class="h7-sub"><strong>Sense package wires</strong> — Eye · Ear · Mouth fused to Hostess 7 matrix · <span style="color:#e8c878">♪ music theory on every session</span>.</p>
      <div class="h7-tracks" style="margin-top:10px">${rows.map(([id, t]) => {
        const tab = id.replace("final_", "final-").replace("sense_neural_wire", "training");
        const score = pct(t.score);
        return `<article class="h7-card" style="min-width:200px">
          <h2>${esc(t.label || id)}</h2>
          <span class="h7-badge ${levelClass(t.level)}">${esc(t.level || "pending")}</span>
          <div class="score">${score}%</div>
          <div class="bar"><i style="width:${score}%"></i></div>
          <button type="button" class="h7-sense-track-train" data-track="${esc(id)}">Train</button>
          ${id.startsWith("final_") ? `<button type="button" data-view-jump="${esc(tab)}" style="margin-left:6px">Tab →</button>` : ""}
        </article>`;
      }).join("")}</div>`;
    el.querySelectorAll(".h7-sense-track-train").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        await fetch(`${TRAIN_API}/track/${btn.dataset.track}`, { method: "POST" });
        btn.disabled = false;
        global.NexusTraining?.refresh?.(true);
      });
    });
  }

  function setBundleFromSlice(slice) {
    if (!slice || slice.schema !== "hostess7-training/v1" || !slice.tracks) return;
    lastBundle = {
      schema: "hostess7-training-viewer/v1",
      assessment: {
        tracks: slice.tracks,
        overall_score: slice.overall_score,
        completion_level: slice.completion_level,
      },
      sense_training: slice.sense_training || {},
      wireframe: slice.wireframe || {},
    };
  }

  global.SenseTrainingWire = {
    initForPanel,
    refreshTab,
    drawMiniWire,
    renderMatrixSense,
    fetchBundle,
    setBundleFromSlice,
    get lastBundle() { return lastBundle; },
    setBundle(b) { lastBundle = b; },
  };
})(window);