/**
 * NEXUS Clipboard Wire — hardware-secured copy/paste on all wire surfaces.
 * Ctrl+C Ctrl+V Shift+Insert OpenApple — ALL OF IT (standard · emacs · nano · vi · Apple IIe · …).
 */
(function () {
  "use strict";

  const OWNER = "nexus-clipboard-wire";
  const WIRE_SEL = "[data-clipboard-wire], [data-hardware-wire], [data-smart-wire], [data-front-hook], [data-admin-shield], [data-queen-surface=\"browser\"], .qw-browser-shell, .fm-shell";
  const API = "/api/field-clipboard";

  const state = {
    owner: OWNER,
    boarded: false,
    scheme: "standard",
    bindings: [],
    chordsHandled: 0,
    blockedUntrusted: 0,
    vaultOps: 0,
    ghostMode: true,
    historicCount: 0,
    historyCursor: 0,
  };

  function onWireSurface(target) {
    return !!(target && target.closest && target.closest(WIRE_SEL));
  }

  function parseChord(chord) {
    const parts = String(chord || "").toLowerCase().split("+").map((s) => s.trim()).filter(Boolean);
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

  function vaultAction(action, text) {
    state.vaultOps += 1;
    const opts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, text: text || "" }),
      credentials: "same-origin",
    };
    return fetch(API, opts)
      .then((r) => r.json())
      .catch(() => ({ ok: false, error: "vault_unreachable" }));
  }

  function performAction(action, ev) {
    if (action === "break") {
      state.chordsHandled += 1;
      return;
    }
    if (action === "copy" || action === "kill_region") {
      const text = selectionText();
      if (!text) return;
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      vaultAction(action, text);
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
      ev.preventDefault();
      ev.stopImmediatePropagation();
      state.chordsHandled += 1;
      vaultAction(action === "paste_primary" ? "paste" : action).then((doc) => {
        const text = (doc && doc.stdout) || "";
        if (text) insertText(text);
      });
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

  function onKeydown(ev) {
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
      if (text) vaultAction(ev.type === "cut" ? "copy" : "copy", ev.type === "cut" ? cutSelection() : text);
    }
    if (ev.type === "paste") {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      vaultAction("paste").then((doc) => {
        const text = (doc && doc.stdout) || "";
        if (text) insertText(text);
      });
    }
  }

  function loadScheme() {
    return fetch(API, { credentials: "same-origin" })
      .then((r) => r.json())
      .then((doc) => {
        state.scheme = doc.scheme || "standard";
        state.ghostMode = doc.ghost_mode !== false;
        state.historicCount = doc.historic_count || 0;
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
      })
      .catch(() => {
        state.bindings = [
          { action: "copy", chord: "Control+c", parsed: parseChord("Control+c") },
          { action: "paste", chord: "Control+v", parsed: parseChord("Control+v") },
          { action: "paste", chord: "Shift+Insert", parsed: parseChord("Shift+Insert") },
        ];
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
    document.querySelectorAll(WIRE_SEL).forEach((n) => {
      n.setAttribute("data-clipboard-wire", OWNER);
    });
    if (document.documentElement) {
      document.documentElement.setAttribute("data-nexus-clipboard-wire", OWNER);
    }
    state.boarded = true;
    return state;
  }

  function init() {
    loadScheme().finally(board);
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
    setScheme(scheme) {
      return fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scheme }),
        credentials: "same-origin",
      }).then(() => loadScheme());
    },
    state() { return { ...state }; },
  };
})();