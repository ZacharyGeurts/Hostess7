/**
 * Field Performance Flyout — live CPU, memory, thermal, energy overlay.
 * Toggle via Debug menu checkbox; auto-closes on page unload.
 */
(function (global) {
  "use strict";

  const DEFAULT_API = "/api/field-performance-flyout";
  const DEFAULT_KEY = "nexus_perf_flyout";
  const POLL_MS = 500;

  function benchmarkMode() {
    if (document.body?.dataset?.queenBenchmark === "1") return true;
    try {
      return global.localStorage?.getItem("queen_benchmark") === "1";
    } catch (_) {
      return false;
    }
  }
  const HISTORY = 72;

  let root = null;
  let pollTimer = null;
  let waveAnim = null;
  let wavePhase = 0;
  let dragging = false;
  let dragOff = { x: 0, y: 0 };
  let cfg = { apiUrl: DEFAULT_API, storageKey: DEFAULT_KEY, checkboxId: null };
  let cpuHist = [];
  let memHist = [];
  let loadHist = [];
  let lastDoc = null;

  function $(sel) {
    return typeof sel === "string" ? document.getElementById(sel) : sel;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function fmtPct(v) {
    const n = Number(v);
    return Number.isFinite(n) ? `${n.toFixed(1)}%` : "—";
  }

  function fmtW(v) {
    const n = Number(v);
    return Number.isFinite(n) ? `${n.toFixed(1)} W` : "—";
  }

  function fmtKb(kb) {
    const n = Number(kb);
    if (!Number.isFinite(n) || n <= 0) return "—";
    if (n >= 1048576) return `${(n / 1048576).toFixed(1)} GB`;
    if (n >= 1024) return `${(n / 1024).toFixed(0)} MB`;
    return `${Math.round(n)} KB`;
  }

  function pushHist(arr, v, max) {
    arr.push(Number.isFinite(Number(v)) ? Number(v) : 0);
    while (arr.length > max) arr.shift();
  }

  function ensureRoot() {
    if (root) return root;
    root = document.createElement("div");
    root.id = "fpf-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", "Performance flyout");
    root.innerHTML = `
      <div class="fpf-head" id="fpf-head">
        <strong>Performance</strong>
        <span class="fpf-sub" id="fpf-sub">field metrics · loopback</span>
        <button type="button" class="fpf-close" id="fpf-close" title="Close flyout" aria-label="Close">×</button>
      </div>
      <div class="fpf-metrics" id="fpf-metrics">
        <div class="fpf-pill"><b id="fpf-cpu">—</b><span>CPU</span></div>
        <div class="fpf-pill"><b id="fpf-mem">—</b><span>Memory</span></div>
        <div class="fpf-pill"><b id="fpf-pwr">—</b><span>Power</span></div>
        <div class="fpf-pill"><b id="fpf-therm">—</b><span>Headroom</span></div>
      </div>
      <div class="fpf-canvas-row">
        <label>CPU · load · memory</label>
        <canvas id="fpf-chart" width="400" height="56"></canvas>
      </div>
      <div class="fpf-canvas-row fpf-wave">
        <label>Field wave · 3D surface</label>
        <canvas id="fpf-wave" width="400" height="88"></canvas>
      </div>
      <div class="fpf-foot" id="fpf-foot">—</div>`;
    document.body.appendChild(root);
    $("fpf-close")?.addEventListener("click", () => setOpen(false));
    bindDrag();
    bindUnload();
    return root;
  }

  function bindDrag() {
    const head = $("fpf-head");
    if (!head) return;
    head.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".fpf-close")) return;
      dragging = true;
      const r = root.getBoundingClientRect();
      dragOff.x = e.clientX - r.left;
      dragOff.y = e.clientY - r.top;
      root.style.right = "auto";
      root.style.bottom = "auto";
      root.style.left = `${r.left}px`;
      root.style.top = `${r.top}px`;
      head.setPointerCapture(e.pointerId);
    });
    head.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const w = root.offsetWidth;
      const h = root.offsetHeight;
      const left = Math.max(4, Math.min(window.innerWidth - w - 4, e.clientX - dragOff.x));
      const top = Math.max(4, Math.min(window.innerHeight - h - 4, e.clientY - dragOff.y));
      root.style.left = `${left}px`;
      root.style.top = `${top}px`;
    });
    head.addEventListener("pointerup", () => { dragging = false; });
    head.addEventListener("pointercancel", () => { dragging = false; });
  }

  function bindUnload() {
    const close = () => setOpen(false, { persist: false, silent: true });
    window.addEventListener("beforeunload", close);
    window.addEventListener("pagehide", close);
  }

  function syncCheckbox(on) {
    const id = cfg.checkboxId;
    if (!id) return;
    const cb = $(id);
    if (cb && document.activeElement !== cb) cb.checked = !!on;
  }

  function readStored() {
    try { return localStorage.getItem(cfg.storageKey) === "1"; } catch (_) { return false; }
  }

  function writeStored(on) {
    try { localStorage.setItem(cfg.storageKey, on ? "1" : "0"); } catch (_) {}
  }

  function setOpen(on, opts = {}) {
    const { persist = true, silent = false } = opts;
    ensureRoot();
    root.classList.toggle("open", !!on);
    if (persist) writeStored(!!on);
    if (!silent) syncCheckbox(!!on);
    if (on) {
      startPoll();
      startWave();
      tick();
    } else {
      stopPoll();
      stopWave();
    }
  }

  async function fetchSample(reset) {
    const init = reset ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reset: true }) } : { cache: "no-store" };
    const url = reset ? cfg.apiUrl : `${cfg.apiUrl}?t=${Date.now()}`;
    const res = await fetch(url, init);
    if (!res.ok) throw new Error(`perf ${res.status}`);
    return res.json();
  }

  function drawChart() {
    const canvas = $("fpf-chart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const grid = (color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      for (let i = 1; i < 4; i += 1) {
        const y = (h * i) / 4;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
    };
    grid("rgba(255,255,255,0.04)");

    function plotLine(data, color, maxY, fill) {
      if (!data.length) return;
      const step = w / Math.max(1, HISTORY - 1);
      ctx.beginPath();
      data.forEach((v, i) => {
        const x = i * step;
        const y = h - (Math.min(maxY, Math.max(0, v)) / maxY) * (h - 4) - 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      if (fill) {
        const lastX = (data.length - 1) * step;
        ctx.lineTo(lastX, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    plotLine(memHist, "rgba(88,166,255,0.35)", 100, "rgba(88,166,255,0.12)");
    plotLine(cpuHist, "#3fb950", 100, null);
    plotLine(loadHist.map((v) => Math.min(100, v * 20)), "#f0883e", 100, null);
  }

  function drawWave() {
    const canvas = $("fpf-wave");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const seeds = (lastDoc && lastDoc.wave) || [];
    const cols = 32;
    const rows = 14;
    const cpu = Number(lastDoc?.cpu_pct) || 0;
    const head = Number(lastDoc?.energy?.headroom_pct) || 50;
    const amp = 0.35 + (cpu / 100) * 0.45;
    const hue = 120 + (head / 100) * 80;

    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols - 1; c += 1) {
        const s0 = seeds[c % seeds.length] ?? 0.5;
        const s1 = seeds[(c + 1) % seeds.length] ?? 0.5;
        const z0 = Math.sin(wavePhase + c * 0.22 + r * 0.17) * amp + s0 * 0.25;
        const z1 = Math.sin(wavePhase + (c + 1) * 0.22 + r * 0.17) * amp + s1 * 0.25;
        const persp = 1 - r / (rows + 2);
        const x0 = (c / cols) * w;
        const x1 = ((c + 1) / cols) * w;
        const y0 = h * 0.55 - z0 * h * 0.28 * persp - r * 2.2;
        const y1 = h * 0.55 - z1 * h * 0.28 * persp - r * 2.2;
        const lit = 38 + persp * 28 + z0 * 30;
        ctx.strokeStyle = `hsla(${hue}, 72%, ${lit}%, ${0.25 + persp * 0.45})`;
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        ctx.stroke();
      }
    }

    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "rgba(63,185,80,0.08)");
    grad.addColorStop(1, "rgba(56,139,253,0.02)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  }

  function paint(doc) {
    lastDoc = doc;
    pushHist(cpuHist, doc.cpu_pct, HISTORY);
    pushHist(memHist, doc.memory?.used_pct, HISTORY);
    const load = (doc.loadavg && doc.loadavg[0]) || 0;
    pushHist(loadHist, load, HISTORY);

    const sub = $("fpf-sub");
    if (sub) {
      const tier = doc.substrate?.label || doc.substrate?.tier || "field";
      sub.textContent = `${doc.cpu_cores || "—"} cores · ${tier} · ${doc.ts || ""}`;
    }
    const cpuEl = $("fpf-cpu");
    if (cpuEl) cpuEl.textContent = fmtPct(doc.cpu_pct);
    const memEl = $("fpf-mem");
    if (memEl) memEl.textContent = fmtPct(doc.memory?.used_pct);
    const pwrEl = $("fpf-pwr");
    if (pwrEl) pwrEl.textContent = fmtW(doc.energy?.power_w);
    const thermEl = $("fpf-therm");
    if (thermEl) {
      const hr = doc.energy?.headroom_pct;
      thermEl.textContent = hr != null ? fmtPct(hr) : (doc.energy?.peak_c != null ? `${doc.energy.peak_c}°C` : "—");
    }
    const foot = $("fpf-foot");
    if (foot) {
      const ops = doc.field_ops?.max_at_budget;
      const j = doc.field_ops?.joules_per_op;
      foot.textContent = [
        `load ${(doc.loadavg || []).join(" · ") || "—"}`,
        `mem ${fmtKb(doc.memory?.used_kb)} / ${fmtKb(doc.memory?.total_kb)}`,
        ops != null ? `ops/s ${ops}` : "",
        j != null ? `${j} J/op` : "",
        doc.loopback_only ? "loopback" : "",
      ].filter(Boolean).join(" · ");
    }
    drawChart();
    drawWave();
  }

  async function tick() {
    if (!root?.classList.contains("open")) return;
    try {
      const doc = await fetchSample(false);
      if (doc && doc.ok !== false) paint(doc);
    } catch (_) {
      const foot = $("fpf-foot");
      if (foot) foot.textContent = "metrics unavailable — retrying…";
    }
  }

  function startPoll() {
    if (benchmarkMode()) return;
    stopPoll();
    pollTimer = window.setInterval(tick, POLL_MS);
  }

  function stopPoll() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startWave() {
    stopWave();
    const loop = () => {
      wavePhase += 0.06;
      drawWave();
      waveAnim = requestAnimationFrame(loop);
    };
    waveAnim = requestAnimationFrame(loop);
  }

  function stopWave() {
    if (waveAnim) {
      cancelAnimationFrame(waveAnim);
      waveAnim = null;
    }
  }

  function wireCheckbox(id) {
    const cb = $(id);
    if (!cb || cb.dataset.fpfWired) return;
    cb.dataset.fpfWired = "1";
    cb.addEventListener("change", () => setOpen(cb.checked));
  }

  function init(options) {
    cfg = {
      apiUrl: options?.apiUrl || DEFAULT_API,
      storageKey: options?.storageKey || DEFAULT_KEY,
      checkboxId: options?.checkboxId || null,
    };
    if (benchmarkMode()) {
      setOpen(false, { silent: true });
      return { setOpen, tick, close: () => setOpen(false) };
    }
    if (cfg.checkboxId) wireCheckbox(cfg.checkboxId);
    if (readStored()) setOpen(true, { silent: true });
    return { setOpen, tick, close: () => setOpen(false) };
  }

  global.FieldPerformanceFlyout = { init, setOpen, tick };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      if ($("set-perf-flyout")) init({ checkboxId: "set-perf-flyout" });
      if ($("qc-perf-flyout")) init({ checkboxId: "qc-perf-flyout" });
      if ($("qb-perf-flyout")) init({ checkboxId: "qb-perf-flyout" });
    });
  } else {
    if ($("set-perf-flyout")) init({ checkboxId: "set-perf-flyout" });
    if ($("qc-perf-flyout")) init({ checkboxId: "qc-perf-flyout" });
    if ($("qb-perf-flyout")) init({ checkboxId: "qb-perf-flyout" });
  }
})(typeof window !== "undefined" ? window : globalThis);