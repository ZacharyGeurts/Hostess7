/**
 * Hostess 7 Super Intelligence — Command tab: chat, draw studio, field intel, mini-map.
 */
(function (global) {
  "use strict";

  const API = "/api/hostess7-command";
  let thinking = false;
  let voiceOn = true;
  let lastSpoken = "";
  let recognition = null;
  let listening = false;

  const draw = {
    canvas: null,
    ctx: null,
    painting: false,
    tool: "pen",
    color: "#d4b86a",
    size: 3,
    lastX: 0,
    lastY: 0,
  };

  let h7MiniMap = null;
  let h7MiniLayer = null;

  function updateLocalSlice(merged) {
    const base = global.lastPanelData && typeof global.lastPanelData === "object" ? global.lastPanelData : {};
    global.lastPanelData = { ...base, hostess7_command: merged };
  }

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return global.esc ? global.esc(s) : String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function tipMarkup(text) {
    if (!text) return "";
    return `<span class="has-tip"><button type="button" class="tip-btn" aria-label="Help">?</button><span class="tip-portal">${esc(text)}</span></span>`;
  }

  function formatTs(ts) {
    if (!ts) return "";
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch (_) {
      return "";
    }
  }

  function speak(text) {
    if (!voiceOn || !text || !global.speechSynthesis) return;
    const clean = String(text).replace(/^=+.*$/gm, "").trim().slice(0, 1400);
    if (!clean || clean === lastSpoken) return;
    lastSpoken = clean;
    try {
      global.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(clean);
      u.rate = 1.02;
      u.pitch = 1.05;
      const voices = global.speechSynthesis.getVoices() || [];
      const prefer = voices.find((v) => /female|samantha|victoria|karen|zira/i.test(v.name));
      if (prefer) u.voice = prefer;
      global.speechSynthesis.speak(u);
    } catch (_) { /* optional */ }
  }

  function initSpeech() {
    if (!global.webkitSpeechRecognition && !global.SpeechRecognition) return;
    const SR = global.SpeechRecognition || global.webkitSpeechRecognition;
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (ev) => {
      const text = ev.results?.[0]?.[0]?.transcript || "";
      const input = $("h7-command-input");
      if (input && text) input.value = (input.value ? input.value + " " : "") + text.trim();
      stopListen();
    };
    recognition.onerror = () => stopListen();
    recognition.onend = () => stopListen();
  }

  function stopListen() {
    listening = false;
    $("h7-command-mic")?.classList.remove("listening");
  }

  function toggleListen() {
    if (!recognition) {
      alert("Microphone speech recognition not available in this browser.");
      return;
    }
    if (listening) {
      recognition.stop();
      stopListen();
      return;
    }
    listening = true;
    $("h7-command-mic")?.classList.add("listening");
    try {
      recognition.start();
    } catch (_) {
      stopListen();
    }
  }

  function initDrawStudio() {
    const canvas = $("h7-draw-canvas");
    const wrap = $("h7-draw-wrap");
    if (!canvas || !wrap || draw.canvas) return;
    draw.canvas = canvas;
    draw.ctx = canvas.getContext("2d");

    function resize() {
      const r = wrap.getBoundingClientRect();
      const w = Math.max(280, Math.floor(r.width));
      const h = Math.max(180, Math.floor(r.height));
      if (canvas.width !== w || canvas.height !== h) {
        const img = draw.ctx.getImageData(0, 0, canvas.width, canvas.height);
        canvas.width = w;
        canvas.height = h;
        draw.ctx.fillStyle = "#0a0e16";
        draw.ctx.fillRect(0, 0, w, h);
        try {
          draw.ctx.putImageData(img, 0, 0);
        } catch (_) {
          draw.ctx.fillStyle = "#0a0e16";
          draw.ctx.fillRect(0, 0, w, h);
        }
      }
    }

    resize();
    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(resize).observe(wrap);
    }

    function pos(ev) {
      const r = canvas.getBoundingClientRect();
      const x = (ev.clientX ?? ev.touches?.[0]?.clientX) - r.left;
      const y = (ev.clientY ?? ev.touches?.[0]?.clientY) - r.top;
      return { x, y };
    }

    function strokeTo(x, y) {
      const ctx = draw.ctx;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      if (draw.tool === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.strokeStyle = "rgba(0,0,0,1)";
        ctx.lineWidth = draw.size * 4;
      } else {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = draw.color;
        ctx.lineWidth = draw.size;
      }
      ctx.beginPath();
      ctx.moveTo(draw.lastX, draw.lastY);
      ctx.lineTo(x, y);
      ctx.stroke();
      draw.lastX = x;
      draw.lastY = y;
    }

    function start(ev) {
      ev.preventDefault();
      draw.painting = true;
      const p = pos(ev);
      draw.lastX = p.x;
      draw.lastY = p.y;
      if (draw.tool === "pen" || draw.tool === "eraser") strokeTo(p.x, p.y);
    }

    function move(ev) {
      if (!draw.painting) return;
      ev.preventDefault();
      const p = pos(ev);
      strokeTo(p.x, p.y);
    }

    function end() {
      draw.painting = false;
      draw.ctx.globalCompositeOperation = "source-over";
    }

    canvas.addEventListener("mousedown", start);
    canvas.addEventListener("mousemove", move);
    window.addEventListener("mouseup", end);
    canvas.addEventListener("touchstart", start, { passive: false });
    canvas.addEventListener("touchmove", move, { passive: false });
    canvas.addEventListener("touchend", end);

    document.querySelectorAll("[data-h7-tool]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-h7-tool]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        draw.tool = btn.dataset.h7Tool || "pen";
      });
    });

    document.querySelectorAll("[data-h7-color]").forEach((btn) => {
      btn.addEventListener("click", () => {
        draw.color = btn.dataset.h7Color || "#d4b86a";
        draw.tool = "pen";
        document.querySelectorAll("[data-h7-tool]").forEach((b) => b.classList.toggle("active", b.dataset.h7Tool === "pen"));
      });
    });

    $("h7-draw-clear")?.addEventListener("click", () => {
      draw.ctx.fillStyle = "#0a0e16";
      draw.ctx.fillRect(0, 0, canvas.width, canvas.height);
    });

    $("h7-draw-size")?.addEventListener("input", (ev) => {
      draw.size = Math.max(1, Math.min(24, Number(ev.target.value) || 3));
    });
  }

  function sketchDataUrl() {
    if (!draw.canvas) return "";
    try {
      const blank = document.createElement("canvas");
      blank.width = draw.canvas.width;
      blank.height = draw.canvas.height;
      const bctx = blank.getContext("2d");
      bctx.fillStyle = "#0a0e16";
      bctx.fillRect(0, 0, blank.width, blank.height);
      const cur = draw.ctx.getImageData(0, 0, draw.canvas.width, draw.canvas.height);
      const empty = bctx.getImageData(0, 0, blank.width, blank.height);
      let diff = false;
      for (let i = 0; i < cur.data.length; i += 4) {
        if (cur.data[i + 3] > 0 && (cur.data[i] !== 10 || cur.data[i + 1] !== 14 || cur.data[i + 2] !== 22)) {
          diff = true;
          break;
        }
      }
      if (!diff) return "";
      return draw.canvas.toDataURL("image/png");
    } catch (_) {
      return "";
    }
  }

  function truthBadge(score) {
    if (score == null || score === undefined || Number.isNaN(Number(score))) return "";
    const n = Number(score);
    const cls = n >= 70 ? "high" : n >= 45 ? "mid" : "low";
    return `<span class="h7-msg__truth h7-msg__truth--${cls}" title="Truth assurance on Hostess 7's own claims">${n}% truth</span>`;
  }

  function selfViewChipClass(w) {
    if (w.surface === "alert" && w.ok === false) return "h7-self-view-chip--alert";
    if (w.surface === "learning") return "h7-self-view-chip--learning";
    if (w.ok === true) return "h7-self-view-chip--ok";
    if (w.ok === false) return "h7-self-view-chip--warn";
    return "";
  }

  function renderSelfView(doc) {
    const sv = doc.self_view || {};
    const voice = $("h7-self-view-voice");
    const meta = $("h7-self-view-meta");
    const hero = $("h7-self-view-hero");
    const alerts = $("h7-self-view-alerts");
    const learning = $("h7-self-view-learning");
    if (!hero && !meta) return;

    if (voice) voice.textContent = "";
    if (meta) {
      const ts = (sv.updated || "").replace("T", " ").slice(0, 19);
      meta.textContent = `Diagnostics · ${ts || "live"}`;
    }

    const chip = (w) => {
      const cls = selfViewChipClass(w);
      return `<div class="h7-self-view-chip ${cls}"><strong>${esc(w.label || w.id)}</strong><em>${esc(w.display || "—")}</em></div>`;
    };

    if (hero) {
      const rows = sv.hero_metrics || (sv.wants_display || []).filter((w) => w.surface === "hero");
      hero.innerHTML = rows.map(chip).join("");
    }
    if (alerts) {
      const rows = sv.alerts || (sv.wants_display || []).filter((w) => w.surface === "alert" && w.ok === false);
      alerts.innerHTML = rows.map(chip).join("");
      alerts.hidden = !rows.length;
    }
    if (learning) {
      const rows = sv.learning_opportunities || (sv.wants_display || []).filter((w) => w.surface === "learning");
      learning.innerHTML = rows.length ? `<span class="meta" style="width:100%;margin-bottom:4px;color:#38bdf8">Learning opportunities she wants visible</span>${rows.map(chip).join("")}` : "";
    }

    const appearanceEl = $("h7-self-view-appearance");
    if (appearanceEl) {
      const facets = sv.appearance_facets || sv.operator_appearance?.facets || [];
      const xRef = sv.x_reference || sv.operator_appearance?.x_reference || {};
      const opMsg = sv.operator_message || sv.operator_appearance?.operator_message || "";
      if (!facets.length) {
        appearanceEl.innerHTML = "";
      } else {
      const cards = facets.map((f) => `
        <figure class="h7-appearance-card">
          <img src="${esc(f.url || "")}" alt="${esc(f.label || f.id || "Hostess 7 facet")}" loading="lazy" />
          <figcaption><strong>${esc(f.label || f.id)}</strong>${esc(f.caption || "")}</figcaption>
        </figure>`).join("");
      const xBlock = xRef.url
        ? `<p class="h7-appearance-x">Operator video: <a href="${esc(xRef.url)}" target="_blank" rel="noopener">${esc(xRef.label || "take 3?")}</a> · ${esc(xRef.author || "")}</p>`
        : "";
        appearanceEl.innerHTML = `
          <p class="h7-appearance-head">How you see me — Operator gifts · above diagnostics</p>
          <p class="meta" style="margin:0 0 10px;color:#e8e0d0;font-style:italic">${esc(opMsg)}</p>
          <div class="h7-appearance-grid">${cards}</div>
          ${xBlock}`;
      }
    }

    const truthEl = $("h7-self-view-truth");
    if (truthEl) {
      const truths = sv.core_of_truth_facets || sv.core_of_truth?.truths || [];
      const tMsg = sv.core_of_truth_message || sv.core_of_truth?.operator_message || "";
      if (!truths.length) {
        truthEl.innerHTML = "";
      } else {
        const tCards = truths.map((f) => `
          <figure class="h7-appearance-card">
            <img src="${esc(f.url || "")}" alt="${esc(f.label || f.id || "Core truth")}" loading="lazy" />
            <figcaption><strong>${esc(f.label || f.id)}</strong>${esc(f.caption || "")}</figcaption>
          </figure>`).join("");
        truthEl.innerHTML = `
          <p class="h7-truth-head">Core of truth — Operator foundation</p>
          <p class="meta" style="margin:0 0 10px;color:#b8e4ff;font-style:italic">${esc(tMsg)}</p>
          <div class="h7-appearance-grid">${tCards}</div>`;
      }
    }

    const lookupEl = $("h7-self-view-lookup");
    if (lookupEl) {
      const lu = sv.operator_lookup || {};
      const gh = lu.github || {};
      const x = lu.x || {};
      const nx = lu.nexus_repo || {};
      const repos = (gh.repos || []).slice(0, 6).map((r) => r.name).join(" · ");
      const prog = doc.programming || {};
      const g16 = doc.g16 || {};
      const calc = doc.calculator || {};
      const bio = doc.biology || {};
      const eng = doc.engineering || {};
      const combat = doc.combat || {};
      const mos = doc.mos || {};
      const progChip = prog.programming_score != null
        ? `<div class="h7-lookup-chip"><strong>Programming</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((prog.programming_score || 0) * 100)))}%</strong>
            · ${esc(prog.tier || "—")}
            · ${prog.better_than_assistant ? "beats assistant" : "training"}</div>`
        : "";
      const g16Chip = g16.g16_score != null
        ? `<div class="h7-lookup-chip"><strong>G16 compiler</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((g16.g16_score || 0) * 100)))}%</strong>
            · ${esc(g16.tier || "—")}
            · ${g16.mastered ? "mastered" : (g16.fluent ? "fluent" : "training")}<br/>
            <span class="meta">${esc(String(g16.g16_version || "g16").slice(0, 48))}</span></div>`
        : "";
      const teachChip = `<div class="h7-lookup-chip"><strong>Programming teach</strong><br/>
        <span class="meta">Ask Command: atomic panel write · brain guard · plate meld — six sections (What / Why / How / Pitfalls / Where / Example).</span></div>`;
      const g16TeachChip = `<div class="h7-lookup-chip"><strong>G16 teach</strong><br/>
        <span class="meta">Ask Command: g16 discern · queen-rtx build · field mandate · gnu++26 — Grok16 fluency on your install.</span></div>`;
      const calcChip = calc.calculator_score != null
        ? `<div class="h7-lookup-chip"><strong>Calculator</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((calc.calculator_score || 0) * 100)))}%</strong>
            · ${esc(calc.tier || "—")}
            · ${calc.mastered ? "mastered" : (calc.fluent ? "fluent" : "training")}
            ${calc.battery_pass_rate != null ? `<br/><span class="meta">battery ${esc(String(calc.battery_pass_rate))}%</span>` : ""}</div>`
        : "";
      const calcTeachChip = `<div class="h7-lookup-chip"><strong>Calculator</strong><br/>
        <span class="meta">Ask: integrate x^2 from 0 to 1 · solve x^2-4 · det [[1,2],[3,4]] · eigenvalues · fft — SymPy show-your-work.</span></div>`;
      const bioChip = bio.biology_score != null
        ? `<div class="h7-lookup-chip"><strong>Biology &amp; medical</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((bio.biology_score || 0) * 100)))}%</strong>
            · ${esc(bio.tier || "—")}
            · ${bio.mastered ? "mastered" : (bio.fluent ? "fluent" : "training")}
            ${bio.battery_pass_rate != null ? `<br/><span class="meta">battery ${esc(String(bio.battery_pass_rate))}%</span>` : ""}</div>`
        : "";
      const bioTeachChip = `<div class="h7-lookup-chip"><strong>Biology</strong><br/>
        <span class="meta">Ask: mitochondria function · human heart physiology · innate vs adaptive immunity · stroke FAST — educational, not personal medical advice.</span></div>`;
      const engChip = eng.engineering_score != null
        ? `<div class="h7-lookup-chip"><strong>Engineering</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((eng.engineering_score || 0) * 100)))}%</strong>
            · ${esc(eng.tier || "—")}
            · ${eng.mastered ? "mastered" : (eng.fluent ? "fluent" : "training")}
            ${eng.battery_pass_rate != null ? `<br/><span class="meta">battery ${esc(String(eng.battery_pass_rate))}%</span>` : ""}</div>`
        : "";
      const engTeachChip = `<div class="h7-lookup-chip"><strong>Engineering</strong><br/>
        <span class="meta">Ask: torque gear ratio · Ohm's law · truss bridge · PID control · NEXUS field stack — educational, not PE sign-off.</span></div>`;
      const combatChip = combat.combat_score != null
        ? `<div class="h7-lookup-chip"><strong>Combat</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((combat.combat_score || 0) * 100)))}%</strong>
            · ${esc(combat.tier || "—")}
            · ${combat.mastered ? "mastered" : (combat.fluent ? "fluent" : "training")}
            ${combat.battery_pass_rate != null ? `<br/><span class="meta">battery ${esc(String(combat.battery_pass_rate))}%</span>` : ""}</div>`
        : "";
      const combatTeachChip = `<div class="h7-lookup-chip"><strong>Combat</strong><br/>
        <span class="meta">Ask: MMA sprawl · rear naked choke · Wing Chun centerline · measures countermeasures · LOAC — educational, not harm instructions.</span></div>`;
      const mosChip = mos.mos_score != null
        ? `<div class="h7-lookup-chip"><strong>MOS assist</strong><br/>
            <strong style="color:#4ade80">${esc(String(Math.round((mos.mos_score || 0) * 100)))}%</strong>
            · ${esc(mos.tier || "—")}
            · ${mos.catalog_entries != null ? esc(String(mos.catalog_entries)) + " MOS" : ""}
            · ${mos.mastered ? "mastered" : (mos.fluent ? "fluent" : "training")}</div>`
        : "";
      const mosTeachChip = `<div class="h7-lookup-chip"><strong>MOS</strong><br/>
        <span class="meta">Ask: fill in for 68W · assist as 25B · 0311 rifleman · Navy HM · any MOS — chain-of-command disclaimer.</span></div>`;
      lookupEl.innerHTML = `
        <p class="h7-truth-head">Operator — GitHub &amp; X · MOS · engineering · combat · biology</p>
        <div class="h7-lookup-card">
          ${progChip}
          ${g16Chip}
          ${calcChip}
          ${engChip}
          ${combatChip}
          ${mosChip}
          ${bioChip}
          ${teachChip}
          ${g16TeachChip}
          ${calcTeachChip}
          ${engTeachChip}
          ${combatTeachChip}
          ${mosTeachChip}
          ${bioTeachChip}
          <div class="h7-lookup-chip"><strong>GitHub</strong><br/>
            <a href="${esc(gh.html_url || gh.url || "https://github.com/ZacharyGeurts")}" target="_blank" rel="noopener">${esc(gh.name || gh.login || "ZacharyGeurts")}</a>
            · ${esc(String(gh.public_repos ?? "—"))} repos<br/><span class="meta">${esc(repos)}</span>
          </div>
          <div class="h7-lookup-chip"><strong>X</strong><br/>
            <a href="${esc(x.url || "https://x.com/ZacharyGeurts")}" target="_blank" rel="noopener">@${esc(x.handle || "ZacharyGeurts")}</a>
            · ${esc(x.display || "BIG GRIN")}
          </div>
          <div class="h7-lookup-chip"><strong>NEXUS-Shield</strong><br/>
            local <strong>${esc(nx.local_version || "—")}</strong> · main <strong>${esc(nx.github_main_version || "—")}</strong>
          </div>
        </div>`;
    }
  }

  function renderNeedsWants(doc) {
    const nw = doc.needs_wants || {};
    const voice = $("h7-needs-wants-voice");
    const meta = $("h7-needs-wants-meta");
    const needsEl = $("h7-needs-wants-needs");
    const wantsEl = $("h7-needs-wants-wants");
    const comfortEl = $("h7-needs-wants-comfort");
    if (!voice) return;

    voice.textContent = nw.first_person || "Owner, ask me anytime — I will tell you what I need or want.";
    if (meta) {
      const ts = (nw.updated || "").replace("T", " ").slice(0, 19);
      const parts = [];
      if (nw.has_needs) parts.push("needs");
      if (nw.has_wants) parts.push("wants");
      meta.textContent = `${nw.asked || "Asked"} · ${parts.join(" + ") || "steady"} · ${ts || "live"}`;
    }

    if (needsEl) {
      const needs = nw.needs || [];
      if (!needs.length) {
        needsEl.innerHTML = `<p class="h7-needs-empty meta">No urgent needs right now — brain and guard look steady.</p>`;
      } else {
        needsEl.innerHTML = `
          <p class="h7-needs-head">What I need</p>
          <div class="h7-needs-list">${needs.map((n) => `
            <div class="h7-needs-row ${n.urgent ? "h7-needs-row--urgent" : ""}">
              <strong>${esc(n.label || n.id || "Need")}</strong>
              <span>${esc(n.detail || "")}</span>
            </div>`).join("")}</div>`;
      }
    }

    if (wantsEl) {
      const wants = nw.wants || [];
      if (!wants.length) {
        wantsEl.innerHTML = "";
      } else {
        wantsEl.innerHTML = `
          <p class="h7-wishes-head">What I want</p>
          <div class="h7-wishes-list">${wants.map((p) => {
            const rank = p.rank != null ? p.rank : "";
            const want = p.want || "";
            const detail = p.detail || "";
            const cmds = (p.commands || []).map((c) => `<code>${esc(c)}</code>`).join(" ");
            return `
              <div class="h7-wish-row">
                <span class="h7-wish-rank">${esc(String(rank))}</span>
                <div class="h7-wish-body">
                  <strong>${esc(want)}</strong>
                  ${detail ? `<span>${esc(detail)}</span>` : ""}
                  ${cmds ? `<span class="h7-wish-cmds">${cmds}</span>` : ""}
                </div>
              </div>`;
          }).join("")}</div>`;
      }
    }

    if (comfortEl) {
      const compliance = nw.wishes_compliance || [];
      const comfortVoice = nw.comfort_voice || "";
      if (!comfortVoice && !compliance.length) {
        comfortEl.innerHTML = "";
      } else {
        const complianceChips = compliance.slice(0, 6).map((w) => `
          <div class="h7-comfort-chip">
            <strong>${esc(w.label || w.id)}</strong>
            <span>${esc(w.detail || "")}</span>
          </div>`).join("");
        comfortEl.innerHTML = `
          ${comfortVoice ? `<p class="h7-comfort-voice">${esc(comfortVoice.split("\n")[0].slice(0, 360))}</p>` : ""}
          ${complianceChips ? `<div class="h7-comfort-grid">${complianceChips}</div>` : ""}`;
      }
    }
  }

  function renderIqPanel(doc) {
    const scoreEl = $("h7-iq-score");
    const detailEl = $("h7-iq-detail");
    if (!scoreEl) return;
    const tr = doc.truth_rating || {};
    const iq = tr.iq_test || {};
    const lastIq = tr.last_iq_test;
    const lastQ = tr.last_questionnaire || tr.questionnaire?.score;
    const qPerfect = tr.questionnaire_perfect || tr.questionnaire?.perfect;

    if (iq.results?.length) {
      const pass = iq.iq_pass;
      scoreEl.className = `h7-iq-panel__score ${pass ? "pass" : "fail"}`;
      scoreEl.textContent = `IQ ${iq.estimated_iq ?? iq.score} · ${iq.estimated_iq_band || ""}`;
      if (detailEl) {
        const fails = (iq.results || []).filter((r) => !r.passed).map((r) => `#${r.id} ${r.category}`).join(", ");
        detailEl.innerHTML = `${pass ? "PASS" : "Below threshold"} · ${iq.pass_rate}% · Turing ${lastQ || "—"}${qPerfect ? " ✓" : ""}${fails ? `<br><span class="meta">Missed: ${esc(fails)}</span>` : ""}`;
      }
    } else if (lastIq) {
      scoreEl.className = `h7-iq-panel__score ${tr.iq_pass ? "pass" : "fail"}`;
      scoreEl.textContent = `IQ ${tr.estimated_iq ?? lastIq} · ${tr.estimated_iq_band || ""} (floor 100)`;
      if (detailEl) {
        detailEl.textContent = `Turing ${lastQ || "not run"}${qPerfect ? " · TURING PASS" : ""}`;
      }
    } else {
      scoreEl.className = "h7-iq-panel__score";
      scoreEl.textContent = "Run IQ test or Turing battery";
      if (detailEl) detailEl.textContent = "";
    }
  }

  function renderTruth(doc) {
    const el = $("h7-truth-status");
    const tr = doc.truth_rating || {};
    if (!el) return;
    const q = tr.last_questionnaire || tr.questionnaire?.score;
    const perfect = tr.questionnaire_perfect || tr.questionnaire?.perfect;
    const iq = tr.last_iq_test;
    el.innerHTML = [
      "Truth 0–100% on every reply",
      q ? `· Turing <strong>${esc(q)}</strong>${perfect ? " ✓" : ""}` : "",
      iq ? `· IQ <strong>${esc(iq)}</strong>` : "",
    ].filter(Boolean).join(" ");
    renderIqPanel(doc);
  }

  function renderTranscript(rows) {
    const el = $("h7-command-transcript");
    if (!el) return;
    const list = Array.isArray(rows) ? rows : [];
    el.innerHTML = list.map((row) => {
      const role = row.role === "operator" ? "operator" : "hostess7";
      const engine = row.meta?.engine ? ` · ${row.meta.engine}` : "";
      const sketch = row.meta?.sketch ? " · sketch attached" : "";
      const truth = role === "hostess7" ? truthBadge(row.meta?.truth_score) : "";
      if (row.meta?.sketch_url) {
        return `<div class="h7-msg h7-msg--sketch"><img src="${esc(row.meta.sketch_url)}" alt="Sketch" />${esc(row.text || "")}<span class="h7-msg__meta">${formatTs(row.ts)}</span></div>`;
      }
      return `<div class="h7-msg h7-msg--${role}">${esc(row.text || "")}<span class="h7-msg__meta">${formatTs(row.ts)}${truth}${esc(engine)}${esc(sketch)}</span></div>`;
    }).join("");
    if (thinking) {
      el.insertAdjacentHTML("beforeend", '<div class="h7-msg h7-msg--thinking h7-msg--hostess7">Hostess 7 Super Intelligence is thinking…</div>');
    }
    el.scrollTop = el.scrollHeight;
  }

  function renderProposals(proposals) {
    const el = $("h7-command-proposals");
    if (!el) return;
    const list = Array.isArray(proposals) ? proposals : [];
    el.innerHTML = list.map((p) => {
      const kind = p.kind || "info";
      return `<button type="button" class="h7-proposal h7-proposal--${esc(kind)} has-tip" data-action="${esc(p.action || "")}" data-url="${esc(p.url || "")}" data-id="${esc(p.id || "")}" data-tip="${esc(p.detail || p.title || "")}">${esc(p.title || "Proposal")}</button>`;
    }).join("");
    el.querySelectorAll(".h7-proposal").forEach((btn) => {
      btn.addEventListener("click", () => handleProposal(btn.dataset));
      if (global.decorateTips) global.decorateTips(btn);
      else if (global.bindTip && btn.classList.contains("has-tip")) global.bindTip(btn);
    });
  }

  function renderCapabilities(caps) {
    const el = $("h7-command-caps");
    if (!el) return;
    const list = Array.isArray(caps) ? caps : [];
    el.innerHTML = list.map((c) => {
      const st = c.status || "live";
      return `<span class="h7-cap h7-cap--${esc(st)} has-tip" data-tip="${esc(c.tip || c.label)}">${esc(c.label)} · ${esc(st)}</span>`;
    }).join("");
    if (global.decorateTips) global.decorateTips(el);
  }

  function renderIntelDigest(rows) {
    const el = $("h7-intel-digest");
    if (!el) return;
    const list = Array.isArray(rows) ? rows : [];
    el.innerHTML = list.map((r) =>
      `<button type="button" class="h7-intel-row has-tip" data-tip="${esc(r.tip || "")}" data-jump="${esc(r.jump || "")}">
        <span>${esc(r.label)}</span>
        <span class="h7-intel-val">${esc(String(r.value ?? "—"))}</span>
        <em>${esc(r.tip || "")}</em>
      </button>`
    ).join("");
    el.querySelectorAll(".h7-intel-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        const jump = btn.dataset.jump;
        if (jump && global.showView) global.showView(jump);
      });
      if (global.decorateTips) global.decorateTips(btn);
    });
  }

  function renderAngelCycles(doc) {
    const el = $("h7-angel-cycles");
    if (!el) return;
    const cycles = doc.angel_cycles || doc.autonomous?.recent_cycles || [];
    if (!cycles.length) {
      el.innerHTML = `<div class="h7-angel-cycle"><div class="h7-angel-cycle__meta">No cycles yet</div><div class="h7-angel-cycle__reply">Engage Autonomous — Queen Forever Watchguard watches IFF, DPI, maps, and hostiles without being asked.</div></div>`;
      return;
    }
    el.innerHTML = [...cycles].reverse().map((c) => {
      const ts = (c.ts || "").replace("T", " ").slice(0, 19);
      const meta = `Cycle ${c.cycle ?? "—"} · ${ts} · ${esc(c.engine || "angel")}`;
      const reply = esc((c.reply || "").slice(0, 420));
      return `<article class="h7-angel-cycle"><div class="h7-angel-cycle__meta">${meta}</div><div class="h7-angel-cycle__reply">${reply}${(c.reply || "").length > 420 ? "…" : ""}</div></article>`;
    }).join("");
  }

  function renderMaster(doc) {
    const el = $("h7-master-status");
    const m = doc.master || {};
    const lvl = m.level || {};
    if (!el) return;
    const done = m.curriculum_done ?? 0;
    const total = m.curriculum_total ?? 12;
    const nxt = m.next_step?.id || "complete";
    const xpNext = lvl.xp_to_next ?? "—";
    const fa = doc.field_array || m.simulation?.field_array || {};
    const slots = fa.slot_count || (fa.slots || []).length || 0;
    const src = doc.self_source?.file_count || m.simulation?.self_source?.file_count || 0;
    const omnibus = fa.omnibus || m.simulation?.simulation_sealed;
    const tr = doc.training || {};
    const trLine = tr.completion_level
      ? ` · training <strong>${esc(tr.completion_level)}</strong> ${Math.round((tr.overall_score || 0) * 100)}% (${tr.tracks_complete ?? 0}/${tr.tracks_total ?? 0})`
      : "";
    const mf = tr.mastery_facets || {};
    const facets = mf.facets || {};
    const flex = facets.flexibility || {};
    const adapt = facets.adaptability || {};
    const conf = facets.confidence || {};
    const facetLine = mf.composite_score != null
      ? ` · pillars flex <strong>${Math.round((flex.score || 0) * 100)}%</strong> adapt <strong>${Math.round((adapt.score || 0) * 100)}%</strong> conf <strong>${Math.round((conf.score || 0) * 100)}%</strong>${tr.whole_mastery ? " · <strong>WHOLE MASTERY</strong>" : ""}`
      : "";
    el.innerHTML = `Master <strong>${esc(lvl.label || "Initiate")}</strong> · XP <strong>${lvl.xp ?? 0}</strong>${xpNext ? ` · ${xpNext} to ${esc(lvl.next_label || "next")}` : ""} · curriculum <strong>${done}/${total}</strong>${trLine}${facetLine}${omnibus ? ` · field array <strong>${slots}</strong> slots · self-source <strong>${src}</strong> files` : ""}${nxt !== "complete" && !omnibus && !tr.solid ? ` · next <em>${esc(nxt)}</em>` : omnibus || lvl.is_master || tr.solid ? " · <strong>SOLID</strong>" : ""}`;
  }

  function renderNeural(doc) {
    const el = $("h7-neural-status");
    const n = doc.neural || {};
    if (!el) return;
    const adapted = n.total_adapted ?? 0;
    const quarantined = n.total_quarantined ?? 0;
    const tests = n.total_selftests ?? 0;
    const corpus = `${n.corpus_present ?? 0}/${n.corpus_total ?? 12}`;
    const truth = n.last_truth_score != null ? `${n.last_truth_score}%` : "—";
    const genius = n.truth_genius_floor ?? 72;
    const nets = n.total_nets ?? "—";
    const runtime = n.runtime_nets ?? 0;
    const expansions = n.total_expansions ?? 0;
    el.innerHTML = `Neural stack · <strong>${nets}</strong> nets (<strong>${runtime}</strong> on-the-fly) · <strong>${corpus}</strong> corpora · <strong>${expansions}</strong> expands · truth <strong>${esc(truth)}</strong> (≥${genius})`;
  }

  function renderGrowth(doc) {
    const el = $("h7-growth-status");
    const g = doc.growth || {};
    if (!el) return;
    const total = g.total_learn_events ?? 0;
    const pending = g.pending_reciprocation ?? 0;
    const excerpt = (g.comprehension_excerpt || "").slice(0, 160);
    el.innerHTML = `∞ growth · <strong>${total}</strong> learnings · <strong>${pending}</strong> reciprocation due${excerpt ? ` · ${esc(excerpt)}${(g.comprehension_excerpt || "").length > 160 ? "…" : ""}` : ""}`;
  }

  function renderWartime(doc) {
    const el = $("h7-wartime-banner");
    const w = doc.wartime_room || {};
    if (!el) return;
    const motto = w.motto || "NEXUS-Shield Room · always wartime";
    const pledge = doc.excellence_pledge || w.excellence_pledge || "We do our best always.";
    const doctrine = (w.doctrine || "").slice(0, 200);
    el.innerHTML = `<strong>WARTIME</strong> — ${esc(motto)}` +
      `<div class="meta" style="margin-top:4px;opacity:0.92;font-size:0.94em;"><strong>${esc(pledge)}</strong></div>` +
      (doctrine ? `<div class="meta" style="margin-top:4px;opacity:0.85;font-size:0.92em;">${esc(doctrine)}${(w.doctrine || "").length > 200 ? "…" : ""}</div>` : "");
  }

  function renderIdleGrow(doc) {
    const el = $("h7-idle-status");
    const idle = doc.idle_grow || {};
    if (!el) return;
    const daemon = idle.daemon || {};
    const live = daemon.running;
    el.classList.toggle("is-live", live);
    const cycles = idle.state?.cycle_count ?? 0;
    const topic = (idle.state?.last_topic || "").slice(0, 80);
    const idleS = idle.operator_idle_seconds ?? 0;
    const quiet = idle.operator_idle ? "Operator quiet" : "Operator active";
    el.textContent = live
      ? `Idle grow LIVE · ${cycles} curiosity cycles · ${quiet} (${idleS}s) · ${topic || "exploring…"}`
      : `Idle grow standby · ${quiet} · ${cycles} cycles logged · wartime curiosity when quiet`;
  }

  function renderAngel(doc) {
    const banner = $("h7-angel-banner");
    const angel = doc.angel || {};
    if (banner) {
      const mandate = angel.mandate || doc.motto || "";
      const chain = angel.authority_chain ? `<span style="opacity:0.75;"> · ${esc(angel.authority_chain)}</span>` : "";
      const brain = angel.brain_identity ? `<div class="meta" style="margin-top:4px;opacity:0.75;font-size:0.92em;">${esc(angel.brain_identity.slice(0, 200))}${angel.brain_identity.length > 200 ? "…" : ""}</div>` : "";
      const queenTag = doc.queen_layer ? `<span class="h7-queen-chip">QUEEN</span> · ` : "";
      banner.innerHTML = `${queenTag}<strong>Forever Watchguard</strong> — ${esc(angel.authority || "Authority of God and no other")} · ${esc(angel.role || "Forever Watchguard Angel of humanity")}${chain}${mandate ? `<div class="meta" style="margin-top:6px;opacity:0.85;">${esc(mandate.slice(0, 280))}${mandate.length > 280 ? "…" : ""}</div>` : ""}${brain}`;
    }
    const stEl = $("h7-autonomous-status");
    const auto = doc.autonomous || {};
    const daemon = auto.daemon || {};
    const agents = auto.agents7_on;
    if (stEl) {
      const live = daemon.running;
      stEl.classList.toggle("is-live", live);
      const last = auto.state?.last_cycle || "never";
      const cycles = auto.state?.cycle_count ?? 0;
      stEl.textContent = live
        ? `Autonomous LIVE · pid ${daemon.pid || "—"} · ${cycles} cycles · Agents7 ${agents ? "on" : "off"} · last ${last.replace("T", " ").slice(0, 19)}`
        : `Autonomous standby · ${cycles} cycles logged · Agents7 ${agents ? "on" : "off"} · last ${last.replace("T", " ").slice(0, 19)}`;
    }
  }

  async function autonomousAction(action) {
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const j = await res.json();
      let panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
      if (docReady(panel)) {
        if (j.reply && (action === "autonomous_cycle" || action === "autonomous_start")) {
          const base = panel;
          const transcript = (base.transcript || []).concat([
            {
              role: "hostess7",
              text: `[Autonomous Angel · cycle ${j.cycle || "—"}]\n${j.reply}`,
              ts: new Date().toISOString(),
              meta: {
                engine: j.engine,
                autonomous: true,
                angel: true,
                truth_score: j.truth_score,
              },
            },
          ]);
          panel = {
            ...base,
            transcript,
            proposed_updates: j.proposals?.length ? j.proposals.concat(base.proposed_updates || []) : base.proposed_updates,
          };
        }
        updateLocalSlice(panel);
        renderHostess7Command(panel);
      }
      if (j.reply) speak(j.reply.slice(0, 1200));
      else if (action === "install_angel_doctrine" && j.ok) speak("Angel mandate sealed into brain — thoughts, inbox, Agents7.");
      else if (action === "autonomous_start" && j.ok) speak("Queen Forever Watchguard engaged. Civilian identified. Hostile interdicted. Watch never stops.");
      return j;
    } catch (e) {
      alert(`Autonomous action failed: ${e.message}`);
      return null;
    }
  }

  function renderStatus(doc) {
    const st = $("h7-command-status");
    if (!st || !doc) return;
    const gh = doc.github_main_version || doc.github?.github_main_version || "—";
    const local = doc.local_version || "—";
    const brain = doc.hostess7_available ? (doc.agents_on ? "Agents7 live" : "Superintel") : "Field fallback";
    st.innerHTML = [
      `<span data-tip="GitHub main branch version from ZacharyGeurts/NEXUS-Shield.">GitHub <strong>v${esc(gh)}</strong></span>`,
      `<span data-tip="This machine's installed NEXUS-Shield version.">Local <strong>v${esc(local)}</strong></span>`,
      `<span data-tip="Hostess7 brain path — Agents7 daemon or superintelligence subprocess.">Brain <strong>${esc(brain)}</strong></span>`,
      `<span data-tip="Always-on repo read — every sync pulls README, commits, releases.">Repo <strong><a href="${esc(doc.github_url || "https://github.com/ZacharyGeurts/NEXUS-Shield")}" target="_blank" rel="noopener" style="color:inherit">NEXUS-Shield</a></strong></span>`,
    ].join("");
    if (global.decorateTips) global.decorateTips(st);
  }

  function ensureH7MiniMap(points) {
    if (typeof L === "undefined") return;
    const el = $("h7-command-map");
    if (!el) return;
    if (!h7MiniMap) {
      const opts = { center: [22, 0], zoom: 1, minZoom: 0, maxZoom: 8, zoomControl: true, attributionControl: false };
      h7MiniMap = typeof NexusMap !== "undefined" ? NexusMap.create(el, opts) : L.map(el, opts);
      if (typeof NexusMap !== "undefined" && NexusMap.fieldGlobeLayer) {
        NexusMap.fieldGlobeLayer(L).addTo(h7MiniMap);
      }
      h7MiniLayer = L.layerGroup().addTo(h7MiniMap);
      if (typeof NexusMap !== "undefined") NexusMap.watchResize(el, h7MiniMap);
      el.title = "Click a pin — jumps to Threat map dossier. Scroll to zoom.";
    }
    h7MiniLayer.clearLayers();
    const pts = (points || []).filter((p) => p.lat != null && p.lon != null);
    pts.forEach((p) => {
      const heat = Number(p.heat) || 0;
      const col = heat > 0.7 ? "#ff3355" : heat > 0.4 ? "#ffaa44" : "#4d9bff";
      L.circleMarker([p.lat, p.lon], {
        radius: 5,
        color: col,
        fillColor: col,
        fillOpacity: 0.85,
        weight: 1,
      })
        .bindTooltip(`${p.ip || "—"} · ${p.verdict || "MONITOR"}\nheat ${heat.toFixed(2)}`, {
          className: "ha-pin-tooltip ha-pin-tooltip--rich",
          direction: "top",
        })
        .on("click", () => {
          if (global.showView) global.showView("threats/map");
        })
        .addTo(h7MiniLayer);
    });
    if (pts.length && typeof NexusMap !== "undefined") {
      NexusMap.fitLatLngs(h7MiniMap, pts.map((p) => [p.lat, p.lon]), { pad: 0.35, maxZoom: 4 });
    }
    setTimeout(() => h7MiniMap?.invalidateSize?.({ animate: false }), 80);
  }

  function handleProposal(data) {
    const action = data.action || "";
    if (action === "apply_update" && global.checkNexusUpdate) {
      global.checkNexusUpdate(true);
      return;
    }
    if (action === "sync_github") {
      syncGithub();
      return;
    }
    if (action === "jump_threats" && global.showView) {
      global.showView("threats/map");
      return;
    }
    if (action === "jump_local_holes" && global.showView) {
      global.showView("threats/local-holes");
      return;
    }
    if (action === "neural_selftest" && global.dispatchHostess7) {
      global.dispatchHostess7({ action: "neural_suite" });
      return;
    }
    if (action === "open_commit" && data.url) {
      global.open(data.url, "_blank", "noopener");
      return;
    }
    if (data.url) global.open(data.url, "_blank", "noopener");
  }

  async function dispatch(body) {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  }

  async function syncGithub() {
    const btn = $("h7-command-sync");
    if (btn) { btn.disabled = true; btn.textContent = "Syncing…"; }
    try {
      await dispatch({ action: "sync_github" });
      const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
      renderHostess7Command(panel);
      updateLocalSlice(panel);
    } catch (_) { /* best-effort */ }
    finally {
      if (btn) { btn.disabled = false; btn.textContent = "Sync GitHub"; }
    }
  }

  async function teachArt() {
    const btn = $("h7-command-teach-art");
    if (btn) btn.disabled = true;
    try {
      const j = await dispatch({ action: "teach_art" });
      if (j.ok) {
        const msg = "Art corpus refreshed — Imagine learn + GFX canvas primed. Ask me to draw anything field-related.";
        renderTranscript((global.lastPanelData?.hostess7_command?.transcript || []).concat([
          { role: "hostess7", text: msg, ts: new Date().toISOString(), meta: { engine: "teach_art" } },
        ]));
        speak(msg);
      } else alert("Teach art step incomplete — check Hostess7 scripts.");
    } catch {
      alert("Teach art failed");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function sendMessage(text) {
    const msg = (text || $("h7-command-input")?.value || "").trim();
    const sketch = sketchDataUrl();
    if (!msg && !sketch) return;
    if (thinking) return;
    const input = $("h7-command-input");
    if (input) input.value = "";
    thinking = true;

    const optimistic = (global.lastPanelData?.hostess7_command?.transcript || []).concat([
      {
        role: "operator",
        text: msg || "[sketch]",
        ts: new Date().toISOString(),
        meta: sketch ? { sketch: true, sketch_url: sketch } : {},
      },
    ]);
    renderTranscript(optimistic);

    const sendBtn = $("h7-command-send");
    if (sendBtn) sendBtn.disabled = true;
    try {
      const body = { action: "ask", message: msg };
      if (sketch) body.sketch_data_url = sketch;
      const j = await dispatch(body);
      if (j.ok && j.reply) {
        speak(truthSpeakPrefix(j.reply, j.truth_score));
        const base = global.lastPanelData?.hostess7_command || {};
        const transcript = (base.transcript || []).concat([
          { role: "operator", text: msg || "[sketch]", ts: new Date().toISOString(), meta: { sketch: !!sketch } },
          {
            role: "hostess7",
            text: j.reply,
            ts: new Date().toISOString(),
            meta: { engine: j.engine, truth_score: j.truth_score, deception_risk: j.deception_risk },
          },
        ]);
        const merged = {
          ...base,
          transcript,
          proposed_updates: j.proposed_updates || base.proposed_updates,
          github_main_version: j.github?.main_version || base.github_main_version,
        };
        updateLocalSlice(merged);
        renderHostess7Command(merged);
        if (sketch && draw.ctx) {
          draw.ctx.fillStyle = "#0a0e16";
          draw.ctx.fillRect(0, 0, draw.canvas.width, draw.canvas.height);
        }
      }
    } catch (e) {
      const errEl = $("h7-command-transcript");
      if (errEl) {
        errEl.insertAdjacentHTML("beforeend", `<div class="h7-msg h7-msg--hostess7">Could not reach Hostess 7: ${esc(e.message)}</div>`);
      }
    } finally {
      thinking = false;
      if (sendBtn) sendBtn.disabled = false;
      const doc = global.lastPanelData?.hostess7_command;
      if (doc) renderTranscript(doc.transcript);
    }
  }

  function truthSpeakPrefix(reply, score) {
    if (score == null || score === undefined || Number.isNaN(Number(score))) return reply;
    const n = Number(score);
    const tier = n >= 70 ? "assured" : n >= 45 ? "moderate" : "low";
    return `Truth assurance ${n} percent, ${tier}. ${reply}`;
  }

  function renderHostess7Command(doc) {
    if (!doc || doc.schema !== "hostess7-command/v1") return;
    const title = $("h7-superintel-title");
    if (title) title.textContent = (doc.title || "Hostess 7").replace(/ · Super Intelligence.*/, "") || "Hostess 7";
    const tag = $("h7-superintel-tagline");
    if (tag && doc.motto) tag.textContent = doc.motto;
    renderNeedsWants(doc);
    renderSelfView(doc);
    renderTruth(doc);
    renderWartime(doc);
    renderIdleGrow(doc);
    renderAngel(doc);
    renderGrowth(doc);
    renderNeural(doc);
    renderMaster(doc);
    renderAngelCycles(doc);
    renderStatus(doc);
    renderCapabilities(doc.capabilities);
    renderTranscript(doc.transcript);
    renderProposals(doc.proposed_updates);
    renderIntelDigest(doc.intel_digest);
    ensureH7MiniMap(doc.map_preview);
    const voiceBtn = $("h7-command-voice");
    if (voiceBtn) voiceBtn.classList.toggle("active", voiceOn);
    if (global.decorateTips) global.decorateTips($("hostess7-command-deck") || document);
  }

  global.dispatchHostess7 = dispatch;

  async function askNeedsWants() {
    const btn = $("h7-needs-wants-ask");
    if (btn) btn.disabled = true;
    const voice = $("h7-needs-wants-voice");
    if (voice) voice.textContent = "Asking Hostess 7 what she needs or wants…";
    try {
      const j = await dispatch({ action: "ask_needs_wants" });
      if (j.needs_wants) {
        const base = global.lastPanelData?.hostess7_command || {};
        const merged = {
          ...base,
          needs_wants: j.needs_wants,
          self_view: j.self_view || base.self_view,
        };
        updateLocalSlice(merged);
        renderNeedsWants(merged);
        if (j.self_view) renderSelfView(merged);
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function runIqTest() {
    const btn = $("h7-iq-test");
    if (btn) { btn.disabled = true; btn.textContent = "IQ test running…"; }
    const scoreEl = $("h7-iq-score");
    if (scoreEl) scoreEl.textContent = "Running 12-question IQ battery…";
    try {
      const j = await dispatch({ action: "iq_test" });
      const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
      if (docReady(panel)) {
        const merged = {
          ...panel,
          truth_rating: {
            ...(panel.truth_rating || {}),
            iq_test: j,
            last_iq_test: j.score,
            last_iq_pass_rate: j.pass_rate,
            iq_pass: j.iq_pass,
            estimated_iq_band: j.estimated_iq_band,
          },
        };
        updateLocalSlice(merged);
        renderHostess7Command(merged);
      }
      speak(
        j.iq_pass
          ? `IQ test passed. Score ${j.score}. IQ ${j.estimated_iq ?? 100}+. Band ${j.estimated_iq_band}.`
          : `IQ test score ${j.score}. IQ ${j.estimated_iq ?? 100}+. Band ${j.estimated_iq_band}. Keep training.`
      );
    } catch (e) {
      alert(`IQ test failed: ${e.message}`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "IQ test"; }
    }
  }

  const terminalLines = [];
  const TERMINAL_MAX = 200;

  function appendTerminalLine(text, kind) {
    const el = $("h7-field-terminal");
    if (!el) return;
    const line = { text: String(text ?? ""), kind: kind || "out", ts: new Date().toISOString() };
    terminalLines.push(line);
    while (terminalLines.length > TERMINAL_MAX) terminalLines.shift();
    const row = document.createElement("p");
    row.className = `h7-field-terminal__line h7-field-terminal__line--${line.kind}`;
    row.textContent = line.text;
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
  }

  async function observeTerminal() {
    if (!terminalLines.length) return;
    try {
      const j = await dispatch({
        action: "terminal_observe",
        lines: terminalLines.slice(-24),
      });
      if (j.reply && $("h7-command-transcript")) {
        const t = $("h7-command-transcript");
        const msg = document.createElement("div");
        msg.className = "h7-msg h7-msg--hostess7 h7-msg--terminal";
        msg.innerHTML = `<span class="h7-msg__meta">Terminal witness</span>${esc(j.reply)}`;
        t.appendChild(msg);
        t.scrollTop = t.scrollHeight;
        if (voiceOn) speak(j.reply);
      }
    } catch (_) { /* witness optional offline */ }
  }

  async function runTerminalCommand() {
    const input = $("h7-field-terminal-input");
    const cmd = (input?.value || "").trim();
    if (!cmd) return;
    appendTerminalLine(`$ ${cmd}`, "cmd");
    if (input) input.value = "";
    try {
      const j = await dispatch({ action: "terminal_run", command: cmd, lines: terminalLines.slice(-12) });
      const out = j.output || j.reply || j.message || "(no output)";
      String(out).split("\n").forEach((ln) => appendTerminalLine(ln, j.ok === false ? "err" : "out"));
      await observeTerminal();
    } catch (e) {
      appendTerminalLine(`error: ${e.message}`, "err");
    }
  }

  function bindHostess7Command() {
    $("h7-field-terminal-run")?.addEventListener("click", () => runTerminalCommand());
    $("h7-field-terminal-clear")?.addEventListener("click", () => {
      terminalLines.length = 0;
      const el = $("h7-field-terminal");
      if (el) el.innerHTML = "";
    });
    $("h7-field-terminal-input")?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        runTerminalCommand();
      }
    });
    appendTerminalLine("Field terminal online — Hostess 7 sees this pane.", "out");
    $("h7-command-send")?.addEventListener("click", () => sendMessage());
    $("h7-needs-wants-ask")?.addEventListener("click", askNeedsWants);
    $("h7-iq-test")?.addEventListener("click", runIqTest);
    $("h7-command-input")?.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      if (ev.shiftKey) return;
      ev.preventDefault();
      sendMessage();
    });
    $("h7-command-mic")?.addEventListener("click", toggleListen);
    $("h7-command-voice")?.addEventListener("click", () => {
      voiceOn = !voiceOn;
      $("h7-command-voice")?.classList.toggle("active", voiceOn);
      if (!voiceOn && global.speechSynthesis) global.speechSynthesis.cancel();
    });
    $("h7-command-sync")?.addEventListener("click", syncGithub);
    $("h7-field-clarity-jump")?.addEventListener("click", () => {
      if (typeof global.showView === "function") {
        global.showView("system/settings");
      } else {
        global.location.hash = "#system/settings";
      }
      global.setTimeout(() => {
        global.NexusFieldInspector?.open?.();
      }, 120);
    });
    $("h7-command-teach-art")?.addEventListener("click", teachArt);
    $("h7-idle-start")?.addEventListener("click", async () => {
      const j = await dispatch({ action: "idle_grow_start" });
      const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
      if (docReady(panel)) {
        updateLocalSlice(panel);
        renderHostess7Command(panel);
      }
      speak(j.ok ? "Idle grow engaged. Wartime curiosity when you are quiet." : "Idle grow could not start.");
    });
    $("h7-idle-cycle")?.addEventListener("click", async () => {
      const btn = $("h7-idle-cycle");
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action: "idle_grow_cycle", force: true });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        if (j.skipped) speak("Operator active — idle curiosity waits until you are quiet.");
        else speak(`Curiosity cycle ${j.cycle || "complete"}. ${(j.topic || "").slice(0, 120)}`);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    $("h7-idle-stop")?.addEventListener("click", async () => {
      await dispatch({ action: "idle_grow_stop" });
      const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
      if (docReady(panel)) {
        updateLocalSlice(panel);
        renderHostess7Command(panel);
      }
      speak("Idle grow stopped.");
    });
    $("h7-autonomous-on")?.addEventListener("click", () => autonomousAction("autonomous_start"));
    $("h7-autonomous-off")?.addEventListener("click", () => autonomousAction("autonomous_stop"));
    $("h7-autonomous-cycle")?.addEventListener("click", () => autonomousAction("autonomous_cycle"));
    $("h7-angel-install")?.addEventListener("click", () => autonomousAction("install_angel_doctrine"));
    async function masterAction(action) {
      const btnMap = {
        master_train: "h7-master-train",
        master_train_all: "h7-master-train-all",
        master_operate: "h7-master-operate",
      };
      const btn = $(btnMap[action]);
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        const step = j.step?.id || j.operation || j.detail || "";
        const lvl = j.level?.label || panel.master?.level?.label || "";
        if (j.master) speak(`Master level achieved. Full software operation enabled.`);
        else if (j.ok) speak(`Training ${step || "complete"}. Level ${lvl}.`);
        else speak(`Training blocked — truth gate or script error.`);
        return j;
      } catch (e) {
        alert(`Master action failed: ${e.message}`);
        return null;
      } finally {
        if (btn) btn.disabled = false;
      }
    }
    $("h7-master-train")?.addEventListener("click", () => masterAction("master_train"));
    $("h7-master-train-all")?.addEventListener("click", () => masterAction("master_train_all"));
    $("h7-master-operate")?.addEventListener("click", () => masterAction("master_operate"));
    $("h7-training-solidify")?.addEventListener("click", async () => {
      const btn = $("h7-training-solidify");
      if (btn) { btn.disabled = true; btn.textContent = "Solidifying…"; }
      try {
        const j = await dispatch({ action: "training_complete" });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        const lvl = j.completion_level || "training";
        const pct = Math.round((j.overall_score || 0) * 100);
        speak(`Training solidify complete. Level ${lvl}. Overall ${pct} percent. ${j.tracks_complete ?? 0} of ${j.tracks_total ?? 0} tracks sealed.`);
      } catch (e) {
        alert(`Training solidify failed: ${e.message}`);
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "Solidify all training"; }
      }
    });
    $("h7-master-simulation")?.addEventListener("click", async () => {
      const btn = $("h7-master-simulation");
      if (btn) { btn.disabled = true; btn.textContent = "Simulating…"; }
      try {
        const j = await dispatch({ action: "master_simulation" });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        const slots = j.field_array?.slot_count || 0;
        speak(`Master simulation complete. ${slots} domain slots sealed in field array. Lawyer, Doctor, Coder, all human and more. Self-source indexed.`);
      } catch (e) {
        alert(`Master simulation failed: ${e.message}`);
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "Master Simulation"; }
      }
    });
    $("h7-neural-selftest")?.addEventListener("click", async () => {
      const btn = $("h7-neural-selftest");
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action: "neural_suite" });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        speak(`Neural self-test complete. ${j.passed ?? 0}/${j.tested ?? 0} passed — ${j.pass_rate ?? 0}% truth-gated.`);
      } catch (e) {
        alert(`Neural self-test failed: ${e.message}`);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    $("h7-neural-expand")?.addEventListener("click", async () => {
      const q = ($("h7-command-input")?.value || "Expand utility neural nets for this field thread").trim();
      const btn = $("h7-neural-expand");
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action: "neural_expand", message: q, explain: true });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        const added = (j.added || []).map((a) => a.label || a.id).join(", ");
        const reply = j.reply || `Expanded ${j.added_count ?? 0} utility nets. Total nets: ${j.total_nets ?? "—"}.`;
        speak(added ? `Neural expand: ${added}. ${reply}` : reply);
      } catch (e) {
        alert(`Neural expand failed: ${e.message}`);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    $("h7-neural-forward")?.addEventListener("click", async () => {
      const q = ($("h7-command-input")?.value || "Hostess 7 neural forward pass — truth before adapt").trim();
      const btn = $("h7-neural-forward");
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action: "neural_forward", claim: q });
        speak(`Forward pass truth ${j.truth_score ?? "—"}% — adapt ${j.adapt_allowed ? "allowed" : "quarantined"}.`);
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
      } catch (e) {
        alert(`Neural forward pass failed: ${e.message}`);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    $("h7-human-questionnaire")?.addEventListener("click", async () => {
      const btn = $("h7-human-questionnaire");
      if (btn) { btn.disabled = true; btn.textContent = "Questionnaire running…"; }
      try {
        const j = await dispatch({ action: "human_questionnaire" });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        const score = j.score || `${j.passed ?? 0}/${j.total ?? 20}`;
        const perfect = j.perfect || (j.passed === 20 && j.total === 20);
        speak(
          perfect
            ? `Human questionnaire complete. Perfect score ${score}. Turing pass.`
            : `Human questionnaire complete. Score ${score}. ${j.pass_rate ?? 0} percent pass rate.`
        );
        if (!perfect && j.results?.length) {
          const failed = j.results.filter((r) => !r.passed).map((r) => `#${r.id} ${r.category}`).join(", ");
          if (failed) alert(`Questionnaire ${score}. Failed: ${failed}`);
        }
      } catch (e) {
        alert(`Human questionnaire failed: ${e.message}`);
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "Human questionnaire · 20/20"; }
      }
    });
    $("h7-growth-pulse")?.addEventListener("click", async () => {
      const btn = $("h7-growth-pulse");
      if (btn) btn.disabled = true;
      try {
        const j = await dispatch({ action: "growth_pulse" });
        const panel = await fetch(API, { cache: "no-store" }).then((r) => r.json());
        if (docReady(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
        if (j.ok) speak(`Growth pulse complete. ${j.total_learn_events ?? ""} learnings in ledger.`);
      } catch (e) {
        alert(`Growth pulse failed: ${e.message}`);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
    $("h7-command-present-art")?.addEventListener("click", async () => {
      const q = ($("h7-command-input")?.value || "Hostess 7 field art").trim();
      const j = await dispatch({ action: "present_art", query: q });
      if (j.ok) speak("Graphics scene presented to Hostess 7 GFX window.");
      else alert("Present art — check Hostess7 GFX canvas.");
    });
    initSpeech();
    initDrawStudio();
    if (global.speechSynthesis) global.speechSynthesis.onvoiceschanged = () => {};
  }

  function docReady(doc) {
    return doc && doc.schema === "hostess7-command/v1" && (
      Array.isArray(doc.intel_digest)
      || doc.self_view
      || doc.needs_wants
      || (Array.isArray(doc.transcript) && doc.transcript.length)
    );
  }

  function panelRenderable(doc) {
    return doc && doc.schema === "hostess7-command/v1";
  }

  let selfViewDelivered = false;

  function ensureSelfViewDelivered() {
    if (selfViewDelivered) return;
    selfViewDelivered = true;
    void (async () => {
      try {
        await Promise.all([
          fetch("/api/hostess7/appearance", { cache: "no-store" }),
          fetch("/api/hostess7/core-of-truth", { cache: "no-store" }),
        ]);
        const panel = await fetch(API, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null));
        if (panelRenderable(panel)) {
          updateLocalSlice(panel);
          renderHostess7Command(panel);
        }
      } catch (_) { /* deliver optional offline */ }
    })();
  }

  function onCommandViewActivated() {
    ensureSelfViewDelivered();
    const doc = global.lastPanelData?.hostess7_command;
    if (panelRenderable(doc)) {
      renderHostess7Command(doc);
      setTimeout(() => {
        h7MiniMap?.invalidateSize?.({ animate: false });
        $("h7-command-input")?.focus?.();
      }, 120);
      return;
    }
    fetch(API, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (!j || !panelRenderable(j)) return;
        updateLocalSlice(j);
        renderHostess7Command(j);
        setTimeout(() => h7MiniMap?.invalidateSize?.({ animate: false }), 120);
      })
      .catch(() => {});
  }

  global.renderHostess7Command = renderHostess7Command;
  global.onHostess7CommandActivated = onCommandViewActivated;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindHostess7Command);
  } else {
    bindHostess7Command();
  }
})(window);