/**
 * Field Talk — minimal browser for whole NEXUS on field drive.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let tools = [];
  let lastStatus = null;

  function log(msg) {
    const el = $("out");
    if (!el) return;
    el.textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
  }

  function appendLog(msg) {
    const el = $("out");
    if (!el) return;
    el.textContent += "\n" + (typeof msg === "string" ? msg : JSON.stringify(msg, null, 2));
  }

  async function api(path, opts) {
    const res = await fetch(path, opts);
    return res.json();
  }

  function renderPills(st) {
    const el = $("pills");
    if (!el || !st) return;
    const m = st.manifest || {};
    const pills = [
      ["Drive", st.drive_mounted ? "mounted" : "offline"],
      ["Whole system", st.whole_system_on_drive ? "on drive" : "not published"],
      ["State", (st.state_dir || "").split("/").slice(-2).join("/")],
      ["System files", String(m.system_files || "—")],
      ["ASM", st.field_outside_talk?.asm_ready ? "ready" : "socket"],
      ["Firewall", st.firewall || "—"],
    ];
    el.innerHTML = pills
      .map(([k, v]) => {
        const cls = /offline|not|fail/i.test(String(v)) ? "pill pill--warn" : "pill";
        return `<div class="${cls}"><span>${k}</span> <strong>${v}</strong></div>`;
      })
      .join("");
  }

  async function loadTools() {
    try {
      const j = await api("/api/field-outside-talk");
      tools = j.tools || [];
      const sel = $("tool");
      if (!sel) return;
      sel.innerHTML = tools.map((t) => `<option value="${t.id}">${t.label}</option>`).join("");
      sel.addEventListener("change", () => {
        const t = tools.find((x) => x.id === sel.value);
        if (t && $("port")) $("port").value = String(t.port || 22);
      });
      if (tools[0] && $("port")) $("port").value = String(tools[0].port || 22);
    } catch (e) {
      log("Tools load failed: " + e.message);
    }
  }

  async function loadStatus() {
    try {
      lastStatus = await api("/api/field-drive");
      renderPills(lastStatus);
      log({
        panel: lastStatus.panel_url,
        talk_inbox: lastStatus.talk?.inbox_pending,
        version: lastStatus.version,
      });
    } catch (e) {
      log("Status failed: " + e.message);
    }
  }

  async function talk(op, extra) {
    const body = {
      op,
      tool: $("tool")?.value,
      host: ($("host")?.value || "").trim(),
      port: parseInt($("port")?.value || "0", 10),
      username: ($("user")?.value || "").trim(),
      ...extra,
    };
    if (!body.host) {
      log("Host required.");
      return;
    }
    log((op === "probe" ? "Probing" : "Connecting") + "…");
    try {
      const j = await api("/api/field-drive/talk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      log(j);
      await loadStatus();
    } catch (e) {
      log("Talk failed: " + e.message);
    }
  }

  $("connect")?.addEventListener("click", () => talk("connect"));
  $("probe")?.addEventListener("click", () => talk("probe"));
  $("publish")?.addEventListener("click", async () => {
    log("Publishing whole system to field drive…");
    try {
      const j = await api("/api/field-drive/talk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ op: "publish", full: true }),
      });
      log(j);
      await loadStatus();
    } catch (e) {
      log("Publish failed: " + e.message);
    }
  });
  $("refresh-status")?.addEventListener("click", (e) => {
    e.preventDefault();
    loadStatus();
  });

  loadTools();
  loadStatus();
  setInterval(loadStatus, 60000);
})();