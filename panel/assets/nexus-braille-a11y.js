/**
 * NEXUS Braille & blind-operator accessibility — Grade 1 braille, screen reader hooks,
 * keyboard routes to Library, alphabetical book listbox.
 */
(function (global) {
  "use strict";

  const STORAGE_BLIND = "nexus_blind_mode";
  const STORAGE_BRAILLE_READER = "nexus_braille_reader_on";

  const CHAR_MAP = {
    a: "⠁", b: "⠃", c: "⠉", d: "⠙", e: "⠑", f: "⠋", g: "⠛", h: "⠓", i: "⠊", j: "⠚",
    k: "⠅", l: "⠇", m: "⠍", n: "⠝", o: "⠕", p: "⠏", q: "⠟", r: "⠗", s: "⠎", t: "⠞",
    u: "⠥", v: "⠧", w: "⠺", x: "⠭", y: "⠽", z: "⠵",
    "1": "⠁", "2": "⠃", "3": "⠉", "4": "⠙", "5": "⠑", "6": "⠋", "7": "⠛", "8": "⠓", "9": "⠊", "0": "⠚",
    " ": " ", "\n": "\n",
    ",": "⠂", ";": "⠆", ":": "⠒", ".": "⠲", "!": "⠖", "?": "⠦", "-": "⠤", "'": "⠄",
    "(": "⠷", ")": "⠾", "/": "⠌", "&": "⠯",
  };

  const CAP = "⠠";
  const NUM = "⠼";

  let announcer = null;
  let listboxBound = false;

  function $(id) {
    return document.getElementById(id);
  }

  function toBraille(text, { capitals = true, numbers = true } = {}) {
    const raw = String(text ?? "");
    let out = "";
    let inNumber = false;
    for (let i = 0; i < raw.length; i++) {
      const ch = raw[i];
      const low = ch.toLowerCase();
      if (numbers && ch >= "0" && ch <= "9") {
        if (!inNumber) {
          out += NUM;
          inNumber = true;
        }
        out += CHAR_MAP[ch] || ch;
        continue;
      }
      inNumber = false;
      if (ch >= "A" && ch <= "Z" && capitals) {
        out += CAP + (CHAR_MAP[low] || low);
        continue;
      }
      if (ch >= "a" && ch <= "z") {
        out += CHAR_MAP[low] || low;
        continue;
      }
      out += CHAR_MAP[ch] ?? ch;
    }
    return out;
  }

  function announce(message, { polite = true } = {}) {
    const el = announcer || $("nexus-a11y-announcer");
    if (!el || !message) return;
    announcer = el;
    el.setAttribute("aria-live", polite ? "polite" : "assertive");
    el.textContent = "";
    requestAnimationFrame(() => {
      el.textContent = String(message);
    });
  }

  function blindModeOn() {
    return document.documentElement.classList.contains("nexus-blind-mode");
  }

  function setBlindMode(on) {
    document.documentElement.classList.toggle("nexus-blind-mode", !!on);
    try {
      localStorage.setItem(STORAGE_BLIND, on ? "1" : "0");
    } catch (_) {}
    const btn = $("nexus-blind-mode-toggle");
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
    announce(on ? "Blind-friendly mode on — stronger focus rings and larger base text." : "Blind-friendly mode off.");
  }

  function brailleReaderOn() {
    try {
      return localStorage.getItem(STORAGE_BRAILLE_READER) !== "0";
    } catch (_) {
      return true;
    }
  }

  function setBrailleReaderOn(on) {
    try {
      localStorage.setItem(STORAGE_BRAILLE_READER, on ? "1" : "0");
    } catch (_) {}
    const btn = $("nexus-braille-reader-toggle");
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function sortBooksAlpha(books) {
    return [...(books || [])].sort((a, b) =>
      String(a?.title || a?.id || "").localeCompare(String(b?.title || b?.id || ""), undefined, {
        sensitivity: "base",
        numeric: true,
      })
    );
  }

  function bookLabel(book) {
    if (!book) return "No book selected";
    const parts = [book.title, book.author, book.dewey ? `Dewey ${book.dewey}` : ""].filter(Boolean);
    return parts.join(" by ").replace(" by Dewey", " · Dewey");
  }

  function updateLibraryBraille(book, { index, total } = {}) {
    const out = $("library-braille-output");
    const plain = $("library-braille-plain");
    const openBtn = $("library-braille-open-reader");
    if (!out) return;
    if (!book) {
      out.textContent = toBraille("Select a book from the A to Z list.");
      if (plain) plain.textContent = "Use arrow keys in the book list. Press Enter to open the accessible reader.";
      if (openBtn) openBtn.disabled = true;
      return;
    }
    const label = bookLabel(book);
    const pos = index != null && total ? ` · ${index + 1} of ${total}` : "";
    const line = `${label}${pos}`;
    out.textContent = toBraille(line);
    if (plain) {
      plain.textContent = line + (book.format ? ` · ${book.format}` : "");
    }
    if (openBtn) openBtn.disabled = book.ready === false;
    announce(`${book.title || book.id}${pos}. Braille line updated.`);
  }

  function wireLibraryListbox(shelfEl, onSelect) {
    if (!shelfEl || listboxBound) return;
    listboxBound = true;

    shelfEl.addEventListener("keydown", (ev) => {
      const opts = [...shelfEl.querySelectorAll('[role="option"]')];
      if (!opts.length) return;
      const cur = opts.findIndex((o) => o.getAttribute("aria-selected") === "true");
      let next = cur;
      if (ev.key === "ArrowDown" || ev.key === "ArrowRight") {
        ev.preventDefault();
        next = Math.min(opts.length - 1, cur < 0 ? 0 : cur + 1);
      } else if (ev.key === "ArrowUp" || ev.key === "ArrowLeft") {
        ev.preventDefault();
        next = Math.max(0, cur < 0 ? 0 : cur - 1);
      } else if (ev.key === "Home") {
        ev.preventDefault();
        next = 0;
      } else if (ev.key === "End") {
        ev.preventDefault();
        next = opts.length - 1;
      } else if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        const sel = opts[cur >= 0 ? cur : 0];
        if (sel?.dataset?.bookId) onSelect?.(sel.dataset.bookId, { openReader: ev.key === "Enter" && ev.shiftKey });
        return;
      } else {
        return;
      }
      const opt = opts[next];
      if (!opt?.dataset?.bookId) return;
      opts.forEach((o, i) => {
        o.setAttribute("aria-selected", i === next ? "true" : "false");
        o.tabIndex = i === next ? 0 : -1;
      });
      shelfEl.setAttribute("aria-activedescendant", opt.id || "");
      onSelect?.(opt.dataset.bookId);
      opt.scrollIntoView({ block: "nearest" });
    });
  }

  function renderBookListbox(shelfEl, books, selectedId, onSelect) {
    if (!shelfEl) return;
    const sorted = sortBooksAlpha(books.filter((b) => b.ready !== false));
    if (!sorted.length) {
      shelfEl.removeAttribute("role");
      return sorted;
    }
    shelfEl.setAttribute("role", "listbox");
    shelfEl.setAttribute("aria-label", "Books alphabetically A to Z");
    shelfEl.setAttribute("tabindex", "0");
    shelfEl.classList.add("library-a11y-listbox");

    const head = `<div class="library-shelf-head" aria-hidden="true">${sorted.length} books · A → Z</div>`;
    shelfEl.innerHTML =
      head +
      sorted
        .map((b, i) => {
          const sel = b.id === selectedId;
          const optId = `lib-book-${String(b.id).replace(/[^a-zA-Z0-9_-]/g, "_")}`;
          return `<button type="button" role="option" id="${optId}" class="library-book-option${
            sel ? " active" : ""
          }" data-book-id="${escapeAttr(b.id)}" aria-selected="${sel ? "true" : "false"}" tabindex="${sel ? "0" : "-1"}">
            <strong>${escapeHtml(b.title || b.id)}</strong>
            <em>${escapeHtml(b.author || "Unknown author")} · Dewey ${escapeHtml(b.dewey || "?")} · ${escapeHtml(b.format || "H7")}</em>
          </button>`;
        })
        .join("");

    if (selectedId) {
      const active = [...shelfEl.querySelectorAll("[data-book-id]")].find((el) => el.dataset.bookId === selectedId);
      if (active) shelfEl.setAttribute("aria-activedescendant", active.id);
    }

    shelfEl.querySelectorAll("[data-book-id]").forEach((btn) => {
      btn.addEventListener("click", () => onSelect?.(btn.dataset.bookId));
    });
    wireLibraryListbox(shelfEl, onSelect);
    return sorted;
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s);
  }

  function goToLibrary(focusTarget) {
    if (typeof global.showView === "function") global.showView("library");
    announce("Library · field books. Search or browse the A to Z list.");
    requestAnimationFrame(() => {
      const target =
        focusTarget === "search"
          ? $("library-search")
          : focusTarget === "braille"
          ? $("library-braille-output")
          : $("library-shelf");
      target?.focus?.();
    });
  }

  function enhanceNav() {
    document.querySelectorAll('nav.menu button[data-view="library"]').forEach((btn) => {
      btn.setAttribute("aria-keyshortcuts", "Alt+Shift+B");
      const cur = btn.getAttribute("aria-label") || btn.textContent.trim();
      if (!cur.includes("Books")) {
        btn.setAttribute("aria-label", `${cur} · Books tab · Alt Shift B`);
      }
    });
    document.querySelectorAll("nav.menu button[data-view]").forEach((btn) => {
      if (!btn.getAttribute("aria-label")) {
        btn.setAttribute("aria-label", btn.textContent.trim());
      }
    });
  }

  function wireGlobalShortcuts() {
    document.addEventListener("keydown", (ev) => {
      if (ev.altKey && ev.shiftKey && (ev.key === "B" || ev.key === "b")) {
        ev.preventDefault();
        goToLibrary("list");
        return;
      }
      if (ev.altKey && ev.shiftKey && (ev.key === "S" || ev.key === "s")) {
        const lib = $("view-library");
        if (lib?.classList.contains("active")) {
          ev.preventDefault();
          $("library-search")?.focus();
        }
        return;
      }
      if (ev.key === "/" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        const tag = (document.activeElement?.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") return;
        const lib = $("view-library");
        if (lib?.classList.contains("active")) {
          ev.preventDefault();
          $("library-search")?.focus();
        }
      }
    });
  }

  function ensureA11yDialog() {
    let dlg = $("nexus-a11y-dialog");
    if (dlg) return dlg;
    dlg = document.createElement("div");
    dlg.id = "nexus-a11y-dialog";
    dlg.className = "nexus-a11y-dialog";
    dlg.setAttribute("role", "dialog");
    dlg.setAttribute("aria-modal", "true");
    dlg.setAttribute("aria-labelledby", "nexus-a11y-dialog-title");
    dlg.innerHTML = `
      <div class="nexus-a11y-dialog-card">
        <h2 id="nexus-a11y-dialog-title">Keyboard · Braille navigation</h2>
        <dl>
          <dt>Alt + Shift + B</dt><dd>Jump to Library · Books tab</dd>
          <dt>Alt + Shift + S</dt><dd>Focus library search (when on Library)</dd>
          <dt>/ (slash)</dt><dd>Focus library search from Library view</dd>
          <dt>Arrow keys</dt><dd>Move through alphabetical book list</dd>
          <dt>Enter</dt><dd>Select book · Shift+Enter opens accessible reader</dd>
          <dt>Reader arrows</dt><dd>Previous / next page · Escape closes reader</dd>
        </dl>
        <button type="button" id="nexus-a11y-dialog-close" style="margin-top:14px;padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:#1a2430;color:var(--text);cursor:pointer;">Close</button>
      </div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("click", (ev) => {
      if (ev.target === dlg) dlg.classList.remove("open");
    });
    dlg.querySelector("#nexus-a11y-dialog-close")?.addEventListener("click", () => dlg.classList.remove("open"));
    return dlg;
  }

  function wireToolbar() {
    $("nexus-blind-mode-toggle")?.addEventListener("click", () => setBlindMode(!blindModeOn()));
    $("nexus-braille-reader-toggle")?.addEventListener("click", () => {
      const on = !brailleReaderOn();
      setBrailleReaderOn(on);
      announce(on ? "Braille reader output on." : "Braille reader output off.");
    });
    $("nexus-a11y-help")?.addEventListener("click", () => {
      ensureA11yDialog().classList.add("open");
      $("nexus-a11y-dialog-close")?.focus();
    });
    $("nexus-goto-library")?.addEventListener("click", () => goToLibrary("list"));
    $("library-braille-open-reader")?.addEventListener("click", () => {
      const ev = new CustomEvent("nexus-open-braille-reader");
      document.dispatchEvent(ev);
    });
    setBlindMode(localStorage.getItem(STORAGE_BLIND) === "1");
    setBrailleReaderOn(brailleReaderOn());
  }

  function onViewActivated(viewId) {
    const names = {
      command: "Command center",
      us: "US field identity",
      packets: "Packets and connections",
      threats: "Threats and globe",
      intel: "Intelligence",
      signals: "Signals field",
      dns: "Truth DNS",
      outside: "Outside egress gate",
      library: "Library · books A to Z · braille reader ready",
      settings: "Settings",
      logs: "Logs",
    };
    const key = viewId?.split("/")?.[0] || viewId;
    if (names[key]) announce(names[key]);
  }

  function labelViews() {
    const labels = {
      "view-command": "Command center",
      "view-us": "US field identity",

      "view-monitor": "Live connections monitor",
      "view-inspect": "Packet inspect",
      "view-home-protector": "Home protector airspace",
      "view-host-attack": "Host attack map",
      "view-spiderweb": "Terror spiderweb",
      "view-precision-map": "Precision map",
      "view-precision-web": "Precision spiderweb",
      "view-dossier": "Angel dossiers",
      "view-people": "People registry",
      "view-human-dossier": "Human dossiers",
      "view-honor": "Honorability",
      "view-audio-train": "Audio train",
      "view-field-rf": "Field RF sentinel",
      "view-research": "Research tables",
      "view-signals": "Signals field",
      "view-dns": "DNS and DHCP planetary command",
      "view-outside": "Outside egress gate",
      "view-library": "Library field books",
      "view-settings": "Settings",
      "view-logs": "System logs",
    };
    Object.entries(labels).forEach(([id, label]) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (!el.getAttribute("aria-label")) el.setAttribute("aria-label", label);
      if (!el.getAttribute("role")) el.setAttribute("role", "region");
    });
  }

  function init() {
    announcer = $("nexus-a11y-announcer");
    labelViews();
    enhanceNav();
    wireGlobalShortcuts();
    wireToolbar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.NexusBraille = {
    toBraille,
    announce,
    sortBooksAlpha,
    renderBookListbox,
    updateLibraryBraille,
    goToLibrary,
    onViewActivated,
    blindModeOn,
    brailleReaderOn,
    bookLabel,
  };
})(typeof window !== "undefined" ? window : globalThis);