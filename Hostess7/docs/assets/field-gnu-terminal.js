/**
 * Field GNU Terminal — foundational panel shell · code-preview sidebar · Ironclad truth.
 */
(function () {
  "use strict";

  const API = (function () {
    if (globalThis.H7Api) return globalThis.H7Api("/api/field-gnu-terminal");
    try {
      const p = new URL(globalThis.location?.href || "/Hostess7/");
      if (p.port === "9481") return `${p.origin}/api/field-gnu-terminal`;
      return "/api/field-gnu-terminal";
    } catch (_) {
      return "/api/field-gnu-terminal";
    }
  })();
  const PROXY = "/browse/view";
  const THEME_API = "/api/ammoos-themes";
  const MAX_DOM_LINES = 1200;
  const CODE_PREVIEW_MIN_FONT = 0.22;
  const CODE_PREVIEW_BASE_FONT = 0.58;
  const SCROLL_EDGE = 10;
  const MAX_SPLIT = 4;
  const TAB_THRESHOLD = 5;

  const PALETTE_16 = [
    "#000000", "#cd3131", "#0dbc79", "#e5e510", "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5",
    "#666666", "#f14c4c", "#23d18b", "#f5f543", "#3b8eea", "#d670d6", "#29b8db", "#ffffff",
  ];

  const root = {
    shell: null,
    workspace: null,
    tabstrip: null,
    scrolltrack: null,
    scrollthumb: null,
    scrollwrap: null,
    cliFamily: "",
    codePreviewBody: null,
    codePreviewMeta: null,
    menuSorted: false,
    sessions: [],
    activeId: null,
    layout: "tabs",
    nextId: 1,
    cwd: "",
    kilroyRoot: "",
    kernel: {},
    themes: [],
    themeId: "black_emerald_rose_2026",
    fontSize: 0.88,
    wrap: true,
    bell: false,
    showCodePreview: true,
    showMini: true,
    initialized: false,
    scrollDrag: null,
    uiSyncPending: false,
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function xterm256(n) {
    if (n < 16) return PALETTE_16[n];
    if (n < 232) {
      const idx = n - 16;
      const r = (idx / 36) | 0;
      const g = ((idx / 6) | 0) % 6;
      const b = idx % 6;
      const conv = (v) => (v ? 55 + v * 40 : 0);
      return `rgb(${conv(r)},${conv(g)},${conv(b)})`;
    }
    const gray = 8 + (n - 232) * 10;
    return `rgb(${gray},${gray},${gray})`;
  }

  function applySgr(state, params) {
    if (!params.length || (params.length === 1 && params[0] === 0)) {
      state.fg = null;
      state.bg = null;
      state.bold = false;
      state.dim = false;
      return;
    }
    let i = 0;
    while (i < params.length) {
      const p = params[i++];
      if (p === 0) {
        state.fg = null;
        state.bg = null;
        state.bold = false;
        state.dim = false;
      } else if (p === 1) state.bold = true;
      else if (p === 2) state.dim = true;
      else if (p === 22) {
        state.bold = false;
        state.dim = false;
      } else if (p >= 30 && p <= 37) state.fg = PALETTE_16[p - 30];
      else if (p === 39) state.fg = null;
      else if (p >= 40 && p <= 47) state.bg = PALETTE_16[p - 40];
      else if (p === 49) state.bg = null;
      else if (p >= 90 && p <= 97) state.fg = PALETTE_16[p - 90 + 8];
      else if (p >= 100 && p <= 107) state.bg = PALETTE_16[p - 100 + 8];
      else if (p === 38 && params[i] === 5 && i + 1 < params.length) {
        state.fg = xterm256(params[++i]);
        i++;
      } else if (p === 38 && params[i] === 2 && i + 3 < params.length) {
        state.fg = `rgb(${params[++i]},${params[++i]},${params[++i]})`;
      } else if (p === 48 && params[i] === 5 && i + 1 < params.length) {
        state.bg = xterm256(params[++i]);
        i++;
      } else if (p === 48 && params[i] === 2 && i + 3 < params.length) {
        state.bg = `rgb(${params[++i]},${params[++i]},${params[++i]})`;
      }
    }
  }

  function parseAnsiText(text) {
    const frag = document.createDocumentFragment();
    const state = { fg: null, bg: null, bold: false, dim: false };
    let i = 0;
    let chunk = "";

    const flush = () => {
      if (!chunk) return;
      const el = document.createElement("span");
      if (state.fg) el.style.color = state.fg;
      if (state.bg) el.style.backgroundColor = state.bg;
      if (state.bold) el.style.fontWeight = "700";
      if (state.dim) el.style.opacity = "0.72";
      el.textContent = chunk;
      frag.appendChild(el);
      chunk = "";
    };

    while (i < text.length) {
      if (text.charCodeAt(i) === 27 && text[i + 1] === "[") {
        flush();
        let j = i + 2;
        while (j < text.length && /[0-9;]/.test(text[j])) j++;
        const cmd = text[j];
        if (cmd === "m") {
          const params = text
            .slice(i + 2, j)
            .split(";")
            .filter((s) => s.length)
            .map((s) => parseInt(s, 10));
          if (!params.length) params.push(0);
          applySgr(state, params);
        }
        i = cmd ? j + 1 : j;
        continue;
      }
      chunk += text[i++];
    }
    flush();
    return frag.childNodes.length ? frag : null;
  }

  function hexAlpha(hex, alpha) {
    if (!hex || !hex.startsWith("#") || hex.length < 7) return hex || "transparent";
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function applyFieldTheme(theme) {
    const t = theme || activeThemeDoc();
    if (!t?.tokens?.colors) return;
    const c = t.tokens.colors;
    const ty = t.tokens.typography || {};
    const shell = root.shell;
    if (!shell) return;
    root.themeId = t.id || root.themeId;
    shell.dataset.fgtTheme = root.themeId;
    shell.style.setProperty("--fgt-green", c.accent || c.emerald || "#3ecf8e");
    shell.style.setProperty("--fgt-green-dim", hexAlpha(c.dim || c.accent, 0.55));
    shell.style.setProperty("--fgt-green-glow", hexAlpha(c.accent || c.emerald, 0.35));
    shell.style.setProperty("--fgt-bg", hexAlpha(c.bg || c.void, 0.82));
    shell.style.setProperty("--fgt-bg-pane", hexAlpha(c.surface || c.panel, 0.78));
    shell.style.setProperty("--fgt-border", hexAlpha(c.border || c.accent, 0.28));
    shell.style.setProperty("--fgt-text", c.text || "#e8f2ea");
    shell.style.setProperty("--fgt-cmd", c.aqua || "#7ec8ff");
    shell.style.setProperty("--fgt-err", c.danger || c.rose || "#f472b6");
    shell.style.setProperty("--fgt-url", c.flow || c.aqua || "#6ab0ff");
    if (ty.mono_font) shell.style.fontFamily = ty.mono_font;
    const themeEl = shell.querySelector("#fgt-theme-label");
    if (themeEl) themeEl.textContent = t.label || t.id || "AmmoOS";
  }

  function bindThemeWatch() {
    if (root._themeWatch) return;
    root._themeWatch = true;
    document.addEventListener("queen-styles-changed", () => applyFieldTheme());
  }

  function activeThemeDoc() {
    const cat = globalThis.AmmoosThemes?.getCatalog?.();
    const id = cat?.active?.queen_styles || root.themeId;
    return globalThis.AmmoosThemes?.themeById?.(cat, id) || null;
  }

  async function loadTerminalThemes() {
    try {
      if (globalThis.AmmoosThemes?.fetchCatalog) {
        const doc = await globalThis.AmmoosThemes.fetchCatalog();
        root.themes = doc?.queen_styles?.themes || doc?.themes || [];
        return;
      }
      const r = await fetch(THEME_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "catalog" }),
        cache: "no-store",
      });
      if (r.ok) {
        const doc = await r.json();
        root.themes = doc.queen_styles?.themes || doc.themes || [];
      }
    } catch (_) {}
  }

  async function applyThemeId(id) {
    if (globalThis.AmmoosThemes?.apply) {
      try {
        await globalThis.AmmoosThemes.apply({ queen_styles: id });
      } catch (_) {}
    }
    const cat = globalThis.AmmoosThemes?.getCatalog?.();
    applyFieldTheme(globalThis.AmmoosThemes?.themeById?.(cat, id));
    root.themeId = id;
  }

  function cycleTheme(dir) {
    const themes = root.themes.length ? root.themes : [];
    if (!themes.length) return;
    const idx = Math.max(0, themes.findIndex((t) => t.id === root.themeId));
    const next = themes[(idx + dir + themes.length) % themes.length];
    void applyThemeId(next.id);
    appendLine(`Theme → ${next.label || next.id}`, "banner");
  }

  function scheduleUiSync() {
    if (root.uiSyncPending) return;
    root.uiSyncPending = true;
    requestAnimationFrame(() => {
      root.uiSyncPending = false;
      syncScrollbar();
      renderCodePreview();
    });
  }

  function shortCwd(path) {
    const home = path || "/";
    if (root.kilroyRoot && home.startsWith(root.kilroyRoot)) {
      return home.replace(root.kilroyRoot, "~/KILROY").replace(/\/$/, "") || "~/KILROY";
    }
    return home.replace(/^.*\/SG\/?/, "~/SG/").replace(/\/$/, "") || "~/SG";
  }

  function promptLabel(cwd) {
    return `${shortCwd(cwd || root.cwd)} $ `;
  }

  function activeSession() {
    return root.sessions.find((s) => s.id === root.activeId) || root.sessions[0] || null;
  }

  function sessionById(id) {
    return root.sessions.find((s) => s.id === id) || null;
  }

  function layoutLabel() {
    if (root.layout === "tabs") return `tabs · ${root.sessions.length}`;
    return root.layout.replace("split-", "split ×");
  }

  function updateStatusBar() {
    const cwdEl = root.shell?.querySelector("#fgt-cwd");
    const profileEl = root.shell?.querySelector("#fgt-profile");
    const layoutEl = root.shell?.querySelector("#fgt-status-layout");
    const cliEl = root.shell?.querySelector("#fgt-cli-family");
    const sess = activeSession();
    if (cwdEl) cwdEl.textContent = shortCwd(sess?.cwd || root.cwd);
    if (layoutEl) layoutEl.textContent = layoutLabel();
    if (cliEl) cliEl.textContent = root.cliFamily || "universal";
    if (profileEl && root.kernel) {
      const loaded = root.kernel.field_kernel_running || root.kernel.proc_kilroy_field;
      const mode = root.kernel.ai_default_mode || "home";
      profileEl.textContent = loaded
        ? `KILROY Field OS · AI ${mode}`
        : "Host compat · Grok16 PATH";
    }
  }

  function isAtBottom(out) {
    if (!out) return true;
    return out.scrollHeight - out.scrollTop - out.clientHeight <= SCROLL_EDGE;
  }

  function scrollOutBy(out, delta) {
    if (!out) return;
    out.scrollTop = Math.max(0, Math.min(out.scrollHeight - out.clientHeight, out.scrollTop + delta));
    syncScrollbar();
    renderCodePreview();
  }

  function scrollOutPage(out, dir) {
    if (!out) return;
    scrollOutBy(out, dir * Math.max(120, out.clientHeight * 0.85));
  }

  function resolveUniversalCli(line) {
    const shell = globalThis.KilroyUniversalShell;
    if (!shell?.resolveLine) return null;
    try {
      return shell.resolveLine(line);
    } catch (_) {
      return null;
    }
  }

  function setDeckFlags() {
    const deck = root.shell?.querySelector("#fgt-deck");
    if (!deck) return;
    deck.dataset.codepreview = root.showCodePreview ? "1" : "0";
    deck.dataset.mini = root.showMini ? "1" : "0";
  }

  function applyLayout(mode) {
    const count = root.sessions.length;
    if (count >= TAB_THRESHOLD && mode !== "tabs") {
      root.layout = "tabs";
    } else {
      root.layout = mode;
    }
    if (root.workspace) {
      root.workspace.dataset.layout = root.layout;
    }
    const strip = root.tabstrip;
    if (strip) {
      strip.hidden = root.layout !== "tabs";
    }
    root.sessions.forEach((s, i) => {
      if (s.head) s.head.hidden = root.layout === "tabs";
      s.pane.classList.toggle("active", root.layout === "tabs" ? s.id === root.activeId : i < countForLayout());
    });
    renderTabstrip();
    updateStatusBar();
  }

  function countForLayout() {
    if (root.layout === "split-2") return 2;
    if (root.layout === "split-3") return 3;
    if (root.layout === "split-4") return 4;
    return root.sessions.length;
  }

  function ensureSessionCount(n) {
    while (root.sessions.length < n) {
      createSession({ focus: false });
    }
    if (root.sessions.length > n && root.layout !== "tabs") {
      root.sessions.slice(n).forEach((s) => removeSession(s.id, true));
    }
  }

  function renderTabstrip() {
    if (!root.tabstrip) return;
    const tabs = root.sessions
      .map(
        (s) =>
          `<button type="button" class="fgt-tab${s.id === root.activeId ? " active" : ""}" data-tab="${esc(s.id)}" title="${esc(s.title)}">${esc(s.title)}</button>`,
      )
      .join("");
    root.tabstrip.innerHTML =
      tabs +
      '<button type="button" class="fgt-tab fgt-tab-add" data-tab="add" title="New tab">+</button>';
    root.tabstrip.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.tab === "add") {
          addSession();
          return;
        }
        activateSession(btn.dataset.tab);
      });
    });
  }

  function createSession(opts = {}) {
    const id = `t${root.nextId++}`;
    const pane = document.createElement("section");
    pane.className = "fgt-session";
    pane.dataset.sessionId = id;
    pane.tabIndex = 0;
    pane.innerHTML =
      `<div class="fgt-session-head"><strong>${esc(opts.title || `Shell ${root.sessions.length + 1}`)}</strong></div>` +
      `<div class="fgt-terminal-out" role="log" aria-live="polite"></div>` +
      `<div class="fgt-prompt-row">` +
      `<span class="fgt-prompt-label"></span>` +
      `<input type="text" class="fgt-prompt-input" autocomplete="off" spellcheck="false" aria-label="Command line" />` +
      `</div>`;
    root.workspace?.appendChild(pane);

    const out = pane.querySelector(".fgt-terminal-out");
    const label = pane.querySelector(".fgt-prompt-label");
    const input = pane.querySelector(".fgt-prompt-input");
    const head = pane.querySelector(".fgt-session-head");

    const session = {
      id,
      title: opts.title || `Shell ${root.sessions.length + 1}`,
      cwd: root.cwd,
      lines: [],
      history: [],
      histIdx: -1,
      pane,
      head,
      out,
      label,
      input,
    };

    label.textContent = promptLabel(session.cwd);
    input.addEventListener("keydown", (ev) => onPromptKey(ev, session));
    pane.addEventListener("mousedown", () => activateSession(id));
    out.addEventListener("scroll", () => {
      if (session.id === root.activeId) {
        syncScrollbar();
        renderCodePreview();
      }
    });
    out.addEventListener("wheel", (ev) => {
      if (session.id !== root.activeId) return;
      ev.preventDefault();
      scrollOutBy(out, ev.deltaY);
    }, { passive: false });
    out.addEventListener("keydown", (ev) => {
      if (session.id !== root.activeId) return;
      if (ev.key === "PageUp") {
        ev.preventDefault();
        scrollOutPage(out, -1);
      }
      if (ev.key === "PageDown") {
        ev.preventDefault();
        scrollOutPage(out, 1);
      }
      if (ev.key === "Home" && ev.ctrlKey) {
        ev.preventDefault();
        out.scrollTop = 0;
        syncScrollbar();
        renderCodePreview();
      }
      if (ev.key === "End" && ev.ctrlKey) {
        ev.preventDefault();
        out.scrollTop = out.scrollHeight;
        syncScrollbar();
        renderCodePreview();
      }
    });

    root.sessions.push(session);
    if (opts.focus !== false) activateSession(id);
    applyLayout(root.layout);
    return session;
  }

  function removeSession(id, silent) {
    if (root.sessions.length <= 1) return;
    const idx = root.sessions.findIndex((s) => s.id === id);
    if (idx < 0) return;
    root.sessions[idx].pane.remove();
    root.sessions.splice(idx, 1);
    if (root.activeId === id) {
      root.activeId = root.sessions[Math.max(0, idx - 1)]?.id || null;
    }
    if (!silent) applyLayout(root.layout);
  }

  function activateSession(id) {
    root.activeId = id;
    root.sessions.forEach((s) => {
      const on = s.id === id;
      s.pane.classList.toggle("active", root.layout === "tabs" ? on : true);
    });
    renderTabstrip();
    updateStatusBar();
    syncScrollbar();
    renderCodePreview();
    const sess = sessionById(id);
    sess?.input?.focus();
  }

  function addSession() {
    if (root.sessions.length >= TAB_THRESHOLD - 1) {
      applyLayout("tabs");
    } else if (root.layout !== "tabs" && root.sessions.length >= MAX_SPLIT) {
      applyLayout("tabs");
    }
    const sess = createSession();
    if (root.sessions.length >= TAB_THRESHOLD) applyLayout("tabs");
    return sess;
  }

  function splitTo(n) {
    if (n >= TAB_THRESHOLD) {
      ensureSessionCount(n);
      applyLayout("tabs");
      return;
    }
    ensureSessionCount(n);
    applyLayout(`split-${n}`);
  }

  function buildLineRow(text, kind) {
    const line = { text: String(text ?? ""), kind: kind || "out" };
    const row = document.createElement("p");
    row.className = `fgt-line fgt-line--${line.kind}`;
    const raw = line.text;
    const cleaned = raw.replace(/\x1b\[[0-9;]*[A-Za-z]/g, (m) => (m.endsWith("m") ? m : ""));
    const hasAnsi = cleaned.includes("\x1b");
    const urlRe = /https?:\/\/[^\s<>"']+/g;

    if (hasAnsi) {
      const parsed = parseAnsiText(cleaned);
      if (parsed) row.appendChild(parsed);
      else row.textContent = cleaned.replace(/\x1b\[[0-9;]*m/g, "");
    } else if (line.kind === "out" && urlRe.test(raw)) {
      urlRe.lastIndex = 0;
      row.innerHTML = esc(raw).replace(
        urlRe,
        (u) => `<span class="fgt-line--url" data-url="${esc(u)}">${esc(u)}</span>`,
      );
      row.querySelectorAll("[data-url]").forEach((el) => {
        el.addEventListener("click", () => miniNavigate(el.dataset.url));
      });
    } else {
      row.textContent = raw;
    }
    return { row, line };
  }

  function appendLine(text, kind, session) {
    const sess = session || activeSession();
    if (!sess?.out) return;
    const { row, line } = buildLineRow(text, kind);
    sess.lines.push(line);
    while (sess.out.childElementCount > MAX_DOM_LINES) {
      sess.lines.shift();
      const first = sess.out.firstElementChild;
      if (first) first.remove();
    }
    const stick = isAtBottom(sess.out);
    sess.out.appendChild(row);
    if (stick) sess.out.scrollTop = sess.out.scrollHeight;
    if (sess.id === root.activeId) scheduleUiSync();
    if (sess.label) sess.label.textContent = promptLabel(sess.cwd);
  }

  function appendLines(text, kind, session) {
    const sess = session || activeSession();
    if (!sess?.out || text == null) return;
    const parts = String(text).split("\n");
    const frag = document.createDocumentFragment();
    for (const part of parts) {
      const { row, line } = buildLineRow(part, kind);
      sess.lines.push(line);
      frag.appendChild(row);
    }
    while (sess.out.childElementCount > MAX_DOM_LINES) {
      const drop = sess.out.childElementCount - MAX_DOM_LINES;
      sess.lines.splice(0, drop);
      for (let i = 0; i < drop && sess.out.firstElementChild; i++) {
        sess.out.firstElementChild.remove();
      }
    }
    const stick = isAtBottom(sess.out);
    sess.out.appendChild(frag);
    if (stick) sess.out.scrollTop = sess.out.scrollHeight;
    if (sess.id === root.activeId) scheduleUiSync();
    if (sess.label) sess.label.textContent = promptLabel(sess.cwd);
  }

  function clearTerminal(session) {
    const sess = session || activeSession();
    if (!sess) return;
    sess.lines.length = 0;
    if (sess.out) sess.out.innerHTML = "";
    syncScrollbar();
    renderCodePreview();
  }

  function syncScrollbar() {
    const sess = activeSession();
    const wrap = root.scrollwrap;
    const thumb = root.scrollthumb;
    const out = sess?.out;
    if (!out || !wrap || !thumb) return;

    const sh = out.scrollHeight;
    const ch = out.clientHeight;
    const trackH = wrap.clientHeight;
    if (sh <= ch + 2) {
      thumb.style.height = `${trackH}px`;
      thumb.style.top = "0px";
      thumb.style.opacity = "0.35";
      return;
    }
    thumb.style.opacity = "1";
    const ratio = ch / sh;
    const thumbH = Math.max(28, Math.floor(trackH * ratio));
    const maxTop = Math.max(0, trackH - thumbH);
    const scrollRatio = maxTop > 0 ? out.scrollTop / (sh - ch) : 0;
    thumb.style.height = `${thumbH}px`;
    thumb.style.top = `${Math.floor(maxTop * scrollRatio)}px`;
  }

  function scrollTerminalTo(ratio) {
    const out = activeSession()?.out;
    if (!out) return;
    const max = out.scrollHeight - out.clientHeight;
    out.scrollTop = Math.max(0, Math.min(max, ratio * max));
    syncScrollbar();
    renderCodePreview();
  }

  function scrollTerminalTop() {
    const out = activeSession()?.out;
    if (!out) return;
    out.scrollTop = 0;
    syncScrollbar();
    renderCodePreview();
  }

  function scrollTerminalBottom() {
    const out = activeSession()?.out;
    if (!out) return;
    out.scrollTop = out.scrollHeight;
    syncScrollbar();
    renderCodePreview();
  }

  function codePreviewFontRem(lineCount) {
    if (lineCount <= 24) return CODE_PREVIEW_BASE_FONT;
    const shrink = Math.pow(0.992, lineCount - 24);
    return Math.max(CODE_PREVIEW_MIN_FONT, CODE_PREVIEW_BASE_FONT * shrink);
  }

  function renderCodePreview() {
    if (!root.codePreviewBody || !root.showCodePreview) return;
    const sess = activeSession();
    if (!sess) return;
    const lines = sess.lines;
    const n = lines.length;
    const fontRem = codePreviewFontRem(n);
    root.codePreviewBody.style.fontSize = `${fontRem}rem`;
    root.codePreviewBody.innerHTML = lines
      .map(
        (l) =>
          `<p class="fgt-codepreview-line fgt-codepreview-line--${esc(l.kind || "out")}">${esc(l.text)}</p>`,
      )
      .join("");
    if (root.codePreviewMeta) {
      root.codePreviewMeta.textContent = `${n} lines · ${fontRem.toFixed(2)}rem`;
    }
    const out = sess.out;
    if (out && root.codePreviewBody) {
      const ratio = out.scrollHeight > out.clientHeight
        ? out.scrollTop / (out.scrollHeight - out.clientHeight)
        : 1;
      const body = root.codePreviewBody;
      const target = Math.max(0, (body.scrollHeight - body.clientHeight) * ratio);
      if (Math.abs(body.scrollTop - target) > 2) body.scrollTop = target;
    }
  }

  function bindScrollbar() {
    const track = root.scrolltrack;
    const wrap = root.scrollwrap;
    const thumb = root.scrollthumb;
    if (!track || !wrap || !thumb) return;

    window.addEventListener("resize", () => {
      syncScrollbar();
      renderCodePreview();
    });

    wrap.addEventListener("mousedown", (ev) => {
      if (ev.target === thumb) return;
      const rect = wrap.getBoundingClientRect();
      const y = ev.clientY - rect.top;
      const thumbTop = parseFloat(thumb.style.top) || 0;
      const thumbH = thumb.offsetHeight;
      if (y < thumbTop) scrollOutPage(activeSession()?.out, -1);
      else if (y > thumbTop + thumbH) scrollOutPage(activeSession()?.out, 1);
      else scrollTerminalTo(y / rect.height);
    });

    thumb.addEventListener("mousedown", (ev) => {
      ev.preventDefault();
      root.scrollDrag = {
        startY: ev.clientY,
        startTop: parseFloat(thumb.style.top) || 0,
        trackH: wrap.clientHeight,
        thumbH: thumb.offsetHeight,
      };
      track.classList.add("dragging");
    });

    document.addEventListener("mousemove", (ev) => {
      if (!root.scrollDrag) return;
      const d = root.scrollDrag;
      const maxTop = d.trackH - d.thumbH;
      const top = Math.max(0, Math.min(maxTop, d.startTop + (ev.clientY - d.startY)));
      scrollTerminalTo(maxTop > 0 ? top / maxTop : 0);
    });

    document.addEventListener("mouseup", () => {
      if (!root.scrollDrag) return;
      root.scrollDrag = null;
      track.classList.remove("dragging");
    });

    track.querySelector("#fgt-scroll-up")?.addEventListener("click", () => {
      scrollOutPage(activeSession()?.out, -1);
    });
    track.querySelector("#fgt-scroll-down")?.addEventListener("click", () => {
      scrollOutPage(activeSession()?.out, 1);
    });
  }

  function miniNavigate(url) {
    const raw = (url || "").trim();
    const input = root.shell?.querySelector("#fgt-mini-url");
    const frame = root.shell?.querySelector("#fgt-mini-frame");
    if (!raw || !frame) return;
    if (input) input.value = raw;

    let target = raw;
    if (!/^https?:\/\//i.test(target) && !target.startsWith("/")) target = `https://${target}`;
    const proxied =
      target.startsWith("http") && !target.startsWith(location.origin)
        ? `${PROXY}?url=${encodeURIComponent(target)}`
        : target;
    frame.src = proxied;
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`terminal HTTP ${r.status}`);
    return r.json();
  }

  async function runCommand(cmd, session) {
    const sess = session || activeSession();
    const trimmed = (cmd || "").trim();
    if (!trimmed || !sess) return;
    if (trimmed === "clear" || trimmed === "reset") {
      clearTerminal(sess);
      appendLine("Terminal cleared.", "out", sess);
      return;
    }
    appendLine(`${promptLabel(sess.cwd)}${trimmed}`, "cmd", sess);
    sess.history.push(trimmed);
    sess.histIdx = sess.history.length;

    const low = trimmed.toLowerCase().split()[0];
    if (low === "wiki" || low === "field-tech" || low === "fieldtech") {
      const wiki = "https://zacharygeurts.github.io/GNUEOLTerminal/wiki/";
      const book = "https://zacharygeurts.github.io/GNUEOLTerminal/";
      appendLine("GNUEOL Classic Schooler Wiki — for Emacs veterans and Bash poets", "out", sess);
      appendLine(`  wiki:  ${wiki}`, "out", sess);
      appendLine(`  book:  ${book}`, "out", sess);
      appendLine("  pages: emacs · bash · coreutils · ssh · gpl · field-tech", "out", sess);
      miniNavigate(wiki);
      return;
    }

    const resolved = resolveUniversalCli(trimmed);
    if (resolved?.family) {
      root.cliFamily = resolved.canonical ? `${resolved.family} · ${resolved.canonical}` : resolved.family;
      updateStatusBar();
    }

    try {
      const j = await api({ action: "run", command: trimmed, cwd: sess.cwd || root.cwd });
      fetch("/api/hostess7/userwatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "work_zone",
          cwd: sess.cwd || root.cwd,
          command: trimmed,
          source: "field-gnu-terminal",
        }),
      }).catch(() => {});
      if (j.clear) {
        clearTerminal(sess);
        return;
      }
      if (j.cwd) {
        sess.cwd = j.cwd;
        root.cwd = j.cwd;
        updateStatusBar();
      }
      if (j.field_kernel) root.kernel = j.field_kernel;
      const out = j.output || j.error || "";
      if (out) appendLines(out, j.ok === false ? "err" : "out", sess);
      if (j.open_url) {
        const url = String(j.open_url);
        const name = (j.module && j.module.label) || "DOS 4.0 module";
        appendLine("Opening " + name + "…", "out", sess);
        if (global.parent && global.parent !== global && global.parent.NexusFieldShell?.launch) {
          global.parent.NexusFieldShell.launch({
            id: "dos40-" + ((j.module && j.module.id) || "module"),
            name: name,
            exec: url,
            shell: true,
          });
        } else if (global.NexusFieldShell?.launch) {
          global.NexusFieldShell.launch({
            id: "dos40-" + ((j.module && j.module.id) || "module"),
            name: name,
            exec: url,
            shell: true,
          });
        } else {
          global.location.href = url.startsWith("http") ? url : (global.location.origin + url);
        }
      }
      if (!j.ok && root.bell) {
        try {
          const ctx = new AudioContext();
          const o = ctx.createOscillator();
          o.connect(ctx.destination);
          o.frequency.value = 440;
          o.start();
          o.stop(ctx.currentTime + 0.08);
        } catch (_) {
          /* optional */
        }
      }
    } catch (e) {
      appendLine(`error: ${e.message}`, "err", sess);
    }
    syncScrollbar();
  }

  function onPromptKey(ev, session) {
    const input = session.input;
    if (ev.key === "Enter") {
      ev.preventDefault();
      const v = input.value;
      input.value = "";
      runCommand(v, session);
      return;
    }
    if (ev.key === "ArrowUp") {
      ev.preventDefault();
      if (!session.history.length) return;
      session.histIdx = Math.max(0, session.histIdx - 1);
      input.value = session.history[session.histIdx] || "";
    }
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      if (!session.history.length) return;
      session.histIdx = Math.min(session.history.length, session.histIdx + 1);
      input.value = session.histIdx >= session.history.length ? "" : session.history[session.histIdx] || "";
    }
    if (ev.key === "l" && ev.ctrlKey) {
      ev.preventDefault();
      clearTerminal(session);
    }
  }

  function closeMenus() {
    root.shell?.querySelectorAll(".fgt-menu-drop").forEach((d) => d.classList.remove("open"));
    root.shell?.querySelectorAll(".fgt-menu-btn").forEach((b) => b.setAttribute("aria-expanded", "false"));
  }

  function bindMenus() {
    root.shell?.querySelectorAll(".fgt-menu").forEach((menu) => {
      const btn = menu.querySelector(".fgt-menu-btn");
      const drop = menu.querySelector(".fgt-menu-drop");
      if (!btn || !drop) return;
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const open = drop.classList.contains("open");
        closeMenus();
        if (!open) {
          drop.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });
      drop.querySelectorAll("button[data-action]").forEach((item) => {
        item.addEventListener("click", () => {
          const act = item.dataset.action;
          closeMenus();
          const sess = activeSession();
          if (act === "clear") clearTerminal(sess);
          if (act === "copy") {
            const text = (sess?.lines || []).map((l) => l.text).join("\n");
            navigator.clipboard?.writeText(text);
          }
          if (act === "paste") {
            navigator.clipboard?.readText().then((t) => {
              sess?.input && (sess.input.value = (sess.input.value + t).trim());
            });
          }
          if (act === "select-all" && sess?.out) {
            const range = document.createRange();
            range.selectNodeContents(sess.out);
            const sel = window.getSelection();
            sel?.removeAllRanges();
            sel?.addRange(range);
          }
          if (act === "font-larger") {
            root.fontSize = Math.min(1.25, root.fontSize + 0.06);
            root.shell?.style.setProperty("--fgt-font-size", `${root.fontSize}rem`);
          }
          if (act === "font-smaller") {
            root.fontSize = Math.max(0.72, root.fontSize - 0.06);
            root.shell?.style.setProperty("--fgt-font-size", `${root.fontSize}rem`);
          }
          if (act === "toggle-wrap") {
            root.wrap = !root.wrap;
            root.sessions.forEach((s) => s.out?.classList.toggle("fgt-nowrap", !root.wrap));
          }
          if (act === "toggle-bell") {
            root.bell = !root.bell;
            appendLine(`Bell ${root.bell ? "on" : "off"}.`, "out");
          }
          if (act === "tab-new") addSession();
          if (act === "split-2") splitTo(2);
          if (act === "split-3") splitTo(3);
          if (act === "split-4") splitTo(4);
          if (act === "layout-tabs") applyLayout("tabs");
          if (act === "scroll-top") scrollTerminalTop();
          if (act === "scroll-bottom") scrollTerminalBottom();
          if (act === "toggle-codepreview") {
            root.showCodePreview = !root.showCodePreview;
            setDeckFlags();
            renderCodePreview();
          }
          if (act === "toggle-mini") {
            root.showMini = !root.showMini;
            setDeckFlags();
          }
          if (act === "wiki") {
            const wiki = "https://zacharygeurts.github.io/GNUEOLTerminal/wiki/";
            miniNavigate(wiki);
            appendLine(`wiki → ${wiki}`, "out");
          }
          if (act === "about") {
            appendLine(
              "Field Tech Terminal · GNUEOLTerminal textbook · Grok impersonates RMS (disclosed) · https://zacharygeurts.github.io/GNUEOLTerminal/",
              "out",
            );
          }
          if (act === "mini-home") miniNavigate(`${location.origin}/world/`);
          if (act === "mini-docs") miniNavigate("https://zacharygeurts.github.io/GNUEOLTerminal/wiki/");
          if (act === "theme-next") cycleTheme(1);
          if (act === "theme-mono") {
            void applyThemeId("mono_terminal");
          }
          if (act === "theme-emerald") {
            void applyThemeId("black_emerald_rose_2026");
          }
          if (act === "truth-help") {
            runCommand("truth", sess);
          }
          if (act === "about") {
            appendLine("AmmoOS GNU Terminal · panel · ANSI 256/truecolor · KILROY cwd", "banner");
          }
        });
      });
    });
    document.addEventListener("click", closeMenus);
  }

  function bindChrome() {
    root.shell?.querySelector("#fgt-mini-go")?.addEventListener("click", () => {
      miniNavigate(root.shell?.querySelector("#fgt-mini-url")?.value);
    });
    root.shell?.querySelector("#fgt-mini-url")?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") miniNavigate(ev.target.value);
    });
  }

  function wireShell(shell) {
    root.shell = shell;
    root.workspace = shell.querySelector("#fgt-workspace");
    root.tabstrip = shell.querySelector("#fgt-tabstrip");
    root.scrolltrack = shell.querySelector("#fgt-scrolltrack");
    root.scrollwrap = shell.querySelector("#fgt-scroll-wrap");
    root.scrollthumb = shell.querySelector("#fgt-scrollthumb");
    root.codePreviewBody = shell.querySelector("#fgt-codepreview-body");
    root.codePreviewMeta = shell.querySelector("#fgt-codepreview-meta");
    shell.style.setProperty("--fgt-font-size", `${root.fontSize}rem`);
    setDeckFlags();
  }

  function shellInner() {
    return (
      `<header class="fgt-topbar">` +
      `<span class="fgt-topbar-brand">AmmoOS Terminal</span>` +
      `<span class="fgt-topbar-pill fgt-topbar-pill--secured">Iron Plate</span>` +
      `<span class="fgt-topbar-pill fgt-topbar-pill--kilroy">GNU·EOL</span>` +
      `<nav class="fgt-menubar" aria-label="Terminal menus">` +
      menuBlock("File", [
        ["clear", "Clear terminal"],
        ["tab-new", "New tab"],
        ["wiki", "Open GNUEOL wiki"],
        ["about", "About AmmoOS Terminal"],
      ]) +
      menuBlock("Edit", [
        ["copy", "Copy buffer"],
        ["paste", "Paste"],
        ["sep", ""],
        ["select-all", "Select all"],
      ]) +
      menuBlock("View", [
        ["tab-new", "New tab"],
        ["split-2", "Split ×2"],
        ["split-3", "Split ×3"],
        ["split-4", "Split ×4"],
        ["layout-tabs", "Tab view"],
        ["sep", ""],
        ["scroll-top", "Scroll to top"],
        ["scroll-bottom", "Scroll to bottom"],
        ["sep", ""],
        ["font-larger", "Larger font"],
        ["font-smaller", "Smaller font"],
        ["toggle-wrap", "Toggle wrap"],
        ["sep", ""],
        ["theme-next", "Next theme"],
        ["theme-mono", "Mono Terminal theme"],
        ["theme-emerald", "Emerald Rose theme"],
        ["sep", ""],
        ["toggle-codepreview", "Toggle code preview"],
        ["toggle-mini", "Toggle minibrowser"],
        ["mini-home", "Minibrowser → panel home"],
      ]) +
      menuBlock("Options", [
        ["toggle-bell", "Bell on error"],
        ["mini-docs", "Minibrowser → Classic wiki"],
        ["wiki", "GNUEOL textbook wiki"],
        ["truth-help", "Ironclad truth program"],
      ]) +
      menuBlock("Help", [
        ["wiki", "Classic schooler wiki"],
        ["about", "Field Tech Terminal"],
        ["truth-help", "truth — information or diagnostic"],
        ["mini-docs", "GNU Bash manual"],
      ]) +
      `<span class="fgt-titlebar">Shell ≡ terminal · Ironclad · truth</span></nav></header>` +
      `<div class="fgt-statusbar">` +
      `<span>Cwd: <strong id="fgt-cwd">~/KILROY</strong></span>` +
      `<span id="fgt-profile">field-native</span>` +
      `<span class="fgt-status-cli" id="fgt-cli-family" title="Universal CLI family">universal</span>` +
      `<span class="fgt-status-theme" id="fgt-theme-label" title="AmmoOS theme">AmmoOS</span>` +
      `<span class="fgt-status-layout" id="fgt-status-layout">tabs · 1</span>` +
      `</div>` +
      `<div class="fgt-deck" id="fgt-deck" data-codepreview="1" data-mini="1">` +
      `<div class="fgt-main">` +
      `<div class="fgt-tabstrip" id="fgt-tabstrip"></div>` +
      `<div class="fgt-workspace" id="fgt-workspace" data-layout="tabs"></div>` +
      `</div>` +
      `<aside class="fgt-codepreview" id="fgt-codepreview" aria-label="Code preview">` +
      `<div class="fgt-codepreview-label">Code preview</div>` +
      `<div class="fgt-codepreview-meta" id="fgt-codepreview-meta">0 lines</div>` +
      `<div class="fgt-codepreview-body" id="fgt-codepreview-body"></div>` +
      `</aside>` +
      `<section class="fgt-minibrowser-pane" aria-label="Minibrowser">` +
      `<div class="fgt-mini-head"><strong>Mini</strong>` +
      `<input type="url" class="fgt-mini-url" id="fgt-mini-url" placeholder="URL or path…" spellcheck="false" />` +
      `<button type="button" class="fgt-mini-go" id="fgt-mini-go">Go</button></div>` +
      `<iframe class="fgt-mini-frame" id="fgt-mini-frame" title="Field minibrowser" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation"></iframe>` +
      `</section>` +
      `<aside class="fgt-scrolltrack" id="fgt-scrolltrack" aria-label="Terminal scrollbar">` +
      `<button type="button" class="fgt-scrollbtn fgt-scrollbtn--up" id="fgt-scroll-up" aria-label="Scroll up">▲</button>` +
      `<div class="fgt-scrollthumb-wrap" id="fgt-scroll-wrap">` +
      `<div class="fgt-scrollthumb" id="fgt-scrollthumb"></div></div>` +
      `<button type="button" class="fgt-scrollbtn fgt-scrollbtn--down" id="fgt-scroll-down" aria-label="Scroll down">▼</button></aside>` +
      `</div>`
    );
  }

  function shellTemplate(opts = {}) {
    const idAttr = opts.shellId ? ` id="${opts.shellId}"` : "";
    return `<div class="fgt-shell"${idAttr} data-fgt-secured="1">${shellInner()}</div>`;
  }

  function menuBlock(title, items) {
    const lis = items
      .map(([act, label]) =>
        act === "sep" ? `<li class="sep" role="separator"></li>` : `<li><button type="button" data-action="${act}" role="menuitem">${label}</button></li>`,
      )
      .join("");
    return (
      `<div class="fgt-menu"><button type="button" class="fgt-menu-btn" aria-haspopup="true" aria-expanded="false">${title}</button>` +
      `<ul class="fgt-menu-drop" role="menu">${lis}</ul></div>`
    );
  }

  async function sortMenusIronclad() {
    if (root.menuSorted || !root.shell || !globalThis.IroncladBus?.sort) return;
    const menus = root.shell.querySelectorAll(".fgt-menu-drop");
    for (const drop of menus) {
      const buttons = [...drop.querySelectorAll("button[data-action]")];
      if (buttons.length < 2) continue;
      const entries = buttons.map((btn) => ({
        id: btn.dataset.action,
        label: btn.textContent || btn.dataset.action,
        title: btn.textContent || "",
      }));
      try {
        const res = await globalThis.IroncladBus.sort(entries, "terminal_menu");
        const sorted = res?.entries || entries;
        const order = new Map(sorted.map((row, i) => [row.id || row.label, i]));
        buttons.sort((a, b) => (order.get(a.dataset.action) ?? 99) - (order.get(b.dataset.action) ?? 99));
        buttons.forEach((btn) => drop.appendChild(btn.parentElement));
      } catch (_) {
        buttons.sort((a, b) => (a.textContent || "").localeCompare(b.textContent || ""));
        buttons.forEach((btn) => drop.appendChild(btn.parentElement));
      }
    }
    root.menuSorted = true;
  }

  function mount(container, opts = {}) {
    if (!container) return null;
    container.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = opts.embedClass || "fgt-embed";
    wrap.innerHTML = shellTemplate();
    container.appendChild(wrap);
    wireShell(wrap.querySelector(".fgt-shell"));
    root.layout = opts.layout || "tabs";
    root.showCodePreview = opts.codepreview !== false && opts.miniview !== false;
    root.showMini = opts.minibrowser !== false;
    setDeckFlags();
    return init({ quiet: opts.quiet });
  }

  function bootModeFromUrl() {
    const q = new URLSearchParams(location.search);
    const mode = (q.get("mode") || q.get("m") || "").toLowerCase();
    const cmd = q.get("c") || q.get("command") || "";
    if (mode === "combinatronic" || mode === "combinatorics") return { kind: "combinatronic" };
    if (cmd) return { kind: "command", command: cmd };
    if (q.get("shell") === "1" || q.get("surface") === "shell") return { kind: "shell" };
    return { kind: "terminal" };
  }

  async function bootSession(sess) {
    appendLine("Field GNU Terminal — shell ≡ terminal · truth program · wiki: type wiki", "banner", sess);
    appendLine("Code preview sidebar — infinite lines · scales smaller · scroll", "out", sess);
    const loaded = root.kernel.field_kernel_running || root.kernel.proc_kilroy_field;
    const mode = root.kernel.ai_default_mode || "home";
    appendLine(
      loaded
        ? `KILROY loaded · /proc/kilroy_field live · AI mode ${mode}`
        : `Host compat · KILROY tree at ${root.kilroyRoot || "—"}`,
      "banner",
      sess,
    );
    appendLine(`cwd: ${sess.cwd}`, "out", sess);
  }

  async function init(opts = {}) {
    if (root.initialized && !opts.remount) {
      syncScrollbar();
      activeSession()?.input?.focus();
      return root;
    }

    const host = document.getElementById("fgt-shell");
    if (host && !root.shell) {
      if (!host.querySelector(".fgt-workspace")) {
        if (!host.innerHTML.trim()) {
          host.innerHTML = shellInner();
        } else {
          host.outerHTML = shellTemplate({ shellId: "fgt-shell" });
        }
      }
      wireShell(document.getElementById("fgt-shell") || host);
    }

    if (!root.shell) return root;

    if (!root.sessions.length) {
      createSession({ title: "Shell 1" });
    }

    await loadTerminalThemes();
    bindThemeWatch();
    applyFieldTheme(activeThemeDoc());

    if (!opts.quiet) {
      try {
        const j = await api({ action: "status" });
        root.kilroyRoot = j.kilroy_root || "";
        root.kernel = j.field_kernel || {};
        root.cwd = j.cwd_default || j.kilroy_root || j.sg_root || "";
        if (j.theme_default) root.themeId = j.theme_default;
        root.sessions.forEach((s) => {
          if (!s.cwd) s.cwd = root.cwd;
        });
        updateStatusBar();
        applyFieldTheme(activeThemeDoc());
        const sess = activeSession();
        if (sess && !sess.lines.length) {
          await bootSession(sess);
          const boot = bootModeFromUrl();
          if (boot.kind === "combinatronic") {
            appendLine("Combinatronic mode — type combinatorics or bash -c combinatorics", "out", sess);
            runCommand("combinatorics", sess);
          } else if (boot.kind === "command" && boot.command) {
            runCommand(boot.command, sess);
          } else if (boot.kind === "shell") {
            appendLine("Field shell surface — identical to terminal", "out", sess);
          }
        }
        miniNavigate("https://zacharygeurts.github.io/GNUEOLTerminal/wiki/");
      } catch (e) {
        appendLine(`Terminal API offline: ${e.message}`, "err");
      }
    }

    bindMenus();
    void sortMenusIronclad();
    bindScrollbar();
    bindChrome();
    applyLayout(root.layout || "tabs");
    root.initialized = true;
    syncScrollbar();
    activeSession()?.input?.focus();
    return root;
  }

  globalThis.FieldGnuTerminal = {
    init,
    mount,
    runCommand,
    miniNavigate,
    clearTerminal,
    scrollTop: scrollTerminalTop,
    scrollBottom: scrollTerminalBottom,
    addSession,
    splitTo,
    applyLayout,
    applyTheme: applyFieldTheme,
    activeSession,
  };
})();