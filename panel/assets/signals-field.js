/**
 * Signals tab — rippling green 3D field sheet, multi-truth RF representations.
 */
(function (global) {
  "use strict";

  const FIELD_ANTENNA_REMOVED = true;

  let animId = 0;
  let phase = 0;
  let lastDoc = null;
  let heroBound = false;
  let sheetCache = null;

  const FIELD_GREEN = {
    "2.4GHz": [77, 232, 138],
    "5GHz": [46, 201, 106],
    "6GHz": [138, 240, 176],
    unknown: [61, 214, 140],
  };

  const THREAT_COLORS = {
    none: "#4de88a",
    watch: "#c8e878",
    critical: "#ff6a82",
  };

  let refreshBound = false;
  let testBound = false;
  let radioSearchBound = false;
  let radioTuneBound = false;
  let worldTuneBound = false;
  let lastRadioStations = [];
  let lastTuned = null;

  function mergeSignalsPayload(panelData) {
    const raw = panelData || {};
    const sf = raw.signals_field || raw;
    const fa = FIELD_ANTENNA_REMOVED ? {} : (raw.field_antenna || {});
    const frRoot = raw.field_radio || {};
    const frSf = sf.field_radio || {};
    const frNested = (fa.field_radio && fa.field_radio.station_menu) ? fa.field_radio : {};
    const fr = Object.keys(frRoot).length ? frRoot
      : Object.keys(frNested).length ? frNested
      : frSf;
    const readiness = fa.readiness || sf.field_antenna || {};
    const opProf = sf.operator_profile || raw.operator_location || fr.operator || {};
    return {
      ...sf,
      field_hardware: sf.field_hardware || raw.field_hardware || {},
      field_hazard_onset: sf.field_hazard_onset || raw.field_hazard_onset || {},
      lethal_enforcement: sf.lethal_enforcement || raw.lethal_enforcement || {},
      hostess7_lethal_insight: sf.hostess7_lethal_insight || raw.hostess7_lethal_insight || {},
      field_antenna_catch: sf.field_antenna_catch || raw.field_antenna_catch || fa.catch || {},
      field_antenna: {
        blaster_ready: readiness.blaster_ready ?? sf.field_antenna?.blaster_ready,
        score: readiness.score ?? sf.field_antenna?.score,
        tier: readiness.tier ?? sf.field_antenna?.tier,
        sub_micron_accuracy: readiness.sub_micron_accuracy ?? sf.field_antenna?.sub_micron_accuracy,
        checks: readiness.checks || [],
        modalities: (fa.frequency_knowledge || {}).modalities || sf.field_antenna?.modalities || [],
        frequency_coverage_pct: (fa.frequency_knowledge || {}).coverage_pct ?? sf.field_antenna?.frequency_coverage_pct,
      },
      field_radio: Object.keys(fr).length ? fr : frSf,
      field_world_placement: raw.field_world_placement || sf.field_world_placement || {},
      operator_profile: opProf,
    };
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function operatorCenter(doc) {
    const op = doc?.field_radio?.operator || doc?.operator || {};
    if (op.lat != null && op.lon != null) return { lat: Number(op.lat), lon: Number(op.lon) };
    return null;
  }

  /** On-point WGS84 → canvas — never radial/path. */
  function pointToNorm(lat, lon, center) {
    if (lat == null || lon == null || !center) return null;
    const dlat = Number(lat) - center.lat;
    const dlon = Number(lon) - center.lon;
    return {
      u: clamp(0.5 + dlon * 4.0, 0.04, 0.96),
      v: clamp(0.5 - dlat * 4.0, 0.04, 0.96),
    };
  }

  function itemCanvasPoint(item, center, i, fallbackCount) {
    if (item.norm_x != null && item.norm_y != null) {
      return { u: clamp(Number(item.norm_x), 0.04, 0.96), v: clamp(Number(item.norm_y), 0.04, 0.96) };
    }
    const lat = item.lat ?? item.tower_lat;
    const lon = item.lon ?? item.tower_lon;
    const pt = pointToNorm(lat, lon, center);
    if (pt) return pt;
    const n = Math.max(fallbackCount || 1, 1);
    const u = 0.5 + (((i * 17) % n) / n - 0.5) * 0.12;
    const v = 0.5 + (((i * 11) % n) / n - 0.5) * 0.12;
    return { u: clamp(u, 0.08, 0.92), v: clamp(v, 0.08, 0.92) };
  }

  function greenRgb(band, alpha) {
    const rgb = FIELD_GREEN[band] || FIELD_GREEN.unknown;
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
  }

  function stopAnimation() {
    if (animId) cancelAnimationFrame(animId);
    animId = 0;
  }

  function isSignalsActive() {
    return document.getElementById("view-signals")?.classList.contains("active");
  }

  function buildSheetMesh(w, h, doc) {
    const cols = 36;
    const rows = 22;
    const registry = doc.frequency_registry?.entries || [];
    const antennas = doc.antennas || [];
    const dots = doc.scan_dots || [];
    const sectors = doc.material_field?.sectors || [];
    const center = operatorCenter(doc);
    const mesh = [];

    for (let y = 0; y <= rows; y++) {
      const row = [];
      for (let x = 0; x <= cols; x++) {
        const u = x / cols;
        const v = y / rows;
        let hNorm = 0;
        let energy = 0;
        let band = "unknown";

        registry.forEach((slot, i) => {
          const su = (i % cols) / cols;
          const sv = Math.floor(i / cols) / Math.max(rows, 1);
          const d = Math.hypot(u - su, v - sv);
          const str = (slot.strength || 0) / 100;
          if (str > 0) {
            hNorm += Math.exp(-d * d * 28) * str;
            energy += Math.exp(-d * d * 18) * str;
            if (str > (slot._peak || 0)) {
              band = slot.band || "unknown";
            }
          }
        });

        const center = operatorCenter(doc);
        antennas.forEach((a, i) => {
          const pt = itemCanvasPoint(a, center, i, antennas.length);
          const ax = pt.u;
          const ay = pt.v;
          const d = Math.hypot(u - ax, v - ay);
          const sig = (a.signal_avg || 20) / 100;
          hNorm += Math.exp(-d * d * 40) * sig * 0.6;
          energy += Math.sin(d * 18 - phase * 2 + i) * sig * 0.15;
        });

        dots.forEach((dot, i) => {
          const pt = itemCanvasPoint(dot, center, i, dots.length);
          const sig = clamp((dot.signal || 0) / 100, 0, 1);
          const dx = pt.u;
          const dy = pt.v;
          const d = Math.hypot(u - dx, v - dy);
          hNorm += Math.exp(-d * d * 55) * sig;
        });

        sectors.forEach((s, si) => {
          const pt = itemCanvasPoint(s, center, si, sectors.length);
          const d = Math.hypot(u - pt.u, v - pt.v);
          hNorm += Math.exp(-d * d * 22) * (s.confidence || 0.3) * 0.35;
        });

        const ripple =
          Math.sin(u * 14 + phase * 1.6) * Math.cos(v * 12 - phase * 1.3) * 0.08 +
          Math.sin((u + v) * 10 - phase * 2.1) * 0.05;
        hNorm = clamp(hNorm + ripple, 0, 1);
        row.push({ u, v, h: hNorm, energy, band });
      }
      mesh.push(row);
    }
    return mesh;
  }

  function projectSheetPoint(u, v, h, w, hCanvas, tilt) {
    const cx = w / 2;
    const cy = hCanvas / 2;
    const scaleX = w * 0.88;
    const scaleY = hCanvas * 0.42;
    const z = h * hCanvas * 0.22;
    const px = cx + (u - 0.5) * scaleX;
    const py = cy + (v - 0.5) * scaleY * tilt - z;
    return { x: px, y: py, z };
  }

  function drawRipplingFieldSheet(ctx, w, h, t, doc) {
    if (!sheetCache || sheetCache.w !== w || sheetCache.h !== h) {
      sheetCache = { w, h, mesh: null };
    }
    sheetCache.mesh = buildSheetMesh(w, h, doc);
    const mesh = sheetCache.mesh;
    const rows = mesh.length;
    const cols = mesh[0]?.length || 0;
    const tilt = 0.72;

    for (let y = 0; y < rows - 1; y++) {
      for (let x = 0; x < cols - 1; x++) {
        const p00 = mesh[y][x];
        const p10 = mesh[y][x + 1];
        const p01 = mesh[y + 1][x];
        const p11 = mesh[y + 1][x + 1];
        const avgH = (p00.h + p10.h + p01.h + p11.h) / 4;
        const rgb = FIELD_GREEN[p00.band] || FIELD_GREEN.unknown;
        const lit = 0.18 + avgH * 0.55;
        const alpha = clamp(0.04 + avgH * 0.28, 0.02, 0.42);

        const a = projectSheetPoint(p00.u, p00.v, p00.h, w, h, tilt);
        const b = projectSheetPoint(p10.u, p10.v, p10.h, w, h, tilt);
        const c = projectSheetPoint(p11.u, p11.v, p11.h, w, h, tilt);
        const d = projectSheetPoint(p01.u, p01.v, p01.h, w, h, tilt);

        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.lineTo(c.x, c.y);
        ctx.lineTo(d.x, d.y);
        ctx.closePath();
        ctx.fillStyle = `rgba(${Math.round(rgb[0] * lit)}, ${Math.round(rgb[1] * lit)}, ${Math.round(rgb[2] * lit)}, ${alpha})`;
        ctx.fill();

        if (avgH > 0.12) {
          ctx.strokeStyle = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${0.08 + avgH * 0.2})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }

    ctx.strokeStyle = greenRgb("unknown", 0.35);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let x = 0; x < cols; x += 3) {
      const p = mesh[Math.floor(rows / 2)][x];
      const pr = projectSheetPoint(p.u, p.v, p.h, w, h, tilt);
      if (x === 0) ctx.moveTo(pr.x, pr.y);
      else ctx.lineTo(pr.x, pr.y);
    }
    ctx.stroke();
  }

  function drawFieldGridTruth(ctx, w, h, t, doc) {
    const registry = doc.frequency_registry?.entries || [];
    if (!registry.length) return;
    const barW = w * 0.82;
    const barX = (w - barW) / 2;
    const barY = h - 36;
    const slotW = barW / Math.max(registry.length, 1);

    registry.forEach((slot, i) => {
      const str = (slot.strength || 0) / 100;
      const bh = 4 + str * 18;
      const x = barX + i * slotW;
      const rgb = FIELD_GREEN[slot.band] || FIELD_GREEN.unknown;
      ctx.fillStyle = slot.recognized
        ? `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${0.45 + str * 0.5})`
        : "rgba(30, 50, 38, 0.35)";
      ctx.fillRect(x + 0.5, barY - bh, Math.max(slotW - 1, 1), bh);
    });
    ctx.font = "9px ui-monospace, monospace";
    ctx.fillStyle = "rgba(200, 240, 210, 0.55)";
    ctx.fillText("frequency registry · every permitted slot", barX, barY + 14);
  }

  function drawAcreRing(ctx, w, h, t, acreFt) {
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) * 0.36;
    const pulse = 0.88 + Math.sin(t * 1.6) * 0.06;
    ctx.beginPath();
    ctx.arc(cx, cy, r * pulse, 0, Math.PI * 2);
    ctx.strokeStyle = greenRgb("unknown", 0.28 + Math.sin(t * 2) * 0.08);
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 10]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.font = "11px ui-monospace, monospace";
    ctx.fillStyle = greenRgb("unknown", 0.7);
    ctx.fillText(`~${acreFt || 55} ft home`, cx - 42, cy + r * pulse + 18);
  }

  async function drawSdfAt(ctx, assetId, x, y, color, scale, alpha, sdfPhase) {
    if (!global.NexusSdf) return;
    try {
      const pack = await NexusSdf.loadField(assetId);
      const c = document.createElement("canvas");
      const ph = sdfPhase || 0;
      const sc = scale * (1 + ph * 0.25);
      NexusSdf.renderSdf(c, pack, color, {
        scale: sc,
        glow: true,
        edge: 0.05,
        alphaBoost: alpha * (1 - ph * 0.5),
      });
      ctx.globalAlpha = alpha;
      ctx.drawImage(c, x - c.width / 2, y - c.height / 2);
      ctx.globalAlpha = 1;
    } catch (_) { /* sdf optional */ }
  }

  async function paintHero(canvas, doc, t) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 900;
    const h = canvas.clientHeight || 420;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const cx = w / 2;
    const cy = h / 2;
    const grad = ctx.createRadialGradient(cx, cy * 0.9, 0, cx, cy, Math.max(w, h) * 0.6);
    grad.addColorStop(0, "#061208");
    grad.addColorStop(0.4, "#030806");
    grad.addColorStop(1, "#010302");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    const antennas = doc.antennas || [];
    const acreFt = doc.home_protector?.acre_ft || 55;
    const center = operatorCenter(doc);

    drawRipplingFieldSheet(ctx, w, h, t, doc);
    drawAcreRing(ctx, w, h, t, acreFt);
    drawFieldGridTruth(ctx, w, h, t, doc);

    const mf = doc.material_field || {};
    if (mf.sectors?.length) {
      const r = Math.min(w, h) * 0.3;
      mf.sectors.forEach((s) => {
        const start = ((s.bearing_deg || 0) - (s.width_deg || 45) / 2 - 90) * (Math.PI / 180);
        const end = start + ((s.width_deg || 45) * Math.PI) / 180;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, r, start, end);
        ctx.closePath();
        ctx.fillStyle = s.color || greenRgb("unknown", 0.2);
        ctx.globalAlpha = 0.1 + (s.confidence || 0) * 0.18;
        ctx.fill();
        ctx.globalAlpha = 1;
      });
    }

    const sdfJobs = [];
    for (let i = 0; i < antennas.length; i++) {
      const a = antennas[i];
      const pt = itemCanvasPoint(a, center, i, antennas.length);
      const ax = pt.u * w;
      const ay = pt.v * h;
      const col = a.color || "#4de88a";
      const localPhase = (t * 0.9 + (a.pulse_phase || 0)) % 1;

      for (let p = 0; p < 3; p++) {
        const ph = (localPhase + p * 0.33) % 1;
        sdfJobs.push(drawSdfAt(ctx, "ring-pulse", ax, ay, col, 1.4 + p * 0.45, 0.32 * (1 - ph), ph));
      }
      sdfJobs.push(drawSdfAt(ctx, "antenna-bloom", ax, ay, col, 1.0 + Math.sin(t * 2 + i) * 0.12, 0.5, localPhase * 0.3));

      ctx.beginPath();
      ctx.arc(ax, ay, 6, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.shadowColor = col;
      ctx.shadowBlur = 16;
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.font = "10px ui-monospace, monospace";
      ctx.fillStyle = "rgba(240, 255, 245, 0.9)";
      ctx.fillText(a.device || `ant${i}`, ax + 10, ay - 6);
    }

    (doc.scan_dots || []).forEach((dot, i) => {
      const pt = itemCanvasPoint(dot, center, i, (doc.scan_dots || []).length);
      const sig = clamp((dot.signal || 0) / 100, 0.08, 1);
      const dx = pt.u * w;
      const dy = pt.v * h;
      const flicker = 0.65 + Math.sin(t * 3 + i) * 0.35;
      const tl = dot.threat_level || "none";
      ctx.beginPath();
      ctx.arc(dx, dy, 3 + sig * 2, 0, Math.PI * 2);
      ctx.fillStyle = dot.color || THREAT_COLORS[tl] || "#4de88a";
      ctx.globalAlpha = flicker * sig;
      ctx.fill();
      ctx.globalAlpha = 1;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, 10, 0, Math.PI * 2);
    const og = ctx.createRadialGradient(cx, cy, 0, cx, cy, 10);
    og.addColorStop(0, "#8af0b0");
    og.addColorStop(1, greenRgb("unknown", 0.15));
    ctx.fillStyle = og;
    ctx.fill();
    ctx.font = "bold 11px ui-monospace, monospace";
    ctx.fillStyle = "#f0fff4";
    ctx.fillText("YOU", cx + 14, cy + 4);

    await Promise.all(sdfJobs);
  }

  async function paintAntennaCard(canvas, antenna, t) {
    if (!canvas || !antenna) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.clientWidth || 160;
    const h = canvas.clientHeight || 120;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#020604";
    ctx.fillRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h / 2;
    const col = antenna.color || "#4de88a";
    const lp = (t + (antenna.pulse_phase || 0)) % 1;
    for (let p = 0; p < 2; p++) {
      const ph = (lp + p * 0.5) % 1;
      await drawSdfAt(ctx, "ring-pulse", cx, cy, col, 1.1 + p * 0.35, 0.38 * (1 - ph), ph);
    }
    await drawSdfAt(ctx, "antenna-bloom", cx, cy, col, 0.8, 0.48, lp);
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
  }

  function renderPulseChannels(el, channels, t) {
    if (!el) return;
    const ch = channels || [];
    if (!ch.length) {
      el.innerHTML = '<div class="empty">Pulse channels appear after first RF scan cycle.</div>';
      return;
    }
    el.innerHTML = ch.map((c, i) => {
      const e = c.energy || 0.05;
      const wobble = Math.sin(t * 2.5 + i * 0.7) * 0.12;
      const pct = Math.round(clamp(e + wobble, 0.02, 1) * 100);
      const rec = c.recognized ? "live" : "silent";
      const meta = c.strength != null ? `${c.strength}%` : rec;
      return `<div class="signals-channel${c.recognized ? " signals-channel-live" : ""}" style="--ch-color:${esc(c.color || '#4de88a')}">
        <div class="signals-channel-head">
          <span class="signals-channel-dot"></span>
          <strong>${esc(c.label || c.id)}</strong>
          <em>${esc(c.band || c.kind || "rf")}</em>
        </div>
        <div class="signals-channel-bar"><span style="width:${pct}%"></span></div>
        <div class="signals-channel-meta">${esc(meta)}${c.source_count != null && c.source_count ? ` · ${esc(String(c.source_count))} src` : ""}${c.fcc_id ? ` · <span class="fcc-id-chip">${esc(c.fcc_id)}</span>` : ""}${c.threat_tag && c.threat_tag !== "none" ? ` <span class="fcc-threat-tag level-${esc(c.threat_level || "watch")}">${esc(c.threat_tag)}</span>` : ""}</div>
      </div>`;
    }).join("");
  }

  function threatTagHtml(tag, level, label) {
    if (!tag || tag === "none") return '<span class="fcc-threat-tag level-none">permitted</span>';
    return `<span class="fcc-threat-tag level-${esc(level || "watch")}">${esc(label || tag)}</span>`;
  }

  function renderFccBanner(fcc) {
    const el = document.getElementById("signals-fcc-banner");
    if (!el) return;
    const st = fcc?.stats || {};
    const master = st.master_total ?? (fcc?.master_record?.stats || {}).total ?? 0;
    const jsonl = st.jsonl_lines ?? (fcc?.master_record?.stats || {}).jsonl_lines ?? 0;
    el.innerHTML = `<strong>FCC master record</strong> — ${esc(String(st.total ?? 0))} identified · ${esc(String(master))} stored · ${esc(String(jsonl))} log lines · <span style="color:#ff8a9a">${esc(String(st.threats ?? 0))} threats</span>`;
  }

  function renderFrequencyRegistry(doc) {
    const el = document.getElementById("signals-freq-registry");
    if (!el) return;
    const reg = doc.frequency_registry || {};
    const entries = reg.entries || [];
    if (!entries.length) {
      el.innerHTML = '<div class="empty">Frequency registry builds from FCC permitted bands…</div>';
      return;
    }
    const active = entries.filter((e) => e.recognized);
    el.innerHTML = `<div class="signals-freq-summary">
      <span><strong>${esc(String(reg.total_slots ?? entries.length))}</strong> slots</span>
      <span class="signals-freq-live"><strong>${esc(String(reg.recognized_slots ?? active.length))}</strong> recognized</span>
      <span><strong>${esc(String(reg.silent_slots ?? entries.length - active.length))}</strong> silent</span>
      <span>coverage <strong>${esc(String(reg.coverage_pct ?? 0))}%</strong></span>
    </div>
    <table class="honor-table signals-freq-table"><thead><tr>
      <th>Band</th><th>Ch</th><th>MHz</th><th>Strength</th><th>Status</th>
    </tr></thead><tbody>${entries.map((e) => `<tr class="${e.recognized ? "freq-live" : "freq-silent"}">
      <td>${esc(e.band || "—")}</td>
      <td>${e.channel != null ? esc(String(e.channel)) : "—"}</td>
      <td class="meta">${esc(String(e.freq_mhz ?? "—"))}</td>
      <td><strong>${esc(String(e.strength ?? 0))}%</strong></td>
      <td>${e.recognized ? '<span class="fcc-threat-tag level-none">recognized</span>' : '<span class="meta">silent</span>'}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderFccTable(fcc) {
    const el = document.getElementById("signals-fcc-table");
    if (!el) return;
    const masterRows = (fcc?.master_record?.records || []);
    const rows = (masterRows.length ? masterRows : (fcc?.identified || [])).slice(0, 64);
    if (!rows.length) {
      el.innerHTML = '<div class="empty">Scanning — FCC lookups populate after first RF cycle…</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table"><thead><tr>
      <th>Signal</th><th>FCC ID</th><th>Rule</th><th>Threat</th><th>Level</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>${esc(r.label || r.ssid || r.ip || r.kind || "—")}</strong>${r.bssid ? `<div class="meta">${esc(r.bssid)}</div>` : ""}</td>
      <td><span class="fcc-id-chip">${esc(r.fcc_id || "—")}</span></td>
      <td class="meta">${esc(r.fcc_rule || r.fcc_label || "—")}</td>
      <td>${threatTagHtml(r.threat_tag, r.level, r.label)}</td>
      <td>${esc(r.level || "none")}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderAntennaCards(doc, t) {
    const grid = document.getElementById("signals-antenna-grid");
    if (!grid) return;
    const antennas = doc.antennas || [];
    if (!antennas.length) {
      grid.innerHTML = '<div class="empty">No WiFi antenna fields detected — plug in wireless or enable Field RF.</div>';
      return;
    }
    grid.innerHTML = antennas.map((a, i) => `
      <div class="signals-antenna-card" style="--ant-color:${esc(a.color || '#4de88a')}">
        <canvas class="signals-antenna-canvas" data-ant-idx="${i}" width="160" height="120"></canvas>
        <div class="signals-antenna-info">
          <strong>${esc(a.device || "antenna")}</strong>
          <span class="meta">${esc(a.tuned_band || "—")} · ch ${esc(a.tuned_channel || "—")}</span>
          <span class="meta">${esc(a.state || "")} · scan ${esc(String(a.scan_count || 0))}</span>
          <span class="meta">sig max ${esc(String(a.signal_max || 0))}% · avg ${esc(String(a.signal_avg || 0))}</span>
        </div>
      </div>`).join("");
    grid.querySelectorAll(".signals-antenna-canvas").forEach((c) => {
      const idx = Number(c.dataset.antIdx);
      paintAntennaCard(c, antennas[idx], t);
    });
  }

  function renderOperatorStrip(doc) {
    const el = document.getElementById("signals-operator");
    if (!el) return;
    const op = doc?.operator_profile || doc?.field_radio?.operator || {};
    const name = op.display_name || "Operator";
    const addr = op.address || op.label || "";
    const lat = op.lat;
    const lon = op.lon;
    const gps = lat != null && lon != null
      ? `${Number(lat).toFixed(5)}°, ${Number(lon).toFixed(5)}°`
      : "GPS warming…";
    const urls = Array.isArray(op.urls) ? op.urls : [];
    const github = op.github || urls.find((u) => /github\.com/i.test(u)) || "";
    const xUrl = op.x || urls.find((u) => /x\.com|twitter\.com/i.test(u)) || "";
    const linkBits = [];
    if (github) linkBits.push(`<a href="${esc(github)}" target="_blank" rel="noopener">GitHub</a>`);
    if (xUrl) linkBits.push(`<a href="${esc(xUrl)}" target="_blank" rel="noopener">X</a>`);
    el.innerHTML = [
      `<strong>${esc(name)}</strong>`,
      addr ? `<span>${esc(addr)}</span>` : "",
      `<span class="signals-op-gps">${esc(gps)}</span>`,
      linkBits.length ? linkBits.join(" · ") : "",
      op.remember !== false ? '<span class="meta">remembered</span>' : "",
    ].filter(Boolean).join(" · ");
  }

  function renderAntennaBanner(fa) {
    const el = document.getElementById("signals-antenna-banner");
    if (!el) return;
    const a = fa || {};
    const ready = !!a.blaster_ready;
    el.className = `gov-merge-banner ${ready ? "blaster-ready" : "blaster-warming"}`;
    const tier = a.tier || (ready ? "blaster" : "warming");
    const mods = (a.modalities || []).join(", ") || "—";
    el.innerHTML = ready
      ? `<strong>BLASTER READY</strong> — score ${esc(String(a.score ?? "—"))}% · ${esc(tier)} · sub-µm ${a.sub_micron_accuracy ? "ON" : "off"} · modalities: ${esc(mods)}`
      : `<strong>Field antenna warming</strong> — score ${esc(String(a.score ?? "—"))}% · ${esc(tier)} · run Rescan antenna until blaster_ready · modalities: ${esc(mods)}`;
  }

  function renderAntennaReadiness(fa) {
    const el = document.getElementById("signals-antenna-readiness");
    if (!el) return;
    const checks = fa?.checks || [];
    if (!checks.length) {
      el.innerHTML = '<span class="meta">Readiness checks load after antenna cycle…</span>';
      return;
    }
    el.innerHTML = checks.map((c) =>
      `<span class="${c.ok ? "ok" : "fail"}">${esc(c.name)} ${c.ok ? "✓" : "✗"}</span>`
    ).join("");
  }

  function freqDisplay(s) {
    if (s.freq_label) return s.freq_label;
    if (s.band === "fm" && s.freq_mhz != null) return `${s.freq_mhz} MHz`;
    return s.freq_khz != null ? `${s.freq_khz} kHz` : "—";
  }

  function renderWimkStatus(tuned, wp) {
    const el = document.getElementById("signals-wimk-status");
    if (!el) return;
    const ws = tuned?.wimk_status || wp?.wimk_playback || {};
    const working = !!(tuned?.wimk_working ?? ws.working);
    const attempts = tuned?.playback_attempts || ws.attempts || [];
    const phys = ws.physics || tuned?.physics || {};
    const last = attempts.length ? attempts[attempts.length - 1] : {};
    if (working) {
      el.innerHTML = [
        '<span class="signals-freq-live">93.1 WIMK WORKING</span>',
        ws.working_method || tuned?.wimk_working_method ? `via <strong>${esc(ws.working_method || tuned.wimk_working_method)}</strong>` : "",
        ws.working_reason ? `(${esc(ws.working_reason)})` : "",
        ws.field_locked || tuned?.wimk_field_locked ? '<span class="signals-freq-live">3-FIELD LOCK</span>' : "",
        ws.ota_source ? esc(ws.ota_source) : "field_generator_spectrum",
        ws.snr_db != null ? `SNR ${esc(String(ws.snr_db))} dB` : "",
        ws.output_rms_dbfs != null ? `${esc(String(ws.output_rms_dbfs))} dBFS` : "",
        ws.crest_factor != null ? `crest ${esc(String(ws.crest_factor))}` : "",
        ws.spectral_flatness != null ? `flat ${esc(String(ws.spectral_flatness))}` : "",
        ws.program_audio ? '<span class="signals-freq-live">PROGRAM</span>' : "",
        ws.fields_active != null ? `${esc(String(ws.fields_active))} fields` : "",
        `${attempts.length || ws.attempt_count || 0} attempts`,
      ].filter(Boolean).join(" · ");
    } else if (attempts.length || ws.attempt_count) {
      el.innerHTML = [
        '<span style="color:#ffb0a8">93.1 WIMK trying…</span>',
        `attempt ${esc(String(last.attempt || attempts.length))}/${esc(String(ws.max_attempts || 10))}`,
        last.method ? esc(last.method) : "",
        last.error ? esc(last.error) : (last.working_reason || "warming 3-field spectrum"),
        ws.fields_active != null ? `${esc(String(ws.fields_active))} fields` : "3 fields",
        ws.listen_ready ? "field listen ready" : "",
      ].filter(Boolean).join(" · ");
    } else {
      el.innerHTML = '93.1 WIMK — <strong>3-field antenna</strong> tunes station · press Play (retries until program audio)';
    }
  }

  function updateRadioPlayer(tuned, playing) {
    const wrap = document.getElementById("signals-radio-player");
    const title = document.getElementById("signals-radio-player-title");
    const meta = document.getElementById("signals-radio-player-meta");
    const audio = document.getElementById("signals-radio-audio");
    if (!wrap || !title || !meta || !audio) return;
    if (!tuned || (!tuned.station_id && !tuned.caught && !tuned.ok && !tuned.heard)) {
      wrap.classList.remove("playing");
      title.textContent = "Field wave tuner · 93.1 WIMK K-Rock";
      meta.textContent = "Field antenna OTA · we are the hardware · Iron Mountain → Gladstone";
      audio.removeAttribute("src");
      return;
    }
    const st = tuned.station || {};
    const line = tuned.line || {};
    const sp = tuned.start_point || line.start_point || {};
    const ep = tuned.end_point || line.end_point || {};
    const inst = tuned.instability || {};
    const phys = inst.physics || {};
    title.textContent = `${tuned.freq_label || (tuned.freq_mhz ? tuned.freq_mhz + " MHz" : "")} · ${tuned.call_sign || st.call_sign || "FIELD"} — ${tuned.name || st.name || "field catch"}`;
    const yp = tuned.your_place || tuned.world_placement?.your_place || {};
    const selfRec = tuned.self || tuned.self_recognition || tuned.world_placement?.self || {};
    meta.textContent = [
      selfRec.recognized ? "SELF RECOGNIZED" : (selfRec.confidence != null ? `self ${Math.round(selfRec.confidence * 100)}%` : ""),
      yp.summary || "",
      sp.gps ? `tower ${sp.gps}` : (tuned.tower_gps ? `tower ${tuned.tower_gps}` : ""),
      ep.gps ? `you ${ep.gps}` : "",
      tuned.distance_label ? tuned.distance_label : "",
      tuned.bearing_deg != null ? `${tuned.bearing_deg}°` : "",
      inst.instability_index != null ? `instability ${inst.instability_index} (${inst.instability_class || "—"})` : "",
      phys.wavelength_m != null ? `λ ${phys.wavelength_m} m` : "",
      phys.fspl_db != null ? `${phys.fspl_db} dB FSPL` : "",
      inst.freq_mhz_corrected != null ? `tuned ${inst.freq_mhz_corrected} MHz` : "",
      tuned.ota_source || tuned.method || "field_generator_spectrum",
      playing || tuned.heard ? "HEARD" : (tuned.capture?.error || tuned.live_play?.error || "warming"),
    ].filter(Boolean).join(" · ");
    const audioUrl = tuned.audio_url || (tuned.catch || {}).audio_url || "";
    if (audioUrl && audio.getAttribute("src") !== audioUrl) {
      audio.src = audioUrl;
    }
    wrap.classList.toggle("playing", !!playing || !!tuned.caught);
    renderWimkStatus(tuned, lastDoc?.field_world_placement);
  }

  function renderPrototype(proto) {
    const meta = document.getElementById("signals-prototype-meta");
    const table = document.getElementById("signals-prototype-table");
    if (!table) return;
    const doc = proto || {};
    const read = doc.read || doc.field_read || {};
    const id = doc.identity || read.identity || {};
    const corr = read.corrections || {};
    if (meta) {
      meta.textContent = [
        doc.sounded || doc.heard ? "SOUNDED OFF" : "prototype ready",
        read.fidelity_pct != null ? `fidelity ${read.fidelity_pct}%` : "",
        id.call_sign ? id.call_sign : "",
        read.method || "generated_fields",
        doc.mesh_energy != null ? `mesh ${doc.mesh_energy}` : "",
      ].filter(Boolean).join(" · ") || "3 fields in one file — generated mesh reads every MHz";
    }
    const meshFields = (read.mesh || {}).fields || [];
    table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><tbody>
      <tr><td class="meta">Read</td><td><strong>${esc(read.freq_label || read.freq_mhz || "—")}</strong> · ${esc(id.name || "")}</td></tr>
      <tr><td class="meta">Fidelity</td><td><strong>${esc(String(read.fidelity_pct ?? "—"))}%</strong> boost ${esc(corr.fidelity_boost ?? "—")}</td></tr>
      <tr><td class="meta">Corrected</td><td>crosstalk ${esc(corr.crosstalk_corrected ?? "—")} · sway ${esc(corr.sway_corrected ?? "—")} · interference ${esc(corr.interference_corrected ?? "—")}</td></tr>
      <tr><td class="meta">3-field mesh</td><td>${meshFields.map((f) => `${esc(f.field_id)} ${esc(f.strength_pct)}%`).join(" · ") || "generate on read"}</td></tr>
      <tr><td class="meta">Tag</td><td><code>${esc(id.tag || "—")}</code> ${id.identified ? '<span class="signals-freq-live">IDENTIFIED</span>' : ""}</td></tr>
      <tr><td class="meta">Disk IQ</td><td><code>${esc(doc.capture?.iq_path || doc.demod?.iq_path || "—")}</code></td></tr>
      <tr><td class="meta">Spectrum SNR</td><td><strong>${esc(String(doc.snr_db ?? doc.demod?.snr_db ?? "—"))} dB</strong> · ${esc(doc.band || doc.demod?.band || "fm").toUpperCase()} ${esc((doc.demod || {}).method || "demod")}</td></tr>
      <tr><td class="meta">Level</td><td><strong>${esc(String(doc.output_rms_dbfs ?? doc.demod?.output_rms_dbfs ?? doc.audio_quality?.rms_dbfs ?? "—"))} dBFS</strong> polite · peak ${esc(doc.demod?.polite_peak_dbfs ?? "-6")} dBFS</td></tr>
      <tr><td class="meta">Crest</td><td><strong>${esc(String(doc.crest_factor ?? doc.audio_quality?.crest_factor ?? doc.demod?.crest_factor ?? "—"))}</strong> · flatness ${esc(String(doc.spectral_flatness ?? doc.audio_quality?.spectral_flatness ?? doc.demod?.spectral_flatness ?? "—"))}</td></tr>
      <tr><td class="meta">Program</td><td>${doc.program_audio || doc.audio_quality?.program_audio ? '<span class="signals-freq-live">PROGRAM AUDIO</span>' : '<span class="meta">warming tone check</span>'}</td></tr>
    </tbody></table>`;
  }

  function audioQualityFromDoc(doc) {
    const catchDoc = doc?.field_antenna_catch || doc?.catch || doc?.field_antenna?.catch || {};
    const demod = catchDoc.demod || doc?.demod || doc?.field_antenna_prototype?.demod || {};
    const q = catchDoc.audio_quality || demod.audio_quality || doc?.audio_quality || {};
    return {
      crest_factor: catchDoc.crest_factor ?? demod.crest_factor ?? q.crest_factor,
      spectral_flatness: catchDoc.spectral_flatness ?? demod.spectral_flatness ?? q.spectral_flatness,
      rms_dbfs: catchDoc.output_rms_dbfs ?? demod.output_rms_dbfs ?? q.rms_dbfs,
      program_audio: catchDoc.program_audio ?? demod.program_audio ?? q.program_audio,
      thresholds: q.thresholds || {},
    };
  }

  function renderAudioQuality(doc) {
    const meta = document.getElementById("signals-audio-quality-meta");
    const table = document.getElementById("signals-audio-quality-table");
    if (!table) return;
    const q = audioQualityFromDoc(doc);
    if (meta) {
      meta.textContent = [
        q.program_audio ? "PROGRAM AUDIO VALIDATED" : "awaiting program dynamics",
        q.crest_factor != null ? `crest ${q.crest_factor}` : "",
        q.spectral_flatness != null ? `flatness ${q.spectral_flatness}` : "",
        q.rms_dbfs != null ? `${q.rms_dbfs} dBFS` : "",
      ].filter(Boolean).join(" · ") || "crest · spectral flatness · RMS — polite listening level";
    }
    const th = q.thresholds || {};
    table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><tbody>
      <tr><td class="meta">Crest factor</td><td><strong>${esc(String(q.crest_factor ?? "—"))}</strong> min ${esc(String(th.crest_min ?? "2.5"))}</td></tr>
      <tr><td class="meta">Spectral flatness</td><td><strong>${esc(String(q.spectral_flatness ?? "—"))}</strong> min ${esc(String(th.flatness_min ?? "0.02"))}</td></tr>
      <tr><td class="meta">RMS</td><td><strong>${esc(String(q.rms_dbfs ?? "—"))} dBFS</strong> polite ${esc(String(th.polite_rms_dbfs ?? "-20"))}</td></tr>
      <tr><td class="meta">Verdict</td><td>${q.program_audio ? '<span class="signals-freq-live">PROGRAM</span>' : '<span class="meta">not program yet</span>'}</td></tr>
    </tbody></table>`;
  }

  function renderHardware(doc) {
    const meta = document.getElementById("signals-hardware-meta");
    const table = document.getElementById("signals-hardware-table");
    if (!table) return;
    const hw = doc?.field_hardware || {};
    if (!hw.schema && !hw.host) {
      if (meta) meta.textContent = "Field hardware warming…";
      table.innerHTML = '<div class="empty">Awaiting field publish — run ./nexus.sh</div>';
      return;
    }
    try {
      if (meta) {
        meta.textContent = [
          hw.standalone ? "FIELD STANDALONE" : "installed",
          hw.dongle_present ? "RTL dongle" : "3-field antenna",
          hw.we_are_the_antenna ? `${hw.antenna_fields} fields` : "",
          `${(hw.field_tools || {}).ready_count || 0}/${(hw.field_tools || {}).count || 0} tools ready`,
          hw.host?.hostname || "",
        ].filter(Boolean).join(" · ");
      }
      const usb = (hw.usb || []).filter((d) => d.rtl_sdr).slice(0, 3);
      const nets = (hw.net || []).filter((n) => n.carrier).slice(0, 4);
      const tools = (hw.field_tools?.tools || []).filter((t) => t.ready).slice(0, 6);
      table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><tbody>
        <tr><td class="meta">USB RTL</td><td>${usb.length ? usb.map((d) => esc(d.usb_id)).join(" · ") : "none (field antenna mode)"}</td></tr>
        <tr><td class="meta">Net up</td><td>${nets.length ? nets.map((n) => esc(n.name)).join(" · ") : "—"}</td></tr>
        <tr><td class="meta">Audio</td><td>${(hw.audio || []).map((a) => esc(a.label || a.index)).join(" · ") || "—"}</td></tr>
        <tr><td class="meta">Tools</td><td>${tools.map((t) => `<code>${esc(t.id)}</code>`).join(" ") || "run field-drive publish_tools"}</td></tr>
        <tr><td class="meta">State</td><td><code>${esc(hw.state_dir || "—")}</code></td></tr>
      </tbody></table>`;
    } catch (_) {
      if (meta) meta.textContent = "Hardware probe warming…";
      table.innerHTML = '<div class="empty">Field hardware slice missing</div>';
    }
  }

  function renderHazardOnset(doc) {
    const meta = document.getElementById("signals-hazard-meta");
    const table = document.getElementById("signals-hazard-table");
    if (!table) return;
    const hz = doc?.field_hazard_onset || {};
    const last = hz.last || hz.panel?.last || {};
    const guard = last.guard_action || last.guard?.action || "—";
    if (meta) {
      meta.textContent = [
        hz.proactive ? "PROACTIVE" : "monitor",
        last.onset_us != null ? `${last.onset_us} µs onset` : "",
        guard !== "—" ? guard : "",
      ].filter(Boolean).join(" · ") || "microsecond onset guard";
    }
    table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><tbody>
      <tr><td class="meta">Status</td><td><strong>${esc(hz.status || (last.ceased ? "ceased" : "ready"))}</strong></td></tr>
      <tr><td class="meta">Onset</td><td>${esc(String(last.onset_us ?? "—"))} µs · sample ${esc(String(last.onset_sample ?? "—"))}</td></tr>
      <tr><td class="meta">Guard</td><td><code>${esc(guard)}</code></td></tr>
      <tr><td class="meta">Hazard</td><td>${esc(last.hazard_kind || last.hazard?.kind || "—")}</td></tr>
    </tbody></table>`;
  }

  async function prototypeSoundOff(opts) {
    const body = { action: "sound_off", freq_mhz: 93.1, station_id: "wimk-931", call_sign: "WIMK", play: true, ...opts };
    const res = await fetch("/api/field-antenna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const out = await res.json();
    lastTuned = out;
    renderPrototype(out);
    renderInstability(out.instability);
    renderTriPanel(out, null);
    const audio = document.getElementById("signals-radio-audio");
    const audioUrl = out.audio_url || "";
    if (audioUrl && audio) {
      audio.src = audioUrl + (audioUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
      try {
        await audio.play();
      } catch (_) { /* server paplay */ }
    }
    updateRadioPlayer(out, !!out.playing || !!out.heard || !!out.sounded);
    return out;
  }

  function renderInstability(inst) {
    const meta = document.getElementById("signals-instability-meta");
    const table = document.getElementById("signals-instability-table");
    if (!table) return;
    const doc = inst || {};
    const hw = doc.hardware || {};
    const phys = doc.physics || {};
    if (meta) {
      meta.textContent = [
        doc.instability_index != null ? `index ${doc.instability_index} (${doc.instability_class || "—"})` : "",
        doc.stable_enough ? "STABLE" : "warming fields",
        "3-field antenna",
        doc.listen_anyway ? "listen ready" : "listen blocked",
        phys.corrected_hz ? `${phys.corrected_hz} Hz` : "",
      ].filter(Boolean).join(" · ") || "Run field wave tune — 3 fields detect instability before field-wave-fm";
    }
    const blockers = doc.listen_blockers || [];
    table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><tbody>
      <tr><td class="meta">λ / FSPL</td><td><code>${esc(phys.wavelength_m ?? doc.wavelength_m ?? "—")} m</code> · <strong>${esc(String(phys.fspl_db ?? doc.path_loss_db ?? "—"))} dB</strong></td></tr>
      <tr><td class="meta">Freq lock</td><td><code>${esc(doc.freq_mhz)} MHz</code> → <code>${esc(doc.freq_mhz_corrected ?? doc.freq_mhz)} MHz</code> ppm ${esc(doc.ppm_correction ?? 0)}</td></tr>
      <tr><td class="meta">Field wave</td><td>field-wave-fm ${hw.field_wave_fm ? "yes" : "no"} · 3-field antenna · ppm ${esc(hw.ppm_correction ?? 0)}</td></tr>
      <tr><td class="meta">Spread</td><td>strength ${esc(doc.field_strength_spread ?? "—")}% · bearing ${esc(doc.bearing_spread_deg ?? "—")}° · drift ${esc(doc.history_drift ?? "—")}</td></tr>
      ${blockers.length ? `<tr><td class="meta">Blockers</td><td style="color:#ffb0a8">${blockers.map((b) => esc(b)).join(" · ")}</td></tr>` : ""}
    </tbody></table>`;
  }

  function renderTriPanel(tri, antenna) {
    const meta = document.getElementById("signals-tri-meta");
    const fieldsEl = document.getElementById("signals-tri-fields");
    if (!fieldsEl) return;
    const cmp = tri?.tri_compare || tri || antenna?.tri_receive?.tri_compare || {};
    const rows = cmp.fields || [];
    const conf = cmp.tri_confidence ?? tri?.tri_confidence;
    const pin = cmp.pinpoint_gps || tri?.pinpoint_gps || "—";
    if (meta) {
      meta.textContent = [
        conf != null ? `confidence ${Math.round(conf * 100)}%` : "",
        cmp.tri_ready ? "TRI READY" : "warming tri",
        pin !== "—" ? `pinpoint ${pin}` : "",
      ].filter(Boolean).join(" · ") || "Compare 3 fields to your GPS, then field wave tune 93.1 WIMK";
    }
    if (!rows.length) {
      fieldsEl.innerHTML = '<div class="meta">Run 3-field pinpoint & listen to compare Gladstone, Escanaba, Marquette vs operator GPS.</div>';
      return;
    }
    fieldsEl.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><thead><tr>
      <th>Field</th><th>vs GPS</th><th>→ target</th><th>Strength</th>
    </tr></thead><tbody>${rows.map((f) => `<tr>
      <td>${esc(f.label || f.field_id)}</td>
      <td class="meta">${esc(f.operator_match_label || "—")}</td>
      <td class="meta">${esc(f.distance_to_target_label || "—")} · ${esc(String(f.bearing_to_target_deg ?? "—"))}°</td>
      <td><strong>${esc(String(f.signal_strength_pct ?? "—"))}%</strong></td>
    </tr>`).join("")}</tbody></table>`;
  }

  async function triListenFrequency(opts) {
    const statusEl = document.getElementById("signals-wimk-status");
    if (statusEl) statusEl.textContent = "93.1 WIMK — trying playback paths until working…";
    const body = { action: "listen", freq_mhz: 93.1, station_id: "wimk-931", call_sign: "WIMK", live_play: true, ota_only: true, ...opts };
    const res = await fetch("/api/field-antenna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const heard = await res.json();
    lastTuned = heard;
    renderWorldPlacement(heard.world_placement || lastDoc?.field_world_placement);
    renderInstability(heard.instability);
    renderTriPanel(heard, null);
    const audio = document.getElementById("signals-radio-audio");
    const audioUrl = heard.audio_url || "";
    if (audioUrl && audio) {
      audio.src = audioUrl;
      try {
        await audio.play();
      } catch (_) { /* server may paplay live */ }
    }
    updateRadioPlayer(heard, !!heard.playing || !!heard.heard);
    return heard;
  }

  async function catchRadioFrequency(opts) {
    const body = { action: "catch", freq_mhz: 93.1, station_id: "wimk-931", call_sign: "WIMK", ...opts };
    const res = await fetch("/api/field-antenna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const caught = await res.json();
    lastTuned = caught;
    renderInstability(caught.instability);
    renderTriPanel(caught, null);
    const audio = document.getElementById("signals-radio-audio");
    const audioUrl = caught.audio_url || "";
    if (caught.ok && audioUrl && audio) {
      audio.src = audioUrl;
      try {
        await audio.play();
        updateRadioPlayer(caught, true);
      } catch (_) {
        updateRadioPlayer(caught, !!caught.caught);
      }
    } else {
      updateRadioPlayer(caught, !!caught.caught);
    }
    return caught;
  }

  async function tuneWorldBand(band) {
    const res = await fetch("/api/field-antenna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "listen", band, live_play: true, ota_only: true }),
      cache: "no-store",
    });
    const heard = await res.json();
    lastTuned = heard;
    renderWorldPlacement(heard.world_placement || lastDoc?.field_world_placement);
    renderInstability(heard.instability);
    renderTriPanel(heard, null);
    const audio = document.getElementById("signals-radio-audio");
    const audioUrl = heard.audio_url || "";
    if (audioUrl && audio) {
      audio.src = audioUrl + (audioUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
      try { await audio.play(); } catch (_) {}
    }
    updateRadioPlayer(heard, !!heard.playing || !!heard.heard);
    return heard;
  }

  function bindWorldPlacementTune() {
    if (worldTuneBound) return;
    worldTuneBound = true;
    document.getElementById("signals-world-bands")?.addEventListener("click", async (ev) => {
      const btn = ev.target.closest("[data-world-band]");
      if (!btn) return;
      btn.disabled = true;
      try {
        await tuneWorldBand(btn.getAttribute("data-world-band"));
      } finally {
        btn.disabled = false;
      }
    });
  }

  function renderWorldPlacement(wp) {
    const meta = document.getElementById("signals-world-meta");
    const bandsEl = document.getElementById("signals-world-bands");
    const placeEl = document.getElementById("signals-world-placements");
    if (!bandsEl && !placeEl) return;
    const doc = wp || {};
    const yp = doc.your_place || {};
    const selfRec = doc.self || doc.self_recognition || {};
    const stats = doc.stats || {};
    const db = doc.station_tower_db || {};
    if (meta) {
      meta.innerHTML = [
        selfRec.recognized ? '<span class="signals-freq-live">SELF RECOGNIZED</span>' : '<span class="meta">recognizing self…</span>',
        yp.summary ? esc(yp.summary) : "",
        stats.stations_identified != null ? `${stats.stations_identified} stations · ${stats.tower_gps ?? 0} towers GPS` : "",
        yp.in_range_total != null ? `${yp.in_range_total} in range` : "",
      ].filter(Boolean).join(" · ");
    }
    if (bandsEl) {
      const bandKeys = ["fm", "am", "lw", "sw"];
      bandsEl.innerHTML = bandKeys.map((band) => {
        const b = (doc.bands || {})[band] || {};
        const count = b.in_range ?? b.total ?? 0;
        return `<button type="button" class="signals-radio-tune-btn" data-world-band="${esc(band)}" style="margin:2px 4px 2px 0;font-size:0.72rem;">${esc((b.label || band).toUpperCase())} <strong>${esc(String(count))}</strong></button>`;
      }).join("");
      bindWorldPlacementTune();
    }
    const rows = (doc.placements || []).filter((p) => p.role === "transmitter").slice(0, 12);
    const inRange = (db.in_range_stations || doc.identified_stations || []).filter((s) => s.in_range).slice(0, 8);
    if (placeEl) {
      if (!rows.length && !inRange.length) {
        placeEl.innerHTML = '<div class="meta">Scan bands from operator GPS — stations and tower placements populate here.</div>';
        return;
      }
      const selfRow = `<tr><td class="meta">You</td><td><strong>${selfRec.recognized ? "SELF" : "operator"}</strong> · ${esc(yp.operator_gps || doc.operator?.gps || "—")}</td><td>${selfRec.home_match_label ? esc(selfRec.home_match_label) : "—"}</td></tr>`;
      const towerRows = (inRange.length ? inRange : rows).map((p) => `<tr>
        <td><span class="signals-freq-live">${esc(p.call_sign || p.label || "—")}</span></td>
        <td>${esc(p.freq_label || (p.freq_mhz != null ? p.freq_mhz + " MHz" : p.freq_khz != null ? p.freq_khz + " kHz" : "—"))} · ${esc(p.band || "")}</td>
        <td class="meta">${esc(p.tower_gps || p.gps || "—")} · ${esc(p.distance_label || "—")}${p.bearing_deg != null ? ` · ${esc(String(p.bearing_deg))}°` : ""}</td>
      </tr>`).join("");
      placeEl.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:4px;"><thead><tr>
        <th>Station</th><th>Band</th><th>Tower GPS · range</th>
      </tr></thead><tbody>${selfRow}${towerRows}</tbody></table>`;
    }
  }

  function bindRadioTune() {
    if (radioTuneBound) return;
    radioTuneBound = true;
    document.getElementById("signals-radio-tune-931")?.addEventListener("click", async () => {
      const btn = document.getElementById("signals-radio-tune-931");
      if (btn) btn.disabled = true;
      try {
        await triListenFrequency({ station_id: "wimk-931", freq_mhz: 93.1, call_sign: "WIMK" });
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    document.getElementById("signals-radio-tri-listen")?.addEventListener("click", async () => {
      const btn = document.getElementById("signals-radio-tri-listen");
      if (btn) btn.disabled = true;
      try {
        await triListenFrequency({ station_id: "wimk-931", freq_mhz: 93.1, call_sign: "WIMK" });
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    document.getElementById("signals-prototype-soundoff")?.addEventListener("click", async () => {
      const btn = document.getElementById("signals-prototype-soundoff");
      if (btn) btn.disabled = true;
      try {
        await prototypeSoundOff({ station_id: "wimk-931", freq_mhz: 93.1, call_sign: "WIMK" });
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    const audio = document.getElementById("signals-radio-audio");
    audio?.addEventListener("playing", () => updateRadioPlayer(lastTuned, true));
    audio?.addEventListener("pause", () => updateRadioPlayer(lastTuned, false));
    audio?.addEventListener("error", () => updateRadioPlayer(lastTuned, false));
  }

  function bindRadioSearch() {
    if (radioSearchBound) return;
    radioSearchBound = true;
    const input = document.getElementById("signals-radio-search");
    const menu = document.getElementById("signals-radio-menu");
    if (!input || !menu) return;
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      const filtered = !q
        ? lastRadioStations
        : lastRadioStations.filter((s) =>
            [s.call_sign, s.name, s.city, s.country, String(s.freq_khz), String(s.freq_mhz), s.freq_label, s.tower_gps]
              .filter(Boolean)
              .join(" ")
              .toLowerCase()
              .includes(q)
          );
      renderRadioMenu(menu, filtered);
    });
  }

  function renderRadioMenu(menu, stations) {
    if (!menu) return;
    if (!stations.length) {
      menu.innerHTML = '<div class="empty">No stations match filter — adjust GPS or search.</div>';
      return;
    }
    menu.innerHTML = stations.map((s, i) => `
      <div class="signals-radio-station legal" role="option" data-radio-idx="${i}" data-station-id="${esc(s.id || "")}" title="${esc(s.tower_gps || "")}">
        <span class="signals-radio-freq">${esc(freqDisplay(s))}</span>
        <div>
          <strong>${esc(s.call_sign || "—")}</strong> · ${esc(s.name || "")}
            ${s.playable ? '<span class="signals-radio-play">◎ catch</span>' : ""}
            <div class="signals-radio-tower">${esc(s.city || "")} ${esc(s.state || s.country || "")} · point ${esc(s.tower_gps || (s.lat != null ? s.lat + ", " + s.lon : "—"))} · ${esc(s.distance_label || "—")}</div>
        </div>
        <span class="meta">${esc(s.tier || "")} · ${esc(String(s.clarity_pct ?? 0))}%</span>
      </div>`).join("");
    menu.querySelectorAll(".signals-radio-station").forEach((el) => {
      el.addEventListener("click", async () => {
        menu.querySelectorAll(".signals-radio-station").forEach((x) => x.classList.remove("selected"));
        el.classList.add("selected");
        const idx = parseInt(el.getAttribute("data-radio-idx") || "0", 10);
        const st = stations[idx];
        if (st?.playable || st?.catch_target) {
          const body = {
            action: "listen",
            station_id: st.id,
            call_sign: st.call_sign,
            live_play: true,
            ota_only: true,
          };
          if (st.freq_mhz != null) body.freq_mhz = st.freq_mhz;
          if (st.freq_khz != null) body.freq_khz = st.freq_khz;
          const res = await fetch("/api/field-antenna", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            cache: "no-store",
          });
          const heard = await res.json();
          lastTuned = heard;
          renderPrototype(heard);
          renderInstability(heard.instability);
          renderTriPanel(heard, null);
          const audio = document.getElementById("signals-radio-audio");
          const audioUrl = heard.audio_url || "";
          if (audioUrl && audio) {
            audio.src = audioUrl + (audioUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
            try { await audio.play(); } catch (_) {}
          }
          updateRadioPlayer(heard, !!heard.playing || !!heard.heard);
        }
      });
    });
  }

  function renderRadioCatcher(radio) {
    const meta = document.getElementById("signals-radio-meta");
    const menu = document.getElementById("signals-radio-menu");
    const spec = document.getElementById("signals-radio-spectrum");
    const illegal = document.getElementById("signals-radio-illegal");
    if (!menu) return;
    const r = radio || {};
    const st = r.stats || {};
    const boost = r.field_boost || {};
    if (meta) {
      meta.innerHTML = [
        `<span>crystal <strong>${esc(r.crystal_clarity || "warming")}</strong></span>`,
        `<span>boost <strong>${esc(String(Math.round((boost.boost || 0) * 100)))}%</strong></span>`,
        `<span>menu <strong>${esc(String(st.menu_count ?? 0))}</strong> legal</span>`,
        `<span>FM <strong>${esc(String(st.fm_in_range ?? 0))}</strong> local</span>`,
        `<span style="color:#ff6a82">illegal <strong>${esc(String(st.illegal_slots ?? 0))}</strong></span>`,
        `<span>FCC stored <strong>${esc(String((r.fcc_master || {}).total_records ?? 0))}</strong></span>`,
        boost.world_tune ? '<span class="signals-freq-live">world tune ON</span>' : "",
      ].filter(Boolean).join("");
    }
    lastRadioStations = r.station_menu || [];
    lastTuned = r.tuned || lastTuned;
    bindRadioSearch();
    bindRadioTune();
    const tunedDoc = r.tuned || r.catch || global.lastPanelData?.field_wave_tuner || {};
    renderInstability(tunedDoc.instability || global.lastPanelData?.field_instability);
    renderTriPanel(tunedDoc, { tri_receive: (global.lastPanelData?.field_antenna || {}).tri_receive });
    updateRadioPlayer(lastTuned || tunedDoc, !!(lastTuned?.playing || tunedDoc?.playing || tunedDoc?.heard));
    if (!lastRadioStations.length) {
      menu.innerHTML = '<div class="empty">Set operator GPS — legal stations appear for your 1940s catcher range.</div>';
    } else {
      const q = document.getElementById("signals-radio-search")?.value?.trim().toLowerCase() || "";
      const filtered = !q ? lastRadioStations : lastRadioStations.filter((s) =>
        [s.call_sign, s.name, s.city, s.country, String(s.freq_khz), String(s.freq_mhz), s.freq_label, s.tower_gps].filter(Boolean).join(" ").toLowerCase().includes(q)
      );
      renderRadioMenu(menu, filtered);
    }
    const fmSlots = (r.spectrum || []).filter((x) => x.band === "fm");
    const amSlots = (r.spectrum || []).filter((x) => x.band === "am").slice(0, 80);
    const specSlots = fmSlots.length ? fmSlots : amSlots;
    if (spec) {
      spec.innerHTML = specSlots.map((slot) =>
        `<span class="signals-radio-slot ${esc(slot.status || "silent")}" title="${esc(slot.label || (slot.freq_mhz ? slot.freq_mhz + " MHz" : slot.freq_khz + " kHz"))}"></span>`
      ).join("") || '<span class="meta">AM/FM spectrum builds with GPS…</span>';
    }
    const pirates = r.illegal_frequencies || [];
    if (illegal) {
      if (!pirates.length) {
        illegal.innerHTML = '<div class="meta">No illegal in-band frequencies in current AM window.</div>';
      } else {
        illegal.innerHTML = `<strong style="color:#ff6a82">Illegal frequencies (red)</strong>
          <div class="signals-radio-scroll" style="max-height:120px;margin-top:6px;">${pirates.slice(0, 24).map((p) => `
            <div class="signals-radio-station illegal">
              <span class="signals-radio-freq">${esc(String(p.freq_khz))}</span>
              <div><strong>UNLICENSED</strong> · ${esc(p.band || "am")} band<div class="signals-radio-tower">${esc(p.label || "")}</div></div>
              <span class="fcc-threat-tag level-critical">pirate</span>
            </div>`).join("")}</div>`;
      }
    }
  }

  function renderCrosstalk(ct) {
    const meta = document.getElementById("signals-crosstalk-meta");
    const table = document.getElementById("signals-crosstalk-table");
    if (!table) return;
    const doc = ct || {};
    const illegal = doc.illegal_crosstalk || [];
    const enforced = (doc.stats || {}).enforced_at_start ?? 0;
    if (meta) {
      meta.textContent = [
        `${illegal.length} illegal line touch`,
        `${enforced} blocked at start`,
        `${(doc.stats || {}).violators_tracked ?? 0} violators tracked`,
        doc.target_mhz ? `target ${doc.target_mhz} MHz` : "",
      ].filter(Boolean).join(" · ");
    }
    const rows = [...illegal, ...(doc.legal_crosstalk || []).slice(0, 4)];
    if (!rows.length) {
      table.innerHTML = '<div class="meta">No crosstalk on our lines — rescan antenna to populate.</div>';
      return;
    }
    table.innerHTML = `<table class="honor-table" style="font-size:0.72rem;margin-top:6px;"><thead><tr>
      <th>Class</th><th>Start (their end)</th><th>End (our line)</th><th>Counter</th>
    </tr></thead><tbody>${rows.map((r) => {
      const start = r.start_point || {};
      const end = r.end_point || {};
      const cm = r.countermeasure || {};
      return `<tr>
        <td><span class="fcc-threat-tag level-${esc(r.severity || "medium")}">${esc(r.classification || "")}</span></td>
        <td class="meta">${esc(start.label || start.gps || "—")}</td>
        <td class="meta">${esc(end.gps || end.label || "—")}</td>
        <td>${cm.enforced ? '<span class="signals-freq-live">BLOCKED AT START</span>' : esc(r.mitigation || "—")}</td>
      </tr>`;
    }).join("")}</tbody></table>`;
  }

  function renderSignalsMeta(doc) {
    const motto = document.getElementById("signals-motto");
    if (motto) {
      motto.innerHTML = FIELD_ANTENNA_REMOVED
        ? `<strong>Signals</strong> — ${esc(doc.tagline || doc.motto || "WiFi and wire pulse scan — field antenna removed")}`
        : `<strong>Signals · Field Antennas</strong> — ${esc(doc.tagline || doc.motto || "")}`;
    }
    const stats = document.getElementById("signals-stats");
    const st = doc.stats || {};
    const ant = doc.antenna || {};
    const fa = doc.field_antenna || {};
    const fr = doc.field_radio || {};
    if (stats) {
      stats.innerHTML = [
        ["Blaster", fa.blaster_ready ? "READY" : "warming"],
        ["Score", fa.score != null ? `${fa.score}%` : "—"],
        ["Radio", (fr.stats || {}).menu_count ?? (fr.station_menu || []).length ?? 0],
        ["Illegal", (fr.stats || {}).illegal_slots ?? (fr.illegal_frequencies || []).length ?? 0],
        ["Antennas", st.antenna_fields ?? 0],
        ["Pulses", st.pulse_channels ?? 0],
        ["Freq slots", st.frequency_slots ?? 0],
        ["Coverage", st.frequency_coverage_pct != null ? `${st.frequency_coverage_pct}%` : "—"],
        ["FCC IDs", st.fcc_identified ?? 0],
      ].map(([k, v]) => `<span class="signals-stat"><span class="signals-stat-label">${esc(k)}</span><strong>${esc(String(v))}</strong></span>`).join("");
    }
    renderOperatorStrip(doc);
    if (!FIELD_ANTENNA_REMOVED) {
      renderAntennaBanner(fa);
      renderAntennaReadiness(fa);
    }
    renderFccBanner(doc.fcc);
    renderFccTable(doc.fcc);
    renderFrequencyRegistry(doc);
    renderRadioCatcher(doc.field_radio);
    renderWorldPlacement(doc.field_world_placement);
    renderWimkStatus(null, doc.field_world_placement);
    renderCrosstalk(doc.crosstalk);
    renderInstability(doc.field_instability || (doc.field_wave_tuner || {}).instability);
    renderPrototype(doc.field_antenna_prototype || doc.prototype);
    renderAudioQuality(doc);
    renderHardware(doc);
    renderHazardOnset(doc);
  }

  function bindSignalsRefresh() {
    if (refreshBound) return;
    refreshBound = true;
    document.getElementById("signals-refresh")?.addEventListener("click", async () => {
      const btn = document.getElementById("signals-refresh");
      if (btn) btn.disabled = true;
      try {
        await fetch("/api/field", { method: "POST", cache: "no-store" });
        const res = await fetch("/api/field", { cache: "no-store" });
        const doc = await res.json();
        renderSignalsField(mergeSignalsPayload(doc));
        if (global.refresh) global.refresh();
      } catch (_) {
        if (global.refresh) global.refresh();
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    if (!testBound) {
      testBound = true;
      document.getElementById("signals-antenna-test")?.addEventListener("click", async () => {
        const btn = document.getElementById("signals-antenna-test");
        if (btn) btn.disabled = true;
        try {
          const res = await fetch("/api/field-antenna", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "test" }),
            cache: "no-store",
          });
          const test = await res.json();
          const banner = document.getElementById("signals-antenna-banner");
          if (banner) {
            banner.textContent = test.blaster_ready
              ? `BLASTER TEST PASS — score ${test.score}%`
              : `BLASTER TEST — score ${test.score}% — not ready yet`;
          }
          if (global.refresh) global.refresh();
        } catch (_) {
          if (global.refresh) global.refresh();
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    }
  }

  function tick() {
    if (!isSignalsActive()) {
      stopAnimation();
      return;
    }
    phase += 0.016;
    sheetCache = null;
    const hero = document.getElementById("signals-field-hero");
    if (hero && lastDoc) paintHero(hero, lastDoc, phase);
    renderPulseChannels(document.getElementById("signals-channels"), lastDoc?.pulse_channels, phase);
    renderAntennaCards(lastDoc, phase);
    animId = requestAnimationFrame(tick);
  }

  function startAnimation() {
    stopAnimation();
    if (isSignalsActive()) animId = requestAnimationFrame(tick);
  }

  function renderSignalsField(doc) {
    lastDoc = mergeSignalsPayload(typeof doc?.signals_field === "object" ? doc : { signals_field: doc });
    sheetCache = null;
    renderSignalsMeta(lastDoc);
    renderPulseChannels(document.getElementById("signals-channels"), lastDoc.pulse_channels, phase);
    renderAntennaCards(lastDoc, phase);
    const hero = document.getElementById("signals-field-hero");
    if (hero) paintHero(hero, lastDoc, phase);
    if (!heroBound) {
      heroBound = true;
      window.addEventListener("resize", () => {
        sheetCache = null;
        if (lastDoc && isSignalsActive()) paintHero(document.getElementById("signals-field-hero"), lastDoc, phase);
      });
    }
    bindSignalsRefresh();
    startAnimation();
  }

  function onSignalsViewActivated() {
    startAnimation();
  }

  function onSignalsViewDeactivated() {
    stopAnimation();
  }

  global.mergeSignalsPayload = mergeSignalsPayload;
  global.renderSignalsField = renderSignalsField;
  global.onSignalsViewActivated = onSignalsViewActivated;
  global.onSignalsViewDeactivated = onSignalsViewDeactivated;
})(window);