/**
 * Thermal Earth — SDF temperature top-down + 3D globe, warm/cold body registry.
 */
(function (global) {
  "use strict";

  let thermalData = null;
  let globePhase = 0;
  let globeAnim = null;
  const thermalMap = { map: null, layer: null, markers: null, sdfLayer: null };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function bodyIcon(kind) {
    const col = kind === "warm" ? "#ff5c3a" : kind === "cold" ? "#4d9bff" : "#9aa8be";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14">
      <circle cx="7" cy="7" r="5.5" fill="${col}" fill-opacity="0.9" stroke="#e8ecf4" stroke-width="1.2"/>
    </svg>`;
    return L.divIcon({
      className: `thermal-body-${kind}`,
      html: svg,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
  }

  function ensureThermalMap() {
    const el = document.getElementById("spiderweb-thermal-map");
    if (!el || typeof L === "undefined") return null;
    if (thermalMap.map) return thermalMap.map;
    const mk = global.NexusMap;
    thermalMap.map = mk
      ? mk.create(el, { center: [20, 0], zoom: 2, minZoom: 1, maxZoom: 18 })
      : L.map(el, {
        center: [20, 0], zoom: 2, minZoom: 1, maxZoom: 18,
        worldCopyJump: true, zoomControl: true, scrollWheelZoom: true,
      });
    if (global.NexusSdf?.createThermalGlobeLayer) {
      thermalMap.sdfLayer = NexusSdf.createThermalGlobeLayer(L);
      thermalMap.sdfLayer.addTo(thermalMap.map);
    } else if (global.NexusMap?.fieldGlobeLayer) {
      NexusMap.fieldGlobeLayer(L).addTo(thermalMap.map);
    } else if (global.NexusSdf?.createGlobeLayer) {
      NexusSdf.createGlobeLayer(L).addTo(thermalMap.map);
    }
    thermalMap.markers = L.layerGroup().addTo(thermalMap.map);
    const finish = () => {
      el.classList.remove("host-map-booting");
      el.classList.add("host-map-ready");
      if (mk) mk.scheduleInvalidate(thermalMap.map, el);
      else thermalMap.map.invalidateSize();
    };
    setTimeout(finish, mk ? 60 : 120);
    return thermalMap.map;
  }

  function renderThermalMarkers() {
    if (!thermalMap.markers || !thermalData) return;
    thermalMap.markers.clearLayers();
    (thermalData.bodies || []).forEach((b) => {
      if (b.lat == null || b.lon == null) return;
      const tip = [
        b.label,
        b.kind,
        b.temp_c != null ? `${b.temp_c}°C` : "",
        b.source,
        b.ocr_corroborated ? "OCR ✓" : "",
      ].filter(Boolean).join(" · ");
      thermalMap.markers.addLayer(
        L.marker([b.lat, b.lon], { icon: bodyIcon(b.kind), riseOnHover: true })
          .bindTooltip(tip, { direction: "top" })
      );
    });
  }

  function renderThermalGlobe3D() {
    const canvas = document.getElementById("thermal-globe-3d");
    if (!canvas || !global.NexusSdf?.renderThermalGlobe3D) return;
    const wrap = canvas.parentElement;
    const w = wrap?.clientWidth || 480;
    const h = Math.max(220, wrap?.clientHeight || 280);
    NexusSdf.renderThermalGlobe3D(canvas, w, h, { phase: globePhase, tilt: 0.28 });
  }

  function startGlobeSpin() {
    if (globeAnim) cancelAnimationFrame(globeAnim);
    const tick = () => {
      globePhase = (globePhase + 0.0025) % 1;
      renderThermalGlobe3D();
      globeAnim = requestAnimationFrame(tick);
    };
    globeAnim = requestAnimationFrame(tick);
  }

  function stopGlobeSpin() {
    if (globeAnim) cancelAnimationFrame(globeAnim);
    globeAnim = null;
  }

  function renderThermalMeta() {
    const meta = document.getElementById("thermal-earth-meta");
    const stats = document.getElementById("thermal-earth-stats");
    const table = document.getElementById("thermal-bodies-table");
    const s = thermalData?.stats || {};
    const sdf = thermalData?.sdf || {};
    if (meta) {
      meta.innerHTML = [
        esc(thermalData?.tagline || "Thermal Earth SDF"),
        sdf.temp_min_c != null ? `range ${sdf.temp_min_c}°C – ${sdf.temp_max_c}°C` : "",
        thermalData?.model?.local_now ? `LOCAL NOW: ${esc(thermalData.model.local_now)}` : "",
      ].filter(Boolean).join(" · ");
    }
    if (stats) {
      stats.innerHTML = [
        `<span>Warm <strong style="color:#ff5c3a">${s.warm_bodies ?? 0}</strong></span>`,
        `<span>Cold <strong style="color:#4d9bff">${s.cold_bodies ?? 0}</strong></span>`,
        `<span>Total <strong>${s.total_bodies ?? 0}</strong></span>`,
        `<span>OCR <strong>${s.ocr_warm_cold ?? 0}</strong></span>`,
        `<span>Grid <strong>${s.grid_samples ?? 0}</strong></span>`,
      ].join("");
    }
    if (table) {
      const rows = (thermalData?.bodies || []).slice(0, 200);
      table.innerHTML = rows.length
        ? `<table class="honor-table"><thead><tr>
            <th>Kind</th><th>Label</th><th>Temp °C</th><th>Δ median</th><th>GPS</th><th>Source</th><th>OCR</th>
          </tr></thead><tbody>
          ${rows.map((b) => `<tr>
            <td><span style="color:${b.kind === "warm" ? "#ff5c3a" : b.kind === "cold" ? "#4d9bff" : "#9aa8be"}">${esc(b.kind)}</span></td>
            <td>${esc(b.label)}</td>
            <td>${b.temp_c != null ? esc(b.temp_c) : "—"}</td>
            <td>${b.delta_c != null ? esc(b.delta_c) : "—"}</td>
            <td>${esc(`${b.lat}, ${b.lon}`)}</td>
            <td>${esc(b.source)}</td>
            <td>${b.ocr_corroborated ? '<span class="severity-ok">✓</span>' : "—"}</td>
          </tr>`).join("")}
          </tbody></table>`
        : '<div class="empty">Rebuild thermal field to identify warm and cold bodies.</div>';
    }
  }

  function flyThermalFocus() {
    const op = thermalData?.operator_focus;
    const bodies = thermalData?.bodies || [];
    const warm = bodies.find((b) => b.kind === "warm" && b.lat != null);
    const focus = op || warm || bodies[0];
    if (!focus || !thermalMap.map) return;
    thermalMap.map.flyTo([focus.lat, focus.lon], 5, { duration: 1.1 });
  }

  function renderThermalEarth(data) {
    thermalData = data || thermalData;
    if (!thermalData) return;
    renderThermalMeta();
    ensureThermalMap();
    renderThermalMarkers();
    renderThermalGlobe3D();
    const tab = document.querySelector('.sw-map-tab[data-sw-map="thermal"]');
    if (tab?.classList.contains("active")) {
      startGlobeSpin();
      setTimeout(() => thermalMap.map?.invalidateSize(), 80);
    }
  }

  function bindThermalControls() {
    document.getElementById("thermal-rebuild")?.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/thermal-earth/rebuild", { method: "POST" });
        const doc = await res.json();
        renderThermalEarth(doc);
        if (global.renderTerrorSpiderweb && global.lastPanelData) {
          global.lastPanelData.thermal_earth = doc;
        }
      } catch {
        /* ignore */
      }
    });
    document.getElementById("thermal-refocus")?.addEventListener("click", flyThermalFocus);
    document.querySelector('.sw-map-tab[data-sw-map="thermal"]')?.addEventListener("click", () => {
      setTimeout(() => {
        thermalMap.map?.invalidateSize();
        renderThermalGlobe3D();
        startGlobeSpin();
      }, 100);
    });
    document.querySelectorAll('.sw-map-tab:not([data-sw-map="thermal"])').forEach((btn) => {
      btn.addEventListener("click", stopGlobeSpin);
    });
  }

  function invalidateThermalMap() {
    thermalMap.map?.invalidateSize();
    renderThermalGlobe3D();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindThermalControls);
  } else {
    bindThermalControls();
  }

  global.renderThermalEarth = renderThermalEarth;
  global.invalidateThermalMap = invalidateThermalMap;
})(window);