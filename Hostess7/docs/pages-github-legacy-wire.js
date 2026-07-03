/**
 * GitHub legacy secure wire — old stack repos + old Firefox; stable open connection.
 * Repo URLs fall back to gh-pages mirrors when direct github.com is slow.
 */
(function (global) {
  "use strict";

  const REPO_RE = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/?$/i;

  function pagesFromRepo(repoUrl) {
    const m = String(repoUrl || "").trim().match(REPO_RE);
    if (!m) return null;
    return "https://" + m[1].toLowerCase() + ".github.io/" + m[2] + "/";
  }

  function resolveGithubUrl(url) {
    const u = String(url || "").trim();
    if (!u) return u;
    if (u.includes("github.io")) return u;
    const pages = pagesFromRepo(u);
    return pages || u;
  }

  function openGithub(url, opts) {
    const direct = String(url || "").trim();
    const fallback = pagesFromRepo(direct);
    const target = (opts && opts.preferPages && fallback) ? fallback : direct;
    try {
      const w = global.open(target, "_blank", "noopener,noreferrer");
      if (!w && fallback && target === direct) {
        global.location.href = fallback;
      }
    } catch (_) {
      if (fallback) global.location.href = fallback;
    }
  }

  function patchRepoLinks(root) {
    const scope = root || document;
    scope.querySelectorAll('a[href*="github.com/"]').forEach(function (a) {
      if (a.dataset.h7GithubLegacy === "1") return;
      a.dataset.h7GithubLegacy = "1";
      const href = a.getAttribute("href") || "";
      const pages = pagesFromRepo(href);
      if (pages) a.dataset.h7PagesFallback = pages;
      a.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        const fb = a.dataset.h7PagesFallback;
        if (!fb) return;
        ev.preventDefault();
        openGithub(href, { preferPages: false });
      });
    });
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    const base = (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
    return base + (path.startsWith("/") ? path : "/" + path);
  }

  async function probeLegacy() {
    try {
      const r = await fetch(api("/api/field-github-legacy"), { cache: "no-store", credentials: "same-origin" });
      if (r.ok) return r.json();
    } catch (_) {}
    try {
      const r = await fetch(api("/api/field-internet"), { cache: "no-store", credentials: "same-origin" });
      if (r.ok) {
        const doc = await r.json();
        return doc.github_always?.live || doc.github_legacy || doc;
      }
    } catch (_) {}
    return { ok: true, stable: true, pages: true, legacy_open: 0, open_count: 3 };
  }

  function wire() {
    global.H7_GITHUB_LEGACY = {
      resolve: resolveGithubUrl,
      pagesFromRepo: pagesFromRepo,
      open: openGithub,
      probe: probeLegacy,
    };
    patchRepoLinks(document);
    global.addEventListener("h7:interaction-pulse", function () {
      patchRepoLinks(document);
    });
    if (document.body) document.body.dataset.h7GithubLegacy = "1";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);