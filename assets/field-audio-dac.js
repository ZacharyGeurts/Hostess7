(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let state = { doc: null, vuAnim: null };

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  async function dac(action, body) {
    return api("/api/field-audio-dac", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({ action: action }, body || {})),
    });
  }

  function optList(items, selected) {
    return (items || [])
      .map((it) => {
        const val = it.name || it.id || it;
        return `<option value="${esc(val)}"${val === selected ? " selected" : ""}>${esc(it.description || it.label || val)}</option>`;
      })
      .join("");
  }

  function renderRail(doc) {
    const el = $("dac-rail");
    if (!el) return;
    const b = doc.backend || {};
    const tags = [];
    if (b.pipewire) tags.push("PipeWire");
    else if (b.pulse_compat) tags.push("Pulse");
    if (b.alsa_available) tags.push("ALSA");
    if (b.jack) tags.push("JACK");
    if ((b.sdl3_mixer || {}).available) tags.push("SDL3 Mixer");
    const zn = (doc.znetwork_hook || {}).layer || "audio_layer";
    el.innerHTML =
      "<h3>Layer</h3><p>ZNetwork · " + esc(zn) + "</p>" +
      "<h3>Backend</h3>" + tags.map((t) => '<span class="dac-tag">' + esc(t) + "</span>").join("") +
      "<p>" + esc(b.server_name || b.name || "") + "</p>" +
      "<h3>Profile</h3><p>" + esc((doc.active_profile || {}).label || "Stereo") + "</p>" +
      "<h3>Emu</h3><p>" + esc((doc.emulation || {}).emulation || "off") + "</p>";
  }

  function renderLayout(doc) {
    const el = $("dac-layout");
    if (!el) return;
    const layout = (doc.active_profile || {}).layout || ["FL", "FR"];
    el.innerHTML = layout.map((ch) => '<span class="dac-ch">' + esc(ch) + "</span>").join("");
  }

  function drawVu(levels) {
    const canvas = $("dac-vu-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const n = Math.max(2, (levels || []).length);
    const gap = 6;
    const barW = (w - gap * (n + 1)) / n;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < n; i++) {
      const lv = levels[i] != null ? levels[i] : 0.05;
      const x = gap + i * (barW + gap);
      const bh = Math.max(4, lv * (h - 24));
      const y = h - 12 - bh;
      const grad = ctx.createLinearGradient(x, y, x, h - 12);
      grad.addColorStop(0, "#34d399");
      grad.addColorStop(0.65, "#10b981");
      grad.addColorStop(1, "#064e3b");
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.fillRect(x, 12, barW, h - 24);
      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barW, bh);
      if (lv > 0.85) {
        ctx.fillStyle = "#f472b6";
        ctx.fillRect(x, 12, barW, 4);
      }
    }
  }

  function startVuLoop(doc) {
    if (state.vuAnim) cancelAnimationFrame(state.vuAnim);
    const base = (doc.vu || {}).levels || [0.1, 0.15];
    let t = 0;
    function tick() {
      t += 0.08;
      const wobble = base.map((v, i) => Math.min(1, Math.max(0.02, v + Math.sin(t + i * 0.7) * 0.12)));
      drawVu(wobble);
      state.vuAnim = requestAnimationFrame(tick);
    }
    tick();
  }

  function renderDevices(doc) {
    const el = $("dac-devices");
    if (!el) return;
    const d = doc.devices || {};
    const s = doc.settings || {};
    el.innerHTML =
      '<div class="dac-card"><h3>Microphone / input</h3>' +
      '<div class="dac-field"><label>Source</label><select class="dac-select" id="dac-in">' +
      optList(d.sources, s.input_device) + "</select></div></div>" +
      '<div class="dac-card"><h3>Speakers / output</h3>' +
      '<div class="dac-field"><label>Sink</label><select class="dac-select" id="dac-out">' +
      optList(d.sinks, s.output_device) + "</select></div></div>" +
      '<div class="dac-card"><h3>Monitor tap</h3>' +
      '<div class="dac-field"><label>Monitor</label><select class="dac-select" id="dac-mon">' +
      '<option value="">— none —</option>' + optList(d.monitors, s.monitor_device) + "</select></div></div>" +
      '<div class="dac-card"><h3>Loopback</h3>' +
      '<div class="dac-field"><label>Loopback</label><select class="dac-select" id="dac-loop">' +
      '<option value="">— none —</option>' + optList(d.loopbacks, s.loopback_device) + "</select></div></div>";
  }

  function renderGain(doc) {
    const el = $("dac-gain");
    if (!el) return;
    const s = doc.settings || {};
    const inDb = s.input_gain_db ?? 0;
    const outDb = s.output_gain_db ?? 0;
    el.innerHTML =
      '<div class="dac-card"><h3>Input gain</h3>' +
      '<div class="dac-row"><span class="dac-db" id="dac-in-db">' + inDb + " dB</span></div>" +
      '<input type="range" class="dac-range" id="dac-in-gain" min="-24" max="12" step="0.5" value="' + inDb + '" />' +
      '<label class="dac-check"><input type="checkbox" id="dac-in-mute"' + (s.input_muted ? " checked" : "") + " /> Mute input</label></div>" +
      '<div class="dac-card"><h3>Output gain</h3>' +
      '<div class="dac-row"><span class="dac-db" id="dac-out-db">' + outDb + " dB</span></div>" +
      '<input type="range" class="dac-range" id="dac-out-gain" min="-24" max="6" step="0.5" value="' + outDb + '" />' +
      '<label class="dac-check"><input type="checkbox" id="dac-out-mute"' + (s.output_muted ? " checked" : "") + " /> Mute output</label></div>" +
      '<div class="dac-card"><h3>Chain</h3>' +
      '<label class="dac-check"><input type="checkbox" id="dac-echo"' + (s.echo_cancel ? " checked" : "") + " /> Echo cancel</label>" +
      '<label class="dac-check"><input type="checkbox" id="dac-gate"' + (s.noise_gate ? " checked" : "") + " /> Noise gate</label>" +
      '<label class="dac-check"><input type="checkbox" id="dac-static"' + (s.static_filter ? " checked" : "") + " /> Static filter</label>" +
      '<label class="dac-check"><input type="checkbox" id="dac-emu"' + (s.emulation_enabled !== false ? " checked" : "") + " /> Format emulation</label></div>";

    const inGain = $("dac-in-gain");
    const outGain = $("dac-out-gain");
    if (inGain) inGain.oninput = () => { const p = $("dac-in-db"); if (p) p.textContent = inGain.value + " dB"; };
    if (outGain) outGain.oninput = () => { const p = $("dac-out-db"); if (p) p.textContent = outGain.value + " dB"; };
  }

  function renderFormats(doc) {
    const el = $("dac-formats");
    if (!el) return;
    const cur = (doc.settings || {}).format_profile || "stereo";
    const profiles = doc.format_profiles || [];
    el.innerHTML =
      "<h2>Format &amp; layout</h2>" +
      '<div class="dac-format-grid">' +
      profiles
        .map(
          (p) =>
            '<button type="button" class="dac-format' + (p.id === cur ? " active" : "") + '" data-profile="' + esc(p.id) + '">' +
            "<strong>" + esc(p.label) + "</strong><span>" + esc((p.channels || 2) + " ch") +
            (p.emulation ? " · emu" : "") + "</span></button>"
        )
        .join("") +
      "</div>" +
      '<p class="dac-toggle-hard" id="dac-hard-toggle">Hard settings ▾</p>';

    el.querySelectorAll(".dac-format").forEach((btn) => {
      btn.addEventListener("click", () => {
        dac("set_profile", { format_profile: btn.dataset.profile }).then(refresh);
      });
    });
    const toggle = $("dac-hard-toggle");
    if (toggle) {
      toggle.onclick = () => {
        const panel = $("dac-hard");
        if (panel) {
          panel.hidden = !panel.hidden;
          toggle.textContent = panel.hidden ? "Hard settings ▾" : "Hard settings ▴";
        }
      };
    }
    renderHard(doc);
  }

  function renderHard(doc) {
    const grid = $("dac-hard-grid");
    const panel = $("dac-hard");
    if (!grid || !panel) return;
    const s = doc.settings || {};
    grid.innerHTML =
      '<div class="dac-card"><div class="dac-field"><label>Sample rate</label><input class="dac-input" type="number" id="dac-rate" value="' + (s.sample_rate || 48000) + '" /></div>' +
      '<div class="dac-field"><label>Buffer frames</label><input class="dac-input" type="number" id="dac-buf" value="' + (s.buffer_frames || 1024) + '" /></div>' +
      '<div class="dac-field"><label>Latency ms</label><input class="dac-input" type="number" id="dac-lat" value="' + (s.latency_ms || 20) + '" /></div></div>' +
      '<div class="dac-card"><div class="dac-field"><label>Resample</label><input class="dac-input" id="dac-resample" value="' + esc(s.resample_method || "speex-float-10") + '" /></div>' +
      '<div class="dac-field"><label>Channel map</label><input class="dac-input" id="dac-chmap" value="' + esc(s.channel_map || "default") + '" /></div>' +
      '<div class="dac-field"><label>PipeWire quantum</label><input class="dac-input" type="number" id="dac-pw-q" value="' + (s.pipewire_quantum || 1024) + '" /></div></div>';
    panel.hidden = !s.hard_mode;
  }

  function collectPatch() {
    return {
      input_device: ($("dac-in") || {}).value,
      output_device: ($("dac-out") || {}).value,
      monitor_device: ($("dac-mon") || {}).value,
      loopback_device: ($("dac-loop") || {}).value,
      input_gain_db: parseFloat(($("dac-in-gain") || {}).value) || 0,
      output_gain_db: parseFloat(($("dac-out-gain") || {}).value) || 0,
      input_muted: ($("dac-in-mute") || {}).checked,
      output_muted: ($("dac-out-mute") || {}).checked,
      echo_cancel: ($("dac-echo") || {}).checked,
      noise_gate: ($("dac-gate") || {}).checked,
      static_filter: ($("dac-static") || {}).checked,
      emulation_enabled: ($("dac-emu") || {}).checked,
      sample_rate: parseInt(($("dac-rate") || {}).value, 10) || 48000,
      buffer_frames: parseInt(($("dac-buf") || {}).value, 10) || 1024,
      latency_ms: parseInt(($("dac-lat") || {}).value, 10) || 20,
      resample_method: ($("dac-resample") || {}).value,
      channel_map: ($("dac-chmap") || {}).value,
      pipewire_quantum: parseInt(($("dac-pw-q") || {}).value, 10) || 1024,
    };
  }

  function render(doc) {
    state.doc = doc;
    renderRail(doc);
    renderLayout(doc);
    renderDevices(doc);
    renderGain(doc);
    renderFormats(doc);
    startVuLoop(doc);
    const foot = $("dac-foot");
    if (foot) foot.textContent = doc.posture || "DAC ready";
    const sub = $("dac-sub");
    if (sub) sub.textContent = (doc.backend || {}).name + " · " + ((doc.active_profile || {}).label || "Stereo");
  }

  async function refresh() {
    try {
      render(await api("/api/field-audio-dac"));
    } catch (e) {
      const foot = $("dac-foot");
      if (foot) foot.textContent = "Load failed: " + e.message;
    }
  }

  function bindControls() {
    $("dac-apply")?.addEventListener("click", () => dac("apply", collectPatch()).then(refresh));
    $("dac-bind")?.addEventListener("click", () =>
      api("/api/field-audio-secure-bind/auto", { method: "POST", body: "{}" }).then(refresh)
    );
  }

  bindControls();
  refresh();
  setInterval(() => {
    dac("vu", { channels: (state.doc?.active_profile?.channels) || 8 })
      .then((r) => { if (r.levels) drawVu(r.levels); })
      .catch(() => {});
  }, 800);
})();