/**
 * MS-DOS 4.0 module picker — right-click · GNU Terminal extras.
 */
(function (global) {
  "use strict";

  const API = "/api/field-dos40";
  let pickerEl = null;
  let modulesCache = null;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fetchModules() {
    if (modulesCache) return Promise.resolve(modulesCache);
    const fetchFn = global.FieldSovereignBus?.fetch || fetch;
    return fetchFn(API, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (doc) {
        modulesCache = doc;
        return doc;
      });
  }

  function launchModule(mod) {
    if (!mod || mod.coming_soon) {
      global.FieldHostDesktop?.toast?.((mod && mod.label) + " — coming soon");
      return;
    }
    const exec = mod.exec || "/mspaint";
    const app = {
      id: "dos40-" + (mod.id || "module"),
      name: mod.label || mod.id,
      exec: exec,
      shell: true,
      os_layer: 0,
      category: "AmmoOS · DOS 4.0",
    };
    if (global.NexusFieldShell?.launch) {
      global.NexusFieldShell.launch(app);
      return;
    }
    global.location.href = exec.startsWith("http") ? exec : (global.H7Page ? global.H7Page(exec) : exec);
  }

  function ensurePicker() {
    if (pickerEl) return pickerEl;
    pickerEl = document.createElement("div");
    pickerEl.id = "fd40-picker";
    pickerEl.className = "fd40-picker";
    pickerEl.setAttribute("role", "dialog");
    pickerEl.setAttribute("aria-label", "Load DOS 4.0 module");
    pickerEl.hidden = true;
    document.body.appendChild(pickerEl);
    document.addEventListener("pointerdown", function (ev) {
      if (!pickerEl || pickerEl.hidden) return;
      if (pickerEl.contains(ev.target)) return;
      pickerEl.hidden = true;
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && pickerEl && !pickerEl.hidden) pickerEl.hidden = true;
    });
    return pickerEl;
  }

  function openModulePicker(x, y) {
    fetchModules().then(function (doc) {
      const el = ensurePicker();
      const mods = doc.modules || [];
      el.innerHTML =
        '<div class="fd40-picker-head"><strong>Load module</strong><span>MS-DOS 4.0</span></div>' +
        '<p class="fd40-picker-motto">GNU Terminal · <code>load-module &lt;name&gt;</code> · <code>modules</code></p>' +
        mods.map(function (m) {
          const soon = m.coming_soon ? " fd40-mod--soon" : "";
          const clip = m.clipboard ? " · clipboard" : "";
          return (
            '<button type="button" class="fd40-mod' + soon + '" data-mod="' + esc(m.id) + '">' +
            '<span>' + esc(m.label || m.id) + "</span>" +
            '<small>' + esc(m.dos_help || m.id) + clip + "</small></button>"
          );
        }).join("");
      el.querySelectorAll("[data-mod]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const id = btn.getAttribute("data-mod");
          const mod = mods.find(function (m) { return m.id === id; });
          el.hidden = true;
          launchModule(mod);
        });
      });
      el.hidden = false;
      const pad = 8;
      const rect = el.getBoundingClientRect();
      el.style.left = Math.min(Math.max(pad, x), innerWidth - rect.width - pad) + "px";
      el.style.top = Math.min(Math.max(pad, y), innerHeight - rect.height - pad) + "px";
    });
  }

  function contextExtras() {
    return [
      { label: "Clipboard scheme…", action: "clipboard-flyout" },
      { label: "Paste from vault", action: "clipboard-paste" },
      { divider: true },
      { label: "Load DOS 4.0 module…", action: "dos40-modules" },
    ];
  }

  function handleAction(action, ev) {
    if (action === "clipboard-flyout") {
      global.NexusClipboardWire?.toggleFlyout?.(ev || { clientX: innerWidth / 2, clientY: 80 });
      return true;
    }
    if (action === "clipboard-paste") {
      global.NexusClipboardWire?.pasteMedia?.();
      global.FieldHostDesktop?.toast?.("Paste from clipboard vault");
      return true;
    }
    if (action === "dos40-modules") {
      const x = ev && ev.clientX != null ? ev.clientX : innerWidth / 2 - 120;
      const y = ev && ev.clientY != null ? ev.clientY : 100;
      openModulePicker(x, y);
      return true;
    }
    return false;
  }

  global.FieldDos40Menu = {
    fetchModules: fetchModules,
    openModulePicker: openModulePicker,
    launchModule: launchModule,
    contextExtras: contextExtras,
    handleAction: handleAction,
  };
})(typeof window !== "undefined" ? window : globalThis);