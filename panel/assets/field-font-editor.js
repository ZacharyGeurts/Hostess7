(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let font = null;
  let selected = "A";

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  async function clipboardCopy(text) {
    try {
      const res = await fetch("/api/field-clipboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "copy", text: String(text) }),
      });
      const doc = await res.json();
      if (!doc.ok) throw new Error(doc.error || "copy failed");
      return doc;
    } catch (e) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(String(text));
      }
      throw e;
    }
  }

  function renderPointSizes() {
    const sel = $("ffe-point-size");
    if (!sel || !font) return;
    const sizes = font.point_sizes || [12, 16, 24, 32];
    sel.innerHTML = sizes.map((s) => `<option value="${s}">${s} pt</option>`).join("");
    sel.value = String(sizes.includes(24) ? 24 : sizes[0]);
  }

  function renderGlyphs() {
    const grid = $("ffe-glyphs");
    if (!grid || !font?.glyphs) return;
    const keys = Object.keys(font.glyphs).sort();
    grid.innerHTML = keys
      .map(
        (ch) =>
          `<button type="button" class="ffe-glyph${ch === selected ? " selected" : ""}" data-ch="${esc(ch)}">${esc(ch === " " ? "␣" : ch)}</button>`
      )
      .join("");
    grid.querySelectorAll(".ffe-glyph").forEach((btn) => {
      btn.addEventListener("click", () => {
        selected = btn.dataset.ch || "A";
        renderGlyphs();
        renderPreview();
      });
    });
  }

  function renderPreview() {
    const g = (font?.glyphs || {})[selected];
    const props = $("ffe-props");
    const canvas = $("ffe-canvas");
    if (props) {
      props.textContent = g
        ? JSON.stringify({ char: selected, ...g, family: font.family, style: font.style, weight: font.weight }, null, 2)
        : "No glyph selected";
    }
    if (!canvas || !g) return;
    const ctx = canvas.getContext("2d");
    const pt = parseInt($("ffe-point-size")?.value || "24", 10);
    ctx.fillStyle = "#0a1410";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#3ecf8e";
    ctx.font = `bold ${pt}px system-ui, sans-serif`;
    ctx.textBaseline = "middle";
    ctx.fillText(selected === " " ? "·" : selected, 24, canvas.height / 2);
    if (font.sdf?.preview) {
      const img = new Image();
      img.onload = function () {
        const rect = g.sdf_rect || [0, 0, 64, 64];
        ctx.drawImage(img, rect[0], rect[1], rect[2], rect[3], canvas.width - 120, 16, 96, 96);
      };
      img.src = font.sdf.preview;
    }
  }

  async function refresh() {
    const res = await fetch("/api/field-font");
    font = await res.json();
    if (font.font) font = font.font;
    renderPointSizes();
    renderGlyphs();
    renderPreview();
  }

  $("ffe-refresh")?.addEventListener("click", refresh);
  $("ffe-point-size")?.addEventListener("change", renderPreview);
  $("ffe-copy-glyph")?.addEventListener("click", async () => {
    const g = (font?.glyphs || {})[selected];
    if (!g) return;
    await clipboardCopy(JSON.stringify({ glyph: selected, ...g }, null, 2));
  });
  $("ffe-copy-font")?.addEventListener("click", async () => {
    if (!font) return;
    await clipboardCopy(JSON.stringify(font, null, 2));
  });

  refresh();
})();