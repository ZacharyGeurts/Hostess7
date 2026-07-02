/**
 * Queen Game Room — Webbrowser theater, CHIPS systems, cinema, gamepad (no RTX comp shader).
 */
(function () {
  "use strict";

  const API = "/api/game-room";
  const FB_API = "/api/game-room/fb";
  const ASPECTS = ["16/9", "4/3", "2.39/1", "10/9"];

  const state = {
    doc: null,
    system: "nes",
    cpu: "native",
    memory: "stock",
    aspect: "16/9",
    mode: "emulator",
    gamepad: null,
    fullscreen: false,
    webLive: false,
    spawned: false,
    romPath: null,
    fbPoll: null,
    curtainsOpen: false,
    lastPadBtn: {},
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function parseAspect(ratio) {
    const parts = String(ratio || "16/9").split("/").map(Number);
    const w = parts[0] || 16;
    const h = parts[1] || 9;
    return w / h;
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
    });
    return r.json();
  }

  async function refresh() {
    const r = await fetch(API, { cache: "no-store" });
    state.doc = r.ok ? await r.json() : await api({ action: "status" });
    state.webLive = !!(state.doc?.surface === "webbrowser" || state.doc?.web_surface);
    render();
    return state.doc;
  }

  function applyAspect(ratio) {
    const wrap = $("gr-screen-wrap");
    if (!wrap) return;
    const r = ratio || state.aspect || "16/9";
    wrap.style.aspectRatio = r.replace("/", " / ");
    wrap.dataset.aspect = r;
    resizeCanvas();
  }

  function resizeCanvas() {
    const wrap = $("gr-screen-wrap");
    const canvas = $("gr-canvas");
    if (!wrap || !canvas || canvas.hidden) return;
    const rect = wrap.getBoundingClientRect();
    const ratio = parseAspect(wrap.dataset.aspect || state.aspect);
    const w = Math.max(320, Math.floor(rect.width));
    const h = Math.max(240, Math.floor(w / ratio));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      if (!state.webLive) drawCanvasIdle();
    }
  }

  function openCurtains() {
    const stage = $("gr-stage");
    if (!stage) return;
    stage.classList.add("gr-curtains-open");
    state.curtainsOpen = true;
  }

  function closeCurtains() {
    const stage = $("gr-stage");
    if (!stage) return;
    stage.classList.remove("gr-curtains-open");
    state.curtainsOpen = false;
  }

  function renderSystems() {
    const el = $("gr-systems");
    if (!el || !state.doc) return;
    const systems = state.doc.systems || [];
    el.innerHTML = systems
      .map(
        (s) => {
          const infoUrl = s.info_url || `/world/queen-system-info.html?system=${encodeURIComponent(s.id)}`;
          return `
      <button type="button" class="gr-tile${state.system === s.id ? " active" : ""}${s.status === "scaffold" ? " scaffold" : ""}"
        data-system="${esc(s.id)}" title="${esc(s.chips || "")}">
        <a class="gr-tile-info" href="${esc(infoUrl)}" title="System info · CHIPS catalog" aria-label="Info for ${esc(s.label)}">ⓘ</a>
        <span class="gr-tile-label">${esc(s.label)}</span>
        <span class="gr-tile-meta">${esc(s.era)} · ${esc(s.cpu)}</span>
        ${s.movie ? '<span class="gr-tile-badge">Cinema</span>' : ""}
      </button>`;
        },
      )
      .join("");
    el.querySelectorAll("[data-system]").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        if (ev.target.closest(".gr-tile-info")) return;
        selectSystem(btn.dataset.system);
      });
    });
  }

  function renderCpus() {
    const el = $("gr-cpus");
    if (!el || !state.doc) return;
    el.innerHTML = (state.doc.host_cpus || [])
      .map(
        (c) =>
          `<option value="${esc(c.id)}"${state.cpu === c.id ? " selected" : ""}>${esc(c.label)}</option>`,
      )
      .join("");
  }

  function renderMemory() {
    const el = $("gr-memory");
    if (!el || !state.doc) return;
    el.innerHTML = (state.doc.memory_profiles || [])
      .map(
        (m) =>
          `<option value="${esc(m.id)}"${state.memory === m.id ? " selected" : ""}>${esc(m.label)}</option>`,
      )
      .join("");
  }

  function renderTestRom(test) {
    const el = $("gr-test-rom");
    if (!el) return;
    if (!test || test.ok === false) {
      if (state.system && state.system !== "cinema") {
        el.hidden = false;
        el.textContent = test?.hint || "Test ROM: run fetch-queen-test-roms.py";
      } else {
        el.hidden = true;
      }
      return;
    }
    el.hidden = false;
    el.textContent = `Test ROM: ${test.title || test.filename || "ready"} · ${test.filename || ""}`;
  }

  function renderStatus() {
    const el = $("gr-status");
    if (!el || !state.doc) return;
    const chips = state.doc.chips || {};
    const g16 = state.doc.grok16 || {};
    const rtx = state.doc.rtx || {};
    el.innerHTML = [
      `<span class="gr-pill${chips.present ? " ok" : ""}">CHIPS ${chips.headers || 0} headers</span>`,
      `<span class="gr-pill${g16.ready ? " ok" : ""}">G16 ${g16.profile || "field_opt"}</span>`,
      `<span class="gr-pill ok">Webbrowser</span>`,
      state.spawned
        ? `<span class="gr-pill ok">● pump ${state.system}</span>`
        : state.webLive
          ? `<span class="gr-pill ok">● CHIPS live</span>`
          : `<span class="gr-pill">CHIPS idle</span>`,
      state.gamepad
        ? `<span class="gr-pill ok">🎮 ${esc(state.gamepad.id)}</span>`
        : `<span class="gr-pill">🎮 controller</span>`,
    ].join("");
    const hud = $("gr-hud");
    if (hud) {
      if (state.webLive) {
        hud.hidden = false;
        hud.textContent = "Queen Webbrowser canvas · CHIPS web surface";
      } else if (state.mode === "cinema") {
        hud.hidden = false;
        hud.textContent = "Cinema · any movie format";
      } else {
        hud.hidden = true;
      }
    }
  }

  function render() {
    renderSystems();
    renderCpus();
    renderMemory();
    renderStatus();
    const sys = (state.doc?.systems || []).find((s) => s.id === state.system);
    const ratio = state.aspect || sys?.ratio || "16/9";
    applyAspect(ratio);
    const title = $("gr-stage-title");
    if (title) title.textContent = sys?.label || "Game Room";
    const mode = $("gr-mode-label");
    if (mode) {
      mode.textContent = sys?.movie
        ? "Cinema · MP4 WebM MKV MOV AVI MPEG HLS"
        : `${sys?.cpu || "CHIPS"} · ${state.cpu} host · ${state.memory} RAM`;
    }
  }

  async function selectSystem(id) {
    state.system = id;
    const sys = (state.doc?.systems || []).find((s) => s.id === id);
    if (sys?.movie) {
      state.mode = "cinema";
      applyAspect(sys.ratio || "2.39/1");
    } else {
      state.mode = "emulator";
      if (sys?.ratio) applyAspect(sys.ratio);
    }
    globalThis.QueenNesLibrary?.showNesRoom?.(id === "nes");
    render();
    const cfg = await api({
      action: "configure",
      system: state.system,
      host_cpu: state.cpu,
      memory: state.memory,
      aspect: state.aspect,
    });
    renderTestRom(cfg.test_rom);
  }

  function cycleSystem(dir) {
    const systems = state.doc?.systems || [];
    if (!systems.length) return;
    const idx = systems.findIndex((s) => s.id === state.system);
    const next = (idx + dir + systems.length) % systems.length;
    selectSystem(systems[next].id);
  }

  function cycleAspect(dir) {
    const idx = ASPECTS.indexOf(state.aspect);
    const next = (idx < 0 ? 0 : idx + dir + ASPECTS.length) % ASPECTS.length;
    state.aspect = ASPECTS[next];
    const sel = $("gr-aspect");
    if (sel) sel.value = state.aspect;
    applyAspect(state.aspect);
  }

  function stopFbPoll() {
    if (state.fbPoll) {
      clearInterval(state.fbPoll);
      state.fbPoll = null;
    }
  }

  function showFramebuffer(live) {
    const canvas = $("gr-canvas");
    const fb = $("gr-fb");
    const video = $("gr-video");
    if (!fb) return;
    if (live) {
      fb.hidden = false;
      if (canvas) canvas.hidden = true;
      if (video) video.hidden = true;
      fb.src = `${FB_API}/image?t=${Date.now()}`;
    } else {
      fb.hidden = true;
      fb.removeAttribute("src");
    }
  }

  async function pollFramebuffer() {
    try {
      const r = await fetch(FB_API, { cache: "no-store" });
      if (!r.ok) return;
      const fb = await r.json();
      state.spawned = !!(fb.spawned || fb.queen_process);
      if (fb.programs_canvas_ready && fb.image_url) {
        state.webLive = true;
        showFramebuffer(true);
        const hud = $("gr-hud");
        if (hud) {
          hud.hidden = false;
          hud.textContent = `CHIPS live · ${fb.system || state.system}${fb.rom_path ? " · " + fb.rom_path.split("/").pop() : ""}`;
        }
        renderStatus();
      } else if (!fb.queen_process) {
        state.webLive = false;
        state.spawned = false;
        stopFbPoll();
        showFramebuffer(false);
        renderStatus();
      }
    } catch (_) {
      /* quiet poll */
    }
  }

  function startFbPoll() {
    stopFbPoll();
    pollFramebuffer();
    state.fbPoll = setInterval(pollFramebuffer, 120);
  }

  async function launch(opts) {
    opts = opts || {};
    openCurtains();
    const body = {
      action: "launch",
      system: opts.system || state.system,
      host_cpu: state.cpu,
      memory: state.memory,
      spawn_rtx: opts.spawn_rtx !== false,
      surface: "webbrowser",
    };
    if (opts.rom_path) body.rom_path = opts.rom_path;
    if (opts.nes_id) body.nes_id = opts.nes_id;
    if (opts.title) body.title = opts.title;
    if (opts.system) state.system = opts.system;

    const out = await api(body);
    const log = $("gr-log");
    if (log) log.textContent = JSON.stringify(out, null, 2);
    if (out.mode === "cinema") {
      $("gr-movie-input")?.click();
    } else if (out.ok && out.spawned) {
      state.webLive = true;
      state.spawned = true;
      state.romPath = out.rom_path || null;
      startFbPoll();
      renderStatus();
    } else if (out.ok) {
      state.webLive = false;
      drawCanvasActive(out);
      renderStatus();
    }
    return out;
  }

  function drawCanvasActive(out) {
    const canvas = $("gr-canvas");
    if (!canvas) return;
    canvas.hidden = false;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const sys = out.system?.label || state.system || "CHIPS";
    ctx.fillStyle = "#0a0806";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#d4a853";
    ctx.font = `bold ${Math.max(16, w / 32)}px Georgia, serif`;
    ctx.textAlign = "center";
    ctx.fillText(sys, w / 2, h / 2 - 8);
    ctx.font = `${Math.max(11, w / 48)}px system-ui, sans-serif`;
    ctx.fillStyle = "#9a8b72";
    ctx.fillText("Queen Webbrowser · web canvas", w / 2, h / 2 + 16);
  }

  function pageActive() {
    return (
      document.body.classList.contains("queen-game-room-page") ||
      !!document.querySelector('[data-pane="gameroom"]:not([hidden])')
    );
  }

  function toggleFullscreen() {
    const stage = $("gr-stage");
    if (!stage) return;
    if (!document.fullscreenElement) {
      stage.requestFullscreen?.().catch(() => {});
      state.fullscreen = true;
      openCurtains();
    } else {
      document.exitFullscreen?.();
      state.fullscreen = false;
    }
    $("gr-fullscreen")?.classList.toggle("active", state.fullscreen);
  }

  function padPressed(gp, idx) {
    const pressed = gp.buttons[idx]?.pressed;
    const was = state.lastPadBtn[gp.index + ":" + idx];
    state.lastPadBtn[gp.index + ":" + idx] = pressed;
    return pressed && !was;
  }

  function pollGamepad() {
    const pads = navigator.getGamepads?.() || [];
    const gp = pads.find((p) => p && p.connected);
    if (gp && (!state.gamepad || state.gamepad.index !== gp.index)) {
      state.gamepad = gp;
      renderStatus();
    }
    if (!gp || !pageActive()) return;

    if (padPressed(gp, 0)) launch();
    if (padPressed(gp, 9) || padPressed(gp, 8)) toggleFullscreen();
    if (padPressed(gp, 1)) closeCurtains();
    if (padPressed(gp, 4)) cycleAspect(-1);
    if (padPressed(gp, 5)) cycleAspect(1);

    const ax = gp.axes[0] || 0;
    if (Math.abs(ax) > 0.55) {
      const key = "ax" + gp.index;
      if (!state.lastPadBtn[key]) {
        state.lastPadBtn[key] = true;
        cycleSystem(ax > 0 ? 1 : -1);
      }
    } else {
      state.lastPadBtn["ax" + gp.index] = false;
    }
  }

  function wireGamepad() {
    window.addEventListener("gamepadconnected", (e) => {
      state.gamepad = e.gamepad;
      renderStatus();
    });
    window.addEventListener("gamepaddisconnected", () => {
      state.gamepad = null;
      renderStatus();
    });
    setInterval(pollGamepad, 80);
  }

  function wireMovie() {
    const input = $("gr-movie-input");
    const video = $("gr-video");
    const canvas = $("gr-canvas");
    const fb = $("gr-fb");
    if (!input || !video) return;
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      const url = URL.createObjectURL(file);
      video.src = url;
      video.hidden = false;
      if (canvas) canvas.hidden = true;
      if (fb) fb.hidden = true;
      openCurtains();
      video.play().catch(() => {});
      state.mode = "cinema";
      const log = $("gr-log");
      if (log) log.textContent = `Playing: ${file.name} (${file.type || "unknown"})`;
      renderStatus();
    });
    video.addEventListener("dblclick", toggleFullscreen);
  }

  function wireControls() {
    $("gr-launch")?.addEventListener("click", () => launch());
    $("gr-fullscreen")?.addEventListener("click", toggleFullscreen);
    $("gr-refresh")?.addEventListener("click", () => refresh());
    $("gr-cpus")?.addEventListener("change", (e) => {
      state.cpu = e.target.value;
      api({ action: "configure", system: state.system, host_cpu: state.cpu, memory: state.memory });
      render();
    });
    $("gr-memory")?.addEventListener("change", (e) => {
      state.memory = e.target.value;
      api({ action: "configure", system: state.system, host_cpu: state.cpu, memory: state.memory });
    });
    $("gr-aspect")?.addEventListener("change", (e) => {
      state.aspect = e.target.value;
      applyAspect(state.aspect);
    });
    document.addEventListener("fullscreenchange", () => {
      state.fullscreen = !!document.fullscreenElement;
      $("gr-fullscreen")?.classList.toggle("active", state.fullscreen);
      resizeCanvas();
    });
    document.addEventListener("keydown", (e) => {
      if (!pageActive()) return;
      if (document.activeElement?.tagName === "INPUT") return;
      if (e.key === "f" && !e.ctrlKey) toggleFullscreen();
      if (e.key === "ArrowLeft") cycleSystem(-1);
      if (e.key === "ArrowRight") cycleSystem(1);
      if (e.key === "Enter") launch();
    });
    const wrap = $("gr-screen-wrap");
    if (wrap && globalThis.ResizeObserver) {
      new ResizeObserver(() => resizeCanvas()).observe(wrap);
    }
    window.addEventListener("resize", resizeCanvas);
  }

  function drawCanvasIdle() {
    const canvas = $("gr-canvas");
    if (!canvas || canvas.hidden) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, "#1a1210");
    g.addColorStop(1, "#050403");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "rgba(212, 168, 83, 0.18)";
    ctx.font = `bold ${Math.max(18, w / 28)}px Georgia, serif`;
    ctx.textAlign = "center";
    ctx.fillText("Queen Cinema", w / 2, h / 2 - 14);
    ctx.font = `${Math.max(12, w / 42)}px Inter, sans-serif`;
    ctx.fillStyle = "#9a8b72";
    ctx.fillText("75% Theater · 25% Arcade · Launch loads best test ROM", w / 2, h / 2 + 18);
    ctx.strokeStyle = "rgba(212, 168, 83, 0.25)";
    ctx.lineWidth = 2;
    ctx.strokeRect(w * 0.08, h * 0.12, w * 0.84, h * 0.76);
  }

  function setSystem(id) {
    state.system = id;
    globalThis.QueenNesLibrary?.showNesRoom?.(id === "nes");
    render();
  }

  function init() {
    const urlSystem = new URLSearchParams(location.search).get("system");
    if (urlSystem) state.system = urlSystem;

    wireControls();
    wireGamepad();
    wireMovie();
    drawCanvasIdle();
    refresh().then(async () => {
      if (urlSystem) await selectSystem(urlSystem);
      globalThis.QueenNesLibrary?.showNesRoom?.(state.system === "nes");
      globalThis.QueenNesLibrary?.init?.();
      globalThis.QueenSAP?.init?.();
      const cfg = await api({
        action: "configure",
        system: state.system,
        host_cpu: state.cpu,
        memory: state.memory,
        aspect: state.aspect,
      });
      renderTestRom(cfg.test_rom);
    });
    setInterval(refresh, 30000);
  }

  globalThis.QueenGameRoom = {
    state,
    refresh,
    launch,
    selectSystem,
    setSystem,
    toggleFullscreen,
    openCurtains,
    startFbPoll,
    stopFbPoll,
    init,
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();