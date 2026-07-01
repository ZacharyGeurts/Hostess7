/**
 * AmmoCode secured settings — server-backed signed file; migrates on run.
 */
(function (global) {
  "use strict";

  const LEGACY_EDITOR = "ammocode-settings-v1";
  const LEGACY_COLLAB = "ammocode-collab-v1";
  const LEGACY_FILES = "ammocode-file-settings-v1";

  function apiBase() {
    return global.AmmoCodeG16?.cfg?.()?.apiBase || "/api/ammocode";
  }

  async function action(name, body) {
    const r = await fetch(apiBase(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: name, ...body }),
    });
    return r.json();
  }

  function legacyImport() {
    const out = {};
    try {
      const ed = localStorage.getItem(LEGACY_EDITOR);
      if (ed) Object.assign(out, JSON.parse(ed));
    } catch (_) {}
    try {
      const co = localStorage.getItem(LEGACY_COLLAB);
      if (co) {
        const c = JSON.parse(co);
        if (c.name) out.collabName = c.name;
        if (c.cursorId) out.collabCursorId = c.cursorId;
        if (c.invite) out.collabInvite = c.invite;
        if (c.muted != null) out.collabMuted = c.muted;
        if (c.volume != null) out.collabVolume = c.volume;
      }
    } catch (_) {}
    try {
      const fs = localStorage.getItem(LEGACY_FILES);
      if (fs) out.fileDisableAging = JSON.parse(fs);
    } catch (_) {}
    return Object.keys(out).length ? out : null;
  }

  async function load(opts) {
    const legacy = opts?.importLegacy !== false ? legacyImport() : null;
    const j = await action("settings_load", legacy ? { import_local: legacy } : {});
    if (legacy && j.ok) {
      try {
        localStorage.removeItem(LEGACY_EDITOR);
        localStorage.removeItem(LEGACY_COLLAB);
        localStorage.removeItem(LEGACY_FILES);
      } catch (_) {}
    }
    return j;
  }

  async function save(patch) {
    return action("settings_save", { patch: patch || {} });
  }

  async function status() {
    return action("settings_status", {});
  }

  function editorFrom(doc) {
    const s = doc?.settings || doc || {};
    return {
      fontSize: s.fontSize ?? 13,
      tabSize: s.tabSize ?? 4,
      wordWrap: !!s.wordWrap,
      autodetect: s.autodetect !== false,
      profile: s.profile || "belt_2_0",
      theme: s.theme || "nexus_c2",
      syntaxTheme: s.syntaxTheme || "nexus_c2",
      toolbarEnabled: s.toolbarEnabled && typeof s.toolbarEnabled === "object" ? s.toolbarEnabled : {},
      iconSize: s.iconSize ?? 24,
      showMinimap: !!s.showMinimap,
      showBreadcrumbs: !!s.showBreadcrumbs,
      splitEditor: !!s.splitEditor,
      tabAging: s.tabAging !== false,
    };
  }

  function collabFrom(doc) {
    const s = doc?.settings || doc || {};
    return {
      name: s.collabName || "coder",
      cursorId: s.collabCursorId || "arrow_emerald",
      invite: s.collabInvite || "",
      muted: !!s.collabMuted,
      volume: typeof s.collabVolume === "number" ? s.collabVolume : 0.8,
    };
  }

  function fileAgingFrom(doc) {
    const s = doc?.settings || doc || {};
    const fa = s.fileDisableAging;
    if (fa && typeof fa === "object") {
      return fa.paths ? fa : { paths: fa };
    }
    return { paths: {} };
  }

  global.AmmoCodeSettings = {
    load,
    save,
    status,
    editorFrom,
    collabFrom,
    fileAgingFrom,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);