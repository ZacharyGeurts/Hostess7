/**
 * Field Ping — colorful ICMP + traceroute panel (KILROY iPXE lineage).
 */
(function (global) {
  "use strict";

  const API = (function () {
    if (global.H7Api) return global.H7Api("/api/field-ping");
    return "/api/field-ping";
  })();

  const state = { busy: false, lastPing: null, lastTrace: null, posture: null };

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

  function hostValue() {
    return String($("fp-host")?.value || "").trim();
  }

  function bodyBase() {
    return {
      host: hostValue(),
      count: Number($("fp-count")?.value || 4),
      size: Number($("fp-size")?.value || 64),
      max_hops: Number($("fp-hops")?.value || 30),
    };
  }

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  async function apiCall(action, extra) {
    const body = Object.assign({ action: action }, bodyBase(), extra || {});
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("api " + res.status);
    return res.json();
  }

  async function httpProbe(host) {
    const t0 = performance.now();
    const schemes = ["https://", "http://"];
    let lastErr = null;
    for (let i = 0; i < schemes.length; i++) {
      const url = schemes[i] + host.replace(/^\/*/, "") + "/";
      try {
        await fetch(url, { mode: "no-cors", cache: "no-store" });
        const ms = Math.round(performance.now() - t0);
        return {
          ok: true,
          mode: "http_probe",
          host: host,
          rtts_ms: [ms],
          stats: { avg_ms: ms, min_ms: ms, max_ms: ms, rx: 1, tx: 1, loss_pct: 0 },
          raw: "HTTP probe (Pages) · ICMP available on loopback NEXUS panel",
          at: new Date().toISOString(),
        };
      } catch (e) {
        lastErr = e;
      }
    }
    return {
      ok: false,
      mode: "http_probe",
      host: host,
      error: String(lastErr || "probe_failed"),
      raw: "HTTP probe failed · run on loopback for ICMP",
    };
  }

  function setBusy(on) {
    state.busy = !!on;
    ["fp-run-ping", "fp-run-trace", "fp-run-both"].forEach(function (id) {
      const el = $(id);
      if (el) el.disabled = state.busy;
    });
  }

  function setTab(name) {
    document.querySelectorAll(".fp-tab").forEach(function (btn) {
      const on = btn.dataset.tab === name;
      btn.classList.toggle("fp-tab--active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".fp-panel").forEach(function (panel) {
      const on = panel.dataset.panel === name;
      panel.classList.toggle("fp-panel--active", on);
      panel.hidden = !on;
    });
  }

  function rttClass(ms) {
    if (ms == null || !Number.isFinite(ms)) return "";
    if (ms < 30) return "fp-reply--fast";
    if (ms < 120) return "fp-reply--mid";
    return "fp-reply--slow";
  }

  function hopBarWidth(ms, maxMs) {
    if (!Number.isFinite(ms) || !maxMs) return 4;
    return Math.max(4, Math.round((ms / maxMs) * 100));
  }

  function paintSpark(rtts) {
    const canvas = $("fp-spark");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const pad = 12;
    const vals = (rtts || []).filter(function (v) {
      return Number.isFinite(v);
    });
    if (!vals.length) {
      ctx.fillStyle = "#4b5563";
      ctx.font = "12px system-ui";
      ctx.fillText("Run ping to paint RTT sparkline", pad, h / 2);
      return;
    }
    const max = Math.max.apply(null, vals) * 1.15 || 1;
    ctx.strokeStyle = "rgba(148,163,184,0.15)";
    for (let g = 0; g < 4; g++) {
      const y = pad + ((h - pad * 2) * g) / 3;
      ctx.beginPath();
      ctx.moveTo(pad, y);
      ctx.lineTo(w - pad, y);
      ctx.stroke();
    }
    const step = (w - pad * 2) / Math.max(vals.length - 1, 1);
    const grad = ctx.createLinearGradient(pad, 0, w - pad, 0);
    grad.addColorStop(0, "#34d399");
    grad.addColorStop(0.5, "#22d3ee");
    grad.addColorStop(1, "#fb7185");
    ctx.strokeStyle = grad;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    vals.forEach(function (v, i) {
      const x = pad + i * step;
      const y = h - pad - (v / max) * (h - pad * 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    vals.forEach(function (v, i) {
      const x = pad + i * step;
      const y = h - pad - (v / max) * (h - pad * 2);
      ctx.fillStyle = "#22d3ee";
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function renderPing(doc) {
    state.lastPing = doc;
    const stats = doc.stats || {};
    const rtts = doc.rtts_ms || [];
    const loss = stats.loss_pct;
    const avg = stats.avg_ms;
    const statHtml = [
      statCard(avg != null ? avg.toFixed(1) + " ms" : "—", "Avg RTT", avg != null && avg < 80 ? "ok" : "warn"),
      statCard(stats.min_ms != null ? stats.min_ms.toFixed(1) + " ms" : "—", "Min", "info"),
      statCard(stats.max_ms != null ? stats.max_ms.toFixed(1) + " ms" : "—", "Max", "warn"),
      statCard(loss != null ? loss + "%" : "—", "Loss", loss > 0 ? "bad" : "ok"),
      statCard(String(stats.rx != null ? stats.rx : "—") + "/" + String(stats.tx != null ? stats.tx : "—"), "Rx/Tx", "info"),
      statCard(doc.mode || "icmp", "Mode", doc.ok ? "ok" : "bad"),
    ].join("");
    const statsEl = $("fp-stats");
    if (statsEl) statsEl.innerHTML = statHtml;
    paintSpark(rtts);
    const replies = $("fp-replies");
    if (replies) {
      if (!rtts.length && doc.raw) {
        replies.innerHTML = '<div class="fp-reply">' + esc(doc.raw.split("\n").slice(0, 8).join("\n")) + "</div>";
      } else {
        replies.innerHTML = rtts
          .map(function (ms, i) {
            return (
              '<div class="fp-reply ' +
              rttClass(ms) +
              '">seq=' +
              (i + 1) +
              " · " +
              esc(doc.host) +
              " · <strong>" +
              ms.toFixed(2) +
              " ms</strong></div>"
            );
          })
          .join("");
      }
    }
    renderDetails();
    renderRaw();
    const foot = $("fp-foot");
    if (foot) foot.textContent = "Ping " + (doc.ok ? "OK" : "FAIL") + " · " + (doc.at || "—");
  }

  function statCard(val, label, tone) {
    return (
      '<div class="fp-stat fp-stat--' +
      (tone || "info") +
      '"><b>' +
      esc(val) +
      "</b><span>" +
      esc(label) +
      "</span></div>"
    );
  }

  function renderTrace(doc) {
    state.lastTrace = doc;
    const hops = doc.hops || [];
    const maxRtt = Math.max.apply(
      null,
      hops.map(function (h) {
        return h.rtt_ms || 0;
      }).concat([1])
    );
    const meta = $("fp-trace-meta");
    if (meta) {
      meta.innerHTML =
        "<strong>" +
        esc(doc.tool || "traceroute") +
        "</strong> → " +
        esc(doc.host) +
        " · " +
        hops.length +
        " hops · " +
        (doc.elapsed_ms != null ? doc.elapsed_ms + " ms" : "—");
    }
    const body = $("fp-trace-body");
    if (body) {
      body.innerHTML = hops
        .map(function (h) {
          const ms = h.rtt_ms;
          const w = hopBarWidth(ms, maxRtt);
          return (
            "<tr><td>" +
            esc(h.hop) +
            "</td><td>" +
            esc(h.host) +
            "</td><td>" +
            (ms != null ? ms.toFixed(2) + " ms" : "—") +
            '</td><td><div class="fp-trace-bar"><i style="width:' +
            w +
            '%"></i></div></td></tr>'
          );
        })
        .join("");
    }
    renderDetails();
    renderRaw();
  }

  function renderDetails() {
    const el = $("fp-details");
    if (!el) return;
    const rows = [];
    const ping = state.lastPing;
    const trace = state.lastTrace;
    if (ping) {
      rows.push(detailRow("Ping host", ping.host));
      rows.push(detailRow("Resolve", (ping.resolve?.addrs || []).join(", ") || ping.resolve?.error || "—"));
      rows.push(detailRow("Payload", String(ping.size || "—") + " B"));
      rows.push(detailRow("Elapsed", (ping.elapsed_ms != null ? ping.elapsed_ms + " ms" : "—")));
    }
    if (trace) {
      rows.push(detailRow("Trace tool", trace.tool || "—"));
      rows.push(detailRow("Hop count", String(trace.hop_count != null ? trace.hop_count : "—")));
      rows.push(detailRow("Trace resolve", (trace.resolve?.addrs || []).join(", ") || "—"));
    }
    if (state.posture) {
      rows.push(detailRow("ICMP bin", state.posture.ping_bin || "—"));
      rows.push(detailRow("Trace bin", state.posture.traceroute_bin || "—"));
      rows.push(detailRow("Source", state.posture.source || "KILROY iPXE"));
    }
    el.innerHTML = rows.join("") || '<div class="fp-detail-row"><strong>Status</strong><span>Run ping or traceroute</span></div>';
  }

  function detailRow(k, v) {
    return '<div class="fp-detail-row"><strong>' + esc(k) + "</strong><span>" + esc(v) + "</span></div>";
  }

  function renderRaw() {
    const el = $("fp-raw");
    if (!el) return;
    const chunks = [];
    if (state.lastPing?.raw) chunks.push("=== PING ===\n" + state.lastPing.raw);
    if (state.lastTrace?.raw) chunks.push("=== TRACEROUTE ===\n" + state.lastTrace.raw);
    el.textContent = chunks.join("\n\n") || "Raw output appears here after a run.";
  }

  async function runPing() {
    if (!hostValue()) return;
    setBusy(true);
    try {
      let doc;
      try {
        doc = await apiCall("ping");
      } catch (_) {
        if (pagesRuntime()) doc = await httpProbe(hostValue());
        else throw _;
      }
      if (!doc.ok && pagesRuntime() && doc.error) {
        doc = await httpProbe(hostValue());
      }
      renderPing(doc);
      setTab("ping");
    } catch (e) {
      renderPing({ ok: false, host: hostValue(), raw: String(e), rtts_ms: [], stats: {} });
    } finally {
      setBusy(false);
    }
  }

  async function runTrace() {
    if (!hostValue()) return;
    setBusy(true);
    try {
      const doc = await apiCall("traceroute");
      renderTrace(doc);
      setTab("trace");
    } catch (e) {
      renderTrace({ ok: false, host: hostValue(), hops: [], raw: String(e) });
      setTab("trace");
    } finally {
      setBusy(false);
    }
  }

  async function runBoth() {
    if (!hostValue()) return;
    setBusy(true);
    try {
      let pingDoc;
      try {
        pingDoc = await apiCall("ping");
      } catch (_) {
        pingDoc = pagesRuntime() ? await httpProbe(hostValue()) : { ok: false, raw: String(_) };
      }
      const traceDoc = await apiCall("traceroute").catch(function (e) {
        return { ok: false, hops: [], raw: String(e) };
      });
      renderPing(pingDoc);
      renderTrace(traceDoc);
      setTab("ping");
    } finally {
      setBusy(false);
    }
  }

  async function loadPosture() {
    try {
      const res = await fetch(API + "?t=" + Date.now(), { cache: "no-store", credentials: "same-origin" });
      if (res.ok) state.posture = await res.json();
    } catch (_) {
      state.posture = { source: "KILROY iPXE", icmp_available: false };
    }
    const el = $("fp-posture");
    if (el && state.posture) {
      el.textContent =
        (state.posture.icmp_available ? "ICMP live" : "HTTP probe on Pages · ICMP on loopback") +
        " · " +
        (state.posture.posture || "");
    }
    renderDetails();
  }

  function wire() {
    $("fp-form")?.addEventListener("submit", function (ev) {
      ev.preventDefault();
      runPing();
    });
    $("fp-run-trace")?.addEventListener("click", runTrace);
    $("fp-run-both")?.addEventListener("click", runBoth);
    document.querySelectorAll(".fp-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setTab(btn.dataset.tab || "ping");
      });
    });
    const params = new URLSearchParams(location.search);
    const h = params.get("host");
    if (h && $("fp-host")) $("fp-host").value = h;
    loadPosture();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);