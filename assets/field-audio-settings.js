(function () {
  "use strict";

  let doc = null;
  let testing = false;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function toast(msg, kind) {
    const el = $("fa-toast");
    if (!el) return;
    el.className = "fa-toast" + (kind ? " fa-toast-" + kind : "");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () {
      el.hidden = true;
    }, 5200);
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

  function findCard(id) {
    const cards = (doc && doc.soundcards && doc.soundcards.cards) || [];
    return cards.find(function (c) {
      return c.id === id;
    });
  }

  function activeCardDetail() {
    if (doc && doc.active_soundcard) return doc.active_soundcard;
    const s = (doc && doc.settings) || {};
    return findCard(s.soundcard_id || "host-live");
  }

  function renderRail(data) {
    const rail = $("fa-rail");
    if (!rail) return;
    const b = data.backend || {};
    const v = data.vintage || {};
    const hdmi = data.hdmi || {};
    const tags = [];
    if (b.pipewire) tags.push("PipeWire");
    else if (b.pulse_compat) tags.push("PulseAudio");
    if (b.alsa_available) tags.push("ALSA");
    if (v.gstreamer) tags.push("GStreamer");
    if (v.ffmpeg) tags.push("FFmpeg");
    const active = data.active_soundcard || {};
    const prof = active.profile || {};
    const sinkDummy = /null|dummy/i.test(String(data.default_sink || ""));
    rail.innerHTML =
      "<h3>Backend</h3>" +
      tags
        .map(function (t) {
          return '<span class="fa-tag">' + esc(t) + "</span> ";
        })
        .join("") +
      "<p>" +
      esc(b.server_name || "audio") +
      "</p>" +
      "<h3>Output</h3>" +
      '<p class="fa-rail-sink' +
      (sinkDummy ? " fa-warn" : "") +
      '">' +
      esc(data.default_sink || "—") +
      "</p>" +
      (sinkDummy ? '<p class="fa-warn">Dummy sink — use Bind HDMI</p>' : "") +
      "<h3>Active card</h3>" +
      "<p><strong>" +
      esc(active.name || v.active?.card_id || "—") +
      "</strong></p>" +
      (prof.sample_rate
        ? "<p>" +
          esc(prof.sample_rate + " Hz · " + prof.channels + "ch · " + prof.bits + "-bit") +
          "</p>"
        : "") +
      "<h3>Catalog</h3>" +
      "<p>" +
      esc(String(v.card_count || (data.soundcards && data.soundcards.card_count) || 0)) +
      " cards · any format</p>" +
      (hdmi.default_is_dummy
        ? '<button type="button" class="fa-apply fa-apply-sm" id="fa-bind-hdmi">Bind HDMI</button>'
        : "");
    const bindBtn = $("fa-bind-hdmi");
    if (bindBtn) {
      bindBtn.onclick = function () {
        bindHdmi();
      };
    }
  }

  function cardOptionsHtml(cards, selected, filter) {
    const q = (filter || "").toLowerCase();
    const groups = (doc && doc.vintage && doc.vintage.groups) || [];
    if (groups.length) {
      return groups
        .map(function (g) {
          const opts = (g.cards || [])
            .filter(function (c) {
              if (!q) return true;
              return (
                String(c.name || "")
                  .toLowerCase()
                  .includes(q) ||
                String(c.id || "")
                  .toLowerCase()
                  .includes(q)
              );
            })
            .map(function (c) {
              return (
                '<option value="' +
                esc(c.id) +
                '"' +
                (c.id === selected ? " selected" : "") +
                ">" +
                esc(c.name) +
                (c.era ? " · " + esc(c.era) : "") +
                "</option>"
              );
            })
            .join("");
          if (!opts) return "";
          return '<optgroup label="' + esc(g.vendor) + '">' + opts + "</optgroup>";
        })
        .join("");
    }
    return (cards || [])
      .filter(function (c) {
        if (!q) return true;
        return String(c.name || "")
          .toLowerCase()
          .includes(q);
      })
      .map(function (c) {
        return (
          '<option value="' +
          esc(c.id) +
          '"' +
          (c.id === selected ? " selected" : "") +
          ">" +
          esc(c.name) +
          "</option>"
        );
      })
      .join("");
  }

  function renderCardDetail(card) {
    const el = $("fa-card-detail");
    if (!el) return;
    if (!card) {
      el.innerHTML = "<p class='fa-dim'>Select a soundcard</p>";
      return;
    }
    const prof = card.profile || {};
    const chips = (card.chips || []).join(", ") || "—";
    const systems = (card.systems || []).join(", ") || "—";
    const formats = ((doc.vintage && doc.vintage.playback && doc.vintage.playback.formats_in) || [])
      .slice(0, 8)
      .join(", ");
    el.innerHTML =
      '<div class="fa-detail-grid">' +
      '<div><span class="fa-k">Era</span><span>' +
      esc(card.era || "—") +
      "</span></div>" +
      '<div><span class="fa-k">Bus</span><span>' +
      esc(card.bus || prof.bus || "—") +
      "</span></div>" +
      '<div><span class="fa-k">Family</span><span>' +
      esc(card.family || card.emulation || "—") +
      "</span></div>" +
      '<div><span class="fa-k">Profile</span><span>' +
      esc(
        prof.sample_rate
          ? prof.sample_rate + " Hz · " + prof.channels + "ch · " + prof.bits + "b"
          : "live"
      ) +
      "</span></div>" +
      '<div class="fa-detail-wide"><span class="fa-k">CHIPS</span><span>' +
      esc(chips) +
      "</span></div>" +
      '<div class="fa-detail-wide"><span class="fa-k">Systems</span><span>' +
      esc(systems) +
      "</span></div>" +
      (formats
        ? '<div class="fa-detail-wide"><span class="fa-k">Formats</span><span>' +
          esc(formats + "…") +
          "</span></div>"
        : "") +
      "</div>";
  }

  function renderSoundcards(data) {
    const el = $("fa-soundcards");
    if (!el) return;
    const s = data.settings || {};
    const cards = (data.soundcards && data.soundcards.cards) || [];
    const sel = s.soundcard_id || (data.vintage && data.vintage.active && data.vintage.active.card_id) || "nvidia-hdmi-pro";
    const card = data.active_soundcard || findCard(sel) || cards[0];
    const quick = [
      "adlib-original",
      "sb16",
      "sb-awe64-gold",
      "covox-speech-thing",
      "ess-solo1",
      "tb-santa-cruz",
      "gus-classic",
      "nvidia-hdmi-pro",
    ];
    el.innerHTML =
      '<div class="fa-card fa-card-wide"><h3>Soundcard laboratory · CHIPS composite</h3>' +
      '<p class="fa-hint">Every vintage card plays any format (MP4, MP3, WAV, …) resampled to its native profile, routed to your live HDMI sink.</p>' +
      '<div class="fa-field"><label for="fa-card-search">Search</label>' +
      '<input class="fa-input" id="fa-card-search" placeholder="SB16, Turtle Beach, AdLib, ESS…" /></div>' +
      '<div class="fa-field"><label for="fa-card">Select card</label>' +
      '<select class="fa-select" id="fa-card" size="1">' +
      cardOptionsHtml(cards, sel, "") +
      "</select></div>" +
      '<div id="fa-card-detail" class="fa-card-detail"></div>' +
      '<div class="fa-btn-row">' +
      '<button type="button" class="fa-apply" id="fa-card-activate">Activate card</button>' +
      '<button type="button" class="fa-apply fa-apply-tune" id="fa-card-test">♪ Play test tune</button>' +
      "</div>" +
      '<div class="fa-quick-row"><span class="fa-k">Quick test</span>' +
      quick
        .map(function (id) {
          const c = findCard(id);
          const label = c ? c.name : id;
          return (
            '<button type="button" class="fa-chip-btn" data-card="' +
            esc(id) +
            '" title="Test ' +
            esc(label) +
            '">' +
            esc(label.split(" ").slice(0, 2).join(" ")) +
            "</button>"
          );
        })
        .join("") +
      "</div></div>";
    renderCardDetail(card);

    const cardSel = $("fa-card");
    const search = $("fa-card-search");
    function syncSelect() {
      const picked = findCard(cardSel.value);
      renderCardDetail(picked);
    }
    if (search && cardSel) {
      search.oninput = function () {
        const cur = cardSel.value;
        cardSel.innerHTML = cardOptionsHtml(cards, cur, search.value);
        if (![...cardSel.options].some(function (o) { return o.value === cur; }) && cardSel.options.length) {
          cardSel.selectedIndex = 0;
        }
        syncSelect();
      };
    }
    if (cardSel) {
      cardSel.onchange = syncSelect;
    }
    const activate = $("fa-card-activate");
    if (activate) {
      activate.onclick = function () {
        const id = cardSel.value;
        applySettings({ soundcard_id: id, action: "select_card" }, "Activated " + (findCard(id)?.name || id));
      };
    }
    const testBtn = $("fa-card-test");
    if (testBtn) {
      testBtn.onclick = function () {
        playTestTune(cardSel.value);
      };
    }
    el.querySelectorAll("[data-card]").forEach(function (btn) {
      btn.onclick = function () {
        const id = btn.dataset.card;
        if (cardSel) cardSel.value = id;
        syncSelect();
        playTestTune(id);
      };
    });
  }

  function renderFormats(data) {
    const el = $("fa-formats");
    if (!el) return;
    const profiles = (data.dac_chamber && data.dac_chamber.format_profiles) || [];
    const cur = (data.settings || {}).format_profile || "surround_8ch";
    el.innerHTML =
      '<div class="fa-card"><h3>Output format profile</h3><div class="fa-format-row">' +
      profiles
        .map(function (p) {
          const on = p.id === cur ? " fa-format-on" : "";
          return (
            '<button type="button" class="fa-format-btn' +
            on +
            '" data-prof="' +
            esc(p.id) +
            '">' +
            esc(p.label) +
            "<small>" +
            esc((p.channels || 2) + "ch") +
            "</small></button>"
          );
        })
        .join("") +
      "</div></div>";
    el.querySelectorAll("[data-prof]").forEach(function (btn) {
      btn.onclick = function () {
        applySettings({ format_profile: btn.dataset.prof });
      };
    });
  }

  function renderSpeakerTest(data) {
    const el = $("fa-speaker-test");
    if (!el) return;
    const chans = ["FL", "FR", "FC", "LFE", "BL", "BR", "SL", "SR"];
    el.innerHTML =
      '<div class="fa-card"><h3>Speaker channel ping</h3><div class="fa-spk-grid">' +
      chans
        .map(function (ch) {
          return '<button type="button" class="fa-apply fa-apply-sm" data-spk="' + ch + '">' + ch + "</button>";
        })
        .join("") +
      "</div></div>";
    el.querySelectorAll("[data-spk]").forEach(function (btn) {
      btn.onclick = function () {
        fetch("/api/field-audio-dac", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "test_tone", channel: btn.dataset.spk }),
        }).catch(function () {});
        toast("Ping " + btn.dataset.spk, "info");
      };
    });
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
      '<div class="fa-card fa-card-actions">' +
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
    if (sinkMute) sinkMute.onclick = function () { sinkMute.classList.toggle("on"); };
    if (srcMute) srcMute.onclick = function () { srcMute.classList.toggle("on"); };
    const apply = $("fa-apply");
    if (apply) apply.onclick = function () { applySettings(collectPatch()); };
  }

  function renderAdvanced(data) {
    const panel = $("fa-advanced-panel");
    if (!panel) return;
    panel.hidden = true;
  }

  function collectPatch(includeAdvanced) {
    const patch = {
      default_sink: ($("fa-sink") || {}).value,
      default_source: ($("fa-source") || {}).value,
      sink_volume: (($("fa-sink-vol") || {}).value || 100) / 100,
      source_volume: (($("fa-src-vol") || {}).value || 100) / 100,
      sink_muted: ($("fa-sink-mute") || {}).classList.contains("on"),
      source_muted: ($("fa-src-mute") || {}).classList.contains("on"),
      soundcard_id: ($("fa-card") || {}).value,
      advanced: false,
    };
    return patch;
  }

  function render(data) {
    doc = data;
    renderRail(data);
    renderSoundcards(data);
    renderFormats(data);
    renderDevices(data);
    renderVolume(data);
    renderSpeakerTest(data);
    renderAdvanced(data);
    const sub = $("fa-subtitle");
    if (sub) {
      const ac = data.active_soundcard || {};
      sub.textContent =
        (ac.name || "Audio") +
        " · " +
        (data.sinks?.length || 0) +
        " sinks · " +
        (data.vintage?.card_count || 0) +
        " vintage cards";
    }
  }

  async function applySettings(patch, okMsg) {
    try {
      const out = await api("/api/field-audio-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      render(out);
      if (okMsg) toast(okMsg, "ok");
      else if (out.ok !== false) toast("Settings applied", "ok");
      else toast(out.error || "Apply failed", "err");
    } catch (e) {
      toast("Settings request failed", "err");
      console.error(e);
    }
  }

  async function playTestTune(cardId) {
    if (testing) {
      toast("Already playing…", "info");
      return;
    }
    testing = true;
    const btn = $("fa-card-test");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "♪ Playing…";
    }
    const name = (findCard(cardId) || {}).name || cardId;
    toast("Test tune on " + name + "…", "info");
    try {
      const out = await api("/api/field-audio-settings/test-tune", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId, soundcard_id: cardId }),
      });
      if (out.refresh_recommended) await refresh();
      else render(out);
      const tr = out.test_result || {};
      if (out.ok && tr.ok !== false) {
        toast("♪ " + name + " — tune complete", "ok");
      } else {
        toast(tr.error || out.error || out.message || "Playback failed", "err");
      }
    } catch (e) {
      toast("Test tune failed", "err");
      console.error(e);
    } finally {
      testing = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = "♪ Play test tune";
      }
    }
  }

  async function bindHdmi() {
    toast("Binding HDMI…", "info");
    try {
      const out = await api("/api/field-audio-settings/bind-hdmi", { method: "POST" });
      render(out);
      if (out.ok) toast("HDMI audio bound", "ok");
      else toast(out.error || "HDMI bind failed", "err");
    } catch (e) {
      toast("HDMI bind failed", "err");
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