/**
 * ZNetwork Secure Vault — push-only ZISV peer transfer UI.
 */
(function () {
  "use strict";

  const state = { panel: null, queue: null, registry: null };

  function $(id) {
    return document.getElementById(id);
  }

  function toast(msg, ok) {
    const el = $("zv-toast");
    if (!el) return;
    el.textContent = msg;
    el.style.borderColor = ok === false ? "rgba(248,113,113,0.5)" : "rgba(56,189,248,0.35)";
    el.classList.add("show");
    setTimeout(function () {
      el.classList.remove("show");
    }, 3200);
  }

  function fmtBytes(n) {
    n = Number(n) || 0;
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    return (n / 1048576).toFixed(2) + " MB";
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(path, {
      method: opts.method || "GET",
      credentials: "same-origin",
      headers: opts.body ? { "Content-Type": "application/json" } : undefined,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const doc = await res.json().catch(function () {
      return { ok: false, error: "invalid_json" };
    });
    if (!res.ok && doc.ok !== false) doc.ok = false;
    return doc;
  }

  function renderQueue(items) {
    const box = $("zv-queue");
    if (!box) return;
    if (!items || !items.length) {
      box.innerHTML = '<p class="zv-empty">No pending offers — ZNetwork does not answer requests.</p>';
      return;
    }
    box.innerHTML = items
      .map(function (row) {
        const hostile = row.hostile ? ' <span style="color:var(--zv-bad)">⚠ threat</span>' : "";
        return (
          '<article class="zv-offer" data-id="' +
          esc(row.transfer_id) +
          '">' +
          '<div class="zv-offer-head">' +
          '<span class="zv-offer-name">' +
          esc(row.filename) +
          hostile +
          "</span>" +
          '<span class="zv-offer-meta">' +
          fmtBytes(row.size) +
          "</span></div>" +
          '<div class="zv-offer-meta">From ' +
          esc(row.sender_label || row.sender_wire) +
          " · " +
          esc(row.received_at || "") +
          "</div>" +
          '<div class="zv-actions">' +
          '<button type="button" class="zv-btn zv-btn--ok" data-act="accept">Accept</button>' +
          '<button type="button" class="zv-btn zv-btn--bad" data-act="reject">Reject</button>' +
          "</div></article>"
        );
      })
      .join("");

    box.querySelectorAll("[data-act]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const offer = btn.closest(".zv-offer");
        const id = offer && offer.dataset.id;
        const act = btn.dataset.act;
        if (!id) return;
        if (act === "accept") acceptOffer(id);
        else rejectOffer(id);
      });
    });
  }

  function renderRegistry(reg) {
    state.registry = reg;
    const profile = reg && reg.profile;
    const registered = !!(reg && reg.registered && profile);
    const form = $("zv-register-form");
    const view = $("zv-registered-view");
    if (registered) {
      if (form) form.classList.add("zv-hidden");
      if (view) view.classList.remove("zv-hidden");
      $("zv-reg-full").textContent = profile.full_name || "—";
      $("zv-reg-display").textContent = profile.display_name || "—";
      $("zv-reg-region").textContent = profile.region || "—";
      $("zv-reg-score").textContent = String(profile.composite_score != null ? profile.composite_score : "—");
      $("zv-reg-id").textContent = profile.operator_id || "—";
      const label = $("zv-label");
      if (label && !label.value) label.value = profile.display_name || "";
    } else {
      if (form) form.classList.remove("zv-hidden");
      if (view) view.classList.add("zv-hidden");
    }
    renderMesh((reg && reg.mesh && reg.mesh.entries) || []);
  }

  function renderMesh(entries) {
    const box = $("zv-mesh");
    if (!box) return;
    if (!entries.length) {
      box.innerHTML = '<p class="zv-empty">No mesh entries yet — register yourself to appear here.</p>';
      return;
    }
    box.innerHTML = entries
      .map(function (row) {
        const selfCls = row.self ? " self" : "";
        return (
          '<article class="zv-mesh-row' +
          selfCls +
          '">' +
          '<div class="zv-offer-head">' +
          '<span class="zv-offer-name">' +
          esc(row.full_name || row.display_name) +
          (row.self ? " (you)" : "") +
          "</span>" +
          '<span class="zv-mesh-score">BSP ' +
          esc(String(row.composite_score != null ? row.composite_score : "—")) +
          "</span></div>" +
          '<div class="zv-offer-meta">' +
          esc(row.display_name) +
          " · " +
          esc(row.region || "—") +
          "</div>" +
          '<div class="zv-wire" style="margin-top:4px;font-size:0.76rem">' +
          esc(row.wire_point) +
          "</div>" +
          (row.public_bio ? '<div class="zv-offer-meta" style="margin-top:4px">' + esc(row.public_bio) + "</div>" : "") +
          "</article>"
        );
      })
      .join("");
  }

  function renderPanel(doc) {
    state.panel = doc;
    const q = (doc.queue || {});
    state.queue = q;
    const gate = (doc.truth_gate || {}).pass_ok;
    $("zv-pill").textContent = gate ? "ZISV READY" : "GATE HOLD";
    $("zv-wire").textContent = q.wire_point || doc.wire_point || "—";
    $("zv-threats").textContent = String(q.threats_blocked || 0);
    $("zv-outbound").textContent = String((q.outbound || []).length);
    renderQueue(q.inbound_pending || []);
  }

  async function refreshRegistry() {
    try {
      const reg = await api("/api/znetwork/registry");
      renderRegistry(reg);
    } catch (e) {
      /* registry optional on first paint */
    }
  }

  async function refresh() {
    try {
      const doc = await api("/api/znetwork/vault");
      renderPanel(doc);
      await refreshRegistry();
    } catch (e) {
      toast("Vault API unavailable", false);
    }
  }

  async function registerOperator(ev) {
    if (ev && ev.preventDefault) ev.preventDefault();
    const body = {
      full_name: ($("zv-full-name") && $("zv-full-name").value || "").trim(),
      given_name: ($("zv-given") && $("zv-given").value || "").trim(),
      family_name: ($("zv-family") && $("zv-family").value || "").trim(),
      display_name: ($("zv-display") && $("zv-display").value || "").trim(),
      region: ($("zv-region") && $("zv-region").value || "").trim(),
      locale: ($("zv-locale") && $("zv-locale").value || "en").trim(),
      public_bio: ($("zv-bio") && $("zv-bio").value || "").trim(),
    };
    if (!body.full_name) {
      toast("Full name is required", false);
      return;
    }
    const btn = $("zv-register-btn");
    if (btn) btn.disabled = true;
    try {
      const doc = await api("/api/znetwork/registry/register", { method: "POST", body: body });
      if (doc.ok) {
        toast("Registered · BSP " + (doc.composite_score != null ? doc.composite_score : ""), true);
        renderRegistry({ registered: true, profile: doc.profile, mesh: { entries: [] } });
        await refreshRegistry();
      } else toast(doc.error || "Registration failed", false);
    } catch (e) {
      toast("Register error: " + e.message, false);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function acceptOffer(id) {
    const doc = await api("/api/znetwork/vault/accept", { method: "POST", body: { transfer_id: id } });
    if (doc.ok) toast("Accepted · " + (doc.filename || id), true);
    else toast(doc.error || "Accept failed", false);
    refresh();
  }

  async function rejectOffer(id) {
    const doc = await api("/api/znetwork/vault/reject", { method: "POST", body: { transfer_id: id } });
    if (doc.ok) toast("Rejected", true);
    else toast(doc.error || "Reject failed", false);
    refresh();
  }

  function readFileB64(file) {
    return new Promise(function (resolve, reject) {
      const reader = new FileReader();
      reader.onload = function () {
        const dataUrl = String(reader.result || "");
        const b64 = dataUrl.split(",")[1] || "";
        resolve(b64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function sendOffer() {
    const wire = ($("zv-recipient") && $("zv-recipient").value || "").trim();
    const label = ($("zv-label") && $("zv-label").value || "").trim();
    const fileInput = $("zv-file");
    const file = fileInput && fileInput.files && fileInput.files[0];
    if (!wire) {
      toast("Recipient wire-point required", false);
      return;
    }
    if (!file) {
      toast("Choose a file to send", false);
      return;
    }
    const btn = $("zv-send");
    if (btn) btn.disabled = true;
    try {
      const data_b64 = await readFileB64(file);
      const doc = await api("/api/znetwork/vault/send", {
        method: "POST",
        body: {
          recipient_wire: wire,
          filename: file.name,
          mime: file.type || "application/octet-stream",
          data_b64: data_b64,
          sender_label: label,
        },
      });
      if (doc.ok) toast("Sealed offer queued · " + (doc.transfer_id || ""), true);
      else toast(doc.error || "Send failed", false);
      refresh();
    } catch (e) {
      toast("Send error: " + e.message, false);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function bind() {
    const regForm = $("zv-register-form");
    if (regForm) regForm.addEventListener("submit", registerOperator);
    const sendBtn = $("zv-send");
    if (sendBtn) sendBtn.addEventListener("click", sendOffer);
    const rotBtn = $("zv-rotate");
    if (rotBtn) {
      rotBtn.addEventListener("click", async function () {
        const doc = await api("/api/znetwork/vault/wire-point?rotate=1");
        if (doc.wire_point) {
          $("zv-wire").textContent = doc.wire_point;
          toast("Wire-point rotated", true);
        }
      });
    }
    setInterval(refresh, 12000);
  }

  document.addEventListener("DOMContentLoaded", function () {
    bind();
    refresh();
  });
})();