/**
 * Final Eye Manager — NEXUS C2 operator surface for queen-eyeball + ironclad block.
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

  function drawVisionPlate(canvas, eyeball) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#100810";
    ctx.fillRect(0, 0, w, h);
    const virtual = eyeball?.virtual_eyes?.virtual_eyes || [];
    const n = Math.max(virtual.length, 24);
    for (let i = 0; i < n; i += 1) {
      const t = i / n;
      const bh = 12 + Math.sin(t * Math.PI * 4 + Date.now() / 900) * 40 + 30;
      ctx.fillStyle = "#f472b6";
      ctx.globalAlpha = 0.35 + t * 0.45;
      ctx.fillRect((w / n) * i + 1, h - bh - 8, Math.max(1, w / n - 2), bh);
    }
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "rgba(253, 164, 175, 0.35)";
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, Math.min(w, h) * 0.22, 0, Math.PI * 2);
    ctx.stroke();
  }

  function setLevel(ok) {
    const pill = $("qfy-level");
    if (!pill) return;
    if (ok === false) {
      pill.dataset.level = "warn";
      pill.textContent = "DEGRADED";
    } else {
      pill.dataset.level = "ok";
      pill.textContent = "WATCHING";
    }
  }

  function setKillPill(sk) {
    const pill = $("qfy-kill");
    if (!pill || !sk) return;
    if (sk.ok) {
      pill.dataset.level = "ok";
      pill.textContent = "KILL ARMED";
    } else {
      pill.dataset.level = "warn";
      pill.textContent = "KILL OPEN";
    }
    $("qfy-kill-policy").textContent = sk.kill_policy || "—";
    $("qfy-war").textContent = sk.war_hardened ? "hardened" : "warming";
    $("qfy-kill-motto").textContent = sk.motto || $("qfy-kill-motto").textContent;
  }

  function applyEyeball(doc) {
    if (!doc) return;
    const twins = doc.twins || {};
    const living = twins.living || doc.living || {};
    const truth = twins.truth || doc.truth || {};
    $("qfy-vita").textContent = living.name || living.entity || "Vita";
    $("qfy-living-hint").textContent = living.live ? "live" : (living.role || "living eye");
    $("qfy-veritas").textContent = truth.name || truth.entity || "Veritas";
    $("qfy-truth-hint").textContent = truth.forward ? "forward on" : "truth eye";
    const virtual = doc.virtual_eyes || {};
    const eyes = virtual.virtual_eyes || [];
    $("qfy-virtual").textContent = eyes.length ? String(eyes.length) : (virtual.ok ? "ready" : "—");
    const product = doc.product || {};
    $("qfy-product").textContent = product.product || product.name || "Final_Eye";
    $("qfy-version").textContent = product.version || "—";
    $("qfy-rule").textContent = (doc.rule || product.rule || "").slice(0, 48);
    $("qfy-mesh").textContent = doc.mesh_ok === true ? "woven" : doc.mesh_ok === false ? "check" : "—";
    const sov = doc.sovereign_time || {};
    $("qfy-time").textContent = sov.ok != null ? (sov.ok ? "sealed" : "open") : "—";
    const rig = doc.rig || {};
    $("qfy-rig").textContent = rig.mode ? `${rig.mode} · ${rig.eye_count ?? "—"} eye(s)` : "—";
    const off = doc.offense || {};
    $("qfy-offense").textContent = off.ok != null ? (off.ok ? "armed" : "standby") : "—";
    drawVisionPlate($("qfy-vision"), doc);
    $("qfy-ts").textContent = doc.updated || "—";
  }

  function applyBlock(doc) {
    if (!doc) return;
    $("qfy-held").textContent = doc.held ? "HELD" : "OPEN";
    $("qfy-headroom").textContent = `headroom ${doc.headroom_pct != null ? Number(doc.headroom_pct).toFixed(1) : "—"}%`;
    $("qfy-block-posture").textContent = doc.posture || "—";
    const ocr = doc.ocr || {};
    $("qfy-ocr").textContent = ocr.hit_count != null ? String(ocr.hit_count) : "—";
    setKillPill(doc.secure_kill);
    setLevel(doc.ok !== false);
  }

  async function loadG16() {
    const el = $("qfy-g16");
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
    const status = $("qfy-status");
    if (status) status.textContent = "Polling eyeball + block…";
    try {
      const [eye, block] = await Promise.all([
        fetchPanel("/api/queen-eyeball"),
        fetchPanel("/api/field-final-eye-block"),
      ]);
      applyEyeball(eye);
      applyBlock(block);
      if (status) status.textContent = "Live · eyeball + ironclad block + secure kill";
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
      setLevel(false);
    }
  }

  async function armEye() {
    const status = $("qfy-status");
    if (status) status.textContent = "Arming eyeball…";
    try {
      await fetchPanel("/api/queen-eyeball", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "arm", mode: "dishes" }),
      });
      await refresh();
      if (status) status.textContent = "Vision armed";
    } catch (e) {
      if (status) status.textContent = `Arm failed: ${e.message || e}`;
    }
  }

  $("qfy-refresh")?.addEventListener("click", refresh);
  $("qfy-arm")?.addEventListener("click", armEye);
  loadG16();
  refresh();
  setInterval(refresh, REFRESH_MS);
})();