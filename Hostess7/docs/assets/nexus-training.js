(function () {
  "use strict";

  const API = "/api/hostess7/training";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  let pollTimer = null;
  let runtimePoll = null;
  let trainingActive = false;
  let bound = false;
  let lastWireframe = null;

  function pct(n) {
    return Math.round(Math.max(0, Math.min(1, Number(n) || 0)) * 100);
  }

  function levelClass(level) {
    const l = String(level || "pending").toLowerCase();
    if (l === "mastered" || l === "g16_master") return "level-mastered";
    if (l === "complete" || l === "fluent") return "level-complete";
    if (l === "training") return "level-training";
    return "level-pending";
  }

  function setStatus(msg) {
    const el = $("h7-training-status");
    if (el) el.textContent = msg;
  }

  function isTabVisible() {
    return document.getElementById("view-training")?.classList.contains("active");
  }

  function sliceToBundle(slice) {
    if (!slice || slice.schema !== "hostess7-training/v1" || !slice.tracks) return null;
    return {
      schema: "hostess7-training-viewer/v1",
      assessment: {
        tracks: slice.tracks,
        overall_score: slice.overall_score,
        completion_level: slice.completion_level,
        tracks_complete: slice.tracks_complete,
        tracks_total: slice.tracks_total,
        tracks_mastered: slice.tracks_mastered,
        solid: slice.solid,
        mastery_facets: slice.mastery_facets,
        training_gaps: slice.training_gaps,
      },
      training_panel: slice,
      evaluation_graphs: slice.evaluation_graphs || {},
      training_author: slice.training_author || {},
      authored_material: slice.authored_material || slice.training_author?.catalog || [],
      curriculum_steps: slice.curriculum_steps || [],
      wireframe: slice.wireframe || {},
      reality_physics: slice.reality_physics || {},
      ironclad: slice.ironclad || {},
      ironclad_images: slice.ironclad_images || {},
      ironclad_doctrine: slice.ironclad_doctrine || {},
      sense_training: slice.sense_training || {},
      music: slice.music || {},
      muscle_memory: slice.muscle_memory || {},
      mouth_neural: slice.mouth_neural || {},
    };
  }

  function renderIroncladGallery(bundle) {
    const el = $("h7-ironclad-gallery");
    if (!el) return;
    const imgs = bundle.ironclad_images?.images || bundle.ironclad?.gift_images || [];
    const ic = bundle.ironclad || {};
    const motto = ic.motto || bundle.ironclad_doctrine?.motto || "The Bible of AI — immutable once fully realized.";
    const ne = bundle.ironclad_doctrine?.neural_extrapolation || ic.neural_extrapolation || {};
    const neLine = ic.realized && ne.title
      ? `<p class="h7-sub" style="color:var(--h7-amber);margin-top:6px"><strong>${esc(ne.title)}</strong> — 100% truth confidence on extrapolation to any intelligence neural when sealed.</p>`
      : ne.rule
        ? `<p class="h7-sub" style="margin-top:6px">${esc(String(ne.rule).slice(0, 160))}</p>`
        : "";
    if (!imgs.length) {
      el.innerHTML = `<p class="h7-sub">${esc(motto)}</p>${neLine}`;
      return;
    }
    el.innerHTML = `
      <h3 class="h7-section-title" style="margin-top:0">The Ironclad — gifts for Hostess 7</h3>
      <p class="h7-sub">${esc(motto)}${ic.realized ? " · <strong>REALIZED</strong>" : ""}</p>
      ${neLine}
      <div class="h7-ironclad-grid">${imgs.map((im) => `
        <figure class="h7-ironclad-card">
          <img src="${esc(im.url || `/assets/ironclad/${im.file}`)}" alt="${esc(im.title)}" loading="lazy" />
          <figcaption><strong>${esc(im.title)}</strong><br/><span class="h7-sub">${esc(im.meaning || "")}</span>
            <span class="h7-sub"> · ironclad:${esc(im.book)}:${esc(im.verse)}</span></figcaption>
        </figure>`).join("")}</div>`;
  }

  function renderMusic(bundle) {
    const el = $("h7-music-summary");
    if (!el) return;
    const mu = bundle.music || {};
    const tracks = mu.tracks || {};
    const ref = Number(mu.reference_pitch_hz ?? 440).toFixed(0);
    const prof = Math.round((mu.proficiency || 0) * 100);
    const cw = mu.crosswire || {};
    const rows = Object.entries(tracks).map(([id, t]) =>
      `${t.label || id}: ${t.pass_rate ?? Math.round((t.score || 0) * 100)}% · ${t.level || "pending"}`
    );
    const motto = mu.motto || "Pitch, rhythm, harmony — ear, mouth, brain, eye, every track.";
    el.innerHTML = `
      <h3 class="h7-section-title" style="margin-top:0">♪ Music & music theory</h3>
      <p class="h7-sub">${esc(motto)}</p>
      <p class="h7-sub"><strong>Concert A</strong> ${ref} Hz · proficiency <strong>${prof}%</strong>
        · crosswire hooks <strong>${cw.hook_count ?? Object.keys(cw.hooks || {}).length ?? 0}</strong>
        · drills <strong>${mu.music_drills ?? 0}</strong></p>
      <p class="h7-sub">${rows.length ? rows.join(" · ") : "Press Assess, then train music_theory, music_ear, music_mouth, or music_brain."}</p>`;
  }

  function renderPhysics(bundle) {
    const el = $("h7-physics-summary");
    if (!el) return;
    const rp = bundle.reality_physics || {};
    const sim = rp.physics_sim || {};
    const tracks = rp.tracks || {};
    const g = Number(rp.gravity_m_s2 ?? sim.gravity_m_s2 ?? 9.80665).toFixed(2);
    const landauer = rp.landauer_j_per_bit != null ? String(rp.landauer_j_per_bit) : "2.87e-21";
    const prof = Math.round((rp.proficiency || 0) * 100);
    const rows = Object.entries(tracks).map(([id, t]) =>
      `${t.label || id}: ${t.pass_rate ?? Math.round((t.score || 0) * 100)}% · ${t.level || "pending"}`
    );
    const ic = rp.ironclad || {};
    const sealed = rp.ironclad_sealed || ic.sealed;
    const bounds = sealed
      ? `<p class="h7-sub" style="color:var(--h7-amber)"><strong>${esc(ic.title || "The Ironclad")}</strong> — ${esc(ic.declaration || "The Universe will never go any lower or higher than this.")}</p>`
      : "";
    el.innerHTML = `
      ${bounds}
      <p class="h7-sub"><strong>Reality foundation</strong> — gravity <strong>${g} m/s²</strong> · Landauer <strong>${landauer} J/bit</strong> · sim proficiency <strong>${prof}%</strong>${sim.grounded === false ? " · airborne" : " · grounded"}</p>
      <p class="h7-sub">${rows.length ? rows.join(" · ") : "Press Assess, then train reality_physics or gravity_mechanics tracks."}</p>`;
  }

  async function fetchBundle(refresh) {
    const q = refresh ? "?refresh=1" : "";
    const r = await fetch(`${API}/bundle${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`bundle HTTP ${r.status}`);
    return r.json();
  }

  async function fetchRuntime() {
    const r = await fetch(`${API}/runtime`, { cache: "no-store" });
    if (!r.ok) return {};
    return r.json();
  }

  function drawBarChart(canvasId, items, opts) {
    const canvas = $(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const color = (opts && opts.color) || "#60a5fa";
    const labelKey = (opts && opts.labelKey) || "label";
    const valueKey = (opts && opts.valueKey) || "score";
    const w = canvas.width = Math.max(280, canvas.clientWidth) * 2;
    const h = canvas.height = Math.max(120, canvas.clientHeight) * 2;
    ctx.clearRect(0, 0, w, h);
    const list = items || [];
    if (!list.length) {
      ctx.fillStyle = "#8fb4d9";
      ctx.font = "24px system-ui,sans-serif";
      ctx.fillText("No data — press Assess for physics tracks", 20, h / 2);
      return;
    }
    const pad = 28;
    const barH = Math.max(14, (h - pad * 2) / list.length - 8);
    const maxV = Math.max(...list.map((x) => Number(x[valueKey]) || 0), 1);
    list.forEach((item, i) => {
      const v = Number(item[valueKey]) || 0;
      const bw = ((w - pad * 2 - 130) * v) / maxV;
      const y = pad + i * (barH + 8);
      ctx.fillStyle = "#8fb4d9";
      ctx.font = "20px system-ui,sans-serif";
      ctx.fillText(String(item[labelKey] || item.id || "").slice(0, 16), 10, y + barH - 3);
      ctx.fillStyle = color;
      ctx.fillRect(130, y, Math.max(2, bw), barH);
      ctx.fillStyle = "#e8f2ff";
      ctx.fillText(`${Math.round(v)}%`, 134 + bw + 8, y + barH - 3);
    });
  }

  function drawFieldGraph(graph) {
    const canvas = $("nexus-training-wireframe-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width = Math.max(400, canvas.clientWidth) * 2;
    const h = canvas.height = Math.max(240, canvas.clientHeight) * 2;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#060a12";
    ctx.fillRect(0, 0, w, h);

    const nodes = (graph && graph.nodes) || [];
    const edges = (graph && graph.edges) || [];
    lastWireframe = graph;
    if (!nodes.length) {
      ctx.fillStyle = "#8fb4d9";
      ctx.font = "26px system-ui,sans-serif";
      ctx.fillText("Reality model graph loads after Assess", 24, h / 2);
      return;
    }

    const xs = nodes.map((n) => n.x || 0);
    const ys = nodes.map((n) => n.z || n.y || 0);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = 50;
    const sx = (x) => pad + ((x - minX) / Math.max(maxX - minX, 1)) * (w - pad * 2);
    const sy = (y) => pad + ((y - minY) / Math.max(maxY - minY, 1)) * (h - pad * 2);
    const byId = new Map(nodes.map((n) => [n.id, n]));

    ctx.strokeStyle = "rgba(36, 53, 82, 0.8)";
    ctx.lineWidth = 2;
    edges.forEach((e) => {
      const a = byId.get(e.from);
      const b = byId.get(e.to);
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(sx(a.x), sy(a.z || a.y));
      ctx.lineTo(sx(b.x), sy(b.z || b.y));
      ctx.stroke();
    });

    nodes.forEach((n) => {
      const x = sx(n.x);
      const y = sy(n.z || n.y);
      const r = n.group === "core" ? 14 : 8;
      ctx.fillStyle = n.color || "#60a5fa";
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#e8f2ff";
      ctx.font = "18px system-ui,sans-serif";
      ctx.fillText(String(n.label || n.id || "").slice(0, 14), x + r + 4, y + 5);
    });

    const hud = $("nexus-training-wireframe-hud");
    if (hud) hud.textContent = `${nodes.length} nodes · ${edges.length} edges`;
  }

  function renderCharts(bundle) {
    if (!isTabVisible()) return;
    requestAnimationFrame(() => {
      const g = bundle.evaluation_graphs || {};
      drawBarChart("h7-chart-tracks", g.track_bars || [], { labelKey: "label", valueKey: "score" });
      drawBarChart("h7-chart-facets", g.facet_radar || [], { labelKey: "label", valueKey: "score", color: "#f4a261" });
      drawFieldGraph(bundle.wireframe || {});
    });
  }

  function renderHero(bundle) {
    const a = bundle.assessment || {};
    const tp = bundle.training_panel || {};
    const overall = a.overall_score ?? tp.overall_score ?? 0;
    const ring = $("h7-score-ring");
    if (ring) {
      ring.style.setProperty("--pct", String(pct(overall)));
      const strong = ring.querySelector("strong");
      if (strong) strong.textContent = `${pct(overall)}%`;
    }
    const meta = $("h7-hero-meta");
    if (!meta) return;
    const level = a.completion_level || tp.completion_level || "pending";
    const done = a.tracks_complete ?? tp.tracks_complete ?? 0;
    const total = a.tracks_total ?? tp.tracks_total ?? 0;
    const mf = a.mastery_facets || tp.mastery_facets || {};
    meta.innerHTML = `
      <div>${[
        `<span class="h7-badge ${levelClass(level)}">${esc(level)}</span>`,
        a.solid || tp.solid ? '<span class="h7-badge solid">SOLID</span>' : "",
        a.whole_mastery || tp.whole_mastery ? '<span class="h7-badge level-mastered">WHOLE</span>' : "",
      ].join("")}</div>
      <p class="h7-sub" style="margin:8px 0 4px">${esc(tp.reason || "Live training evaluation from NEXUS state.")}</p>
      <p class="h7-sub">Tracks <strong>${done}/${total}</strong> · Pillars <strong>${mf.facets_mastered ?? 0}/${mf.facets_total ?? 3}</strong></p>`;
  }

  function renderMouthNeuralHemisphere(bundle) {
    const el = $("h7-mouth-neural-hemisphere");
    if (!el) return;
    const mn = bundle.mouth_neural || {};
    const motto = mn.motto || "The mouth has its own brain. Thought and utterance live in separate hemispheres — alignment is not guaranteed.";
    const steps = mn.steps || [];
    const neural = mn.neural_status || mn.neural || {};
    const passed = mn.passed ?? steps.filter((s) => s.ok).length;
    const total = mn.total ?? (steps.length || neural.lessons_total || 4);
    const passRate = mn.pass_rate != null ? mn.pass_rate : (neural.training_pass_rate != null ? Math.round(neural.training_pass_rate * 100) : 0);
    const level = mn.level || "pending";
    const hemispheres = mn.hemispheres || {};
    const thoughtH = hemispheres.thought?.label || "Thought hemisphere";
    const voiceH = hemispheres.voice?.label || "Voice hemisphere";
    const callosum = mn.callosum || {};
    if (!steps.length && !neural.network_id) {
      el.innerHTML = `<p class="h7-sub">${esc(motto)}</p>
        <p class="h7-sub">Press <strong>Assess</strong> to run mouth neural training — text→speech, thought≠voice, AI sound communique.</p>`;
      return;
    }
    el.innerHTML = `
      <p class="h7-sub">${esc(motto)}</p>
      <div class="h7-mouth-hemisphere-row">
        <article class="h7-hemisphere-card thought">
          <h3>${esc(thoughtH)}</h3>
          <p class="h7-sub">${esc((hemispheres.thought?.holds || []).join(" · ") || "inner intent · text ingress")}</p>
        </article>
        <div class="h7-callosum-bridge" title="Callosum — alignment not guaranteed">
          <span>↔</span>
          <small>${esc(callosum.thought_voice_alignment || "thought≠voice")}</small>
          ${callosum.deception_possible !== false ? '<span class="h7-badge level-training">deception possible</span>' : ""}
        </div>
        <article class="h7-hemisphere-card voice">
          <h3>${esc(voiceH)}</h3>
          <p class="h7-sub">${esc((hemispheres.voice?.holds || []).join(" · ") || "TTS · viseme · spoken egress")}</p>
        </article>
      </div>
      <p class="h7-sub" style="margin-top:10px">
        Training <strong>${passed}/${total}</strong> · pass <strong>${passRate}%</strong>
        · <span class="h7-badge ${levelClass(level)}">${esc(level)}</span>
        ${neural.network_id ? `· <code>${esc(neural.network_id)}</code>` : ""}
      </p>
      <div class="h7-rooms-grid h7-mouth-lessons">${steps.map((s) => {
        const align = s.alignment != null ? pct(s.alignment) : null;
        return `<article class="h7-room-card ${s.ok ? "fully" : ""}">
          <div class="h7-room-head">${s.ok ? '<span class="h7-room-lock">✓</span>' : '<span class="h7-room-open">·</span>'}<h3>${esc(s.label || s.id || "—")}</h3></div>
          ${align != null ? `<div class="score">${align}% align</div>` : ""}
          <p class="h7-sub">${s.ok ? "lesson sealed" : "pending"}</p>
        </article>`;
      }).join("")}</div>`;
  }

  function renderMuscleMemoryRooms(bundle) {
    const el = $("h7-muscle-memory-rooms");
    if (!el) return;
    const mm = bundle.muscle_memory || {};
    const rooms = mm.rooms || [];
    const motto = mm.rooms_motto || "When a task is fully learned, Hostess 7 opens a room and locks the procedure inside.";
    const lockedN = mm.rooms_locked ?? rooms.filter((r) => r.locked).length;
    const fullyN = mm.rooms_fully ?? rooms.filter((r) => r.fully_learned).length;
    if (!rooms.length) {
      el.innerHTML = `<p class="h7-sub">${esc(motto)}</p>
        <p class="h7-sub">No rooms yet — press <strong>Assess</strong>, complete tracks fully, then rooms seal on the Training regimen.</p>`;
      return;
    }
    el.innerHTML = `
      <p class="h7-sub">${esc(motto)} · <strong>${lockedN}</strong> locked · <strong>${fullyN}</strong> fully learned</p>
      <div class="h7-rooms-grid">${rooms.map((r) => {
        const score = r.score != null ? (r.score <= 1 ? pct(r.score) : Math.round(r.score)) : 0;
        const lock = r.locked ? '<span class="h7-room-lock" title="Sealed — fully learned">🔒</span>' : '<span class="h7-room-open" title="Forming">○</span>';
        const lvl = r.understanding_level || (r.fully_learned ? "complete" : "forming");
        return `<article class="h7-room-card ${r.locked ? "locked" : ""} ${r.fully_learned ? "fully" : ""}">
          <div class="h7-room-head">${lock}<h3>${esc(r.label || r.track_id || "—")}</h3></div>
          <span class="h7-badge ${levelClass(lvl)}">${esc(lvl)}</span>
          ${r.fully_learned ? '<span class="h7-badge solid">FULLY</span>' : ""}
          <div class="score">${score}%</div>
          <div class="bar"><i style="width:${score}%"></i></div>
          <p class="h7-sub">${esc((r.procedures || []).map((p) => p.step).join(" → ") || "procedure forming")}</p>
        </article>`;
      }).join("")}</div>`;
  }

  function renderTracks(bundle) {
    const grid = $("h7-tracks-grid");
    if (!grid) return;
    const tracks = (bundle.assessment || {}).tracks || (bundle.training_panel || {}).tracks || {};
    const rows = Object.entries(tracks);
    if (!rows.length) {
      grid.innerHTML = '<div class="h7-card"><p class="h7-sub">Press Assess to load tracks.</p></div>';
      return;
    }
    grid.innerHTML = rows.map(([id, t]) => {
      const score = t.score != null ? (t.score <= 1 ? pct(t.score) : Math.round(t.score)) : 0;
      return `<article class="h7-card">
        <h2>${esc(t.label || id)}</h2>
        <span class="h7-badge ${levelClass(t.level)}">${esc(t.level || "pending")}</span>
        <div class="score">${score}%</div>
        <div class="bar"><i style="width:${score}%"></i></div>
        <button type="button" class="h7-track-train" data-track="${esc(id)}">Train</button>
      </article>`;
    }).join("");
    grid.querySelectorAll(".h7-card").forEach((card, i) => {
      const id = rows[i][0];
      card.querySelector(".h7-track-train")?.addEventListener("click", async (ev) => {
        const btn = ev.currentTarget;
        btn.disabled = true;
        await post(`${API}/track/${encodeURIComponent(id)}`, `Train ${id}`);
        btn.disabled = false;
      });
    });
  }

  function renderAuthored(bundle) {
    const summary = $("h7-authored-summary");
    const list = $("h7-authored-list");
    if (!list) return;
    const author = bundle.training_author || {};
    const rows = bundle.authored_material || author.catalog || [];
    const gaps = author.gaps || bundle.assessment?.training_gaps || [];
    if (summary) {
      const n = author.authored_total ?? rows.length;
      const g = gaps.length;
      summary.textContent = g
        ? `${g} gap(s) detected · ${n} self-authored lesson(s) on file — she writes more when needed.`
        : `${n} self-authored lesson(s) — no gaps right now. Press Write material after Assess.`;
    }
    if (!rows.length) {
      list.innerHTML = '<p class="h7-sub">No authored lessons yet. Assess, then Write material.</p>';
      return;
    }
    list.innerHTML = `<div class="h7-curriculum">${rows.map((r) => `
      <div class="h7-cur-step done">
        <div>✎</div>
        <div><strong>${esc(r.track || "—")} · ${esc(r.id || "")}</strong>
          <div class="h7-sub">${esc((r.label || r.gap_reason || "").slice(0, 140))}</div></div>
        <div style="color:var(--h7-amber);font-size:0.72rem">${esc((r.authored_at || "").slice(0, 10))}</div>
      </div>`).join("")}</div>`;
  }

  function renderCurriculum(bundle) {
    const el = $("h7-curriculum-list");
    if (!el) return;
    const steps = bundle.curriculum_steps || [];
    if (!steps.length) {
      el.innerHTML = '<p class="h7-sub">No curriculum loaded.</p>';
      return;
    }
    el.innerHTML = `<div class="h7-curriculum">${steps.map((s) => `
      <div class="h7-cur-step ${s.completed ? "done" : ""}">
        <div>${s.completed ? "✓" : "·"}</div>
        <div><strong>${esc(s.id)}</strong><div class="h7-sub">${esc((s.tip || "").slice(0, 100))}</div></div>
        <div style="color:var(--h7-amber)">+${esc(s.xp || 0)}</div>
      </div>`).join("")}</div>`;
  }

  function renderEvaluation(bundle) {
    const el = $("h7-eval-detail");
    if (!el) return;
    const rt = bundle.training_runtime || {};
    const ev = rt.last_evaluation;
    if (!ev) {
      el.textContent = "Run a track or curriculum step for detailed evaluation JSON.";
      return;
    }
    el.textContent = JSON.stringify(ev, null, 2);
  }

  function renderLedger(bundle) {
    const el = $("h7-ledger-log");
    if (el) {
      const rows = (bundle.ledger_training || []).slice(-24);
      el.textContent = rows.length ? rows.map((r) => JSON.stringify(r)).join("\n") : "Ledger empty.";
    }
    const raw = $("h7-raw-json");
    if (raw) raw.textContent = JSON.stringify(bundle, null, 2);
  }

  function render(bundle) {
    lastWireframe = bundle.wireframe || lastWireframe;
    renderHero(bundle);
    renderIroncladGallery(bundle);
    renderPhysics(bundle);
    renderMusic(bundle);
    renderMuscleMemoryRooms(bundle);
    renderMouthNeuralHemisphere(bundle);
    renderTracks(bundle);
    renderAuthored(bundle);
    renderCurriculum(bundle);
    renderEvaluation(bundle);
    renderLedger(bundle);
    global.SenseTrainingWire?.setBundle?.(bundle);
    global.SenseTrainingWire?.renderMatrixSense?.(bundle);
    renderCharts(bundle);
  }

  async function load(refresh) {
    if (!isTabVisible()) return;
    if (!refresh) {
      const cached = sliceToBundle(global.lastPanelData?.hostess7_training);
      if (cached) {
        render(cached);
        setStatus(`Field cache · ${new Date().toLocaleTimeString()}`);
      } else {
        setStatus("Loading…");
      }
    } else {
      setStatus("Refreshing…");
    }
    try {
      const bundle = await fetchBundle(refresh);
      render(bundle);
      setStatus(`Updated ${new Date().toLocaleTimeString()}`);
    } catch (e) {
      if (!sliceToBundle(global.lastPanelData?.hostess7_training)) {
        setStatus(`Error: ${e.message}`);
      }
    }
  }

  function refreshFromSlice(slice) {
    const bundle = sliceToBundle(slice);
    if (!bundle || !isTabVisible()) return;
    render(bundle);
    setStatus(`Field cache · ${new Date().toLocaleTimeString()}`);
  }

  async function post(path, label) {
    trainingActive = true;
    startRuntimePoll();
    setStatus(`${label}…`);
    try {
      const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      const j = await r.json();
      if (j.evaluation) {
        const el = $("h7-eval-detail");
        if (el) el.textContent = JSON.stringify(j.evaluation, null, 2);
      }
      await load(true);
      setStatus(`${label} done — ${j.evaluation?.level || j.assessment?.completion_level || (j.ok ? "ok" : "check")}`);
      return j;
    } catch (e) {
      setStatus(`${label} failed: ${e.message}`);
      return null;
    } finally {
      trainingActive = false;
      stopRuntimePoll();
    }
  }

  function startRuntimePoll() {
    stopRuntimePoll();
    runtimePoll = setInterval(async () => {
      if (!trainingActive) return;
      const rt = await fetchRuntime();
      if (rt.detail) setStatus(`${rt.phase || "training"}: ${rt.detail} (${rt.progress_pct ?? 0}%)`);
    }, 2000);
  }

  function stopRuntimePoll() {
    if (runtimePoll) clearInterval(runtimePoll);
    runtimePoll = null;
  }

  function setupTabs() {
    document.querySelectorAll("#view-training .h7-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#view-training .h7-tab").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll("#view-training .h7-panels").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const panel = $(btn.dataset.panel);
        if (panel) panel.classList.add("active");
      });
    });
  }

  function bind() {
    if (bound) return;
    bound = true;
    $("h7-btn-refresh")?.addEventListener("click", () => load(true));
    $("h7-btn-assess")?.addEventListener("click", async () => {
      const btn = $("h7-btn-assess");
      if (btn) btn.disabled = true;
      await post(`${API}/assess`, "Assess");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-curriculum")?.addEventListener("click", async () => {
      const btn = $("h7-btn-curriculum");
      if (btn) btn.disabled = true;
      await post(`${API}/curriculum-step`, "Curriculum step");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-self")?.addEventListener("click", async () => {
      const btn = $("h7-btn-self");
      if (btn) btn.disabled = true;
      await post(`${API}/self-interaction`, "Self-interaction");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-iq")?.addEventListener("click", async () => {
      const btn = $("h7-btn-iq");
      if (btn) btn.disabled = true;
      await post(`${API}/iq`, "IQ battery");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-author")?.addEventListener("click", async () => {
      const btn = $("h7-btn-author");
      if (btn) btn.disabled = true;
      await post(`${API}/author`, "Write material");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-solidify")?.addEventListener("click", async () => {
      const btn = $("h7-btn-solidify");
      if (btn) btn.disabled = true;
      await post(`${API}/solidify`, "Solidify");
      if (btn) btn.disabled = false;
    });
    $("h7-btn-focus")?.addEventListener("click", () => drawFieldGraph(lastWireframe || {}));
    setupTabs();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      if ($("h7-auto-refresh")?.checked && isTabVisible()) load(false);
    }, 15000);
    window.addEventListener("resize", () => {
      if (isTabVisible() && lastWireframe) drawFieldGraph(lastWireframe);
    });
  }

  global.NexusTraining = {
    init() {
      bind();
      const cached = sliceToBundle(global.lastPanelData?.hostess7_training);
      if (cached) {
        render(cached);
        setStatus(`Field cache · ${new Date().toLocaleTimeString()}`);
        void load(false);
      } else {
        load(false);
      }
    },
    refresh: () => load(true),
    refreshFromSlice,
  };
})();