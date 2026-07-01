/**
 * Field Ironclad Taskbar — AmmoOS bottom search + sort on C2 startbar and focused surfaces.
 * @g16 5.1.0 · Grok16/ironclad-secure-api · field-best-sort
 */
(function (global) {
  "use strict";

  const BUS = global.IroncladBus;
  const HOME_PANEL = "/field";
  const HOME_QUEEN = "http://127.0.0.1:9481/world/browser.html";

  const state = { debounce: null, root: null, resultsEl: null, focusBound: false };

  function esc(s) {
    return BUS?.esc ? BUS.esc(s) : String(s ?? "");
  }

  function isAmmoHome() {
    const p = global.location?.pathname || "";
    return p === "/field" || p === "/field/" || p === "/";
  }

  function isRunningOs() {
    return isAmmoHome() && !!document.getElementById("fsb-root");
  }

  function shouldShowIronclad() {
    if (document.body?.dataset?.ironcladTaskbar === "0") return false;
    if (document.body?.dataset?.forceIroncladTaskbar === "1") return true;
    if (isRunningOs()) return true;
    return !!(document.hasFocus && document.hasFocus());
  }

  function applyVisibility() {
    const nodes = document.querySelectorAll(".fitb-root, #fitb-mount");
    nodes.forEach(function (el) {
      el.style.display = shouldShowIronclad() ? "" : "none";
    });
  }

  function bindFocusGate() {
    if (state.focusBound) return;
    state.focusBound = true;
    global.addEventListener("focus", applyVisibility, true);
    global.addEventListener("blur", applyVisibility, true);
    document.addEventListener("visibilitychange", applyVisibility);
  }

  function homeTarget() {
    try {
      if (global.location?.port === "9481") return HOME_QUEEN;
    } catch (_) {}
    return HOME_PANEL;
  }

  function goHome() {
    const url = homeTarget();
    if (global.top && global.top !== global) {
      try {
        global.top.location.href = url;
        return;
      } catch (_) {}
    }
    global.location.href = url;
  }

  function renderResults(hits) {
    if (!state.resultsEl) return;
    if (!hits || !hits.length) {
      state.resultsEl.innerHTML = '<p class="fitb-empty">No matches — try another term or context.</p>';
      state.resultsEl.classList.add("open");
      return;
    }
    state.resultsEl.innerHTML = hits
      .map(function (hit) {
        const label = BUS?.hitLabel ? BUS.hitLabel(hit) : hit.title || hit.label || "result";
        const kind = hit.source || hit.kind || "hit";
        const url = BUS?.hitUrl ? BUS.hitUrl(hit) : hit.url || hit.exec || "";
        return (
          '<button type="button" class="fitb-hit" data-url="' +
          esc(url) +
          '"><span class="fitb-hit-kind">' +
          esc(kind) +
          '</span><span class="fitb-hit-label">' +
          esc(label) +
          "</span></button>"
        );
      })
      .join("");
    state.resultsEl.querySelectorAll(".fitb-hit").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const url = btn.dataset.url;
        state.resultsEl.classList.remove("open");
        if (!url) return;
        if (url.startsWith("http")) {
          global.open(url, "_blank", "noopener");
          return;
        }
        global.location.href = url;
      });
    });
    state.resultsEl.classList.add("open");
  }

  async function runSearch(input, sortSel) {
    if (!BUS?.search) return;
    const q = input.value.trim();
    const ctx = sortSel?.value || "all";
    if (!q) {
      state.resultsEl?.classList.remove("open");
      return;
    }
    try {
      const doc = await BUS.search(q, { context: ctx, limit: 32 });
      renderResults(doc.hits || []);
    } catch (e) {
      if (state.resultsEl) {
        state.resultsEl.innerHTML = '<p class="fitb-empty">Search unavailable — ' + esc(e.message) + "</p>";
        state.resultsEl.classList.add("open");
      }
    }
  }

  function bindSearch(input, sortSel) {
    input.addEventListener("input", function () {
      clearTimeout(state.debounce);
      state.debounce = setTimeout(function () {
        runSearch(input, sortSel);
      }, 240);
    });
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        input.value = "";
        state.resultsEl?.classList.remove("open");
      }
      if (ev.key === "Enter") runSearch(input, sortSel);
    });
    document.addEventListener("click", function (ev) {
      if (!state.root?.contains(ev.target)) state.resultsEl?.classList.remove("open");
    });
  }

  function buildMarkup(embedded) {
    const homeLabel = isAmmoHome() ? "AmmoOS" : "← AmmoOS";
    return (
      '<nav class="fitb-root' +
      (embedded ? " fitb-embedded" : "") +
      '" aria-label="Ironclad search and sort">' +
      '<button type="button" class="fitb-home" id="fitb-home" title="Return to AmmoOS C2">' +
      esc(homeLabel) +
      "</button>" +
      '<label class="fitb-search-wrap">' +
      '<span class="visually-hidden">Ironclad search</span>' +
      '<input type="search" class="fitb-search" id="fitb-search" placeholder="Ironclad search…" autocomplete="off" />' +
      '<select class="fitb-sort" id="fitb-sort" aria-label="Search context">' +
      '<option value="all">All</option>' +
      '<option value="registry">Registry</option>' +
      '<option value="catalog">Catalog</option>' +
      '<option value="chips">CHIPS</option>' +
      '<option value="routes">Routes</option>' +
      "</select>" +
      "</label>" +
      '<div class="fitb-results" id="fitb-results" role="listbox" aria-label="Search results"></div>' +
      "</nav>"
    );
  }

  function wire(root) {
    state.root = root;
    state.resultsEl = root.querySelector("#fitb-results");
    root.querySelector("#fitb-home")?.addEventListener("click", goHome);
    const input = root.querySelector("#fitb-search");
    const sortSel = root.querySelector("#fitb-sort");
    if (input) bindSearch(input, sortSel);
  }

  function mountStandalone() {
    if (document.getElementById("fitb-root") || document.body?.dataset?.noIroncladTaskbar === "1") return null;
    if (isAmmoHome() && document.getElementById("fsb-root")) return null;
    const root = document.createElement("div");
    root.id = "fitb-mount";
    root.innerHTML = buildMarkup(false);
    document.body.appendChild(root);
    document.body.classList.add("fitb-pad-bottom");
    if (document.getElementById("fsb-root")) document.body.classList.add("has-fsb-root");
    wire(root.querySelector(".fitb-root"));
    return root;
  }

  function injectIntoStartbar() {
    const fsb = document.querySelector(".fsb-root");
    if (!fsb || document.getElementById("fitb-embedded")) return null;
    const wrap = document.createElement("div");
    wrap.id = "fitb-embedded";
    wrap.className = "fitb-embedded-wrap";
    wrap.innerHTML = buildMarkup(true);
    const quick = document.getElementById("fsb-quick");
    if (quick && quick.nextSibling) fsb.insertBefore(wrap, quick.nextSibling);
    else fsb.appendChild(wrap);
    wire(wrap.querySelector(".fitb-root"));
    return wrap;
  }

  function init() {
    if (!BUS) return;
    bindFocusGate();
    if (document.getElementById("fsb-root")) injectIntoStartbar();
    else if (!isAmmoHome() || document.body?.dataset?.forceIroncladTaskbar === "1") mountStandalone();
    applyVisibility();
  }

  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(init, 0);
  });

  global.FieldIroncladTaskbar = {
    init,
    mountStandalone,
    injectIntoStartbar,
    goHome,
    homeTarget,
  };
})(typeof window !== "undefined" ? window : globalThis);