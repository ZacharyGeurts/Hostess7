/**
 * GitHub for everyone — botnet civilian passthrough on Pages + loopback.
 * Repos, raw, API, git — Pages mirror when github.com is slow; H7t for foreign payloads.
 */
(function (global) {
  "use strict";

  const INTERVAL_MS = 30000;
  const REPO_RE = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/?$/i;

  const state = { wired: false, timer: null, doc: null, githubOpen: false };

  function base() {
    return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    return base() + (path.startsWith("/") ? path : "/" + path);
  }

  function loopback() {
    return (global.H7_LOOPBACK_AUTHORITY || "http://127.0.0.1:9477").replace(/\/$/, "");
  }

  function pagesFromRepo(url) {
    const m = String(url || "").trim().match(REPO_RE);
    if (!m) return null;
    return "https://" + m[1].toLowerCase() + ".github.io/" + m[2] + "/";
  }

  function openGithub(url, opts) {
    const direct = String(url || "").trim();
    const fallback = pagesFromRepo(direct);
    const preferPages = opts && opts.preferPages;
    const target = preferPages && fallback ? fallback : direct;
    try {
      const w = global.open(target, "_blank", "noopener,noreferrer");
      if (!w && fallback && target === direct) global.location.href = fallback;
    } catch (_) {
      if (fallback) global.location.href = fallback;
    }
  }

  function patchGithubLinks(root) {
    const scope = root || document;
    scope.querySelectorAll('a[href*="github.com/"], a[href*="github.io/"]').forEach(function (a) {
      if (a.dataset.h7GithubEveryone === "1") return;
      a.dataset.h7GithubEveryone = "1";
      const href = a.getAttribute("href") || "";
      const pages = pagesFromRepo(href);
      if (pages) a.dataset.h7PagesFallback = pages;
      a.title = (a.title || "") + " · GitHub for everyone";
      a.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        const fb = a.dataset.h7PagesFallback;
        if (!fb || state.githubOpen) return;
        ev.preventDefault();
        openGithub(href, { preferPages: false });
      });
    });
  }

  async function fetchEveryone() {
    const paths = [
      api("/api/field-github-everyone"),
      api("/api/field-internet"),
      loopback() + "/api/field-github-everyone",
    ];
    for (let i = 0; i < paths.length; i++) {
      try {
        const r = await fetch(paths[i], { cache: "no-store", credentials: "same-origin" });
        if (r.ok) return r.json();
      } catch (_) {}
    }
    return {
      ok: true,
      for_everyone: { enabled: true, civilian_passthrough: true },
      github_open: true,
      motto: "GitHub for everyone — Pages mirror active",
    };
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
    state.doc = await fetchEveryone();
    state.githubOpen = !!(
      state.doc.github_open ||
      state.doc.legacy?.github_always?.stable ||
      state.doc.resilience?.degraded_ok
    );
    global.H7_GITHUB_EVERYONE = Object.assign(
      { openGithub: openGithub, pagesFromRepo: pagesFromRepo, pulse: pulse },
      state.doc
    );
    if (document.body) {
      document.body.dataset.h7GithubEveryone = state.githubOpen ? "open" : "linking";
    }
    patchGithubLinks(document);
    global.dispatchEvent(
      new CustomEvent("h7:github-everyone", { detail: { open: state.githubOpen, doc: state.doc } })
    );
    return state.doc;
  }

  function wire() {
    if (state.wired) return;
    state.wired = true;
    pulse();
    state.timer = global.setInterval(pulse, INTERVAL_MS);
    global.addEventListener("h7:interaction-pulse", function () {
      patchGithubLinks(document);
    });
    global.addEventListener("pagehide", function () {
      if (state.timer) global.clearInterval(state.timer);
    });
  }

  global.Hostess7GithubEveryone = { wire: wire, pulse: pulse, open: openGithub };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);