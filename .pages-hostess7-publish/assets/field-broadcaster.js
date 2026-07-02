(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let state = {
    doc: null,
    activeScene: null,
    previewScene: null,
    previewUrl: "",
    programUrl: "",
    desktopTick: null,
  };

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function formatBytes(n) {
    const b = Number(n) || 0;
    if (b < 1024) return b + " B";
    if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
    return (b / 1048576).toFixed(1) + " MB";
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  async function chamber(action, body) {
    return api("/api/field-broadcaster/chamber", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.assign({ action: action }, body || {})),
    });
  }

  async function studio(action, body) {
    return chamber(action, body);
  }

  function studioDoc(doc) {
    return doc.studio || doc;
  }

  function feedUrl(feed) {
    if (!feed || !feed.url) return "";
    if (feed.type === "desktop_preview") {
      return feed.url + (feed.url.includes("?") ? "&" : "?") + "t=" + Date.now();
    }
    return feed.url;
  }

  function applyFeed(img, ph, feed, stateKey) {
    if (!img) return;
    const url = feedUrl(feed);
    if (url && feed?.type) {
      if (state[stateKey] !== url || feed.type === "desktop_preview") {
        state[stateKey] = url;
        img.src = url;
      }
      img.hidden = false;
      if (ph) ph.hidden = true;
      return;
    }
    img.hidden = true;
    if (ph) ph.hidden = false;
  }

  function renderPlatforms(doc) {
    const sel = $("bc-platform-select");
    if (!sel) return;
    const st = studioDoc(doc);
    const plats = (st.platforms || doc.platforms || {}).platforms || [];
    const cur = (st.platform || doc.platform || {}).id || "kick";
    sel.innerHTML = plats
      .map((p) => `<option value="${esc(p.id)}"${p.id === cur ? " selected" : ""}>${esc(p.label)}</option>`)
      .join("");
    const platLbl = $("bc-platform-label");
    if (platLbl) platLbl.textContent = `Platform: ${(st.platform || {}).label || cur}`;
  }

  function renderCodecs(doc) {
    const el = $("bc-codecs");
    if (!el) return;
    const codecs = studioDoc(doc).codecs || doc.codecs || {};
    const enc = studioDoc(doc).encoder || {};
    const vids = (codecs.video_codecs || []).slice(0, 6).map((c) => c.id).join(", ");
    const auds = (codecs.audio_codecs || []).slice(0, 5).map((c) => c.id).join(", ");
    el.innerHTML =
      `<div class="bc-dev-row"><strong>Stream</strong>${esc(enc.video || "h264")} + ${esc(enc.audio || "aac")}</div>` +
      `<div class="bc-dev-row"><strong>Bitrate</strong>${enc.bitrate_kbps ?? 4500} kbps</div>` +
      `<div class="bc-dev-row"><strong>Video</strong>${esc(vids || "h264 av1 vp9")}</div>` +
      `<div class="bc-dev-row"><strong>Audio</strong>${esc(auds || "aac opus flac")}</div>` +
      `<div class="bc-dev-row"><strong>NVENC</strong>${codecs.nvenc_available ? "yes" : "cpu"}</div>`;
  }

  function renderCanvas(doc) {
    const el = $("bc-canvas");
    if (!el) return;
    const wire = doc.canvas_wire || studioDoc(doc).canvas_wire || {};
    const linked = !!(wire.connected || doc.canvas_wire?.connected);
    const mode = wire.mode || wire.link?.mode || doc.routing?.default || "straight_path";
    el.className = "bc-canvas" + (linked ? " linked" : "");
    const feed = wire.feed || wire.link?.feed || {};
    const egress = (feed.secure || {}).localhost_only ? "localhost sealed" : "check egress";
    const routeLbl = mode === "straight_path" ? "straight path" : "look path";
    el.innerHTML = linked
      ? `CANVAS linked · ${routeLbl} · ${esc(wire.posture || "Final_Eye → CANVAS")} · ${egress}`
      : `CANVAS standby — straight path wire (Eye looks only on demand)`;
  }

  function renderPreview(doc) {
    const st = studioDoc(doc);
    const feed =
      st.preview_feed ||
      (doc.final_eye?.reachable !== false
        ? {
            type: "mjpeg",
            url:
              doc.canvas_wire?.feed?.ingress?.mjpeg ||
              doc.final_eye?.mjpeg ||
              doc.final_eye?.display?.mjpeg ||
              (doc.final_eye?.camera || {}).mjpeg ||
              "",
          }
        : null);
    applyFeed($("bc-preview-img"), $("bc-preview-ph"), feed, "previewUrl");
  }

  function renderProgram(doc) {
    const st = studioDoc(doc);
    const feed = st.program_feed || st.preview_feed || null;
    applyFeed($("bc-program-img"), $("bc-program-ph"), feed, "programUrl");
    const prog = $("bc-program-ph");
    if (prog && feed?.label) prog.textContent = `${feed.label} · CANVAS`;
    scheduleDesktopRefresh(feed);
  }

  function scheduleDesktopRefresh(feed) {
    if (state.desktopTick) {
      clearInterval(state.desktopTick);
      state.desktopTick = null;
    }
    if (!feed || feed.type !== "desktop_preview") return;
    const ms = Math.max(2000, Number(feed.refresh_ms) || 2000);
    state.desktopTick = setInterval(() => {
      const img = $("bc-program-img");
      if (!img || img.hidden) return;
      const base = String(feed.url || "").split("&t=")[0];
      img.src = base + (base.includes("?") ? "&" : "?") + "t=" + Date.now();
    }, ms);
  }

  function renderRecordings(doc) {
    const el = $("bc-recordings");
    if (!el) return;
    const rows = doc.recordings || [];
    el.innerHTML = rows.length
      ? rows
          .map(
            (r) =>
              `<li data-play-url="${esc(r.playback_url || "")}">` +
              `<span>${esc(r.name)}</span>` +
              `<span class="bc-src-kind">${formatBytes(r.bytes)}</span></li>`
          )
          .join("")
      : '<li class="bc-muted">Record locally — playback here</li>';
    el.querySelectorAll("[data-play-url]").forEach((li) => {
      li.addEventListener("click", () => playRecording(li.dataset.playUrl));
    });
  }

  function playRecording(url) {
    const vid = $("bc-playback");
    if (!vid || !url) return;
    vid.src = url;
    vid.hidden = false;
    vid.play().catch(() => {});
  }

  function renderScenes(doc) {
    const el = $("bc-scenes");
    if (!el) return;
    const st = studioDoc(doc);
    const scenes = st.scenes || [];
    const active = st.active_scene || state.activeScene;
    const preview = st.preview_scene || state.previewScene;
    el.innerHTML = scenes
      .map((s) => {
        const cls = s.id === active ? "active" : s.id === preview ? "preview" : "";
        return `<li class="${cls}" data-scene-id="${esc(s.id)}"><span>${esc(s.name)}</span></li>`;
      })
      .join("");
    el.querySelectorAll("li").forEach((li) => {
      li.addEventListener("click", () => activateScene(li.dataset.sceneId));
      li.addEventListener("dblclick", () => {
        state.previewScene = li.dataset.sceneId;
        studio("scene_activate", { scene_id: li.dataset.sceneId, preview: true }).then(refresh);
      });
    });
  }

  function renderSources(doc) {
    const el = $("bc-sources");
    if (!el) return;
    const st = studioDoc(doc);
    const sid = st.active_scene || state.activeScene;
    const sources = (st.sources || {})[sid] || [];
    el.innerHTML = sources.length
      ? sources
          .map(
            (s) =>
              `<li data-source-id="${esc(s.id)}">` +
              `<span>${esc(s.name)}</span>` +
              `<span class="bc-src-kind">${esc(s.kind)}</span></li>`
          )
          .join("")
      : '<li class="bc-muted">Add display, desktop, camera, or audio</li>';
    el.querySelectorAll("[data-source-id]").forEach((li) => {
      li.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        openMenu(ev.clientX, ev.clientY, [
          { label: "Move up", fn: () => moveSource(li.dataset.sourceId, "up") },
          { label: "Move down", fn: () => moveSource(li.dataset.sourceId, "down") },
          { label: "Remove", fn: () => removeSource(li.dataset.sourceId), danger: true },
        ]);
      });
    });
  }

  function renderDevices(doc) {
    const el = $("bc-devices");
    if (!el) return;
    const dev = studioDoc(doc).devices || {};
    const rows = []
      .concat(
        (dev.displays || []).map((d) => ({
          cat: d.capturable ? "Desktop" : d.primary ? "Final_Eye Display" : "Display",
          name: d.name,
        }))
      )
      .concat((dev.cameras || []).map((d) => ({ cat: d.primary ? "Final_Eye Cam" : "Camera", name: d.name })))
      .concat((dev.audio_inputs || []).slice(0, 3).map((d) => ({ cat: "Audio In", name: d.name })));
    el.innerHTML = rows.length
      ? rows.map((r) => `<div class="bc-dev-row"><strong>${esc(r.cat)}</strong>${esc(r.name)}</div>`).join("")
      : "<span>No devices detected</span>";
  }

  function renderMixer(doc) {
    const el = $("bc-mixer");
    if (!el) return;
    const audio = doc.audio || {};
    const settings = audio.settings || dacSettings(audio);
    const prof = audio.active_profile || {};
    const inDev = settings.input_device || audio.devices?.default_source || "default";
    const outDev = settings.output_device || audio.devices?.default_sink || "default";
    el.innerHTML =
      `<div class="bc-dev-row"><strong>Profile</strong>${esc(prof.label || settings.format_profile || "Stereo")}</div>` +
      `<div class="bc-dev-row"><strong>Mic</strong>${esc(String(inDev).slice(0, 28))}</div>` +
      `<div class="bc-dev-row"><strong>Out</strong>${esc(String(outDev).slice(0, 28))}</div>` +
      `<div class="bc-dev-row"><strong>In</strong>${settings.input_gain_db ?? 0} dB · <strong>Out</strong>${settings.output_gain_db ?? 0} dB</div>` +
      `<a class="bc-dac-link" href="/field-audio-dac" target="_blank">Open DAC →</a>`;
  }

  function dacSettings(audio) {
    return audio.settings && audio.settings.input_device ? audio.settings : audio.chain?.settings || {};
  }

  function renderThreat(doc) {
    const el = $("bc-threat");
    if (!el) return;
    const threat = studioDoc(doc).threat || doc.threat || {};
    const blocked = !threat.ok && threat.blocked > 0;
    el.className = "bc-threat" + (blocked ? " blocked" : "");
    el.innerHTML = blocked
      ? `Threat blocked · ${threat.blocked} candidate(s) — go-live refused`
      : `Scene guard OK · threat control active`;
  }

  function renderStatus(doc) {
    const st = studioDoc(doc);
    const live = !!(st.streaming || doc.streaming);
    const rec = !!(st.recording || doc.recording);
    if ($("bc-status-text")) $("bc-status-text").textContent = live ? "STREAMING" : rec ? "RECORDING" : "Ready";
    if ($("bc-menubar-status")) $("bc-menubar-status").textContent = live ? "● ON AIR" : rec ? "● REC" : "Studio ready";
    if ($("bc-scene-label")) $("bc-scene-label").textContent = `Scene: ${st.active_scene || "—"}`;
    const comb = st.combinatorics || doc.combinatorics || {};
    if ($("bc-comb-label")) $("bc-comb-label").textContent = `Seq: ${comb.sequence_length ?? "—"}`;
    $("bc-go-live")?.classList.toggle("on-air", live);
    $("bc-record")?.classList.toggle("on-air", rec);
  }

  function render(doc) {
    state.doc = doc;
    state.activeScene = studioDoc(doc).active_scene;
    state.previewScene = studioDoc(doc).preview_scene;
    renderPlatforms(doc);
    renderCodecs(doc);
    renderCanvas(doc);
    renderPreview(doc);
    renderProgram(doc);
    renderScenes(doc);
    renderSources(doc);
    renderDevices(doc);
    renderMixer(doc);
    renderThreat(doc);
    renderRecordings(doc);
    renderStatus(doc);
  }

  async function refresh() {
    try {
      render(await api("/api/field-broadcaster"));
    } catch (e) {
      if ($("bc-menubar-status")) $("bc-menubar-status").textContent = "Load failed: " + e.message;
    }
  }

  async function savePlatform() {
    const id = $("bc-platform-select")?.value || "kick";
    const key = $("bc-stream-key")?.value || "";
    await studio("set_platform", { platform_id: id, stream_key: key });
    await refresh();
  }

  async function wireCanvas() {
    await chamber("canvas_connect", { connect: true, mode: "straight_path" });
    await refresh();
  }

  async function eyeLook() {
    const r = await chamber("look", { label: "broadcaster_panel_look" });
    if (!r.ok) alert(r.error === "truth_gate_failed" ? "Truth gate blocked look" : r.error || "Look failed");
    await refresh();
  }

  async function activateScene(sceneId) {
    await studio("scene_activate", { scene_id: sceneId });
    state.activeScene = sceneId;
    await refresh();
  }

  async function transitionCut() {
    const to = state.previewScene || state.activeScene;
    if (!to) return;
    await studio("transition", { to_scene: to, from_scene: state.activeScene, kind: "cut", ms: 0 });
    await refresh();
  }

  async function transitionFade() {
    const to = state.previewScene || state.activeScene;
    if (!to) return;
    const viewport = $("bc-program");
    const r = await studio("transition", { to_scene: to, from_scene: state.activeScene, kind: "fade", ms: 500 });
    if (!r.ok) {
      alert(r.error || "Transition failed");
      return;
    }
    const ms = (r.transition && r.transition.ms) || 500;
    viewport?.classList.add("bc-fade-out");
    setTimeout(async () => {
      await studio("scene_activate", { scene_id: to });
      viewport?.classList.remove("bc-fade-out");
      viewport?.classList.add("bc-fade-in");
      setTimeout(() => viewport?.classList.remove("bc-fade-in"), ms);
      await refresh();
    }, ms);
  }

  async function addScene() {
    const name = prompt("Scene name", "New Scene");
    if (!name) return;
    await studio("scene_add", { name: name });
    await refresh();
  }

  async function addSource(kind, device) {
    const sid = state.activeScene || studioDoc(state.doc || {}).active_scene;
    if (!sid) return;
    const mapped = kind === "display" ? "final_eye_display" : kind === "camera" ? "final_eye" : kind;
    const body = { scene_id: sid, kind: mapped };
    if (device) body.device = device;
    const r = await studio("source_add", body);
    if (!r.ok) {
      alert(
        r.error === "threat_blocked"
          ? "Threat guard blocked desktop capture"
          : r.error === "invalid_desktop_monitor"
            ? "Pick a valid monitor"
            : r.error || "Add source failed"
      );
    }
    await refresh();
  }

  async function addDesktop(ev) {
    const r = await studio("desktops");
    if (!r.ok) {
      alert(r.error === "threat_blocked" ? "Threat guard blocked desktop capture" : r.error || "Desktop unavailable");
      return;
    }
    const monitors = r.monitors || [];
    if (!monitors.length) {
      alert("No capturable monitors on this session");
      return;
    }
    if (monitors.length === 1) {
      await addSource("desktop", monitors[0].id);
      return;
    }
    const x = ev?.clientX || 120;
    const y = ev?.clientY || 120;
    openMenu(
      x,
      y,
      monitors.map((m) => ({
        label: m.name || m.id,
        fn: () => addSource("desktop", m.id),
      }))
    );
  }

  async function removeSource(sourceId) {
    await studio("source_remove", { scene_id: state.activeScene, source_id: sourceId });
    await refresh();
  }

  async function moveSource(sourceId, direction) {
    await studio("source_move", { scene_id: state.activeScene, source_id: sourceId, direction: direction });
    await refresh();
  }

  function openMenu(x, y, items) {
    const dd = $("bc-dropdown");
    if (!dd) return;
    dd.hidden = false;
    dd.style.left = x + "px";
    dd.style.top = y + "px";
    dd.innerHTML = items
      .map(
        (it, i) =>
          `<button type="button" data-idx="${i}"${it.danger ? ' style="color:#fca5a5"' : ""}>${esc(it.label)}</button>`
      )
      .join("");
    dd.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        items[parseInt(btn.dataset.idx, 10)].fn();
        dd.hidden = true;
      });
    });
    const close = () => {
      dd.hidden = true;
      document.removeEventListener("click", close);
    };
    setTimeout(() => document.addEventListener("click", close), 0);
  }

  const MENUS = {
    file: [
      { label: "Wire Final_Eye → CANVAS (straight path)", fn: () => wireCanvas() },
      { label: "Final_Eye Look → share Hostess 7", fn: () => eyeLook() },
      { label: "Exit", fn: () => window.close() },
    ],
    edit: [
      { label: "Add Scene", fn: () => addScene() },
      { label: "Remove Active Scene", fn: () => studio("scene_remove", { scene_id: state.activeScene }).then(refresh) },
    ],
    view: [{ label: "Refresh", fn: () => refresh() }],
    scene: [{ label: "Add Scene", fn: () => addScene() }],
    stream: [
      { label: "Kick", fn: () => studio("set_platform", { platform_id: "kick" }).then(refresh) },
      { label: "Twitch", fn: () => studio("set_platform", { platform_id: "twitch" }).then(refresh) },
      { label: "YouTube", fn: () => studio("set_platform", { platform_id: "youtube" }).then(refresh) },
    ],
    codecs: [
      { label: "H.264 + AAC (stream)", fn: () => studio("set_encoder", { video: "h264", audio: "aac" }).then(refresh) },
      { label: "VP9 + Opus (WebM)", fn: () => studio("set_encoder", { video: "vp9", audio: "opus", container_record: "webm" }).then(refresh) },
      { label: "AV1 + AAC", fn: () => studio("set_encoder", { video: "av1", audio: "aac" }).then(refresh) },
    ],
    threat: [
      { label: "Threat panel", fn: () => window.open("/threat-panel.html", "_blank") },
      { label: "Re-check guard", fn: () => studio("threat").then(refresh) },
    ],
    help: [
      {
        label: "AmmoOS Broadcaster",
        fn: () =>
          alert(
            "Straight path by default: display/capture → CANVAS → stream. Desktop capture uses enumerated monitors only. Playback is localhost-sealed. Final_Eye looks are truth-gated."
          ),
      },
    ],
  };

  function bindMenus() {
    document.querySelectorAll(".bc-menu").forEach((nav) => {
      nav.addEventListener("click", (ev) => {
        openMenu(ev.clientX, ev.clientY - 8, MENUS[nav.dataset.menu] || []);
      });
    });
  }

  function bindControls() {
    $("bc-go-live")?.addEventListener("click", () => {
      api("/api/field-broadcaster/go-live", { method: "POST", body: "{}" }).then((r) => {
        if (!r.ok) alert(r.error === "stream_key_missing" ? "Set stream key first" : r.error || "Go-live failed");
        refresh();
      });
    });
    $("bc-record")?.addEventListener("click", () => api("/api/field-broadcaster/record", { method: "POST" }).then(refresh));
    $("bc-stop")?.addEventListener("click", () => studio("stop").then(refresh));
    $("bc-scene-add")?.addEventListener("click", addScene);
    $("bc-source-add-display")?.addEventListener("click", () => addSource("display"));
    $("bc-source-add-camera")?.addEventListener("click", () => addSource("camera"));
    $("bc-source-add-desktop")?.addEventListener("click", (ev) => addDesktop(ev));
    $("bc-source-add-audio")?.addEventListener("click", () => addSource("audio_input"));
    $("bc-platform-save")?.addEventListener("click", savePlatform);
    $("bc-canvas-wire")?.addEventListener("click", wireCanvas);
    $("bc-transition-cut")?.addEventListener("click", transitionCut);
    $("bc-transition-fade")?.addEventListener("click", transitionFade);
  }

  bindMenus();
  bindControls();
  refresh();
  setInterval(refresh, 5000);
})();