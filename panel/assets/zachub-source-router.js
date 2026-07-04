/**
 * AmmoDrive source router — true sources only; stale gh-pages/github routes burned on exit.
 */
(function (global) {
  "use strict";

  const OWNER = "ZacharyGeurts";
  const REPO_RE = /^https?:\/\/github\.com\/([^/]+)\/([^/?#]+)\/?/i;
  const PAGES_RE = /^https?:\/\/([^.]+)\.github\.io\/([^/?#]*)/i;

  const STALE_PATH_PREFIXES = [
    "field/",
    "Hostess7/field/",
    "Hostess7/field-desktop/",
    "AmmoOS/field/",
    "command/field/",
    "KILROY/field/",
  ];

  const state = {
    wired: false,
    loopbackLive: false,
    pins: {},
    staleRoutes: {},
    sovereignDesktop: null,
    firedRepos: { field: true },
  };

  function loopback() {
    return (global.H7_LOOPBACK_AUTHORITY || global.ZACHUB_LOOPBACK || "http://127.0.0.1:9477").replace(/\/$/, "");
  }

  function sovereignDesktop() {
    return (
      state.sovereignDesktop ||
      global.ZACHUB_SOVEREIGN_DESKTOP ||
      global.HOSTESS7_SOVEREIGN_DESKTOP ||
      loopback() + "/field"
    );
  }

  function onLoopback() {
    try {
      const host = global.location && global.location.hostname;
      return host === "127.0.0.1" || host === "localhost";
    } catch (_) {
      return false;
    }
  }

  function onPagesRuntime() {
    try {
      const host = global.location && global.location.hostname;
      if (host && host.endsWith(".github.io")) return true;
      if (document.body && document.body.dataset && document.body.dataset.pagesRuntime === "1") return true;
    } catch (_) {}
    return false;
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    const base = (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
    return base + (path.startsWith("/") ? path : "/" + path);
  }

  function slugFromGithub(url) {
    const m = String(url || "").trim().match(REPO_RE);
    if (!m) return null;
    return m[1] + "/" + m[2];
  }

  function defaultPin(slug) {
    const name = slug.split("/", 2)[1];
    if (!name) return null;
    const lower = slug.split("/", 1)[0].toLowerCase();
    return "https://" + lower + ".github.io/" + name + "/";
  }

  function sovereignPin(slug, pin) {
    const name = slug.split("/", 2)[1];
    if (!name) return pin || sovereignDesktop();
    if (state.firedRepos[name]) return sovereignDesktop();
    if (state.loopbackLive || onLoopback()) {
      if (name === "Hostess7") return loopback() + "/field";
      if (name === "command") return loopback() + "/command/";
      if (name === "AmmoOS") return loopback() + "/ammoos/";
      return loopback() + "/" + name.replace(/_/g, "-").toLowerCase() + "/";
    }
    return pin || defaultPin(slug);
  }

  function rewriteTarget(url) {
    const slug = slugFromGithub(url);
    if (!slug) return url;
    if (slug.split("/", 1)[0] !== OWNER) return url;
    const repo = slug.split("/", 2)[1];
    if (state.firedRepos[repo]) return sovereignDesktop();
    const row = state.pins[slug] || {};
    const pin = row.sovereign_url || row.pin_url || row.pages_url || defaultPin(slug);
    if (slug === OWNER + "/field") return sovereignDesktop();
    return sovereignPin(slug, pin);
  }

  function rewritePagesStale(url) {
    const u = String(url || "").trim().replace(/\/$/, "") + "/";
    const hit = state.staleRoutes[u] || state.staleRoutes[u.replace(/\/$/, "")];
    if (hit) return hit;
    const m = u.match(PAGES_RE);
    if (!m) return null;
    const path = (m[2] || "").replace(/\/$/, "");
    for (let i = 0; i < STALE_PATH_PREFIXES.length; i++) {
      if (path === STALE_PATH_PREFIXES[i].replace(/\/$/, "") || path.indexOf(STALE_PATH_PREFIXES[i]) === 0) {
        return sovereignDesktop();
      }
    }
    if (path === "field") return sovereignDesktop();
    if (path === "Hostess7/field" || path === "Hostess7/field-desktop") {
      return state.loopbackLive || onLoopback()
        ? sovereignDesktop()
        : global.HOSTESS7_CANONICAL_DESKTOP || "https://zacharygeurts.github.io/Hostess7/desktop/";
    }
    return null;
  }

  function burnStaleLocation() {
    try {
      const host = global.location.hostname || "";
      const path = (global.location.pathname || "").replace(/^\//, "");
      if (host.indexOf("github.io") < 0) return false;
      for (let i = 0; i < STALE_PATH_PREFIXES.length; i++) {
        const prefix = STALE_PATH_PREFIXES[i];
        if (path === prefix.replace(/\/$/, "") || path.indexOf(prefix) === 0) {
          global.location.replace(onLoopback() ? sovereignDesktop() : (global.HOSTESS7_CANONICAL_DESKTOP || sovereignDesktop()));
          return true;
        }
      }
      if (path === "field") {
        global.location.replace(sovereignDesktop());
        return true;
      }
    } catch (_) {}
    return false;
  }

  function ingestGuard(doc) {
    if (!doc) return;
    state.sovereignDesktop = (doc.sovereign_primary && doc.sovereign_primary.desktop) || state.sovereignDesktop;
    (doc.stale_pages_routes || []).forEach(function (route) {
      state.staleRoutes[String(route).replace(/\/$/, "") + "/"] = sovereignDesktop();
    });
    const fired = doc.fired_repos || (doc.fork_policy && doc.fork_policy.fired_repos);
    if (Array.isArray(fired)) {
      fired.forEach(function (name) {
        state.firedRepos[name] = true;
      });
    }
  }

  function ingestPins(doc) {
    if (!doc) return;
    const rows = doc.favorites || doc.repos || doc.pin_index || [];
    if (Array.isArray(rows)) {
      rows.forEach(function (row) {
        if (!row) return;
        const name = row.repo || row.name;
        if (!name) return;
        const slug = OWNER + "/" + name;
        state.pins[slug] = {
          pin_url: row.sovereign_url || row.pin_url || row.pages || row.pages_url,
          sovereign_url: row.sovereign_url || row.pin_url,
          pages_url: row.pages_url || row.pages,
          github: row.github || row.url || row.repo_url,
          true_source: row.true_source || "sovereign_loopback",
        };
      });
    } else if (typeof rows === "object") {
      Object.keys(rows).forEach(function (name) {
        const row = rows[name];
        if (!row || typeof row !== "object") return;
        const slug = OWNER + "/" + name;
        state.pins[slug] = {
          pin_url: row.sovereign_url || row.pin_url || row.pages || row.pages_url,
          sovereign_url: row.sovereign_url || row.pin_url,
          pages_url: row.pages_url || row.pages,
          github: row.github || row.url,
          true_source: row.true_source || "sovereign_loopback",
        };
      });
    }
    if (doc.pin_index && typeof doc.pin_index === "object") {
      Object.keys(doc.pin_index).forEach(function (slug) {
        state.pins[slug] = doc.pin_index[slug];
      });
    }
  }

  async function fetchJson(paths) {
    for (let i = 0; i < paths.length; i++) {
      try {
        const r = await fetch(paths[i], { cache: "no-store", credentials: "same-origin" });
        if (r.ok) return r.json();
      } catch (_) {}
    }
    return null;
  }

  async function hydrate() {
    const loopPaths = [
      loopback() + "/api/field-zachub-fork-guard",
      loopback() + "/api/field-github-planet-sweep",
    ];
    const pagesPaths = [
      api("/api/field-zachub-fork-guard.json"),
      api("/api/field-github-planet-sweep.json"),
      api("/api/field-endpoint-registry.json"),
    ];
    const guardDoc = await fetchJson(onLoopback() ? loopPaths.concat(pagesPaths) : pagesPaths.concat(loopPaths));
    if (guardDoc) {
      ingestGuard(guardDoc);
      ingestPins(guardDoc);
    }
    const fav = await fetchJson([api("/api/github-favorites.json"), loopback() + "/api/github-favorites"]);
    if (fav) ingestPins(fav);
    try {
      const probe = await fetch(loopback() + "/api/field-zachub-fork-guard", {
        cache: "no-store",
        credentials: "same-origin",
      });
      state.loopbackLive = probe.ok;
    } catch (_) {
      state.loopbackLive = onLoopback();
    }
    return guardDoc;
  }

  function patchLinks(root) {
    const scope = root || document;
    scope.querySelectorAll('a[href*="github.com/"], a[href*="github.io/"]').forEach(function (a) {
      if (a.dataset.zachubRouted === "1") return;
      a.dataset.zachubRouted = "1";
      const href = a.getAttribute("href") || "";
      let target = href;

      const stale = rewritePagesStale(href);
      if (stale) target = stale;

      const slug = slugFromGithub(href);
      if (slug && slug.indexOf(OWNER + "/") === 0) {
        const rewritten = rewriteTarget(href);
        const row = state.pins[slug] || {};
        const pin = row.sovereign_url || row.pin_url || row.pages_url || defaultPin(slug);
        a.dataset.h7CanonicalPin = pin;
        if (a.dataset.h7GithubRepo === "1" || a.hasAttribute("data-h7-github-repo")) {
          a.dataset.h7GithubRepo = href;
          target = sovereignPin(slug, pin);
        } else if (onPagesRuntime() || state.loopbackLive || onLoopback()) {
          target = rewritten;
        }
      }

      if (target !== href) {
        a.setAttribute("href", target);
        a.dataset.zachubFrom = href;
        a.dataset.zachubBurned = "1";
      }
      a.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        const raw = a.dataset.zachubFrom || a.dataset.h7GithubRepo || href;
        const s = slugFromGithub(raw);
        if (!s || s.indexOf(OWNER + "/") !== 0) return;
        const row = state.pins[s] || {};
        const pin = row.sovereign_url || row.pin_url || row.pages_url || defaultPin(s);
        const go = sovereignPin(s, pin);
        if (!go || go === raw) return;
        ev.preventDefault();
        try {
          global.open(go, a.target || "_self", "noopener,noreferrer");
        } catch (_) {
          global.location.href = go;
        }
      });
    });
  }

  async function pulse() {
    burnStaleLocation();
    await hydrate();
    patchLinks(document);
    if (document.body) {
      document.body.dataset.zachubSource = state.loopbackLive ? "sovereign" : "pages_pin";
      document.body.dataset.zachubBurnStale = "1";
    }
    const api = {
      rewriteTarget: rewriteTarget,
      sovereignDesktop: sovereignDesktop,
      pins: state.pins,
      pulse: pulse,
      burnStaleLocation: burnStaleLocation,
    };
    global.AmmoDriveSourceRouter = api;
    global.ZacHubSourceRouter = api;
    global.ZachHubSourceRouter = api;
    return state;
  }

  function wire() {
    if (state.wired) return;
    state.wired = true;
    pulse();
    global.addEventListener("h7:pages-propagate", pulse);
    global.addEventListener("h7:interaction-pulse", function () {
      patchLinks(document);
    });
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) pulse();
    });
  }

  const boot = { wire: wire, pulse: pulse, rewriteTarget: rewriteTarget, burnStaleLocation: burnStaleLocation };
  global.AmmoDriveSourceRouter = boot;
  global.ZacHubSourceRouter = boot;
  global.ZachHubSourceRouter = boot;

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", wire);
    } else {
      wire();
    }
  }
})(typeof window !== "undefined" ? window : globalThis);