/**
 * AmmoCode network mesh — polite discovery, HTTP tunnel, friend/block, threat ratings.
 */
(function (global) {
  "use strict";

  const POLL_TUNNEL_MS = 2500;
  let tunnelId = null;
  let tunnelTimer = null;
  let lastDiscover = null;
  let hostEval = null;

  function $(id) {
    return document.getElementById(id);
  }

  function apiBase() {
    return global.AmmoCodeG16?.cfg?.()?.apiBase || "/api/ammocode";
  }

  async function netAction(action, body) {
    const r = await fetch(apiBase(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...body }),
    });
    return r.json();
  }

  function ratingClass(r) {
    const n = r?.rating ?? 0;
    if (n >= 85) return "ok";
    if (n >= 50) return "warn";
    return "bad";
  }

  function renderHostCard(host) {
    if (!host) return "<div class=\"ac-net-muted\">Host evaluation pending…</div>";
    const cls = host.host_score >= 80 ? "ok" : host.host_score >= 50 ? "warn" : "bad";
    const findings = (host.findings || []).slice(0, 4).map((f) =>
      `<div class="ac-net-finding ${f.severity || ""}">${f.id}${f.peer ? ` · ${f.peer}` : ""}${f.count != null ? ` (${f.count})` : ""}</div>`,
    ).join("");
    return [
      `<div class="ac-net-host-score ${cls}">This host: <strong>${host.host_score}/100</strong> · ${host.host_label}</div>`,
      `<div class="ac-net-muted">${host.hostname || ""} · ${(host.local_ips || []).join(", ")}</div>`,
      findings || '<div class="ac-net-muted">No hostile findings</div>',
    ].join("");
  }

  function renderHostRow(h) {
    const t = h.threat || {};
    const cls = ratingClass(t);
    const net = h.network || t.network || "local";
    return `<div class="ac-net-host" data-host="${h.host}" data-port="${h.port || 9555}">`
      + `<span class="ac-net-rating ${cls}">${t.rating ?? "?"}</span>`
      + `<span class="ac-net-addr">${h.host}:${h.port || 9555}</span>`
      + `<span class="ac-net-verdict">${t.verdict || ""} · ${net}</span>`
      + `<span class="ac-net-actions">`
      + `<button type="button" class="ac-net-friend" data-ip="${h.host}" title="Add friend">+F</button>`
      + `<button type="button" class="ac-net-block" data-ip="${h.host}" title="Block">✕</button>`
      + `<button type="button" class="ac-net-tunnel" data-host="${h.host}" data-port="${h.port || 9555}" title="HTTP tunnel">⇄</button>`
      + `</span></div>`;
  }

  function renderLists(lists) {
    const f = (lists?.friends || []).map((ip) =>
      `<span class="ac-net-chip ok">${ip} <button type="button" data-rm-friend="${ip}">×</button></span>`,
    ).join("") || '<span class="ac-net-muted">none</span>';
    const b = (lists?.blocks || []).map((ip) =>
      `<span class="ac-net-chip bad">${ip} <button type="button" data-rm-block="${ip}">×</button></span>`,
    ).join("") || '<span class="ac-net-muted">none</span>';
    return `<div class="ac-net-lists"><div>Friends: ${f}</div><div>Blocks: ${b}</div></div>`;
  }

  function bindPanel(el) {
    el.querySelector("#ac-net-discover")?.addEventListener("click", async () => {
      const j = await netAction("network_discover", { force: false });
      lastDiscover = j;
      const list = el.querySelector("#ac-net-hosts");
      if (list) {
        if (j.throttled) {
          list.innerHTML = `<div class="ac-net-muted">${j.message}</div>`;
        } else {
          list.innerHTML = (j.hosts || []).map(renderHostRow).join("")
            || '<div class="ac-net-muted">No AmmoCode peers on LAN (try again later)</div>';
          bindPanel(el);
        }
      }
      global.AmmoCodeEditor?.toast?.(j.throttled ? j.message : `Found ${j.found_count || 0} host(s)`, !j.throttled);
    });
    el.querySelector("#ac-net-eval-host")?.addEventListener("click", async () => {
      hostEval = await netAction("host_evaluate", { force: true });
      const card = el.querySelector("#ac-net-host-card");
      if (card) card.innerHTML = renderHostCard(hostEval);
    });
    el.querySelector("#ac-net-add-friend")?.addEventListener("click", async () => {
      const ip = el.querySelector("#ac-net-ip-input")?.value?.trim();
      if (!ip) return;
      await netAction("network_friend_add", { entry: ip });
      await refreshPanel(el);
    });
    el.querySelector("#ac-net-add-block")?.addEventListener("click", async () => {
      const ip = el.querySelector("#ac-net-ip-input")?.value?.trim();
      if (!ip) return;
      await netAction("network_block_add", { entry: ip });
      await refreshPanel(el);
    });
    el.querySelectorAll(".ac-net-friend").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await netAction("network_friend_add", { entry: btn.dataset.ip });
        await refreshPanel(el);
      });
    });
    el.querySelectorAll(".ac-net-block").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await netAction("network_block_add", { entry: btn.dataset.ip });
        await refreshPanel(el);
      });
    });
    el.querySelectorAll("[data-rm-friend]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await netAction("network_friend_remove", { entry: btn.dataset.rmFriend });
        await refreshPanel(el);
      });
    });
    el.querySelectorAll("[data-rm-block]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await netAction("network_block_remove", { entry: btn.dataset.rmBlock });
        await refreshPanel(el);
      });
    });
    el.querySelectorAll(".ac-net-tunnel").forEach((btn) => {
      btn.addEventListener("click", () => tunnelConnect(btn.dataset.host, Number(btn.dataset.port) || 9555));
    });
  }

  async function refreshPanel(el) {
    const st = await netAction("network_status", {});
    if (st.host) hostEval = st.host;
    const card = el?.querySelector("#ac-net-host-card");
    if (card) card.innerHTML = renderHostCard(hostEval);
    const listsEl = el?.querySelector("#ac-net-lists");
    if (listsEl) listsEl.innerHTML = renderLists(st.lists);
    bindPanel(el);
  }

  function renderPanel(el) {
    if (!el) return;
    el.innerHTML = [
      '<div class="ac-side-head">Network mesh</div>',
      '<div class="ac-flyout-body ac-net-body">',
      '<p class="ac-flyout-desc">Polite LAN discovery (rate-limited, not spammy). Local + open peers via HTTP tunnel. Friend/block lists drive threat ratings.</p>',
      '<div id="ac-net-host-card"></div>',
      '<div class="ac-net-actions-row">',
      '<button type="button" id="ac-net-discover">Discover LAN hosts</button>',
      '<button type="button" id="ac-net-eval-host">Re-scan this host</button>',
      '</div>',
      '<label class="ac-collab-field">IP / host<input type="text" id="ac-net-ip-input" placeholder="192.168.1.42" /></label>',
      '<div class="ac-net-actions-row">',
      '<button type="button" id="ac-net-add-friend">Add friend</button>',
      '<button type="button" id="ac-net-add-block">Block</button>',
      '</div>',
      '<div id="ac-net-lists"></div>',
      '<div class="ac-side-head" style="margin-top:8px">Discovered</div>',
      '<div id="ac-net-hosts" class="ac-net-hosts"><div class="ac-net-muted">Click Discover — max 1 scan / 2 min</div></div>',
      '<div id="ac-net-tunnel-status" class="ac-net-muted"></div>',
      '</div>',
    ].join("");
    refreshPanel(el);
  }

  async function ensureTunnelId() {
    if (tunnelId) return tunnelId;
    const j = await netAction("tunnel_register", {});
    tunnelId = j.tunnel_id;
    return tunnelId;
  }

  function stopTunnelPoll() {
    if (tunnelTimer) clearInterval(tunnelTimer);
    tunnelTimer = null;
  }

  function startTunnelPoll(onMessage) {
    stopTunnelPoll();
    tunnelTimer = setInterval(async () => {
      if (!tunnelId) return;
      try {
        const j = await netAction("tunnel_poll", { tunnel_id: tunnelId, timeout_ms: 500 });
        (j.messages || []).forEach((m) => onMessage?.(m));
      } catch (_) {}
    }, POLL_TUNNEL_MS);
  }

  async function tunnelConnect(host, port) {
    const tid = await ensureTunnelId();
    const j = await netAction("tunnel_connect", {
      local_id: tid,
      remote_host: host,
      remote_port: port,
    });
    const st = $("ac-net-tunnel-status");
    if (!j.ok) {
      if (st) st.textContent = `Tunnel blocked: ${j.error} (rating ${j.threat?.rating ?? "?"})`;
      global.AmmoCodeEditor?.toast?.(j.error || "tunnel failed", false);
      return;
    }
    if (st) st.textContent = `HTTP tunnel → ${host}:${port} · rating ${j.threat?.rating}/100`;
    startTunnelPoll((m) => {
      if (st) st.textContent = `Tunnel msg from ${m.from || "peer"}`;
    });
    global.AmmoCodeEditor?.toast?.(`HTTP tunnel to ${host}`, true);
    return j;
  }

  async function init() {
    hostEval = await netAction("host_evaluate", {});
    await ensureTunnelId();
    const pill = $("ac-net-pill");
    if (pill && hostEval?.host_score != null) {
      pill.textContent = `host: ${hostEval.host_score}`;
      pill.className = "pill " + (hostEval.host_score >= 80 ? "ok" : hostEval.host_score >= 50 ? "warn" : "bad");
      pill.title = `Host threat score ${hostEval.host_score}/100`;
    }
  }

  global.AmmoCodeNetwork = {
    init,
    renderPanel,
    refreshPanel,
    netAction,
    tunnelConnect,
    lastDiscover: () => lastDiscover,
    hostEval: () => hostEval,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);