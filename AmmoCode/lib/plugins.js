/**
 * AmmoCode plugin host — VS Code + Open VSX extension manifests on one surface.
 * Loads unpacked extensions; registers commands, languages, themes into AmmoCode menus.
 */
(function (global) {
  "use strict";

  const extensions = [];
  const commands = new Map();
  const extraLanguages = new Map();

  const vscode = {
    commands: {
      registerCommand(id, handler) {
        commands.set(id, handler);
        return { dispose() { commands.delete(id); } };
      },
      executeCommand(id, ...args) {
        const fn = commands.get(id);
        if (fn) return Promise.resolve(fn(...args));
        return Promise.reject(new Error("command not found: " + id));
      },
    },
    languages: {
      registerDocumentHighlightProvider(_selector, provider) {
        if (provider?.provideDocumentHighlights) {
          global.AmmoCodePluginHighlighters = global.AmmoCodePluginHighlighters || [];
          global.AmmoCodePluginHighlighters.push(provider);
        }
        return { dispose() {} };
      },
      createDiagnosticCollection() {
        return { set() {}, clear() {}, dispose() {} };
      },
    },
    window: {
      showInformationMessage(msg) {
        global.AmmoCodeEditor?.toast?.(msg, true);
        return Promise.resolve(msg);
      },
      showErrorMessage(msg) {
        global.AmmoCodeEditor?.toast?.(msg, false);
        return Promise.resolve(msg);
      },
    },
    workspace: {
      getConfiguration() {
        return { get(k, d) { return d; }, update() { return Promise.resolve(); } };
      },
    },
    Uri: {
      file(p) { return { fsPath: p, scheme: "file" }; },
    },
    Range: function (a, b) { this.start = a; this.end = b; },
    Position: function (line, ch) { this.line = line; this.character = ch; },
    DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
  };

  function activateExtension(manifest, activateFn, source) {
    const ctx = {
      subscriptions: [],
      extensionPath: manifest.extensionPath || "",
      extensionUri: vscode.Uri.file(manifest.extensionPath || ""),
    };
    const api = { ...vscode, extension: manifest };
    if (typeof activateFn === "function") {
      activateFn(api, ctx);
    }
    extensions.push({ manifest, source, ctx });
    (manifest.contributes?.languages || []).forEach((lang) => {
      extraLanguages.set(lang.id, lang);
    });
    (manifest.contributes?.commands || []).forEach((cmd) => {
      commands.set(cmd.command, () => global.AmmoCodeEditor?.toast?.(cmd.title || cmd.command, true));
    });
    return manifest;
  }

  async function loadManifestFromUrl(url, source) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("manifest " + r.status);
    const manifest = await r.json();
    manifest.extensionPath = url.replace(/\/package\.json$/, "");
    activateExtension(manifest, null, source);
    return manifest;
  }

  async function loadUnpackedFolder(files, source) {
    const pkg = files.find((f) => f.name === "package.json");
    if (!pkg) throw new Error("package.json required");
    const text = await pkg.text();
    const manifest = JSON.parse(text);
    manifest.extensionPath = pkg.webkitRelativePath.replace(/\/package\.json$/, "") || ".";
    activateExtension(manifest, null, source);
    return manifest;
  }

  function listExtensions() {
    return extensions.map((e) => ({
      id: e.manifest.name || e.manifest.displayName,
      version: e.manifest.version,
      publisher: e.manifest.publisher,
      source: e.source,
    }));
  }

  function mergedLanguageIds(base) {
    const set = new Set(base || []);
    extraLanguages.forEach((_v, k) => set.add(k));
    return [...set].sort();
  }

  global.AmmoCodePlugins = {
    vscode,
    activateExtension,
    loadManifestFromUrl,
    loadUnpackedFolder,
    listExtensions,
    mergedLanguageIds,
    executeCommand: vscode.commands.executeCommand,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);