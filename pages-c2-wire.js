/**
 * GitHub Pages — Universal Protector C2 wire-up (version stamp, OPS routes, protector bar).
 */
(function (global) {
  "use strict";

  function pagesRuntime() {
    return (
      document.body?.dataset?.pagesRuntime === "1" ||
      !!global.HOSTESS7_PAGES_BASE ||
      !!global.HOSTESS7_PAGES
    );
  }

  function base() {
    return global.HOSTESS7_PAGES_BASE || "/Hostess7";
  }

  function assetHost() {
    return global.H7_ASSET_HOST || base();
  }

  function $(id) {
    return document.getElementById(id);
  }

  function pagesRoutes() {
    const b = base().replace(/\/$/, "");
    const commandUrl = b === "/command" ? "/command/" : b + "/command/";
    return {
      command: commandUrl,
      desktop: b + "/desktop/",
      queen: b + "/queen/browser.html",
      ammonet: b + "/ammonet/",
      finalInternet: b + "/final-internet/",
      training: b + "/training-room/",
      g16: b + "/g16-build-output/",
      zacs: b + "/zacs/png/",
      bookmark: b + "/bookmark-jump/",
      vault: b + "/field-znetwork-vault/",
      panel: commandUrl,
      threat: b === "/command" ? assetHost().replace(/\/$/, "") + "/threat-panel/" : b + "/threat-panel/",
      basement: "/command/",
    };
  }

  async function stampVersion() {
    const verBtn = $("nexus-version-btn");
    const detail = $("nexus-update-detail");
    let ver = "2.0.7h";
    try {
      const status = await fetch("/api/status", { cache: "no-store" }).then((r) => (r.ok ? r.json() : null));
      if (status?.version) ver = status.version;
    } catch (_) {}
    if (verBtn) verBtn.textContent = "v" + ver;
    const title = $("nexus-version-title");
    if (title) title.textContent = "NEXUS-Shield";
    const sub = $("nexus-brand-sub");
    if (sub) {
      sub.textContent = global.NEXUS_C2_BASEMENT
        ? "NEXUS C2 Basement · secure layer · black · emerald · rose · shared with everyone"
        : "Universal Protector · AmmoNet ISP · Final Internet · Hostess 7 · GitHub Pages C2 · threat HIGH";
    }
    if (detail) {
      detail.textContent = "Pages lane v" + ver + " · sovereign C2 · loopback for live training";
      detail.classList.remove("update-ready");
    }
    const upBtn = $("nexus-upgrade-btn");
    const restartBtn = $("nexus-restart-btn");
    if (upBtn) {
      upBtn.style.display = "none";
      upBtn.disabled = true;
    }
    if (restartBtn) {
      restartBtn.style.display = "none";
      restartBtn.disabled = true;
    }
    const help = $("help-bar");
    if (help && !help.dataset.pagesStamped) {
      help.dataset.pagesStamped = "1";
      const strong = help.querySelector("strong");
      if (strong) {
        strong.textContent =
          "v" + ver + " Universal Protector — GitHub Pages C2. Command · US · Packets · Threats · Intel · Final Eye · Library · System.";
      }
    }
  }

  function wireHeaderLinks() {
    const routes = pagesRoutes();
    const queenLink = document.querySelector(".header-twitch-link");
    if (queenLink) queenLink.href = routes.queen;
    document.querySelectorAll('a[href*="127.0.0.1:9481"]').forEach((a) => {
      if (/browser\.html/.test(a.href)) a.href = routes.queen;
    });
    document.querySelectorAll('a[href*="127.0.0.1:9477"]').forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (/\/command/.test(href)) a.href = routes.command;
      else if (/\/desktop/.test(href)) a.href = routes.desktop;
      else a.href = routes.panel;
    });
  }

  function wireOpsFlow() {
    const routes = pagesRoutes();
    document.querySelectorAll("[data-pages-route]").forEach((el) => {
      const key = el.dataset.pagesRoute;
      if (routes[key]) {
        if (el.tagName === "A") el.href = routes[key];
        else el.addEventListener("click", () => {
          global.location.href = routes[key];
        });
      }
    });
    const status = $("h7-command-status");
    if (status && !status.dataset.pagesWired) {
      status.dataset.pagesWired = "1";
      status.textContent = "GitHub Pages · NEXUS-Shield C2 · static Super Intelligence deck";
    }
  }

  function bootProtector() {
    if (global.NexusUniversalProtector?.boot) {
      global.NexusUniversalProtector.boot();
      return;
    }
    setTimeout(bootProtector, 80);
  }

  function boot() {
    if (!pagesRuntime()) return;
    document.documentElement.classList.add("h7-pages-c2");
    document.documentElement.classList.remove("h7-pages-lane");
    stampVersion().catch(() => {});
    wireHeaderLinks();
    wireOpsFlow();
    bootProtector();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.Hostess7PagesC2 = { boot, pagesRoutes };
})(typeof window !== "undefined" ? window : globalThis);