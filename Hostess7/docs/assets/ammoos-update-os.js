(function () {
  "use strict";

  const API = "/api/ammoos-update";
  const POLL_MS = 2500;

  let state = null;
  let applying = false;
  let pollTimer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function setBusy(busy, message) {
    const card = $("au-status-card");
    const apply = $("au-apply");
    const check = $("au-check");
    if (card) card.classList.toggle("au-busy", !!busy);
    if (apply) {
      apply.disabled = !!busy || !state?.update_available;
      apply.textContent = busy ? "Updating…" : "Apply update";
    }
    if (check) check.disabled = !!busy;
    if (message && $("au-status-detail")) $("au-status-detail").textContent = message;
  }

  function renderSafety(pf) {
    const list = $("au-safety-list");
    if (!list) return;
    list.innerHTML = "";
    if (!pf) {
      list.innerHTML = '<li class="warn">Preflight not run</li>';
      return;
    }
    const items = [];
    if (pf.disk_free_mb != null) {
      const ok = pf.disk_free_mb >= 512;
      items.push({
        cls: ok ? "ok" : "fail",
        text: `Disk space: ${pf.disk_free_mb} MB free`,
      });
    }
    if (pf.source_root) {
      items.push({ cls: "ok", text: `Source tree: ${pf.source_root}` });
    }
    if (pf.never_harm_os) {
      items.push({ cls: "ok", text: "Host OS protection enabled" });
    }
    for (const issue of pf.issues || []) {
      items.push({ cls: "fail", text: issue.message || issue.kind || "Issue" });
    }
    if (!items.length) {
      items.push({ cls: pf.preflight_ok ? "ok" : "warn", text: pf.preflight_ok ? "All checks passed" : "Review checks" });
    }
    list.innerHTML = items
      .map((it) => `<li class="${esc(it.cls)}">${esc(it.text)}</li>`)
      .join("");
  }

  function renderComponents(components) {
    const body = $("au-components-body");
    if (!body) return;
    const rows = components || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="4">No components</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map((c) => {
        let badge = "current";
        let label = c.status || "unknown";
        if (c.status === "not_installed") {
          badge = "optional";
          label = "optional";
        } else if (c.update_available) {
          badge = "update";
          label = "update available";
        }
        return `<tr>
          <td>${esc(c.name || c.id)}</td>
          <td>${esc(c.local_version || (c.present ? "present" : "—"))}</td>
          <td>${esc(c.remote_version || "—")}</td>
          <td><span class="au-badge ${badge}">${esc(label)}</span></td>
        </tr>`;
      })
      .join("");
  }

  function renderStatus(data) {
    state = data;
    const current = $("au-current");
    const latest = $("au-latest");
    const latestWrap = $("au-latest-wrap");
    const arrow = $("au-arrow");
    const detail = $("au-status-detail");
    const apply = $("au-apply");
    const card = $("au-status-card");
    const notesSec = $("au-notes-section");
    const notes = $("au-notes");

    if (current) current.textContent = data.current ? `v${data.current}` : "—";

    if (data.update_available && !data.update_in_progress) {
      if (latestWrap) latestWrap.hidden = false;
      if (arrow) arrow.hidden = false;
      if (latest) latest.textContent = data.latest ? `v${data.latest}` : "—";
      if (card) card.classList.add("au-ready");
      if (apply) {
        apply.disabled = !(data.preflight && data.preflight.preflight_ok);
        apply.classList.add("au-ready");
      }
      if (detail) detail.textContent = data.label || `${data.previous} → ${data.latest}`;
    } else {
      if (latestWrap) latestWrap.hidden = true;
      if (arrow) arrow.hidden = true;
      if (card) card.classList.remove("au-ready");
      if (apply) apply.classList.remove("au-ready");
      if (data.update_in_progress) {
        setBusy(true, data.message || data.label || "Update in progress…");
      } else {
        setBusy(false);
        if (apply) apply.disabled = true;
        if (detail) {
          detail.textContent = data.label || `Up to date · ${data.github_repo || "GitHub"}`;
        }
      }
    }

    if (notesSec && notes) {
      const body = (data.release_notes || "").trim();
      if (body) {
        notesSec.hidden = false;
        notes.textContent = body;
      } else {
        notesSec.hidden = true;
      }
    }

    renderSafety(data.preflight);
    renderComponents(data.components);
  }

  async function fetchLog() {
    try {
      const res = await fetch(`${API}/log`, { cache: "no-store" });
      const data = await res.json();
      const log = $("au-log");
      if (log && data.lines) {
        log.textContent = data.lines.length ? data.lines.join("\n") : "(empty)";
      }
    } catch {
      /* offline */
    }
  }

  async function checkUpdate(force) {
    if (applying) return;
    const detail = $("au-status-detail");
    if (force && detail) detail.textContent = "Checking GitHub…";
    try {
      const res = await fetch(`${API}/check?force=${force ? 1 : 0}`, { cache: "no-store" });
      const data = await res.json();
      renderStatus(data);
      if (data.update_in_progress) startPoll();
      await fetchLog();
    } catch {
      if (detail) detail.textContent = "Offline — connect to check GitHub";
    }
  }

  async function pollStatus() {
    try {
      const res = await fetch(`${API}/status`, { cache: "no-store" });
      const data = await res.json();
      renderStatus(data);
      await fetchLog();
      if (data.needs_sudo) {
        await fetch(`${API}/sudo-prompt`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        return true;
      }
      if (data.update_in_progress) return true;
      applying = false;
      setBusy(false);
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
    }, POLL_MS);
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
    if (state.preflight && !state.preflight.preflight_ok) {
      $("au-status-detail").textContent = "Fix safety checks before applying";
      return;
    }
    applying = true;
    setBusy(true, `Applying ${state.previous} → ${state.latest}…`);
    try {
      const res = await fetch(`${API}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await res.json();
      if (res.status === 202 || data.started) {
        setBusy(true, data.message || "Update running in background…");
        startPoll();
        return;
      }
      if (data.already_current) {
        applying = false;
        await checkUpdate(true);
        return;
      }
      applying = false;
      $("au-status-detail").textContent = data.message || data.error || "Update not applied";
    } catch {
      setBusy(true, "Update started — polling…");
      startPoll();
    }
  }

  function bind() {
    $("au-check")?.addEventListener("click", () => checkUpdate(true));
    $("au-apply")?.addEventListener("click", applyUpdate);
    $("au-log-refresh")?.addEventListener("click", fetchLog);
    checkUpdate(false);
    setInterval(() => checkUpdate(false), 3600000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();