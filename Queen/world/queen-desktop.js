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

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
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
      if (u.pathname.endsWith("/browser.html") || u.pathname.endsWith("/world/browser.html")) {
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
        showWindowsLayer(false);
      }
    }
    renderTasks();
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

    if (!state.tasks.find((t) => t.winId === id)) {
      state.tasks.push({ ...item, winId: id });
    }
    $("qd-root")?.classList.add("has-window");
    renderTasks();
    toast("Opened · " + (item.name || ""));
  }

  async function launch(item, opts) {
    const url = item.url || item.exec || "";
    if (!url) return;

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
    const libUrl = globalThis.QueenIconEngine?.lookupEntry?.(ref)?.icon_url;
    const url = libUrl || item.icon_url || globalThis.QueenIconEngine?.programIconUrl?.(item, 32);
    if (url && globalThis.QueenIconEngine?.programIconHtml) {
      wrap.innerHTML = globalThis.QueenIconEngine.programIconHtml({ ...item, id: item.id }, 32);
      return wrap;
    }
    if (url) {
      const img = document.createElement("img");
      img.className = "qd-png-icon";
      img.src = url;
      img.alt = "";
      img.width = 32;
      img.height = 32;
      img.loading = "lazy";
      img.dataset.queenIconRef = ref;
      wrap.appendChild(img);
      return wrap;
    }
    const kind = item.sdf_kind || item.kind || (item.category === "System" ? "folder" : "program");
    if (globalThis.QueenSdfIcons?.mountIcon) {
      globalThis.QueenSdfIcons.mountIcon(wrap, kind, { size: 32 });
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
    return mergedPrograms();
  }

  function renderIcons(programs) {
    const grid = $("qd-icons");
    if (!grid) return;
    const list = sortPrograms(programs ?? desktopSurfacePrograms());
    grid.hidden = state.data?.desktop_icons_in_start === true || list.length === 0;
    grid.innerHTML = "";
    list.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "qd-icon" + (item.pinned ? " pinned" : "");
      btn.dataset.id = item.id;
      btn.dataset.name = item.name || "";
      btn.dataset.qdTip = item.name || "";
      btn.draggable = true;
      if (item.url) {
        btn.dataset.queenProgramUrl = item.url;
        btn.dataset.queenProgramName = item.name || "";
      }

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "qd-icon-pin";
      pinBtn.setAttribute("aria-label", item.pinned ? "Unpin" : state.data?.desktop_icons_in_start ? "Pin to Start" : "Pin to desktop");
      pinBtn.textContent = "📌";
      pinBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        togglePin(item);
      });

      btn.appendChild(pinBtn);
      btn.appendChild(iconNode(item));
      const label = document.createElement("span");
      label.className = "qd-icon-label";
      label.textContent = item.name || "";
      btn.appendChild(label);

      btn.addEventListener("click", () => {
        grid.querySelectorAll(".qd-icon").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        state.selected = item;
        launch(item);
      });
      btn.addEventListener("dblclick", () => launch(item, { newTab: true }));
      btn.addEventListener("mouseenter", () => showTip(btn, item.name || ""));
      btn.addEventListener("mouseleave", hideTip);
      btn.addEventListener("dragstart", (ev) => {
        const url = btn.dataset.queenProgramUrl || item.url;
        const name = btn.dataset.queenProgramName || item.name || "Program";
        if (!url) return;
        ev.dataTransfer.setData("text/uri-list", url);
        ev.dataTransfer.setData(
          "application/x-queen-program",
          JSON.stringify({ url, name }),
        );
        ev.dataTransfer.effectAllowed = "copy";
      });
      btn.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        openCtx(ev.clientX, ev.clientY, item);
      });
      grid.appendChild(btn);
    });
    applySearch(list);
    wireTips(document);
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
        rows.push(`<button type="button" class="qd-task" data-id="${esc(t.id)}">${esc(t.name)}</button>`);
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
        const item = state.tasks.find((x) => x.id === btn.dataset.id);
        if (item) launch(item);
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
    ctx.innerHTML =
      '<button type="button" data-a="open">Open</button>' +
      '<button type="button" data-a="props">Properties…</button>';
    ctx.style.left = Math.min(x, innerWidth - 180) + "px";
    ctx.style.top = Math.min(y, innerHeight - 140) + "px";
    ctx.classList.add("open");
    ctx.onclick = async (ev) => {
      const b = ev.target.closest("[data-a]");
      if (!b) return;
      ctx.classList.remove("open");
      if (b.dataset.a === "open") launch(item);
      else if (b.dataset.a === "props") globalThis.QueenProgramSurface?.showProperties?.(item);
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
      url: "/world/queen-files.html",
    };
    launch(files);
  }

  function openBrowser() {
    const browser = mergedPrograms().find((p) => p.id === "browser") || {
      id: "browser",
      name: "Queen Browser",
      url: "/world/browser.html",
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
      toast("Desktop load failed");
    }
  }

  function wireChrome() {
    $("qd-taskbar-start")?.addEventListener("click", () => {
      if (inQueenShell()) {
        window.parent.postMessage({ type: "queen:desktop", action: "toggle_start", side: "classic" }, "*");
      }
    });
    $("qd-quick-files")?.addEventListener("click", openFiles);
    $("qd-quick-browser")?.addEventListener("click", openBrowser);
    $("qd-home")?.addEventListener("click", () => {
      const home = global.IroncladBus?.PANEL_ORIGIN ? global.IroncladBus.PANEL_ORIGIN + "/field" : "http://127.0.0.1:9477/field";
      if (inQueenShell()) window.parent.location.href = home;
      else window.location.href = home;
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