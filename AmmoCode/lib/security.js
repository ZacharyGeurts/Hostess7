/**
 * AmmoCode security — transparent vuln scan, red stop sign, use_instead tooltips.
 */
(function (global) {
  "use strict";

  let registry = null;

  async function loadRegistry() {
    if (registry) return registry;
    try {
      const r = await fetch("data/vulnerability-registry.json", { cache: "no-store" });
      if (r.ok) registry = await r.json();
    } catch (_) {}
    registry = registry || { patterns: [], policy: { transparent: true, no_black_box: true } };
    return registry;
  }

  function lineOf(text, index) {
    return text.slice(0, index).split("\n").length;
  }

  function scanLocal(content, lang) {
    const doc = registry || { patterns: [] };
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
        const line = lineOf(content, m.index);
        const sev = row.severity || "bad";
        findings.push({
          id: row.id,
          line,
          column: m.index - content.lastIndexOf("\n", m.index),
          match: m[0].slice(0, 120),
          severity: sev,
          bad: true,
          message: row.message || "Unsafe pattern",
          use_instead: row.use_instead || row.alternative,
          rewrite: row.rewrite,
        });
        if (sev === "critical" || sev === "bad" || sev === "block" || row.block) blocked = true;
      }
    }
    return { ok: !blocked, blocked, findings, finding_count: findings.length };
  }

  function mergeFindings(a, b) {
    const findings = [...(a?.findings || []), ...(b?.findings || [])];
    const blocked = !!(a?.blocked || b?.blocked);
    return { ok: !blocked, blocked, findings, finding_count: findings.length, hardened: true };
  }

  async function scan(content, lang, opts) {
    await loadRegistry();
    let comb = { findings: [], blocked: false };
    if (global.AmmoCodeCombinatorics?.scan) {
      comb = await global.AmmoCodeCombinatorics.scan(content, lang);
    }
    const api = global.AmmoCodeG16?.cfg?.()?.apiBase;
    if (api && !opts?.localOnly) {
      try {
        const r = await fetch(api, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "security_scan", content, language: lang }),
        });
        const j = await r.json();
        if (j.ok !== undefined || j.scan) return mergeFindings(j.scan || j, comb);
      } catch (_) {}
    }
    return mergeFindings(scanLocal(content, lang), comb);
  }

  function instaRewriteLocal(content, lang) {
    const doc = registry || { patterns: [] };
    let out = content;
    const applied = [];
    for (const row of doc.patterns || []) {
      if (!row.rewrite || !row.pattern) continue;
      const langs = row.langs;
      if (langs && lang && !langs.includes(lang) && !langs.includes("*")) continue;
      let rx;
      try {
        rx = new RegExp(row.pattern, "gim");
      } catch (_) {
        continue;
      }
      const next = out.replace(rx, row.rewrite);
      if (next !== out) {
        applied.push({ id: row.id, use_instead: row.use_instead });
        out = next;
      }
    }
    return { ok: true, changed: out !== content, content: out, applied };
  }

  async function instaRewrite(content, lang) {
    await loadRegistry();
    const api = global.AmmoCodeG16?.cfg?.()?.apiBase;
    if (api) {
      try {
        const r = await fetch(api, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "harden_rewrite", content, language: lang }),
        });
        const j = await r.json();
        if (j.rewrite) return j.rewrite;
        if (j.content) return j;
      } catch (_) {}
    }
    let out = instaRewriteLocal(content, lang);
    if (global.AmmoCodeCombinatorics?.scan) {
      const comb = await global.AmmoCodeCombinatorics.scan(out.content || content, lang);
      if (comb.blocked) return { ok: false, changed: false, content, blocked: true, findings: comb.findings };
    }
    return out;
  }

  function findingsByLine(findings) {
    const map = new Map();
    for (const f of findings || []) {
      const line = f.line || 1;
      if (!map.has(line)) map.set(line, []);
      map.get(line).push(f);
    }
    return map;
  }

  function renderGutterSecurity(gutterEl, text, findings) {
    if (!gutterEl) return;
    const n = Math.max(1, (text.match(/\n/g) || []).length + (text.length && !text.endsWith("\n") ? 1 : 0));
    const byLine = findingsByLine(findings);
    const lines = [];
    for (let i = 1; i <= n; i++) {
      const hits = byLine.get(i);
      if (hits && hits.length) {
        const tip = hits
          .map((h) => `Bad: ${h.message}${h.use_instead ? ` — use ${h.use_instead} instead` : ""}`)
          .join("\n");
        lines.push(`⛔`);
        gutterEl.querySelector(`[data-line="${i}"]`)?.setAttribute("title", tip);
      } else {
        lines.push(String(i));
      }
    }
    gutterEl.innerHTML = Array.from({ length: n }, (_, i) => {
      const line = i + 1;
      const hits = byLine.get(line);
      if (hits && hits.length) {
        const tip = hits
          .map((h) => `Bad: ${h.message}${h.use_instead ? ` — use ${h.use_instead} instead` : ""}`)
          .join("&#10;");
        return `<span class="ac-stop" data-line="${line}" title="${tip.replace(/"/g, "&quot;")}">⛔</span>`;
      }
      return `<span data-line="${line}">${line}</span>`;
    }).join("\n");
  }

  global.AmmoCodeSecurity = {
    loadRegistry,
    scan,
    scanLocal,
    instaRewrite,
    instaRewriteLocal,
    renderGutterSecurity,
    findingsByLine,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);