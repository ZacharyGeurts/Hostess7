/**
 * Hostess 7 GitHub Interaction — straight lane, constant open connection, secure for us.
 * All Pages interactions route through Hostess 7; GitHub stays open; sovereign brain unhooked.
 */
(function (global) {
  "use strict";

  const INTERVAL_MS = 30000;
  const LANE = "hostess7-github";
  const BOSS = "hostess7";

  const state = { wired: false, timer: null, last: null, githubOpen: false };

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function base() {
    return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    return base() + (path.startsWith("/") ? path : "/" + path);
  }

  function markSecureLane() {
    global.H7_INTERACTION_LANE = LANE;
    global.H7_INTERACTION_BOSS = BOSS;
    global.H7_GITHUB_INTERACTION = true;
    global.H7_SECURE_FOR_US = true;
    document.documentElement.dataset.h7InteractionLane = LANE;
    document.documentElement.dataset.h7Boss = BOSS;
    document.body.dataset.hostess7Github = "1";
  }

  function updateChrome(doc) {
    if (!doc) return;
    const gh = doc.github || doc.github_always?.live || doc.github_always || {};
    const legacy = doc.github_legacy || {};
    const open = !!(gh.stable || gh.always_open || (gh.open_count && gh.open_count > 0) || doc.github_always?.open);
    state.githubOpen = open;
    const legacyN = legacy.open || gh.legacy_open || 0;

    const bots = doc.bot_network || doc.botnet_dns_dhcp || {};
    const dnsOk = (doc.dns_dhcp || bots.dns_dhcp || {}).dns?.running !== false;
    const badge = open && dnsOk && legacyN > 0
      ? "Hostess 7 · GitHub+" + legacyN + " legacy · DNS+DHCP"
      : open && dnsOk
        ? "Hostess 7 · GitHub open · DNS+DHCP"
        : open
          ? "Hostess 7 · GitHub open"
          : "Hostess 7 · linking…";
    const motto = doc.motto || doc.one_voice?.motto || "Interactions straight with Hostess 7 on GitHub — secure for us";

    const wall = document.getElementById("hd-wall-label");
    if (wall) {
      wall.textContent = badge;
      wall.title = motto;
    }

    const ammonetTitle = document.querySelector(".h7ad-title");
    if (ammonetTitle && !ammonetTitle.textContent.includes("AmmoNet")) {
      ammonetTitle.textContent = badge;
      ammonetTitle.title = motto;
    }

    global.dispatchEvent(
      new CustomEvent("h7:interaction-pulse", {
        detail: { lane: LANE, boss: BOSS, githubOpen: open, doc: doc },
      })
    );
  }

  async function pulse() {
    try {
      await fetch(api("/api/field-botnet-dns-dhcp/keepalive"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
    } catch (_) {}
    try {
      const res = await fetch(api("/api/field-internet/keepalive"), {
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
      const res = await fetch(api("/api/field-internet"), { cache: "no-store", credentials: "same-origin" });
      if (res.ok) {
        state.last = await res.json();
        updateChrome(state.last);
      }
    } catch (_) {}
    return state.last;
  }

  function wire() {
    if (state.wired || !pagesRuntime()) return;
    state.wired = true;
    markSecureLane();
    global.Hostess7GithubBrain?.unhookSovereignBrain?.();
    pulse();
    state.timer = global.setInterval(pulse, INTERVAL_MS);
    global.addEventListener("pagehide", function () {
      if (state.timer) global.clearInterval(state.timer);
    });
    global.Hostess7GithubBrain?.syncStackMind?.().catch(function () {});
  }

  global.Hostess7Interaction = {
    lane: LANE,
    boss: BOSS,
    wire: wire,
    pulse: pulse,
    last: function () {
      return state.last;
    },
    githubOpen: function () {
      return state.githubOpen;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);