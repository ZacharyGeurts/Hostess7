/**
 * Field Internet Unified — one voice through Hostess 7; GitHub keepalive; all pipes connected.
 */
(function (global) {
  "use strict";

  const INTERVAL_MS = 30000;
  const state = { wired: false, timer: null, last: null };

  function apiUrl(path) {
    if (global.H7Api) return global.H7Api(path);
    return path;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function updateChrome(doc) {
    const title = document.querySelector(".h7ad-title");
    if (!title || !doc) return;
    const gh = doc.github || doc.github_always?.live || {};
    const open = gh.open_count ?? gh.open_count;
    const pipes = doc.pipes || doc.all_pipes || {};
    const connected = pipes.connected_at_once !== false;
    const ghOk = gh.always_open || (gh.open_count && gh.open_count > 0);
    const dnsOk = (doc.bot_network?.dns_dhcp || doc.dns_dhcp || {}).dns?.running !== false;
    const badge = ghOk && connected && dnsOk
      ? " · GitHub open · DNS+DHCP · unified"
      : ghOk && connected
        ? " · GitHub open · unified"
        : ghOk
          ? " · GitHub open"
          : " · linking…";
    title.textContent = "AmmoNet · Layer 0" + badge;
    title.title = doc.motto || doc.one_voice?.motto || "Field Internet Unified — Hostess 7";
  }

  async function pulse() {
    try {
      await fetch(apiUrl("/api/field-botnet-dns-dhcp/keepalive"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
    } catch (_) {}
    try {
      const res = await fetch(apiUrl("/api/field-internet/keepalive"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (res.ok) {
        state.last = await res.json();
        updateChrome(state.last);
        return state.last;
      }
    } catch (_) {}
    try {
      const res = await fetch(apiUrl("/api/field-internet"), { cache: "no-store", credentials: "same-origin" });
      if (res.ok) {
        state.last = await res.json();
        updateChrome(state.last);
      }
    } catch (_) {}
    return state.last;
  }

  function wire() {
    if (state.wired) return;
    state.wired = true;
    pulse();
    state.timer = global.setInterval(pulse, INTERVAL_MS);
    global.addEventListener("pagehide", function () {
      if (state.timer) global.clearInterval(state.timer);
    });
  }

  global.FieldInternetUnified = {
    wire: wire,
    pulse: pulse,
    last: function () {
      return state.last;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);