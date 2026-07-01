/**
 * Field material discernment — polar sector map colored by inferred path materials.
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function drawPolarMap(canvas, sectors, legend) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 320;
    const h = canvas.clientHeight || 280;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) * 0.42;

    ctx.fillStyle = "#040810";
    ctx.fillRect(0, 0, w, h);

    for (let ring = 4; ring >= 1; ring--) {
      ctx.beginPath();
      ctx.arc(cx, cy, (r * ring) / 4, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(136, 200, 255, 0.08)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    (sectors || []).forEach((s) => {
      const start = ((s.bearing_deg || 0) - (s.width_deg || 45) / 2 - 90) * (Math.PI / 180);
      const end = start + ((s.width_deg || 45) * Math.PI) / 180;
      const alpha = 0.35 + Math.min(0.55, (s.confidence || 0) * 0.55);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, end);
      ctx.closePath();
      ctx.fillStyle = s.color || "#5a6070";
      ctx.globalAlpha = s.source_count ? alpha : 0.12;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "rgba(248, 251, 255, 0.15)";
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#88c8ff";
    ctx.fill();
    ctx.font = "10px ui-monospace, monospace";
    ctx.fillStyle = "#c8d6ea";
    ctx.fillText("YOU", cx + 8, cy + 4);

    ctx.fillStyle = "#88c8ff";
    ctx.fillText("N", cx - 3, cy - r - 8);
    ctx.fillText("E", cx + r + 6, cy + 4);
    ctx.fillText("S", cx - 3, cy + r + 14);
    ctx.fillText("W", cx - r - 14, cy + 4);

    if (legend) {
      const keys = Object.keys(legend);
      let lx = 10;
      let ly = h - 10 - keys.length * 14;
      keys.forEach((k) => {
        const item = legend[k];
        ctx.fillStyle = item.color || "#5a6070";
        ctx.fillRect(lx, ly, 10, 10);
        ctx.fillStyle = "#c8d6ea";
        ctx.fillText(item.label || k, lx + 14, ly + 9);
        ly += 14;
      });
    }
  }

  function renderMaterialField(mf, scanMaterial) {
    const wrap = document.getElementById("field-rf-material-wrap");
    const meta = document.getElementById("field-rf-material-meta");
    const table = document.getElementById("field-rf-material-table");
    const canvas = document.getElementById("field-rf-material-map");
    if (!wrap) return;

    if (!mf?.sectors?.length) {
      wrap.style.display = "none";
      return;
    }
    wrap.style.display = "";

    const st = mf.stats || {};
    if (meta) {
      meta.innerHTML = [
        esc(mf.tagline || ""),
        st.dominant_material ? `dominant <strong style="color:${esc((mf.legend || {})[st.dominant_material]?.color || "#8a8a8a")}">${esc(st.dominant_material)}</strong>` : "",
        st.dominant_bearing_deg != null ? `@ ${st.dominant_bearing_deg}°` : "",
        `interference ${st.mean_interference ?? "—"}`,
        `fall-off ${st.mean_falloff_db ?? "—"} dB/dec`,
        `${st.classified_sectors ?? 0}/${st.active_sectors ?? 0} sectors`,
      ].filter(Boolean).join(" · ");
    }

    drawPolarMap(canvas, mf.sectors, mf.legend);

    if (table) {
      const rows = (mf.sectors || []).filter((s) => s.source_count > 0);
      table.innerHTML = rows.length
        ? `<table class="honor-table"><thead><tr>
            <th>Bearing</th><th>Material</th><th>Conf</th><th>Interference</th><th>Fall-off</th><th>Sources</th><th>Top AP</th>
          </tr></thead><tbody>
          ${rows.map((s) => {
            const top = (s.top_sources || [])[0];
            return `<tr>
              <td>${esc(s.bearing_deg)}°</td>
              <td><span class="fm-swatch" style="background:${esc(s.color)}"></span> ${esc(s.label || s.material)}</td>
              <td>${Math.round((s.confidence || 0) * 100)}%</td>
              <td>${esc(s.interference)}</td>
              <td>${s.falloff_db != null ? esc(s.falloff_db) + " dB" : "—"}</td>
              <td>${esc(s.source_count)}</td>
              <td>${top ? esc(`${top.ssid || "?"} · ${top.signal_dbm || "?"}%`) : "—"}</td>
            </tr>`;
          }).join("")}
          </tbody></table>`
        : '<div class="empty">Scan cycle needed — passive RF will classify sector materials.</div>';
    }

    const scanEl = document.getElementById("field-rf-material-scan");
    if (scanEl && scanMaterial?.length) {
      const colored = scanMaterial.filter((a) => a.path_material);
      scanEl.innerHTML = colored.length
        ? `<table class="honor-table"><thead><tr>
            <th>SSID</th><th>Signal</th><th>Band</th><th>Material</th><th>Bearing</th><th>Interference</th>
          </tr></thead><tbody>
          ${colored.slice(0, 40).map((a) => `<tr>
            <td>${esc(a.ssid)}</td>
            <td>${esc(a.signal_dbm)}%</td>
            <td>${esc(a.band)}</td>
            <td><span class="fm-swatch" style="background:${esc(a.path_color || "#5a6070")}"></span> ${esc(a.path_material)}</td>
            <td>${a.path_bearing_deg != null ? esc(a.path_bearing_deg) + "°" : "—"}</td>
            <td>${a.path_interference != null ? esc(Number(a.path_interference).toFixed(2)) : "—"}</td>
          </tr>`).join("")}
          </tbody></table>`
        : "";
    }
  }

  global.renderMaterialField = renderMaterialField;
})(window);