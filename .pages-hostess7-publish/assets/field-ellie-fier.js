(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function render(doc) {
    const sw = doc.systemwide || {};
    const slices = doc.security_slices || sw.security_slices || {};
    const pill = $("ef-verdict-pill");
    if (pill) {
      pill.textContent = `${sw.verdict || "—"} · ${sw.score != null ? Number(sw.score).toFixed(2) : "—"}`;
      pill.className = `ef-pill ${esc(sw.verdict || "").toLowerCase()}`;
    }
    const sub = $("ef-sub");
    if (sub) sub.textContent = doc.posture || doc.motto || "Unified security authority";
    const meta = $("ef-meta");
    if (meta) {
      meta.innerHTML = [
        `<span>threat <strong>${esc(doc.threat_warn_level || sw.threat_warn_level || "high")}</strong></span>`,
        `<span>feeds <strong>${slices.live_count ?? "—"}</strong>/${slices.feed_count ?? "—"}</span>`,
        `<span>ironclad <strong>${sw.ironclad_sealed ? "sealed" : "open"}</strong></span>`,
        `<span>popcorn <strong>${sw.popcorn_count ?? "—"}</strong></span>`,
      ].join("");
    }
    const pillarsEl = $("ef-pillars");
    if (pillarsEl) {
      const pillars = slices.pillars || {};
      const keys = Object.keys(pillars);
      pillarsEl.innerHTML = keys.length
        ? keys
            .map((k) => {
              const p = pillars[k] || {};
              return (
                `<article class="ef-pillar">` +
                `<h3>${esc(k)}</h3>` +
                `<div class="ef-pv">${esc(p.verdict || "—")}</div>` +
                `<small>${esc(p.live || 0)} live · score ${esc(p.max_score ?? "—")}</small>` +
                `</article>`
              );
            })
            .join("")
        : '<p class="ef-muted">No pillar data — refresh posture.</p>';
    }
    const feedsEl = $("ef-feeds");
    if (feedsEl) {
      const feeds = slices.feeds || [];
      feedsEl.innerHTML = feeds.length
        ? feeds
            .map(
              (f) =>
                `<div class="ef-feed">` +
                `<strong>${esc(f.id)}</strong>` +
                `<span>${esc(f.verdict)} · ${f.live ? "live" : "idle"}</span>` +
                `</div>`
            )
            .join("")
        : '<p class="ef-muted">No feeds cached.</p>';
    }
  }

  async function refresh(scan) {
    const url = scan ? "/api/field-ellie-fier/threat" : "/api/field-ellie-fier";
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return;
      const doc = await res.json();
      render(doc);
    } catch (_) {}
  }

  $("ef-refresh")?.addEventListener("click", () => refresh(true));
  refresh(false);
  setInterval(() => refresh(false), 20000);
})();