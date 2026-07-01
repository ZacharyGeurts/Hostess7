/**
 * AmmoCode AI Primer — copy-paste tutorial for AI assistants per compiler/language.
 */
(function (global) {
  "use strict";

  const MARKER_START = "AMMOCODE AI PRIMER";
  const MARKER_END = "END PRIMER";

  let registry = null;
  const cache = new Map();

  async function loadRegistry() {
    if (registry) return registry;
    try {
      const r = await fetch("data/ai-primers.json", { cache: "no-store" });
      if (r.ok) registry = await r.json();
    } catch (_) {}
    registry = registry || { primers: {}, facts: {}, stack: {} };
    return registry;
  }

  function displayName(lang) {
    const names = registry?.display_names || {};
    return names[lang] || lang.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function fence(lang) {
    const map = {
      cxx: "cpp", csharp: "csharp", shell: "bash", visual_basic: "vb", verilog: "verilog",
      wat: "wat", dockerfile: "dockerfile", makefile: "makefile",
    };
    return map[lang] || lang;
  }

  function stackBlock(profile) {
    const s = registry?.stack || {};
    return [
      "## AmmoCode / g16 stack (truthful)",
      `- Editor: AmmoCode 2027 — sovereign compiler GUI, zero telemetry`,
      `- Compiler: g16 universal (Grok16) · profile **${profile}**`,
      `- Security: hardened rewrite — no eval, no shell injection, transparent vuln scan`,
      `- Field doctrine: max_field_depth 0 — no nested fields; flat universal_2d blanket`,
      `- Combinatorics: background only — you write code, not operator crank trees`,
      `- Collab: invite-only; voice + cursor personas optional`,
      s.motto ? `- Motto: ${s.motto}` : "",
    ].filter(Boolean).join("\n");
  }

  function outputContract(lang, fenceLang) {
    return [
      "## Output contract (read this)",
      "You are a **coding assistant** for this AmmoCode tab. Follow strictly:",
      "1. **Most of your reply must be code** inside a fenced code block.",
      `2. Open with \`\`\`${fenceLang} and close with \`\`\` — one primary block per answer unless asked otherwise.`,
      "3. Prefer **complete, runnable snippets** — includes imports/headers, main entry when relevant.",
      "4. Match the language and profile above — do not switch languages unless asked.",
      "5. **Never** use banned patterns: eval, exec, shell=True, gets(), strcpy(), innerHTML=, pickle.loads on untrusted data.",
      "6. Short prose is OK **before** the code block (1–3 sentences). Put implementation in the block.",
      "7. When extending existing code, show the **full function or file section**, not just a diff fragment.",
      "",
      "Bad: long explanation, no code block.",
      "Good: one sentence intent, then a full ``` block.",
    ].join("\n");
  }

  function generatePrimer(lang, profile) {
    const key = `${lang}:${profile}`;
    if (cache.has(key)) return cache.get(key);

    const facts = (registry?.facts || {})[lang] || (registry?.facts || {})._default || {};
    const fenceLang = fence(lang);
    const name = displayName(lang);
    const starter = (registry?.starters || {})[lang] || facts.starter || `// ${name} — starter for g16 ${profile}\n`;

    const body = [
      `You are assisting on **${name}** in the AmmoCode 2027 / g16 stack.`,
      "",
      stackBlock(profile),
      "",
      `## Language: ${name}`,
      facts.paradigm ? `**Paradigm:** ${facts.paradigm}` : "",
      facts.typing ? `**Typing:** ${facts.typing}` : "",
      facts.compiler ? `**Tooling:** ${facts.compiler}` : "",
      facts.version_note ? `**Version note:** ${facts.version_note}` : "",
      "",
      facts.summary || `Write idiomatic ${name} suitable for g16 profile ${profile}.`,
      "",
      facts.rules ? "### Rules for this language\n" + facts.rules : "",
      facts.avoid ? "### Do not\n" + facts.avoid : "",
      facts.patterns ? "### Prefer\n" + facts.patterns : "",
      "",
      outputContract(lang, fenceLang),
      "",
      "## Starter template (replace and expand)",
      "```" + fenceLang,
      starter.trimEnd(),
      "```",
      "",
      "## First request to try",
      `Ask the AI: "Write a minimal ${name} program for g16 ${profile} that compiles cleanly and follows AmmoCode security rules. Output code in a single fenced block."`,
    ].filter((line) => line !== undefined && line !== null).join("\n");

    const text = formatPrimer(lang, profile, body);
    cache.set(key, text);
    return text;
  }

  function formatPrimer(lang, profile, body) {
    const name = displayName(lang);
    const line = "═".repeat(62);
    return [
      line,
      `${MARKER_START} — ${name} · g16 ${profile}`,
      "Copy everything below into ChatGPT, Claude, Grok, or any AI — then ask for code.",
      line,
      "",
      body,
      "",
      "---",
      `${MARKER_END} — Tab: ${lang} · Profile: ${profile} · Paste AI replies back into AmmoCode.`,
      "",
    ].join("\n");
  }

  async function get(lang, profile) {
    await loadRegistry();
    const prof = profile || registry?.default_profile || "belt_2_0";
    const custom = (registry?.primers || {})[lang];
    if (custom) {
      const body = typeof custom === "string" ? custom : custom.body;
      if (body) return formatPrimer(lang, prof, body.trim());
    }
    return generatePrimer(lang, prof);
  }

  function isPrimerContent(text) {
    if (!text || typeof text !== "string") return false;
    return text.includes(MARKER_START) && text.includes(MARKER_END);
  }

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    }
  }

  global.AmmoCodePrimer = {
    loadRegistry,
    get,
    generatePrimer,
    isPrimerContent,
    copyToClipboard,
    MARKER_START,
    MARKER_END,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);