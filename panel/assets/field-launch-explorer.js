(function () {
  "use strict";

  const API = "/api/field-g16-launch";
  const QUEEN_FILES = "http://127.0.0.1:9481/world/queen-files.html";

  let doc = null;
  let items = [];
  let selected = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function toast(msg) {
    const el = $("le-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    setTimeout(function () {
      el.classList.add("hidden");
    }, 3200);
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function filtered() {
    const q = ($("le-search")?.value || "").toLowerCase().trim();
    return items.filter(function (it) {
      if (!q) return true;
      return (
        (it.title || "").toLowerCase().includes(q) ||
        (it.name || "").toLowerCase().includes(q) ||
        (it.path || "").toLowerCase().includes(q)
      );
    });
  }

  function renderGrid() {
    const grid = $("le-grid");
    if (!grid) return;
    const list = filtered();
    grid.innerHTML = list
      .map(function (it) {
        const sel = selected && selected.path === it.path ? " selected" : "";
        return (
          '<button type="button" class="le-card' +
          sel +
          '" data-path="' +
          esc(it.path) +
          '">' +
          '<div class="le-card-title">' +
          esc(it.title || it.name) +
          "</div>" +
          '<div class="le-card-meta">' +
          esc(it.entry || "—") +
          " · " +
          (it.launchable_count != null ? it.launchable_count + " launchables" : "chamber") +
          "</div>" +
          (it.runtime
            ? '<span class="le-card-runtime">' + esc(it.runtime) + "</span>"
            : "") +
          "</button>"
        );
      })
      .join("");

    grid.querySelectorAll(".le-card").forEach(function (card) {
      card.addEventListener("click", function () {
        selectChamber(card.getAttribute("data-path"));
      });
      card.addEventListener("dblclick", function () {
        runChamber(card.getAttribute("data-path"));
      });
      card.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        const it = items.find(function (x) {
          return x.path === card.getAttribute("data-path");
        });
        showCtx(ev.clientX, ev.clientY, it);
      });
    });
  }

  async function selectChamber(path) {
    selected = items.find(function (x) {
      return x.path === path;
    });
    renderGrid();
    const detail = $("le-detail");
    if (!detail || !path) return;
    detail.innerHTML = "<p class='le-empty'>Loading chamber…</p>";
    try {
      const ex = await api(API + "/explore?path=" + encodeURIComponent(path));
      if (!ex.ok) {
        detail.innerHTML = "<p>Explore failed: " + esc(ex.error) + "</p>";
        return;
      }
      const m = ex.manifest || {};
      const lbs = (ex.launchables || [])
        .map(function (lb) {
          return (
            "<li data-lb='" +
            esc(lb.path) +
            "'>▶ " +
            esc(lb.name || lb.path) +
            " <span style='color:var(--le-dim)'>" +
            esc(lb.runtime || "") +
            "</span></li>"
          );
        })
        .join("");
      detail.innerHTML =
        "<h2>" +
        esc(m.title || selected?.title) +
        "</h2>" +
        "<p style='color:var(--le-dim);font-size:11px;word-break:break-all'>" +
        esc(ex.chamber_root || path) +
        "</p>" +
        "<p>Entry: <strong>" +
        esc(m.entry) +
        "</strong> · Runtime: " +
        esc(m.runtime) +
        "</p>" +
        "<p>Uncompiled: " +
        (m.uncompiled ? "yes" : "—") +
        " · Locked: " +
        (m.locked ? "yes" : "—") +
        "</p>" +
        '<div class="le-actions">' +
        '<button type="button" class="le-btn primary" data-act="run">Run chamber</button>' +
        '<button type="button" class="le-btn" data-act="explore">Queen Files browse</button>' +
        '<button type="button" class="le-btn" data-act="copy">Copy path</button>' +
        "</div>" +
        (lbs ? "<ul class='le-launchables'>" + lbs + "</ul>" : "") +
        "<pre>" +
        esc(JSON.stringify(m, null, 2)) +
        "</pre>";

      detail.querySelector("[data-act=run]")?.addEventListener("click", function () {
        runChamber(path);
      });
      detail.querySelector("[data-act=explore]")?.addEventListener("click", function () {
        openQueenFiles(ex.chamber_root || path);
      });
      detail.querySelector("[data-act=copy]")?.addEventListener("click", function () {
        navigator.clipboard?.writeText(path);
        toast("Copied path");
      });
      detail.querySelectorAll("[data-lb]").forEach(function (li) {
        li.addEventListener("click", function () {
          runLaunchable(ex.chamber_root, li.getAttribute("data-lb"));
        });
      });
    } catch (e) {
      detail.innerHTML = "<p>Explore error</p>";
    }
  }

  function openQueenFiles(chamberRoot) {
    const url =
      QUEEN_FILES +
      "?path=" +
      encodeURIComponent(chamberRoot) +
      "&browse_inside=1";
    window.open(url, "_blank", "noopener");
  }

  async function runChamber(path) {
    toast("Firing chamber…");
    try {
      const out = await api(API + "/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path }),
      });
      toast(
        out.ok
          ? "Ran OK · rc " + (out.returncode ?? 0)
          : "Run failed · " + (out.error || out.message || "error")
      );
    } catch (e) {
      toast("Run failed");
    }
  }

  async function runLaunchable(root, rel) {
    toast("Running launchable…");
    try {
      const out = await fetch("/api/queen-file-browser", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "run_launchable",
          path: root + "/" + rel,
        }),
      }).then(function (r) {
        return r.json();
      });
      toast(out.ok ? "Launchable OK" : "Launchable failed");
    } catch (e) {
      toast("Launchable failed");
    }
  }

  function showCtx(x, y, item) {
    if (!item) return;
    const menu = $("le-ctx");
    if (!menu) return;
    const actions = [
      { id: "run", label: "Run chamber" },
      { id: "explore", label: "Explore inside" },
      { id: "manifest", label: "View manifest" },
      { id: "files", label: "Open in Queen Files" },
      { id: "copy", label: "Copy path" },
    ];
    menu.innerHTML = actions
      .map(function (a) {
        return (
          '<button type="button" data-ctx="' +
          a.id +
          '">' +
          esc(a.label) +
          "</button>"
        );
      })
      .join("");
    menu.classList.remove("hidden");
    menu.style.left = Math.min(x, window.innerWidth - 210) + "px";
    menu.style.top = Math.min(y, window.innerHeight - 220) + "px";

    menu.querySelectorAll("[data-ctx]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        menu.classList.add("hidden");
        const act = btn.getAttribute("data-ctx");
        if (act === "run") await runChamber(item.path);
        else if (act === "explore" || act === "manifest") await selectChamber(item.path);
        else if (act === "files") openQueenFiles(item.chamber_root || item.dir);
        else if (act === "copy") {
          navigator.clipboard?.writeText(item.path);
          toast("Copied");
        }
      });
    });
  }

  function renderG16(g16) {
    const pill = $("le-g16-pill");
    if (!pill) return;
    if (g16?.ok) {
      pill.textContent = "g16 " + (g16.dumpversion || "ready");
      pill.classList.add("ready");
      pill.classList.remove("miss");
    } else {
      pill.textContent = "g16 missing";
      pill.classList.add("miss");
      pill.classList.remove("ready");
    }
  }

  async function load(rescan) {
    doc = await api(API + (rescan ? "?rescan=1" : ""));
    const idx = await api(API + "/index");
    items = idx.items || [];
    renderG16(doc.g16);
    const sub = $("le-sub");
    if (sub) sub.textContent = doc.posture || doc.motto || "";
    renderGrid();
  }

  function wire() {
    $("le-scan")?.addEventListener("click", function () {
      load(true);
    });
    $("le-search")?.addEventListener("input", renderGrid);
    document.addEventListener("click", function (ev) {
      if (!ev.target.closest("#le-ctx")) $("le-ctx")?.classList.add("hidden");
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") $("le-ctx")?.classList.add("hidden");
    });
  }

  async function init() {
    if (globalThis.FieldShellDock) {
      FieldShellDock.init({ activeIcon: "launch" });
    }
    wire();
    const params = new URLSearchParams(location.search);
    const path = params.get("path");
    try {
      await load(false);
      if (path) {
        await selectChamber(path);
        if (params.get("run") === "1") await runChamber(path);
      }
    } catch (e) {
      $("le-grid").innerHTML = "<p>Launch Explorer failed to load.</p>";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();