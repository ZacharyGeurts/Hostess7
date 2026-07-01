/**
 * Hostess 7 program frame — File menu + full Help on every H7 window.
 */
(function (global) {
  "use strict";

  const HELP_URL = "/api/hostess7/program-help";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  async function fetchHelp(programId) {
    try {
      const res = await fetch(`${HELP_URL}?id=${encodeURIComponent(programId)}`, { credentials: "same-origin" });
      return await res.json();
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  }

  function buildHelpHtml(doc) {
    if (!doc?.sections?.length) {
      return `<h2>${esc(doc?.title || "Help")}</h2><p>${esc(doc?.summary || "No help loaded.")}</p>`;
    }
    let html = `<h2>${esc(doc.title)}</h2><p>${esc(doc.summary || "")}</p>`;
    for (const s of doc.sections) {
      html += `<h3>${esc(s.heading)}</h3><p>${esc(s.body)}</p>`;
    }
    return html;
  }

  function closeMenus(root) {
    root.querySelectorAll(".h7pf-menu.open").forEach((m) => m.classList.remove("open"));
  }

  function mount(opts) {
    const programId = opts.programId || "hostess7-training";
    const title = opts.title || "Hostess 7";
    const icon = opts.icon || "/assets/hostess7-training-chamber.svg";
    const bodyEl = opts.bodyEl || document.body;
    const onRefresh = opts.onRefresh || (() => location.reload());
    const onExport = opts.onExport || null;

    if (bodyEl.classList.contains("h7pf-wrapped")) return;

    const root = document.createElement("div");
    root.className = "h7pf-root";

    const menubar = document.createElement("header");
    menubar.className = "h7pf-menubar";
    menubar.innerHTML = `
      <img class="h7pf-icon" src="${esc(icon)}" alt="" width="22" height="22" />
      <span class="h7pf-title">${esc(title)}</span>
      <div class="h7pf-menu" data-menu="file">
        <button type="button">File</button>
        <div class="h7pf-dropdown">
          <button type="button" data-act="refresh">Refresh panel</button>
          <button type="button" data-act="export">Export panel JSON</button>
          <hr />
          <button type="button" data-act="close">Close window</button>
        </div>
      </div>
      <div class="h7pf-menu" data-menu="help">
        <button type="button">Help</button>
        <div class="h7pf-dropdown">
          <button type="button" data-act="help-full">Full help…</button>
          <button type="button" data-act="help-about">About this program</button>
        </div>
      </div>
    `;

    const content = document.createElement("div");
    content.className = "h7pf-body";
    while (bodyEl.firstChild) {
      content.appendChild(bodyEl.firstChild);
    }

    const overlay = document.createElement("div");
    overlay.className = "h7pf-help-overlay";
    overlay.innerHTML = `<div class="h7pf-help-panel" role="dialog" aria-labelledby="h7pf-help-title">
      <div id="h7pf-help-body"></div>
      <button type="button" class="h7pf-help-close">Close help</button>
    </div>`;

    root.appendChild(menubar);
    root.appendChild(content);
    bodyEl.appendChild(root);
    bodyEl.appendChild(overlay);
    bodyEl.classList.add("h7pf-wrapped");

    const helpBody = overlay.querySelector("#h7pf-help-body");
    let helpCache = null;

    async function showHelp(mode) {
      if (!helpCache) {
        const raw = await fetchHelp(programId);
        helpCache = raw.help || raw;
      }
      if (mode === "about") {
        helpBody.innerHTML = `<h2 id="h7pf-help-title">${esc(helpCache.title || title)}</h2>
          <p>${esc(helpCache.summary || "")}</p>
          <p><small>Program id: ${esc(programId)} · Hostess 7 sovereign stack</small></p>`;
      } else {
        helpBody.innerHTML = buildHelpHtml(helpCache);
      }
      overlay.classList.add("open");
    }

    menubar.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".h7pf-menu > button");
      if (btn) {
        const menu = btn.parentElement;
        const wasOpen = menu.classList.contains("open");
        closeMenus(root);
        if (!wasOpen) menu.classList.add("open");
        ev.stopPropagation();
        return;
      }
      const act = ev.target.closest("[data-act]")?.dataset?.act;
      if (!act) return;
      closeMenus(root);
      if (act === "refresh") onRefresh();
      if (act === "export") {
        if (onExport) onExport();
        else {
          fetch(opts.exportUrl || `/api/hostess7/training/json`)
            .then((r) => r.json())
            .then((doc) => {
              const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = `${programId}-panel.json`;
              a.click();
              URL.revokeObjectURL(a.href);
            })
            .catch(() => alert("Export failed"));
        }
      }
      if (act === "close") window.close();
      if (act === "help-full") showHelp("full");
      if (act === "help-about") showHelp("about");
    });

    document.addEventListener("click", () => closeMenus(root));
    overlay.querySelector(".h7pf-help-close").addEventListener("click", () => overlay.classList.remove("open"));
    overlay.addEventListener("click", (ev) => {
      if (ev.target === overlay) overlay.classList.remove("open");
    });
  }

  global.Hostess7ProgramFrame = { mount, fetchHelp };
})(window);