/**
 * AmmoCode permitted screen share — collab host grant, GUI capture only (no getDisplayMedia).
 */
(function (global) {
  "use strict";

  const MAX_FPS = 2;
  const TARGET = ".ac-app";

  let active = false;
  let granted = false;
  let sharing = false;
  let timer = null;
  let frameSeq = 0;
  let sessionProof = null;
  let onFrame = null;

  function isActive() {
    return active || sharing || granted;
  }

  function isSanctioned() {
    return isActive();
  }

  function setSessionProof(proof) {
    sessionProof = proof || null;
  }

  function setOnFrame(fn) {
    onFrame = fn;
  }

  async function frameMac(frameId) {
    if (!sessionProof || !global.crypto?.subtle) return "";
    const key = await global.crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(sessionProof),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const msg = new TextEncoder().encode(`frame:${frameId}`);
    const sig = await global.crypto.subtle.sign("HMAC", key, msg);
    return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  }

  async function captureFrame() {
    const cap = global.AmmoCodeScreenshot?.captureElement;
    if (!cap) return null;
    const el = document.querySelector(TARGET);
    const canvas = await cap(el || document.body, { bg: "#010302" });
    return canvas.toDataURL("image/jpeg", 0.72);
  }

  async function startSharing(ws, peerId) {
    if (!ws || sharing) return;
    active = true;
    sharing = true;
    const interval = Math.round(1000 / MAX_FPS);
    timer = setInterval(async () => {
      if (!sharing || ws.readyState !== 1) return;
      try {
        const data = await captureFrame();
        if (!data) return;
        frameSeq += 1;
        const fid = String(frameSeq);
        const mac = await frameMac(fid);
        ws.send(JSON.stringify({
          type: "screen_share_frame",
          frame_id: fid,
          mac,
          data,
        }));
      } catch (_) {}
    }, interval);
  }

  function stopSharing() {
    sharing = false;
    active = false;
    if (timer) clearInterval(timer);
    timer = null;
  }

  function grantReceived() {
    granted = true;
    active = true;
  }

  function revokeReceived() {
    granted = false;
    stopSharing();
  }

  function showRemoteFrame(data, fromName) {
    const img = document.getElementById("ac-screenshare-img");
    const label = document.getElementById("ac-screenshare-label");
    if (img && data) {
      img.src = data;
      img.hidden = false;
    }
    if (label) label.textContent = fromName ? `Viewing ${fromName}` : "Screen share";
    onFrame?.(data, fromName);
  }

  function hidePreview() {
    const img = document.getElementById("ac-screenshare-img");
    if (img) {
      img.hidden = true;
      img.removeAttribute("src");
    }
  }

  global.AmmoCodeScreenShare = {
    isActive,
    isSanctioned,
    setSessionProof,
    setOnFrame,
    startSharing,
    stopSharing,
    grantReceived,
    revokeReceived,
    showRemoteFrame,
    hidePreview,
    captureFrame,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);