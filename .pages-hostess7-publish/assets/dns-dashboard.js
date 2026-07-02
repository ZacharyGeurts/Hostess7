/**
 * Planetary DNS & DHCP Command — threat levels, traffic patterns, secure threat model, details.
 */
(function (global) {
  "use strict";

  let lastFd = null;
  let lastDnsFp = "";
  let tabsBound = false;
  let filterBound = false;
  const smooth = () => global.NexusUiSmooth;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  function complianceChip(c) {
    const v = String(c || "documented").toLowerCase();
    const cls = v === "enforced" ? "dns-chip-ok" : v.includes("block") ? "dns-chip-warn" : "dns-chip-meta";
    return `<span class="dns-chip ${cls}">${esc(c)}</span>`;
  }

  function alertLevelClass(level) {
    if (level === "critical") return "dns-alert--critical";
    if (level === "high") return "dns-alert--high";
    if (level === "medium") return "dns-alert--medium";
    return "dns-alert--info";
  }

  function threatLevelClass(level) {
    const v = String(level || "info").toLowerCase();
    if (v === "extreme" || v === "critical") return "dns-threat-lvl--extreme";
    if (v === "high") return "dns-threat-lvl--high";
    if (v === "medium") return "dns-threat-lvl--medium";
    if (v === "mitigated" || v === "low") return "dns-threat-lvl--low";
    return "dns-threat-lvl--info";
  }

  function threatLevelChip(level) {
    return `<span class="dns-threat-lvl ${threatLevelClass(level)}">${esc(level)}</span>`;
  }

  function trafficData(fd) {
    return fd.traffic_patterns || synthesizeTraffic(fd);
  }

  function threatModelData(fd) {
    return fd.threat_model || synthesizeThreatModel(fd);
  }

  function synthesizeTraffic(fd) {
    if (fd.traffic_patterns) return fd.traffic_patterns;
    const st = fd.stats || {};
    const dhcp = fd.dhcp_server || fd.servers?.dhcp || {};
    const eg = fd.egress_integrity?.stats || {};
    const tg = fd.threat_guard?.stats || {};
    const queries = Number(st.queries_total || st.queries || 0);
    const cache = Number(st.cache_hits || 0);
    const blocked = Number(st.blocked || 0);
    const errors = Number(st.errors || 0);
    const total = Math.max(queries, 1);
    const pct = (n) => (queries ? Math.round((n / total) * 100) : 0);
    return {
      dns: {
        queries,
        cache_hits: cache,
        blocked,
        errors,
        hit_rate_pct: pct(cache),
        block_rate_pct: pct(blocked),
        error_rate_pct: pct(errors),
        egress_checks: Number(eg.total_checks || 0),
        egress_verified: Number(eg.verified_exact || 0),
        permanent_blocks: Number(tg.permanent_blocks || 0),
      },
      dhcp: {
        leases_active: Number(dhcp.lease_count || 0),
        running: Boolean(dhcp.running),
        bind: dhcp.bind || "0.0.0.0:67",
      },
      channels: [
        { id: "queries", label: "DNS queries", value: queries, pct: 100 },
        { id: "cache", label: "Cache hits", value: cache, pct: pct(cache) },
        { id: "blocked", label: "Policy blocked", value: blocked, pct: pct(blocked) },
        { id: "errors", label: "SERVFAIL", value: errors, pct: pct(errors) },
        { id: "egress", label: "Egress verified", value: Number(eg.verified_exact || 0), pct: eg.total_checks ? Math.round((Number(eg.verified_exact || 0) / Number(eg.total_checks)) * 100) : 0 },
        { id: "leases", label: "DHCP leases", value: Number(dhcp.lease_count || 0), pct: dhcp.running ? 100 : 0 },
      ],
    };
  }

  function synthesizeThreatModel(fd) {
    if (fd.threat_model) return fd.threat_model; // used only when building fallback
    const pol = fd.resolver_policy || {};
    const tg = fd.threat_guard || {};
    const to = fd.takeover || {};
    const dhcp = fd.dhcp_server || {};
    const mp = fd.multipoint_identity || {};
    const enforced = (fd.engineer_briefing?.quick_facts?.rfc_enforced) || 0;
    const rfcTotal = (fd.engineer_briefing?.quick_facts?.rfc_total) || (fd.rfc_matrix?.length) || 0;
    const alerts = fd.engineer_briefing?.alerts || [];
    const concernCount = alerts.filter((a) => ["critical", "high", "medium"].includes(a.level)).length;
    const overall = concernCount >= 2 ? "elevated" : concernCount ? "guarded" : (fd.planetary_security_level === "extreme" ? "controlled" : "stable");
    return {
      framework: "STRIDE + DNS/DHCP planetary",
      overall_risk: overall,
      controls_active: enforced,
      controls_total: rfcTotal,
      summary: "Loopback Truth Resolver, multipoint fingerprint, foreign resolver block, DHCP listen-before-reject.",
      dns_vectors: [
        { id: "spoofing", threat: "DNS response spoofing / cache poison", level: pol.truthful_trace ? "mitigated" : "open", control: "dig +trace from root — no public shortcut", rfc: "RFC 4033" },
        { id: "tampering", threat: "Unauthorized zone or record mutation", level: pol.loopback_only ? "mitigated" : "monitored", control: "Loopback bind only · egress integrity hash match", rfc: "RFC 1035 §4.1" },
        { id: "repudiation", threat: "Query/answer non-repudiation gap", level: "monitored", control: "Recent query JSONL + egress integrity log", rfc: "RFC 7766" },
        { id: "disclosure", threat: "Foreign resolver data exfiltration", level: fd.foreign_resolvers_stopped ? "mitigated" : "open", control: `${fd.engineer_briefing?.quick_facts?.foreign_blocked || 0} resolvers blocked`, rfc: "RFC 8484" },
        { id: "dos", threat: "Amplification / QPS flood", level: tg.policy?.max_qps_per_client ? "mitigated" : "monitored", control: `Max ${tg.policy?.max_qps_per_client || 30} QPS/client · permanent eradication`, rfc: "RFC 6891" },
        { id: "elevation", threat: "Lateral movement via DNS channel", level: tg.policy?.no_lateral_movement ? "mitigated" : "monitored", control: "No lateral movement · DHCP DNS-only option", rfc: "RFC 2131" },
      ],
      dhcp_vectors: [
        { id: "rogue", threat: "Rogue DHCP server on LAN", level: to.incumbents?.incumbent_dhcp ? "monitored" : "mitigated", control: "Incumbent port-67 detection · graceful takeover", rfc: "RFC 2131" },
        { id: "starvation", threat: "DHCP pool exhaustion", level: dhcp.running ? "monitored" : "info", control: `${dhcp.lease_count || 0} active leases · bind ${dhcp.bind || "67/udp"}`, rfc: "RFC 2131 §4.3" },
        { id: "option-inject", threat: "Malicious DNS option injection", level: "mitigated", control: `DNS option → ${(dhcp.dns_option || ["127.0.0.1"]).join(", ")}`, rfc: "RFC 3646" },
      ],
      identification: {
        points: mp.point_count || (fd.identification_points || []).length,
        untrusted_blocked: (mp.untrusted_never_added || []).length,
      },
    };
  }

  function bindRefTabs() {
    if (tabsBound) return;
    tabsBound = true;
    const nav = $("dns-ref-tabs");
    if (!nav) return;
    nav.querySelectorAll("[data-dns-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.dnsTab;
        nav.querySelectorAll("[data-dns-tab]").forEach((b) => b.classList.toggle("active", b === btn));
        document.querySelectorAll(".dns-ref-panel").forEach((p) => {
          const on = p.dataset.dnsPanel === tab;
          p.classList.toggle("active", on);
          p.hidden = !on;
        });
      });
    });
  }

  function bindFilters() {
    if (filterBound) return;
    filterBound = true;
    const ui = smooth();
    const onRfc = () => { if (lastFd) renderRfcTable(lastFd); };
    const onInternet = () => { if (lastFd) renderInternetField(lastFd); };
    if (ui) {
      ui.bindDebouncedInput($("dns-rfc-search"), onRfc, 150);
      ui.bindDebouncedInput($("dns-internet-filter"), onInternet, 150);
    } else {
      $("dns-rfc-search")?.addEventListener("input", onRfc);
      $("dns-internet-filter")?.addEventListener("input", onInternet);
    }
  }

  function dnsFingerprint(fd) {
    const ui = smooth();
    if (ui) {
      return ui.fingerprint(fd, ["updated", "schema", "running", "stats", "recent_queries", "top_domains", "threats", "dhcp_events"]);
    }
    return String(fd.updated || "") + String((fd.stats || {}).queries_total || 0);
  }

  function dnsViewRoot() {
    return $("view-dns");
  }

  function renderDnsHero(fd) {
    const br = fd.engineer_briefing || {};
    const qf = br.quick_facts || {};
    const run = fd.running;
    const title = $("dns-hero-title");
    const motto = $("dns-motto");
    const status = $("dns-hero-status");
    const dhcp = fd.dhcp_server || fd.servers?.dhcp || {};
    const dhcpRun = Boolean(dhcp.running);
    if (title) {
      title.innerHTML = run
        ? `<span class="dns-hero-run">RUNNING</span> Truth Resolver · ${dhcpRun ? '<span class="dns-hero-run">DHCP LIVE</span>' : '<span class="dns-hero-stop">DHCP IDLE</span>'}`
        : '<span class="dns-hero-stop">STOPPED</span> Truth Resolver · Field DHCP';
    }
    if (motto) {
      motto.textContent = br.lead || fd.planetary?.motto || "Planetary DNS & DHCP — trace-only resolver, graceful takeover, EXTREME zone posture.";
    }
    if (status) {
      const listeners = (fd.listeners || qf.listeners || []).map((l) => `<code>${esc(l)}</code>`).join(" ");
      const tm = threatModelData(fd);
      status.innerHTML = [
        `<div class="dns-hero-pill ${run ? "dns-hero-pill--ok" : "dns-hero-pill--bad"}"><span>DNS</span><strong>${run ? "LIVE" : "DOWN"}</strong></div>`,
        `<div class="dns-hero-pill ${dhcpRun ? "dns-hero-pill--ok" : ""}"><span>DHCP</span><strong>${dhcpRun ? "LIVE" : dhcp.may_serve === false ? "OBSERVE" : "IDLE"}</strong></div>`,
        `<div class="dns-hero-pill"><span>Planetary</span><strong>${esc(fd.planetary_security_level || qf.planetary_level || "—")}</strong></div>`,
        `<div class="dns-hero-pill"><span>Threat</span><strong>${esc(tm.overall_risk || "—")}</strong></div>`,
        `<div class="dns-hero-pill"><span>Leases</span><strong>${esc(String(dhcp.lease_count ?? 0))}</strong></div>`,
        `<div class="dns-hero-pill dns-hero-pill--wide"><span>Listeners</span><strong>${listeners || "—"}</strong></div>`,
      ].join("");
    }
  }

  function renderPostureStrip(fd) {
    const el = $("dns-posture-strip");
    if (!el) return;
    const qf = fd.engineer_briefing?.quick_facts || {};
    const tm = threatModelData(fd);
    const traffic = trafficData(fd);
    const concerns = (fd.engineer_briefing?.alerts || []).length;
    const items = [
      ["Planetary security", fd.planetary_security_level || qf.planetary_level || "—", fd.planetary_security_level === "extreme" ? "extreme" : "info"],
      ["Threat posture", tm.overall_risk || "—", tm.overall_risk],
      ["RFC controls", `${tm.controls_active}/${tm.controls_total}`, tm.controls_active === tm.controls_total ? "mitigated" : "monitored"],
      ["Active concerns", String(concerns), concerns ? "high" : "mitigated"],
      ["DNS queries", String(traffic.dns.queries), "info"],
      ["Cache hit rate", `${traffic.dns.hit_rate_pct}%`, traffic.dns.hit_rate_pct > 50 ? "mitigated" : "monitored"],
      ["DHCP leases", String(traffic.dhcp.leases_active), traffic.dhcp.running ? "mitigated" : "monitored"],
      ["Permanent blocks", String(traffic.dns.permanent_blocks), traffic.dns.permanent_blocks ? "high" : "mitigated"],
    ];
    el.innerHTML = items.map(([label, value, lvl]) => `<div class="dns-posture-card">
      <span class="dns-posture-label">${esc(label)}</span>
      <strong class="dns-posture-value">${esc(String(value))}</strong>
      ${threatLevelChip(lvl)}
    </div>`).join("");
  }

  function renderThreatPosture(fd) {
    const el = $("dns-threat-posture");
    if (!el) return;
    const alerts = fd.engineer_briefing?.alerts || [];
    const tm = threatModelData(fd);
    const zones = fd.zones || fd.planetary?.zones || [];
    const extremeZones = zones.filter((z) => z.security_level === "extreme" || z.extreme_active).length;
    el.innerHTML = `<div class="dns-threat-summary">
      <div class="dns-threat-gauge">
        <span class="dns-threat-gauge-label">Overall risk</span>
        ${threatLevelChip(tm.overall_risk)}
        <p class="meta">${esc(tm.summary || "")}</p>
      </div>
      <dl class="dns-kv-grid">
        <dt>Planetary zones</dt><dd><strong>${esc(String(zones.length))}</strong> regions · <strong>${esc(String(extremeZones))}</strong> EXTREME</dd>
        <dt>RFC enforced</dt><dd><strong>${esc(String(tm.controls_active))}</strong> / ${esc(String(tm.controls_total))}</dd>
        <dt>Multipoint IDs</dt><dd><strong>${esc(String(tm.identification?.points || 0))}</strong> trusted · ${esc(String(tm.identification?.untrusted_blocked || 0))} foreign blocked</dd>
        <dt>Foreign resolvers</dt><dd>${fd.foreign_resolvers_stopped ? '<span class="dns-chip dns-chip-ok">stopped</span>' : '<span class="dns-chip dns-chip-warn">review</span>'}</dd>
      </dl>
    </div>
    <div class="dns-concerns-list">
      <strong class="dns-concerns-head">Active concerns</strong>
      ${alerts.length ? alerts.map((a) => `<div class="dns-concern-row ${alertLevelClass(a.level)}">
        ${threatLevelChip(a.level)}
        <div><strong>${esc(a.title)}</strong><span class="meta">${esc(a.detail)}</span></div>
      </div>`).join("") : '<div class="meta dns-concern-ok">No critical concerns — planetary DNS/DHCP posture healthy.</div>'}
    </div>`;
  }

  function renderTrafficPatterns(fd) {
    const el = $("dns-traffic-patterns");
    if (!el) return;
    const traffic = trafficData(fd);
    const maxVal = Math.max(...traffic.channels.map((c) => c.value), 1);
    el.innerHTML = `<div class="dns-traffic-dns">
      <div class="dns-traffic-head"><strong>DNS</strong><span class="meta">${esc(String(traffic.dns.queries))} queries · QPS ${esc(fmtQps(traffic.dns.qps_60s))} · ${esc(String(traffic.dns.hit_rate_pct))}% cache · ${esc(fmtMs(traffic.dns.avg_latency_ms))} avg</span></div>
      ${traffic.channels.filter((c) => c.id !== "leases").map((ch) => `<div class="dns-traffic-row">
        <span class="dns-traffic-label">${esc(ch.label)}</span>
        <div class="dns-traffic-bar-wrap"><div class="dns-traffic-bar" style="width:${clamp((ch.value / maxVal) * 100, 2, 100)}%"></div></div>
        <strong class="dns-traffic-val">${esc(String(ch.value))}</strong>
        <span class="meta dns-traffic-pct">${esc(String(ch.pct))}%</span>
      </div>`).join("")}
    </div>
    <div class="dns-traffic-dhcp">
      <div class="dns-traffic-head"><strong>DHCP</strong><span class="meta">${traffic.dhcp.running ? "LIVE" : "observing"} · <code>${esc(traffic.dhcp.bind)}</code></span></div>
      <div class="dns-traffic-row">
        <span class="dns-traffic-label">Active leases</span>
        <div class="dns-traffic-bar-wrap"><div class="dns-traffic-bar dns-traffic-bar--dhcp" style="width:${clamp(traffic.dhcp.leases_active ? Math.min(traffic.dhcp.leases_active * 8, 100) : 4, 4, 100)}%"></div></div>
        <strong class="dns-traffic-val">${esc(String(traffic.dhcp.leases_active))}</strong>
      </div>
      <p class="meta dns-traffic-note">DNS option v4 ${(fd.dhcp_server?.dns_option || fd.servers?.dhcp?.dns_option || ["127.0.0.1"]).map((d) => `<code>${esc(d)}</code>`).join(" ")} — clients steered to Truth Resolver.</p>
    </div>`;
  }

  function renderThreatModel(fd) {
    const el = $("dns-threat-model");
    if (!el) return;
    const tm = threatModelData(fd);
    const allVectors = [...(tm.dns_vectors || []), ...(tm.dhcp_vectors || [])];
    el.innerHTML = `<div class="dns-model-meta">
      <span class="dns-chip dns-chip-meta">${esc(tm.framework || "STRIDE")}</span>
      <span>Overall: ${threatLevelChip(tm.overall_risk)}</span>
      <span class="meta">Controls ${esc(String(tm.controls_active))}/${esc(String(tm.controls_total))} RFC enforced</span>
    </div>
    <table class="honor-table dns-table dns-threat-model-table"><thead><tr>
      <th>Vector</th><th>Threat</th><th>Level</th><th>Control</th><th>RFC</th>
    </tr></thead><tbody>${allVectors.map((v) => `<tr>
      <td><code>${esc(v.id)}</code></td>
      <td>${esc(v.threat)}</td>
      <td>${threatLevelChip(v.level)}</td>
      <td class="meta">${esc(v.control)}</td>
      <td><code>${esc(v.rfc || "—")}</code></td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderOperationsDetail(fd) {
    const el = $("dns-operations-detail");
    if (!el) return;
    renderTakeover(fd);
    renderEgress(fd);
    renderThreatGuard(fd);
    renderMultipoint(fd);
    renderThreatsLog(fd);
    renderDhcpLeases(fd);
    renderDhcpEvents(fd);
    const to = $("dns-takeover-panel")?.innerHTML || "";
    const eg = $("dns-egress-panel")?.innerHTML || "";
    const tg = $("dns-threat-panel")?.innerHTML || "";
    const mp = $("dns-multipoint-panel")?.innerHTML || "";
    const threats = $("dns-threats-log")?.innerHTML || "";
    const leases = $("dns-dhcp-leases")?.innerHTML || "";
    const events = $("dns-dhcp-events")?.innerHTML || "";
    el.innerHTML = `<div class="dns-ops-grid">
      <section class="dns-ops-section"><h5>Graceful takeover</h5>${to}</section>
      <section class="dns-ops-section"><h5>Egress integrity</h5>${eg}</section>
      <section class="dns-ops-section"><h5>Threat guard</h5>${tg}</section>
      <section class="dns-ops-section"><h5>Threat events</h5>${threats}</section>
      <section class="dns-ops-section"><h5>DHCP leases</h5>${leases}</section>
      <section class="dns-ops-section"><h5>DHCP events</h5>${events}</section>
      <section class="dns-ops-section"><h5>Multipoint secure ID</h5>${mp}</section>
    </div>`;
  }

  function renderAlerts(fd) {
    const el = $("dns-alerts");
    if (!el) return;
    const alerts = fd.engineer_briefing?.alerts || [];
    if (!alerts.length) {
      el.innerHTML = brHealthy(fd)
        ? '<div class="dns-alert dns-alert--ok">All engineer checks passed — resolver posture healthy.</div>'
        : "";
      return;
    }
    el.innerHTML = alerts.map((a) => `<div class="dns-alert ${alertLevelClass(a.level)}">
      <strong>${esc(a.title)}</strong>
      <span class="meta">${esc(a.detail)}</span>
      ${a.action ? `<code class="dns-alert-action">${esc(a.action)}</code>` : ""}
    </div>`).join("");
  }

  function brHealthy(fd) {
    return fd.engineer_briefing?.healthy !== false && fd.running;
  }

  function renderEngineerBriefing(fd) {
    const el = $("dns-engineer-briefing");
    if (!el) return;
    const br = fd.engineer_briefing || {};
    const upfront = br.upfront || [];
    if (!upfront.length) {
      el.innerHTML = '<div class="meta">Click Refresh DNS field to load engineer upfront briefing.</div>';
      return;
    }
    el.innerHTML = `
      <p class="dns-briefing-lead">${esc(br.headline || "")}</p>
      <ul class="dns-briefing-list">${upfront.map((line) => `<li>${esc(line)}</li>`).join("")}</ul>
      ${br.love_note ? `<p class="dns-briefing-love">${esc(br.love_note)}</p>` : ""}`;
  }

  function fmtQps(v) {
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) return "0";
    return n < 10 ? n.toFixed(2) : n.toFixed(1);
  }

  function fmtMs(v) {
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) return "—";
    return n < 100 ? `${n.toFixed(1)} ms` : `${Math.round(n)} ms`;
  }

  function fmtRemaining(sec) {
    const s = Number(sec);
    if (!Number.isFinite(s) || s < 0) return "—";
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  }

  function renderOpsStrip(fd) {
    const el = $("dns-ops-strip");
    if (!el) return;
    const st = fd.stats || {};
    const br = fd.engineer_briefing?.quick_facts || {};
    const queries = st.queries_total ?? st.queries ?? 0;
    const qPct = queries ? Math.round(((st.cache_hits || 0) / queries) * 100) : 0;
    const errPct = queries ? Math.round(((st.errors || 0) / queries) * 100) : 0;
    const cache = fd.cache || {};
    const hitRate = cache.hit_rate != null ? `${Math.round(cache.hit_rate * 100)}%` : `${qPct}%`;
    const items = [
      ["Queries", queries, ""],
      ["QPS 60s", fmtQps(st.qps_60s), "rolling window"],
      ["QPS 5m", fmtQps(st.qps_5m), "rolling window"],
      ["Avg latency", fmtMs(st.avg_latency_ms), "from query log"],
      ["Cache hits", st.cache_hits ?? 0, `${hitRate} hit rate`],
      ["Cache misses", st.cache_misses ?? 0, "resolver path"],
      ["Blocked", st.blocks ?? st.blocked ?? 0, "NXDOMAIN policy"],
      ["Rate limits", st.rate_limits ?? 0, "threat guard"],
      ["Errors", st.errors ?? 0, `${errPct}% SERVFAIL`],
      ["Cache entries", fd.cache?.size ?? fd.cache_entries ?? br.cache_entries ?? 0, "in-memory TTL"],
      ["Blocklist", fd.blocklists?.domains ?? fd.blocklist_domains ?? br.blocklist_domains ?? 0, "domains"],
      ["Internet slots", fd.internet_slots ?? br.internet_slots ?? 0, "WHOLE field"],
      ["Recognized", fd.internet_recognized ?? br.internet_recognized ?? 0, `${fd.internet_coverage_pct ?? 0}% coverage`],
      ["RFC enforced", `${br.rfc_enforced ?? 0}/${br.rfc_total ?? fd.rfc_matrix?.length ?? 0}`, ""],
      ["Root hints", br.root_servers ?? fd.root_servers?.length ?? 0, "IANA"],
      ["Multipoint", br.multipoint_points ?? 0, "trusted IDs"],
      ["Foreign blocked", br.foreign_blocked ?? 0, `${br.foreign_ipv6_blocked ?? 0} IPv6`],
    ];
    el.innerHTML = items.map(([k, v, sub]) => `<div class="dns-ops-card">
      <span class="dns-ops-label">${esc(k)}</span>
      <strong class="dns-ops-value">${esc(String(v))}</strong>
      ${sub ? `<em class="dns-ops-sub">${esc(sub)}</em>` : ""}
    </div>`).join("");
  }

  function renderRealityModel(fd) {
    const el = $("dns-reality-model");
    if (!el) return;
    const inf = fd.internet_field || {};
    const model = inf.model || {};
    const total = inf.total_slots || 1;
    const rec = inf.recognized_slots || 0;
    const silent = inf.silent_slots ?? total - rec;
    const pct = inf.coverage_pct ?? Math.round((rec / total) * 100);
    el.innerHTML = `<div class="dns-reality-grid">
      <div class="dns-model-col dns-model-col--whole">
        <strong>WHOLE</strong>
        <p class="meta">${esc(model.whole || "Every TLD slot in field storage — passive everywhere at once.")}</p>
        <div class="dns-model-stat"><span>Slots</span><strong>${esc(String(total))}</strong></div>
      </div>
      <div class="dns-model-col dns-model-col--now">
        <strong>LOCAL NOW</strong>
        <p class="meta">${esc(model.local_now || "Resolver cache + trace probes mark recognized strength.")}</p>
        <div class="dns-model-stat"><span>Live</span><strong>${esc(String(rec))}</strong> <span class="meta">/ ${esc(String(silent))} silent</span></div>
      </div>
    </div>
    <div class="dns-coverage-bar" aria-label="Internet field coverage">
      <div class="dns-coverage-fill" style="width:${clamp(pct, 0, 100)}%"></div>
    </div>
    <div class="dns-coverage-label"><span>Coverage</span><strong>${esc(String(pct))}%</strong> · linear time placement — full timeline in field JSONL</div>`;
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function renderInternetField(fd) {
    const el = $("dns-internet-field");
    if (!el) return;
    const inf = fd.internet_field || {};
    const filter = ($("dns-internet-filter")?.value || "").trim().toLowerCase();
    let entries = inf.entries || [];
    if (filter) {
      entries = entries.filter((e) =>
        String(e.tld || "").toLowerCase().includes(filter)
        || String(e.domain || "").toLowerCase().includes(filter)
        || String(e.source || "").toLowerCase().includes(filter));
    }
    if (!entries.length && !(inf.entries || []).length) {
      el.innerHTML = '<div class="empty">Internet field — click Refresh DNS field to pull TLD registry…</div>';
      return;
    }
    if (!entries.length) {
      el.innerHTML = '<div class="empty">No slots match filter.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table dns-internet-table"><thead><tr>
      <th>TLD</th><th>Apex / domain</th><th>Strength</th><th>Answers</th><th>Source</th><th>Status</th>
    </tr></thead><tbody>${entries.map((e) => `<tr class="${e.recognized ? "dns-row-live" : "dns-row-silent"}">
      <td><code>.${esc(e.tld || "—")}</code></td>
      <td>${esc(e.domain || "—")}</td>
      <td><div class="dns-strength-cell"><span class="dns-strength-bar" style="width:${clamp(e.strength || 0, 0, 100)}%"></span><strong>${esc(String(e.strength ?? 0))}%</strong></div></td>
      <td class="meta">${(e.answers || []).slice(0, 2).map((a) => `<code>${esc(a)}</code>`).join(" ") || "—"}</td>
      <td class="meta">${esc(e.source || "—")}</td>
      <td>${e.recognized ? '<span class="dns-chip dns-chip-ok">recognized</span>' : '<span class="meta">silent</span>'}</td>
    </tr>`).join("")}</tbody></table>
    <div class="dns-table-foot meta">Showing ${entries.length} of ${(inf.entries || []).length} slots · TLDs ${inf.tld_count ?? "—"}</div>`;
  }

  function queryRowHtml(r) {
    const reason = r.reason || r.status || (r.blocked ? "blocked" : "");
    const chip = reason === "blocked" || reason === "block"
      ? '<span class="dns-chip dns-chip-warn">blocked</span>'
      : reason === "rate_limit"
        ? '<span class="dns-chip dns-chip-warn">rate limit</span>'
        : reason
          ? `<span class="meta">${esc(reason)}</span>`
          : '<span class="dns-chip dns-chip-ok">ok</span>';
    const key = `${r.ts || ""}:${r.qname || r.name || ""}`;
    return `<tr data-row-key="${esc(key)}">
      <td class="meta">${esc((r.ts || "").slice(11, 19) || "—")}</td>
      <td><strong>${esc(r.qname || r.name || "—")}</strong></td>
      <td class="meta">${(r.answers || []).map((a) => `<code>${esc(a)}</code>`).join(" ") || "—"}</td>
      <td class="meta">${fmtMs(r.latency_ms ?? r.latency)}</td>
      <td>${chip}</td>
    </tr>`;
  }

  function renderRecentQueries(fd) {
    const el = $("dns-recent-queries");
    if (!el) return;
    const rows = fd.recent_queries || [];
    if (!rows.length) {
      el.innerHTML = '<div class="empty">No queries yet — resolve a name against 127.0.0.1 to populate LOCAL NOW.</div>';
      return;
    }
    const ui = smooth();
    if (ui && !ui.isUserTyping(dnsViewRoot())) {
      if (!el.querySelector("table")) {
        el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
          <th>Time</th><th>QNAME</th><th>Answers</th><th>Latency</th><th>Status</th>
        </tr></thead><tbody></tbody></table>
        <div class="dns-table-foot meta" id="dns-recent-queries-foot"></div>`;
      }
      ui.patchTableRows(el, rows, (r) => `${r.ts || ""}:${r.qname || r.name || ""}`, queryRowHtml, { maxRows: 200 });
      const foot = $("dns-recent-queries-foot");
      if (foot) foot.textContent = `Showing ${rows.length} recent · schema ${fd.schema || "field-dns/v2"}`;
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Time</th><th>QNAME</th><th>Answers</th><th>Latency</th><th>Status</th>
    </tr></thead><tbody>${rows.map(queryRowHtml).join("")}</tbody></table>
    <div class="dns-table-foot meta">Showing ${rows.length} recent · schema ${esc(fd.schema || "field-dns/v2")}</div>`;
  }

  function renderTopDomains(fd) {
    const el = $("dns-top-domains");
    if (!el) return;
    const top = fd.top_domains || {};
    const entries = Object.entries(top).sort((a, b) => b[1] - a[1]).slice(0, 25);
    if (!entries.length) {
      el.innerHTML = '<div class="empty">No domain volume yet — queries populate top_domains from JSONL.</div>';
      return;
    }
    const max = entries[0][1] || 1;
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Domain</th><th>Queries</th><th>Share</th>
    </tr></thead><tbody>${entries.map(([dom, cnt]) => {
      const pct = Math.round((cnt / max) * 100);
      return `<tr>
        <td><strong>${esc(dom)}</strong></td>
        <td>${esc(String(cnt))}</td>
        <td><div class="dns-strength-cell"><span class="dns-strength-bar" style="width:${pct}%"></span></div></td>
      </tr>`;
    }).join("")}</tbody></table>`;
  }

  function renderThreatsLog(fd) {
    const el = $("dns-threats-log");
    if (!el) return;
    const dnsThreats = fd.threats || [];
    const dhcpThreats = (fd.servers?.dhcp?.threats || fd.dhcp_server?.threats || []).map((t) => ({
      ...t,
      type: t.type || "dhcp_reject",
    }));
    const rows = [...dnsThreats, ...dhcpThreats].slice(0, 50);
    if (!rows.length) {
      el.innerHTML = '<div class="meta">No threat events — rate limits, blocks, and poison anomalies log here.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Time</th><th>Type</th><th>Target</th><th>Count</th><th>Detail</th>
    </tr></thead><tbody>${rows.map((t) => `<tr>
      <td class="meta">${esc((t.last || t.ts || "").slice(11, 19) || "—")}</td>
      <td><span class="dns-chip dns-chip-warn">${esc(t.type || t.action || "threat")}</span></td>
      <td class="meta">${esc(t.client || t.ip || t.mac || "—")}</td>
      <td>${esc(String(t.count ?? "—"))}</td>
      <td class="meta">${esc(t.reason || t.detail || "—")}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderDhcpLeases(fd) {
    const el = $("dns-dhcp-leases");
    if (!el) return;
    const dhcp = fd.servers?.dhcp || fd.dhcp_server || {};
    const rows = fd.dhcp_leases_detailed || dhcp.leases_detailed || [];
    const ext = dhcp.stats_extended || {};
    if (!rows.length) {
      el.innerHTML = `<div class="meta">No active leases · pool ${esc(dhcp.pool?.start || "—")}–${esc(dhcp.pool?.end || "—")}</div>
        <div class="dns-ops-strip" style="margin-top:8px;">
          <div class="dns-ops-card"><span class="dns-ops-label">Discovers</span><strong>${esc(String(ext.discovers ?? 0))}</strong></div>
          <div class="dns-ops-card"><span class="dns-ops-label">Offers</span><strong>${esc(String(ext.offers ?? 0))}</strong></div>
          <div class="dns-ops-card"><span class="dns-ops-label">Acks</span><strong>${esc(String(ext.acks ?? 0))}</strong></div>
          <div class="dns-ops-card"><span class="dns-ops-label">Threat rejects</span><strong>${esc(String(ext.threat_rejects ?? 0))}</strong></div>
        </div>`;
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>MAC</th><th>IP</th><th>Expires</th><th>Remaining</th><th>Renewals</th><th>DNS</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><code>${esc(r.mac || "—")}</code></td>
      <td><code>${esc(r.ip || "—")}</code></td>
      <td class="meta">${esc((r.expires_at || "").slice(11, 19) || "—")}</td>
      <td>${esc(fmtRemaining(r.remaining_seconds))}</td>
      <td>${esc(String(r.renewals ?? 0))}</td>
      <td class="meta">${(r.dns || []).map((d) => `<code>${esc(d)}</code>`).join(" ") || "—"}</td>
    </tr>`).join("")}</tbody></table>
    <div class="dns-table-foot meta">${rows.length} leases · ${esc(String(ext.conflicts_detected ?? 0))} conflicts · ${esc(String(ext.threat_rejects ?? 0))} threat rejects</div>`;
  }

  function renderDhcpEvents(fd) {
    const el = $("dns-dhcp-events");
    if (!el) return;
    const rows = fd.dhcp_events || fd.servers?.dhcp?.lease_history_events || fd.dhcp_server?.lease_history_events || [];
    if (!rows.length) {
      el.innerHTML = '<div class="meta">No DHCP events yet — discover/offer/ack/reject log to JSONL.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Time</th><th>Event</th><th>MAC</th><th>IP</th><th>Reason</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td class="meta">${esc((r.ts || "").slice(11, 19) || "—")}</td>
      <td><span class="dns-chip dns-chip-meta">${esc(r.event || r.type || "—")}</span></td>
      <td><code>${esc(r.mac || "—")}</code></td>
      <td><code>${esc(r.ip || "—")}</code></td>
      <td class="meta">${esc(r.reason || "—")}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function phaseChip(phase) {
    const p = String(phase || "observing").toLowerCase();
    const cls = p === "primary" ? "dns-chip-ok" : p === "ready" ? "dns-chip-meta" : "dns-chip-warn";
    return `<span class="dns-chip ${cls}">${esc(p)}</span>`;
  }

  function renderDnsServer(fd) {
    const el = $("dns-server-panel");
    if (!el) return;
    const srv = fd.servers || {};
    const dns = srv.dns || {};
    const dhcp = srv.dhcp || fd.dhcp_server || {};
    const h7 = fd.hostess7_service || {};
    const inside = h7.inside || {};
    const outside = h7.outside || {};
    const listeners = (dns.listeners || fd.listeners || []).map((l) => `<code>${esc(l)}</code>`).join(" ");
    const to = fd.takeover || {};
    const phase = to.phase || "observing";
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Service</th><th>Status</th><th>Bind</th><th>Planetary detail</th>
    </tr></thead><tbody>
      <tr>
        <td><strong>Truth DNS</strong></td>
        <td>${dns.running || fd.running ? '<span class="dns-chip dns-chip-ok">LIVE</span>' : '<span class="dns-chip dns-chip-warn">DOWN</span>'}</td>
        <td>${listeners || `<code>127.0.0.1:${esc(String(dns.port || 53))}</code>`}</td>
        <td class="meta">PID ${esc(String(dns.pid || fd.pid || "—"))} · ${esc(fd.planetary_security_level || "—")} · trace-only · ${phaseChip(phase)}</td>
      </tr>
      <tr>
        <td><strong>Field DHCP</strong></td>
        <td>${dhcp.running ? '<span class="dns-chip dns-chip-ok">LIVE</span>' : dhcp.may_serve === false ? '<span class="dns-chip dns-chip-warn">OBSERVING</span>' : '<span class="dns-chip dns-chip-meta">IDLE</span>'}</td>
        <td><code>${esc(dhcp.bind || "0.0.0.0:67")}</code></td>
        <td class="meta">${esc(String(dhcp.lease_count ?? 0))} leases · DNS v4 ${(dhcp.dns_option || ["127.0.0.1"]).map((d) => `<code>${esc(d)}</code>`).join(" ")} · v6 ${(dhcp.dns_option_v6 || ["::1"]).map((d) => `<code>${esc(d)}</code>`).join(" ")}</td>
      </tr>
    </tbody></table>
    <dl class="dns-kv-grid" style="margin-top:12px;">
      <dt>Hostess 7 inside</dt><dd class="meta">${esc(inside.dns || "—")} · ${esc(inside.dhcp || "—")} · ${esc(inside.movement || "none")}</dd>
      <dt>Hostess 7 outside</dt><dd class="meta">${esc(outside.dns_admin || "—")} · ${esc(outside.dhcp || "—")} · ${esc(outside.movement || "none")}</dd>
      <dt>Takeover</dt><dd class="meta">${esc(to.motto || "Listen first — never interrupt on arrival.")}</dd>
    </dl>`;
  }

  function renderTakeover(fd) {
    const el = $("dns-takeover-panel");
    if (!el) return;
    const to = fd.takeover || {};
    const inc = to.incumbents || {};
    const perm = to.permissions || {};
    const health = to.health || {};
    if (!to.phase) {
      el.innerHTML = '<div class="meta">Takeover state builds on next DNS field refresh.</div>';
      return;
    }
    el.innerHTML = `<dl class="dns-kv-grid">
      <dt>Phase</dt><dd>${phaseChip(to.phase)} · streak ${esc(String(to.healthy_streak ?? 0))}</dd>
      <dt>Resolver health</dt><dd>${health.healthy ? '<span class="dns-chip dns-chip-ok">healthy</span>' : '<span class="dns-chip dns-chip-warn">warming</span>'} · probe ${health.probe_ok ? "ok" : "pending"}</dd>
      <dt>Incumbent DNS</dt><dd>${inc.incumbent_dns ? '<span class="dns-chip dns-chip-warn">present</span>' : '<span class="dns-chip dns-chip-ok">vacant</span>'} ${inc.systemd_resolved ? "· systemd-resolved" : ""}</dd>
      <dt>Incumbent DHCP</dt><dd>${inc.incumbent_dhcp ? '<span class="dns-chip dns-chip-warn">port 67 busy</span>' : '<span class="dns-chip dns-chip-ok">vacant</span>'}</dd>
      <dt>Permissions</dt><dd>resolv ${perm.enforce_resolv ? "✓" : "—"} · DHCP ${perm.serve_dhcp ? "✓" : "—"} · capture ${perm.local_capture ? "✓" : "—"}</dd>
      <dt>Policy</dt><dd class="meta">${esc(to.motto || "Listen first — never interrupt on arrival.")}</dd>
    </dl>`;
  }

  function renderEgress(fd) {
    const el = $("dns-egress-panel");
    if (!el) return;
    const eg = fd.egress_integrity || {};
    const st = eg.stats || {};
    const rows = (eg.recent || []).slice(0, 12);
    el.innerHTML = `<div class="dns-ops-strip" style="margin-bottom:10px;">
      <div class="dns-ops-card"><span class="dns-ops-label">Checks</span><strong>${esc(String(st.total_checks ?? 0))}</strong></div>
      <div class="dns-ops-card"><span class="dns-ops-label">Exact match</span><strong>${esc(String(st.verified_exact ?? 0))}</strong></div>
      <div class="dns-ops-card"><span class="dns-ops-label">Mismatches</span><strong>${esc(String(st.mismatches ?? 0))}</strong></div>
      <div class="dns-ops-card"><span class="dns-ops-label">Healthy</span><strong>${eg.healthy !== false ? "yes" : "NO"}</strong></div>
    </div>
    <p class="meta">${esc(eg.motto || "Allowed egress verified — payload hash match.")}</p>
    ${rows.length ? `<table class="honor-table dns-table"><thead><tr><th>Time</th><th>Kind</th><th>Exact</th><th>Dest</th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td class="meta">${esc((r.ts || "").slice(11, 19))}</td><td>${esc(r.kind)}</td><td>${r.exact_match ? '<span class="dns-chip dns-chip-ok">yes</span>' : '<span class="dns-chip dns-chip-warn">no</span>'}</td><td class="meta">${esc(r.dest || "—")}</td></tr>`).join("")}
    </tbody></table>` : '<div class="meta">No integrity checks yet — resolver activity will populate.</div>'}`;
  }

  function renderThreatGuard(fd) {
    const el = $("dns-threat-panel");
    if (!el) return;
    const tg = fd.threat_guard || {};
    const st = tg.stats || {};
    const blocks = (tg.permanent_blocks || []).slice(0, 8);
    el.innerHTML = `<dl class="dns-kv-grid">
      <dt>Policy</dt><dd class="meta">${esc(tg.motto || "Listen before reject · permanent eradication.")}</dd>
      <dt>Permanent blocks</dt><dd><strong>${esc(String(st.permanent_blocks ?? 0))}</strong></dd>
      <dt>Max QPS / client</dt><dd><code>${esc(String(tg.policy?.max_qps_per_client ?? "30"))}</code></dd>
      <dt>No lateral movement</dt><dd>${tg.policy?.no_lateral_movement ? '<span class="dns-chip dns-chip-ok">enforced</span>' : "—"}</dd>
    </dl>
    ${blocks.length ? `<table class="honor-table dns-table"><thead><tr><th>Client</th><th>Vector</th><th>Reason</th></tr></thead><tbody>
      ${blocks.map((b) => `<tr><td><code>${esc(b.client)}</code></td><td>${esc(b.vector)}</td><td class="meta">${esc(b.reason)}</td></tr>`).join("")}
    </tbody></table>` : '<div class="meta">No permanent blocks — threats eradicated on first strike.</div>'}`;
  }

  function renderMultipoint(fd) {
    const el = $("dns-multipoint-panel");
    if (!el) return;
    const mp = fd.multipoint_identity || {};
    const points = fd.identification_points || mp.identification_points || [];
    const untrusted = mp.untrusted_never_added || [];
    if (!points.length) {
      el.innerHTML = '<div class="empty">Multipoint identity builds when resolver is running.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>ID</th><th>Listener</th><th>Role</th><th>Family</th><th>RFC</th><th>Fingerprint</th>
    </tr></thead><tbody>${points.map((p) => `<tr>
      <td><strong>${esc(p.id)}</strong></td>
      <td><code>${esc(p.listener || p.address)}</code></td>
      <td>${esc(p.role)}</td>
      <td>${esc(p.family || "—")}</td>
      <td class="meta">${esc(p.rfc || "—")}</td>
      <td class="meta"><code title="${esc(p.secure_fingerprint || "")}">${esc(String(p.secure_fingerprint || "").slice(0, 20))}…</code></td>
    </tr>`).join("")}</tbody></table>
    <p class="meta dns-mp-foot">Never added: ${untrusted.map((u) => `<code>${esc(u)}</code>`).join(" ")}</p>`;
  }

  function renderRfcTable(fd) {
    const el = $("dns-rfc-table");
    if (!el) return;
    const q = ($("dns-rfc-search")?.value || "").trim().toLowerCase();
    let rows = fd.rfc_matrix || [];
    if (q) {
      rows = rows.filter((r) =>
        JSON.stringify(r).toLowerCase().includes(q));
    }
    if (!rows.length) {
      el.innerHTML = q
        ? '<div class="empty">No RFC rows match search.</div>'
        : '<div class="meta">RFC matrix — click Refresh DNS field to rebuild from seed.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>RFC</th><th>Title</th><th>§</th><th>Requirement</th><th>Status</th><th>NEXUS control</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>${esc(r.rfc)}</strong></td>
      <td>${esc(r.title)}</td>
      <td><code>${esc(r.section)}</code></td>
      <td>${esc(r.requirement)}</td>
      <td>${complianceChip(r.compliance)}</td>
      <td class="meta">${esc(r.nexus_control)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderLegalTable(fd) {
    const el = $("dns-legal-table");
    if (!el) return;
    const rows = fd.legal_framework || [];
    if (!rows.length) {
      el.innerHTML = '<div class="meta">Legal framework — click Refresh DNS field to rebuild from seed.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Citation</th><th>Instrument</th><th>Requirement</th><th>NEXUS application</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>${esc(r.citation)}</strong></td>
      <td>${esc(r.title)}</td>
      <td>${esc(r.requirement)}</td>
      <td class="meta">${esc(r.nexus_application)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderRootServers(fd) {
    const el = $("dns-root-table");
    if (!el) return;
    const rows = fd.root_servers || [];
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Root</th><th>Hostname</th><th>IPv4</th><th>IPv6</th><th>Operator</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>.${esc(r.letter)}</strong></td>
      <td>${esc(r.hostname)}</td>
      <td><code>${esc(r.ipv4)}</code></td>
      <td><code>${esc(r.ipv6)}</code></td>
      <td>${esc(r.operator)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderPlanetary(fd) {
    const el = $("dns-planetary-table");
    if (!el) return;
    const zones = fd.zones || [];
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Region</th><th>TLD group</th><th>Security</th><th>RFC</th><th>Legal</th><th>Note</th>
    </tr></thead><tbody>${zones.map((z) => `<tr>
      <td><strong>${esc(z.region)}</strong></td>
      <td><code>${esc(z.tld_group)}</code></td>
      <td>${z.security_level === "extreme" ? '<span class="honor-extreme-chip">EXTREME</span>' : esc(z.security_level)}</td>
      <td><code>${esc(z.rfc || "—")}</code></td>
      <td>${esc(z.legal || "—")}</td>
      <td class="meta">${esc(z.note)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderLegacy(fd) {
    const el = $("dns-legacy-table");
    if (!el) return;
    const rows = fd.legacy_dns_equipment || [];
    if (!rows.length) {
      el.innerHTML = '<div class="meta">Legacy gear interop — see dns-admin-seed.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Vendor</th><th>Era</th><th>Role</th><th>RFC</th><th>Interop</th><th>Notes</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>${esc(r.vendor)}</strong></td>
      <td>${esc(r.era)}</td>
      <td>${esc(r.role)}</td>
      <td><code>${esc(r.rfc)}</code></td>
      <td>${esc(r.interop)}</td>
      <td class="meta">${esc(r.notes)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderForeignBlocked(fd) {
    const el = $("dns-foreign-blocked");
    if (!el) return;
    const rows = fd.planetary?.foreign_resolvers_blocked
      || fd.foreign_resolvers_blocked
      || (fd.planetary?.foreign_resolver_ipv4 || fd.foreign_resolver_ipv4 || []).map((ip) => ({
        name: "Foreign resolver",
        ipv4: [ip],
        ipv6: [],
        reason: "Blocked under planetary policy",
      }));
    if (!rows.length) {
      el.innerHTML = '<div class="meta">No foreign resolver list.</div>';
      return;
    }
    el.innerHTML = `<table class="honor-table dns-table"><thead><tr>
      <th>Resolver</th><th>IPv4</th><th>IPv6</th><th>Reason</th>
    </tr></thead><tbody>${rows.map((r) => `<tr>
      <td><strong>${esc(r.name)}</strong></td>
      <td><code>${(r.ipv4 || []).join(", ") || "—"}</code></td>
      <td><code>${(r.ipv6 || []).join(", ") || "—"}</code></td>
      <td class="meta">${esc(r.reason)}</td>
    </tr>`).join("")}</tbody></table>`;
  }

  function renderDnsAdminPortal(fd, panel) {
    const el = $("dns-admin-portal-info");
    if (!el) return;
    const br = fd.engineer_briefing || {};
    const ports = br.admin_ports || [7, 77, 777];
    const mnemonic = br.port_mnemonic || {};
    const host = location.hostname || "127.0.0.1";
    const portLinks = ports.map((p) => {
      const hint = mnemonic[String(p)] || String(p);
      return `<a class="dns-admin-port-link" href="http://${host}:${p}/" target="_blank" rel="noopener" title="${esc(hint)}">:${esc(p)}</a>`;
    }).join("");
    const dap = fd.dns_admin_portal || panel?.dns_admin_portal;
    el.innerHTML = `<div class="dns-admin-engineer-grid">
      <div>
        <span class="dns-chip dns-chip-ok">information only</span>
        <span class="dns-chip dns-chip-warn">remote control blocked</span>
        <p class="dns-admin-lead">Tired engineer ports: ${portLinks}</p>
        <p class="meta">Passkey can be the port number (7, 77, 777) or mnemonic from welcome. Equipment room MDF/IDF reporting on by default.</p>
      </div>
      <div class="dns-admin-quick">
        <strong>Quick login</strong>
        <ul class="dns-admin-users">
          <li><code>engineer</code> / <code>77</code> on port 77</li>
          <li><code>hostess</code> / <code>lucky7</code> on any port</li>
          <li><code>field</code> / <code>777</code> on port 777</li>
        </ul>
        ${dap?.running ? `<span class="dns-chip dns-chip-ok">admin portal live</span> <span class="meta">ports ${(dap.live_ports || dap.ports || []).map((p) => `<code>:${esc(String(p))}</code>`).join(" ")}</span>` : '<span class="dns-chip dns-chip-meta">portal starts with daemon</span>'}
      </div>
    </div>`;
  }

  function renderDnsStats(fd) {
    const el = $("dns-stats");
    if (!el) return;
    const st = fd.stats || {};
    const dnssec = fd.dnssec || {};
    const tp = fd.traffic_patterns || {};
    const dnsTp = tp.dns || {};
    const qps60 = st.qps_60s ?? dnsTp.qps_60s ?? 0;
    const qps5 = st.qps_5m ?? dnsTp.qps_5m ?? 0;
    const lat = st.avg_latency_ms ?? dnsTp.avg_latency_ms ?? 0;
    const dnssecOn = dnssec.enabled === true;
    const dnssecCls = dnssecOn ? "dns-ok" : "dns-warn";
    const egressOk = tp.egress_integrity_ok !== false;
    el.innerHTML = [
      `<div class="dns-stat"><span class="meta">QPS 60s</span><strong>${esc(fmtQps(qps60))}</strong></div>`,
      `<div class="dns-stat"><span class="meta">QPS 5m</span><strong>${esc(fmtQps(qps5))}</strong></div>`,
      `<div class="dns-stat"><span class="meta">Avg latency</span><strong>${esc(fmtMs(lat))}</strong></div>`,
      `<div class="dns-stat"><span class="meta">DNSSEC</span><strong class="${dnssecCls}">${dnssecOn ? "enabled" : "stub"}</strong> <span class="meta">${esc(String(dnssec.validations ?? 0))} ok · ${esc(String(dnssec.failures ?? 0))} fail</span></div>`,
      `<div class="dns-stat"><span class="meta">DHCP leases</span><strong>${esc(String(tp.dhcp_lease_count ?? fd.servers?.dhcp?.lease_count ?? 0))}</strong></div>`,
      `<div class="dns-stat"><span class="meta">Egress integrity</span><strong class="${egressOk ? "dns-ok" : "dns-warn"}">${egressOk ? "ok" : "check"}</strong></div>`,
      `<div class="dns-stat dns-stat--spark" aria-hidden="true" title="QPS sparkline placeholder"><span class="meta">QPS trend</span><div class="dns-sparkline" style="width:100%;height:18px;background:linear-gradient(90deg, rgba(77,232,138,0.15) ${clamp(Math.round(qps60 * 8), 4, 100)}%, transparent 0)"></div></div>`,
    ].join("");
  }

  function renderDnsFieldLight(fd) {
    if (!fd) return;
    lastFd = fd;
    renderDnsStats(fd);
    renderOpsStrip(fd);
    renderTrafficPatterns(fd);
    renderRecentQueries(fd);
    renderTopDomains(fd);
    renderThreatsLog(fd);
    renderDhcpLeases(fd);
    renderDhcpEvents(fd);
  }

  function renderDnsField(fd, panel) {
    if (!fd) return;
    const fp = dnsFingerprint(fd);
    const ui = smooth();
    if (ui && ui.isUserTyping(dnsViewRoot()) && fp === lastDnsFp) return;
    if (fp === lastDnsFp) {
      renderDnsFieldLight(fd);
      return;
    }
    lastDnsFp = fp;
    lastFd = fd;
    bindRefTabs();
    bindFilters();
    renderDnsHero(fd);
    renderPostureStrip(fd);
    renderAlerts(fd);
    renderThreatPosture(fd);
    renderTrafficPatterns(fd);
    renderDnsServer(fd);
    renderThreatModel(fd);
    renderOpsStrip(fd);
    renderEngineerBriefing(fd);
    renderOperationsDetail(fd);
    renderRealityModel(fd);
    renderInternetField(fd);
    renderRecentQueries(fd);
    renderTopDomains(fd);
    renderForeignBlocked(fd);
    renderRfcTable(fd);
    renderLegalTable(fd);
    renderRootServers(fd);
    renderPlanetary(fd);
    renderLegacy(fd);
    renderDnsAdminPortal(fd, panel);
    renderDnsStats(fd);
  }

  global.renderDnsField = renderDnsField;
  global.renderDnsFieldLight = renderDnsFieldLight;
})(window);