/**
 * Queen — plated field branding · local assets only.
 */
(function (global) {
  "use strict";

  const SEQ = "queen";
  let buf = "";

  function guideUrl() {
    return `${location.origin}/world/queen-browser-guide.html`;
  }

  function toast() {
    let el = document.getElementById("qb-queen-crown-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "qb-queen-crown-toast";
      el.className = "qb-queen-crown-toast";
      el.setAttribute("role", "status");
      el.innerHTML = `
        <strong>Queen Browser</strong>
        <span>Your field web engine — sovereign on loopback. Migrated from another browser?
          <a href="${guideUrl()}">Open the user guide</a> for imports, shortcuts, and gates.</span>
        <img src="assets/branding/queen-crown-surprise.svg" alt="" width="216" height="216" loading="lazy"
          title="Queen crown — local asset only" />`;
      document.body.appendChild(el);
    }
    document.body.classList.add("qb-queen-crown-reveal");
    el.classList.add("qb-queen-crown-toast--show");
    setTimeout(() => {
      el.classList.remove("qb-queen-crown-toast--show");
      document.body.classList.remove("qb-queen-crown-reveal");
    }, 7200);
  }

  function wireCrownEgg() {
    let btn = document.getElementById("qb-queen-crown-egg");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.id = "qb-queen-crown-egg";
      btn.className = "qb-queen-crown-egg";
      btn.setAttribute("aria-label", "Queen crown — open guide");
      btn.title = "Queen crown — click for tips. Type queen for the guide toast.";
      document.body.appendChild(btn);
    }
    btn.addEventListener("click", () => {
      toast();
    });
  }

  function wireTooltips() {
    const avatar = document.querySelector(".qb-brand-avatar");
    if (avatar) {
      avatar.title =
        "Queen Browser — black · emerald · rose. Double-click for quick tips.";
      avatar.setAttribute("aria-label", "Queen Browser — field web engine");
    }
    const strip = document.querySelector(".qb-brand-strip span:last-child");
    if (strip) strip.textContent = "Queen";
    document.querySelector(".qb-brand-strip")?.setAttribute(
      "title",
      "Queen Browser — sovereign field web engine. Guide: /world/queen-browser-guide.html",
    );
    document.getElementById("qb-security-strip")?.setAttribute(
      "title",
      "Queen Webbrowser — CHIPS/cores web surface. Gates held on every navigation.",
    );
    document.getElementById("qb-gate-pill")?.setAttribute(
      "title",
      "Gate verdict — every navigation checked. Hostile contacts quarantined before memory.",
    );
    document.getElementById("qb-compat-pill")?.setAttribute(
      "title",
      "Web compat — legacy sites auto-caged. AI-friendly without remote polyfill CDNs.",
    );
    document.getElementById("qb-proxy")?.setAttribute(
      "title",
      "Queen proxy — loopback fallback when a site blocks iframes. Still gate-held.",
    );
    document.getElementById("qb-gates")?.setAttribute(
      "title",
      "Open gate manifest — see which defenses are armed for Humans and AI.",
    );
    const help = document.getElementById("qb-ha-help");
    if (help) {
      help.title = "Open Queen Browser user guide";
      help.setAttribute("aria-label", "Queen Browser user guide");
    }
  }

  function onKey(ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const ch = String(ev.key || "").toLowerCase();
    if (ch.length !== 1) return;
    buf = (buf + ch).slice(-SEQ.length);
    if (buf.endsWith(SEQ)) toast();
  }

  function init() {
    const surface = document.body?.dataset?.queenSurface;
    if (surface !== "browser" && surface !== "field-home") return;
    document.addEventListener("keydown", onKey);
    if (surface === "browser") {
      wireCrownEgg();
      wireTooltips();
      document.querySelector(".qb-brand-avatar")?.addEventListener("dblclick", toast);
    }
    if (document.title.includes("Browser") || document.title === "Queen") {
      document.title = "Queen Browser";
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  global.QueenBranding = { revealCrown: toast, guideUrl };
})(window);