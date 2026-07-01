/**
 * AmmoCode 2027 — background combinatorics + harder rewrite client.
 */
(function (global) {
  "use strict";

  let patterns = null;
  let doctrine = null;
  let lastCycle = null;

  async function loadPatterns() {
    if (patterns) return patterns;
    try {
      const r = await fetch("data/combinatorics-rewrite-patterns.json", { cache: "no-store" });
      if (r.ok) patterns = await r.json();
    } catch (_) {}
    patterns = patterns || { patterns: [], tree: {} };
    return patterns;
  }

  async function loadDoctrine() {
    if (doctrine) return doctrine;
    try {
      const r = await fetch("data/ammocode-2027-doctrine.json", { cache: "no-store" });
      if (r.ok) doctrine = await r.json();
    } catch (_) {}
    doctrine = doctrine || { compiler_gui: { background_combinatorics: true } };
    return doctrine;
  }

  function lineOf(text, index) {
    return text.slice(0, index).split("\n").length;
  }

  function scanLocal(content, lang) {
    const doc = patterns || { patterns: [] };
    const findings = [];
    let blocked = false;
    for (const row of doc.patterns || []) {
      const langs = row.langs;
      if (langs && lang && !langs.includes(lang) && !langs.includes("*")) continue;
      let rx;
      try {
        rx = new RegExp(row.pattern, "gim");
      } catch (_) {
        continue;
      }
      let m;
      while ((m = rx.exec(content)) !== null) {
        findings.push({
          id: row.id,
          line: lineOf(content, m.index),
          match: m[0].slice(0, 80),
          severity: row.severity || "bad",
          message: row.message,
          use_instead: row.use_instead,
          combinatorics: true,
        });
        if (row.block || row.severity === "critical" || row.severity === "bad") blocked = true;
      }
    }
    return { findings, blocked, finding_count: findings.length };
  }

  async function scan(content, lang) {
    await loadPatterns();
    return scanLocal(content, lang);
  }

  async function runCycle(profile) {
    const api = global.AmmoCodeG16?.cfg?.()?.apiBase;
    if (api) {
      try {
        const r = await fetch(api, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "combinatorics", profile: profile || "belt_2_0" }),
        });
        const j = await r.json();
        if (j.ok !== undefined) {
          lastCycle = j;
          return j;
        }
      } catch (_) {}
    }
    await loadPatterns();
    lastCycle = {
      ok: true,
      combinatorics: {
        background: true,
        operator_combinatorics: false,
        facets: patterns?.facets || [],
        tree: patterns?.tree || {},
      },
    };
    return lastCycle;
  }

  function renderPanel(el) {
    if (!el) return;
    const c = lastCycle?.combinatorics || {};
    const tree = c.tree || patterns?.tree || {};
    el.innerHTML = [
      '<div class="ac-comb-head">Background combinatorics</div>',
      `<div class="ac-comb-line">Operator crank: <strong>${c.operator_combinatorics ? "on" : "off"}</strong></div>`,
      `<div class="ac-comb-line">Facets: ${(c.facets || patterns?.facets || []).join(" · ") || "—"}</div>`,
      `<div class="ac-comb-line">Tree depth cap: ${tree.max_depth ?? 4}</div>`,
      `<div class="ac-comb-line">Speed cap: ${tree.speed_cap_ops_per_sec ?? 8192} ops/s</div>`,
      `<div class="ac-comb-line muted">Condense on truth: ${tree.condense_on_truth !== false ? "yes" : "no"}</div>`,
      '<button type="button" class="ac-comb-run" id="ac-comb-cycle">Run cycle</button>',
    ].join("");
    el.querySelector("#ac-comb-cycle")?.addEventListener("click", async () => {
      const prof = global.AmmoCodeEditor?.state?.settings?.profile || "belt_2_0";
      await runCycle(prof);
      renderPanel(el);
      global.AmmoCodeEditor?.toast?.("Combinatorics cycle OK", true);
    });
  }

  global.AmmoCodeCombinatorics = {
    loadPatterns,
    loadDoctrine,
    scan,
    scanLocal,
    runCycle,
    renderPanel,
    lastCycle: () => lastCycle,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);