/**
 * Sweet Anita Protocol (SAP) — Queen Game Room multiplayer client over HTTP tunnel.
 */
(function (global) {
  "use strict";

  const API = "/api/sap";

  const state = {
    doc: null,
    session: null,
    pollTimer: null,
    connected: false,
    viewport: "desktop",
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
    ].join("");
    const invite = $("gr-sap-invite");
    if (invite && state.session?.invite) {
      invite.value = state.session.invite;
      invite.hidden = false;
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
      render();
      startPoll();
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
      state.session = { session_id: sessionId, remote };
      startPoll();
    }
    render();
    const log = $("gr-log");
    if (log) log.textContent = JSON.stringify(out, null, 2);
    return out;
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
      }
      if (p.type === "sap_join_ack") {
        state.connected = true;
        render();
      }
    }
  }

  function startPoll() {
    stopPoll();
    state.pollTimer = setInterval(pollOnce, 150);
  }

  function stopPoll() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = null;
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

  global.QueenSAP = { state, refresh, hostSession, joinSession, startPoll, stopPoll, init };
})(typeof window !== "undefined" ? window : globalThis);