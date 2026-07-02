/**
 * Final_Eye — dedicated NEXUS panel tab (ocular spectrum, twins, operations).
 */
(function (global) {
  "use strict";

  const API = "/api/queen-eyeball";
  const EYE_PORT = 9479;
  let eyeDoc = null;
  let ocularBins = [];
  let animId = 0;
  let phase = 0;

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function log(msg) {
    const el = document.getElementById("fe-log");
    if (!el) return;
    const line = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
    el.textContent = (el.textContent ? el.textContent + "\n" : "") + line;
    el.scrollTop = el.scrollHeight;
  }

  async function dispatch(action, extra) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    return r.json();
  }

  function drawOcularSpectrum(canvas, bins, color) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#020408";
    ctx.fillRect(0, 0, w, h);
    const data = bins.length ? bins : syntheticOcular(64);
    const n = data.length;
    const barW = w / n;
    let minDb = -60;
    let maxDb = -10;
    data.forEach((b) => {
      if (b.db < minDb) minDb = b.db;
      if (b.db > maxDb) maxDb = b.db;
    });
    const span = Math.max(maxDb - minDb, 1);
    data.forEach((b, i) => {
      const t = (b.db - minDb) / span;
      const bh = Math.max(2, t * (h - 24));
      const x = i * barW;
      const g = ctx.createLinearGradient(0, h, 0, h - bh);
      g.addColorStop(0, color + "22");
      g.addColorStop(1, color);
      ctx.fillStyle = g;
      ctx.fillRect(x + 1, h - bh - 12, Math.max(1, barW - 2), bh);
      if (b.nm) {
        ctx.fillStyle = "rgba(200,220,255,0.35)";
        ctx.font = "9px monospace";
        if (i % 8 === 0) ctx.fillText(String(b.nm), x, h - 2);
      }
    });
    phase += 0.04;
    ctx.strokeStyle = color + "55";
    ctx.beginPath();
    for (let x = 0; x < w; x++) {
      const y = h * 0.35 + Math.sin(x * 0.02 + phase) * 8 + Math.sin(x * 0.05 + phase * 1.3) * 4;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function syntheticOcular(n) {
    const peaks = [420, 530, 560];
    const out = [];
    for (let i = 0; i < n; i++) {
      const nm = 400 + (300 * i) / n;
      let e = 0.05;
      peaks.forEach((p) => {
        e += Math.exp(-0.5 * ((nm - p) / 35) ** 2);
      });
      out.push({ nm: Math.round(nm), db: 20 * Math.log10(Math.max(e, 1e-6)) });
    }
    return out;
  }

  function binsFromProfiles(doc) {
    const eye = doc?.final_eyeball?.eye || doc?.eye || {};
    const profile = eye.active_profile || "human";
    const receptors = [
      { nm: 420, w: 0.9 },
      { nm: 530, w: 1.0 },
      { nm: 560, w: 0.85 },
      { nm: 600, w: 0.4 },
    ];
    return receptors.map((r, i) => ({
      nm: r.nm,
      db: -18 + r.w * 12 + Math.sin(phase + i) * 2,
      band: i,
    }));
  }

  function renderStatus(doc) {
    eyeDoc = doc;
    const el = document.getElementById("fe-status");
    if (!el || !doc) return;
    const prod = doc.product || {};
    const final = doc.final_eyeball || {};
    const twins = doc.twins || {};
    const rig = doc.rig || {};
    el.innerHTML = [
      `<div class="sense-stats">`,
      `<span><strong>${esc(prod.product || "Final_Eye")}</strong> ${esc(prod.version || "")}</span>`,
      `<span>Mode <strong>${esc(final.active_mode || "—")}</strong></span>`,
      `<span>Profile <strong>${esc((final.eye || doc.eye || {}).active_profile || "human")}</strong></span>`,
      `<span>Twins <strong>${twins.living?.live ? "Vita ✓" : "Vita …"}</strong> · <strong>${twins.truth?.forward ? "Veritas ✓" : "Veritas …"}</strong></span>`,
      `<span>Rig <strong>${esc(rig.mode || "—")}</strong></span>`,
      `</div>`,
      `<p class="meta">${esc(doc.rule || final.speak || "")}</p>`,
    ].join("");
    const stream = document.getElementById("fe-stream");
    if (stream) {
      stream.src = `http://127.0.0.1:${EYE_PORT}/api/stream/mjpeg`;
      stream.onerror = () => { stream.style.display = "none"; };
    }
    ocularBins = binsFromProfiles(doc);
    const canvas = document.getElementById("fe-spectrum");
    if (canvas) drawOcularSpectrum(canvas, ocularBins, "#7ec8ff");
  }

  function tickAnim() {
    if (document.getElementById("view-final-eye")?.classList.contains("active")) {
      ocularBins = binsFromProfiles(eyeDoc);
      drawOcularSpectrum(document.getElementById("fe-spectrum"), ocularBins, "#7ec8ff");
    }
    animId = requestAnimationFrame(tickAnim);
  }

  function bindActions() {
    document.getElementById("fe-arm-dishes")?.addEventListener("click", async () => {
      log(await dispatch("arm", { mode: "dishes" }));
      await refresh();
    });
    document.getElementById("fe-arm-person")?.addEventListener("click", async () => {
      log(await dispatch("arm", { mode: "stereo_human" }));
      await refresh();
    });
    document.getElementById("fe-verify")?.addEventListener("click", async () => log(await dispatch("verify")));
    document.getElementById("fe-teach")?.addEventListener("click", async () => log(await dispatch("teach", { lesson: "authority" })));
    document.getElementById("fe-targets")?.addEventListener("click", async () => log(await dispatch("targets")));
    document.getElementById("fe-fusion")?.addEventListener("click", async () => log(await dispatch("fused_analyze", { evidence: { mouth_correlation: 0.9 } })));
    document.getElementById("fe-virtual")?.addEventListener("click", async () => log(await dispatch("virtual_spawn", { mechanism: "wifi_rf" })));
    document.getElementById("fe-refresh")?.addEventListener("click", () => refresh());
  }

  async function refresh() {
    try {
      const r = await fetch(API);
      const j = await r.json();
      renderStatus(j);
      global.SenseTrainingWire?.initForPanel?.("final-eye");
    } catch (e) {
      log("Eye refresh failed: " + e.message);
    }
  }

  function init() {
    bindActions();
    if (!animId) tickAnim();
    const canvas = document.getElementById("fe-spectrum");
    if (canvas) {
      const ro = new ResizeObserver(() => {
        canvas.width = canvas.clientWidth * (devicePixelRatio || 1);
        canvas.height = canvas.clientHeight * (devicePixelRatio || 1);
      });
      ro.observe(canvas);
      canvas.width = canvas.clientWidth * (devicePixelRatio || 1);
      canvas.height = canvas.clientHeight * (devicePixelRatio || 1);
    }
  }

  global.FinalEyeTab = { init, refresh, renderStatus };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);