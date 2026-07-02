(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  async function fetchLibrary(q) {
    const url = q ? `/api/cpu-library/search?q=${encodeURIComponent(q)}` : "/api/cpu-library";
    const res = await fetch(url, { cache: "no-store" });
    return res.ok ? res.json() : null;
  }

  function renderStats(doc) {
    const el = $("qcl-stats");
    if (!el) return;
    const c = doc?.counts || {};
    el.innerHTML = [
      `<p><strong>${c.total ?? "—"}</strong> CPUs</p>`,
      `<p>ARM: ${c.arm ?? "—"}</p>`,
      `<p>Apple: ${c.apple_silicon ?? "—"}</p>`,
      `<p>Mobile: ${c.mobile_soc ?? "—"}</p>`,
      `<p>Intel: ${c.x86_intel ?? "—"}</p>`,
      `<p>AMD: ${c.x86_amd ?? "—"}</p>`,
      `<p>Detailed: ${c.detailed ?? "—"}</p>`,
    ].join("");
  }

  function renderList(entries) {
    const el = $("qcl-list");
    if (!el) return;
    el.innerHTML = (entries || [])
      .slice(0, 200)
      .map(
        (row) =>
          `<button type="button" class="qcl-row" data-id="${esc(row.id)}">` +
          `<span class="qcl-tag">${esc(row.family)}</span>${esc(row.label)}` +
          ` <small>${esc(row.vendor)}</small></button>`
      )
      .join("");
    el.querySelectorAll(".qcl-row").forEach((btn) => {
      btn.addEventListener("click", () => showDetail(btn.dataset.id));
    });
  }

  async function showDetail(id) {
    const el = $("qcl-detail");
    if (!el || !id) return;
    el.querySelectorAll(".qcl-row")?.forEach?.(() => {});
    document.querySelectorAll(".qcl-row").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
    const res = await fetch(`/api/cpu-library/detail?id=${encodeURIComponent(id)}`);
    const row = res.ok ? await res.json() : null;
    if (!row || row.error) {
      el.innerHTML = "<p class='qcl-muted'>Not found</p>";
      return;
    }
    el.innerHTML = [
      `<h2>${esc(row.label)}</h2>`,
      `<p><span class="qcl-tag">${esc(row.vendor)}</span> <span class="qcl-tag">${esc(row.family)}</span> ${esc(row.arch || "")}</p>`,
      `<p><strong>Company</strong> ${esc(row.company)} · <strong>Mfg</strong> ${esc(row.mfg_date_start || "—")}</p>`,
      `<p><strong>Address map</strong><br>${esc(row.address_map || "—")}</p>`,
      `<p><strong>Schematic</strong><br>${esc(row.schematic_blueprint || "—")}</p>`,
      `<p><strong>AI detail</strong><br>${esc(row.ai_detail || "—")}</p>`,
      `<p><strong>Diagram</strong> ${esc(row.diagram_hint || "—")}</p>`,
    ].join("");
  }

  async function refresh() {
    const q = ($("qcl-search")?.value || "").trim();
    const doc = await fetchLibrary(q);
    if (!doc) return;
    const entries = doc.entries || doc.hits || doc.sample || [];
    renderStats(doc);
    renderList(entries);
  }

  $("qcl-refresh")?.addEventListener("click", refresh);
  $("qcl-search")?.addEventListener("input", () => {
    clearTimeout(window._qclTimer);
    window._qclTimer = setTimeout(refresh, 280);
  });
  refresh();
})();