/**
 * Human BSP hub — compact adaptive panes: Ask Hostess7 · Tasks · Library · Ironclad sort.
 * @g16 5.1.0 · Grok16/field-human-bsp · ironclad-secure-api
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "field-human-bsp-ratios-v1";
  const DEFAULT_TREE = {
    axis: "h",
    ratio: 0.52,
    a: {
      axis: "v",
      ratio: 0.58,
      a: { pane: "ask" },
      b: { pane: "tasks" },
    },
    b: {
      axis: "v",
      ratio: 0.5,
      a: { pane: "library" },
      b: { pane: "ironclad" },
    },
  };

  const state = { tree: null, rootEl: null, dragging: null };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function apiUrl(path) {
    if (global.H7Base) return global.H7Base(path);
    return path;
  }

  function pageUrl(path) {
    const base = global.HOSTESS7_PAGES_BASE || "";
    const p = String(path || "");
    if (p.startsWith("http")) return p;
    if (p.startsWith("/")) return (base || "") + p;
    return (base ? base + "/" : "/") + p;
  }

  function loadTree() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_e) {}
    return JSON.parse(JSON.stringify(DEFAULT_TREE));
  }

  function saveTree() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.tree));
    } catch (_e) {}
  }

  function paneTitle(id) {
    return (
      {
        ask: "Ask Hostess 7",
        tasks: "Her tasks",
        library: "Library",
        ironclad: "Ironclad sort",
      }[id] || id
    );
  }

  function paneBody(id) {
    if (id === "ask") {
      return (
        '<div class="hhb-chat-log" id="hhb-chat-log" role="log" aria-live="polite">' +
        '<div class="hhb-msg hostess"><span class="hhb-msg-meta">Hostess 7</span>Human hub online — ask me about wants, library, human UI, or what to do first. I answer from the GitHub brain mirror.</div>' +
        "</div>" +
        '<form class="hhb-form" id="hhb-ask-form">' +
        '<input id="hhb-ask-in" type="text" placeholder="What should we improve for humans?" autocomplete="off" />' +
        '<button type="submit" class="hhb-btn">Ask</button></form>'
      );
    }
    if (id === "tasks") {
      return '<div id="hhb-tasks" class="hhb-empty">Loading tasklist…</div>';
    }
    if (id === "library") {
      return (
        '<form class="hhb-form" id="hhb-lib-form">' +
        '<input id="hhb-lib-q" type="search" placeholder="Search Dewey shelves…" />' +
        '<button type="submit" class="hhb-btn">Find</button></form>' +
        '<div id="hhb-lib-hits"></div>'
      );
    }
    return (
      '<form class="hhb-form" id="hhb-ic-form">' +
      '<select id="hhb-ic-ctx" aria-label="Search context">' +
      '<option value="all">All</option><option value="route">Routes</option><option value="registry">Registry</option><option value="catalog">Catalog</option></select>' +
      '<input id="hhb-ic-q" type="search" placeholder="Ironclad search + BSP sort…" />' +
      '<button type="submit" class="hhb-btn">Sort</button></form>' +
      '<div id="hhb-ic-hits"></div>'
    );
  }

  function renderNode(node, host) {
    if (node.pane) {
      const pane = document.createElement("section");
      pane.className = "hhb-pane";
      pane.dataset.pane = node.pane;
      pane.innerHTML =
        '<header class="hhb-pane-head"><h2>' +
        esc(paneTitle(node.pane)) +
        '</h2></header><div class="hhb-pane-body">' +
        paneBody(node.pane) +
        "</div>";
      host.appendChild(pane);
      return pane;
    }
    const split = document.createElement("div");
    split.className = "hhb-split " + (node.axis === "v" ? "v" : "h");
    host.appendChild(split);
    const aWrap = document.createElement("div");
    const bWrap = document.createElement("div");
    aWrap.style.flex = String(node.ratio || 0.5);
    bWrap.style.flex = String(1 - (node.ratio || 0.5));
    aWrap.style.minWidth = aWrap.style.minHeight = "0";
    bWrap.style.minWidth = bWrap.style.minHeight = "0";
    aWrap.style.display = bWrap.style.display = "flex";
    aWrap.style.flexDirection = bWrap.style.flexDirection = "column";
    aWrap.style.overflow = bWrap.style.overflow = "hidden";
    split.appendChild(aWrap);
    const handle = document.createElement("div");
    handle.className = "hhb-handle";
    handle.dataset.axis = node.axis;
    split.appendChild(handle);
    split.appendChild(bWrap);
    renderNode(node.a, aWrap);
    renderNode(node.b, bWrap);
    bindHandle(handle, node, aWrap, bWrap, split);
  }

  function bindHandle(handle, node, aWrap, bWrap, split) {
    handle.addEventListener("pointerdown", function (ev) {
      ev.preventDefault();
      state.dragging = { handle: handle, node: node, aWrap: aWrap, bWrap: bWrap, split: split, axis: node.axis, start: ev.clientX, startY: ev.clientY, startRatio: node.ratio || 0.5 };
      handle.classList.add("dragging");
      handle.setPointerCapture(ev.pointerId);
    });
    handle.addEventListener("pointermove", function (ev) {
      if (!state.dragging || state.dragging.handle !== handle) return;
      const d = state.dragging;
      const rect = d.split.getBoundingClientRect();
      let ratio = d.startRatio;
      if (d.axis === "h") {
        const dx = ev.clientX - d.start;
        ratio = d.startRatio + dx / Math.max(rect.width, 1);
      } else {
        const dy = ev.clientY - d.startY;
        ratio = d.startRatio + dy / Math.max(rect.height, 1);
      }
      ratio = Math.max(0.18, Math.min(0.82, ratio));
      d.node.ratio = ratio;
      d.aWrap.style.flex = String(ratio);
      d.bWrap.style.flex = String(1 - ratio);
    });
    handle.addEventListener("pointerup", function () {
      if (!state.dragging) return;
      handle.classList.remove("dragging");
      saveTree();
      state.dragging = null;
    });
  }

  function mount(rootId) {
    state.rootEl = document.getElementById(rootId);
    if (!state.rootEl) return;
    state.tree = loadTree();
    state.rootEl.innerHTML = "";
    renderNode(state.tree, state.rootEl);
    wirePanes();
    loadTasks();
    setStatus("GitHub brain mirror · drag handles to BSP resize");
  }

  function setStatus(msg) {
    const el = document.getElementById("hhb-status-text");
    if (el) el.textContent = msg;
  }

  function appendChat(role, text, meta) {
    const log = document.getElementById("hhb-chat-log");
    if (!log) return;
    const div = document.createElement("div");
    div.className = "hhb-msg " + (role === "user" ? "user" : "hostess");
    div.innerHTML =
      '<span class="hhb-msg-meta">' +
      esc(meta || (role === "user" ? "You" : "Hostess 7")) +
      "</span>" +
      esc(text);
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  async function askHostess(query) {
    const r = await fetch(apiUrl("/api/ask"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query }),
      cache: "no-store",
    });
    return r.json();
  }

  async function loadTasks() {
    const el = document.getElementById("hhb-tasks");
    if (!el) return;
    try {
      const doc = await fetch(apiUrl("/api/hostess7-tasklist"), { cache: "no-store" }).then((r) => r.json());
      const open = (doc.open || []).slice();
      if (!open.length) {
        el.innerHTML = '<p class="hhb-empty">Queue clear — ask Hostess 7 what she wants next.</p>';
        return;
      }
      const sorted = await ironcladSort(open, "registry_index");
      const rows = sorted.entries || sorted || open;
      el.innerHTML = rows
        .map(function (t) {
          return (
            '<div class="hhb-task"><strong>' +
            esc(t.title || t.want || "task") +
            "</strong><span>" +
            esc(t.status || "pending") +
            (t.priority ? " · p" + t.priority : "") +
            "</span></div>"
          );
        })
        .join("");
    } catch (e) {
      el.innerHTML = '<p class="hhb-empty">Tasklist unavailable — ' + esc(e.message) + "</p>";
    }
  }

  async function ironcladSearch(q, ctx) {
    const url =
      apiUrl("/api/ironclad/secure-api/search") +
      "?q=" +
      encodeURIComponent(q) +
      "&context=" +
      encodeURIComponent(ctx || "all") +
      "&limit=24";
    return fetch(url, { cache: "no-store" }).then((r) => r.json());
  }

  async function ironcladSort(entries, ctx) {
    return fetch(apiUrl("/api/ironclad/secure-api/sort"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: entries, context: ctx || "registry_index" }),
      cache: "no-store",
    }).then((r) => r.json());
  }

  async function searchLibrary(q) {
    const url = apiUrl("/api/library/search") + "?q=" + encodeURIComponent(q) + "&limit=12";
    return fetch(url, { cache: "no-store" }).then((r) => r.json());
  }

  function wirePanes() {
    const askForm = document.getElementById("hhb-ask-form");
    if (askForm) {
      askForm.addEventListener("submit", async function (ev) {
        ev.preventDefault();
        const input = document.getElementById("hhb-ask-in");
        const q = (input && input.value || "").trim();
        if (!q) return;
        appendChat("user", q);
        if (input) input.value = "";
        const btn = askForm.querySelector("button");
        if (btn) btn.disabled = true;
        setStatus("Asking GitHub brain…");
        try {
          const doc = await askHostess(q);
          appendChat("hostess", doc.text || doc.answer || "(no answer)", doc.route || "github-mirror");
          setStatus("Answered via " + (doc.route || "github-mirror") + " · " + (doc.chunk_count || "?") + " corpus chunks");
          if (/task|want|priority|human|ui/i.test(q)) loadTasks();
        } catch (e) {
          appendChat("hostess", "Ask failed — " + e.message);
          setStatus("Ask error");
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    }

    const libForm = document.getElementById("hhb-lib-form");
    if (libForm) {
      libForm.addEventListener("submit", async function (ev) {
        ev.preventDefault();
        const q = (document.getElementById("hhb-lib-q")?.value || "").trim();
        const hitsEl = document.getElementById("hhb-lib-hits");
        if (!hitsEl) return;
        if (!q) {
          hitsEl.innerHTML = "";
          return;
        }
        hitsEl.innerHTML = '<p class="hhb-empty">Searching library…</p>';
        try {
          const doc = await searchLibrary(q);
          const hits = doc.hits || doc.books || [];
          if (!hits.length) {
            hitsEl.innerHTML = '<p class="hhb-empty">No volumes — try broader terms or open the full library.</p>';
            return;
          }
          hitsEl.innerHTML = hits
            .map(function (b) {
              const title = b.title || b.id || "book";
              const shelf = b.shelf || b.dewey || "";
              return (
                '<button type="button" class="hhb-lib-hit" data-shelf="' +
                esc(shelf) +
                '" data-id="' +
                esc(b.id || "") +
                '"><strong>' +
                esc(title) +
                "</strong><br><span>" +
                esc(shelf) +
                "</span></button>"
              );
            })
            .join("");
          hitsEl.querySelectorAll(".hhb-lib-hit").forEach(function (btn) {
            btn.addEventListener("click", function () {
              global.location.href = pageUrl("/library/?shelf=" + encodeURIComponent(btn.dataset.shelf || "") + "&book=" + encodeURIComponent(btn.dataset.id || ""));
            });
          });
        } catch (e) {
          hitsEl.innerHTML = '<p class="hhb-empty">Library search failed — ' + esc(e.message) + "</p>";
        }
      });
    }

    const icForm = document.getElementById("hhb-ic-form");
    if (icForm) {
      icForm.addEventListener("submit", async function (ev) {
        ev.preventDefault();
        const q = (document.getElementById("hhb-ic-q")?.value || "").trim();
        const ctx = document.getElementById("hhb-ic-ctx")?.value || "all";
        const hitsEl = document.getElementById("hhb-ic-hits");
        if (!hitsEl) return;
        if (!q) {
          hitsEl.innerHTML = "";
          return;
        }
        hitsEl.innerHTML = '<p class="hhb-empty">Ironclad sorting…</p>';
        try {
          const doc = await ironcladSearch(q, ctx);
          const hits = doc.hits || [];
          if (!hits.length) {
            hitsEl.innerHTML = '<p class="hhb-empty">No matches — try route or catalog context.</p>';
            return;
          }
          const sorted = await ironcladSort(hits, ctx === "catalog" ? "catalog_index" : "registry_index");
          const rows = sorted.entries || hits;
          hitsEl.innerHTML = rows
            .map(function (h) {
              const url = h.url || h.exec || (h.kind === "route" ? pageUrl("/" + (h.id || h.label || "")) : "");
              return (
                '<button type="button" class="hhb-ic-hit" data-url="' +
                esc(url) +
                '"><span class="hhb-ic-kind">' +
                esc(h.source || h.kind || "hit") +
                '</span><span>' +
                esc(h.label || h.title || h.name || "result") +
                "</span></button>"
              );
            })
            .join("");
          hitsEl.querySelectorAll(".hhb-ic-hit").forEach(function (btn) {
            btn.addEventListener("click", function () {
              const url = btn.dataset.url;
              if (!url) return;
              if (url.startsWith("http")) global.open(url, "_blank", "noopener");
              else global.location.href = url;
            });
          });
          setStatus("Ironclad · " + rows.length + " hits sorted (" + ctx + ")");
        } catch (e) {
          hitsEl.innerHTML = '<p class="hhb-empty">Ironclad failed — ' + esc(e.message) + "</p>";
        }
      });
    }
  }

  global.FieldHumanBsp = { mount: mount, askHostess: askHostess, ironcladSearch: ironcladSearch };
})(typeof window !== "undefined" ? window : globalThis);