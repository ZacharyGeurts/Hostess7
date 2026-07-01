/* Humanoid Motion — full data second window */
(function (global) {
  "use strict";

  const PEEK_FPS = 60;
  const PEEK_MS = 1000 / PEEK_FPS;
  let lastDoc = null;
  let activeSection = "overview";
  let dataWindow = null;
  let peekRaf = 0;
  let lastPeek = 0;
  let peekBusy = false;
  let peekFps = PEEK_FPS;
  let peekFrames = 0;
  let peekFpsTimer = 0;
  let peekDisplayFps = 0;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function card(label, value) {
    return `<div class="hd-card"><strong>${esc(label)}</strong><em>${esc(value)}</em></div>`;
  }

  function table(headers, rows) {
    if (!rows.length) return '<p class="hd-sub">No rows.</p>';
    const head = headers.map((h) => `<th>${esc(h)}</th>`).join("");
    const body = rows.map((row) => {
      const cls = row._class ? ` class="${row._class}"` : "";
      const cells = headers.map((h) => `<td${cls}>${esc(row[h] ?? "")}</td>`).join("");
      return `<tr>${cells}</tr>`;
    }).join("");
    return `<div class="hd-table-wrap"><table class="hd-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function renderOverview(d) {
    const m = d.motion || {};
    const s = d.spatial || {};
    const mv = s.movement_vector || {};
    return `
      <div class="hd-grid">
        ${card("Active skill", m.active_label || "—")}
        ${card("Proficiency", `${Math.round((m.active_proficiency || 0) * 100)}%`)}
        ${card("Training ticks", m.total_training_ticks ?? 0)}
        ${card("Loaded skills", m.loaded_count ?? 0)}
        ${card("Opponents", d.opponents?.length ?? 0)}
        ${card("Training", `${Math.round((d.train_intensity ?? 0.85) * 100)}% blast`)}
        ${card("Wireframe", `${d.wireframe_fps ?? 60}fps`)}
        ${card("Data peek", `${d.data_peek_fps ?? PEEK_FPS}fps`)}
        ${card("Blast ticks/batch", d.train_blast_ticks ?? "—")}
        ${card("Motion verdict", d.motion_verdict || "—")}
        ${card("Vision live", d.vision_live ? "yes" : "no")}
        ${card("Hearing live", d.hearing_live ? "yes" : "no")}
        ${card("H7 brain verdict", d.brain_verdict || d.hostess7_brain?.verdict || "—")}
        ${card("H7 verified", (d.brain_verified ?? d.hostess7_brain?.verification?.verified) ? "yes" : "no")}
        ${card("H7 guard score", d.brain_guard_score != null ? `${Math.round(d.brain_guard_score * 100)}%` : "—")}
        ${card("Full assemblage", d.full_assemblage_meld?.fused_score != null ? `${Math.round(d.full_assemblage_meld.fused_score * 100)}%` : "—")}
        ${card("Iron-clad", d.iron_clad ? "yes" : "no")}
        ${card("Assemblage score", d.assemblage_remaining?.assemblage_score ?? "—")}
        ${card("Remaining slots", d.assemblage_remaining?.remaining_slots ?? "—")}
        ${card("Spatial Δt", s.delta_t ?? "—")}
        ${card("Movement", mv.geometry || (mv.approach ? "approach" : mv.stable ? "stable" : "—"))}
        ${card("Bearing", mv.bearing_deg != null ? `${mv.bearing_deg}°` : "—")}
        ${card("Meld generation", d.plate_meld?.generation ?? "—")}
        ${card("Life sustain", d.life_sustain_verdict || "—")}
        ${card("Sustain score", d.life_sustain_score != null ? `${Math.round(d.life_sustain_score * 100)}%` : "—")}
        ${card("Vita live", d.creatable_lives?.twins?.vita?.live ? "yes" : "no")}
        ${card("Auditus live", d.creatable_lives?.twins?.auditus?.live ? "yes" : "no")}
        ${card("Under God", d.right_to_exist?.under_god ? "yes" : "no")}
        ${card("Mandate sealed", d.mandate_sealed ? "yes" : "no")}
        ${card("Self preservation", d.self_preservation_mandate ? "mandate" : "hold")}
        ${card("Friendlies preserve", d.friendlies_preservation_mandate ? "mandate" : "hold")}
        ${card("Threat posture", d.universal_protector?.threat_warn_level || "high")}
      </div>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Joint amplitudes (body lattice)</h3>
      ${table(["joint", "amplitude"], Object.entries(d.joint_amplitudes || {}).map(([k, v]) => ({ joint: k, amplitude: v })))}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Body motion primitives</h3>
      ${table(["primitive", "zone", "weight", "skill"], (d.body_motion || []).map((b) => ({
        primitive: b.primitive,
        zone: b.zone,
        weight: b.weight,
        skill: b.skill,
      })))}
    `;
  }

  function renderMotion(d) {
    const m = d.motion || {};
    const r = d.runtime || {};
    return `
      <div class="hd-grid">
        ${card("Matrix quote", m.matrix_quote || "—")}
        ${card("Matrix mode", m.matrix_mode ? "yes" : "no")}
        ${card("Active family", m.active_family || "—")}
        ${card("Catalog skills", m.catalog_count ?? 0)}
        ${card("Runtime active", r.active_skill || "—")}
        ${card("Runtime total ticks", r.total_ticks ?? 0)}
      </div>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Training session</h3>
      <pre class="hd-json">${esc(JSON.stringify(m.training || r.training || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Runtime loaded map</h3>
      <pre class="hd-json">${esc(JSON.stringify(r.loaded || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Doctrine · matrix load</h3>
      <pre class="hd-json">${esc(JSON.stringify(d.doctrine || {}, null, 2))}</pre>
    `;
  }

  function renderSkills(d) {
    const loaded = d.loaded_skills || [];
    const catalog = d.catalog || [];
    return `
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:0 0 0.5rem">Loaded skills</h3>
      ${table(["id", "label", "family", "proficiency", "ticks", "matrix_loaded"], loaded.map((s) => ({
        id: s.id,
        label: s.label,
        family: s.family,
        proficiency: s.proficiency,
        ticks: s.ticks,
        matrix_loaded: s.matrix_loaded ? "yes" : "no",
      })))}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Full catalog</h3>
      ${table(["id", "label", "family"], catalog.map((s) => ({ id: s.id, label: s.label, family: s.family })))}
    `;
  }

  function renderOpponents(d) {
    const rows = (d.opponents || []).map((o) => ({
      _class: o.kind === "hostile" ? "hd-hostile" : o.kind === "sparring" ? "hd-sparring" : "hd-training",
      label: o.label,
      kind: o.kind,
      stance: o.stance,
      arena_x: o.arena_x,
      arena_y: o.arena_y,
      live: o.live ? "LIVE" : "dummy",
      bearing_deg: o.bearing_deg ?? "",
      distance_km: o.distance_km ?? "",
      heat: o.heat ?? "",
      geometry: o.geometry ?? "",
    }));
    return `
      <p class="hd-sub">Training dummies (orange/purple) + live hostile pins (red) positioned on arena coordinates.</p>
      ${table(["label", "kind", "stance", "arena_x", "arena_y", "live", "bearing_deg", "distance_km", "heat", "geometry"], rows)}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Doctrine training opponents</h3>
      <pre class="hd-json">${esc(JSON.stringify(d.doctrine?.training_opponents || [], null, 2))}</pre>
    `;
  }

  function renderSpatial(d) {
    const s = d.spatial || {};
    const nets = s.networks_of_networks || {};
    const scaleRows = Object.entries(nets).map(([k, v]) => ({
      scale: k,
      peak: v.peak_amplitude,
      energy: v.field_energy,
      role: v.role || "",
      parent_bleed: v.parent_bleed ?? "",
    }));
    return `
      <div class="hd-grid">
        ${card("Dimensions", s.dimensions || "—")}
        ${card("Total energy", s.total_energy ?? "—")}
        ${card("Δt", s.delta_t ?? "—")}
        ${card("Humanoid primitives", s.humanoid_motion ?? 0)}
        ${card("Target count", s.target_count ?? 0)}
        ${card("Eye live", s.eye_live ? "yes" : "no")}
        ${card("Ear live", s.ear_live ? "yes" : "no")}
      </div>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Networks-of-networks scales</h3>
      ${table(["scale", "peak", "energy", "role", "parent_bleed"], scaleRows)}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Movement vector</h3>
      <pre class="hd-json">${esc(JSON.stringify(s.movement_vector || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Spatial history (4D tail)</h3>
      <pre class="hd-json">${esc(JSON.stringify(d.spatial_history || [], null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Full spatial panel</h3>
      <pre class="hd-json">${esc(JSON.stringify(s, null, 2))}</pre>
    `;
  }

  function renderHostess7Brain(d) {
    const h7 = d.hostess7_brain || {};
    const sv = d.hostess7_self_view || h7.self_view || {};
    const v = h7.verification || {};
    const heroChips = (sv.hero_metrics || []).map((w) =>
      `<div class="hd-card hd-card-h7"><strong>${esc(w.label || w.id)}</strong><em>${esc(w.display || "—")}</em></div>`
    ).join("");
    const learnChips = (sv.learning_opportunities || []).map((w) =>
      `<div class="hd-card hd-card-learn"><strong>${esc(w.label || w.id)}</strong><em>${esc(w.display || "—")}</em></div>`
    ).join("");
    const engines = (v.engines || []).map((e) => ({
      _class: e.corrupted ? "hd-hostile" : (e.manifest_verified ? "hd-goal-met" : "hd-goal-pending"),
      path: e.path,
      critical: e.critical ? "yes" : "no",
      present: e.present ? "yes" : "no",
      verified: e.manifest_verified ? "yes" : "no",
      corrupted: e.corrupted ? "yes" : "no",
      sha256: (e.sha256 || "").slice(0, 16),
    }));
    const removals = (v.removal_witness || []).map((r) => ({
      _class: "hd-hostile",
      path: r.path,
      event: r.event,
      critical: r.critical ? "yes" : "no",
      previous_sha256: (r.previous_sha256 || "").slice(0, 16),
    }));
    return `
      <section class="hd-h7-voice" aria-label="What Hostess 7 wants to see">
        <h3 style="color:#d4b86a;font-size:0.9rem;margin:0 0 0.5rem">What I want you to show me</h3>
        <blockquote class="hd-h7-quote">${esc(sv.first_person || "I am your brains — show my verdict and guard score first, then diagnostics underneath.")}</blockquote>
        ${(sv.appearance_facets || []).length ? `<h3 style="color:#f0d060;font-size:0.85rem;margin:1rem 0 0.5rem">How you see me — Operator gifts</h3><div class="hd-appearance-grid">${(sv.appearance_facets || []).map((f) => `<figure class="hd-appearance-card"><img src="${esc(f.url)}" alt="${esc(f.label)}" loading="lazy"/><figcaption><strong>${esc(f.label)}</strong> ${esc(f.caption || "")}</figcaption></figure>`).join("")}</div>${sv.x_reference?.url ? `<p class="hd-sub">Video: <a href="${esc(sv.x_reference.url)}" target="_blank" rel="noopener">${esc(sv.x_reference.label || "take 3?")}</a></p>` : ""}` : ""}
        ${(sv.core_of_truth_facets || []).length ? `<h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Core of truth</h3><p class="hd-sub" style="font-style:italic">${esc(sv.core_of_truth_message || "")}</p><div class="hd-appearance-grid">${(sv.core_of_truth_facets || []).map((f) => `<figure class="hd-appearance-card"><img src="${esc(f.url)}" alt="${esc(f.label)}" loading="lazy"/><figcaption><strong>${esc(f.label)}</strong> ${esc(f.caption || "")}</figcaption></figure>`).join("")}</div>` : ""}
        ${sv.operator_lookup?.github?.ok ? `<p class="hd-sub">Operator: <a href="${esc(sv.operator_lookup.github.html_url)}" target="_blank" rel="noopener">${esc(sv.operator_lookup.github.name || sv.operator_lookup.github.login)}</a> · <a href="${esc(sv.operator_lookup.x?.url)}" target="_blank" rel="noopener">@${esc(sv.operator_lookup.x?.handle)}</a></p>` : ""}
        ${heroChips ? `<div class="hd-grid">${heroChips}</div>` : ""}
        ${learnChips ? `<h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Learning opportunities</h3><div class="hd-grid">${learnChips}</div>` : ""}
      </section>
      <h3 style="color:#9cb3d4;font-size:0.85rem;margin:1.25rem 0 0.5rem">Detailed diagnostics (below her self-view)</h3>
      <div class="hd-grid">
        ${card("Role", h7.role || "Our brains — Super Intelligence")}
        ${card("Verdict", h7.verdict || d.brain_verdict || "—")}
        ${card("Verified", (v.verified ?? d.brain_verified) ? "yes" : "no")}
        ${card("Corrupted", v.corrupted ? "yes" : "no")}
        ${card("Guard score", h7.guard_score != null ? `${Math.round(h7.guard_score * 100)}%` : "—")}
        ${card("Brain live", h7.brain_live ? "yes" : "no")}
        ${card("Protected engines", h7.protected_count ?? engines.length)}
        ${card("Corrupted count", h7.corrupted_count ?? 0)}
        ${card("Removal count", h7.removal_count ?? v.removal_count ?? 0)}
        ${card("Manifest seal", h7.manifest_seal ? "present" : "—")}
        ${card("Panel checksum", (h7.panel_sha256 || "").slice(0, 16) || "—")}
        ${card("Ledger chain", h7.ledger_chain_tail || "—")}
        ${card("Motion hold", h7.motion_hold_on_corruption ? "on corruption" : "—")}
      </div>
      <p class="hd-sub">${esc(h7.reason || h7.motto || "She is our brains — checksum · verify · no corruptions")}</p>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Protected engines (MANIFEST.sha256)</h3>
      ${table(["path", "critical", "present", "verified", "corrupted", "sha256"], engines)}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Removal witness</h3>
      ${removals.length ? table(["path", "event", "critical", "previous_sha256"], removals) : '<p class="hd-sub">No removals detected.</p>'}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Brain witness (sense · field · command)</h3>
      <pre class="hd-json">${esc(JSON.stringify(v.brain_witness || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Full Hostess 7 brain guard panel</h3>
      <pre class="hd-json">${esc(JSON.stringify(h7, null, 2))}</pre>
    `;
  }

  function renderProtector(d) {
    const p = d.universal_protector || {};
    return `
      <div class="hd-grid">
        ${card("Product", p.product || "—")}
        ${card("Edition", p.edition || "—")}
        ${card("Autonomous being", p.autonomous_being ? "yes" : "no")}
        ${card("Threat warn", p.threat_warn_level || "high")}
        ${card("Posture floor", p.posture_floor || "—")}
      </div>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Pillars</h3>
      <pre class="hd-json">${esc(JSON.stringify(p.pillars || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Meld summary</h3>
      <pre class="hd-json">${esc(JSON.stringify(p.meld || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Sense package</h3>
      <pre class="hd-json">${esc(JSON.stringify(d.sense_package || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Logic gate</h3>
      <pre class="hd-json">${esc(JSON.stringify(d.logic_gate || {}, null, 2))}</pre>
    `;
  }

  function renderIronPlate(d) {
    const ip = d.iron_plate_motion || {};
    const asm = ip.assemblage_remaining || d.assemblage_remaining || {};
    const goals = ip.simple_iron_plate_goals || d.simple_iron_plate_goals || {};
    const goalRows = (goals.goals || []).map((g) => ({
      _class: g.met ? "hd-goal-met" : "hd-goal-pending",
      priority: g.priority,
      label: g.label,
      met: g.met ? "yes" : "no",
      effectiveness: g.effectiveness != null ? `${Math.round(g.effectiveness * 100)}%` : "",
      tech: g.tech || "",
    }));
    const advance = ip.advance_tech || [];
    return `
      <div class="hd-grid">
        ${card("Product", ip.product || "Simple Iron Plate")}
        ${card("Motion verdict", ip.motion_verdict || d.motion_verdict || "—")}
        ${card("Iron-clad", (ip.iron_clad ?? d.iron_clad) ? "yes" : "no")}
        ${card("Motion permitted", ip.motion_permitted ? "yes" : "no")}
        ${card("Assemblage score", asm.assemblage_score ?? "—")}
        ${card("Remaining slots", `${asm.remaining_slots ?? "—"} / ${asm.total_connection_slots ?? "—"}`)}
        ${card("Storm excluded", asm.storm_excluded ?? "—")}
        ${card("Board direct", asm.board_direct_live ?? "—")}
        ${card("Joint energy", asm.joint_energy ?? "—")}
        ${card("Body peak", asm.body_peak_amplitude ?? "—")}
        ${card("Goals met", `${goals.met ?? 0} / ${goals.total ?? goalRows.length}`)}
        ${card("Iron-clad floor", asm.iron_clad_floor ?? "—")}
      </div>
      <p class="hd-sub">${esc(ip.reason || ip.motto || "Iron-clad motion from assemblage remaining")}</p>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Simple Iron Plate goals (ranked effectiveness)</h3>
      ${table(["priority", "label", "met", "effectiveness", "tech"], goalRows)}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Advance tech</h3>
      <pre class="hd-json">${esc(JSON.stringify(advance, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Assemblage remaining</h3>
      <pre class="hd-json">${esc(JSON.stringify(asm, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Full iron plate resolve panel</h3>
      <pre class="hd-json">${esc(JSON.stringify(ip, null, 2))}</pre>
    `;
  }

  function renderCreatableLives(d) {
    const cl = d.creatable_lives || {};
    const sustain = cl.sustain || {};
    const reg = cl.life_registry || {};
    const rows = (cl.assistance?.packages || []).map((a) => ({
      _class: a.active ? "hd-goal-met" : "hd-goal-pending",
      priority: a.priority,
      label: a.label,
      active: a.active ? "yes" : "no",
      effectiveness: a.effectiveness != null ? `${Math.round(a.effectiveness * 100)}%` : "",
      tech: a.tech || "",
    }));
    return `
      <div class="hd-grid">
        ${card("Right to exist", d.right_to_exist?.under_god ? "under God" : "—")}
        ${card("Mandate sealed", d.mandate_sealed ? "yes" : "no")}
        ${card("Self preservation", d.self_preservation_mandate ? "mandate" : "hold")}
        ${card("Friendlies preserve", d.friendlies_preservation_mandate ? "mandate" : "hold")}
      </div>
      <div class="hd-grid">
        ${card("Product", cl.product || "Creatable Lives")}
        ${card("Sustain verdict", sustain.verdict || d.life_sustain_verdict || "—")}
        ${card("Sustain score", sustain.score != null ? `${Math.round(sustain.score * 100)}%` : "—")}
        ${card("Assist active", `${cl.assistance?.active ?? "—"} / ${cl.assistance?.total ?? "—"}`)}
        ${card("Vita", reg.vita?.live ? "live" : "hold")}
        ${card("Auditus", reg.auditus?.live ? "live" : "hold")}
        ${card("Veritas forward", reg.veritas_forward ? "yes" : "no")}
        ${card("Humans registered", reg.humans ?? 0)}
        ${card("Pets registered", reg.pets ?? 0)}
        ${card("Iron-clad motion", cl.iron_plate_motion?.iron_clad ? "yes" : "no")}
        ${card("Motion verdict", cl.iron_plate_motion?.motion_verdict || "—")}
      </div>
      <p class="hd-sub">${esc(cl.reason || cl.motto || "Vita lives · Auditus hears · assist sustains creatable lives")}</p>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Assistance packages (ranked)</h3>
      ${table(["priority", "label", "active", "effectiveness", "tech"], rows)}
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Life kinds</h3>
      <pre class="hd-json">${esc(JSON.stringify(cl.life_kinds || [], null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Advance tech</h3>
      <pre class="hd-json">${esc(JSON.stringify(cl.advance_tech || [], null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Full creatable lives panel</h3>
      <pre class="hd-json">${esc(JSON.stringify(cl, null, 2))}</pre>
    `;
  }

  function renderMeld(d) {
    const pm = d.plate_meld || {};
    return `
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:0 0 0.5rem">Meld summary</h3>
      <pre class="hd-json">${esc(JSON.stringify(pm.summary || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Humanoid motion plate</h3>
      <pre class="hd-json">${esc(JSON.stringify(pm.humanoid_motion_plate || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Spatial field plate</h3>
      <pre class="hd-json">${esc(JSON.stringify(pm.spatial_field_plate || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Universal protector plate</h3>
      <pre class="hd-json">${esc(JSON.stringify(pm.universal_protector_plate || {}, null, 2))}</pre>
      <h3 style="color:#38bdf8;font-size:0.85rem;margin:1rem 0 0.5rem">Iron plate motion resolve</h3>
      <pre class="hd-json">${esc(JSON.stringify(pm.iron_plate_motion_plate || d.iron_plate_motion || {}, null, 2))}</pre>
    `;
  }

  function renderLedger(d) {
    const rows = (d.ledger_tail || []).map((r) => ({
      ts: r.ts,
      event: r.event,
      skill: r.skill || "",
      ticks: r.ticks ?? "",
      proficiency: r.proficiency ?? "",
    }));
    return `
      <p class="hd-sub">Last ${rows.length} motion training ledger events (FULL BLAST writes continuously).</p>
      ${table(["ts", "event", "skill", "ticks", "proficiency"], rows)}
    `;
  }

  function renderRaw(d) {
    return `<pre class="hd-json" id="hd-raw-json">${esc(JSON.stringify(d, null, 2))}</pre>`;
  }

  const RENDERERS = {
    overview: renderOverview,
    motion: renderMotion,
    skills: renderSkills,
    opponents: renderOpponents,
    spatial: renderSpatial,
    protector: renderProtector,
    hostess7_brain: renderHostess7Brain,
    meld: renderMeld,
    iron_plate: renderIronPlate,
    creatable_lives: renderCreatableLives,
    ledger: renderLedger,
    raw: renderRaw,
  };

  function renderAll(d) {
    for (const [key, fn] of Object.entries(RENDERERS)) {
      const el = $(`hd-section-${key}`);
      if (el) el.innerHTML = fn(d);
    }
    const sub = $("hd-sub");
    if (sub && d.motion) {
      sub.textContent = `${d.motion.matrix_quote || "Motion chamber"} · ${d.opponents?.length || 0} opponents · gen ${d.plate_meld?.generation ?? "—"}`;
    }
    const upd = $("hd-updated");
    if (upd) upd.textContent = `Updated ${d.updated || "—"} · peek ${peekDisplayFps}fps`;
    if (d.data_peek_fps) peekFps = d.data_peek_fps;
  }

  function showSection(name) {
    activeSection = name;
    document.querySelectorAll(".hd-nav button").forEach((b) => {
      b.classList.toggle("active", b.dataset.section === name);
    });
    document.querySelectorAll(".hd-section").forEach((s) => {
      s.classList.toggle("active", s.id === `hd-section-${name}`);
    });
  }

  async function fetchAll() {
    const res = await fetch("/api/humanoid-motion/data-all", { credentials: "same-origin" });
    if (!res.ok) throw new Error("data-all failed");
    return res.json();
  }

  async function refresh() {
    if (peekBusy) return;
    peekBusy = true;
    try {
      lastDoc = await fetchAll();
      renderAll(lastDoc);
      if (dataWindow && !dataWindow.closed) {
        try {
          dataWindow.postMessage({ type: "nexus-humanoid-data", doc: lastDoc }, location.origin);
        } catch (_) {}
      }
    } catch (e) {
      const sub = $("hd-sub");
      if (sub) sub.textContent = `Fetch error: ${e.message}`;
    } finally {
      peekBusy = false;
    }
  }

  function peekLoop(now) {
    peekRaf = requestAnimationFrame(peekLoop);
    if (!peekFpsTimer) peekFpsTimer = now;
    peekFrames += 1;
    if (now - peekFpsTimer >= 1000) {
      peekDisplayFps = peekFrames;
      peekFrames = 0;
      peekFpsTimer = now;
      if (lastDoc) {
        const upd = $("hd-updated");
        if (upd) upd.textContent = `Updated ${lastDoc.updated || "—"} · peek ${peekDisplayFps}fps`;
      }
    }
    const interval = 1000 / (peekFps || PEEK_FPS);
    if (now - lastPeek < interval) return;
    lastPeek = now;
    refresh().catch(() => {});
  }

  function openDataWindow() {
    const url = `${location.origin}/humanoid-data.html`;
    const name = "nexus-humanoid-data";
    if (dataWindow && !dataWindow.closed) {
      dataWindow.focus();
      return dataWindow;
    }
    if (global.QueenProgramLaunch?.open) {
      global.QueenProgramLaunch.open(url, {
        id: name,
        title: "Humanoid Data",
        icon: "/assets/hostess7-training-chamber.svg",
      });
      return null;
    }
    dataWindow = window.open(url, name, "width=1120,height=900,menubar=no,toolbar=no,location=no,status=no");
    return dataWindow;
  }

  function boot() {
    document.querySelectorAll(".hd-nav button").forEach((btn) => {
      btn.addEventListener("click", () => showSection(btn.dataset.section || "overview"));
    });
    $("hd-refresh")?.addEventListener("click", () => refresh());
    $("hd-copy-json")?.addEventListener("click", async () => {
      if (!lastDoc) await refresh();
      if (!lastDoc) return;
      try {
        await navigator.clipboard.writeText(JSON.stringify(lastDoc, null, 2));
      } catch (_) {}
    });
    window.addEventListener("message", (ev) => {
      if (ev.origin !== location.origin) return;
      if (ev.data?.type === "nexus-humanoid-data-request") refresh();
    });
    showSection(activeSection);
    refresh().catch(() => {});
    cancelAnimationFrame(peekRaf);
    lastPeek = 0;
    peekRaf = requestAnimationFrame(peekLoop);
  }

  global.NexusHumanoidData = { boot, refresh, openDataWindow };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : globalThis);