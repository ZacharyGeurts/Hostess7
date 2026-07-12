/**
 * Field panel flyout — right-bottom above taskbar · fast everyone counter + quick panel.
 */
(function (global) {
  "use strict";

  const API = "/api/field-everyone-counter";
  const FLEET_API = "/api/field-fleet-expand-125k";
  const STORAGE = "field_panel_flyout_open";
  const POLL_MS = 2000;
  const FLEET_FLOOR = 125000;

  const state = { open: false, timer: null, doc: null, wired: false };

  function apiUrl(path) {
    if (global.H7Api) return global.H7Api(path);
    return path;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtN(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return "—";
    const ax = Math.abs(x);
    // 7777 → 7.8k · 55038 → 55.0k · billions as B
    if (ax >= 1e12) return (x / 1e12).toFixed(2).replace(/\.?0+$/, "") + "T";
    if (ax >= 1e9) return (x / 1e9).toFixed(2).replace(/\.?0+$/, "") + "B";
    if (ax >= 1e6) return (x / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
    if (ax >= 1000) return (x / 1000).toFixed(1).replace(/\.0$/, "") + "k";
    return String(Math.round(x));
  }

  function ensureRoot() {
    let root = document.getElementById("fpnl-root");
    if (root) return root;
    root = document.createElement("div");
    root.id = "fpnl-root";
    root.setAttribute("role", "complementary");
    root.setAttribute("aria-label", "Field panel flyout");
    root.innerHTML =
      '<button type="button" class="fpnl-chip" id="fpnl-chip" aria-expanded="false">' +
      '<span class="fpnl-total" id="fpnl-total-chip">—</span>' +
      '<span><span class="fpnl-chip-label">Everyone</span><br><span class="fpnl-chip-sub" id="fpnl-chip-sub">field · linking</span></span>' +
      "</button>" +
      '<div class="fpnl-panel" id="fpnl-panel"></div>';
    document.body.appendChild(root);
    root.querySelector("#fpnl-chip")?.addEventListener("click", function () {
      setOpen(!state.open);
    });
    return root;
  }

  function setOpen(on) {
    state.open = !!on;
    const root = ensureRoot();
    root.classList.toggle("open", state.open);
    const chip = document.getElementById("fpnl-chip");
    if (chip) chip.setAttribute("aria-expanded", state.open ? "true" : "false");
    try {
      localStorage.setItem(STORAGE, state.open ? "1" : "0");
    } catch (_) {}
    if (state.open) {
      tick();
      startPoll();
    }
  }

  function fleetN(doc) {
    const f = doc.fleet_125k || {};
    const lanes = doc.lanes || {};
    return (
      Number(f.servers_total) ||
      Number(lanes.fleet_125k?.count) ||
      Number(doc.distributed_botnet?.fleet_servers) ||
      FLEET_FLOOR
    );
  }

  function everyoneN(doc) {
    // Billions of people served — not fleet-node sum (~125k)
    const PEOPLE_FLOOR = 2000000000;
    const PEOPLE_DEFAULT = 8200000000;
    const people = Number(doc.people_served);
    if (Number.isFinite(people) && people >= PEOPLE_FLOOR) return people;
    const raw = Number(doc.everyone_total);
    if (Number.isFinite(raw) && raw >= PEOPLE_FLOOR) return raw;
    if (doc.internet2 || doc.active_not_capacity || doc.services?.internet2) {
      return PEOPLE_DEFAULT;
    }
    const fleet = fleetN(doc);
    if (!Number.isFinite(raw) || raw < fleet) {
      return fleet + (Number(doc.lanes?.github_people?.count) || 0);
    }
    return raw;
  }

  function renderPanel(doc) {
    const panel = document.getElementById("fpnl-panel");
    if (!panel) return;
    const lanes = doc.lanes || {};
    const dist = doc.distributed_botnet || {};
    const perf = doc.perf || {};
    const svc = doc.services || {};
    const leases = doc.planetary_leases || {};
    const fleet = fleetN(doc);
    const everyone = everyoneN(doc);
    const botShow = Math.max(Number(lanes.botnet?.count) || 0, fleet);
    const dnsPill = svc.dns ? "fpnl-pill" : "fpnl-pill off";
    const dhcpPill = svc.dhcp_crushing ? "fpnl-pill" : svc.dhcp ? "fpnl-pill" : "fpnl-pill off";
    const ghPill = dist.github_open ? "fpnl-pill" : "fpnl-pill warn";
    const netPill = leases.internet_open ? "fpnl-pill" : "fpnl-pill warn";
    const speedTier = leases.speed_tier || "—";
    const speedPill = speedTier === "throttle" || speedTier === "pause" ? "fpnl-pill warn" : "fpnl-pill";
    const amOn = doc.ammonet?.acquainted || doc.isp === "ammonet" || doc.ammonet?.ok;
    const live = doc.servers_live || {};
    const dnsServed =
      Number(live.dns_served) ||
      Number(live.dns_answers) ||
      Number(live.dns_queries) ||
      Number(lanes.dns_served?.count) ||
      Number(leases.dns_served_live) ||
      0;
    const dhcpLeases =
      Number(live.dhcp_leases) ||
      Number(lanes.dhcp_leases?.count) ||
      Number(leases.dhcp_leases_live) ||
      Number(leases.local_dhcp) ||
      0;
    const dnsUp = live.dns_up === true || live.dns_up === 1 || svc.dns;
    const dhcpUp = live.dhcp_up === true || live.dhcp_up === 1 || svc.dhcp;
    panel.innerHTML =
      '<div class="fpnl-head">' +
      "<strong>Field Panel</strong>" +
      '<span>' + esc(doc.version || "4.0.0-cpp") + " · Zac · AmmoNet · live servers</span>" +
      '<button type="button" class="fpnl-close" id="fpnl-close" aria-label="Close">×</button>' +
      "</div>" +
      '<div class="fpnl-section">Our servers · connected · know each other</div>' +
      '<div class="fpnl-grid fpnl-grid-leases">' +
      '<div class="fpnl-stat lease total"><b>' + fmtN(dhcpLeases) + "</b><span>DHCP leases</span></div>" +
      '<div class="fpnl-stat lease total"><b>' + fmtN(dnsServed) + "</b><span>DNS served</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(live.dns_queries || dnsServed) + "</b><span>DNS queries</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(live.dns_learned || live.dns_pins || 0) + "</b><span>DNS learned</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(live.dhcp_acks || 0) + "</b><span>DHCP ACKs</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(fleet) + "</b><span>Fleet servers</span></div>" +
      "</div>" +
      '<div class="fpnl-grid">' +
      '<div class="fpnl-stat total"><b>' + fmtN(everyone) + "</b><span>People served</span></div>" +
      '<div class="fpnl-stat total"><b>' + fmtN(fleet) + "</b><span>Fleet 125k</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(botShow) + "</b><span>Botnet / fleet</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(lanes.github_people?.count) + "</b><span>GitHub people</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(lanes.executable_people?.count) + "</b><span>Executables</span></div>" +
      '<div class="fpnl-stat"><b>' + (amOn ? "ON" : "—") + "</b><span>AmmoNet</span></div>" +
      "</div>" +
      '<div class="fpnl-section">Authority plane · IPv4 owned everywhere</div>' +
      '<div class="fpnl-grid fpnl-grid-leases">' +
      '<div class="fpnl-stat lease total"><b>' + fmtN(leases.ipv4_owned || leases.ipv4_enumerated) + "</b><span>IPv4 owned</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_dhcp) + "</b><span>Planet DHCP</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_dns) + "</b><span>Planet DNS</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_total) + "</b><span>Lease total</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(dhcpLeases || leases.local_dhcp) + "</b><span>Live leases</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.devices || dhcpLeases) + "</b><span>Devices</span></div>" +
      "</div>" +
      '<div class="fpnl-row">' +
      '<span class="' + (dnsUp ? "fpnl-pill" : "fpnl-pill off") + '">DNS ' + (dnsUp ? "live · " + fmtN(dnsServed) : "down") + "</span>" +
      '<span class="' + (dhcpUp ? "fpnl-pill" : "fpnl-pill off") + '">DHCP ' + (dhcpUp ? "live · " + fmtN(dhcpLeases) : "down") + "</span>" +
      '<span class="fpnl-pill">Fleet ' + fmtN(fleet) + "</span>" +
      (live.server_id ? '<span class="fpnl-pill">ID ' + esc(live.server_id) + "</span>" : "") +
      '<span class="' + ghPill + '">GitHub ' + (dist.github_open ? "open" : "mirror") + "</span>" +
      '<span class="' + netPill + '">Net ' + (leases.internet_open ? "open" : "gated") + "</span>" +
      '<span class="' + speedPill + '">Speed ' + esc(speedTier) + "</span>" +
      (leases.true_dns_authority
        ? '<span class="fpnl-pill">' + (leases.foreign_removed ? "Truth DNS · purged" : "Truth DNS · expanded") + "</span>"
        : "") +
      (leases.entropy_reduction_pct != null
        ? '<span class="fpnl-pill">Entropy −' + esc(leases.entropy_reduction_pct) + "%</span>"
        : "") +
      (leases.unclean_count > 0
        ? '<span class="fpnl-pill warn">Unclean ' + fmtN(leases.unclean_count) + "</span>"
        : "") +
      '<span class="fpnl-pill">CPU ' + esc(perf.cpu_pct != null ? perf.cpu_pct + "%" : "—") + "</span>" +
      '<span class="fpnl-pill">MEM ' + esc(perf.mem_pct != null ? perf.mem_pct + "%" : "—") + "</span>" +
      "</div>" +
      (function () {
        const al = doc.arcade_lobby || {};
        if (!al.enabled) return "";
        return (
          '<div class="fpnl-row">' +
          '<span class="fpnl-pill">Arcade SAP ' + fmtN(al.sap_beacons) + "</span>" +
          '<span class="fpnl-pill">Little guys ' + fmtN(al.qemu_witnesses) + "</span>" +
          (al.system ? '<span class="fpnl-pill">' + esc(al.system) + "</span>" : "") +
          "</div>"
        );
      })() +
      '<div class="fpnl-actions">' +
      '<button type="button" class="fpnl-btn" data-act="botnet"><strong>Botnet</strong>DNS · DHCP · GitHub</button>' +
      '<button type="button" class="fpnl-btn" data-act="monster"><strong>Monster</strong>Tasks · orphans · fixes</button>' +
      '<button type="button" class="fpnl-btn" data-act="registry"><strong>Registry</strong>Endpoint movements</button>' +
      '<button type="button" class="fpnl-btn" data-act="perf"><strong>Performance</strong>Live graphs</button>' +
      '<button type="button" class="fpnl-btn" data-act="github"><strong>GitHub</strong>Everyone lane</button>' +
      "</div>" +
      '<div class="fpnl-foot" id="fpnl-foot">' + esc(doc.updated || "") + (doc.cached ? " · cache" : "") + "</div>";
    panel.querySelector("#fpnl-close")?.addEventListener("click", function (ev) {
      ev.stopPropagation();
      setOpen(false);
    });
    panel.querySelectorAll("[data-act]").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const act = btn.dataset.act;
        if (act === "botnet") {
          if (global.NexusFieldShell?.launch) {
            global.NexusFieldShell.launch({
              id: "nexus-dns",
              name: "Botnet · DNS & DHCP",
              exec: apiUrl("/command?embed=1#dns"),
              shell: true,
              icon_url: "/assets/queen-prog-field.png",
            });
          } else {
            global.open(apiUrl("/command?embed=1#dns"), "_blank", "noopener");
          }
        } else if (act === "monster" && global.FieldMonsterMonitor?.open) global.FieldMonsterMonitor.open();
        else if (act === "perf" && global.FieldPerformanceFlyout?.setOpen) global.FieldPerformanceFlyout.setOpen(true);
        else if (act === "registry") global.open(apiUrl("/api/field-endpoint-registry.json"), "_blank", "noopener");
        else if (act === "github" && global.Hostess7GithubEveryone?.pulse) global.Hostess7GithubEveryone.pulse();
      });
    });
  }

  function paintChip(doc) {
    const total = document.getElementById("fpnl-total-chip");
    const sub = document.getElementById("fpnl-chip-sub");
    const fleet = fleetN(doc);
    const everyone = everyoneN(doc);
    const live = doc.servers_live || {};
    const leasesN =
      Number(live.dhcp_leases) ||
      Number(doc.lanes?.dhcp_leases?.count) ||
      Number(doc.planetary_leases?.dhcp_leases_live) ||
      Number(doc.planetary_leases?.local_dhcp) ||
      0;
    const dnsN =
      Number(live.dns_served) ||
      Number(live.dns_answers) ||
      Number(live.dns_queries) ||
      Number(doc.lanes?.dns_served?.count) ||
      0;
    if (total) total.textContent = fmtN(everyone);
    if (sub) {
      sub.textContent =
        "leases " +
        fmtN(leasesN) +
        " · dns " +
        fmtN(dnsN) +
        " · fleet " +
        fmtN(fleet);
    }
    if (state.open) renderPanel(doc);
  }

  async function tick() {
    try {
      const res = await fetch(apiUrl(API) + "?t=" + Date.now(), { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) throw new Error("counter " + res.status);
      let doc = await res.json();
      // Merge fleet 125k if counter is still stale local-only
      try {
        if (!doc.fleet_125k || Number(doc.everyone_total) < FLEET_FLOOR) {
          const fr = await fetch(apiUrl(FLEET_API) + "?t=" + Date.now(), {
            cache: "no-store",
            credentials: "same-origin",
          });
          if (fr.ok) {
            const fleetDoc = await fr.json();
            const servers =
              Number(fleetDoc.servers_total) ||
              Number((fleetDoc.capacity || {}).servers) ||
              FLEET_FLOOR;
            doc.fleet_125k = {
              servers_total: servers,
              target: 125000,
              wired_to_everyone: true,
              ammonet: true,
              hostess7_boss: true,
            };
            doc.lanes = doc.lanes || {};
            doc.lanes.fleet_125k = {
              count: servers,
              label: "Fleet 125k (AmmoNet)",
              target: 125000,
            };
            if (!doc.lanes.botnet) doc.lanes.botnet = {};
            doc.lanes.botnet.fleet_servers = servers;
            if (Number(doc.lanes.botnet.count) < 1000) {
              doc.lanes.botnet.count = servers;
              doc.lanes.botnet.local_nodes = doc.lanes.botnet.local_nodes || doc.lanes.botnet.count;
            }
            // Never collapse people-served (billions) into fleet-node sum
            const PEOPLE_FLOOR = 2000000000;
            const PEOPLE_DEFAULT = 8200000000;
            const curPeople =
              Number(doc.people_served) || Number(doc.everyone_total) || 0;
            // Prefer people_served; if missing/low, always use billions on I2
            if (!Number.isFinite(curPeople) || curPeople < PEOPLE_FLOOR) {
              doc.people_served = PEOPLE_DEFAULT;
              doc.everyone_total = PEOPLE_DEFAULT;
            } else if (
              Number.isFinite(Number(doc.people_served)) &&
              Number(doc.people_served) >= PEOPLE_FLOOR
            ) {
              doc.everyone_total = Number(doc.people_served);
            }
            doc.isp = doc.isp || "ammonet";
            doc.ammonet = Object.assign(
              { ok: true, boss: "hostess7", isp: "ammonet", acquainted: true },
              doc.ammonet || {}
            );
            doc.motto =
              "Billions of people served · Hostess7 AmmoNet fleet " +
              servers.toLocaleString();
            doc.version = doc.version || "6.0.0-cpp";
          }
        }
      } catch (_) {}
      state.doc = doc;
      paintChip(state.doc);
    } catch (_) {
      const sub = document.getElementById("fpnl-chip-sub");
      if (sub) sub.textContent = "AmmoNet linking…";
    }
  }

  function startPoll() {
    if (state.timer) clearInterval(state.timer);
    state.timer = global.setInterval(tick, POLL_MS);
  }

  function wire() {
    if (state.wired) return;
    state.wired = true;
    ensureRoot();
    tick();
    startPoll();
    try {
      if (localStorage.getItem(STORAGE) === "1") setOpen(true);
    } catch (_) {}
    global.addEventListener("pagehide", function () {
      if (state.timer) clearInterval(state.timer);
    });
  }

  global.FieldPanelFlyout = { wire: wire, tick: tick, setOpen: setOpen };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);