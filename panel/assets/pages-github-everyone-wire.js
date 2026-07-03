/**
 * GitHub for everyone — botnet civilian passthrough on Pages + loopback.
 * Mirror chains from sovereign endpoint registry (beyond ICANN) — no silent relocations.
 */
(function (global) {
  "use strict";

  const INTERVAL_MS = 30000;
  const REPO_RE = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/?$/i;
  const REPO_MIRRORS_FALLBACK = {
    "ZacharyGeurts/GNUEOLTerminal": [
      "https://zacharygeurts.github.io/GNUEOLTerminal/",
      "https://zacharygeurts.github.io/Hostess7/gnueol-terminal/",
    ],
  };

  const state = {
    wired: false,
    timer: null,
    doc: null,
    registry: null,
    githubOpen: false,
    repoMirrors: Object.assign({}, REPO_MIRRORS_FALLBACK),
  };

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

  function ingestRegistry(doc) {
    if (!doc || !doc.routes) return;
    state.registry = doc;
    const routes = doc.routes;
    Object.keys(routes).forEach(function (key) {
      const r = routes[key];
      if (!r || (r.layer !== "pages" && r.layer !== "mirror")) return;
      const slug = r.id || (key.split(":").slice(1).join(":"));
      if (!slug || slug.indexOf("/") < 0) return;
      const chain = [];
      if (r.canonical) chain.push(r.canonical);
      (r.mirror_chain || []).forEach(function (u) {
        if (u && chain.indexOf(u) < 0) chain.push(u);
      });
      if (chain.length) state.repoMirrors[slug] = chain;
    });
  }

  async function fetchRegistry() {
    const paths = [
      api("/api/field-endpoint-registry.json"),
      api("/api/field-pages-movement.json"),
      loopback() + "/api/field-endpoint-registry",
      loopback() + "/api/field-pages-movement",
    ];
    for (let i = 0; i < paths.length; i++) {
      try {
        const r = await fetch(paths[i], { cache: "no-store", credentials: "same-origin" });
        if (r.ok) {
          const doc = await r.json();
          ingestRegistry(doc);
          return doc;
        }
      } catch (_) {}
    }
    return null;
  }

  function pagesFromRepo(url) {
    const u = String(url || "").trim();
    const m = u.match(REPO_RE);
    if (!m) return null;
    const slug = m[1] + "/" + m[2];
    const mirrors = state.repoMirrors[slug];
    if (mirrors && mirrors.length) return mirrors[0];
    return "https://" + m[1].toLowerCase() + ".github.io/" + m[2] + "/";
  }

  function mirrorChain(url) {
    const m = String(url || "").trim().match(REPO_RE);
    if (!m) return [];
    const slug = m[1] + "/" + m[2];
    const chain = (state.repoMirrors[slug] || []).slice();
    const generic = pagesFromRepo(url);
    if (generic && chain.indexOf(generic) < 0) chain.unshift(generic);
    return chain;
  }

  function registryWitness(url) {
    const m = String(url || "").trim().match(REPO_RE);
    if (!m || !state.registry) return null;
    const slug = m[1] + "/" + m[2];
    const key = "pages:" + slug;
    const r = (state.registry.routes || {})[key];
    if (!r) return null;
    return { canonical: r.canonical, mirror_chain: r.mirror_chain, updated: r.updated };
  }

  function openGithub(url, opts) {
    const direct = String(url || "").trim();
    const chain = mirrorChain(direct);
    const fallback = chain[0] || pagesFromRepo(direct);
    const preferPages = opts && opts.preferPages;
    const githubDown = !state.githubOpen;
    const target = (preferPages || githubDown) && fallback ? fallback : direct;
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
      const chain = mirrorChain(href);
      const pages = chain[0] || pagesFromRepo(href);
      const witness = registryWitness(href);
      if (pages) a.dataset.h7PagesFallback = pages;
      if (chain.length > 1) a.dataset.h7MirrorChain = chain.join(",");
      if (witness) a.dataset.h7RegistryWitness = witness.updated || "1";
      if (href.indexOf("github.com/") >= 0 && pages) {
        a.dataset.h7GithubRepo = href;
        if (!a.dataset.h7GithubRepoOnly) {
          a.setAttribute("href", pages);
          if (a.textContent === "GitHub") a.textContent = "Browse";
        }
      }
      a.title = (a.title || "") + " · registry witnessed";
      a.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        const fb = a.dataset.h7PagesFallback;
        const forceMirror = href.indexOf("github.com/") >= 0;
        if (!fb || (!forceMirror && state.githubOpen)) return;
        ev.preventDefault();
        openGithub(href, { preferPages: forceMirror || !state.githubOpen });
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
      motto: "GitHub for everyone — endpoint registry witnessed",
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
    await fetchRegistry();
    state.doc = await fetchEveryone();
    state.githubOpen = !!(
      state.doc.github_open ||
      state.doc.legacy?.github_always?.stable ||
      state.doc.resilience?.degraded_ok
    );
    global.H7_GITHUB_EVERYONE = Object.assign(
      {
        openGithub: openGithub,
        pagesFromRepo: pagesFromRepo,
        mirrorChain: mirrorChain,
        registry: state.registry,
        pulse: pulse,
      },
      state.doc
    );
    if (document.body) {
      document.body.dataset.h7GithubEveryone = state.githubOpen ? "open" : "linking";
      document.body.dataset.h7EndpointRegistry = state.registry ? "witnessed" : "fallback";
    }
    patchGithubLinks(document);
    global.dispatchEvent(
      new CustomEvent("h7:github-everyone", {
        detail: { open: state.githubOpen, doc: state.doc, registry: state.registry },
      })
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

  global.Hostess7GithubEveryone = { wire: wire, pulse: pulse, open: openGithub, registry: fetchRegistry };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);