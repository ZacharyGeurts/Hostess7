/**
 * Queen CHIPS & Cores — Webbrowser surface + Universal Combinatronic bands.
 */
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function bandClass(pipe) {
    const p = String(pipe || "").toLowerCase();
    if (p === "narrow") return "narrow";
    if (p === "warm") return "warm";
    return "cold";
  }

  function renderBands(pred) {
    const grid = $("qcc-band-grid");
    if (!grid) return;
    const bands = pred?.bands || [];
    if (!bands.length) {
      grid.innerHTML = '<p class="qcc-muted">Path bands loading…</p>';
      return;
    }
    grid.innerHTML = bands
      .map((band) => {
        const cls = bandClass(band.pipe_width);
        const slots = (band.slots || [])
          .map(
            (s) =>
              `<div class="qcc-slot" title="${esc(s.chip_id)}">` +
              `<span class="qcc-slot-pct">${esc(s.path_pct)}%</span>` +
              `<span class="qcc-slot-id">${esc(s.chip_id)}</span></div>`
          )
          .join("");
        return (
          `<section class="qcc-band-row ${cls}">` +
          `<div class="qcc-band-head">` +
          `<strong>Band ${esc(band.band)} · ${esc(band.pipe_width)}</strong>` +
          `<span>${esc(band.path_count)} paths · ${esc(band.band_pct)}%</span>` +
          `</div>` +
          `<div class="qcc-slot-grid">${slots || '<span class="qcc-muted">empty</span>'}</div>` +
          `</section>`
        );
      })
      .join("");
  }

  function renderLeaves(doc) {
    const el = $("qcc-leaves");
    if (!el) return;
    const leaves = doc?.combinatorics_leaves || [];
    if (!leaves.length) {
      el.innerHTML = '<p class="qcc-muted">No combinatorics leaves cached — refresh battery.</p>';
      return;
    }
    el.innerHTML = leaves
      .slice(0, 48)
      .map(
        (leaf) =>
          `<div class="qcc-leaf">` +
          `<strong>${esc(leaf.label || leaf.chip_id || leaf.id)}</strong>` +
          `<small>${esc(leaf.family)} · ${esc(leaf.path_pct)}% · band ${esc(leaf.band)} slot ${esc(leaf.slot)} · ${esc(leaf.pipe_width || leaf.kind)}</small>` +
          `</div>`
      )
      .join("");
  }

  function renderPlateDimensions(doc) {
    const el = $("qcc-plate-dimensions");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    if (panel.group_count == null && !panel.dimensions) {
      el.innerHTML = '<p class="qcc-muted">Plate dimensions loading…</p>';
      return;
    }
    const dims = panel.dimensions || {};
    const travel = panel.travel || {};
    const meta = (panel.meta_plates || [])
      .map(
        (m) =>
          `<span class="qcc-meta-plate" title="${esc((m.members || []).join(", "))}">` +
          `${esc(m.id)} · ${esc(m.present)}/${esc(m.total)}</span>`
      )
      .join("");
    el.innerHTML = [
      `<div class="qcc-dim-meta">`,
      `<span>grid <strong>${dims.width ?? "—"}×${dims.length ?? "—"}</strong></span>`,
      `<span>groups <strong>${panel.group_count ?? "—"}</strong> → meta <strong>${panel.meta_plate_count ?? "—"}</strong></span>`,
      `<span>fewer <strong>${panel.fewer_plates ?? "—"}</strong></span>`,
      `<span>travel <strong>−${travel.reduction_pct ?? "—"}%</strong></span>`,
      `</div>`,
      `<div class="qcc-meta-plates">${meta || '<span class="qcc-muted">no meta-plates</span>'}</div>`,
    ].join("");
  }

  function renderCombinamatrix(doc) {
    const el = $("qcc-combinamatrix");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    const dims = panel.dimensions || {};
    const cells = panel.top_cells || [];
    if (!dims.width && panel.cell_count == null) {
      el.innerHTML = '<p class="qcc-muted">Combinamatrix loading…</p>';
      return;
    }
    el.innerHTML = [
      `<div class="qcc-cm-meta">`,
      `<span>matrix <strong>${dims.width ?? "—"}×${dims.length ?? "—"}</strong></span>`,
      `<span>cells <strong>${panel.cell_count ?? dims.filled ?? "—"}</strong></span>`,
      `<span>facets <strong>${panel.facet_count ?? "—"}</strong></span>`,
      `</div>`,
      `<div class="qcc-cm-cells">`,
      cells
        .map(
          (c) =>
            `<span class="qcc-cm-cell" title="${esc(c.id)}">` +
            `r${esc(c.row)}c${esc(c.col)} · ${esc(c.activation)}</span>`
        )
        .join("") || '<span class="qcc-muted">no cells</span>',
      `</div>`,
    ].join("");
  }

  function renderSteelPlates(doc) {
    const el = $("qcc-steel-plates");
    if (!el) return;
    const panel = doc?.panel || doc?.battery?.panel || doc || {};
    const depth = panel.connection_depth || {};
    const wires = panel.wires || {};
    const plates = panel.top_plates || [];
    const paths = panel.top_deep_paths || [];
    if (!panel.plate_count && !depth.max) {
      el.innerHTML = '<p class="qcc-muted">Steel Neural Plates loading…</p>';
      return;
    }
    el.innerHTML = [
      `<div class="qcc-steel-meta">`,
      `<span>plates <strong>${panel.plate_count ?? "—"}</strong></span>`,
      `<span>depth <strong>${depth.achieved ?? "—"}/${depth.max ?? "—"}</strong></span>`,
      `<span>wires <strong>${wires.total ?? "—"}</strong></span>`,
      `<span>deep paths <strong>${depth.deep_path_count ?? "—"}</strong></span>`,
      `</div>`,
      `<div class="qcc-steel-plate-row">`,
      plates
        .map(
          (p) =>
            `<span class="qcc-steel-plate" title="${esc(p.domain)}">` +
            `${esc(p.domain)} · ${esc(p.member_count)} · d${esc(p.depth_layer)}</span>`
        )
        .join("") || '<span class="qcc-muted">no plates</span>',
      `</div>`,
      `<div class="qcc-steel-paths">`,
      paths
        .slice(0, 6)
        .map(
          (p) =>
            `<span class="qcc-steel-path">${esc((p.path || []).slice(0, 4).join(" → "))}` +
            `${(p.path || []).length > 4 ? " …" : ""} · ${esc(p.hops)}h</span>`
        )
        .join("") || '<span class="qcc-muted">no deep paths yet</span>',
      `</div>`,
    ].join("");
  }

  function renderUniversalNeural(doc) {
    const el = $("qcc-universal-neural");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    const battery = doc?.battery || panel;
    const cm = battery.combinamatrix || panel.combinamatrix || {};
    const uni = battery.universal || panel.universal || {};
    const steps = battery.curriculum_steps || panel.curriculum_steps || [];
    if (!panel.neural_id && !battery.neural_id && !steps.length) {
      el.innerHTML = '<p class="qcc-muted">Universal Neural loading…</p>';
      return;
    }
    el.innerHTML = [
      `<div class="qcc-un-meta">`,
      `<span>neural <strong>${esc(panel.neural_id || battery.neural_id || "universal_combinamatrix")}</strong></span>`,
      `<span>gen <strong>${panel.generation ?? battery.generation ?? "—"}</strong></span>`,
      `<span>universal <strong>${uni.leaf_count ?? "—"}</strong> leaves</span>`,
      `<span>matrix <strong>${cm.cells ?? cm.cell_count ?? "—"}</strong> cells</span>`,
      `</div>`,
      `<div class="qcc-un-steps">`,
      steps
        .map((s) => `<span class="qcc-un-step${s.ok ? " ok" : ""}">${esc(s.step)}</span>`)
        .join("") || '<span class="qcc-muted">run teach to load curriculum</span>',
      `</div>`,
    ].join("");
  }

  function renderGrowth(doc) {
    const el = $("qcc-growth");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    if (panel.file_count == null && !panel.growth_curve?.length) {
      el.innerHTML = '<p class="qcc-muted">Growth scan loading…</p>';
      return;
    }
    const curve = (panel.growth_curve || [])
      .map(
        (g) =>
          `<span class="qcc-growth-gen">g${esc(g.generation)} ` +
          `d${esc(g.surface_depth)} · ${esc(g.surface_score)}</span>`
      )
      .join("");
    el.innerHTML = [
      `<div class="qcc-growth-meta">`,
      `<span><strong>${panel.file_count ?? "—"}</strong> files</span>`,
      `<span>optimal width <strong>${panel.optimal_width ?? "—"}</strong></span>`,
      `<span>surface <strong>${panel.best_surface_score ?? "—"}</strong></span>`,
      `<span>${esc(panel.sort_method || "van_emde_bois")}</span>`,
      `</div>`,
      `<div class="qcc-growth-curve">${curve || '<span class="qcc-muted">no curve</span>'}</div>`,
    ].join("");
  }

  function renderSequence(doc) {
    const el = $("qcc-sequence");
    const aml = $("qcc-ammolang");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    if (panel.sequence_length == null && panel.gapless == null) {
      el.innerHTML = '<p class="qcc-muted">Sequence loading…</p>';
      if (aml) aml.textContent = "";
      return;
    }
    el.innerHTML = [
      `<div class="qcc-seq-meta">`,
      `<span>gapless <strong>${panel.gapless ? "yes" : "fill"}</strong></span>`,
      `<span><strong>${panel.sequence_length ?? "—"}</strong> steps</span>`,
      `<span><strong>${panel.leaf_count ?? "—"}</strong> leaves</span>`,
      `<span>gaps <strong>${panel.gap_count ?? 0}</strong> · filled <strong>${panel.gap_fill_count ?? 0}</strong></span>`,
      `</div>`,
      (panel.sample_sequence || [])
        .slice(0, 8)
        .map(
          (s) =>
            `<div class="qcc-seq-row">` +
            `<span>${esc(s.sequence_rank)}</span>` +
            `<code>${esc(s.id)}</code>` +
            `<small>${esc(s.facet)} · ${esc(s.kind)}</small>` +
            `</div>`
        )
        .join(""),
    ].join("");
    if (aml) {
      aml.textContent = (panel.ammolang_preview || []).join("\n") + "\n…";
    }
  }

  function renderSpiderWire(doc) {
    const el = $("qcc-spider-wire");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    const pri = panel.top_priorities || doc?.top_priorities || [];
    if (!pri.length && panel.wire_count == null) {
      el.innerHTML = '<p class="qcc-muted">Spider wire loading…</p>';
      return;
    }
    const bn = panel.bottleneck_count ?? doc?.bottleneck_count ?? "—";
    const lanes = panel.lane_count ?? doc?.lane_count ?? "—";
    const wires = panel.wire_count ?? doc?.wire_count ?? "—";
    el.innerHTML = [
      `<div class="qcc-spider-meta">`,
      `<span>view <strong>ironclad outward</strong></span>`,
      `<span><strong>${wires}</strong> wires</span>`,
      `<span><strong>${lanes}</strong> lanes</span>`,
      `<span>bottlenecks <strong>${bn}</strong></span>`,
      `</div>`,
      `<div class="qcc-spider-pri">`,
      pri
        .slice(0, 12)
        .map(
          (p) =>
            `<div class="qcc-spider-row">` +
            `<span class="qcc-spider-rank">${esc(p.priority_rank)}</span>` +
            `<code>${esc(p.instruction)}</code>` +
            `<small>${esc(p.pipe_width)} · pri ${esc(p.neural_priority)}</small>` +
            `</div>`
        )
        .join(""),
      `</div>`,
    ].join("");
  }

  function renderChipGallery(visuals) {
    const el = $("qcc-chip-gallery");
    if (!el) return;
    const items = (visuals?.manifest?.chips?.items || []).filter((r) => r.ok);
    if (!items.length) {
      el.innerHTML = '<p class="qcc-muted">Chip macro gallery loading…</p>';
      return;
    }
    el.innerHTML = items
      .map(
        (chip) =>
          `<figure class="qcc-chip-card">` +
          `<img src="${esc(chip.world_url)}" alt="${esc(chip.chip_id)}" loading="lazy" width="240" height="180" />` +
          `<figcaption>` +
          `<strong>${esc(chip.chip_id)}</strong>` +
          `<small>${esc(chip.pins)} pins · ${esc(chip.package || "")}</small>` +
          `</figcaption></figure>`
      )
      .join("");
  }

  function renderBookGallery(visuals) {
    const el = $("qcc-book-gallery");
    if (!el) return;
    const items = (visuals?.manifest?.books?.items || []).filter((r) => r.ok);
    if (!items.length) {
      el.innerHTML = '<p class="qcc-muted">Explaining language covers loading…</p>';
      return;
    }
    el.innerHTML = items
      .slice(0, 36)
      .map(
        (book) =>
          `<figure class="qcc-book-card">` +
          `<img src="${esc(book.world_url)}" alt="Explaining ${esc(book.label || book.lang_id)}" loading="lazy" width="100" height="150" />` +
          `<figcaption>` +
          `<strong>Explaining ${esc(book.label || book.lang_id)}</strong>` +
          `<small>${esc(book.command_count)} cmds · H7</small>` +
          `</figcaption></figure>`
      )
      .join("");
  }

  function renderCombinatronic(doc, visuals) {
    const meta = $("qcc-comb-meta");
    if (!meta) return;
    const pred = doc?.path_prediction || {};
    const counts = doc?.counts || {};
    const safety = doc?.line_safety || {};
    const vis = visuals?.manifest || {};
    meta.innerHTML = [
      `<span><strong>${counts.total ?? "—"}</strong> chips</span>`,
      `<span><strong>${doc.leaf_count ?? "—"}</strong> leaves</span>`,
      `<span><strong>${pred.total_pct ?? "—"}%</strong> path total</span>`,
      `<span><strong>${(pred.bands || []).length}</strong> bands</span>`,
      `<span>macro <strong>${vis.chips?.count ?? "—"}</strong></span>`,
      `<span>H7 books <strong>${vis.books?.count ?? "—"}</strong></span>`,
      `<span>narrow width <strong>${safety.narrow_band_width ?? "—"}</strong></span>`,
      `<span>policy <strong>${esc(safety.pipe_policy || "adjacent_narrow_only")}</strong></span>`,
    ].join("");
    renderBands(pred);
    renderChipGallery(visuals);
    renderBookGallery(visuals);
    renderLeaves(doc);
  }

  function renderChipsCore(doc) {
    const el = $("qcc-chips-core");
    if (!el) return;
    const panel = doc?.panel || doc || {};
    const counts = panel.counts || {};
    if (panel.condensed == null && panel.pending == null) {
      el.innerHTML = '<p class="qcc-muted">CHIPS core loading…</p>';
      return;
    }
    el.innerHTML = [
      `<div class="qcc-core-meta">`,
      `<span>state <strong>${panel.condensed ? "condensed" : "scattered"}</strong></span>`,
      `<span>ironclad <strong>${panel.ironclad_sealed ? "sealed" : "open"}</strong></span>`,
      `<span>modules <strong>${counts.core_modules ?? "—"}</strong></span>`,
      `<span>chips <strong>${counts.chips ?? "—"}</strong></span>`,
      `<span>ratio <strong>${counts.compression_ratio ?? "—"}×</strong></span>`,
      `</div>`,
      `<p class="qcc-muted">${esc(panel.posture || "")}</p>`,
    ].join("");
  }

  async function refresh() {
    const [chips, boot, comb, chipsCore, visuals, spider, growth, plateDims, combinamatrix, universalNeural, steelPlates, sequence] = await Promise.all([
      fetch("/api/chips", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/queen-boot", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/chips/combinatronic", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/chips/core", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/combinatronic/visuals", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/combinatronic/spider-wire", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/combinatronics/growth", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/plate-dimensions", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/combinamatrix", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/universal-neural", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/steel-neural-plates", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      fetch("/api/combinatorics/sequence", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]);
    const chipsDoc = chips || {};
    const bootDoc = boot || {};
    const combDoc = comb || chipsDoc.combinatronic || {};
    const tree = chipsDoc.chips || {};
    const g16 = chipsDoc.grok16 || {};
    const die = bootDoc.chips || bootDoc.cores || [];
    const battery = chipsDoc.chip_battery || {};

    const coreDoc = chipsCore || {};
    const corePanel = coreDoc.panel || coreDoc || {};
    $("qcc-status").innerHTML = [
      `<span class="gr-pill${tree.present ? " ok" : ""}">CHIPS ${tree.headers || 0}</span>`,
      `<span class="gr-pill${g16.ready ? " ok" : ""}">G16 ${esc(g16.profile || "field_opt")}</span>`,
      `<span class="gr-pill${combDoc.ok !== false ? " ok" : ""}">Combinatronic ${battery.leaf_count ?? combDoc.leaf_count ?? "—"}</span>`,
      `<span class="gr-pill${corePanel.condensed ? " ok" : ""}">Core ${corePanel.condensed ? "sealed" : "pending"}</span>`,
      `<span class="gr-pill ok">Webbrowser</span>`,
    ].join("");

    $("qcc-chips").innerHTML = [
      `<p><strong>${tree.headers || 0}</strong> headers · ${(tree.platforms || []).length} platforms</p>`,
      `<p>${esc(tree.root || "CHIPS tree")}</p>`,
      (g16.chips_optimizations || [])
        .slice(0, 8)
        .map((h) => `<p><code>${esc(h.chip || h.header || h)}</code></p>`)
        .join("") || "<p>No hot paths cached.</p>",
    ].join("");

    $("qcc-cores").innerHTML = die.length
      ? `<ul>${die.map((c) => `<li>${esc(c.name || c.id)} — ${esc(c.role || "")}</li>`).join("")}</ul>`
      : "<p>Boot map loading…</p>";

    renderCombinatronic(combDoc, visuals || {});
    renderChipsCore(coreDoc);
    renderGrowth(growth || {});
    renderPlateDimensions(plateDims || {});
    renderCombinamatrix(combinamatrix || {});
    renderUniversalNeural(universalNeural || {});
    renderSteelPlates(steelPlates || {});
    renderSequence(sequence || {});
    renderSpiderWire(spider || {});

    const vis = visuals?.manifest || {};
    const sw = spider?.panel || spider || {};
    const gr = growth?.panel || growth || {};
    const pd = plateDims?.panel || plateDims || {};
    const cm = combinamatrix?.panel || combinamatrix || {};
    const un = universalNeural?.panel || universalNeural?.battery || universalNeural || {};
    const sp = steelPlates?.panel || steelPlates?.battery?.panel || steelPlates || {};
    $("qcc-sub").textContent =
      `AmmoOS growth · ${gr.file_count ?? "—"} files · width ${gr.optimal_width ?? "—"} · ` +
      `matrix ${cm.dimensions?.width ?? "—"}×${cm.dimensions?.length ?? "—"} · ` +
      `steel ${sp.plate_count ?? "—"} plates · depth ${sp.connection_depth?.achieved ?? "—"} · ` +
      `neural gen ${un.generation ?? "—"} · ` +
      `plates ${pd.group_count ?? "—"}→${pd.meta_plate_count ?? "—"} · ` +
      `Ironclad · ${sw.lane_count ?? "—"} lanes · ${sw.bottleneck_count ?? 0} bottlenecks · ` +
      `${combDoc.leaf_count ?? battery.leaf_count ?? "—"} leaves · ${vis.chips?.count ?? "—"} chips`;
  }

  $("qcc-refresh")?.addEventListener("click", refresh);
  refresh();
  setInterval(refresh, 30000);
})();