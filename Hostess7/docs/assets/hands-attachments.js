(function () {
  "use strict";

  const API_HANDS = "/api/hostess7/hands";
  const API_ATTACH = "/api/hostess7/attachments";
  const API_DISPATCH = "/api/hostess7/body/dispatch";

  let lastHands = null;
  let lastAttach = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  async function getJson(url) {
    const res = await fetch(url, { credentials: "same-origin" });
    return res.json();
  }

  function drawHand(canvas, side, wf) {
    if (!canvas || !wf) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width = canvas.clientWidth || 280;
    const h = canvas.height = canvas.clientHeight || 220;
    ctx.clearRect(0, 0, w, h);
    const hand = wf.hands?.[side];
    if (!hand) return;
    const cx = w * 0.5;
    const cy = h * 0.28;
    const scale = Math.min(w, h) * 0.42;
    const palm = hand.palm || { x: side === "left" ? -0.26 : 0.26, z: 0.72 };
    const px = cx + (palm.x || 0) * scale * (side === "left" ? 1 : 1);
    const py = cy + 0.1 * scale;

    ctx.strokeStyle = side === "left" ? "#38bdf8" : "#a78bfa";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    const tips = hand.tips || {};
    const order = ["thumb", "index", "middle", "ring", "pinky"];
    for (const finger of order) {
      const t = tips[finger];
      if (!t) continue;
      const tx = cx + (t.x || 0) * scale;
      const ty = cy + (t.z || 0) * scale * 0.8;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      const flex = t.flex || 0;
      const r = 4 + Math.min(8, flex * 0.06);
      ctx.fillStyle = flex > 40 ? "#f0d060" : ctx.strokeStyle;
      ctx.beginPath();
      ctx.arc(tx, ty, r, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(px, py, 10, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px system-ui,sans-serif";
    ctx.textAlign = "center";
    ctx.fillText((hand.grip || "open") + " · " + side, cx, h - 12);
  }

  function renderHands(doc) {
    lastHands = doc;
    const wf = doc.wireframe || doc;
    drawHand($("ha-canvas-left"), "left", wf);
    drawHand($("ha-canvas-right"), "right", wf);
    const prof = Math.round((doc.proficiency || 0) * 100);
    $("ha-hand-prof").textContent = `Hand proficiency ${prof}% · ${doc.fluent ? "fluent" : "training"}`;
    $("ha-hand-bar").style.width = prof + "%";
  }

  function renderAttachments(doc) {
    lastAttach = doc;
    const list = $("ha-attach-list");
    if (!list) return;
    const items = doc.attachments || [];
    list.innerHTML = items.map((a) => {
      const p = Math.round((a.proficiency || 0) * 100);
      const mounted = a.mounted || a.mount_point;
      return `<article class="ha-attach ${mounted ? "mounted" : ""}" data-id="${esc(a.id)}">
        <h3>${esc(a.label)}</h3>
        <div class="meta">${esc(a.kind)} · mount ${esc(mounted || a.default_mount || "—")} · ${p}% ${a.mastered ? "mastered" : a.fluent ? "fluent" : ""}</div>
        <div class="ha-bar"><span style="width:${p}%"></span></div>
        <div class="ha-attach-row">
          <button type="button" data-act="mount" data-id="${esc(a.id)}">Mount</button>
          <button type="button" data-act="look" data-id="${esc(a.id)}">Look</button>
          <button type="button" data-act="learn" data-id="${esc(a.id)}">Learn</button>
          <button type="button" data-act="wield" data-id="${esc(a.id)}">Wield</button>
          <button type="button" data-act="unmount" data-id="${esc(a.id)}">Unmount</button>
        </div>
      </article>`;
    }).join("");

    list.querySelectorAll("button[data-act]").forEach((btn) => {
      btn.addEventListener("click", () => onAttachAction(btn.dataset.act, btn.dataset.id));
    });
  }

  function log(msg) {
    const el = $("ha-log");
    if (!el) return;
    const line = document.createElement("div");
    line.textContent = new Date().toLocaleTimeString() + " — " + msg;
    el.prepend(line);
    while (el.children.length > 8) el.removeChild(el.lastChild);
  }

  async function refresh() {
    try {
      const [hands, attach] = await Promise.all([getJson(API_HANDS), getJson(API_ATTACH)]);
      if (hands.ok !== false) renderHands(hands);
      if (attach.ok !== false) renderAttachments(attach);
    } catch (e) {
      log("refresh failed: " + e.message);
    }
  }

  async function setGrip(side, grip) {
    await postJson(API_DISPATCH, { action: "hands", subaction: "grip", side, grip });
    log(`Grip ${grip} on ${side}`);
    await refresh();
  }

  async function onAttachAction(act, id) {
    const map = {
      mount: { action: "attachment", subaction: "mount", id },
      unmount: { action: "attachment", subaction: "unmount", id },
      look: { action: "attachment", subaction: "inspect", id },
      learn: { action: "attachment", subaction: "learn", id, ticks: 32 },
      wield: { action: "attachment", subaction: "wield", id },
    };
    const body = map[act];
    if (!body) return;
    const row = await postJson(API_DISPATCH, body);
    log(`${act} ${id}: ${row.ok ? "ok" : row.error || "fail"}${row.match?.score != null ? " match " + row.match.score : ""}${row.proficiency != null ? " prof " + Math.round(row.proficiency * 100) + "%" : ""}`);
    await refresh();
  }

  function bindGrips(containerId, side) {
    const row = $(containerId);
    if (!row) return;
    row.querySelectorAll("button[data-grip]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        row.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        await setGrip(side, btn.dataset.grip);
      });
    });
  }

  async function trainHands() {
    await postJson(API_DISPATCH, { action: "hands", subaction: "train", ticks: 24 });
    log("Hand training burst");
    await refresh();
  }

  async function registerAttachment() {
    const label = $("ha-reg-label")?.value?.trim();
    if (!label) return;
    await postJson(API_DISPATCH, {
      action: "attachment",
      subaction: "register",
      label,
      kind: $("ha-reg-kind")?.value || "custom",
      default_mount: $("ha-reg-mount")?.value || "hand_r",
    });
    log("Registered: " + label);
    $("ha-reg-label").value = "";
    await refresh();
  }

  function init() {
    bindGrips("ha-grip-left", "left");
    bindGrips("ha-grip-right", "right");
    $("ha-train-hands")?.addEventListener("click", trainHands);
    $("ha-refresh")?.addEventListener("click", refresh);
    $("ha-reg-btn")?.addEventListener("click", registerAttachment);
    refresh();
    setInterval(refresh, 8000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();