(function () {
  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function fmtOps(n) {
    const v = Number(n);
    if (!v) return "—";
    if (v >= 1e6) return (v / 1e6).toFixed(1) + "M/s";
    if (v >= 1e3) return (v / 1e3).toFixed(0) + "K/s";
    return v.toFixed(0) + "/s";
  }

  function fmtBytes(n) {
    const v = Number(n);
    if (!v) return "—";
    if (v >= 1024) return (v / 1024).toFixed(1) + " KB";
    return v + " B";
  }

  function log(line) {
    const el = $("comb-log");
    if (!el) return;
    const ts = new Date().toLocaleTimeString();
    el.textContent = `[${ts}] ${line}\n` + el.textContent;
  }

  function setBusy(busy) {
    document.querySelectorAll(".comb-actions button").forEach((b) => {
      b.disabled = busy;
    });
    const badge = $("comb-badge");
    if (badge) badge.textContent = busy ? "Running…" : "Operator studio";
  }

  function thermalClass(headroom, gateOk) {
    if (!gateOk) return "bad";
    if (headroom >= 50) return "ok";
    if (headroom >= 20) return "warn";
    return "bad";
  }

  function renderMetricsStrip(doc) {
    const el = $("comb-metrics-strip");
    if (!el) return;
    const m = doc.metrics || {};
    const th = m.thermal || {};
    const sense = m.sense || {};
    const bench = m.bench || {};
    const meld = m.meld || {};
    const hr = Number(th.headroom_pct) || 0;
    const gateOk = th.gate_ok !== false;

    const tiles = [
      {
        label: "Thermal headroom",
        value: `${hr.toFixed(0)}%`,
        sub: `Level ${th.level || "ok"} · gate ${gateOk ? "open" : "closed"}`,
        cls: thermalClass(hr, gateOk),
        bar: hr,
      },
      {
        label: "Sense ladder",
        value: sense.profile || "—",
        sub: `Score ${sense.score ?? "—"} · gen ${sense.meld_generation ?? 0}`,
        cls: sense.g16_ready ? "ok" : "warn",
      },
      {
        label: "Bench ceiling",
        value: fmtOps(bench.native_ceiling_ops_per_sec),
        sub: bench.host || "local bench",
        cls: "accent",
      },
      {
        label: "Truth blocks",
        value: String(doc.truth_blocks?.eligible_count ?? "—"),
        sub: doc.truth_blocks?.free_meld ? "free meld on" : "collecting",
        cls: doc.truth_blocks?.free_meld ? "ok" : "",
      },
      {
        label: "Meld generation",
        value: String(meld.generation ?? "—"),
        sub: `${meld.plates_fused ?? "—"} plates fused`,
        cls: (meld.generation || 0) >= 3 ? "ok" : "",
      },
      {
        label: "Ideal compile",
        value: doc.ideal_profile || "—",
        sub: doc.evaluate?.verdict?.best_belt || "",
        cls: "accent",
      },
    ];

    el.innerHTML = tiles.map((t) => {
      const bar = t.bar != null
        ? `<div class="comb-thermal-bar"><span style="width:${Math.min(100, Math.max(0, t.bar))}%"></span></div>`
        : "";
      return `<div class="comb-metric-tile ${t.cls}">
        <div class="label">${esc(t.label)}</div>
        <div class="value">${esc(t.value)}</div>
        <div class="sub">${esc(t.sub)}</div>${bar}
      </div>`;
    }).join("");
  }

  function renderNarrative(ev) {
    const el = $("comb-narrative");
    if (!el) return;
    const sections = ev?.sections || [];
    if (!sections.length) {
      el.innerHTML = '<p class="comb-muted">Run a cycle to generate plain English evaluation.</p>';
      return;
    }
    el.innerHTML = sections.map((s) =>
      `<article class="comb-narrative-block">
        <h3>${esc(s.title)}</h3>
        <p>${esc(s.text)}</p>
      </article>`
    ).join("");
  }

  function renderVerdict(ev, doc) {
    const v = ev?.verdict || {};
    const prof = $("comb-verdict-profile");
    const det = $("comb-verdict-detail");
    const why = $("comb-verdict-why");
    if (!prof) return;

    const profile = v.best_profile || doc.ideal_profile || "—";
    prof.textContent = profile;

    if (det) {
      det.textContent = [
        v.best_belt ? `${v.best_belt} belt` : "",
        v.best_die_slots ? `${v.best_die_slots} die slots` : "",
        v.best_pattern ? `pattern ${v.best_pattern}` : "",
        v.best_runner ? `runner ${v.best_runner}` : "",
        v.confidence ? `confidence ${v.confidence}` : "",
      ].filter(Boolean).join(" · ");
    }

    if (why) {
      why.textContent = v.why || "Run Full cycle to score recombinatorics and produce a verdict.";
    }
  }

  function renderLeaves(top, terminal) {
    const el = $("comb-leaves");
    if (!el) return;
    const tid = terminal?.pattern_id || terminal?.id;
    const rows = (top || []).slice(0, 8);
    if (!rows.length) {
      el.innerHTML = '<div class="comb-muted">Run Walk or Full cycle to score leaves.</div>';
      return;
    }
    el.innerHTML = rows.map((leaf) => {
      const isTerm = leaf.pattern_id === tid;
      return `<div class="comb-leaf${isTerm ? " terminal" : ""}">
        <div>
          <strong>${esc(leaf.pattern_id || leaf.runner || "leaf")}</strong>
          · ${esc(leaf.belt_profile || "")} · ${esc(leaf.runner || "")}
          ${isTerm ? ' <span class="comb-chip on">terminal</span>' : ""}
        </div>
        <div class="score">${leaf.score != null ? leaf.score.toFixed(3) : "—"}</div>
      </div>`;
    }).join("");
  }

  function renderCandidates(recomb) {
    const el = $("comb-candidates");
    if (!el) return;
    const rows = recomb?.candidates || [];
    const ideal = recomb?.ideal_profile;
    if (!rows.length) {
      el.innerHTML = '<p class="comb-muted">Run Recombine to score compile profiles.</p>';
      return;
    }
    el.innerHTML = `<table><thead><tr><th>Profile</th><th>Speed</th><th>Size</th><th>Score</th></tr></thead><tbody>${
      rows.map((r) => `<tr class="${r.profile === ideal ? "ideal" : ""}">
        <td>${esc(r.profile)}${r.profile === ideal ? " ★" : ""}</td>
        <td>${fmtOps(r.ops_per_sec)}</td>
        <td>${fmtBytes(r.binary_bytes)}</td>
        <td>${r.composite_score != null ? r.composite_score.toFixed(4) : "—"}</td>
      </tr>`).join("")
    }</tbody></table>`;
  }

  function drawSparkline(canvasId, values, color) {
    const canvas = $(canvasId);
    if (!canvas || !values || !values.length) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.clientWidth || 240;
    const h = canvas.height || 56;
    canvas.width = w;
    const nums = values.map((v) => Number(v)).filter((v) => !Number.isNaN(v));
    if (!nums.length) return;
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    const span = max - min || 1;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = color || "#5eead4";
    ctx.lineWidth = 2;
    ctx.beginPath();
    nums.forEach((v, i) => {
      const x = (i / Math.max(1, nums.length - 1)) * (w - 8) + 4;
      const y = h - 8 - ((v - min) / span) * (h - 16);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = color || "#5eead4";
    const lx = w - 4;
    const ly = h - 8 - ((nums[nums.length - 1] - min) / span) * (h - 16);
    ctx.beginPath();
    ctx.arc(lx, ly, 3, 0, Math.PI * 2);
    ctx.fill();
  }

  function renderCharts(comb) {
    const charts = comb?.charts || {};
    const spark = charts.sparkline || {};
    drawSparkline("chart-elapsed", spark.elapsed_ms, "#38bdf8");
    drawSparkline("chart-ops", spark.native_ops_per_sec, "#5eead4");
    drawSparkline("chart-leaves", spark.leaves_reached, "#a78bfa");
    drawSparkline("chart-thermal", spark.headroom_pct, "#4ade80");
    const freq = $("comb-pattern-freq");
    if (freq) {
      const rows = charts.pattern_frequency || [];
      freq.innerHTML = rows.length
        ? rows.slice(0, 8).map((r) =>
            `<span class="comb-freq-chip">${esc(r.pattern_id)} × ${r.count}</span>`
          ).join("")
        : '<span class="comb-muted">Run cycles to build pattern frequency chart.</span>';
    }
    const badge = $("comb-poll-badge");
    if (badge) badge.textContent = `Live · ${comb?.poll_interval_sec || 8}s · ${charts.point_count || 0} pts`;
  }

  function plainBrain(text) {
    return String(text || "").replace(/\*\*([^*]+)\*\*/g, "$1");
  }

  function renderQuintStrip(comb) {
    const strip = $("comb-quint-strip");
    if (!strip) return;
    const fs = comb?.field_surfaces || {};
    const c2 = (fs.surfaces || []).find((s) => s.id === "c2_taskbar");
    const quint = c2?.quint || [];
    if (!quint.length) {
      strip.innerHTML = '<p class="comb-muted">Run C2 taskbar plate to fuse the quint.</p>';
      return;
    }
    const bsp = c2?.bsp_hit ? "BSP hit" : "BSP miss";
    const cond = fs.c2_taskbar_condensed ? " · condensed" : "";
    strip.innerHTML = [
      `<span class="comb-quint-meta">${c2?.quint_live ?? 0}/${c2?.quint_total ?? quint.length} live · ${esc(bsp)}${cond}</span>`,
      ...quint.map((slot) => {
        const live = slot.ok ? " live" : "";
        const label = slot.label || slot.id || "";
        return `<span class="comb-quint-slot${live}" title="${esc(slot.posture || "")}">${esc(label)}</span>`;
      }),
    ].join("");
  }

  function renderFieldSurfaces(comb) {
    const grid = $("comb-surfaces-grid");
    const badge = $("comb-surfaces-badge");
    if (!grid) return;
    const fs = comb?.field_surfaces || {};
    const rows = (fs.surfaces || []).filter((s) => s.id !== "c2_taskbar");
    renderQuintStrip(comb);
    if (badge) {
      const c2Note = fs.c2_bsp_hit ? " · BSP hit" : fs.c2_bsp_hit === false ? " · BSP miss" : "";
      badge.textContent = `${fs.live_count ?? 0}/${fs.total_count ?? rows.length + 1} live${
        fs.condensed ? " · surfaces condensed" : ""
      }${fs.c2_taskbar_condensed ? " · quint condensed" : ""}${c2Note}`;
    }
    if (!rows.length) {
      grid.innerHTML = '<p class="comb-muted">Run Bridge meld to plate operator surfaces.</p>';
      return;
    }
    grid.innerHTML = rows.map((s) => {
      const href = s.exec || s.route || "#";
      const live = s.ok ? " live" : "";
      let sub = s.posture || s.combinatorics_role || "";
      if (s.id === "field_lock" && s.product) sub = `${s.product} · ${sub}`.trim();
      return `<a class="comb-surface-tile${live}" href="${esc(href)}"><strong>${esc(s.label || s.id)}</strong><span>${esc(sub)}</span></a>`;
    }).join("");
  }

  function renderMeldDesign(comb) {
    const meld = comb?.plate_meld_design || {};
    const chainEl = $("comb-meld-chain");
    const layersEl = $("comb-meld-layers");
    const sourcesEl = $("comb-meld-sources");
    const genEl = $("comb-meld-gen");
    if (genEl) {
      genEl.textContent = `gen ${meld.generation ?? "—"} · ${meld.plates_fused ?? "—"} plates`;
    }
    const arc = meld.fusion_arc || meld.chain || [];
    if (chainEl) {
      chainEl.innerHTML = arc.length
        ? arc.map((s, i) => {
            const live = s.present !== false ? " live" : "";
            const core = s.combinatorics_core ? " core" : "";
            const arrow = i < arc.length - 1 ? '<span class="comb-meld-arrow" aria-hidden="true">→</span>' : "";
            return `<div class="comb-meld-step${live}${core}"><strong>${esc(s.step)}</strong><span>${esc(s.role)}</span></div>${arrow}`;
          }).join("")
        : '<p class="comb-muted">Meld chain pending.</p>';
    }
    if (layersEl) {
      const layers = meld.compatibility_layers || [];
      layersEl.innerHTML = layers.length
        ? layers.map((l) =>
            `<span class="comb-layer-pill${l.live ? " live" : ""}">${esc(l.glyph || "")} ${esc(l.label || l.id)}</span>`
          ).join("")
        : '<span class="comb-muted">Compatibility layers loading…</span>';
    }
    if (sourcesEl) {
      const sources = (meld.plate_sources || []).filter((s) => s.combinatorics);
      sourcesEl.innerHTML = sources.length
        ? sources.map((s) =>
            `<span class="comb-source-pill${s.present ? " on" : ""}">${esc(s.id)}${s.present ? "" : " (missing)"}</span>`
          ).join("")
        : "";
    }
  }

  function renderBrainSpeed(comb) {
    const bs = comb?.brain_speed || {};
    const plain = $("comb-brain-plain");
    if (plain) plain.textContent = plainBrain(bs.plain || plain.textContent);
    const alts = $("comb-brain-alts");
    if (!alts) return;
    const rows = bs.alternatives || [];
    const primary = bs.primary_route || {};
    let html = primary.brain_area
      ? `<div class="comb-brain-alt"><strong>${esc(primary.brain_area)}</strong> · ${esc(primary.neural_chamber || "")}<br>${esc(primary.why || "")}</div>`
      : "";
    html += rows.map((a) =>
      `<div class="comb-brain-alt">${esc(a.suggestion)} → <strong>${esc(a.brain_area)}</strong> (${esc(a.chamber)})</div>`
    ).join("");
    alts.innerHTML = html || '<p class="comb-muted">At ceiling — hold posture.</p>';
  }

  function renderCpuCatalog(comb) {
    const grid = $("comb-cpu-grid");
    const totalEl = $("comb-cpu-total");
    if (!grid) return;
    const cat = comb?.cpu_catalog || {};
    const archs = cat.architectures || [];
    if (totalEl) {
      const battery = cat.ironclad_chips_total ?? cat.chip_battery_total ?? 0;
      const pred = cat.code_path_prediction || {};
      const pct = pred.total_pct != null ? ` · ${pred.total_pct}% paths` : "";
      const bands = pred.bands != null ? ` · ${pred.bands} bands` : "";
      totalEl.textContent = `${cat.total_architectures ?? archs.length} architectures · ${battery} chips${pct}${bands} · ${cat.guest_systems ?? 0} guests · ${cat.host_cpus ?? 0} hosts`;
    }
    if (!archs.length) {
      grid.innerHTML = '<p class="comb-muted">CPU catalog loading…</p>';
      return;
    }
    grid.innerHTML = archs.slice(0, 48).map((a) => {
      const active = a.active ? " active" : "";
      const pathPct = a.path_pct != null ? `${a.path_pct}%` : "";
      const band = a.band != null ? `b${a.band}` : "";
      const sub = [pathPct, band, a.pipe_width, a.runner || a.cpu || a.vendor || a.chips || a.era || ""].filter(Boolean).join(" · ");
      return `<div class="comb-cpu-tile${active}"><span class="kind">${esc(a.kind)}</span><strong>${esc(a.label || a.id)}</strong>${esc(sub)}</div>`;
    }).join("");
  }

  function render(doc) {
    const tree = doc.tree || {};
    const condense = doc.condense || {};
    const terminal = tree.terminal || {};
    const cap = doc.speed_cap || {};
    const ev = doc.evaluate || {};

    $("comb-leaves-count").textContent = tree.leaves_reached ?? "—";
    $("comb-condense-count").textContent = condense.group_count ?? "—";
    $("comb-cardinality").textContent =
      doc.cardinality != null ? Number(doc.cardinality).toLocaleString() : "—";

    const capEl = $("comb-speed-cap");
    if (capEl) {
      const native = cap.native_ceiling_ops_per_sec || cap.estimated_cap_ops_per_sec
        || (doc.metrics?.bench || {}).native_ceiling_ops_per_sec;
      capEl.textContent = native ? fmtOps(native) : "Run bench";
    }

    const chips = $("comb-status-chips");
    if (chips) {
      const gate = doc.gate || {};
      chips.innerHTML = [
        `<span class="comb-chip ${tree.complete ? "on" : ""}">${tree.complete ? "Tree complete" : "Tree pending"}</span>`,
        `<span class="comb-chip ${doc.bridge_ok ? "on" : "warn"}">Bridge ${doc.bridge_ok ? "OK" : "—"}</span>`,
        `<span class="comb-chip ${gate.ok !== false ? "on" : "warn"}">Thermal gate ${gate.ok !== false ? "open" : "closed"}</span>`,
        `<span class="comb-chip accent">${esc(terminal.pattern_id || "no terminal")}</span>`,
        `<span class="comb-chip">${esc(terminal.belt_profile || "")} · ${terminal.die_slots || 256} die</span>`,
      ].join("");
    }

    renderMetricsStrip(doc);
    renderNarrative(ev);
    renderVerdict(ev, doc);
    renderLeaves(tree.top_leaves, terminal);
    renderCandidates(doc.recombinatorics || {});
    const comb = doc.comb || {};
    renderCharts(comb);
    renderFieldSurfaces(comb);
    renderMeldDesign(comb);
    renderBrainSpeed(comb);
    renderCpuCatalog(comb);
    renderEmulatorLaunch(doc, comb);
  }

  function renderEmulatorLaunch(doc, comb) {
    const host = $("comb-emulator-launch");
    if (!host) return;
    const posture = comb?.exec_posture || doc?.exec_posture || {};
    const hook = (comb?.field_surfaces || {}).exec_hook?.emulator_launch;
    const emulator = posture.emulator || hook?.surface && "FieldChips";
    if (emulator !== "FieldChips" && !hook) {
      host.innerHTML = '<p class="comb-muted">Exec posture is not CHIPS retro — walk tree or refresh chip battery.</p>';
      return;
    }
    const system = posture.launch_system || hook?.system || "nes";
    host.innerHTML = `
      <div class="comb-emulator-row">
        <span class="comb-chip on">FieldChips</span>
        <span class="comb-chip">${esc(system)}</span>
        <button type="button" class="comb-btn comb-btn--accent" id="comb-launch-gameroom">Launch Game Room</button>
      </div>
      <p class="comb-muted">Combinatorics picked CHIPS emulator — spawns queen-game-room pump.</p>`;
    host.querySelector("#comb-launch-gameroom")?.addEventListener("click", async () => {
      log(`Launching Game Room CHIPS pump (${system})…`);
      try {
        const res = await fetch("/api/game-room", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "launch", system, spawn_rtx: true }),
        });
        const out = await res.json();
        log(out.spawned ? `Pump started: ${out.rom_path || system}` : `Launch: ${out.error || out.message || "see log"}`);
        if (out.spawned) window.open("/world/queen-game-room.html", "_blank", "noopener");
      } catch (e) {
        log(`Game Room launch error: ${e.message || e}`);
      }
    });
  }

  async function fetchStatus() {
    const res = await fetch("/api/combinatorics");
    if (!res.ok) throw new Error("status failed");
    return res.json();
  }

  async function runAction(action) {
    setBusy(true);
    log(`Starting: ${action}`);
    try {
      const res = await fetch("/api/combinatorics/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const doc = await res.json();
      if (!doc.ok) log(`Warning: ${action} finished with issues`);
      else log(`Done: ${action}`);
      (doc.steps || []).forEach((s) => {
        log(`  · ${s.step}: ${s.ok === false ? "FAIL" : "ok"}${s.ideal_profile ? " → " + s.ideal_profile : ""}`);
      });
      const v = doc.evaluate?.verdict;
      if (v?.best_profile) log(`Verdict: best compile ${v.best_profile} — ${v.why?.slice(0, 120)}…`);
      render(doc);
    } catch (e) {
      log(`Error: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  document.querySelectorAll("[data-comb-action]").forEach((btn) => {
    btn.addEventListener("click", () => runAction(btn.dataset.combAction));
  });

  let pollTimer = null;

  async function fetchCombPayload() {
    const res = await fetch("/api/combinatorics/comb");
    if (res.ok) return res.json();
    const st = await fetch("/api/combinatorics");
    if (!st.ok) return null;
    const doc = await st.json();
    return doc.comb || null;
  }

  async function refreshCombCharts() {
    try {
      const comb = await fetchCombPayload();
      if (!comb) return;
      renderCharts(comb);
      renderFieldSurfaces(comb);
      renderMeldDesign(comb);
      renderBrainSpeed(comb);
      renderCpuCatalog(comb);
    } catch (_) { /* quiet poll */ }
  }

  async function tryBrainSpeed() {
    const btn = $("comb-brain-try");
    if (btn) btn.disabled = true;
    log("Trying brain speed route…");
    try {
      const res = await fetch("/api/combinatorics/brain-try", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const doc = await res.json();
      const route = doc.brain_invoke?.route_line || doc.brain_invoke?.route?.primary_area;
      if (route) log(`Brain route: ${route}`);
      if (doc.comb) {
        renderCharts(doc.comb);
        renderFieldSurfaces(doc.comb);
        renderMeldDesign(doc.comb);
        renderBrainSpeed(doc.comb);
        renderCpuCatalog(doc.comb);
      }
      if (!doc.ok) log(`Brain try note: ${doc.brain_invoke?.error || "check headroom"}`);
      else log("Brain area engaged — tick recorded on comb ledger.");
    } catch (e) {
      log(`Brain try error: ${e.message || e}`);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function startPoll(intervalSec) {
    if (pollTimer) clearInterval(pollTimer);
    const ms = Math.max(3000, (intervalSec || 5) * 1000);
    pollTimer = setInterval(refreshCombCharts, ms);
  }

  const brainBtn = $("comb-brain-try");
  if (brainBtn) brainBtn.addEventListener("click", tryBrainSpeed);

  fetchStatus()
    .then((doc) => {
      render(doc);
      startPoll(doc.poll_interval_sec || doc.comb?.poll_interval_sec || 5);
      log("Studio ready — live comb charts, CPU map, meld arc, brain speed paths.");
    })
    .catch((e) => log("Load failed: " + (e.message || e)));
})();