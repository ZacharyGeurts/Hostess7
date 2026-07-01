/**
 * Hostess7 Pages live brain — queries corpus built from GitHub repo files.
 */
(function (global) {
  const GITHUB_RAW_DEFAULT =
    "https://raw.githubusercontent.com/ZacharyGeurts/Hostess7/main/";
  const MAX_QUERY = 2000;
  const SENSITIVE_RE =
    /ssh-rsa|BEGIN OPENSSH|pin_sha256|sudo\s+pw|password\s*[:=]|known_hosts/i;

  function sanitize(input) {
    let s = String(input ?? "")
      .replace(/<[^>]*>/g, "")
      .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "")
      .trim();
    if (s.length > MAX_QUERY) s = s.slice(0, MAX_QUERY);
    return s;
  }

  function tokenize(q) {
    return sanitize(q)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length > 2);
  }

  function scoreChunk(chunk, tokens) {
    const hay = `${chunk.title} ${chunk.text} ${(chunk.tags || []).join(" ")}`.toLowerCase();
    let score = 0;
    for (const t of tokens) {
      if (hay.includes(t)) score += t.length > 5 ? 3 : 1;
    }
    if (chunk.domain === "wants" && /want|priority|first/.test(tokens.join(" "))) score += 4;
    if (chunk.domain === "personality" && /who|hostess|you|grok/.test(tokens.join(" "))) score += 4;
    if (chunk.domain === "field_stack" && /kilroy|stack|boot|field/.test(tokens.join(" "))) score += 3;
    return score;
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error("fetch " + url + ": " + r.status);
    return r.json();
  }

  async function loadCorpus(manifest) {
    const local = manifest?.corpus || "/github-brain/corpus.json";
    let corpus = await fetchJson(local);
    const rawBase = manifest?.github_raw || GITHUB_RAW_DEFAULT;
    try {
      const liveFiles = manifest?.github_files || [];
      const extra = [];
      for (const f of liveFiles.slice(0, 12)) {
        try {
          const doc = await fetchJson(rawBase + f.path);
          const flat = JSON.stringify(doc).slice(0, 4000);
          if (!SENSITIVE_RE.test(flat)) {
            extra.push({
              id: "live-" + f.path.replace(/\W+/g, "-"),
              domain: f.domain || "github",
              title: f.path,
              text: flat,
              source: f.path,
              tags: ["github-live", f.domain],
            });
          }
        } catch (_e) {
          /* bundled corpus suffices */
        }
      }
      if (extra.length) {
        corpus = Object.assign({}, corpus, {
          chunks: (corpus.chunks || []).concat(extra),
          live_github_merged: extra.length,
        });
      }
    } catch (_e) {
      /* bundled only */
    }
    return corpus;
  }

  function composeAnswer(query, hits, manifest) {
    if (!hits.length) {
      return (
        "I'm Hostess 7 on GitHub Pages — I search doctrine and corpora from our repo files. " +
        "Try: wants, KILROY stack, truth floor, boot steps, or English training. " +
        "For full agents and /api/ask, run ./Hostess7.sh boot on your machine or Codespaces."
      );
    }
    const top = hits.slice(0, 4);
    const lines = ["You asked: " + query, ""];
    for (const h of top) {
      const excerpt = h.text.length > 520 ? h.text.slice(0, 520) + "…" : h.text;
      lines.push("• " + h.title, excerpt, "");
    }
    if (manifest?.loopback_upgrade) {
      lines.push("Sources: " + top.map((h) => h.source).join(", "));
      lines.push("Full brain: " + manifest.loopback_upgrade);
    }
    return lines.join("\n").trim();
  }

  async function askBrain(query, opts) {
    opts = opts || {};
    const manifest = opts.manifest;
    const corpus = opts.corpus;
    const loopbackUrl = opts.loopbackUrl;
    const q = sanitize(query);
    if (!q) return { ok: false, error: "empty query" };

    if (loopbackUrl) {
      try {
        const r = await fetch(loopbackUrl + "/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q }),
          mode: "cors",
        });
        if (r.ok) {
          const doc = await r.json();
          return {
            ok: true,
            text: doc.text || doc.answer || String(doc),
            route: "loopback",
            query: q,
          };
        }
      } catch (_e) {
        /* pages brain */
      }
    }

    const tokens = tokenize(q);
    const chunks = corpus?.chunks || [];
    const ranked = chunks
      .map((c) => Object.assign({}, c, { _score: scoreChunk(c, tokens) }))
      .filter((c) => c._score > 0)
      .sort((a, b) => b._score - a._score);

    const text = composeAnswer(q, ranked, manifest);
    if (SENSITIVE_RE.test(text)) {
      return {
        ok: true,
        text: "I withhold that on public Pages — information discipline. Ask on loopback after boot.",
        route: "pages-filtered",
        query: q,
      };
    }
    return {
      ok: true,
      text: text,
      route: "github-mirror",
      query: q,
      hits: ranked.slice(0, 4).map((h) => ({
        id: h.id,
        title: h.title,
        source: h.source,
        score: h._score,
      })),
      chunk_count: chunks.length,
    };
  }

  async function initPagesBrain() {
    const manifest = await fetchJson("/github-brain/manifest.json");
    const corpus = await loadCorpus(manifest);
    return { manifest: manifest, corpus: corpus };
  }

  global.Hostess7Brain = {
    sanitize: sanitize,
    initPagesBrain: initPagesBrain,
    askBrain: askBrain,
  };
})(typeof window !== "undefined" ? window : globalThis);