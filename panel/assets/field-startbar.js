/**
 * Field Startbar — AmmoOS start button, taskbar, Monster rescue, Ironclad search.
 * @g16 5.1.0 · Grok16/field-c2-taskbar-plate · field-host-desktop
 */
(function (global) {
  "use strict";

  const LONG_PRESS_MS = 480;
  const QUEEN_ICON = "/assets/ammoos-field-48.png";

  function quickSvg(glyph) {
    const paths = {
      folder:
        '<path fill="currentColor" d="M4 6h6l2 2h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/>',
      terminal:
        '<rect fill="currentColor" x="3" y="5" width="18" height="14" rx="2"/><path stroke="#0a0c10" stroke-width="1.5" fill="none" d="M7 10l3 3-3 3"/><path stroke="#0a0c10" stroke-width="1.5" d="M12 16h5"/>',
      broadcast:
        '<circle fill="currentColor" cx="12" cy="12" r="3"/><path fill="currentColor" d="M6 12a6 6 0 0 1 12 0M4 12a8 8 0 0 1 16 0"/>',
      lock:
        '<path fill="currentColor" d="M8 10V8a4 4 0 1 1 8 0v2h2v10H6V10h2zm2 0h4V8a2 2 0 1 0-4 0v2z"/>',
      browser:
        '<circle fill="currentColor" cx="12" cy="12" r="9" fill-opacity="0.15" stroke="currentColor" stroke-width="1.4"/><path fill="currentColor" d="M8 9h8l-1 6H9l-1-6zm2 2v2h4v-2h-4z"/>',
      audio:
        '<path fill="currentColor" d="M12 4L7 9H4v6h3l5 5V4zm2.5 4.5a4.5 4.5 0 0 1 0 7 1 1 0 1 0 1.4 1.4 6.5 6.5 0 0 0 0-9.8 1 1 0 0 0-1.4 1.4z"/>',
      display:
        '<rect fill="currentColor" x="3" y="5" width="18" height="12" rx="2"/><path fill="#0a0c10" d="M8 21h8v-2H8z"/>',
      bookmark:
        '<path fill="currentColor" d="M6 4h12a2 2 0 0 1 2 2v14l-8-4-8 4V6a2 2 0 0 1 2-2z"/>',
    };
    return '<svg class="fsb-quick-svg" viewBox="0 0 24 24" aria-hidden="true">' + (paths[glyph] || paths.folder) + "</svg>";
  }

  function quickIcon(app) {
    return iconEl(app, true);
  }

  const state = {
    data: null,
    menuOpen: false,
    tasks: [],
    activeTask: null,
    longPressTimer: null,
    ctxTarget: null,
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function iconEl(app, small, size) {
    const QIE = global.QueenIconEngine;
    const px = size || (small ? 20 : 28);
    if (QIE?.programIconHtml) {
      return QIE.programIconHtml(app, px, { small: small || px <= 24, base: QIE.PANEL_ICONS })
        .replace(/qie-prog-icon/g, "qie-prog-icon fsb-app-icon")
        .replace(/qie-live-wrap/g, "qie-live-wrap fsb-icon-live-wrap")
        .replace(/qie-live-ring/g, "qie-live-ring fsb-live-ring");
    }
    const src = app.icon_url || QUEEN_ICON;
    const sz = small ? 20 : 28;
    const live = !!(app && app.live);
    if (live) {
      return (
        '<span class="fsb-icon-live-wrap' +
        (small ? " fsb-icon-live-wrap--sm" : "") +
        '">' +
        '<img src="' +
        esc(src) +
        '" alt="" width="' +
        sz +
        '" height="' +
        sz +
        '" class="fsb-app-icon fsb-app-icon--live' +
        (small ? " fsb-app-icon--sm" : "") +
        '" loading="lazy" decoding="async" />' +
        '<span class="fsb-live-ring" aria-hidden="true"></span>' +
        "</span>"
      );
    }
    return (
      '<img src="' +
      esc(src) +
      '" alt="" width="' +
      sz +
      '" height="' +
      sz +
      '" class="fsb-app-icon' +
      (small ? " fsb-app-icon--sm" : "") +
      '" loading="lazy" decoding="async" />'
    );
  }

  function folderIconEl() {
    const QIE = global.QueenIconEngine;
    if (QIE?.iconUrl) {
      const src = QIE.iconUrl("folder", 20, QIE.PANEL_ICONS);
      return (
        '<img src="' +
        esc(src) +
        '" alt="" width="20" height="20" class="fsb-folder-ico-img qie-file-icon qie-file-icon--folder" loading="lazy" decoding="async" onerror="this.outerHTML=\'<span class=\\\'fsb-folder-ico\\\' aria-hidden=\\\'true\\\'>📁</span>\'" />'
      );
    }
    return '<span class="fsb-folder-ico" aria-hidden="true">📁</span>';
  }

  function launchApp(app) {
    if (!app) return;
    const exec = app.exec || app.url;
    if (!exec) return;
    if (global.NexusFieldShell?.launch && (app.shell || exec.includes("embed=1") || app.view || exec.startsWith("/"))) {
      global.NexusFieldShell.launch(app);
      return;
    }
    global.FieldHostDesktop?.trackRunning?.(app);
    if (/^https?:\/\//i.test(exec)) {
      if (global.FieldQueenNav?.launch) {
        global.FieldQueenNav.launch(exec, { id: app.id, name: app.name });
        return;
      }
      if (global.NexusFieldShell?.launch) {
        global.NexusFieldShell.launch(app);
        return;
      }
      return;
    }
    if (exec.startsWith("/")) {
      if (global.NexusFieldShell?.launch) {
        global.NexusFieldShell.launch(app);
        return;
      }
      global.location.href = exec;
      return;
    }
    global.FieldHostDesktop?.toast?.("Launch: " + (app.name || exec));
  }

  function closeCtx() {
    const ctx = document.getElementById("fsb-ctx");
    if (ctx) ctx.classList.remove("open");
    state.ctxTarget = null;
  }

  function openCtx(x, y, items, target) {
    const ctx = document.getElementById("fsb-ctx");
    if (!ctx) return;
    state.ctxTarget = target;
    ctx.innerHTML = items
      .map(function (it) {
        return (
          '<button type="button" data-action="' +
          esc(it.action) +
          '"' +
          (it.danger ? ' class="danger"' : "") +
          ">" +
          esc(it.label) +
          "</button>"
        );
      })
      .join("");
    ctx.style.left = Math.min(x, global.innerWidth - 180) + "px";
    ctx.style.top = Math.min(y, global.innerHeight - 120) + "px";
    ctx.classList.add("open");
  }

  function bindLongPress(el, onLong, onShort) {
    let startX = 0;
    let startY = 0;
    function clear() {
      if (state.longPressTimer) {
        clearTimeout(state.longPressTimer);
        state.longPressTimer = null;
      }
    }
    el.addEventListener("pointerdown", function (ev) {
      startX = ev.clientX;
      startY = ev.clientY;
      clear();
      state.longPressTimer = setTimeout(function () {
        state.longPressTimer = null;
        onLong(ev);
      }, state.data?.startbar?.long_press_ms || LONG_PRESS_MS);
    });
    el.addEventListener("pointerup", function (ev) {
      if (state.longPressTimer) {
        clear();
        const dx = Math.abs(ev.clientX - startX);
        const dy = Math.abs(ev.clientY - startY);
        if (dx < 12 && dy < 12) onShort(ev);
      }
    });
    el.addEventListener("pointercancel", clear);
    el.addEventListener("pointerleave", clear);
  }

  function toggleMenu(force) {
    const menu = document.getElementById("fsb-menu");
    const start = document.getElementById("fsb-start");
    if (!menu || !start) return;
    state.menuOpen = force !== undefined ? force : !state.menuOpen;
    menu.classList.toggle("open", state.menuOpen);
    menu.setAttribute("aria-hidden", state.menuOpen ? "false" : "true");
    start.setAttribute("aria-expanded", state.menuOpen ? "true" : "false");
    if (state.menuOpen) {
      const search = document.getElementById("fsb-search");
      if (search) setTimeout(function () { search.focus(); }, 80);
    }
  }

  function usesFlyoutMenu(m) {
    return !!(m && (m.flyout || m.layout === "flyout" || (m.style === "nexus_c2" && !m.tree)));
  }

  function renderMenuItems(apps, filter, iconSize) {
    const q = (filter || "").trim().toLowerCase();
    const list = (apps || []).filter(function (a) {
      if (!q) return true;
      return (a.name || "").toLowerCase().includes(q) || (a.category || "").toLowerCase().includes(q);
    });
    const flyout = iconSize && iconSize >= 36;
    return list
      .map(function (app) {
        return (
          '<button type="button" class="fsb-menu-item' +
          (flyout ? " fsb-menu-item--flyout" : "") +
          '" data-app-id="' +
          esc(app.id) +
          '" title="' +
          esc((app.name || "") + (app.category ? " · " + app.category : "")) +
          '">' +
          iconEl(app, false, iconSize || 32) +
          "<span>" +
          esc(app.name) +
          "</span></button>"
        );
      })
      .join("");
  }

  function renderFlyoutSections(m) {
    const cats = m.category_order || Object.keys(m.categories || {});
    const groups = m.categories || {};
    const host = m.host_categories || {};
    let html = '<div class="fsb-flyout-sections">';
    cats.forEach(function (cat) {
      const items = groups[cat];
      if (!items || !items.length) return;
      const label = cat.replace(/^NEXUS · /, "").replace(/^AmmoOS · /, "");
      html +=
        '<section class="fsb-flyout-section">' +
        '<div class="fsb-flyout-section-label">' + esc(label) + "</div>" +
        '<div class="fsb-menu-grid fsb-menu-grid--flyout">' +
        renderMenuItems(items, "", 40) +
        "</div></section>";
    });
    const hostKeys = Object.keys(host).sort();
    if (hostKeys.length) {
      html += '<section class="fsb-flyout-section fsb-flyout-section--host">';
      html += '<div class="fsb-flyout-section-label">Host programs</div>';
      hostKeys.forEach(function (cat) {
        html +=
          '<div class="fsb-flyout-sub">' + esc(cat.replace(/^Host · /, "")) +
          '<div class="fsb-menu-grid fsb-menu-grid--flyout">' +
          renderMenuItems(host[cat], "", 40) +
          "</div></div>";
      });
      html += "</section>";
    }
    html += "</div>";
    return html;
  }

  function renderTreeSections(m, apps) {
    const cats = m.category_order || Object.keys(m.categories || {});
    const groups = m.categories || {};
    const host = m.host_categories || {};
    const collapsed = state.data?.startbar?.start_menu_collapsed !== false;
    let html = '<div class="fsb-menu-tree">';
    cats.forEach(function (cat) {
      const items = groups[cat];
      if (!items || !items.length) return;
      const label = cat.replace(/^NEXUS · /, "").replace(/^AmmoOS · /, "");
      html +=
        '<details class="fsb-tree-branch fsb-tree-folder"' + (collapsed ? "" : " open") + ">" +
        '<summary class="fsb-tree-label">' + folderIconEl() +
        esc(label) + ' <span class="fsb-tree-count">' + items.length + "</span></summary>" +
        '<div class="fsb-menu-grid fsb-menu-grid--section">' + renderMenuItems(items) + "</div></details>";
    });
    const hostKeys = Object.keys(host).sort();
    if (hostKeys.length) {
      html += '<details class="fsb-tree-branch fsb-tree-branch--host"><summary class="fsb-tree-label">Host programs</summary>';
      hostKeys.forEach(function (cat) {
        html += '<div class="fsb-menu-sub">' + esc(cat.replace(/^Host · /, "")) +
          '<div class="fsb-menu-grid fsb-menu-grid--section">' + renderMenuItems(host[cat]) + "</div></div>";
      });
      html += "</details>";
    }
    html += "</div>";
    return html;
  }

  function renderNexusSections(apps) {
    const groups = {};
    (apps || []).forEach(function (a) {
      const cat = a.category || "Other";
      if (!cat.startsWith("NEXUS")) return;
      groups[cat] = groups[cat] || [];
      groups[cat].push(a);
    });
    const order = (state.data && state.data.menu && state.data.menu.category_order) || [];
    const cats = order.filter(function (c) { return groups[c]; }).concat(
      Object.keys(groups).filter(function (c) { return order.indexOf(c) < 0; }).sort()
    );
    if (!cats.length) return "";
    let html = "";
    cats.forEach(function (cat) {
      html +=
        '<div class="fsb-menu-section"><div class="fsb-menu-section-label">' +
        esc(cat.replace("NEXUS · ", "")) +
        "</div>" +
        '<div class="fsb-menu-grid fsb-menu-grid--section">' +
        renderMenuItems(groups[cat]) +
        "</div></div>";
    });
    return html;
  }

  function renderMenu(data) {
    const menu = document.getElementById("fsb-menu");
    if (!menu || !data) return;
    const m = data.menu || {};
    const apps = data.programs || [];
    const pinned = m.pinned || m.favorites || m.dock_pinned || [];
    const theme = data.theme || "ammo-field";

    let body = "";
    if (usesFlyoutMenu(m)) {
      if (pinned.length) {
        body +=
          '<div class="fsb-menu-pinned-label">Pinned</div>' +
          '<div class="fsb-menu-grid fsb-menu-grid--flyout fsb-menu-grid--pinned" id="fsb-pinned">' +
          renderMenuItems(pinned, "", 40) +
          "</div>";
      }
      body += renderFlyoutSections(m);
      menu.classList.add("fsb-menu--flyout");
      menu.innerHTML =
        '<div class="fsb-menu-head fsb-menu-head--c2">' +
        '<span class="fsb-menu-brand">' + esc(state.data?.product || "AmmoOS") + " C2</span>" +
        (m.search !== false
          ? '<input type="search" class="fsb-search" id="fsb-search" placeholder="Search programs…" autocomplete="off" />'
          : "") +
        "</div>" +
        '<div class="fsb-menu-body fsb-menu-body--flyout">' + body + "</div>" +
        '<div class="fsb-menu-foot" id="fsb-power">' +
        (m.power || []).map(function (p) {
          return '<button type="button" class="fsb-power-btn' + (p.danger ? " danger" : "") +
            '" data-power="' + esc(p.action || p.id) + '"' +
            (p.exec ? ' data-exec="' + esc(p.exec) + '"' : "") + ">" + esc(p.label) + "</button>";
        }).join("") +
        "</div>";
      const search = document.getElementById("fsb-search");
      if (search) {
        search.addEventListener("input", function () {
          const q = search.value.trim().toLowerCase();
          document.querySelectorAll(".fsb-menu-body--flyout .fsb-menu-item").forEach(function (btn) {
            const name = (btn.textContent || "").toLowerCase();
            btn.style.display = !q || name.includes(q) ? "" : "none";
          });
          document.querySelectorAll(".fsb-flyout-section").forEach(function (sec) {
            const visible = sec.querySelectorAll('.fsb-menu-item:not([style*="display: none"])').length;
            sec.style.display = visible || !q ? "" : "none";
          });
        });
      }
      bindMenuClicks(data);
      document.querySelectorAll("[data-power]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          toggleMenu(false);
          if (btn.dataset.exec) {
            launchApp({ id: "power-" + btn.dataset.power, name: btn.textContent, exec: btn.dataset.exec });
            return;
          }
          const handler = global.NexusFieldShell?.handlePower || global.FieldHostDesktop?.handlePower;
          if (handler) handler(btn.dataset.power);
        });
      });
      return;
    }
    if (m.tree || m.layout === "tree_sidebar") {
      if (pinned.length) {
        body +=
          '<div class="fsb-menu-pinned-label">Pinned</div>' +
          '<div class="fsb-menu-grid fsb-menu-grid--pinned" id="fsb-pinned">' +
          renderMenuItems(pinned) +
          "</div>";
      }
      body += renderTreeSections(m, apps);
      menu.innerHTML =
        '<div class="fsb-menu-head fsb-menu-head--c2">' +
        '<span class="fsb-menu-brand">' + esc(state.data?.product || "AmmoOS") + " C2</span>" +
        (m.search !== false
          ? '<input type="search" class="fsb-search" id="fsb-search" placeholder="Search programs…" autocomplete="off" />'
          : "") +
        "</div>" +
        '<div class="fsb-menu-body fsb-menu-body--tree">' + body + "</div>" +
        '<div class="fsb-menu-foot" id="fsb-power">' +
        (m.power || []).map(function (p) {
          return '<button type="button" class="fsb-power-btn' + (p.danger ? " danger" : "") +
            '" data-power="' + esc(p.action || p.id) + '"' +
            (p.exec ? ' data-exec="' + esc(p.exec) + '"' : "") + ">" + esc(p.label) + "</button>";
        }).join("") +
        "</div>";
      const search = document.getElementById("fsb-search");
      if (search) {
        search.addEventListener("input", function () {
          const q = search.value.trim().toLowerCase();
          document.querySelectorAll(".fsb-menu-tree .fsb-menu-item").forEach(function (btn) {
            const name = (btn.textContent || "").toLowerCase();
            btn.style.display = !q || name.includes(q) ? "" : "none";
          });
        });
      }
      bindMenuClicks(data);
      document.querySelectorAll("[data-power]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          toggleMenu(false);
          if (btn.dataset.exec) {
            launchApp({ id: "power-" + btn.dataset.power, name: btn.textContent, exec: btn.dataset.exec });
            return;
          }
          const handler = global.NexusFieldShell?.handlePower || global.FieldHostDesktop?.handlePower;
          if (handler) handler(btn.dataset.power);
        });
      });
      return;
    }

    if (theme.startsWith("windows") && pinned.length) {
      body +=
        '<div class="fsb-menu-cats"><span style="font-size:11px;color:var(--fsb-dim)">Pinned</span></div>' +
        '<div class="fsb-menu-grid" id="fsb-pinned">' +
        renderMenuItems(pinned) +
        '</div><hr style="border-color:var(--fsb-edge);margin:8px 0" />';
    }

    const nexusBlock = renderNexusSections(apps);
    const hostApps = apps.filter(function (a) {
      return !(a.category || "").startsWith("NEXUS");
    });
    if (nexusBlock) {
      body += nexusBlock;
      if (hostApps.length) {
        body += '<hr style="border-color:var(--fsb-edge);margin:10px 0" />';
        body += '<div class="fsb-menu-section-label">Host programs</div>';
      }
    }
    if (m.categories && typeof m.categories === "object" && !Array.isArray(m.categories)) {
      const cats = Object.keys(m.categories);
      body += '<div class="fsb-menu-cats" id="fsb-cats">';
      body += '<button type="button" class="fsb-cat-btn active" data-cat="__all__">All</button>';
      cats.forEach(function (c) {
        body += '<button type="button" class="fsb-cat-btn" data-cat="' + esc(c) + '">' + esc(c) + "</button>";
      });
      body += "</div>";
      body += '<div class="fsb-menu-grid" id="fsb-prog-grid">' + renderMenuItems(hostApps.length ? hostApps : apps) + "</div>";
    } else {
      body += '<div class="fsb-menu-grid" id="fsb-prog-grid">' + renderMenuItems(hostApps.length ? hostApps : apps) + "</div>";
    }

    menu.innerHTML =
      '<div class="fsb-menu-head">' +
      (m.search !== false
        ? '<input type="search" class="fsb-search" id="fsb-search" placeholder="Search programs…" autocomplete="off" />'
        : "") +
      "</div>" +
      '<div class="fsb-menu-body">' +
      body +
      "</div>" +
      '<div class="fsb-menu-foot" id="fsb-power">' +
      (m.power || [])
        .map(function (p) {
          return (
            '<button type="button" class="fsb-power-btn' +
            (p.danger ? " danger" : "") +
            '" data-power="' +
            esc(p.action || p.id) +
            '"' +
            (p.exec ? ' data-exec="' + esc(p.exec) + '"' : "") +
            ">" +
            esc(p.label) +
            "</button>"
          );
        })
        .join("") +
      "</div>";

    const search = document.getElementById("fsb-search");
    if (search) {
      search.addEventListener("input", function () {
        const grid = document.getElementById("fsb-prog-grid");
        if (grid) grid.innerHTML = renderMenuItems(apps, search.value);
        bindMenuClicks(data);
      });
    }

    document.querySelectorAll(".fsb-cat-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".fsb-cat-btn").forEach(function (b) {
          b.classList.toggle("active", b === btn);
        });
        const cat = btn.dataset.cat;
        const grid = document.getElementById("fsb-prog-grid");
        if (!grid) return;
        if (cat === "__all__") {
          grid.innerHTML = renderMenuItems(apps);
        } else {
          grid.innerHTML = renderMenuItems((m.categories && m.categories[cat]) || []);
        }
        bindMenuClicks(data);
      });
    });

    bindMenuClicks(data);
    document.querySelectorAll("[data-power]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        toggleMenu(false);
        if (btn.dataset.exec) {
          launchApp({ id: "power-" + btn.dataset.power, name: btn.textContent, exec: btn.dataset.exec });
          return;
        }
        const handler = global.NexusFieldShell?.handlePower || global.FieldHostDesktop?.handlePower;
        if (handler) handler(btn.dataset.power);
      });
    });
  }

  function appIndex(data) {
    const byId = {};
    function add(a) {
      if (a && a.id) byId[a.id] = a;
    }
    (data.programs || []).forEach(add);
    const m = data.menu || {};
    (m.pinned || m.favorites || m.dock_pinned || []).forEach(add);
    (m.programs || []).forEach(add);
    Object.keys(m.categories || {}).forEach(function (cat) {
      (m.categories[cat] || []).forEach(add);
    });
    Object.keys(m.host_categories || {}).forEach(function (cat) {
      (m.host_categories[cat] || []).forEach(add);
    });
    return byId;
  }

  function bindMenuClicks(data) {
    const byId = appIndex(data);
    document.querySelectorAll(".fsb-menu-item[data-app-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        launchApp(byId[btn.dataset.appId]);
        toggleMenu(false);
      });
    });
  }

  function trayIconEl(app) {
    return iconEl(app, true);
  }

  function handleTrayAction(app) {
    if (!app) return;
    if (app.action === "bookmarks") {
      const url = "http://127.0.0.1:9481/world/browser.html";
      if (global.FieldQueenNav?.launch) {
        global.FieldQueenNav.launch(url, { id: "bookmarks", name: "Bookmarks" });
        return;
      }
      fetch("/api/field-c2-bookmarks", { method: "POST", credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (doc) {
          if (doc.ok && global.NexusFieldShell?.launch) {
            global.NexusFieldShell.launch({
              id: "queen-browser",
              name: "Queen Browser",
              exec: url,
              shell: true,
            });
          }
        })
        .catch(function () {
          launchApp({ id: "queen-browser", name: "Queen Browser", exec: url, shell: true });
        });
      return;
    }
    launchApp(app);
  }

  function renderTrayIcons() {
    const tray = document.getElementById("fsb-tray-icons");
    if (!tray) return;
    const icons = state.data?.startbar?.tray_icons || [];
    const byId = appIndex(state.data || {});
    icons.forEach(function (a) {
      if (a && a.id) byId[a.id] = Object.assign({}, byId[a.id] || {}, a);
    });
    tray.innerHTML = icons
      .map(function (app) {
        const row = byId[app.id] || app;
        const tiny = row.tiny ? " fsb-tray-icon--tiny" : "";
        const live = row.live ? " fsb-tray-icon--live" : "";
        return (
          '<button type="button" class="fsb-tray-icon' + tiny + live + '" data-tray-id="' +
          esc(row.id) + '" title="' + esc(row.name) + '">' + trayIconEl(row) + "</button>"
        );
      })
      .join("");
    tray.querySelectorAll(".fsb-tray-icon").forEach(function (btn) {
      btn.addEventListener("click", function () {
        handleTrayAction(byId[btn.dataset.trayId]);
      });
    });
  }

  function renderQuick() {
    const tray = document.getElementById("fsb-quick");
    if (!tray) return;
    const quick = state.data?.startbar?.quick || [];
    tray.innerHTML = quick
      .map(function (app) {
        return (
          '<button type="button" class="fsb-quick-btn" data-quick-id="' +
          esc(app.id) +
          '" title="' +
          esc(app.name) +
          '">' +
          quickIcon(app) +
          "</button>"
        );
      })
      .join("");
    const byId = {};
    quick.forEach(function (a) {
      byId[a.id] = a;
    });
    tray.querySelectorAll(".fsb-quick-btn").forEach(function (btn) {
      const app = byId[btn.dataset.quickId];
      btn.addEventListener("click", function () {
        launchApp(app);
      });
      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        const items = [{ label: "Open", action: "quick-open" }];
        if (app && app.unpinnable) {
          items.push({ label: "Unpin from taskbar", action: "quick-unpin", danger: true });
        } else if (app) {
          items.push({ label: "Unpin from taskbar", action: "quick-unpin", danger: true });
        }
        openCtx(ev.clientX, ev.clientY, items, app);
      });
    });
  }

  function persistQuickUnpin(appId) {
    fetch("/api/field-taskbar-pins", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "unpin", id: appId }),
    })
      .then(function () {
        return fetch("/api/field-host-desktop", { credentials: "same-origin" });
      })
      .then(function (r) { return r.json(); })
      .then(function (doc) {
        if (doc && global.FieldHostDesktop?.applyDesktop) {
          global.FieldHostDesktop.applyDesktop(doc);
        } else if (doc) {
          state.data = doc;
          renderQuick();
        }
      })
      .catch(function () {});
  }

  function renderTasks() {
    const tray = document.getElementById("fsb-tasks");
    if (!tray) return;
    if (state.data?.startbar?.quick_only) {
      tray.innerHTML = "";
      return;
    }
    const tasks = state.tasks.length ? state.tasks : (state.data?.startbar?.show_running === false ? [] : (state.data?.running || []).slice(0, 8));
    tray.innerHTML = tasks
      .map(function (t) {
        const active = state.activeTask === t.id ? " active" : "";
        return (
          '<button type="button" class="fsb-task' +
          active +
          '" data-task-id="' +
          esc(t.id) +
          '">' +
          iconEl(t, true) +
          "<span>" +
          esc(t.name) +
          "</span></button>"
        );
      })
      .join("");

    tray.querySelectorAll(".fsb-task").forEach(function (btn) {
      const task = tasks.find(function (t) {
        return t.id === btn.dataset.taskId;
      });
      bindLongPress(
        btn,
        function (ev) {
          openCtx(ev.clientX, ev.clientY, [
            { label: "Focus", action: "focus" },
            { label: "Pin to taskbar", action: "pin" },
            { label: "Close", action: "close", danger: true },
          ], task);
        },
        function () {
          state.activeTask = btn.dataset.taskId;
          renderTasks();
          if (task && task.shellWin && global.NexusFieldShell?.toggle) {
            global.NexusFieldShell.toggle(task.shellWin);
            return;
          }
          if (task && task.exec && global.NexusFieldShell?.toggle) {
            global.NexusFieldShell.toggle(task.id);
            return;
          }
          if (task && task.exec) launchApp(task);
        }
      );
      btn.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        openCtx(ev.clientX, ev.clientY, [
          { label: "Focus", action: "focus" },
          { label: "Pin to taskbar", action: "pin" },
          { label: "Close", action: "close", danger: true },
        ], task);
      });
    });
  }

  function tickClock() {
    const el = document.getElementById("fsb-clock");
    if (!el) return;
    const now = new Date();
    const h = now.getHours();
    const m = String(now.getMinutes()).padStart(2, "0");
    const ap = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    const ident = state.data?.field_identity;
    if (ident?.znetwork_running && ident?.authority) {
      el.textContent = ident.authority + " · " + h12 + ":" + m + " " + ap;
      el.title = (ident.motto || ident.label) + " — " + now.toLocaleString();
      el.classList.add("fsb-clock--loopback");
    } else {
      el.textContent = h12 + ":" + m + " " + ap;
      el.title = now.toLocaleString();
      el.classList.remove("fsb-clock--loopback");
    }
  }

  function startIcon() {
    const QIE = global.QueenIconEngine;
    if (QIE?.programIconHtml) {
      return (
        QIE.programIconHtml({ id: "ammoos", icon: "queen-prog-ammoos", name: "AmmoOS" }, 28, { small: false, base: QIE.PANEL_ICONS })
          .replace(/qie-prog-icon/g, "qie-prog-icon fsb-start-queen")
      );
    }
    return (
      '<img class="fsb-start-queen" src="' +
      QUEEN_ICON +
      '" alt="" width="28" height="28" decoding="async" title="AmmoOS Start" />' +
      '<span class="fsb-start-label">Start</span>'
    );
  }

  function mount(root, data) {
    state.data = data;
    const theme = data.theme || "ammo-field";
    document.documentElement.dataset.osTheme = theme;

    root.innerHTML =
      '<nav class="fsb-root" aria-label="Field startbar">' +
      '<div class="fsb-start-wrap">' +
      '<button type="button" class="fsb-start" id="fsb-start" aria-label="Start menu" aria-expanded="false" aria-haspopup="true">' +
      startIcon() +
      "</button>" +
      '<div class="fsb-menu fsb-menu--flyout" id="fsb-menu" role="dialog" aria-label="Programs" aria-hidden="true"></div>' +
      "</div>" +
      '<div class="fsb-quick" id="fsb-quick" role="toolbar" aria-label="Quick launch"></div>' +
      '<div class="fsb-tasks" id="fsb-tasks" role="list"></div>' +
      '<div class="fsb-tray">' +
      '<div class="fsb-tray-icons" id="fsb-tray-icons" role="toolbar" aria-label="System tray"></div>' +
      '<button type="button" class="fsb-desktop-tray" id="fsb-desktop-min" title="Show desktop — minimize all windows" aria-label="Minimize desktop">' +
      iconEl({ id: "nexus-c2-desktop", icon: "queen-prog-os", name: "Desktop" }, true, 18) +
      "</button>" +
      '<div class="fsb-clock" id="fsb-clock" role="timer"></div>' +
      '<button type="button" class="fsb-cad" id="fsb-cad" title="Monster rescue (Ctrl+Alt+Del)" aria-label="System rescue">⌁</button>' +
      "</div></nav>" +
      '<div class="fsb-ctx" id="fsb-ctx" role="menu"></div>';

    renderMenu(data);
    renderQuick();
    renderTrayIcons();
    renderTasks();
    tickClock();
    setInterval(tickClock, 15000);

    if (global.FieldIroncladTaskbar?.injectIntoStartbar) {
      global.FieldIroncladTaskbar.injectIntoStartbar();
    }

    document.getElementById("fsb-desktop-min")?.addEventListener("click", function () {
      if (global.NexusFieldShell?.showDesktop) {
        global.NexusFieldShell.showDesktop();
        return;
      }
      global.FieldHostDesktop?.toast?.("Desktop shown");
    });

    document.getElementById("fsb-cad")?.addEventListener("click", function () {
      if (global.FieldMonsterMonitor?.open) global.FieldMonsterMonitor.open();
      else global.FieldHostDesktop?.toast?.("Monster monitor loading…");
    });

    const start = document.getElementById("fsb-start");
    bindLongPress(
      start,
      function (ev) {
        openCtx(ev.clientX, ev.clientY, [
          { label: "Properties", action: "start-props" },
          { label: "Control Panel", action: "control-panel" },
          { label: "Show desktop", action: "show-desktop" },
        ], null);
      },
      function () {
        toggleMenu();
      }
    );
    start.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      openCtx(ev.clientX, ev.clientY, [
        { label: "Properties", action: "start-props" },
        { label: "Control Panel", action: "control-panel" },
        { label: "Display settings", action: "display-settings" },
        { label: "Show desktop", action: "show-desktop" },
      ], null);
    });

    document.getElementById("fsb-ctx")?.addEventListener("click", function (ev) {
      const btn = ev.target.closest("[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      const target = state.ctxTarget;
      closeCtx();
      if (action === "close" && target) {
        state.tasks = state.tasks.filter(function (t) {
          return t.id !== target.id;
        });
        renderTasks();
        return;
      }
      if (action === "pin" && target) {
        if (!state.tasks.find(function (t) { return t.id === target.id; })) {
          state.tasks.push(target);
          try {
            sessionStorage.setItem("fsb-pinned", JSON.stringify(state.tasks));
          } catch (_) {}
        }
        renderTasks();
        return;
      }
      if (action === "focus" && target) {
        state.activeTask = target.id;
        renderTasks();
        if (target.shellWin && global.NexusFieldShell?.focus) global.NexusFieldShell.focus(target.shellWin);
        else if (target.exec) launchApp(target);
        return;
      }
      if (action === "quick-open" && target) {
        launchApp(target);
        return;
      }
      if (action === "quick-unpin" && target && target.id) {
        persistQuickUnpin(target.id);
        return;
      }
      if (action === "start-props") {
        global.NexusFieldShell?.openStartProperties?.();
        return;
      }
      if (action === "display-settings") {
        global.NexusFieldShell?.openDisplaySettings?.();
        return;
      }
      if (action === "show-desktop") {
        global.NexusFieldShell?.showDesktop?.();
        return;
      }
      if (action === "control-panel") {
        launchApp({ id: "nexus-control-panel", name: "Control Panel", exec: "/control-panel" });
        return;
      }
      global.NexusFieldShell?.handlePower?.(action) || global.FieldHostDesktop?.handlePower?.(action);
    });

    document.addEventListener("click", function (ev) {
      if (!ev.target.closest(".fsb-start-wrap")) {
        toggleMenu(false);
      }
      if (!ev.target.closest(".fsb-ctx")) closeCtx();
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        toggleMenu(false);
        closeCtx();
      }
    });

    try {
      const pinned = JSON.parse(sessionStorage.getItem("fsb-pinned") || "[]");
      if (Array.isArray(pinned) && pinned.length) state.tasks = pinned;
      renderTasks();
    } catch (_) {}

    (data.programs || []).forEach(function (app) {
      if (app.live && app.pinned) trackRunning(app);
    });
  }

  function trackRunning(app) {
    if (!app || !app.id) return;
    if (state.tasks.find(function (t) { return t.id === app.id; })) return;
    state.tasks.push(app);
    state.activeTask = app.id;
    try {
      sessionStorage.setItem("fsb-pinned", JSON.stringify(state.tasks.slice(-12)));
    } catch (_) {}
    renderTasks();
  }

  function syncShellTasks(tasks, activeId) {
    state.tasks = tasks || [];
    if (activeId) {
      const hit = state.tasks.find(function (t) {
        return t.shellWin === activeId;
      });
      if (hit) state.activeTask = hit.id;
    }
    renderTasks();
  }

  global.FieldStartbar = {
    mount: mount,
    trackRunning: trackRunning,
    launchApp: launchApp,
    syncShellTasks: syncShellTasks,
  };
})(window);