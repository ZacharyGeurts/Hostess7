/**
 * Field Shell Dock — AmmoOS program dock, tray, bookmarks flyout.
 * @g16 5.1.0 · Grok16/field-stack-fabric · field-c2-taskbar-plate
 */
(function (global) {
  "use strict";

  const API = "/api/field-shell-dock";

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function dockSvg(glyph) {
    const paths = {
      start:
        '<circle fill="currentColor" cx="12" cy="12" r="9"/><path fill="#0a0c10" d="M8 7h8l-1 10H9L8 7zm2 2h4l.5 6h-5l.5-6z"/>',
      broadcast:
        '<circle fill="currentColor" cx="12" cy="12" r="3"/><path fill="none" stroke="currentColor" stroke-width="1.5" d="M6 12a6 6 0 0 1 12 0M4 12a8 8 0 0 1 16 0"/>',
      lock:
        '<path fill="currentColor" d="M8 10V8a4 4 0 1 1 8 0v2h2v10H6V10h2zm2 0h4V8a2 2 0 1 0-4 0v2z"/>',
      folder:
        '<path fill="currentColor" d="M4 6h6l2 2h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/>',
      terminal:
        '<rect fill="currentColor" x="3" y="5" width="18" height="14" rx="2"/><path stroke="#0a0c10" stroke-width="1.5" fill="none" d="M7 10l3 3-3 3"/><path stroke="#0a0c10" stroke-width="1.5" d="M12 16h5"/>',
      bookmarks:
        '<path fill="currentColor" d="M6 4h12a1 1 0 0 1 1 1v15l-7-4-7 4V5a1 1 0 0 1 1-1z"/>',
    };
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' + (paths[glyph] || paths.folder) + "</svg>";
  }

  function driftClass(ns) {
    const n = Math.abs(Number(ns) || 0);
    if (n === 0) return "fsd-drift";
    if (n < 1000) return "fsd-drift warn";
    return "fsd-drift bad";
  }

  function formatDrift(ns) {
    const n = Number(ns) || 0;
    const sign = n > 0 ? "+" : n < 0 ? "−" : "";
    return sign + Math.abs(n).toLocaleString() + " ns";
  }

  const FieldShellDock = {
    doc: null,
    pollTimer: null,
    leftEl: null,
    rightEl: null,
    activeIcon: null,
    extraTrayHtml: "",
    bookmarksOpen: false,
    timeMenuOpen: false,

    async api(path, opts) {
      const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
      return res.json();
    },

    init(opts) {
      opts = opts || {};
      this.leftEl = document.getElementById(opts.leftId || "fsd-dock-left");
      this.rightEl = document.getElementById(opts.rightId || "fsd-dock-right");
      this.activeIcon = opts.activeIcon || null;
      if (!this.leftEl && !this.rightEl) {
        const legacyLeft = document.getElementById("fg-dock-left");
        const legacyRight = document.getElementById("fg-dock-right");
        if (legacyLeft) {
          legacyLeft.id = "fsd-dock-left";
          legacyLeft.classList.add("fsd-dock-left");
          this.leftEl = legacyLeft;
        }
        if (legacyRight) {
          legacyRight.id = "fsd-dock-right";
          legacyRight.classList.add("fsd-dock-right");
          this.rightEl = legacyRight;
        }
        const dock = document.querySelector(".fg-dock");
        if (dock) dock.classList.add("fsd-dock");
      }
      this.refresh();
      this.schedulePoll(opts.pollMs);
      document.addEventListener("click", this._onDocClick.bind(this));
    },

    setExtraTray(html) {
      this.extraTrayHtml = html || "";
      if (this.doc) this.renderTray(this.doc);
    },

    schedulePoll(ms) {
      if (this.pollTimer) clearInterval(this.pollTimer);
      const interval = ms || this.doc?.poll_ms || 1000;
      this.pollTimer = setInterval(() => this.refresh(), interval);
    },

    async refresh() {
      try {
        const q = this.activeIcon ? "?active_icon=" + encodeURIComponent(this.activeIcon) : "";
        const doc = await this.api(API + q);
        this.render(doc);
      } catch (e) {
        console.error("field-shell-dock", e);
      }
    },

    render(doc) {
      this.doc = doc;
      this.renderDock(doc.dock_icons || []);
      this.renderTray(doc);
    },

    renderDock(icons) {
      if (!this.leftEl) return;
      this.leftEl.innerHTML = (icons || [])
        .map((ic) => {
          const active = ic.active ? " active" : "";
          const badge = ic.badge ? '<span class="fsd-badge">1</span>' : "";
          const exec = ic.exec ? String(ic.exec) : "";
          const click =
            exec && ic.id !== this.activeIcon
              ? ' data-exec="' + esc(exec) + '"'
              : "";
          return (
            '<button type="button" class="fsd-dock-icon' +
            active +
            '" title="' +
            esc(ic.label) +
            '" data-id="' +
            esc(ic.id) +
            '"' +
            click +
            ">" +
            dockSvg(ic.glyph) +
            badge +
            "</button>"
          );
        })
        .join("");
      this.leftEl.querySelectorAll("[data-exec]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const url = btn.getAttribute("data-exec");
          if (url) location.href = url;
        });
      });
    },

    renderTray(doc) {
      if (!this.rightEl) return;
      const sess = doc.session || {};
      const sovereign = doc.sovereign || {};
      const handshake = doc.timeserver_handshake || {};
      const best = handshake.best || {};
      const synced = !!sovereign.all_synced;
      const driftNs = sess.drift_since_session_ns;
      const timeText = doc.time_display?.active || "—";
      const tf = doc.settings?.time_format || "long";
      const formats = doc.time_formats || [];

      const timeOpts = formats
        .map((f) => {
          const on = f.id === tf ? " active" : "";
          return (
            '<button type="button" class="fsd-time-opt' +
            on +
            '" data-tf="' +
            esc(f.id) +
            '">' +
            esc(f.label) +
            "</button>"
          );
        })
        .join("");

      const bookmarks = (doc.bookmarks || [])
        .map((bm) => {
          return (
            '<button type="button" class="fsd-flyout-item" data-url="' +
            esc(bm.url) +
            '">' +
            esc(bm.title) +
            "<small>" +
            esc(bm.url) +
            "</small></button>"
          );
        })
        .join("");

      const method = best.method || "pending";
      const probeCount = handshake.probe_count || 0;

      this.rightEl.innerHTML =
        '<span class="fsd-tray-live' +
        (synced ? " synced" : "") +
        '" title="Sovereign ' +
        (synced ? "synced" : "desync") +
        '"></span>' +
        (this.extraTrayHtml || "") +
        '<span class="' +
        driftClass(driftNs) +
        '" title="Session drift since last handshake sync · step ' +
        esc(formatDrift(sess.drift_step_ns)) +
        '">' +
        esc(formatDrift(driftNs)) +
        "</span>" +
        '<span class="fsd-sovereign-detail" title="' +
        esc(doc.posture || "") +
        '">' +
        esc(method) +
        " · " +
        probeCount +
        " probes</span>" +
        '<div class="fsd-bookmarks-wrap">' +
        '<button type="button" class="fsd-bookmarks-btn" id="fsd-bookmarks-btn" aria-expanded="false">' +
        dockSvg("bookmarks") +
        " Bookmarks</button>" +
        '<div class="fsd-flyout' +
        (this.bookmarksOpen ? " open" : "") +
        '" id="fsd-bookmarks-flyout">' +
        '<div class="fsd-flyout-head">Bookmarks</div>' +
        bookmarks +
        "</div></div>" +
        '<div class="fsd-time-wrap">' +
        '<button type="button" class="fsd-tray-pill clickable" id="fsd-time-btn">' +
        esc(timeText) +
        "</button>" +
        '<div class="fsd-time-menu' +
        (this.timeMenuOpen ? " open" : "") +
        '" id="fsd-time-menu">' +
        timeOpts +
        "</div></div>";

      const bmBtn = document.getElementById("fsd-bookmarks-btn");
      const bmFly = document.getElementById("fsd-bookmarks-flyout");
      if (bmBtn && bmFly) {
        bmBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          this.bookmarksOpen = !this.bookmarksOpen;
          this.timeMenuOpen = false;
          bmFly.classList.toggle("open", this.bookmarksOpen);
          bmBtn.setAttribute("aria-expanded", this.bookmarksOpen ? "true" : "false");
          const menu = document.getElementById("fsd-time-menu");
          if (menu) menu.classList.remove("open");
        });
        bmFly.querySelectorAll("[data-url]").forEach((item) => {
          item.addEventListener("click", () => {
            const url = item.getAttribute("data-url");
            if (url) location.href = url;
            this.bookmarksOpen = false;
            bmFly.classList.remove("open");
          });
        });
      }

      const timeBtn = document.getElementById("fsd-time-btn");
      const timeMenu = document.getElementById("fsd-time-menu");
      if (timeBtn && timeMenu) {
        timeBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          this.timeMenuOpen = !this.timeMenuOpen;
          this.bookmarksOpen = false;
          timeMenu.classList.toggle("open", this.timeMenuOpen);
          if (bmFly) bmFly.classList.remove("open");
        });
        timeMenu.querySelectorAll("[data-tf]").forEach((opt) => {
          opt.addEventListener("click", async () => {
            const fmt = opt.getAttribute("data-tf");
            try {
              const updated = await this.api(API + "/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ time_format: fmt }),
              });
              this.timeMenuOpen = false;
              this.render(updated);
            } catch (e) {
              console.error(e);
            }
          });
        });
      }
    },

    _onDocClick() {
      this.bookmarksOpen = false;
      this.timeMenuOpen = false;
      const fly = document.getElementById("fsd-bookmarks-flyout");
      const menu = document.getElementById("fsd-time-menu");
      if (fly) fly.classList.remove("open");
      if (menu) menu.classList.remove("open");
      const bmBtn = document.getElementById("fsd-bookmarks-btn");
      if (bmBtn) bmBtn.setAttribute("aria-expanded", "false");
    },
  };

  function ensureIroncladTaskbar() {
    if (document.body?.dataset?.ironcladTaskbar === "0") return;
    const onField = (global.location?.pathname || "") === "/field";
    if (!onField && document.hasFocus && !document.hasFocus()) return;
    const scripts = [
      { src: "/assets/ironclad-bus.js?v=1", check: "IroncladBus" },
      { src: "/assets/field-ironclad-taskbar.js?v=1", check: "FieldIroncladTaskbar" },
      { src: "/assets/field-nav-spine.js?v=1", check: "FieldNavSpine" },
    ];
    const css = "/assets/field-ironclad-taskbar.css?v=1";
    if (!document.querySelector('link[href*="field-ironclad-taskbar.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = css;
      document.head.appendChild(link);
    }
    if (!document.querySelector('link[href*="field-nav-spine.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/assets/field-nav-spine.css?v=1";
      document.head.appendChild(link);
    }
    let pending = 0;
    scripts.forEach(function (row) {
      if (global[row.check]) return;
      if (document.querySelector('script[src*="' + row.src.split("?")[0] + '"]')) return;
      pending += 1;
      const s = document.createElement("script");
      s.src = row.src;
      s.defer = true;
      s.onload = function () {
        pending -= 1;
        if (pending <= 0 && global.FieldIroncladTaskbar?.mountStandalone) {
          global.FieldIroncladTaskbar.mountStandalone();
        }
      };
      document.head.appendChild(s);
    });
    if (pending === 0 && global.FieldIroncladTaskbar?.mountStandalone) {
      global.FieldIroncladTaskbar.mountStandalone();
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(ensureIroncladTaskbar, 50);
  });

  global.FieldShellDock = FieldShellDock;
})(typeof window !== "undefined" ? window : globalThis);