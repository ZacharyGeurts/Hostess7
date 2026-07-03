/**
 * Queen Game Room arcade deck — controller setup (leave theater → 25% arcade).
 * Keyboard · mouse · gamepad · hand · stereo · peripherals · TV watch → Hostess 7.
 */
(function (global) {
  "use strict";

  const API = "/api/hostess7/input-training";
  const STEREO_API = "/api/field-stereo-vision";
  const FH_API = "/api/final-hands";
  const LAB_API = "/api/hostess7/lab";
  const BTN_LABELS = [
    "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "Back", "Start", "LS", "RS", "D↑", "D↓", "D←", "D→",
  ];
  const GRIPS = ["open", "power", "precision", "trigger"];

  let lastKeyTs = 0;
  let lastMouseTs = 0;
  let lastMouseX = 0;
  let lastMouseY = 0;
  let panelDoc = null;
  let pollTimer = null;
  let wired = false;
  let voiceRec = null;
  let voiceHolding = false;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;");
  }

  function panelHtml() {
    return (
      '<div class="qcs-root" id="qcs-root">' +
      '<p class="qcs-motto">Arcade deck — left the theater for controller setup</p>' +
      '<div class="qcs-stereo" id="qcs-stereo"></div>' +
      '<div class="qcs-senses" id="qcs-senses"></div>' +
      '<div class="qcs-tv"><label>Webcam at TV</label><div class="qcs-tv-row">' +
      '<select id="qcs-webcam"></select>' +
      '<input type="number" id="qcs-tv-in" placeholder="TV in" min="20" max="120" value="55" title="Diagonal inches" />' +
      '<input type="number" id="qcs-tv-dist" placeholder="Distance m" step="0.1" min="0.5" max="8" title="Calibration distance" />' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-tv-learn">TV learn</button>' +
      "</div></div>" +
      '<div class="qcs-prof" id="qcs-prof"></div>' +
      '<div class="qcs-periph"><label>Peripheral</label><select id="qcs-periph-select"></select></div>' +
      '<div class="qcs-voice">' +
      '<label>Voice games — Final Ear + Mouth</label>' +
      '<div class="qcs-voice-row">' +
      '<select id="qcs-voice-game"><option value="seaman">Seaman (Dreamcast)</option></select>' +
      '<button type="button" class="gr-btn qcs-act qcs-voice-btn" id="qcs-voice-hold">Hold to talk</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-seaman">Seaman drill</button>' +
      "</div>" +
      '<div class="qcs-voice-out" id="qcs-voice-out">Mic lane — speak for Seaman-style games</div>' +
      "</div>" +
      '<div class="qcs-actions">' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-play">Play with Hostess 7</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-zapper">Zapper timing</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-senses">Sync senses</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-verify">Verify emulators</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-relay">SAP relay</button>' +
      '<button type="button" class="gr-btn qcs-act" id="qcs-tour">Lab tour</button>' +
      "</div>" +
      '<div class="qcs-status" id="qcs-status">Connect a controller or use keyboard/mouse…</div>' +
      '<div class="qcs-hand"><span>Hand grip</span><div id="qcs-grips"></div></div>' +
      '<div class="qcs-grid" id="qcs-buttons"></div>' +
      '<div class="qcs-keys" id="qcs-keys"></div>' +
      '<div class="qcs-axes" id="qcs-axes"></div>' +
      '<div class="qcs-log" id="qcs-log"></div>' +
      "</div>"
    );
  }

  function parseApiJson(raw, status) {
    if (!String(raw || "").trim()) {
      return { ok: false, error: "empty_response", http_status: status };
    }
    try {
      const doc = JSON.parse(raw);
      if (status >= 400 && doc.ok !== false) doc.ok = false;
      if (status >= 400) doc.http_status = status;
      return doc;
    } catch (_e) {
      return { ok: false, error: "bad_json", http_status: status, detail: String(raw).slice(0, 160) };
    }
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "panel" }),
    });
    return parseApiJson(await r.text(), r.status);
  }

  async function stereoApi(body) {
    const r = await fetch(STEREO_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
    });
    return parseApiJson(await r.text(), r.status);
  }

  async function ingest(modality, payload) {
    try {
      await api({ action: "ingest", modality: modality, ...payload });
      await refreshPanel();
    } catch (_e) {
      log("Ingest failed: " + modality);
    }
  }

  function log(msg) {
    const el = document.getElementById("qcs-log");
    if (!el) return;
    const line = document.createElement("p");
    line.className = "qcs-log-line";
    line.textContent = msg;
    el.appendChild(line);
    while (el.children.length > 28) el.removeChild(el.firstElementChild);
    el.scrollTop = el.scrollHeight;
  }

  function renderStereo(st) {
    const el = document.getElementById("qcs-stereo");
    if (!el) return;
    const doc = st || panelDoc?.stereo_vision || {};
    const devices = doc.devices || doc.cached?.devices || [];
    const dev = devices[0] || {};
    const mode = dev.mode || (doc.stereoscopic ? "stereo" : "pending");
    const left = (dev.eyes || []).find(function (e) { return e.role === "left"; });
    const right = (dev.eyes || []).find(function (e) { return e.role === "right"; });
    const wtv = doc.webcam_tv || doc.cached?.webcam_tv;
    const dist = wtv?.last_depth?.distance_m || wtv?.last_capture?.depth?.distance_m;
    el.innerHTML =
      '<span class="qcs-stereo-badge' + (doc.stereoscopic ? " on" : "") + '">Stereo ' + (doc.stereoscopic ? "ON" : "…") + "</span>" +
      '<span class="qcs-eye' + (left?.live ? " live" : "") + '">L ' + (left?.live ? "live" : dev.surviving_role === "left" ? "sim" : "—") + "</span>" +
      '<span class="qcs-eye' + (right?.live ? " live" : "") + '">R ' + (right?.live ? "live" : dev.surviving_role === "right" ? "sim" : "—") + "</span>" +
      '<span class="qcs-mode">' + esc(mode) + (dist != null ? " · " + dist + " m" : "") + "</span>";
  }

  function renderSenses() {
    const el = document.getElementById("qcs-senses");
    if (!el || !panelDoc) return;
    renderStereo(panelDoc.stereo_vision);
    const mods = panelDoc.modalities || {};
    el.innerHTML = ["stereo_vision", "final_eye", "final_ear", "final_mouth"]
      .map(function (k) {
        const p = Math.round((mods[k]?.proficiency || 0) * 100);
        const live = mods[k]?.last_event === "live";
        return '<span class="qcs-sense' + (live ? " live" : "") + '">' + esc(k.replace("final_", "").replace("stereo_vision", "stereo")) + " " + p + "%</span>";
      })
      .join("");
  }

  function renderProf() {
    const el = document.getElementById("qcs-prof");
    if (!el || !panelDoc) return;
    const mods = panelDoc.modalities || {};
    renderSenses();
    el.innerHTML = ["keyboard", "mouse", "gamepad", "hand", "voice"]
      .map(function (m) {
        const p = Math.round((mods[m]?.proficiency || 0) * 100);
        return '<div class="qcs-prow"><span>' + esc(m) + '</span><div class="qcs-bar"><i style="width:' + p + '%"></i></div><span>' + p + "%</span></div>";
      })
      .join("");
    if (panelDoc.play_ready) {
      el.insertAdjacentHTML("beforeend", '<p class="qcs-ready">Play ready — Hostess 7 can join SAP</p>');
    }
  }

  async function refreshPanel() {
    try {
      panelDoc = await api({ action: "panel" });
      renderProf();
    } catch (_e) {
      /* offline */
    }
  }

  async function loadWebcams() {
    const sel = document.getElementById("qcs-webcam");
    if (!sel) return;
    try {
      const out = await stereoApi({ action: "probe_webcams" });
      sel.innerHTML = '<option value="">— webcam —</option>';
      (out.devices || []).forEach(function (d) {
        const o = document.createElement("option");
        o.value = d.device;
        o.textContent = (d.label || d.device) + (d.learnable ? " ✓" : "");
        sel.appendChild(o);
      });
    } catch (_e) {
      /* optional */
    }
  }

  async function loadPeripherals() {
    const sel = document.getElementById("qcs-periph-select");
    if (!sel || sel.options.length > 1) return;
    try {
      const r = await fetch(FH_API + "/catalog");
      const cat = await r.json();
      (cat.peripherals || [])
        .filter(function (p) { return p.status === "active"; })
        .forEach(function (p) {
          const o = document.createElement("option");
          o.value = p.id;
          o.textContent = p.label + " (" + p.system + ")";
          sel.appendChild(o);
        });
    } catch (_e) {
      /* optional */
    }
  }

  function renderGrips() {
    const el = document.getElementById("qcs-grips");
    if (!el) return;
    el.innerHTML = GRIPS.map(function (g) {
      return '<button type="button" class="qcs-grip" data-grip="' + esc(g) + '">' + esc(g) + "</button>";
    }).join("");
    el.querySelectorAll(".qcs-grip").forEach(function (btn) {
      btn.addEventListener("click", function () {
        ingest("hand", { grip: btn.getAttribute("data-grip"), event: "grip_select" });
        log("Hand grip: " + btn.getAttribute("data-grip"));
      });
    });
  }

  function renderPad(gp) {
    const st = document.getElementById("qcs-status");
    const btns = document.getElementById("qcs-buttons");
    const axes = document.getElementById("qcs-axes");
    if (!gp) {
      if (st) st.textContent = "No controller — keyboard/mouse/hand lanes still train Hostess 7";
      if (btns) btns.innerHTML = "";
      if (axes) axes.innerHTML = "";
      return;
    }
    if (st) {
      st.innerHTML = "<strong>" + esc(gp.id) + "</strong> · " + gp.buttons.length + " buttons · " + gp.axes.length + " axes";
    }
    if (btns) {
      btns.innerHTML = (gp.buttons || []).map(function (b, i) {
        const on = b.pressed || (b.value != null && b.value > 0.5);
        return '<span class="qcs-btn' + (on ? " on" : "") + '">' + esc(BTN_LABELS[i] || String(i)) + "</span>";
      }).join("");
    }
    if (axes) {
      axes.innerHTML = (gp.axes || []).map(function (v, i) {
        const pct = Math.round(Math.abs(v) * 100);
        return '<div class="qcs-axis"><span>Axis ' + i + '</span><div class="qcs-bar"><i style="width:' + pct + '%"></i></div><span>' + v.toFixed(2) + "</span></div>";
      }).join("");
    }
  }

  function pollGamepad() {
    const setup = document.getElementById("gr-arcade-setup");
    if (setup && setup.hidden) return;
    const pads = navigator.getGamepads?.() || [];
    const gp = pads.find(function (p) { return p && p.connected; });
    renderPad(gp || null);
    if (!gp) return;
    const buttons = [];
    for (let i = 0; i < gp.buttons.length; i++) {
      const b = gp.buttons[i];
      buttons.push({ i: i, pressed: !!b?.pressed, value: Number(b?.value) || 0 });
    }
    const axes = [];
    for (let i = 0; i < gp.axes.length; i++) {
      axes.push({ i: i, value: Number(gp.axes[i]) || 0 });
    }
    const pressed = buttons.some(function (b) { return b.pressed || b.value > 0.5; });
    const moved = axes.some(function (a) { return Math.abs(a.value) > 0.2; });
    if (pressed || moved) {
      ingest("gamepad", { buttons: buttons, axes: axes, id: gp.id });
    }
  }

  function wire() {
    if (wired) return;
    wired = true;

    window.addEventListener("gamepadconnected", function (e) {
      log("Gamepad: " + (e.gamepad && e.gamepad.id));
      pollGamepad();
    });
    window.addEventListener("gamepaddisconnected", function () {
      log("Gamepad disconnected");
      pollGamepad();
    });

    const keysEl = document.getElementById("qcs-keys");
    const watch = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Enter", "z", "x", "a", "s", "w", "d"];
    window.addEventListener("keydown", function (e) {
      const setup = document.getElementById("gr-arcade-setup");
      if (!setup || setup.hidden) return;
      if (!watch.includes(e.key)) return;
      const now = Date.now();
      const dt = lastKeyTs ? now - lastKeyTs : 0;
      lastKeyTs = now;
      ingest("keyboard", { key: e.key, dt_ms: dt, event: "keydown" });
      if (keysEl) {
        keysEl.innerHTML = '<span class="qcs-btn on">' + esc(e.key === " " ? "Space" : e.key) + "</span>";
      }
      log("Key: " + e.key);
    });

    window.addEventListener("mousemove", function (e) {
      const setup = document.getElementById("gr-arcade-setup");
      if (!setup || setup.hidden) return;
      const now = Date.now();
      const dt = lastMouseTs ? now - lastMouseTs : 0;
      const dx = e.clientX - lastMouseX;
      const dy = e.clientY - lastMouseY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const speed = dt > 0 ? (dist / dt) * 1000 : 0;
      lastMouseTs = now;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      if (dist > 2) {
        ingest("mouse", { event: "move", x: e.clientX, y: e.clientY, dt_ms: dt, speed: speed });
      }
    });

    window.addEventListener("mousedown", function (e) {
      const setup = document.getElementById("gr-arcade-setup");
      if (!setup || setup.hidden) return;
      ingest("mouse", { event: "click", x: e.clientX, y: e.clientY, button: e.button });
      log("Mouse click");
    });

    window.addEventListener("touchstart", function (e) {
      const setup = document.getElementById("gr-arcade-setup");
      if (!setup || setup.hidden) return;
      const t = e.touches[0];
      if (!t) return;
      ingest("hand", { event: "touch", x: t.clientX, y: t.clientY, grip: "precision" });
    }, { passive: true });

    document.getElementById("qcs-play")?.addEventListener("click", async function () {
      const sys = global.QueenGameRoom?.state?.system || "nes";
      log("Play with Hostess 7…");
      const out = await api({ action: "play_with_us", system: sys, spawn_rtx: false });
      log(out.message || (out.ok ? "Armed" : "Play failed"));
      await refreshPanel();
    });

    document.getElementById("qcs-zapper")?.addEventListener("click", async function () {
      const out = await api({ action: "zapper_timing", display: "ntsc_60", frame: 0 });
      const w = out.detect_window || {};
      log("Zapper " + w.start_ms + "–" + w.end_ms + " ms @ " + (out.refresh_hz || 59.94) + " Hz");
    });

    document.getElementById("qcs-senses")?.addEventListener("click", async function () {
      const out = await api({ action: "sync_senses" });
      log("Senses synced — " + Object.keys(out.senses || {}).length + " lanes");
      await refreshPanel();
    });

    document.getElementById("qcs-tour")?.addEventListener("click", async function () {
      try {
        const r = await fetch(LAB_API + "/tour");
        const tour = await r.json();
        log("Lab tour: " + (tour.stop_count || 0) + " stops");
        if (tour.voice) log(tour.voice.split("\n")[0]);
      } catch (_e) {
        log("Lab tour unavailable");
      }
    });

    document.getElementById("qcs-periph-select")?.addEventListener("change", async function () {
      const pid = this.value;
      if (!pid) return;
      await api({ action: "peripheral_train", peripheral_id: pid, ticks: 4 });
      log("Trained: " + pid);
      await refreshPanel();
    });

    document.getElementById("qcs-verify")?.addEventListener("click", async function () {
      log("Verifying emulators…");
      const out = await api({ action: "verify", capture: false, final_eye: false });
      log("ROM ready: " + (out.rom_ready || 0) + "/" + (out.systems_checked || "?"));
      if (out.engine_missing) log("Engine missing — run Queen/scripts/g16-build.sh");
    });

    document.getElementById("qcs-relay")?.addEventListener("click", async function () {
      const sys = global.QueenGameRoom?.state?.system || "nes";
      const out = await api({ action: "sap_relay", system: sys });
      log(out.ok ? "SAP relay ok" : "SAP relay failed");
    });

    document.getElementById("qcs-tv-learn")?.addEventListener("click", async function () {
      const device = document.getElementById("qcs-webcam")?.value || undefined;
      const tvIn = parseFloat(document.getElementById("qcs-tv-in")?.value || "55");
      const dist = document.getElementById("qcs-tv-dist")?.value;
      log("TV watch learn…");
      await stereoApi({ action: "configure_webcam_tv", device: device, tv_diagonal_in: tvIn, distance_m: dist ? parseFloat(dist) : undefined });
      const out = await api({ action: "tv_watch", device: device, tv_diagonal_in: tvIn, distance_m: dist ? parseFloat(dist) : undefined });
      const depth = out.capture?.depth?.depth || out.capture?.depth;
      if (depth?.distance_m != null) {
        log("TV depth " + depth.distance_m + " m (" + depth.distance_ft + " ft)");
      } else {
        log(out.capture?.ok === false ? "TV capture failed — check webcam" : "TV learn tick");
      }
      await refreshPanel();
    });

    async function runVoiceGame(utterance, gameId) {
      const gid = gameId || document.getElementById("qcs-voice-game")?.value || "seaman";
      const sys = gid === "seaman" ? "dreamcast" : (global.QueenGameRoom?.state?.system || "dreamcast");
      log("Voice game: " + gid + (utterance ? " — " + utterance.slice(0, 40) : ""));
      const out = await api({
        action: "voice_game",
        game: gid,
        system: sys,
        utterance: utterance || undefined,
        speak: true,
      });
      const outEl = document.getElementById("qcs-voice-out");
      if (outEl) {
        outEl.innerHTML =
          (out.heard ? '<span class="qcs-voice-heard">You: ' + esc(out.heard) + "</span> ") : "") +
          (out.reply ? '<span class="qcs-voice-reply">Mouth: ' + esc(out.reply) + "</span>" : "");
      }
      if (out.reply) log("Mouth: " + out.reply.slice(0, 72));
      await refreshPanel();
      return out;
    }

    function wireVoice() {
      const holdBtn = document.getElementById("qcs-voice-hold");
      const Speech = global.SpeechRecognition || global.webkitSpeechRecognition;
      if (Speech && !voiceRec) {
        voiceRec = new Speech();
        voiceRec.continuous = false;
        voiceRec.interimResults = false;
        voiceRec.lang = "en-US";
        voiceRec.onresult = function (ev) {
          const t = ev.results?.[0]?.[0]?.transcript || "";
          if (t) runVoiceGame(t);
        };
        voiceRec.onerror = function () {
          log("Voice capture unavailable — use Seaman drill");
        };
      }
      holdBtn?.addEventListener("pointerdown", function () {
        voiceHolding = true;
        holdBtn.classList.add("on");
        if (voiceRec) {
          try { voiceRec.start(); } catch (_e) { /* already started */ }
        } else {
          log("Web Speech API unavailable — click Seaman drill");
        }
      });
      holdBtn?.addEventListener("pointerup", function () {
        voiceHolding = false;
        holdBtn.classList.remove("on");
        if (voiceRec) {
          try { voiceRec.stop(); } catch (_e) { /* ok */ }
        }
      });
      holdBtn?.addEventListener("pointerleave", function () {
        if (!voiceHolding) return;
        voiceHolding = false;
        holdBtn.classList.remove("on");
        if (voiceRec) try { voiceRec.stop(); } catch (_e) { /* ok */ }
      });
      document.getElementById("qcs-seaman")?.addEventListener("click", function () {
        runVoiceGame("Hello Seaman — Hostess 7 is listening.", "seaman");
      });
      fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "voice_games" }),
      })
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          const sel = document.getElementById("qcs-voice-game");
          if (!sel || !doc.profiles) return;
          sel.innerHTML = "";
          Object.keys(doc.profiles).forEach(function (gid) {
            const g = doc.profiles[gid];
            const o = document.createElement("option");
            o.value = gid;
            o.textContent = (g.label || gid) + " (" + (g.platform || g.system || "") + ")";
            sel.appendChild(o);
          });
        })
        .catch(function () { /* offline */ });
    }

    wireVoice();
    pollTimer = setInterval(pollGamepad, 80);
  }

  function mount(host) {
    const root = host || document.getElementById("gr-controller-mount");
    if (!root) return;
    if (!document.getElementById("qcs-root")) {
      const wrap = document.createElement("div");
      wrap.innerHTML = panelHtml();
      root.appendChild(wrap.firstElementChild);
    }
    renderGrips();
    wire();
    loadPeripherals();
    loadWebcams();
    refreshPanel();
    pollGamepad();
  }

  function open() {
    const setup = document.getElementById("gr-arcade-setup");
    const layout = document.querySelector(".gr-layout");
    const arcade = document.querySelector(".gr-arcade");
    if (!setup) return;
    setup.hidden = false;
    layout?.classList.add("gr-layout--arcade-focus");
    global.QueenGameRoom?.closeCurtains?.();
    mount();
    arcade?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    if (location.hash !== "#arcade") {
      history.replaceState(null, "", "/queen-game-room.html#arcade");
    }
  }

  function close() {
    const setup = document.getElementById("gr-arcade-setup");
    const layout = document.querySelector(".gr-layout");
    if (!setup) return;
    setup.hidden = true;
    layout?.classList.remove("gr-layout--arcade-focus");
    global.QueenGameRoom?.openCurtains?.();
    if (location.hash === "#arcade") {
      history.replaceState(null, "", "/queen-game-room.html");
    }
  }

  function toggle() {
    const setup = document.getElementById("gr-arcade-setup");
    if (setup && !setup.hidden) close();
    else open();
  }

  global.QueenControllerSetup = {
    mount: mount,
    open: open,
    close: close,
    toggle: toggle,
    poll: pollGamepad,
    ingest: ingest,
  };
})(typeof window !== "undefined" ? window : globalThis);