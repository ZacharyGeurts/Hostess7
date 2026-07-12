/**
 * Queen NES Library — separate API, sortable cart tiles, dimmed when ROM missing.
 */
(function (global) {
  "use strict";

  const API = "/api/nes-library";
  const LAUNCH_API = "/api/game-room";

  const state = {
    sort: "title_az",
    query: "",
    offset: 0,
    limit: 120,
    total: 0,
    entries: [],
    selected: null,
    loading: false,
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

  async function fetchLibrary() {
    state.loading = true;
    const params = new URLSearchParams({
      sort: state.sort,
      limit: String(state.limit),
      offset: String(state.offset),
    });
    if (state.query) params.set("q", state.query);
    const r = await fetch(`${API}?${params}`, { cache: "no-store" });
    const doc = r.ok ? await r.json() : { entries: [] };
    state.entries = doc.entries || [];
    state.total = doc.total ?? state.entries.length;
    state.loading = false;
    renderStats(doc);
    renderGrid();
    return doc;
  }

  function renderStats(doc) {
    const el = $("gr-nes-stats");
    if (!el) return;
    const have = doc?.rom_count ?? 0;
    const all = doc?.count ?? doc?.catalog_count ?? 0;
    el.textContent = `${have} playable · ${all - have} gray · ${all} catalog`;
  }

  function cartTile(row) {
    const have = !!row.have_rom;
    const cls = have ? "gr-nes-cart have" : "gr-nes-cart missing";
    const img = row.cart_path || row.box_path || "";
    const meta = [row.year, row.genre].filter(Boolean).join(" · ");
    return (
      `<button type="button" class="${cls}${state.selected === row.id ? " selected" : ""}"` +
      ` data-nes-id="${esc(row.id)}" data-have="${have ? "1" : "0"}"` +
      (row.rom_path ? ` data-rom-path="${esc(row.rom_path)}"` : "") +
      ` title="${esc(row.title)}${have ? "" : " — ROM not in library"}">` +
      `<img src="${esc(img)}" alt="" loading="lazy" />` +
      `<span class="gr-nes-cart-title">${esc(row.title)}</span>` +
      `<span class="gr-nes-cart-meta">${esc(meta)}</span>` +
      (have ? '<span class="gr-nes-badge have">Have</span>' : '<span class="gr-nes-badge miss">—</span>') +
      `</button>`
    );
  }

  function renderGrid() {
    const grid = $("gr-nes-grid");
    if (!grid) return;
    if (!state.entries.length) {
      grid.innerHTML = '<p class="gr-nes-empty">Loading NES library…</p>';
      return;
    }
    grid.innerHTML = state.entries.map(cartTile).join("");
    grid.querySelectorAll(".gr-nes-cart").forEach((btn) => {
      btn.addEventListener("click", () => selectCart(btn));
    });
  }

  function selectCart(btn) {
    const id = btn.dataset.nesId;
    const have = btn.dataset.have === "1";
    state.selected = id;
    gridSelected();
    const detail = $("gr-nes-detail");
    const entry = state.entries.find((e) => e.id === id);
    if (detail && entry) {
      detail.innerHTML = [
        `<strong>${esc(entry.title)}</strong>`,
        entry.publisher ? `<span>${esc(entry.publisher)}</span>` : "",
        entry.mapper_fix ? `<p class="gr-nes-fix">${esc(entry.mapper_fix)}</p>` : "",
        have
          ? `<button type="button" class="gr-btn gr-btn--gold" id="gr-nes-play">Insert &amp; Play</button>`
          : `<p class="gr-nes-miss">Add <code>.nes</code> to <code>assets/dos/incoming/nes/</code> — any dumped ROM supported.</p>`,
      ].join("");
      $("gr-nes-play")?.addEventListener("click", () => playSelected(entry));
    }
    if (!have) return;
    playSelected(entry);
  }

  function gridSelected() {
    const grid = $("gr-nes-grid");
    if (!grid) return;
    grid.querySelectorAll(".gr-nes-cart").forEach((b) => {
      b.classList.toggle("selected", b.dataset.nesId === state.selected);
    });
  }

  async function playSelected(entry) {
    if (!entry?.have_rom) return;
    global.QueenGameRoom?.openCurtains?.();
    const body = {
      action: "launch",
      system: "nes",
      nes_id: entry.id,
      rom_path: entry.rom_path,
      title: entry.title,
      spawn_rtx: true,
    };
    const r = await fetch(LAUNCH_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const out = await r.json();
    const log = $("gr-log");
    if (log) log.textContent = JSON.stringify(out, null, 2);
    if (out.ok && out.spawned) {
      global.QueenGameRoom?.startFbPoll?.();
      global.QueenGameRoom?.setSystem?.("nes");
    }
    return out;
  }

  function wireToolbar() {
    $("gr-nes-sort")?.addEventListener("change", (e) => {
      state.sort = e.target.value;
      state.offset = 0;
      fetchLibrary();
    });
    $("gr-nes-search")?.addEventListener("input", (e) => {
      state.query = e.target.value.trim();
      state.offset = 0;
      clearTimeout(wireToolbar._t);
      wireToolbar._t = setTimeout(() => fetchLibrary(), 280);
    });
    $("gr-nes-more")?.addEventListener("click", () => {
      if (state.offset + state.limit >= state.total) return;
      state.offset += state.limit;
      loadMore();
    });
  }

  async function loadMore() {
    const params = new URLSearchParams({
      sort: state.sort,
      limit: String(state.limit),
      offset: String(state.offset),
    });
    if (state.query) params.set("q", state.query);
    const r = await fetch(`${API}?${params}`);
    const doc = r.ok ? await r.json() : { entries: [] };
    state.entries = state.entries.concat(doc.entries || []);
    renderGrid();
  }

  function showNesRoom(visible) {
    const room = $("gr-nes-room");
    if (room) room.hidden = !visible;
  }

  function init() {
    wireToolbar();
    fetchLibrary();
  }

  global.QueenNesLibrary = { state, fetchLibrary, showNesRoom, playSelected, init };
})(typeof window !== "undefined" ? window : globalThis);