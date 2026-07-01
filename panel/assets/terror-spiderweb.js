/**
 * Global terror Spiderweb — three maps + universal field registry tables.
 */
(function (global) {
  "use strict";

  let swData = null;
  let swFocused = false;
  let swRegistryFilter = "all";
  let swRegistrySearch = "";

  const maps = {
    terror: { map: null, layer: null, canvas: null, ctx: null, focused: false },
    registry: { map: null, layer: null, focused: false },
    mobile: { map: null, layer: null, focused: false },
    thermal: { map: null, focused: false },
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function homePinIcon(kind) {
    const fill = kind === "neighbor" ? "#3dd68c" : "#d4af37";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
      <path d="M14 0C7 0 2 6 2 13c0 9 12 23 12 23s12-14 12-23C26 6 21 0 14 0z" fill="${fill}" stroke="#1a2030" stroke-width="1.2"/>
      <circle cx="14" cy="12" r="5" fill="#0d1220"/>
      <rect x="11" y="16" width="6" height="5" rx="1" fill="#e8ecf4"/>
    </svg>`;
    return L.divIcon({
      className: "sw-home-pin",
      html: svg,
      iconSize: [28, 36],
      iconAnchor: [14, 35],
    });
  }

  function terrorIcon(heat) {
    const r = 6 + Math.min(10, (heat || 0.5) * 12);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${r * 2}" height="${r * 2}">
      <circle cx="${r}" cy="${r}" r="${r - 1}" fill="#ff3a4a" fill-opacity="0.85" stroke="#ffb0b8" stroke-width="1.5"/>
    </svg>`;
    return L.divIcon({
      className: "sw-terror-pin",
      html: svg,
      iconSize: [r * 2, r * 2],
      iconAnchor: [r, r],
    });
  }

  function cellphoneIcon(moving) {
    const pulse = moving ? "#5ec8ff" : "#7a9ab8";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="28" viewBox="0 0 18 28">
      <rect x="3" y="1" width="12" height="26" rx="3" fill="${pulse}" stroke="#1a2030" stroke-width="1"/>
      <rect x="6" y="4" width="6" height="14" rx="1" fill="#0d1220"/>
      <circle cx="9" cy="22" r="2" fill="#0d1220"/>
    </svg>`;
    return L.divIcon({
      className: "sw-mobile-pin",
      html: svg,
      iconSize: [18, 28],
      iconAnchor: [9, 26],
    });
  }

  function batteryIcon(capacity) {
    const pct = Number.isFinite(Number(capacity)) ? Math.max(0, Math.min(100, Number(capacity))) : 50;
    const fill = pct > 20 ? "#ffb84d" : "#ff6b4a";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="26" height="14" viewBox="0 0 26 14">
      <rect x="1" y="2" width="20" height="10" rx="2" fill="#1a2030" stroke="#4a5568" stroke-width="1"/>
      <rect x="3" y="4" width="${Math.round(16 * pct / 100)}" height="6" rx="1" fill="${fill}"/>
      <rect x="22" y="5" width="3" height="4" rx="1" fill="#4a5568"/>
    </svg>`;
    return L.divIcon({
      className: "sw-battery-pin",
      html: svg,
      iconSize: [26, 14],
      iconAnchor: [13, 7],
    });
  }

  function remoteIcon() {
    return L.divIcon({
      className: "sw-remote-pin",
      html: '<span style="display:block;width:8px;height:8px;border-radius:50%;background:#9aa8be;border:1px solid #4d9bff;"></span>',
      iconSize: [8, 8],
      iconAnchor: [4, 4],
    });
  }

  function nodeById(id) {
    return (swData?.nodes || []).find((n) => n.id === id);
  }

  function ensureMap(key, elId, onReady) {
    const el = document.getElementById(elId);
    if (!el || typeof L === "undefined") return null;
    const slot = maps[key];
    if (slot.map) {
      onReady?.(slot);
      return slot.map;
    }
    const mk = global.NexusMap;
    slot.map = mk
      ? mk.create(el, { center: [20, 0], zoom: 2, minZoom: 2, maxZoom: 18 })
      : L.map(el, {
        center: [20, 0], zoom: 2, minZoom: 2, maxZoom: 18,
        worldCopyJump: true, zoomControl: true, scrollWheelZoom: true,
      });
    (mk ? (mk.fieldGlobeLayer ? mk.fieldGlobeLayer(L) : mk.darkTileLayer(L, { maxZoom: 19 })) : (
      global.NexusSdf?.createGlobeLayer ? NexusSdf.createGlobeLayer(L) : L.gridLayer({ tileSize: 256 })
    )).addTo(slot.map);
    slot.layer = L.layerGroup().addTo(slot.map);
    if (key === "terror") {
      slot.canvas = document.createElement("canvas");
      slot.canvas.className = "spiderweb-canvas";
      slot.canvas.style.cssText =
        "position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:450;";
      el.appendChild(slot.canvas);
      slot.ctx = slot.canvas.getContext("2d");
      slot.map.on("move zoom resize viewreset", () => drawWeb());
    }
    const finish = () => {
      el.classList.remove("host-map-booting");
      el.classList.add("host-map-ready");
      if (mk?.primeMapPanel) mk.primeMapPanel(el, slot.map);
      else if (mk) mk.scheduleInvalidate(slot.map, el);
      else slot.map.invalidateSize();
      onReady?.(slot);
    };
    setTimeout(finish, mk ? 60 : 120);
    return slot.map;
  }

  function resizeTerrorCanvas() {
    const slot = maps.terror;
    if (!slot.canvas || !slot.map) return;
    const size = slot.map.getSize();
    slot.canvas.width = size.x;
    slot.canvas.height = size.y;
  }

  function drawWeb() {
    const slot = maps.terror;
    if (!slot.ctx || !slot.map || !swData) return;
    resizeTerrorCanvas();
    const w = slot.canvas.width;
    const h = slot.canvas.height;
    slot.ctx.clearRect(0, 0, w, h);
    (swData.edges || []).forEach((e) => {
      const a = nodeById(e.from);
      const b = nodeById(e.to);
      if (!a || !b || a.lat == null || b.lat == null) return;
      const pa = slot.map.latLngToContainerPoint([a.lat, a.lon]);
      const pb = slot.map.latLngToContainerPoint([b.lat, b.lon]);
      slot.ctx.beginPath();
      slot.ctx.moveTo(pa.x, pa.y);
      slot.ctx.lineTo(pb.x, pb.y);
      slot.ctx.strokeStyle = e.color || "#4d9bff";
      slot.ctx.lineWidth = Math.max(1.2, (e.weight || 1.5) * 0.9);
      slot.ctx.globalAlpha = e.kind === "terror" ? 0.75 : 0.55;
      slot.ctx.setLineDash(e.kind === "pipe_up" || e.kind === "pipe_down" ? [6, 4] : []);
      slot.ctx.stroke();
      slot.ctx.globalAlpha = 1;
    });
  }

  function markerForNode(n, mode) {
    if (n.pushpin || n.kind === "home" || n.kind === "neighbor" || n.kind === "lan" || n.kind === "gov" || n.kind === "tagged") {
      return homePinIcon(n.kind);
    }
    if (n.kind === "terror") return terrorIcon(n.heat);
    if (n.kind === "cellphone" || n.kind === "mobile") return cellphoneIcon(n.moving);
    if (n.kind === "battery") return batteryIcon(n.capacity_pct);
    if (mode === "registry") {
      const color = n.color || "#9aa8be";
      return L.divIcon({
        className: "sw-registry-dot",
        html: `<span style="display:block;width:7px;height:7px;border-radius:50%;background:${color};border:1px solid #e8ecf4;"></span>`,
        iconSize: [7, 7],
        iconAnchor: [3, 3],
      });
    }
    return remoteIcon();
  }

  function nodeTooltip(n) {
    const parts = [n.label || n.id];
    if (n.address) parts.push(n.address);
    if (n.ip) parts.push(n.ip);
    if (n.vendor) parts.push(n.vendor);
    if (n.moving) parts.push("moving");
    if (n.capacity_pct != null) parts.push(`${n.capacity_pct}%`);
    return parts.join(" · ");
  }

  function renderMarkersOn(slot, nodes, mode) {
    if (!slot.layer) return;
    slot.layer.clearLayers();
    nodes.forEach((n) => {
      if (n.lat == null || n.lon == null) return;
      const icon = markerForNode(n, mode);
      const m = L.marker([n.lat, n.lon], { icon, riseOnHover: true })
        .bindTooltip(nodeTooltip(n), { direction: "top" });
      slot.layer.addLayer(m);
    });
  }

  function flyToFocus(slot, focus, flagKey) {
    if (!slot.map || !focus || slot[flagKey]) return;
    const lat = Number(focus.lat);
    const lon = Number(focus.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    slot.map.flyTo([lat, lon], focus.zoom || 6, { duration: 1.2 });
    slot[flagKey] = true;
  }

  function renderTerrorMap(data) {
    ensureMap("terror", "spiderweb-map", () => {
      renderMarkersOn(maps.terror, data.nodes || [], "terror");
      drawWeb();
      maps.terror.focused = false;
      flyToFocus(maps.terror, data.focus, "focused");
    });
  }

  function renderRegistryMap(data) {
    const reg = data.registry || {};
    const all = []
      .concat(reg.homes || [])
      .concat(reg.internet || [])
      .concat(reg.mobile || [])
      .concat(reg.batteries || [])
      .filter((n) => n.placed && n.lat != null);
    ensureMap("registry", "spiderweb-registry-map", () => {
      renderMarkersOn(maps.registry, all, "registry");
      maps.registry.focused = false;
      const focus = data.focus || { lat: 20, lon: 0, zoom: 2 };
      flyToFocus(maps.registry, { ...focus, zoom: Math.min((focus.zoom || 6) + 1, 10) }, "focused");
    });
  }

  function renderMobileMap(data) {
    const reg = data.registry || {};
    const mobileNodes = []
      .concat(reg.mobile || [])
      .concat(reg.batteries || [])
      .filter((n) => n.placed && n.lat != null);
    ensureMap("mobile", "spiderweb-mobile-map", () => {
      renderMarkersOn(maps.mobile, mobileNodes, "mobile");
      maps.mobile.focused = false;
      flyToFocus(maps.mobile, data.mobile_focus || data.focus, "focused");
    });
  }

  function registryRows(data) {
    const reg = data.registry || {};
    const rows = [];
    (reg.homes || []).forEach((r) => rows.push({ ...r, _section: "home" }));
    (reg.internet || []).forEach((r) => rows.push({ ...r, _section: "internet" }));
    (reg.mobile || []).forEach((r) => rows.push({ ...r, _section: "mobile" }));
    (reg.batteries || []).forEach((r) => rows.push({ ...r, _section: "battery" }));
    return rows;
  }

  function filterRegistryRows(rows) {
    const q = swRegistrySearch.trim().toLowerCase();
    return rows.filter((r) => {
      if (swRegistryFilter !== "all" && r._section !== swRegistryFilter) return false;
      if (!q) return true;
      const hay = [
        r.id, r.label, r.address, r.ip, r.role, r.kind, r.vendor, r.org, r.city, r.country,
        r.status, r.device, r.ssid, (r.sources || []).join(" "),
      ].join(" ").toLowerCase();
      return hay.includes(q);
    });
  }

  function renderRegistryTables(data) {
    const host = document.getElementById("spiderweb-registry-tables");
    if (!host) return;
    const rows = filterRegistryRows(registryRows(data));
    const sections = [
      { key: "home", title: "All homes", cols: ["id", "label", "address", "GPS", "role", "sources"] },
      { key: "internet", title: "All internet", cols: ["ip", "label", "kind", "city", "org", "placed", "sources"] },
      { key: "mobile", title: "All cellphones & radios", cols: ["label", "kind", "vendor", "moving", "GPS", "sources"] },
      { key: "battery", title: "All batteries", cols: ["label", "capacity_pct", "status", "moving", "GPS", "sources"] },
    ];
    host.innerHTML = sections.map((sec) => {
      const secRows = rows.filter((r) => r._section === sec.key);
      if (!secRows.length && swRegistryFilter !== "all" && swRegistryFilter !== sec.key) return "";
      return `<div class="sw-registry-block">
        <h4 class="sw-registry-title">${esc(sec.title)} <span class="meta">(${secRows.length})</span></h4>
        ${secRows.length ? `<div class="sw-registry-scroll"><table class="honor-table"><thead><tr>
          ${sec.cols.map((c) => `<th>${esc(c)}</th>`).join("")}
        </tr></thead><tbody>
          ${secRows.slice(0, 200).map((r) => `<tr>
            <td>${esc(r.id || r.ip || "—")}</td>
            <td>${esc(r.label || "—")}</td>
            <td>${esc(r.address || r.kind || r.org || "—")}</td>
            <td>${r.lat != null ? esc(`${r.lat}, ${r.lon}`) : "<em>unplaced</em>"}</td>
            <td>${esc(String(r.role || r.city || r.vendor || r.capacity_pct ?? r.moving ?? "—"))}</td>
            <td>${esc((r.sources || []).slice(0, 4).join(", ") || "—")}</td>
          </tr>`).join("")}
        </tbody></table></div>` : '<div class="empty">No entries in this section.</div>'}
      </div>`;
    }).join("");
  }

  function renderSectionsDiagram(data) {
    const host = document.getElementById("spiderweb-sections-diagram");
    if (!host) return;
    const diag = data.sections_diagram || {};
    const sections = Array.isArray(diag.sections) ? diag.sections : [];
    const idle = data.mode === "idle" || diag.idle || data.stats?.idle;
    if (!sections.length && !diag.ascii) {
      host.innerHTML =
        '<pre class="sw-sections-ascii">[ idle — press Rebuild web to survey sections ]</pre>';
      return;
    }
    const cards = sections
      .map((sec) => {
        const placed =
          sec.placed != null ? ` · ${sec.placed} placed` : sec.moving != null ? ` · ${sec.moving} moving` : "";
        const samples = (sec.samples || []).length
          ? `<div class="sw-section-samples">${esc((sec.samples || []).join(" · "))}</div>`
          : "";
        return (
          `<article class="sw-section-card${idle ? " sw-section-card--idle" : ""}">` +
          `<h4>${esc(sec.title || sec.id)}</h4>` +
          `<div class="sw-section-count"><strong>${sec.total ?? 0}</strong>${placed}</div>` +
          samples +
          "</article>"
        );
      })
      .join("");
    host.innerHTML =
      (diag.ascii
        ? `<pre class="sw-sections-ascii" aria-label="Section topology">${esc(diag.ascii)}</pre>`
        : "") +
      `<div class="sw-sections-grid">${cards}</div>`;
  }

  function renderMeta(data) {
    const motto = document.getElementById("spiderweb-motto");
    const meta = document.getElementById("spiderweb-meta");
    const stats = document.getElementById("spiderweb-stats");
    const banner = document.getElementById("spiderweb-universal-banner");
    const leg = document.getElementById("spiderweb-legend");
    const s = data.stats || {};
    const focus = data.focus || {};
    const idle = data.mode === "idle" || s.idle;

    renderSectionsDiagram(data);

    if (motto && data.motto) {
      motto.innerHTML = `<strong>Global terror · Spiderweb</strong> — ${esc(data.motto)}`;
    }
    if (banner) {
      banner.innerHTML = [
        `<span class="sw-banner-item"><strong>${s.total_homes ?? 0}</strong> homes</span>`,
        `<span class="sw-banner-item"><strong>${s.total_internet ?? 0}</strong> internet</span>`,
        `<span class="sw-banner-item"><strong>${s.total_mobile ?? 0}</strong> mobile</span>`,
        `<span class="sw-banner-item"><strong>${s.total_battery ?? 0}</strong> batteries</span>`,
        `<span class="sw-banner-item sw-banner-highlight"><strong>${s.identified_everywhere ?? 0}</strong> identified everywhere</span>`,
        `<span class="sw-banner-item meta">${s.mobile_moving ?? 0} moving · ${s.internet_unplaced ?? 0} internet unplaced</span>`,
      ].join("");
    }
    if (meta) {
      meta.textContent = idle
        ? "Idle — operator rebuild only · no background probes"
        : [
            focus.label || "Spiderweb survey",
            `heat ${focus.heat_sum ?? 0}`,
            s.terror_nodes != null ? `terror ${s.terror_nodes}` : "",
            s.edges != null ? `edges ${s.edges}` : "",
            data.tempered ? "tempered build" : "",
          ].filter(Boolean).join(" · ");
    }
    if (stats) {
      stats.innerHTML = [
        `<span>Homes <strong>${s.total_homes ?? 0}</strong> (${s.homes_placed ?? 0} placed)</span>`,
        `<span>Internet <strong>${s.total_internet ?? 0}</strong> (${s.internet_placed ?? 0} placed)</span>`,
        `<span>Mobile <strong>${s.total_mobile ?? 0}</strong> (${s.mobile_moving ?? 0} moving)</span>`,
        `<span>Battery <strong>${s.total_battery ?? 0}</strong></span>`,
        `<span>Terror <strong>${s.terror_nodes ?? 0}</strong></span>`,
        `<span>Pipe ↑ <strong style="color:#4d9bff">${s.pipe_up ?? 0}</strong></span>`,
        `<span>Pipe ↓ <strong style="color:#b06cff">${s.pipe_down ?? 0}</strong></span>`,
      ].join("");
    }
    if (leg && data.legend) {
      leg.innerHTML = Object.entries(data.legend).map(([k, v]) =>
        `<span class="sw-legend-item"><span class="sw-swatch" style="background:${esc(v.color)}"></span>${esc(v.label || k)}</span>`
      ).join("");
    }
    renderRegistryTables(data);
    renderExistenceTable(data);
  }

  function renderExistenceTable(data) {
    const meta = document.getElementById("spiderweb-existence-meta");
    const host = document.getElementById("spiderweb-existence-table");
    const ex = data.existence_identity || {};
    const stats = ex.stats || {};
    const toolkit = ex.toolkit || {};
    const ocr = toolkit.ocr || {};
    const vision = toolkit.vision || {};
    if (meta) {
      meta.innerHTML = [
        `<span><strong>${stats.existing ?? 0}</strong> existing</span>`,
        `<span>${stats.absent ?? 0} absent (persisted)</span>`,
        `<span>${stats.vision_corroborated ?? 0} vision</span>`,
        `<span>${stats.ocr_corroborated ?? 0} OCR</span>`,
        `<span>${stats.with_identity_hash ?? 0} identity hash</span>`,
        `<span class="meta">OCR ${ocr.available ? "tesseract ON" : "tesseract off"} · H7 vision ${vision.h7_team_mounted ? "mounted" : "cache"} · ${vision.domain_count ?? 0} domains</span>`,
      ].join(" · ");
    }
    if (!host) return;
    const rows = (ex.table || []).filter((r) => {
      const q = swRegistrySearch.trim().toLowerCase();
      if (!q) return true;
      const hay = [
        r.existence_id, r.entity_key, r.label, r.section, r.ip, r.mac, r.vendor,
        r.identity_hash, (r.vision_domains || []).join(" "),
      ].join(" ").toLowerCase();
      return hay.includes(q);
    });
    host.innerHTML = rows.length
      ? `<table class="honor-table"><thead><tr>
          <th>Existence ID</th><th>Section</th><th>Label</th><th>Exists</th><th>Score</th><th>Identity</th><th>Vision</th><th>OCR</th><th>GPS</th><th>Sightings</th>
        </tr></thead><tbody>
        ${rows.slice(0, 300).map((r) => `<tr class="${r.exists ? "" : "meta"}">
          <td>${esc(r.existence_id)}</td>
          <td>${esc(r.section)}</td>
          <td>${esc(r.label)}</td>
          <td>${r.exists ? '<span class="severity-ok">yes</span>' : '<span class="meta">absent</span>'}</td>
          <td>${esc(r.existence_score)}</td>
          <td>${r.identity_hash ? esc(r.identity_hash.slice(0, 12) + "…") : "—"}</td>
          <td>${(r.vision_domains || []).length ? esc((r.vision_domains || []).join(", ")) : "—"}</td>
          <td>${r.ocr_corroborated ? '<span class="severity-ok">✓</span>' : "—"}</td>
          <td>${r.lat != null ? esc(`${r.lat}, ${r.lon}`) : "—"}</td>
          <td>${esc(r.sightings ?? 1)}</td>
        </tr>`).join("")}
        </tbody></table>`
      : '<div class="empty">Rebuild spiderweb to populate persistent existence identities.</div>';
  }

  function setActiveMapTab(tab) {
    document.querySelectorAll(".sw-map-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.swMap === tab);
    });
    document.querySelectorAll(".sw-map-panel").forEach((panel) => {
      const active =
        (tab === "terror" && panel.id === "spiderweb-map")
        || (tab === "thermal" && panel.id === "spiderweb-thermal-map")
        || panel.id === `spiderweb-${tab}-map`;
      panel.classList.toggle("active", active);
    });
    const globe3d = document.getElementById("thermal-globe-3d-wrap");
    if (globe3d) globe3d.classList.toggle("active", tab === "thermal");
    const slot = maps[tab];
    if (slot?.map) {
      const elId = tab === "terror" ? "spiderweb-map" : `spiderweb-${tab}-map`;
      const el = document.getElementById(elId);
      const mk = global.NexusMap;
      setTimeout(() => {
        if (mk?.primeMapPanel && el) mk.primeMapPanel(el, slot.map);
        else slot.map.invalidateSize();
        if (tab === "terror") drawWeb();
      }, 60);
    }
  }

  function bindRegistryControls() {
    const search = document.getElementById("spiderweb-registry-search");
    const filter = document.getElementById("spiderweb-registry-filter");
    if (search && !search.dataset.bound) {
      search.dataset.bound = "1";
      search.addEventListener("input", () => {
        swRegistrySearch = search.value || "";
        if (swData) renderRegistryTables(swData);
      });
    }
    if (filter && !filter.dataset.bound) {
      filter.dataset.bound = "1";
      filter.addEventListener("change", () => {
        swRegistryFilter = filter.value || "all";
        if (swData) renderRegistryTables(swData);
      });
    }
    document.querySelectorAll(".sw-map-tab").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => setActiveMapTab(btn.dataset.swMap || "terror"));
    });
  }

  function renderTerrorSpiderweb(sw) {
    if (!sw) return;
    swData = sw;
    swFocused = false;
    maps.terror.focused = false;
    maps.registry.focused = false;
    maps.mobile.focused = false;
    renderMeta(sw);
    bindRegistryControls();
    renderTerrorMap(sw);
    renderRegistryMap(sw);
    renderMobileMap(sw);
    if (sw.thermal_earth && global.renderThermalEarth) {
      global.renderThermalEarth(sw.thermal_earth);
    }
    if (document.getElementById("view-spiderweb")?.classList.contains("active")) {
      Object.values(maps).forEach((slot) => slot.map?.invalidateSize());
      drawWeb();
    }
  }

  function invalidateSpiderwebMap() {
    Object.values(maps).forEach((slot) => slot.map?.invalidateSize());
    drawWeb();
  }

  function refocusSpiderweb() {
    swFocused = false;
    maps.terror.focused = false;
    if (swData?.focus) flyToFocus(maps.terror, swData.focus, "focused");
  }

  global.renderTerrorSpiderweb = renderTerrorSpiderweb;
  global.invalidateSpiderwebMap = invalidateSpiderwebMap;
  global.refocusSpiderweb = refocusSpiderweb;
})(window);