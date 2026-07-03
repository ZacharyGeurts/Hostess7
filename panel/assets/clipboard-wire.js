/**
 * NEXUS Clipboard Wire — hardware-secured copy/paste · Ctrl+Alt+Space scheme flyout.
 * AmmoOS sovereign clipboard: scheme persists in vault state across every page.
 */
(function () {
  "use strict";

  const OWNER = "nexus-clipboard-wire";
  const LS_SCHEME = "nexus-clipboard-scheme";
  const LS_HISTORY = "nexus-clipboard-scheme-history";
  const LS_MEDIA = "nexus-clipboard-media-active";
  const WIRE_SEL =
    "[data-clipboard-wire], [data-hardware-wire], [data-smart-wire], [data-front-hook], [data-admin-shield], [data-queen-surface=\"browser\"], [data-nexus-clipboard-sovereign], .qw-browser-shell, .fm-shell";
  const API = "/api/field-clipboard";
  const FLYOUT_CHORD = "Control+Alt+Space";

  const state = {
    owner: OWNER,
    boarded: false,
    sovereign: false,
    scheme: "standard",
    schemeLabel: "AmmoOS field standard",
    schemeHistory: [],
    schemes: [],
    bindings: [],
    flyoutChord: FLYOUT_CHORD,
    flyoutOpen: false,
    flyoutPos: { x: 0, y: 0 },
    chordsHandled: 0,
    blockedUntrusted: 0,
    vaultOps: 0,
    ghostMode: true,
    historicCount: 0,
    mediaCount: 0,
    mediaActiveId: null,
    historyCursor: 0,
  };

  let flyoutEl = null;

  function isSovereignSurface() {
    const root = document.documentElement;
    const body = document.body;
    return !!(
      (root && root.getAttribute("data-nexus-clipboard-sovereign") === "1") ||
      (body && body.hasAttribute("data-clipboard-wire")) ||
      (root && root.hasAttribute("data-clipboard-wire")) ||
      (root && root.getAttribute("data-front-hook")) ||
      (body && body.getAttribute("data-front-hook"))
    );
  }

  function onWireSurface(target) {
    if (state.sovereign) return true;
    return !!(target && target.closest && target.closest(WIRE_SEL));
  }

  function parseChord(chord) {
    const parts = String(chord || "")
      .toLowerCase()
      .split("+")
      .map((s) => s.trim())
      .filter(Boolean);
    const mods = new Set();
    let key = "";
    parts.forEach((p) => {
      if (p === "ctrl" || p === "control") mods.add("control");
      else if (p === "shift") mods.add("shift");
      else if (p === "alt" || p === "openapple") mods.add("alt");
      else if (p === "meta" || p === "super" || p === "solidapple") mods.add("meta");
      else key = p;
    });
    return { mods, key };
  }

  function eventMods(ev) {
    const mods = new Set();
    if (ev.ctrlKey) mods.add("control");
    if (ev.shiftKey) mods.add("shift");
    if (ev.altKey) mods.add("alt");
    if (ev.metaKey) mods.add("meta");
    return mods;
  }

  function eventKeyName(ev) {
    const k = (ev.key || "").toLowerCase();
    if (k === " " || k === "spacebar") return "space";
    if (k === "insert") return "insert";
    if (k === "delete") return "delete";
    if (k.length === 1) return k;
    return k;
  }

  function modsEqual(a, b) {
    if (a.size !== b.size) return false;
    for (const x of a) if (!b.has(x)) return false;
    return true;
  }

  function matchBinding(ev, binding) {
    const parsed = binding.parsed || parseChord(binding.chord);
    const em = eventMods(ev);
    const key = eventKeyName(ev);
    if (key !== parsed.key) return false;
    return modsEqual(em, parsed.mods);
  }

  function isFlyoutChord(ev) {
    return matchBinding(ev, { parsed: parseChord(state.flyoutChord || FLYOUT_CHORD) });
  }

  function lsGet(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function lsSet(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (_) {}
  }

  function persistSchemeLocal(scheme, history) {
    if (scheme) lsSet(LS_SCHEME, { scheme, at: Date.now() });
    if (history) lsSet(LS_HISTORY, { history, at: Date.now() });
  }

  function selectionText() {
    const sel = window.getSelection && window.getSelection();
    if (sel && String(sel).trim()) return String(sel);
    const el = document.activeElement;
    if (el && (el.tagName === "TEXTAREA" || el.tagName === "INPUT")) {
      const start = el.selectionStart;
      const end = el.selectionEnd;
      if (start != null && end != null && end > start) {
        return el.value.slice(start, end);
      }
      return el.value || "";
    }
    return "";
  }

  function insertText(text) {
    const el = document.activeElement;
    if (el && (el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && el.type !== "password"))) {
      const start = el.selectionStart != null ? el.selectionStart : el.value.length;
      const end = el.selectionEnd != null ? el.selectionEnd : el.value.length;
      const before = el.value.slice(0, start);
      const after = el.value.slice(end);
      el.value = before + text + after;
      const pos = start + text.length;
      el.selectionStart = el.selectionEnd = pos;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      return true;
    }
    const sel = window.getSelection && window.getSelection();
    if (sel && sel.rangeCount) {
      const range = sel.getRangeAt(0);
      range.deleteContents();
      range.insertNode(document.createTextNode(text));
      return true;
    }
    return false;
  }

  function cutSelection() {
    const text = selectionText();
    if (!text) return "";
    const el = document.activeElement;
    if (el && (el.tagName === "TEXTAREA" || el.tagName === "INPUT")) {
      const start = el.selectionStart;
      const end = el.selectionEnd;
      if (start != null && end != null && end > start) {
        const slice = el.value.slice(start, end);
        el.value = el.value.slice(0, start) + el.value.slice(end);
        el.selectionStart = el.selectionEnd = start;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        return slice;
      }
    }
    document.execCommand("delete");
    return text;
  }

  function vaultAction(action, text, extra) {
    state.vaultOps += 1;
    const body = Object.assign({ action, text: text || "" }, extra || {});
    return fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    })
      .then((r) => r.json())
      .catch(() => ({ ok: false, error: "vault_unreachable" }));
  }

  function dispatchClipboard(body) {
    state.vaultOps += 1;
    return fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      credentials: "same-origin",
    })
      .then((r) => r.json())
      .catch(() => ({ ok: false, error: "vault_unreachable" }));
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  function dataUrlToBlob(dataUrl) {
    const parts = String(dataUrl).split(",");
    const mime = (parts[0].match(/data:([^;]+)/) || [])[1] || "application/octet-stream";
    const b64 = parts[1] || "";
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new Blob([arr], { type: mime });
  }

  function mediaTargetFromEvent(ev) {
    const t = (ev && ev.target) || document.activeElement;
    if (!t || !t.closest) return null;
    const img = t.closest("img");
    if (img && img.src) return img;
    const video = t.closest("video");
    if (video) return video;
    const canvas = t.closest("canvas");
    if (canvas) return canvas;
    if (t.tagName === "IMG" || t.tagName === "VIDEO" || t.tagName === "CANVAS") return t;
    const sel = window.getSelection && window.getSelection();
    if (sel && sel.anchorNode) {
      const node = sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement;
      const hit = node && node.querySelector && node.querySelector("img,video,canvas");
      if (hit) return hit;
    }
    return null;
  }

  async function blobFromElement(el) {
    if (!el) return null;
    const tag = (el.tagName || "").toUpperCase();
    if (tag === "IMG") {
      try {
        const res = await fetch(el.currentSrc || el.src, { credentials: "same-origin" });
        if (res.ok) return await res.blob();
      } catch (_) {}
      const canvas = document.createElement("canvas");
      const w = el.naturalWidth || el.width || 1;
      const h = el.naturalHeight || el.height || 1;
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(el, 0, 0);
      return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/png"));
    }
    if (tag === "VIDEO") {
      try {
        const src = el.currentSrc || el.src;
        if (src && !src.startsWith("blob:")) {
          const res = await fetch(src, { credentials: "same-origin" });
          if (res.ok) return await res.blob();
        }
      } catch (_) {}
      const canvas = document.createElement("canvas");
      canvas.width = el.videoWidth || el.clientWidth || 1;
      canvas.height = el.videoHeight || el.clientHeight || 1;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(el, 0, 0, canvas.width, canvas.height);
      return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/png"));
    }
    if (tag === "CANVAS") {
      return new Promise((resolve) => el.toBlob((b) => resolve(b), "image/png"));
    }
    return null;
  }

  async function writeSystemClipboard(blob, mime) {
    if (!blob || !navigator.clipboard || !window.ClipboardItem) return false;
    try {
      const type = mime || blob.type || "application/octet-stream";
      await navigator.clipboard.write([new ClipboardItem({ [type]: blob })]);
      return true;
    } catch (_) {
      if ((mime || blob.type || "").startsWith("image/")) {
        try {
          await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
          return true;
        } catch (_2) {}
      }
      return false;
    }
  }

  async function readSystemClipboard() {
    if (!navigator.clipboard || !navigator.clipboard.read) return null;
    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          const blob = await item.getType(type);
          return { blob, mime: type, kind: type.startsWith("image/") ? "image" : type.startsWith("video/") ? "video" : "file" };
        }
      }
    } catch (_) {}
    return null;
  }

  async function storeMediaBlob(blob, mime, name) {
    const dataUrl = await blobToDataUrl(blob);
    const doc = await dispatchClipboard({
      action: "copy_media",
      mime: mime || blob.type,
      data_url: dataUrl,
      name: name || "",
    });
    if (doc && doc.ok) {
      state.mediaCount = doc.count || state.mediaCount;
      state.mediaActiveId = doc.media_id || state.mediaActiveId;
      lsSet(LS_MEDIA, { media_id: doc.media_id, mime: doc.mime, kind: doc.kind, at: Date.now() });
      state.historicCount = (doc.historic && doc.historic.count) || state.historicCount;
    }
    return doc;
  }

  function insertMediaBlob(blob, mime) {
    const type = mime || blob.type || "";
    const url = URL.createObjectURL(blob);
    const el = document.activeElement;
    if (type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = url;
      img.alt = "clipboard-paste";
      img.className = "ncw-paste-image";
      if (el && el.isContentEditable) {
        el.focus();
        const sel = window.getSelection();
        if (sel && sel.rangeCount) {
          const range = sel.getRangeAt(0);
          range.deleteContents();
          range.insertNode(img);
          return true;
        }
        el.appendChild(img);
        return true;
      }
      document.body.appendChild(img);
      flashPasteToast("Image pasted — click target field to insert next time");
      return true;
    }
    if (type.startsWith("video/")) {
      const video = document.createElement("video");
      video.src = url;
      video.controls = true;
      video.className = "ncw-paste-video";
      if (el && el.isContentEditable) {
        el.appendChild(video);
        return true;
      }
      flashPasteToast("Video copied to vault — open a media surface to insert");
      return true;
    }
    flashPasteToast("File in vault (" + type + ")");
    return false;
  }

  function flashPasteToast(msg) {
    let toast = document.getElementById("ncw-paste-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "ncw-paste-toast";
      toast.className = "ncw-paste-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add("ncw-paste-toast--show");
    clearTimeout(flashPasteToast._t);
    flashPasteToast._t = setTimeout(() => toast.classList.remove("ncw-paste-toast--show"), 2200);
  }

  async function copyMediaFromContext(ev) {
    const el = mediaTargetFromEvent(ev);
    let blob = null;
    let mime = "";
    let name = "";
    if (el) {
      blob = await blobFromElement(el);
      mime = blob && blob.type;
      name = el.getAttribute && (el.getAttribute("alt") || el.getAttribute("title") || el.src || "") || "";
    }
    if (!blob) {
      const clip = await readSystemClipboard();
      if (clip && clip.blob) {
        blob = clip.blob;
        mime = clip.mime;
      }
    }
    if (!blob) return false;
    await writeSystemClipboard(blob, mime);
    await storeMediaBlob(blob, mime, name);
    flashPasteToast("Copied " + (mime.split("/")[0] || "media") + " to secured vault");
    return true;
  }

  async function pasteMediaFirst() {
    const clip = await readSystemClipboard();
    if (clip && clip.blob) {
      insertMediaBlob(clip.blob, clip.mime);
      const dataUrl = await blobToDataUrl(clip.blob);
      await dispatchClipboard({ action: "copy_media", mime: clip.mime, data_url: dataUrl });
      return true;
    }
    const cached = lsGet(LS_MEDIA, null);
    const doc = await dispatchClipboard({
      action: "paste_media",
      media_id: (cached && cached.media_id) || state.mediaActiveId || undefined,
    });
    if (!doc || !doc.ok) return false;
    const blob = dataUrlToBlob(doc.data_url || "");
    await writeSystemClipboard(blob, doc.mime);
    insertMediaBlob(blob, doc.mime);
    state.mediaActiveId = doc.media_id || state.mediaActiveId;
    return true;
  }

  async function copyUnified(ev) {
    const text = selectionText();
    if (text && text.trim()) {
      if (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
      }
      state.chordsHandled += 1;
      await vaultAction("copy", text);
      return true;
    }
    const got = await copyMediaFromContext(ev);
    if (got && ev) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
    }
    return got;
  }

  async function pasteUnified(ev) {
    if (ev) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
    }
    state.chordsHandled += 1;
    const media = await pasteMediaFirst();
    if (media) return true;
    const doc = await vaultAction("paste");
    const text = (doc && doc.stdout) || "";
    if (text) insertText(text);
    return !!text;
  }

  function performAction(action, ev) {
    if (action === "break") {
      state.chordsHandled += 1;
      return;
    }
    if (action === "copy" || action === "kill_region") {
      copyUnified(ev);
      return;
    }
    if (action === "cut") {
      const text = cutSelection();
      if (!text) return;
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      vaultAction("copy", text);
      return;
    }
    if (action === "paste" || action === "yank" || action === "paste_primary" || action === "paste_clip") {
      pasteUnified(ev);
      return;
    }
    if (action === "clear") {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      vaultAction("clear");
      return;
    }
    if (action === "history" || action === "historic") {
      const text = selectionText();
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      if (text) vaultAction("copy", text);
      vaultAction("history").then((doc) => {
        if (doc && typeof doc.count === "number") state.historicCount = doc.count;
      });
      return;
    }
    if (action === "history_paste" || action === "historic_paste" || action === "paste_history") {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      vaultAction("history_paste", "").then((doc) => {
        const text = (doc && doc.stdout) || "";
        if (text) insertText(text);
      });
    }
  }

  function ensureFlyout() {
    if (flyoutEl) return flyoutEl;
    flyoutEl = document.createElement("div");
    flyoutEl.id = "ncw-flyout";
    flyoutEl.className = "ncw-flyout";
    flyoutEl.setAttribute("role", "dialog");
    flyoutEl.setAttribute("aria-label", "Clipboard scheme picker");
    flyoutEl.hidden = true;
    document.body.appendChild(flyoutEl);
    document.addEventListener(
      "pointerdown",
      (ev) => {
        if (!state.flyoutOpen || !flyoutEl) return;
        if (flyoutEl.contains(ev.target)) return;
        closeFlyout();
      },
      true,
    );
    document.addEventListener("keydown", (ev) => {
      if (state.flyoutOpen && ev.key === "Escape") {
        ev.preventDefault();
        closeFlyout();
      }
    });
    return flyoutEl;
  }

  function schemeLabel(id) {
    const row = (state.schemes || []).find((s) => s.id === id);
    return (row && row.label) || id;
  }

  function renderFlyout() {
    const el = ensureFlyout();
    const hist = (state.schemeHistory || []).filter((id) => id !== state.scheme).slice(0, 6);
    const histHtml = hist.length
      ? hist
          .map(
            (id) =>
              `<button type="button" class="ncw-scheme-btn" data-ncw-scheme="${id}">` +
              `<span>${esc(schemeLabel(id))}</span><small>recent</small></button>`,
          )
          .join("")
      : `<p class="ncw-flyout-motto">No recent schemes yet — pick a style below.</p>`;

    const listHtml = (state.schemes || [])
      .map((s) => {
        const active = s.id === state.scheme ? " ncw-scheme-btn--active" : "";
        return (
          `<button type="button" class="ncw-scheme-btn${active}" data-ncw-scheme="${s.id}">` +
          `<span>${esc(s.label || s.id)}</span><small>${esc(s.id)}</small></button>`
        );
      })
      .join("");

    el.innerHTML =
      `<div class="ncw-flyout-head">` +
      `<h2>Clipboard Wire</h2>` +
      `<span class="ncw-flyout-active">${esc(state.schemeLabel || state.scheme)}</span>` +
      `</div>` +
      `<p class="ncw-flyout-motto">Secured vault · historic ring · ${esc(state.flyoutChord)}</p>` +
      (hist.length ? `<section class="ncw-flyout-section"><h3>Recent</h3>${histHtml}</section>` : "") +
      `<section class="ncw-flyout-section"><h3>Editor soul</h3>${listHtml}</section>` +
      `<div class="ncw-flyout-foot">` +
      `AmmoOS is your clipboard · <span class="ncw-flyout-kbd">${esc(state.flyoutChord)}</span> toggle · ` +
      `${state.historicCount || 0} text · ${state.mediaCount || 0} media` +
      `</div>`;

    el.querySelectorAll("[data-ncw-scheme]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-ncw-scheme");
        if (id) applyScheme(id, true).then(() => renderFlyout());
      });
    });
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function openFlyout(x, y) {
    renderFlyout();
    const el = ensureFlyout();
    const pad = 12;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    el.hidden = false;
    el.classList.add("ncw-flyout--open");
    state.flyoutOpen = true;
    const rect = el.getBoundingClientRect();
    let left = Math.min(Math.max(pad, x), vw - rect.width - pad);
    let top = Math.min(Math.max(pad, y), vh - rect.height - pad);
    if (top < pad && y > vh * 0.5) top = Math.max(pad, y - rect.height - 8);
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
    state.flyoutPos = { x: left, y: top };
  }

  function closeFlyout() {
    if (!flyoutEl) return;
    flyoutEl.classList.remove("ncw-flyout--open");
    flyoutEl.hidden = true;
    state.flyoutOpen = false;
  }

  function toggleFlyout(ev) {
    if (state.flyoutOpen) {
      closeFlyout();
      return;
    }
    const x = ev && ev.clientX != null ? ev.clientX : window.innerWidth / 2 - 140;
    const y = ev && ev.clientY != null ? ev.clientY : 72;
    openFlyout(x, y);
  }

  function onKeydown(ev) {
    if (isFlyoutChord(ev)) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      toggleFlyout(ev);
      return;
    }
    if (!onWireSurface(ev.target)) return;
    if (!ev.isTrusted) {
      state.blockedUntrusted += 1;
      ev.preventDefault();
      ev.stopImmediatePropagation();
      return;
    }
    for (const binding of state.bindings) {
      if (matchBinding(ev, binding)) {
        performAction(String(binding.action || ""), ev);
        return;
      }
    }
  }

  function onClipboardEvent(ev) {
    if (!onWireSurface(ev.target)) return;
    if (!ev.isTrusted) {
      state.blockedUntrusted += 1;
      ev.preventDefault();
      ev.stopImmediatePropagation();
      return;
    }
    if (ev.type === "copy" || ev.type === "cut") {
      const text = selectionText();
      if (text) {
        vaultAction(ev.type === "cut" ? "copy" : "copy", ev.type === "cut" ? cutSelection() : text);
        return;
      }
      copyMediaFromContext(ev);
      return;
    }
    if (ev.type === "paste") {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      pasteUnified(ev);
    }
  }

  function applyBindings(doc) {
    state.scheme = doc.scheme || doc.active || state.scheme;
    state.schemeLabel = doc.active_label || doc.label || schemeLabel(state.scheme);
    state.ghostMode = doc.ghost_mode !== false;
    state.historicCount = doc.historic_count || doc.count || state.historicCount;
    state.mediaCount = doc.media_count || state.mediaCount;
    state.mediaActiveId = doc.media_active_id || state.mediaActiveId;
    state.flyoutChord = doc.flyout_chord || state.flyoutChord;
    if (Array.isArray(doc.scheme_history)) state.schemeHistory = doc.scheme_history;
    if (Array.isArray(doc.history)) state.schemeHistory = doc.history;
    state.bindings = (doc.bindings || []).map((b) => ({
      ...b,
      parsed: b.parsed || parseChord(b.chord),
    }));
    if (!state.bindings.length) {
      state.bindings = [
        { action: "copy", chord: "Control+c", parsed: parseChord("Control+c") },
        { action: "paste", chord: "Control+v", parsed: parseChord("Control+v") },
        { action: "cut", chord: "Control+x", parsed: parseChord("Control+x") },
        { action: "paste", chord: "Shift+Insert", parsed: parseChord("Shift+Insert") },
        { action: "copy", chord: "Control+Insert", parsed: parseChord("Control+Insert") },
      ];
    }
    persistSchemeLocal(state.scheme, state.schemeHistory);
  }

  function loadSchemes() {
    return fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "schemes" }),
      credentials: "same-origin",
    })
      .then((r) => r.json())
      .then((doc) => {
        if (doc.schemes) state.schemes = doc.schemes;
        if (doc.active) state.scheme = doc.active;
        if (doc.active_label) state.schemeLabel = doc.active_label;
        if (doc.history) state.schemeHistory = doc.history;
        if (doc.flyout_chord) state.flyoutChord = doc.flyout_chord;
        if (doc.sovereign_on_boot) state.sovereign = !!doc.sovereign_on_boot;
        persistSchemeLocal(state.scheme, state.schemeHistory);
        return doc;
      })
      .catch(() => null);
  }

  function loadScheme() {
    const cached = lsGet(LS_SCHEME, null);
    const cachedHist = lsGet(LS_HISTORY, null);
    if (cached && cached.scheme) {
      state.scheme = cached.scheme;
      state.schemeLabel = schemeLabel(cached.scheme);
    }
    if (cachedHist && Array.isArray(cachedHist.history)) {
      state.schemeHistory = cachedHist.history;
    }
    return fetch(API, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((doc) => {
        applyBindings(doc);
        if (doc.sovereign_on_boot !== false) state.sovereign = true;
        return doc;
      })
      .catch(() => {
        state.bindings = [
          { action: "copy", chord: "Control+c", parsed: parseChord("Control+c") },
          { action: "paste", chord: "Control+v", parsed: parseChord("Control+v") },
          { action: "paste", chord: "Shift+Insert", parsed: parseChord("Shift+Insert") },
        ];
      });
  }

  function applyScheme(scheme, reload) {
    return fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scheme }),
      credentials: "same-origin",
    })
      .then((r) => r.json())
      .then((doc) => {
        if (!doc.ok) return doc;
        state.scheme = doc.scheme || scheme;
        state.schemeLabel = doc.label || schemeLabel(state.scheme);
        if (doc.scheme_history) state.schemeHistory = doc.scheme_history;
        persistSchemeLocal(state.scheme, state.schemeHistory);
        if (reload) return loadScheme().then(() => doc);
        applyBindings(doc);
        return doc;
      });
  }

  function markSovereign() {
    state.sovereign = true;
    if (document.documentElement) {
      document.documentElement.setAttribute("data-nexus-clipboard-sovereign", "1");
      document.documentElement.setAttribute("data-clipboard-wire", OWNER);
    }
    if (document.body) {
      document.body.setAttribute("data-clipboard-wire", OWNER);
    }
    document.querySelectorAll(WIRE_SEL).forEach((n) => {
      n.setAttribute("data-clipboard-wire", OWNER);
    });
  }

  function board() {
    if (state.boarded) return state;
    ["keydown", "keyup"].forEach((t) => {
      window.addEventListener(t, onKeydown, true);
      document.addEventListener(t, onKeydown, true);
    });
    ["copy", "cut", "paste"].forEach((t) => {
      window.addEventListener(t, onClipboardEvent, true);
      document.addEventListener(t, onClipboardEvent, true);
    });
    markSovereign();
    state.boarded = true;
    return state;
  }

  function init() {
    if (isSovereignSurface()) state.sovereign = true;
    Promise.all([loadScheme(), loadSchemes()]).finally(() => {
      board();
      if (state.sovereign) {
        fetch(API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "enforce" }),
          credentials: "same-origin",
        }).catch(() => {});
      }
    });
  }

  if (window.NexusHardwareWire && typeof window.NexusHardwareWire.board === "function") {
    window.NexusHardwareWire.board();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.NexusClipboardWire = {
    owner: OWNER,
    board,
    openFlyout,
    closeFlyout,
    toggleFlyout,
    copyMedia: copyMediaFromContext,
    pasteMedia: pasteMediaFirst,
    storeMediaBlob,
    setScheme(scheme) {
      return applyScheme(scheme, true);
    },
    loadSchemes,
    state() {
      return { ...state };
    },
  };
})();