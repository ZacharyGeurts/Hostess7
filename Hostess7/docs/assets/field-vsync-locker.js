(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  async function api(path, method) {
    const res = await fetch(path, {
      method: method || "GET",
      headers: { Accept: "application/json" },
    });
    return res.json();
  }

  function fmt(obj) {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (_e) {
      return String(obj);
    }
  }

  function setPill(doc) {
    const pill = $("vl-status-pill");
    if (!pill) return;
    const rogues = (doc.last_rogues && doc.last_rogues.rogue_count) || 0;
    const guard = doc.guard || {};
    if (rogues > 0) {
      pill.textContent = "ROGUE " + rogues;
      pill.className = "vl-pill bad";
    } else if (guard.running) {
      pill.textContent = "PATROL";
      pill.className = "vl-pill ok";
    } else {
      pill.textContent = "IDLE";
      pill.className = "vl-pill warn";
    }
  }

  async function refresh() {
    const doc = await api("/api/vsync-locker");
    if (doc.motto && $("vl-motto")) $("vl-motto").textContent = doc.motto;
    setPill(doc);
    if ($("vl-guard")) $("vl-guard").textContent = fmt(doc.guard || {});
    if ($("vl-lock")) $("vl-lock").textContent = fmt({ locked: doc.locked, displays: doc.displays });
    if ($("vl-drift")) $("vl-drift").textContent = fmt(doc.anti_perfect_sync || {});
    if ($("vl-rogues")) $("vl-rogues").textContent = fmt(doc.last_rogues || doc.last_patrol || {});
  }

  function bind(id, path, method) {
    const el = $(id);
    if (!el) return;
    el.addEventListener("click", async () => {
      el.disabled = true;
      try {
        await api(path, method || "POST");
        await refresh();
      } finally {
        el.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bind("vl-btn-lock", "/api/vsync-locker/lock", "POST");
    bind("vl-btn-patrol", "/api/vsync-locker/patrol", "POST");
    bind("vl-btn-launch", "/api/vsync-locker/launch", "POST");
    bind("vl-btn-drift", "/api/vsync-locker/drift", "POST");
    refresh();
    setInterval(refresh, 5000);
  });
})();