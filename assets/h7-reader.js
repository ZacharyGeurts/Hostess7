/**
 * Hostess7 H7 secure full-page reader — librarian-issued session, bookmarks, themes, layout.
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "h7_reader_prefs";
  const RATIOS = [
    { id: "auto", label: "Auto", width: "100%", maxWidth: "none" },
    { id: "4-3", label: "4:3", width: "min(100%, 72ch)", maxWidth: "900px" },
    { id: "3-2", label: "3:2", width: "min(100%, 68ch)", maxWidth: "820px" },
    { id: "16-9", label: "16:9", width: "min(100%, 80ch)", maxWidth: "960px" },
    { id: "page", label: "Page", width: "min(100%, 60ch)", maxWidth: "720px" },
  ];
  const THEMES = {
    night: { fontColor: "#d8e0ec", bgColor: "#0a1018", label: "Night" },
    paper: { fontColor: "#1a1a1a", bgColor: "#f4f0e6", label: "Paper" },
    sepia: { fontColor: "#3d2f1f", bgColor: "#f0e4c8", label: "Sepia" },
    contrast: { fontColor: "#ffffff", bgColor: "#000000", label: "High contrast" },
    field: { fontColor: "#c8e0f0", bgColor: "#0d1828", label: "Field blue" },
  };

  const DEFAULT_PREFS = {
    fontSize: 18,
    fontColor: "#d8e0ec",
    bgColor: "#0a1018",
    fontId: "georgia",
    ratioId: "auto",
    lineHeight: 1.55,
    themeId: "night",
    marginPx: 12,
  };

  let overlay = null;
  let state = {
    bookId: null,
    book: null,
    pages: [],
    fullText: "",
    page: 1,
    pageChars: 3200,
    canonicalPages: true,
    loading: false,
    figures: {},
    prefs: { ...DEFAULT_PREFS },
    fonts: [],
    touchStartY: 0,
    touchStartX: 0,
    brailleMode: false,
    session: null,
    bookmarks: [],
    librarian: null,
    liesIndex: null,
    allLies: [],
    lieLibrarian: null,
    appendixPage: null,
    corrections: [],
    progressTimer: null,
    readStartedAt: null,
    readTimerInterval: null,
  };

  function loadPrefs() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) Object.assign(state.prefs, JSON.parse(raw));
    } catch (_) { /* ignore */ }
  }

  function savePrefs() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.prefs));
    } catch (_) { /* ignore */ }
    saveLayoutRemote();
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fontFamily() {
    const hit = state.fonts.find((f) => f.id === state.prefs.fontId);
    return hit?.family || "Georgia, serif";
  }

  function ratioSpec() {
    return RATIOS.find((r) => r.id === state.prefs.ratioId) || RATIOS[0];
  }

  function applyTheme(themeId) {
    const t = THEMES[themeId];
    if (!t) return;
    state.prefs.themeId = themeId;
    state.prefs.fontColor = t.fontColor;
    state.prefs.bgColor = t.bgColor;
  }

  function paginateClient(text, charsPerPage) {
    const t = String(text || "").replace(/\r\n/g, "\n").trim();
    if (!t) return [""];
    const pages = [];
    let start = 0;
    while (start < t.length) {
      let chunk = t.slice(start, start + charsPerPage);
      if (start + charsPerPage < t.length) {
        const brk = Math.max(chunk.lastIndexOf("\n\n"), chunk.lastIndexOf("\n"), chunk.lastIndexOf(". "));
        if (brk > charsPerPage / 3) chunk = chunk.slice(0, brk + 1);
      }
      pages.push(chunk.trim());
      start += Math.max(chunk.length, 1);
    }
    return pages.length ? pages : [""];
  }

  function charsPerPage() {
    if (state.canonicalPages && state.pageChars > 0) return state.pageChars;
    const el = overlay?.querySelector(".h7r-body");
    if (!el) return state.pageChars || 3200;
    const fs = state.prefs.fontSize;
    const lh = state.prefs.lineHeight;
    const w = el.clientWidth || 640;
    const h = el.clientHeight || 480;
    const cols = Math.max(24, Math.floor(w / (fs * 0.52)));
    const rows = Math.max(8, Math.floor(h / (fs * lh)));
    return Math.max(800, cols * rows * 2);
  }

  function sentenceBaseForPage(pageNum) {
    let base = 0;
    for (let p = 0; p < pageNum - 1; p++) {
      base += splitSentences(state.pages[p] || "").length;
    }
    return base;
  }

  function repaginateCanonical() {
    if (!state.fullText) return;
    const cur = state.page;
    state.pages = paginateClient(state.fullText, charsPerPage());
    if (state.appendixPage && state.appendixPage <= state.pages.length) {
      /* appendix_page stable under canonical PAGE_CHARS */
    }
    setPage(Math.min(cur, state.pages.length));
  }

  async function fetchFullText(bookId) {
    const res = await fetch(`/api/library/full?book=${encodeURIComponent(bookId)}`, { cache: "no-store" });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "read_failed");
    return data;
  }

  async function issueSecureSession(bookId, bookMeta) {
    const res = await fetch("/Hostess7/api/library/reader/issue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ book_id: bookId, book: bookMeta || null }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "reader_issue_failed");
    return data.session;
  }

  function sessionHeaders() {
    if (!state.session) return {};
    return {
      "Content-Type": "application/json",
      "X-Reader-Token": state.session.token,
      "X-Reader-Signature": state.session.signature,
    };
  }

  async function readerPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: sessionHeaders(),
      body: JSON.stringify({ ...body, book_id: state.bookId, token: state.session?.token, signature: state.session?.signature }),
    });
    return res.json();
  }

  function formatElapsed(ms) {
    const s = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return `${h}:${String(m % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
    return `${m}:${String(s % 60).padStart(2, "0")}`;
  }

  function checkoutDueLabel() {
    const co = state.book?.checkout;
    if (!co || co.status !== "active") return "";
    if (co.infinite) return "Loan · ∞";
    if (co.overdue) return `Overdue · ${Math.abs(co.days_left || 0)}d`;
    if (co.due_at) return `Due ${String(co.due_at).slice(0, 10)}`;
    return "";
  }

  function startReadTimer() {
    stopReadTimer();
    state.readStartedAt = Date.now();
    const tick = () => {
      const el = overlay?.querySelector(".h7r-read-timer");
      if (!el || !state.readStartedAt) return;
      const elapsed = formatElapsed(Date.now() - state.readStartedAt);
      const due = checkoutDueLabel();
      const est = state.book?.reading_time_min ? `~${state.book.reading_time_min} min` : "";
      el.textContent = [elapsed, due, est].filter(Boolean).join(" · ");
    };
    tick();
    state.readTimerInterval = setInterval(tick, 1000);
  }

  function stopReadTimer() {
    if (state.readTimerInterval) {
      clearInterval(state.readTimerInterval);
      state.readTimerInterval = null;
    }
    state.readStartedAt = null;
  }

  function scheduleProgressSave() {
    if (!state.session) return;
    clearTimeout(state.progressTimer);
    state.progressTimer = setTimeout(() => {
      readerPost("/api/library/reader/progress", {
        page: state.page,
        page_count: state.pages.length,
      }).catch(() => {});
    }, 600);
  }

  function saveLayoutRemote() {
    if (!state.session) return;
    readerPost("/api/library/reader/layout", {
      layout: { ...state.prefs, brailleMode: state.brailleMode },
    }).catch(() => {});
  }

  function announce(msg) {
    if (global.NexusBraille?.announce) NexusBraille.announce(msg);
    else {
      const el = document.getElementById("nexus-a11y-announcer");
      if (el) el.textContent = String(msg || "");
    }
  }

  async function openSecure(bookId, bookMeta, opts) {
    loadPrefs();
    state.bookId = bookId;
    state.book = bookMeta || null;
    state.brailleMode = !!(opts?.braille ?? global.NexusBraille?.brailleReaderOn?.());
    state.loading = true;
    state.session = null;
    state.bookmarks = [];
    ensureOverlay();
    renderChrome();
    announce(`Librarian opening ${bookMeta?.title || bookId}…`);
    try {
      const session = await issueSecureSession(bookId, bookMeta);
      state.session = session;
      state.librarian = session.librarian;
      state.book = session.book || bookMeta;
      state.bookmarks = session.bookmarks || [];
      state.pageChars = Number(session.page_chars) || 3200;
      state.canonicalPages = true;
      state.liesIndex = session.lies_index || null;
      state.allLies = session.all_lies?.lies || session.lies_index?.entries || [];
      state.lieLibrarian = session.lie_librarian || null;
      state.appendixPage = session.appendix_page || null;
      state.corrections = session.corrections || [];
      if (session.layout && Object.keys(session.layout).length) {
        Object.assign(state.prefs, session.layout);
        if (session.layout.brailleMode != null) state.brailleMode = !!session.layout.brailleMode;
      }
      const data = await fetchFullText(bookId);
      state.book = data.book || state.book;
      state.figures = data.figures || {};
      state.fullText = data.text || "";
      state.pages = paginateClient(state.fullText, state.pageChars);
      const resume = session.progress?.page;
      state.page = resume && resume <= state.pages.length ? resume : 1;
      state.loading = false;
      renderContent();
      renderChrome();
      announce(`${state.librarian?.name || "Librarian"} issued secure reader — page ${state.page} of ${state.pages.length}.`);
      startReadTimer();
    } catch (err) {
      state.loading = false;
      const body = overlay.querySelector(".h7r-body");
      if (body) body.innerHTML = `<div class="h7r-error">Could not open book: ${esc(err.message || err)}</div>`;
    }
  }

  async function open(bookId, bookMeta, opts) {
    if (opts?.secure !== false) {
      return openSecure(bookId, bookMeta, opts);
    }
    loadPrefs();
    state.bookId = bookId;
    state.book = bookMeta || null;
    state.brailleMode = !!(opts?.braille ?? global.NexusBraille?.brailleReaderOn?.());
    state.loading = true;
    state.session = null;
    ensureOverlay();
    renderChrome();
    announce(`Opening ${bookMeta?.title || bookId} in accessible reader.`);
    try {
      const data = await fetchFullText(bookId);
      state.book = data.book || bookMeta;
      state.figures = data.figures || {};
      state.fullText = data.text || "";
      state.pageChars = 3200;
      state.canonicalPages = true;
      state.pages = paginateClient(state.fullText, state.pageChars);
      state.page = 1;
      state.loading = false;
      renderContent();
      renderChrome();
      startReadTimer();
    } catch (err) {
      state.loading = false;
      const body = overlay.querySelector(".h7r-body");
      if (body) body.innerHTML = `<div class="h7r-error">Could not open book: ${esc(err.message || err)}</div>`;
    }
  }

  function close() {
    if (overlay) overlay.classList.remove("open");
    state.bookId = null;
    state.pages = [];
    state.session = null;
    clearTimeout(state.progressTimer);
    stopReadTimer();
    document.body.style.overflow = "";
  }

  function setPage(n) {
    const max = state.pages.length || 1;
    state.page = Math.max(1, Math.min(n, max));
    renderContent();
    renderChrome();
    const body = overlay?.querySelector(".h7r-body");
    if (body) body.scrollTop = 0;
    announce(`Page ${state.page} of ${max}`);
    scheduleProgressSave();
  }

  function prevPage() {
    if (state.page > 1) setPage(state.page - 1);
  }

  function nextPage() {
    if (state.page < state.pages.length) setPage(state.page + 1);
  }

  function applyPrefs() {
    savePrefs();
    if (state.bookId && state.fullText) {
      repaginateCanonical();
    }
    renderContent();
    renderChrome();
  }

  async function addBookmark() {
    if (!state.session) return;
    const label = prompt("Bookmark label (optional):", `Page ${state.page}`) || `Page ${state.page}`;
    const data = await readerPost("/api/library/reader/bookmarks", { action: "add", page: state.page, label });
    if (data.ok) {
      state.bookmarks = data.bookmarks || [];
      renderChrome();
      announce(`Bookmark saved — page ${state.page}.`);
    }
  }

  async function deleteBookmark(id) {
    if (!state.session) return;
    const data = await readerPost("/api/library/reader/bookmarks", { action: "delete", bookmark_id: id });
    if (data.ok) {
      state.bookmarks = data.bookmarks || [];
      renderChrome();
    }
  }

  function onKeyDown(ev) {
    if (!overlay?.classList.contains("open")) return;
    if (ev.key === "ArrowLeft" || ev.key === "ArrowUp" || ev.key === "PageUp") {
      ev.preventDefault();
      prevPage();
    } else if (ev.key === "ArrowRight" || ev.key === "ArrowDown" || ev.key === "PageDown") {
      ev.preventDefault();
      nextPage();
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      close();
    } else if (ev.key === "Home") {
      ev.preventDefault();
      setPage(1);
    } else if (ev.key === "End") {
      ev.preventDefault();
      setPage(state.pages.length);
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key === "d") {
      ev.preventDefault();
      addBookmark();
    }
  }

  function onTouchStart(ev) {
    if (!ev.touches?.length) return;
    state.touchStartY = ev.touches[0].clientY;
    state.touchStartX = ev.touches[0].clientX;
  }

  function onTouchEnd(ev) {
    if (!ev.changedTouches?.length) return;
    const dy = ev.changedTouches[0].clientY - state.touchStartY;
    const dx = ev.changedTouches[0].clientX - state.touchStartX;
    if (Math.abs(dy) < 40 && Math.abs(dx) < 40) return;
    if (Math.abs(dy) >= Math.abs(dx)) {
      if (dy < 0) nextPage();
      else prevPage();
    } else {
      if (dx < 0) nextPage();
      else prevPage();
    }
  }

  function ensureOverlay() {
    if (overlay) {
      overlay.classList.add("open");
      document.body.style.overflow = "hidden";
      return;
    }
    overlay = document.createElement("div");
    overlay.id = "h7-reader-overlay";
    overlay.className = "h7r-overlay";
    overlay.innerHTML = `
      <div class="h7r-shell" role="dialog" aria-modal="true" aria-label="Secure accessible book reader">
        <header class="h7r-top"></header>
        <div class="h7r-body-wrap"><article class="h7r-body" tabindex="0" aria-live="polite" aria-atomic="true"></article></div>
        <aside class="h7r-bookmarks" id="h7r-bookmarks" hidden aria-label="Bookmarks"></aside>
        <aside class="h7r-lies-index" id="h7r-lies-index" hidden aria-label="Deception Index — Autonomous Warfare corpus gate"></aside>
        <div class="h7r-truth-panel" id="h7r-truth-panel" hidden role="complementary" aria-label="Ironclad truth readout for selected sentence"></div>
        <div class="h7r-braille-strip" id="h7r-braille-strip" hidden aria-label="Braille line for refreshable display"></div>
        <footer class="h7r-bottom"></footer>
        <button type="button" class="h7r-close" aria-label="Close reader">✕</button>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector(".h7r-close").addEventListener("click", close);
    overlay.querySelector(".h7r-body").addEventListener("touchstart", onTouchStart, { passive: true });
    overlay.querySelector(".h7r-body").addEventListener("touchend", onTouchEnd, { passive: true });
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", () => {
      if (!overlay?.classList.contains("open") || !state.bookId || state.canonicalPages) return;
      repaginateCanonical();
    });
    document.body.style.overflow = "hidden";
    overlay.classList.add("open");
  }

  function renderBookmarks() {
    const panel = overlay?.querySelector("#h7r-bookmarks");
    if (!panel) return;
    const has = state.bookmarks.length > 0;
    panel.hidden = !has && !state.session;
    if (!state.session) { panel.hidden = true; return; }
    panel.innerHTML = `
      <div class="h7r-bm-head">Bookmarks <button type="button" class="h7r-bm-add">+ Add</button></div>
      <ul class="h7r-bm-list">${state.bookmarks.map((b) =>
        `<li><button type="button" class="h7r-bm-jump" data-page="${b.page}">${esc(b.label || `p${b.page}`)}</button>
         <button type="button" class="h7r-bm-del" data-id="${esc(b.id)}" aria-label="Remove bookmark">×</button></li>`
      ).join("") || '<li class="h7r-bm-empty">No bookmarks — Ctrl+D to add</li>'}</ul>`;
    panel.querySelector(".h7r-bm-add")?.addEventListener("click", addBookmark);
    panel.querySelectorAll(".h7r-bm-jump").forEach((btn) => {
      btn.addEventListener("click", () => setPage(Number(btn.dataset.page)));
    });
    panel.querySelectorAll(".h7r-bm-del").forEach((btn) => {
      btn.addEventListener("click", () => deleteBookmark(btn.dataset.id));
    });
  }

  function renderChrome() {
    if (!overlay) return;
    const top = overlay.querySelector(".h7r-top");
    const bottom = overlay.querySelector(".h7r-bottom");
    const title = state.book?.title || state.bookId || "H7 Reader";
    const libName = state.librarian?.name || "";
    const fontOpts = (state.fonts.length ? state.fonts : [{ id: "georgia", label: "Georgia" }])
      .map((f) => `<option value="${esc(f.id)}"${f.id === state.prefs.fontId ? " selected" : ""}>${esc(f.label)}</option>`)
      .join("");
    const ratioOpts = RATIOS.map(
      (r) => `<option value="${esc(r.id)}"${r.id === state.prefs.ratioId ? " selected" : ""}>${esc(r.label)}</option>`
    ).join("");
    const themeOpts = Object.entries(THEMES).map(
      ([id, t]) => `<option value="${esc(id)}"${id === state.prefs.themeId ? " selected" : ""}>${esc(t.label)}</option>`
    ).join("");

    top.innerHTML = `
      <div class="h7r-title-wrap">
        <div class="h7r-title" id="h7r-title">${esc(title)}</div>
        ${libName ? `<div class="h7r-librarian">Issued by ${esc(libName)} · secure local reader</div>` : ""}
        ${state.book?.description ? `<div class="h7r-desc">${esc(state.book.description.slice(0, 160))}${state.book.description.length > 160 ? "…" : ""}</div>` : ""}
      </div>
      <div class="h7r-controls">
        <label><input type="checkbox" class="h7r-braille-toggle" ${state.brailleMode ? "checked" : ""}> Braille</label>
        <label>Theme <select class="h7r-theme" aria-label="Reading theme">${themeOpts}</select></label>
        <label>Size <input type="range" min="12" max="36" step="1" class="h7r-fs" value="${state.prefs.fontSize}" aria-label="Font size"></label>
        <label>Line <input type="range" min="1.2" max="2.2" step="0.05" class="h7r-lh" value="${state.prefs.lineHeight}" aria-label="Line height"></label>
        <label>Margin <input type="range" min="0" max="48" step="2" class="h7r-margin" value="${state.prefs.marginPx}" aria-label="Side margin"></label>
        <label>Text <input type="color" class="h7r-fg" value="${state.prefs.fontColor}" aria-label="Text color"></label>
        <label>Bg <input type="color" class="h7r-bg" value="${state.prefs.bgColor}" aria-label="Background color"></label>
        <label>Font <select class="h7r-font" aria-label="Font">${fontOpts}</select></label>
        <label>Ratio <select class="h7r-ratio" aria-label="Page ratio">${ratioOpts}</select></label>
        <button type="button" class="h7r-bm-toolbar" title="Bookmark this page (Ctrl+D)">🔖</button>
        <button type="button" class="h7r-lies-toolbar" title="Deception index — LIKELY_FALSE flags">Deception</button>
        ${state.appendixPage ? `<button type="button" class="h7r-appendix-jump" title="Jump to appendix">Appendix p${state.appendixPage}</button>` : ""}
      </div>`;

    const max = Math.max(1, state.pages.length);
    const timerText = state.readStartedAt
      ? formatElapsed(Date.now() - state.readStartedAt)
      : "0:00";
    const due = checkoutDueLabel();
    bottom.innerHTML = `
      <button type="button" class="h7r-nav h7r-prev" ${state.page <= 1 ? "disabled" : ""}>◀</button>
      <div class="h7r-slider-wrap">
        <input type="range" class="h7r-slider" min="1" max="${max}" value="${state.page}">
        <span class="h7r-page-label">${state.page} / ${max}</span>
      </div>
      <span class="h7r-read-timer" aria-live="off">${esc([timerText, due].filter(Boolean).join(" · "))}</span>
      <button type="button" class="h7r-nav h7r-next" ${state.page >= max ? "disabled" : ""}>▶</button>`;

    top.querySelector(".h7r-theme").addEventListener("change", (e) => {
      applyTheme(e.target.value);
      applyPrefs();
    });
    top.querySelector(".h7r-fs").addEventListener("input", (e) => {
      state.prefs.fontSize = Number(e.target.value);
      applyPrefs();
    });
    top.querySelector(".h7r-lh").addEventListener("input", (e) => {
      state.prefs.lineHeight = Number(e.target.value);
      applyPrefs();
    });
    top.querySelector(".h7r-margin").addEventListener("input", (e) => {
      state.prefs.marginPx = Number(e.target.value);
      applyPrefs();
    });
    top.querySelector(".h7r-fg").addEventListener("input", (e) => {
      state.prefs.fontColor = e.target.value;
      state.prefs.themeId = "custom";
      applyPrefs();
    });
    top.querySelector(".h7r-bg").addEventListener("input", (e) => {
      state.prefs.bgColor = e.target.value;
      state.prefs.themeId = "custom";
      applyPrefs();
    });
    top.querySelector(".h7r-font").addEventListener("change", (e) => {
      state.prefs.fontId = e.target.value;
      applyPrefs();
    });
    top.querySelector(".h7r-ratio").addEventListener("change", (e) => {
      state.prefs.ratioId = e.target.value;
      applyPrefs();
    });
    top.querySelector(".h7r-braille-toggle")?.addEventListener("change", (e) => {
      state.brailleMode = !!e.target.checked;
      renderContent();
      saveLayoutRemote();
      announce(state.brailleMode ? "Braille line on." : "Braille line off.");
    });
    top.querySelector(".h7r-bm-toolbar")?.addEventListener("click", addBookmark);
    top.querySelector(".h7r-lies-toolbar")?.addEventListener("click", toggleLiesIndex);
    top.querySelector(".h7r-appendix-jump")?.addEventListener("click", () => {
      if (state.appendixPage) setPage(state.appendixPage);
    });
    bottom.querySelector(".h7r-prev")?.addEventListener("click", prevPage);
    bottom.querySelector(".h7r-next")?.addEventListener("click", nextPage);
    bottom.querySelector(".h7r-slider")?.addEventListener("input", (e) => setPage(Number(e.target.value)));
    renderBookmarks();
    renderLiesIndex();
  }

  function toggleLiesIndex() {
    const panel = overlay?.querySelector("#h7r-lies-index");
    if (!panel) return;
    panel.hidden = !panel.hidden;
    if (!panel.hidden) renderLiesIndex();
  }

  function renderLiesIndex() {
    const panel = overlay?.querySelector("#h7r-lies-index");
    if (!panel) return;
    const entries = state.allLies.length ? state.allLies : (state.liesIndex?.entries || []);
    if (!entries.length) {
      panel.hidden = true;
      return;
    }
    const libName = state.lieLibrarian?.name || "Lie Librarian — Ironclad Deception Index";
    const total = state.liesIndex?.total_lie_count || entries.length;
    panel.innerHTML = `
      <div class="h7r-lies-head">Deception Index — ${esc(libName)} <button type="button" class="h7r-lies-close">×</button></div>
      <p class="h7r-lies-note">${total} flagged claim(s) · Autonomous Warfare corpus gate · verify before fielding · p.${state.pageChars} chars/page</p>
      <ol class="h7r-lies-list">${entries.map((e) => {
        const fh = e.for_humans || {};
        const label = fh.likely_label || (e.likely_false ? "likely false" : "uncertain");
        const assessment = fh.assessment || "";
        return `<li><button type="button" class="h7r-lies-jump" data-page="${e.page}" data-idx="${e.sentence_index}">
          <span class="h7r-lies-rank">#${e.rank}</span>
          <span class="h7r-lies-label">${esc(label)}</span> p.${e.page}
          ${assessment ? `<span class="h7r-lies-assessment">${esc(assessment)}</span>` : `<span class="h7r-lies-excerpt">${esc((e.excerpt || "").slice(0, 100))}</span>`}
        </button></li>`;
      }).join("")}</ol>`;
    panel.querySelector(".h7r-lies-close")?.addEventListener("click", () => { panel.hidden = true; });
    panel.querySelectorAll(".h7r-lies-jump").forEach((btn) => {
      btn.addEventListener("click", () => setPage(Number(btn.dataset.page)));
    });
  }

  function renderContent() {
    if (!overlay) return;
    const body = overlay.querySelector(".h7r-body");
    const wrap = overlay.querySelector(".h7r-body-wrap");
    const ratio = ratioSpec();
    const p = state.prefs;
    const brailleStrip = overlay.querySelector("#h7r-braille-strip");
    if (state.loading) {
      body.textContent = "Librarian opening secure reader…";
      body.setAttribute("aria-busy", "true");
      if (brailleStrip) brailleStrip.hidden = true;
      return;
    }
    body.removeAttribute("aria-busy");
    wrap.style.background = p.bgColor;
    wrap.style.padding = `12px ${p.marginPx}px`;
    body.style.color = p.fontColor;
    body.style.background = p.bgColor;
    body.style.fontSize = `${p.fontSize}px`;
    body.style.lineHeight = String(p.lineHeight);
    body.style.fontFamily = fontFamily();
    body.style.maxWidth = ratio.maxWidth;
    body.style.width = ratio.width;
    body.style.margin = "0 auto";
    const text = state.pages[state.page - 1] || "";
    body.innerHTML = renderSentencesHtml(text, sentenceBaseForPage(state.page));
    body.querySelectorAll(".h7r-sentence").forEach((el) => {
      el.addEventListener("click", () => onSentenceClick(el));
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          onSentenceClick(el);
        }
      });
    });
    body.setAttribute("aria-label", `${state.book?.title || state.bookId || "Book"} page ${state.page} of ${state.pages.length}`);
    if (brailleStrip) {
      const show = state.brailleMode && global.NexusBraille?.toBraille;
      brailleStrip.hidden = !show;
      if (show) {
        const sample = text.slice(0, 280);
        brailleStrip.textContent = NexusBraille.toBraille(sample);
      }
    }
  }

  function setFonts(fonts) {
    state.fonts = Array.isArray(fonts) ? fonts : [];
  }

  function splitSentences(text) {
    const t = String(text || "").replace(/\r\n/g, "\n").trim();
    if (!t) return [];
    const parts = t.split(/(?<=[.!?])\s+(?=[A-Z0-9"'])/);
    return parts.map((s) => s.trim()).filter((s) => s.length >= 8);
  }

  function renderBlockHtml(block, sentenceBase = 0) {
    const figRe = /!\[([^\]]*)\]\(h7fig:([a-zA-Z0-9_.-]+)\)/g;
    if (figRe.test(block)) {
      figRe.lastIndex = 0;
      return block.replace(figRe, (_, alt, id) => {
        const f = state.figures[id];
        if (f && f.data_url) {
          return `<figure class="h7r-figure"><img src="${f.data_url}" alt="${esc(alt || id)}" /><figcaption>${esc(alt || id)}</figcaption></figure>`;
        }
        return `<p class="h7r-fig-missing">[figure: ${esc(id)}]</p>`;
      }).replace(/^### (.+)$/gm, "<h3 class='h7r-h3'>$1</h3>").replace(/^## (.+)$/gm, "<h2 class='h7r-h2'>$1</h2>").replace(/^# (.+)$/gm, "<h1 class='h7r-h1'>$1</h1>");
    }
    const sents = splitSentences(block);
    if (!sents.length) return esc(block);
    return sents.map((s, i) => {
      const gidx = sentenceBase + i;
      return `<span class="h7r-sentence" tabindex="0" role="button" data-sentence-index="${gidx}" data-page="${state.page}" aria-label="Truth check page ${state.page} sentence ${i + 1}">${esc(s)}</span>`;
    }).join(" ");
  }

  function renderSentencesHtml(text, sentenceBase = 0) {
    const t = String(text || "");
    if (/^#+ /.m.test(t) || /h7fig:/.test(t)) {
      return renderBlockHtml(t, sentenceBase);
    }
    const sents = splitSentences(t);
    if (!sents.length) return esc(t);
    return sents.map((s, i) => {
      const gidx = sentenceBase + i;
      return `<span class="h7r-sentence" tabindex="0" role="button" data-sentence-index="${gidx}" data-page="${state.page}" aria-label="Truth check page ${state.page} sentence ${i + 1}">${esc(s)}</span>`;
    }).join(" ");
  }

  async function onSentenceClick(el) {
    const idx = Number(el.dataset.sentenceIndex);
    const panel = overlay?.querySelector("#h7r-truth-panel");
    if (!panel || !state.bookId) return;
    panel.hidden = false;
    panel.innerHTML = `<div class="h7r-truth-loading">Ironclad truth filter…</div>`;
    announce("Checking sentence truth through Ironclad.");
    try {
      const q = new URLSearchParams({
        book: state.bookId,
        index: String(idx),
        text: el.textContent || "",
      });
      const res = await fetch(`/api/library/truth?${q}`, { cache: "no-store" });
      const data = await res.json();
      renderTruthPanel(panel, data);
      el.classList.remove("h7r-verdict-clear", "h7r-verdict-questionable", "h7r-verdict-unknown");
      if (data.verdict) el.classList.add(`h7r-verdict-${data.verdict}`);
      announce(`${data.verdict || "truth"} — ${data.truth_score || "?"} percent.`);
    } catch (err) {
      panel.innerHTML = `<div class="h7r-truth-error">Truth check failed: ${esc(err.message || err)}</div>`;
    }
  }

  function renderTruthPanel(panel, data) {
    const v = data.verdict || "unknown";
    let html = `<div class="h7r-truth-verdict ${esc(v)}">${esc(v)}</div>`;
    const pageLine = data.page ? `Page <strong>${esc(String(data.page))}</strong>${data.sentence_on_page ? ` · sentence ${esc(String(data.sentence_on_page))}` : ""} · ` : "";
    const likelyLabel = data.likely_false_class
      ? esc(String(data.likely_false_class).replace(/_/g, " "))
      : (data.verdict === "questionable" ? "likely false" : data.verdict || "");
    html += `<div>${pageLine}<span class="h7r-likely-label">${likelyLabel}</span> · Truth score: <strong>${esc(String(data.truth_score ?? "?"))}%</strong> · Ironclad ${esc(data.ironclad?.verdict || "?")}${data.ironclad?.sealed ? " (sealed)" : ""}</div>`;
    const assessment = data.for_humans?.assessment;
    if (assessment) {
      html += `<p class="h7r-truth-assessment">${esc(assessment)}</p>`;
    }
    html += `<p>${esc(data.readout || "")}</p>`;
    if (data.clearer_statement) html += `<p><strong>Clearer:</strong> ${esc(data.clearer_statement)}</p>`;
    if (data.concise_truth) html += `<p><strong>Concise truth:</strong> ${esc(data.concise_truth)}</p>`;
    if (data.questionable_aspects?.length) html += `<p><strong>Questionable:</strong> ${esc(data.questionable_aspects.join(", "))}</p>`;
    if (data.investigation?.hints?.length) {
      html += `<p><strong>Investigate unknown:</strong></p><ul>${data.investigation.hints.map((h) => `<li>${esc(h)}</li>`).join("")}</ul>`;
    }
    panel.innerHTML = html;
  }

  global.H7Reader = { open, openSecure, close, setFonts, setPage, prevPage, nextPage, addBookmark };
})(window);