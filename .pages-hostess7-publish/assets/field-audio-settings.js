(function () {
  "use strict";

  let doc = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function optionList(items, selected, key) {
    return (items || [])
      .map(function (it) {
        const val = it.name || it.id || it;
        const sel = val === selected ? " selected" : "";
        return (
          '<option value="' +
          esc(val) +
          '"' +
          sel +
          ">" +
          esc(it.description || it.title || val) +
          "</option>"
        );
      })
      .join("");
  }

  function renderRail(data) {
    const rail = $("fa-rail");
    if (!rail) return;
    const b = data.backend || {};
    const tags = [];
    if (b.pipewire) tags.push("PipeWire");
    else if (b.pulse_compat) tags.push("PulseAudio");
    if (b.alsa_available) tags.push("ALSA");
    if (b.jack) tags.push("JACK");
    rail.innerHTML =
      "<h3>Backend</h3>" +
      tags.map(function (t) {
        return '<span class="fa-tag">' + esc(t) + "</span> ";
      }).join("") +
      '<p>Server: ' +
      esc(b.server_name) +
      "</p>" +
      "<h3>Defaults</h3>" +
      "<p>Sink: " +
      esc(data.default_sink) +
      "</p>" +
      "<p>Source: " +
      esc(data.default_source) +
      "</p>";
  }

  function renderDevices(data) {
    const el = $("fa-devices");
    if (!el) return;
    const s = data.settings || {};
    el.innerHTML =
      '<div class="fa-card"><h3>Output (sink)</h3>' +
      '<div class="fa-field"><label for="fa-sink">Device</label>' +
      '<select class="fa-select" id="fa-sink">' +
      optionList(data.sinks, s.default_sink || data.default_sink) +
      "</select></div></div>" +
      '<div class="fa-card"><h3>Input (source)</h3>' +
      '<div class="fa-field"><label for="fa-source">Device</label>' +
      '<select class="fa-select" id="fa-source">' +
      optionList(data.sources, s.default_source || data.default_source) +
      "</select></div></div>";
  }

  function renderVolume(data) {
    const el = $("fa-volume");
    if (!el) return;
    const v = data.volume || {};
    const s = data.settings || {};
    const sinkPct = v.sink_percent != null ? v.sink_percent : Math.round((s.sink_volume || 1) * 100);
    const srcPct = v.source_percent != null ? v.source_percent : Math.round((s.source_volume || 1) * 100);
    el.innerHTML =
      '<div class="fa-card"><h3>Output volume</h3>' +
      '<div class="fa-row"><span id="fa-sink-pct">' +
      sinkPct +
      '%</span><button type="button" class="fa-mute' +
      (v.sink_muted ? " on" : "") +
      '" id="fa-sink-mute">Mute</button></div>' +
      '<input type="range" class="fa-range" id="fa-sink-vol" min="0" max="100" value="' +
      sinkPct +
      '" /></div>' +
      '<div class="fa-card"><h3>Input volume</h3>' +
      '<div class="fa-row"><span id="fa-src-pct">' +
      srcPct +
      '%</span><button type="button" class="fa-mute' +
      (v.source_muted ? " on" : "") +
      '" id="fa-src-mute">Mute</button></div>' +
      '<input type="range" class="fa-range" id="fa-src-vol" min="0" max="100" value="' +
      srcPct +
      '" /></div>' +
      '<div class="fa-card" style="display:flex;align-items:flex-end">' +
      '<button type="button" class="fa-apply" id="fa-apply">Apply routing</button></div>';

    const sinkVol = $("fa-sink-vol");
    const srcVol = $("fa-src-vol");
    if (sinkVol) {
      sinkVol.oninput = function () {
        const p = $("fa-sink-pct");
        if (p) p.textContent = sinkVol.value + "%";
      };
    }
    if (srcVol) {
      srcVol.oninput = function () {
        const p = $("fa-src-pct");
        if (p) p.textContent = srcVol.value + "%";
      };
    }
    const sinkMute = $("fa-sink-mute");
    const srcMute = $("fa-src-mute");
    if (sinkMute) {
      sinkMute.onclick = function () {
        sinkMute.classList.toggle("on");
      };
    }
    if (srcMute) {
      srcMute.onclick = function () {
        srcMute.classList.toggle("on");
      };
    }
    const apply = $("fa-apply");
    if (apply) {
      apply.onclick = function () {
        applySettings(collectPatch());
      };
    }
  }

  function renderAdvanced(data) {
    const panel = $("fa-advanced-panel");
    if (!panel) return;
    const adv = data.advanced || {};
    const s = data.settings || {};
    const show = !!s.advanced;
    panel.hidden = !show;
    if (!show) return;

    const methods = (adv.resample_methods || []).map(function (m) {
      const sel = m === adv.resample_method ? " selected" : "";
      return '<option value="' + esc(m) + '"' + sel + ">" + esc(m) + "</option>";
    }).join("");

    const cards = (adv.alsa_cards || data.alsa_cards || []).map(function (c) {
      const sel = String(c.id) === String(adv.alsa_card) ? " selected" : "";
      return '<option value="' + esc(c.id) + '"' + sel + ">" + esc(c.description) + "</option>";
    }).join("");

    panel.innerHTML =
      '<div class="fa-grid">' +
      '<div class="fa-card"><h3>Latency &amp; buffers</h3>' +
      '<div class="fa-field"><label>Latency (ms)</label><input class="fa-input" type="number" id="fa-latency" value="' +
      esc(adv.latency_ms) +
      '" /></div>' +
      '<div class="fa-field"><label>Buffer size</label><input class="fa-input" type="number" id="fa-buffer" value="' +
      esc(adv.buffer_size) +
      '" /></div>' +
      '<div class="fa-field"><label>Periods</label><input class="fa-input" type="number" id="fa-periods" value="' +
      esc(adv.periods) +
      '" /></div></div>' +
      '<div class="fa-card"><h3>Sample rate &amp; resample</h3>' +
      '<div class="fa-field"><label>Sample rate (Hz)</label><input class="fa-input" type="number" id="fa-rate" value="' +
      esc(adv.sample_rate) +
      '" /></div>' +
      '<div class="fa-field"><label>Resample method</label><select class="fa-select" id="fa-resample">' +
      methods +
      "</select></div>" +
      '<div class="fa-field"><label>Channel map</label><input class="fa-input" id="fa-chmap" value="' +
      esc(adv.channel_map) +
      '" /></div></div>' +
      '<div class="fa-card"><h3>PipeWire / ALSA</h3>' +
      '<div class="fa-field"><label>PipeWire quantum</label><input class="fa-input" type="number" id="fa-pw-q" value="' +
      esc(adv.pipewire_quantum) +
      '" /></div>' +
      '<div class="fa-field"><label>PipeWire rate</label><input class="fa-input" type="number" id="fa-pw-rate" value="' +
      esc(adv.pipewire_rate) +
      '" /></div>' +
      '<div class="fa-field"><label>ALSA card</label><select class="fa-select" id="fa-alsa">' +
      cards +
      "</select></div>" +
      "<p style='font-size:11px;color:var(--fa-dim)'>Config hint: " +
      esc(adv.pipewire_config_hint) +
      "</p></div>" +
      '<div class="fa-card"><h3>Processing &amp; network</h3>' +
      '<label class="fa-check"><input type="checkbox" id="fa-echo"' +
      (adv.echo_cancel ? " checked" : "") +
      " /> Echo cancellation</label>" +
      '<label class="fa-check"><input type="checkbox" id="fa-noise"' +
      (adv.noise_suppression ? " checked" : "") +
      " /> Noise suppression</label>" +
      '<label class="fa-check"><input type="checkbox" id="fa-agc"' +
      (adv.agc ? " checked" : "") +
      " /> Automatic gain</label>" +
      '<label class="fa-check"><input type="checkbox" id="fa-jack"' +
      (adv.jack_bridge ? " checked" : "") +
      " /> JACK bridge</label>" +
      '<label class="fa-check"><input type="checkbox" id="fa-flat"' +
      (adv.flat_volumes ? " checked" : "") +
      " /> Flat volumes</label>" +
      '<label class="fa-check"><input type="checkbox" id="fa-net"' +
      (adv.network_audio ? " checked" : "") +
      " /> Network audio</label>" +
      '<div class="fa-field"><label>RTP latency (ms)</label><input class="fa-input" type="number" id="fa-rtp" value="' +
      esc(adv.rtp_latency) +
      '" /></div>' +
      '<button type="button" class="fa-apply" id="fa-apply-adv">Apply advanced</button></div></div>';
    const applyAdv = $("fa-apply-adv");
    if (applyAdv) {
      applyAdv.onclick = function () {
        applySettings(collectPatch(true));
      };
    }
  }

  function collectPatch(includeAdvanced) {
    const patch = {
      default_sink: ($("fa-sink") || {}).value,
      default_source: ($("fa-source") || {}).value,
      sink_volume: (($("fa-sink-vol") || {}).value || 100) / 100,
      source_volume: (($("fa-src-vol") || {}).value || 100) / 100,
      sink_muted: ($("fa-sink-mute") || {}).classList.contains("on"),
      source_muted: ($("fa-src-mute") || {}).classList.contains("on"),
      advanced: ($("fa-advanced") || {}).checked,
    };
    if (includeAdvanced) {
      Object.assign(patch, {
        latency_ms: parseInt(($("fa-latency") || {}).value, 10) || 0,
        buffer_size: parseInt(($("fa-buffer") || {}).value, 10) || 1024,
        periods: parseInt(($("fa-periods") || {}).value, 10) || 3,
        sample_rate: parseInt(($("fa-rate") || {}).value, 10) || 48000,
        resample_method: ($("fa-resample") || {}).value,
        channel_map: ($("fa-chmap") || {}).value,
        pipewire_quantum: parseInt(($("fa-pw-q") || {}).value, 10) || 1024,
        pipewire_rate: parseInt(($("fa-pw-rate") || {}).value, 10) || 48000,
        alsa_card: ($("fa-alsa") || {}).value,
        echo_cancel: ($("fa-echo") || {}).checked,
        noise_suppression: ($("fa-noise") || {}).checked,
        agc: ($("fa-agc") || {}).checked,
        jack_bridge: ($("fa-jack") || {}).checked,
        flat_volumes: ($("fa-flat") || {}).checked,
        network_audio: ($("fa-net") || {}).checked,
        rtp_latency: parseInt(($("fa-rtp") || {}).value, 10) || 200,
      });
    }
    return patch;
  }

  function render(data) {
    doc = data;
    renderRail(data);
    renderDevices(data);
    renderVolume(data);
    renderAdvanced(data);
    const sub = $("fa-subtitle");
    if (sub) {
      sub.textContent =
        (data.backend?.server_name || "audio") +
        " · " +
        (data.sinks?.length || 0) +
        " sinks · " +
        (data.sources?.length || 0) +
        " sources";
    }
    const adv = $("fa-advanced");
    if (adv) adv.checked = false;
  }

  async function applySettings(patch) {
    try {
      render(await api("/api/field-audio-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }));
    } catch (e) {
      console.error(e);
    }
  }

  async function refresh() {
    try {
      render(await api("/api/field-audio-settings"));
    } catch (e) {
      const main = $("fa-main");
      if (main) main.innerHTML = "<p>Audio settings load failed.</p>";
    }
  }

  function init() {
    if (globalThis.FieldShellDock) {
      FieldShellDock.init({ activeIcon: "music" });
    }
    refresh();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();