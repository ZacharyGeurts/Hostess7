(function () {
  "use strict";

  const VENDOR_ACCENT = {
    nvidia: "#76b900",
    amd: "#ed1c24",
    intel: "#0071c5",
    all: "#3fb950",
    unknown: "#f472b6",
    "3dfx": "#8b6fd4",
  };

  const fanHistory = new Map();
  const MAX_HIST = 48;
  let pollTimer = null;
  let doc = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function fmt(v, suffix) {
    if (v == null || v === "" || Number.isNaN(v)) return "—";
    return String(v) + (suffix || "");
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function trayFanPill(gpu) {
    const r = gpu?.readouts || {};
    const fan =
      r.fan_pct != null ? r.fan_pct + "%" : r.fan_rpm != null ? r.fan_rpm + " RPM" : "—";
    return '<span class="fsd-tray-pill">Fan ' + esc(fan) + "</span>";
  }

  function accentFor(gpu) {
    if (!gpu) return VENDOR_ACCENT.all;
    if (gpu.color_wheel) return "hsl(" + (doc?.settings?.unknown_hue || 142) + ", 72%, 58%)";
    if (gpu.color) return gpu.color;
    return VENDOR_ACCENT[gpu.vendor] || VENDOR_ACCENT.unknown;
  }

  function pushHistory(id, fan) {
    if (fan == null) return;
    const arr = fanHistory.get(id) || [];
    arr.push(Number(fan));
    if (arr.length > MAX_HIST) arr.shift();
    fanHistory.set(id, arr);
  }

  function drawFanChart(canvas, values, accent) {
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!values.length) return;
    const max = Math.max(100, ...values);
    ctx.strokeStyle = accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach(function (v, i) {
      const x = (i / Math.max(1, values.length - 1)) * (w - 8) + 4;
      const y = h - 4 - (v / max) * (h - 8);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = accent + "33";
    ctx.lineTo(w - 4, h - 4);
    ctx.lineTo(4, h - 4);
    ctx.closePath();
    ctx.fill();
  }

  function renderVendors(vendors, activeFilter) {
    const el = $("fg-vendors");
    if (!el) return;
    const order = ["all", "nvidia", "amd", "intel"];
    el.innerHTML =
      "<h3>Vendors</h3>" +
      order
        .map(function (key) {
          const v = vendors[key] || { name: key, accent: VENDOR_ACCENT[key] };
          const on = activeFilter === key ? " active" : "";
          return (
            '<button type="button" class="fg-vendor-btn' +
            on +
            '" data-vendor="' +
            esc(key) +
            '" style="--fg-accent:' +
            esc(v.accent || VENDOR_ACCENT[key]) +
            '">' +
            '<span class="fg-vendor-dot" style="background:' +
            esc(v.accent || VENDOR_ACCENT[key]) +
            '"></span>' +
            esc(v.name || key) +
            "</button>"
          );
        })
        .join("");
    el.querySelectorAll("[data-vendor]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        saveSettings({ vendor_filter: btn.dataset.vendor, selected_gpu_id: null });
      });
    });
  }

  function gpuOptions(data) {
    const opts = [];
    (data.filtered_gpus || data.gpus || []).forEach(function (g) {
      opts.push({ id: g.id, label: (g.detected ? "● " : "") + g.name, group: "detected" });
    });
    (data.legacy_catalog || []).forEach(function (g) {
      opts.push({ id: g.id, label: "◆ " + g.name, group: "legacy" });
    });
    return opts;
  }

  function renderSelect(data) {
    const sel = $("fg-gpu-select");
    if (!sel) return;
    const activeId = data.active_gpu?.id;
    sel.innerHTML = gpuOptions(data)
      .map(function (o) {
        return (
          '<option value="' +
          esc(o.id) +
          '"' +
          (o.id === activeId ? " selected" : "") +
          ">" +
          esc(o.label) +
          "</option>"
        );
      })
      .join("");
    sel.onchange = function () {
      saveSettings({ selected_gpu_id: sel.value });
    };
  }

  function renderReadouts(gpu) {
    const grid = $("fg-readouts");
    if (!grid) return;
    const r = gpu?.readouts || {};
    const accent = accentFor(gpu);
    document.documentElement.style.setProperty("--fg-accent", accent);

    const items = [
      { cls: "hot", label: "GPU temp", val: fmt(r.temp_c, " °C") },
      { cls: "fan", label: "Fan", val: r.fan_pct != null ? fmt(r.fan_pct, "%") : fmt(r.fan_rpm, " RPM") },
      { cls: "power", label: "Power", val: fmt(r.power_w, " W") },
      { cls: "", label: "GPU util", val: fmt(r.gpu_util_pct, "%") },
      { cls: "", label: "VRAM", val: r.vram_used_mb != null ? fmt(r.vram_used_mb) + " / " + fmt(r.vram_total_mb) + " MB" : fmt(r.vram_total_mb, " MB") },
      { cls: "", label: "Core clock", val: fmt(r.core_clock_mhz, " MHz") },
      { cls: "", label: "Mem clock", val: fmt(r.mem_clock_mhz, " MHz") },
      { cls: "", label: "Mem util", val: fmt(r.mem_util_pct, "%") },
    ];
    grid.innerHTML = items
      .map(function (it) {
        return (
          '<div class="fg-readout ' +
          it.cls +
          '"><span>' +
          esc(it.label) +
          '</span><strong style="color:' +
          esc(accent) +
          '">' +
          esc(it.val) +
          "</strong></div>"
        );
      })
      .join("");
  }

  function renderVisual(gpu) {
    const box = $("fg-card-visual");
    if (!box) return;
    const accent = accentFor(gpu);
    if (gpu?.color_wheel) {
      const hue = doc?.settings?.unknown_hue || 142;
      box.innerHTML =
        '<div class="fg-color-wheel" style="filter:hue-rotate(' +
        (hue - 142) +
        'deg)"></div><p style="text-align:center;color:var(--fg-dim)">Unknown GPU — pick hue below</p>';
    } else {
      box.innerHTML =
        '<img src="/assets/field-gpu-card.svg" alt="Video card" style="filter:drop-shadow(0 0 18px ' +
        accent +
        '55)"/>';
    }
  }

  function renderFans(data) {
    const el = $("fg-fans");
    if (!el) return;
    const gpus = data.filtered_gpus?.length ? data.filtered_gpus : data.gpus || [];
    if (!gpus.length) {
      el.innerHTML = '<p class="fg-sub">No live fans — select a legacy card or attach a GPU.</p>';
      return;
    }
    el.innerHTML = gpus
      .map(function (g, i) {
        const r = g.readouts || {};
        const fan = r.fan_pct != null ? r.fan_pct : r.fan_rpm;
        pushHistory(g.id, fan);
        const pct = r.fan_pct != null ? Math.min(100, r.fan_pct) : fan != null ? Math.min(100, fan / 40) : 0;
        const accent = accentFor(g);
        return (
          '<div class="fg-fan-card">' +
          "<h4>" +
          esc(g.name) +
          "</h4>" +
          '<div class="fg-fan-bar"><div class="fg-fan-fill" style="width:' +
          pct +
          "%;background:linear-gradient(90deg," +
          accent +
          ",var(--fg-blue))\"></div></div>" +
          '<span class="fg-sub">' +
          esc(r.fan_pct != null ? r.fan_pct + "%" : r.fan_rpm != null ? r.fan_rpm + " RPM" : "N/A") +
          " · " +
          esc(r.temp_c != null ? r.temp_c + " °C" : "temp N/A") +
          "</span>" +
          '<canvas id="fg-fan-chart-' +
          i +
          '" width="240" height="48"></canvas></div>"
        );
      })
      .join("");
    gpus.forEach(function (g, i) {
      const c = $("fg-fan-chart-" + i);
      drawFanChart(c, fanHistory.get(g.id) || [], accentFor(g));
    });
  }

  function renderGpuList(data) {
    const el = $("fg-gpu-list");
    if (!el) return;
    const activeId = data.active_gpu?.id;
    const rows = data.gpus || [];
    el.innerHTML = rows.length
      ? rows
          .map(function (g) {
            const r = g.readouts || {};
            return (
              '<div class="fg-gpu-tile' +
              (g.id === activeId ? " active" : "") +
              '" data-gpu="' +
              esc(g.id) +
              '">' +
              '<div class="name">' +
              esc(g.name) +
              "</div>" +
              '<div class="meta">' +
              esc(g.vendor) +
              " · " +
              esc(r.temp_c != null ? r.temp_c + "°C" : "—") +
              " · " +
              esc(g.source || "") +
              "</div></div>"
            );
          })
          .join("")
      : '<p class="fg-sub">No PCI GPU detected — use legacy catalog →</p>';
    el.querySelectorAll("[data-gpu]").forEach(function (tile) {
      tile.addEventListener("click", function () {
        saveSettings({ selected_gpu_id: tile.dataset.gpu });
      });
    });
  }

  function renderLegacy(data) {
    const el = $("fg-legacy-list");
    if (!el) return;
    const activeId = data.active_gpu?.id;
    el.innerHTML = (data.legacy_catalog || [])
      .map(function (leg) {
        return (
          '<div class="fg-legacy-item' +
          (leg.id === activeId ? " active" : "") +
          '" data-legacy="' +
          esc(leg.id) +
          '">' +
          esc(leg.name) +
          (leg.era ? ' <em style="opacity:0.6">· ' + esc(leg.era) + "</em>" : "") +
          "</div>"
        );
      })
      .join("");
    el.querySelectorAll("[data-legacy]").forEach(function (item) {
      item.addEventListener("click", function () {
        saveSettings({ selected_gpu_id: item.dataset.legacy, legacy_selection: item.dataset.legacy });
      });
    });
    const hue = $("fg-hue");
    if (hue) {
      hue.value = data.settings?.unknown_hue || 142;
      hue.oninput = function () {
        saveSettings({ unknown_hue: parseInt(hue.value, 10) });
      };
    }
  }

  function render(data) {
    doc = data;
    const gpu = data.active_gpu || {};
    if (globalThis.FieldShellDock) {
      FieldShellDock.setExtraTray(trayFanPill(gpu));
    }
    renderVendors(data.vendors || {}, data.settings?.vendor_filter || "all");
    renderSelect(data);
    const title = $("fg-title");
    const sub = $("fg-subtitle");
    if (title) title.textContent = gpu.name || "Field GPU Control";
    if (sub) sub.textContent = data.posture || data.motto || "";
    renderVisual(gpu);
    renderReadouts(gpu);
    renderFans(data);
    renderGpuList(data);
    renderLegacy(data);
    const pill = $("fg-detect-pill");
    if (pill) {
      pill.textContent = data.detected_count + " detected";
      pill.style.borderColor = accentFor(gpu);
      pill.style.color = accentFor(gpu);
    }
  }

  async function saveSettings(patch) {
    try {
      render(await api("/api/field-gpu/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }));
    } catch (e) {
      console.error(e);
    }
  }

  async function refresh() {
    try {
      render(await api("/api/field-gpu"));
    } catch (e) {
      const main = $("fg-main");
      if (main) main.innerHTML = "<p>GPU panel load failed: " + esc(e.message) + "</p>";
    }
  }

  function schedulePoll() {
    if (pollTimer) clearInterval(pollTimer);
    const ms = doc?.poll_ms || 1200;
    pollTimer = setInterval(refresh, ms);
  }

  async function init() {
    if (globalThis.FieldShellDock) {
      FieldShellDock.init({ activeIcon: "gpu" });
    }
    await refresh();
    schedulePoll();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();