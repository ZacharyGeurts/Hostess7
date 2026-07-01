/**
 * Outside Talk — NEXUS egress gate. Operator-initiated SSH, telnet, mail, custom ports.
 */
(function (global) {
  "use strict";

  let lastDoc = null;
  let bound = false;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  function alertClass(level) {
    if (level === "critical") return "outside-alert--critical";
    if (level === "high") return "outside-alert--high";
    if (level === "medium") return "outside-alert--medium";
    return "outside-alert--info";
  }

  function toolById(doc, id) {
    return (doc.tools || []).find((t) => t.id === id) || null;
  }

  function applyToolDefaults(tool) {
    if (!tool) return;
    const portEl = $("outside-port");
    const protoEl = $("outside-proto");
    if (portEl && tool.port) portEl.value = String(tool.port);
    if (protoEl && tool.proto) protoEl.value = tool.proto;
    const hint = $("outside-tool-hint");
    if (hint) {
      hint.textContent = tool.hint || "";
      hint.classList.toggle("outside-hint--warn", tool.secure === false);
    }
    const secureBadge = $("outside-secure-badge");
    if (secureBadge) {
      secureBadge.textContent = tool.secure ? "TLS / encrypted path" : "Cleartext — caution";
      secureBadge.className = tool.secure ? "outside-secure outside-secure--ok" : "outside-secure outside-secure--warn";
    }
    const userRow = $("outside-user-row");
    if (userRow) userRow.hidden = !(tool.fields || []).includes("username");
    const pathRow = $("outside-path-row");
    if (pathRow) pathRow.hidden = !(tool.fields || []).includes("path");
    const protoRow = $("outside-proto-row");
    if (protoRow) protoRow.hidden = tool.id !== "custom";
  }

  function bindControls(doc) {
    if (bound) return;
    bound = true;

    $("outside-tool-select")?.addEventListener("change", (ev) => {
      const t = toolById(doc, ev.target.value);
      applyToolDefaults(t);
    });

    $("outside-connect-btn")?.addEventListener("click", () => runConnect(false));
    $("outside-probe-btn")?.addEventListener("click", () => runConnect(true));
    $("outside-refresh-btn")?.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/field-outside-talk", { method: "POST" });
        const j = await res.json();
        renderOutsideTalk(j);
      } catch (err) {
        $("outside-terminal")?.insertAdjacentHTML(
          "beforeend",
          `<div class="outside-line outside-line--err">Refresh failed: ${esc(err.message)}</div>`
        );
      }
    });

    $("outside-clear-terminal")?.addEventListener("click", () => {
      const el = $("outside-terminal");
      if (el) el.innerHTML = '<div class="outside-line outside-line--meta">Terminal cleared.</div>';
    });
  }

  async function runConnect(probeOnly) {
    const tool = $("outside-tool-select")?.value || "ssh";
    const host = ($("outside-host")?.value || "").trim();
    const port = parseInt($("outside-port")?.value || "0", 10);
    const username = ($("outside-user")?.value || "").trim();
    const path = ($("outside-path")?.value || "/").trim() || "/";
    const proto = ($("outside-proto")?.value || "tcp").trim();
    const force = $("outside-force")?.checked;
    const trust = $("outside-trust")?.checked;
    const term = $("outside-terminal");
    if (!host) {
      if (term) term.insertAdjacentHTML("beforeend", '<div class="outside-line outside-line--err">Host required.</div>');
      return;
    }
    const btn = probeOnly ? $("outside-probe-btn") : $("outside-connect-btn");
    if (btn) btn.disabled = true;
    if (term) {
      term.insertAdjacentHTML(
        "beforeend",
        `<div class="outside-line outside-line--meta">${probeOnly ? "Probing" : "Connecting via NEXUS firewall"} → ${esc(tool)} ${esc(host)}:${port}…</div>`
      );
      term.scrollTop = term.scrollHeight;
    }
    try {
      const res = await fetch(probeOnly ? "/api/field-outside-talk/probe" : "/api/field-outside-talk/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, host, port, username, path, proto, force, trust_forever: trust }),
      });
      const j = await res.json();
      const cls = j.ok ? "outside-line--ok" : "outside-line--err";
      const lines = [
        `<div class="outside-line ${cls}">[${esc(j.ts || new Date().toISOString())}] ${j.ok ? "OK" : "FAIL"} rc=${esc(j.probe_rc)} engine=${esc(j.engine || "—")} ${esc(j.tool_label || j.tool)} ${esc(j.host)}:${esc(j.port)}</div>`,
      ];
      if (j.output) {
        lines.push(`<pre class="outside-pre">${esc(j.output)}</pre>`);
      }
      if (j.hint) {
        lines.push(`<div class="outside-line outside-line--hint">${esc(j.hint)}</div>`);
      }
      if (j.error) {
        lines.push(`<div class="outside-line outside-line--err">${esc(j.error)} ${esc(j.hint || "")}</div>`);
      }
      if (term) {
        term.insertAdjacentHTML("beforeend", lines.join(""));
        term.scrollTop = term.scrollHeight;
      }
      if (!probeOnly && lastDoc) {
        const res2 = await fetch("/api/field-outside-talk");
        const fresh = await res2.json();
        renderOutsideTalk(fresh);
      }
    } catch (err) {
      if (term) {
        term.insertAdjacentHTML("beforeend", `<div class="outside-line outside-line--err">${esc(err.message)}</div>`);
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function renderHero(doc) {
    const br = doc.engineer_briefing || {};
    const qf = br.quick_facts || {};
    const fw = doc.firewall || {};
    const title = $("outside-hero-title");
    const motto = $("outside-motto");
    const status = $("outside-hero-status");
    if (title) {
      title.innerHTML = fw.active
        ? '<span class="outside-hero-run">FIREWALL ACTIVE</span> Outside Talk'
        : '<span class="outside-hero-stop">FIREWALL PENDING</span> Outside Talk';
    }
    if (motto) motto.textContent = br.lead || doc.motto || "NEXUS egress gate — operator-initiated outbound only.";
    const hard = doc.hardening || {};
    const eng = hard.asm_ready ? "ASM" : (qf.engine || "socket");
    if (status) {
      status.innerHTML = [
        `<div class="outside-hero-pill outside-hero-pill--ok"><span>Engine</span><strong>${esc(eng)}</strong></div>`,
        `<div class="outside-hero-pill"><span>Tools</span><strong>${qf.tool_count ?? doc.tools?.length ?? 0}</strong></div>`,
        `<div class="outside-hero-pill"><span>Sessions</span><strong>${qf.sessions_logged ?? doc.recent_sessions?.length ?? 0}</strong></div>`,
        `<div class="outside-hero-pill"><span>Rate cap</span><strong>${hard.rate_limit_per_min ?? 20}/min</strong></div>`,
        `<div class="outside-hero-pill outside-hero-pill--wide"><span>Legal</span><strong>${esc(br.legal_notice || doc.legal_notice || "Authorized access only")}</strong></div>`,
      ].join("");
    }
  }

  function renderAlerts(doc) {
    const el = $("outside-alerts");
    if (!el) return;
    const alerts = doc.engineer_briefing?.alerts || [];
    if (!alerts.length) {
      el.innerHTML = '<div class="outside-alert outside-alert--ok">Egress gate ready — select a tool and connect outward through NEXUS.</div>';
      return;
    }
    el.innerHTML = alerts
      .map(
        (a) => `<div class="outside-alert ${alertClass(a.level)}">
          <strong>${esc(a.title)}</strong>
          <div>${esc(a.detail)}</div>
          ${a.action ? `<div class="outside-alert-action">${esc(a.action)}</div>` : ""}
        </div>`
      )
      .join("");
  }

  function renderLegal(doc) {
    const el = $("outside-legal-table");
    if (!el) return;
    const rows = doc.legal_framework || [];
    if (!rows.length) {
      el.innerHTML = '<div class="empty">No legal framework loaded.</div>';
      return;
    }
    el.innerHTML = `<table class="outside-table"><thead><tr>
      <th>Citation</th><th>Title</th><th>Requirement</th><th>NEXUS application</th>
    </tr></thead><tbody>${rows
      .map(
        (r) => `<tr>
          <td><code>${esc(r.citation)}</code></td>
          <td>${esc(r.title)}</td>
          <td>${esc(r.requirement)}</td>
          <td>${esc(r.nexus_application)}</td>
        </tr>`
      )
      .join("")}</tbody></table>`;
  }

  function renderSessions(doc) {
    const el = $("outside-sessions");
    if (!el) return;
    const rows = doc.recent_sessions || [];
    if (!rows.length) {
      el.innerHTML = '<div class="empty">No outbound sessions yet — connect to populate audit log.</div>';
      return;
    }
    el.innerHTML = `<table class="outside-table"><thead><tr>
      <th>Time</th><th>Tool</th><th>Target</th><th>Port</th><th>Result</th>
    </tr></thead><tbody>${rows
      .map(
        (r) => `<tr class="${r.ok ? "" : "outside-row-fail"}">
          <td>${esc((r.ts || "").slice(11, 19))}</td>
          <td>${esc(r.tool_label || r.tool)}</td>
          <td><code>${esc(r.host)}</code> <span class="meta">${esc(r.ip || "")}</span></td>
          <td>${esc(r.port)}</td>
          <td>${r.ok ? '<span class="outside-chip-ok">reach</span>' : '<span class="outside-chip-warn">fail</span>'}</td>
        </tr>`
      )
      .join("")}</tbody></table>`;
  }

  function renderToolSelect(doc) {
    const sel = $("outside-tool-select");
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = (doc.tools || [])
      .map((t) => `<option value="${esc(t.id)}">${esc(t.label)}</option>`)
      .join("");
    if (cur && (doc.tools || []).some((t) => t.id === cur)) sel.value = cur;
    applyToolDefaults(toolById(doc, sel.value));
  }

  function renderOutsideTalk(doc, panel) {
    if (!doc) return;
    lastDoc = doc;
    global.lastOutsideDoc = doc;
    bindControls(doc);
    renderHero(doc);
    renderAlerts(doc);
    renderLegal(doc);
    renderSessions(doc);
    renderToolSelect(doc);
    const fd = panel?.field_drive;
    if (fd && global.renderFieldDrive) {
      global.renderFieldDrive(fd);
    }
  }

  global.renderOutsideTalk = renderOutsideTalk;
})(typeof window !== "undefined" ? window : globalThis);