/**
 * Queen Files 2026 — split pane browser, wishlist menu, zero-cost 4-slot jail.
 * Conventions: absolute, SG/, ~/, queen://files/, queen://, file://
 */
(function () {
  "use strict";

  const API = "/api/queen-file-browser";
  const state = {
    path: "",
    roots: [],
    hotbar: [],
    dock: [],
    nav: { stack: [], index: -1 },
    entries: [],
    launchables: [],
    selected: null,
    ctxEntry: null,
    ctxBundle: null,
    propsEntry: null,
    propsBundle: null,
    propsSection: null,
    showHidden: false,
    launchablesOnly: false,
    sortMode: "dirs_first",
    zeroCost: null,
    dragId: null,
    fileTypes: null,
    iconOverrides: null,
    previewOn: true,
    previewPath: "",
    searchQ: "",
    searchTimer: null,
    searchMode: "local",
    fileTypes: null,
    library: null,
    typeFilter: null,
    typesSearch: "",
    librarySearch: "",
    libraryTab: "programs",
    libraryFacet: { kind: "", dewey: "", platform: "" },
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
    });
    return r.json();
  }

  function fmtSize(n) {
    if (n == null) return "—";
    const u = ["B", "KB", "MB", "GB"];
    let v = Number(n);
    let i = 0;
    while (v >= 1024 && i < u.length - 1) {
      v /= 1024;
      i += 1;
    }
    return `${v < 10 && i > 0 ? v.toFixed(1) : Math.round(v)} ${u[i]}`;
  }

  function alwaysKnowsBadge(entry) {
    const af = entry?.always;
    if (!af?.knows?.length) return "";
    const n = af.knows_count ?? af.knows.length;
    const ghost = af.overlay?.destroyed || af.overlay?.catalog_only;
    const rollback = af.timeshift?.rollback_available ? "↺" : "";
    const cls = ghost ? "qf-knows qf-knows--ghost" : "qf-knows";
    return `<span class="${cls}" title="${esc((af.knows || []).join(", "))}">${rollback}◈${n}</span>`;
  }

  function alwaysMeta(entry) {
    const af = entry?.always;
    if (!af) return fmtSize(entry?.size);
    const parts = [];
    if (af.role) parts.push(af.role);
    if (af.value?.label) parts.push(`v${af.value.value ?? ""}`);
    if (af.overlay?.destroyed) parts.push("ghost");
    else if (af.overlay?.deleted) parts.push("deleted");
    if (af.sha256) parts.push(af.sha256);
    return parts.join(" · ") || fmtSize(entry?.size);
  }

  function alwaysSecurityBanner(entry) {
    const sec = entry?.always?.security || {};
    if (!sec.system_managed && !entry?.always?.knows?.length) return "";
    const posture = sec.posture || "System secures this file — no password needed";
    return `<div class="qf-sec-banner" title="${esc(posture)}">
      <span class="qf-sec-icon">◈</span>
      <span class="qf-sec-text">${esc(posture)}</span>
      <button type="button" class="qf-sec-props" data-always-props="${esc(entry.path)}">Properties</button>
    </div>`;
  }

  function alwaysDetailsHtml(entry) {
    const af = entry?.always;
    if (!af) return alwaysSecurityBanner(entry);
    const knows = (af.knows || []).map((k) => `<span class="qf-always-tag">${esc(k)}</span>`).join("");
    const ai = af.ai || {};
    const ts = af.timeshift || {};
    const ov = af.overlay || {};
    const sec = af.security || {};
    return `
      ${alwaysSecurityBanner(entry)}
      <div class="qf-always-panel">
        <div class="qf-always-head">
          <strong>Always File</strong>
          <span class="qf-always-conf">${Math.round((af.confidence || 0) * 100)}% aware</span>
        </div>
        ${af.description ? `<p class="qf-always-desc">${esc(af.description)}</p>` : ""}
        <div class="qf-always-tags">${knows}</div>
        <dl class="qf-always-dl">
          ${af.role ? `<dt>Role</dt><dd>${esc(af.role)}</dd>` : ""}
          ${sec.system_managed ? `<dt>Security</dt><dd>System managed · no password</dd>` : ""}
          ${ai.read_max_bytes != null ? `<dt>AI read cap</dt><dd>${esc(String(ai.read_max_bytes))} B · ${esc(ai.edit_policy || "checkpoint_first")}</dd>` : ""}
          ${ov.destroyed ? `<dt>Overlay</dt><dd>destroyed · catalog only</dd>` : ov.deleted ? `<dt>Overlay</dt><dd>deleted</dd>` : ""}
          ${ts.rollback_available ? `<dt>TimeShift</dt><dd>rollback available${ts.latest_checkpoint ? ` · ${esc(ts.latest_checkpoint)}` : ""}</dd>` : ""}
        </dl>
        <div class="qf-always-actions">
          <button type="button" class="qf-always-btn" data-always-props="${esc(entry.path)}">All properties…</button>
          <button type="button" class="qf-always-btn qf-always-btn--ghost" data-always-checkpoint="${esc(entry.path)}">Checkpoint</button>
        </div>
      </div>`;
  }

  function bindAlwaysPreviewActions(root) {
    if (!root) return;
    root.querySelectorAll("[data-always-props]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const entry = findEntry(btn.dataset.alwaysProps);
        if (entry) showProperties(entry);
      });
    });
    root.querySelectorAll("[data-always-checkpoint]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await alwaysCheckpoint(btn.dataset.alwaysCheckpoint);
      });
    });
  }

  function launchMeta(entry) {
    if (entry?.launch_meta) {
      const m = entry.launch_meta;
      const parts = [];
      if (m.entry) parts.push(m.entry);
      if (m.runtime) parts.push(m.runtime);
      if (m.file_count != null) parts.push(`${m.file_count} files`);
      if (m.locked || m.secured) parts.push(`secured${m.seal_generation != null ? `·g${m.seal_generation}` : ""}`);
      return parts.join(" · ") || fmtSize(entry.size);
    }
    const ft = entry?.file_type;
    if (ft?.type_id === "launch" || entry?.facade) {
      const parts = [];
      if (ft?.entry) parts.push(ft.entry);
      if (ft?.runtime) parts.push(ft.runtime);
      if (ft?.file_count != null) parts.push(`${ft.file_count} files`);
      if (parts.length) return parts.join(" · ");
    }
    return entry?.kind === "dir" ? "—" : fmtSize(entry.size);
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch (_) {
      return iso.slice(0, 16);
    }
  }

  function resolveIcon(entry) {
    if (global.QueenIconEngine?.fileBatteryId) {
      return { type: "battery", id: global.QueenIconEngine.fileBatteryId(entry) };
    }
    const ft = entry?.file_type;
    if (entry?.kind === "dir") return "📁";
    if (entry?.kind === "symlink") return "🔗";
    if (ft?.global_icon) return ft.global_icon;
    return "📄";
  }

  function iconHtml(icon, entry) {
    if (entry && global.QueenIconEngine?.fileIconHtml) {
      return global.QueenIconEngine.fileIconHtml(entry, 20);
    }
    if (icon && typeof icon === "object" && icon.type === "battery" && global.QueenIconEngine?.fileIconHtml) {
      return global.QueenIconEngine.fileIconHtml({ kind: icon.id === "folder" ? "dir" : "file", file_type: { type_id: icon.id } }, 20);
    }
    if (icon && typeof icon === "object" && icon.type === "asset") {
      const name = icon.asset || "code";
      return `<span class="ico ico--${esc(name)}" role="img" aria-hidden="true"></span>`;
    }
    return `<span class="ico">${esc(String(icon || "📄"))}</span>`;
  }

  function entryAction(entry) {
    return entry?.file_type?.action || entry?.action || (entry?.kind === "dir" ? "open_dir" : "open_tab");
  }

  function renderZeroCost(doc) {
    const z = doc?.zero_cost_4_slot || doc?.zero_cost_4slot || doc;
    state.zeroCost = z;
    const pill = $("qf-zero-pill");
    if (!pill) return;
    const slots = (z.slots || []).map((s) => (typeof s === "string" ? s : s.id)).join(" · ");
    pill.textContent = `4-slot · ${z.runtime_tax ?? 0}% tax · ${slots || "TIME MEMORY THERMO CONTEXT"}`;
    pill.title = z.rule || "Zero-cost security — tamper aborts";
  }

  function renderCrumbs(path) {
    const el = $("qf-crumb");
    if (!el) return;
    const parts = path.split("/").filter(Boolean);
    const buttons = [`<button type="button" data-crumb="/">/</button>`];
    let acc = "";
    for (const p of parts) {
      acc += `/${p}`;
      buttons.push(`<span class="sep">/</span>`);
      buttons.push(`<button type="button" data-crumb="${esc(acc)}">${esc(p)}</button>`);
    }
    el.innerHTML = buttons.join("");
    el.querySelectorAll("[data-crumb]").forEach((btn) => {
      btn.addEventListener("click", () => openPath(btn.dataset.crumb === "/" ? state.roots[0]?.path : btn.dataset.crumb));
    });
  }

  function renderDock() {
    const bar = $("qf-dock");
    if (!bar) return;
    const slots = (state.dock || []).sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    if (!slots.length) {
      bar.innerHTML = '<span class="qf-hotbar-label">Dock</span>';
      return;
    }
    bar.innerHTML =
      '<span class="qf-hotbar-label">Dock</span>' +
      slots
        .map(
          (s) =>
            `<button type="button" class="qf-dock-slot${state.path === s.path ? " active" : ""}" data-path="${esc(s.path)}" title="${esc(s.path)}">${esc(s.label || s.path.split("/").pop())}</button>`,
        )
        .join("");
    bar.querySelectorAll(".qf-dock-slot").forEach((btn) => {
      btn.addEventListener("click", () => openPath(btn.dataset.path));
    });
  }

  function updateNavButtons() {
    const nav = state.nav || { stack: [], index: -1 };
    const back = $("qf-back");
    const fwd = $("qf-forward");
    if (back) back.disabled = (nav.index ?? -1) <= 0;
    if (fwd) fwd.disabled = (nav.index ?? -1) >= (nav.stack?.length ?? 0) - 1;
  }

  function renderMobilePickers() {
    const rootSel = $("qf-mobile-root");
    const jumpSel = $("qf-mobile-jump");
    if (rootSel) {
      rootSel.innerHTML = (state.roots || [])
        .map((r) => `<option value="${esc(r.path)}">${esc(r.label)}</option>`)
        .join("");
      rootSel.value = state.roots.find((r) => state.path.startsWith(r.path))?.path || state.roots[0]?.path || "";
    }
    if (jumpSel) {
      const parts = (state.path || "").split("/").filter(Boolean);
      let acc = "";
      const opts = parts.map((p) => {
        acc += `/${p}`;
        return `<option value="${esc(acc)}">${esc(p)}</option>`;
      });
      jumpSel.innerHTML = opts.join("");
      jumpSel.hidden = parts.length < 2;
      jumpSel.value = state.path || "";
    }
  }

  function sortEntries(entries) {
    const rows = [...(entries || [])];
    const mode = state.sortMode || "dirs_first";
    if (mode === "dirs_first") {
      return rows.sort((a, b) => {
        const ad = a.kind === "dir" || a.kind === "launch_facade" ? 0 : 1;
        const bd = b.kind === "dir" || b.kind === "launch_facade" ? 0 : 1;
        if (ad !== bd) return ad - bd;
        return (a.name || "").localeCompare(b.name || "");
      });
    }
    if (mode === "name") return rows.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    if (mode === "size") return rows.sort((a, b) => (Number(b.size) || 0) - (Number(a.size) || 0));
    if (mode === "mtime") return rows.sort((a, b) => String(b.mtime || "").localeCompare(String(a.mtime || "")));
    if (mode === "type") {
      return rows.sort((a, b) => {
        const at = a.file_type?.type_id || a.kind || "";
        const bt = b.file_type?.type_id || b.kind || "";
        return at.localeCompare(bt) || (a.name || "").localeCompare(b.name || "");
      });
    }
    return rows;
  }

  function renderLaunchablesPanel(rows) {
    const panel = $("qf-launchables-panel");
    if (!panel) return;
    const list = rows || state.launchables || [];
    if (!list.length) {
      panel.hidden = true;
      panel.innerHTML = "";
      return;
    }
    panel.hidden = false;
    panel.innerHTML =
      `<strong>Launchables (${list.length})</strong>` +
      list
        .map(
          (e) =>
            `<div class="qf-launch-row" data-path="${esc(e.path)}">▶ <span>${esc(e.name)}</span> <span class="meta">${esc(e.runtime || e.file_type?.runtime || "")}</span></div>`,
        )
        .join("");
    panel.querySelectorAll(".qf-launch-row").forEach((row) => {
      row.addEventListener("click", () => runLaunchable(row.dataset.path));
    });
  }

  async function runLaunchable(path) {
    const out = await api({ action: "run_launchable", path });
    const status = $("qf-status-right");
    if (status) status.textContent = out.message || (out.ok ? "Launchable run ok" : out.error || "failed");
    return out;
  }

  async function dockCurrent() {
    if (!state.path) return;
    const out = await api({ action: "dock_push", path: state.path });
    if (out.ok) {
      state.dock = out.dock?.slots || state.dock;
      renderDock();
    }
  }

  async function navBack() {
    const out = await api({ action: "nav_back" });
    if (out.ok && out.path) await openPath(out.path, { skipNavPush: true });
    else updateNavButtons();
  }

  async function navForward() {
    const out = await api({ action: "nav_forward" });
    if (out.ok && out.path) await openPath(out.path, { skipNavPush: true });
    else updateNavButtons();
  }

  function renderHotbar() {
    const bar = $("qf-hotbar");
    if (!bar) return;
    const label = `<span class="qf-hotbar-label">Wishlist</span>`;
    const slots = (state.hotbar || [])
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map(
        (s) => `
      <div class="qf-hot-slot" draggable="true" data-id="${esc(s.id)}" data-path="${esc(s.path)}" title="${esc(s.path)}">
        <span class="ico">${s.kind === "folder" ? "📁" : "📄"}</span>
        <span class="lbl">${esc(s.label || s.path.split("/").pop())}</span>
        <button type="button" class="rm" data-rm="${esc(s.id)}" aria-label="Remove">×</button>
      </div>`,
      )
      .join("");
    bar.innerHTML = label + slots;
    bar.querySelectorAll(".qf-hot-slot").forEach(bindHotSlot);
    bar.querySelectorAll("[data-rm]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        removeHotSlot(btn.dataset.rm);
      });
    });
  }

  function bindHotSlot(el) {
    el.addEventListener("dragstart", (e) => {
      state.dragId = el.dataset.id;
      el.classList.add("dragging");
      e.dataTransfer?.setData("text/plain", el.dataset.id || "");
      e.dataTransfer.effectAllowed = "move";
    });
    el.addEventListener("dragend", () => {
      el.classList.remove("dragging");
      state.dragId = null;
      document.querySelectorAll(".qf-hot-slot.drag-over").forEach((n) => n.classList.remove("drag-over"));
    });
    el.addEventListener("dragover", (e) => {
      e.preventDefault();
      el.classList.add("drag-over");
    });
    el.addEventListener("dragleave", () => el.classList.remove("drag-over"));
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.classList.remove("drag-over");
      const fromId = e.dataTransfer?.getData("text/plain") || state.dragId;
      const toId = el.dataset.id;
      if (fromId && toId && fromId !== toId) reorderHotbar(fromId, toId);
    });
    el.addEventListener("click", (e) => {
      if (e.target.closest(".rm")) return;
      openPath(el.dataset.path);
    });
    el.querySelector(".lbl")?.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      const slot = state.hotbar.find((s) => s.id === el.dataset.id);
      if (!slot) return;
      const next = window.prompt("Wishlist label", slot.label || "");
      if (next === null) return;
      slot.label = next.trim() || slot.label;
      persistHotbar(state.hotbar);
    });
  }

  function reorderHotbar(fromId, toId) {
    const slots = [...state.hotbar].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    const fromIdx = slots.findIndex((s) => s.id === fromId);
    const toIdx = slots.findIndex((s) => s.id === toId);
    if (fromIdx < 0 || toIdx < 0) return;
    const [item] = slots.splice(fromIdx, 1);
    slots.splice(toIdx, 0, item);
    slots.forEach((s, i) => {
      s.order = i;
    });
    persistHotbar(slots);
  }

  async function persistHotbar(slots) {
    const out = await api({ action: "hotbar_save", slots });
    if (out.ok) {
      state.hotbar = out.hotbar?.slots || slots;
      renderHotbar();
    }
  }

  function removeHotSlot(id) {
    const slots = state.hotbar.filter((s) => s.id !== id);
    slots.forEach((s, i) => {
      s.order = i;
    });
    persistHotbar(slots);
  }

  async function addToHotbar(entry) {
    if (!entry?.path) return;
    const id = `hot-${Date.now().toString(36)}`;
    const slots = [
      ...state.hotbar,
      {
        id,
        path: entry.path,
        label: entry.name || entry.path.split("/").pop(),
        kind: entry.kind === "dir" ? "folder" : "file",
        order: state.hotbar.length,
      },
    ];
    await persistHotbar(slots);
  }

  function renderTree(tree, container) {
    if (!container) return;
    if (!tree?.length) {
      container.innerHTML = '<p class="qf-empty">No folders</p>';
      return;
    }
    const ul = document.createElement("ul");
    ul.className = "qf-tree-node";
    for (const node of tree) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = `📁 ${node.name}`;
      btn.dataset.path = node.path;
      if (node.path === state.path) btn.classList.add("active");
      btn.addEventListener("click", () => openPath(node.path));
      li.appendChild(btn);
      if (node.children?.length) {
        const sub = document.createElement("ul");
        sub.className = "qf-tree-node";
        for (const ch of node.children) {
          const cli = document.createElement("li");
          const cbtn = document.createElement("button");
          cbtn.type = "button";
          cbtn.textContent = `📁 ${ch.name}`;
          cbtn.dataset.path = ch.path;
          if (ch.path === state.path) cbtn.classList.add("active");
          cbtn.addEventListener("click", () => openPath(ch.path));
          cli.appendChild(cbtn);
          sub.appendChild(cli);
        }
        li.appendChild(sub);
      }
      ul.appendChild(li);
    }
    container.innerHTML = "";
    container.appendChild(ul);
  }

  function findEntry(path) {
    return state.entries.find((e) => e.path === path) || null;
  }

  function setPreviewOpen(on) {
    state.previewOn = on !== false;
    const main = $("qf-main");
    if (main) main.classList.toggle("qf-preview-off", !state.previewOn);
    $("qf-preview-toggle")?.classList.toggle("active", state.previewOn);
  }

  async function showPreview(path) {
    if (!state.previewOn || !path) return;
    const entry = findEntry(path);
    const title = $("qf-preview-title");
    const langEl = $("qf-preview-lang");
    const body = $("qf-preview-body");
    const codeBtn = $("qf-preview-code");
    if (title) title.textContent = entry?.name || path.split("/").pop() || path;
    const alwaysBlock = alwaysDetailsHtml(entry);
    if (entry?.kind === "dir") {
      if (langEl) langEl.textContent = "folder";
      if (body) {
        body.innerHTML =
          (alwaysBlock || "") + '<div class="qv-empty">Folder — double-click to open</div>';
        bindAlwaysPreviewActions(body);
      }
      if (codeBtn) codeBtn.hidden = true;
      return;
    }
    const QV = window.QueenViewer;
    if (!QV?.mount) {
      if (body) {
        body.innerHTML =
          (alwaysBlock || "") + '<div class="qv-empty">Viewer module not loaded</div>';
        bindAlwaysPreviewActions(body);
      }
      return;
    }
    state.previewPath = path;
    if (body) body.innerHTML = alwaysBlock + '<div class="qf-preview-viewer"></div>';
    bindAlwaysPreviewActions(body);
    const mountEl = body?.querySelector(".qf-preview-viewer") || body;
    const out = await QV.mount(mountEl, path, entry);
    global.QueenZoomLightbox?.bind?.(mountEl);
    if (langEl) langEl.textContent = out?.language || "";
    if (codeBtn) {
      codeBtn.hidden = false;
      codeBtn.onclick = () => navigateUrl(codeViewerUrl(path));
    }
  }

  function codeViewerUrl(path) {
    const base = `${location.origin}/world/queen-code.html`;
    return `${base}?path=${encodeURIComponent(path)}`;
  }

  const BIG_DRIVE_EXTS = new Set([
    ".iso", ".cue", ".chd", ".img", ".ima", ".flp", ".dsk", ".raw", ".dd",
    ".vhd", ".vhdx", ".vdi", ".qcow2", ".qcow", ".dmg", ".fielddrive", ".bin", ".nrg",
  ]);

  function panelPort() {
    try {
      return parent?.document?.body?.dataset?.nexusPanelPort || document.body?.dataset?.nexusPanelPort || "9477";
    } catch (_) {
      return "9477";
    }
  }

  function bigDriveEligible(entry) {
    if (!entry || entry.kind === "dir") return false;
    if (entry.file_type?.big_drive) return true;
    const ext = (entry.path || "").toLowerCase().replace(/.*(\.[^./]+)$/, "$1");
    return BIG_DRIVE_EXTS.has(ext);
  }

  function bigDriveUrl(path) {
    return `http://127.0.0.1:${panelPort()}/field-big-drive?path=${encodeURIComponent(path)}`;
  }

  function openInTab(path) {
    const entry = findEntry(path);
    const action = entry ? entryAction(entry) : "open_tab";
    if (action === "open_code") {
      navigateUrl(codeViewerUrl(path));
      return;
    }
    const url = path.startsWith("http") ? path : `file://${path}`;
    navigateUrl(url);
  }

  function navigateUrl(url) {
    try {
      if (parent?.QueenOS?.browser?.navigate) {
        parent.QueenOS.browser.navigate(url);
        return;
      }
      if (parent?.QueenOS?.browser?.newTab) {
        parent.QueenOS.browser.newTab(url);
        return;
      }
    } catch (_) {
      /* cross-origin */
    }
    if (url.includes("queen-code.html")) {
      location.href = url;
      return;
    }
    window.open(url, "_blank", "noopener");
  }

  async function releaseCompileMode(entry) {
    const out = await api({ action: "compile_mode", path: entry.path });
    const status = $("qf-status-right");
    if (status) {
      status.textContent = out.ok
        ? `Release compile · ${out.artifact || "staged"}`
        : out.error || "compile failed";
    }
    if (out.ok && out.message) {
      $("qf-status-left").textContent = out.message;
    }
    return out;
  }

  async function launchSpv(path) {
    const out = await api({ action: "launch", path });
    const status = $("qf-status-right");
    if (status) status.textContent = out.message || (out.ok ? "SPIR-V launched" : out.error || "launch failed");
    return out;
  }

  async function runLaunchChamber(entry) {
    const out = await api({ action: "run_launch", path: entry.path });
    const status = $("qf-status-right");
    const left = $("qf-status-left");
    if (status) {
      const ops = out.ops_per_sec;
      const plane = out.plane || {};
      const suffix = ops
        ? ` · ${Number(ops).toLocaleString(undefined, { maximumFractionDigits: 0 })} ops/s`
        : "";
      const cache = plane.cache_hit ? " · plane cache" : plane.convert_ms != null ? ` · convert ${plane.convert_ms}ms` : "";
      status.textContent =
        (out.message || (out.ok ? "Chamber run ok" : out.error || "launch failed")) + suffix + cache;
    }
    if (left && out.ok) {
      if (out.launch_mode === "organized_field" && out.field_count != null) {
        left.textContent = `Organized field · ${out.field_count} files · ${out.plane?.toolchain || out.plane?.runtime || "run"}`;
      } else if (out.singular_field && out.field_count != null) {
        left.textContent = `Singular field · ${out.field_count} on plane · trimmed ${out.trimmed_excess ?? 0} excess`;
      } else if (out.stdout_tail) {
        left.textContent = out.stdout_tail.split("\n").filter(Boolean).slice(-3).join(" · ") || out.message;
      }
    }
    return out;
  }

  async function fetchLaunchSeal() {
    if (state.launchSeal?.generation != null) return state.launchSeal;
    try {
      const r = await fetch("/api/compatibility");
      const d = await r.json();
      state.launchSeal = d.launch_seal || { generation: 0 };
      return state.launchSeal;
    } catch (_) {
      return { generation: 0 };
    }
  }

  async function createLaunchFile(entry, refresh = true) {
    const seal = await fetchLaunchSeal();
    const out = await api({
      action: "create_launch",
      path: entry.chamber_root || entry.path,
      refresh: Boolean(refresh),
      launch_seal_generation: seal.generation,
    });
    const status = $("qf-status-right");
    if (status) {
      if (out.ok) {
        status.textContent =
          `Secured ${out.path || ".launch"} · gen ${out.seal_generation ?? seal.generation} · ` +
          `${out.manifest?.launchable_count ?? "?"} launchables`;
      } else if (out.error === "launch_seal_stale_sync_compatibility_layers_first") {
        status.textContent = "Sync compatibility layers first, then refresh .launch";
      } else if (out.error === "launch_locked") {
        status.textContent = "Launch locked — sync layers, then refresh";
      } else {
        status.textContent = out.error || out.hint || "seal failed";
      }
    }
    if (out.ok) await openPath(state.path);
    return out;
  }

  async function runDefaultAction(entry) {
    if (!entry) return;
    const action = entryAction(entry);
    if (action === "run_launch" || entry.kind === "launch_facade" || entry.facade) {
      await runLaunchChamber(entry);
      return;
    }
    if (entry.kind === "dir" || action === "open_dir") {
      if (entry.file_type?.type_id === "code_chamber" || entry.file_type?.facade) {
        await runLaunchChamber(entry);
        return;
      }
      await openPath(entry.path);
      return;
    }
    if (action === "launch_spv") {
      await launchSpv(entry.path);
      return;
    }
    if (action === "run_launchable" || entry.launchable) {
      await runLaunchable(entry.path);
      return;
    }
    if (action === "open_code") {
      navigateUrl(codeViewerUrl(entry.path));
      return;
    }
    openInTab(entry.path);
  }

  function hideCtx() {
    const menu = $("qf-ctx");
    if (menu) menu.hidden = true;
    state.ctxEntry = null;
    state.ctxBundle = null;
  }

  function hideProperties() {
    const flyout = $("qf-props-flyout");
    const body = $("qf-preview-body");
    if (flyout) flyout.hidden = true;
    if (body) body.hidden = false;
    state.propsEntry = null;
    state.propsBundle = null;
    state.propsSection = null;
  }

  async function fetchAlwaysBundle(path) {
    try {
      const out = await api({ action: "always_properties", path, inspect: true });
      if (out.ok) return out;
    } catch (_) {}
    return null;
  }

  async function alwaysCheckpoint(path, note) {
    const entry = findEntry(path) || { path, name: path.split("/").pop() };
    const out = await api({
      action: "always_checkpoint",
      path,
      note: note || `checkpoint · ${entry.name || path}`,
    });
    $("qf-status-right").textContent = out.ok
      ? `TimeShift checkpoint · ${out.id || out.checkpoint?.id || "saved"}`
      : out.error || "checkpoint failed";
    return out;
  }

  function formatPropValue(field) {
    if (field.format === "bytes" && field.value != null && field.value !== "—") {
      return fmtSize(field.value);
    }
    if (typeof field.value === "boolean") return field.value ? "Yes" : "No";
    return field.value == null || field.value === "" ? "—" : String(field.value);
  }

  function sectionFieldCount(sec) {
    const fields = (sec.fields || []).filter((f) => f.value != null && f.value !== "—" && f.value !== "").length;
    const tags = (sec.tags || []).length;
    const layers = (sec.layers || []).length;
    return fields + tags + layers;
  }

  function renderPropsSection(sec) {
    const pane = $("qf-props-pane");
    if (!pane || !sec) return;
    const fields = (sec.fields || [])
      .filter((f) => f.value != null && f.value !== "—" && f.value !== "")
      .map((f) => {
        const val = formatPropValue(f);
        const copyBtn = f.copy
          ? `<button type="button" class="qf-props-copy" data-copy="${esc(String(f.value))}" title="Copy">⧉</button>`
          : "";
        const link = f.link
          ? `<a class="qf-props-link" href="${esc(f.link)}" target="_blank" rel="noopener">open</a>`
          : "";
        return `<div class="qf-props-row${f.mono ? " mono" : ""}"><span class="qf-props-k">${esc(f.label)}</span><span class="qf-props-v">${esc(val)}${copyBtn}${link}</span></div>`;
      })
      .join("");
    const tags = (sec.tags || []).map((t) => `<span class="qf-always-tag">${esc(t)}</span>`).join("");
    const layers = (sec.layers || [])
      .map(
        (L) =>
          `<div class="qf-props-layer${L.ok ? " ok" : ""}"><span>${esc(L.label)}</span><small>${esc(L.detail || "")}</small></div>`,
      )
      .join("");
    pane.innerHTML = `<section class="qf-props-section">
      <h3>${esc(sec.title)}</h3>
      ${sec.banner ? `<p class="qf-props-banner">${esc(sec.banner)}</p>` : ""}
      ${tags ? `<div class="qf-always-tags">${tags}</div>` : ""}
      ${fields || '<p class="qf-props-empty">No fields in this section</p>'}
      ${layers ? `<div class="qf-props-layers">${layers}</div>` : ""}
    </section>`;
    pane.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => copyPath(btn.dataset.copy));
    });
  }

  function renderPropsMenu(bundle, activeId) {
    const menu = $("qf-props-menu");
    if (!menu || !bundle) return;
    menu.innerHTML = (bundle.sections || [])
      .map((sec) => {
        const n = sectionFieldCount(sec);
        const badge = n ? `<span class="qf-fly-badge">${n}</span>` : "";
        const active = sec.id === activeId ? " active" : "";
        return `<button type="button" class="qf-fly-menu-item${active}" data-section="${esc(sec.id)}">${esc(sec.title)}${badge}</button>`;
      })
      .join("");
    menu.querySelectorAll("[data-section]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.propsSection = btn.dataset.section;
        renderPropertiesFlyout(state.propsEntry, state.propsBundle, state.propsSection);
      });
    });
  }

  function renderPropsActions(entry, bundle) {
    const footer = $("qf-props-actions");
    if (!footer || !bundle) return;
    footer.innerHTML = (bundle.actions || [])
      .filter((a) => a.ui)
      .slice(0, 12)
      .map(
        (a) =>
          `<button type="button" class="qf-props-action" data-ui-action="${esc(a.ui)}">${esc(a.label)}</button>`,
      )
      .join("");
    footer.querySelectorAll("[data-ui-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        alwaysUiAction(btn.dataset.uiAction, entry, bundle);
      });
    });
  }

  function setFlyoutIcon(entry) {
    const flyIcon = $("qf-fly-icon");
    if (!flyIcon || !entry) return;
    if (global.QueenIconEngine?.iconUrl) {
      const bid = global.QueenIconEngine.fileBatteryId(entry);
      flyIcon.src = global.QueenIconEngine.iconUrl(bid, 32);
      flyIcon.className = `qf-fly-icon qie-file-icon qie-file-icon--${bid}`;
      flyIcon.hidden = false;
      return;
    }
    flyIcon.hidden = true;
  }

  function renderPropertiesFlyout(entry, bundle, sectionId) {
    const title = $("qf-props-title");
    const sub = $("qf-props-sub");
    if (!bundle) return;
    const sections = bundle.sections || [];
    const activeId = sectionId || sections[0]?.id;
    state.propsSection = activeId;
    if (title) title.textContent = bundle.name || entry?.name || "Properties";
    if (sub) sub.textContent = bundle.security?.posture || "Always Files · system secured";
    setFlyoutIcon(entry);
    renderPropsMenu(bundle, activeId);
    const sec = sections.find((s) => s.id === activeId) || sections[0];
    if (sec) renderPropsSection(sec);
    renderPropsActions(entry, bundle);
  }

  function renderPropertiesSheet(entry, bundle) {
    renderPropertiesFlyout(entry, bundle, state.propsSection);
  }

  async function showProperties(entry, bundle) {
    if (!entry) return;
    hideCtx();
    const flyout = $("qf-props-flyout");
    const body = $("qf-preview-body");
    if (!flyout) return;
    state.propsEntry = entry;
    if (body) body.hidden = true;
    flyout.hidden = false;
    $("qf-props-pane").innerHTML = '<div class="qf-props-loading">Loading Always Files…</div>';
    $("qf-props-menu").innerHTML = "";
    $("qf-props-actions").innerHTML = "";
    if (!bundle) {
      const out = await fetchAlwaysBundle(entry.path);
      bundle = out?.properties_menu;
      state.propsBundle = bundle;
      if (!bundle) {
        $("qf-props-pane").innerHTML = '<div class="qv-empty">Always Files unavailable</div>';
        return;
      }
    } else {
      state.propsBundle = bundle;
    }
    renderPropertiesFlyout(entry, bundle, state.propsSection);
  }

  async function alwaysUiAction(actionId, entry, bundle) {
    if (!entry) return;
    const af = bundle?.always_file || entry.always || {};
    switch (actionId) {
      case "open":
        await runDefaultAction(entry);
        break;
      case "preview":
        state.selected = entry.path;
        await showPreview(entry.path);
        setPreviewOpen(true);
        break;
      case "properties":
        await showProperties(entry, bundle);
        return;
      case "queen_code":
        navigateUrl(codeViewerUrl(entry.path));
        break;
      case "tab":
        openInTab(entry.path);
        break;
      case "hotbar":
        await addToHotbar(entry);
        break;
      case "copy_path":
        await copyPath(entry.path);
        break;
      case "copy_rel":
        await copyPath(af.rel_install || af.rel_sg || entry.always?.rel_install || "");
        break;
      case "copy_sha":
        await copyPath(entry.always?.sha256_full || af.sha256 || "");
        break;
      case "checkpoint":
        await alwaysCheckpoint(entry.path);
        break;
      case "rollback":
        $("qf-status-left").textContent = "TimeShift rollback — use Field panel /api/field-timeshift";
        break;
      default:
        break;
    }
    hideProperties();
  }

  function ctxActionItems(entry) {
    const action = entryAction(entry);
    const ft = entry.file_type;
    const isDir = entry.kind === "dir";
    const isChamber =
      action === "run_launch" ||
      entry.facade ||
      entry.kind === "launch_facade" ||
      ft?.type_id === "code_chamber" ||
      ft?.type_id === "launch";
    const items = [];

    if (isChamber) {
      const entryLabel = ft?.entry ? `Run · ${ft.entry}` : "Run chamber";
      const chamberRoot = entry.chamber_root || ft?.chamber_root || (entry.kind === "launch_facade" ? entry.chamber_root : null);
      items.push({ id: "run", label: entryLabel, action: () => runLaunchChamber(entry) });
      const insidePath = chamberRoot || (ft?.type_id === "launch" ? ft.chamber_root : null) || entry.path;
      items.push({
        id: "browse",
        label: "Browse inside",
        action: () => openPath(insidePath, { browseInside: true }),
      });
      if (isDir && !entry.facade) {
        items.push({
          id: "seal",
          label: "System refresh .launch",
          action: () => createLaunchFile(entry, true),
        });
      }
      if (entry.launch_meta?.locked || entry.file_type?.locked) {
        items.push({
          id: "locked",
          label: `System sealed · gen ${entry.launch_meta?.seal_generation ?? "—"} · no password`,
          action: () => {},
          disabled: true,
        });
      }
    } else {
      items.push({ id: "open", label: isDir ? "Open" : "Open", action: () => runDefaultAction(entry) });
    }

    if (!isDir && action === "open_code") {
      items.push({ id: "code", label: "Open in Queen Code", action: () => navigateUrl(codeViewerUrl(entry.path)) });
    }
    if (!isDir && bigDriveEligible(entry)) {
      items.push({
        id: "bigdrive",
        label: "Open in Big Drive",
        action: () => navigateUrl(bigDriveUrl(entry.path)),
      });
    }
    if (!isDir && action === "launch_spv") {
      items.push({ id: "launch", label: "Launch SPIR-V", action: () => launchSpv(entry.path) });
    }
    if (!isDir && (ft?.launchable || entry.launchable || ft?.action === "run_launchable")) {
      items.push({
        id: "runlb",
        label: `Run launchable · ${ft?.runtime || "exec"}`,
        action: () => runLaunchable(entry.path),
      });
    }
    if (!isDir && (ft?.compileable || entry.compileable)) {
      items.push({
        id: "compile",
        label: "Compile mode (release)",
        action: () => releaseCompileMode(entry),
      });
    }
    if (!isDir) {
      items.push({ id: "tab", label: "Open in tab", action: () => openInTab(entry.path) });
    }
    items.push({ id: "hotbar", label: "Add to wishlist", action: () => addToHotbar(entry) });
    if (isDir) {
      items.push({ id: "dock", label: "Dock folder", action: () => api({ action: "dock_push", path: entry.path }).then((o) => { if (o.ok) { state.dock = o.dock?.slots || []; renderDock(); } }) });
    }
    items.push({ id: "copy", label: "Copy path", action: () => copyPath(entry.path) });
    if (!isDir) {
      items.push({ id: "inspect", label: "Inspect", action: () => showInspect(entry) });
      items.push({ id: "icon", label: "Customize icon", action: () => customizeIcon(entry) });
    }
    return items;
  }

  function renderCtxMenu(menu, entry, items, bundle, x, y) {
    const ft = entry.file_type;
    const af = entry.always || {};
    const sec = bundle?.security || af.security || {};
    const knowsN = af.knows_count || (af.knows || []).length || 0;
    const hint = ft
      ? `${ft.label || ft.type_id} · ${Math.round((ft.confidence || 0) * 100)}%`
      : entry.name;
    const alwaysHead = knowsN
      ? `<div class="qf-ctx-always">
          <span class="qf-ctx-always-title">◈ Always Files</span>
          <span class="qf-ctx-always-sub">${esc(sec.posture || "System secures · no password")}</span>
        </div>`
      : "";
    const alwaysItems = [
      { id: "props", label: "Properties…", action: () => showProperties(entry, bundle), accent: true },
      { id: "cp", label: "TimeShift checkpoint", action: () => alwaysCheckpoint(entry.path) },
    ];
    if (bundle?.clickables?.length) {
      alwaysItems.push({
        id: "vfs",
        label: "Open VFS resolve",
        action: () => window.open(bundle.clickables[0].href, "_blank", "noopener"),
      });
    }
    const alwaysHtml = knowsN
      ? alwaysItems
          .map(
            (it) =>
              `<button type="button" class="qf-ctx-always-btn${it.accent ? " accent" : ""}" data-ctx="${esc(it.id)}">${esc(it.label)}</button>`,
          )
          .join("") + '<div class="sep"></div>'
      : "";
    const fileHtml = items
      .map(
        (it, i) =>
          (i === 2 && entry.kind !== "dir" ? '<div class="sep"></div>' : "") +
          `<button type="button" data-ctx="${esc(it.id)}"${it.disabled ? " disabled" : ""}>${esc(it.label)}</button>`,
      )
      .join("");
    menu.innerHTML = `<span class="hint">${esc(hint)}</span>${alwaysHead}${alwaysHtml}${fileHtml}`;
    const allItems = [...alwaysItems, ...items];
    menu.querySelectorAll("[data-ctx]").forEach((btn) => {
      const it = allItems.find((x) => x.id === btn.dataset.ctx);
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (it?.disabled) return;
        hideCtx();
        it?.action?.();
      });
    });
    menu.hidden = false;
    const rect = menu.getBoundingClientRect();
    const left = Math.min(x, window.innerWidth - rect.width - 8);
    const top = Math.min(y, window.innerHeight - rect.height - 8);
    menu.style.left = `${Math.max(4, left)}px`;
    menu.style.top = `${Math.max(4, top)}px`;
  }

  async function showCtx(x, y, entry) {
    const menu = $("qf-ctx");
    if (!menu || !entry) return;
    state.ctxEntry = entry;
    const items = ctxActionItems(entry);
    menu.innerHTML = '<span class="hint">Always Files…</span>';
    menu.hidden = false;
    menu.style.left = `${Math.max(4, x)}px`;
    menu.style.top = `${Math.max(4, y)}px`;
    const out = await fetchAlwaysBundle(entry.path);
    state.ctxBundle = out?.properties_menu || null;
    renderCtxMenu(menu, entry, items, state.ctxBundle, x, y);
  }

  async function copyPath(path) {
    try {
      await navigator.clipboard.writeText(path);
      $("qf-status-right").textContent = "Path copied";
    } catch (_) {
      $("qf-status-right").textContent = path;
    }
  }

  async function showInspect(entry) {
    const out = await api({ action: "inspect", path: entry.path });
    const ft = out.inspect || entry.file_type;
    const hints = (ft?.hints || []).join(", ");
    $("qf-status-left").textContent = `${ft?.label || "unknown"} · ${ft?.type_id || "?"} · ${hints || "no hints"}`;
    $("qf-status-right").textContent = `action: ${ft?.action || "?"} · icon: ${ft?.icon || "?"}`;
  }

  async function customizeIcon(entry) {
    const ft = entry.file_type || {};
    const current = resolveIcon(entry);
    const next = window.prompt(
      `Icon for ${entry.name}\n(program icon — global stays ${ft.global_icon || "📄"})`,
      current,
    );
    if (next === null) return;
    const scope = window.confirm("Apply to all files of this type?\nCancel = this file only.") ? "type" : "path";
    const body =
      scope === "path"
        ? { action: "icon_save", scope: "path", path: entry.path, icon: next.trim() || null }
        : { action: "icon_save", scope: "type", key: ft.type_id || entry.ext, icon: next.trim() || null };
    const out = await api(body);
    if (out.ok) {
      state.iconOverrides = out.overrides;
      await openPath(state.path);
      $("qf-status-right").textContent = scope === "path" ? "Icon saved for file" : "Icon saved for type";
    }
  }

  function jumpToSearchMatch(q) {
    const box = $("qf-rows");
    if (!box || !q) return;
    const needle = q.trim().toLowerCase();
    if (!needle) return;
    let first = null;
    box.querySelectorAll(".qf-row").forEach((row) => {
      const name = (row.querySelector(".name span")?.textContent || "").toLowerCase();
      const match = name.includes(needle);
      row.classList.toggle("match", match);
      row.classList.toggle("hidden-by-search", !match);
      if (match && !first) first = row;
    });
    if (first) {
      first.scrollIntoView({ block: "nearest", behavior: "smooth" });
      const path = first.dataset.path;
      if (path) {
        state.selected = path;
        box.querySelectorAll(".qf-row").forEach((r) => r.classList.toggle("selected", r.dataset.path === path));
        showPreview(path);
      }
    }
  }

  function renderRows(entries) {
    const box = $("qf-rows");
    if (!box) return;
    let rows = entries || [];
    if (state.launchablesOnly) {
      rows = rows.filter((e) => e.launchable || e.file_type?.launchable || e.action === "run_launchable" || e.file_type?.action === "run_launchable");
    }
    if (state.typeFilter) {
      rows = rows.filter((e) => (e.file_type?.type_id || e.ext?.replace(".", "")) === state.typeFilter);
    }
    state.entries = rows;
    if (!rows?.length) {
      box.innerHTML = '<div class="qf-empty">Empty folder</div>';
      return;
    }
    const sorted = sortEntries(rows);
    const q = (state.searchQ || "").trim().toLowerCase();
    box.innerHTML = sorted
      .map(
        (e) => {
          const match = q && (e.name || "").toLowerCase().includes(q);
          const hide = q && !match;
          return `
      <div class="qf-row${state.selected === e.path ? " selected" : ""}${match ? " match" : ""}${hide ? " hidden-by-search" : ""}" data-path="${esc(e.path)}" data-kind="${esc(e.kind)}" data-action="${esc(entryAction(e))}">
        <div class="name">${iconHtml(resolveIcon(e), e)}<span>${esc(e.name)}</span>${alwaysKnowsBadge(e)}</div>
        <div class="meta">${alwaysMeta(e) || launchMeta(e)}</div>
        <div class="meta">${fmtTime(e.mtime)}</div>
      </div>`;
        },
      )
      .join("");
    box.querySelectorAll(".qf-row").forEach((row) => {
      const path = row.dataset.path;
      row.addEventListener("click", () => {
        state.selected = path;
        box.querySelectorAll(".qf-row").forEach((r) => r.classList.toggle("selected", r.dataset.path === state.selected));
        showPreview(path);
      });
      row.addEventListener("dblclick", () => {
        const entry = findEntry(path);
        runDefaultAction(entry || { path, kind: row.dataset.kind });
      });
      row.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const entry = findEntry(path);
        if (entry) showCtx(e.clientX, e.clientY, entry);
      });
      row.setAttribute("draggable", "true");
      row.addEventListener("dragstart", (ev) => {
        const entry = findEntry(path);
        ev.dataTransfer?.setData(
          "application/x-queen-file",
          JSON.stringify({
            path,
            name: entry?.name || row.querySelector(".name span:last-child")?.textContent,
            kind: row.dataset.kind,
          }),
        );
      });
    });
    if (q) jumpToSearchMatch(q);
    const hotbar = $("qf-hotbar");
    hotbar?.addEventListener("dragover", (e) => {
      if (e.dataTransfer?.types?.includes("application/x-queen-file")) {
        e.preventDefault();
      }
    });
    hotbar?.addEventListener("drop", async (e) => {
      e.preventDefault();
      try {
        const raw = e.dataTransfer?.getData("application/x-queen-file");
        if (!raw) return;
        const entry = JSON.parse(raw);
        await addToHotbar({
          path: entry.path,
          name: entry.name,
          kind: entry.kind === "dir" ? "dir" : "file",
        });
      } catch (_) {
        /* ignore */
      }
    });
  }

  function renderFolderMenu() {
    const menu = $("qf-folder-menu");
    if (!menu) return;
    menu.innerHTML = (state.roots || [])
      .map(
        (r) => `
      <li role="none">
        <button type="button" role="menuitem" data-root="${esc(r.path)}">
          ${esc(r.label)}
          <small>${esc(r.path)}</small>
        </button>
      </li>`,
      )
      .join("");
    menu.querySelectorAll("[data-root]").forEach((btn) => {
      btn.addEventListener("click", () => {
        openPath(btn.dataset.root);
        menu.hidden = true;
        $("qf-folder-menu-btn")?.setAttribute("aria-expanded", "false");
      });
    });
  }

  async function openPath(path, opts = {}) {
    if (!opts.skipNavPush) {
      const navOut = await api({ action: "nav_push", path });
      if (navOut.ok && navOut.nav) state.nav = navOut.nav;
      updateNavButtons();
    }
    const out = await api({
      action: "list",
      path,
      show_hidden: state.showHidden,
      browse_inside: Boolean(opts.browseInside),
    });
    if (!out.ok) {
      $("qf-status-left").textContent = `Blocked: ${out.error || "jail_denied"}`;
      return;
    }
    state.path = out.path;
    state.launchables = out.launchables || [];
    renderCrumbs(state.path);
    renderMobilePickers();
    renderLaunchablesPanel(state.launchables);
    renderRows(out.entries);
    const facadeNote = out.facade ? " · sealed .launch facade" : "";
    const launchNote = out.launchable_count ? ` · ${out.launchable_count} launchables` : "";
    $("qf-status-left").textContent = `${out.entries?.length || 0} items · ${out.relative || out.path}${facadeNote}${launchNote}`;
    if (out.message && out.facade) $("qf-status-right").textContent = out.message;
    else if (out.truncated) $("qf-status-right").textContent = `List capped at ${out.entries?.length}`;
    else $("qf-status-right").textContent = out.capped ? "Capped" : "Unlimited list · jail active";
    const treeOut = await api({ action: "tree", path: state.path, depth: 2 });
    if (treeOut.ok) renderTree(treeOut.tree, $("qf-tree"));
  }

  function bindDivider() {
    const split = $("qf-split");
    const div = $("qf-divider");
    if (!split || !div) return;
    let dragging = false;
    div.addEventListener("mousedown", () => {
      dragging = true;
    });
    window.addEventListener("mouseup", () => {
      dragging = false;
    });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const rect = split.getBoundingClientRect();
      const pct = Math.min(48, Math.max(16, ((e.clientX - rect.left) / rect.width) * 100));
      split.style.gridTemplateColumns = `${pct}% 5px 1fr`;
    });
  }

  async function runSearch(deep) {
    const q = ($("qf-search")?.value || "").trim();
    state.searchQ = q;
    if (!q) {
      state.searchMode = "local";
      await openPath(state.path);
      return;
    }
    if (!deep && state.entries.length) {
      renderRows(state.entries);
      $("qf-status-left").textContent = `Filtering ${state.entries.length} items · “${q}”`;
      return;
    }
    const out = await api({ action: "search", path: state.path, query: q });
    if (!out.ok) {
      $("qf-status-left").textContent = `Search blocked: ${out.error || "failed"}`;
      return;
    }
    state.searchMode = "deep";
    state.launchables = [];
    renderLaunchablesPanel([]);
    renderRows(out.hits || []);
    $("qf-status-left").textContent = `${out.count || 0} hits for “${q}” under ${out.path}`;
    $("qf-status-right").textContent = out.truncated ? "Search capped" : "Deep search · jail active";
  }

  function onSearchInput() {
    const el = $("qf-search");
    const q = (el?.value || "").trim();
    state.searchQ = q;
    clearTimeout(state.searchTimer);
    if (!q) {
      state.searchMode = "local";
      openPath(state.path);
      return;
    }
    if (state.entries.length) {
      renderRows(state.entries);
      $("qf-status-left").textContent = `Instant · “${q}”`;
    }
    state.searchTimer = setTimeout(() => {
      if (q.length >= 2) runSearch(true);
    }, 320);
  }

  function typeIcon(t) {
    return t?.global_icon || t?.program_icon || "📄";
  }

  function renderTypeBar() {
    const bar = $("qf-type-bar");
    const types = state.fileTypes?.types || {};
    const pins = state.fileTypes?.type_prefs?.bar_pins || [];
    if (!bar) return;
    if (!pins.length) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    bar.innerHTML = pins
      .map((tid) => {
        const t = types[tid];
        if (!t) return "";
        const active = state.typeFilter === tid;
        return `<button type="button" class="qf-type-chip${active ? " active" : ""}" data-type="${esc(tid)}" title="${esc(t.label)}"><span class="ico">${typeIcon(t)}</span>${esc(t.label)}</button>`;
      })
      .join("");
    bar.querySelectorAll(".qf-type-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.typeFilter = state.typeFilter === btn.dataset.type ? null : btn.dataset.type;
        renderTypeBar();
        renderRows(state.entries);
      });
    });
  }

  function renderTypesDrawer() {
    const body = $("qf-types-body");
    if (!body) return;
    const types = state.fileTypes?.types || {};
    const q = (state.typesSearch || "").trim().toLowerCase();
    const rows = Object.entries(types).filter(([tid, t]) => {
      if (!q) return true;
      const hay = `${tid} ${t.label || ""} ${(t.extensions || []).join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
    body.innerHTML = rows
      .map(([tid, t]) => {
        const flags = t.flags || {};
        const exts = (t.extensions || []).slice(0, 6).join(", ");
        return (
          `<details class="qf-type-row" data-type="${esc(tid)}">` +
          `<summary><span class="ico">${typeIcon(t)}</span><strong>${esc(t.label || tid)}</strong>` +
          `<span class="qf-lib-meta">${esc(exts || "—")}</span></summary>` +
          `<div class="qf-type-detail">` +
          `<div><code>${esc(tid)}</code> · action <code>${esc(t.settings?.action || t.action || "?")}</code> · open <code>${esc(t.settings?.open_with || t.open_with || "—")}</code></div>` +
          `<div class="qf-type-flags">` +
          `<button type="button" class="qf-flag${flags.compileable ? " on" : ""}" data-flag="compileable" data-type="${esc(tid)}">Compile</button>` +
          `<button type="button" class="qf-flag${flags.launchable ? " on" : ""}" data-flag="launchable" data-type="${esc(tid)}" disabled>Launch</button>` +
          `<button type="button" class="qf-flag${flags.on_bar ? " on" : ""}" data-flag="on_bar" data-type="${esc(tid)}">On bar</button>` +
          `<button type="button" class="qf-flag${flags.preview !== false ? " on" : ""}" data-flag="preview" data-type="${esc(tid)}">Preview</button>` +
          `</div></div></details>`
        );
      })
      .join("");
    body.querySelectorAll(".qf-flag[data-flag='on_bar']").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const out = await api({ action: "toggle_type_flag", type_id: btn.dataset.type, key: "on_bar", toggle: true });
        if (out.ok) {
          state.fileTypes = out;
          renderTypeBar();
          renderTypesDrawer();
        }
      });
    });
    body.querySelectorAll(".qf-flag[data-flag='compileable']").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const out = await api({ action: "toggle_type_flag", type_id: btn.dataset.type, key: "compileable", toggle: true });
        if (out.ok) {
          state.fileTypes = out;
          renderTypesDrawer();
        }
      });
    });
    body.querySelectorAll(".qf-flag[data-flag='preview']").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const tid = btn.dataset.type;
        const cur = (state.fileTypes?.types || {})[tid]?.flags?.preview !== false;
        const out = await api({ action: "set_type_pref", type_id: tid, key: "preview", value: !cur });
        if (out.ok) {
          state.fileTypes = out;
          renderTypesDrawer();
        }
      });
    });
  }

  function renderLibraryFacets(facets) {
    const wrap = $("qf-library-facets");
    if (!wrap) return;
    const f = facets || state.library?.facets || {};
    const chips = [];
    const active = state.libraryFacet || {};
    chips.push(
      `<button type="button" class="qf-lib-chip${!active.kind && !active.dewey && !active.platform ? " on" : ""}" data-facet="clear">All</button>`
    );
    for (const row of (f.kinds || []).slice(0, 8)) {
      const on = active.kind === row.id ? " on" : "";
      chips.push(
        `<button type="button" class="qf-lib-chip${on}" data-facet-kind="${esc(row.id)}">${esc(row.id)} (${row.count})</button>`
      );
    }
    for (const row of (f.dewey || []).slice(0, 6)) {
      const on = active.dewey === row.code ? " on" : "";
      chips.push(
        `<button type="button" class="qf-lib-chip qf-lib-chip--dewey${on}" data-facet-dewey="${esc(row.code)}" title="${esc(row.label)}">${esc(row.code)} · ${esc(row.label)} (${row.count})</button>`
      );
    }
    wrap.innerHTML = chips.join("");
    wrap.querySelectorAll("[data-facet]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.libraryFacet = { kind: "", dewey: "", platform: "" };
        renderLibraryFacets(f);
        searchLibrary(state.librarySearch);
      });
    });
    wrap.querySelectorAll("[data-facet-kind]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.facetKind || "";
        state.libraryFacet.kind = state.libraryFacet.kind === id ? "" : id;
        renderLibraryFacets(f);
        searchLibrary(state.librarySearch);
      });
    });
    wrap.querySelectorAll("[data-facet-dewey]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const code = btn.dataset.facetDewey || "";
        state.libraryFacet.dewey = state.libraryFacet.dewey === code ? "" : code;
        renderLibraryFacets(f);
        searchLibrary(state.librarySearch);
      });
    });
  }

  function libraryCoverUrl(p) {
    return p.cover_url || p.box_art_url || p.cover || p.icon_url || global.QueenIconEngine?.libraryIconUrl?.(p.id) || "";
  }

  function renderLibraryDrawer(items, meta) {
    const body = $("qf-library-body");
    if (!body) return;
    if (state.libraryTab === "nes") {
      body.innerHTML = '<p class="qf-empty">Loading NES cartridge theater…</p>';
      global.QueenNesTheater?.loadCatalog?.(48).then((out) => {
        if (out?.ok) global.QueenNesTheater?.render?.(body, out.entries);
        else body.innerHTML = '<p class="qf-empty">NES catalog not built — run field-nes-cartridge-forge build.</p>';
      });
      return;
    }
    const list = items || state.library?.programs || [];
    const policy = state.library?.policy || {};
    if (!list.length) {
      body.innerHTML =
        '<p class="qf-empty">Library empty — Scan builds the Dewey-classified icon index (zero disk copy).</p>';
      return;
    }
    const policyNote = policy.icon_cache === false ? " · zero-copy · Dewey" : "";
    const scoreNote = meta?.search_engine ? ` · ${meta.search_engine}` : "";
    $("qf-status-right").textContent = `Library · ${meta?.count ?? list.length} shown · ${state.library?.count || 0} total${policyNote}${scoreNote}`;
    body.innerHTML = list
      .map((p) => {
        const ai = p.ai || {};
        const cmd = ai.command || p.exec || p.command || "";
        const cover = libraryCoverUrl(p);
        const thumb = cover || "";
        const dewey = p.dewey ? `${p.dewey}${p.dewey_label ? ` · ${p.dewey_label}` : ""}` : "";
        const score = p.score != null && p.score > 0 ? `<span class="qf-lib-score">${p.score}</span>` : "";
        const lic = p.license_label ? `<br><span class="qf-lib-lic">${esc(p.license_label)}</span>` : "";
        return (
          `<div class="qf-lib-row${cover ? " qf-lib-row--cover" : ""}" data-queen-ai-operate="${esc(ai.operate || "open")}"` +
          ` data-queen-ai-command="${esc(cmd)}" data-queen-ai-name="${esc(p.name || "")}"` +
          ` data-queen-icon-ref="${esc(p.id || "")}">` +
          (thumb
            ? `<div class="qf-lib-cover"><img class="qz-zoomable" src="${esc(thumb)}" alt="${esc(p.name || "")}" loading="lazy" decoding="async" /></div>`
            : `<span class="ico">📦</span>`) +
          `<div><strong>${esc(p.name)}</strong>${score}` +
          `<code>${esc(cmd)}</code>` +
          `<div class="qf-lib-meta">` +
          `${esc(p.kind || ai.kind || "")} · ${esc(p.source || "")} · ${esc(p.serve_mode || "")}` +
          (dewey ? `<br><span class="qf-lib-dewey">${esc(dewey)}</span>` : "") +
          (p.genre ? `<br>Genre: ${esc(p.genre)}` : "") +
          (p.console_id ? `<br>Platform: ${esc(p.console_id)}` : "") +
          (p.year ? `<br>Year: ${esc(p.year)}` : "") +
          lic +
          (p.has_rom ? `<br><span class="qf-lib-rom">.nes ROM in library</span>` : "") +
          (ai.description ? `<br>${esc(ai.description)}` : "") +
          `</div></div></div>`
        );
      })
      .join("");
    global.QueenAiSurface?.enrichFromLibrary?.();
    global.QueenZoomLightbox?.bind?.(body);
  }

  async function switchLibraryTab(tab) {
    state.libraryTab = tab || "programs";
    document.querySelectorAll(".qf-lib-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.libTab === state.libraryTab);
    });
    const facets = $("qf-library-facets");
    if (facets) facets.hidden = state.libraryTab === "nes";
    if (state.libraryTab === "nes") {
      renderLibraryDrawer([], state.library);
      return;
    }
    if (state.libraryTab === "games") {
      const out = await api({
        action: "library_search",
        query: state.librarySearch || "",
        kind: "video_game",
        limit: 120,
      });
      if (out.ok) renderLibraryDrawer(out.hits, out);
      return;
    }
    const seed = state.library?.programs?.length
      ? state.library.programs
      : Object.values(state.library?.entries || {});
    renderLibraryDrawer(seed.slice(0, 120), state.library);
  }

  async function refreshFileTypes() {
    const out = await api({ action: "file_types" });
    if (out.ok) {
      state.fileTypes = out;
      renderTypeBar();
      if (!$("qf-types-drawer")?.hidden) renderTypesDrawer();
    }
  }

  async function loadLibrary(scan) {
    const out = await api({ action: scan ? "library_scan" : "program_library" });
    if (out.ok) {
      state.library = out;
      await global.QueenIconEngine?.loadLibraryIndex?.(true);
      renderLibraryFacets(out.facets);
      const seed = out.programs?.length ? out.programs : Object.values(out.entries || {});
      renderLibraryDrawer(seed.slice(0, 120), out);
      $("qf-status-left").textContent =
        `Library v3 · ${out.count || 0} entries · ${out.games_count || 0} games · ${out.dewey_books || 0} Dewey · ${out.icons_resolved || 0} icons`;
    }
  }

  async function searchLibrary(q) {
    const facet = state.libraryFacet || {};
    const hasFilter = !!(q || facet.kind || facet.dewey || facet.platform);
    if (!hasFilter) {
      const seed = state.library?.programs?.length
        ? state.library.programs
        : Object.values(state.library?.entries || {});
      renderLibraryDrawer(seed.slice(0, 120), state.library);
      return;
    }
    const out = await api({
      action: "library_search",
      query: q,
      kind: facet.kind || "",
      dewey: facet.dewey || "",
      platform: facet.platform || "",
      limit: 120,
    });
    if (out.ok) {
      if (out.facets) renderLibraryFacets(out.facets);
      renderLibraryDrawer(out.hits, out);
    }
  }

  function toggleDrawer(id, on) {
    const el = $(id);
    if (!el) return;
    const open = on !== undefined ? on : el.hidden;
    el.hidden = !open;
    document.querySelectorAll(".qf-drawer").forEach((d) => {
      if (d.id !== id) d.hidden = true;
    });
    if (open && id === "qf-types-drawer") renderTypesDrawer();
    if (open && id === "qf-library-drawer" && !state.library) loadLibrary(false);
  }

  async function mkdirHere() {
    const name = window.prompt("New folder name");
    if (!name || !name.trim()) return;
    const out = await api({ action: "mkdir", path: state.path, name: name.trim() });
    const status = $("qf-status-right");
    if (out.ok) {
      if (status) status.textContent = `Created ${out.path}`;
      await openPath(state.path);
    } else if (status) {
      status.textContent = out.error || "mkdir failed";
    }
  }

  function bindChrome() {
    $("qf-folder-menu-btn")?.addEventListener("click", () => {
      const menu = $("qf-folder-menu");
      const open = menu?.hidden !== false;
      if (menu) menu.hidden = !open;
      $("qf-folder-menu-btn")?.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $("qf-back")?.addEventListener("click", () => navBack());
    $("qf-forward")?.addEventListener("click", () => navForward());
    $("qf-dock-pin")?.addEventListener("click", () => dockCurrent());
    $("qf-mobile-root")?.addEventListener("change", (e) => openPath(e.target.value));
    $("qf-mobile-jump")?.addEventListener("change", (e) => openPath(e.target.value));
    $("qf-launch-filter")?.addEventListener("click", () => {
      state.launchablesOnly = !state.launchablesOnly;
      $("qf-launch-filter").classList.toggle("active", state.launchablesOnly);
      renderRows(state.entries);
    });
    $("qf-sort")?.addEventListener("change", (e) => {
      state.sortMode = e.target.value;
      renderRows(state.entries);
    });
    $("qf-preview-toggle")?.addEventListener("click", () => {
      setPreviewOpen(!state.previewOn);
      if (state.previewOn && state.selected) showPreview(state.selected);
    });
    $("qf-preview-close")?.addEventListener("click", () => setPreviewOpen(false));
    $("qf-preview-code")?.addEventListener("click", () => {
      if (state.previewPath) navigateUrl(codeViewerUrl(state.previewPath));
    });
    $("qf-preview-props")?.addEventListener("click", () => {
      if (state.selected) {
        const entry = findEntry(state.selected);
        if (entry) showProperties(entry);
      }
    });
    $("qf-props-close")?.addEventListener("click", hideProperties);
    $("qf-up")?.addEventListener("click", async () => {
      const out = await api({ action: "list", path: state.path });
      if (out.parent) openPath(out.parent);
    });
    $("qf-refresh")?.addEventListener("click", () => openPath(state.path));
    $("qf-search")?.addEventListener("input", onSearchInput);
    $("qf-search")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runSearch(true);
      }
      if (e.key === "Escape") {
        e.target.value = "";
        state.searchQ = "";
        state.searchMode = "local";
        openPath(state.path);
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const rows = [...document.querySelectorAll(".qf-row:not(.hidden-by-search)")];
        if (!rows.length) return;
        const cur = rows.findIndex((r) => r.classList.contains("selected"));
        const next = e.key === "ArrowDown"
          ? rows[Math.min(cur + 1, rows.length - 1)]
          : rows[Math.max(cur - 1, 0)];
        if (next) {
          state.selected = next.dataset.path;
          rows.forEach((r) => r.classList.toggle("selected", r === next));
          next.scrollIntoView({ block: "nearest", behavior: "smooth" });
          showPreview(state.selected);
        }
      }
    });
    $("qf-mkdir")?.addEventListener("click", () => mkdirHere());
    $("qf-hidden")?.addEventListener("click", (e) => {
      state.showHidden = !state.showHidden;
      e.target.textContent = state.showHidden ? "Hide hidden" : "Show hidden";
      openPath(state.path);
    });
    $("qf-add-hot")?.addEventListener("click", async () => {
      if (!state.selected) return;
      const out = await api({ action: "stat", path: state.selected });
      if (out.ok) await addToHotbar(out.entry);
    });
    $("qf-open-tab")?.addEventListener("click", () => {
      if (state.selected) {
        const entry = findEntry(state.selected);
        runDefaultAction(entry || { path: state.selected, kind: "file" });
      }
    });
    $("qf-shell")?.addEventListener("click", () => toggleTerminalDrawer());
    $("qf-types-btn")?.addEventListener("click", () => toggleDrawer("qf-types-drawer"));
    $("qf-types-close")?.addEventListener("click", () => toggleDrawer("qf-types-drawer", false));
    $("qf-library-btn")?.addEventListener("click", () => toggleDrawer("qf-library-drawer"));
    $("qf-library-close")?.addEventListener("click", () => toggleDrawer("qf-library-drawer", false));
    $("qf-library-scan")?.addEventListener("click", () => loadLibrary(true));
    document.querySelectorAll(".qf-lib-tab").forEach((btn) => {
      btn.addEventListener("click", () => switchLibraryTab(btn.dataset.libTab || "programs"));
    });
    $("qf-types-search")?.addEventListener("input", (e) => {
      state.typesSearch = e.target.value;
      renderTypesDrawer();
    });
    let libTimer = null;
    $("qf-library-search")?.addEventListener("input", (e) => {
      state.librarySearch = e.target.value;
      clearTimeout(libTimer);
      libTimer = setTimeout(() => searchLibrary(state.librarySearch), 280);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".qf-folder-menu")) {
        $("qf-folder-menu").hidden = true;
        $("qf-folder-menu-btn")?.setAttribute("aria-expanded", "false");
      }
      if (!e.target.closest(".qf-ctx")) hideCtx();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        hideProperties();
        hideCtx();
        toggleDrawer("qf-types-drawer", false);
        toggleDrawer("qf-library-drawer", false);
      }
    });
    window.addEventListener("scroll", hideCtx, true);
  }

  function terminalEmbedUrl() {
    const cwd = state.path || "";
    const q = new URLSearchParams({ layout: "tabs", miniview: "1", mini: "0" });
    if (cwd) q.set("cwd", cwd);
    return `/world/queen-gnu-terminal-embed.html?${q}`;
  }

  function toggleTerminalDrawer(force) {
    const drawer = $("qf-terminal-drawer");
    const frame = $("qf-terminal-frame");
    const btn = $("qf-shell");
    if (!drawer || !frame) return;
    const open = force === true ? true : force === false ? false : drawer.hidden;
    drawer.hidden = !open;
    btn?.classList.toggle("active", open);
    if (open && !frame.src) frame.src = terminalEmbedUrl();
    else if (open) frame.src = terminalEmbedUrl();
  }

  async function init() {
    bindDivider();
    bindChrome();
    const st = await api({ action: "status" });
    if (!st.ok && st.schema !== "queen-file-browser/v1") {
      $("qf-status-left").textContent = "File browser API offline";
      return;
    }
    state.roots = st.roots || [];
    state.hotbar = st.hotbar?.slots || [];
    state.dock = st.dock?.slots || [];
    state.nav = st.nav || { stack: [], index: -1 };
    state.fileTypes = st.file_types;
    state.iconOverrides = st.file_types?.icon_overrides;
    renderTypeBar();
    loadLibrary(false).catch(() => {});
    const ps = st.power_sort || {};
    if (ps.always_best_sort && ps.mode) {
      state.sortMode = ps.mode;
      const sortEl = $("qf-sort");
      if (sortEl) sortEl.value = ps.mode;
    }
    renderZeroCost(st);
    renderFolderMenu();
    renderHotbar();
    renderDock();
    updateNavButtons();
    renderMobilePickers();
    const navPath = state.nav?.stack?.[state.nav?.index ?? -1];
    const kilroyRoot = (state.roots || []).find((r) => r.id === "kilroy");
    const start =
      navPath || kilroyRoot?.path || state.hotbar[0]?.path || state.dock[0]?.path || state.roots[0]?.path || "";
    setPreviewOpen(true);
    if (start) await openPath(start, { skipNavPush: Boolean(navPath) });
  }

  init();
})();