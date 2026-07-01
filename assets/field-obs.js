(function () {
  "use strict";

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function render(doc) {
    const main = document.getElementById("fo-main");
    if (!main) return;

    const ui = doc.ui || {};
    const recs = (doc.recordings || [])
      .map(function (r) {
        return (
          '<div class="fo-rec"><span>' +
          esc(r.name) +
          '</span><span class="fo-dim">' +
          Math.round((r.bytes || 0) / 1048576) +
          " MB</span></div>"
        );
      })
      .join("");

    main.innerHTML =
      '<div class="fo-card"><strong>Field capture</strong>' +
      '<p class="fo-dim">' +
      esc(doc.posture || "") +
      "</p>" +
      '<p class="fo-dim">Portable config · bundled plugins · no updater · recordings local</p>' +
      '<div class="fo-row">' +
      '<button type="button" class="fo-btn primary" id="fo-launch">Launch OBS</button>' +
      '<button type="button" class="fo-btn record" id="fo-record">Record now</button>' +
      '<button type="button" class="fo-btn" id="fo-vcam">Virtual cam</button>' +
      '<button type="button" class="fo-btn" id="fo-studio">Studio mode</button>' +
      "</div></div>" +
      '<div class="fo-card"><strong>Readable UI</strong>' +
      '<span class="fo-tier">' +
      esc(ui.tier || "fhd") +
      "</span>" +
      '<span class="fo-tier">Qt ' +
      esc(String(ui.qt_scale_factor || "1.1")) +
      "×</span>" +
      (ui.nvenc ? '<span class="fo-tier">NVENC</span>' : '<span class="fo-tier">x264</span>') +
      '<div class="fo-slider-row"><label for="fo-scale">UI scale</label><span class="fo-slider-val" id="fo-scale-val">' +
      esc(String(ui.ui_scale_pct || 125)) +
      "%</span></div>" +
      '<input type="range" id="fo-scale" min="85" max="150" step="5" value="' +
      esc(String(ui.ui_scale_pct || 125)) +
      '" />' +
      '<label class="fo-dim"><input type="checkbox" id="fo-rtx" ' +
      (ui.rtx_reduce ? "checked" : "") +
      " /> RTX comfort reduce</label></div>" +
      '<div class="fo-card"><strong>Profile</strong><p class="fo-dim">' +
      esc(doc.profile || "Field") +
      " · " +
      esc(doc.collection || "Field-Queen") +
      "<br/>" +
      esc(doc.recordings_dir || "") +
      "</p>" +
      (doc.upstream_cloned ? "<p class='fo-dim'>Upstream cloned ✓</p>" : "<p class='fo-dim'>Run clone-upstream.sh for rewrite lane</p>") +
      "</div>" +
      '<div class="fo-card"><strong>Recordings</strong>' +
      (recs || '<p class="fo-dim">No recordings yet — hit Record now</p>') +
      "</div>";

    document.getElementById("fo-launch")?.addEventListener("click", function () {
      api("/api/field-broadcaster/launch", { method: "POST", body: "{}" });
    });
    document.getElementById("fo-record")?.addEventListener("click", function () {
      api("/api/field-broadcaster/record", { method: "POST" }).then(init);
    });
    document.getElementById("fo-vcam")?.addEventListener("click", function () {
      api("/api/field-broadcaster/virtualcam", { method: "POST" });
    });
    document.getElementById("fo-studio")?.addEventListener("click", function () {
      api("/api/field-broadcaster/studio", { method: "POST" });
    });

    const scale = document.getElementById("fo-scale");
    const scaleVal = document.getElementById("fo-scale-val");
    const rtx = document.getElementById("fo-rtx");
    function saveUi() {
      const pct = parseInt(scale?.value || "125", 10);
      if (scaleVal) scaleVal.textContent = pct + "%";
      api("/api/field-broadcaster/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ui_scale_pct: pct, rtx_reduce: !!rtx?.checked }),
      }).then(init);
    }
    scale?.addEventListener("change", saveUi);
    rtx?.addEventListener("change", saveUi);
  }

  async function init() {
    try {
      render(await api("/api/field-broadcaster"));
    } catch (e) {
      const main = document.getElementById("fo-main");
      if (main) main.textContent = "Broadcaster load failed: " + e.message;
    }
  }

  function renderUSVoltage(slice) {
    const el = document.getElementById("us-voltage-regulation");
    if (!el) return;
    if (!slice) {
      el.innerHTML = '<p class="meta">Voltage regulation loading…</p>';
      return;
    }
    const ok = slice.ok;
    el.innerHTML =
      "<h4>Voltage · present rail</h4>" +
      '<p class="meta" style="margin:0 0 10px;">' +
      esc(slice.motto || "") +
      "</p>" +
      '<div class="us-obs-kv">' +
      "<div><span>Status</span><strong>" +
      (ok ? "good — voltage started" : "pending") +
      "</strong></div>" +
      "<div><span>Started</span><strong>" +
      esc(slice.voltage_started_at || "—") +
      "</strong></div>" +
      "<div><span>Operate here</span><strong>" +
      (slice.operate_at_present_rail ? "yes" : "no") +
      "</strong></div>" +
      "<div><span>Grid trust</span><strong>" +
      (slice.grid_blocked ? "blocked" : "open") +
      "</strong></div>" +
      "</div>";
  }

  function renderUSObs(slice) {
    const el = document.getElementById("us-broadcaster-field") || document.getElementById("us-obs-field");
    if (!el) return;
    if (!slice) {
      el.innerHTML = '<p class="meta">Broadcaster slice loading…</p>';
      return;
    }
    const pconf = slice.posterity_confirm_avg;
    const markers = slice.last_markers || {};
    const markerTxt = Object.keys(markers).slice(0, 2).join(", ") || "—";
    el.innerHTML =
      "<h4>Broadcaster · NEXUS C2</h4>" +
      '<p class="meta" style="margin:0 0 10px;">' +
      esc(slice.motto || "") +
      "</p>" +
      '<div class="us-obs-kv">' +
      "<div><span>g16 ready</span><strong>" +
      (slice.g16_ready ? "yes" : "host fallback") +
      "</strong></div>" +
      "<div><span>Plugin</span><strong>" +
      (slice.plugin_installed ? "installed" : "not installed") +
      "</strong></div>" +
      "<div><span>Engine</span><strong>" +
      (slice.running || slice.obs_running ? "running" : "stopped") +
      "</strong></div>" +
      "<div><span>Encoder</span><strong>" +
      esc(slice.encoder || "x264") +
      "</strong></div>" +
      "<div><span>Defaults</span><strong>" +
      esc(slice.defaults || "clean_passthrough") +
      "</strong></div>" +
      "<div><span>Threat rows</span><strong>" +
      (slice.threat_rows ?? 0) +
      "</strong></div>" +
      "<div><span>Confirm avg</span><strong>" +
      (pconf != null ? pconf.toFixed(2) : "—") +
      "</strong></div>" +
      "<div><span>Markers</span><strong>" +
      esc(markerTxt) +
      "</strong></div>" +
      "<div><span>Filters</span><strong>" +
      (slice.filters || []).length +
      " registered</strong></div>" +
      "</div>" +
      '<div class="fo-row" style="margin-top:12px;">' +
      '<a href="/field-broadcaster" class="fo-btn primary">Open Broadcaster →</a>' +
      "</div>";
  }

  const FieldObsPanel = { render, renderUSObs, renderUSVoltage, init, api };

  if (typeof window !== "undefined") window.FieldObsPanel = FieldObsPanel;
  if (typeof globalThis !== "undefined") globalThis.FieldObsPanel = FieldObsPanel;

  if (document.getElementById("fo-main")) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
  }
})();