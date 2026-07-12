/**
 * Queen browser — secure import status + primary browser registration.
 */
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function formatImport(doc) {
    const imp = doc?.import || {};
    const vault = doc?.vault || {};
    const parts = [];
    if (imp.bookmarks) parts.push(`${imp.bookmarks} bookmarks`);
    if (imp.credentials || vault.count) parts.push(`${imp.credentials || vault.count} logins`);
    if (imp.quarantined) parts.push(`${imp.quarantined} quarantined`);
    return parts.length ? parts.join(" · ") : "Sweeping host browsers…";
  }

  async function refreshImportChip() {
    const chip = $("qb-import-chip");
    const detail = $("qb-import-detail");
    if (!chip || !detail) return;
    try {
      const res = await fetch("/api/queen-browser", { cache: "no-store" });
      const doc = await res.json();
      detail.textContent = formatImport(doc);
      const vault = doc.vault || {};
      chip.title = [
        "Humans: your bookmarks & passwords — local vault, field-gated.",
        vault.encrypted ? "AI assist: AES-256 vault — plaintext never on disk." : "Vault: local seal active.",
        "Drop bookmarks.html or passwords.csv in .nexus-state/imports/",
        "Shift+click = register Queen as default browser.",
      ].join(" ");
      if ((doc.import?.credentials_added || 0) > 0 || (doc.import?.bookmarks || 0) > 0) {
        chip.classList.add("qb-import-ready");
      }
    } catch {
      detail.textContent = "Import offline";
    }
  }

  async function runImport(force) {
    const detail = $("qb-import-detail");
    if (detail) detail.textContent = "Importing & resecuring…";
    try {
      const res = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import_all", apply: true, force: !!force }),
      });
      const out = await res.json();
      if (out.manifest) {
        const m = out.manifest;
        if (detail) {
          detail.textContent = [
            m.bookmarks ? `${m.bookmarks} bookmarks` : null,
            m.credentials_added ? `${m.credentials_added} logins secured` : m.credentials ? `${m.credentials} logins` : null,
            m.quarantined ? `${m.quarantined} quarantined` : null,
          ].filter(Boolean).join(" · ") || "Import complete";
        }
      }
      await refreshImportChip();
      if (globalThis.QueenOS?.browser?.refresh) {
        await globalThis.QueenOS.browser.refresh();
      }
    } catch {
      if (detail) detail.textContent = "Import failed";
    }
  }

  async function setPrimary() {
    const detail = $("qb-import-detail");
    try {
      const res = await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "set_primary_browser" }),
      });
      const out = await res.json();
      if (detail) {
        detail.textContent = out.primary
          ? "Queen set as default browser"
          : out.hint || "Primary browser — use applications menu";
      }
    } catch {
      if (detail) detail.textContent = "Primary browser setup failed";
    }
  }

  function bind() {
    $("qb-import-chip")?.addEventListener("click", (e) => {
      if (e.shiftKey) {
        setPrimary();
        return;
      }
      runImport(true);
    });
    refreshImportChip();
    setInterval(refreshImportChip, 120000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();