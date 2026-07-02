/**
 * NEXUS Map — unified Leaflet bootstrap: mousewheel zoom, pan, invalidateSize, dark tiles.
 */
(function (global) {
  "use strict";

  /** Field globe base — SDF wireframe tiles only (no third-party map services). */
  function fieldGlobeLayer(Lref) {
    const sdf = global.NexusSdf;
    if (sdf?.createGlobeLayer) {
      return sdf.createGlobeLayer(Lref);
    }
    const GridLayer = Lref.GridLayer.extend({
      createTile(coords, done) {
        const tile = document.createElement("canvas");
        const size = this.getTileSize().x;
        tile.width = size;
        tile.height = size;
        const ctx = tile.getContext("2d");
        ctx.fillStyle = "#060a14";
        ctx.fillRect(0, 0, size, size);
        ctx.strokeStyle = "rgba(77, 155, 255, 0.18)";
        for (let i = 0; i <= size; i += 32) {
          ctx.beginPath();
          ctx.moveTo(i, 0);
          ctx.lineTo(i, size);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(0, i);
          ctx.lineTo(size, i);
          ctx.stroke();
        }
        done(null, tile);
      },
    });
    return new GridLayer({
      tileSize: 256,
      minZoom: 0,
      maxZoom: 22,
      noWrap: false,
      className: "nexus-field-globe-layer",
    });
  }

  function scheduleInvalidate(map, el, delays) {
    if (!map) return;
    const times = delays || [0, 80, 200, 450];
    times.forEach((ms) => {
      setTimeout(() => {
        try {
          map.invalidateSize({ animate: false, pan: false });
        } catch (_) {
          /* map torn down */
        }
      }, ms);
    });
    if (el) {
      requestAnimationFrame(() => {
        try {
          map.invalidateSize({ animate: false, pan: false });
        } catch (_) {}
      });
    }
  }

  function bindWheelCapture(map, el) {
    if (!map || !el) return;
    el.classList.add("nexus-map");
    const container = map.getContainer();
    const stopPageScroll = (e) => {
      if (!map.scrollWheelZoom || !map.scrollWheelZoom.enabled()) return;
      e.preventDefault();
      e.stopPropagation();
    };
    container.addEventListener("wheel", stopPageScroll, { passive: false });
    container.addEventListener("mouseenter", () => el.classList.add("nexus-map-hover"));
    container.addEventListener("mouseleave", () => el.classList.remove("nexus-map-hover"));
    map.on("zoomstart", () => el.classList.add("nexus-map-zooming"));
    map.on("zoomend", () => el.classList.remove("nexus-map-zooming"));
  }

  function darkTileLayer(L, opts) {
    return fieldGlobeLayer(L);
  }

  function create(el, options) {
    if (!el || typeof L === "undefined") return null;
    const opts = Object.assign({
      center: [20, 0],
      zoom: 2,
      minZoom: 1,
      maxZoom: 22,
      worldCopyJump: true,
      zoomControl: false,
      scrollWheelZoom: true,
      wheelDebounceTime: 35,
      wheelPxPerZoomLevel: 55,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      fadeAnimation: true,
      zoomAnimation: true,
      inertia: true,
      inertiaDeceleration: 2800,
      preferCanvas: true,
    }, options || {});

    el.classList.add("host-map-booting", "nexus-map-host");
    const map = L.map(el, opts);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    bindWheelCapture(map, el);
    scheduleInvalidate(map, el);
    setTimeout(() => {
      el.classList.remove("host-map-booting");
      el.classList.add("host-map-ready");
      scheduleInvalidate(map, el, [0, 120]);
    }, 60);
    return map;
  }

  function bindCanvasZoomPan(canvas, wrap, onDraw) {
    if (!canvas || !wrap) return null;
    const state = {
      scale: 1,
      panX: 0,
      panY: 0,
      dragging: false,
      lastX: 0,
      lastY: 0,
      minScale: 0.35,
      maxScale: 12,
    };

    function clamp() {
      state.scale = Math.max(state.minScale, Math.min(state.maxScale, state.scale));
      const rect = wrap.getBoundingClientRect();
      const maxPanX = Math.max(0, (rect.width * state.scale - rect.width) * 0.5);
      const maxPanY = Math.max(0, (rect.height * state.scale - rect.height) * 0.5);
      state.panX = Math.max(-maxPanX, Math.min(maxPanX, state.panX));
      state.panY = Math.max(-maxPanY, Math.min(maxPanY, state.panY));
    }

    function redraw() {
      clamp();
      onDraw?.(state);
    }

    wrap.classList.add("nexus-canvas-map");
    canvas.style.cursor = "grab";

    wrap.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = wrap.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const prev = state.scale;
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      state.scale *= factor;
      state.panX = mx - (mx - state.panX) * (state.scale / prev);
      state.panY = my - (my - state.panY) * (state.scale / prev);
      redraw();
    }, { passive: false });

    canvas.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      state.dragging = true;
      state.lastX = e.clientX;
      state.lastY = e.clientY;
      canvas.style.cursor = "grabbing";
    });
    window.addEventListener("mousemove", (e) => {
      if (!state.dragging) return;
      state.panX += e.clientX - state.lastX;
      state.panY += e.clientY - state.lastY;
      state.lastX = e.clientX;
      state.lastY = e.clientY;
      redraw();
    });
    window.addEventListener("mouseup", () => {
      state.dragging = false;
      canvas.style.cursor = "grab";
    });

    return { state, redraw, reset() { state.scale = 1; state.panX = 0; state.panY = 0; redraw(); } };
  }

  function parseNm(v) {
    try {
      return Number(BigInt(String(v ?? "0")));
    } catch {
      const n = Number(v);
      return Number.isFinite(n) ? n : 0;
    }
  }

  /** ENU spread — pick dominant axis; height (U) often has most variance for placement. */
  function varianceExtents(entities) {
    const eVals = [];
    const nVals = [];
    const uVals = [];
    const lats = [];
    const lons = [];
    (entities || []).forEach((ent) => {
      if (ent.lat != null && ent.lon != null) {
        lats.push(Number(ent.lat));
        lons.push(Number(ent.lon));
      }
      if (ent.enu_e_nm != null) eVals.push(parseNm(ent.enu_e_nm));
      if (ent.enu_n_nm != null) nVals.push(parseNm(ent.enu_n_nm));
      if (ent.enu_u_nm != null) uVals.push(parseNm(ent.enu_u_nm));
    });
    const spread = (arr) => {
      if (!arr.length) return 0;
      if (arr.length < 2) return Math.abs(arr[0]);
      return Math.max(...arr) - Math.min(...arr);
    };
    const varE = spread(eVals);
    const varN = spread(nVals);
    const varU = spread(uVals);
    let dominant = "n";
    if (varU >= varE && varU >= varN) dominant = "u";
    else if (varE >= varN) dominant = "e";
    const mean = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);
    return {
      lats,
      lons,
      varE,
      varN,
      varU,
      dominant,
      centerLat: lats.length ? mean(lats) : null,
      centerLon: lons.length ? mean(lons) : null,
      meanU: mean(uVals),
      meanE: mean(eVals),
      meanN: mean(nVals),
    };
  }

  function resolveAnchor(data) {
    const anchor = data?.anchor || {};
    const entities = data?.entities || data?.points || [];
    const ex = varianceExtents(entities);
    if (anchor.lat != null && anchor.lon != null && !(Number(anchor.lat) === 0 && Number(anchor.lon) === 0)) {
      return {
        lat: Number(anchor.lat),
        lon: Number(anchor.lon),
        label: anchor.label || "Operator",
        alt_m: anchor.alt_m != null ? Number(anchor.alt_m) : ex.meanU / 1e9,
        dominant_axis: ex.dominant,
      };
    }
    const op = data?.operator_location || {};
    if (op.lat != null && op.lon != null && op.gps_ready !== false) {
      return {
        lat: Number(op.lat),
        lon: Number(op.lon),
        label: op.label || "Operator",
        alt_m: op.alt_m != null ? Number(op.alt_m) : ex.meanU / 1e9,
        dominant_axis: ex.dominant,
      };
    }
    if (ex.centerLat != null && ex.centerLon != null) {
      return {
        lat: ex.centerLat,
        lon: ex.centerLon,
        label: `Centroid · ${entities.length} detections`,
        alt_m: ex.meanU / 1e9,
        dominant_axis: ex.dominant,
        variance_u_nm: ex.varU,
      };
    }
    return { lat: 45.845976, lon: -87.055759, label: "Gladstone MI · operator", alt_m: 0, dominant_axis: "u" };
  }

  function fitLatLngs(map, latlngs, options) {
    if (!map || !latlngs?.length || typeof L === "undefined") return;
    const bounds = L.latLngBounds(latlngs);
    if (!bounds.isValid()) return;
    map.fitBounds(bounds.pad(options?.pad ?? 0.22), {
      maxZoom: options?.maxZoom ?? 15,
      animate: options?.animate !== false,
    });
    scheduleInvalidate(map, map.getContainer()?.parentElement || map.getContainer(), [0, 80]);
  }

  function flyToAnchor(map, anchor, options) {
    if (!map || anchor?.lat == null || anchor?.lon == null) return;
    const zoom = options?.zoom ?? (options?.points?.length > 1 ? 8 : 12);
    map.flyTo([anchor.lat, anchor.lon], zoom, { duration: options?.duration ?? 0.75 });
    scheduleInvalidate(map, map.getContainer()?.parentElement || map.getContainer(), [0, 120]);
  }

  function watchResize(el, map) {
    if (!el || !map || typeof ResizeObserver === "undefined") return;
    if (el._nexusMapObs) return;
    const ro = new ResizeObserver(() => scheduleInvalidate(map, el, [0, 40, 120]));
    ro.observe(el);
    el._nexusMapObs = ro;
  }

  function primeMapPanel(el, map) {
    if (!el || !map) return;
    const box = el.closest(".map-viewport") || el.parentElement;
    if (box) {
      const h = box.getBoundingClientRect().height;
      if (h < 120) {
        box.style.minHeight = "min(58vh, 580px)";
      }
    }
    scheduleInvalidate(map, el, [0, 60, 180, 400]);
    watchResize(el, map);
  }

  function refreshGlobePins(points, options) {
    const pins = (points || []).filter((p) => p && p.globe_pin !== false && p.lat != null && p.lon != null);
    window.dispatchEvent(
      new CustomEvent("nexus-globe-refresh", {
        detail: { points: pins, fit: options?.fit !== false, source: options?.source || "heavyboi" },
      })
    );
    return pins.length;
  }

  global.NexusMap = {
    create,
    fieldGlobeLayer,
    darkTileLayer,
    scheduleInvalidate,
    bindWheelCapture,
    bindCanvasZoomPan,
    varianceExtents,
    resolveAnchor,
    fitLatLngs,
    flyToAnchor,
    watchResize,
    primeMapPanel,
    refreshGlobePins,
  };
})(window);