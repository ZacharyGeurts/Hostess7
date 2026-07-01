/**
 * Thermal Manager — NEXUS C2 gorgeous operator surface for field thermal guard.
 */
(function () {
  "use strict";

  const GAUGE_C = 2 * Math.PI * 82;
  const REFRESH_MS = 8000;

  const $ = (id) => document.getElementById(id);

  function panelPort() {
    try {
      return window.parent?.document?.body?.dataset?.nexusPanelPort
        || document.body?.dataset?.nexusPanelPort
        || "9477";
    } catch {
      return "9477";
    }
  }

  function panelBase() {
    return `http://127.0.0.1:${panelPort()}`;
  }

  async function fetchPanel(path) {
    const url = path.startsWith("http") ? path : `${panelBase()}${path.startsWith("/") ? path : `/${path}`}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path} HTTP ${res.status}`);
    return res.json();
  }

  function fmtNum(n, digits = 1) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    const v = Number(n);
    if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)}G`;
    if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
    if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
    return v.toFixed(digits);
  }

  function setGauge(pct) {
    const fill = $("qtm-gauge-fill");
    const val = $("qtm-headroom-val");
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    if (fill) {
      fill.style.strokeDashoffset = String(GAUGE_C * (1 - p / 100));
    }
    if (val) val.textContent = p.toFixed(1);
  }

  function setLevel(level) {
    const pill = $("qtm-level");
    if (!pill) return;
    const lv = String(level || "ok").toLowerCase();
    pill.dataset.level = lv;
    const labels = {
      ok: "STABLE",
      warn: "ADVISORY",
      crit: "CRITICAL",
      unknown: "NO SENSOR",
    };
    pill.textContent = labels[lv] || lv.toUpperCase();
  }

  function renderLayers(layers) {
    const el = $("qtm-layers");
    if (!el) return;
    if (!layers || typeof layers !== "object") {
      el.innerHTML = "<span class=\"qtm-stat-hint\">Layer data pending…</span>";
      return;
    }
    el.innerHTML = Object.entries(layers)
      .map(([name, score]) => {
        const pct = Math.round(Number(score) * 100);
        return `<div class="qtm-layer">
          <span class="qtm-layer-name">${name.replace(/_/g, " ")}</span>
          <div class="qtm-layer-bar"><div class="qtm-layer-fill" style="width:${pct}%"></div></div>
          <span class="qtm-layer-pct">${pct}%</span>
        </div>`;
      })
      .join("");
  }

  function applyGuard(doc) {
    const metrics = doc.metrics || {};
    setGauge(doc.headroom_pct);
    $("qtm-peak-c").textContent = doc.peak_c != null ? `${Number(doc.peak_c).toFixed(1)}°C` : "—";
    $("qtm-rapl").textContent = doc.rapl_watts != null ? `${fmtNum(doc.rapl_watts)} W` : "—";
    $("qtm-certainty").textContent = doc.certainty_score != null
      ? `${Math.round(Number(doc.certainty_score) * 100)}%`
      : "—";
    $("qtm-certainty-label").textContent = doc.certainty_label || "field layers";
    $("qtm-max-j").textContent = fmtNum(doc.max_joules_per_second, 1);
    $("qtm-j-op").textContent = doc.joules_per_field_op != null ? String(doc.joules_per_field_op) : "—";
    $("qtm-ops-budget").textContent = fmtNum(
      doc.max_ops_per_second_at_budget || metrics.budget_headroom_ops_per_s,
      0,
    );
    $("qtm-cur-w").textContent = doc.current_power_w != null ? `${fmtNum(doc.current_power_w, 4)} W` : "—";
    $("qtm-canvas-px").textContent = metrics.canvas_pixels_4k_uhd != null
      ? fmtNum(metrics.canvas_pixels_4k_uhd, 0)
      : "—";
    $("qtm-chunk").textContent = doc.max_global_redata_chunk != null
      ? fmtNum(doc.max_global_redata_chunk, 0)
      : "—";
    $("qtm-passes").textContent = metrics.incremental_passes_4k != null
      ? String(metrics.incremental_passes_4k)
      : "—";
    const gain = metrics.dispatch_gain_band_pct;
    $("qtm-gain").textContent = Array.isArray(gain) ? `${gain[0]}–${gain[1]}%` : "—";
    renderLayers(metrics.layers);
    const anom = doc.anomaly || {};
    $("qtm-anomaly").textContent = anom.active
      ? `Anomaly active · ${anom.thermal_level || "elevated"}`
      : "No thermal anomaly — incremental redata held";
    $("qtm-ts").textContent = doc.ts || "—";
    if (anom.thermal_level) setLevel(anom.thermal_level);
    else if (Number(doc.headroom_pct) < 50) setLevel("warn");
    else setLevel("ok");
  }

  function applyGovernor(doc) {
    if (!doc) return;
    $("qtm-sensors").textContent = `${doc.sensors || 0} sensors`;
    $("qtm-quota").textContent = doc.quota_pct != null ? `${doc.quota_pct}%` : "—";
    $("qtm-wave").textContent = `wave shed ${doc.wave_shed || "ok"}`;
    if (doc.level && doc.level !== "ok") setLevel(doc.level);
    if (doc.peak_c != null && $("qtm-peak-c").textContent === "—") {
      $("qtm-peak-c").textContent = `${Number(doc.peak_c).toFixed(1)}°C`;
    }
  }

  async function loadG16() {
    const el = $("qtm-g16");
    if (!el) return;
    try {
      const doc = await fetchPanel("/api/nexus-c2");
      const g16 = doc.g16 || doc.field_opt || {};
      const ok = g16.ok !== false && (g16.ready !== false);
      el.textContent = g16.label || (ok ? "G16 ready" : "G16 warming");
      el.classList.toggle("ok", ok);
      el.classList.toggle("bad", !ok);
    } catch {
      el.textContent = "G16 offline";
      el.classList.add("bad");
    }
  }

  async function refresh() {
    const status = $("qtm-status");
    if (status) status.textContent = "Polling NEXUS C2…";
    try {
      const [guard, gov] = await Promise.all([
        fetchPanel("/api/field-thermal-guard"),
        fetchPanel("/api/thermal-governor").catch(() => null),
      ]);
      applyGuard(guard);
      applyGovernor(gov);
      if (status) status.textContent = "Live · thermal guard + governor";
    } catch (e) {
      if (status) status.textContent = String(e.message || e);
      setLevel("unknown");
    }
  }

  async function cycleGuard() {
    const status = $("qtm-status");
    if (status) status.textContent = "Running guard cycle…";
    try {
      await fetch(`${panelBase()}/api/field-thermal-guard/cycle`, { method: "POST" });
      await refresh();
      if (status) status.textContent = "Cycle complete";
    } catch (e) {
      if (status) status.textContent = `Cycle failed: ${e.message || e}`;
    }
  }

  $("qtm-refresh")?.addEventListener("click", refresh);
  $("qtm-cycle")?.addEventListener("click", cycleGuard);
  loadG16();
  refresh();
  setInterval(refresh, REFRESH_MS);
})();