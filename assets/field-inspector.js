/**
 * NEXUS Field Clarity — v9.1 inspector (score/geo/dns/antenna + panel slices).
 * Live values from window.lastPanelData; state under /var/lib/nexus-shield/.
 */
(function (global) {
  "use strict";

  const VERSION = "v9.1";
  const STATE_HINT = "/var/lib/nexus-shield/field-state";

  const PANEL_SLICES = [
    "field_command", "gatekeeper", "lethal_enforcement", "hostess7_lethal_insight",
    "hostess7_command", "us_field", "packet_field", "home_protector", "local_services",
    "host_attacks", "terror_spiderweb", "precision_field", "angel_dossiers", "human_dossier",
    "angel_research", "browser_awareness", "audio_train", "field_rf", "signals_field",
    "field_hardware", "field_hazard_onset", "field_antenna", "field_radio", "field_dns",
    "field_outside_talk", "field_drive", "h7_library", "field_brain", "settings",
    "police_agency", "human_registry", "gov_intel", "program_tags", "census_field",
    "existence_identity", "operator_location",
  ];

  const ALL_FIELDS = {
    scoreAxes: [
      "user_intent", "bandwidth_abuse", "beacon_pattern", "entropy", "shadow_integrity",
      "behavior_chain", "geo_risk", "asn_abuse", "mac_oui", "packet_dpi",
    ],
    monitorAxes: [
      "user_browser", "media_stream", "search_ephemeral", "bandwidth_abuse", "stream_theft_risk",
      "beacon_pattern", "process_trust", "destination_class", "threat_linked", "operator_auth",
    ],
    verdicts: ["USER_OK", "EPHEMERAL", "SUSPICIOUS", "HARM_CANDIDATE", "MONITOR"],
    dnsDhcp: [
      "FIELD_DNS_PORT", "FIELD_DNS_BINDS_IPV4", "FIELD_DNS_BINDS_IPV6", "FIELD_DHCP",
      "NEXUS_FIELD_DNS_ENFORCE_RESOLV", "NEXUS_FIELD_DNS_IPV4", "NEXUS_FIELD_DNS_IPV6",
    ],
    config: [
      "NEXUS_ULTRA_STEALTH", "NEXUS_FIELD_ANTENNA", "NEXUS_HOME_PROTECTOR", "NEXUS_PARANOIA_MODE",
      "NEXUS_FIREWALL_TAKEOVER", "NEXUS_CONNECTION_GATEKEEPER", "NEXUS_PACKET_ORACLE",
      "NEXUS_SHADOW_WATCH", "NEXUS_ENTROPY_WATCH", "NEXUS_BEHAVIOR_WATCH",
    ],
    intel: ["geo", "asn", "registrar", "abuse", "mac_oui", "ptr", "cve"],
    panelSlices: PANEL_SLICES,
  };

  const GLOSSARY = {
    user_intent: "Human vs machine behavior | v9.1 neural on-the-fly",
    user_browser: "Looks like a normal web browser session.",
    media_stream: "Looks like video or music streaming.",
    bandwidth_abuse: "Heavy data movement — innocent updates or bandwidth hog.",
    beacon_pattern: "Repeated check-ins — common in apps, occasionally spyware.",
    entropy: "Shannon entropy spike — packed or encrypted payloads.",
    shadow_integrity: "File tamper watch — shadow hash drift in state dir.",
    behavior_chain: "Parent/child process chain depth from behavior symphony.",
    geo_risk: "Geographic risk from egress geo-intel.",
    asn_abuse: "ASN reputation from abuse registries.",
    mac_oui: "OUI vendor fingerprint on LAN/Wi‑Fi paths.",
    packet_dpi: "Deep packet inspection segment verdict.",
    FIELD_DNS_PORT: "Planetary resolver port — binds loopback only.",
    FIELD_DNS_BINDS_IPV4: "IPv4 bind hosts (127.0.0.1; not 127.0.0.53).",
    FIELD_DHCP: "LAN DHCP pool — DNS option points to field resolver.",
    NEXUS_FIELD_DNS_ENFORCE_RESOLV: "resolv.conf truth enforcement cycle.",
    NEXUS_FIELD_ANTENNA: "RF/SDR sentinel — 93.1 MHz catch + tri-angulation.",
    NEXUS_ULTRA_STEALTH: "cgroup + adaptive pacing stealth envelope.",
    NEXUS_HOME_PROTECTOR: "Home perimeter hardening module.",
    NEXUS_FIREWALL_TAKEOVER: "nftables takeover — block hostile egress.",
    USER_OK: "Trusted forever stored in nexus-trusted.jsonl",
    HARM_CANDIDATE: "1-click block + hostile.jsonl append",
    EPHEMERAL: "Short-lived CDN tab — dies and returns.",
    SUSPICIOUS: "Harm and trust scores diverge.",
    MONITOR: "Routine egress — permitted at zero nft cost.",
    field_dns: "Truth DNS & DHCP tab — planetary resolver takeover.",
    field_antenna: "RF catch + tri-receive orchestrator.",
    gatekeeper: "Live connection scoring — connection-intent.json",
    packet_field: "tcpdump TX/RX archive + inspect pane.",
    signals_field: "Pulse channels + antenna menu.",
    field_outside_talk: "Outside tools + planet shield egress.",
  };

  const SLICE_JUMP = {
    field_command: "command/command",
    gatekeeper: "packets/monitor",
    lethal_enforcement: "command/command",
    hostess7_command: "command/command",
    packet_field: "packets/inspect",
    field_dns: "dns/dns",
    field_antenna: "signals/signals",
    signals_field: "signals/signals",
    field_radio: "signals/signals",
    field_hardware: "signals/signals",
    field_outside_talk: "outside/outside",
    field_drive: "outside/outside",
    home_protector: "threats/home-protector",
    local_services: "threats/local-holes",
    host_attacks: "threats/host-attack",
    terror_spiderweb: "threats/spiderweb",
    precision_field: "threats/precision-map",
    settings: "system/settings",
    h7_library: "library/library",
    field_brain: "library/library",
    browser_awareness: "intel/honor",
    human_registry: "intel/people",
    audio_train: "intel/audio-train",
    field_rf: "intel/field-rf",
    angel_research: "intel/research",
    angel_dossiers: "threats/dossier",
    human_dossier: "threats/human-dossier",
    us_field: "us/us",
    operator_location: "command/command",
    census_field: "intel/people",
    existence_identity: "intel/people",
  };

  const STATE_FILES = {
    gatekeeper: "connection-intent.json",
    field_dns: "field-dns-panel.json",
    packet_field: "packet-field.json",
    host_attacks: "host-attacks.json",
    settings: "nexus-settings.json",
  };

  let mounted = false;
  let filterTimer = null;
  let activeField = null;
  let lastQuery = "";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  function panelData() {
    return global.lastPanelData || global.NEXUS_FIELD || null;
  }

  function firstConnection(data) {
    const gk = data?.gatekeeper || {};
    return (gk.connections && gk.connections[0]) || (data?.internet?.connections && data.internet.connections[0]) || null;
  }

  function formatLive(val) {
    if (val == null || val === "") return "—";
    if (typeof val === "boolean") return val ? "on" : "off";
    if (typeof val === "number") return String(val);
    if (Array.isArray(val)) {
      if (!val.length) return "[]";
      return val.length > 3 ? `${val.slice(0, 2).join(", ")}… (${val.length})` : val.join(", ");
    }
    if (typeof val === "object") {
      if (val.updated) return val.updated;
      if (val.schema) return val.schema;
      const keys = Object.keys(val);
      return keys.length ? `{${keys.slice(0, 3).join(", ")}${keys.length > 3 ? "…" : ""}}` : "{}";
    }
    const s = String(val);
    return s.length > 48 ? `${s.slice(0, 45)}…` : s;
  }

  function sliceReady(data, key) {
    if (!data || data[key] == null) return false;
    const val = data[key];
    if (key === "gatekeeper") return typeof val === "object" && Array.isArray(val.connections);
    if (typeof val === "object" && !Array.isArray(val)) return Object.keys(val).length > 0 || val.updated != null;
    return Boolean(val);
  }

  function resolveLive(field, data) {
    if (!data) return null;

    if (data.settings && Object.prototype.hasOwnProperty.call(data.settings, field)) {
      return data.settings[field];
    }

    const fd = data.field_dns || {};
    const resolv = fd.resolv || fd.planetary?.resolv || {};
    const dhcp = fd.dhcp || {};
    const dnsMap = {
      FIELD_DNS_PORT: fd.ipv4?.port ?? fd.stats?.port ?? 53,
      FIELD_DNS_BINDS_IPV4: fd.ipv4?.host ?? (fd.listeners || [])[0],
      FIELD_DNS_BINDS_IPV6: fd.ipv6?.host ?? (fd.listeners || [])[1],
      FIELD_DHCP: dhcp.running ? `running · ${dhcp.lease_count ?? 0} leases` : "off",
      NEXUS_FIELD_DNS_ENFORCE_RESOLV: resolv.nexus_truth_enforced ?? resolv.ipv4_truth_enforced,
      NEXUS_FIELD_DNS_IPV4: fd.ipv4?.host,
      NEXUS_FIELD_DNS_IPV6: fd.ipv6?.host,
    };
    if (Object.prototype.hasOwnProperty.call(dnsMap, field) && dnsMap[field] != null) {
      return dnsMap[field];
    }

    if (ALL_FIELDS.verdicts.includes(field)) {
      const rows = data.gatekeeper?.connections || data.internet?.connections || [];
      return rows.filter((c) => c.verdict === field).length;
    }

    const conn = firstConnection(data);
    if (conn?.scores && Object.prototype.hasOwnProperty.call(conn.scores, field)) {
      return `${conn.scores[field]}/10`;
    }

    if (ALL_FIELDS.intel.includes(field)) {
      const intel = data.vector_intel || conn?.intel || conn?.vector_intel || {};
      if (intel[field] != null) return intel[field];
      if (field === "geo" && (conn?.geo || intel.geo_country)) return conn?.geo || intel.geo_country;
      if (field === "asn" && (conn?.asn || intel.asn)) return conn?.asn || intel.asn;
    }

    if (PANEL_SLICES.includes(field)) {
      if (!sliceReady(data, field)) return null;
      const doc = data[field];
      if (typeof doc === "object" && doc && !Array.isArray(doc)) {
        if (doc.updated) return doc.updated;
        if (field === "gatekeeper") return `${(doc.connections || []).length} conn`;
        if (field === "field_dns") return doc.running ? "resolver on" : "resolver off";
        if (field === "field_antenna") return doc.readiness?.score != null ? `ready ${doc.readiness.score}%` : "loaded";
      }
      return "loaded";
    }

    if (field.startsWith("NEXUS_")) {
      return global.NEXUS_FIELD?.settings?.[field] ?? null;
    }

    return null;
  }

  function liveClass(field, data) {
    const v = resolveLive(field, data);
    if (v == null || v === "—") return "missing";
    if (PANEL_SLICES.includes(field) && sliceReady(data, field)) return "ready";
    if (ALL_FIELDS.verdicts.includes(field) && Number(v) > 0) return "warn";
    return "";
  }

  function buildCatalog() {
    const rows = [];
    Object.entries(ALL_FIELDS).forEach(([cat, fields]) => {
      fields.forEach((f) => rows.push({ cat, field: f }));
    });
    return rows;
  }

  function renderFields() {
    const list = $("field-list");
    if (!list) return;
    const data = panelData();
    list.innerHTML = Object.entries(ALL_FIELDS).map(([cat, fields]) => {
      const rows = fields.map((f) => {
        const live = formatLive(resolveLive(f, data));
        const cls = liveClass(f, data);
        return `<div class="field-row" data-field="${esc(f)}" data-cat="${esc(cat)}">
          <span class="field-name">${esc(f)}</span>
          <span class="field-live ${cls}">${esc(live)}</span>
        </div>`;
      }).join("");
      return `<details open data-cat-block="${esc(cat)}">
        <summary>${esc(cat)} (${fields.length})</summary>
        ${rows}
      </details>`;
    }).join("");

    list.querySelectorAll(".field-row").forEach((row) => {
      row.addEventListener("click", () => explain(row.dataset.field));
    });
    applyFilter(lastQuery);
  }

  function rowMatches(field, cat, q, data) {
    if (!q) return true;
    const live = formatLive(resolveLive(field, data)).toLowerCase();
    const tip = (GLOSSARY[field] || "").toLowerCase();
    const blob = `${field} ${cat} ${live} ${tip}`.toLowerCase();
    return blob.includes(q);
  }

  function applyFilter(q) {
    lastQuery = q;
    const query = (q || "").trim().toLowerCase();
    const data = panelData();
    const list = $("field-list");
    if (!list) return;

    list.querySelectorAll(".field-row").forEach((row) => {
      const match = rowMatches(row.dataset.field, row.dataset.cat, query, data);
      row.classList.toggle("hidden", !match);
    });

    list.querySelectorAll("details[data-cat-block]").forEach((det) => {
      const visible = det.querySelectorAll(".field-row:not(.hidden)").length;
      det.style.display = query && visible === 0 ? "none" : "";
    });
  }

  function filterFields() {
    const q = $("field-search")?.value || "";
    clearTimeout(filterTimer);
    filterTimer = setTimeout(() => applyFilter(q), 90);
  }

  function explain(field) {
    activeField = field;
    const data = panelData();
    const live = resolveLive(field, data);
    const tip = GLOSSARY[field] || `Live value from ${STATE_HINT} + panel slice`;
    const stateFile = STATE_FILES[field];
    const stateLine = stateFile ? `${STATE_HINT.replace(/field-state$/, "")}${stateFile}` : STATE_HINT;
    const jump = SLICE_JUMP[field];

    document.querySelectorAll(".field-row").forEach((r) => {
      r.classList.toggle("active", r.dataset.field === field);
    });

    const box = $("field-explain");
    if (!box) return;
    box.classList.remove("hidden");
    box.innerHTML = `
      <div class="field-explain-title">${esc(field)}</div>
      <div class="field-explain-tip">${esc(tip)}</div>
      <div class="field-explain-value">Live: ${esc(formatLive(live))}</div>
      <div class="field-explain-value">State: ${esc(stateLine)}</div>
      <div class="field-explain-actions">
        ${jump ? `<button type="button" data-jump="${esc(jump)}">Open tab</button>` : ""}
        <button type="button" data-dismiss="1">Dismiss</button>
      </div>`;

    box.querySelector("[data-dismiss]")?.addEventListener("click", () => {
      box.classList.add("hidden");
      document.querySelectorAll(".field-row.active").forEach((r) => r.classList.remove("active"));
      activeField = null;
    });
    box.querySelector("[data-jump]")?.addEventListener("click", (ev) => {
      const route = ev.currentTarget.getAttribute("data-jump");
      if (route && typeof global.showView === "function") global.showView(route);
    });
  }

  function refreshLiveBadges() {
    const data = panelData();
    document.querySelectorAll(".field-row").forEach((row) => {
      const live = formatLive(resolveLive(row.dataset.field, data));
      const badge = row.querySelector(".field-live");
      if (!badge) return;
      badge.textContent = live;
      badge.className = `field-live ${liveClass(row.dataset.field, data)}`;
    });
    if (activeField) {
      const box = $("field-explain");
      const liveEl = box?.querySelector(".field-explain-value");
      if (liveEl && box && !box.classList.contains("hidden")) {
        liveEl.textContent = `Live: ${formatLive(resolveLive(activeField, data))}`;
      }
    }
    applyFilter(lastQuery);
  }

  function hookPaintPanel() {
    const orig = global.paintPanel;
    if (typeof orig !== "function" || orig.__fieldInspector) return;
    global.paintPanel = function fieldInspectorPaint(data) {
      const out = orig.apply(this, arguments);
      refreshLiveBadges();
      const ver = $("field-inspector-ver");
      if (ver && data?.version) ver.textContent = `v${data.version}`;
      return out;
    };
    global.paintPanel.__fieldInspector = true;
  }

  function bindUi() {
    $("field-search")?.addEventListener("input", filterFields);
    $("field-search")?.addEventListener("keyup", filterFields);
    $("field-inspector-toggle")?.addEventListener("click", () => {
      $("field-inspector")?.classList.toggle("collapsed");
    });
  }

  function openIntegrated() {
    const fold = document.querySelector(".field-clarity-fold");
    const mount = document.getElementById("field-clarity-mount");
    if (fold) fold.open = true;
    if (mount) {
      mount.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  async function mount() {
    if (mounted || document.getElementById("field-inspector")) return;
    try {
      const res = await fetch("/assets/field-inspector.html", { cache: "no-store" });
      if (!res.ok) throw new Error("fragment missing");
      const html = await res.text();
      const host = document.createElement("div");
      host.innerHTML = html.trim();
      const node = host.firstElementChild;
      if (!node) throw new Error("empty fragment");
      const target = document.getElementById("field-clarity-mount") || document.body;
      const integrated = target.id === "field-clarity-mount";
      node.classList.toggle("field-inspector--integrated", integrated);
      target.appendChild(node);
      mounted = true;
      bindUi();
      renderFields();
      hookPaintPanel();
      refreshLiveBadges();
      console.log("✅ Field Clarity loaded | integrated in System settings");
    } catch (err) {
      console.warn("Field inspector mount failed:", err);
    }
  }

  function boot() {
    mount();
  }

  global.NexusFieldInspector = {
    VERSION,
    ALL_FIELDS,
    renderFields,
    filterFields,
    explain,
    resolveLive,
    refresh: refreshLiveBadges,
    open: openIntegrated,
  };
  global.filterFields = filterFields;
  global.explain = explain;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);
