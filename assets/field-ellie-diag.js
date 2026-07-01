(function () {
  "use strict";

  const ROUTE_TO_PILLAR = {
    network: "network",
    truth: "truth",
    thermal: "thermal_power",
    firmware: "firmware_vault",
    media: "media",
    sovereign: "sovereign",
  };

  const PILLARS = {
    network: { title: "Network Threat", tag: "Gatekeeper · ZNetwork · DPI" },
    truth: { title: "Truth & Ironclad", tag: "Sanity · Reality field · Bugfinder" },
    thermal_power: { title: "Thermal & Power", tag: "GPU · Voltage · Physics witness" },
    firmware_vault: { title: "Firmware & Vault", tag: "Threat removal · Lock" },
    media: { title: "Media Integrity", tag: "Popcorn · Inspector" },
    sovereign: { title: "Sovereign Stack", tag: "Time · DNS · Last host" },
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function routeSlug() {
    const m = location.pathname.match(/\/field-ellie\/([a-z_]+)/i);
    if (m) return m[1].toLowerCase();
    const q = new URLSearchParams(location.search).get("pillar");
    return (q || "network").toLowerCase();
  }

  function pillarFromPath() {
    const slug = routeSlug();
    return ROUTE_TO_PILLAR[slug] || slug;
  }

  function apiPillarSlug() {
    return routeSlug();
  }

  function verdictClass(v) {
    return String(v || "clear").toLowerCase().replace(/[^a-z]/g, "") || "clear";
  }

  function feedRows(feed) {
    const panel = feed.panel_data || {};
    const rows = [];
    const skip = new Set(["schema", "ok", "ts", "updated", "feeds", "security_slices"]);
    Object.keys(panel)
      .sort()
      .forEach(function (k) {
        if (skip.has(k)) return;
        const v = panel[k];
        if (v == null || typeof v === "object") return;
        rows.push(`<div class="ed-row"><span>${esc(k)}</span><span>${esc(v)}</span></div>`);
      });
    if (feed.threats && feed.threats.length) {
      rows.push(
        `<div class="ed-row"><span>threats</span><span>${esc(feed.threats.join(", "))}</span></div>`
      );
    }
    if (!rows.length) {
      rows.push(`<div class="ed-row"><span>status</span><span>${feed.live ? "live" : "idle"}</span></div>`);
    }
    return rows.join("");
  }

  function render(doc) {
    const pillar = doc.pillar || pillarFromPath();
    const meta = PILLARS[pillar] || { title: pillar, tag: "ELLIE diagnostic" };
    const title = $("ed-title");
    if (title) title.textContent = meta.title;
    document.title = "ELLIE · " + meta.title;

    const pv = doc.pillar_posture || {};
    const verdict = $("ed-verdict");
    if (verdict) {
      verdict.textContent = `${pv.verdict || "—"} · ${pv.live != null ? pv.live + "/" + (pv.feed_count || "—") : ""}`;
      verdict.className = "ed-verdict " + verdictClass(pv.verdict);
    }

    const summary = $("ed-summary");
    if (summary) {
      const sw = doc.systemwide || {};
      summary.innerHTML = [
        `<div class="ed-stat"><b>${esc(doc.threat_warn_level || sw.threat_warn_level || "high")}</b><small>Threat level</small></div>`,
        `<div class="ed-stat"><b>${sw.score != null ? Number(sw.score).toFixed(2) : "—"}</b><small>System score</small></div>`,
        `<div class="ed-stat"><b>${esc(meta.tag)}</b><small>Pillar scope</small></div>`,
      ].join("");
    }

    const feedsEl = $("ed-feeds");
    const feeds = doc.feeds || [];
    if (feedsEl) {
      feedsEl.innerHTML = feeds.length
        ? feeds
            .map(function (f) {
              return (
                `<article class="ed-feed">` +
                `<div class="ed-feed-head"><strong>${esc(f.id)}</strong>` +
                `<span class="${f.live ? "ed-live" : "ed-idle"}">${esc(f.verdict || "—")}</span></div>` +
                `<div class="ed-feed-body">${feedRows(f)}</div></article>`
              );
            })
            .join("")
        : '<p class="ed-foot">No feeds for this pillar.</p>';
    }

    const foot = $("ed-foot");
    if (foot) {
      foot.textContent = `ELLIE · ${meta.title} · ${doc.updated || "—"} · workers report, ELLIE decides`;
    }
  }

  async function refresh(scan) {
    const pillar = pillarFromPath();
    const url =
      `/api/field-ellie-fier/pillar/${encodeURIComponent(apiPillarSlug())}` + (scan ? "?scan=1" : "");
    try {
      const res = await fetch(url, { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) return;
      render(await res.json());
    } catch (_) {}
  }

  $("ed-refresh")?.addEventListener("click", function () {
    refresh(true);
  });

  refresh(false);
  setInterval(function () {
    refresh(false);
  }, 20000);
})();