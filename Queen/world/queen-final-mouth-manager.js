/**
 * Final Mouth Manager — NEXUS C2 operator surface for queen-mouthball + ironclad block.
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
    ctx.fillStyle = "#100810";
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
      ctx.fillStyle = color || "#d87ae8";
      ctx.globalAlpha = 0.55 + t * 0.45;
      ctx.fillRect(i * barW + 1, h - bh - 8, Math.max(1, barW - 2), bh);
    });
    ctx.globalAlpha = 1;
  }

  function setLevel(ok) {
    const pill = $("qfm-level");
    if (!pill) return;
    if (ok === false) {
      pill.dataset.level = "warn";
      pill.textContent = "MUTED";
    } else {
      pill.dataset.level = "ok";
      pill.textContent = "VOICED";
    }
  }

  function renderModes(modes, active) {
    const el = $("qfm-modes");
    if (!el) return;
    if (!Array.isArray(modes) || !modes.length) {
      el.innerHTML = "<span class=\"qfm-motto\">Modes pending…</span>";
      return;
    }
    el.innerHTML = modes
      .map((m) => {
        const id = m.id || m;
        const label = m.label || id;
        const cls = id === active ? "qfm-mode-pill active" : "qfm-mode-pill";
        return `<span class="${cls}">${label}</span>`;
      })
      .join("");
  }

  function applyMouthball(doc) {
    if (!doc) return;
    const product = doc.product || {};
    const twins = product.twins || {};
    const final = doc.final_mouth || {};
    $("qfm-loquor").textContent = twins.living || "Loquor";
    $("qfm-living-hint").textContent = "living mouth";
    $("qfm-veritas").textContent = twins.truth || "Veritas Vox";
    $("qfm-truth-hint").textContent = doc.mouth?.truth_forward ? "forward on" : "truth voice";
    $("qfm-mode").textContent = final.active_mode || "—";
    $("qfm-profile").textContent = `profile ${final.active_profile || "—"}`;
    $("qfm-product").textContent = product.name || "The Final Mouth";
    $("qfm-version").textContent = product.version || "—";
    $("qfm-codec").textContent = product.codec || "GVC1";
    $("qfm-rule").textContent = (doc.rule || product.rule || "").slice(0, 48);
    const vf = final.voice_fix || {};
    $("qfm-rate").textContent = vf.rate_wpm != null ? `${vf.rate_wpm} wpm` : "—";
    $("qfm-pitch").textContent = vf.pitch_semitones != null ? `${vf.pitch_semitones} st` : "—";
    const spec = final.spectrum || {};
    $("qfm-formants").textContent = Array.isArray(spec.formants_hz)
      ? spec.formants_hz.map((f) => Math.round(f)).join(" · ")
      : "—";
    const neural = doc.mouth_neural || {};
    $("qfm-neural").textContent = neural.available ? (neural.ok ? "ready" : "warm") : "—";
    renderModes(final.modes, final.active_mode);
    drawSpectrum($("qfm-spectrum"), spec.bins, "#d87ae8");
    $("qfm-ts").textContent = doc.updated || "—";
  }

  function applyBlock(doc) {
    if (!doc) return;
    $("qfm-held").textContent = doc.held ? "HELD" : "OPEN";
    $("qfm-headroom").textContent = `headroom ${doc.headroom_pct != null ? Number(doc.headroom_pct).toFixed(1) : "—"}%`;
    $("qfm-block-posture").textContent = doc.posture || "—";
    const ocr = doc.ocr || {};
    $("qfm-ocr").textContent = ocr.hit_count != null ? String(ocr.hit_count) : "—";
    setLevel(doc.ok !== false);
  }

  async function loadG16() {
    const el = $("qfm-g16");
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
    const status = $("qfm-status");
    if (status) status.textContent = "Polling mouthball + block…";
    try {
      const [mouth, block] = await Promise.all([
        fetchPanel("/api/queen-mouthball"),
        fetchPanel("/api/field-final-mouth-block"),
      ]);
      applyMouthball(mouth);
      applyBlock(block);
      if (status) status.textContent = "Live · mouthball + ironclad block";
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
      setLevel(false);
    }
  }

  async function armMouth() {
    const status = $("qfm-status");
    if (status) status.textContent = "Arming mouthball…";
    try {
      await fetchPanel("/api/queen-mouthball", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "arm", mode: "dishes" }),
      });
      await refresh();
      if (status) status.textContent = "Voice armed";
    } catch (e) {
      if (status) status.textContent = `Arm failed: ${e.message || e}`;
    }
  }

  $("qfm-refresh")?.addEventListener("click", refresh);
  $("qfm-arm")?.addEventListener("click", armMouth);
  loadG16();
  refresh();
  setInterval(refresh, REFRESH_MS);
})();