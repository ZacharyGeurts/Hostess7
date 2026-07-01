/**
 * NES cartridge theater — sleeve, booklet slide, console reveal, cart insert.
 */
(function (global) {
  "use strict";

  const API = "/api/queen-file-browser";
  const CONSOLE_IMG = {
    nes: "/library/assets/devices/nes.png",
    famicom: "/library/assets/devices/nes.png",
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function licenseClass(lic) {
    if (lic === "bootleg") return "nes-theater-badge--bootleg";
    if (lic === "unlicensed") return "nes-theater-badge--unlicensed";
    return "nes-theater-badge--licensed";
  }

  function metaTable(entry) {
    const rows = [
      ["Year", entry.year || "—"],
      ["Publisher", entry.publisher || "—"],
      ["Developer", entry.developer || "—"],
      ["Genre", entry.genre || "—"],
      ["Region", entry.region || "—"],
      ["Hardware", (entry.hardware_form || "nes").toUpperCase()],
      ["License", entry.license_label || entry.license || "—"],
    ];
    if (entry.ines) {
      rows.push(["PRG ROM", `${entry.ines.prg_kb || 0} KB`]);
      rows.push(["CHR ROM", `${entry.ines.chr_kb || 0} KB`]);
      rows.push(["Mapper", `${entry.ines.mapper} (${entry.ines.mapper_name || ""})`]);
    }
    if (entry.rom) {
      rows.push(["ROM", entry.rom.filename || "—"]);
    }
    return (
      "<table>" +
      rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("") +
      "</table>"
    );
  }

  function cardHtml(entry) {
    const hw = entry.hardware_form || "nes";
    const lic = entry.license || "licensed";
    const badges =
      `<span class="nes-theater-badge ${licenseClass(lic)}">${esc(entry.license_label || lic)}</span>` +
      (entry.rom ? '<span class="nes-theater-badge nes-theater-badge--rom">.nes in library</span>' : "");
    const consoleSrc = CONSOLE_IMG[hw] || CONSOLE_IMG.nes;
    const romPath = entry.rom?.path || "";
    return (
      `<article class="nes-theater-card" data-nes-id="${esc(entry.id)}"` +
      (romPath ? ` data-rom-path="${esc(romPath)}"` : "") +
      ` data-title="${esc(entry.title)}">` +
      `<div class="nes-theater-stage" data-hw="${esc(hw)}">` +
      `<div class="nes-theater-console"><img src="${esc(consoleSrc)}" alt="${esc(hw)} console" loading="lazy" /></div>` +
      `<div class="nes-theater-stack" role="button" tabindex="0" aria-label="Insert ${esc(entry.title)}">` +
      `<div class="nes-theater-sleeve"><img src="${esc(entry.sleeve_path || entry.box_path)}" alt="sleeve" loading="lazy" /></div>` +
      `<div class="nes-theater-booklet"><img src="${esc(entry.booklet_path || entry.box_path)}" alt="booklet" loading="lazy" /></div>` +
      `<div class="nes-theater-cart"><img src="${esc(entry.cart_path)}" alt="cartridge" loading="lazy" /></div>` +
      `</div></div>` +
      `<div class="nes-theater-meta">` +
      `<strong>${esc(entry.title)}</strong>${badges}${metaTable(entry)}` +
      `</div></article>`
    );
  }

  function bindStage(root) {
    const scope = root || document;
    scope.querySelectorAll(".nes-theater-stack").forEach((stack) => {
      if (stack.dataset.nesBound) return;
      stack.dataset.nesBound = "1";
      const stage = stack.closest(".nes-theater-stage");
      stack.addEventListener("mouseenter", () => {
        stage?.classList.add("nes-show-console");
        stack.classList.add("nes-booklet-out");
      });
      const insert = () => {
        if (stack.classList.contains("nes-inserting")) return;
        stack.classList.add("nes-inserting");
        const card = stack.closest(".nes-theater-card");
        const romPath = card?.dataset?.romPath || "";
        const nesId = card?.dataset?.nesId || "";
        const title = card?.dataset?.title || card?.querySelector("strong")?.textContent || "";
        setTimeout(async () => {
          stack.classList.remove("nes-inserting");
          if (romPath && global.QueenGameRoom?.launch) {
            await global.QueenGameRoom.launch({
              system: "nes",
              rom_path: romPath,
              nes_id: nesId,
              title,
            });
            if (global.location.pathname.includes("queen-game-room")) return;
            global.location.href = "/world/queen-game-room.html";
            return;
          }
          global.QueenZoomLightbox?.open?.(
            stack.querySelector(".nes-theater-cart img")?.src,
            title,
          );
        }, 1200);
      };
      stack.addEventListener("click", insert);
      stack.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          insert();
        }
      });
    });
    global.QueenZoomLightbox?.bind?.(scope);
  }

  async function loadCatalog(limit) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "nes_catalog", limit: limit || 48 }),
    });
    return r.json();
  }

  function render(container, entries) {
    if (!container) return;
    const list = entries || [];
    if (!list.length) {
      container.innerHTML = '<p class="qf-empty">No NES cartridges indexed yet — run field-nes-cartridge-forge build.</p>';
      return;
    }
    container.innerHTML =
      `<div class="nes-theater"><div class="nes-theater-grid">` +
      list.map(cardHtml).join("") +
      `</div></div>`;
    bindStage(container);
  }

  global.QueenNesTheater = { render, bindStage, loadCatalog, cardHtml };
})(typeof window !== "undefined" ? window : globalThis);