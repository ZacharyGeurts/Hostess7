/**
 * GitHub Pages — sovereign GitHub mind lane (unhook local/sovereign brain).
 * NEXUS C2 · KILROY · ZNetwork · Truth DNS · Field DHCP · iPXE stack updates queue here.
 */
(function (global) {
  "use strict";

  const OUTBOX_KEY = "h7-github-brain-outbox";
  const LANE = "github-mirror";

  function pagesRuntime() {
    return document.body?.dataset?.pagesRuntime === "1" || !!global.HOSTESS7_PAGES_BASE;
  }

  function base() {
    return (global.HOSTESS7_PAGES_BASE || "/Hostess7").replace(/\/$/, "");
  }

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    return base() + (path.startsWith("/") ? path : "/" + path);
  }

  function now() {
    return new Date().toISOString();
  }

  function readOutbox() {
    try {
      const raw = global.localStorage.getItem(OUTBOX_KEY);
      return raw ? JSON.parse(raw) : { schema: "github-brain-outbox/v1", entries: [], updated: null };
    } catch (_) {
      return { schema: "github-brain-outbox/v1", entries: [], updated: null };
    }
  }

  function writeOutbox(doc) {
    doc.updated = now();
    try {
      global.localStorage.setItem(OUTBOX_KEY, JSON.stringify(doc));
    } catch (_) {}
    return doc;
  }

  function queueMindUpdate(entry) {
    const box = readOutbox();
    box.entries = box.entries || [];
    box.entries.push(
      Object.assign(
        {
          id: "mind-" + Date.now().toString(36),
          ts: now(),
          lane: LANE,
          source: "nexus-c2-pages",
        },
        entry || {}
      )
    );
    while (box.entries.length > 48) box.entries.shift();
    writeOutbox(box);
    global.dispatchEvent(new CustomEvent("h7:github-mind-update", { detail: box }));
    return box;
  }

  /* DO NOT REMOVE — Pages never probes sovereign cache/fieldstorage brain. */
  function unhookSovereignBrain() {
    global.H7_BRAIN_LANE = LANE;
    global.H7_SOVEREIGN_BRAIN = false;
    global.H7_LOCAL_BRAIN = false;
    global.H7_GITHUB_MIND = true;
    document.documentElement.dataset.h7BrainLane = LANE;
    const orig = global.__H7_ORIG_FETCH__;
    if (!orig || orig.__h7BrainUnhooked) return;
    global.__H7_ORIG_FETCH__ = async function h7BrainGuardedFetch(url, opts) {
      const u = String(url || "");
      if (
        /127\.0\.0\.1:\d+/.test(u) &&
        (/\/api\/field-brain/.test(u) ||
          /\/api\/brain/.test(u) ||
          /fieldstorage/.test(u) ||
          /\/api\/hostess7-command/.test(u))
      ) {
        throw new Error("Sovereign brain unhooked — GitHub mind only on Pages");
      }
      return orig(url, opts);
    };
    global.__H7_ORIG_FETCH__.__h7BrainUnhooked = true;
  }

  async function loadStackSlice(path) {
    try {
      const r = await fetch(api(path), { cache: "no-store" });
      if (!r.ok) return null;
      return r.json();
    } catch (_) {
      return null;
    }
  }

  async function syncStackMind() {
    const [brain, dns, zn, status, botDns] = await Promise.all([
      loadStackSlice("/api/brain"),
      loadStackSlice("/api/field-dns"),
      loadStackSlice("/api/znetwork"),
      loadStackSlice("/api/status"),
      loadStackSlice("/api/field-botnet-dns-dhcp"),
    ]);
    const stack = {
      kilroy: { role: "PC core · network lane · loopback defense", layer: -2, fkey: "F10" },
      nexus_c2: { role: "Command · security · Universal Protector", layer: -3, fkey: "F9", surface: base() + "/command/" },
      znetwork: { ok: !!(zn && zn.ok !== false), schema: zn?.schema, motto: zn?.motto || "Field secure network manager" },
      dns: { ok: !!(dns && dns.ok !== false), schema: dns?.schema || "field-dns/v2", title: dns?.title || "Truth Resolver · Field DHCP" },
      dhcp: { role: "Field DHCP · auto-connect with Truth DNS", planetary: true },
      botnet_dns_dhcp: {
        ok: !!(botDns && botDns.ok !== false),
        node_count: botDns?.bot_network?.node_count,
        stable: botDns?.stable,
        github: botDns?.github_control_plane?.pages_runtime,
      },
      ipxe: { role: "iPXE boot chain · stack netboot lane", note: "Doctrine wired on publish — loopback for live TFTP" },
      queen_browser: { layer: 0, fkey: "F12", surface: base() + "/queen/browser.html" },
      brain: {
        lane: brain?.mode || LANE,
        identity: brain?.identity || "Hostess7-GitHub",
        corpus: base() + "/github-brain/corpus.json",
        read_only: true,
        writes_to_sovereign: false,
      },
      version: status?.version || brain?.version,
    };
    const summary =
      "GitHub mind synced · KILROY · NEXUS C2 · ZNetwork · DNS · DHCP · iPXE stack — " +
      (stack.version ? "v" + stack.version : "Pages lane") +
      ". Sovereign brain unhooked; updates queue for pages-build publish.";
    queueMindUpdate({
      type: "stack_sync",
      title: "NEXUS C2 stack mind",
      text: summary,
      stack: stack,
    });
    return { ok: true, summary: summary, stack: stack, lane: LANE };
  }

  function boot() {
    if (!pagesRuntime()) return;
    unhookSovereignBrain();
    global.Hostess7Interaction?.wire?.();
    if (!readOutbox().entries?.length) {
      syncStackMind().catch(function () {});
    }
  }

  global.Hostess7GithubBrain = {
    lane: LANE,
    queueMindUpdate: queueMindUpdate,
    readOutbox: readOutbox,
    syncStackMind: syncStackMind,
    unhookSovereignBrain: unhookSovereignBrain,
    boot: boot,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : globalThis);