(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  const KIND_FIELDS = {
    nexus_module: ["module", "args", "score_key", "summary_keys"],
    panel_file: ["path", "score_key", "ready_key"],
    install_data: ["path", "ready_key"],
    http_json: ["url", "timeout"],
    path_exists: ["path"],
  };

  function levelBadge(lv) {
    const l = String(lv || "pending").toLowerCase();
    return `<span class="badge level-${l.includes("master") ? "mastered" : l.includes("complete") || l.includes("fluent") ? "complete" : l.includes("train") || l.includes("online") ? "training" : "pending"}">${esc(lv)}</span>`;
  }

  async function fetchModels() {
    const r = await fetch("/api/models", { cache: "no-store" });
    if (!r.ok) throw new Error(`models HTTP ${r.status}`);
    return r.json();
  }

  function renderList(models) {
    const el = $("models-list");
    if (!el) return;
    if (!models?.length) {
      el.innerHTML = '<p class="meta">No connected models — add one below.</p>';
      return;
    }
    el.innerHTML = models.map((m) => {
      const p = m.probe || {};
      return `<article class="model-card" data-id="${esc(m.id)}">
        <div class="model-head">
          <strong>${esc(m.label || m.id)}</strong>
          ${levelBadge(p.level)}
        </div>
        <div class="meta">${esc(m.kind)} · ${esc(m.group || "connected")}</div>
        <div class="meta">${esc(p.detail || (p.online ? "online" : "offline"))}</div>
        <div class="model-actions">
          <button type="button" class="btn-probe" data-id="${esc(m.id)}">Probe</button>
          <button type="button" class="btn-del" data-id="${esc(m.id)}">Remove</button>
        </div>
      </article>`;
    }).join("");

    el.querySelectorAll(".btn-del").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        if (!id || !confirm(`Remove model ${id}?`)) return;
        await fetch(`/api/models?id=${encodeURIComponent(id)}`, { method: "DELETE" });
        await refresh();
        if (window.H7Viewer?.reloadGraph) window.H7Viewer.reloadGraph(true);
      });
    });

    el.querySelectorAll(".btn-probe").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const model = models.find((x) => x.id === id);
        if (!model) return;
        const r = await fetch("/api/models/probe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(model),
        });
        const j = await r.json();
        alert(`${id}: ${j.probe?.level} — ${j.probe?.detail || ""}`);
        await refresh();
      });
    });
  }

  function parseConnectTo(raw) {
    return String(raw || "hostess7_core")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function buildModelFromForm() {
    const kind = $("model-kind")?.value || "panel_file";
    const id = ($("model-id")?.value || "").trim().replace(/\s+/g, "_");
    if (!id) throw new Error("Model id required");
    const model = {
      id,
      label: ($("model-label")?.value || id).trim(),
      group: ($("model-group")?.value || "connected").trim(),
      kind,
      connect_to: parseConnectTo($("model-connect")?.value),
      color: $("model-color")?.value || "#60a5fa",
    };
    if (kind === "nexus_module") {
      model.module = ($("model-path")?.value || "").trim();
      try {
        model.args = JSON.parse($("model-extra")?.value || '["json"]');
      } catch {
        model.args = ["json"];
      }
      model.score_key = "programming_score";
    } else if (kind === "http_json") {
      model.url = ($("model-path")?.value || "").trim();
      model.timeout = 10;
    } else {
      model.path = ($("model-path")?.value || "").trim();
      if (kind === "panel_file") model.score_key = "programming_score";
      if (kind === "install_data") model.ready_key = "ready_g16";
    }
    return model;
  }

  function updateFormHints() {
    const kind = $("model-kind")?.value || "panel_file";
    const pathLbl = $("label-model-path");
    const extra = $("model-extra-wrap");
    if (pathLbl) {
      pathLbl.textContent = kind === "http_json" ? "URL" : kind === "nexus_module" ? "Module (lib/…)" : "Path";
    }
    if (extra) extra.style.display = kind === "nexus_module" ? "block" : "none";
    const ph = $("model-path");
    if (ph) {
      ph.placeholder = kind === "http_json"
        ? "http://127.0.0.1:9477/api/hostess7/g16"
        : kind === "nexus_module"
          ? "hostess7-g16.py"
          : kind === "panel_file"
            ? "hostess7-g16-panel.json"
            : "/path/to/resource";
    }
  }

  async function refresh() {
    try {
      const j = await fetchModels();
      renderList(j.models || []);
    } catch (e) {
      const el = $("models-list");
      if (el) el.innerHTML = `<p class="meta">Error: ${esc(e.message)}</p>`;
    }
  }

  function bind() {
    $("model-kind")?.addEventListener("change", updateFormHints);
    $("btn-add-model")?.addEventListener("click", async () => {
      try {
        const model = buildModelFromForm();
        const r = await fetch("/api/models", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(model),
        });
        const j = await r.json();
        if (!j.ok) throw new Error(j.error || "save failed");
        $("model-id").value = "";
        $("model-label").value = "";
        await refresh();
        if (window.H7Viewer?.reloadGraph) window.H7Viewer.reloadGraph(true);
      } catch (e) {
        alert(e.message);
      }
    });
    updateFormHints();
    refresh();
  }

  window.H7Models = { refresh };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();