/**
 * Field panel flyout — right-bottom above taskbar · fast everyone counter + quick panel.
 */
(function (global) {
  "use strict";

  const API = "/api/field-everyone-counter";
  const STORAGE = "field_panel_flyout_open";
  const POLL_MS = 1000;

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
    if (x >= 1000000000) return (x / 1000000000).toFixed(1) + "B";
    if (x >= 1000000) return (x / 1000000).toFixed(1) + "M";
    if (x >= 1000) return (x / 1000).toFixed(1) + "k";
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

  function renderPanel(doc) {
    const panel = document.getElementById("fpnl-panel");
    if (!panel) return;
    const lanes = doc.lanes || {};
    const dist = doc.distributed_botnet || {};
    const perf = doc.perf || {};
    const svc = doc.services || {};
    const leases = doc.planetary_leases || {};
    const dnsPill = svc.dns ? "fpnl-pill" : "fpnl-pill off";
    const dhcpPill = svc.dhcp_crushing ? "fpnl-pill" : svc.dhcp ? "fpnl-pill" : "fpnl-pill off";
    const ghPill = dist.github_open ? "fpnl-pill" : "fpnl-pill warn";
    const netPill = leases.internet_open ? "fpnl-pill" : "fpnl-pill warn";
    const speedTier = leases.speed_tier || "—";
    const speedPill = speedTier === "throttle" || speedTier === "pause" ? "fpnl-pill warn" : "fpnl-pill";
    panel.innerHTML =
      '<div class="fpnl-head">' +
      "<strong>Field Panel</strong>" +
      '<span>' + esc(doc.version || "3.0.7-beta4") + " · distributed botnet</span>" +
      '<button type="button" class="fpnl-close" id="fpnl-close" aria-label="Close">×</button>' +
      "</div>" +
      '<div class="fpnl-grid">' +
      '<div class="fpnl-stat total"><b>' + fmtN(doc.everyone_total) + "</b><span>Everyone total</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(lanes.botnet?.count) + "</b><span>Botnet nodes</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(lanes.github_people?.count) + "</b><span>GitHub people</span></div>" +
      '<div class="fpnl-stat"><b>' + fmtN(lanes.executable_people?.count) + "</b><span>Executables</span></div>" +
      "</div>" +
      '<div class="fpnl-section">IPv4 owned · enumerated everywhere</div>' +
      '<div class="fpnl-grid fpnl-grid-leases">' +
      '<div class="fpnl-stat lease total"><b>' + fmtN(leases.ipv4_owned || leases.ipv4_enumerated) + "</b><span>IPv4 owned</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_dhcp) + "</b><span>Planet DHCP</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_dns) + "</b><span>Planet DNS</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.planet_total) + "</b><span>Lease total</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.local_dhcp) + "</b><span>Local enumerated</span></div>" +
      '<div class="fpnl-stat lease"><b>' + fmtN(leases.devices) + "</b><span>Devices</span></div>" +
      "</div>" +
      '<div class="fpnl-row">' +
      '<span class="' + dnsPill + '">DNS ' + (svc.dns ? "truth" : "down") + "</span>" +
      '<span class="' + dhcpPill + '">DHCP ' + (svc.dhcp_crushing ? "crush" : svc.dhcp ? "serve" : "down") + "</span>" +
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
    if (total) total.textContent = fmtN(doc.everyone_total);
    if (sub) {
      const leases = doc.planetary_leases || {};
      const lt = leases.planet_total ?? 0;
      const b = doc.lanes?.botnet?.count ?? 0;
      const g = doc.lanes?.github_people?.count ?? 0;
      const e = doc.lanes?.executable_people?.count ?? 0;
      const owned = leases.ipv4_owned || leases.ipv4_enumerated || 0;
      sub.textContent =
        "ipv4 " + fmtN(owned) + " · leases " + fmtN(lt) + " · bot " + fmtN(b);
    }
    if (state.open) renderPanel(doc);
  }

  async function tick() {
    try {
      const res = await fetch(apiUrl(API) + "?t=" + Date.now(), { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) throw new Error("counter " + res.status);
      state.doc = await res.json();
      paintChip(state.doc);
    } catch (_) {
      const sub = document.getElementById("fpnl-chip-sub");
      if (sub) sub.textContent = "loopback linking…";
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