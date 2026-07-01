/**
 * Compile alerts — structured post-build layout; honest autocorrect only.
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderHumanExplanation(human) {
    if (!human || !human.entries || !human.entries.length) return "";
    let html = `<section class="ac-human-explanation" aria-label="Human Explanation">`;
    html += `<h4 class="ac-human-title">${esc(human.title || "Human Explanation")}`;
    if (human.count) html += ` <span class="ac-human-count">(${human.count})</span>`;
    html += `</h4>`;
    if (human.platform && human.platform !== "generic") {
      html += `<p class="ac-human-platform">Platform: ${esc(human.platform)} · Lang: ${esc(human.lang || "—")}</p>`;
    }
    html += `<ol class="ac-human-list">`;
    for (const e of human.entries) {
      html += `<li class="ac-human-entry">`;
      if (e.line) html += `<span class="ac-human-loc">L${esc(e.line)}</span> `;
      html += `<span class="ac-human-raw">${esc(e.message || "")}</span>`;
      if (e.explanation) {
        html += `<p class="ac-human-text">${esc(e.explanation)}</p>`;
      }
      if (e.hint) {
        html += `<p class="ac-human-hint"><strong>Hint:</strong> ${esc(e.hint)}</p>`;
      }
      html += `</li>`;
    }
    html += `</ol></section>`;
    return html;
  }

  function renderEmulatorSeries(emu) {
    if (!emu || !emu.series || !emu.series.length) return "";
    const ready = !!emu.all_series_ready;
    let html = `<section class="ac-emulator-series" aria-label="Emulator series">`;
    html += `<p class="ac-emu-summary ${ready ? "ready" : "pending"}">`;
    html += ready ? "Emulator/chip series ready" : "Some emulator series pending";
    if (emu.amiga_ready) html += ` · Amiga seeded`;
    html += `</p></section>`;
    return html;
  }

  function renderAlerts(alerts) {
    if (!alerts) return "";
    const cards = alerts.cards || [];
    const summary = alerts.summary || (alerts.ok ? "Compile OK" : "Compile failed");
    const ok = !!alerts.ok;
    const human = alerts.human_explanation || alerts.sections?.human_explanation;
    const emu = alerts.emulator_series || alerts.sections?.emulator_series;
    let html = `<div class="ac-alerts ${ok ? "ok" : "err"}">`;
    html += `<div class="ac-alerts-summary"><span class="ac-alerts-badge">${ok ? "OK" : "FAIL"}</span> ${esc(summary)}</div>`;
    if (!cards.length && !human) {
      html += `<p class="ac-alerts-empty">No diagnostics.</p>`;
    } else if (cards.length) {
      html += `<ul class="ac-alerts-list">`;
      for (const c of cards) {
        const kind = c.kind || "error";
        html += `<li class="ac-alert ac-alert-${esc(kind)}">`;
        if (c.line) html += `<span class="ac-alert-loc">L${esc(c.line)}</span>`;
        html += `<span class="ac-alert-kind">${esc(c.title || kind)}</span>`;
        html += `<span class="ac-alert-detail">${esc(c.detail || "")}</span>`;
        if (c.before && c.after && c.before !== c.after) {
          html += `<div class="ac-alert-diff"><del>${esc(c.before)}</del> → <ins>${esc(c.after)}</ins></div>`;
        }
        html += `</li>`;
      }
      html += `</ul>`;
    }
    html += renderHumanExplanation(human);
    html += renderEmulatorSeries(emu);
    html += `</div>`;
    return html;
  }

  function applyCorrectedContent(editor, result) {
    const corrected = result?.corrected_content || (result?.content_changed ? result?.content : null);
    if (!corrected || !editor) return false;
    editor.value = corrected;
    return true;
  }

  function showBuildResult(result, { outputEl, alertsEl, editor, onStatus } = {}) {
    const alerts = result?.alerts;
    if (alertsEl) {
      alertsEl.innerHTML = renderAlerts(alerts);
      alertsEl.classList.toggle("hidden", !alerts);
    }
    const applied = (result?.applied_fixes || []).length;
    if (outputEl) {
      const lines = [];
      if (result?.message) lines.push(result.message);
      if (applied) lines.push(`${applied} safe autocorrect(s) applied.`);
      if (result?.stderr_tail) lines.push(result.stderr_tail);
      if (result?.stderr) lines.push(result.stderr);
      if (result?.detail) lines.push(result.detail);
      outputEl.textContent = lines.filter(Boolean).join("\n") || JSON.stringify(result, null, 2);
      outputEl.classList.toggle("ok", !!result?.ok);
      outputEl.classList.toggle("err", !result?.ok);
    }
    if (applyCorrectedContent(editor, result) && typeof onStatus === "function") {
      onStatus("Editor updated from verified autocorrect.", true);
    }
    return result;
  }

  global.AmmoCodeCompileAlerts = {
    renderAlerts,
    showBuildResult,
    applyCorrectedContent,
  };
})(typeof window !== "undefined" ? window : globalThis);