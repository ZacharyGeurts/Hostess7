/**
 * Final_Mouth — voice fix, vocal spectrum, TTS, mouth-ear-eye fusion.
 */
(function (global) {
  "use strict";

  const API = "/api/queen-mouthball";
  let mouthDoc = null;
  let fixState = { pitch_semitones: 0, rate_wpm: 140, eq_low_db: 0, eq_mid_db: 0, eq_high_db: 0 };

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function log(msg) {
    const el = document.getElementById("fm-log");
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

  function drawVocalSpectrum(canvas, bins) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#08040a";
    ctx.fillRect(0, 0, w, h);
    const data = bins || [];
    if (!data.length) return;
    const n = data.length;
    const barW = w / n;
    data.forEach((b, i) => {
      const t = Math.min(1, Math.max(0, (b.db + 50) / 50));
      const bh = Math.max(3, t * (h - 24));
      const g = ctx.createLinearGradient(0, h, 0, h - bh);
      g.addColorStop(0, "#f0a06033");
      g.addColorStop(1, "#f0a060");
      ctx.fillStyle = g;
      ctx.fillRect(i * barW + 1, h - bh - 10, Math.max(1, barW - 2), bh);
    });
    (mouthDoc?.vocal_spectrum?.visemes || []).forEach((v, i) => {
      const x = 12 + i * 36;
      ctx.fillStyle = "rgba(240,160,96,0.25)";
      ctx.fillRect(x, h - 28, 28, 18);
      ctx.fillStyle = "#f0d060";
      ctx.font = "10px sans-serif";
      ctx.fillText(v, x + 4, h - 14);
    });
  }

  function browserSpeak(text, rate, pitch) {
    if (!global.speechSynthesis || !text) return false;
    const u = new SpeechSynthesisUtterance(text);
    u.rate = Math.min(2, Math.max(0.5, rate / 140));
    u.pitch = Math.min(2, Math.max(0.5, 1 + pitch / 12));
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
    return true;
  }

  function renderFusion(score) {
    const el = document.getElementById("fm-fusion-bar");
    const label = document.getElementById("fm-fusion-label");
    const pct = Math.round((score || 0) * 100);
    if (el) el.style.width = pct + "%";
    if (label) label.textContent = `Fusion ${pct}% — mouth·ear·eye correlation`;
  }

  function renderNeuralHemisphere(neural) {
    const el = document.getElementById("fm-neural-hemisphere");
    if (!el || !neural) return;
    const align = neural.thought_voice_alignment != null
      ? Math.round(Number(neural.thought_voice_alignment) * 100)
      : null;
    const risk = neural.deception_risk != null
      ? Math.round(Number(neural.deception_risk) * 100)
      : (align != null ? 100 - align : null);
    const lessons = neural.lessons_passed || [];
    el.innerHTML = [
      `<div class="sense-stats">`,
      `<span>Hemisphere <strong>${esc(neural.hemisphere || "voice_egress")}</strong></span>`,
      align != null ? `<span>Alignment <strong>${align}%</strong></span>` : "",
      risk != null ? `<span>Deception risk <strong>${risk}%</strong></span>` : "",
      neural.deception_possible !== false ? `<span class="h7-badge level-training">deception possible</span>` : "",
      `</div>`,
      `<p class="meta">${esc(neural.thought_voice_rule || neural.rule || "Thought and utterance may diverge — mouth is its own brain.")}</p>`,
      lessons.length ? `<p class="meta">Lessons sealed: ${esc(lessons.join(", "))}</p>` : "",
    ].join("");
  }

  async function renderThoughtUtterance() {
    const el = document.getElementById("fm-thought-utterance");
    if (!el) return;
    const thought = (document.getElementById("fm-speak-text")?.value || "").trim()
      || "Field voice online. Mouth owns the sound.";
    try {
      const prep = await dispatch("prepare_utterance", { thought, text: thought });
      const align = prep.thought_voice_alignment != null
        ? Math.round(Number(prep.thought_voice_alignment) * 100)
        : null;
      el.innerHTML = [
        `<div class="fm-thought-row"><strong>Thought</strong><p>${esc(prep.thought || thought)}</p></div>`,
        `<div class="fm-utterance-row"><strong>Utterance</strong><p>${esc(prep.utterance || thought)}</p></div>`,
        align != null ? `<p class="meta">Alignment ${align}% · label ${esc(prep.top_label || "—")}${prep.deception_possible ? " · deception possible" : ""}</p>` : "",
      ].join("");
    } catch (e) {
      el.innerHTML = `<p class="meta">Prepare failed: ${esc(e.message)}</p>`;
    }
  }

  function renderStatus(doc) {
    mouthDoc = doc;
    const el = document.getElementById("fm-status");
    if (!el || !doc) return;
    const prod = doc.product || {};
    const final = doc.final_mouth || {};
    const neural = doc.mouth_neural || {};
    fixState = { ...fixState, ...(final.voice_fix || {}) };
    el.innerHTML = [
      `<div class="sense-stats">`,
      `<span><strong>${esc(prod.name || "Final Mouth")}</strong> ${esc(prod.version || "1.0.0")}</span>`,
      `<span>Mode <strong>${esc(final.active_mode || "dishes")}</strong></span>`,
      `<span>Profile <strong>${esc(final.active_profile || "human_neutral")}</strong></span>`,
      `<span>Voice <strong>${esc(final.active_voice || "robotics_brief")}</strong></span>`,
      neural.network_id ? `<span>Neural <strong>${esc(neural.network_id)}</strong></span>` : "",
      `</div>`,
      `<p class="meta">${esc(doc.rule || "")}</p>`,
    ].join("");
    renderNeuralHemisphere(neural);
    const spec = final.spectrum || doc.vocal_spectrum || {};
    drawVocalSpectrum(document.getElementById("fm-spectrum"), spec.bins);
    syncSliders();
  }

  function syncSliders() {
    const map = {
      "fm-pitch": "pitch_semitones",
      "fm-rate": "rate_wpm",
      "fm-eq-low": "eq_low_db",
      "fm-eq-mid": "eq_mid_db",
      "fm-eq-high": "eq_high_db",
    };
    Object.entries(map).forEach(([id, key]) => {
      const inp = document.getElementById(id);
      const val = document.getElementById(id + "-val");
      if (inp) inp.value = fixState[key] ?? inp.value;
      if (val) val.textContent = String(fixState[key] ?? inp?.value ?? "");
    });
  }

  function bindFixSliders() {
    const rows = [
      ["fm-pitch", "pitch_semitones", -12, 12, 0.5],
      ["fm-rate", "rate_wpm", 80, 220, 5],
      ["fm-eq-low", "eq_low_db", -12, 12, 1],
      ["fm-eq-mid", "eq_mid_db", -12, 12, 1],
      ["fm-eq-high", "eq_high_db", -12, 12, 1],
    ];
    rows.forEach(([id, key]) => {
      document.getElementById(id)?.addEventListener("input", async (ev) => {
        fixState[key] = parseFloat(ev.target.value);
        document.getElementById(id + "-val").textContent = ev.target.value;
        const j = await dispatch("voice_fix", fixState);
        log(j);
        if (j.spectrum?.bins) drawVocalSpectrum(document.getElementById("fm-spectrum"), j.spectrum.bins);
      });
    });
  }

  function bindActions() {
    document.getElementById("fm-arm-dishes")?.addEventListener("click", async () => {
      log(await dispatch("arm", { mode: "dishes" }));
      await refresh();
    });
    document.getElementById("fm-arm-war")?.addEventListener("click", async () => {
      log(await dispatch("arm", { mode: "war" }));
      await refresh();
    });
    document.getElementById("fm-speak-text")?.addEventListener("input", () => {
      renderThoughtUtterance();
    });
    document.getElementById("fm-prepare")?.addEventListener("click", () => renderThoughtUtterance());
    document.getElementById("fm-speak")?.addEventListener("click", async () => {
      const text = (document.getElementById("fm-speak-text")?.value || "").trim()
        || "Field voice online. Mouth owns the sound.";
      const prep = await dispatch("prepare_utterance", { thought: text, text });
      const utterance = prep.utterance || text;
      const j = await dispatch("speak", { text: utterance, engine: "doctrine" });
      log({ prepare: prep, speak: j });
      renderThoughtUtterance();
      browserSpeak(j.text || utterance, fixState.rate_wpm, fixState.pitch_semitones);
    });
    document.getElementById("fm-fusion")?.addEventListener("click", async () => {
      const j = await dispatch("fusion", {
        evidence: { mouth_correlation: 0.88, ear_correlation: 0.85, eye_correlation: 0.84 },
      });
      log(j);
      renderFusion(j.fusion_score);
    });
    document.getElementById("fm-verify")?.addEventListener("click", async () => log(await dispatch("verify")));
    document.getElementById("fm-refresh")?.addEventListener("click", () => refresh());
  }

  async function refresh() {
    try {
      const r = await fetch(API);
      const j = await r.json();
      renderStatus(j);
      const spec = await dispatch("spectrum");
      if (spec.bins) drawVocalSpectrum(document.getElementById("fm-spectrum"), spec.bins);
      global.SenseTrainingWire?.initForPanel?.("final-mouth");
      renderThoughtUtterance();
    } catch (e) {
      log("Mouth refresh failed: " + e.message);
    }
  }

  function init() {
    bindActions();
    bindFixSliders();
    const canvas = document.getElementById("fm-spectrum");
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

  global.FinalMouthTab = { init, refresh, renderStatus };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);