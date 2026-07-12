/**
 * Queen Browser — Humans & AI local assistant strip (no remote).
 * Rotating IT tips · contact vector · Hostess authority posture.
 */
(function () {
  "use strict";

  const TIPS = [
    {
      who: "human",
      text: "Your bookmarks and passwords stay on this machine — vault encrypted, gates held.",
    },
    {
      who: "ai",
      text: "Local AI reads field gates only. No cloud telemetry from this browser shell.",
    },
    {
      who: "human",
      text: "Shift+click IMPORT to make Queen your default browser — replaces host browser handlers on this machine.",
    },
    {
      who: "human",
      text: "New to Queen? Click ? in the bar or open /world/queen-browser-guide.html for migration help.",
    },
    {
      who: "ai",
      text: "Hostess 7 assists; humans remain in the loop. Supreme authority stays local.",
    },
    {
      who: "human",
      text: "Drop bookmarks.html or passwords.csv into .nexus-state/imports/ to migrate safely.",
    },
    {
      who: "ai",
      text: "Quarantined URLs never load silently — check the gate drawer (◇) for verdicts.",
    },
    {
      who: "human",
      text: "Mic, camera, and screen capture are locked until you grant local capture.",
    },
    {
      who: "ai",
      text: "UPDATE pulls NXF manifest when online — install runs locally with your approval.",
    },
    {
      who: "ai",
      text: "Muscle memory — Hostess 7 learns your repeat navigation and shortcuts on this machine only.",
    },
    {
      who: "human",
      text: "Ask Hostess what sites you visit most — procedural habits stay vault-local, never cloud.",
    },
    {
      who: "human",
      text: "Stress and terror are discerned locally — corroborate before act; never illegal recreational shoot.",
    },
    {
      who: "ai",
      text: "External panic is held until IFF clears — signals directed from another being do not auto-escalate.",
    },
  ];

  let tipIdx = 0;
  let vector = null;

  function $(id) {
    return document.getElementById(id);
  }

  function renderVector(el) {
    if (!el || !vector) return;
    const v = vector;
    const pct = (k) => `${Number(v[k] || 0).toFixed(0)}%`;
    el.innerHTML = [
      `<span class="qb-ha-pill qb-ha-ai" title="AI contact share — local classifier only">AI ${pct("ai")}</span>`,
      `<span class="qb-ha-pill qb-ha-human" title="Human situational share — you stay authoritative">Human ${pct("human")}</span>`,
      `<span class="qb-ha-pill qb-ha-unknown" title="Unknown contacts held at gate">? ${pct("unknown")}</span>`,
    ].join("");
  }

  function renderTip() {
    const tipEl = $("qb-ha-tip");
    const whoEl = $("qb-ha-who");
    if (!tipEl) return;
    const row = TIPS[tipIdx % TIPS.length];
    tipIdx += 1;
    if (whoEl) {
      whoEl.textContent = row.who === "ai" ? "AI" : "Human";
      whoEl.className = `qb-ha-who qb-ha-who--${row.who}`;
      whoEl.title =
        row.who === "ai"
          ? "Local AI assistant — Hostess / field brain on loopback only"
          : "Human operator — you approve installs, capture, and high-risk actions";
    }
    tipEl.textContent = row.text;
    tipEl.title = row.text;
  }

  async function refreshVector() {
    try {
      const r = await fetch("/api/contact-vector", { cache: "no-store" });
      if (!r.ok) return;
      const doc = await r.json();
      vector = doc.vector || doc.contact_vector || doc;
      renderVector($("qb-ha-vector"));
    } catch {
      /* offline — local tips still run */
    }
  }

  async function recordShortcut(combo, context) {
    try {
      await fetch("/api/muscle-memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "record_shortcut",
          combo,
          context: context || "browser",
          source: "queen-humans-ai",
        }),
      });
    } catch {
      /* local-only assist */
    }
  }

  function bind() {
    $("qb-ha-help")?.addEventListener("click", () => {
      const guide = `${location.origin}/world/queen-browser-guide.html`;
      if (globalThis.QueenOS?.browser?.openTab) {
        globalThis.QueenOS.browser.openTab(guide, { title: "Queen Guide" });
      } else {
        window.open(guide, "_blank", "noopener");
      }
    });
    renderTip();
    refreshVector();
    setInterval(renderTip, 14000);
    setInterval(refreshVector, 45000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();