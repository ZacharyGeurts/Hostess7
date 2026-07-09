/**
 * Sweet Anita Protocol (SAP) — Queen Room multiplayer client over HTTP tunnel.
 * Lockstep input sync v1 — gamepad → sap_input → sync_frame.
 */
(function (global) {
  "use strict";

  const API = "/api/sap";
  const POLL_MS = 150;
  const SYNC_MS = 150;

  const state = {
    doc: null,
    session: null,
    pollTimer: null,
    syncTimer: null,
    connected: false,
    viewport: "desktop",
    frame: 0,
    role: null,
    lastInputs: null,
    remoteInbox: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function detectViewport() {
    const w = global.innerWidth || 1024;
    if (w < 600) return "mobile";
    if (w < 1024) return "tablet";
    return "desktop";
  }

  async function sap(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
    });
    return r.json();
  }

  function readGamepadSnapshot() {
    const pads = navigator.getGamepads?.() || [];
    const gp = pads.find((p) => p && p.connected);
    if (!gp) return { connected: false, buttons: [], axes: [] };
    const buttons = [];
    for (let i = 0; i < gp.buttons.length; i++) {
      const b = gp.buttons[i];
      buttons.push({ i, pressed: !!b?.pressed, value: Number(b?.value) || 0 });
    }
    const axes = [];
    for (let i = 0; i < gp.axes.length; i++) {
      axes.push({ i, value: Number(gp.axes[i]) || 0 });
    }
    return { connected: true, id: gp.id, index: gp.index, buttons, axes, ts: Date.now() };
  }

  function inputsChanged(a, b) {
    if (!a || !b) return true;
    return JSON.stringify(a) !== JSON.stringify(b);
  }

  async function refresh() {
    state.doc = await sap({ action: "status" });
    state.viewport = detectViewport();
    render();
    return state.doc;
  }

  function render() {
    const el = $("gr-sap-status");
    if (!el || !state.doc) return;
    const b = state.doc.beacon || {};
    el.innerHTML = [
      `<span class="gr-pill ok">SAP v${b.sap_version || 1}</span>`,
      `<span class="gr-pill">${esc(state.viewport)}</span>`,
      state.session
        ? `<span class="gr-pill ok">session ${esc(state.session.session_id || "").slice(0, 12)}…</span>`
        : `<span class="gr-pill">no session</span>`,
      state.connected ? `<span class="gr-pill ok">tunnel live</span>` : "",
      state.frame ? `<span class="gr-pill">f${state.frame}</span>` : "",
      state.role ? `<span class="gr-pill">${esc(state.role)}</span>` : "",
    ].join("");
    const invite = $("gr-sap-invite");
    if (invite && state.session?.invite) {
      invite.value = state.session.invite;
      invite.hidden = false;
    }
  }

  async function publishBeacon(hostOut) {
    try {
      await fetch("/api/field-arcade-battalion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "publish_beacon",
          session_id: hostOut.session_id,
          token: hostOut.token,
          system: hostOut.system || global.QueenGameRoom?.state?.system || "nes",
          display_name: "Arcade Host",
        }),
      });
    } catch (_e) {
      /* lobby optional */
    }
  }

  async function hostSession() {
    const sys = global.QueenGameRoom?.state?.system || "nes";
    const rom = global.QueenNesLibrary?.state?.selected;
    const out = await sap({
      action: "host",
      system: sys,
      nes_id: rom,
      viewport: state.viewport,
      max_players: 4,
    });
    if (out.ok) {
      state.session = out;
      state.role = "host";
      state.frame = 0;
      render();
      startPoll();
      startInputSync();
      publishBeacon(out);
    }
    const log = $("gr-log");
    if (log) log.textContent = JSON.stringify(out, null, 2);
    return out;
  }

  async function joinSession() {
    const remote = ($("gr-sap-remote")?.value || "").trim();
    const sessionId = ($("gr-sap-session")?.value || "").trim();
    const token = ($("gr-sap-token")?.value || "").trim();
    if (!remote || !sessionId || !token) return;
    const out = await sap({
      action: "join",
      remote,
      session_id: sessionId,
      token,
      viewport: state.viewport,
    });
    if (out.ok) {
      state.connected = true;
      state.session = { session_id: sessionId, remote, token };
      state.role = "guest";
      state.remoteInbox = out.connect?.remote_inbox || null;
      startPoll();
      startInputSync();
    }
    render();
    const log = $("gr-log");
    if (log) log.textContent = JSON.stringify(out, null, 2);
    return out;
  }

  async function sendInput(inputs) {
    const inbox = state.doc?.inbox;
    if (!inbox) return;
    const payload = {
      type: "sap_input",
      session_id: state.session?.session_id,
      frame: state.frame,
      inputs,
      viewport: state.viewport,
    };
    if (state.role === "host" && state.session?.session_id) {
      await sap({
        action: "sync",
        session_id: state.session.session_id,
        frame: state.frame,
        inputs,
      });
      return;
    }
    const to = state.remoteInbox;
    if (to) {
      await sap({ action: "send", to_id: to, payload });
    }
  }

  async function pollOnce() {
    const inbox = state.doc?.inbox;
    if (!inbox) return;
    const out = await sap({ action: "poll", tunnel_id: inbox, timeout_ms: 800 });
    const msgs = out.messages || [];
    for (const m of msgs) {
      const p = m.payload || {};
      if (p.type === "sap_frame" && global.QueenGameRoom?.state) {
        global.QueenGameRoom.state.sapFrame = p.frame;
        state.frame = Number(p.frame) || state.frame;
      }
      if (p.type === "sap_join_ack") {
        state.connected = true;
        state.frame = Number(p.frame) || 0;
        render();
      }
      if (p.type === "sap_input") {
        global.QueenGameRoom = global.QueenGameRoom || { state: {} };
        global.QueenGameRoom.state.sapInputs = p.inputs;
        state.frame = Number(p.frame) || state.frame;
      }
    }
  }

  function startInputSync() {
    stopInputSync();
    state.syncTimer = setInterval(async () => {
      if (!state.session) return;
      const inputs = readGamepadSnapshot();
      if (!inputs.connected) return;
      if (!inputsChanged(inputs, state.lastInputs)) return;
      state.lastInputs = inputs;
      if (state.role === "host") {
        state.frame += 1;
      }
      await sendInput(inputs);
      render();
    }, SYNC_MS);
  }

  function startPoll() {
    stopPoll();
    state.pollTimer = setInterval(pollOnce, POLL_MS);
  }

  function stopPoll() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = null;
  }

  function stopInputSync() {
    if (state.syncTimer) clearInterval(state.syncTimer);
    state.syncTimer = null;
  }

  function wire() {
    $("gr-sap-host")?.addEventListener("click", () => hostSession());
    $("gr-sap-join")?.addEventListener("click", () => joinSession());
    global.addEventListener("resize", () => {
      state.viewport = detectViewport();
      render();
    });
  }

  function init() {
    wire();
    refresh();
  }

  global.QueenSAP = {
    state,
    refresh,
    hostSession,
    joinSession,
    readGamepadSnapshot,
    startPoll,
    stopPoll,
    startInputSync,
    stopInputSync,
    init,
  };
})(typeof window !== "undefined" ? window : globalThis);