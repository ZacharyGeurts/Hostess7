/**
 * Final Ear Manager — NEXUS C2 operator surface for queen-earball + ironclad block.
 */
(function () {
  "use strict";

  const REFRESH_MS = 8000;
  const $ = (id) => document.getElementById(id);

  function panelPort() {
    try {
      return window.parent?.document?.body?.dataset?.nexusPanelPort
        || document.body?.dataset?.nexusPanelPort
        || "9477";
    } catch {
      return "9477";
    }
  }

  function panelBase() {
    return `http://127.0.0.1:${panelPort()}`;
  }

  async function fetchPanel(path, opts) {
    const url = path.startsWith("http") ? path : `${panelBase()}${path.startsWith("/") ? path : `/${path}`}`;
    const res = await fetch(url, { cache: "no-store", ...(opts || {}) });
    if (!res.ok) throw new Error(`${path} HTTP ${res.status}`);
    return res.json();
  }

  function drawSpectrum(canvas, bins, color) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#040810";
    ctx.fillRect(0, 0, w, h);
    const data = bins || [];
    if (!data.length) return;
    const n = data.length;
    const barW = w / n;
    let minDb = -72;
    let maxDb = -6;
    data.forEach((b) => {
      const db = b.db != null ? b.db : b;
      if (db < minDb) minDb = db;
      if (db > maxDb) maxDb = db;
    });
    const span = Math.max(maxDb - minDb, 1);
    data.forEach((b, i) => {
      const db = b.db != null ? b.db : b;
      const t = (db - minDb) / span;
      const bh = Math.max(2, t * (h - 20));
      ctx.fillStyle = color || "#4dc9e8";
      ctx.globalAlpha = 0.55 + t * 0.45;
      ctx.fillRect(i * barW + 1, h - bh - 8, Math.max(1, barW - 2), bh);
    });
    ctx.globalAlpha = 1;
  }

  function setLevel(ok) {
    const pill = $("qfe-level");
    if (!pill) return;
    if (ok === false) {
      pill.dataset.level = "warn";
      pill.textContent = "DEGRADED";
    } else {
      pill.dataset.level = "ok";
      pill.textContent = "LISTENING";
    }
  }

  function applyEarball(doc) {
    if (!doc) return;
    const twins = doc.twins || {};
    const living = twins.living || {};
    const truth = twins.truth || {};
    $("qfe-auditus").textContent = living.live ? "LIVE" : (living.name || "Auditus");
    $("qfe-living-hint").textContent = living.role || "living ear";
    $("qfe-veritas").textContent = truth.forward ? "FORWARD" : (truth.name || "Veritas");
    $("qfe-truth-hint").textContent = `fwd ${twins.forward_count ?? "—"} · rej ${twins.lies_rejected ?? "—"}`;
    const virtual = doc.virtual || doc.technology?.virtual_ear || {};
    $("qfe-virtual").textContent = virtual.count != null ? String(virtual.count) : (virtual.ok ? "ready" : "—");
    const product = doc.product || {};
    $("qfe-product").textContent = product.name || "The Final Ear";
    $("qfe-version").textContent = product.version || "—";
    $("qfe-codec").textContent = product.codec || "GAC1";
    $("qfe-rule").textContent = (doc.rule || product.rule || "").slice(0, 48);
    const h7 = doc.hostess7 || {};
    $("qfe-bridge").textContent = h7.bridge ? "linked" : "—";
    $("qfe-stack").textContent = Array.isArray(h7.neural_stack) ? `${h7.neural_stack.length} nets` : "—";
    const st = doc.technology?.sovereign_time || {};
    $("qfe-time").textContent = st.ok != null ? (st.ok ? "sealed" : "open") : "—";
    const tr = doc.technology?.sound_tracker || {};
    $("qfe-tracker").textContent = tr.ok ? "tracking" : "—";
    const sp = doc.technology?.secure_path || {};
    if (sp.pipeline) $("qfe-pipeline").textContent = sp.pipeline;
    $("qfe-ts").textContent = doc.updated || "—";
  }

  function applyBlock(doc) {
    if (!doc) return;
    $("qfe-held").textContent = doc.held ? "HELD" : "OPEN";
    $("qfe-headroom").textContent = `headroom ${doc.headroom_pct != null ? Number(doc.headroom_pct).toFixed(1) : "—"}%`;
    $("qfe-block-posture").textContent = doc.posture || "—";
    const ocr = doc.ocr || {};
    $("qfe-ocr").textContent = ocr.hit_count != null ? String(ocr.hit_count) : "—";
    setLevel(doc.ok !== false);
  }

  async function loadG16() {
    const el = $("qfe-g16");
    if (!el) return;
    try {
      const doc = await fetchPanel("/api/nexus-c2");
      const g16 = doc.g16 || {};
      const ready = g16.ok !== false && g16.ready !== false;
      el.textContent = g16.label || (ready ? "G16 ready" : "G16 warming");
      el.classList.toggle("ok", ready);
      el.classList.toggle("bad", !ready);
    } catch {
      el.textContent = "G16 offline";
      el.classList.add("bad");
    }
  }

  async function refresh() {
    const status = $("qfe-status");
    if (status) status.textContent = "Polling earball + block…";
    try {
      const [ear, block, spectrum] = await Promise.all([
        fetchPanel("/api/queen-earball"),
        fetchPanel("/api/field-final-ear-block"),
        fetchPanel("/api/queen-earball", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "spectrum", seconds: 0.25 }),
        }).catch(() => null),
      ]);
      applyEarball(ear);
      applyBlock(block);
      const bins = spectrum?.bins || spectrum?.spectrum?.bins || ear?.final_ear?.spectrum?.bins;
      drawSpectrum($("qfe-spectrum"), bins, "#4dc9e8");
      if (status) status.textContent = "Live · earball + ironclad block";
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
      setLevel(false);
    }
  }

  async function armEar() {
    const status = $("qfe-status");
    if (status) status.textContent = "Arming earball…";
    try {
      await fetchPanel("/api/queen-earball", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "arm", mode: "dishes" }),
      });
      await refresh();
      if (status) status.textContent = "Ear armed";
    } catch (e) {
      if (status) status.textContent = `Arm failed: ${e.message || e}`;
    }
  }

  $("qfe-refresh")?.addEventListener("click", refresh);
  $("qfe-arm")?.addEventListener("click", armEar);
  loadG16();
  refresh();
  setInterval(refresh, REFRESH_MS);
})();