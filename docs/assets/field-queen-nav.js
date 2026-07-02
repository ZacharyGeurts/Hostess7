/**
 * Field Queen Nav — all web I/O through Queen Browser inside NEXUS C2. Never the client OS browser.
 */
(function (global) {
  "use strict";

  const QUEEN_PORT = "9481";
  const PANEL_PORT = "9477";

  function queenBrowserBase() {
    return "http://127.0.0.1:" + QUEEN_PORT + "/Hostess7/queen/browser.html";
  }

  function panelBase() {
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
    const u = String(url || "").trim();
    if (!u) return panelBase() + "/field";
    if (u.startsWith("/")) return panelBase() + u;
    if (isInternal(u)) return u;
    return { shell: queenBrowserBase(), navigate: u };
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
    const exec = String(app.exec || app.url || "");
    if (exec.includes(":9488")) return "/api/hostess7-training-viewer/ensure";
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
    return fetch("/api/queen-browser/open", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts.body || {}),
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
    queenBrowserBase: queenBrowserBase,
    panelBase: panelBase,
    isInternal: isInternal,
    patchWindowOpen: patchWindowOpen,
  };

  patchWindowOpen();
})(window);