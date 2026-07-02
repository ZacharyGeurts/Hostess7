/**
 * AmmoOS shell context — sovereign right-click in program windows/tabs (not browser default).
 */
(function (global) {
  "use strict";

  const FLAG = "__H7_AMMOOS_CTX_BRIDGE__";

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function bridgeScript() {
    return (
      "(function(){if(window." +
      FLAG +
      ")return;window." +
      FLAG +
      '=1;var QS=document.body&&(document.body.dataset.queenSurface==="browser"||document.body.classList.contains("qw-browser-shell"));document.addEventListener("contextmenu",function(e){if(window.__QUEEN_PAGE_AGENT__)return;if(e.target.closest(".qpa-context-menu,.qps-ctx,.qb-bookmark-flyout,.nfs-desktop-ctx,.nfs-window-ctx,.fsb-ctx"))return;if(QS){if(e.target.closest(".qb-viewport,.qb-frame")||e.target.tagName==="IFRAME")return;if(e.target.closest(".qb-chrome,.qb-tabs,.qb-row--bookmarks,.qb-start-menu,.qb-gate-drawer,.qb-humans-ai")){e.preventDefault();e.stopPropagation();parent.postMessage({type:"nexus:contextmenu",x:e.clientX,y:e.clientY,tag:(e.target.tagName||"").toLowerCase(),href:(e.target.closest("a[href]")||{}).href||"",src:location.href,queenShell:true,zone:"chrome"}, "*");return;}}if(e.target.closest("[data-ctx-native]"))return;e.preventDefault();e.stopPropagation();var link=e.target.closest&&e.target.closest("a[href]");parent.postMessage({type:"nexus:contextmenu",x:e.clientX,y:e.clientY,tag:(e.target.tagName||"").toLowerCase(),href:link?link.href:"",src:location.href,queenShell:QS,zone:"content"}, "*");},true);})();'
    );
  }

  function injectBridge(iframe) {
    if (!iframe) return;
    function run() {
      try {
        const doc = iframe.contentDocument;
        if (!doc || doc.getElementById("h7-ctx-bridge")) return;
        const s = doc.createElement("script");
        s.id = "h7-ctx-bridge";
        s.textContent = bridgeScript();
        (doc.head || doc.documentElement).appendChild(s);
      } catch (_) {
        /* cross-origin — shell overlay only */
      }
    }
    run();
    iframe.addEventListener("load", run);
  }

  function wireAllFrames() {
    document.querySelectorAll(".nfs-win iframe").forEach(injectBridge);
  }

  function iframeToScreen(iframe, x, y) {
    const r = iframe.getBoundingClientRect();
    return {
      x: Math.min(r.left + x, global.innerWidth - 12),
      y: Math.min(r.top + y, global.innerHeight - 12),
    };
  }

  function findWinForSource(source) {
    const frames = document.querySelectorAll(".nfs-win iframe");
    for (let i = 0; i < frames.length; i += 1) {
      try {
        if (frames[i].contentWindow === source) {
          const el = frames[i].closest(".nfs-win");
          return { iframe: frames[i], winId: el ? el.id : null };
        }
      } catch (_) {}
    }
    return { iframe: null, winId: null };
  }

  function ensureMenu() {
    let el = document.getElementById("nfs-window-ctx");
    if (el) return el;
    el = document.createElement("div");
    el.id = "nfs-window-ctx";
    el.className = "nfs-desktop-ctx nfs-window-ctx";
    el.setAttribute("role", "menu");
    el.setAttribute("aria-label", "AmmoOS window menu");
    document.body.appendChild(el);
    document.addEventListener(
      "click",
      function () {
        el.classList.remove("open");
      },
      true
    );
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") el.classList.remove("open");
    });
    return el;
  }

  function openMenu(x, y, items, onPick) {
    const menu = ensureMenu();
    menu.innerHTML = items
      .map(function (it) {
        if (it.sep) return "<hr />";
        return (
          '<button type="button" data-wact="' +
          esc(it.id) +
          '"' +
          (it.danger ? ' class="danger"' : "") +
          (it.disabled ? " disabled" : "") +
          ">" +
          esc(it.label) +
          "</button>"
        );
      })
      .join("");
    menu.style.left = Math.min(x, global.innerWidth - 220) + "px";
    menu.style.top = Math.min(y, global.innerHeight - 320) + "px";
    menu.classList.add("open");
    menu.onclick = function (ev) {
      const btn = ev.target.closest("[data-wact]");
      if (!btn || btn.disabled) return;
      ev.stopPropagation();
      menu.classList.remove("open");
      onPick(btn.dataset.wact);
    };
  }

  function postFrame(iframe, msg) {
    if (!iframe) return;
    try {
      iframe.contentWindow?.postMessage(msg, "*");
    } catch (_) {}
  }

  function openWindowContext(x, y, win, meta, iframe) {
    const shell = global.NexusFieldShell;
    if (!shell) return;
    const name = win?.name || "Program";
    const items = [
      { id: "reload", label: "Reload" },
      { id: "back", label: "Back", disabled: !iframe },
      { id: "forward", label: "Forward", disabled: !iframe },
      { sep: true },
      { id: "focus", label: "Focus window" },
      { id: "minimize", label: "Minimize" },
      { id: "close", label: "Close", danger: true },
      { sep: true },
      { id: "props", label: "Properties" },
      { id: "desktop", label: "Show desktop" },
    ];
    if (meta?.href) {
      items.splice(3, 0, { id: "open-link", label: "Open link" }, { id: "copy-link", label: "Copy link address" });
    }
    if (meta?.queenShell && meta.zone === "chrome") {
      items.unshift(
        { id: "qb-new-tab", label: "New tab" },
        { id: "qb-reload-tab", label: "Reload tab" },
        { id: "qb-inspector", label: "Page inspector" }
      );
    }
    openMenu(x, y, items, function (act) {
      if (!win) return;
      if (act === "reload" && iframe) iframe.src = iframe.src;
      else if (act === "back") postFrame(iframe, { type: "nexus:history", dir: "back" });
      else if (act === "forward") postFrame(iframe, { type: "nexus:history", dir: "forward" });
      else if (act === "focus") shell.focusWindow?.(win.id);
      else if (act === "minimize") shell.minimizeWindow?.(win.id);
      else if (act === "close") shell.closeWindow?.(win.id);
      else if (act === "props") global.FieldHostDesktop?.toast?.(name + " · " + (win.url || ""));
      else if (act === "desktop") shell.showDesktop?.();
      else if (act === "open-link" && meta.href) shell.launch?.({ id: "link", name: "Link", exec: meta.href }, { newWindow: true });
      else if (act === "copy-link" && meta.href && navigator.clipboard) navigator.clipboard.writeText(meta.href).catch(function () {});
      else if (act === "qb-new-tab") postFrame(iframe, { type: "queen:shell", action: "new_tab" });
      else if (act === "qb-reload-tab") postFrame(iframe, { type: "queen:shell", action: "reload" });
      else if (act === "qb-inspector") postFrame(iframe, { type: "queen:shell", action: "inspector" });
    });
  }

  function onIframeMessage(ev, getWindows) {
    const msg = ev.data;
    if (!msg || msg.type !== "nexus:contextmenu") return false;
    const hit = findWinForSource(ev.source);
    const wins = typeof getWindows === "function" ? getWindows() : [];
    const win = hit.winId ? wins.find(function (w) { return w.id === hit.winId; }) : null;
    const coords = hit.iframe ? iframeToScreen(hit.iframe, msg.x, msg.y) : { x: msg.x, y: msg.y };
    if (msg.queenShell && global.QueenBrowserShell?.openShellContext) {
      global.QueenBrowserShell.openShellContext(coords.x, coords.y, msg, hit.iframe);
      return true;
    }
    openWindowContext(coords.x, coords.y, win, msg, hit.iframe);
    return true;
  }

  function wireShellCapture() {
    document.addEventListener(
      "contextmenu",
      function (ev) {
        if (ev.target.closest(".fsb-root, .fsb-ctx, .nfs-desktop-ctx, .nfs-window-ctx, .hd-icon")) return;
        const winEl = ev.target.closest(".nfs-win");
        if (!winEl) return;
        if (ev.target.tagName === "IFRAME") {
          ev.preventDefault();
          const shell = global.NexusFieldShell;
          const win = shell?.getWindow?.(winEl.id);
          openWindowContext(ev.clientX, ev.clientY, win, {}, winEl.querySelector("iframe"));
        }
      },
      true
    );
  }

  function init() {
    wireShellCapture();
    global.FieldShellContext = {
      injectBridge: injectBridge,
      wireAllFrames: wireAllFrames,
      openWindowContext: openWindowContext,
      onIframeMessage: onIframeMessage,
    };
  }

  init();
})(window);