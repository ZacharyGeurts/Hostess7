/**
 * Monster — AmmoOS task & system monitor · chrome · green · pink graphs & intel.
 * @g16 5.1.0 · field-monster-monitor.py · hostess7-ocr-control
 */
(function (global) {
  "use strict";

  const API = "/api/field-monster-monitor";
  const OCR_API = "/api/hostess7/ocr/status";
  const HISTORY = 48;
  const TABS = [
    { id: "graphs", label: "Graphs" },
    { id: "vision", label: "Vision" },
    { id: "security", label: "Security" },
    { id: "processes", label: "Processes" },
    { id: "resources", label: "Resources" },
    { id: "services", label: "Services" },
    { id: "rescue", label: "Rescue" },
  ];

  const state = {
    tab: "graphs",
    processes: [],
    filter: "",
    timer: null,
    open: false,
    lastDoc: null,
    ocrDoc: null,
    cpuHist: [],
    memHist: [],
    loadHist: [],
    chamberHist: {},
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, opts) {
    const res = await fetch(API + path, Object.assign({ credentials: "same-origin", cache: "no-store" }, opts || {}));
    return res.json();
  }

  async function ocrStatus() {
    try {
      const res = await fetch(OCR_API, { credentials: "same-origin", cache: "no-store" });
      return res.json();
    } catch (_) {
      return { ok: false };
    }
  }

  function pushHist(arr, v) {
    arr.push(Number.isFinite(Number(v)) ? Number(v) : 0);
    while (arr.length > HISTORY) arr.shift();
  }

  function recordSample(doc) {
    pushHist(state.cpuHist, doc.cpu_pct);
    pushHist(state.memHist, doc.memory?.used_pct);
    pushHist(state.loadHist, (doc.loadavg || [])[0]);
    state.lastDoc = doc;
    const chambers = state.ocrDoc?.status?.chambers || state.ocrDoc?.chambers || {};
    Object.keys(chambers).forEach(function (cid) {
      const row = chambers[cid];
      const train = row?.train || row;
      const n = Number(train?.verified_count || row?.train?.verified_count || 0);
      if (!state.chamberHist[cid]) state.chamberHist[cid] = [];
      pushHist(state.chamberHist[cid], n);
    });
  }

  function statClass(pct) {
    const p = Number(pct) || 0;
    if (p >= 90) return "crit";
    if (p >= 70) return "warn";
    return "ok";
  }

  function ensureOverlay() {
    let el = document.getElementById("monster-overlay");
    if (el) return el;
    el = document.createElement("div");
    el.id = "monster-overlay";
    el.className = "monster-overlay";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Monster rescue panel");
    const nav = TABS.map(function (t) {
      return (
        '<button type="button" class="monster-tab' +
        (t.id === state.tab ? " active" : "") +
        '" data-tab="' +
        esc(t.id) +
        '">' +
        esc(t.label) +
        "</button>"
      );
    }).join("");
    el.innerHTML =
      '<div class="monster-panel">' +
      '<header class="monster-head">' +
      '<div><h2 class="monster-title">MONSTER</h2><div class="monster-sub">Task manager · graphs · vision · security hold</div></div>' +
      '<span class="monster-badge" id="monster-hold-badge">Security hold</span>' +
      '<button type="button" class="monster-close" id="monster-close">Close (Esc)</button>' +
      "</header>" +
      '<div class="monster-body">' +
      '<nav class="monster-nav" id="monster-nav">' +
      nav +
      "</nav>" +
      '<main class="monster-main" id="monster-main"></main>' +
      "</div></div>";
    document.body.appendChild(el);
    el.querySelector("#monster-close")?.addEventListener("click", close);
    el.addEventListener("click", function (ev) {
      if (ev.target === el) close();
    });
    el.querySelectorAll(".monster-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.tab = btn.dataset.tab || "graphs";
        el.querySelectorAll(".monster-tab").forEach(function (b) {
          b.classList.toggle("active", b.dataset.tab === state.tab);
        });
        render();
      });
    });
    if (!document.querySelector('link[href*="field-monster-monitor.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/assets/field-monster-monitor.css?v=2";
      document.head.appendChild(link);
    }
    return el;
  }

  function drawLineChart(canvas, series, maxY) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(184,194,212,0.08)";
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i += 1) {
      const y = (h * i) / 4;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    function plot(data, color, fill) {
      if (!data.length) return;
      const step = w / Math.max(1, HISTORY - 1);
      ctx.beginPath();
      data.forEach(function (v, i) {
        const x = i * step;
        const y = h - (Math.min(maxY, Math.max(0, v)) / maxY) * (h - 6) - 3;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      if (fill) {
        const lastX = (data.length - 1) * step;
        ctx.lineTo(lastX, h);
        ctx.lineTo(0, h);
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    plot(series.mem || [], "rgba(96,205,255,0.85)", "rgba(96,205,255,0.1)");
    plot(series.cpu || [], "#3dd68c", "rgba(61,214,140,0.12)");
    plot(series.load || [], "#e8a0c8", null);
  }

  function drawChamberBars(canvas, chambers) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const ids = Object.keys(chambers || {}).sort();
    if (!ids.length) return;
    const barW = Math.max(8, (w - 20) / ids.length - 4);
    let maxV = 1;
    ids.forEach(function (id) {
      const row = chambers[id];
      const train = row?.train || row;
      maxV = Math.max(maxV, Number(train?.verified_count || 0));
    });
    ids.forEach(function (id, i) {
      const row = chambers[id];
      const train = row?.train || row;
      const v = Number(train?.verified_count || 0);
      const bh = Math.max(4, (v / maxV) * (h - 28));
      const x = 10 + i * (barW + 4);
      const y = h - 18 - bh;
      const grad = ctx.createLinearGradient(x, y, x, h - 18);
      grad.addColorStop(0, "#3dd68c");
      grad.addColorStop(1, "#e8a0c8");
      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barW, bh);
      ctx.fillStyle = "rgba(138,150,168,0.9)";
      ctx.font = "9px system-ui";
      ctx.save();
      ctx.translate(x + barW / 2, h - 4);
      ctx.rotate(-0.5);
      ctx.textAlign = "right";
      ctx.fillText(id.slice(0, 8), 0, 0);
      ctx.restore();
    });
  }

  function renderResources(doc) {
    const mem = doc.memory || {};
    const cpu = doc.cpu_pct ?? 0;
    return (
      '<div class="monster-stats">' +
      '<div class="monster-stat"><div class="monster-stat-label">CPU</div><div class="monster-stat-val ' +
      statClass(cpu) +
      '">' +
      esc(cpu) +
      '%</div><div class="monster-bar"><span style="width:' +
      esc(cpu) +
      '%"></span></div></div>' +
      '<div class="monster-stat"><div class="monster-stat-label">Memory</div><div class="monster-stat-val ' +
      statClass(mem.used_pct) +
      '">' +
      esc(mem.used_pct) +
      '%</div><div class="monster-bar"><span style="width:' +
      esc(mem.used_pct) +
      '%"></span></div></div>' +
      '<div class="monster-stat"><div class="monster-stat-label">Load (1/5/15)</div><div class="monster-stat-val">' +
      esc((doc.loadavg || []).join(" / ")) +
      "</div></div>" +
      '<div class="monster-stat"><div class="monster-stat-label">Cores</div><div class="monster-stat-val">' +
      esc(doc.cpu_cores) +
      "</div></div>" +
      "</div>" +
      '<p class="monster-sub">Swap: ' +
      esc(mem.swap_used_pct) +
      "% · Processes: " +
      esc(doc.process_count) +
      " · Uptime: " +
      esc(Math.round((doc.uptime_sec || 0) / 60)) +
      " min</p>"
    );
  }

  function renderGraphsTab(doc) {
    return (
      '<div class="monster-section">' +
      '<h3 class="monster-section-title">Live <span>metrics</span></h3>' +
      renderResources(doc) +
      "</div>" +
      '<div class="monster-section">' +
      '<h3 class="monster-section-title">History <span>graphs</span></h3>' +
      '<div class="monster-chart-grid">' +
      '<div class="monster-chart-card"><label>CPU · memory · load (1m)</label>' +
      '<canvas id="monster-chart-live" width="520" height="120"></canvas>' +
      '<div class="monster-legend"><span><i class="lg"></i>CPU</span><span><i class="lb"></i>Memory</span><span><i class="lp"></i>Load</span></div></div>' +
      '<div class="monster-chart-card"><label>OCR chambers · verified samples</label>' +
      '<canvas id="monster-chart-chambers" width="520" height="120"></canvas></div>' +
      "</div></div>" +
      (doc.thermal?.headroom_pct != null
        ? '<div class="monster-section"><h3 class="monster-section-title">Thermal <span>headroom</span></h3>' +
          '<div class="monster-stat" style="max-width:240px"><div class="monster-stat-label">Headroom</div>' +
          '<div class="monster-stat-val ' +
          statClass(100 - Number(doc.thermal.headroom_pct)) +
          '">' +
          esc(doc.thermal.headroom_pct) +
          '%</div></div></div>'
        : "")
    );
  }

  function renderVisionTab(ocr) {
    const status = ocr?.status || ocr || {};
    const chambers = status.chambers || {};
    const brain = status.ocr_brain || {};
    const ids = Object.keys(chambers).sort();
    let cards = "";
    ids.forEach(function (cid) {
      const row = chambers[cid];
      const train = row?.train || {};
      const corpus = row?.corpus || {};
      const verified = Number(train.verified_count || 0);
      const candidates = Number(corpus.candidate_count || train.candidate_count || 0);
      const pct = candidates ? Math.min(100, Math.round((verified / candidates) * 100)) : 0;
      cards +=
        '<div class="monster-chamber"><h4>' +
        esc(cid) +
        "</h4>" +
        '<div class="monster-bar"><span style="width:' +
        pct +
        '%"></span></div>' +
        '<div class="monster-chamber-meta">' +
        esc(verified) +
        " verified · " +
        esc(candidates) +
        " candidates" +
        (train.fluent ? " · <span class='monster-posture-ok'>fluent</span>" : "") +
        "</div></div>";
    });
    return (
      '<div class="monster-section">' +
      '<h3 class="monster-section-title">Hostess 7 <span>vision OCR</span></h3>' +
      '<div class="monster-stats">' +
      '<div class="monster-stat"><div class="monster-stat-label">Chambers</div><div class="monster-stat-val ok">' +
      esc(ids.length || brain.chambers?.length || 0) +
      "</div></div>" +
      '<div class="monster-stat"><div class="monster-stat-label">Brain candidates</div><div class="monster-stat-val">' +
      esc(brain.total_candidates || "—") +
      "</div></div>" +
      '<div class="monster-stat"><div class="monster-stat-label">Verified</div><div class="monster-stat-val ok">' +
      esc(brain.total_verified || "—") +
      "</div></div>" +
      '<div class="monster-stat"><div class="monster-stat-label">Final Eye</div><div class="monster-stat-val ' +
      (status.final_eye_live ? "ok" : "warn") +
      '">' +
      (status.final_eye_live ? "Live" : "Offline") +
      "</div></div>" +
      "</div>" +
      '<div class="monster-toolbar">' +
      '<button type="button" class="monster-btn action" data-ocr="ingest-all">Ingest all</button>' +
      '<button type="button" class="monster-btn action" data-ocr="train-all">Train all</button>' +
      '<button type="button" class="monster-btn pink" data-ocr="cycle">Full cycle</button>' +
      "</div></div>" +
      '<div class="monster-section"><h3 class="monster-section-title">Chamber <span>posture</span></h3>' +
      '<div class="monster-chamber-grid">' +
      (cards || "<p class='monster-sub'>No chamber data yet — run ingest.</p>") +
      "</div></div>"
    );
  }

  function renderSecurityTab(intel) {
    const sec = intel?.security || {};
    const yielded = !!(global.NexusFieldShell?.isYieldedToHost?.() || document.documentElement.classList.contains("field-yielded-to-host"));
    return (
      '<div class="monster-section">' +
      '<h3 class="monster-section-title">Security <span>hold</span></h3>' +
      '<div class="monster-posture">' +
      '<div class="monster-posture-card"><h4>Underlying OS</h4><p>' +
      (sec.freeze_underlying_os === false
        ? "<span class='monster-posture-ok'>Not frozen</span> — guest OS keeps running. AmmoOS holds the security envelope (gatekeeper, shield, OCR brain)."
        : "Freeze policy legacy — prefer security hold.") +
      "</p></div>" +
      '<div class="monster-posture-card"><h4>Alt+Tab</h4><p>' +
      (yielded
        ? "<span class='monster-posture-warn'>Yielded to host</span> — Alt+Tab belongs to the underlying OS. Security hold remains active."
        : "<span class='monster-posture-ok'>AmmoOS sovereign</span> — Alt+Tab cycles field programs. Use <em>Return to host OS</em> from Start when you want the guest desktop.") +
      "</p></div>" +
      '<div class="monster-posture-card"><h4>Protections</h4><p>' +
      esc((sec.protections || ["connection_gatekeeper", "field_perimeter", "ironclad"]).join(" · ")) +
      "</p></div>" +
      "</div></div>" +
      '<div class="monster-section"><h3 class="monster-section-title">Desktop <span>yield</span></h3>' +
      '<div class="monster-action-grid">' +
      (yielded
        ? '<button type="button" class="monster-action-card" data-yield="return"><strong>Restore AmmoOS</strong>Return from host — fullscreen C2, security unchanged</button>'
        : '<button type="button" class="monster-action-card pink" data-yield="host"><strong>Return to host OS</strong>Drop AmmoOS to background — no freeze, security hold stays on</button>') +
      '<button type="button" class="monster-action-card" data-rescue="desktop"><strong>Show desktop</strong>Minimize all program windows</button>' +
      '<button type="button" class="monster-action-card" data-rescue="lock"><strong>Lock</strong>Field lock screen</button>' +
      "</div></div>"
    );
  }

  function filteredProcesses() {
    const q = state.filter.toLowerCase();
    if (!q) return state.processes;
    return state.processes.filter(function (p) {
      const blob = (p.name + " " + p.cmd + " " + p.user + " " + p.pid).toLowerCase();
      return blob.includes(q);
    });
  }

  function renderProcesses() {
    const rows = filteredProcesses();
    let html =
      '<div class="monster-toolbar">' +
      '<input type="search" class="monster-search" id="monster-proc-search" placeholder="Filter processes…" value="' +
      esc(state.filter) +
      '" />' +
      '<button type="button" class="monster-btn end" id="monster-refresh">Refresh</button>' +
      '</div><table class="monster-table"><thead><tr>' +
      "<th>Name</th><th>PID</th><th>CPU</th><th>MEM</th><th>User</th><th>Command</th><th></th>" +
      "</tr></thead><tbody>";
    rows.forEach(function (p) {
      html +=
        "<tr><td>" +
        esc(p.name) +
        "</td><td>" +
        esc(p.pid) +
        "</td><td>" +
        esc(p.cpu_pct) +
        "</td><td>" +
        esc(p.mem_pct) +
        "</td><td>" +
        esc(p.user) +
        '</td><td class="cmd" title="' +
        esc(p.cmd) +
        '">' +
        esc(p.cmd) +
        '</td><td><button type="button" class="monster-btn" data-kill="' +
        esc(p.pid) +
        '" ' +
        (p.protected ? 'disabled title="Protected field process"' : "") +
        ">Kill</button> <button type="button" class="monster-btn end" data-end=\"" +
        esc(p.pid) +
        '" ' +
        (p.protected ? "disabled" : "") +
        ">End</button></td></tr>";
    });
    html += "</tbody></table>";
    return html;
  }

  function renderServices(services) {
    let html = '<div class="monster-svc">';
    (services || []).forEach(function (s) {
      html +=
        '<div class="monster-svc-row">' +
        '<span class="monster-svc-dot' +
        (s.up ? " up" : "") +
        '"></span>' +
        '<span class="monster-svc-name">' +
        esc(s.name) +
        " :" +
        esc(s.port) +
        "</span>" +
        '<span class="monster-sub">' +
        esc(s.status) +
        "</span>" +
        (s.up
          ? '<button type="button" class="monster-btn end" data-svc-term="' +
            esc(s.id) +
            '">Terminate</button>'
          : "") +
        "</div>";
    });
    html += "</div>";
    return html;
  }

  function renderRescue() {
    return (
      '<div class="monster-rescue">' +
      '<button type="button" class="monster-rescue-btn" data-rescue="desktop"><strong>Show desktop</strong>Minimize all program windows</button>' +
      '<button type="button" class="monster-rescue-btn" data-rescue="home"><strong>AmmoOS C2</strong>Return to field desktop</button>' +
      '<button type="button" class="monster-rescue-btn pink" data-yield="host"><strong>Return to host OS</strong>Security hold — no freeze</button>' +
      '<button type="button" class="monster-rescue-btn" data-rescue="lock"><strong>Lock</strong>Open field lock screen</button>' +
      '<button type="button" class="monster-rescue-btn" data-rescue="thermal"><strong>Thermal</strong>Open thermal manager</button>' +
      '<button type="button" class="monster-rescue-btn danger" data-rescue="shield"><strong>Shield scan</strong>Admin window shield enforce</button>' +
      "</div>"
    );
  }

  function paintCharts() {
    drawLineChart(document.getElementById("monster-chart-live"), {
      cpu: state.cpuHist,
      mem: state.memHist,
      load: state.loadHist.map(function (v) {
        return Math.min(100, v * 20);
      }),
    }, 100);
    const chambers = (state.ocrDoc?.status || state.ocrDoc || {}).chambers || {};
    drawChamberBars(document.getElementById("monster-chart-chambers"), chambers);
  }

  async function render() {
    const main = document.getElementById("monster-main");
    if (!main) return;
    const doc = await api("");
    recordSample(doc);

    if (state.tab === "graphs") {
      main.innerHTML = renderGraphsTab(doc);
      requestAnimationFrame(paintCharts);
      return;
    }
    if (state.tab === "vision") {
      state.ocrDoc = await ocrStatus();
      main.innerHTML = renderVisionTab(state.ocrDoc);
      bindActions(main);
      return;
    }
    if (state.tab === "security") {
      const intel = doc.intel || (await api("/intel"));
      main.innerHTML = renderSecurityTab(intel);
      bindActions(main);
      return;
    }
    if (state.tab === "resources") {
      main.innerHTML = renderResources(doc);
      return;
    }
    if (state.tab === "services") {
      main.innerHTML = renderServices(doc.services);
      bindActions(main);
      return;
    }
    if (state.tab === "rescue") {
      main.innerHTML = renderRescue();
      bindActions(main);
      return;
    }
    const procDoc = await api("/processes");
    state.processes = procDoc.processes || [];
    main.innerHTML =
      '<div class="monster-section"><h3 class="monster-section-title">System <span>snapshot</span></h3>' +
      renderResources(doc) +
      "</div>" +
      renderProcesses();
    bindActions(main);
    const search = document.getElementById("monster-proc-search");
    search?.addEventListener("input", function () {
      state.filter = search.value;
      const table = main.querySelector(".monster-table");
      if (table) {
        const wrap = document.createElement("div");
        wrap.innerHTML = renderProcesses();
        const newTable = wrap.querySelector(".monster-table");
        if (newTable) table.replaceWith(newTable);
        bindActions(main);
      }
    });
    document.getElementById("monster-refresh")?.addEventListener("click", function () {
      render();
    });
  }

  function bindActions(root) {
    root.querySelectorAll("[data-kill]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!confirm("Kill process " + btn.dataset.kill + "?")) return;
        await api("/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "kill", pid: Number(btn.dataset.kill), force: true }),
        });
        render();
      });
    });
    root.querySelectorAll("[data-end]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!confirm("End process " + btn.dataset.end + " (SIGTERM)?")) return;
        await api("/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "kill", pid: Number(btn.dataset.end) }),
        });
        render();
      });
    });
    root.querySelectorAll("[data-svc-term]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!confirm("Terminate service " + btn.dataset.svcTerm + "?")) return;
        await api("/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "terminate", service: btn.dataset.svcTerm }),
        });
        render();
      });
    });
    root.querySelectorAll("[data-rescue]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const act = btn.dataset.rescue;
        if (act === "desktop") global.NexusFieldShell?.showDesktop?.();
        else if (act === "home") global.location.href = "/field";
        else if (act === "lock") global.NexusFieldShell?.openProgram?.({ exec: "/field-lock" });
        else if (act === "thermal") global.open("http://127.0.0.1:9481/world/queen-thermal-manager.html", "_blank");
        else if (act === "shield")
          fetch("/api/admin-shield", { method: "GET", credentials: "same-origin" }).catch(function () {});
        close();
      });
    });
    root.querySelectorAll("[data-yield]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.yield === "host") global.NexusFieldShell?.yieldToHost?.();
        else global.NexusFieldShell?.returnFromHost?.();
        close();
        render();
      });
    });
    root.querySelectorAll("[data-ocr]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        const sub = btn.dataset.ocr;
        const path =
          sub === "ingest-all"
            ? "/api/hostess7/ocr/ingest-all"
            : sub === "train-all"
              ? "/api/hostess7/ocr/train-all"
              : "/api/hostess7/ocr/cycle";
        btn.disabled = true;
        try {
          await fetch(path, {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store",
          });
        } catch (_) {}
        btn.disabled = false;
        render();
      });
    });
  }

  function open() {
    ensureOverlay();
    state.open = true;
    document.getElementById("monster-overlay")?.classList.add("open");
    render();
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(function () {
      if (state.open) render();
    }, 4000);
  }

  function close() {
    state.open = false;
    document.getElementById("monster-overlay")?.classList.remove("open");
    if (state.timer) clearInterval(state.timer);
  }

  global.FieldMonsterMonitor = { open, close, render };
})(typeof window !== "undefined" ? window : globalThis);