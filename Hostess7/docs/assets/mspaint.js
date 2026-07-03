(function () {
  "use strict";

  const API = "/api/field-mspaint";
  const CLASSIC16 = [
    "#000000", "#7f7f7f", "#880015", "#ed1c24", "#ff7f27", "#fff200",
    "#22b14c", "#00a2e8", "#3f48cc", "#a349a4", "#ffffff", "#c3c3c3",
    "#b97a57", "#ffaec9", "#ffc90e", "#efe4b0",
  ];

  const state = {
    tool: "pencil",
    fg: "#000000",
    bg: "#ffffff",
    size: 2,
    drawing: false,
    start: null,
    snapshot: null,
    undo: [],
  };

  let canvas, ctx;

  function $(id) { return document.getElementById(id); }

  function setStatus(msg) {
    const el = $("msp-status");
    if (el) el.textContent = msg;
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function pushUndo() {
    if (!canvas) return;
    state.undo.push(canvas.toDataURL("image/png"));
    if (state.undo.length > 24) state.undo.shift();
  }

  function undo() {
    const prev = state.undo.pop();
    if (!prev || !ctx) return;
    const img = new Image();
    img.onload = function () {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      setStatus("Undo");
    };
    img.src = prev;
  }

  function clearCanvas() {
    if (!ctx) return;
    pushUndo();
    ctx.fillStyle = state.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setStatus("New image");
  }

  function renderPalette() {
    const grid = $("msp-palette");
    if (!grid) return;
    grid.innerHTML = CLASSIC16.map(function (c) {
      const active = c === state.fg ? " msp-pal-swatch--fg" : "";
      return '<button type="button" class="msp-pal-swatch' + active + '" data-color="' + c + '" style="background:' + c + '" title="' + c + '"></button>';
    }).join("");
    grid.querySelectorAll("[data-color]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.fg = btn.dataset.color;
        $("msp-fg").value = state.fg;
        renderPalette();
      });
    });
  }

  function pos(ev) {
    const r = canvas.getBoundingClientRect();
    const scaleX = canvas.width / r.width;
    const scaleY = canvas.height / r.height;
    return {
      x: Math.floor((ev.clientX - r.left) * scaleX),
      y: Math.floor((ev.clientY - r.top) * scaleY),
    };
  }

  function strokeAt(p) {
    ctx.lineWidth = state.size;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = state.tool === "eraser" ? state.bg : state.fg;
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  }

  function floodFill(x, y) {
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const d = img.data;
    const w = canvas.width;
    const h = canvas.height;
    const idx = (y * w + x) * 4;
    const tr = d[idx], tg = d[idx + 1], tb = d[idx + 2], ta = d[idx + 3];
    const fr = parseInt(state.fg.slice(1, 3), 16);
    const fg = parseInt(state.fg.slice(3, 5), 16);
    const fb = parseInt(state.fg.slice(5, 7), 16);
    if (tr === fr && tg === fg && tb === fb) return;
    const stack = [[x, y]];
    const seen = new Set();
    while (stack.length) {
      const [cx, cy] = stack.pop();
      const key = cx + "," + cy;
      if (seen.has(key) || cx < 0 || cy < 0 || cx >= w || cy >= h) continue;
      seen.add(key);
      const i = (cy * w + cx) * 4;
      if (d[i] !== tr || d[i + 1] !== tg || d[i + 2] !== tb || d[i + 3] !== ta) continue;
      d[i] = fr; d[i + 1] = fg; d[i + 2] = fb; d[i + 3] = 255;
      stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
    ctx.putImageData(img, 0, 0);
  }

  function drawShape(end) {
    if (!state.snapshot) return;
    ctx.putImageData(state.snapshot, 0, 0);
    ctx.strokeStyle = state.fg;
    ctx.fillStyle = state.fg;
    ctx.lineWidth = state.size;
    const s = state.start;
    if (state.tool === "line") {
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
    } else if (state.tool === "rect") {
      ctx.strokeRect(s.x, s.y, end.x - s.x, end.y - s.y);
    } else if (state.tool === "ellipse") {
      const rx = Math.abs(end.x - s.x) / 2;
      const ry = Math.abs(end.y - s.y) / 2;
      const cx = (s.x + end.x) / 2;
      const cy = (s.y + end.y) / 2;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx || 1, ry || 1, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  function onPointerDown(ev) {
    ev.preventDefault();
    const p = pos(ev);
    if (state.tool === "pick") {
      const px = ctx.getImageData(p.x, p.y, 1, 1).data;
      state.fg = "#" + [px[0], px[1], px[2]].map(function (n) { return n.toString(16).padStart(2, "0"); }).join("");
      $("msp-fg").value = state.fg;
      renderPalette();
      setStatus("Picked color");
      return;
    }
    if (state.tool === "fill") {
      pushUndo();
      floodFill(p.x, p.y);
      setStatus("Fill");
      return;
    }
    pushUndo();
    state.drawing = true;
    state.start = p;
    if (state.tool === "line" || state.tool === "rect" || state.tool === "ellipse") {
      state.snapshot = ctx.getImageData(0, 0, canvas.width, canvas.height);
      return;
    }
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    strokeAt(p);
  }

  function onPointerMove(ev) {
    if (!state.drawing) return;
    const p = pos(ev);
    if (state.tool === "line" || state.tool === "rect" || state.tool === "ellipse") {
      drawShape(p);
      return;
    }
    strokeAt(p);
  }

  function onPointerUp(ev) {
    if (!state.drawing) return;
    state.drawing = false;
    state.snapshot = null;
    if (state.tool === "line" || state.tool === "rect" || state.tool === "ellipse") {
      drawShape(pos(ev));
    }
    ctx.beginPath();
  }

  function canvasToPcxB64() {
    const w = canvas.width;
    const h = canvas.height;
    const img = ctx.getImageData(0, 0, w, h);
    const pal = CLASSIC16.map(function (hex) {
      return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
    });
    function nearest(r, g, b) {
      let best = 0, dist = 1e9;
      pal.forEach(function (p, i) {
        const d = (r - p[0]) ** 2 + (g - p[1]) ** 2 + (b - p[2]) ** 2;
        if (d < dist) { dist = d; best = i; }
      });
      return best;
    }
    const pixels = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        pixels[y * w + x] = nearest(img.data[i], img.data[i + 1], img.data[i + 2]);
      }
    }
    const header = new Uint8Array(128);
    header[0] = 10; header[1] = 5; header[2] = 1; header[3] = 1;
    header[4] = 0; header[5] = 0; header[8] = w & 255; header[9] = (w >> 8) & 255;
    header[10] = h & 255; header[11] = (h >> 8) & 255;
    header[12] = 0; header[13] = 0; header[14] = w & 255; header[15] = (w >> 8) & 255;
    header[16] = h & 255; header[17] = (h >> 8) & 255;
    header[65] = 8;
    const palBlock = new Uint8Array(768);
    pal.forEach(function (p, i) {
      palBlock[i * 3] = p[0]; palBlock[i * 3 + 1] = p[1]; palBlock[i * 3 + 2] = p[2];
    });
    const rle = [];
    let i = 0;
    while (i < pixels.length) {
      let run = 1;
      while (i + run < pixels.length && run < 63 && pixels[i + run] === pixels[i]) run++;
      if (run > 1 || (pixels[i] & 0xc0) === 0xc0) {
        rle.push(0xc0 | run, pixels[i]);
        i += run;
      } else {
        let raw = [];
        while (i < pixels.length && raw.length < 63 && !((pixels[i] & 0xc0) === 0xc0)) {
          raw.push(pixels[i++]);
        }
        if (raw.length) rle.push(raw.length, ...raw);
      }
    }
    rle.push(0);
    const body = new Uint8Array(header.length + palBlock.length + rle.length);
    body.set(header, 0);
    body.set(palBlock, 128);
    body.set(new Uint8Array(rle), 128 + 768);
    let bin = "";
    body.forEach(function (b) { bin += String.fromCharCode(b); });
    return btoa(bin);
  }

  async function api(body) {
    const fetchFn = global.FieldSovereignBus?.fetch || fetch;
    const r = await fetchFn(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    return r.json();
  }

  async function savePcx() {
    const name = prompt("Save as (PCX)", "drawing") || "drawing";
    const pcx_b64 = canvasToPcxB64();
    const doc = await api({ action: "save_pcx", name: name, pcx_b64: pcx_b64 });
    setStatus(doc.ok ? "Saved " + (doc.name || "PCX") : "Save failed");
  }

  async function copyToClipboard() {
    try {
      const blob = await new Promise(function (res) { canvas.toBlob(res, "image/png"); });
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      setStatus("Copied to clipboard");
    } catch (e) {
      setStatus("Copy failed — use File → Save PCX");
    }
  }

  async function pasteFromClipboard() {
    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith("image/")) {
            const blob = await item.getType(type);
            const url = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = function () {
              pushUndo();
              ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
              URL.revokeObjectURL(url);
              setStatus("Pasted image");
            };
            img.src = url;
            return;
          }
        }
      }
      if (global.NexusClipboardWire?.pasteMedia) {
        await global.NexusClipboardWire.pasteMedia();
        setStatus("Paste from vault");
      }
    } catch (_) {
      setStatus("Paste — Ctrl+V or clipboard flyout");
    }
  }

  function showMenu(kind, anchor) {
    const drop = $("msp-dropdown");
    if (!drop) return;
    const menus = {
      file: [
        { label: "New", fn: clearCanvas },
        { label: "Paste from clipboard", fn: pasteFromClipboard },
        { label: "Save PCX…", fn: savePcx },
        { label: "Copy to clipboard", fn: copyToClipboard },
      ],
      edit: [
        { label: "Undo", fn: undo },
        { label: "Clear", fn: clearCanvas },
      ],
      view: [{ label: "Actual size", fn: function () { setStatus(canvas.width + "×" + canvas.height); } }],
      image: [{ label: "Clear image", fn: clearCanvas }],
      colors: [{ label: "Swap colors", fn: function () {
        const t = state.fg; state.fg = state.bg; state.bg = t;
        $("msp-fg").value = state.fg; $("msp-bg").value = state.bg;
        renderPalette();
      }}],
      help: [{ label: "DOS 4.0: load-module mspaint", fn: function () { setStatus("GNU Terminal · modules · load-module mspaint"); } }],
    };
    const items = menus[kind] || [];
    drop.innerHTML = items.map(function (it, i) {
      return '<button type="button" data-idx="' + i + '">' + esc(it.label) + "</button>";
    }).join("");
    const r = anchor.getBoundingClientRect();
    drop.style.left = r.left + "px";
    drop.style.top = r.bottom + 2 + "px";
    drop.hidden = false;
    drop.querySelectorAll("button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        drop.hidden = true;
        items[parseInt(btn.dataset.idx, 10)]?.fn?.();
      });
    });
  }

  function bindUi() {
    document.querySelectorAll(".msp-tool").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.tool = btn.dataset.tool;
        document.querySelectorAll(".msp-tool").forEach(function (b) { b.classList.remove("msp-tool--active"); });
        btn.classList.add("msp-tool--active");
        setStatus("Tool: " + state.tool);
      });
    });
    $("msp-brush-size")?.addEventListener("input", function (ev) {
      state.size = parseInt(ev.target.value, 10) || 2;
    });
    $("msp-fg")?.addEventListener("input", function (ev) {
      state.fg = ev.target.value;
      renderPalette();
    });
    $("msp-bg")?.addEventListener("input", function (ev) {
      state.bg = ev.target.value;
    });
    document.querySelectorAll(".msp-menu-btn").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        showMenu(btn.dataset.menu, btn);
        ev.stopPropagation();
      });
    });
    document.addEventListener("click", function () {
      const drop = $("msp-dropdown");
      if (drop) drop.hidden = true;
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.ctrlKey && ev.key === "z") { ev.preventDefault(); undo(); }
      if (ev.ctrlKey && ev.key === "v") { ev.preventDefault(); pasteFromClipboard(); }
      if (ev.ctrlKey && ev.key === "s") { ev.preventDefault(); savePcx(); }
    });
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointerleave", onPointerUp);
  }

  function refreshSovereign() {
    const chip = $("msp-sovereign");
    const fetchFn = global.FieldSovereignBus?.fetch || fetch;
    fetchFn("/api/sovereign-time", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (doc) {
        if (chip) chip.textContent = (doc.derived_utc || "…").slice(11, 19);
      })
      .catch(function () {});
  }

  async function init() {
    canvas = $("msp-canvas");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
    ctx.fillStyle = state.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    renderPalette();
    bindUi();
    refreshSovereign();
    setInterval(refreshSovereign, 5000);
    try {
      const doc = await api({ action: "status" });
      if (doc.ok) setStatus("MSPaint ready · " + (doc.formats || []).join(" · "));
    } catch (_) {
      setStatus("MSPaint ready");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();