(function () {
  "use strict";

  const API = "/api/tristate-installer";
  const STEPS = ["welcome", "root", "unfield", "znetwork", "arrive", "transform", "commit"];
  const STORAGE_KEY = "tristate-wizard-step";

  let state = null;
  let step = "welcome";
  let znChoice = "yes";
  let znLoaded = false;
  let rootReady = false;
  let defieldOk = false;
  let unfieldAutoRan = false;
  let launchRootDone = false;
  const ROOT_SESSION_KEY = "tristate-root-session";

  const $ = (id) => document.getElementById(id);

  function toast(msg) {
    const el = $("ti-toast");
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 3200);
  }

  function stepIndex(id) {
    return STEPS.indexOf(id);
  }

  function persistStep() {
    try {
      sessionStorage.setItem(STORAGE_KEY, step);
    } catch (_) { /* ignore */ }
  }

  function restoreStep() {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved && STEPS.includes(saved)) return saved;
    } catch (_) { /* ignore */ }
    return "welcome";
  }

  function canAdvance(id) {
    if (id === "root") return rootReady;
    if (id === "unfield") return defieldOk;
    if (id === "znetwork") return znChoice === "yes";
    if (id === "arrive") return rootReady && defieldOk;
    return true;
  }

  function setStep(next) {
    if (next === "committed") {
      step = "committed";
      document.querySelectorAll(".ti-step").forEach((el) => {
        el.classList.remove("active");
        el.classList.add("done");
      });
      document.querySelectorAll(".ti-pane").forEach((el) => {
        const show = el.dataset.pane === "committed";
        el.hidden = !show;
        el.classList.toggle("active", show);
      });
      const nav = $("ti-wizard-nav");
      if (nav) nav.hidden = true;
      updateChrome("committed");
      return;
    }

    if (!STEPS.includes(next)) return;
    step = next;
    persistStep();

    const idx = stepIndex(next);
    document.querySelectorAll(".ti-step").forEach((el) => {
      const s = el.dataset.step;
      const i = stepIndex(s);
      el.classList.toggle("active", s === next);
      el.classList.toggle("done", i >= 0 && i < idx);
    });

    document.querySelectorAll(".ti-pane").forEach((el) => {
      const show = el.dataset.pane === next;
      el.hidden = !show;
      el.classList.toggle("active", show);
    });

    const nav = $("ti-wizard-nav");
    if (nav) nav.hidden = false;

    const back = $("ti-wizard-back");
    const nxt = $("ti-wizard-next");
    const meta = $("ti-wizard-meta");
    if (back) back.disabled = idx <= 0;
    if (meta) meta.textContent = "Step " + (idx + 1) + " of " + STEPS.length;
    if (nxt) {
      nxt.textContent = idx === STEPS.length - 1 ? "Review commit" : "Next";
      nxt.disabled = !canAdvance(next);
    }

    updateChrome(next);

    if (next === "root" && !rootReady && !launchRootDone) maybeAutoAcquireRoot();
    if (next === "unfield" && !unfieldAutoRan) {
      unfieldAutoRan = true;
      runUnfieldAudit(true);
    }
    if (next === "znetwork") {
      if (!znLoaded) loadZnetworkOffer();
      else ensureZnetworkIngrained(true);
    }
  }

  function updateChrome(id) {
    const badge = $("ti-status-badge");
    const heroes = {
      welcome: ["Welcome to the Field", "Seven guided steps — root first, unfield drives, then install."],
      root: ["Administrator access", "One approval for install, network, WRDT, and commit — not just ZNetwork."],
      unfield: ["Unfield files on drive", "Quarantine nested field copies and clear tail formats before install."],
      znetwork: ["ZNetwork ingrained", "Field network is built in — review the replacer plan, then continue."],
      arrive: ["Install protections", "NEXUS Shield, Queen, perimeter — uses root granted at step 2."],
      transform: ["Transform", "Re-field shadow first — then sovereign restore, audit, World redump."],
      commit: ["Commit — permanent", "We are always the underlay from this point. No off switch."],
      committed: ["Underlay live", "Guest substrate inside field protections. Reboot when ready."],
    };
    const labels = {
      welcome: "WELCOME",
      root: "ROOT",
      unfield: "UNFIELD",
      znetwork: "NETWORK",
      arrive: "INSTALL",
      transform: "TRANSFORM",
      commit: "COMMIT",
      committed: "UNDERLAY LIVE",
    };
    const h = heroes[id] || heroes.welcome;
    const ht = $("ti-hero-title");
    const hs = $("ti-hero-sub");
    if (ht) ht.textContent = h[0];
    if (hs) hs.innerHTML = h[1].replace("F9", "<strong>F9</strong>");
    if (badge) {
      badge.textContent = labels[id] || id.toUpperCase();
      badge.classList.toggle("ti-badge--committed", id === "committed");
    }
    const prog = $("ti-progress-bar");
    if (prog) {
      const pct = {
        welcome: 5,
        root: 18,
        unfield: 32,
        znetwork: 46,
        arrive: 58,
        transform: 74,
        commit: 90,
        committed: 100,
      };
      prog.style.width = (pct[id] || 0) + "%";
    }
  }

  function renderRoot(root) {
    root = root || state?.root || {};
    rootReady = !!(root.ready || root.is_root || root.has_cached_sudo);
    const status = $("ti-root-status");
    const method = $("ti-root-method");
    if (status) {
      status.textContent = rootReady ? "READY" : "PENDING";
      status.classList.toggle("ti-ok", rootReady);
      status.classList.toggle("ti-danger", !rootReady);
    }
    if (method) method.textContent = root.elevation_method || root.method || "—";
    const nxt = $("ti-wizard-next");
    if (nxt && step === "root") nxt.disabled = !canAdvance("root");
    const installBtn = $("ti-install-nexus");
    if (installBtn) installBtn.disabled = !(rootReady && defieldOk);
  }

  function renderDefield(data) {
    const panel = data?.drive_converter?.panel || {};
    const defieldAudit = panel.defield_audit || data?.non_fielded || {};
    defieldOk = panel.defield_ok === true || defieldAudit.defield_ok === true;
    const nestedDrives = defieldAudit.nested_nexus_field_on_drives || [];
    const restoreTotals = data?.drive_converter?.restore_plan?.totals || panel.restore_totals || {};

    const defStatus = $("ti-defield-status");
    const defTails = $("ti-defield-tails");
    const defNested = $("ti-defield-nested");
    const defMirror = $("ti-defield-mirror");
    if (defStatus) {
      defStatus.textContent = defieldOk ? "CLEAN" : "BLOCKED";
      defStatus.classList.toggle("ti-ok", defieldOk);
      defStatus.classList.toggle("ti-danger", !defieldOk);
    }
    if (defTails) {
      const tails = defieldAudit.restorable_files ?? restoreTotals.restorable_files;
      defTails.textContent = tails != null ? String(tails) : "—";
    }
    if (defNested) {
      defNested.textContent = nestedDrives.length ? String(nestedDrives.length) : "0";
      defNested.title = nestedDrives.join("\n");
    }
    if (defMirror) {
      defMirror.textContent = defieldAudit.host_mirror_only ? "HOST MIRROR" : "DRIVE OK";
    }
    const nestedList = $("ti-defield-nested-list");
    if (nestedList) {
      nestedList.innerHTML = nestedDrives.length
        ? nestedDrives.map((p) => "<li>" + p + "</li>").join("")
        : "<li class=\"ti-muted\">No nested nexus-field on drives</li>";
    }

    const purgeNestedBtn = $("ti-purge-nested");
    if (purgeNestedBtn) purgeNestedBtn.disabled = !nestedDrives.length;

    const nxt = $("ti-wizard-next");
    if (nxt && (step === "unfield" || step === "arrive")) nxt.disabled = !canAdvance(step);
    const installBtn = $("ti-install-nexus");
    if (installBtn) installBtn.disabled = !(rootReady && defieldOk);
    const commitBtn = $("ti-commit");
    const accept = $("ti-accept-permanent");
    if (commitBtn && accept) commitBtn.disabled = !accept.checked || !defieldOk;
  }

  function renderZnetwork(zn) {
    zn = zn || state?.znetwork || {};
    const offer = zn.offer || {};
    const conn = $("ti-zn-conn");
    if (conn) conn.textContent = offer.connection || zn.status?.connection?.iface || "No live connection";

    const fillList = (id, items) => {
      const ul = $(id);
      if (!ul) return;
      ul.innerHTML = "";
      const list = items && items.length ? items : ["—"];
      list.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        ul.appendChild(li);
      });
    };
    fillList("ti-zn-disable", offer.will_disable);
    fillList("ti-zn-replace", offer.will_replace_with);

    const status = $("ti-zn-status");
    const choiceLbl = $("ti-zn-choice-label");
    if (status) {
      status.textContent = zn.running ? "RUNNING" : zn.choice ? zn.choice.toUpperCase() : "PENDING";
    }
    znChoice = "yes";
    if (choiceLbl) choiceLbl.textContent = "INGRAINED";
    const nxt = $("ti-wizard-next");
    if (nxt && step === "znetwork") nxt.disabled = !canAdvance("znetwork");
  }

  function renderStatus(data) {
    state = data;
    renderRoot(data.root);
    renderDefield(data);

    const ul = data.underlay || {};
    const verdict = $("ti-underlay-verdict");
    const prot = $("ti-protections");
    if (verdict) verdict.textContent = ul.verdict || "—";
    if (prot) {
      const p = ul.protections || {};
      prot.textContent = (p.modules_present != null ? p.modules_present : "—") + " / envelope";
    }
    const op = data.operator || ul.operator || {};
    const plate = op.iron_plate || {};
    const oc = $("ti-operator-conns");
    const oi = $("ti-operator-irq");
    if (oc) oc.textContent = plate.connection_count != null ? String(plate.connection_count) : "—";
    if (oi) {
      const top = (plate.fast_profiles || op.fast_profiles || {}).irq;
      const irqTop = top?.top?.[0];
      oi.textContent = irqTop ? String(irqTop.total || "—") : "—";
    }

    const wrdt = data.wrdt_plan || data.drive_converter?.plan || {};
    const restorePlan = data.drive_converter?.restore_plan || {};
    const dc = data.drive_converter || {};
    const panel = dc.panel || {};
    const totals = wrdt.totals || {};
    const restoreTotals = restorePlan.totals || panel.restore_totals || {};
    const refield = dc.refield || panel.refield || {};
    const refOk = panel.refield_ok || refield.refield_ok;
    const rfs = $("ti-refield-status");
    const rf = $("ti-restore-files");
    const rs = $("ti-restore-status");
    const wf = $("ti-wrdt-files");
    if (rfs) rfs.textContent = refOk ? "SHADOW" : "—";
    if (rf) rf.textContent = restoreTotals.restorable_files != null ? String(restoreTotals.restorable_files) : "—";
    if (rs) {
      rs.textContent = panel.restored ? "DONE" : panel.restore_scanned ? "READY" : "—";
    }
    if (wf) wf.textContent = totals.packable_files != null ? String(totals.packable_files) : "—";

    const promises = refield.promises || [];
    const promEl = $("ti-field-promises");
    if (promEl && promises.length) {
      promEl.innerHTML = promises.slice(0, 5).map((p) => "<li>" + p + "</li>").join("");
    }

    const scanRestoreBtn = $("ti-scan-restore");
    if (scanRestoreBtn) scanRestoreBtn.disabled = !refOk;

    const log = $("ti-wrdt-log");
    const logLines = [];
    if (restorePlan.scans) {
      (restorePlan.scans || []).forEach((s) => {
        const sc = s.scan || {};
        logLines.push("[packed] " + s.root + ": " + (sc.restorable_files ?? "?") + " tail");
      });
    }
    if (wrdt.scans) {
      (wrdt.scans || []).forEach((s) => {
        const sc = s.scan || {};
        logLines.push("[convert] " + s.root + ": " + (sc.packable_files ?? "?") + " packable");
      });
    }
    if (log) {
      log.textContent = logLines.length ? logLines.join("\n") : "Re-field → scan packed → bring back out → audit → scan → convert…";
    }

    const restoreBtn = $("ti-restore-out");
    const hasTail = (restoreTotals.restorable_files || 0) > 0;
    if (restoreBtn) restoreBtn.disabled = !refOk || !panel.restore_scanned || !hasTail;

    const applyBtn = $("ti-apply-wrdt");
    const dryBtn = $("ti-drive-dryrun");
    const scanWrdtBtn = $("ti-scan-wrdt");
    const driveAuditBtn = $("ti-drive-audit");
    const auditOk = panel.audit_ok === true;
    const hasFiles = totals.packable_files > 0;
    const transformReady = defieldOk && auditOk;
    if (applyBtn) applyBtn.disabled = !(transformReady && hasFiles);
    if (dryBtn) dryBtn.disabled = !(transformReady && hasFiles);
    if (scanWrdtBtn) scanWrdtBtn.disabled = !defieldOk;
    if (driveAuditBtn) driveAuditBtn.disabled = !defieldOk;

    renderZnetwork(data.znetwork);

    if (data.committed) {
      setStep("committed");
      return;
    }

    const serverPhase = data.phase || "arrive";
    if (serverPhase === "commit" && stepIndex(step) < stepIndex("transform")) {
      setStep("transform");
    }
  }

  async function apiGet() {
    const r = await fetch(API, { credentials: "same-origin" });
    if (!r.ok) throw new Error("status " + r.status);
    return r.json();
  }

  async function apiPost(path, body) {
    const r = await fetch(API + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok && !j.ok) throw new Error(j.error || "request failed");
    return j;
  }

  async function refresh() {
    try {
      const data = await apiGet();
      renderStatus(data);
    } catch (e) {
      toast("Panel offline — start NEXUS Field first");
    }
  }

  async function acquireRoot(silent) {
    if (!silent) toast("Approve administrator access in the system dialog…");
    try {
      const j = await apiPost("/acquire-root", {});
      if (j.root) renderRoot(j.root);
      if (j.posture) renderStatus(j.posture);
      else await refresh();
      if (j.ok || j.already || rootReady) {
        launchRootDone = true;
        try {
          sessionStorage.setItem(ROOT_SESSION_KEY, "1");
        } catch (_) { /* ignore */ }
        if (!silent) toast("Administrator access granted — this session only");
        const nxt = $("ti-wizard-next");
        if (nxt && step === "root") nxt.disabled = false;
      } else if (!silent) {
        toast(j.error || "Elevation declined");
      }
      return j;
    } catch (e) {
      if (!silent) toast(String(e.message || e));
      return { ok: false, error: String(e.message || e) };
    }
  }

  async function launchAcquireRoot() {
    if (launchRootDone && rootReady) return;
    try {
      if (sessionStorage.getItem(ROOT_SESSION_KEY) === "1") {
        const data = await apiGet();
        renderStatus(data);
        if (rootReady) {
          launchRootDone = true;
          return;
        }
      }
    } catch (_) { /* panel may still be warming */ }
    toast("Launch: one administrator approval (UAC/sudo) for the whole installer…");
    await acquireRoot(true);
    if (rootReady) {
      toast("Administrator access cached — no further prompts this session");
    } else {
      toast("Approve administrator access when ready (step 2 or Grant button)");
    }
  }

  function maybeAutoAcquireRoot() {
    if (rootReady || launchRootDone) return;
    const btn = $("ti-acquire-root");
    if (btn && !btn.dataset.autoTried) {
      btn.dataset.autoTried = "1";
      acquireRoot(false);
    }
  }

  async function runUnfieldAudit(silent) {
    if (!silent) toast("Unfield audit — scanning drives…");
    try {
      const j = await apiPost("/defield-audit", {});
      renderStatus(j.posture || j);
      const ok = j.defield_ok || j.posture?.drive_converter?.panel?.defield_ok;
      if (!silent) toast(ok ? "Unfield clean — ready to install" : j.error || "Unfield blocked");
      const nxt = $("ti-wizard-next");
      if (nxt && step === "unfield") nxt.disabled = !canAdvance("unfield");
    } catch (e) {
      if (!silent) toast(String(e.message || e));
    }
  }

  async function ensureZnetworkIngrained(silent) {
    znChoice = "yes";
    const nxt = $("ti-wizard-next");
    if (nxt && step === "znetwork") nxt.disabled = false;
    if (silent) return;
    try {
      await apiPost("/znetwork-choice", { choice: "yes" });
    } catch (_) { /* offer step may retry */ }
  }

  async function loadZnetworkOffer() {
    toast("Loading ZNetwork replacer plan…");
    try {
      const j = await apiPost("/znetwork-offer", {});
      znLoaded = true;
      if (j.offer) state = { ...(state || {}), znetwork: j };
      renderZnetwork(j);
      await ensureZnetworkIngrained(true);
      try {
        const saved = await apiPost("/znetwork-choice", { choice: "yes" });
        renderStatus(saved.posture || saved);
        toast("ZNetwork ingrained — auto-enabled");
      } catch (e) {
        toast("ZNetwork plan ready");
      }
    } catch (e) {
      toast(String(e.message || e));
    }
  }

  async function saveZnetworkChoice(choice) {
    znChoice = choice;
    document.querySelectorAll(".ti-choice").forEach((btn) => {
      btn.classList.toggle("selected", btn.dataset.znChoice === choice);
    });
    const nxt = $("ti-wizard-next");
    if (nxt && step === "znetwork") nxt.disabled = false;

    toast("Saving choice…");
    try {
      const j = await apiPost("/znetwork-choice", { choice });
      renderStatus(j.posture || j);
      const labels = { yes: "ZNetwork enabled", no: "Native manager kept", skip: "Skipped (not recommended)" };
      toast(labels[choice] || "Choice saved");
    } catch (e) {
      toast(String(e.message || e));
    }
  }

  $("ti-wizard-back")?.addEventListener("click", () => {
    const idx = stepIndex(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  });

  $("ti-wizard-next")?.addEventListener("click", () => {
    const idx = stepIndex(step);
    if (idx < 0 || idx >= STEPS.length - 1) {
      if (step === "commit") {
        $("ti-pane-commit")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      return;
    }
    if (!canAdvance(step)) {
      const hints = {
        root: "Grant administrator access first",
        unfield: "Run unfield audit — drives must be clean before install",
        znetwork: "Loading ZNetwork plan…",
        arrive: "Root and unfield must pass before install",
      };
      toast(hints[step] || "Complete this step first");
      return;
    }
    setStep(STEPS[idx + 1]);
  });

  $("ti-refresh")?.addEventListener("click", refresh);
  $("ti-acquire-root")?.addEventListener("click", acquireRoot);

  $("ti-operator-board")?.addEventListener("click", async () => {
    toast("Scanning Operator — parallel IRQ, DMA, PCI…");
    try {
      const [scanR, plateR] = await Promise.all([
        fetch("/api/field-operator/scan", { credentials: "same-origin" }),
        fetch("/api/field-operator/iron-plate", { credentials: "same-origin" }),
      ]);
      const scan = await scanR.json();
      const plate = await plateR.json();
      const ms = scan.scan?.elapsed_ms ?? scan.scan?.cache?.age_ms;
      const data = await apiGet();
      data.operator = {
        fast_profiles: scan.profiles,
        iron_plate: plate,
        scan: { fast_ms: ms, amazing: true },
        ready: (plate.connection_count ?? 0) > 0,
      };
      renderStatus(data);
      const n = plate.connection_count ?? 0;
      toast(n ? "Operator live — " + n + " wires (" + (ms != null ? ms + "ms" : "cached") + ")" : "Operator scanned");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-accept-permanent")?.addEventListener("change", (e) => {
    const btn = $("ti-commit");
    if (btn) btn.disabled = !e.target.checked || !defieldOk;
  });

  $("ti-install-nexus")?.addEventListener("click", async () => {
    if (!rootReady || !defieldOk) {
      toast("Root and unfield must pass before install");
      return;
    }
    toast("Launching install — uses administrator access from step 2…");
    try {
      await apiPost("/install-nexus", {});
      toast("Install started — tap Refresh when complete");
      setTimeout(refresh, 4000);
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-refield")?.addEventListener("click", async () => {
    toast("Re-fielding — shadow until reboot…");
    try {
      const j = await apiPost("/refield", {});
      renderStatus(j.posture || j);
      toast(j.refield_ok || j.ok ? "Field shadow live — promises today" : j.error || "refield incomplete");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-scan-restore")?.addEventListener("click", async () => {
    toast("Scanning for WRZC / WRDT / ZAC tail files…");
    try {
      const j = await apiPost("/drive-restore-scan", {});
      renderStatus(j.posture || j);
      const n = j.plan?.totals?.restorable_files ?? j.posture?.drive_converter?.restore_plan?.totals?.restorable_files;
      toast(n ? "Found " + n + " tail file(s)" : "No tail formats — sovereign bytes already");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-restore-out")?.addEventListener("click", async () => {
    if (!confirm("Bring all tail formats back out?\n\nRe-field shadow is active.\nWRZC / WRDT / ZAC → sovereign bytes · zero loss.\nShadow map kept until reboot.")) return;
    toast("Restoring sovereign bytes…");
    try {
      const j = await apiPost("/drive-restore", { confirm: true });
      renderStatus(j.posture || j);
      toast(j.ok ? "Tail formats restored — sovereign bytes out" : j.error || "restore failed");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-drive-audit")?.addEventListener("click", async () => {
    toast("Running World_Redata safety audit…");
    try {
      const j = await apiPost("/drive-audit", {});
      renderStatus(j.posture || j);
      toast(j.ok ? "Audit passed" : j.error || "audit check");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-defield-audit")?.addEventListener("click", () => runUnfieldAudit(false));

  $("ti-purge-nested")?.addEventListener("click", async () => {
    if (!confirm("Quarantine nested nexus-field copies on TEAM/KILROY drives?\n\nPre-commit publish stays on host mirror only.")) return;
    toast("Purging nested drive field copies…");
    try {
      const j = await apiPost("/purge-nested-drive", { apply: true, confirm: true });
      renderStatus(j.posture || j);
      toast(j.ok ? "Nested field quarantined" : j.error || "purge incomplete");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-scan-wrdt")?.addEventListener("click", async () => {
    toast("Scanning drive (dry-run)…");
    try {
      const j = await apiPost("/scan-wrdt", {});
      renderStatus(j.posture || j);
      toast("Drive scan complete");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-drive-dryrun")?.addEventListener("click", async () => {
    toast("Dry-run convert — no disk writes…");
    try {
      const j = await apiPost("/drive-convert", { dry_run: true });
      renderStatus(j.posture || j);
      toast("Dry-run complete");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-apply-wrdt")?.addEventListener("click", async () => {
    if (!confirm("Convert all files in-place with World redump (WRDT1)?\n\nSame paths · lossless · non-destructive.\nRequires admin auth once.")) return;
    toast("Converting in-place — authenticate if prompted…");
    try {
      const j = await apiPost("/wrdt-apply", { confirm: true });
      renderStatus(j.posture || j);
      toast(j.ok ? "Drive conversion complete" : j.error || "failed");
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  $("ti-commit")?.addEventListener("click", async () => {
    if (!$("ti-accept-permanent")?.checked) return;
    if (!confirm("Permanent underlay — no off switch. Commit?")) return;
    toast("Committing underlay…");
    try {
      const j = await apiPost("/commit", { confirm: true });
      renderStatus(j.posture || j);
      toast("Underlay committed — permanent");
      const rebootBtn = $("ti-reboot");
      if (rebootBtn) rebootBtn.disabled = false;
    } catch (e) {
      toast(String(e.message || e));
    }
  });

  async function doReboot() {
    if (!confirm("Reboot into KILROY Field now?")) return;
    toast("Rebooting…");
    try {
      await apiPost("/reboot", {});
    } catch (e) {
      toast(String(e.message || e));
    }
  }

  $("ti-reboot")?.addEventListener("click", doReboot);
  $("ti-reboot-committed")?.addEventListener("click", doReboot);

  document.querySelectorAll(".ti-step").forEach((el) => {
    el.addEventListener("click", () => {
      const target = el.dataset.step;
      if (!target || !STEPS.includes(target)) return;
      if (stepIndex(target) <= stepIndex(step)) setStep(target);
    });
  });

  async function boot() {
    await launchAcquireRoot();
    if (location.hash === "#committed") {
      setStep("committed");
    } else {
      setStep(restoreStep());
    }
    await refresh();
  }

  boot().catch(() => refresh());
})();