/** Hostess 7 browser graphics — mirrors field_gfx_canvas scene routing */
(function () {
  const canvas = document.getElementById("gfx");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const caption = document.getElementById("gfx-caption");
  let mode = "pen";
  let drawing = false;
  let lastX = 0;
  let lastY = 0;

  function fitCanvas() {
    const wrap = canvas.parentElement;
    const w = wrap.clientWidth;
    const ratio = 16 / 9;
    const h = Math.max(220, Math.min(540, Math.round(w / ratio)));
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
  }

  function fill(bg) {
    ctx.fillStyle = `rgb(${bg[0]},${bg[1]},${bg[2]})`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function text(x, y, str, color, size) {
    ctx.fillStyle = `rgb(${color[0]},${color[1]},${color[2]})`;
    ctx.font = `600 ${size}px Segoe UI, system-ui, sans-serif`;
    ctx.fillText(str, x, y);
  }

  function rect(x, y, w, h, color) {
    ctx.fillStyle = `rgb(${color[0]},${color[1]},${color[2]})`;
    ctx.fillRect(x, y, w, h);
  }

  function smpteBars() {
    fill([18, 22, 30]);
    text(16, 28, "SMPTE bars — lossless pixels", [200, 210, 220], 18);
    const colors = [
      [192, 192, 192], [192, 192, 0], [0, 192, 192], [0, 192, 0],
      [192, 0, 192], [192, 0, 0], [0, 0, 192],
    ];
    const barW = Math.floor((canvas.width - 32) / colors.length);
    colors.forEach((c, i) => rect(16 + i * barW, 60, barW, 280, c));
    text(16, canvas.height - 24, "Vision Expert · broadcast reference", [120, 130, 150], 13);
  }

  function pixelGrid() {
    fill([18, 22, 30]);
    const step = 8;
    for (let y = 0; y < canvas.height; y += step) {
      for (let x = 0; x < canvas.width; x += step) {
        const even = ((x / step) + (y / step)) % 2 === 0;
        rect(x, y, step, step, even ? [40, 48, 62] : [28, 34, 46]);
      }
    }
    text(16, 36, `Pixel grid ${canvas.width}×${canvas.height}`, [180, 190, 200], 16);
  }

  function brainHemispheres() {
    fill([18, 22, 30]);
    text(16, 28, "Hostess 7 brain", [140, 200, 255], 22);
    rect(40, 80, 360, 200, [50, 90, 140]);
    rect(560, 80, 360, 200, [140, 70, 120]);
    text(120, 110, "LEFT", [220, 230, 240], 24);
    text(640, 110, "RIGHT", [220, 230, 240], 24);
    text(430, 170, "callosum", [180, 200, 220], 18);
    text(16, canvas.height - 24, "Language · Logic · Memory · Vision", [120, 130, 150], 13);
  }

  function storageChart() {
    fill([18, 22, 30]);
    text(16, 28, "Field storage — lossless", [140, 200, 255], 20);
    const bars = [
      ["brain", 0.55, [80, 140, 220]],
      ["textbooks", 0.25, [100, 180, 120]],
      ["lexicon", 0.12, [180, 120, 200]],
      ["other", 0.08, [140, 140, 160]],
    ];
    let y = 70;
    bars.forEach(([label, frac, col]) => {
      const bw = Math.floor(frac * (canvas.width - 120));
      rect(100, y, bw, 36, col);
      text(16, y + 24, label, [200, 210, 220], 14);
      y += 52;
    });
  }

  function defaultScene(query) {
    fill([18, 22, 30]);
    text(16, 28, "Hostess 7 Graphics", [140, 200, 255], 22);
    const line = (query || "listening…").slice(0, 72);
    text(16, 64, line, [200, 210, 220], 16);
    text(16, 96, "Talk on the right — I draw what you ask about.", [140, 150, 160], 13);
    const g = ctx.createLinearGradient(0, 120, canvas.width, 400);
    g.addColorStop(0, "rgba(126,200,255,0.15)");
    g.addColorStop(1, "rgba(196,160,255,0.08)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 120, canvas.width, 280);
  }

  function presentScene(query) {
    const q = (query || "").toLowerCase();
    if (q.includes("tv") || q.includes("smpte") || q.includes("broadcast") || q.includes("bar")) {
      smpteBars();
    } else if (q.includes("pixel") || q.includes("framebuffer") || q.includes("grid") || q.includes("4k")) {
      pixelGrid();
    } else if (q.includes("brain") || q.includes("hemisphere") || q.includes("callosum")) {
      brainHemispheres();
    } else if (q.includes("storage") || q.includes("drive") || q.includes("lossless") || q.includes("field")) {
      storageChart();
    } else if (q.includes("draw")) {
      brainHemispheres();
    } else {
      defaultScene(query);
    }
    if (caption) caption.textContent = query ? `Drawing: ${query.slice(0, 80)}` : "Canvas ready.";
  }

  function pointerPos(e) {
    const r = canvas.getBoundingClientRect();
    const sx = canvas.width / r.width;
    const sy = canvas.height / r.height;
    return {
      x: (e.clientX - r.left) * sx,
      y: (e.clientY - r.top) * sy,
    };
  }

  function startDraw(e) {
    if (mode !== "pen") return;
    drawing = true;
    const p = pointerPos(e);
    lastX = p.x;
    lastY = p.y;
  }

  function moveDraw(e) {
    if (!drawing || mode !== "pen") return;
    const p = pointerPos(e);
    ctx.strokeStyle = "rgba(126, 200, 255, 0.9)";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    lastX = p.x;
    lastY = p.y;
  }

  function endDraw() {
    drawing = false;
  }

  canvas.addEventListener("pointerdown", startDraw);
  canvas.addEventListener("pointermove", moveDraw);
  canvas.addEventListener("pointerup", endDraw);
  canvas.addEventListener("pointerleave", endDraw);

  document.getElementById("tool-pen")?.addEventListener("click", () => {
    mode = "pen";
    document.querySelectorAll(".tool").forEach((b) => b.classList.remove("active"));
    document.getElementById("tool-pen")?.classList.add("active");
  });

  document.getElementById("tool-hostess")?.addEventListener("click", () => {
    mode = "hostess";
    document.querySelectorAll(".tool").forEach((b) => b.classList.remove("active"));
    document.getElementById("tool-hostess")?.classList.add("active");
  });

  document.getElementById("tool-clear")?.addEventListener("click", () => {
    defaultScene("");
    if (caption) caption.textContent = "Canvas cleared.";
  });

  window.addEventListener("resize", fitCanvas);
  fitCanvas();
  defaultScene("");

  window.HostessGfx = { presentScene, clear: () => defaultScene("") };
})();
