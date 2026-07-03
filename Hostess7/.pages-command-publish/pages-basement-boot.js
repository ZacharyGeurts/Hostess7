/**
 * NEXUS C2 secure basement — drop to real layer 1 · black · emerald · rose · shared.
 */
(function (global) {
  "use strict";

  function isBasement() {
    const parts = global.location.pathname.split("/").filter(Boolean);
    return parts[0] === "command" || /[?&]basement=1/.test(global.location.search || "");
  }

  function applyTheme() {
    const root = document.documentElement;
    root.classList.add(
      "nexus-c2-basement",
      "mil-c2",
      "nexus-military-v8",
      "nexus-v82",
      "dusty-midnight",
      "nexus-4k"
    );
    root.dataset.queenTheme = "black_emerald_rose_2026";
    root.dataset.nexusC2Basement = "1";
    if (document.body) {
      document.body.dataset.nexusC2Basement = "1";
      document.body.dataset.pagesRuntime = "1";
    }
  }

  function mountHud(doc) {
    if (document.getElementById("nc2b-hud")) return;
    const hud = document.createElement("div");
    hud.id = "nc2b-hud";
    hud.className = "nc2b-hud";
    hud.setAttribute("role", "status");
    hud.setAttribute("aria-live", "polite");
    const gates = doc?.gates || {};
    const gateBits = Object.keys(gates)
      .filter((k) => gates[k])
      .slice(0, 4)
      .map((k) => k.replace(/_/g, " "))
      .join(" · ");
    hud.innerHTML =
      "<span><strong>NEXUS C2 Basement</strong> · layer −3 · secure command deck</span>" +
      '<span class="nc2b-rose">black · emerald · rose</span>' +
      '<span class="nc2b-secure">SECURE · shared with everyone</span>' +
      (gateBits ? "<span>" + gateBits + "</span>" : "");
    document.body.insertBefore(hud, document.body.firstChild);
  }

  async function loadBasementState() {
    try {
      const url = (global.H7Base ? global.H7Base("/api/nexus-c2-basement") : "/api/nexus-c2-basement");
      const res = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
      if (res.ok) return await res.json();
    } catch (_e) {}
    return {
      schema: "nexus-c2-basement/v1",
      role: "secure_basement",
      weaponized: true,
      war_posture: true,
      kiosk: false,
      command_deck: true,
      pages: true,
      motto: "NEXUS C2 is the secure basement — not a kiosk.",
    };
  }

  function boot() {
    if (!isBasement()) return;
    applyTheme();
    loadBasementState().then(mountHud);
    try {
      sessionStorage.setItem("nexus-c2-basement", "1");
    } catch (_e) {}
    global.NEXUS_C2_BASEMENT = true;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : globalThis);