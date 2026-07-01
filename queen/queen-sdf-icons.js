/**
 * Queen SDF icons — analytic distance-field desktop glyphs (folder, program, document).
 */
(function (global) {
  "use strict";

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function sdBox(px, py, hx, hy) {
    const dx = Math.abs(px) - hx;
    const dy = Math.abs(py) - hy;
    return Math.sqrt(Math.max(dx, 0) ** 2 + Math.max(dy, 0) ** 2) + Math.min(Math.max(dx, dy), 0);
  }

  function sdRoundBox(px, py, hx, hy, r) {
    const dx = Math.abs(px) - hx + r;
    const dy = Math.abs(py) - hy + r;
    return Math.sqrt(Math.max(dx, 0) ** 2 + Math.max(dy, 0) ** 2) + Math.min(Math.max(dx, dy), 0) - r;
  }

  function fill(canvas, drawFn, colors) {
    const w = canvas.width;
    const h = canvas.height;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(w, h);
    const edge = 0.045;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const u = (x + 0.5) / w - 0.5;
        const v = (y + 0.5) / h - 0.5;
        const d = drawFn(u * 2, v * 2);
        const aa = clamp(0.5 - d / edge, 0, 1);
        const idx = (y * w + x) * 4;
        const c = colors(d, u, v, aa);
        img.data[idx] = c[0];
        img.data[idx + 1] = c[1];
        img.data[idx + 2] = c[2];
        img.data[idx + 3] = Math.round(c[3] * aa);
      }
    }
    ctx.putImageData(img, 0, 0);
  }

  function folderField(u, v) {
    const tab = sdRoundBox(u + 0.02, v - 0.22, 0.18, 0.06, 0.02);
    const body = sdRoundBox(u, v + 0.04, 0.38, 0.34, 0.04);
    return Math.min(tab, body);
  }

  function programField(u, v) {
    const win = sdRoundBox(u, v + 0.02, 0.36, 0.36, 0.03);
    const bar = sdBox(u, v - 0.28, 0.34, 0.05);
    const btn1 = sdBox(u - 0.24, v - 0.28, 0.03, 0.03);
    const btn2 = sdBox(u - 0.16, v - 0.28, 0.03, 0.03);
    const btn3 = sdBox(u - 0.08, v - 0.28, 0.03, 0.03);
    return Math.min(win, bar, btn1, btn2, btn3);
  }

  function documentField(u, v) {
    const page = sdRoundBox(u - 0.02, v, 0.3, 0.38, 0.03);
    const fold = sdBox(u + 0.18, v - 0.22, 0.1, 0.1);
    const line1 = sdBox(u - 0.02, v + 0.08, 0.2, 0.02);
    const line2 = sdBox(u - 0.02, v + 0.18, 0.16, 0.02);
    return Math.min(page, fold, line1, line2);
  }

  function hostField(u, v) {
    const shield = sdRoundBox(u, v, 0.34, 0.38, 0.06);
    const notch = sdBox(u, v - 0.12, 0.12, 0.12);
    return Math.min(shield, notch);
  }

  const PALETTES = {
    folder: (d, _u, _v, aa) => [255, 212, 76, 255 * aa],
    program: (d, _u, _v, aa) => {
      const t = clamp(0.55 + d * 0.3, 0, 1);
      return [180 + t * 40, 190 + t * 30, 210 + t * 20, 255 * aa];
    },
    document: (d, _u, _v, aa) => [240, 240, 235, 255 * aa],
    host: (d, _u, _v, aa) => [100, 160, 220, 255 * aa],
  };

  function renderIcon(canvas, kind, opts) {
    const size = opts?.size || 48;
    canvas.width = size;
    canvas.height = size;
    const k = kind || "program";
    const field =
      k === "folder" ? folderField : k === "document" ? documentField : k === "host" ? hostField : programField;
    const pal = PALETTES[k] || PALETTES.program;
    fill(canvas, field, pal);
    return canvas;
  }

  function mountIcon(el, kind, opts) {
    if (!el) return;
    const canvas = document.createElement("canvas");
    canvas.className = "qd-sdf-icon";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-hidden", "true");
    renderIcon(canvas, kind, opts);
    el.textContent = "";
    el.appendChild(canvas);
  }

  global.QueenSdfIcons = { renderIcon, mountIcon };
})(window);