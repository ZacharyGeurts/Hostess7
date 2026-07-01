/**
 * Queen Browser — bookmarks hub flyout (top-left primary navigation).
 */
(function () {
  "use strict";

  const state = { open: false, doc: null, query: "" };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function navigate(url) {
    if (!url) return;
    const api = globalThis.QueenOS?.browser;
    if (api?.navigate) api.navigate(url);
    else if (api?.newTab) api.newTab(url);
    closeFlyout();
  }

  function closeFlyout() {
    state.open = false;
    const fly = $("qb-bookmarks-flyout");
    const btn = $("qb-bookmarks-flyout-btn");
    if (fly) fly.hidden = true;
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  function openFlyout() {
    state.open = true;
    const fly = $("qb-bookmarks-flyout");
    const btn = $("qb-bookmarks-flyout-btn");
    if (fly) fly.hidden = false;
    if (btn) btn.setAttribute("aria-expanded", "true");
    $("qb-bookmarks-search")?.focus();
  }

  function toggleFlyout() {
    if (state.open) closeFlyout();
    else openFlyout();
  }

  function renderRecent(doc) {
    const el = $("qbf-recent-list");
    if (!el) return;
    const recent = (doc?.visit_list?.recently_visited || doc?.recently_visited || []).slice(0, 8);
    if (!recent.length) {
      el.innerHTML = '<p class="qbf-section-title">Recent</p><p class="qbf-item" style="cursor:default;opacity:.6">No visits yet</p>';
      return;
    }
    el.innerHTML =
      '<p class="qbf-section-title">Recent</p>' +
      recent
        .map(function (r) {
          const url = r.url || "";
          const title = r.title || url;
          return (
            '<button type="button" class="qbf-item" data-url="' +
            esc(url) +
            '" title="' +
            esc(url) +
            '">' +
            esc(title) +
            "<small>" +
            esc(url) +
            "</small></button>"
          );
        })
        .join("");
    el.querySelectorAll("[data-url]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        navigate(btn.dataset.url);
      });
    });
  }

  function filterNodes(nodes, query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) return nodes;
    const out = [];
    nodes.forEach(function (node) {
      if (!node) return;
      if (node.kind === "folder") {
        const kids = filterNodes(node.children || [], q);
        if (kids.length || (node.title || "").toLowerCase().includes(q)) {
          out.push({ ...node, children: kids.length ? kids : node.children });
        }
        return;
      }
      const title = (node.title || "").toLowerCase();
      const hint = (node.hint || "").toLowerCase();
      const url = (node.url || "").toLowerCase();
      if (title.includes(q) || hint.includes(q) || url.includes(q)) out.push(node);
    });
    return out;
  }

  function renderTrees(doc) {
    const el = $("qbf-tree-list");
    if (!el) return;
    const trees = doc?.bookmark_trees || [];
    const filtered = filterNodes(trees, state.query);
    if (!filtered.length) {
      el.innerHTML = '<p class="qbf-section-title">Bookmarks</p><p class="qbf-item" style="cursor:default;opacity:.6">No matches</p>';
      return;
    }
    let html = '<p class="qbf-section-title">Bookmarks</p>';
    filtered.forEach(function (node) {
      if (node.kind === "folder") {
        html +=
          '<button type="button" class="qbf-item qbf-folder" data-folder="' +
          esc(node.id) +
          '">' +
          esc(node.title) +
          "</button>" +
          '<div class="qbf-folder-children" data-folder-children="' +
          esc(node.id) +
          '" hidden>';
        (node.children || []).forEach(function (child) {
          if (!child?.url) return;
          html +=
            '<button type="button" class="qbf-item" data-url="' +
            esc(child.url) +
            '" title="' +
            esc(child.hint || child.title) +
            '">' +
            esc(child.title) +
            "<small>" +
            esc(child.hint || child.url) +
            "</small></button>";
        });
        html += "</div>";
        return;
      }
      if (node.url) {
        html +=
          '<button type="button" class="qbf-item" data-url="' +
          esc(node.url) +
          '">' +
          esc(node.title) +
          "<small>" +
          esc(node.hint || node.url) +
          "</small></button>";
      }
    });
    el.innerHTML = html;
    el.querySelectorAll("[data-url]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        navigate(btn.dataset.url);
      });
    });
    el.querySelectorAll(".qbf-folder").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const id = btn.dataset.folder;
        const kids = el.querySelector('[data-folder-children="' + id + '"]');
        if (!kids) return;
        const open = kids.hidden;
        kids.hidden = !open;
        btn.classList.toggle("open", open);
      });
    });
  }

  function render(doc) {
    state.doc = doc || state.doc;
    if (!state.doc) return;
    renderRecent(state.doc);
    renderTrees(state.doc);
  }

  async function refresh() {
    try {
      const r = await fetch("/api/queen-browser", { cache: "no-store" });
      const doc = await r.json();
      render(doc);
    } catch (_) {}
  }

  function wire() {
    $("qb-bookmarks-flyout-btn")?.addEventListener("click", function (ev) {
      ev.stopPropagation();
      toggleFlyout();
      if (state.open) refresh();
    });
    $("qb-bookmarks-search")?.addEventListener("input", function (ev) {
      state.query = ev.target.value || "";
      renderTrees(state.doc);
    });
    document.addEventListener("click", function (ev) {
      if (!state.open) return;
      if (ev.target.closest(".qb-bookmarks-hub")) return;
      closeFlyout();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && state.open) closeFlyout();
    });
  }

  function init() {
    wire();
    refresh();
  }

  globalThis.QueenBookmarksFlyout = { init, render, refresh, close: closeFlyout, open: openFlyout };
})();