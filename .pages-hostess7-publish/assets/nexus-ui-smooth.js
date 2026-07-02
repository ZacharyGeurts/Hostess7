/**
 * NEXUS UI Smooth — shared debounce/throttle, rAF batching, incremental tables, focus guard.
 * Low-cost: avoids full DOM rebuilds and poll-driven input resets.
 */
(function (global) {
  "use strict";

  function debounce(fn, ms) {
    let t = 0;
    return function debounced(...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function throttle(fn, ms) {
    let last = 0;
    let pending = 0;
    return function throttled(...args) {
      const now = Date.now();
      const run = () => {
        last = Date.now();
        fn.apply(this, args);
      };
      if (now - last >= ms) {
        run();
        return;
      }
      clearTimeout(pending);
      pending = setTimeout(run, ms - (now - last));
    };
  }

  const domQueue = new Map();
  let domRaf = 0;

  function scheduleDom(key, fn) {
    domQueue.set(key, fn);
    if (domRaf) return;
    domRaf = requestAnimationFrame(() => {
      domRaf = 0;
      const jobs = [...domQueue.entries()];
      domQueue.clear();
      jobs.forEach(([, job]) => {
        try { job(); } catch (_) { /* keep panel alive */ }
      });
    });
  }

  function isTextInput(el) {
    if (!el || el === document.body) return false;
    const tag = String(el.tagName || "").toLowerCase();
    if (tag === "textarea") return true;
    if (tag !== "input") return false;
    const type = String(el.type || "text").toLowerCase();
    return !["button", "checkbox", "radio", "submit", "reset", "file", "hidden", "range", "color"].includes(type);
  }

  function isUserTyping(root) {
    const active = document.activeElement;
    if (!isTextInput(active)) return false;
    if (!root) return true;
    return root.contains(active);
  }

  function captureFocus() {
    const el = document.activeElement;
    if (!isTextInput(el)) return null;
    return {
      id: el.id || "",
      value: el.value,
      start: el.selectionStart,
      end: el.selectionEnd,
    };
  }

  function restoreFocus(snap) {
    if (!snap || !snap.id) return;
    const el = document.getElementById(snap.id);
    if (!el || el.value !== snap.value) {
      if (el) el.value = snap.value;
    }
    if (!el) return;
    try {
      el.focus({ preventScroll: true });
      if (typeof snap.start === "number" && typeof snap.end === "number") {
        el.setSelectionRange(snap.start, snap.end);
      }
    } catch (_) { /* ignore */ }
  }

  function bindDebouncedInput(el, handler, ms) {
    if (!el || el.dataset.nexusDebounced) return;
    el.dataset.nexusDebounced = "1";
    const wait = ms || 120;
    el.addEventListener("input", debounce(() => handler(el.value, el), wait));
  }

  function ensureTableWrap(el, className) {
    if (!el) return null;
    let table = el.querySelector("table");
    if (table) return table.querySelector("tbody") || table;
    el.innerHTML = `<table class="honor-table dns-table ${className || ""}"><thead></thead><tbody></tbody></table>`;
    return el.querySelector("tbody");
  }

  /**
   * Incremental tbody patch — keyed rows, minimal DOM churn.
   * rowHtmlFn(row) -> full <tr data-row-key="...">...</tr> string.
   */
  function patchTableRows(container, rows, keyFn, rowHtmlFn, opts) {
    if (!container) return;
    const maxRows = (opts && opts.maxRows) || rows.length;
    const slice = rows.slice(0, maxRows);
    const dataFp = slice.map((r) => keyFn(r)).join("\x1e") + ":" + slice.length;
    if (container.dataset.patchFp === dataFp) return;
    container.dataset.patchFp = dataFp;
    const snap = captureFocus();
    scheduleDom(`table:${container.id || "anon"}`, () => {
      let tbody = container.tagName === "TBODY" ? container : container.querySelector("tbody");
      if (!tbody) {
        const table = container.querySelector("table");
        if (table) tbody = table.querySelector("tbody");
      }
      if (!tbody) {
        container.innerHTML = `<table class="honor-table dns-table"><tbody></tbody></table>`;
        tbody = container.querySelector("tbody");
      }
      const existing = new Map();
      tbody.querySelectorAll("tr[data-row-key]").forEach((tr) => {
        existing.set(tr.getAttribute("data-row-key"), tr);
      });
      const ordered = [];
      slice.forEach((row) => {
        const key = String(keyFn(row));
        const html = rowHtmlFn(row);
        let tr = existing.get(key);
        if (tr) {
          if (tr.outerHTML !== html) {
            const tmp = document.createElement("tbody");
            tmp.innerHTML = html;
            const next = tmp.firstElementChild;
            if (next) {
              tr.replaceWith(next);
              tr = next;
            }
          }
          existing.delete(key);
        } else {
          const tmp = document.createElement("tbody");
          tmp.innerHTML = html;
          tr = tmp.firstElementChild;
        }
        if (tr) ordered.push(tr);
      });
      existing.forEach((tr) => tr.remove());
      tbody.replaceChildren(...ordered);
      restoreFocus(snap);
    });
  }

  function fingerprint(obj, keys) {
    if (!obj || typeof obj !== "object") return "";
    return keys.map((k) => {
      const v = obj[k];
      if (v && typeof v === "object") return JSON.stringify(v);
      return String(v ?? "");
    }).join("\x1f");
  }

  global.NexusUiSmooth = {
    debounce,
    throttle,
    scheduleDom,
    isTextInput,
    isUserTyping,
    captureFocus,
    restoreFocus,
    bindDebouncedInput,
    patchTableRows,
    fingerprint,
  };
})(window);