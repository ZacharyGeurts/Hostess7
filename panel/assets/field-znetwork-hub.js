/**
 * ZNetwork Hub — NEXUS C2 stack · Queen Browser · AmmoOS · settings + live posture
 */
(function () {
  "use strict";

  const STORAGE_KEY = "znetwork_hub_prefs_v1";
  const DEFAULT_PREFS = {
    autoRefresh: true,
    refreshSec: 15,
    compactStack: false,
    showSiblings: true,
    highlightLayer: "znetwork",
  };

  const SURFACES = {
    nexus_c2: { url: "/field", label: "C2 Desktop" },
    queen: { url: "http://127.0.0.1:9481/world/browser.html", label: "Queen Browser" },
    ammoos: { url: "/field", label: "AmmoOS Start" },
    vault: { url: "/field-znetwork-vault", label: "Secure Vault" },
    nexus_c2_programmatic: { url: "http://127.0.0.1:9481/world/queen-nexus-c2.html", label: "AmmoOS C2" },
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

  function loadPrefs() {
    try {
      return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
    } catch (_) {
      return { ...DEFAULT_PREFS };
    }
  }

  function savePrefs(prefs) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch (_) {
      /* ignore */
    }
  }

  let prefs = loadPrefs();
  let pollTimer = null;

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!res.ok) return null;
    return res.json();
  }

  function pill(text, kind) {
    return `<span class="zn-pill${kind ? " " + kind : ""}">${esc(text)}</span>`;
  }

  function gateChip(id, ok) {
    return `<div class="zn-gate${ok ? " ok" : " err"}">${esc(id)} ${ok ? "✓" : "✗"}</div>`;
  }

  function renderStack(stackDoc, versionDoc) {
    const el = $("zn-stack");
    if (!el) return;
    const layers = stackDoc?.layers_bottom_up || stackDoc?.layers || [];
    if (!layers.length) {
      el.innerHTML = "<p class=\"zn-tagline\">Stack doctrine unavailable.</p>";
      return;
    }
    el.innerHTML = layers
      .map((layer, idx) => {
        const id = layer.id || "";
        const on = id === prefs.highlightLayer || id === "znetwork";
        const you = id === "znetwork";
        const surf = SURFACES[id];
        const port = layer.port ? `:${layer.port}` : "";
        const link = surf
          ? `<a href="${esc(surf.url)}" target="_blank" rel="noopener">${esc(surf.label)}</a>`
          : layer.surfaces?.field
            ? `<a href="${esc(layer.surfaces.field)}">Open</a>`
            : layer.port
              ? `<a href="http://127.0.0.1:${layer.port}/">:${layer.port}</a>`
              : "";
        return (
          `<article class="zn-layer${on ? " on" : ""}${you ? " you" : ""}" data-layer="${esc(id)}">` +
          `<span class="zn-layer-order">${layer.order ?? idx}</span>` +
          `<div class="zn-layer-body"><strong>${esc(layer.label || id)}</strong>` +
          `<span>${esc(layer.role || "")}${port ? " · " + port : ""}</span></div>` +
          `<div class="zn-layer-link">${link}</div></article>`
        );
      })
      .join("");

    if (prefs.compactStack) el.classList.add("zn-stack--compact");
    else el.classList.remove("zn-stack--compact");
  }

  function renderSiblings(versionDoc) {
    const el = $("zn-siblings");
    if (!el || !prefs.showSiblings) {
      if (el) el.closest(".zn-card")?.classList.add("zn-hidden");
      return;
    }
    el.closest(".zn-card")?.classList.remove("zn-hidden");
    const sibs = versionDoc?.stack_siblings || [];
    const wired = new Set(["ZNetwork", "Grok16", "AMOURANTHRTX", "KILROY", "Final_Ear", "Final_Eye"]);
    el.innerHTML = sibs
      .map((name) => `<span class="zn-sib${wired.has(name) ? " on" : ""}">${esc(name)}</span>`)
      .join("");
  }

  function renderStatus(zn, stackDoc, versionDoc, nexusC2) {
    const pills = $("zn-pills");
    const live = $("zn-live");
    const gates = $("zn-gates");
    const pipe = $("zn-pipe");
    const sovereignty = zn?.sovereignty || {};
    const z = sovereignty.znetwork || zn?.znetwork || {};
    const truth = zn?.truth_gate || {};
    const mode = z.mode || truth.mode || zn?.mode || "—";
    const ok = zn?.ok !== false;
    const pipePct = z.internet_pipe_percent ?? z.internet_pipe_target ?? "—";

    if (pills) {
      pills.innerHTML = [
        pill(ok ? "ZNetwork live" : "ZNetwork offline", ok ? "ok" : "err"),
        pill(`Mode ${mode}`, mode === "ACTIVE" ? "ok" : "warn"),
        pill(`Pipe ${pipePct}%`, Number(pipePct) >= 100 ? "ok" : "warn"),
        pill(versionDoc?.product ? `${versionDoc.product} ${versionDoc.version}` : "AmmoOS", "ok"),
        pill(sovereignty.container || "Queen Browser", ""),
      ].join("");
    }

    if (live) {
      const dns = sovereignty.local_services?.dns || {};
      const dhcp = sovereignty.local_services?.dhcp || {};
      live.innerHTML = [
        row("Orchestrator", zn?.schema || "—"),
        row("Relayer", z.relayer_enabled ? "enabled" : "off"),
        row("Smart inside", zn?.smart_inside?.passthrough_all_traffic !== false ? "passthrough" : "—"),
        row("Never harm OS", sovereignty.hardware_no_break !== false ? "yes" : "no"),
        row("Loopback", sovereignty.loopback_authority || "127.0.0.1"),
        row("Truth DNS", dns.running ? "running" : dns.connected ? "connected" : "idle"),
        row("Field DHCP", dhcp.running ? "running" : "idle"),
        row("Binary", zn?.binary || z.binary || "—"),
        row("Doctrine", (zn?.doctrine || "").split("/").pop() || "znetwork-doctrine.json"),
      ].join("");
    }

    if (pipe) {
      const target = z.internet_pipe_target ?? 100;
      const current = z.internet_pipe_percent ?? 0;
      pipe.innerHTML = [
        `<div class="zn-row"><span>Target</span><span>${esc(target)}%</span></div>`,
        `<div class="zn-row"><span>Current</span><span class="${Number(current) >= 100 ? "zn-ok" : ""}">${esc(current)}%</span></div>`,
        `<div class="zn-row"><span>Sole stack</span><span>${z.sole_stack ? "yes" : "no"}</span></div>`,
        `<div class="zn-row"><span>Protection only</span><span>${truth.protection_only ? "yes" : "no"}</span></div>`,
      ].join("");
    }

    if (gates && truth.gates) {
      gates.innerHTML = Object.entries(truth.gates)
        .map(([k, v]) => gateChip(k, !!(v && v.ok)))
        .join("");
    }

    const log = $("zn-log");
    if (log) {
      const snap = {
        ts: new Date().toISOString(),
        mode,
        pipe: pipePct,
        nexus_c2: nexusC2?.schema || null,
        stack: stackDoc?.title || null,
      };
      const prev = log.textContent || "";
      log.textContent = `${JSON.stringify(snap)}\n${prev}`.slice(0, 4000);
    }
  }

  function row(label, value) {
    return `<div class="zn-row"><span>${esc(label)}</span><span>${esc(value)}</span></div>`;
  }

  function wireSettings() {
    const auto = $("zn-pref-auto");
    const interval = $("zn-pref-interval");
    const compact = $("zn-pref-compact");
    const sibs = $("zn-pref-siblings");
    const layer = $("zn-pref-layer");

    if (auto) auto.checked = !!prefs.autoRefresh;
    if (interval) interval.value = String(prefs.refreshSec);
    if (compact) compact.checked = !!prefs.compactStack;
    if (sibs) sibs.checked = !!prefs.showSiblings;
    if (layer) layer.value = prefs.highlightLayer || "znetwork";

    function apply() {
      prefs = {
        autoRefresh: !!auto?.checked,
        refreshSec: Math.max(5, Number(interval?.value) || 15),
        compactStack: !!compact?.checked,
        showSiblings: !!sibs?.checked,
        highlightLayer: layer?.value || "znetwork",
      };
      savePrefs(prefs);
      schedulePoll();
      refresh();
    }

    [auto, interval, compact, sibs, layer].forEach((el) => {
      el?.addEventListener("change", apply);
    });
  }

  function schedulePoll() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    if (prefs.autoRefresh) {
      pollTimer = setInterval(refresh, prefs.refreshSec * 1000);
    }
  }

  function renderHostess7(h7) {
    const profile = h7?.profile || h7;
    const op = profile?.operator || {};
    const conn = h7?.connection || {};
    const display = $("zn-h7-display");
    const handle = $("zn-h7-handle");
    const bio = $("zn-h7-bio");
    const avatar = $("zn-h7-avatar");
    const pills = $("zn-h7-pills");
    if (display) display.textContent = op.display_name || "BIG GRIN";
    if (handle) handle.textContent = `@${op.handle || "ZacharyGeurts"}`;
    if (bio) bio.textContent = op.bio || "";
    if (avatar && op.avatar_local) avatar.src = op.avatar_local;
    if (pills) {
      pills.innerHTML = [
        pill(conn.connected ? "H7 ↔ ZNetwork" : "Wire pending", conn.connected ? "ok" : "warn"),
        pill("Local profile", "ok"),
        pill("Queen egress", conn.queen_egress === "znetwork_relayer" ? "ok" : ""),
      ].join("");
    }
  }

  async function sendHostessSpeak() {
    const text = ($("zn-h7-speak")?.value || "").trim();
    const res = await fetch("/api/hostess7/znetwork/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "speak", text }),
    });
    const doc = res.ok ? await res.json() : { ok: false };
    const log = $("zn-log");
    if (log) {
      log.textContent = `${JSON.stringify(doc)}\n${log.textContent || ""}`.slice(0, 4000);
    }
    if (doc.ok && $("zn-h7-speak")) $("zn-h7-speak").value = "";
    return doc;
  }

  async function rebuildProfile() {
    const res = await fetch("/api/hostess7/znetwork/rebuild-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "rebuild-profile" }),
    });
    return res.ok ? res.json() : { ok: false };
  }

  async function refresh() {
    const [zn, stack, version, nexusC2, h7] = await Promise.all([
      fetchJson("/api/znetwork"),
      fetchJson("/api/field-stack-layer"),
      fetchJson("/data/ammoos-version.json"),
      fetchJson("/api/nexus-c2/snapshot"),
      fetchJson("/api/hostess7/znetwork"),
    ]);
    renderStack(stack, version);
    renderSiblings(version);
    renderStatus(zn || {}, stack, version, nexusC2);
    renderHostess7(h7 || {});
    return { zn, stack, version, nexusC2, h7 };
  }

  function init() {
    wireSettings();
    $("zn-refresh")?.addEventListener("click", refresh);
    $("zn-h7-send")?.addEventListener("click", sendHostessSpeak);
    $("zn-h7-rebuild")?.addEventListener("click", async () => {
      await rebuildProfile();
      refresh();
    });
    refresh();
    schedulePoll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  globalThis.ZNetworkHub = { refresh, prefs };
})();