(function () {
  "use strict";

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function render(doc) {
    const main = document.getElementById("fk-main");
    const pill = document.getElementById("fk-pill");
    if (!main) return;
    if (pill) pill.textContent = doc.offline_only ? "OFFLINE" : "—";

    const ui = doc.ui || {};
    const vaults = (doc.vaults || [])
      .map(function (v) {
        return (
          '<div class="fk-vault"><span>' +
          esc(v.name) +
          '</span><button type="button" class="fk-btn" data-vault="' +
          esc(v.path) +
          '">Open</button></div>'
        );
      })
      .join("");

    main.innerHTML =
      '<div class="fk-card"><strong>Sovereign vault</strong>' +
      '<p class="fk-dim">' +
      esc(doc.posture || "") +
      "</p>" +
      '<p class="fk-dim">No cloud accounts · KeeShare off · clipboard clears in 30s · screenshot blocked</p>' +
      '<div class="fk-row">' +
      '<button type="button" class="fk-btn primary" id="fk-launch">Unlock vault</button>' +
      '<button type="button" class="fk-btn" id="fk-new">New vault</button>' +
      "</div></div>" +
      '<div class="fk-card"><strong>Readable UI</strong>' +
      '<p class="fk-dim">10% desktop bump · tier-aware scaling · no tiny icons</p>' +
      '<span class="fk-tier">' +
      esc(ui.tier || "fhd") +
      "</span>" +
      '<span class="fk-tier">Qt ' +
      esc(String(ui.qt_scale_factor || "1.1")) +
      "×</span>" +
      (ui.rtx_detected
        ? '<span class="fk-tier">RTX ' + (ui.rtx_reduce ? "comfort" : "native") + "</span>"
        : "") +
      '<div class="fk-slider-row"><label for="fk-scale">UI scale</label><span class="fk-slider-val" id="fk-scale-val">' +
      esc(String(ui.ui_scale_pct || 125)) +
      "%</span></div>" +
      '<input type="range" id="fk-scale" min="85" max="150" step="5" value="' +
      esc(String(ui.ui_scale_pct || 125)) +
      '" />' +
      '<label class="fk-dim"><input type="checkbox" id="fk-rtx" ' +
      (ui.rtx_reduce ? "checked" : "") +
      " /> RTX comfort reduce (drop one tier)</label></div>" +
      '<div class="fk-card"><strong>Import passwords</strong>' +
      '<p class="fk-dim">KeePass · 1Password · Bitwarden · LastPass · CSV · browser exports</p>' +
      '<div class="fk-row">' +
      '<button type="button" class="fk-btn" id="fk-import-scan">Scan & import</button>' +
      '<button type="button" class="fk-btn" id="fk-import-browser">From browsers</button>' +
      '<button type="button" class="fk-btn" id="fk-import-csv">Import CSV path</button>' +
      "</div>" +
      '<p class="fk-dim" id="fk-import-status">Staging: ' + esc(String((doc.import || {}).staging_count || 0)) + " entries</p></div>" +
      '<div class="fk-card"><strong>Vaults</strong>' +
      (vaults || '<p class="fk-dim">No .kdbx found — create one with New vault</p>') +
      "</div>" +
      '<div class="fk-card"><strong>Platform</strong><p class="fk-dim">' +
      esc(doc.platform || "") +
      " · " +
      esc(doc.binary || "not installed") +
      "</p></div>";

    document.getElementById("fk-launch")?.addEventListener("click", function () {
      api("/api/field-lock/launch", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then(function (r) {
        if (!r.ok) alert(r.error || "launch failed");
      });
    });
    document.getElementById("fk-import-scan")?.addEventListener("click", function () {
      api("/api/field-lock/import-scan", { method: "POST" }).then(function (r) {
        const st = document.getElementById("fk-import-status");
        if (st) st.textContent = "Found " + (r.vault_count || 0) + " vaults · staging " + ((r.staging || {}).entry_count || 0);
        init();
      });
    });
    document.getElementById("fk-import-browser")?.addEventListener("click", function () {
      api("/api/field-lock/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "bridge_browser" }),
      }).then(function (r) {
        const st = document.getElementById("fk-import-status");
        if (st) st.textContent = r.ok ? "Browser bridge: " + (r.added || 0) + " entries" : (r.error || "failed");
        init();
      });
    });
    document.getElementById("fk-import-csv")?.addEventListener("click", function () {
      const path = prompt("Path to CSV/JSON/kdbx export", "~/Downloads/passwords.csv");
      if (!path) return;
      api("/api/field-lock/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import", path: path }),
      }).then(function (r) {
        const st = document.getElementById("fk-import-status");
        if (st) st.textContent = r.ok ? "Imported " + (r.entries_parsed || 0) + " (" + (r.format || "") + ")" : (r.error || "failed");
        init();
      });
    });
    document.getElementById("fk-new")?.addEventListener("click", function () {
      api("/api/field-lock/new", { method: "POST" }).then(function (r) {
        if (r.ok) init();
        else alert(r.error || "new vault failed");
      });
    });
    main.querySelectorAll("[data-vault]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const path = btn.getAttribute("data-vault");
        api("/api/field-lock/launch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ vault: path }),
        }).then(function (r) {
          if (!r.ok) alert(r.error || "open failed");
        });
      });
    });
    const scale = document.getElementById("fk-scale");
    const scaleVal = document.getElementById("fk-scale-val");
    const rtx = document.getElementById("fk-rtx");
    function saveUi() {
      const pct = parseInt(scale?.value || "125", 10);
      if (scaleVal) scaleVal.textContent = pct + "%";
      api("/api/field-lock/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ui_scale_pct: pct, rtx_reduce: !!rtx?.checked }),
      }).then(init);
    }
    scale?.addEventListener("change", saveUi);
    rtx?.addEventListener("change", saveUi);
  }

  async function init() {
    try {
      const doc = await api("/api/field-lock");
      render(doc);
    } catch (e) {
      const main = document.getElementById("fk-main");
      if (main) main.textContent = "Lock load failed: " + e.message;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();