/**
 * AmmoCode 2027 — invite-only collab, IP friends, voice, cursor personas.
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "ammocode-collab-v1";

  const state = {
    connected: false,
    ws: null,
    peerId: null,
    isHost: false,
    roomId: null,
    invite: "",
    name: "coder",
    cursorId: "arrow_emerald",
    peers: [],
    cursors: [],
    friendIps: [],
    muted: false,
    volume: 0.8,
    localStream: null,
    peerConnections: new Map(),
    audioEls: new Map(),
    sessionProof: "",
    screenShareGranted: false,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function cfg() {
    return global.AmmoCodeG16?.cfg?.() || { apiBase: "/api/ammocode" };
  }

  async function loadCursors() {
    if (state.cursors.length) return state.cursors;
    try {
      const r = await fetch("data/collab-cursors.json", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        state.cursors = j.cursors || [];
        state.cursorId = j.default || state.cursorId;
      }
    } catch (_) {}
    return state.cursors;
  }

  function collabWsUrl() {
    const host = location.hostname || "127.0.0.1";
    const port = new URLSearchParams(location.search).get("collab_port") || "9556";
    return `ws://${host}:${port}`;
  }

  async function createInvite(friendIps) {
    const r = await fetch(cfg().apiBase, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "collab_invite", friend_ips: friendIps || [] }),
    });
    return r.json();
  }

  async function saveLocal() {
    const patch = {
      collabName: state.name,
      collabCursorId: state.cursorId,
      collabInvite: state.invite,
      collabMuted: state.muted,
      collabVolume: state.volume,
    };
    try {
      if (global.AmmoCodeSettings?.save) {
        await global.AmmoCodeSettings.save(patch);
        return;
      }
    } catch (_) {}
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        name: state.name,
        cursorId: state.cursorId,
        invite: state.invite,
        muted: state.muted,
        volume: state.volume,
      }));
    } catch (_) {}
  }

  async function loadLocal() {
    try {
      if (global.AmmoCodeSettings?.load) {
        const j = await global.AmmoCodeSettings.load();
        if (j.ok) {
          const c = global.AmmoCodeSettings.collabFrom(j);
          state.name = c.name || state.name;
          state.cursorId = c.cursorId || state.cursorId;
          state.invite = c.invite || state.invite;
          state.muted = !!c.muted;
          state.volume = typeof c.volume === "number" ? c.volume : state.volume;
          return;
        }
      }
    } catch (_) {}
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const j = JSON.parse(raw);
      state.name = j.name || state.name;
      state.cursorId = j.cursorId || state.cursorId;
      state.invite = j.invite || state.invite;
      state.muted = !!j.muted;
      state.volume = typeof j.volume === "number" ? j.volume : state.volume;
    } catch (_) {}
  }

  function cursorMeta(id) {
    return state.cursors.find((c) => c.id === id) || { id, label: id, glyph: "↖", color: "#22c55e" };
  }

  function renderCursorOverlays() {
    const layer = $("ac-cursor-layer");
    if (!layer) return;
    layer.innerHTML = "";
    for (const p of state.peers) {
      if (p.peer_id === state.peerId) continue;
      const meta = cursorMeta(p.cursor_id);
      const el = document.createElement("div");
      el.className = "ac-remote-cursor";
      el.dataset.peer = p.peer_id;
      el.style.color = meta.color;
      el.style.setProperty("--cursor-color", meta.color);
      el.innerHTML = `<span class="ac-remote-glyph">${meta.glyph}</span><span class="ac-remote-name">${p.name}</span>`;
      layer.appendChild(el);
    }
  }

  function moveRemoteCursor(peerId, x, y, line, col) {
    const layer = $("ac-cursor-layer");
    const wrap = document.querySelector(".ac-editor-wrap");
    const ed = $("ac-editor");
    if (!layer || !wrap || !ed) return;
    let el = layer.querySelector(`[data-peer="${peerId}"]`);
    if (!el) {
      renderCursorOverlays();
      el = layer.querySelector(`[data-peer="${peerId}"]`);
    }
    if (!el) return;
    if (typeof x === "number" && typeof y === "number") {
      const rect = wrap.getBoundingClientRect();
      el.style.left = `${Math.max(0, x - rect.left)}px`;
      el.style.top = `${Math.max(0, y - rect.top)}px`;
    } else if (typeof line === "number") {
      const lineH = parseFloat(getComputedStyle(ed).lineHeight) || 19.5;
      const pad = 12;
      el.style.left = `${48 + pad + (col || 0) * 7}px`;
      el.style.top = `${pad + (line - 1) * lineH}px`;
    }
  }

  function appendChat(name, text, self) {
    const log = $("ac-chat-log");
    if (!log) return;
    const row = document.createElement("div");
    row.className = "ac-chat-row" + (self ? " self" : "");
    row.textContent = `${name}: ${text}`;
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  }

  function setStatus(text, ok) {
    const el = $("ac-collab-status");
    if (el) {
      el.textContent = text;
      el.className = "ac-collab-status " + (ok ? "ok" : "err");
    }
  }

  function updateMicUi() {
    const btn = $("ac-mic-toggle");
    const vol = $("ac-mic-volume");
    const icon = $("ac-mic-icon");
    if (btn) btn.classList.toggle("muted", state.muted);
    if (vol) vol.value = String(Math.round(state.volume * 100));
    if (icon) icon.textContent = state.muted ? "🔇" : "🎤";
    if (state.localStream) {
      state.localStream.getAudioTracks().forEach((t) => {
        t.enabled = !state.muted;
      });
    }
  }

  async function ensureMic() {
    if (state.localStream) return state.localStream;
    if (!navigator.mediaDevices?.getUserMedia) return null;
    try {
      state.localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      updateMicUi();
      return state.localStream;
    } catch (e) {
      setStatus("Mic denied", false);
      return null;
    }
  }

  function createPeerConnection(remoteId) {
    if (state.peerConnections.has(remoteId)) return state.peerConnections.get(remoteId);
    const pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
    state.peerConnections.set(remoteId, pc);
    if (state.localStream) {
      state.localStream.getTracks().forEach((t) => pc.addTrack(t, state.localStream));
    }
    pc.ontrack = (ev) => {
      let audio = state.audioEls.get(remoteId);
      if (!audio) {
        audio = document.createElement("audio");
        audio.autoplay = true;
        audio.dataset.peer = remoteId;
        $("ac-voice-sink")?.appendChild(audio);
        state.audioEls.set(remoteId, audio);
      }
      audio.srcObject = ev.streams[0];
      audio.volume = state.volume;
    };
    pc.onicecandidate = (ev) => {
      if (ev.candidate && state.ws?.readyState === WebSocket.OPEN) {
        state.ws.send(JSON.stringify({
          type: "voice_signal",
          to: remoteId,
          candidate: ev.candidate,
        }));
      }
    };
    return pc;
  }

  async function handleVoiceSignal(msg) {
    const from = msg.from;
    if (!from || from === state.peerId) return;
    const pc = createPeerConnection(from);
    if (msg.sdp) {
      await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
      if (msg.sdp.type === "offer") {
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        state.ws?.send(JSON.stringify({ type: "voice_signal", to: from, sdp: answer }));
      }
    }
    if (msg.candidate) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
      } catch (_) {}
    }
  }

  async function startVoiceMesh() {
    await ensureMic();
    for (const p of state.peers) {
      if (p.peer_id === state.peerId) continue;
      const pc = createPeerConnection(p.peer_id);
      if (state.peerId < p.peer_id) {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        state.ws?.send(JSON.stringify({ type: "voice_signal", to: p.peer_id, sdp: offer }));
      }
    }
  }

  function bindEditorCursor() {
    const wrap = document.querySelector(".ac-editor-wrap");
    const ed = $("ac-editor");
    if (!wrap || !ed) return;
    let throttle = 0;
    const send = (e) => {
      if (!state.connected || state.ws?.readyState !== WebSocket.OPEN) return;
      const now = Date.now();
      if (now - throttle < 50) return;
      throttle = now;
      const text = ed.value;
      const pos = ed.selectionStart;
      const line = text.slice(0, pos).split("\n").length;
      const col = pos - text.lastIndexOf("\n", pos - 1);
      state.ws.send(JSON.stringify({
        type: "cursor",
        line,
        col,
        x: e.clientX,
        y: e.clientY,
      }));
    };
    wrap.addEventListener("mousemove", send);
    ed.addEventListener("keyup", send);
    ed.addEventListener("click", send);
  }

  function renderCollabPanel() {
    const el = $("ac-flyout-collab");
    if (!el) return;
    const cursorOpts = state.cursors.map((c) =>
      `<option value="${c.id}" ${c.id === state.cursorId ? "selected" : ""}>${c.glyph} ${c.label}</option>`,
    ).join("");
    el.innerHTML = [
      '<div class="ac-side-head">Collab · invite only</div>',
      '<div class="ac-collab-body">',
      `<div class="ac-collab-status" id="ac-collab-status">${state.connected ? "connected" : "disconnected"}</div>`,
      '<label class="ac-collab-field">Display name<input type="text" id="ac-collab-name" maxlength="32" /></label>',
      '<label class="ac-collab-field">Invite token<input type="text" id="ac-collab-invite" placeholder="host shares token" /></label>',
      '<label class="ac-collab-field">Cursor persona<select id="ac-collab-cursor"></select></label>',
      '<label class="ac-collab-field">Friend IP (host)<input type="text" id="ac-friend-ip" placeholder="e.g. 192.168.1.42" /></label>',
      '<div class="ac-collab-actions">',
      '<button type="button" class="primary" id="ac-host-invite">Host · create invite</button>',
      '<button type="button" id="ac-join-room">Join with invite</button>',
      '<button type="button" id="ac-leave-room">Leave</button>',
      '</div>',
      '<div class="ac-voice-bar">',
      '<button type="button" class="ac-mic-btn" id="ac-mic-toggle" title="Mute microphone"><span id="ac-mic-icon">🎤</span></button>',
      '<label class="ac-mic-vol">Vol<input type="range" id="ac-mic-volume" min="0" max="100" value="80" /></label>',
      '<button type="button" id="ac-voice-start">Voice on</button>',
      '</div>',
      '<div class="ac-screenshare-bar">',
      '<div class="ac-side-head" style="margin:0">Screen share (permitted)</div>',
      '<p class="ac-net-muted">Host grants · GUI capture only · MITM session proof</p>',
      '<div class="ac-collab-actions">',
      '<button type="button" id="ac-ss-request">Request view</button>',
      '<button type="button" id="ac-ss-share" title="Host shares editor GUI">Share my GUI</button>',
      '<button type="button" id="ac-ss-stop">Stop share</button>',
      '</div>',
      '<div id="ac-screenshare-label" class="ac-net-muted"></div>',
      '<img id="ac-screenshare-img" class="ac-screenshare-img" alt="Remote screen" hidden />',
      '</div>',
      '<div class="ac-peer-list" id="ac-peer-list"></div>',
      '<div class="ac-chat-log" id="ac-chat-log"></div>',
      '<form class="ac-chat-form" id="ac-chat-form"><input id="ac-chat-input" placeholder="Chat while coding…" /><button type="submit">Send</button></form>',
      '<div id="ac-voice-sink" hidden></div>',
      '<div class="ac-invite-out" id="ac-invite-out"></div>',
      '</div>',
    ].join("");

    $("ac-collab-name").value = state.name;
    $("ac-collab-invite").value = state.invite;
    const sel = $("ac-collab-cursor");
    if (sel) sel.innerHTML = cursorOpts;

    $("ac-host-invite")?.addEventListener("click", async () => {
      const ip = $("ac-friend-ip")?.value?.trim();
      const j = await createInvite(ip ? [ip] : []);
      if (!j.ok) {
        setStatus(j.error || "invite failed", false);
        return;
      }
      state.invite = j.invite;
      $("ac-collab-invite").value = j.invite;
      saveLocal();
      $("ac-invite-out").textContent = `Share: ${j.invite}`;
      setStatus("Invite created — share token", true);
    });

    $("ac-join-room")?.addEventListener("click", () => connect());
    $("ac-leave-room")?.addEventListener("click", () => disconnect());
    $("ac-collab-name")?.addEventListener("change", (e) => { state.name = e.target.value; saveLocal(); });
    $("ac-collab-invite")?.addEventListener("change", (e) => { state.invite = e.target.value; saveLocal(); });
    $("ac-collab-cursor")?.addEventListener("change", (e) => {
      state.cursorId = e.target.value;
      saveLocal();
      if (state.connected) state.ws?.send(JSON.stringify({ type: "set_cursor", cursor_id: state.cursorId }));
    });
    $("ac-mic-toggle")?.addEventListener("click", () => {
      state.muted = !state.muted;
      updateMicUi();
      saveLocal();
      state.ws?.send(JSON.stringify({ type: "voice_state", muted: state.muted, volume: state.volume }));
    });
    $("ac-mic-volume")?.addEventListener("input", (e) => {
      state.volume = Number(e.target.value) / 100;
      updateMicUi();
      state.audioEls.forEach((a) => { a.volume = state.volume; });
      saveLocal();
      state.ws?.send(JSON.stringify({ type: "voice_state", muted: state.muted, volume: state.volume }));
    });
    $("ac-voice-start")?.addEventListener("click", () => startVoiceMesh());
    $("ac-chat-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = $("ac-chat-input");
      const text = input?.value?.trim();
      if (!text || !state.connected) return;
      state.ws?.send(JSON.stringify({ type: "chat", text }));
      appendChat(state.name, text, true);
      input.value = "";
    });
    $("ac-friend-ip")?.addEventListener("change", () => {
      const ip = $("ac-friend-ip")?.value?.trim();
      if (ip && state.isHost && state.connected) {
        state.ws?.send(JSON.stringify({ type: "add_friend_ip", ip }));
      }
    });
    $("ac-ss-request")?.addEventListener("click", () => {
      if (!state.connected) return;
      state.ws?.send(JSON.stringify({ type: "screen_share_request" }));
      setStatus("Screen share requested — awaiting host", true);
    });
    $("ac-ss-share")?.addEventListener("click", () => {
      if (!state.connected || !state.isHost) {
        global.AmmoCodeEditor?.toast?.("Only host can share GUI", false);
        return;
      }
      global.AmmoCodeScreenShare?.startSharing?.(state.ws, state.peerId);
      setStatus("Sharing GUI (sanctioned)", true);
    });
    $("ac-ss-stop")?.addEventListener("click", () => {
      global.AmmoCodeScreenShare?.stopSharing?.();
      global.AmmoCodeScreenShare?.hidePreview?.();
      if (state.isHost && state.connected) {
        state.ws?.send(JSON.stringify({ type: "screen_share_revoke", to: state.screenShareTarget || "" }));
      }
      state.screenShareGranted = false;
      setStatus("Screen share stopped", true);
    });
    updateMicUi();
    renderPeers();
  }

  function renderPeers() {
    const el = $("ac-peer-list");
    if (!el) return;
    el.innerHTML = state.peers.length
      ? state.peers.map((p) => {
          const m = cursorMeta(p.cursor_id);
          const mic = p.muted ? "🔇" : "🎤";
          const grantBtn = state.isHost && !p.is_host
            ? `<button type="button" class="ac-ss-grant" data-peer="${p.peer_id}">📺</button>` : "";
          return `<div class="ac-peer-row"><span style="color:${m.color}">${m.glyph}</span> ${p.name} ${p.is_host ? "(host)" : ""} <span class="ac-peer-mic">${mic}</span>${grantBtn}</div>`;
        }).join("")
      : '<div class="ac-peer-empty">No peers yet</div>';
    el.querySelectorAll(".ac-ss-grant").forEach((btn) => {
      btn.addEventListener("click", () => {
        const pid = btn.dataset.peer;
        if (!pid || !state.connected) return;
        state.ws?.send(JSON.stringify({ type: "screen_share_grant", to: pid }));
        state.screenShareTarget = pid;
        global.AmmoCodeEditor?.toast?.("Screen share permitted for peer", true);
      });
    });
    renderCursorOverlays();
  }

  function connect() {
    const invite = ($("ac-collab-invite")?.value || state.invite || "").trim();
    if (!invite) {
      setStatus("No connection without invite", false);
      global.AmmoCodeEditor?.toast?.("Invite token required", false);
      return;
    }
    state.name = ($("ac-collab-name")?.value || state.name).trim() || "coder";
    state.invite = invite;
    saveLocal();
    disconnect();
    const ws = new WebSocket(collabWsUrl());
    state.ws = ws;
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: "join",
        invite,
        name: state.name,
        cursor_id: state.cursorId,
      }));
    };
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (_) { return; }
      if (msg.type === "error") {
        setStatus(msg.message || msg.error, false);
        global.AmmoCodeEditor?.toast?.(msg.message || msg.error, false);
        disconnect();
        return;
      }
      if (msg.type === "joined") {
        state.connected = true;
        state.peerId = msg.peer_id;
        state.isHost = !!msg.is_host;
        state.roomId = msg.room_id;
        state.sessionProof = msg.session_proof || "";
        state.peers = msg.peers || [];
        global.AmmoCodeScreenShare?.setSessionProof?.(state.sessionProof);
        (msg.chat_log || []).forEach((c) => appendChat(c.name, c.text, c.peer_id === state.peerId));
        setStatus(`Joined · ${state.peers.length} peer(s) · session secured`, true);
        renderPeers();
        global.AmmoCodeEditor?.toast?.("Collab connected (invite + session proof)", true);
        return;
      }
      if (msg.type === "presence" || msg.type === "peer_joined") {
        state.peers = msg.peers || state.peers;
        renderPeers();
        return;
      }
      if (msg.type === "cursor") {
        moveRemoteCursor(msg.peer_id, msg.x, msg.y, msg.line, msg.col);
        return;
      }
      if (msg.type === "chat") {
        const p = state.peers.find((x) => x.peer_id === msg.peer_id);
        appendChat(msg.name || p?.name || "peer", msg.text, msg.peer_id === state.peerId);
        return;
      }
      if (msg.type === "voice_signal") {
        handleVoiceSignal(msg);
        return;
      }
      if (msg.type === "voice_state") {
        const p = state.peers.find((x) => x.peer_id === msg.peer_id);
        if (p) {
          p.muted = msg.muted;
          p.volume = msg.volume;
          renderPeers();
        }
        return;
      }
      if (msg.type === "cursor_persona") {
        const p = state.peers.find((x) => x.peer_id === msg.peer_id);
        if (p) p.cursor_id = msg.cursor_id;
        renderPeers();
        return;
      }
      if (msg.type === "friend_ips") {
        state.friendIps = msg.ips || [];
        return;
      }
      if (msg.type === "screen_share_request" && state.isHost) {
        const from = state.peers.find((x) => x.peer_id === msg.from);
        setStatus(`${from?.name || "Peer"} requests screen share — click 📺 to permit`, true);
        return;
      }
      if (msg.type === "screen_share_granted") {
        if (msg.to === state.peerId) {
          state.screenShareGranted = true;
          global.AmmoCodeScreenShare?.grantReceived?.();
          setStatus("Host permitted screen share", true);
        }
        return;
      }
      if (msg.type === "screen_share_revoked") {
        global.AmmoCodeScreenShare?.revokeReceived?.();
        global.AmmoCodeScreenShare?.hidePreview?.();
        state.screenShareGranted = false;
        return;
      }
      if (msg.type === "screen_share_frame") {
        const p = state.peers.find((x) => x.peer_id === msg.from);
        global.AmmoCodeScreenShare?.showRemoteFrame?.(msg.data, p?.name || msg.from);
        return;
      }
    };
    ws.onclose = () => {
      if (state.connected) setStatus("Disconnected", false);
      state.connected = false;
    };
  }

  function disconnect() {
    state.peerConnections.forEach((pc) => pc.close());
    state.peerConnections.clear();
    state.audioEls.forEach((a) => a.remove());
    state.audioEls.clear();
    if (state.localStream) {
      state.localStream.getTracks().forEach((t) => t.stop());
      state.localStream = null;
    }
    global.AmmoCodeScreenShare?.stopSharing?.();
    global.AmmoCodeScreenShare?.hidePreview?.();
    state.sessionProof = "";
    state.screenShareGranted = false;
    if (state.ws) {
      try { state.ws.close(); } catch (_) {}
      state.ws = null;
    }
    state.connected = false;
    state.peers = [];
    renderPeers();
  }

  async function init() {
    await loadLocal();
    await loadCursors();
    renderCollabPanel();
    bindEditorCursor();
    const params = new URLSearchParams(location.search);
    const inv = params.get("invite");
    if (inv) {
      state.invite = inv;
      if ($("ac-collab-invite")) $("ac-collab-invite").value = inv;
      global.AmmoCodeFlyout?.setActive?.("collab");
      if (params.get("collab") === "1") setTimeout(() => connect(), 400);
    }
  }

  global.AmmoCodeCollab = { init, connect, disconnect, createInvite, state, cursorMeta };
})(typeof globalThis !== "undefined" ? globalThis : window);