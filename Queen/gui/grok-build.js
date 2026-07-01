(function () {
  "use strict";

  const API = "/api/grok-build";
  const BOOT_API = "/api/queen-boot";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function appendMsg(role, text) {
    const t = $("gb-transcript");
    if (!t) return;
    const p = document.createElement("p");
    p.className = `gb-msg gb-msg--${role}`;
    p.textContent = text;
    t.appendChild(p);
    t.scrollTop = t.scrollHeight;
  }

  async function fetchPost(action, extra) {
    const r = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function fetchStatus() {
    const r = await fetch(API, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  function render(doc) {
    const page = doc.branded_page || {};
    $("gb-eyebrow").textContent = page.eyebrow || "Queen · xAI secure channel";
    $("gb-title").textContent = page.title || doc.title || "Grok Build Inside Queen";
    $("gb-motto").textContent = doc.motto || page.motto || "";
    $("gb-partner").textContent = doc.partner || "xAI / X — branded page permitted";

    const sec = $("gb-secure");
    if (sec) {
      sec.textContent = `Secure channel: ${doc.secure_channel ? "ACTIVE" : "INACTIVE"}`;
      sec.classList.toggle("ok", !!doc.secure_channel);
      sec.classList.toggle("warn", !doc.secure_channel);
    }
    const acp = doc.acp || {};
    const acpEl = $("gb-acp");
    if (acpEl) {
      acpEl.textContent = `ACP ${acp.ws_url || "—"}: ${acp.reachable ? "REACHABLE" : "standby"}`;
      acpEl.classList.toggle("ok", !!acp.reachable);
      acpEl.classList.toggle("warn", !acp.reachable);
    }

    const env = $("gb-env");
    if (env) {
      const m = doc.secure_channel_env || {};
      env.innerHTML = Object.entries(m)
        .map(([k, v]) => `<li class="${v ? "on" : ""}">${esc(k)}: ${v ? "on" : "off"}</li>`)
        .join("");
    }
    const hosts = $("gb-hosts");
    if (hosts) {
      hosts.innerHTML = (doc.allowed_hosts || []).map((h) => `<li>${esc(h)}</li>`).join("");
    }
  }

  async function refresh() {
    const doc = await fetchStatus();
    render(doc);
  }

  $("gb-refresh")?.addEventListener("click", () => refresh().catch((e) => appendMsg("system", e.message)));
  $("gb-start-acp")?.addEventListener("click", async () => {
    try {
      const j = await fetchPost("acp_start");
      appendMsg("system", j.ok ? `ACP started pid ${j.pid}` : `ACP failed: ${j.error || "unknown"}`);
      await refresh();
    } catch (e) {
      appendMsg("system", e.message);
    }
  });
  $("gb-send")?.addEventListener("click", async () => {
    const text = ($("gb-input")?.value || "").trim();
    if (!text) return;
    appendMsg("user", text);
    $("gb-input").value = "";
    try {
      const doc = await fetchStatus();
      if (!doc.secure_channel) {
        appendMsg("system", "Enable secure channel env (NEXUS_AI_SECURE_CHANNEL + QUEEN_GROK_BUILD_SECURE).");
        return;
      }
      if (!doc.acp?.reachable) {
        appendMsg("system", "Start loopback ACP first — grok agent serve on 127.0.0.1:2419");
        return;
      }
      appendMsg("grok", "[ACP] Prompt queued — connect WebSocket client to " + (doc.acp.ws_url || "ws://127.0.0.1:2419"));
    } catch (e) {
      appendMsg("system", e.message);
    }
  });

  async function bootPost(action, extra) {
    const r = await fetch(BOOT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    if (!r.ok) throw new Error(`boot HTTP ${r.status}`);
    return r.json();
  }

  $("gb-login")?.addEventListener("click", async () => {
    try {
      const j = await bootPost("login");
      appendMsg("system", j.ok ? "Grok login flow started — complete auth in browser/device." : `Login: ${j.error || "failed"}`);
      await refresh();
    } catch (e) {
      appendMsg("system", e.message);
    }
  });
  $("gb-rebuild")?.addEventListener("click", async () => {
    appendMsg("system", "Rebuild started — queen-build run-all…");
    try {
      const j = await bootPost("rebuild");
      appendMsg("system", j.ok ? "Rebuild complete." : `Rebuild failed rc=${j.returncode}`);
    } catch (e) {
      appendMsg("system", e.message);
    }
  });
  $("gb-reboot")?.addEventListener("click", async () => {
    try {
      const j = await bootPost("reboot");
      appendMsg("system", j.ok ? `Queen reboot pid ${j.pid}` : `Reboot: ${j.error || "failed"}`);
    } catch (e) {
      appendMsg("system", e.message);
    }
  });

  refresh().catch((e) => appendMsg("system", `Panel API offline: ${e.message}`));
})();