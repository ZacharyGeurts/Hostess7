/**
 * Queen Browser window manager — open all panel programs inside Queen, never raw OS popups.
 */
(function (global) {
  "use strict";

  const QUEEN_BROWSER = "http://127.0.0.1:9481/world/browser.html";
  const PANEL_ORIGIN = location.origin;

  function absUrl(url) {
    const u = String(url || "").trim();
    if (!u) return "";
    if (u.startsWith("http://") || u.startsWith("https://")) return u;
    if (u.startsWith("/")) return `${PANEL_ORIGIN}${u}`;
    return `${PANEL_ORIGIN}/${u}`;
  }

  function inQueenShell() {
    try {
      return window.parent !== window;
    } catch {
      return false;
    }
  }

  function shellPost(action, payload) {
    if (!inQueenShell()) return false;
    try {
      window.parent.postMessage({ type: "queen:shell", action, ...payload }, "*");
      return true;
    } catch {
      return false;
    }
  }

  function desktopPost(action, item) {
    if (!inQueenShell()) return false;
    try {
      window.parent.postMessage({ type: "queen:desktop", action, item }, "*");
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Open a program URL in Queen Browser window manager.
   * @param {string} url
   * @param {{id?:string,name?:string,title?:string,icon?:string,newTab?:boolean}} opts
   */
  function open(url, opts) {
    opts = opts || {};
    const full = absUrl(url);
    if (!full) return null;

    const item = {
      id: opts.id || full,
      name: opts.name || opts.title || "Program",
      url: full,
      icon: opts.icon,
      kind: "program",
      category: opts.category || "Hostess 7",
      queen_browser: true,
    };

    if (shellPost("open_window", { url: full, title: item.name, icon: opts.icon, item })) {
      return { mode: "queen_shell_window", url: full };
    }

    if (opts.newTab && shellPost("new_tab", { url: full })) {
      return { mode: "queen_shell_tab", url: full };
    }

    if (inQueenShell() && global.QueenDesktop?.openWindow) {
      global.QueenDesktop.openWindow(item);
      return { mode: "queen_desktop", url: full };
    }

    const launch = `${QUEEN_BROWSER}?launch=${encodeURIComponent(full)}&title=${encodeURIComponent(item.name)}`;
    const win = window.open(launch, opts.id || "queen-program", "noopener");
    return win ? { mode: "queen_browser_navigate", url: launch } : null;
  }

  global.QueenProgramLaunch = { open, absUrl, QUEEN_BROWSER };
})(window);