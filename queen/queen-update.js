/**
 * Queen browser — NXF/GitHub update chip (online only).
 */
(function () {
  "use strict";

  let state = null;
  let applying = false;
  let pollTimer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function setBusy(busy, message) {
    const btn = $("qb-update-btn");
    const detail = $("qb-update-detail");
    if (btn) {
      btn.disabled = !!busy;
      btn.classList.toggle("qb-update-busy", !!busy);
      if (busy) btn.textContent = "UPDATING…";
    }
    if (detail && message) {
      detail.textContent = message;
      detail.classList.add("qb-update-ready");
    }
  }

  async function checkUpdate(force = false) {
    const btn = $("qb-update-btn");
    const detail = $("qb-update-detail");
    if (!btn || !detail || applying) return;
    if (!force && state && !state.update_available && !state.update_in_progress) {
      btn.textContent = `v${state.current}`;
      return;
    }
    if (force) detail.textContent = "Checking GitHub…";
    try {
      const res = await fetch(`/api/update/status?force=${force ? 1 : 0}`, { cache: "no-store" });
      const data = await res.json();
      state = data;
      btn.classList.remove("qb-update-busy");
      btn.disabled = false;
      if (data.update_in_progress) {
        btn.textContent = "UPDATING…";
        btn.classList.add("qb-update-busy");
        btn.disabled = true;
        detail.textContent = data.message || "NXF install running…";
        detail.classList.add("qb-update-ready");
        startPoll();
        return;
      }
      if (!data.ok) {
        btn.textContent = data.current ? `v${data.current}` : "v?";
        detail.textContent = data.error || "Offline";
        return;
      }
      if (data.update_available) {
        btn.classList.add("qb-update-ready");
        detail.classList.add("qb-update-ready");
        btn.textContent = "UPDATE";
        detail.textContent = `${data.previous} → ${data.latest} · ${data.product || "AmmoOS"}`;
      } else {
        btn.classList.remove("qb-update-ready");
        detail.classList.remove("qb-update-ready");
        btn.textContent = `v${data.current}`;
        detail.textContent = `Current · local NXF · ${data.latest || data.current}`;
        btn.title = "Up to date — NXF manifest checked on loopback when online.";
      }
    } catch {
      btn.textContent = state?.current ? `v${state.current}` : "UPDATE";
      detail.textContent = "Offline — check when connected";
    }
  }

  async function pollStatus() {
    try {
      const res = await fetch("/api/update/status", { cache: "no-store" });
      const data = await res.json();
      state = data;
      if (data.needs_sudo) {
        setBusy(true, "Administrator password required");
        await fetch("/api/update/sudo-prompt", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        return true;
      }
      if (data.update_in_progress) {
        setBusy(true, data.message || "Update in progress…");
        return true;
      }
      applying = false;
      setBusy(false);
      await checkUpdate(true);
      if (data.latest && data.latest !== data.current) {
        location.reload();
      }
      return false;
    } catch {
      return applying;
    }
  }

  function startPoll() {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
      const busy = await pollStatus();
      if (!busy) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    }, 2500);
  }

  async function applyUpdate() {
    if (applying || state?.update_in_progress) {
      startPoll();
      return;
    }
    if (!state?.update_available) {
      await checkUpdate(true);
      return;
    }
    applying = true;
    setBusy(true, `Installing ${state.previous} → ${state.latest}…`);
    try {
      const res = await fetch("/api/update/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await res.json();
      if (res.status === 202 || data.started) {
        setBusy(true, data.message || "NXF release installer running…");
        startPoll();
        return;
      }
      if (data.already_current) {
        applying = false;
        await checkUpdate(true);
        return;
      }
      applying = false;
      $("qb-update-detail").textContent = data.message || data.error || "Update not applied";
    } catch {
      setBusy(true, "Restarting services…");
      startPoll();
    }
  }

  function bind() {
    $("qb-update-btn")?.addEventListener("click", () => {
      if (applying || state?.update_in_progress) {
        pollStatus();
        return;
      }
      if (state?.update_available) applyUpdate();
      else checkUpdate(true);
    });
    checkUpdate(false);
    setInterval(() => checkUpdate(false), 3600000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();