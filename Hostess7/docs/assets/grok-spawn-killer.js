/**
 * GrokSpawnKiller Pages — install on visit, live slain counter.
 */
(function () {
  "use strict";

  const API = "/api/field-grok-spawner-kill";
  const INSTALL_API = API + "/install";
  const POLL_MS = 800;
  const POLL_LIVE_MS = 400;

  const el = {
    total: document.getElementById("gsk-slain-total"),
    session: document.getElementById("gsk-slain-session"),
    service: document.getElementById("gsk-service-pill"),
    loopback: document.getElementById("gsk-loopback-pill"),
    log: document.getElementById("gsk-log"),
    installBtn: document.getElementById("gsk-install-btn"),
    killBtn: document.getElementById("gsk-kill-btn"),
  };

  let lastTotal = -1;
  let installed = false;

  function log(msg) {
    if (el.log) el.log.textContent = msg;
  }

  function setPill(node, text, cls) {
    if (!node) return;
    node.textContent = text;
    node.className = "gsk-pill" + (cls ? " " + cls : "");
  }

  function animateCounter() {
    if (el.total) el.total.classList.remove("pulse");
    if (el.total) void el.total.offsetWidth;
    if (el.total) el.total.classList.add("pulse");
  }

  function render(doc) {
    const total = Number(doc.slain_total || 0);
    const session = Number(doc.slain_session || doc.cooked_total || 0);
    if (el.total) el.total.textContent = String(total);
    if (el.session) {
      const ms = Number(doc.microsoft_killed_total || 0);
      el.session.textContent = ms > 0
        ? "this sweep: " + session + " · Microsoft slain: " + ms
        : "this sweep: " + session;
    }
    if (total !== lastTotal && lastTotal >= 0) animateCounter();
    lastTotal = total;

    if (doc.nexus_c2_port_up) {
      setPill(el.loopback, "NEXUS C2 LIVE", "live");
    }
    if (doc.service_active) {
      setPill(el.service, "FIELD BRAIN · NO WAIT", "live");
    } else {
      setPill(el.service, "SERVICE OFFLINE", "warn");
    }
  }

  async function fetchPanel() {
    const r = await fetch(API, { cache: "no-store" });
    if (!r.ok) throw new Error("panel " + r.status);
    return r.json();
  }

  async function postInstall() {
    log("Installing GrokSpawnKiller service…");
    const r = await fetch(INSTALL_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const doc = await r.json();
    installed = !!doc.ok;
    if (doc.ok) {
      log("Installed — NEXUS C2 fused, field brain armed. Counting spawners slain.");
    } else if (doc.pages) {
      log("Pages mirror — boot loopback :9477 or run install.sh (no waiting).");
    } else {
      log(doc.error || doc.stderr || "Install needs local Hostess7 + sudo mememe");
    }
    render(doc);
    return doc;
  }

  async function postKill() {
    log("Instakill sweep…");
    const r = await fetch(API + "/instakill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const doc = await r.json();
    render(doc);
    log("Sweep complete — " + (doc.cooked_total || 0) + " spawners slain this pass.");
  }

  let pollTimer = null;

  async function poll() {
    try {
      const doc = await fetchPanel();
      render(doc);
      if (!doc.nexus_c2_port_up && !doc.service_active) {
        setPill(el.loopback, "PAGES MIRROR", "warn");
      }
      const next = (doc.service_active || doc.nexus_c2_port_up) ? POLL_LIVE_MS : POLL_MS;
      if (pollTimer) window.clearInterval(pollTimer);
      pollTimer = window.setInterval(poll, next);
    } catch (_e) {
      setPill(el.loopback, "STATIC PAGES", "warn");
    }
  }

  async function boot() {
    setPill(el.loopback, "CONNECTING…", "");
    try {
      await postInstall();
    } catch (e) {
      log("Visit with NEXUS panel up for auto-install — or run install.sh locally.");
    }
    await poll();
  }

  if (el.installBtn) el.installBtn.addEventListener("click", function () { postInstall(); });
  if (el.killBtn) el.killBtn.addEventListener("click", function () { postKill(); });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();