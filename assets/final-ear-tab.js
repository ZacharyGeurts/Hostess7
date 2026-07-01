/**
 * Final_Ear — dedicated NEXUS panel tab (auditory spectrum, tracker, truth).
 */
(function (global) {
  "use strict";

  const API = "/api/queen-earball";
  let earDoc = null;
  let waterfallHistory = [];
  let animId = 0;
  let phase = 0;

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function log(msg) {
    const el = document.getElementById("fer-log");
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

  function drawSpectrumBars(canvas, bins, color) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#020408";
    ctx.fillRect(0, 0, w, h);
    const data = bins || [];
    if (!data.length) return;
    const n = data.length;
    const barW = w / n;
    let minDb = -72;
    let maxDb = -6;
    data.forEach((b) => {
      if (b.db < minDb) minDb = b.db;
      if (b.db > maxDb) maxDb = b.db;
    });
    const span = Math.max(maxDb - minDb, 1);
    data.forEach((b, i) => {
      const t = (b.db - minDb) / span;
      const bh = Math.max(2, t * (h - 20));
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.55 + t * 0.45;
      ctx.fillRect(i * barW + 1, h - bh - 8, Math.max(1, barW - 2), bh);
    });
    ctx.globalAlpha = 1;
  }

  function drawWaterfall(canvas, history, color) {
    if (!canvas || !history.length) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const rowH = Math.max(2, Math.floor(h / Math.max(history.length, 1)));
    ctx.fillStyle = "#020408";
    ctx.fillRect(0, 0, w, h);
    history.slice(-Math.floor(h / rowH)).forEach((row, ri) => {
      const y = h - (ri + 1) * rowH;
      const bins = row.bins || [];
      const n = bins.length || 1;
      bins.forEach((b, i) => {
        const t = Math.min(1, Math.max(0, (b.db + 72) / 72));
        const r = Math.floor(255 * (1 - t) * 0.3);
        const g = Math.floor(180 + 75 * t);
        const bl = Math.floor(100 * t);
        ctx.fillStyle = `rgb(${r},${g},${bl})`;
        ctx.fillRect((i / n) * w, y, w / n + 1, rowH);
      });
    });
    ctx.fillStyle = color + "cc";
    ctx.font = "10px monospace";
    ctx.fillText("Hz →", 4, 12);
  }

  async function fetchSpectrum() {
    const j = await dispatch("spectrum", { seconds: 0.5 });
    if (j.bins) {
      waterfallHistory.push(j);
      if (waterfallHistory.length > 120) waterfallHistory.shift();
    }
    return j;
  }

  function renderProfiles(doc) {
    const el = document.getElementById("fer-profiles");
    if (!el) return;
    const equip = doc.equipment || {};
    const profiles = equip.profiles || (doc.technology?.gac1?.profiles) || [];
    const list = Array.isArray(profiles) ? profiles : [];
    const active = doc.final_ear?.ear?.active_profile || doc.ear?.active_profile || "human_binaural";
    if (!list.length && doc.final_ear) {
      el.innerHTML = `<span class="meta">Profile <strong>${esc(active)}</strong> · ${equip.total ?? "—"} equipment paths</span>`;
      return;
    }
    el.innerHTML = list.slice(0, 12).map((p) => {
      const id = p.id || p;
      const label = p.label || id;
      const cls = id === active ? "sense-profile-chip active" : "sense-profile-chip";
      return `<button type="button" class="${cls}" data-ear-profile="${esc(id)}">${esc(label)}</button>`;
    }).join("");
    el.querySelectorAll("[data-ear-profile]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        log(await dispatch("arm", { mode: "dishes", profile: btn.dataset.earProfile }));
        await refresh();
      });
    });
  }

  function renderTracks(doc) {
    const el = document.getElementById("fer-tracks");
    if (!el) return;
    const tracker = doc.technology?.sound_tracker || {};
    const tracks = tracker.tracks || [];
    if (!tracks.length) {
      el.innerHTML = `<li class="meta">No tracked sources — run Sense all or Follow desktop</li>`;
      return;
    }
    el.innerHTML = tracks.slice(0, 10).map((t) =>
      `<li><code>${esc(t.sound_id || "?")}</code> ${esc(t.label || "")} · ${esc(t.heading_deg ?? "?")}° · ${t.motion?.is_moving ? "moving" : "hold"}</li>`
    ).join("");
  }

  function renderStatus(doc) {
    earDoc = doc;
    const el = document.getElementById("fer-status");
    if (!el || !doc) return;
    const prod = doc.product || {};
    const final = doc.final_ear || {};
    const sov = doc.sovereign_time || doc.technology?.sovereign_time || {};
    el.innerHTML = [
      `<div class="sense-stats">`,
      `<span><strong>${esc(prod.name || "Final Ear")}</strong> ${esc(prod.version || "")}</span>`,
      `<span>Codec <strong>${esc(prod.codec || "GAC1")}</strong></span>`,
      `<span>Mode <strong>${esc(final.ear?.active_mode || "dishes")}</strong></span>`,
      `<span>Sovereign <strong>${sov.ok !== false ? "✓" : "…"}</strong></span>`,
      `<span>Sources <strong>${doc.technology?.sound_tracker?.track_count ?? "—"}</strong></span>`,
      `</div>`,
      `<p class="meta">${esc(doc.rule || "")}</p>`,
    ].join("");
    renderProfiles(doc);
    renderTracks(doc);
  }

  async function paintSpectrum() {
    const spec = await fetchSpectrum();
    drawSpectrumBars(document.getElementById("fer-spectrum"), spec.bins, "#4de88a");
    drawWaterfall(document.getElementById("fer-waterfall"), waterfallHistory, "#4de88a");
    const meta = document.getElementById("fer-spectrum-meta");
    if (meta) {
      meta.textContent = `Peak ${spec.peak_hz ?? "—"} Hz @ ${spec.peak_db ?? "—"} dB · RMS ${spec.rms_db ?? "—"} dB · ${spec.capture?.backend || "live"}`;
    }
  }

  function tickAnim() {
    if (document.getElementById("view-final-ear")?.classList.contains("active")) {
      phase += 0.02;
    }
    animId = requestAnimationFrame(tickAnim);
  }

  let spectrumTimer = 0;
  function startSpectrumPoll() {
    if (spectrumTimer) return;
    spectrumTimer = setInterval(() => {
      if (document.getElementById("view-final-ear")?.classList.contains("active")) {
        paintSpectrum().catch(() => {});
      }
    }, 2500);
  }

  function bindActions() {
    document.getElementById("fer-arm")?.addEventListener("click", async () => {
      log(await dispatch("arm", { mode: "dishes" }));
      await refresh();
    });
    document.getElementById("fer-truth")?.addEventListener("click", async () =>
      log(await dispatch("truth_filter", { evidence: { mouth_correlation: 0.88 } }))
    );
    document.getElementById("fer-fusion")?.addEventListener("click", async () =>
      log(await dispatch("eye_ear_fusion", { evidence: { mouth_correlation: 0.91, speech_present: true }, existence: { correlation: 0.84 } }))
    );
    document.getElementById("fer-sense-all")?.addEventListener("click", async () => log(await dispatch("sense_all")));
    document.getElementById("fer-desktop")?.addEventListener("click", async () => log(await dispatch("desktop_audio", { follow: true })));
    document.getElementById("fer-verify")?.addEventListener("click", async () => log(await dispatch("verify")));
    document.getElementById("fer-refresh")?.addEventListener("click", () => refresh());
  }

  async function refresh() {
    try {
      const r = await fetch(API);
      const j = await r.json();
      renderStatus(j);
      await paintSpectrum();
      global.SenseTrainingWire?.initForPanel?.("final-ear");
    } catch (e) {
      log("Ear refresh failed: " + e.message);
    }
  }

  function init() {
    bindActions();
    startSpectrumPoll();
    if (!animId) tickAnim();
    ["fer-spectrum", "fer-waterfall"].forEach((id) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;
      const ro = new ResizeObserver(() => {
        canvas.width = canvas.clientWidth * (devicePixelRatio || 1);
        canvas.height = canvas.clientHeight * (devicePixelRatio || 1);
      });
      ro.observe(canvas);
      canvas.width = canvas.clientWidth * (devicePixelRatio || 1);
      canvas.height = canvas.clientHeight * (devicePixelRatio || 1);
    });
  }

  global.FinalEarTab = { init, refresh, renderStatus, paintSpectrum };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);