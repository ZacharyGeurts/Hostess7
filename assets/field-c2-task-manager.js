/**
 * C2 task manager bullet — AmmoOS running-task strip + field switch companion.
 * @g16 5.1.0 · Grok16/nexus-field-shell · field-host-desktop
 */
(function (global) {
  "use strict";

  const HOME_ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z"/></svg>';

  const state = { tasks: [], activeId: null, hang: null, hangTimer: null };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function iconHtml(task) {
    const QIE = global.QueenIconEngine;
    if (QIE?.programIconHtml) {
      return QIE.programIconHtml(task, 22, { small: true, base: QIE.PANEL_ICONS });
    }
    const src = task.icon_url || "/assets/queen-favicon-48.png";
    return '<img src="' + esc(src) + '" alt="" width="22" height="22" />';
  }

  function render() {
    const root = document.getElementById("c2tm-root");
    if (!root) return;
    const tasks = state.tasks || [];
    let html = '<span class="c2tm-hint">Switch</span>';
    html +=
      '<button type="button" class="c2tm-btn c2tm-home" data-c2tm="home" title="Six tools (desktop)">' +
      HOME_ICON +
      "</button>";
    tasks.forEach(function (task) {
      const id = task.shellWin || task.id;
      const active = id && (id === state.activeId || task.id === state.activeId);
      html +=
        '<button type="button" class="c2tm-btn' +
        (active ? " active" : "") +
        '" data-c2tm="' +
        esc(id) +
        '" title="' +
        esc(task.name || task.id) +
        '">' +
        iconHtml(task) +
        "</button>";
    });
    root.innerHTML = html;
    root.querySelectorAll("[data-c2tm]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = btn.dataset.c2tm;
        if (id === "home") {
          global.NexusFieldShell?.showDesktop?.();
          return;
        }
        global.NexusFieldShell?.toggle?.(id);
      });
    });
  }

  function mount(rootEl) {
    if (!rootEl) return;
    rootEl.innerHTML =
      '<div class="c2tm-hang" id="c2tm-hang" hidden></div>' +
      '<div class="c2tm-root" id="c2tm-root" role="toolbar" aria-label="Task manager"></div>';
    render();
    if (state.hangTimer) clearInterval(state.hangTimer);
    state.hangTimer = setInterval(pollHang, 4000);
    pollHang();
  }

  function sync(tasks, activeId) {
    state.tasks = Array.isArray(tasks) ? tasks : [];
    state.activeId = activeId || null;
    render();
  }

  async function hangRespond(id, choice) {
    try {
      await fetch("/Hostess7/api/field-monster-shell/hang-respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ id: id, choice: choice }),
      });
    } catch (_) {}
    state.hang = null;
    renderHang();
  }

  function hangHeadline(row) {
    const label = row.label || "Program";
    const phase = String(row.phase || "").toLowerCase();
    if (phase === "prompt") return label + " — quiet a while; still running?";
    if (row.pid_alive === false) return label + " — finished or moved on";
    return label + " — working quietly (Monster is watching)";
  }

  function renderHang() {
    const bar = document.getElementById("c2tm-hang");
    if (!bar) return;
    const row = state.hang;
    if (!row || row.pid_alive === false) {
      bar.hidden = true;
      bar.innerHTML = "";
      return;
    }
    bar.hidden = false;
    const detail = String(row.detail || "").split("\n")[0].slice(0, 160);
    bar.innerHTML =
      '<div class="c2tm-hang-inner">' +
      '<span class="c2tm-hang-label">' +
      esc(hangHeadline(row)) +
      "</span>" +
      '<span class="c2tm-hang-detail">' +
      esc(detail) +
      "</span>" +
      '<button type="button" class="c2tm-hang-wait" data-hang-wait="' +
      esc(row.id) +
      '">Wait</button>' +
      '<button type="button" class="c2tm-hang-quit" data-hang-quit="' +
      esc(row.id) +
      '">End task</button>' +
      "</div>";
    bar.querySelector("[data-hang-wait]")?.addEventListener("click", function () {
      hangRespond(row.id, "wait");
    });
    bar.querySelector("[data-hang-quit]")?.addEventListener("click", function () {
      if (!confirm("End task " + (row.label || row.id) + "?")) return;
      hangRespond(row.id, "quit");
    });
  }

  async function pollHang() {
    try {
      const res = await fetch("/Hostess7/api/field-monster-shell/hang-pending", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const doc = await res.json();
      const pending = Array.isArray(doc.pending) ? doc.pending[0] : null;
      if (!pending || !pending.id || pending.pid_alive === false) {
        state.hang = null;
      } else {
        state.hang = pending;
      }
      renderHang();
    } catch (_) {}
  }

  global.FieldC2TaskManager = { mount: mount, sync: sync, pollHang: pollHang };
})(window);