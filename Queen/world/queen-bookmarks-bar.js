/**
 * Queen Browser — bookmark bar row (folder chips below chrome).
 */
(function () {
  "use strict";

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
  }

  function render(doc) {
    const bar = $("qb-bookmarks");
    if (!bar || !doc) return;
    const rows = doc.bookmark_bar || [];
    if (!rows.length && doc.bookmark_trees?.length) {
      globalThis.QueenBookmarksFlyout?.render?.(doc);
      return;
    }
    bar.innerHTML = rows
      .slice(0, 12)
      .map(function (bm) {
        if (bm.kind === "folder") {
          return '<span class="qb-bookmark qb-bookmark-folder" title="' + esc(bm.title) + '">' + esc(bm.title) + " ▾</span>";
        }
        return (
          '<button type="button" class="qb-bookmark" data-url="' +
          esc(bm.url) +
          '" title="' +
          esc(bm.hint || bm.title) +
          '">' +
          esc(bm.title) +
          "</button>"
        );
      })
      .join("");
    bar.querySelectorAll("[data-url]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        navigate(btn.dataset.url);
      });
    });
  }

  globalThis.QueenBookmarksBar = { render };
})();