/**
 * Queen Icon Engine — library-backed icons, zero local icon cache, AI-resolve.
 */
(function (global) {
  "use strict";

  const WORLD_ICONS = "/world/assets/icons/";
  const PANEL_ICONS = "/assets/";
  const LIB_INDEX_URL = "/api/queen-program-library?index=1";

  const APP_ALIASES = {
    "ammoos-field": "queen-prog-ammoos",
    "nexus-field": "queen-prog-field",
    "nexus-shield": "queen-prog-shield",
    "nexus-znetwork": "queen-prog-znetwork",
    "znetwork-tray": "queen-prog-znetwork",
    "znetwork-tray-24": "queen-prog-znetwork",
    "znetwork-tray-32": "queen-prog-znetwork",
    "znetwork-tray-22": "queen-prog-znetwork",
    "queen-prog-browser": "queen-prog-browser",
    "queen-prog-terminal": "queen-prog-terminal",
    "queen-prog-files": "queen-prog-files",
    "queen-prog-code": "queen-prog-code",
    "prog-ammoos": "queen-prog-ammoos",
    "prog-files": "queen-prog-files",
    "prog-browser": "queen-prog-browser",
    kilroy: "queen-prog-kilroy",
    files: "queen-prog-files",
    browser: "queen-prog-browser",
    terminal: "queen-prog-terminal",
    code: "queen-prog-code",
    folder: "file-folder",
    file: "file-file",
  };

  const FILE_TYPE_BATTERY = {
    dir: "file-folder",
    launch_facade: "file-launch",
    launch: "file-launch",
    python: "file-python",
    json: "file-json",
    cpp: "file-code",
    shell: "file-shell",
    markdown: "file-markdown",
    image: "file-image",
    video: "file-video",
    audio: "file-audio",
    archive: "file-archive",
    config: "file-config",
    binary: "file-binary",
    unknown: "file-file",
    file: "file-file",
    symlink: "file-symlink",
    code_chamber: "file-launch",
  };

  const EXT_BATTERY = {
    ".py": "file-python",
    ".json": "file-json",
    ".md": "file-markdown",
    ".sh": "file-shell",
    ".launch": "file-launch",
    ".png": "file-image",
    ".jpg": "file-image",
    ".svg": "file-image",
    ".mp4": "file-video",
    ".mp3": "file-audio",
    ".zip": "file-archive",
    ".yaml": "file-config",
    ".cpp": "file-code",
    ".c": "file-code",
    ".comp": "file-code",
  };

  let libIndex = null;
  let libPromise = null;

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeRef(app) {
    const raw = String(app?.icon || app?.id || app?.name || "").trim();
    if (!raw) return "queen-prog-field";
    if (APP_ALIASES[raw]) return APP_ALIASES[raw];
    if (raw.startsWith("znetwork-tray")) return "queen-prog-znetwork";
    if (raw === "nexus-znetwork" || raw === "znetwork") return "queen-prog-znetwork";
    if (raw.startsWith("queen-prog-") || raw.startsWith("file-") || raw.startsWith("type-") || raw.startsWith("host-")) {
      return raw;
    }
    if (raw.startsWith("prog-")) return `queen-prog-${raw.replace("prog-", "").replace(/-48$/, "").replace(/-32$/, "")}`;
    return `queen-prog-${raw.replace(/[^a-z0-9_-]/gi, "").toLowerCase()}`;
  }

  function fileBatteryId(entry) {
    if (!entry) return "file-file";
    if (entry.kind === "dir" || entry.kind === "folder") return "file-folder";
    if (entry.kind === "symlink") return "file-symlink";
    if (entry.kind === "launch_facade" || entry.facade) return "file-launch";
    const ft = entry.file_type || {};
    const tid = String(ft.type_id || "").toLowerCase();
    if (tid) return `type-${tid}`;
    if (tid && FILE_TYPE_BATTERY[tid]) return FILE_TYPE_BATTERY[tid];
    const ext = String(entry.ext || entry.name || "").split(".").pop().toLowerCase();
    const dotted = ext ? `.${ext}` : "";
    if (EXT_BATTERY[dotted]) return EXT_BATTERY[dotted];
    if (ft.action === "open_code" || ft.action === "run_launchable") return "file-code";
    if (ft.launchable) return "file-launch";
    return "file-file";
  }

  async function loadLibraryIndex(force) {
    if (libIndex && !force) return libIndex;
    if (libPromise && !force) return libPromise;
    libPromise = fetch(LIB_INDEX_URL, { cache: "no-store" })
      .then((r) => r.json())
      .then((doc) => {
        libIndex = doc.index || {};
        libIndex._policy = doc.policy || {};
        libIndex._updated = doc.updated;
        return libIndex;
      })
      .catch(() => {
        libIndex = {};
        return libIndex;
      });
    return libPromise;
  }

  function lookupEntry(ref) {
    if (!libIndex) return null;
    const candidates = [
      ref,
      APP_ALIASES[ref],
      `queen-prog-${ref}`,
      `file-${ref}`,
      `type-${ref}`,
    ].filter(Boolean);
    for (const cid of candidates) {
      if (libIndex[cid]) return { id: cid, ...libIndex[cid] };
    }
    return null;
  }

  function libraryIconUrl(ref, size) {
    const hit = lookupEntry(ref);
    if (hit?.icon_url) return hit.icon_url;
    return `/api/queen-program-library/icon/${encodeURIComponent(ref)}${size ? `?size=${size}` : ""}`;
  }

  function iconUrl(batteryId, size) {
    const hit = lookupEntry(batteryId);
    if (hit?.icon_url) return hit.icon_url;
    const sz = size || 32;
    return `${WORLD_ICONS}${String(batteryId).replace(/^(file-|queen-prog-)/, (m) => (m === "file-" ? "file-" : "prog-"))}-${sz}.png`;
  }

  function programIconUrl(app, size, base) {
    if (app?.icon_url && !app.icon_url.includes("field-host-desktop")) return app.icon_url;
    const ref = normalizeRef(app);
    const hit = lookupEntry(ref);
    if (hit?.icon_url) return hit.icon_url;
    const pid = ref.replace("queen-prog-", "");
    const sz = size || 32;
    if (base === PANEL_ICONS) return `${PANEL_ICONS}queen-prog-${pid}.png`;
    return libraryIconUrl(ref, sz);
  }

  function programIconHtml(app, size, opts) {
    const small = opts?.small;
    const sz = size || (small ? 20 : 28);
    const ref = normalizeRef(app);
    const hit = lookupEntry(ref);
    const src = programIconUrl(app, sz, opts?.base);
    const ai = hit ? ` data-queen-icon-ref="${esc(ref)}" data-queen-ai-name="${esc(hit.name || app?.name || "")}"` : "";
    const cls = `qie-prog-icon${small ? " qie-prog-icon--sm" : ""}${app?.live ? " qie-prog-icon--live" : ""}`;
    if (app?.live) {
      return `<span class="qie-live-wrap${small ? " qie-live-wrap--sm" : ""}"><img src="${esc(src)}" alt="" width="${sz}" height="${sz}" class="${cls}" loading="lazy" decoding="async"${ai} /><span class="qie-live-ring" aria-hidden="true"></span></span>`;
    }
    return `<img src="${esc(src)}" alt="" width="${sz}" height="${sz}" class="${cls}" loading="lazy" decoding="async"${ai} onerror="this.classList.add('qie-miss');this.src='${esc(PANEL_ICONS)}ammoos-field-48.png'" />`;
  }

  function folderHeatVars(heat) {
    const fc = Number(heat?.file_count ?? heat?.child_count ?? 0);
    const bytes = Number(heat?.total_bytes ?? 0);
    const subs = Number(heat?.subdir_count ?? 0);
    const blue = Math.min(1, Math.log10(1 + fc) / 2.4);
    const yellow = Math.min(1, Math.log10(1 + bytes) / 7.2);
    const dark = Math.min(1, Math.log10(1 + subs) / 1.75);
    return { blue, yellow, dark, fc, bytes, subs };
  }

  function folderHeatTitle(heat) {
    const v = folderHeatVars(heat || {});
    const kb = v.bytes >= 1024 * 1024 ? `${(v.bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(v.bytes / 1024)} KB`;
    return `${v.fc} files · ${kb} · ${v.subs} folders`;
  }

  function fileIconHtml(entry, size) {
    const bid = fileBatteryId(entry);
    const hit = lookupEntry(bid);
    const sz = size || 20;
    const src = hit?.icon_url || iconUrl(bid, sz);
    const title = entry?.file_type?.label || entry?.name || hit?.name || bid;
    const ref = hit?.id || bid;
    const img = `<img src="${esc(src)}" alt="" width="${sz}" height="${sz}" class="qie-file-icon qie-file-icon--${esc(bid)}" title="${esc(title)}" loading="lazy" decoding="async" data-queen-icon-ref="${esc(ref)}" onerror="this.replaceWith(qieEmojiFallback('${esc(bid)}'))" />`;
    if ((entry?.kind === "dir" || entry?.kind === "folder") && entry?.folder_heat) {
      const v = folderHeatVars(entry.folder_heat);
      return (
        `<span class="qie-folder-heat" style="--fh-blue:${v.blue};--fh-yellow:${v.yellow};--fh-dark:${v.dark}"` +
        ` title="${esc(folderHeatTitle(entry.folder_heat))}" data-queen-ai-kind="folder" data-queen-ai-name="${esc(entry.name || "")}">${img}</span>`
      );
    }
    return img;
  }

  function emojiFallback(bid) {
    const map = {
      "file-folder": "📁",
      "file-file": "📄",
      "file-launch": "▶",
      "file-python": "🐍",
      "file-json": "📋",
      "file-code": "⌨",
      "file-shell": "⌨",
      "file-symlink": "🔗",
      "file-image": "🖼",
      "file-video": "🎬",
      "file-audio": "🔊",
      "file-markdown": "📝",
      "file-config": "⚙",
      "file-archive": "📦",
      "file-binary": "🔷",
    };
    const span = document.createElement("span");
    span.className = "qie-emoji";
    span.textContent = map[bid] || map[String(bid).replace("type-", "file-")] || "📄";
    return span;
  }

  global.qieEmojiFallback = emojiFallback;

  loadLibraryIndex();

  global.QueenIconEngine = {
    WORLD_ICONS,
    PANEL_ICONS,
    loadLibraryIndex,
    lookupEntry,
    libraryIconUrl,
    normalizeRef,
    fileBatteryId,
    iconUrl,
    programIconUrl,
    programIconHtml,
    fileIconHtml,
    folderHeatVars,
    folderHeatTitle,
    APP_ALIASES,
    FILE_TYPE_BATTERY,
  };
})(typeof window !== "undefined" ? window : globalThis);