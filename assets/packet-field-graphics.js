/* Packet Field — zero-cost RTX canvas (paint only when fingerprint changes). */
(function (global) {
  "use strict";

  const RTX = {
    aqua: "#38bdf8",
    cyan: "#22d3ee",
    edge: "#0e7490",
    glow: "rgba(56, 189, 248, 0.35)",
    bg: "#040c14",
    grid: "rgba(56, 189, 248, 0.08)",
  };

  let lastFingerprint = "";
  let capturePending = false;

  function canvas(id) {
    return document.getElementById(id);
  }

  function setupCanvas(el, h) {
    if (!el) return null;
    const ctx = el.getContext("2d");
    if (!ctx) return null;
    const dpr = Math.min(global.devicePixelRatio || 1, 2);
    const w = el.clientWidth || 280;
    const height = h || el.clientHeight || 100;
    if (el.width !== Math.round(w * dpr) || el.height !== Math.round(height * dpr)) {
      el.width = Math.round(w * dpr);
      el.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    return { ctx, w, h: height };
  }

  function padSamples(samples, n) {
    const out = (samples || []).slice(-n).map((v) => Math.max(0, Math.min(1, Number(v) || 0)));
    while (out.length < n) out.unshift(0);
    return out;
  }

  function deriveGraphics(doc) {
    const recent = doc.recent || [];
    const tx = [];
    const rx = [];
    recent.forEach((ev) => {
      const mag = Math.min(1, (Number(ev.length) || 64) / 1400);
      if (ev.direction === "TX") tx.push(mag);
      else if (ev.direction === "RX") rx.push(mag);
    });
    const ports = (doc.ports || []).slice(0, 16);
    const radar = ports.map((p, i) => ({
      port: p.port,
      angle: (i / Math.max(ports.length, 1)) * 360,
      magnitude: Math.min(1, ((p.tx_packets || 0) + (p.rx_packets || 0)) / 40),
      service: p.service,
    }));
    return {
      tx_wave: padSamples(tx, 48),
      rx_wave: padSamples(rx, 48),
      port_radar: radar,
      fingerprint: `${doc.updated}|${tx.length}|${rx.length}|${ports.length}`,
      zero_cost: true,
      theme: "rtx-aqua",
    };
  }

  function drawWave(el, samples, stroke) {
    const c = setupCanvas(el, 100);
    if (!c) return;
    const { ctx, w, h } = c;
    const data = padSamples(samples, 48);
    ctx.fillStyle = RTX.bg;
    ctx.fillRect(0, 0, w, h);
    for (let i = 1; i <= 4; i++) {
      const y = (h * i) / 5;
      ctx.strokeStyle = RTX.grid;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    const mid = h * 0.55;
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = (i / (data.length - 1 || 1)) * (w - 8) + 4;
      const y = mid - v * (h * 0.42);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.shadowColor = RTX.glow;
    ctx.shadowBlur = 6;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.lineTo(w - 4, mid);
    ctx.lineTo(4, mid);
    ctx.closePath();
    ctx.fillStyle = stroke.replace(")", ", 0.12)").replace("rgb", "rgba").replace("#38bdf8", "rgba(56,189,248,0.12)");
    if (stroke.startsWith("#")) {
      ctx.fillStyle = "rgba(56, 189, 248, 0.1)";
    }
    ctx.fill();
  }

  function drawRadar(el, points) {
    const c = setupCanvas(el, 120);
    if (!c) return;
    const { ctx, w, h } = c;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) * 0.38;
    ctx.fillStyle = RTX.bg;
    ctx.fillRect(0, 0, w, h);
    for (let ring = 4; ring >= 1; ring--) {
      ctx.beginPath();
      ctx.arc(cx, cy, (r * ring) / 4, 0, Math.PI * 2);
      ctx.strokeStyle = RTX.grid;
      ctx.stroke();
    }
    (points || []).forEach((p) => {
      const rad = ((Number(p.angle) || 0) - 90) * (Math.PI / 180);
      const mag = Math.max(0.05, Math.min(1, Number(p.magnitude) || 0));
      const x = cx + Math.cos(rad) * r * mag;
      const y = cy + Math.sin(rad) * r * mag;
      const grd = ctx.createRadialGradient(x, y, 0, x, y, 10 + mag * 8);
      grd.addColorStop(0, RTX.cyan);
      grd.addColorStop(1, "rgba(34, 211, 238, 0)");
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.arc(x, y, 6 + mag * 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = RTX.aqua;
      ctx.font = "9px ui-monospace, monospace";
      ctx.fillText(String(p.port || ""), x + 4, y - 2);
    });
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fillStyle = RTX.cyan;
    ctx.fill();
  }

  function packetsTabActive() {
    const view = document.querySelector('.view[data-panel="packets"].active, #packets.view.active');
    return !!view || document.querySelector("#packet-field-wrap")?.offsetParent != null;
  }

  function render(doc) {
    if (!doc || global.NexusRtxZero?.paused?.()) return;
    const gfx = doc.field_graphics || deriveGraphics(doc);
    const fp = gfx.fingerprint || JSON.stringify([gfx.tx_wave?.length, gfx.rx_wave?.length, gfx.port_radar?.length]);
    if (fp === lastFingerprint) return;
    lastFingerprint = fp;
    drawWave(canvas("packet-tx-wave"), gfx.tx_wave, RTX.aqua);
    drawWave(canvas("packet-rx-wave"), gfx.rx_wave, RTX.cyan);
    drawRadar(canvas("packet-port-radar"), gfx.port_radar);
  }

  async function refreshCapture() {
    if (capturePending || document.hidden || !packetsTabActive()) return;
    if (global.NexusRtxZero?.paused?.()) return;
    capturePending = true;
    try {
      await fetch("/api/packet-field/capture", { method: "POST", cache: "no-store" });
    } catch (_) {
      /* zero-cost — skip on miss */
    } finally {
      capturePending = false;
    }
  }

  global.PacketFieldGraphics = { render, refreshCapture };
})(window);