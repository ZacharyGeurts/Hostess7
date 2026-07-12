/**
 * AmmoDrive — GitHub Pages read-only lane; loopback upgrade when sovereign panel is live.
 */
(function (global) {
  "use strict";

  const PRODUCT = "AmmoDrive";
  const INTERVAL_PAGES_MS = 8000;
  const INTERVAL_LOOPBACK_MS = 2500;

  const state = {
    wired: false,
    timer: null,
    loopbackLive: false,
    publicDoc: null,
    storageDoc: null,
    racksDoc: null,
  };

  function base() {
    return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    return base() + (path.startsWith("/") ? path : "/" + path);
  }

  function loopback() {
    return (global.H7_LOOPBACK_AUTHORITY || "http://127.0.0.1:9477").replace(/\/$/, "");
  }

  function onPagesRuntime() {
    try {
      const host = global.location && global.location.hostname;
      if (host && host.endsWith(".github.io")) return true;
      if (document.body && document.body.dataset && document.body.dataset.pagesRuntime === "1") return true;
    } catch (_) {}
    return false;
  }

  function markGlobals(doc) {
    global.AMMODRIVE_PUBLIC = doc || state.publicDoc;
    global.AMMODRIVE_PAGES_LANE = state.loopbackLive ? "sovereign" : "pages";
    global.AMMODRIVE_PRODUCT = PRODUCT;
    document.documentElement.dataset.ammodriveProduct = PRODUCT;
    document.documentElement.dataset.ammodriveLane = global.AMMODRIVE_PAGES_LANE;
    if (document.body) {
      document.body.dataset.ammodrive = "1";
      document.body.dataset.ammodriveSecure = "1";
    }
  }

  function formatGb(n) {
    const v = Number(n);
    if (!isFinite(v) || v <= 0) return null;
    return v >= 100 ? Math.round(v) + " GB" : v.toFixed(1) + " GB";
  }

  function storageBadge() {
    const totals = (state.racksDoc && state.racksDoc.storage_totals) || (state.publicDoc && state.publicDoc.storage_totals) || {};
    const combined = totals.combined_h7_addressable_gb || totals.total_redundant_gb || totals.logical_gb;
    const racks = (state.racksDoc && (state.racksDoc.slots || state.racksDoc.racks_provisioned)) || [];
    const rackN = racks.length || Number(state.publicDoc && state.publicDoc.rack_count) || 0;
    const gb = formatGb(combined);
    const iso = (state.racksDoc && state.racksDoc.internet_isolated) !== false;
    let label = PRODUCT;
    if (gb) label += " · " + gb;
    if (rackN) label += " · " + rackN + " racks";
    if (iso) label += " · isolated";
    if (state.loopbackLive) label += " · live";
    else if (onPagesRuntime()) label += " · Pages mirror";
    return label;
  }

  function updateChrome() {
    const motto =
      (state.publicDoc && state.publicDoc.motto) ||
      (state.storageDoc && state.storageDoc.motto) ||
      "AmmoDrive — sovereign H7 storage on loopback; read-only mirror on GitHub Pages.";
    const badge = storageBadge();

    const wall = document.getElementById("hd-wall-label");
    if (wall && !wall.dataset.ammodriveLocked) {
      wall.textContent = badge;
      wall.title = motto;
    }

    const bootDetail = document.getElementById("boot-detail");
    if (bootDetail) {
      bootDetail.textContent = badge + " · " + motto;
    }

    const stripCount = document.getElementById("h7-ammonet-strip-count");
    if (stripCount && state.publicDoc) {
      const sec = state.publicDoc.security || {};
      stripCount.textContent = PRODUCT + (sec.pages_read_only ? " · secure Pages mirror" : "");
      stripCount.title = sec.motto || motto;
    }

    global.dispatchEvent(
      new CustomEvent("ammodrive:pulse", {
        detail: {
          product: PRODUCT,
          loopbackLive: state.loopbackLive,
          public: state.publicDoc,
          storage: state.storageDoc,
          racks: state.racksDoc,
        },
      })
    );
  }

  async function fetchJson(url) {
    const r = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!r.ok) return null;
    return r.json();
  }

  async function loadAmmoDrive() {
    const pagesPaths = [
      api("/api/ammodrive-public"),
      api("/api/ammodrive-storage"),
      api("/api/ammodrive-qemu-racks"),
    ];
    const loopPaths = [
      loopback() + "/api/ammodrive-public",
      loopback() + "/api/ammodrive-storage",
      loopback() + "/api/ammodrive-qemu-racks",
    ];
    const order = onPagesRuntime() ? pagesPaths : loopPaths.concat(pagesPaths);

    let pub = null;
    let storage = null;
    let racks = null;
    let live = false;

    for (let i = 0; i < order.length; i++) {
      const url = order[i];
      const fromLoop = url.indexOf("127.0.0.1") >= 0 || url.indexOf("localhost") >= 0;
      try {
        const doc = await fetchJson(url);
        if (!doc) continue;
        if (fromLoop && !onPagesRuntime()) live = true;
        if (url.indexOf("ammodrive-public") >= 0 && !pub) pub = doc;
        if (url.indexOf("ammodrive-storage") >= 0 && !storage) storage = doc;
        if (url.indexOf("ammodrive-qemu-racks") >= 0 && !racks) racks = doc;
      } catch (_) {}
    }

    if (!pub) {
      try {
        pub = await fetchJson(api("/api/ammodrive-public.json"));
      } catch (_) {}
    }
    if (!storage) {
      try {
        storage = await fetchJson(api("/api/ammodrive-storage.json"));
      } catch (_) {}
    }
    if (!racks) {
      try {
        racks = await fetchJson(api("/api/ammodrive-qemu-racks.json"));
      } catch (_) {}
    }

    state.loopbackLive = live;
    state.publicDoc = pub;
    state.storageDoc = storage;
    state.racksDoc = racks;
    markGlobals(pub);
    updateChrome();
    return pub;
  }

  function schedulePulse() {
    if (state.timer) global.clearInterval(state.timer);
    const ms = state.loopbackLive ? INTERVAL_LOOPBACK_MS : INTERVAL_PAGES_MS;
    state.timer = global.setInterval(loadAmmoDrive, ms);
  }

  function wire() {
    if (state.wired) return;
    state.wired = true;
    loadAmmoDrive().then(schedulePulse);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }

  global.AmmoDrivePagesWire = {
    pulse: loadAmmoDrive,
    state: state,
    product: PRODUCT,
  };
})(typeof window !== "undefined" ? window : globalThis);