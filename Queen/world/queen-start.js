(function () {
  "use strict";

  const ICON = (id) => `assets/icons/prog-${id}-48.png`;

  const FOLDERS = [
    {
      id: "os",
      label: "OS",
      hint: "Start menu · desktop · shell",
      programs: [
        { id: "browser", label: "Queen Browser", hint: "Tabbed OS", url: "/world/browser.html" },
        { id: "os-desktop", label: "Queen Desktop", hint: "Taskbar shell", url: "/world/queen-desktop.html" },
        { id: "files", label: "Files", hint: "Folder manager", url: "/world/queen-files.html" },
        { id: "terminal", label: "Terminal", hint: "GNU shell", url: "queen://terminal" },
        { id: "thermal-manager", label: "Thermal Manager", hint: "Landauer guard", url: "/world/queen-thermal-manager.html" },
        { id: "code", label: "Queen Code", hint: "Editor", url: "/world/queen-code.html" },
        { id: "gameroom", label: "Game Room", hint: "CHIPS theater", url: "queen://gameroom" },
      ],
    },
    {
      id: "command",
      label: "Command",
      hint: "Integrations · C2 · field stack",
      programs: [
        { id: "ammoos", label: "NEXUS Field", hint: "C2 desktop", url: "http://127.0.0.1:9477/field" },
        { id: "field-command", label: "Field Command", hint: "Operator deck", url: "http://127.0.0.1:9477/command" },
        { id: "nexus-c2", label: "AmmoOS C2", hint: "Panel grid", url: "/world/queen-nexus-c2.html" },
        { id: "chips", label: "CHIPS", hint: "Ironclad compute", url: "queen://chips" },
        { id: "cores", label: "Cores", hint: "Die cores", url: "queen://cores" },
        { id: "kilroy", label: "KILROY", hint: "Field OS", url: "queen://kilroy" },
        { id: "field", label: "Field Tech", hint: "Primer dock", url: "/world/?embed=1&dock=field" },
      ],
    },
    {
      id: "hostess-7",
      label: "Hostess 7",
      hint: "AI training · neural lanes",
      programs: [
        { id: "hostess-hub", label: "AI Training Hub", hint: "Every AI lane", url: "/world/queen-hostess7-hub.html" },
        { id: "hostess", label: "Hostess Brain", hint: "Super intelligence", url: "queen://hostess" },
        { id: "hostess-training", label: "Training Viewer", hint: "Connected models", url: "http://127.0.0.1:9488/" },
        { id: "eyeball", label: "Final_Eye", hint: "Vision NN", url: "queen://eyeball" },
        { id: "final-ear-manager", label: "Final Ear", hint: "Audio NN", url: "/world/queen-final-ear-manager.html" },
        { id: "forge", label: "Forge", hint: "Build deck", url: "/gui/queen-build-deck.html" },
        { id: "g16", label: "Grok16", hint: "Compiler", url: "queen://g16" },
        { id: "gpy", label: "GPY-16", hint: "Runtime", url: "queen://grokpy" },
      ],
    },
  ];

  function programFromTile(btn) {
    return {
      id: btn.dataset.id,
      name: btn.dataset.name || btn.querySelector("strong")?.textContent || "Program",
      url: btn.dataset.url,
    };
  }

  async function openProgram(prog, opts) {
    if (globalThis.QueenProgramSurface?.launchProgram && prog.id) {
      await globalThis.QueenProgramSurface.launchProgram(prog, opts || {});
      return;
    }
    const url = prog.url;
    if (window.parent && window.parent !== window) {
      window.parent.postMessage(
        { type: "queen:shell", action: opts?.newTab ? "new_tab" : "navigate", url },
        window.location.origin,
      );
      return;
    }
    window.location.href = url.startsWith("/") ? `${location.origin}${url}` : url;
  }

  function render() {
    const grid = document.getElementById("qs-programs");
    if (!grid) return;
    grid.innerHTML = FOLDERS.map(
      (folder) =>
        `<section class="qs-folder" data-folder="${folder.id}">` +
        `<header class="qs-folder-head"><strong>${folder.label}</strong><span>${folder.hint}</span></header>` +
        `<div class="qs-folder-grid">` +
        folder.programs
          .map(
            (p) =>
              `<button type="button" class="qs-tile" data-id="${p.id}" data-url="${p.url}" data-name="${p.label}">` +
              `<img class="qs-tile-icon" src="${ICON(p.id.replace("os-desktop", "os"))}" alt="" width="40" height="40" loading="lazy" decoding="async" />` +
              `<strong>${p.label}</strong><span>${p.hint}</span></button>`,
          )
          .join("") +
        `</div></section>`,
    ).join("");
    grid.querySelectorAll(".qs-tile").forEach((btn) => {
      const prog = programFromTile(btn);
      btn.addEventListener("click", () => openProgram(prog, { newTab: true }));
      btn.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        if (globalThis.QueenProgramSurface?.openContextMenu) {
          void globalThis.QueenProgramSurface.openContextMenu(ev.clientX, ev.clientY, prog);
        }
      });
    });
  }

  async function refreshVerdict() {
    const el = document.getElementById("qs-verdict");
    if (!el) return;
    try {
      const r = await fetch("/api/queen-browser", { cache: "no-store" });
      const j = await r.json();
      el.textContent = `Gates ${j.gates?.held ?? "—"}/${j.gates?.total ?? "—"} · ${j.queen_verdict || "…"}`;
    } catch (_) {
      el.textContent = "Gates offline";
    }
  }

  render();
  refreshVerdict();
})();