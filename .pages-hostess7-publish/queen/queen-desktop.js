/**
 * Queen classic desktop — AmmoOS vertical icons, in-desktop apps, Ironclad search, Monster path.
 * @g16 5.1.0 · Grok16/field-stack-fabric · queen-desktop.py
 */
(function () {
  "use strict";

  const PIN_KEY = "queen-desktop-pins-v1";
  const state = {
    data: null,
    tasks: [],
    selected: null,
    windows: new Map(),
    activeWin: null,
    searchQ: "",
    tipTarget: null,
  };

  let desktopFocused = true; // Hostess 7 desktop layer focused by default

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function qUrl(p) {
    // Environment aware: Hostess7/queen/ (published) or /world/ (dev)
    if (!p) return p;
    if (/^https?:\/\//i.test(p) || p.startsWith('//') || p.startsWith('data:')) return p;
    const pn = (location.pathname || '');
    const b = pn.includes('/Hostess7/') ? '/Hostess7/queen/' : (pn.includes('/Hostess7/queen/') || pn.includes('/Queen/world/') ? '/Hostess7/queen/' : '');
    let clean = p.replace(/^\//, '');
    clean = clean.replace(/^world\//, '');
    return b + clean;
  }

  function toast(msg) {
    const el = $("qd-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2400);
  }

  function ironcladHitsEl() {
    let el = $("qd-ironclad-hits");
    if (!el) {
      el = document.createElement("div");
      el.id = "qd-ironclad-hits";
      el.className = "qd-ironclad-hits";
      el.setAttribute("role", "listbox");
      $("qd-search-wrap")?.appendChild(el);
    }
    return el;
  }

  function hideIroncladHits() {
    $("qd-ironclad-hits")?.classList.remove("open");
  }

  function showIroncladHits(hits) {
    const el = ironcladHitsEl();
    if (!hits.length) {
      el.innerHTML = '<p class="qd-ironclad-empty">No Ironclad matches</p>';
      el.classList.add("open");
      return;
    }
    el.innerHTML = hits
      .map((hit) => {
        const label = global.IroncladBus?.hitLabel ? global.IroncladBus.hitLabel(hit) : hit.title || hit.label || "result";
        const url = global.IroncladBus?.hitUrl ? global.IroncladBus.hitUrl(hit) : hit.url || hit.exec || "";
        return '<button type="button" class="qd-ironclad-hit" data-url="' + esc(url) + '">' + esc(label) + "</button>";
      })
      .join("");
    el.querySelectorAll(".qd-ironclad-hit").forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = btn.dataset.url;
        hideIroncladHits();
        if (!url) return;
        if (inQueenShell()) shellPost("navigate", url);
        else window.open(url, "_blank", "noopener");
      });
    });
    el.classList.add("open");
  }

  function inQueenShell() {
    try {
      return window.parent !== window;
    } catch {
      return false;
    }
  }

  function shellPost(action, url, extra) {
    if (!inQueenShell()) return false;
    try {
      window.parent.postMessage({ type: "queen:shell", action, url, ...extra }, window.location.origin);
      return true;
    } catch {
      return false;
    }
  }

  function loadLocalPins() {
    try {
      const raw = localStorage.getItem(PIN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveLocalPins(ids) {
    try {
      localStorage.setItem(PIN_KEY, JSON.stringify(ids));
    } catch (_) { /* ignore */ }
  }

  function mergedPrograms() {
    const list = state.data?.classic_programs || [];
    const serverPins = new Set(list.filter((p) => p.pinned).map((p) => p.id));
    const local = loadLocalPins();
    if (local && Array.isArray(local)) {
      local.forEach((id) => serverPins.add(id));
    }
    return list.map((p) => ({ ...p, pinned: serverPins.has(p.id) }));
  }

  function sortPrograms(programs) {
    const pinned = programs.filter((p) => p.pinned);
    const rest = programs.filter((p) => !p.pinned);
    return [...pinned, ...rest];
  }

  function resolveLaunchUrl(item) {
    const url = item.url || item.exec || "";
    if (!url) return "";
    if (url.startsWith("queen://")) return url;
    if (url.startsWith("/")) return `${location.origin}${url}`;
    return url;
  }

  function embedUrl(url, item) {
    if (!url) return url;
    try {
      const u = new URL(url, location.origin);
      if (u.pathname.endsWith("browser.html") || u.pathname.endsWith("/browser.html")) {
        u.searchParams.set("desktop_embed", "1");
        return u.href;
      }
      if (item?.id === "browser") {
        u.searchParams.set("desktop_embed", "1");
        return u.href;
      }
    } catch (_) { /* ignore */ }
    return url;
  }

  function shouldOpenInDesktop(item, url) {
    if (!url) return false;
    if (url.startsWith("queen://")) return false;
    return true;
  }

  function winId(item) {
    return item.id || item.url || item.name || `win-${Date.now()}`;
  }

  function showWindowsLayer(on) {
    const layer = $("qd-windows");
    const root = $("qd-root");
    if (layer) layer.hidden = !on;
    root?.classList.toggle("has-window", !!on && !!state.activeWin);
  }

  function focusWindow(id) {
    state.windows.forEach((w, wid) => {
      const active = wid === id;
      w.el.classList.toggle("active", active);
      w.minimized = false;
    });
    state.activeWin = id;
    desktopFocused = false;
    showWindowsLayer(true);
    renderTasks();
  }

  function minimizeWindow(id) {
    const w = state.windows.get(id);
    if (!w) return;
    w.el.classList.remove("active");
    w.minimized = true;
    const next = [...state.windows.keys()].find((wid) => {
      const entry = state.windows.get(wid);
      return wid !== id && entry && !entry.minimized;
    });
    if (next) {
      focusWindow(next);
    } else {
      state.activeWin = null;
      desktopFocused = true;
      showWindowsLayer(false);
      state.windows.forEach((entry) => {
        entry.el.classList.remove("active");
      });
    }
    renderTasks();
  }

  function closeWindow(id) {
    const w = state.windows.get(id);
    if (!w) return;
    w.el.remove();
    state.windows.delete(id);
    state.tasks = state.tasks.filter((t) => t.winId !== id);
    if (state.activeWin === id) {
      const remaining = [...state.windows.keys()];
      if (remaining.length) focusWindow(remaining[remaining.length - 1]);
      else {
        state.activeWin = null;
        desktopFocused = true;
        showWindowsLayer(false);
      }
    }
    renderTasks();
  }

  function launchQueenBrowserStandalone() {
    // Pop Queen into AmmoOS desktop space as a window (not host browser tab or ugly URL).
    // Uses openWindow so it appears in AmmoOS desktop, taskbar.
    const url = qUrl("browser.html");
    openWindow({ id: "queen", name: "Queen Browser", url: url });
    toast("Queen Browser opened in desktop space");
    return true;
  }

  function openWindow(item) {
    const id = winId(item);
    const existing = state.windows.get(id);
    if (existing) {
      focusWindow(id);
      return;
    }

    const layer = $("qd-windows");
    if (!layer) return;

    let url = resolveLaunchUrl(item);
    url = embedUrl(url, item);

    const win = document.createElement("div");
    win.className = "qd-win active";
    win.dataset.winId = id;
    win.innerHTML =
      `<div class="qd-win-titlebar">` +
      `<span class="qd-win-title">${esc(item.name || "Application")}</span>` +
      `<button type="button" class="qd-win-btn" data-a="min" aria-label="Minimize">_</button>` +
      `<button type="button" class="qd-win-btn" data-a="close" aria-label="Close">×</button>` +
      `</div>` +
      `<div class="qd-win-frame-wrap">` +
      `<iframe class="qd-win-frame" title="${esc(item.name || "App")}" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation"></iframe>` +
      `</div>`;

    const frame = win.querySelector(".qd-win-frame");
    if (frame) frame.src = url;

    win.querySelector('[data-a="min"]')?.addEventListener("click", () => minimizeWindow(id));
    win.querySelector('[data-a="close"]')?.addEventListener("click", () => closeWindow(id));

    state.windows.forEach((entry) => {
      entry.el.classList.remove("active");
    });
    layer.appendChild(win);
    layer.hidden = false;

    const entry = { id, item, el: win, frame, minimized: false };
    state.windows.set(id, entry);
    state.activeWin = id;
    desktopFocused = false;

    if (!state.tasks.find((t) => t.winId === id)) {
      state.tasks.push({ ...item, winId: id });
    }
    $("qd-root")?.classList.add("has-window");
    renderTasks();
    toast("Opened · " + (item.name || ""));

    // clicking the window (even iframe area) focuses it for special key handling
    win.addEventListener('mousedown', () => focusWindow(id));
  }

  async function launch(item, opts) {
    const url = item.url || item.exec || "";
    if (!url) return;

    // Queen Browser opens as window inside AmmoOS desktop space (popped out of host browser)
    if (item.id === "browser" || item.id === "queen" || (item.name || "").toLowerCase().includes("queen")) {
      return launchQueenBrowserStandalone();
    }

    if (globalThis.QueenProgramSurface?.launchProgram && item.id) {
      const out = await globalThis.QueenProgramSurface.launchProgram(item, { ...opts });
      if (out?.ok) {
        if (out.launch_mode === "queen_window") trackTask(item);
        toast("Opened · " + (item.name || ""));
        return;
      }
    }

    if (url.startsWith("queen://")) {
      if (inQueenShell()) {
        if (shellPost("new_tab", url)) {
          trackTask(item);
          toast("Opened · " + (item.name || ""));
        }
      } else {
        toast("Queen protocol · " + (item.name || ""));
      }
      return;
    }

    if (opts?.newTab && inQueenShell()) {
      if (shellPost("new_tab", resolveLaunchUrl(item))) {
        trackTask(item);
        toast("New tab · " + (item.name || ""));
      }
      return;
    }

    if (inQueenShell() || shouldOpenInDesktop(item, url)) {
      openWindow(item);
      return;
    }

    window.location.href = resolveLaunchUrl(item);
  }

  function trackTask(item) {
    if (!item?.id) return;
    if (state.tasks.find((t) => t.id === item.id && !t.winId)) return;
    state.tasks.push(item);
    renderTasks();
  }

  async function togglePin(item) {
    const programs = mergedPrograms();
    const cur = programs.find((p) => p.id === item.id);
    const next = !(cur?.pinned);
    try {
      const r = await fetch("/api/queen-desktop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "toggle_pin", program_id: item.id, pinned: next }),
      });
      const j = await r.json();
      if (j.ok) {
        state.data = j;
      }
    } catch (_) { /* fallback local */ }

    const local = loadLocalPins() || programs.filter((p) => p.pinned).map((p) => p.id);
    const set = new Set(local);
    if (next) set.add(item.id);
    else set.delete(item.id);
    saveLocalPins([...set]);
    renderIcons(desktopSurfacePrograms());
    toast(next ? "Pinned · " + item.name : "Unpinned · " + item.name);
  }

  function iconNode(item) {
    const wrap = document.createElement("div");
    wrap.className = "qd-icon-glyph";
    const ref = `queen-prog-${item.id || ""}`;
    const icon = item.icon_url || item.icon || "";
    // Big & cartoony for the 4 desktop icons (representative emoji)
    if (icon && (icon.length < 3 || /[\u{1F300}-\u{1F9FF}]/u.test(icon) || /^[💻🗑️📁👑]$/u.test(icon))) {
      const span = document.createElement("span");
      span.style.fontSize = "72px";
      span.style.lineHeight = "1";
      span.textContent = icon;
      wrap.appendChild(span);
      return wrap;
    }
    const libUrl = globalThis.QueenIconEngine?.lookupEntry?.(ref)?.icon_url;
    const url = libUrl || icon || globalThis.QueenIconEngine?.programIconUrl?.(item, 96);
    if (url && globalThis.QueenIconEngine?.programIconHtml) {
      wrap.innerHTML = globalThis.QueenIconEngine.programIconHtml({ ...item, id: item.id }, 96);
      return wrap;
    }
    if (url) {
      const img = document.createElement("img");
      img.className = "qd-png-icon";
      img.src = url;
      img.alt = "";
      img.width = 96;
      img.height = 96;
      img.loading = "lazy";
      img.dataset.queenIconRef = ref;
      wrap.appendChild(img);
      return wrap;
    }
    const kind = item.sdf_kind || item.kind || (item.category === "System" ? "folder" : "program");
    if (globalThis.QueenSdfIcons?.mountIcon) {
      globalThis.QueenSdfIcons.mountIcon(wrap, kind, { size: 96 });
    }
    return wrap;
  }

  function showTip(el, text) {
    const tip = $("qd-tip");
    if (!tip || !text) return;
    const rect = el.getBoundingClientRect();
    tip.textContent = text;
    tip.hidden = false;
    const tipW = tip.offsetWidth || 120;
    let left = rect.left + rect.width / 2 - tipW / 2;
    let top = rect.top - tip.offsetHeight - 6;
    if (top < 4) top = rect.bottom + 6;
    left = Math.max(4, Math.min(left, innerWidth - tipW - 4));
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
    state.tipTarget = el;
  }

  function hideTip() {
    const tip = $("qd-tip");
    if (tip) tip.hidden = true;
    state.tipTarget = null;
  }

  function wireTips(container) {
    container.querySelectorAll("[data-qd-tip]").forEach((el) => {
      el.addEventListener("mouseenter", () => showTip(el, el.dataset.qdTip || el.getAttribute("aria-label") || ""));
      el.addEventListener("mouseleave", hideTip);
      el.addEventListener("focus", () => showTip(el, el.dataset.qdTip || el.getAttribute("aria-label") || ""));
      el.addEventListener("blur", hideTip);
    });
  }

  function applySearch(programs) {
    const q = state.searchQ.trim().toLowerCase();
    const grid = $("qd-icons");
    if (!grid) return;
    let firstMatch = null;
    grid.querySelectorAll(".qd-icon").forEach((btn) => {
      const name = (btn.dataset.name || "").toLowerCase();
      const match = !q || name.includes(q);
      btn.classList.toggle("hidden-by-search", !match);
      btn.classList.toggle("match", !!q && match && name.indexOf(q) >= 0);
      if (q && match && !firstMatch) firstMatch = btn;
    });
    if (firstMatch) {
      firstMatch.scrollIntoView({ block: "nearest", behavior: "smooth" });
      firstMatch.classList.add("selected");
      state.selected = programs.find((p) => p.id === firstMatch.dataset.id) || null;
    }
  }

  function desktopSurfacePrograms() {
    if (state.data?.desktop_icons_in_start) return [];
    const list = mergedPrograms();
    const DESKTOP_ONLY = ["computer", "trash", "files", "browser"];
    return list.filter(p => DESKTOP_ONLY.includes(p.id));
  }

  function renderIcons(programs) {
    const grid = $("qd-icons");
    if (!grid) return;

    // hard force 4 big cartoony (100% bigger), no overlap
    grid.innerHTML = "";
    grid.style.display = "flex";
    grid.style.flexDirection = "column";
    grid.style.gap = "8px";
    grid.style.padding = "8px";
    grid.style.alignItems = "flex-start";

    const list = desktopSurfacePrograms();

    list.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "qd-icon pinned";
      btn.dataset.id = item.id;
      btn.dataset.name = item.name;
      btn.style.width = "240px";
      btn.style.minHeight = "220px";
      btn.style.padding = "8px";
      btn.style.border = "1px solid rgba(255,255,255,0.2)";
      btn.style.background = "rgba(0,0,0,0.3)";
      btn.style.color = "#fff";
      btn.style.fontSize = "20px";
      btn.style.textAlign = "center";
      btn.style.display = "flex";
      btn.style.flexDirection = "column";
      btn.style.alignItems = "center";
      btn.style.justifyContent = "center";
      btn.style.cursor = "pointer";

      const glyph = document.createElement("div");
      glyph.style.fontSize = "144px";
      glyph.style.lineHeight = "1";
      glyph.style.marginBottom = "4px";
      glyph.textContent = item.icon_url || "📁";
      btn.appendChild(glyph);

      const label = document.createElement("span");
      label.style.fontSize = "18px";
      label.textContent = item.name;
      btn.appendChild(label);

      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        grid.querySelectorAll(".qd-icon").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        if (item.id === "browser" || item.id === "queen") {
          launchQueenBrowserStandalone(); // internal desktop window (in AmmoOS space, not host browser)
        } else {
          openWindow(item);
        }
      });
      btn.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        if (item.id === "browser" || item.id === "queen") launchQueenBrowserStandalone(); // internal
        else openWindow(item);
      });
      btn.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        const ctx = document.createElement("div");
        ctx.style.cssText = "position:fixed;background:#111;color:#0f0;padding:4px;z-index:9999;border:1px solid #0f0";
        ctx.innerHTML = `<div>Open ${item.name}</div>`;
        ctx.style.left = ev.clientX + "px";
        ctx.style.top = ev.clientY + "px";
        document.body.appendChild(ctx);
        setTimeout(() => ctx.remove(), 1500);
      });
      grid.appendChild(btn);
    });
  }

  function renderTasks() {
    const tray = $("qd-tasks");
    if (!tray) return;
    const rows = [];

    state.windows.forEach((w, id) => {
      const name = w.item?.name || "App";
      const cls = ["qd-task", state.activeWin === id && !w.minimized ? "active" : "", w.minimized ? "minimized" : ""]
        .filter(Boolean)
        .join(" ");
      rows.push(`<button type="button" class="${cls}" data-win="${esc(id)}">${esc(name)}</button>`);
    });

    state.tasks
      .filter((t) => !t.winId && !state.windows.has(t.id))
      .forEach((t) => {
        const isStandalone = !!t.standalone;
        const label = isStandalone ? esc(t.name) + " ↗" : esc(t.name);
        rows.push(`<button type="button" class="qd-task${isStandalone ? " qd-task-standalone" : ""}" data-id="${esc(t.id)}" data-standalone="${isStandalone ? "1" : ""}">${label}</button>`);
      });

    tray.innerHTML = rows.join("");
    tray.querySelectorAll("[data-win]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.win;
        const w = state.windows.get(id);
        if (!w) return;
        if (state.activeWin === id && !w.minimized) minimizeWindow(id);
        else focusWindow(id);
      });
    });
    tray.querySelectorAll("[data-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tid = btn.dataset.id;
        const item = state.tasks.find((x) => x.id === tid);
        if (!item) return;
        if (item.standalone) {
          const ref = item.winRef;
          if (ref && !ref.closed) {
            try { ref.focus(); } catch (_) {}
            toast("Focused Queen Browser");
          } else {
            // reopen
            launchQueenBrowserStandalone();
          }
        } else {
          launch(item);
        }
      });
    });
  }

  function applyWallpaper(prefs) {
    const root = $("qd-root");
    const wall = $("qd-wallpaper");
    const wp = prefs?.wallpaper || "";
    if (!root || !wall) return;
    if (wp) {
      root.classList.add("has-wallpaper");
      wall.style.backgroundImage = `url("${wp}")`;
      wall.dataset.fit = prefs?.wallpaper_fit || "stretch";
      wall.hidden = false;
    } else {
      root.classList.remove("has-wallpaper");
      wall.style.backgroundImage = "";
      wall.hidden = true;
    }
  }

  function renderNetSeal(doc) {
    const el = $("qd-net-seal");
    if (!el) return;
    const nm = doc?.network_metal || {};
    const fw = nm.firmware_witness || {};
    const sb = fw.secure_boot;
    const tpm = fw.tpm ? "TPM" : "no-TPM";
    const sbTxt = sb === true ? "SB" : sb === false ? "!SB" : "SB?";
    el.textContent = `NET·METAL ${sbTxt} · ${tpm}`;
    el.dataset.qdTip = "BIOS witness · firmware layer · no flash";
  }

  function tickClock() {
    const el = $("qd-clock");
    if (!el) return;
    const now = new Date();
    const h = now.getHours();
    const m = String(now.getMinutes()).padStart(2, "0");
    const ap = h >= 12 ? "PM" : "AM";
    el.textContent = `${h % 12 || 12}:${m} ${ap}`;
  }

  function appendDesktopCtxExtras(item) {
    const ctx = document.getElementById("qps-ctx");
    if (!ctx) return;
    const pinned = mergedPrograms().find((p) => p.id === item.id)?.pinned;
    const extra = document.createElement("div");
    extra.className = "qps-ctx-group";
    extra.innerHTML =
      `<span class="qps-ctx-title">Desktop</span>` +
      `<button type="button" data-desk="pin">${pinned ? "Unpin" : "Pin to desktop"}</button>` +
      `<button type="button" data-desk="wall">Set wallpaper…</button>` +
      `<button type="button" data-desk="clearwall">Clear wallpaper</button>`;
    extra.querySelectorAll("[data-desk]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        ctx.classList.remove("open");
        const a = btn.dataset.desk;
        if (a === "pin") togglePin(item);
        else if (a === "wall") {
          const url = prompt("Wallpaper URL or /world/... path", state.data?.wallpaper || "");
          if (url !== null) await setWallpaper(url);
        } else if (a === "clearwall") await setWallpaper("");
      });
    });
    ctx.appendChild(extra);
  }

  function openCtx(x, y, item) {
    if (globalThis.QueenProgramSurface?.openContextMenu) {
      void globalThis.QueenProgramSurface.openContextMenu(x, y, item).then(() => appendDesktopCtxExtras(item));
      return;
    }
    const ctx = $("qd-ctx");
    if (!ctx) return;
    // Rich fallback right-click for published static desktop — link to real full-featured integrated pages
    const isBrowser = item.id === "browser";
    ctx.innerHTML =
      '<button type="button" data-a="open">Open</button>' +
      '<button type="button" data-a="props">Properties…</button>' +
      (isBrowser ? '' :
        '<div class="qps-ctx-group"><span class="qps-ctx-title">Hostess7 Surfaces</span>' +
        '<button type="button" data-a="bench">GitHub Bench</button>' +
        '<button type="button" data-a="demo">Field Demo</button>' +
        '<button type="button" data-a="queen">Queen Browser</button></div>');
    ctx.style.left = Math.min(x, innerWidth - 220) + "px";
    ctx.style.top = Math.min(y, innerHeight - 160) + "px";
    ctx.classList.add("open");
    ctx.onclick = async (ev) => {
      const b = ev.target.closest("[data-a]");
      if (!b) return;
      ctx.classList.remove("open");
      if (b.dataset.a === "open") launch(item);
      else if (b.dataset.a === "props") globalThis.QueenProgramSurface?.showProperties?.(item);
      else if (b.dataset.a === "bench") window.open(qUrl("bench/index.html"), "_blank");
      else if (b.dataset.a === "demo") window.open(qUrl("field-demo.html"), "_blank");  // or /Hostess7/field-demo.html
      else if (b.dataset.a === "queen") launchQueenBrowserStandalone();
    };
  }

  async function setWallpaper(url) {
    try {
      const r = await fetch("/api/queen-desktop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "set_wallpaper", wallpaper: url }),
      });
      const j = await r.json();
      if (j.ok) {
        state.data = j;
        applyWallpaper(j);
        toast(url ? "Wallpaper set" : "Wallpaper cleared");
      }
    } catch {
      toast("Wallpaper failed");
    }
  }

  function openFiles() {
    const files = mergedPrograms().find((p) => p.id === "files") || {
      id: "files",
      name: "Files",
      url: qUrl("queen-files.html"),
    };
    launch(files);
  }

  function openBrowser() {
    const browser = mergedPrograms().find((p) => p.id === "browser") || {
      id: "browser",
      name: "Queen Browser",
      url: qUrl("browser.html"),
    };
    launch(browser);
  }

  async function refresh() {
    try {
      const r = await fetch("/api/queen-desktop", { cache: "no-store" });
      state.data = await r.json();
      applyWallpaper(state.data);
      renderIcons(desktopSurfacePrograms());
      renderNetSeal(state.data);
      document.documentElement.dataset.bootOs = state.data.boot_os ? "1" : "0";
      document.documentElement.dataset.startButton = state.data.start_button || "split_pill";
    } catch {
      // Static published GitHub Pages fallback: only 4 icons on desktop, rest in start. Big cartoony.
      state.data = state.data || {
        classic_programs: [
          { id: "computer", name: "Computer", url: qUrl("queen-files.html"), kind: "system", category: "System", icon_url: "💻", pinned: true },
          { id: "trash", name: "Trash", url: qUrl("queen-files.html?view=trash"), kind: "system", category: "System", icon_url: "🗑️", pinned: true },
          { id: "files", name: "Folder", url: qUrl("queen-files.html"), kind: "folder", category: "OS", icon_url: "📁", pinned: true },
          { id: "browser", name: "Queen", url: qUrl("browser.html"), kind: "program", category: "OS", icon_url: "👑", pinned: true },
        ],
        desktop_icons_in_start: false,
        wallpaper: "",
        boot_os: "linux",
        start_button: "split_pill",
      };
      // Filter to exactly the 4 for desktop
      state.data.classic_programs = state.data.classic_programs.filter(p => ["computer","trash","files","browser"].includes(p.id));
      applyWallpaper(state.data);
      renderIcons(desktopSurfacePrograms());
      renderNetSeal(state.data);
      document.documentElement.dataset.bootOs = state.data.boot_os ? "1" : "0";
      document.documentElement.dataset.startButton = state.data.start_button || "split_pill";
      // static published desktop status matching the ready UI
      const toastEl = $("qd-toast");
      if (toastEl) toastEl.textContent = "AmmoOS desktop ready · click an icon to launch";
      const seal = $("qd-net-seal"); if (seal) seal.textContent = "AMMOOS · 4 ICONS 💻🗑️📁👑 · CLASSIC START";
    }
  }

  function wireChrome() {
    $("qd-taskbar-start")?.addEventListener("click", () => {
      if (inQueenShell()) {
        window.parent.postMessage({ type: "queen:desktop", action: "toggle_start", side: "classic" }, "*");
      } else {
        const menu = $("qd-start-menu");
        if (menu) {
          menu.hidden = !menu.hidden;
          if (!menu.hidden) {
            if (typeof render === 'function') render();
          }
        }
        setTimeout(() => {
          document.addEventListener('click', function closeStart(e) {
            if (!menu.contains(e.target) && e.target.id !== 'qd-taskbar-start') {
              menu.hidden = true;
              document.removeEventListener('click', closeStart);
            }
          }, {once: true});
        }, 10);
      }
    });
    $("qd-quick-files")?.addEventListener("click", () => {
      const files = { id: "files", name: "Folder", url: qUrl("queen-files.html") };
      openWindow(files);
    });
    $("qd-quick-browser")?.addEventListener("click", () => {
      launchQueenBrowserStandalone();
    });
    $("qd-home")?.addEventListener("click", () => {
      const home = global.IroncladBus?.PANEL_ORIGIN ? global.IroncladBus.PANEL_ORIGIN + "/field" : "/Hostess7/field";
      if (inQueenShell()) window.parent.location.href = home;
      else window.location.href = home;
    });

    // kill any background click toggle
    const rootEl = $("qd-root");
    if (rootEl) rootEl.addEventListener('click', (e) => {
      if (e.target.id === 'qd-root' || e.target.classList.contains('qd-work') || e.target.classList.contains('qd-icons')) {
        e.stopPropagation();
        if (!state.activeWin) desktopFocused = true;
      }
    });

    function isSpecialFocused() {
      // Only capture F9-F12 when Hostess 7 desktop, Queen browser, NEXUS C2 or KILROY is focused.
      // Do not interfere with user space / other app windows or host browser.
      if (desktopFocused || !state.activeWin) return true; // main Hostess7 / AmmoOS desktop
      const activeId = (state.activeWin || '').toLowerCase();
      const specials = ['queen', 'nexus-c2', 'nexus', 'kilroy', 'browser'];
      if (specials.some(s => activeId.includes(s))) return true;
      // check focused element is in special layer
      const activeEl = document.activeElement;
      if (activeEl && activeEl.closest) {
        const winEl = activeEl.closest('.qd-win');
        if (winEl) {
          const wid = winEl.dataset.winId || '';
          if (specials.some(s => wid.toLowerCase().includes(s))) return true;
        }
        if (activeEl.closest('#qd-root, .qd-work, .qd-icons')) return true;
      }
      return false;
    }

    // Add focus listener to desktop area to mark as focused when no window active
    const workArea = $('qd-work') || $('qd-root');
    if (workArea) {
      workArea.addEventListener('mousedown', (e) => {
        if (!state.activeWin && (e.target === workArea || e.target.classList.contains('qd-icons') || e.target.classList.contains('qd-work'))) {
          desktopFocused = true;
        }
      });
    }

    // F9-F12 layers/Queen
    document.addEventListener('keydown', function(e) {
      const fkeys = ['F9','F10','F11','F12'];
      if (!fkeys.includes(e.key)) return;
      if (!isSpecialFocused()) {
        return; // let pass to user space / host
      }
      e.preventDefault();
      if (e.key === 'F9') {
        // NEXUS C2 -3 on top - in desktop space
        openWindow({ id: "nexus-c2", name: "NEXUS C2", url: qUrl('queen-nexus-c2.html') });
      } else if (e.key === 'F10') {
        // KILROY -2 on top - as normal blank tab in desktop space
        openWindow({ id: "kilroy", name: "KILROY", url: "about:blank" });
      } else if (e.key === 'F11') {
        // back to AmmoOS main (desktop layer -1)
        showWindowsLayer(false);
        state.activeWin = null;
        desktopFocused = true;
        const root = $('qd-root');
        if (root) root.focus();
        toast('Back to AmmoOS desktop');
      } else if (e.key === 'F12') {
        // open Queen webbrowser in our OS (in desktop space)
        launchQueenBrowserStandalone();
      }
    });

    const search = $("qd-search");
    const sortSel = $("qd-sort");
    search?.addEventListener("input", () => {
      state.searchQ = search.value;
      applySearch(mergedPrograms());
    });
    search?.addEventListener("keydown", async (e) => {
      if (e.key === "Escape") {
        search.value = "";
        state.searchQ = "";
        applySearch(mergedPrograms());
        hideIroncladHits();
        return;
      }
      if (e.key === "Enter") {
        const q = search.value.trim();
        if (q.length >= 2 && global.IroncladBus?.search) {
          try {
            const doc = await global.IroncladBus.search(q, { context: sortSel?.value || "all", limit: 24 });
            showIroncladHits(doc.hits || []);
          } catch (_) {
            toast("Ironclad search unavailable");
          }
          return;
        }
        if (state.selected) launch(state.selected);
      }
    });

    document.addEventListener("click", (ev) => {
      if (!ev.target.closest(".qd-ctx")) $("qd-ctx")?.classList.remove("open");
    });

    tickClock();
    setInterval(tickClock, 15000);
    wireTips(document);
  }

  window.addEventListener("message", (ev) => {
    if (ev.origin !== location.origin && !/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(ev.origin)) return;
    if (ev.data?.type !== "queen:desktop") return;
    if (ev.data.action === "launch_secured") {
      const item = ev.data.item;
      if (item) launch(item, { newTab: true });
    }
    if (ev.data.action === "open_window" && ev.data.item) {
      openWindow(ev.data.item);
    }
  });

  globalThis.QueenDesktop = { refresh, launch, openWindow, closeWindow, toast, openFiles };

  async function boot() {
    await globalThis.QueenIconEngine?.loadLibraryIndex?.();
    wireChrome();
    refresh();
    globalThis.QueenAiSurface?.enrichFromLibrary?.();
  }

  boot();
})();