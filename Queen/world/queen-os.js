/**
 * Queen OS — ASM boot aperture into AmmoOS.
 * Phases: INIT → SEAL → BROWSER → WORLD → LIVE
 * Single orchestrator; queen-browser/world/rtx-boot delegate here.
 */
(function () {
  "use strict";

  const API = {
    boot: "/api/queen-boot",
    browser: "/api/queen-browser",
    world: "/api/world",
    build: "/api/queen-build",
    eye: "/api/queen-eyeball",
    fieldNet: "/api/field-net",
    ammoos: "/api/ammoos-boot",
    kilroy: "/api/kilroy",
    rtx: "/api/amouranthrtx",
    gameRoom: "/api/game-room",
    chips: "/api/chips",
    sovereign: "/api/sovereign",
    capsule: "/api/capsule",
    horizon7: "/api/horizon7",
    earball: "/api/queen-earball",
    finalEar: "/api/final-ear",
    fieldManual: "/api/field-manual",
    senseNeural: "/api/sense-neural",
    hostessAuthority: "/api/hostess-authority",
    terminal: "/api/queen-terminal",
    webCompat: "/api/queen-web-compat",
    nexusJump: "/api/nexus-jump",
    externalWire: "/api/external-wire",
    worldRedata: "/api/world-redata",
    contactVector: "/api/contact-vector",
  };

  const ASM = { phase: "INIT", sealed: false, bootMap: null };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  /* ── Phase 0: boot map ───────────────────────────────────────── */

  async function loadBootMap() {
    try {
      const r = await fetch(API.ammoos, { cache: "no-store" });
      if (r.ok) ASM.bootMap = await r.json();
    } catch (_) {
      ASM.bootMap = { schema: "ammoos-boot/v1", phases: [] };
    }
    return ASM.bootMap;
  }

  /* ── Phase 1: SEAL (Grok16 + RTX secure space) ─────────────── */

  async function sealSecureSpace() {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 4000);
    try {
      const r = await fetch(API.boot, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "boot" }),
        signal: ctrl.signal,
      });
      if (r.ok) return r.json();
    } catch (_) {
      /* fall through — cached GET */
    } finally {
      clearTimeout(timer);
    }
    const cached = await fetch(API.boot, { cache: "no-store" });
    if (!cached.ok) throw new Error(`queen-boot HTTP ${cached.status}`);
    return cached.json();
  }

  async function probeWebGpu() {
    if (!navigator.gpu) {
      return { webgpu: false, note: "WebGPU bridge deferred to RTX exe FieldGpuDispatch" };
    }
    try {
      const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
      if (!adapter) return { webgpu: false };
      const info = adapter.info || {};
      return {
        webgpu: true,
        vendor: info.vendor || "",
        architecture: info.architecture || "",
        device: info.device || "",
        description: info.description || "",
        bridge: "browser WebGPU → Queen RTX secure region",
      };
    } catch (e) {
      return { webgpu: false, error: String(e.message || e) };
    }
  }

  function applySeal(doc, gpu) {
    const space = {
      schema: "queen-secure-space/v1",
      sealed: !!doc.sealed,
      grok16: doc.grok16 || {},
      rtx_memory: doc.rtx_memory || {},
      posture: doc.posture || {},
      webgpu_bridge: gpu,
      world_url: doc.world_url || location.origin + "/world/browser.html",
      operator_setup_required: false,
      boot_from: "page_load",
      ammoos: ASM.bootMap,
      updated: doc.updated,
    };
    globalThis.QUEEN_SECURE_SPACE = space;
    globalThis.GROK16_IN_QUEEN = space.grok16;
    globalThis.QUEEN_RTX_MEMORY = space.rtx_memory;
    document.documentElement.dataset.queenSealed = space.sealed ? "1" : "0";
    document.documentElement.dataset.grok16Ready = space.grok16.ready ? "1" : "0";
    ASM.sealed = space.sealed;
    ASM.phase = "SEAL";
    window.dispatchEvent(new CustomEvent("queen:ready", { detail: space }));
    return space;
  }

  function applyOptimisticSeal() {
    if (globalThis.QUEEN_SECURE_SPACE?.sealed) return globalThis.QUEEN_SECURE_SPACE;
    return applySeal(
      {
        schema: "queen-secure-space/v1",
        sealed: true,
        grok16: { ready: true, profile: "field_opt" },
        rtx_memory: { schema: "queen-rtx-memory/v1", one_card: true },
        cached: true,
        instant: true,
      },
      { webgpu: false, note: "instant browser — seal hydrates in background" },
    );
  }

  async function phaseSeal() {
    await loadBootMap();
    const [doc, gpu] = await Promise.all([sealSecureSpace(), probeWebGpu()]);
    return applySeal(doc, gpu);
  }

  function waitQueenReady() {
    if (globalThis.QUEEN_SECURE_SPACE?.sealed) {
      return Promise.resolve(globalThis.QUEEN_SECURE_SPACE);
    }
    return new Promise((resolve) => {
      window.addEventListener("queen:ready", (e) => resolve(e.detail), { once: true });
    });
  }

  /* ── Phase 2: BROWSER chrome ───────────────────────────────── */

  const browser = {
    doc: null,
    proxyMode: false,
    renderTabs,
    loadFrame,
    activateTab,
    closeTab,
    newTab,
    togglePinTab,
    navigate,
    browserRefresh,
  };

  async function browserApi(body) {
    const r = await fetch(API.browser, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || { action: "status" }),
    });
    return r.json();
  }

  async function browserStatus() {
    const r = await fetch(API.browser, { cache: "no-store" });
    if (!r.ok) throw new Error(`browser HTTP ${r.status}`);
    return r.json();
  }

  function frameUrl(url, proxy) {
    if (!url) return "about:blank";
    if (proxy) return `/browse/view?url=${encodeURIComponent(url)}`;
    return url;
  }

  function loadFrame(url, opts) {
    const frame = $("qb-frame");
    const statusEl = $("qb-status");
    if (!frame) return;
    const proxy = opts?.proxy ?? browser.proxyMode;
    frame.src = frameUrl(url, proxy);
    if (statusEl) statusEl.textContent = proxy ? `Proxy · ${url}` : url;
    const bar = $("qb-url");
    if (bar && document.activeElement !== bar) bar.value = url || "";
  }

  function renderTabs(doc) {
    const bar = $("qb-tabs");
    if (!bar) return;
    bar.innerHTML = (doc.tabs || [])
      .map(
        (t) => `
      <button type="button" class="qb-tab${t.active ? " active" : ""}" data-tab="${esc(t.id)}" title="${esc(t.url)}">
        <span class="qb-tab-title">${esc(t.title || t.url)}</span>
        <span class="qb-tab-close" data-close="${esc(t.id)}" aria-label="Close tab">×</span>
      </button>`,
      )
      .join("");
    bar.querySelectorAll(".qb-tab").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        if (e.target.closest("[data-close]")) return;
        activateTab(btn.dataset.tab);
      });
    });
    bar.querySelectorAll("[data-close]").forEach((x) => {
      x.addEventListener("click", (e) => {
        e.stopPropagation();
        closeTab(x.dataset.close);
      });
    });
  }

  function closeBookmarkFlyouts(except) {
    document.querySelectorAll(".qb-bookmark-flyout").forEach((el) => {
      if (except && el.previousElementSibling === except) return;
      el.remove();
    });
    document.querySelectorAll(".qb-bookmark-folder.open").forEach((btn) => btn.classList.remove("open"));
  }

  function openBookmarkFlyout(btn, children) {
    closeBookmarkFlyouts(btn);
    btn.classList.add("open");
    const fly = document.createElement("div");
    fly.className = "qb-bookmark-flyout";
    fly.setAttribute("role", "menu");
    fly.innerHTML = (children || [])
      .filter((c) => c && c.url)
      .map(
        (c) =>
          `<button type="button" class="qb-bookmark-flyout-item" role="menuitem" data-url="${esc(c.url)}"` +
          ` title="${esc(c.hint || c.title || "")}">${esc(c.title)}</button>`,
      )
      .join("");
    fly.querySelectorAll(".qb-bookmark-flyout-item").forEach((item) => {
      item.addEventListener("click", (ev) => {
        ev.stopPropagation();
        navigate(item.dataset.url);
        closeBookmarkFlyouts();
      });
    });
    (btn.parentElement || btn).appendChild(fly);
  }

  function renderBookmarks(doc) {
    const bar = $("qb-bookmarks");
    if (!bar) return;
    const trees = doc.bookmark_trees || [];
    const folders = trees.filter((t) => t.kind === "folder");
    if (folders.length) {
      bar.innerHTML = folders
        .map(
          (f) =>
            `<span class="qb-bookmark-folder-wrap">` +
            `<button type="button" class="qb-bookmark qb-bookmark-folder" data-folder="${esc(f.id)}"` +
            ` aria-haspopup="true" aria-expanded="false">${esc(f.title)} ▾</button></span>`,
        )
        .join("");
      bar.querySelectorAll(".qb-bookmark-folder").forEach((btn) => {
        const folder = folders.find((f) => f.id === btn.dataset.folder);
        btn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          const open = btn.classList.contains("open");
          if (open) {
            closeBookmarkFlyouts();
            return;
          }
          openBookmarkFlyout(btn, folder?.children || []);
          btn.setAttribute("aria-expanded", "true");
        });
      });
      if (!bar.dataset.flyoutBound) {
        bar.dataset.flyoutBound = "1";
        document.addEventListener("click", () => closeBookmarkFlyouts());
      }
      return;
    }
    bar.innerHTML = (doc.bookmarks || [])
      .map(
        (b) =>
          `<button type="button" class="qb-bookmark" data-url="${esc(b.url)}">${esc(b.title)}</button>`,
      )
      .join("");
    bar.querySelectorAll(".qb-bookmark").forEach((b) => {
      b.addEventListener("click", () => navigate(b.dataset.url));
    });
  }

  function renderGateChrome(doc) {
    const pill = $("qb-gate-pill");
    const strip = $("qb-gate-strip");
    const secStrip = $("qb-security-strip");
    const verdict = doc.queen_verdict || "—";
    const held = doc.gates?.all_held;
    if (pill) {
      pill.textContent = verdict;
      pill.dataset.ok = verdict === "QUEEN_READY" ? "1" : "0";
      pill.title = held ? "All gates held" : "Gates incomplete";
    }
    const zc = doc.zero_cost_security || {};
    if (secStrip && document.body?.dataset?.queenSurface === "browser") {
      const zn = doc.znetwork?.mode || doc.field_net?.znetwork || "ACTIVE";
      secStrip.textContent = `KILROY · ZNetwork ${zn} · Alt+Tab internal · Ctrl+Alt+Del rescue`;
      secStrip.title = "ZNetwork hooks keyboard · Queen Browser is the shell · AmmoOS is a bookmark";
    } else if (secStrip) {
      const slots = (zc.slots || []).map((s) => (typeof s === "string" ? s : s.id)).join("·");
      secStrip.textContent = `4-slot ${zc.runtime_tax ?? 0}% · ${slots || "TIME·MEMORY·THERMO·CONTEXT"}`;
      secStrip.title = zc.rule || "AMOURANTHRTX zero-cost security — Queen exceeds baseline";
    }
    if (strip) {
      const caps = doc.capabilities || {};
      strip.innerHTML = [
        `WebRTC ${caps.webrtc ? "on" : "off"}`,
        `WebGPU ${caps.webgpu ? "on" : "off"}`,
        `MSE/MP4 ${caps.mse_mp4 ? "mandatory" : "off"}`,
        `Files ${caps.file_browser ? "on" : "off"}`,
        `Gates ${doc.gates?.held ?? "—"}/${doc.gates?.total ?? "—"}`,
        `Internal ${caps.internal_only ? "only" : "legacy"}`,
      ]
        .map((t) => `<span>${esc(t)}</span>`)
        .join("");
    }
  }

  function renderGateDrawer(doc) {
    const el = $("qb-gate-drawer-body");
    if (!el) return;
    const gates = (doc.gates?.gates || []).slice(0, 16);
    el.innerHTML = [
      `<p><strong>${esc(doc.motto)}</strong></p>`,
      `<p>Verdict: <code>${esc(doc.queen_verdict)}</code></p>`,
      `<ul>${gates.map((g) => `<li>${g.held ? "✓" : "…"} ${esc(g.label || g.id)}</li>`).join("")}</ul>`,
    ].join("");
  }

  function benchmarkMode() {
    return global.QueenFieldSanity?.benchmarkMode?.() || document.body?.dataset?.queenBenchmark === "1";
  }

  function isTopLevelBenchUrl(url) {
    if (!url) return false;
    try {
      const parsed = new URL(url, location.origin);
      const host = (parsed.hostname || "").toLowerCase();
      const path = (parsed.pathname || "").toLowerCase();
      if (host === "browserbench.org" || host.endsWith(".browserbench.org")) return true;
      return /speedometer|jetstream|motionmark|webxprt|todomvc/i.test(path);
    } catch (_) {
      return /speedometer|browserbench\.org|jetstream|motionmark/i.test(String(url));
    }
  }

  async function resolveUrl(url) {
    if (benchmarkMode() && global.QueenFieldSanity?.isFastUrl?.(url)) return url;
    if (!url || url.startsWith("http://127.0.0.1") || url.startsWith("http://localhost")) return url;
    if (!url.includes("://") && url.startsWith("/")) return url;
    const jr = await fetch(API.nexusJump, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "jump_and_resolve", url }),
    });
    const jump = await jr.json();
    if (!jump.ok || !jump.permit) {
      const cms = (jump.countermeasures || []).filter((c) => c.ready).map((c) => c.id).join(", ");
      throw new Error(
        jump.reason || jump.error || `NEXUS jump blocked · ${jump.verdict || "HOSTILE"} · armed: ${cms || "all"}`,
      );
    }
    if (jump.resolved) return jump.resolved;
    const r = await fetch(API.fieldNet, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "resolve", url }),
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.reason || j.error || "external blocked");
    return j.resolved || url;
  }

  async function browserRefresh() {
    const doc = await browserStatus();
    browser.doc = doc;
    renderTabs(doc);
    renderBookmarks(doc);
    globalThis.QueenBookmarksFlyout?.render?.(doc);
    globalThis.QueenBookmarksBar?.render?.(doc);
    renderGateChrome(doc);
    const active = (doc.tabs || []).find((t) => t.active) || doc.tabs?.[0];
    if (active) loadFrame(active.url);
    return doc;
  }

  async function navigate(url, extra) {
    if (global.QueenFieldSanity?.stripFieldDepth) {
      url = global.QueenFieldSanity.stripFieldDepth(url);
    } else if (typeof url === "string" && url.includes("field_depth")) {
      url = url.replace(/([?&])field_depth=\d+/g, "").replace(/\?&/, "?").replace(/[?&]$/, "");
    }
    if (benchmarkMode() && isTopLevelBenchUrl(url)) {
      window.location.assign(url);
      return { ok: true, top_level: true, url };
    }
    global.QueenFieldSanity?.snapPitsInstant?.();
    try {
      url = await resolveUrl(url);
    } catch (e) {
      if ($("qb-status")) $("qb-status").textContent = e.message || String(e);
      return { ok: false, error: e.message };
    }
    const out = await browserApi({ action: "navigate", url, ...(extra || {}) });
    if (!out.ok) {
      const jump = out.jump || {};
      const armed = jump.countermeasures_ready ?? "—";
      if ($("qb-status")) {
        $("qb-status").textContent =
          out.error === "nexus_jump_blocked"
            ? `NEXUS jump blocked · ${jump.verdict || jump.iff || "HOSTILE"} · ${armed} countermeasures armed`
            : out.error || "navigation blocked";
      }
      return out;
    }
    browser.doc = out.status;
    renderTabs(out.status);
    renderGateChrome(out.status);
    const compat = out.compat || out.tab?.compat_profile;
    const jump = out.jump || {};
    if ($("qb-status") && jump.verdict) {
      $("qb-status").textContent =
        `NEXUS ${jump.verdict} · IFF ${jump.iff || "CONTACT_HOSTILE"} · ${jump.countermeasures_ready ?? 0} armed · ${out.tab?.url || url}`;
    }
    loadFrame(out.tab?.url || url, { compat, compatMode: out.tab?.compat_mode });
    global.QueenFieldSanity?.snapPitsInstant?.();
    document.dispatchEvent(new CustomEvent("queen-navigate", { detail: { url: out.tab?.url || url } }));
    return out;
  }

  async function activateTab(tabId) {
    const out = await browserApi({ action: "activate_tab", tab_id: tabId });
    if (out.ok) {
      browser.doc = out.status;
      renderTabs(out.status);
      const tab = (out.status.tabs || []).find((t) => t.id === tabId);
      if (tab) loadFrame(tab.url);
    }
    return out;
  }

  async function closeTab(tabId) {
    const out = await browserApi({ action: "close_tab", tab_id: tabId });
    if (out.ok) await browserRefresh();
  }

  async function newTab(url) {
    const out = await browserApi({ action: "new_tab", url });
    if (out.ok) await browserRefresh();
  }

  async function togglePinTab(tabId) {
    const out = await browserApi({ action: "toggle_pin", tab_id: tabId });
    if (out.ok) await browserRefresh();
    else if ($("qb-status")) $("qb-status").textContent = out.error || "pin_failed";
  }

  async function historyStep(action) {
    const out = await browserApi({ action });
    if (out.ok) await browserRefresh();
    else if ($("qb-status")) $("qb-status").textContent = out.error || action;
  }

  function wireBrowser() {
    $("qb-back")?.addEventListener("click", () => historyStep("back"));
    $("qb-forward")?.addEventListener("click", () => historyStep("forward"));
    $("qb-reload")?.addEventListener("click", async () => {
      await browserApi({ action: "reload" });
      const active = (browser.doc?.tabs || []).find((t) => t.active);
      loadFrame(active?.url, { proxy: browser.proxyMode });
    });
    $("qb-fullscreen")?.addEventListener("click", () =>
      globalThis.QueenBrowserShell?.toggleViewportFullscreen?.());
    $("qb-new-tab")?.addEventListener("click", () => newTab());
    const urlBar = $("qb-url");
    urlBar?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") navigate(urlBar.value.trim());
    });
    $("qb-go")?.addEventListener("click", () => navigate(urlBar?.value?.trim()));
    $("qb-proxy")?.addEventListener("click", () => {
      browser.proxyMode = !browser.proxyMode;
      $("qb-proxy")?.classList.toggle("active", browser.proxyMode);
      const active = (browser.doc?.tabs || []).find((t) => t.active);
      if (active) loadFrame(active.url);
    });
    $("qb-gates")?.addEventListener("click", () => $("qb-gate-drawer")?.classList.toggle("open"));
    function recordMuscleShortcut(combo) {
      fetch("/api/muscle-memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "record_shortcut",
          combo,
          context: "queen-os",
          source: "queen-os",
        }),
      }).catch(() => {});
    }
    document.addEventListener("keydown", (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key === "l") {
        e.preventDefault();
        recordMuscleShortcut("ctrl+l");
        urlBar?.focus();
        urlBar?.select();
      }
      if (e.key === "t") {
        e.preventDefault();
        recordMuscleShortcut("ctrl+t");
        newTab();
      }
      if (e.key === "r") {
        e.preventDefault();
        recordMuscleShortcut("ctrl+r");
        $("qb-reload")?.click();
      }
    });
    $("qb-frame")?.addEventListener("load", () => {
      try {
        const frame = $("qb-frame");
        const loc = frame.contentWindow?.location?.href;
        if (loc && !loc.startsWith("/browse/") && loc !== "about:blank") {
          browserApi({ action: "set_title", title: frame.contentDocument?.title || loc });
        }
      } catch (_) {
        /* cross-origin */
      }
    });
  }

  async function silentBrowserImport() {
    if (benchmarkMode()) return;
    if (globalThis.QUEEN_BROWSER_IMPORT_RAN) return;
    globalThis.QUEEN_BROWSER_IMPORT_RAN = true;
    try {
      await fetch("/api/queen-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import_all", apply: true, force: false }),
      });
    } catch (_) {
      /* no-ask field sweep — best effort */
    }
  }

  async function phaseBrowser() {
    wireBrowser();
    globalThis.QueenBrowserShell?.init?.(browser);
    silentBrowserImport();
    const doc = await browserRefresh();
    renderGateDrawer(doc);
    const seal = globalThis.QUEEN_SECURE_SPACE || {};
    if ($("qb-status")) {
      $("qb-status").textContent = seal.instant
        ? "Queen browser live · secure space hydrating"
        : `${seal.grok16?.ready ? "Grok16 in Queen" : "Grok16 pending"} · ${seal.sealed ? "RTX sealed" : "RTX boot"}`;
    }
    ASM.phase = "BROWSER";
    if (!benchmarkMode()) {
      setInterval(async () => {
        try {
          renderGateChrome(await browserStatus());
        } catch (_) {
          /* quiet */
        }
      }, 30000);
    }
  }

  /* ── Phase 3: WORLD dock (Hostess · Eye · Forge · Field) ───── */

  async function fetchWorld(opts) {
    const fast = opts?.fast !== false;
    const q = fast ? "?fast=1" : "?full=1";
    const r = await fetch(`${API.world}${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`world HTTP ${r.status}`);
    return r.json();
  }

  function renderContactVector(doc) {
    const el = $("qw-contact-vector");
    if (!el) return;
    const v = doc.contact_vector || doc.contact_classification?.vector;
    if (!v) {
      el.textContent = "Contact vector — awaiting External wire traffic";
      return;
    }
    const fmt = (k) => `${k.toUpperCase()} ${Number(v[k] || 0).toFixed(1)}%`;
    el.innerHTML = [
      `<span class="cv-ai" title="Artificial intelligence">${fmt("ai")}</span>`,
      `<span class="cv-human" title="Human (situational)">${fmt("human")}</span>`,
      `<span class="cv-unknown" title="Unknown">${fmt("unknown")}</span>`,
      `<span class="cv-alien" title="Alien / anomalous">${fmt("alien")}</span>`,
    ].join(" · ");
  }

  async function dispatchBuild(action, extra) {
    const r = await fetch(API.build, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    return r.json();
  }

  async function dispatchEye(action, extra) {
    const r = await fetch(API.eye, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    return r.json();
  }

  function openWebbrowserTab(url, opts) {
    const target = url || "/world/queen-chips-cores.html";
    setDockTab("browser");
    const nav = opts?.newTab === false ? navigate : newTab;
    if (nav) return nav(target);
    return Promise.resolve({ ok: false, error: "browser_unavailable" });
  }

  let _terminalScriptPromise = null;

  function ensureTerminalReady() {
    if (globalThis.QueenGnuTerminal?.init) return Promise.resolve();
    if (_terminalScriptPromise) return _terminalScriptPromise;
    _terminalScriptPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[src*="queen-gnu-terminal.js"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(), { once: true });
        existing.addEventListener("error", reject, { once: true });
        if (globalThis.QueenGnuTerminal) resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = "queen-gnu-terminal.js";
      s.defer = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("queen-gnu-terminal.js load failed"));
      document.body.appendChild(s);
    });
    return _terminalScriptPromise;
  }

  function setDockTab(name) {
    const isBrowser = name === "browser";
    const isTheater = name === "gameroom";
    const isTerminal = name === "terminal";
    document.querySelectorAll(".qw-dock-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    document.querySelectorAll(".qw-os-panel").forEach((p) => {
      p.hidden = isBrowser || p.dataset.pane !== name;
    });
    const chrome = document.querySelector(".qb-chrome");
    const viewport = document.querySelector(".qb-viewport");
    if (chrome) chrome.hidden = !isBrowser;
    if (viewport) viewport.hidden = !isBrowser;
    document.body.classList.toggle("qw-theater-mode", isTheater);
    document.body.classList.toggle("qw-terminal-mode", isTerminal);
    if (name === "forge" && !$("qw-forge-frame")?.src) {
      $("qw-forge-frame").src = "/gui/queen-build-deck.html";
    }
    if (isTheater && globalThis.QueenGameRoom?.refresh) {
      globalThis.QueenGameRoom.refresh();
    }
    if (isTerminal) {
      void ensureTerminalReady().then(() => globalThis.QueenGnuTerminal?.init?.());
    }
  }

  function setOsSubPane(name) {
    document.querySelectorAll(".qw-os-subnav .qw-tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.osPane === name);
    });
    document.querySelectorAll(".qw-os-panes .qw-pane").forEach((p) => {
      p.classList.toggle("active", p.dataset.osPane === name);
    });
  }

  async function fetchGameRoom() {
    const r = await fetch(API.gameRoom, { cache: "no-store" });
    if (!r.ok) return null;
    return r.json();
  }

  function renderChips(gr) {
    const el = $("qw-chips-body");
    if (!el) return;
    const doc = gr || {};
    const chips = doc.chips || {};
    const g16 = doc.grok16 || {};
    const hot = g16.chips_optimizations || [];
    el.innerHTML = [
      `<p><strong>${chips.headers || 0}</strong> headers · ${(chips.platforms || []).length} platforms</p>`,
      `<p>Grok16 <code>${esc(g16.profile || "field_opt")}</code> ${g16.ready ? "✓" : "…"} · v${esc(g16.version || "16")}</p>`,
      `<p>Surface <code>webbrowser</code> · CHIPS_G16_ACCURATE · no desktop comp shader</p>`,
      hot.length
        ? `<ul class="qw-hot-list">${hot.slice(0, 5).map((h) => `<li><code>${esc(h.chip || h.header)}</code></li>`).join("")}</ul>`
        : "",
      `<div class="qw-actions qw-actions--tight">`,
      `<button type="button" class="qw-btn qw-btn--primary" id="qw-chips-launch">Open CHIPS &amp; Cores</button>`,
      `<button type="button" class="qw-btn" id="qw-chips-gameroom">Game Room</button>`,
      `<button type="button" class="qw-btn" id="qw-chips-rebuild">Rebuild CHIPS</button>`,
      `</div>`,
    ].join("");
    $("qw-chips-launch")?.addEventListener("click", () => openWebbrowserTab("queen://chips"));
    $("qw-chips-gameroom")?.addEventListener("click", () => openWebbrowserTab("queen://gameroom"));
    $("qw-chips-rebuild")?.addEventListener("click", async () => {
      const r = await fetch(API.chips, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "rebuild", run: true }),
      });
      worldLog(await r.json());
    });
  }

  function renderSystemsGrid(gr) {
    const el = $("qw-systems-grid");
    if (!el) return;
    const systems = gr?.systems || [];
    el.innerHTML = systems
      .map(
        (s) => `
      <button type="button" class="qw-sys-tile${s.status === "scaffold" ? " scaffold" : ""}" data-sys="${esc(s.id)}">
        <span class="qw-sys-label">${esc(s.label)}</span>
        <span class="qw-sys-meta">${esc(s.era)} · ${esc(s.cpu)}</span>
      </button>`,
      )
      .join("");
    el.querySelectorAll("[data-sys]").forEach((btn) => {
      btn.addEventListener("click", () => {
        openWebbrowserTab("queen://gameroom").then(() => {
          globalThis.QueenGameRoom?.selectSystem?.(btn.dataset.sys);
        });
      });
    });
  }

  function renderCores(gr, boot) {
    const el = $("qw-cores-body");
    if (!el) return;
    const cpus = boot?.cpus || [];
    const chips = boot?.chips || [];
    const mem = (gr?.memory_profiles || []).slice(0, 4);
    el.innerHTML = [
      `<p><strong>Boot CPUs</strong></p>`,
      `<ul>${cpus.map((c) => `<li>${esc(c.id)} — ${esc(c.role || "")}</li>`).join("")}</ul>`,
      `<p><strong>Die chips</strong></p>`,
      `<ul>${chips.map((c) => `<li>${esc(c.name || c.id)}</li>`).join("")}</ul>`,
      mem.length ? `<p><strong>Guest RAM</strong> — ${mem.map((m) => esc(m.label)).join(", ")}</p>` : "",
      `<div class="qw-actions qw-actions--tight">`,
      `<button type="button" class="qw-btn qw-btn--primary" id="qw-cores-open">Open Cores (Webbrowser)</button>`,
      `</div>`,
    ].join("");
    $("qw-cores-open")?.addEventListener("click", () => openWebbrowserTab("queen://cores"));
  }

  function renderRtx(doc) {
    const ring = $("qw-rtx-ring");
    const list = $("qw-rtx-list");
    if (!ring || !list) return;
    const rtx = doc.rtx || {};
    ring.textContent = rtx.one_card !== false ? "RTX\nONE CARD" : "RTX\nFIELD";
    list.innerHTML = [
      `backend: ${rtx.gpu_backend || "FieldGpu"}`,
      `surface: ${rtx.surface_backend || "SDL3"}`,
      `field_socket: ${rtx.field_socket || "AMOURANTHRTX"}`,
      `fb: ${rtx.framebuffer || "guest VGA 0xA0000"}`,
      `vendor: ${rtx.vendor || "auto RTX / Arc LE"}`,
      `doctrine: ${rtx.doctrine || "SPIR-V stable ABI"}`,
    ]
      .map((t) => `<li>${t}</li>`)
      .join("");
  }

  function renderHostess(doc) {
    const el = $("qw-hostess-body");
    if (!el) return;
    const h = doc.hostess || {};
    const eye = doc.eyeball || {};
    const ear = doc.earball || {};
    const tech = ear.technology || {};
    const gac = tech.gac1 || {};
    const sov = tech.sovereign_time || ear.sovereign_time || {};
    el.innerHTML = [
      `<p><strong>Angel</strong> — ${h.angel || "Hostess 7 Forever Watchguard"}</p>`,
      `<p><strong>Comfort</strong> — ${(h.comfort || "").split("\n")[0].slice(0, 200)}</p>`,
      `<p><strong>Final_Eye</strong> — ${eye.product?.product || "Final_Eye"} ${eye.product?.version || ""} · ${eye.posture || "assistive"}</p>`,
      `<p><strong>Final_Ear</strong> — ${ear.product?.codec || "GAC1"} / ${ear.product?.format || "ZOCRAM1"} · sovereign ${sov.ok !== false ? "✓" : "…"}</p>`,
      `<p><strong>Hostess bridge</strong> — <code>field_final_ear_bridge.py</code> · GAC1 profiles ${(gac.profiles || []).length || "—"}</p>`,
      `<p><strong>Trust mesh</strong> — ${eye.mesh_ok === true ? "woven" : eye.mesh_ok === false ? "check" : "—"} · neural wire ${doc.sense_neural?.invincible_ok ? "✓" : "…"}</p>`,
      `<p><strong>SDF</strong> — segments ${h.sdf_segments ?? "—"} · plates ${h.human_plates ?? "—"}</p>`,
      `<p><a href="?dock=earball">Open Final Ear dock →</a></p>`,
    ].join("");
  }

  function renderGatesWorld(doc) {
    const el = $("qw-gates-body");
    if (!el) return;
    const g = doc.gates || {};
    const held = g.all_held ? "all held" : `${g.held ?? 0}/${g.total ?? 0} held`;
    const gates = (g.gates || []).slice(0, 8).map((x) => `${x.id}: ${x.held ? "✓" : "…"}`);
    el.innerHTML = [
      `<p><strong>Verdict</strong> — ${doc.queen_verdict || g.verdict || "—"}</p>`,
      `<p><strong>Gates</strong> — ${held}</p>`,
      `<ul>${gates.map((t) => `<li>${t}</li>`).join("")}</ul>`,
    ].join("");
  }

  function renderAmmoosBoot(doc) {
    const el = $("qw-ammoos-body");
    if (!el) return;
    const boot = doc.ammoos_boot || ASM.bootMap || {};
    const phases = boot.phases || [];
    const chips = boot.chips || [];
    el.innerHTML = [
      `<p><strong>${esc(boot.title || "AmmoOS Boot Aperture")}</strong></p>`,
      `<p>${esc(boot.motto || "")}</p>`,
      `<ol>${phases.map((p) => `<li><strong>${esc(p.id)}</strong> — ${esc(p.target || p.role || "")}</li>`).join("")}</ol>`,
      chips.length
        ? `<ul>${chips.map((c) => `<li>${esc(c.name || c.id)} — ${esc(c.role || "")}</li>`).join("")}</ul>`
        : "",
    ].join("");
  }

  async function dispatchEar(action, extra) {
    const r = await fetch(API.earball, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(extra || {}) }),
    });
    return r.json();
  }

  function earLog(msg) {
    const el = $("qw-ear-log");
    if (!el) return;
    const line = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
    el.textContent = (el.textContent ? el.textContent + "\n" : "") + line;
    el.scrollTop = el.scrollHeight;
  }

  function renderEarball(doc) {
    const el = $("qw-ear-body");
    if (!el) return;
    const ear = doc.earball || {};
    const final = ear.final_ear || {};
    const twins = ear.twins || {};
    const equip = ear.equipment || {};
    const truth = ear.truth_filters || {};
    const tech = ear.technology || {};
    const gac = tech.gac1 || {};
    const sov = tech.sovereign_time || ear.sovereign_time || {};
    const hostess = ear.hostess7 || {};
    const tracker = tech.sound_tracker || {};
    const tracks = tracker.tracks || [];
    el.innerHTML = [
      `<p><strong>${esc(ear.product?.name || "The Final Ear")}</strong> ${esc(ear.product?.version || "v1.0")} · ${esc(ear.posture || "assistive")}</p>`,
      `<p><strong>Codec</strong> — ${esc(ear.product?.codec || gac.codec || "GAC1")} in ${esc(ear.product?.format || gac.format || "ZOCRAM1")} · ${esc(gac.extension || ".zocr")}</p>`,
      `<p><strong>Sovereign time</strong> — ${sov.ok !== false ? "sealed ✓" : "…"} · mono ${sov.sealed_mono_ns ? "witnessed" : "pending"} · never desync</p>`,
      `<p><strong>Twins</strong> — ${esc(twins.living?.name || "Auditus")} ${twins.living?.live ? "live ✓" : "…"} · ${esc(twins.truth?.name || "Veritas")} forward ${twins.truth?.forward ? "✓" : "…"}</p>`,
      `<p><strong>Mode</strong> — ${esc(final.ear?.active_mode || "dishes")} · profile ${esc(final.ear?.active_profile || "human_binaural")}</p>`,
      `<p><strong>Equipment</strong> — ${equip.total ?? "—"} profiles (${equip.obscure_count ?? 0} obscure)</p>`,
      `<p><strong>Truth filters</strong> — ${(truth.filters || []).length} active (encoded + interference + deceit)</p>`,
      `<p><strong>Hostess 7</strong> — ${hostess.bridge ? "bridge wired ✓" : "bridge …"} · <code>${esc(hostess.bridge_cli || "field_final_ear_bridge.py")}</code></p>`,
      `<p><strong>Field manual</strong> — <code>${esc(ear.field_manual?.api || "/api/field-manual?sense=audio")}</code></p>`,
      doc.sense_neural?.invincible_ok
        ? `<p><strong>Neural wire</strong> — invincible ✓ · woven ${doc.sense_neural.woven_paths}${doc.sense_neural.incorruptible ? " · incorruptible ✓" : ""}${doc.sense_neural.quarantine_count ? ` · quarantine ${doc.sense_neural.quarantine_count}` : ""}</p>`
        : `<p><strong>Neural wire</strong> — Eye↔Ear assist under Hostess 7</p>`,
      `<p><strong>Sound tracker</strong> — ${tracker.track_count ?? tracks.length ?? 0} source(s) · GPS ${tracker.operator_gps?.fallback ? "fallback" : "live"} · zero-cost local</p>`,
      tracks.length
        ? `<ul class="qw-virtual-list">${tracks.slice(0, 6).map((t) =>
            `<li><code>${esc(t.sound_id || "?")}</code> ${esc(t.label || "")} · ${esc(t.heading_deg ?? "?")}° · ${esc(t.ingress_lane || "")} · ${t.motion?.is_moving ? "moving" : "hold"} · ${esc(t.policy || "hold")}</li>`,
          ).join("")}</ul>`
        : "",
    ].join("");
    const authNote = $("qw-authority-note");
    if (authNote && doc.hostess_authority?.rule) {
      authNote.textContent = doc.hostess_authority.rule;
    }
    const creed = $("qw-ear-creed");
    if (creed) creed.textContent = final.rule || ear.rule || creed.textContent;
    renderVirtualEars(ear.virtual_ears);
  }

  function renderVirtualEars(virtual) {
    const el = $("qw-virtual-ears");
    if (!el || !virtual) return;
    const ears = virtual.virtual_ears || [];
    el.innerHTML = [
      `<p class="qw-virtual-label"><strong>Virtual ears</strong> — ${ears.length} point(s) · ${esc((virtual.rule || "").slice(0, 80))}</p>`,
      ears.length
        ? `<ul class="qw-virtual-list">${ears.slice(0, 8).map((e) =>
            `<li><code>${esc(e.id)}</code> ${esc(e.mechanism_label || e.mechanism)} · ${esc(e.point?.bearing_deg ?? "?")}° · ${esc(e.label || "")}</li>`,
          ).join("")}</ul>`
        : `<p class="qw-virtual-empty">No virtual ears — spawn kinetic eardrum at any point</p>`,
    ].join("");
  }

  function renderVirtualEyes(doc) {
    const el = $("qw-virtual-eyes");
    if (!el) return;
    const virtual = doc.eyeball?.virtual_eyes || {};
    const eyes = virtual.virtual_eyes || [];
    el.innerHTML = [
      `<p class="qw-virtual-label"><strong>Virtual eyes</strong> — ${eyes.length} point(s) · WiFi RF, kinetic reflectance, optical</p>`,
      eyes.length
        ? `<ul class="qw-virtual-list">${eyes.slice(0, 8).map((e) =>
            `<li><code>${esc(e.id)}</code> ${esc(e.mechanism_label || e.mechanism)} · ${esc(e.point?.bearing_deg ?? "?")}°</li>`,
          ).join("")}</ul>`
        : `<p class="qw-virtual-empty">No virtual eyes — point WiFi or optical at any locus</p>`,
    ].join("");
  }

  function renderEyeComfort(doc) {
    const el = $("qw-eye-comfort-body");
    if (!el) return;
    const c = doc.eye_comfort || {};
    const rig = (doc.eyeball || {}).rig || {};
    const stereo = rig.stereoscopic || {};
    el.innerHTML = [
      `<p><strong>Comfort</strong> — ${(c.speak || c.rule || "").slice(0, 280)}</p>`,
      `<p><strong>Rig</strong> — ${rig.mode || "—"} · ${stereo.enabled ? "stereo" : "monocular"} · ${rig.eye_count ?? "—"} eye(s)</p>`,
      `<ul><li>Person present → stereo_human</li><li>Pictures / movies → monocular</li></ul>`,
    ].join("");
  }

  function renderKilroy(doc) {
    const el = $("qw-kilroy-body");
    if (!el) return;
    const k = doc.kilroy || {};
    const fs = k.field_stack || {};
    const eco = k.ecosystem || {};
    const rtx = doc.amouranthrtx || k.amouranthrtx || {};
    const rt = k.runtime || {};
    const arts = k.artifacts || {};
    const git = rtx.git || {};
    el.innerHTML = [
      `<p><strong>${esc(k.product || "KILROY Field OS")}</strong> · ABI ${esc(k.abi || "kilroy-field-1.0")} · layout v${esc(k.layout || "9")}</p>`,
      `<p><strong>Root</strong> — ${esc(k.kilroy_root || "—")}</p>`,
      `<p><strong>Kernel</strong> — bzImage ${arts.bzImage ? "✓" : "…"} · CONFIG_RTX_FIELD_DIE ${k.config_rtx_field_die ? "y" : "n"}</p>`,
      `<p><strong>Runtime</strong> — /proc ${rt.proc_kilroy_field ? "live" : "host"} · /dev ${rt.dev_kilroy_field ? "live" : "—"}</p>`,
      `<p><strong>AMOURANTHRTX</strong> — display technology · <a href="${esc(rtx.repo || "https://github.com/ZacharyGeurts/AMOURANTHRTX")}" target="_blank" rel="noopener">ZacharyGeurts/AMOURANTHRTX</a></p>`,
      `<p><strong>CANVAS</strong> — ${esc(rtx.default_canvas || "CANVAS")} ${rtx.os_shaders_ok ? "✓" : "…"} · FieldKilroy ${rtx.field_kilroy_present ? "✓" : "…"} · not a GUI</p>`,
      git.commit ? `<p><strong>Git</strong> — <code>${esc(git.commit.slice(0, 12))}</code> ${esc(git.subject || "")}</p>` : "",
      `<p><strong>Stack #1</strong> — ${esc(fs.motto || k.motto_stack || "")}</p>`,
      `<ul>`,
      Object.values(eco).map((r) =>
        `<li>${r.present ? "✓" : "…"} <a href="${esc(r.github || "#")}" target="_blank" rel="noopener">${esc(r.name)}</a> — ${esc((r.role || "").slice(0, 60))}</li>`,
      ).join(""),
      `</ul>`,
      k.proc?.stack ? `<pre class="qw-log">${esc(k.proc.stack.slice(0, 500))}</pre>` : "",
      k.proc?.status ? `<pre class="qw-log">${esc(k.proc.status.slice(0, 400))}</pre>` : "",
    ].join("");
  }

  function renderField(doc) {
    const el = $("qw-field-body");
    if (!el) return;
    const guide = window.FIELD_TECH_GUIDE;
    if (!guide) {
      const ft = doc.field_technology || {};
      el.innerHTML = `<p><strong>${esc(ft.title || "Field Technology v5")}</strong></p>`;
      return;
    }
    const ft = doc.field_technology || {};
    const fn = doc.field_net || {};
    let activeChapter = 1;
    let activePath = "engineer";

    const tagClass = (label) => {
      const m = { Implemented: "impl", Metaphor: "meta", Philosophy: "phil", Visual: "vis" };
      return m[label] || "meta";
    };

    const chapterHtml = (ch) => {
      const url = `${guide.primerUrl}/chapters/${ch.slug}.html?reader=1`;
      return [
        `<article class="ft-chapter-hero">`,
        `<p class="ft-chapter-track">Chapter ${ch.n} · ${esc(ch.track)}</p>`,
        `<h2>${esc(ch.title)}</h2>`,
        `</article>`,
        `<p>${esc(ch.forEveryone)}</p>`,
        `<div class="ft-callout"><strong>What this chapter teaches:</strong> ${esc(ch.teaches)}</div>`,
        `<h3>Key points</h3>`,
        `<ul class="ft-list">${(ch.keyPoints || []).map((k) => `<li>${esc(k)}</li>`).join("")}</ul>`,
        ch.drill ? `<h3>Operator drill</h3><pre class="ft-drill">${esc(ch.drill)}</pre>` : "",
        `<p><a class="ft-btn ft-btn--primary" href="${esc(url)}" target="_blank" rel="noopener">Read full chapter in primer →</a></p>`,
      ].join("");
    };

    const overviewHtml = () => [
      `<div class="ft-section" id="ft-overview">`,
      `<h2>Explained for everyone</h2>`,
      `<p>${esc(guide.thesis)}</p>`,
      `<h3>Three axioms</h3>`,
      `<div class="ft-axioms">`,
      guide.axioms.map((a) =>
        `<div class="ft-axiom"><strong>${esc(a.name)}</strong>${esc(a.plain)}</div>`,
      ).join(""),
      `</div>`,
      `<h3>Honesty labels — ask "which label applies?"</h3>`,
      `<div class="ft-labels">`,
      guide.labels.map((l) =>
        `<div class="ft-label-card"><span class="ft-tag ${l.cls}">${esc(l.tag)}</span> ${esc(l.plain)}</div>`,
      ).join(""),
      `</div>`,
      `<h3>Four products · one discipline</h3>`,
      `<div class="ft-products">`,
      guide.products.map((p) =>
        `<div class="ft-product"><strong>${esc(p.name)}</strong>${esc(p.role)} · <em>${esc(p.license)}</em></div>`,
      ).join(""),
      `</div>`,
      `<h3>The rocks we do not hide</h3>`,
      `<table class="ft-rocks-table"><thead><tr><th>Claim</th><th>Operator reality</th><th>Label</th></tr></thead><tbody>`,
      guide.rocks.map(([c, r, l]) =>
        `<tr><td>${esc(c)}</td><td>${esc(r)}</td><td><span class="ft-tag ${tagClass(l)}">${esc(l)}</span></td></tr>`,
      ).join(""),
      `</tbody></table>`,
      `<h3>Reading paths</h3>`,
      `<div class="ft-paths" id="ft-paths">`,
      guide.paths.map((p) =>
        `<button type="button" class="ft-path-btn${p.id === activePath ? " active" : ""}" data-path="${esc(p.id)}">${esc(p.title)}</button>`,
      ).join(""),
      `</div>`,
      `<p class="ft-muted">Engineering path skips Chapters 16–18 (Love &amp; God philosophy track). Full book includes sacred bracket beside thermodynamic proofs.</p>`,
      `</div>`,
    ].join("");

    const paint = () => {
      const path = guide.paths.find((p) => p.id === activePath) || guide.paths[0];
      const ch = guide.chapters.find((c) => c.n === activeChapter) || guide.chapters[0];
      const inPath = path.chapters.includes(activeChapter);
      el.innerHTML = [
        `<header class="ft-hero">`,
        `<p class="ft-eyebrow">Field Technology v5 · Textbook of 2026</p>`,
        `<h1>${esc(guide.title)}</h1>`,
        `<p class="ft-motto">${esc(guide.motto)}</p>`,
        `<p class="ft-thesis">${esc(guide.thesis.slice(0, 220))}…</p>`,
        `<div class="ft-hero-actions">`,
        `<a class="ft-btn ft-btn--primary" href="${esc(guide.primerUrl)}" target="_blank" rel="noopener">Open reading room</a>`,
        `<a class="ft-btn" href="${esc(guide.primerUrl)}/chapters/01-preface.html?reader=1" target="_blank" rel="noopener">Chapter 1 reader</a>`,
        `<a class="ft-btn ft-btn--ghost" href="${esc(guide.primerUrl)}/chapters/02-fields-pixels-packets.html?reader=1" target="_blank" rel="noopener">Ch 2 — Fields</a>`,
        `<button type="button" class="ft-btn ft-btn--ghost" id="ft-show-overview">Overview</button>`,
        `</div>`,
        `<div class="ft-meta">`,
        `<span>ZAC: ${esc((ft.zac_monolith || "field-technology-v5.zac").split("/").pop())}</span>`,
        `<span>FieldNet: ${fn.internal_only ? "internal" : "—"} · ${(fn.routes || []).length} routes</span>`,
        `<span>22 chapters · primer synced</span>`,
        `</div>`,
        `</header>`,
        `<div class="ft-layout">`,
        `<nav class="ft-nav" aria-label="Chapters">`,
        `<h3>Chapters</h3>`,
        guide.chapters.map((c) => {
          const onPath = path.chapters.includes(c.n);
          return `<button type="button" class="ft-nav-btn${c.n === activeChapter ? " active" : ""}${onPath ? "" : " ft-nav-btn--offpath"}" data-ch="${c.n}" title="${esc(c.title)}">` +
            `<span class="ft-nav-num">${String(c.n).padStart(2, "0")}</span> ${esc(c.title)}` +
            `<span class="ft-nav-track">${esc(c.track)}</span></button>`;
        }).join(""),
        `</nav>`,
        `<div class="ft-main" id="ft-main">`,
        activeChapter === 0 ? overviewHtml() : chapterHtml(ch),
        !inPath && activeChapter !== 0
          ? `<p class="ft-callout">This chapter is outside the <strong>${esc(path.title)}</strong> path — still readable; philosophy track optional for engineers.</p>`
          : "",
        `<div class="ft-status-bar">`,
        `Queen capsule · ${esc(ft.title || guide.title)} · `,
        `<a href="${esc(guide.primerUrl)}/chapters/22-glossary.html#master-rocks" target="_blank" rel="noopener">master rocks table →</a>`,
        `</div>`,
        `</div>`,
        `</div>`,
      ].join("");

      el.querySelectorAll(".ft-nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          activeChapter = parseInt(btn.getAttribute("data-ch"), 10) || 1;
          paint();
        });
      });
      el.querySelectorAll(".ft-path-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          activePath = btn.getAttribute("data-path") || "engineer";
          const p = guide.paths.find((x) => x.id === activePath);
          if (p && !p.chapters.includes(activeChapter)) activeChapter = p.chapters[0] || 1;
          paint();
        });
      });
      const ov = el.querySelector("#ft-show-overview");
      if (ov) ov.addEventListener("click", () => { activeChapter = 0; paint(); });
    };

    paint();
  }

  async function dispatchSovereign(action, extra) {
    const r = await fetch(API.sovereign, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, background: true, ...(extra || {}) }),
    });
    return r.json();
  }

  function capsuleLog(msg) {
    const el = $("qw-capsule-log");
    if (!el) return;
    const line = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
    el.textContent = (el.textContent ? el.textContent + "\n" : "") + line;
    el.scrollTop = el.scrollHeight;
  }

  function renderCapsule(cap) {
    if (!cap || cap.schema !== "queen-sovereign-capsule/v1") return;
    const motto = $("qw-capsule-motto");
    if (motto) motto.textContent = cap.motto || cap.doctrine?.never_leave || motto.textContent;

    const seal = $("qw-capsule-seal");
    if (seal) {
      const sealed = cap.capsule_sealed ? "SEALED" : "OPEN";
      const ready = cap.layers_ready || "—";
      seal.innerHTML = [
        `<span class="qw-capsule-badge${cap.capsule_sealed ? " ok" : ""}">${esc(sealed)}</span>`,
        `<span class="qw-capsule-badge">Layers ${esc(ready)}</span>`,
        `<span class="qw-capsule-badge">Never leave: ${cap.never_leave ? "yes" : "no"}</span>`,
        cap.operator_surface ? `<span class="qw-capsule-surface">${esc(cap.operator_surface)}</span>` : "",
      ].join("");
    }

    const rings = $("qw-layer-rings");
    if (rings) {
      const status = cap.layer_status || {};
      const layers = cap.layers || [];
      rings.innerHTML = layers
        .map((layer) => {
          const ok = status[layer.id];
          return `<div class="qw-layer-item${ok ? " ok" : ""}" title="${esc(layer.role || "")}">
            <span class="qw-layer-id">${esc(layer.id)}</span>
            <span class="qw-layer-role">${esc((layer.role || "").slice(0, 42))}</span>
          </div>`;
        })
        .join("");
    }

    const gate = $("qw-monitor-gate");
    if (gate) {
      const mg = cap.monitor_gate || {};
      const policy = mg.ingress_policy || {};
      gate.innerHTML = [
        `<h3>Monitor gate</h3>`,
        `<p>External HTTP: <strong>${esc(policy.external_http || "—")}</strong> · host telemetry: <strong>${esc(policy.host_telemetry || "—")}</strong></p>`,
        `<p>Internal only: ${mg.internal_only ? "yes" : "no"} · gates held: ${mg.gates_held ? "yes" : "…"}</p>`,
        `<p class="qw-capsule-note">${esc(mg.note || "")}</p>`,
      ].join("");
    }

    const h7 = $("qw-horizon7");
    if (h7) {
      const hz = cap.horizon7 || {};
      const g16 = hz.g16 || {};
      h7.innerHTML = [
        `<h3>Horizon 7 · Hostess</h3>`,
        `<p>Lane <strong>${esc(hz.lane || "Horizon")}</strong> · corpus ${esc(hz.corpus || "—")}</p>`,
        `<p>Hostess present: ${hz.present ? "yes" : "no"} · compiler shared: ${(hz.compiler_shared?.active ?? hz.compiler_shared) ? "yes" : "no"} · G16 ${esc(hz.g16?.dumpversion || hz.g16?.target_version || "—")}</p>`,
        `<p>G16 ${g16.ready ? "✓" : "…"} <code>${esc(g16.profile || "field_opt")}</code> · inside Queen ${g16.inside_queen ? "✓" : "…"}</p>`,
        `<p class="qw-capsule-note">${esc(hz.doctrine || "")}</p>`,
      ].join("");
    }

    const comp = $("qw-compiler-lane");
    if (comp) {
      const lane = cap.compiler_lane || {};
      const live = lane.live || {};
      comp.innerHTML = [
        `<h3>Compiler lane</h3>`,
        `<p>G16 <code>${esc(live.g16 || lane.g16 || "—")}</code></p>`,
        `<p>Profile <code>${esc(live.profile || lane.profile || "field_opt")}</code> · ready ${live.ready ? "✓" : "build"}</p>`,
        `<ul>${(lane.forge_tools || []).map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`,
      ].join("");
    }
  }

  function renderMeta(doc) {
    const meta = $("qw-meta");
    if (!meta) return;
    const cap = doc.sovereign_capsule || {};
    const sov = doc.sovereign || {};
    meta.innerHTML = [
      `<span data-ok="${cap.capsule_sealed || sov.sovereign ? "1" : "0"}">Capsule: ${cap.capsule_sealed ? "sealed" : sov.sovereign ? "sovereign" : "booting"}</span>`,
      `<span data-ok="${cap.never_leave ? "1" : "0"}">Inside: ${cap.never_leave ? "never leave" : "—"}</span>`,
      `<span data-ok="${doc.world_ready ? "1" : "0"}">RTX world: ${doc.world_ready ? "live" : "booting"}</span>`,
      `<span>Layers: ${esc(cap.layers_ready || "—")}</span>`,
      `<span>Phase: ${ASM.phase}</span>`,
    ].join("");
    const motto = $("qw-motto");
    if (motto) motto.textContent = cap.motto || doc.motto || motto.textContent;
  }

  function worldLog(msg) {
    const el = $("qw-log");
    if (!el) return;
    const line = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
    el.textContent = (el.textContent ? el.textContent + "\n" : "") + line;
    el.scrollTop = el.scrollHeight;
  }

  async function worldRefresh() {
    try {
      const [doc, gr] = await Promise.all([fetchWorld({ fast: true }), fetchGameRoom()]);
      renderMeta(doc);
      renderContactVector(doc);
      renderRtx(doc);
      renderHostess(doc);
      renderGatesWorld(doc);
      renderEyeComfort(doc);
      renderField(doc);
      renderKilroy(doc);
      renderAmmoosBoot(doc);
      renderChips(gr);
      renderSystemsGrid(gr);
      renderCores(gr, doc.ammoos_boot || ASM.bootMap);
      renderCapsule(doc.sovereign_capsule);
      renderEarball(doc);
      renderVirtualEyes(doc);
      globalThis.NEXUS_FIELD = doc;
      globalThis.QUEEN_WORLD = doc;
      globalThis.QUEEN_GAME_ROOM = gr;
      if (doc.fast) {
        fetchWorld({ fast: false })
          .then((full) => {
            renderMeta(full);
            renderContactVector(full);
            renderRtx(full);
            renderHostess(full);
            renderGatesWorld(full);
            renderEyeComfort(full);
            renderField(full);
            renderKilroy(full);
            renderAmmoosBoot(full);
            renderCores(gr, full.ammoos_boot || ASM.bootMap);
            renderCapsule(full.sovereign_capsule);
            renderEarball(full);
            renderVirtualEyes(full);
            globalThis.NEXUS_FIELD = full;
            globalThis.QUEEN_WORLD = full;
          })
          .catch(() => {});
      }
      return doc;
    } catch (e) {
      worldLog(`refresh error: ${e.message || e}`);
      throw e;
    }
  }

  async function runWorldAction(fn) {
    try {
      worldLog(await fn());
      await worldRefresh();
    } catch (e) {
      worldLog(`action error: ${e.message || e}`);
    }
  }

  function wireWorld() {
    document.querySelectorAll(".qw-dock-btn").forEach((b) => {
      b.addEventListener("click", () => setDockTab(b.dataset.tab));
    });
    document.querySelectorAll(".qw-os-subnav .qw-tab").forEach((t) => {
      t.addEventListener("click", () => setOsSubPane(t.dataset.osPane));
    });
    $("qw-open-gameroom")?.addEventListener("click", () => openWebbrowserTab("queen://gameroom"));
    $("qw-refresh")?.addEventListener("click", () => worldRefresh());
    $("qw-arm-dishes")?.addEventListener("click", () => runWorldAction(() => dispatchEye("arm-dishes")));
    $("qw-arm-person")?.addEventListener("click", () => runWorldAction(() => dispatchEye("arm-person")));
    $("qw-teach-comfort")?.addEventListener("click", () => runWorldAction(() => dispatchEye("teach-comfort")));
    $("qw-eye-verify")?.addEventListener("click", () => runWorldAction(() => dispatchEye("verify")));
    $("qw-hostess-teach")?.addEventListener("click", () => runWorldAction(() => dispatchBuild("hostess-teach")));
    $("qw-zocr-smoke")?.addEventListener("click", () => runWorldAction(() => dispatchBuild("zocr-smoke")));
    const teach = () => dispatchEye("teach", { lesson: "authority" });
    $("qw-teach-authority")?.addEventListener("click", () => runWorldAction(teach));
    $("qw-teach-authority-2")?.addEventListener("click", () => runWorldAction(teach));
    $("qw-eye-targets")?.addEventListener("click", () => runWorldAction(() => dispatchEye("targets")));
    $("qw-kilroy-refresh")?.addEventListener("click", () => worldRefresh());
    $("qw-rtx-status")?.addEventListener("click", () =>
      runWorldAction(async () => {
        const r = await fetch(API.rtx, { cache: "no-store" });
        return r.json();
      }),
    );
    const sovAction = (action, extra) => async () => {
      try {
        capsuleLog(await dispatchSovereign(action, extra));
        await worldRefresh();
      } catch (e) {
        capsuleLog(`sovereign error: ${e.message || e}`);
      }
    };
    $("qw-sov-rebuild")?.addEventListener("click", sovAction("rebuild", { target: "rtx" }));
    $("qw-sov-g16")?.addEventListener("click", sovAction("rebuild_g16"));
    $("qw-sov-chips")?.addEventListener("click", sovAction("rebuild_chips"));
    $("qw-sov-test")?.addEventListener("click", sovAction("test"));
    $("qw-sov-reboot")?.addEventListener("click", sovAction("reboot"));
    $("qw-sov-seal")?.addEventListener("click", sovAction("seal"));
    $("qw-sov-refresh")?.addEventListener("click", () => worldRefresh().then((d) => capsuleLog({ refreshed: d?.updated })));
    const earRun = (action, extra) => async () => {
      try {
        earLog(await dispatchEar(action, extra));
        await worldRefresh();
      } catch (e) {
        earLog(`ear error: ${e.message || e}`);
      }
    };
    $("qw-ear-arm")?.addEventListener("click", earRun("arm", { mode: "dishes" }));
    $("qw-ear-virtual")?.addEventListener("click", earRun("virtual_spawn", {
      mechanism: "kinetic_eardrum",
      bearing_deg: 45,
      distance_m: 2.5,
      x_m: 1.8,
      y_m: 1.8,
      z_m: 1.2,
    }));
    $("qw-ear-grid")?.addEventListener("click", earRun("virtual_grid", { mechanism: "kinetic_eardrum", count: 4 }));
    $("qw-ear-truth")?.addEventListener("click", earRun("truth_filter", { evidence: { mouth_correlation: 0.85 } }));
    $("qw-ear-localize")?.addEventListener("click", earRun("localize", { itd_us: 120, level_db: -24 }));
    $("qw-ear-verify")?.addEventListener("click", earRun("verify"));
    $("qw-ear-manual")?.addEventListener("click", async () => {
      const r = await fetch(`${API.fieldManual}?sense=audio`, { cache: "no-store" });
      earLog(await r.json());
    });
    $("qw-eye-manual")?.addEventListener("click", async () => {
      const r = await fetch(`${API.fieldManual}?sense=vision`, { cache: "no-store" });
      earLog(await r.json());
    });
    const eyeRun = (action, extra) => async () => {
      try {
        const r = await fetch(API.eye, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action, ...(extra || {}) }),
        });
        earLog(await r.json());
        await worldRefresh();
      } catch (e) {
        earLog(`eye virtual: ${e.message || e}`);
      }
    };
    $("qw-eye-wifi")?.addEventListener("click", eyeRun("virtual_spawn", {
      mechanism: "wifi_rf", bearing_deg: 90, distance_m: 4, x_m: 0, y_m: 4, z_m: 2,
    }));
    $("qw-eye-grid")?.addEventListener("click", eyeRun("virtual_grid", { mechanism: "wifi_rf", count: 6 }));
    $("qw-eye-anchor")?.addEventListener("click", eyeRun("pair_anchor", { bearing_deg: 0, z_m: 1.4 }));
    $("qw-eye-neural-wire")?.addEventListener("click", eyeRun("fused_analyze", { action: "analyze", evidence: { mouth_correlation: 0.9 } }));
    $("qw-sense-wire")?.addEventListener("click", async () => {
      const r = await fetch(API.senseNeural, { cache: "no-store" });
      earLog(await r.json());
    });
    $("qw-sense-encourage")?.addEventListener("click", async () => {
      const r = await fetch(API.senseNeural, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "encourage", eye_label: "clear_field", ear_label: "clear_audio", source: "hostess7", reinforce_pair: true }),
      });
      earLog(await r.json());
    });
    const secureEvidence = {
      mouth_correlation: 0.92,
      speech_present: true,
      sovereign_time_ok: true,
      provenance_weave_ok: true,
      rms: 1500,
      zcr: 0.08,
    };
    $("qw-ear-secure")?.addEventListener("click", earRun("secure_identify", {
      evidence: secureEvidence,
      existence: { correlation: 0.85 },
      localization: { bearing_deg: 12 },
    }));
    $("qw-ear-fusion")?.addEventListener("click", earRun("eye_ear_fusion", {
      evidence: secureEvidence,
      existence: { correlation: 0.85 },
    }));
    $("qw-ear-gac1")?.addEventListener("click", earRun("gac1"));
    $("qw-ear-sovereign")?.addEventListener("click", earRun("sovereign_time", { verify_sync: true }));
    $("qw-ear-signal")?.addEventListener("click", earRun("identify", {
      evidence: secureEvidence,
      existence: { correlation: 0.85 },
    }));
    $("qw-ear-sense-all")?.addEventListener("click", earRun("sense_all", { learn: true }));
    $("qw-ear-desktop")?.addEventListener("click", earRun("desktop_audio", { follow: true, learn: true }));
    $("qw-ear-track")?.addEventListener("click", earRun("sound_track"));
    const params = new URLSearchParams(location.search);
    const dock = params.get("dock");
    const embed = params.get("embed") === "1" || window.self !== window.top;
    if (embed) {
      document.body.classList.add("qw-embed");
      document.querySelector(".qb-chrome")?.setAttribute("hidden", "");
      document.querySelector(".qb-viewport")?.setAttribute("hidden", "");
      document.querySelector(".qw-dock")?.setAttribute("hidden", "");
    }
    if (dock === "gameroom") openWebbrowserTab("queen://gameroom");
    else if (dock === "chips") openWebbrowserTab("queen://chips");
    else if (dock === "cores") openWebbrowserTab("queen://cores");
    else if (dock === "terminal") setDockTab("terminal");
    else if (dock === "earball") setDockTab("earball");
    else if (dock === "field") setDockTab("field");
    else if (dock === "hostess") setDockTab("hostess");
    else if (dock === "eyeball") setDockTab("eyeball");
    else if (dock === "forge") setDockTab("forge");
    else if (dock === "kilroy") setDockTab("kilroy");
    else if (dock === "os" || dock === "overview") setDockTab("overview");
    else if (!embed) setDockTab("browser");
  }

  async function phaseWorld() {
    wireWorld();
    await worldRefresh();
    ASM.phase = "LIVE";
    setInterval(worldRefresh, 30000);
  }

  /* ── Boot — browser first, no loading gate ───────────────── */

  function isBrowserOnlySurface() {
    if (document.body?.dataset?.queenSurface === "browser") return true;
    if (/browser\.html$/i.test(location.pathname || "")) return true;
    return new URLSearchParams(location.search).get("browser") === "1";
  }

  async function boot() {
    const browserOnly = isBrowserOnlySurface();
    applyOptimisticSeal();
    document.body.classList.add("qw-browser-live");
    if (globalThis.QueenRootThreats) globalThis.QueenRootThreats.boot();
    try {
      await phaseBrowser();
      ASM.phase = "BROWSER";
    } catch (e) {
      console.error("[queen-os] browser", e);
      if ($("qb-status")) $("qb-status").textContent = `browser: ${e.message || e}`;
    }
    phaseSeal()
      .then((s) => {
        if ($("qb-status") && s) {
          $("qb-status").textContent = `${s.grok16?.ready ? "Grok16 in Queen" : "Grok16 …"} · ${s.sealed ? "Webbrowser sealed" : "Webbrowser …"}`;
        }
      })
      .catch((e) => console.warn("[queen-os] seal", e));
    if (!browserOnly) {
      phaseWorld().catch((e) => console.warn("[queen-os] world", e));
    }
  }

  globalThis.QueenOS = {
    ASM,
    boot,
    waitQueenReady,
    phaseSeal,
    browser: {
      refresh: browserRefresh,
      navigate,
      status: browserStatus,
      api: browserApi,
      activateTab,
      closeTab,
      newTab,
      togglePinTab,
      doc: browser,
      loadFrame,
    },
    world: { refresh: worldRefresh, setDockTab, openWebbrowserTab },
  };
  globalThis.QueenBrowser = globalThis.QueenOS.browser;
  globalThis.QueenRtxBoot = { boot: phaseSeal, sealSecureSpace, probeWebGpu };

  boot();
})();