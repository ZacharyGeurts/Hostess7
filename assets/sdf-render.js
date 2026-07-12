/**
 * NEXUS SDF Map Renderer — crisp pointy pins + globe from compact R8 distance fields.
 * Anchor at pin tip = geo-accurate placement on Leaflet lat/lon.
 */
(function (global) {
  "use strict";

  const cache = new Map();
  const activePulses = new WeakMap();
  let manifest = null;

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function parseColor(input) {
    if (!input) return [61, 214, 140, 255];
    if (input.startsWith("#") && input.length >= 7) {
      return [
        parseInt(input.slice(1, 3), 16),
        parseInt(input.slice(3, 5), 16),
        parseInt(input.slice(5, 7), 16),
        255,
      ];
    }
    const m = input.match(/hsl\(\s*([0-9.]+)\s*,\s*([0-9.]+)%\s*,\s*([0-9.]+)%\s*\)/i);
    if (m) {
      const h = Number(m[1]) / 360;
      const s = Number(m[2]) / 100;
      const l = Number(m[3]) / 100;
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      return [
        Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
        Math.round(hue2rgb(p, q, h) * 255),
        Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
        255,
      ];
    }
    return [61, 214, 140, 255];
  }

  function stopPulse(wrap) {
    const id = activePulses.get(wrap);
    if (id) cancelAnimationFrame(id);
    activePulses.delete(wrap);
  }

  async function loadManifest() {
    if (manifest) return manifest;
    const res = await fetch("/assets/sdf/manifest.json");
    manifest = await res.json();
    return manifest;
  }

  async function loadField(assetId) {
    if (cache.has(assetId)) return cache.get(assetId);
    const man = await loadManifest();
    const meta = man.assets[assetId];
    if (!meta) throw new Error(`SDF asset missing: ${assetId}`);
    const img = new Image();
    img.crossOrigin = "anonymous";
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = meta.file;
    });
    const c = document.createElement("canvas");
    c.width = meta.width;
    c.height = meta.height;
    const ctx = c.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, meta.width, meta.height).data;
    const field = new Float32Array(meta.width * meta.height);
    for (let i = 0, j = 0; i < data.length; i += 4, j++) {
      field[j] = (data[i] - 128) / 64;
    }
    const pack = { meta, field };
    cache.set(assetId, pack);
    return pack;
  }

  function sampleField(field, w, h, u, v) {
    const x = clamp(u, 0, 1) * (w - 1);
    const y = clamp(v, 0, 1) * (h - 1);
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const x1 = Math.min(x0 + 1, w - 1);
    const y1 = Math.min(y0 + 1, h - 1);
    const tx = x - x0;
    const ty = y - y0;
    const i00 = y0 * w + x0;
    const i10 = y0 * w + x1;
    const i01 = y1 * w + x0;
    const i11 = y1 * w + x1;
    return (
      field[i00] * (1 - tx) * (1 - ty) +
      field[i10] * tx * (1 - ty) +
      field[i01] * (1 - tx) * ty +
      field[i11] * tx * ty
    );
  }

  function renderSdf(canvas, pack, color, opts) {
    const { meta, field } = pack;
    const scale = opts.scale || meta.display_scale || 1;
    const w = Math.round(meta.width * scale);
    const h = Math.round(meta.height * scale);
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(w, h);
    const rgba = parseColor(color);
    const glow = opts.glow !== false;
    const alphaBoost = opts.alphaBoost || 1;
    const edge = opts.edge || 0.04;

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const u = (x + 0.5) / w;
        const v = (y + 0.5) / h;
        const d = sampleField(field, meta.width, meta.height, u, v);
        const aa = clamp(0.5 - d / edge, 0, 1);
        const glowAmt = glow ? clamp(0.22 - d * 0.35, 0, 0.55) : 0;
        const idx = (y * w + x) * 4;
        const a = clamp((aa + glowAmt) * alphaBoost, 0, 1);
        img.data[idx] = rgba[0];
        img.data[idx + 1] = rgba[1];
        img.data[idx + 2] = rgba[2];
        img.data[idx + 3] = Math.round(a * 255);
      }
    }
    ctx.putImageData(img, 0, 0);
    return { width: w, height: h, anchor: meta.anchor.map((n) => Math.round(n * scale)) };
  }

  async function renderPin(canvas, opts) {
    const killed = !!opts.killed;
    const friendly = !!opts.friendly;
    const assetId = killed ? "pin-killed" : friendly ? "pin-friendly" : "pin-hostile";
    const pack = await loadField(assetId);
    const color = opts.color || (killed ? "#556677" : friendly ? "#3dd68c" : "#ff5c3a");
    return renderSdf(canvas, pack, color, {
      scale: opts.scale || pack.meta.display_scale,
      glow: !killed,
      alphaBoost: opts.heat ? 0.85 + clamp(opts.heat, 0, 1) * 0.35 : 1,
    });
  }

  async function renderRing(canvas, color, scale, phase) {
    const pack = await loadField("ring-pulse");
    return renderSdf(canvas, pack, color, {
      scale: (scale || 1) * (1 + (phase || 0) * 0.35),
      glow: true,
      edge: 0.06,
      alphaBoost: 0.55 * (1 - (phase || 0)),
    });
  }

  function tempToRgb(norm) {
    const t = clamp(norm, 0, 1);
    const r = clamp(Math.round(30 + t * 225), 0, 255);
    const g = clamp(Math.round(40 + (1 - Math.abs(t - 0.5) * 2) * 120 + t * 40), 0, 255);
    const b = clamp(Math.round(220 - t * 200), 0, 255);
    return [r, g, b, 255];
  }

  function sampleThermalNorm(thermalPack, u, v) {
    const { meta, field } = thermalPack;
    const raw = sampleField(field, meta.width, meta.height, u, v);
    return clamp((raw + 2) / 4, 0, 1);
  }

  async function renderThermalTile(canvas, size, x, y, z, opts) {
    const thermalPack = await loadField("earth-thermal");
    const landPack = await loadField("globe-world");
    const wirePack = await loadField("globe-wireframe");
    const b = tileLonLatBounds(x, y, z);
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(size, size);
    const alphaLand = opts?.alphaLand ?? 0.35;
    for (let py = 0; py < size; py++) {
      for (let px = 0; px < size; px++) {
        const lon = b.lonMin + ((px + 0.5) / size) * (b.lonMax - b.lonMin);
        const lat = b.latMax - ((py + 0.5) / size) * (b.latMax - b.latMin);
        const u = (lon + 180) / 360;
        const v = (90 - lat) / 180;
        const norm = sampleThermalNorm(thermalPack, u, v);
        const rgba = tempToRgb(norm);
        const dLand = sampleField(landPack.field, landPack.meta.width, landPack.meta.height, u, v);
        const dWire = sampleField(wirePack.field, wirePack.meta.width, wirePack.meta.height, u, v);
        const land = clamp(0.5 - dLand * 1.4, 0, 1);
        const border = clamp(0.42 - Math.abs(dWire) * 3.0, 0, 1);
        const idx = (py * size + px) * 4;
        img.data[idx] = Math.round(rgba[0] * (0.82 + land * alphaLand));
        img.data[idx + 1] = Math.round(rgba[1] * (0.82 + land * alphaLand));
        img.data[idx + 2] = Math.round(rgba[2] * (0.82 + land * alphaLand));
        img.data[idx + 3] = 255;
        if (border > 0.2) {
          img.data[idx] = Math.min(255, img.data[idx] + Math.round(border * 40));
          img.data[idx + 1] = Math.min(255, img.data[idx + 1] + Math.round(border * 55));
          img.data[idx + 2] = Math.min(255, img.data[idx + 2] + Math.round(border * 70));
        }
      }
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  async function renderThermalGlobe3D(canvas, w, h, opts) {
    const thermalPack = await loadField("earth-thermal");
    const landPack = await loadField("globe-world");
    const wirePack = await loadField("globe-wireframe");
    const phase = (opts?.phase || 0) * Math.PI * 2;
    const tilt = (opts?.tilt ?? 0.32) * Math.PI;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#040810";
    ctx.fillRect(0, 0, w, h);
    const cx = w * 0.5;
    const cy = h * 0.52;
    const radius = Math.min(w, h) * 0.38;
    const img = ctx.createImageData(w, h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const dx = (x - cx) / radius;
        const dy = (y - cy) / radius;
        const r2 = dx * dx + dy * dy;
        const idx = (y * w + x) * 4;
        if (r2 > 1) {
          img.data[idx + 3] = 255;
          continue;
        }
        const dz = Math.sqrt(Math.max(0, 1 - r2));
        const lat = Math.asin(clamp(dy * Math.cos(tilt) + dz * Math.sin(tilt), -1, 1));
        const lon = Math.atan2(dx, dz * Math.cos(tilt) - dy * Math.sin(tilt)) + phase;
        const u = (lon / Math.PI / 2 + 0.5) % 1;
        const v = (90 - (lat * 180 / Math.PI)) / 180;
        const norm = sampleThermalNorm(thermalPack, u, v);
        const rgba = tempToRgb(norm);
        const dLand = sampleField(landPack.field, landPack.meta.width, landPack.meta.height, u, v);
        const dWire = sampleField(wirePack.field, wirePack.meta.width, wirePack.meta.height, u, v);
        const land = clamp(0.55 - dLand * 1.6, 0, 1);
        const border = clamp(0.38 - Math.abs(dWire) * 3.0, 0, 1);
        const shade = 0.55 + dz * 0.45;
        img.data[idx] = Math.round(rgba[0] * shade + land * 18 + border * 35);
        img.data[idx + 1] = Math.round(rgba[1] * shade + land * 28 + border * 55);
        img.data[idx + 2] = Math.round(rgba[2] * shade + land * 38 + border * 75);
        img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    const grad = ctx.createRadialGradient(cx - radius * 0.25, cy - radius * 0.25, radius * 0.1, cx, cy, radius * 1.05);
    grad.addColorStop(0, "rgba(120,200,255,0.12)");
    grad.addColorStop(1, "rgba(0,0,0,0.45)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
    return canvas;
  }

  function createThermalGlobeLayer(Lref) {
    const GridLayer = Lref.GridLayer.extend({
      createTile(coords, done) {
        const tile = document.createElement("canvas");
        const size = this.getTileSize().x;
        renderThermalTile(tile, size, coords.x, coords.y, coords.z)
          .then(() => done(null, tile))
          .catch((err) => done(err, tile));
        return tile;
      },
    });
    return new GridLayer({
      tileSize: 256,
      minZoom: 0,
      maxZoom: 22,
      noWrap: false,
      className: "ha-thermal-tile-layer",
    });
  }

  function tileLonLatBounds(x, y, z) {
    const n = Math.pow(2, z);
    const lonMin = (x / n) * 360 - 180;
    const lonMax = ((x + 1) / n) * 360 - 180;
    const latRad1 = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)));
    const latRad2 = Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 1)) / n)));
    const latMax = (latRad1 * 180) / Math.PI;
    const latMin = (latRad2 * 180) / Math.PI;
    return { lonMin, lonMax, latMin, latMax };
  }

  async function renderGlobeTile(canvas, size, x, y, z) {
    const landPack = await loadField("globe-world");
    const wirePack = await loadField("globe-wireframe");
    const lw = landPack.meta.width;
    const lh = landPack.meta.height;
    const ww = wirePack.meta.width;
    const wh = wirePack.meta.height;
    const b = tileLonLatBounds(x, y, z);
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    const img = ctx.createImageData(size, size);
    for (let py = 0; py < size; py++) {
      for (let px = 0; px < size; px++) {
        const lon = b.lonMin + ((px + 0.5) / size) * (b.lonMax - b.lonMin);
        const lat = b.latMax - ((py + 0.5) / size) * (b.latMax - b.latMin);
        const u = (lon + 180) / 360;
        const v = (90 - lat) / 180;
        const dLand = sampleField(landPack.field, lw, lh, u, v);
        const dWire = sampleField(wirePack.field, ww, wh, u, v);
        const land = clamp(0.5 - dLand * 1.6, 0, 1);
        const border = clamp(0.42 - Math.abs(dWire) * 3.2, 0, 1);
        const idx = (py * size + px) * 4;
        img.data[idx] = Math.round(6 + land * 18 + border * 40);
        img.data[idx + 1] = Math.round(12 + land * 32 + border * 95);
        img.data[idx + 2] = Math.round(22 + land * 48 + border * 120);
        img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  async function renderGlobe(canvas, w, h) {
    const landPack = await loadField("globe-world");
    const wirePack = await loadField("globe-wireframe");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#060a14";
    ctx.fillRect(0, 0, w, h);
    const img = ctx.createImageData(w, h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const u = (x + 0.5) / w;
        const v = (y + 0.5) / h;
        const dLand = sampleField(landPack.field, landPack.meta.width, landPack.meta.height, u, v);
        const dWire = sampleField(wirePack.field, wirePack.meta.width, wirePack.meta.height, u, v);
        const land = clamp(0.55 - dLand * 1.8, 0, 1);
        const border = clamp(0.38 - Math.abs(dWire) * 3.0, 0, 1);
        const idx = (y * w + x) * 4;
        img.data[idx] = Math.round(6 + land * 22 + border * 35);
        img.data[idx + 1] = Math.round(12 + land * 38 + border * 88);
        img.data[idx + 2] = Math.round(20 + land * 52 + border * 110);
        img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  function createGlobeLayer(Lref) {
    const GridLayer = Lref.GridLayer.extend({
      createTile(coords, done) {
        const tile = document.createElement("canvas");
        const size = this.getTileSize().x;
        renderGlobeTile(tile, size, coords.x, coords.y, coords.z)
          .then(() => done(null, tile))
          .catch((err) => done(err, tile));
        return tile;
      },
    });
    return new GridLayer({
      tileSize: 256,
      minZoom: 0,
      maxZoom: 22,
      noWrap: false,
      className: "ha-sdf-tile-layer",
    });
  }

  function formatGps(lat, lon) {
    const la = Number(lat);
    const lo = Number(lon);
    if (!Number.isFinite(la) || !Number.isFinite(lo)) return "";
    return `${la.toFixed(5)}°, ${lo.toFixed(5)}°`;
  }

  async function pinIcon(point) {
    const killed = point.target_status === "killed" || point.disabled_permanent;
    const friendly = point.killable === false && !killed;
    const col = point.color || `hsl(${point.hue || 40}, ${point.sat || 70}%, ${point.light || 50}%)`;
    const wrap = document.createElement("div");
    wrap.className = "ha-sdf-marker";
    const pinCanvas = document.createElement("canvas");
    const ringCanvas = document.createElement("canvas");
    ringCanvas.className = "ha-sdf-ring";
    wrap.appendChild(ringCanvas);
    wrap.appendChild(pinCanvas);
    const gps = formatGps(point.lat, point.lon);
    if (gps) {
      const label = document.createElement("div");
      label.className = "ha-sdf-gps";
      label.textContent = gps;
      wrap.appendChild(label);
    }
    const pin = await renderPin(pinCanvas, {
      color: col,
      killed,
      friendly,
      heat: point.heat,
      scale: killed ? 0.88 : 1.12,
    });
    ringCanvas.style.cssText = "position:absolute;left:0;top:0;pointer-events:none;";
    pinCanvas.style.cssText = "position:absolute;left:0;top:0;";
    const ax = pin.anchor[0];
    const ay = pin.anchor[1];
    wrap.style.width = pin.width + "px";
    wrap.style.height = pin.height + "px";
    if (!killed && !friendly) {
      const pack = await loadField("ring-pulse");
      renderSdf(ringCanvas, pack, col, { scale: 1.0, glow: true, edge: 0.06, alphaBoost: 0.45 });
      ringCanvas.style.left = (ax - ringCanvas.width / 2) + "px";
      ringCanvas.style.top = (ay - ringCanvas.height / 2) + "px";
      ringCanvas.style.animation = "ha-sdf-ring-pulse 2s ease-out infinite";
      ringCanvas.style.transformOrigin = `${ringCanvas.width / 2}px ${ringCanvas.height / 2}px`;
    }
    wrap._sdfCleanup = () => stopPulse(wrap);
    return {
      wrap,
      iconSize: [pin.width, pin.height],
      iconAnchor: [ax, ay],
    };
  }

  const NexusSdf = {
    loadManifest,
    loadField,
    renderSdf,
    renderPin,
    renderRing,
    renderGlobe,
    renderGlobeTile,
    createGlobeLayer,
    renderThermalTile,
    renderThermalGlobe3D,
    createThermalGlobeLayer,
    tempToRgb,
    sampleThermalNorm,
    formatGps,
    pinIcon,
    parseColor,
    stopPulse,
    tileLonLatBounds,
  };

  global.NexusSdf = NexusSdf;
})(typeof window !== "undefined" ? window : globalThis);