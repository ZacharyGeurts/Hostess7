/**
 * Secure bookmark jump — ensure service, then redirect (host browser safe lane).
 */
(function () {
  "use strict";

  const JUMPS = {
    "h7-training-viewer": {
      title: "Training Viewer",
      ensure: "/api/hostess7-training-viewer/ensure",
      target: "http://127.0.0.1:9488/",
      pagesFallback: "/training-room/",
      queenWrap: true,
      httpsSecure: true,
    },
    "cmd-field": { title: "NEXUS Field", ensure: "/api/health", target: "http://127.0.0.1:9477/field", httpsSecure: true },
    "cmd-deck": { title: "Field Command", ensure: "/api/health", target: "http://127.0.0.1:9477/command", httpsSecure: true },
    "cmd-c2": {
      title: "NEXUS C2",
      ensure: "/api/health",
      target: "http://127.0.0.1:9481/world/queen-nexus-c2.html",
      queenWrap: true,
      httpsSecure: true,
    },
    "g16-compiler": {
      title: "Grok16 Compiler",
      ensure: "/api/hostess7/g16-online/ensure",
      target: "http://127.0.0.1:9477/combinatorics",
      pagesFallback: "/g16-build-output/",
      httpsSecure: true,
    },
    "h7-g16-online": {
      title: "Grok16 Build Output",
      ensure: "/api/hostess7/g16-online/ensure",
      target: "http://127.0.0.1:9477/g16-build-output",
      pagesFallback: "/g16-build-output/",
      httpsSecure: true,
    },
    "ammonet": {
      title: "AmmoNet ISP",
      ensure: "/api/health",
      target: "http://127.0.0.1:9477/ammonet-field",
      pagesFallback: "/ammonet/",
      httpsSecure: true,
    },
    "final-internet": {
      title: "Final Internet",
      ensure: "/api/health",
      target: "http://127.0.0.1:9477/ammonet-field",
      pagesFallback: "/final-internet/",
      httpsSecure: true,
    },
  };

  function pagesRuntime() {
    return !!window.HOSTESS7_PAGES_BASE || document.body?.dataset?.pagesRuntime === "1";
  }

  function pagesFallback(path) {
    const base = panelBase();
    return base + (path || "/g16-build-output/");
  }

  function $(id) {
    return document.getElementById(id);
  }

  function panelBase() {
    if (window.HOSTESS7_PAGES_BASE) return String(window.HOSTESS7_PAGES_BASE).replace(/\/$/, "");
    if (document.body?.dataset?.pagesRuntime === "1") {
      const p = location.pathname.match(/^(\/[^/]+)/);
      return p ? p[1] : "/Hostess7";
    }
    const port = document.body?.dataset?.nexusPanelPort || "9477";
    return "http://127.0.0.1:" + port;
  }

  function setStatus(title, msg, showHint) {
    const t = $("fbj-title");
    const s = $("fbj-status");
    const h = $("fbj-hint");
    if (t) t.textContent = title;
    if (s) s.textContent = msg;
    if (h) h.hidden = !showHint;
  }

  function queenLaunch(url) {
    const q = "http://127.0.0.1:9481/world/browser.html?launch=" + encodeURIComponent(url);
    window.location.replace(q);
  }

  async function ensurePath(path) {
    const base = panelBase();
    const root = base || "";
    const r = await fetch(root + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    try {
      return await r.json();
    } catch (_) {
      return { ok: r.ok };
    }
  }

  async function run() {
    const params = new URLSearchParams(location.search);
    const id = params.get("id") || "";
    const to = params.get("to") || "";
    let jump = id ? JUMPS[id] : null;
    let target = to;

    if (jump) {
      target = jump.target;
      const httpsSecure = params.get("https") === "1" || jump.httpsSecure;
      setStatus(jump.title, (httpsSecure ? "HTTPS+Secure · " : "") + "Ensuring " + jump.title + "…");
      try {
        const doc = await ensurePath(jump.ensure);
        if (!doc.ok && jump.ensure !== "/api/health") {
          if (pagesRuntime() && jump.pagesFallback) {
            window.location.replace(pagesFallback(jump.pagesFallback));
            return;
          }
          setStatus("Unavailable", doc.error || "Service did not start", true);
          return;
        }
      } catch (e) {
        if (pagesRuntime() && jump.pagesFallback) {
          window.location.replace(pagesFallback(jump.pagesFallback));
          return;
        }
        setStatus("Panel offline", "NEXUS C2 panel is not running — start ./nexus.sh panel", true);
        return;
      }
      if (jump.queenWrap || target.includes(":9488")) {
        queenLaunch(target);
        return;
      }
      window.location.replace(target);
      return;
    }

    if (!target) {
      setStatus("Missing target", "Use ?id= or ?to= on bookmark-jump", true);
      return;
    }

    setStatus("Jump", "Securing loopback target…");
    if (target.includes(":9488")) {
      try {
        const doc = await ensurePath("/api/hostess7-training-viewer/ensure");
        if (!doc.ok) {
          setStatus("Training Viewer", doc.error || "Could not start :9488", true);
          return;
        }
      } catch (_) {
        setStatus("Panel offline", "Cannot ensure Training Viewer — start panel first", true);
        return;
      }
    } else if (target.includes(":9481")) {
      queenLaunch(target);
      return;
    }

    window.location.replace(target);
  }

  run();
})();