/**
 * Taskbar audio dropdown — all settings, soundcards history, DAC mixer, speaker tests.
 */
(function (global) {
  "use strict";

  const state = { open: false, doc: null, anchor: null, audioCtx: null };

  function api(path, opts) {
    const url = global.H7Api ? global.H7Api(path) : path;
    return fetch(url, Object.assign({ credentials: "same-origin" }, opts || {})).then(function (r) {
      return r.json();
    });
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensurePop() {
    let el = document.getElementById("fsb-audio-pop");
    if (el) return el;
    el = document.createElement("div");
    el.id = "fsb-audio-pop";
    el.className = "fsb-audio-pop";
    el.hidden = true;
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Audio settings");
    document.body.appendChild(el);
    document.addEventListener("click", function (ev) {
      if (!state.open) return;
      const pop = document.getElementById("fsb-audio-pop");
      if (pop && !pop.contains(ev.target) && state.anchor && !state.anchor.contains(ev.target)) {
        close();
      }
    });
    return el;
  }

  function playEmulatedTone(channel) {
    try {
      if (!state.audioCtx) state.audioCtx = new (global.AudioContext || global.webkitAudioContext)();
      const ctx = state.audioCtx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const freqs = { FL: 440, FR: 554, FC: 330, LFE: 80, BL: 392, BR: 494, SL: 370, SR: 587 };
      osc.frequency.value = freqs[channel] || 440;
      osc.type = channel === "LFE" ? "sine" : "triangle";
      gain.gain.value = channel === "LFE" ? 0.35 : 0.12;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.55);
    } catch (_) {}
  }

  function testSpeaker(channel, btn) {
    if (btn) btn.classList.add("testing");
    api("/api/field-audio-dac", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "test_tone", channel: channel }),
    })
      .then(function (res) {
        if (res.emulated || !res.ok) playEmulatedTone(channel);
      })
      .catch(function () {
        playEmulatedTone(channel);
      })
      .finally(function () {
        if (btn) setTimeout(function () { btn.classList.remove("testing"); }, 600);
      });
  }

  function applyPatch(patch) {
    return api("/api/field-audio-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then(function (doc) {
      state.doc = doc.snapshot || doc;
      render();
      return doc;
    });
  }

  function dacAction(action, body) {
    return api("/api/field-audio-dac", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({ action: action }, body || {})),
    });
  }

  function selectedCard() {
    const cards = (state.doc && state.doc.soundcards && state.doc.soundcards.cards) || [];
    const id = (state.doc && state.doc.settings && state.doc.settings.soundcard_id) || "host-live";
    return cards.find(function (c) { return c.id === id; }) || cards[0] || null;
  }

  function render() {
    const pop = ensurePop();
    const d = state.doc || {};
    const s = d.settings || {};
    const profiles = (d.dac_chamber && d.dac_chamber.format_profiles) || [];
    const curProf = s.format_profile || (d.dac_chamber && d.dac_chamber.active_profile && d.dac_chamber.active_profile.id) || "surround_8ch";
    const cards = (d.soundcards && d.soundcards.cards) || [];
    const card = selectedCard();
    const vol = d.volume || {};
    const sinkPct = vol.sink_percent != null ? vol.sink_percent : Math.round((s.sink_volume || 1) * 100);
    const srcPct = vol.source_percent != null ? vol.source_percent : Math.round((s.source_volume || 1) * 100);
    const quality = s.quality || "high";
    const ch = (profiles.find(function (p) { return p.id === curProf; }) || {}).channels || 8;

    const cardOpts = cards
      .map(function (c) {
        const tag = c.live ? " · live" : c.era ? " · " + c.era : "";
        return '<option value="' + esc(c.id) + '"' + (c.id === (s.soundcard_id || "host-live") ? " selected" : "") + ">" + esc(c.name) + esc(tag) + "</option>";
      })
      .join("");

    const fmtBtns = profiles
      .map(function (p) {
        return (
          '<button type="button" class="fsb-audio-fmt' + (p.id === curProf ? " active" : "") + '" data-prof="' + esc(p.id) + '">' +
          "<strong>" + esc(p.label) + "</strong><span>" + esc((p.channels || 2) + " ch") + (p.emulation ? " · emu" : "") + "</span></button>"
        );
      })
      .join("");

    const speakers = ["FL", "FR", "FC", "LFE", "BL", "BR", "SL", "SR"];
    const spkBtns = speakers
      .map(function (chName) {
        const cls = chName === "LFE" ? " fsb-audio-spk--lfe" : "";
        return '<button type="button" class="fsb-audio-spk' + cls + '" data-spk="' + chName + '">' + chName + "</button>";
      })
      .join("");

    pop.innerHTML =
      '<div class="fsb-audio-head">' +
      "<div><h2>Audio</h2><p style='margin:4px 0 0;font-size:11px;color:#9aa8c0'>" +
      esc(d.default_sink || "default sink") + "</p></div>" +
      '<span class="fsb-audio-badge">' + esc(quality) + " · " + ch + "ch</span></div>" +
      '<div class="fsb-audio-section"><h3>Soundcard</h3>' +
      '<select class="fsb-audio-select" id="fsb-audio-card">' + cardOpts + "</select>" +
      (card
        ? '<p class="fsb-audio-chip-note">' +
          esc((card.chips || []).join(", ") || "standard fare") +
          (card.systems && card.systems.length ? " — used in " + esc(card.systems.join(", ")) : "") +
          "</p>"
        : "") +
      "</div>" +
      '<div class="fsb-audio-section"><h3>Output / input</h3>' +
      '<label style="font-size:10px;color:#9aa8c0">Speakers</label>' +
      '<select class="fsb-audio-select" id="fsb-audio-sink" style="margin-bottom:6px">' +
      (d.sinks || []).map(function (x) {
        return '<option value="' + esc(x.name) + '"' + (x.name === (s.default_sink || d.default_sink) ? " selected" : "") + ">" + esc(x.description || x.name) + "</option>";
      }).join("") +
      "</select>" +
      '<label style="font-size:10px;color:#9aa8c0">Microphone</label>' +
      '<select class="fsb-audio-select" id="fsb-audio-source">' +
      (d.sources || []).map(function (x) {
        return '<option value="' + esc(x.name) + '"' + (x.name === (s.default_source || d.default_source) ? " selected" : "") + ">" + esc(x.description || x.name) + "</option>";
      }).join("") +
      "</select></div>" +
      '<div class="fsb-audio-section"><h3>Format &amp; emulation</h3><div class="fsb-audio-formats">' + fmtBtns + "</div></div>" +
      '<div class="fsb-audio-section"><h3>NIC DAC mixer</h3><div class="fsb-audio-mixer">' +
      '<div><label>Output ' + sinkPct + '%</label><input type="range" class="fsb-audio-range" id="fsb-audio-sink-vol" min="0" max="100" value="' + sinkPct + '" /></div>' +
      '<div><label>Input ' + srcPct + '%</label><input type="range" class="fsb-audio-range" id="fsb-audio-src-vol" min="0" max="100" value="' + srcPct + '" /></div></div></div>' +
      '<div class="fsb-audio-section"><h3>Speaker test · Dolby layout</h3><div class="fsb-audio-speakers">' + spkBtns + "</div></div>" +
      '<div class="fsb-audio-foot">' +
      '<button type="button" class="fsb-audio-link" id="fsb-audio-apply">Apply</button>' +
      '<a class="fsb-audio-link" href="/Hostess7/field-audio-dac" target="_blank" rel="noopener">DAC chamber</a>' +
      '<a class="fsb-audio-link" href="/Hostess7/field-audio-settings" target="_blank" rel="noopener">Full settings</a></div>';

    const cardSel = document.getElementById("fsb-audio-card");
    if (cardSel) {
      cardSel.onchange = function () {
        const picked = cards.find(function (c) { return c.id === cardSel.value; });
        const patch = { soundcard_id: cardSel.value };
        if (picked && picked.emulation) patch.format_profile = picked.emulation;
        if (picked && picked.alsa_id != null) patch.alsa_card = picked.alsa_id;
        applyPatch(patch);
        dacAction("set_soundcard", patch);
      };
    }

    pop.querySelectorAll(".fsb-audio-fmt").forEach(function (btn) {
      btn.onclick = function () {
        const prof = btn.dataset.prof;
        applyPatch({ format_profile: prof });
        dacAction("set_profile", { format_profile: prof });
      };
    });

    pop.querySelectorAll(".fsb-audio-spk").forEach(function (btn) {
      btn.onclick = function () {
        testSpeaker(btn.dataset.spk, btn);
      };
    });

    const applyBtn = document.getElementById("fsb-audio-apply");
    if (applyBtn) {
      applyBtn.onclick = function () {
        applyPatch({
          default_sink: (document.getElementById("fsb-audio-sink") || {}).value,
          default_source: (document.getElementById("fsb-audio-source") || {}).value,
          sink_volume: ((document.getElementById("fsb-audio-sink-vol") || {}).value || 100) / 100,
          source_volume: ((document.getElementById("fsb-audio-src-vol") || {}).value || 100) / 100,
          quality: quality,
          format_profile: curProf,
        });
      };
    }
  }

  function position(anchor) {
    const pop = ensurePop();
    const rect = anchor.getBoundingClientRect();
    const h = pop.offsetHeight || 400;
    let top = rect.top - h - 8;
    if (top < 8) top = rect.bottom + 8;
    let left = rect.right - pop.offsetWidth;
    if (left < 8) left = 8;
    pop.style.top = top + "px";
    pop.style.left = left + "px";
  }

  function open(anchor) {
    state.anchor = anchor;
    state.open = true;
    const pop = ensurePop();
    pop.hidden = false;
    api("/api/field-audio-settings")
      .then(function (doc) {
        state.doc = doc.snapshot || doc;
        render();
        position(anchor);
      })
      .catch(function () {
        pop.innerHTML = "<p>Audio settings unavailable.</p>";
        position(anchor);
      });
  }

  function close() {
    state.open = false;
    const pop = document.getElementById("fsb-audio-pop");
    if (pop) pop.hidden = true;
  }

  function toggle(anchor) {
    if (state.open) close();
    else open(anchor);
  }

  global.FieldStartbarAudio = { open: open, close: close, toggle: toggle };
})(typeof window !== "undefined" ? window : globalThis);