/**
 * Queen Program Surface — all Queen software; Window vs Browser is operator choice.
 */
(function (global) {
  "use strict";

  const API = "/api/queen-program-surface";
  const STORAGE_KEY = "queen-program-surface-v1";

  const state = {
    bundle: null,
    program: null,
    section: null,
    flyout: null,
    ctx: null,
  };

  function $(id, root) {
    return (root || document).getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function inQueenShell() {
    try {
      return global.parent !== global;
    } catch {
      return false;
    }
  }

  function shellPost(action, url, extra) {
    if (!inQueenShell()) return false;
    try {
      global.parent.postMessage({ type: "queen:shell", action, url, ...extra }, global.location.origin);
      return true;
    } catch {
      return false;
    }
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`program-surface HTTP ${r.status}`);
    return r.json();
  }

  function programId(item) {
    return String(item?.id || item?.program_id || "").trim();
  }

  function ensureFlyout() {
    if (state.flyout) return state.flyout;
    const root = document.createElement("div");
    root.className = "qps-props-flyout";
    root.id = "qps-props-flyout";
    root.hidden = true;
    root.innerHTML =
      `<div class="qps-props-sheet" role="dialog" aria-labelledby="qps-fly-title">` +
      `<header class="qps-fly-head">` +
      `<div><h2 class="qps-fly-title" id="qps-fly-title">Properties</h2>` +
      `<p class="qps-fly-sub" id="qps-fly-sub">Queen software</p></div>` +
      `<button type="button" class="qps-fly-close" id="qps-fly-close" aria-label="Close">×</button>` +
      `</header>` +
      `<nav class="qps-fly-menu" id="qps-fly-menu" aria-label="Property sections"></nav>` +
      `<div class="qps-props-pane" id="qps-props-pane"></div>` +
      `<footer class="qps-props-actions" id="qps-props-actions"></footer>` +
      `</div>`;
    document.body.appendChild(root);
    root.addEventListener("click", (ev) => {
      if (ev.target === root) hideProperties();
    });
    $("qps-fly-close", root)?.addEventListener("click", hideProperties);
    state.flyout = root;
    return root;
  }

  function ensureCtx() {
    if (state.ctx) return state.ctx;
    const el = document.createElement("div");
    el.className = "qps-ctx";
    el.id = "qps-ctx";
    el.setAttribute("role", "menu");
    document.body.appendChild(el);
    document.addEventListener("click", () => el.classList.remove("open"));
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") el.classList.remove("open");
    });
    state.ctx = el;
    return el;
  }

  function formatField(field) {
    if (field.format === "bytes" && field.value != null && field.value !== "—") {
      const n = Number(field.value);
      if (!Number.isNaN(n)) {
        if (n < 1024) return `${n} B`;
        if (n < 1048576) return `${(n / 1024).toFixed(1)} KiB`;
        return `${(n / 1048576).toFixed(1)} MiB`;
      }
    }
    if (typeof field.value === "boolean") return field.value ? "Yes" : "No";
    return field.value == null || field.value === "" ? "—" : String(field.value);
  }

  function renderSection(sec, bundle) {
    const pane = $("qps-props-pane");
    if (!pane || !sec) return;
    const fields = (sec.fields || [])
      .filter((f) => f.value != null && f.value !== "—" && f.value !== "")
      .map((f) => {
        const val = formatField(f);
        const copyBtn = f.copy
          ? `<button type="button" class="qps-props-copy" data-copy="${esc(String(f.value))}" title="Copy">⧉</button>`
          : "";
        return `<div class="qps-props-row${f.mono ? " mono" : ""}"><span class="qps-props-k">${esc(f.label)}</span><span class="qps-props-v">${esc(val)}${copyBtn}</span></div>`;
      })
      .join("");

    let surfacePick = "";
    if (sec.id === "launch" && (sec.surface_options || []).length) {
      surfacePick =
        `<div class="qps-surface-pick">` +
        sec.surface_options
          .map(
            (o) =>
              `<button type="button" class="qps-surface-btn${o.selected ? " selected" : ""}" data-surface="${esc(o.id)}">${esc(o.label)}</button>`,
          )
          .join("") +
        `</div>`;
    }

    pane.innerHTML =
      `<section class="qps-props-section">` +
      `<h3>${esc(sec.title)}</h3>` +
      `${sec.banner ? `<p class="qps-props-banner">${esc(sec.banner)}</p>` : ""}` +
      `${fields || '<p class="qps-props-empty">No fields</p>'}` +
      `${surfacePick}` +
      `</section>`;

    pane.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => {
        navigator.clipboard?.writeText(btn.dataset.copy || "");
      });
    });
    pane.querySelectorAll("[data-surface]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const pid = bundle?.program_id || programId(state.program);
        if (!pid) return;
        await api({ action: "set_surface", program_id: pid, surface: btn.dataset.surface });
        await showProperties(state.program);
      });
    });
  }

  function renderPropsMenu(bundle, activeId) {
    const menu = $("qps-fly-menu");
    if (!menu || !bundle) return;
    menu.innerHTML = (bundle.sections || [])
      .map((sec) => {
        const active = sec.id === activeId ? " active" : "";
        return `<button type="button" class="qps-fly-menu-item${active}" data-section="${esc(sec.id)}">${esc(sec.title)}</button>`;
      })
      .join("");
    menu.querySelectorAll("[data-section]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.section = btn.dataset.section;
        const sec = (bundle.sections || []).find((s) => s.id === state.section);
        renderSection(sec, bundle);
        renderPropsMenu(bundle, state.section);
      });
    });
  }

  function renderPropsActions(bundle) {
    const footer = $("qps-props-actions");
    if (!footer || !bundle) return;
    footer.innerHTML = (bundle.actions || [])
      .filter((a) => a.ui && !String(a.ui).startsWith("surface_"))
      .slice(0, 10)
      .map(
        (a) =>
          `<button type="button" class="qps-props-action" data-ui="${esc(a.ui)}">${esc(a.label)}</button>`,
      )
      .join("");
    footer.querySelectorAll("[data-ui]").forEach((btn) => {
      btn.addEventListener("click", () => runAction(btn.dataset.ui, state.program, bundle));
    });
  }

  async function showProperties(item) {
    const pid = programId(item);
    if (!pid) return;
    ensureFlyout();
    state.program = item;
    state.flyout.hidden = false;
    $("qps-props-pane").innerHTML = '<p class="qps-props-loading">Loading Queen properties…</p>';
    const bundle = await api({ action: "properties", program_id: pid });
    if (!bundle.ok) {
      $("qps-props-pane").innerHTML = `<p class="qps-props-empty">${esc(bundle.error || "unavailable")}</p>`;
      return;
    }
    state.bundle = bundle;
    state.section = state.section || bundle.sections?.[0]?.id || "general";
    $("qps-fly-title").textContent = bundle.name || pid;
    $("qps-fly-sub").textContent = `Queen software · ${bundle.effective_surface || "launch"} surface`;
    const sec = (bundle.sections || []).find((s) => s.id === state.section) || bundle.sections?.[0];
    renderPropsMenu(bundle, state.section);
    renderSection(sec, bundle);
    renderPropsActions(bundle);
  }

  function hideProperties() {
    if (state.flyout) state.flyout.hidden = true;
    state.bundle = null;
    state.section = null;
  }

  async function resolveLaunch(item, opts) {
    const pid = programId(item);
    if (!pid) return { ok: false, error: "no_program_id" };
    return api({
      action: "resolve_launch",
      program_id: pid,
      surface: opts?.surface || null,
      new_tab: !!opts?.newTab,
    });
  }

  async function runAction(ui, item, bundle) {
    const prog = bundle?.program || item || {};
    const pid = programId(item) || bundle?.program_id;
    switch (ui) {
      case "open":
        await launchProgram(item, {});
        hideProperties();
        break;
      case "open_window":
        await launchProgram(item, { surface: "window" });
        hideProperties();
        break;
      case "open_browser":
        await launchProgram(item, { surface: "browser" });
        hideProperties();
        break;
      case "open_browser_tab":
        await launchProgram(item, { surface: "browser", newTab: true });
        hideProperties();
        break;
      case "properties":
        await showProperties(item);
        break;
      case "surface_auto":
      case "surface_window":
      case "surface_browser":
        if (pid) {
          const surf = ui.replace("surface_", "");
          await api({ action: "set_surface", program_id: pid, surface: surf });
          await showProperties(item);
        }
        break;
      case "copy_window_url":
        navigator.clipboard?.writeText(prog.window_url || prog.url || "");
        break;
      case "copy_browser_url":
        navigator.clipboard?.writeText(prog.browser_url || prog.url || "");
        break;
      default:
        break;
    }
  }

  async function launchProgram(item, opts) {
    const launch = await resolveLaunch(item, opts);
    if (!launch.ok) return launch;
    const url = launch.launch_url || "";
    const mode = launch.launch_mode || "";

    if (mode === "queen_window") {
      if (global.QueenDesktop?.openWindow) {
        global.QueenDesktop.openWindow({ ...item, url: url || item.url });
        return launch;
      }
      if (inQueenShell()) {
        shellPost("desktop_window", url, { program_id: launch.program_id, name: launch.name });
        return launch;
      }
      global.open(url, "_blank", "noopener");
      return launch;
    }

    if (launch.new_tab || opts?.newTab) {
      if (shellPost("new_tab", url)) return launch;
      global.open(url, "_blank", "noopener");
      return launch;
    }

    if (url.startsWith("queen://")) {
      if (shellPost("new_tab", url)) return launch;
    }

    if (inQueenShell()) {
      if (launch.dock) {
        shellPost("dock", url, { dock: launch.dock });
        return launch;
      }
      shellPost("navigate", url);
      return launch;
    }

    if (url.startsWith("/")) {
      global.location.href = `${global.location.origin}${url}`;
      return launch;
    }
    global.location.href = url;
    return launch;
  }

  async function openContextMenu(x, y, item) {
    hideProperties();
    const pid = programId(item);
    if (!pid) return;
    const ctx = ensureCtx();
    const bundle = await api({ action: "properties", program_id: pid });
    if (!bundle.ok) return;
    state.program = item;
    state.bundle = bundle;

    const groups = bundle.context_groups || [];
    const actions = Object.fromEntries((bundle.actions || []).map((a) => [a.id, a]));
    ctx.innerHTML = groups
      .map((g) => {
        const buttons = (g.items || [])
          .map((id) => actions[id])
          .filter(Boolean)
          .map((a) => {
            const cls = a.primary ? " primary" : "";
            return `<button type="button" data-ui="${esc(a.ui)}" class="${cls.trim()}">${esc(a.label)}</button>`;
          })
          .join("");
        if (!buttons) return "";
        return (
          `<div class="qps-ctx-group">` +
          `<span class="qps-ctx-title">${esc(g.title)}</span>` +
          `${g.hint ? `<span class="qps-ctx-hint">${esc(g.hint)}</span>` : ""}` +
          buttons +
          `</div>`
        );
      })
      .join("");

    ctx.querySelectorAll("[data-ui]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        ctx.classList.remove("open");
        await runAction(btn.dataset.ui, item, bundle);
      });
    });

    ctx.style.left = `${Math.min(x, innerWidth - 240)}px`;
    ctx.style.top = `${Math.min(y, innerHeight - 280)}px`;
    ctx.classList.add("open");
    return bundle;
  }

  global.QueenProgramSurface = {
    api,
    launchProgram,
    showProperties,
    hideProperties,
    openContextMenu,
    resolveLaunch,
    programId,
  };
})(window);