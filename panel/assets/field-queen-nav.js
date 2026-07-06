/**
 * Field Queen Nav — all web I/O through Queen Browser. Never a host browser.
 */
(function (global) {
  "use strict";

  const QUEEN_PORT = "9481";
  const PANEL_PORT = "9477";

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function isHostBrowser() {
    if (!pagesRuntime()) return true;
    try {
      return global.self === global.top;
    } catch (_) {
      return true;
    }
  }

  function httpsSecureSuffix() {
    return "&https=1";
  }

  function secureUrl(url, opts) {
    opts = opts || {};
    const u = String(url || "").trim();
    if (!u) return panelBase() + "/field";
    const base = panelBase().replace(/\/$/, "");
    const queen = queenBrowserBase();
    const hs = opts.httpsSecure !== false ? httpsSecureSuffix() : "";
    if (u.includes("/combinatorics") || u.includes("g16-compiler")) {
      return base + "/bookmark-jump/?id=g16-compiler" + hs;
    }
    if (u.includes("/g16-build-output") || u.includes("h7-g16-online")) {
      return base + "/bookmark-jump/?id=h7-g16-online" + hs;
    }
    if (u.includes(":9488") || u.includes("id=h7-training-viewer")) {
      return base + "/bookmark-jump/?id=h7-training-viewer" + hs;
    }
    if (pagesRuntime() && isHostBrowser()) {
      if (u.includes(":9481") || u.includes("/world/")) {
        const launch = u.startsWith("http") ? u : queen.replace(/browser\.html.*/, "") + u.replace(/^\//, "");
        return queen + (queen.includes("?") ? "&" : "?") + "launch=" + encodeURIComponent(launch);
      }
      if (u.includes(":9477")) {
        const tail = u.replace(/^https?:\/\/127\.0\.0\.1:\d+/, "").split("#")[0] || "/";
        if (tail.startsWith("/bookmark-jump")) return base + tail;
        if (tail === "/field" || tail === "/field/") return base + "/desktop/";
        return base + (tail.startsWith("/") ? tail : "/" + tail);
      }
    }
    if (!pagesRuntime()) {
      if (u.includes(":9488")) return "http://127.0.0.1:" + PANEL_PORT + "/bookmark-jump/?id=h7-training-viewer";
      if (u.includes(":9477") && !u.includes("/bookmark-jump")) {
        return "http://127.0.0.1:" + PANEL_PORT + "/bookmark-jump/?to=" + encodeURIComponent(u);
      }
      if (u.includes(":9481") && !u.includes("browser.html")) {
        return "http://127.0.0.1:" + QUEEN_PORT + "/world/browser.html?launch=" + encodeURIComponent(u);
      }
    }
    return u;
  }

  function queenBrowserBase() {
    if (global.H7_QUEEN_LOOPBACK && (global.H7_QUEEN_LOOPBACK.world_ok || global.H7_QUEEN_LOOPBACK.queen)) {
      return global.H7_QUEEN_LOOPBACK.shell || ("http://127.0.0.1:" + QUEEN_PORT + "/world/browser.html");
    }
    if (pagesRuntime()) {
      return (global.HOSTESS7_PAGES_BASE || "/Hostess7") + "/queen/browser.html";
    }
    return "http://127.0.0.1:" + QUEEN_PORT + "/world/browser.html";
  }

  function panelBase() {
    if (pagesRuntime()) return global.HOSTESS7_PAGES_BASE || "/Hostess7";
    return "http://127.0.0.1:" + PANEL_PORT;
  }

  function isPanelUrl(url) {
    const u = String(url || "").trim();
    if (u.startsWith("/")) return true;
    try {
      const p = new URL(u, panelBase());
      return (p.hostname === "127.0.0.1" || p.hostname === "localhost") && p.port === PANEL_PORT;
    } catch {
      return false;
    }
  }

  function isQueenUrl(url) {
    try {
      const p = new URL(String(url || ""), queenBrowserBase());
      return (p.hostname === "127.0.0.1" || p.hostname === "localhost") && p.port === QUEEN_PORT;
    } catch {
      return false;
    }
  }

  function isInternal(url) {
    return isPanelUrl(url) || isQueenUrl(url);
  }

  function resolve(url) {
    const u = secureUrl(String(url || "").trim());
    if (!u) return panelBase() + "/field";
    if (typeof u === "string" && u.startsWith("/")) return panelBase() + u;
    if (typeof u === "string" && isInternal(u)) return u;
    if (typeof u === "string" && pagesRuntime() && (u.includes("/bookmark-jump") || u.startsWith(panelBase()))) {
      return u;
    }
    const raw = String(url || "").trim();
    if (isInternal(raw)) return secureUrl(raw);
    return { shell: queenBrowserBase(), navigate: raw };
  }

  function launch(url, opts) {
    opts = opts || {};
    const r = resolve(url);
    if (typeof r === "string") {
      const app = {
        id: opts.id || "nav",
        name: opts.name || "Program",
        exec: r,
        shell: true,
      };
      if (global.NexusFieldShell?.launch) {
        global.NexusFieldShell.launch(app, opts);
        return app;
      }
      global.location.href = r;
      return app;
    }
    const app = {
      id: opts.id || "queen-browser",
      name: opts.name || "Queen Browser",
      exec: r.shell,
      shell: true,
      queenNavigate: r.navigate,
    };
    if (global.NexusFieldShell?.launch) {
      const win = global.NexusFieldShell.launch(app, opts);
      if (win && r.navigate) {
        global.NexusFieldShell?.queueQueenNavigate?.(win.id, r.navigate);
      }
      return app;
    }
    try {
      global.location.href = r.shell;
    } catch (_) {}
    return app;
  }

  function open(url, opts) {
    return launch(url, opts);
  }

  function isStandaloneQueenApp(app) {
    if (!app) return false;
    if (app.standalone_queen || app.open_via === "api") return true;
    return app.id === "queen-browser" && app.c2_embedded === false;
  }

  function needsEnsureLaunch(app) {
    if (!app) return "";
    if (app.ensure_api) return String(app.ensure_api);
    if (app.native_launch === "field-broadcaster") return "/api/field-broadcaster/launch";
    const exec = String(app.exec || app.url || "");
    if (exec.includes(":9488") || exec.includes("id=h7-training-viewer") || app.id === "hostess7-training-viewer") {
      return "/api/hostess7-training-viewer/ensure";
    }
    return "";
  }

  function ensureProgramLaunch(app) {
    const api = needsEnsureLaunch(app);
    if (!api) return Promise.resolve({ ok: true });
    return fetch(api, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: app.id || "" }),
    })
      .then(function (r) { return r.json(); })
      .catch(function () { return { ok: false }; });
  }

  function openStandalone(app, opts) {
    opts = opts || {};
    const name = (app && app.name) || "Queen Browser";
    const url = (opts.focus_url || app?.exec || queenBrowserBase()).trim();
    if (pagesRuntime()) {
      return fetch("/api/queen-browser/open", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engine: "queen-shell", focus_url: opts.focus_url || "" }),
      })
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          const openUrl = doc.shell_url || queenBrowserBase();
          const features =
            "width=1280,height=840,menubar=no,toolbar=no,location=yes,resizable=yes,scrollbars=yes,status=yes";
          try {
            global.open(openUrl, "QueenBrowser", features);
          } catch (_) {
            global.location.href = openUrl;
          }
          global.FieldHostDesktop?.toast?.("Opened · " + name);
          global.FieldStartbar?.trackRunning?.(app || { id: "queen-browser", name: name });
          return doc;
        })
        .catch(function () {
          try {
            global.open(url, "QueenBrowser", "noopener");
          } catch (_) {
            global.location.href = url;
          }
          return { ok: true, engine: "queen-browser", pages: true, url: url };
        });
    }
    return fetch("/api/queen-browser/open", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts.body || { engine: "queen-shell" }),
    })
      .then(function (r) { return r.json(); })
      .then(function (doc) {
        if (doc && doc.ok !== false) {
          global.FieldHostDesktop?.toast?.("Opened · " + name);
          global.FieldStartbar?.trackRunning?.(app || { id: "queen-browser", name: name });
        } else {
          global.FieldHostDesktop?.toast?.("Queen Browser launch failed");
        }
        return doc;
      })
      .catch(function () {
        global.FieldHostDesktop?.toast?.("Queen Browser launch failed");
        return { ok: false };
      });
  }

  function patchWindowOpen() {
    const orig = global.open;
    global.open = function fieldQueenOpen(url, target, features) {
      if (!url) return null;
      const u = String(url);
      if (isInternal(u) || u.startsWith("/")) {
        launch(u, { newWindow: true });
        return null;
      }
      launch(u, { id: "queen-tab", name: "Queen Browser", newWindow: true });
      return null;
    };
    global.open.__fieldQueenNav = true;
    return orig;
  }

  global.FieldQueenNav = {
    resolve: resolve,
    launch: launch,
    open: open,
    openStandalone: openStandalone,
    isStandaloneQueenApp: isStandaloneQueenApp,
    ensureProgramLaunch: ensureProgramLaunch,
    needsEnsureLaunch: needsEnsureLaunch,
    secureUrl: secureUrl,
    httpsSecureSuffix: httpsSecureSuffix,
    isHostBrowser: isHostBrowser,
    queenBrowserBase: queenBrowserBase,
    panelBase: panelBase,
    isInternal: isInternal,
    pagesRuntime: pagesRuntime,
    patchWindowOpen: patchWindowOpen,
  };

  patchWindowOpen();
})(window);