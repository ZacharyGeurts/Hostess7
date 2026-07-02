/**
 * NEXUS Precision Map — sub-micron GPS placement (ENU nanometers + 15-decimal WGS84).
 */
(function (global) {
  "use strict";

  let pfData = null;
  let mode = "global";
  const state = { global: null, local: null, markers: null, localExtentNm: 0, anchorLayer: null };

  const NM_PER_MM = 1e6;
  const DEFAULT_EXTENT_NM = 20 * NM_PER_MM;

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  function parseNm(v) {
    try {
      return BigInt(String(v || "0"));
    } catch {
      return 0n;
    }
  }

  function formatNm(nm) {
    const n = parseNm(nm);
    const sign = n < 0n ? "-" : "";
    const abs = n < 0n ? -n : n;
    if (abs >= 1000000n) return `${sign}${(Number(abs) / 1e6).toFixed(3)} mm`;
    if (abs >= 1000n) return `${sign}${(Number(abs) / 1e3).toFixed(2)} µm`;
    return `${sign}${abs} nm`;
  }

  function resolveAnchor(data) {
    const mk = global.NexusMap;
    if (mk?.resolveAnchor) return mk.resolveAnchor(data);
    return data?.anchor || { lat: 45.845976, lon: -87.055759, label: "Gladstone MI · operator" };
  }

  function localExtentNm(entities) {
    const mk = global.NexusMap;
    const ex = mk?.varianceExtents ? mk.varianceExtents(entities) : {};
    const spread = Math.max(ex.varE || 0, ex.varN || 0, ex.varU || 0, DEFAULT_EXTENT_NM);
    const padded = Math.max(DEFAULT_EXTENT_NM, spread * 1.6 + 5 * NM_PER_MM);
    return Math.min(padded, 500 * NM_PER_MM);
  }

  function makeEnuCrs(extentNm) {
    const centerNm = extentNm;
    return L.extend({}, L.CRS.Simple, {
      transformation: new L.Transformation(1 / (2 * centerNm), 0.5, -1 / (2 * centerNm), 0.5),
      scale(zoom) {
        return 256 * Math.pow(2, zoom) / (2 * centerNm);
      },
      zoom(scale) {
        return Math.log(scale * (2 * centerNm) / 256) / Math.LN2;
      },
      distance(p1, p2) {
        const dx = p1.lng - p2.lng;
        const dy = p1.lat - p2.lat;
        return Math.sqrt(dx * dx + dy * dy);
      },
      infinite: false,
    });
  }

  function enuLatLng(e) {
    const eNm = Number(parseNm(e.enu_e_nm));
    const nNm = Number(parseNm(e.enu_n_nm));
    return L.latLng(nNm, eNm);
  }

  function globalLatLng(e) {
    return L.latLng(Number(e.lat), Number(e.lon));
  }

  function precisionIcon(e) {
    const col = e.kind === "terror" || e.kind === "hostile" ? "#ff5c3a"
      : e.section === "thermal" ? (e.kind === "warm" ? "#ff5c3a" : "#4d9bff")
      : e.section === "home" ? "#d4af37" : "#5ec8ff";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">
      <circle cx="6" cy="6" r="4.5" fill="${col}" stroke="#e8ecf4" stroke-width="1"/>
      <circle cx="6" cy="6" r="1.2" fill="#fff" fill-opacity="0.9"/>
    </svg>`;
    return L.divIcon({
      className: "pf-pin",
      html: svg,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
  }

  function destroyLocalMap() {
    if (state.local) {
      state.local.remove();
      state.local = null;
    }
    state.anchorLayer = null;
  }

  function destroyMap() {
    if (state.global) {
      state.global.remove();
      state.global = null;
    }
    destroyLocalMap();
    state.markers = null;
  }

  function renderMarkers(map, entities, toLatLng) {
    if (!map) return;
    if (state.markers) state.markers.clearLayers();
    else state.markers = L.layerGroup().addTo(map);
    entities.forEach((e) => {
      if (!e.placed && e.lat == null) return;
      const m = L.marker(toLatLng(e), { icon: precisionIcon(e), riseOnHover: true })
        .bindPopup(`<div class="pf-popup">
          <strong>${esc(e.label || e.id)}</strong><br>
          <span class="meta">${esc(e.precision || "sub_micron")}</span><br>
          lat <code>${esc(e.lat_str || e.lat)}</code><br>
          lon <code>${esc(e.lon_str || e.lon)}</code><br>
          ENU E ${esc(formatNm(e.enu_e_nm))} · N ${esc(formatNm(e.enu_n_nm))}<br>
          ${e.enu_u_nm ? `U ${esc(formatNm(e.enu_u_nm))}<br>` : ""}
          <span class="meta">${esc(e.source || "")}</span>
        </div>`);
      state.markers.addLayer(m);
    });
  }

  function primeEl(el, map) {
    const mk = global.NexusMap;
    if (mk?.primeMapPanel) mk.primeMapPanel(el, map);
    else map?.invalidateSize();
  }

  function ensureGlobalMap() {
    const el = document.getElementById("precision-global-map");
    if (!el || typeof L === "undefined") return null;
    if (state.global) return state.global;
    const mk = global.NexusMap;
    state.global = mk
      ? mk.create(el, { center: [20, 0], zoom: 3, minZoom: 1, maxZoom: 22 })
      : L.map(el, { center: [20, 0], zoom: 3, minZoom: 1, maxZoom: 22, scrollWheelZoom: true });
    (mk ? (mk.fieldGlobeLayer ? mk.fieldGlobeLayer(L) : mk.darkTileLayer(L)) : (
      global.NexusSdf?.createGlobeLayer ? NexusSdf.createGlobeLayer(L) : L.gridLayer({ tileSize: 256 })
    )).addTo(state.global);
    primeEl(el, state.global);
    return state.global;
  }

  function ensureLocalMap(anchor, extentNm) {
    const el = document.getElementById("precision-local-map");
    if (!el || typeof L === "undefined") return null;
    if (state.local && state.localExtentNm === extentNm) return state.local;
    destroyLocalMap();
    state.localExtentNm = extentNm;
    const crs = makeEnuCrs(extentNm);
    const mk = global.NexusMap;
    const localOpts = {
      crs,
      center: [0, 0],
      zoom: 14,
      minZoom: 8,
      maxZoom: 28,
      maxBounds: L.latLngBounds([-extentNm, -extentNm], [extentNm, extentNm]),
      maxBoundsViscosity: 0.85,
    };
    state.local = mk ? mk.create(el, localOpts) : L.map(el, Object.assign({ scrollWheelZoom: true }, localOpts));
    L.rectangle(
      [[-extentNm, -extentNm], [extentNm, extentNm]],
      { color: "#4d9bff", weight: 1, fillOpacity: 0.03 },
    ).addTo(state.local);
    const axis = anchor?.dominant_axis || "u";
    L.marker([0, 0], {
      icon: L.divIcon({
        className: "pf-anchor",
        html: `<span style="color:#d4af37;font-size:14pt">ANCHOR · ${esc(axis.toUpperCase())}</span>`,
        iconSize: [72, 14],
        iconAnchor: [36, 7],
      }),
    }).addTo(state.local).bindTooltip(esc(anchor?.label || "Operator anchor"), { permanent: false });
    primeEl(el, state.local);
    return state.local;
  }

  function renderMeta() {
    const meta = document.getElementById("precision-map-meta");
    const stats = document.getElementById("precision-map-stats");
    const s = pfData?.stats || {};
    const g = pfData?.gps || {};
    const anchor = resolveAnchor(pfData || {});
    if (meta) {
      meta.textContent = [
        pfData?.tagline || "",
        g.resolution_nm ? `LSB ${g.resolution_nm} nm` : "",
        anchor.label ? `anchor ${anchor.label}` : "",
        anchor.dominant_axis ? `dominant ${anchor.dominant_axis.toUpperCase()}` : "",
      ].filter(Boolean).join(" · ");
    }
    if (stats) {
      stats.innerHTML = [
        `<span>Placed <strong>${s.placed ?? 0}</strong></span>`,
        `<span>Sub-µm <strong>${s.sub_micron ?? 0}</strong></span>`,
        `<span>Total <strong>${s.total ?? 0}</strong></span>`,
      ].join("");
    }
  }

  function fitGlobalView(map, entities, anchor) {
    const mk = global.NexusMap;
    const latlngs = (entities || [])
      .filter((e) => e.lat != null && e.lon != null)
      .map((e) => [Number(e.lat), Number(e.lon)]);
    if (anchor?.lat != null && anchor?.lon != null) latlngs.push([anchor.lat, anchor.lon]);
    if (latlngs.length > 1 && mk?.fitLatLngs) {
      mk.fitLatLngs(map, latlngs, { pad: 0.2, maxZoom: 14 });
    } else if (anchor?.lat != null && mk?.flyToAnchor) {
      mk.flyToAnchor(map, anchor, { zoom: latlngs.length ? 10 : 12 });
    } else if (anchor?.lat != null) {
      map.flyTo([anchor.lat, anchor.lon], 12, { duration: 0.75 });
    }
  }

  function fitLocalView(map, entities) {
    const pts = (entities || [])
      .filter((e) => e.enu_e_nm != null || e.enu_n_nm != null)
      .map(enuLatLng);
    if (pts.length < 2) {
      map.setView([0, 0], 16);
      return;
    }
    const bounds = L.latLngBounds(pts);
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.25), { maxZoom: 22, animate: true });
  }

  function setMode(next) {
    mode = next;
    document.querySelectorAll(".pf-map-tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.pfMap === next);
    });
    document.getElementById("precision-global-map")?.classList.toggle("active", next === "global");
    document.getElementById("precision-local-map")?.classList.toggle("active", next === "local");
    const entities = pfData?.entities || [];
    const anchor = resolveAnchor(pfData || {});
    const extent = localExtentNm(entities);
    if (next === "global") {
      const map = ensureGlobalMap();
      renderMarkers(map, entities, globalLatLng);
      fitGlobalView(map, entities, anchor);
      primeEl(document.getElementById("precision-global-map"), map);
    } else {
      const map = ensureLocalMap(anchor, extent);
      renderMarkers(map, entities, enuLatLng);
      fitLocalView(map, entities);
      primeEl(document.getElementById("precision-local-map"), map);
    }
  }

  function renderPrecisionMap(data) {
    pfData = data || pfData;
    if (!pfData) return;
    if (pfData.anchor) pfData.anchor = resolveAnchor(pfData);
    renderMeta();
    setMode(mode);
  }

  async function placeAtClick(e) {
    if (!pfData?.anchor) return;
    const body = {
      label: `Click @ E${Math.round(e.latlng.lng)} N${Math.round(e.latlng.lat)} nm`,
      enu_e_nm: String(Math.round(e.latlng.lng)),
      enu_n_nm: String(Math.round(e.latlng.lat)),
      enu_u_nm: "0",
      section: "manual",
      kind: "placed",
      source: "precision_map_click",
    };
    try {
      const res = await fetch("/api/precision-field/place", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const doc = await res.json();
      if (doc.ok) {
        const rebuilt = await fetch("/api/precision-field/rebuild", { method: "POST" });
        renderPrecisionMap(await rebuilt.json());
      }
    } catch {
      /* ignore */
    }
  }

  function bindControls() {
    document.querySelectorAll(".pf-map-tab").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => setMode(btn.dataset.pfMap || "global"));
    });
    document.getElementById("precision-map-rebuild")?.addEventListener("click", async () => {
      const res = await fetch("/api/precision-field/rebuild", { method: "POST" });
      renderPrecisionMap(await res.json());
    });
    document.getElementById("precision-map-refocus")?.addEventListener("click", () => {
      const entities = pfData?.entities || [];
      const anchor = resolveAnchor(pfData || {});
      if (mode === "global" && state.global) {
        fitGlobalView(state.global, entities, anchor);
      } else if (state.local) {
        fitLocalView(state.local, entities);
      }
    });
    document.getElementById("precision-place-toggle")?.addEventListener("click", (ev) => {
      ev.target.classList.toggle("active");
      const on = ev.target.classList.contains("active");
      if (state.local) {
        if (on) state.local.on("click", placeAtClick);
        else state.local.off("click", placeAtClick);
      }
    });
  }

  function invalidatePrecisionMap() {
    const mk = global.NexusMap;
    const gEl = document.getElementById("precision-global-map");
    const lEl = document.getElementById("precision-local-map");
    if (mk) {
      if (state.global) primeEl(gEl, state.global);
      if (state.local) primeEl(lEl, state.local);
    } else {
      state.global?.invalidateSize();
      state.local?.invalidateSize();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindControls);
  } else {
    bindControls();
  }

  global.renderPrecisionMap = renderPrecisionMap;
  global.invalidatePrecisionMap = invalidatePrecisionMap;
})(window);