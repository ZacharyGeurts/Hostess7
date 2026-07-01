/**
 * Field Library Bookshelf — Dewey-organized search → shelf → pull book → open reader.
 */
(function (global) {
  "use strict";

  const BOOKS_PER_TIER = 48;
  const TIERS_VISIBLE = 3;
  const SEARCH_LIMIT = 60;
  const SHELF_FETCH_LIMIT = 500;

  const DEWEY_CLASSES = [
    { code: "000", title: "Computer science & general works", slug: "000-computer-science" },
    { code: "100", title: "Philosophy & psychology", slug: "100-philosophy" },
    { code: "200", title: "Religion", slug: "200-religion" },
    { code: "300", title: "Social sciences", slug: "300-social-sciences" },
    { code: "400", title: "Language", slug: "400-language" },
    { code: "500", title: "Science", slug: "500-science" },
    { code: "600", title: "Technology", slug: "600-technology" },
    { code: "700", title: "Arts & recreation", slug: "700-arts" },
    { code: "800", title: "Literature", slug: "800-literature" },
    { code: "900", title: "History & geography", slug: "900-history" },
  ];

  const state = {
    view: "lobby",
    query: "",
    hits: [],
    shelves: [],
    shelfSlug: null,
    shelfTitle: "",
    shelfBooks: [],
    shelfTotal: 0,
    shelfPage: 0,
    selectedBook: null,
    facets: null,
    debounce: null,
  };

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function spineLabel(book) {
    const t = String(book.title || book.id || "").trim();
    if (t.length <= 28) return t;
    return t.slice(0, 26) + "…";
  }

  function spineHue(id) {
    let h = 0;
    const s = String(id || "");
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h % 360;
  }

  function spineStyle(book) {
    const hue = spineHue(book.id);
    const h = 0.82 + ((hue % 17) / 100);
    const w = 28 + Math.min(24, Math.floor(String(book.title || "").length / 4));
    return {
      "--spine-h": String(h),
      "--spine-w": w + "px",
      background: `linear-gradient(90deg, hsl(${hue} 42% 28%), hsl(${hue} 48% 38%) 55%, hsl(${hue} 38% 22%))`,
    };
  }

  function coverStyle(book) {
    const hue = spineHue(book.id);
    return {
      "--cover-a": `hsl(${hue} 45% 32%)`,
      "--cover-b": `hsl(${hue} 38% 22%)`,
    };
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    return res.json();
  }

  function parseRoute() {
    const params = new URLSearchParams(global.location.search);
    const shelf = params.get("shelf") || "";
    const book = params.get("book") || "";
    const q = params.get("q") || "";
    return { shelf, book, q };
  }

  function pushRoute(opts) {
    const params = new URLSearchParams();
    if (opts.q) params.set("q", opts.q);
    if (opts.shelf) params.set("shelf", opts.shelf);
    if (opts.book) params.set("book", opts.book);
    const qs = params.toString();
    const url = global.location.pathname + (qs ? "?" + qs : "");
    global.history.replaceState(null, "", url);
  }

  function setView(name) {
    state.view = name;
    $("bsb-lobby")?.toggleAttribute("hidden", name !== "lobby");
    $("bsb-shelf-view")?.toggleAttribute("hidden", name !== "shelf");
  }

  function renderStats() {
    const el = $("bsb-stats");
    if (!el) return;
    const total = state.facets?.counts?.books || state.shelfTotal || "—";
    const shelves = state.shelves.length || "—";
    el.innerHTML = [
      `<span><strong>${total}</strong> books indexed</span>`,
      `<span><strong>${shelves}</strong> Dewey shelves</span>`,
      `<span>Ironclad Library · Autonomous Warfare corpus gate</span>`,
    ].join(" · ");
  }

  function shelvesForClass(code) {
    const prefix = code + "-";
    return state.shelves.filter((s) => String(s.slug || "").startsWith(prefix) || String(s.slug || "") === code);
  }

  function renderLobby() {
    const grid = $("bsb-dewey-grid");
    const hitsEl = $("bsb-search-hits");
    const empty = $("bsb-lobby-empty");
    if (!grid) return;

    const q = state.query.trim();
    if (q) {
      grid.setAttribute("hidden", "");
      if (hitsEl) {
        hitsEl.removeAttribute("hidden");
        if (!state.hits.length) {
          hitsEl.innerHTML = "";
          empty?.removeAttribute("hidden");
        } else {
          empty?.setAttribute("hidden", "");
          hitsEl.innerHTML = state.hits.map((b) =>
            `<article class="bsb-hit" data-id="${esc(b.id)}" data-shelf="${esc(b.shelf || "")}" tabindex="0" role="button">
              <div class="title">${esc(b.title || b.id)}</div>
              <div class="meta">${esc(b.author || "")} · Dewey ${esc(b.dewey || "?")} · ${esc(b.shelf_title || b.shelf || "")}</div>
            </article>`
          ).join("");
          bindHits();
        }
      }
      return;
    }

    empty?.setAttribute("hidden", "");
    hitsEl?.setAttribute("hidden", "");
    grid.removeAttribute("hidden");

    const used = new Set();
    let html = "";
    for (const cls of DEWEY_CLASSES) {
      const subs = shelvesForClass(cls.code);
      const count = subs.reduce((n, s) => n + (s.count || 0), 0);
      if (!count && !subs.length) continue;
      subs.forEach((s) => used.add(s.slug));
      html += `<div class="bsb-dewey-section">
        <div class="bsb-dewey-section-head">
          <span class="bsb-dewey-code">${esc(cls.code)}</span>
          <span class="bsb-dewey-title">${esc(cls.title)}</span>
          <span class="bsb-dewey-count">${count} books</span>
        </div>
        <div class="bsb-dewey-grid bsb-dewey-subgrid">`;
      for (const sh of subs) {
        html += `<article class="bsb-dewey-card" data-shelf="${esc(sh.slug)}" tabindex="0" role="button">
          <div class="bsb-dewey-code">${esc(sh.code || cls.code)}</div>
          <div class="bsb-dewey-title">${esc(sh.title || sh.slug)}</div>
          <div class="bsb-dewey-count">${esc(sh.count)} books</div>
        </article>`;
      }
      html += `</div></div>`;
    }

    const other = state.shelves.filter((s) => !used.has(s.slug));
    if (other.length) {
      html += `<div class="bsb-dewey-section">
        <div class="bsb-dewey-section-head"><span class="bsb-dewey-title">Other shelves</span></div>
        <div class="bsb-dewey-grid bsb-dewey-subgrid">`;
      for (const sh of other) {
        const main = String(sh.slug || "").split("/")[0].split("-")[0];
        html += `<article class="bsb-dewey-card" data-shelf="${esc(sh.slug)}" tabindex="0" role="button">
          <div class="bsb-dewey-code">${esc(sh.code || main)}</div>
          <div class="bsb-dewey-title">${esc(sh.title || sh.slug)}</div>
          <div class="bsb-dewey-count">${esc(sh.count)} books</div>
        </article>`;
      }
      html += `</div></div>`;
    }

    grid.innerHTML = html || '<div class="bsb-empty">No shelves indexed yet.</div>';
    bindLobbyCards();
  }

  function bindLobbyCards() {
    document.querySelectorAll(".bsb-dewey-card[data-shelf]").forEach((el) => {
      const open = () => openShelf(el.dataset.shelf);
      el.addEventListener("click", open);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); }
      });
    });
  }

  function bindHits() {
    $("bsb-search-hits")?.querySelectorAll(".bsb-hit").forEach((el) => {
      const pick = () => openShelf(el.dataset.shelf, el.dataset.id);
      el.addEventListener("click", pick);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); }
      });
    });
  }

  async function loadFacets() {
    const doc = await fetchJson("/api/dewey-index/facets");
    state.facets = doc;
    const shelfFacet = doc?.facets?.shelf || {};
    if (typeof shelfFacet === "object" && !Array.isArray(shelfFacet)) {
      state.shelves = Object.entries(shelfFacet)
        .map(([slug, count]) => ({
          slug,
          count,
          code: slug.split("-")[0],
          title: slug.replace(/-/g, " ").replace(/\//g, " · "),
        }))
        .sort((a, b) => a.slug.localeCompare(b.slug));
    }
    renderStats();
    renderLobby();
  }

  async function searchBooks(q) {
    state.query = q;
    pushRoute({ q });
    if (!q.trim()) {
      state.hits = [];
      renderLobby();
      return;
    }
    const doc = await fetchJson(
      "/api/dewey-index/search?q=" + encodeURIComponent(q) + "&limit=" + SEARCH_LIMIT
    );
    state.hits = doc.hits || [];
    renderLobby();
  }

  async function loadShelfBooks(slug, page) {
    const offset = page * BOOKS_PER_TIER * TIERS_VISIBLE;
    const doc = await fetchJson(
      "/api/dewey-index/search?shelf=" + encodeURIComponent(slug) +
      "&limit=" + SHELF_FETCH_LIMIT
    );
    const all = (doc.hits || []).sort((a, b) =>
      String(a.title || a.id).localeCompare(String(b.title || b.id), undefined, { sensitivity: "base" })
    );
    state.shelfTotal = doc.total_pool || all.length;
    state.shelfBooks = all;
    state.shelfPage = page;
    const first = all[0];
    state.shelfTitle = first?.shelf_title || slug.replace(/-/g, " ").replace(/\//g, " · ");
  }

  function pageSlice() {
    const start = state.shelfPage * BOOKS_PER_TIER * TIERS_VISIBLE;
    return state.shelfBooks.slice(start, start + BOOKS_PER_TIER * TIERS_VISIBLE);
  }

  function renderShelf() {
    const books = pageSlice();
    const tiers = [];
    for (let i = 0; i < books.length; i += BOOKS_PER_TIER) {
      tiers.push(books.slice(i, i + BOOKS_PER_TIER));
    }
    while (tiers.length < TIERS_VISIBLE) tiers.push([]);

    const bookcase = $("bsb-bookcase");
    const titleEl = $("bsb-shelf-title");
    const crumb = $("bsb-breadcrumb");
    const pager = $("bsb-shelf-pager");
    const pulled = $("bsb-pulled");

    if (titleEl) titleEl.textContent = state.shelfTitle || state.shelfSlug || "Bookshelf";
    if (crumb) {
      crumb.innerHTML = '<a href="#" id="bsb-back-lobby">Library</a> · Dewey · ' + esc(state.shelfSlug || "");
    }
    $("bsb-back-lobby")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      goLobby();
    });

    const pages = Math.max(1, Math.ceil(state.shelfBooks.length / (BOOKS_PER_TIER * TIERS_VISIBLE)));
    if (pager) {
      const from = state.shelfPage * BOOKS_PER_TIER * TIERS_VISIBLE + 1;
      const to = Math.min(state.shelfBooks.length, (state.shelfPage + 1) * BOOKS_PER_TIER * TIERS_VISIBLE);
      pager.innerHTML = `
        <button type="button" class="bsb-btn" id="bsb-prev" ${state.shelfPage <= 0 ? "disabled" : ""}>← Prev</button>
        <span>Books ${from}–${to} of ${state.shelfBooks.length} · section ${state.shelfPage + 1}/${pages}</span>
        <button type="button" class="bsb-btn" id="bsb-next" ${state.shelfPage >= pages - 1 ? "disabled" : ""}>Next →</button>`;
      $("bsb-prev")?.addEventListener("click", () => {
        if (state.shelfPage > 0) { state.shelfPage--; renderShelf(); }
      });
      $("bsb-next")?.addEventListener("click", () => {
        if (state.shelfPage < pages - 1) { state.shelfPage++; renderShelf(); }
      });
    }

    if (bookcase) {
      bookcase.innerHTML = tiers.map((tierBooks) => {
        const spines = tierBooks.map((b) => {
          const st = spineStyle(b);
          const styleStr = Object.entries(st).map(([k, v]) => k + ":" + v).join(";");
          const sel = state.selectedBook?.id === b.id ? " selected" : "";
          return `<button type="button" class="bsb-spine${sel}" data-id="${esc(b.id)}" style="${styleStr}" title="${esc(b.title)}">${esc(spineLabel(b))}</button>`;
        }).join("");
        return `<div class="bsb-shelf-tier"><div class="bsb-spines">${spines || '<span class="bsb-empty" style="padding:1rem">Empty shelf section</span>'}</div></div>`;
      }).join("");
      bookcase.querySelectorAll(".bsb-spine").forEach((el) => {
        el.addEventListener("click", () => selectBook(el.dataset.id));
      });
    }

    if (state.selectedBook) renderPulled(pulled);
    else if (pulled) pulled.innerHTML = '<div class="bsb-empty">Click a spine to pull a book from the shelf.</div>';
  }

  function selectBook(id) {
    const book = state.shelfBooks.find((b) => b.id === id) || state.hits.find((b) => b.id === id);
    if (!book) return;
    state.selectedBook = book;
    pushRoute({ shelf: state.shelfSlug, book: id });
    renderShelf();
    renderPulled($("bsb-pulled"));
  }

  function renderPulled(el) {
    if (!el || !state.selectedBook) return;
    const b = state.selectedBook;
    const cs = coverStyle(b);
    const styleStr = Object.entries(cs).map(([k, v]) => k + ":" + v).join(";");
    const coverInner = b.cover
      ? `<img src="${esc(b.cover)}" alt="" />`
      : esc(spineLabel(b));
    el.innerHTML = `
      <div class="bsb-cover" style="${styleStr}">${coverInner}</div>
      <div>
        <h3>${esc(b.title || b.id)}</h3>
        <div class="author">${esc(b.author || "Hostess 7")}</div>
        <div class="dewey-line">Dewey ${esc(b.dewey || "?")} · ${esc(b.shelf_title || b.shelf || "")}</div>
        <p style="color:var(--bsb-muted);font-size:0.88rem;margin:0">Pull complete — open to read in the secure H7 reader.</p>
        <div class="actions">
          <button type="button" class="bsb-open-btn" id="bsb-open-book">Open my book</button>
          <button type="button" class="bsb-btn" id="bsb-return-spine">Return to shelf</button>
        </div>
      </div>`;
    $("bsb-open-book")?.addEventListener("click", () => openBook(b));
    $("bsb-return-spine")?.addEventListener("click", () => {
      state.selectedBook = null;
      pushRoute({ shelf: state.shelfSlug });
      renderShelf();
    });
  }

  function openBook(book) {
    if (global.H7Reader?.open) {
      global.H7Reader.open(book.id, book, { braille: true });
      return;
    }
    global.location.href = "/field#library";
  }

  async function openShelf(slug, bookId) {
    if (!slug) return;
    state.shelfSlug = slug;
    state.shelfPage = 0;
    state.selectedBook = null;
    setView("shelf");
    pushRoute({ shelf: slug, book: bookId || "" });
    await loadShelfBooks(slug, 0);
    renderShelf();
    if (bookId) selectBook(bookId);
  }

  function goLobby() {
    state.shelfSlug = null;
    state.selectedBook = null;
    setView("lobby");
    pushRoute({ q: state.query || "" });
    renderLobby();
  }

  function bindChrome() {
    const qEl = $("bsb-search");
    qEl?.addEventListener("input", () => {
      clearTimeout(state.debounce);
      state.debounce = setTimeout(() => searchBooks(qEl.value), 220);
    });
    qEl?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") searchBooks(qEl.value);
    });
    $("bsb-browse-btn")?.addEventListener("click", goLobby);
  }

  async function init() {
    bindChrome();
    await loadFacets();
    const route = parseRoute();
    if (route.q) {
      $("bsb-search").value = route.q;
      await searchBooks(route.q);
    }
    if (route.shelf) {
      await openShelf(route.shelf, route.book || null);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})(window);