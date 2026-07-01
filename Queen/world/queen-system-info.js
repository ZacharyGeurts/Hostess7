/**
 * Queen emulator system info — device visual + CHIPS catalog stack for one Game Room system.
 */
(function () {
  "use strict";

  const THUMB_FALLBACK = "/world/assets/combinatronic/chips/generic_die.png";
  const params = new URLSearchParams(location.search);
  const systemId = params.get("system") || params.get("id") || "nes";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function mdToHtml(text) {
    const lines = String(text || "").split("\n");
    const out = [];
    let inList = false;

    function closeList() {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
    }

    for (const raw of lines) {
      const line = raw.trimEnd();
      if (!line.trim()) {
        closeList();
        continue;
      }
      if (line.startsWith("## ")) {
        closeList();
        out.push(`<h3>${inlineMd(line.slice(3))}</h3>`);
        continue;
      }
      if (line.startsWith("# ")) {
        closeList();
        out.push(`<h2>${inlineMd(line.slice(2))}</h2>`);
        continue;
      }
      if (line.startsWith("- ")) {
        if (!inList) {
          out.push("<ul>");
          inList = true;
        }
        out.push(`<li>${inlineMd(line.slice(2))}</li>`);
        continue;
      }
      closeList();
      out.push(`<p>${inlineMd(line)}</p>`);
    }
    closeList();
    return out.join("");
  }

  function inlineMd(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }

  async function fetchInfo() {
    const res = await fetch(`/api/game-room/system?system=${encodeURIComponent(systemId)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  }

  function chipCard(row) {
    const thumb = row.thumb_url || THUMB_FALLBACK;
    const href = row.detail_url || `/world/queen-chips-detail.html?id=${encodeURIComponent(row.id)}`;
    return (
      `<a class="qsi-chip-card" href="${esc(href)}">` +
      `<img src="${esc(thumb)}" alt="${esc(row.label)}" loading="lazy" decoding="async" />` +
      `<span>${esc(row.label)}<small>${esc(row.kind)} · ${esc(row.vendor)}</small></span></a>`
    );
  }

  function render(doc) {
    const root = $("qsi-root");
    const title = $("qsi-title");
    const sub = $("qsi-sub");
    const status = $("qsi-status");
    const launch = $("qsi-launch");
    const catalog = $("qsi-catalog");

    if (!doc || !doc.ok) {
      if (root) {
        root.innerHTML = `<p class="qsi-error">Unknown system: ${esc(systemId)}</p>`;
      }
      if (title) title.textContent = "System not found";
      return;
    }

    const sys = doc.system || {};
    const urls = doc.urls || {};
    const stackPage = doc.stack_page || null;

    if (title) title.textContent = sys.label || doc.system_id;
    if (sub) {
      sub.textContent = [
        sys.era ? `Era ${sys.era}` : "",
        sys.cpu ? sys.cpu : "",
        doc.platform_stack_label || doc.platform_stack || "",
      ]
        .filter(Boolean)
        .join(" · ");
    }
    document.title = `${sys.label || doc.system_id} · Queen CHIPS`;

    if (launch) launch.href = urls.game_room || `/world/queen-game-room.html?system=${doc.system_id}`;
    if (catalog) catalog.href = urls.catalog_stack || urls.chips_catalog || "/world/queen-chips-catalog.html";

    if (status) {
      status.innerHTML = [
        `<span class="gr-pill${sys.status === "active" ? " ok" : ""}">${esc(sys.status || "—")}</span>`,
        doc.platform_stack
          ? `<span class="gr-pill ok">${esc(doc.platform_stack)}</span>`
          : `<span class="gr-pill">no stack</span>`,
        `<span class="gr-pill">${doc.stack_chip_count ?? 0} dies</span>`,
      ].join("");
    }

    const deviceImg = doc.device_image || `/library/assets/devices/${doc.system_id}.png`;
    const systemChip = doc.system_chip;
    const stackChips = (doc.stack_chips || []).filter((c) => c.id !== systemChip?.id);

    const prose = stackPage?.body
      ? `<article class="qsi-prose">${mdToHtml(stackPage.body)}</article>`
      : "";

    const systemChipHtml = systemChip
      ? `<a class="qsi-system-chip" href="${esc(systemChip.detail_url)}">` +
        `<img src="${esc(systemChip.thumb_url || THUMB_FALLBACK)}" alt="" loading="lazy" />` +
        `<div><strong>${esc(systemChip.label)}</strong>` +
        `<span>${esc(systemChip.kind)} · ${esc(systemChip.vendor)} · primary system die</span></div></a>`
      : "";

    const actions = [
      urls.game_room
        ? `<a href="${esc(urls.game_room)}">Game Room</a>`
        : "",
      urls.catalog_stack
        ? `<a href="${esc(urls.catalog_stack)}">Platform stack catalog</a>`
        : "",
      urls.chip_detail
        ? `<a href="${esc(urls.chip_detail)}">System die detail</a>`
        : "",
      urls.dewey_device
        ? `<a href="${esc(urls.dewey_device)}">Dewey device book</a>`
        : "",
      urls.chips_catalog
        ? `<a href="${esc(urls.chips_catalog)}">Full CHIPS catalog</a>`
        : "",
    ]
      .filter(Boolean)
      .join("");

    if (root) {
      root.innerHTML =
        `<div class="qsi-layout">` +
        `<aside class="qsi-device-panel">` +
        `<div class="qsi-device-frame">` +
        `<img src="${esc(deviceImg)}" alt="${esc(sys.label)} device visual" loading="eager" decoding="async" />` +
        `</div>` +
        `<p class="qsi-device-meta">` +
        `<strong>${esc(sys.label)}</strong><br />` +
        `${esc(sys.chips || "")}<br />` +
        `Ratio ${esc(sys.ratio || "—")} · ${esc(sys.cpu || "—")}` +
        (doc.dewey_book?.title ? `<br />${esc(doc.dewey_book.title)}` : "") +
        `</p></aside>` +
        `<section class="qsi-content">` +
        `<div class="qsi-stack-head">` +
        `<h2>${esc(doc.platform_stack_label || stackPage?.title || "CHIPS platform stack")}</h2>` +
        `<p>${esc(doc.platform_stack || "—")} · ${doc.stack_chip_count ?? 0} catalog dies for this machine</p>` +
        `</div>` +
        `<div class="qsi-actions">${actions}</div>` +
        systemChipHtml +
        prose +
        `<div class="qsi-chip-section">` +
        `<h3>Stack dies</h3>` +
        `<div class="qsi-chip-grid">` +
        (stackChips.length ? stackChips.map(chipCard).join("") : `<p class="qsi-loading">No companion dies indexed.</p>`) +
        `</div></div></section></div>`;
    }
  }

  async function refresh() {
    const root = $("qsi-root");
    if (root) root.innerHTML = `<p class="qsi-loading">Loading system info…</p>`;
    const doc = await fetchInfo();
    render(doc);
    return doc;
  }

  function init() {
    $("qsi-refresh")?.addEventListener("click", refresh);
    refresh();
  }

  globalThis.QueenSystemInfo = { refresh, systemId };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();