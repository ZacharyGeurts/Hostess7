/**
 * GitHub Pages — Queen RTX loopback bridge (Field Gecko / queen-browser), QEMU bot status deck.
 * Static Pages HTML is NOT the RTX engine — probe loopback and route to :9481 when live.
 */
(function (global) {
  "use strict";

  const QUEEN_PORT = "9481";
  const PANEL_PORT = "9477";
  const TRAINING_PORT = "9488";

  function pagesRuntime() {
    return (
      document.body?.dataset?.pagesRuntime === "1" ||
      !!global.HOSTESS7_PAGES_BASE
    );
  }

  function loopbackShell() {
    return "http://127.0.0.1:" + QUEEN_PORT + "/world/browser.html";
  }

  function loopbackWorld() {
    return "http://127.0.0.1:" + QUEEN_PORT;
  }

  async function probeLoopback() {
    if (global.H7_QUEEN_LOOPBACK) return global.H7_QUEEN_LOOPBACK;
    const doc = { shell: loopbackShell(), world: loopbackWorld(), rtx: false, panel: false, training: false };
    try {
      const r = await fetch("/api/queen-loopback/probe", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        Object.assign(doc, j);
      }
    } catch (_) {}
    global.H7_QUEEN_LOOPBACK = doc;
    return doc;
  }

  function ensureStatusDeck() {
    if (!pagesRuntime() || document.getElementById("h7-rtx-status-deck")) return;
    if (document.documentElement.dataset.ammoosDesktop === "1") return;
    if (/\/desktop\/?$/.test(global.location.pathname || "")) return;
    const deck = document.createElement("aside");
    deck.id = "h7-rtx-status-deck";
    deck.className = "h7-rtx-status-deck";
    deck.setAttribute("role", "complementary");
    deck.innerHTML =
      '<div class="h7-rtx-status-deck__head">' +
      '<strong>Queen RTX · QEMU secure lane</strong>' +
      '<button type="button" id="h7-rtx-status-refresh" title="Refresh loopback probe">↻</button>' +
      "</div>" +
      '<div class="h7-rtx-status-deck__grid" id="h7-rtx-status-grid"></div>' +
      '<p class="h7-rtx-status-deck__hint" id="h7-rtx-status-hint">' +
      "Pages mirror — live Queen is Field Gecko @ :9481. Start ./nexus.sh panel + Queen world." +
      "</p>";
    const style = document.createElement("style");
    style.textContent =
      ".h7-rtx-status-deck{position:fixed;right:12px;bottom:72px;z-index:99990;width:min(360px,92vw);" +
      "border:1px solid rgba(212,184,106,0.45);border-radius:12px;background:rgba(6,10,18,0.94);" +
      "box-shadow:0 12px 40px rgba(0,0,0,0.55);font:13px system-ui,sans-serif;color:#e8eef8}" +
      ".h7-rtx-status-deck__head{display:flex;align-items:center;justify-content:space-between;gap:8px;" +
      "padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.08);color:#d4b86a}" +
      ".h7-rtx-status-deck__grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px 12px}" +
      ".h7-rtx-chip{padding:8px 10px;border-radius:8px;border:1px solid rgba(96,165,250,0.28);" +
      "background:rgba(12,20,36,0.85);min-height:52px}" +
      ".h7-rtx-chip strong{display:block;font-size:10px;letter-spacing:0.08em;text-transform:uppercase;color:#9cb3d4}" +
      ".h7-rtx-chip em{font-style:normal;font-weight:700;color:#f8fbff}" +
      ".h7-rtx-chip--ok{border-color:rgba(74,222,128,0.45)}.h7-rtx-chip--warn{border-color:rgba(250,204,21,0.45)}" +
      ".h7-rtx-chip--off{opacity:0.55}.h7-rtx-status-deck__hint{margin:0;padding:8px 12px 12px;font-size:11px;color:#9cb3d4;line-height:1.45}";
    document.head.appendChild(style);
    document.body.appendChild(deck);
    document.getElementById("h7-rtx-status-refresh")?.addEventListener("click", function () {
      global.H7_QUEEN_LOOPBACK = null;
      paintStatus();
    });
  }

  async function paintStatus() {
    ensureStatusDeck();
    const grid = document.getElementById("h7-rtx-status-grid");
    const hint = document.getElementById("h7-rtx-status-hint");
    if (!grid) return;
    const lb = await probeLoopback();
    let qemu = {};
    try {
      const r = await fetch("/api/qemu-world-status", { cache: "no-store" });
      if (r.ok) qemu = await r.json();
    } catch (_) {}
    const chips = [
      { id: "queen", label: "Queen :9481", on: lb.world_ok || lb.queen, detail: lb.engine || "offline" },
      { id: "rtx", label: "RTX engine", on: lb.rtx, detail: lb.rtx_binary ? "queen-browser" : "build RTX" },
      { id: "panel", label: "NEXUS :9477", on: lb.panel, detail: lb.panel ? "C2 live" : "start panel" },
      { id: "training", label: "Training :9488", on: lb.training, detail: lb.training ? "viewer up" : "training-room" },
      { id: "qemu", label: "QEMU bots", on: qemu.running || (qemu.completed || 0) > 0, detail: (qemu.completed || 0) + "/" + (qemu.target || "?") },
      { id: "transfer", label: "Secure xfer", on: qemu.running || lb.panel, detail: qemu.running ? "pipeline" : "idle" },
    ];
    grid.innerHTML = chips
      .map(function (c) {
        const cls = c.on ? "h7-rtx-chip--ok" : "h7-rtx-chip--off";
        return (
          '<div class="h7-rtx-chip ' + cls + '" data-chip="' + c.id + '">' +
          "<strong>" + c.label + "</strong><em>" + c.detail + "</em></div>"
        );
      })
      .join("");
    if (hint) {
      if (lb.world_ok || lb.queen) {
        hint.textContent = "Loopback Queen live — opening RTX shell instead of static Pages mirror.";
      } else {
        hint.innerHTML =
          'Static Pages lane. Run <code>./nexus.sh panel</code> + Queen world for RTX browser. ' +
          '<a href="' + (global.HOSTESS7_PAGES_BASE || "/Hostess7") + '/training-room/">Training room</a>';
      }
    }
  }

  function patchQueenNav() {
    if (!global.FieldQueenNav || global.FieldQueenNav.__rtxBridge) return;
    const origBase = global.FieldQueenNav.queenBrowserBase;
    const origOpen = global.FieldQueenNav.openStandalone;
    global.FieldQueenNav.queenBrowserBase = function () {
      if (global.H7_QUEEN_LOOPBACK && (global.H7_QUEEN_LOOPBACK.world_ok || global.H7_QUEEN_LOOPBACK.queen)) {
        return global.H7_QUEEN_LOOPBACK.shell || loopbackShell();
      }
      return origBase();
    };
    global.FieldQueenNav.openStandalone = async function (app, opts) {
      opts = opts || {};
      const lb = await probeLoopback();
      if (lb.world_ok || lb.queen) {
        return fetch("/api/queen-browser/open", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(opts.body || { engine: "queen-rtx" }),
        })
          .then(function (r) { return r.json(); })
          .then(function (doc) {
            const url = doc.shell_url || lb.shell || loopbackShell();
            try {
              global.open(url, "QueenBrowserRTX", "width=1280,height=840,resizable=yes");
            } catch (_) {
              global.location.href = url;
            }
            global.FieldHostDesktop?.toast?.("Queen RTX · " + (doc.engine || "queen-browser"));
            return doc;
          })
          .catch(function () { return origOpen(app, opts); });
      }
      return origOpen(app, opts);
    };
    global.FieldQueenNav.__rtxBridge = true;
  }

  async function boot() {
    if (!pagesRuntime()) return;
    document.documentElement.classList.add("h7-queen-rtx-bridge");
    await probeLoopback();
    paintStatus();
    patchQueenNav();
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", patchQueenNav);
    }
    setInterval(paintStatus, 20000);
  }

  global.Hostess7QueenRtxBridge = { probeLoopback: probeLoopback, loopbackShell: loopbackShell, boot: boot };
  boot();
})(typeof window !== "undefined" ? window : globalThis);