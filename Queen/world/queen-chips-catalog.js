(function () {
  "use strict";

  const PAGE_SIZE = 48;
  const AC_LIMIT = 16;
  const THUMB_FALLBACK = "/world/assets/combinatronic/chips/generic_die.png";
  const BOOK_JSON = "/library/dewey/621-computer-engineering/chips-catalog/ironclad-chips-catalog/book.json";

  const $ = (id) => document.getElementById(id);

  let catalog = null;
  let pages = [];
  let stackPages = [];
  let entryById = new Map();
  let activeChapter = 1;
  let activeStack = "";
  let searchQuery = "";
  let searchHits = null;
  let visibleCount = PAGE_SIZE;
  let acIndex = -1;
  let acHits = [];
  let acTimer = null;
  let acAbort = null;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function thumb(row) {
    return row?.thumb_url || THUMB_FALLBACK;
  }

  function highlight(text, query) {
    const raw = String(text ?? "");
    const q = String(query ?? "").trim();
    if (!q) return esc(raw);
    const lower = raw.toLowerCase();
    const tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
    let out = "";
    let i = 0;
    while (i < raw.length) {
      let matched = "";
      for (const tok of tokens) {
        if (lower.slice(i, i + tok.length) === tok) {
          matched = tok;
          break;
        }
      }
      if (matched) {
        out += `<mark>${esc(raw.slice(i, i + matched.length))}</mark>`;
        i += matched.length;
      } else {
        out += esc(raw[i]);
        i += 1;
      }
    }
    return out;
  }

  async function fetchJson(url, opts) {
    const res = await fetch(url, { cache: "no-store", ...opts });
    if (!res.ok) return null;
    return res.json();
  }

  async function fetchCatalog() {
    return fetchJson("/api/chips/catalog");
  }

  async function fetchPages() {
    const doc = await fetchJson("/api/chips/catalog/pages");
    return doc?.pages || [];
  }

  async function fetchBookStacks() {
    const book = await fetchJson(BOOK_JSON);
    return (book?.pages || []).filter((p) => p.kind === "platform_stack" || p.platform_stack);
  }

  async function fetchAutocomplete(q, signal) {
    if (!q || q.length < 1) return [];
    const doc = await fetchJson(
      `/api/chips/catalog/autocomplete?q=${encodeURIComponent(q)}&limit=${AC_LIMIT}`,
      { signal }
    );
    return doc?.hits || doc?.entries || (Array.isArray(doc) ? doc : []);
  }

  async function fetchSearch(q) {
    if (!q || q.length < 2) return null;
    const doc = await fetchJson(`/api/chips/catalog/search?q=${encodeURIComponent(q)}`);
    return doc?.hits || doc?.entries || [];
  }

  function openDetail(id) {
    if (!id) return;
    window.location.href = `/world/queen-chips-detail.html?id=${encodeURIComponent(id)}`;
  }

  function buildEntryMap(entries) {
    entryById = new Map();
    for (const row of entries || []) {
      if (row?.id) entryById.set(String(row.id), row);
    }
  }

  function entriesForChapter(pageNo) {
    const page = pages.find((p) => Number(p.page) === Number(pageNo));
    if (!page?.chip_ids?.length) return catalog?.entries || [];
    const ids = new Set(page.chip_ids);
    return (catalog?.entries || []).filter((e) => ids.has(e.id));
  }

  function entriesForStack(stackId) {
    if (!stackId) return [];
    return (catalog?.entries || []).filter((e) => String(e.platform_stack || "") === stackId);
  }

  function currentEntries() {
    if (searchHits) return searchHits;
    if (activeStack) return entriesForStack(activeStack);
    return entriesForChapter(activeChapter);
  }

  function currentTitle() {
    if (searchQuery) return `Search · “${searchQuery}”`;
    if (activeStack) {
      const hit = stackPages.find((p) => p.platform_stack === activeStack);
      return hit?.title || activeStack;
    }
    const hit = pages.find((p) => Number(p.page) === Number(activeChapter));
    return hit?.title || `Chapter ${activeChapter}`;
  }

  function renderStats() {
    const el = $("qcc-stats");
    if (!el || !catalog) return;
    const c = catalog.counts || {};
    const kinds = Object.entries(c.by_kind || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([k, n]) => `<span class="qcc-tag">${esc(k)} ${n}</span>`)
      .join(" ");
    el.innerHTML = [
      `<p><strong>${c.total ?? "—"}</strong> dies indexed</p>`,
      `<p>Curated <strong>${c.curated ?? "—"}</strong></p>`,
      `<p>Thumbs <strong>${c.thumb_available ?? "—"}</strong></p>`,
      `<p>Chapters <strong>${pages.length}</strong> · Stacks <strong>${stackPages.length}</strong></p>`,
      kinds ? `<p>${kinds}</p>` : "",
      `<p class="qcc-tag qcc-tag--accent">ironclad:chips:3</p>`,
    ].join("");
  }

  function renderPages() {
    const el = $("qcc-pages");
    if (!el) return;
    el.innerHTML = pages
      .map((p) => {
        const on = !activeStack && !searchQuery && Number(p.page) === activeChapter ? " on" : "";
        const count = p.count ?? p.chip_count ?? (p.chip_ids || []).length ?? 0;
        return (
          `<button type="button" class="qcc-page-btn${on}" data-page="${p.page}"` +
          ` aria-pressed="${on ? "true" : "false"}">` +
          `${esc(p.title)} <small>(${count})</small></button>`
        );
      })
      .join("");
    el.querySelectorAll(".qcc-page-btn").forEach((btn) => {
      btn.addEventListener("click", () => selectChapter(Number(btn.dataset.page)));
    });
  }

  function renderStacks() {
    const el = $("qcc-stacks");
    if (!el) return;
    if (!stackPages.length) {
      el.innerHTML = `<span class="qcc-tag">No platform stacks</span>`;
      return;
    }
    el.innerHTML = stackPages
      .map((p) => {
        const stackId = p.platform_stack || p.slug;
        const on = activeStack === stackId && !searchQuery ? " on" : "";
        const count = p.chip_count ?? 0;
        const short = (p.title || stackId).replace(/Platform Stack$/i, "").trim();
        return (
          `<button type="button" class="qcc-page-btn qcc-page-btn--stack${on}"` +
          ` data-stack="${esc(stackId)}" aria-pressed="${on ? "true" : "false"}">` +
          `${esc(short)} <small>(${count})</small></button>`
        );
      })
      .join("");
    el.querySelectorAll("[data-stack]").forEach((btn) => {
      btn.addEventListener("click", () => selectStack(btn.dataset.stack));
    });
  }

  function cardMeta(row) {
    const bits = [];
    if (row.mfg_date_start) bits.push(row.mfg_date_start.slice(0, 4));
    else if (row.era) bits.push(String(row.era).slice(0, 9));
    if (row.socket && row.socket !== "—") bits.push(row.socket);
    return bits.length ? `<span class="qcc-card-era">${esc(bits.join(" · "))}</span>` : "";
  }

  function cardHtml(row) {
    return (
      `<button type="button" class="qcc-card" role="listitem" data-id="${esc(row.id)}">` +
      `<div class="qcc-card-media">` +
      `<img src="${esc(thumb(row))}" alt="${esc(row.label)}" loading="lazy" decoding="async" />` +
      (row.kind ? `<span class="qcc-card-badge">${esc(row.kind)}</span>` : "") +
      (row.featured ? `<span class="qcc-card-badge qcc-card-badge--feat">★</span>` : "") +
      `</div>` +
      `<span class="qcc-card-label">${esc(row.label)}</span>` +
      `<span class="qcc-card-sub">` +
      `<span class="qcc-tag">${esc(row.kind)}</span>${esc(row.vendor)}` +
      `</span>` +
      cardMeta(row) +
      `</button>`
    );
  }

  function renderGrid() {
    const grid = $("qcc-grid");
    const title = $("qcc-grid-title");
    const meta = $("qcc-grid-meta");
    const loadMore = $("qcc-load-more");
    if (!grid) return;

    const all = currentEntries();
    const shown = all.slice(0, visibleCount);
    title.textContent = currentTitle();
    meta.textContent = `Showing ${shown.length} of ${all.length}`;

    if (!shown.length) {
      grid.innerHTML = `<p class="qcc-empty">No chips match this view.</p>`;
    } else {
      grid.innerHTML = shown.map(cardHtml).join("");
      grid.querySelectorAll(".qcc-card").forEach((card) => {
        card.addEventListener("click", () => openDetail(card.dataset.id));
      });
    }

    if (loadMore) {
      const more = all.length > visibleCount;
      loadMore.hidden = !more;
      loadMore.textContent = more
        ? `Load more (${Math.min(PAGE_SIZE, all.length - visibleCount)} of ${all.length - visibleCount} remaining)`
        : "Load more";
    }
  }

  function selectChapter(pageNo) {
    activeChapter = pageNo;
    activeStack = "";
    searchQuery = "";
    searchHits = null;
    visibleCount = PAGE_SIZE;
    const input = $("qcc-search");
    if (input) input.value = "";
    hideAutocomplete();
    renderPages();
    renderStacks();
    renderGrid();
    updateSearchHint("");
  }

  function syncStackUrl(stackId) {
    try {
      const url = new URL(location.href);
      if (stackId) url.searchParams.set("stack", stackId);
      else url.searchParams.delete("stack");
      history.replaceState(null, "", url);
    } catch (_) {
      /* ignore */
    }
  }

  function selectStack(stackId) {
    if (activeStack === stackId) {
      activeStack = "";
      if (!activeChapter) activeChapter = 1;
    } else {
      activeStack = stackId;
    }
    searchQuery = "";
    searchHits = null;
    visibleCount = PAGE_SIZE;
    const input = $("qcc-search");
    if (input) input.value = "";
    hideAutocomplete();
    syncStackUrl(activeStack);
    renderPages();
    renderStacks();
    renderGrid();
    updateSearchHint("");
  }

  function updateSearchHint(text) {
    const hint = $("qcc-search-hint");
    if (hint) hint.textContent = text;
  }

  function setAcActive(index) {
    const ac = $("qcc-ac");
    const input = $("qcc-search");
    const items = ac ? [...ac.querySelectorAll("li")] : [];
    acIndex = index;
    items.forEach((li, i) => {
      const on = i === acIndex;
      li.classList.toggle("on", on);
      li.setAttribute("aria-selected", on ? "true" : "false");
      if (on) {
        li.scrollIntoView({ block: "nearest" });
        if (input) input.setAttribute("aria-activedescendant", li.id || "");
      }
    });
    if (acIndex < 0 && input) input.setAttribute("aria-activedescendant", "");
  }

  function hideAutocomplete() {
    const ac = $("qcc-ac");
    const input = $("qcc-search");
    if (ac) {
      ac.hidden = true;
      ac.innerHTML = "";
    }
    if (input) {
      input.setAttribute("aria-expanded", "false");
      input.setAttribute("aria-activedescendant", "");
    }
    acIndex = -1;
    acHits = [];
  }

  function renderAutocomplete(hits, query) {
    const ac = $("qcc-ac");
    const input = $("qcc-search");
    if (!ac) return;
    acHits = hits || [];
    if (!acHits.length) {
      hideAutocomplete();
      return;
    }
    ac.hidden = false;
    if (input) input.setAttribute("aria-expanded", "true");
    ac.innerHTML = acHits
      .map((row, i) => {
        const id = `qcc-ac-item-${i}`;
        return (
          `<li id="${id}" role="option" data-id="${esc(row.id)}" data-idx="${i}"` +
          ` aria-selected="false" tabindex="-1">` +
          `<img src="${esc(thumb(row))}" alt="" loading="lazy" decoding="async" />` +
          `<div>` +
          `<div class="qcc-ac-label">${highlight(row.label, query)}</div>` +
          `<div class="qcc-ac-meta">${highlight(row.vendor, query)} · ${esc(row.kind)}</div>` +
          `</div></li>`
        );
      })
      .join("");

    ac.querySelectorAll("li").forEach((li) => {
      li.addEventListener("mousedown", (ev) => {
        ev.preventDefault();
        openDetail(li.dataset.id);
      });
      li.addEventListener("mouseenter", () => setAcActive(Number(li.dataset.idx)));
    });
    setAcActive(acIndex >= 0 ? Math.min(acIndex, acHits.length - 1) : -1);
  }

  async function onSearchInput() {
    const input = $("qcc-search");
    const q = (input?.value || "").trim();
    searchQuery = q;

    if (acAbort) acAbort.abort();
    acAbort = new AbortController();

    if (q.length >= 1) {
      const hits = await fetchAutocomplete(q, acAbort.signal);
      if (searchQuery !== q) return;
      renderAutocomplete(hits, q);
      updateSearchHint(hits.length ? `${hits.length} suggestions · ↑↓ navigate · Enter open` : "No matches");
    } else {
      hideAutocomplete();
      updateSearchHint("");
    }

    if (q.length >= 2) {
      searchHits = await fetchSearch(q);
      activeStack = "";
      visibleCount = PAGE_SIZE;
      renderPages();
      renderStacks();
      renderGrid();
      updateSearchHint(
        searchHits?.length
          ? `${searchHits.length} grid results · autocomplete for quick jump`
          : "No grid results"
      );
    } else if (!q) {
      searchHits = null;
      visibleCount = PAGE_SIZE;
      renderPages();
      renderStacks();
      renderGrid();
    }
  }

  function wireSearch() {
    const input = $("qcc-search");
    if (!input) return;

    input.addEventListener("input", () => {
      clearTimeout(acTimer);
      acTimer = setTimeout(onSearchInput, 140);
    });

    input.addEventListener("keydown", (ev) => {
      const ac = $("qcc-ac");
      const open = ac && !ac.hidden;
      const count = acHits.length;

      if (ev.key === "ArrowDown" && count) {
        ev.preventDefault();
        setAcActive(acIndex < count - 1 ? acIndex + 1 : 0);
      } else if (ev.key === "ArrowUp" && count) {
        ev.preventDefault();
        setAcActive(acIndex > 0 ? acIndex - 1 : count - 1);
      } else if (ev.key === "Home" && open && count) {
        ev.preventDefault();
        setAcActive(0);
      } else if (ev.key === "End" && open && count) {
        ev.preventDefault();
        setAcActive(count - 1);
      } else if (ev.key === "Enter") {
        if (open && acIndex >= 0 && acHits[acIndex]) {
          ev.preventDefault();
          openDetail(acHits[acIndex].id);
        }
      } else if (ev.key === "Escape") {
        hideAutocomplete();
        updateSearchHint("");
      } else if (ev.key === "Tab" && open && count && acIndex < 0) {
        setAcActive(0);
      }
    });

    document.addEventListener("click", (ev) => {
      if (!ev.target.closest(".qcc-search-wrap")) hideAutocomplete();
    });
  }

  function wireLoadMore() {
    $("qcc-load-more")?.addEventListener("click", () => {
      visibleCount += PAGE_SIZE;
      renderGrid();
    });
  }

  function readUrlStack() {
    try {
      const stack = new URLSearchParams(location.search).get("stack");
      if (stack) activeStack = stack;
    } catch (_) {
      /* ignore */
    }
  }

  async function refresh() {
    const btn = $("qcc-refresh");
    if (btn) btn.disabled = true;
    await fetch("/api/chips/catalog/publish", { cache: "no-store" });
    const [cat, pg, stacks] = await Promise.all([fetchCatalog(), fetchPages(), fetchBookStacks()]);
    catalog = cat;
    pages = pg.length ? pg : cat?.pages || [];
    stackPages = stacks;
    readUrlStack();
    if (btn) btn.disabled = false;
    if (!catalog) return;
    buildEntryMap(catalog.entries);
    renderStats();
    renderPages();
    renderStacks();
    renderGrid();
  }

  wireSearch();
  wireLoadMore();
  $("qcc-refresh")?.addEventListener("click", refresh);
  refresh();
})();