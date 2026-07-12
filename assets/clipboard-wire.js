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
    mediaIndex: null,
    mimeByExt: {},
    historyCursor: 0,
    sovereignAt: "",
    sovereignMs: 0,
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
    const fetchFn = global.FieldSovereignBus?.fetch || fetch;
    return fetchFn(API, {
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

  function extFromName(name) {
    const m = String(name || "").toLowerCase().match(/(\.[a-z0-9]{1,8})$/i);
    return m ? m[1] : "";
  }

  function formatLabelForName(name, mime) {
    const ext = extFromName(name);
    if (ext && state.mimeByExt[ext]) {
      const row = (state.mediaIndex && state.mediaIndex.formats) || {};
      for (const id in row) {
        const fmt = row[id];
        if ((fmt.extensions || []).map((e) => e.toLowerCase()).includes(ext)) {
          return fmt.label || id;
        }
      }
    }
    return mime ? mime.split("/").pop() : "media";
  }

  function mediaTargetFromEvent(ev) {
    const t = (ev && ev.target) || document.activeElement;
    if (!t || !t.closest) return null;
    const link = t.closest("a[href]");
    if (link && link.href) {
      const href = link.getAttribute("href") || link.href;
      const ext = extFromName(href);
      if (ext && state.mimeByExt[ext]) return { tag: "LINK", href, download: link.download || "" };
    }
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
    if (el.tag === "LINK" && el.href) {
      try {
        const res = await fetch(el.href, { credentials: "same-origin" });
        if (res.ok) {
          const blob = await res.blob();
          return { blob, name: el.download || el.href.split("/").pop() || "file" };
        }
      } catch (_) {}
      return null;
    }
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
      return new Promise((resolve) => canvas.toBlob((b) => resolve(b && { blob: b, name: "frame.png" }), "image/png"));
    }
    if (tag === "CANVAS") {
      return new Promise((resolve) => el.toBlob((b) => resolve(b && { blob: b, name: "canvas.png" }), "image/png"));
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
      lsSet(LS_MEDIA, {
        media_id: doc.media_id,
        mime: doc.mime,
        kind: doc.kind,
        format_label: doc.format_label,
        at: Date.now(),
      });
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
      const got = await blobFromElement(el);
      if (got && got.blob) {
        blob = got.blob;
        mime = got.blob.type;
        name = got.name || "";
      } else if (got && got.type) {
        blob = got;
        mime = got.type;
        name = el.getAttribute && (el.getAttribute("alt") || el.getAttribute("title") || el.src || "") || "";
      }
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
    const doc = await storeMediaBlob(blob, mime, name);
    const label = (doc && doc.format_label) || formatLabelForName(name, mime);
    flashPasteToast("Copied " + label + " to secured vault");
    return true;
  }

  async function copyFileList(files) {
    if (!files || !files.length) return false;
    let any = false;
    for (const file of files) {
      if (!file) continue;
      await writeSystemClipboard(file, file.type);
      await storeMediaBlob(file, file.type, file.name);
      flashPasteToast("Copied " + formatLabelForName(file.name, file.type) + " to vault");
      any = true;
    }
    return any;
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

  function schemeHint(id) {
    const hints = {
      emacs: "C-y yank · M-w kill-ring",
      vi: ":y · p paste",
      nano: "M-6 copy · C-u paste",
      amiga: "OpenApple+C · solid paste",
      standard: "Ctrl+C · Ctrl+V — easy mode",
    };
    return hints[id] || id;
  }

  function refreshSovereignChip() {
    const fetchFn = global.FieldSovereignBus?.fetch || fetch;
    fetchFn("/api/sovereign-time", { credentials: "same-origin" })
      .then((r) => r.json())
      .then((doc) => {
        state.sovereignAt = doc.derived_utc || doc.sovereign_at || "";
        state.sovereignMs = doc.elapsed_ms || 0;
        const chip = flyoutEl && flyoutEl.querySelector("[data-ncw-sovereign]");
        if (chip) {
          const short = state.sovereignAt.length >= 19 ? state.sovereignAt.slice(11, 19) : "…";
          chip.textContent = short;
          chip.title = "Sovereign time · slowdowns are threats · " + (state.sovereignAt || "");
        }
      })
      .catch(() => {});
  }

  function renderFlyout() {
    const el = ensureFlyout();
    const hist = (state.schemeHistory || []).filter((id) => id !== state.scheme).slice(0, 4);
    const histHtml = hist
      .map(
        (id) =>
          `<button type="button" class="ncw-widget ncw-widget--scheme" data-ncw-scheme="${id}">` +
          `<span class="ncw-widget-label">${esc(schemeLabel(id))}</span>` +
          `<small>${esc(schemeHint(id))}</small></button>`,
      )
      .join("");

    const listHtml = (state.schemes || [])
      .map((s) => {
        const active = s.id === state.scheme ? " ncw-widget--active" : "";
        const grandma = s.id === "standard" ? " · for everyone" : s.id === "emacs" ? " · M-x soul" : "";
        return (
          `<button type="button" class="ncw-widget ncw-widget--scheme${active}" data-ncw-scheme="${s.id}">` +
          `<span class="ncw-widget-label">${esc(s.label || s.id)}</span>` +
          `<small>${esc(schemeHint(s.id))}${grandma}</small></button>`
        );
      })
      .join("");

    const sovShort = state.sovereignAt.length >= 19 ? state.sovereignAt.slice(11, 19) : "…";

    el.innerHTML =
      `<div class="ncw-flyout-head">` +
      `<div class="ncw-flyout-title"><h2>Clipboard</h2><span class="ncw-flyout-active">${esc(state.schemeLabel || state.scheme)}</span></div>` +
      `<button type="button" class="ncw-sovereign-chip" data-ncw-sovereign title="Sovereign time">${esc(sovShort)}</button>` +
      `</div>` +
      `<div class="ncw-widget-row">` +
      `<div class="ncw-stat"><strong>${state.historicCount || 0}</strong><span>text clips</span></div>` +
      `<div class="ncw-stat"><strong>${state.mediaCount || 0}</strong><span>photos & files</span></div>` +
      `<div class="ncw-stat ncw-stat--kbd"><span class="ncw-flyout-kbd">${esc(state.flyoutChord)}</span><span>toggle</span></div>` +
      `</div>` +
      (hist.length ? `<section class="ncw-flyout-section ncw-flyout-section--tight"><h3>Recent styles</h3><div class="ncw-scheme-grid">${histHtml}</div></section>` : "") +
      `<section class="ncw-flyout-section ncw-flyout-section--tight"><h3>Copy & paste style</h3><div class="ncw-scheme-grid">${listHtml}</div></section>` +
      `<div class="ncw-flyout-foot">AmmoOS clipboard · Amiga IFF · PCX · DOS · media vault</div>`;

    el.querySelectorAll("[data-ncw-scheme]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-ncw-scheme");
        if (id) applyScheme(id, true).then(() => renderFlyout());
      });
    });
    refreshSovereignChip();
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

  function loadMediaIndex() {
    return fetch("/api/field-filetypes/media", { credentials: "same-origin" })
      .then((r) => r.json())
      .then((doc) => {
        if (!doc.ok) return dispatchClipboard({ action: "media_index" });
        return doc;
      })
      .catch(() => dispatchClipboard({ action: "media_index" }))
      .then((doc) => {
        if (doc && doc.ok) {
          state.mediaIndex = doc;
          state.mimeByExt = doc.mime_by_extension || {};
        }
        return doc;
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
    document.addEventListener(
      "drop",
      (ev) => {
        if (!onWireSurface(ev.target)) return;
        const files = ev.dataTransfer && ev.dataTransfer.files;
        if (files && files.length) {
          ev.preventDefault();
          copyFileList(files);
        }
      },
      true,
    );
    document.addEventListener(
      "dragover",
      (ev) => {
        if (!onWireSurface(ev.target)) return;
        if (ev.dataTransfer && ev.dataTransfer.types && ev.dataTransfer.types.includes("Files")) {
          ev.preventDefault();
        }
      },
      true,
    );
    markSovereign();
    state.boarded = true;
    return state;
  }

  function init() {
    if (isSovereignSurface()) state.sovereign = true;
    Promise.all([loadScheme(), loadSchemes(), loadMediaIndex()]).finally(() => {
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
    copyFileList,
    storeMediaBlob,
    loadMediaIndex,
    setScheme(scheme) {
      return applyScheme(scheme, true);
    },
    loadSchemes,
    state() {
      return { ...state };
    },
  };
})();