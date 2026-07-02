/**
 * Underlay F9 — field command surface (data_bus, meld, underlay doctrine).
 * Zero legacy panel deps — fetch-only against NEXUS APIs.
 */
(function () {
  "use strict";

  const POLL_MS = 5000;
  const SECTORS = [
    "command",
    "underlay",
    "sense",
    "die",
    "meld",
    "firmware",
    "network",
    "sovereign",
    "cycle",
  ];

  const state = {
    sector: "command",
    lastTick: null,
    data: {},
  };

  function $(id) {
    return document.getElementById(id);
  }

  function toast(msg) {
    const el = $("f9-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2800);
  }

  async function api(path, opts) {
    const res = await fetch(path, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(path + " " + res.status);
    return res.json();
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function fmtHex(n) {
    const v = Number(n) >>> 0;
    return "0x" + v.toString(16).padStart(8, "0");
  }

  function chip(id, label, value, cls) {
    const el = $(id);
    if (!el) return;
    el.innerHTML = "<b>" + esc(label) + "</b> " + esc(value ?? "—");
    el.className = "f9-chip" + (cls ? " f9-chip--" + cls : "");
  }

  function setSector(name) {
    if (!SECTORS.includes(name)) return;
    state.sector = name;
    document.querySelectorAll(".f9-nav button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.sector === name);
    });
    document.querySelectorAll(".f9-sector").forEach((sec) => {
      sec.classList.toggle("active", sec.dataset.sector === name);
    });
  }

  function renderBus(bus) {
    const grid = $("f9-bus-grid");
    if (!grid) return;
    const words = Array.isArray(bus?.data_bus) ? bus.data_bus : [];
    if (!Array.isArray(words) || !words.length) {
      grid.innerHTML = '<span class="f9-dim">bus empty</span>';
      return;
    }
    const hot = new Set([0, 1, 4, 8, 9, 12, 13, 14, 15, 28, 56, 60, 63]);
    grid.innerHTML = words
      .map((w, i) => {
        const hotCls = hot.has(i) || (w & 0xff) > 0 ? " hot" : "";
        return (
          '<div class="f9-slot' +
          hotCls +
          '"><span class="f9-slot-i">' +
          i +
          '</span><span class="f9-slot-v">' +
          fmtHex(w).slice(2, 6) +
          "</span></div>"
        );
      })
      .join("");
  }

  function card(title, value, meta) {
    return (
      '<article class="f9-card"><h3>' +
      esc(title) +
      '</h3><div class="f9-val">' +
      esc(value) +
      '</div>' +
      (meta ? '<div class="f9-meta">' + esc(meta) + "</div>" : "") +
      "</article>"
    );
  }

  function renderCommand() {
    const d = state.data;
    const st = d.status || {};
    const ul = d.underlay || {};
    const pm = d.plateMeld || {};
    const ic = d.ironcladImmediate || {};
    const grid = $("f9-command-grid");
    if (!grid) return;
    grid.innerHTML =
      card("Ironclad", ic.ironclad_sealed ? "SEALED" : ic.verdict || "immediate", (ic.truth_percent ?? "—") + "% · " + (ic.charge_holder || "—")) +
      card("Panel build", st.panel_build || "underlay-f9", "NEXUS-Shield v" + (st.version || "—")) +
      card("Vigil mode", st.vigil_mode || st.mode || "calm", "Poll " + POLL_MS + "ms") +
      card("Plate generation", pm.generation ?? "—", "chain " + (pm.chain_hash || "").slice(0, 16)) +
      card("Underlay phase", ul.phase || ul.posture?.phase || "userspace", ul.motto || "bottom-up authority") +
      card("Field max", st.field_max ? "ON" : "off", st.field_mode || "standard") +
      card("Connections", (d.gatekeeper?.connections || []).length, "gatekeeper live");
  }

  function renderUnderlay() {
    const ul = state.data.underlay || {};
    const nat = state.data.native || {};
    const ti = state.data.tristate || {};
    const di = state.data.dropIn || {};
    const proto = state.data.sovereignProtocol || {};
    const nf = ti.non_fielded || ti.drive_converter?.panel?.defield_audit || di.defield_audit || {};
    const defieldOk = di.defield_ok === true || ti.drive_converter?.panel?.defield_ok === true || nf.defield_ok === true;
    const nested = nf.nested_nexus_field_on_drives || [];
    const f9Target = di.f9_target || (defieldOk && proto.secured ? "queen_sovereign_browser" : "tristate_installer");
    const el = $("f9-underlay-body");
    if (!el) return;
    const policy = ul.policy || ul.doctrine?.policy || di.policy || {};
    const defCls = defieldOk ? "ok" : "alert";
    const netCls = proto.secured ? "ok" : "warn";
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Drop-in", policy.drop_in_replacement || di.phase ? "YES" : "no", "phase: " + (di.phase || "—")) +
      card("Guest passthrough", policy.guest_os_passthrough ? "YES" : "no", "incumbent OS inside envelope") +
      card("Hotkey F9", policy.hotkey || "F9", f9Target === "queen_sovereign_browser" ? "Queen sovereign browser" : "Tristate installer") +
      card("Secure network", proto.secured ? "SECURED" : "pending", (proto.managed_live ?? "—") + " managed · legacy compat") +
      card("Native authority", nat.native_authority || "SG/NewLatest", nat.we_are_the_native ? "witness BIOS" : "—") +
      card("Flash chip", nat.flash_chip === false ? "FALSE" : String(nat.flash_chip), nat.flash_policy || "witness only") +
      card("Non-fielded", defieldOk ? "CLEAN" : "BLOCKED", "no field-in-field before whole-system field") +
      card("Restorable tails", nf.restorable_files != null ? String(nf.restorable_files) : "—", "WRDT/WRZC/ZAC/H7 must be 0") +
      card("Drive hotspots", nested.length ? String(nested.length) : "0", nf.host_mirror_only ? "publish → host mirror" : "committed") +
      '</div>' +
      '<div class="f9-actions" style="margin:0.75rem 0">' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-drop-in-force">FORCE DROP-IN</button>' +
      '<button type="button" class="f9-btn" id="f9-defield-audit">DEFIELD AUDIT</button>' +
      '<button type="button" class="f9-btn" id="f9-secure-network" ' + (defieldOk ? "" : "disabled") + '>SECURE NETWORK</button>' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-open-browser" ' + (f9Target === "queen_sovereign_browser" ? "" : "disabled") + '>OPEN QUEEN BROWSER</button>' +
      '<button type="button" class="f9-btn" id="f9-open-display">OPEN DISPLAY</button>' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-purge-nested" ' + (nested.length ? "" : "disabled") + '>PURGE NESTED FIELD</button>' +
      '</div>' +
      (nested.length
        ? '<ul class="f9-list f9-wide"><li class="f9-chip f9-chip--' + defCls + '">Nested nexus-field on drive — quarantine before convert/commit</li>'
          + nested.map((p) => "<li>" + esc(p) + "</li>").join("") + "</ul>"
        : "") +
      '<pre class="f9-pre f9-wide">' +
      esc(JSON.stringify({ underlay: ul.model || ul.posture || ul, non_fielded: nf }, null, 2)) +
      "</pre>";
    $("f9-drop-in-force")?.addEventListener("click", () => runDropInAction("/force", "force drop-in"));
    $("f9-defield-audit")?.addEventListener("click", () => runDropInAction("/defield", "defield audit"));
    $("f9-secure-network")?.addEventListener("click", () => runDropInAction("/secure-network", "secure network"));
    $("f9-open-browser")?.addEventListener("click", () => runQueenBrowser());
    $("f9-open-display")?.addEventListener("click", () => runDisplayOpen());
    $("f9-purge-nested")?.addEventListener("click", () => {
      if (!confirm("Quarantine nested nexus-field on TEAM/KILROY drives?\n\nHost mirror (.nexus-field-drive) is the only pre-commit publish target.")) return;
      runTristateAction("/purge-nested-drive", "purge nested", { apply: true, confirm: true });
    });
  }

  async function runTristateAction(path, label, body) {
    toast(label + "…");
    try {
      const res = await fetch("/api/tristate-installer" + path, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const j = await res.json().catch(() => ({}));
      if (j.posture) state.data.tristate = j.posture;
      renderUnderlay();
      toast(j.ok || j.posture?.drive_converter?.panel?.defield_ok ? label + " complete" : j.error || label + " blocked");
    } catch (e) {
      toast(label + " failed: " + e.message);
    }
  }

  async function runDropInAction(path, label, body) {
    toast(label + "…");
    try {
      const res = await fetch("/api/drop-in-orchestrator" + path, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const j = await res.json().catch(() => ({}));
      if (j.posture) state.data.dropIn = j.posture;
      else state.data.dropIn = j;
      await refresh();
      toast(j.ok ? label + " complete" : j.error || label + " blocked");
    } catch (e) {
      toast(label + " failed: " + e.message);
    }
  }

  async function runQueenBrowser() {
    toast("Opening Queen sovereign browser…");
    try {
      const res = await fetch("/api/queen-browser/f9", {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: "{}",
      });
      const j = await res.json().catch(() => ({}));
      toast(j.ok ? "Queen browser open" : j.error || "browser blocked");
    } catch (e) {
      toast("browser failed: " + e.message);
    }
  }

  async function runDisplayOpen() {
    toast("Opening display…");
    try {
      const j = await api("/api/display-open/local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route: "underlay-f9" }),
      });
      toast(j.ok ? "Display open" : j.error || "display blocked");
    } catch (e) {
      toast("display failed: " + e.message);
    }
  }

  function renderSense() {
    const sp = state.data.sensePackage || {};
    const sum = sp.summary || {};
    const mem = sp.members || {};
    const eye = mem.final_eye || {};
    const ear = mem.final_ear || {};
    const zocr = mem.zocr || {};
    const wr = mem.world_redata || {};
    const h7 = mem.hostess7 || {};
    const icrf = state.data.ironcladReality || {};
    const icim = state.data.ironcladImmediate || {};
    const pts = icim.plate_to_sense || sp.plate_to_sense || sp.ironclad_goldmine || {};
    const sn = state.data.senseNeural || {};
    const el = $("f9-sense-body");
    if (!el) return;
    const smart = h7.smart_one || {};
    const brainMb = smart.brain_bytes ? Math.round(smart.brain_bytes / 1048576) + "M" : "";
    const brainMeta = h7.brain_live
      ? "smart:" + (smart.label || (h7.brain_roots || {}).source || "cache")
        + " · score " + (h7.brain_score ?? "—")
        + (brainMb ? " · " + brainMb : "")
      : "brain witness";
    const candCount = (h7.brain_candidates || []).filter(function (c) { return c.present; }).length;
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Verdict", sp.verdict || "—", "protected · flock + fsync") +
      card("Final Eye", eye.version || "—", (eye.live ? "LIVE :" + (eye.port || 9479) : "witness") + (eye.motion_track ? " · motion" : "")) +
      card("Final Ear", ear.version || "—", ear.live ? "sealed" : "offline") +
      card("Hostess7", h7.version || "—", brainMeta + (h7.sdf_segments ? " · " + h7.sdf_segments + " sdf" : "") + (candCount ? " · " + candCount + " roots" : "")) +
      card("ZOCR legacy", zocr.present ? "present" : "—", zocr.superseded_by_final_eye ? "fallback" : "canonical") +
      card("World Redata", wr.present ? "present" : "—", (wr.live ? "live" : "witness") + " WRDT1/WRZC1") +
      card("Present", sum.present_count ?? "—", "live " + (sum.live_count ?? "—")) +
      card("Ironclad serum", icrf.verdict || "—", (icrf.ironclad_sealed ? "SEALED" : "pending") + " · " + (icrf.truth_serum?.truth_percent ?? "—") + "%") +
      card("Human condition", icrf.ai_in_charge ? "AI IN CHARGE" : "HUMAN HOLDS", icrf.human_condition?.motto || "never wrong gate") +
      card("Charge", icrf.charge_holder || "—", icrf.human_condition?.ai_role || (icrf.ai_in_charge ? "command" : "counsel")) +
      card("Clean voltage", icrf.clean_voltage?.voltage_is_voltage ? "YES" : "no", icrf.clean_voltage?.motto || "voltage_is_voltage") +
      card("Smooth operator", icrf.smoothness?.smoothness_score != null ? String(icrf.smoothness.smoothness_score) : "—", icrf.smoothness?.smooth_operator ? "smooth" : "advisory") +
      card("Plate→Eye", pts.members?.eye_neural?.truth_percent != null ? pts.members.eye_neural.truth_percent + "%" : "—", pts.ironclad_grounded ? "GOLDMINE" : "read_first") +
      card("Plate→Ear", pts.members?.ear_neural?.truth_percent != null ? pts.members.ear_neural.truth_percent + "%" : "—", pts.members?.ear_neural?.citation || "ironclad:neural:2") +
      card("Plate→Mouth", pts.members?.mouth_neural?.truth_percent != null ? pts.members.mouth_neural.truth_percent + "%" : "—", pts.members?.mouth_neural?.hemisphere || "voice") +
      card("Sense wire", sn.goldmine_ok || pts.goldmine_ok ? "GOLDMINE" : sn.invincible_ok ? "invincible" : "wire", (sn.woven_paths ?? pts.woven_paths ?? "—") + " paths · " + (sn.citation || pts.citation || "ironclad:neural:2")) +
      '</div><div class="f9-actions" style="margin:0.5rem 0">' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-ironclad-serum">TRUTH SERUM CYCLE</button>' +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify({ sense: sp, plate_to_sense: pts, sense_neural: sn, ironclad_reality_field: icrf }, null, 2)) +
      "</pre>";
    $("f9-ironclad-serum")?.addEventListener("click", () => runIroncladSerum());
  }

  async function runIroncladSerum() {
    toast("Ironclad truth serum cycle…");
    try {
      const res = await fetch("/api/ironclad/reality-field/cycle", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const j = await res.json().catch(() => ({}));
      state.data.ironcladReality = j;
      renderSense();
      toast(j.verdict === "GREEN" ? "Truth serum GREEN — SI field sealed" : j.verdict || "serum cycle done");
      await refresh();
    } catch (e) {
      toast("serum failed: " + e.message);
    }
  }

  function renderDie() {
    const k = state.data.kernel || {};
    const sum = k.summary || {};
    const el = $("f9-die-body");
    if (!el) return;
    el.innerHTML =
      '<div class="f9-grid">' +
      card("KILROY live", k.kilroy_live ? "LIVE" : "witness", k.kilroy_root || "—") +
      card("bzImage", k.bzimage_ready ? "READY" : "pending", (k.bzimage?.sha256 || "").slice(0, 24)) +
      card("Substrate", k.substrate_pinned ? "linux-7.1.1" : "—", k.substrate?.path || "") +
      card("RTX Field Die", k.config_rtx_field_die?.enabled ? "ON" : "off", "CONFIG_RTX_FIELD_DIE") +
      card("Boot vector", k.boot_vector ?? "—", "bus slot 4") +
      card("Host witness", sum.witness_host ? "generic kernel" : "KILROY", sum.field_kernel_running ? "die running" : "pre-boot") +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify(k, null, 2)) +
      "</pre>";
  }

  function renderMeld() {
    const pm = state.data.plateMeld || {};
    const sum = pm.summary || {};
    const el = $("f9-meld-body");
    if (!el) return;
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Generation", pm.generation ?? "—", "uninterruptable flock") +
      card("Plates", pm.plate_count ?? (pm.plates || []).length, (pm.plates || []).join(", ")) +
      card("Route words", sum.route_words ?? "—", "iron plate") +
      card("Field plate", sum.field_dimension_count ?? "—", "∞ dim · amp " + (sum.field_peak_amplitude ?? "—")) +
      card("Kernel meld", sum.bzimage_ready ? "fused" : "—", "boot " + (sum.boot_vector ?? "—")) +
      card("Firmware", sum.firmware_verdict || "—", "removed " + (sum.firmware_removed ?? 0)) +
      card("Bus checksum", sum.bus_checksum ?? "—", "copilot lane") +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify(pm, null, 2)) +
      "</pre>";
  }

  function renderFirmware() {
    const fw = state.data.firmware || {};
    const scan = fw.scan || fw;
    const el = $("f9-firmware-body");
    if (!el) return;
    const witness = scan.firmware_witness || {};
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Verdict", fw.verdict || scan.verdict || "—", "no ROM flash") +
      card("Threats", fw.threat_count ?? scan.threat_count ?? 0, "removable " + (scan.removable_count ?? 0)) +
      card("Removed", fw.removed_count ?? 0, "software strip") +
      card("BIOS manual", fw.bios_manual_count ?? scan.bios_manual_count ?? 0, "Secure Boot / TPM in firmware setup") +
      card("Secure Boot", witness.secure_boot === true ? "ON" : witness.secure_boot === false ? "OFF" : "?", "efivar witness") +
      card("IOMMU", witness.iommu ? "ON" : "OFF", "DMA protection") +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify(fw, null, 2)) +
      "</pre>";
  }

  function renderNetwork() {
    const ddos = state.data.portDdos || {};
    const deint = state.data.deinterlace || {};
    const pkt = state.data.packet || {};
    const laws = state.data.laws || {};
    const el = $("f9-network-body");
    if (!el) return;
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Port DDoS", ddos.verdict || "—", "storm " + (ddos.storm_edges ?? "—")) +
      card("Deinterlace", deint.processed ?? "—", "secure " + (deint.secure ?? 0)) +
      card("Packets TX/RX", (pkt.tx_count || 0) + "/" + (pkt.rx_count || 0), "alerts " + (pkt.alert_count || 0)) +
      card("Connectivity laws", (laws.laws || laws.rules || []).length || laws.count || "—", "legal reconverge") +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify({ ddos, deint, pkt, laws }, null, 2)) +
      "</pre>";
  }

  function renderSovereign() {
    const st = state.data.sovereignTime || {};
    const clk = state.data.sovereignClock || {};
    const sync = state.data.sovereignSync || {};
    const desync = clk.desync || {};
    const synced = clk.synced !== false && desync.synced !== false;
    const el = $("f9-sovereign-body");
    if (!el) return;
    el.innerHTML =
      '<div class="f9-grid">' +
      card("Sovereign clock", synced ? "SYNC" : "DESYNC", clk.utc || st.derived_utc || "—") +
      card("Linear sealed", st.immutable_linear || clk.immutable_linear ? "SEALED" : "watch", clk.linear_ns ?? "—") +
      card("Cycle", (clk.cycle ?? sync.cycle ?? st.cycle) || "—", "never lose cycle") +
      card("Skew", desync.skew_ms != null ? desync.skew_ms + " ms" : "—", synced ? "never desync" : "red flag") +
      '</div><pre class="f9-pre f9-wide">' +
      esc(JSON.stringify({ sovereignClock: clk, sovereignTime: st, sovereignSync: sync }, null, 2)) +
      "</pre>";
  }

  function renderCycle() {
    const hz = state.data.hostFreeze || {};
    const phase = hz.phase || "idle";
    const frozen = hz.frozen ? "FROZEN" : phase.toUpperCase();
    const isolated = hz.field_draw_isolated ? "field draw isolated" : "full host";
    const el = $("f9-cycle-body");
    if (!el) return;
    el.innerHTML =
      '<div class="f9-grid f9-wide">' +
      card("Last tick", state.lastTick || "—", "auto every " + POLL_MS / 1000 + "s") +
      card("Host freeze", frozen, isolated) +
      card("Sense meld", "POST /api/sense-package/meld", "eye · ear · mouth · redata · hostess7") +
      card("Meld cycle", "POST /api/plate-meld/cycle", "sense → firmware → kernel → plates → bus") +
      card("Bus pack", "POST /api/field-bus/cycle", "data_bus[64] copilot") +
      "</div>" +
      '<p class="f9-lead">Operator cycle fuses all plates under flock — kernel meld, firmware strip, unified bus refresh. Host freeze locks memory and suspends the guest OS; field slice keeps drawing on soft freeze.</p>' +
      '<div class="f9-actions" style="margin-top:0.75rem">' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-run-sense">SENSE MELD</button>' +
      '<button type="button" class="f9-btn" id="f9-run-meld">RUN MELD CYCLE</button>' +
      '<button type="button" class="f9-btn" id="f9-run-bus">PACK BUS</button>' +
      '<button type="button" class="f9-btn" id="f9-run-firmware">STRIP FIRMWARE</button>' +
      "</div>" +
      '<div class="f9-actions" style="margin-top:0.5rem">' +
      '<button type="button" class="f9-btn f9-btn--green" id="f9-freeze-soft">SOFT FREEZE</button>' +
      '<button type="button" class="f9-btn" id="f9-freeze-mem">MEM SLEEP</button>' +
      '<button type="button" class="f9-btn" id="f9-freeze-disk">DISK CLOSE</button>' +
      '<button type="button" class="f9-btn" id="f9-freeze-thaw">THAW</button>' +
      '<button type="button" class="f9-btn" id="f9-freeze-resume">RESUME WITNESS</button>' +
      "</div>" +
      '<pre class="f9-pre f9-wide" id="f9-cycle-log">awaiting cycle…</pre>';
    $("f9-run-sense")?.addEventListener("click", () => runCycle("sense"));
    $("f9-run-meld")?.addEventListener("click", () => runCycle("meld"));
    $("f9-run-bus")?.addEventListener("click", () => runCycle("bus"));
    $("f9-run-firmware")?.addEventListener("click", () => runCycle("firmware"));
    $("f9-freeze-soft")?.addEventListener("click", () => runHostFreeze("freeze", "soft"));
    $("f9-freeze-mem")?.addEventListener("click", () => runHostFreeze("freeze", "mem"));
    $("f9-freeze-disk")?.addEventListener("click", () => runHostFreeze("close", "disk"));
    $("f9-freeze-thaw")?.addEventListener("click", () => runHostFreeze("thaw"));
    $("f9-freeze-resume")?.addEventListener("click", () => runHostFreeze("resume-witness"));
  }

  function renderAll() {
    renderCommand();
    renderUnderlay();
    renderSense();
    renderDie();
    renderMeld();
    renderFirmware();
    renderNetwork();
    renderSovereign();
    if (state.sector === "cycle") renderCycle();
    renderBus(state.data.bus || {});
  }

  function updateHeader() {
    const d = state.data;
    const pm = d.plateMeld || {};
    const fw = d.firmware || {};
    const k = d.kernel || {};
    const sp = d.sensePackage || {};
    const ic = d.ironcladImmediate || {};
    chip("f9-chip-gen", "GEN", pm.generation ?? "—");
    if ($("f9-chip-ironclad")) {
      chip(
        "f9-chip-ironclad",
        "IRON",
        ic.ironclad_sealed ? "SEALED" : ic.verdict || "—",
        ic.ironclad_sealed ? "ok" : ic.verdict === "WATCH" ? "warn" : ""
      );
    }
    const senseVerdict = sp.verdict || fw.verdict || "—";
    chip("f9-chip-verdict", "SENSE", senseVerdict, senseVerdict === "GREEN" ? "ok" : senseVerdict === "WATCH" || senseVerdict === "BIOS_REQUIRED" ? "warn" : "alert");
    chip("f9-chip-die", "DIE", k.kilroy_live ? "LIVE" : "witness", k.bzimage_ready ? "ok" : "");
    chip("f9-chip-bus", "BUS", (d.bus?.checksum ?? "—").toString().slice(-8));
    const clk = d.sovereignClock || {};
    const desync = clk.desync || {};
    const synced = clk.synced !== false && desync.synced !== false;
    if ($("f9-chip-sovereign")) {
      chip("f9-chip-sovereign", "TIME", synced ? "SYNC" : "DESYNC", synced ? "ok" : "alert");
    }
    const tick = clk.utc || clk.utc_full || "";
    $("f9-foot-tick").textContent = tick ? tick.slice(11, 19) + "Z" : state.lastTick || "—";
  }

  async function refresh() {
    try {
      const [
        status,
        underlay,
        native,
        plateMeld,
        kernel,
        firmware,
        sensePackage,
        bus,
        gatekeeper,
        portDdos,
        deinterlace,
        packet,
        laws,
        sovereignTime,
        sovereignClock,
        sovereignSync,
        tristate,
        dropIn,
        sovereignProtocol,
        displays,
        ironcladReality,
        ironcladImmediate,
        senseNeural,
        hostFreeze,
      ] = await Promise.all([
        api("/api/status").catch(() => ({})),
        api("/api/field-underlay").catch(() => ({})),
        api("/api/native-layer").catch(() => ({})),
        api("/api/plate-meld").catch(() => ({})),
        api("/api/kernel-meld").catch(() => ({})),
        api("/api/firmware-threat").catch(() => ({})),
        api("/api/sense-package").catch(() => ({})),
        api("/api/field-bus").catch(() => ({})),
        api("/api/gatekeeper").catch(() => ({})),
        api("/api/port-ddos").catch(() => ({})),
        api("/api/packet-deinterlace").catch(() => ({})),
        api("/api/packet-field").catch(() => ({})),
        api("/api/connectivity-laws").catch(() => ({})),
        api("/api/sovereign-time").catch(() => ({})),
        api("/api/sovereign-clock").catch(() => ({})),
        api("/api/sovereign-sync").catch(() => ({})),
        api("/api/tristate-installer").catch(() => ({})),
        api("/api/drop-in-orchestrator").catch(() => ({})),
        api("/api/sovereign-protocol").catch(() => ({})),
        api("/api/display-open").catch(() => ({})),
        api("/api/ironclad/reality-field").catch(() => ({})),
        api("/api/ironclad/immediate").catch(() => ({})),
        api("/api/sense-neural").catch(() => ({})),
        api("/api/field-host-freeze").catch(() => ({})),
      ]);
      state.data = {
        status,
        underlay,
        native,
        plateMeld,
        kernel,
        firmware,
        sensePackage,
        bus,
        gatekeeper,
        portDdos,
        deinterlace,
        packet,
        laws,
        sovereignTime,
        sovereignClock,
        sovereignSync,
        tristate,
        dropIn,
        sovereignProtocol,
        displays,
        ironcladReality,
        ironcladImmediate,
        senseNeural,
        hostFreeze,
      };
      const tickUtc = sovereignClock?.utc || sovereignClock?.utc_full || "";
      state.lastTick = tickUtc ? tickUtc.slice(11, 19) + "Z" : new Date().toISOString().slice(11, 19) + "Z";
      updateHeader();
      renderAll();
    } catch (e) {
      toast("refresh failed: " + e.message);
    }
  }

  async function runHostFreeze(action, mode) {
    const log = $("f9-cycle-log");
    const path = "/api/field-host-freeze/" + action;
    const needsElevated = action === "freeze" || action === "close" || action === "thaw";
    const body = { mode: mode || "soft" };
    if (needsElevated) body.elevated = true;
    if (log) log.textContent = "host freeze " + action + (mode ? " (" + mode + ")" : "") + "…";
    try {
      const res = await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (log) log.textContent = JSON.stringify(res, null, 2);
      toast(res.ok ? action + " ok" : action + " failed");
      await refresh();
    } catch (e) {
      if (log) log.textContent = String(e);
      toast("host freeze failed");
    }
  }

  async function runCycle(kind) {
    const log = $("f9-cycle-log");
    const paths = {
      sense: "/api/sense-package/meld",
      meld: "/api/plate-meld/cycle",
      bus: "/api/field-bus/cycle",
      firmware: "/api/firmware-threat/cycle",
    };
    const path = paths[kind];
    if (!path) return;
    if (log) log.textContent = "running " + kind + "…";
    try {
      const res = await api(path, { method: "GET" });
      if (log) log.textContent = JSON.stringify(res, null, 2);
      toast(kind + " cycle complete");
      await refresh();
    } catch (e) {
      if (log) log.textContent = String(e);
      toast(kind + " failed");
    }
  }

  function bindNav() {
    document.querySelectorAll(".f9-nav button").forEach((btn) => {
      btn.addEventListener("click", () => {
        setSector(btn.dataset.sector);
        if (btn.dataset.sector === "cycle") renderCycle();
      });
    });
    $("f9-refresh")?.addEventListener("click", () => refresh());
    $("f9-meld")?.addEventListener("click", () => runCycle("meld"));
  }

  function bindF9() {
    document.addEventListener("keydown", async (ev) => {
      if (ev.key !== "F9") return;
      ev.preventDefault();
      const di = state.data.dropIn || {};
      const target = di.f9_target || "tristate_installer";
      if (target === "queen_sovereign_browser") {
        await runQueenBrowser();
        return;
      }
      setSector("underlay");
      toast("UNDERLAY F9 — Tristate installer");
      try {
        await api("/api/queen-browser/f9", { method: "POST", body: "{}" });
      } catch (_) { /* panel may open installer tab */ }
    });
  }

  function initialSector() {
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("sector");
      if (q && SECTORS.includes(q)) return q;
      const hash = (window.location.hash || "").replace(/^#/, "");
      if (hash === "underlay" || (hash && SECTORS.includes(hash))) return hash === "underlay" ? "underlay" : hash;
    } catch (_) { /* ignore */ }
    return "command";
  }

  function init() {
    bindNav();
    bindF9();
    setSector(initialSector());
    refresh();
    setInterval(refresh, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();