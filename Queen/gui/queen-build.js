(function () {
  "use strict";

  const API = "/api/queen-build";

  function $(id) {
    return document.getElementById(id);
  }

  async function fetchStatus() {
    const r = await fetch(API, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function dispatch(action, extra) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    return r.json();
  }

  function renderBrain(doc) {
    const chips = $("qb-brain-chips");
    if (!chips) return;
    const stack = (doc.brain_stack || doc.status?.brain_stack) ?? {};
    const items = Object.entries(stack).map(([k, v]) => `${k}: ${v}`);
    if (!items.length) {
      chips.innerHTML = "<li>Hostess 7 · Neural · Autonomous · RTX · Ladybird · Servo · FFmpeg</li>";
      return;
    }
    chips.innerHTML = items.map((t) => `<li>${t}</li>`).join("");
  }

  function renderHostess(doc) {
    const comfort = $("qb-hostess-comfort");
    const tools = $("qb-hostess-tools");
    if (!comfort && !tools) return;
    const ops = doc.hostess7_brain_ops || {};
    const live = ops.live_status || {};
    const eye = live.eyeball || {};
    const comfortText =
      live.comfort?.comfort || ops.comfort || "Hostess 7 owns brain/sdf/. Queen orchestrates — lossless redata.";
    if (comfort) {
      comfort.textContent = String(comfortText).split("\n")[0].slice(0, 220);
    }
    const ft = doc.field_technology || {};
    const sdf = live.sdf || {};
    const tb = live.textbook || {};
    const buildTools = (ops.commands && Object.entries(ops.commands).map(([k, v]) => `${k}: ${v}`)) || [];
    const fe = eye.product || {};
    const rows = [
      `Final_Eye: ${fe.product || "Final_Eye"} ${fe.version || ""} · ${eye.posture || "assistive"}`,
      `mesh: ${eye.mesh_ok === true ? "woven" : eye.mesh_ok === false ? "check trust" : "—"} · offense strikes: ${eye.offense?.strikes_total ?? "—"}`,
      `sdf segments: ${sdf.segments ?? "—"} · human plates: ${sdf.human_plates ?? "—"}`,
      `Field Technology ZAC: ${tb.zac_present ? `${Math.round((tb.zac_bytes || 0) / 1024)} KiB` : "build Textbook"}`,
      `verify: ${tb.verify_ok === true ? "OK" : "run build --verify-only"}`,
      ...buildTools.slice(0, 5),
    ];
    if (tools) tools.innerHTML = rows.map((t) => `<li>${t}</li>`).join("");
    const comp = $("qb-compiler-status");
    const probe = live.compilers || ops.live_status?.compilers;
    if (comp && probe?.found) {
      const keys = Object.keys(probe.found).slice(0, 8).join(", ");
      comp.textContent = `Compilers (${probe.jobs ?? "?"} jobs): ${keys}${probe.ready_rtx ? " · RTX ready" : ""}`;
    }
  }

  function renderStages(doc) {
    const grid = $("qb-stages");
    if (!grid) return;
    const stages = doc.stages || [];
    grid.innerHTML = stages
      .map((s) => {
        const cls = ["qb-stage", s.ready ? "ready" : "", s.optional ? "optional" : ""].filter(Boolean).join(" ");
        const rep = s.replaces ? `<div class="qb-stage__replaces">↳ ${s.replaces}</div>` : "";
        return `<article class="${cls}">
          <div class="qb-stage__label">${s.label}</div>
          <div class="qb-stage__track">${s.track}${s.optional ? " · optional" : ""}</div>
          ${rep}
          <div class="qb-stage__status ${s.ready ? "ok" : "pending"}">${s.ready ? "READY" : "PENDING"}</div>
          <button type="button" class="qb-btn qb-stage-run" data-stage="${s.id}" ${s.ready ? "disabled" : ""}>Forge</button>
        </article>`;
      })
      .join("");
    grid.querySelectorAll(".qb-stage-run").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await dispatch("run", { stage: btn.dataset.stage });
          await refresh();
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function renderMeta(doc) {
    $("qb-motto").textContent = doc.motto || "—";
    $("qb-inside").textContent = `Inside: ${doc.inside ? "YES" : "forge inside"}`;
    $("qb-core").textContent = `Core: ${doc.core_ready ?? 0}/${doc.core_total ?? 0}`;
    $("qb-binary").textContent = `Binary: ${doc.binary_ready ? "queen-browser READY" : "not built"}`;
    const forgeEl = $("qb-forge");
    if (forgeEl) forgeEl.textContent = `Forge: ${doc.forge || "lib/queen-forge.py"}`;
    const fs = doc.forge_status?.field || {};
    const rt = fs.runtime || {};
    $("qb-field-kernel").textContent = `Field kernel: ${rt.field_kernel_running ? "RUNNING" : fs.artifacts?.bzImage ? "bzImage ready" : "build field_kernel"}`;
    const pkg = (doc.forge_status?.tools || []).find((t) => t.id === "field_package");
    $("qb-field-package").textContent = `Field package: ${pkg?.ready ? "SEALED" : "not sealed"}`;
  }

  async function refreshLog() {
    try {
      const j = await dispatch("log");
      $("qb-log").textContent = j.log || "(empty)";
    } catch (e) {
      $("qb-log").textContent = String(e.message);
    }
  }

  async function refresh() {
    const doc = await fetchStatus();
    renderMeta(doc);
    renderBrain(doc);
    renderHostess(doc);
    renderStages(doc);
    await refreshLog();
  }

  $("qb-refresh")?.addEventListener("click", () => refresh().catch(alert));
  $("qb-run-field")?.addEventListener("click", async () => {
    const btn = $("qb-run-field");
    if (btn) btn.disabled = true;
    try {
      await dispatch("run-field");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-hostess-teach")?.addEventListener("click", async () => {
    const btn = $("qb-hostess-teach");
    if (btn) btn.disabled = true;
    try {
      await dispatch("hostess-teach");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-forge-test")?.addEventListener("click", async () => {
    const btn = $("qb-forge-test");
    if (btn) btn.disabled = true;
    try {
      await dispatch("forge-test");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-hostess-pipeline")?.addEventListener("click", async () => {
    const btn = $("qb-hostess-pipeline");
    if (btn) btn.disabled = true;
    try {
      await dispatch("run-hostess");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-hostess-verify")?.addEventListener("click", async () => {
    const btn = $("qb-hostess-verify");
    if (btn) btn.disabled = true;
    try {
      await dispatch("verify-redata");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-eyeball-verify")?.addEventListener("click", async () => {
    const btn = $("qb-eyeball-verify");
    if (btn) btn.disabled = true;
    try {
      const out = await dispatch("eyeball-verify");
      const comfortEl = $("qb-hostess-comfort");
      if (comfortEl) {
        comfortEl.textContent = `Eyeball ${out.ok ? "verified" : "check"} · mesh ${out.trust_mesh?.ok ? "OK" : "—"} · assistive`.slice(0, 220);
      }
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-eyeball-arm")?.addEventListener("click", async () => {
    const btn = $("qb-eyeball-arm");
    if (btn) btn.disabled = true;
    try {
      const out = await dispatch("eyeball-arm", { mode: "dishes" });
      const comfortEl = $("qb-hostess-comfort");
      if (comfortEl) {
        comfortEl.textContent = `Armed ${out.mode || "dishes"} · ${out.final_eyeball?.speak || out.speak || "assistive eyeball"}`.slice(0, 220);
      }
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-queen-final-eye")?.addEventListener("click", async () => {
    const btn = $("qb-queen-final-eye");
    if (btn) btn.disabled = true;
    try {
      const out = await dispatch("zocr-smoke");
      const z = out.zocr?.ocr_file || out.zocr?.ocr_file || "SG/ZOCR/out/";
      const comfortEl = $("qb-hostess-comfort");
      if (comfortEl) {
        comfortEl.textContent = `ZOCR ${out.ok ? "OK" : "pending"} · ${out.queen_verdict || out.mode || ""} → ${z}`.slice(0, 220);
      }
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  $("qb-run-all")?.addEventListener("click", async () => {
    const btn = $("qb-run-all");
    if (btn) btn.disabled = true;
    try {
      await dispatch("run-all");
      await refresh();
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  refresh().catch((e) => {
    $("qb-log").textContent = `Panel API offline — open from Queen RTX or start panel on :9477.\n${e.message}`;
  });
})();