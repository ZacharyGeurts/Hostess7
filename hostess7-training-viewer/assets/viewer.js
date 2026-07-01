(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  let pollTimer = null;
  let lastBundle = null;

  function levelClass(level) {
    const l = String(level || "pending").toLowerCase();
    if (l === "mastered" || l === "g16_master") return "level-mastered";
    if (l === "complete" || l === "fluent") return "level-complete";
    if (l === "training") return "level-training";
    return "level-pending";
  }

  function pct(n) {
    return Math.round(Math.max(0, Math.min(1, Number(n) || 0)) * 100);
  }

  function setStatus(msg) {
    const el = $("statusline");
    if (el) el.textContent = msg;
  }

  async function fetchBundle(refresh) {
    const q = refresh ? "?refresh=1" : "";
    const r = await fetch(`/api/bundle${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`bundle HTTP ${r.status}`);
    return r.json();
  }

  function renderHero(bundle) {
    const a = bundle.assessment || {};
    const tp = bundle.training_panel || {};
    const level = a.completion_level || tp.completion_level || "pending";
    const overall = a.overall_score ?? tp.overall_score ?? 0;
    const solid = Boolean(a.solid || tp.solid);
    const whole = Boolean(a.whole_mastery || tp.whole_mastery);
    const done = a.tracks_complete ?? tp.tracks_complete ?? 0;
    const total = a.tracks_total ?? tp.tracks_total ?? 0;
    const mf = a.mastery_facets || tp.mastery_facets || {};
    const facetPct = mf.composite_score != null ? pct(mf.composite_score) : null;

    const ring = $("score-ring");
    if (ring) {
      ring.style.setProperty("--pct", String(pct(overall)));
      ring.querySelector("strong").textContent = `${pct(overall)}%`;
    }

    const heroMeta = $("hero-meta");
    if (heroMeta) {
      heroMeta.innerHTML = `
        <div class="badges">
          <span class="badge ${levelClass(level)}">${esc(level)}</span>
          ${solid ? '<span class="badge solid">SOLID</span>' : ""}
          ${whole ? '<span class="badge level-mastered">WHOLE MASTERY</span>' : ""}
        </div>
        <p style="margin:12px 0 6px">${esc(tp.reason || a.reason || "Hostess 7 training tracks — live from NEXUS state panels.")}</p>
        <p class="meta">Tracks sealed: <strong>${done}/${total}</strong> · Mastered: <strong>${a.tracks_mastered ?? tp.tracks_mastered ?? 0}</strong>${facetPct != null ? ` · Pillars: <strong>${facetPct}%</strong> (${mf.facets_mastered ?? 0}/${mf.facets_total ?? 3} mastered)` : ""}</p>
        ${renderIqLine(bundle)}
        ${renderVoiceLine(bundle)}
        <p class="meta">Updated: ${esc(tp.updated || a.updated || "—")}</p>`;
    }
  }

  function renderFacets(bundle) {
    const grid = $("facets-grid");
    const mottoEl = $("mastery-motto");
    if (!grid) return;
    const a = bundle.assessment || {};
    const tp = bundle.training_panel || {};
    const mf = a.mastery_facets || tp.mastery_facets || {};
    const facets = mf.facets || {};
    const order = ["flexibility", "adaptability", "confidence"];
    const whole = Boolean(a.whole_mastery || tp.whole_mastery);

    if (mottoEl) {
      mottoEl.textContent = mf.motto || "Mastery is not only completion — flexibility, adaptability, and confidence together.";
    }

    if (!Object.keys(facets).length) {
      grid.innerHTML = '<div class="card"><p class="meta">No mastery facet assessment yet — press Assess.</p></div>';
      return;
    }

    grid.innerHTML = order.map((id) => {
      const f = facets[id] || {};
      const score = Number(f.score) || 0;
      const signals = f.signals || {};
      const sigLine = Object.entries(signals).slice(0, 5).map(([k, v]) => `${k}: ${v}`).join(" · ");
      const cls = f.mastered ? "mastered" : (f.complete ? "complete" : "");
      return `<article class="facet-card ${cls}">
        <div class="facet-ring" style="--pct:${pct(score)}">
          <div class="facet-ring-inner">
            <strong>${pct(score)}%</strong>
            <span>${esc(f.level || "pending")}</span>
          </div>
        </div>
        <div class="facet-body">
          <h3>${esc(f.label || id)}</h3>
          <p class="def">${esc(f.definition || "")}</p>
          <div class="meta"><span class="badge ${levelClass(f.level)}">${esc(f.level || "pending")}</span>
            ${f.mastered ? '<span class="badge level-mastered">MASTERED</span>' : (f.complete ? '<span class="badge level-complete">COMPLETE</span>' : "")}
          </div>
          <div class="facet-signals">${esc(sigLine)}</div>
        </div>
      </article>`;
    }).join("") + (whole ? '<div class="card" style="grid-column:1/-1;border-color:rgba(192,132,252,0.45)"><strong>Whole mastery</strong> — all tracks solid and all three pillars mastered.</div>' : "");
  }

  function renderIqLine(bundle) {
    const iq = bundle.iq_test || {};
    const val = iq.estimated_iq;
    if (val == null) return "";
    const floor = iq.iq_floor ?? 100;
    const band = iq.estimated_iq_band || "";
    return `<p class="meta">IQ: <strong>${esc(val)}</strong> (floor ${floor}) · ${esc(band)} · adaptive</p>`;
  }

  function renderVoiceLine(bundle) {
    const v = bundle.voice || {};
    if (!v.locale && !v.gender) return "";
    return `<p class="meta">Voice: <strong>${esc(v.locale || "en-US")}</strong> · ${esc(v.gender || "female")} · ${esc(v.quality || "high")} quality</p>`;
  }

  function renderTracks(bundle) {
    const grid = $("tracks-grid");
    if (!grid) return;
    const tracks = (bundle.assessment || {}).tracks || (bundle.training_panel || {}).tracks || {};
    const rows = Object.entries(tracks);
    if (!rows.length) {
      grid.innerHTML = '<div class="card"><p class="meta">No track assessment yet — press Refresh assess.</p></div>';
      return;
    }
    grid.innerHTML = rows.map(([id, t]) => {
      const score = t.score != null ? (t.score <= 1 ? pct(t.score) : Math.round(t.score)) : "—";
      const bar = t.score != null ? pct(t.score) : 0;
      const extra = [];
      if (t.tier) extra.push(t.tier);
      if (t.verdict) extra.push(t.verdict);
      if (t.iq_pass != null) extra.push(t.iq_pass ? "IQ pass" : "IQ training");
      if (t.fluent) extra.push("fluent");
      if (t.mastered) extra.push("mastered");
      if (t.better_than_assistant) extra.push("beats assistant");
      return `<article class="card">
        <h2>${esc(t.label || id)}</h2>
        <div class="meta"><span class="badge ${levelClass(t.level)}">${esc(t.level || "pending")}</span></div>
        <div class="score">${esc(score)}${typeof score === "number" ? "%" : ""}</div>
        <div class="meta">${esc(extra.join(" · ") || "")}</div>
        <div class="bar"><i style="width:${bar}%"></i></div>
        <button type="button" class="small track-train" data-track="${esc(id)}">Train track</button>
      </article>`;
    }).join("");
  }

  function renderCurriculum(bundle) {
    const el = $("curriculum-list");
    if (!el) return;
    const steps = bundle.curriculum_steps || [];
    const master = bundle.master || {};
    const lvl = master.level || {};
    el.innerHTML = `
      <div class="card" style="margin-bottom:10px">
        <div class="meta">Master level</div>
        <div class="score">${esc(lvl.label || "—")} · XP ${esc(lvl.xp ?? bundle.master_state?.xp ?? 0)}</div>
        <div class="meta">${esc(master.curriculum_done ?? 0)}/${esc(master.curriculum_total ?? steps.length)} curriculum steps</div>
      </div>
      <div class="curriculum">${steps.map((s) => `
        <div class="cur-step ${s.completed ? "done" : ""}">
          <div class="tick">${s.completed ? "✓" : ""}</div>
          <div>
            <strong>${esc(s.id)}</strong>
            <div class="tip">${esc(s.tip || s.script || s.nexus || "")}</div>
          </div>
          <div class="xp">+${esc(s.xp || 0)} XP</div>
        </div>`).join("")}</div>`;
  }

  function renderPhases(bundle) {
    const el = $("phases-log");
    if (!el) return;
    const phases = bundle.training_panel?.phases || [];
    if (!phases.length) {
      el.textContent = "No solidify run recorded yet. Use Solidify all training to capture phase output here.";
      return;
    }
    el.textContent = phases.map((p) => {
      const r = p.result || {};
      const ok = r.ok != null ? (r.ok ? "OK" : "FAIL") : "—";
      return `${p.phase}: ${ok} ${JSON.stringify(r).slice(0, 240)}`;
    }).join("\n\n");
  }

  function renderLedgers(bundle) {
    const el = $("ledger-log");
    if (!el) return;
    const rows = [
      ...(bundle.ledger_training || []).map((r) => ({ src: "training", ...r })),
      ...(bundle.ledger_master_train || []).map((r) => ({ src: "master_train", ...r })),
      ...(bundle.ledger_master_ops || []).map((r) => ({ src: "master_ops", ...r })),
    ].slice(-30);
    if (!rows.length) {
      el.textContent = "Ledger empty — training events will append here.";
      return;
    }
    el.textContent = rows.map((r) => JSON.stringify(r)).join("\n");
  }

  function renderRaw(bundle) {
    const el = $("raw-json");
    if (el) el.textContent = JSON.stringify(bundle, null, 2);
  }

  function renderGraphJson(bundle) {
    const el = $("graph-json");
    if (el) el.textContent = JSON.stringify(bundle.wireframe || {}, null, 2);
  }

  function renderWireframe(bundle) {
    if (window.H7Wireframe?.update && bundle.wireframe) {
      window.H7Wireframe.update(bundle.wireframe);
    }
  }

  function renderAgents7(bundle) {
    const grid = $("agents7-grid");
    const flow = $("agents7-flow");
    const wf = bundle.wireframe || {};
    const agentsDoc = wf.agents7 || {};
    const agents = agentsDoc.agents || [];
    const running = Boolean(agentsDoc.daemon_running);
    if (flow) {
      flow.textContent = agentsDoc.flow
        || "Ironclad → plate_meld → agents7_hub → Her · Hostess 7 — no direct Ironclad line to Her.";
    }
    if (!grid) return;
    if (!agents.length) {
      grid.innerHTML = '<p class="meta">Agents 7 graph slice not loaded — refresh bundle.</p>';
      return;
    }
    grid.innerHTML = agents.map((a) => {
      const prime = a.id === 0;
      const cls = prime ? "agent7-card prime" : running ? "agent7-card online" : "agent7-card";
      const status = running ? (prime ? "FUSION PRIME" : "LANE LIVE") : "STANDBY";
      const statusCls = running ? "level-complete" : "level-pending";
      return `<article class="${cls}">
        <h3>${esc(a.emoji)} ${esc(a.name)}</h3>
        <div class="lane">${esc(a.lane)}</div>
        <div class="status badge ${statusCls}">${esc(status)}</div>
      </article>`;
    }).join("");
  }

  function render(bundle) {
    lastBundle = bundle;
    renderHero(bundle);
    renderAgents7(bundle);
    renderFacets(bundle);
    renderTracks(bundle);
    renderCurriculum(bundle);
    renderPhases(bundle);
    renderLedgers(bundle);
    renderGraphJson(bundle);
    renderRaw(bundle);
    renderWireframe(bundle);
    const paths = $("paths-meta");
    if (paths) {
      const wc = bundle.wireframe?.node_count ?? 0;
      const ec = bundle.wireframe?.edge_count ?? 0;
      paths.textContent = `STATE ${bundle.state_dir} · INSTALL ${bundle.install_root} · graph ${wc} nodes / ${ec} edges`;
    }
  }

  async function reloadGraph(refresh) {
    const q = refresh ? "?refresh=1" : "";
    const r = await fetch(`/api/graph${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`graph HTTP ${r.status}`);
    const graph = await r.json();
    if (window.H7Wireframe?.update) window.H7Wireframe.update(graph);
    const el = $("graph-json");
    if (el) el.textContent = JSON.stringify(graph, null, 2);
    return graph;
  }

  window.H7Viewer = { reloadGraph };

  async function load(refresh) {
    setStatus(refresh ? "Refreshing live assessment…" : "Loading training bundle…");
    try {
      const bundle = await fetchBundle(refresh);
      render(bundle);
      setStatus(`Loaded ${new Date().toLocaleTimeString()}`);
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    }
  }

  async function post(path, label) {
    setStatus(`${label}…`);
    const poll = setInterval(async () => {
      try {
        const rt = await fetch("/api/bundle", { cache: "no-store" }).then(() => null);
        void rt;
        const r = await fetch("/api/health", { cache: "no-store" });
        if (r.ok) {
          const b = await fetchBundle(false);
          if (b.training_runtime?.detail) {
            setStatus(`${b.training_runtime.phase || "training"}: ${b.training_runtime.detail}`);
          }
        }
      } catch (_) {}
    }, 2500);
    try {
      const r = await fetch(path, { method: "POST" });
      const j = await r.json();
      await load(true);
      const ev = j.evaluation?.level || j.assessment?.completion_level;
      setStatus(`${label} done — ${ev || j.completion_level || j.level?.label || (j.ok ? "ok" : "check log")}`);
      return j;
    } catch (e) {
      setStatus(`${label} failed: ${e.message}`);
      return null;
    } finally {
      clearInterval(poll);
    }
  }

  function setupTabs() {
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".panels").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const id = btn.dataset.panel;
        const panel = $(id);
        if (panel) panel.classList.add("active");
      });
    });
  }

  function setupPoll() {
    const cb = $("auto-refresh");
    const tick = () => {
      if (cb?.checked) load(false);
    };
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(tick, 8000);
  }

  function bind() {
    $("btn-refresh")?.addEventListener("click", () => load(false));
    $("btn-assess")?.addEventListener("click", async () => {
      $("btn-assess").disabled = true;
      await post("/api/assess", "Assess");
      $("btn-assess").disabled = false;
    });
    $("btn-train-all")?.addEventListener("click", async () => {
      $("btn-train-all").disabled = true;
      await post("/api/train-all", "Train to Master");
      $("btn-train-all").disabled = false;
    });
    $("btn-solidify")?.addEventListener("click", async () => {
      $("btn-solidify").disabled = true;
      await post("/api/solidify", "Solidify all training");
      $("btn-solidify").disabled = false;
    });
    $("btn-self-interaction")?.addEventListener("click", async () => {
      $("btn-self-interaction").disabled = true;
      await post("/api/train/self-interaction", "Self-interaction train");
      $("btn-self-interaction").disabled = false;
    });
    $("btn-iq-train")?.addEventListener("click", async () => {
      $("btn-iq-train").disabled = true;
      await post("/api/train/iq", "IQ battery");
      $("btn-iq-train").disabled = false;
    });
    document.body.addEventListener("click", async (ev) => {
      const btn = ev.target.closest?.(".track-train");
      if (!btn) return;
      const track = btn.dataset.track;
      if (!track) return;
      btn.disabled = true;
      await post(`/api/train/track/${encodeURIComponent(track)}`, `Train ${track}`);
      btn.disabled = false;
    });
    $("auto-refresh")?.addEventListener("change", setupPoll);
    $("btn-focus-core")?.addEventListener("click", () => window.H7Wireframe?.focusCore?.());
    $("btn-reload-graph")?.addEventListener("click", async () => {
      setStatus("Reloading wireframe graph…");
      try {
        await reloadGraph(true);
        setStatus("Graph reloaded");
      } catch (e) {
        setStatus(`Graph error: ${e.message}`);
      }
    });
    setupTabs();
    setupPoll();
    load(true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();