/**
 * NEXUS Precision Spiderweb — sub-micron canvas web at detected GPS coordinates.
 */
(function (global) {
  "use strict";

  let pfData = null;
  let anim = null;
  const web = { canvas: null, ctx: null, mode: "global", viewport: null };

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  function parseNm(v) {
    try {
      return Number(parseInt(String(v || "0"), 10));
    } catch {
      return 0;
    }
  }

  function entityById(id) {
    return (pfData?.entities || []).find((e) => e.id === id);
  }

  function projectGlobal(e, w, h, bounds) {
    const lat = Number(e.lat);
    const lon = Number(e.lon);
    const x = ((lon - bounds.west) / (bounds.east - bounds.west)) * w;
    const y = ((bounds.north - lat) / (bounds.north - bounds.south)) * h;
    return { x, y };
  }

  function projectLocal(e, w, h, extentNm) {
    const ex = parseNm(e.enu_e_nm);
    const ny = parseNm(e.enu_n_nm);
    const x = ((ex + extentNm) / (2 * extentNm)) * w;
    const y = ((extentNm - ny) / (2 * extentNm)) * h;
    return { x, y };
  }

  function computeBounds(entities) {
    let north = -90, south = 90, east = -180, west = 180;
    entities.forEach((e) => {
      const lat = Number(e.lat);
      const lon = Number(e.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      north = Math.max(north, lat);
      south = Math.min(south, lat);
      east = Math.max(east, lon);
      west = Math.min(west, lon);
    });
    const padLat = Math.max(0.002, (north - south) * 0.15);
    const padLon = Math.max(0.002, (east - west) * 0.15);
    return {
      north: north + padLat,
      south: south - padLat,
      east: east + padLon,
      west: west - padLon,
    };
  }

  function resizeCanvas() {
    const wrap = document.getElementById("precision-web-canvas-wrap");
    if (!web.canvas || !wrap) return;
    const rect = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    web.canvas.width = Math.max(320, Math.floor(rect.width * dpr));
    web.canvas.height = Math.max(240, Math.floor(rect.height * dpr));
    web.canvas.style.width = `${rect.width}px`;
    web.canvas.style.height = `${rect.height}px`;
    if (web.ctx) web.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawWeb(viewport) {
    if (!web.ctx || !pfData) return;
    resizeCanvas();
    const rect = web.canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const ctx = web.ctx;
    const vp = viewport || web.viewport?.state || { scale: 1, panX: 0, panY: 0 };
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#03060c";
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(vp.panX, vp.panY);
    ctx.scale(vp.scale, vp.scale);
    const ox = (w * (1 - 1 / vp.scale)) * 0.5;
    const oy = (h * (1 - 1 / vp.scale)) * 0.5;
    ctx.translate(-ox, -oy);

    const entities = (pfData.entities || []).filter((e) => e.lat != null);
    const bounds = computeBounds(entities);
    const extentNm = 20 * 1e6;
    const project = web.mode === "local"
      ? (e) => projectLocal(e, w, h, extentNm)
      : (e) => projectGlobal(e, w, h, bounds);

    const pos = {};
    entities.forEach((e) => {
      pos[e.id] = project(e);
    });

    (pfData.edges || []).forEach((edge) => {
      const a = pos[edge.from];
      const b = pos[edge.to];
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = edge.kind === "terror" ? "rgba(255,74,90,0.82)" : edge.kind === "neighbor" ? "rgba(74,232,154,0.58)" : "rgba(114,184,255,0.55)";
      ctx.lineWidth = edge.kind === "terror" ? 1.8 : 1.2;
      ctx.setLineDash(edge.kind === "terror" ? [] : [4, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    entities.forEach((e) => {
      const p = pos[e.id];
      if (!p) return;
      const r = e.kind === "terror" || e.kind === "hostile" ? 5 : 4;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = e.kind === "terror" ? "#ff3a4a" : e.section === "home" ? "#e8c04a" : "#72b8ff";
      ctx.fill();
      ctx.strokeStyle = "rgba(242,246,252,0.9)";
      ctx.lineWidth = 1;
      ctx.stroke();
      if (web.mode === "local" && (Math.abs(parseNm(e.enu_e_nm)) < 50000 || Math.abs(parseNm(e.enu_n_nm)) < 50000)) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 12, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(232,192,74,0.4)";
        ctx.lineWidth = 0.6;
        ctx.stroke();
      }
    });

    if (web.mode === "local") {
      const cx = w / 2;
      const cy = h / 2;
      ctx.strokeStyle = "rgba(232,192,74,0.55)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - 8, cy);
      ctx.lineTo(cx + 8, cy);
      ctx.moveTo(cx, cy - 8);
      ctx.lineTo(cx, cy + 8);
      ctx.stroke();
    }
    ctx.restore();
  }

  function renderMeta() {
    const meta = document.getElementById("precision-web-meta");
    const table = document.getElementById("precision-web-table");
    const s = pfData?.stats || {};
    if (meta) {
      meta.textContent = [
        "Sub-micron spiderweb edges at detected GPS",
        `${s.edges ?? 0} edges`,
        `${s.sub_micron ?? 0} sub-µm nodes`,
        web.mode === "local" ? "LOCAL ENU nm view" : "GLOBAL WGS84 view",
      ].join(" · ");
    }
    if (table) {
      const rows = (pfData?.entities || []).slice(0, 120);
      table.innerHTML = rows.length
        ? `<table class="honor-table"><thead><tr>
            <th>ID</th><th>Label</th><th>lat (15dp)</th><th>lon (15dp)</th><th>ENU E</th><th>ENU N</th><th>Section</th>
          </tr></thead><tbody>
          ${rows.map((r) => `<tr>
            <td>${esc(r.id)}</td>
            <td>${esc(r.label)}</td>
            <td><code>${esc(r.lat_str || r.lat)}</code></td>
            <td><code>${esc(r.lon_str || r.lon)}</code></td>
            <td>${esc(r.enu_e_nm)}</td>
            <td>${esc(r.enu_n_nm)}</td>
            <td>${esc(r.section || r.kind)}</td>
          </tr>`).join("")}
          </tbody></table>`
        : '<div class="empty">Rebuild precision field to draw spiderweb.</div>';
    }
  }

  function setWebMode(next) {
    web.mode = next;
    document.querySelectorAll(".pf-web-tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.pfWeb === next);
    });
    web.viewport?.reset?.();
    drawWeb();
    renderMeta();
  }

  function renderPrecisionSpiderweb(data) {
    pfData = data || pfData;
    if (!pfData) return;
    const wrap = document.getElementById("precision-web-canvas-wrap");
    if (!wrap) return;
    if (!web.canvas) {
      web.canvas = document.getElementById("precision-web-canvas");
      web.ctx = web.canvas?.getContext("2d");
      if (!wrap.querySelector(".nexus-canvas-hint")) {
        const hint = document.createElement("span");
        hint.className = "nexus-canvas-hint";
        hint.textContent = "Scroll zoom · drag pan";
        wrap.appendChild(hint);
      }
      if (global.NexusMap?.bindCanvasZoomPan) {
        web.viewport = global.NexusMap.bindCanvasZoomPan(web.canvas, wrap, drawWeb);
      }
      window.addEventListener("resize", () => drawWeb());
    }
    renderMeta();
    drawWeb();
  }

  function bindControls() {
    document.querySelectorAll(".pf-web-tab").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => setWebMode(btn.dataset.pfWeb || "global"));
    });
    document.getElementById("precision-web-rebuild")?.addEventListener("click", async () => {
      const res = await fetch("/api/precision-field/rebuild", { method: "POST" });
      renderPrecisionSpiderweb(await res.json());
    });
  }

  function invalidatePrecisionSpiderweb() {
    drawWeb();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindControls);
  } else {
    bindControls();
  }

  global.renderPrecisionSpiderweb = renderPrecisionSpiderweb;
  global.invalidatePrecisionSpiderweb = invalidatePrecisionSpiderweb;
})(window);