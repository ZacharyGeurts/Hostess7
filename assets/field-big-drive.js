(function () {
  "use strict";

  const API = "/api/field-big-drive";
  const state = { doc: null, frameIdx: 1, deviceId: "usb_stick", sourcePath: "", stabilizerTimer: null };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function api(body) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
      credentials: "same-origin",
    });
    return r.json();
  }

  function frames() {
    return state.doc?.frame_sizes || [];
  }

  function currentFrame() {
    const list = frames();
    return list[state.frameIdx] || list[1] || { label: "4 KiB", bytes: 4096, id: "sector_4k" };
  }

  function renderPersistence() {
    const p = state.doc?.persistence || {};
    const usb = p.standard_usb_flash || {};
    const field = p.field_big_drive || {};
    $("bd-persist").innerHTML =
      '<div class="bd-persist-card"><h3>Standard USB flash</h3><ul>' +
      `<li>Retention: ${esc(usb.retention_typical_years)} years typical</li>` +
      `<li>Write cycles: ${esc(usb.write_cycles)}</li>` +
      `<li>${esc(usb.field_exposure)}</li></ul></div>` +
      '<div class="bd-persist-card"><h3>Field Big Drive</h3><ul>' +
      `<li>Retention: ${esc(field.retention_target_years)} years target</li>` +
      `<li>Write cycles: ${esc(field.write_cycles)}</li>` +
      `<li>${esc(field.verdict)}</li></ul></div>`;
  }

  function renderFormats() {
    const sel = $("bd-format");
    if (!sel) return;
    sel.innerHTML = (state.doc?.formats || [])
      .map((f) => `<option value="${esc(f.id)}">${esc(f.label)} (${esc((f.extensions || [])[0])})</option>`)
      .join("");
    sel.value = "fielddrive";
    sel.addEventListener("change", refreshPlan);
  }

  function renderDevices() {
    const grid = $("bd-device-grid");
    if (!grid) return;
    const base = state.doc?.device_grid?.url || "/assets/formats/big_drive_devices.png";
    grid.innerHTML = (state.doc?.devices || [])
      .map((d) => {
        const icon = `/assets/formats/bd_${d.id}.png`;
        const active = d.id === state.deviceId ? " active" : "";
        const tag = d.field_replace ? '<span class="bd-tag">FIELD replaces USB</span>' : d.vm ? '<span class="bd-tag">VM</span>' : "";
        return (
          `<button type="button" class="bd-device${active}" data-device="${esc(d.id)}">` +
          `<img src="${esc(icon)}" alt="" loading="lazy" onerror="this.src='${esc(base)}'" />` +
          `<span>${esc(d.label)}</span>${tag}</button>`
        );
      })
      .join("");
    grid.querySelectorAll("[data-device]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.deviceId = btn.dataset.device;
        grid.querySelectorAll(".bd-device").forEach((b) => b.classList.toggle("active", b === btn));
        refreshPlan();
      });
    });
  }

  function bindSlider() {
    const slider = $("bd-frame-slider");
    const list = frames();
    if (!slider || !list.length) return;
    slider.max = String(list.length - 1);
    slider.addEventListener("input", () => {
      state.frameIdx = parseInt(slider.value, 10) || 0;
      const fr = currentFrame();
      $("bd-frame-label").textContent = fr.label || fr.id;
      $("bd-frame-bytes").textContent =
        fr.bytes > 0 ? `${fr.bytes.toLocaleString()} bytes / frame` : "Custom — use API frame_bytes";
      refreshPlan();
    });
    slider.dispatchEvent(new Event("input"));
  }

  async function refreshPlan() {
    const fr = currentFrame();
    const plan = await api({
      action: "plan",
      frame_id: fr.id,
      frame_bytes: fr.bytes || 0,
      device_id: state.deviceId,
      format_id: $("bd-format")?.value || "fielddrive",
      path: state.sourcePath,
    });
    const el = $("bd-plan");
    if (!el) return;
    if (plan.ok) {
      el.hidden = false;
      el.textContent = JSON.stringify(
        {
          frame: plan.frame?.label,
          device: plan.device?.label,
          format: plan.format?.id,
          sectors: plan.sectors,
          output: plan.output,
          hint: plan.action_hint,
        },
        null,
        2,
      );
    }
  }

  function setStabilizerProgress(doc) {
    const bar = $("bd-stabilizer-bar");
    const label = $("bd-stabilizer-label");
    if (!bar || !label) return;
    const pct = Number(doc?.pct ?? 0);
    bar.value = pct;
    const phase = doc?.phase || "idle";
    const detail = doc?.detail || "";
    label.textContent = doc?.idle ? "Idle" : `${phase}${detail ? " — " + detail : ""} (${pct}%)`;
    if (doc?.error) label.textContent = `Error: ${doc.error}`;
  }

  function stopStabilizerPoll() {
    if (state.stabilizerTimer) {
      clearInterval(state.stabilizerTimer);
      state.stabilizerTimer = null;
    }
  }

  function startStabilizerPoll() {
    stopStabilizerPoll();
    state.stabilizerTimer = setInterval(async () => {
      const prog = await api({ action: "stabilizer_progress" });
      setStabilizerProgress(prog);
      if (prog.done || prog.error || prog.idle) stopStabilizerPoll();
    }, 400);
  }

  async function runAction(action) {
    if (!state.sourcePath) {
      $("bd-status").textContent = "Pick a file — right-click ISO/img in Queen Files → Open in Big Drive";
      return;
    }
    const useStabilizer = action === "field_seal" || action === "replace_usb" || action === "stabilize";
    if (useStabilizer) {
      setStabilizerProgress({ pct: 0, phase: "starting", detail: action });
      startStabilizerPoll();
    }
    $("bd-status").textContent = `Running ${action}…`;
    const fr = currentFrame();
    const out = await api({
      action: useStabilizer ? "stabilize" : action,
      path: state.sourcePath,
      device_id: state.deviceId,
      frame_id: fr.id,
    });
    if (useStabilizer) {
      const prog = await api({ action: "stabilizer_progress" });
      setStabilizerProgress(prog);
      stopStabilizerPoll();
    }
    $("bd-status").textContent = out.ok
      ? `${action} OK · ${out.dest || out.returned_file || out.message || ""}`
      : `Failed: ${out.error || "unknown"}${out.doctrine ? " — " + out.doctrine : ""}`;
  }

  async function init() {
    const params = new URLSearchParams(location.search);
    state.sourcePath = params.get("path") || "";
    $("bd-source-path").textContent = state.sourcePath || "No file — open from Queen Files right-click";
    state.doc = await api({ action: "status" });
    $("bd-motto").textContent = state.doc.motto || "";
    renderPersistence();
    renderFormats();
    renderDevices();
    bindSlider();
    await refreshPlan();
    const therm = state.doc?.thermal;
    if (therm?.rule) {
      const hint = $("bd-stabilizer-label");
      if (hint && !state.stabilizerTimer) {
        hint.title = therm.rule;
      }
    }
    $("bd-ingest").addEventListener("click", () => runAction("stabilize"));
    $("bd-copy-iso").addEventListener("click", () => runAction("copy_iso"));
    $("bd-boot-iso").addEventListener("click", () => runAction("boot_iso"));
    $("bd-replace-usb").addEventListener("click", () => runAction("replace_usb"));
    $("bd-vm").addEventListener("click", () => runAction("vm_attach"));
    $("bd-status").textContent = "Ready · " + (state.doc.devices || []).length + " devices";
  }

  init();
})();