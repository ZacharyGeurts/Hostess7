/**
 * AmmoNet ISP hub — Final Internet · steel plates · Hostess 7 public modules
 */
(function () {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function pagesBase() {
    return window.HOSTESS7_PAGES_BASE || "";
  }

  function withBase(path) {
    if (window.H7Base) return window.H7Base(path);
    const b = pagesBase().replace(/\/$/, "");
    return b + (path.startsWith("/") ? path : "/" + path);
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) return null;
    return r.json();
  }

  function pill(text, kind) {
    return `<span class="an-pill${kind ? " an-pill--" + kind : ""}">${esc(text)}</span>`;
  }

  function renderPills(doc) {
    const el = $("an-pills");
    if (!el || !doc) return;
    const isp = doc.isp || {};
    el.innerHTML = [
      pill("AmmoNet ISP", "ok"),
      pill("Pipe " + (isp.pipe_percent || 100) + "%", "ok"),
      pill("Mode " + (isp.mode || "ACTIVE"), isp.mode === "ACTIVE" ? "ok" : "warn"),
      pill("Boss " + (isp.boss || "hostess7"), "ok"),
      pill(doc.pages ? "Pages live" : "Loopback", doc.pages ? "ok" : "warn"),
    ].join("");
    const tag = $("an-tagline");
    if (tag && doc.final_internet?.motto) tag.textContent = doc.final_internet.motto;
  }

  function renderMigration(doc) {
    const el = $("an-migration");
    if (!el) return;
    const mig = doc.final_internet?.migration || {};
    const stages = mig.stages || [];
    el.innerHTML = stages
      .map(function (s, i) {
        return (
          '<div class="an-card"><strong>' +
          esc(String(s).replace(/_/g, " ")) +
          "</strong><span>Stage " +
          (i + 1) +
          " · Final Internet</span></div>"
        );
      })
      .join("");
  }

  function renderLayers(doc) {
    const el = $("an-layers");
    if (!el) return;
    const layers = doc.layers || [];
    el.innerHTML = layers
      .map(function (layer) {
        const boss = layer.boss || layer.id === "hostess7";
        return (
          '<div class="an-card' +
          (boss ? " an-card--boss" : "") +
          '"><strong>' +
          esc(layer.label || layer.id) +
          '</strong><span>z' +
          esc(layer.z) +
          (boss ? " · boss" : "") +
          "</span></div>"
        );
      })
      .join("");
  }

  function renderSteel(doc) {
    const el = $("an-steel");
    if (!el) return;
    const steel = doc.slices?.steel_plates || {};
    const meld = doc.slices?.plate_meld || {};
    const opt = doc.slices?.steel_optimal || {};
    const plates = steel.plates || [];
    const cards = [
      '<div class="an-card"><strong>Steel plates</strong><span>' +
        esc(String(steel.plate_count || plates.length || 0)) +
        " plates · depth " +
        esc(String(steel.connection_depth || "—")) +
        '</span><div class="an-plate-bar"><i style="width:' +
        Math.min(100, (steel.plate_count || plates.length || 0) * 8) +
        '%"></i></div></div>',
      '<div class="an-card"><strong>Plate meld</strong><span>gen ' +
        esc(String(meld.generation || "—")) +
        " · hash " +
        esc(String(meld.chain_hash || "pending")) +
        (meld.ok ? " · fused" : " · partial") +
        "</span></div>",
      '<div class="an-card"><strong>Optimal sort</strong><span>" +
        esc((opt.algorithms && opt.algorithms.brute_force_permutation) || "steel optimal") +
        "</span></div>",
    ];
    plates.slice(0, 4).forEach(function (p) {
      cards.push(
        '<div class="an-card"><strong>' +
          esc(p.id || p.name || "plate") +
          "</strong><span>path " +
          esc(String(p.path_pct || "—")) +
          "%</span></div>"
      );
    });
    el.innerHTML = cards.join("");
  }

  function moduleCard(m) {
    const href = m.pages_url || m.pages || "#";
    const url = String(href).startsWith("http") ? href : withBase(href);
    return (
      '<a class="an-card" href="' +
      esc(url) +
      '"><strong>' +
      esc(m.label || m.id) +
      '</strong><span>operational · ' +
      esc(m.lane || "pages") +
      (m.category ? " · " + esc(m.category) : "") +
      "</span></a>"
    );
  }

  function renderModules(doc) {
    const el = $("an-modules");
    if (!el) return;
    const mods = (doc.modules || []).filter(function (m) {
      return m.pages || m.pages_url;
    });
    el.innerHTML = mods.slice(0, 12).map(moduleCard).join("");
  }

  function renderCatalog(doc) {
    const el = $("an-catalog");
    const note = $("an-surface-note");
    if (!el) return;
    const count = doc.surface_count || (doc.modules || []).length;
    if (note) {
      note.textContent =
        count +
        " Hostess 7 surfaces operational on GitHub Pages — AmmoNet ISP · Final Internet · loopback meld on ./nexus.sh panel";
    }
    const catalog = doc.surface_catalog || [];
    if (!catalog.length) {
      el.innerHTML = (doc.modules || []).map(moduleCard).join("");
      return;
    }
    el.innerHTML = catalog
      .map(function (cat) {
        const cards = (cat.surfaces || []).map(moduleCard).join("");
        return (
          '<div class="an-catalog-group"><h3>' +
          esc(cat.label || cat.id) +
          '</h3><div class="an-modules">' +
          cards +
          "</div></div>"
        );
      })
      .join("");
  }

  function renderDnsAuthority(zones) {
    const note = $("an-dns-note");
    const el = $("an-dns-catalog");
    if (!el || !zones) return;
    const base = zones.pages_base || zones.web_presence?.home || pagesBase();
    if (note) {
      note.textContent =
        (zones.sole_dns_authority ? "Sole authority · " : "") +
        (zones.zone_count || 0) +
        " zones · " +
        (zones.record_count || 0) +
        " records · Pages " +
        base;
    }
    const list = zones.zones || [];
    el.innerHTML = list
      .map(function (z) {
        const recs = (z.records || []).slice(0, 6);
        const rows = recs
          .map(function (r) {
            const name = r.name === "@" ? z.zone : r.name + "." + z.zone;
            return (
              "<tr><td>" +
              esc(name) +
              "</td><td>" +
              esc(r.type) +
              "</td><td>" +
              esc(r.value) +
              "</td></tr>"
            );
          })
          .join("");
        return (
          '<div class="an-card"><strong>' +
          esc(z.zone) +
          '</strong><table class="an-dns-table"><tbody>' +
          rows +
          "</tbody></table></div>"
        );
      })
      .join("");
  }

  function renderQemu(doc) {
    const el = $("an-qemu");
    if (!el) return;
    const q = doc.slices?.qemu_transfer || {};
    el.innerHTML =
      '<div class="an-card"><strong>QEMU pipeline</strong><span>' +
      (q.running ? "running · secure transfer active" : "idle · Pages static lane") +
      " · " +
      esc(String(q.completed || 0)) +
      "/" +
      esc(String(q.target || "?")) +
      " nodes</span></div>" +
      '<div class="an-card"><strong>Internet clean</strong><span>' +
      esc((doc.slices?.internet_clean || {}).motto || "HTTPS+Secure bookmarks") +
      "</span></div>";
  }

  async function refresh() {
    const [doc, zones] = await Promise.all([
      fetchJson("/api/ammonet"),
      fetchJson("/api/ammonet-dns-zones"),
    ]);
    if (!doc) return;
    if (zones) renderDnsAuthority(zones);
    renderPills(doc);
    renderMigration(doc);
    renderLayers(doc);
    renderSteel(doc);
    renderModules(doc);
    renderCatalog(doc);
    renderQemu(doc);
    const queen = $("an-queen-link");
    if (queen && doc.routes?.queen) queen.href = doc.routes.queen;
  }

  $("an-refresh")?.addEventListener("click", function () {
    refresh();
  });

  $("an-meld")?.addEventListener("click", async function () {
    const btn = $("an-meld");
    if (btn) btn.disabled = true;
    try {
      await fetch("/api/ammonet/meld", { method: "POST", credentials: "same-origin", body: "{}" });
      await refresh();
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  refresh();
  setInterval(refresh, 20000);
})();