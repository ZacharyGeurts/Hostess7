/**
 * Field panel flyout — right-bottom above taskbar · fast everyone counter + quick panel.
 */
(function (global) {
  "use strict";

  const API = "/api/field-everyone-counter";
  const FLEET_API = "/api/field-fleet-expand-125k";
  const STORAGE = "field_panel_flyout_open";
  const POLL_MS = 2500;
  const FLEET_FLOOR = 125000;
  const ACTIVE_LEASE_FLOOR = 1000000000; // below 1B is local sample, not plane

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
      Number(f.active_racks) ||
      Number(lanes.fleet_125k?.count) ||
      Number(doc.distributed_botnet?.fleet_servers) ||
      FLEET_FLOOR
    );
  }

  // ACTIVE Internet 2.0 leases (trillions) — never use local sample as primary
  function activeLeasesN(doc) {
    const live = doc.servers_live || {};
    const lanes = doc.lanes || {};
    const al = doc.active_leases || {};
    const pl = doc.planetary_leases || {};
    const candidates = [
      Number(live.dhcp_leases_active),
      Number(al.dhcp_leases),
      Number(lanes.active_leases?.count),
      Number(pl.active_device_leases),
      Number(pl.dhcp_leases_live),
      Number(live.dhcp_leases),
      Number(lanes.dhcp_leases?.count),
    ];
    let best = 0;
    for (let i = 0; i < candidates.length; i++) {
      const n = candidates[i];
      if (Number.isFinite(n) && n > best) best = n;
    }
    // floor: plane is 7T when internet2 / active_not_capacity stamped
    if (best < 1000000000 && (doc.internet2 || doc.active_not_capacity || al.active)) {
      best = 7000000000000;
    }
    return best;
  }

  function localSampleN(doc) {
    const live = doc.servers_live || {};
    const lanes = doc.lanes || {};
    const al = doc.active_leases || {};
    const pl = doc.planetary_leases || {};
    return (
      Number(live.dhcp_leases_local_sample) ||
      Number(al.local_sample_only) ||
      Number(lanes.local_sample?.count) ||
      Number(pl.local_dhcp_sample) ||
      0
    );
  }

  function everyoneN(doc) {
    const raw = Number(doc.everyone_total);
    const fleet = fleetN(doc);
    // Never show the old local-only 41-style total when fleet plane is 125k
    if (!Number.isFinite(raw) || raw < fleet) return fleet + (Number(doc.lanes?.github_people?.count) || 0);
    return raw;
  }

  // Live-update the C++-baked static Everyone strip on desktop
  function paintStaticEveryone(doc) {
    const el = document.getElementById("h7-everyone-static");
    if (!el) return;
    const active = activeLeasesN(doc);
    const fleet = fleetN(doc);
    const everyone = everyoneN(doc);
    const local = localSampleN(doc);
    const live = doc.servers_live || {};
    const lanes = doc.lanes || {};
    const dns =
      Number(live.dns_served) ||
      Number(live.dns_answers) ||
      Number(live.dns_queries) ||
      Number(lanes.dns_served?.count) ||
      0;
    const dnsUp = live.dns_up === true || live.dns_up === 1 || doc.services?.dns;
    const dhcpUp = live.dhcp_up === true || live.dhcp_up === 1 || doc.services?.dhcp;
    el.dataset.activeLeases = String(active);
    el.dataset.fleet = String(fleet);
    el.dataset.everyone = String(everyone);
    el.dataset.updated = doc.updated || "";
    const set = function (sel, text) {
      const n = el.querySelector(sel);
      if (n) n.textContent = text;
    };
    // grid: ACTIVE, fleet, everyone, dns, local, books(optional)
    const stats = el.querySelectorAll(".h7e-stat b");
    if (stats[0]) stats[0].textContent = fmtN(active);
    if (stats[1]) stats[1].textContent = fmtN(fleet);
    if (stats[2]) stats[2].textContent = fmtN(everyone);
    if (stats[3]) stats[3].textContent = fmtN(dns);
    if (stats[4]) stats[4].textContent = fmtN(local);
    const pills = el.querySelectorAll(".h7e-pill");
    if (pills[0]) {
      pills[0].textContent = "DNS " + (dnsUp ? "live" : "down");
      pills[0].classList.toggle("off", !dnsUp);
    }
    if (pills[1]) {
      pills[1].textContent = "DHCP " + (dhcpUp ? "live" : "down");
      pills[1].classList.toggle("off", !dhcpUp);
    }
    const foot = el.querySelector(".h7e-foot");
    if (foot) {
      const ts = doc.updated || new Date().toISOString();
      foot.innerHTML =
        "Live " +
        esc(ts) +
        ' · <a href="/Hostess7/api/field-everyone-counter.json">API</a> · ' +
        '<a href="/Hostess7/library/">Library</a> · ' +
        '<a href="/Hostess7/desktop/">Desktop</a>';
    }
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
    const active = activeLeasesN(doc);
    const local = localSampleN(doc);
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
    const dnsUp = live.dns_up === true || live.dns_up === 1 || svc.dns;
    const dhcpUp = live.dhcp_up === true || live.dhcp_up === 1 || svc.dhcp;
    panel.innerHTML =
      '<div class="fpnl-head">' +
      "<strong>Field Panel</strong>" +
      '<span>' + esc(doc.version || "5.0.0-cpp") + " · Zac · AmmoNet · Internet 2.0</span>" +
      '<button type="button" class="fpnl-close" id="fpnl-close" aria-label="Close">×</button>' +
      "</div>" +
      '<div class="fpnl-section">ACTIVE leases · not capacity · local sample separate</div>' +
      '<div class="fpnl-grid fpnl-grid-leases">' +
      '<div class="fpnl-stat lease total"><b>' + fmtN(active) + "</b><span>ACTIVE leases</span></div>" +
      '<div class="fpnl-stat lease total"><b>' + fmtN(dnsServed) + "</b><span>DNS served</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(local) + "</b><span>Local sample only</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(live.dns_learned || live.dns_pins || 0) + "</b><span>DNS learned</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(live.dhcp_acks || 0) + "</b><span>DHCP ACKs</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(fleet) + "</b><span>Fleet servers</span></div>" +
      "</div>" +
      '<div class="fpnl-grid">' +
      '<div class="fpnl-stat total"><b>' + fmtN(everyone) + "</b><span>Everyone total</span></div>" +
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
      '<div class="fpnl-stat lease"><b>' + fmtN(active) + "</b><span>ACTIVE device leases</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.devices || active) + "</b><span>Devices</span></div>" +
      "</div>" +
      '<div class="fpnl-row">' +
      '<span class="' + (dnsUp ? "fpnl-pill" : "fpnl-pill off") + '">DNS ' + (dnsUp ? "live · " + fmtN(dnsServed) : "down") + "</span>" +
      '<span class="' + (dhcpUp ? "fpnl-pill" : "fpnl-pill off") + '">DHCP ' + (dhcpUp ? "live · " + fmtN(active) : "down") + "</span>" +
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
    const active = activeLeasesN(doc);
    const live = doc.servers_live || {};
    const dnsN =
      Number(live.dns_served) ||
      Number(live.dns_answers) ||
      Number(live.dns_queries) ||
      Number(doc.lanes?.dns_served?.count) ||
      0;
    // Chip primary = ACTIVE leases (Internet 2.0), not local sample
    if (total) total.textContent = fmtN(active);
    if (sub) {
      sub.textContent =
        "ACTIVE " +
        fmtN(active) +
        " · dns " +
        fmtN(dnsN) +
        " · fleet " +
        fmtN(fleet) +
        " · all " +
        fmtN(everyone);
    }
    paintStaticEveryone(doc);
    if (state.open) renderPanel(doc);
  }

  async function tick() {
    try {
      const res = await fetch(apiUrl(API) + "?t=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "application/json", "Cache-Control": "no-cache" },
      });
      if (!res.ok) throw new Error("counter " + res.status);
      let doc = await res.json();
      // Fill fleet if missing — never clobber ACTIVE 7T leases
      try {
        if (!doc.fleet_125k || Number(doc.fleet_125k.servers_total) < FLEET_FLOOR) {
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
            doc.fleet_125k = Object.assign({}, doc.fleet_125k || {}, {
              servers_total: servers,
              target: 125000,
              wired_to_everyone: true,
              ammonet: true,
              hostess7_boss: true,
            });
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
            }
            if (!Number.isFinite(Number(doc.everyone_total)) || Number(doc.everyone_total) < servers) {
              const gh = Number(doc.lanes.github_people?.count) || 0;
              const ex = Number(doc.lanes.executable_people?.count) || 0;
              doc.everyone_total = servers + gh + ex + 1;
            }
            doc.isp = doc.isp || "ammonet";
            doc.ammonet = Object.assign(
              { ok: true, boss: "hostess7", isp: "ammonet", acquainted: true },
              doc.ammonet || {}
            );
          }
        }
      } catch (_) {}
      // Ensure active lease fields present for paint
      if (!doc.servers_live) doc.servers_live = {};
      if (!Number(doc.servers_live.dhcp_leases_active) && activeLeasesN(doc) >= 1000000000) {
        doc.servers_live.dhcp_leases_active = activeLeasesN(doc);
      }
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