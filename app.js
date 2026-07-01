const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("query");
const statusEl = document.getElementById("status");
const modeBanner = document.getElementById("mode-banner");
const modeTitle = document.getElementById("mode-title");
const modeDetail = document.getElementById("mode-detail");
const bootBtn = document.getElementById("boot-btn");

let liveBrain = false;
let bootManifest = null;

const MAX_QUERY_LEN = 2000;
const BOOT_CMD = "./Hostess7.sh boot";
const CODESPACES =
  "https://github.com/codespaces/new?hide_repo_select=true&repo=ZacharyGeurts/Hostess7";

function sanitize(text) {
  if (typeof text !== "string") return "";
  return text
    .replace(/<[^>]*>/g, "")
    .replace(/javascript:/gi, "")
    .slice(0, MAX_QUERY_LEN)
    .trim();
}

function addMsg(text, role) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function showStackNav(j) {
  const stack = j.stack || {};
  const surfaces = j.surfaces || bootManifest?.surfaces || {};
  const show = (id, on, href) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.hidden = !on;
    if (href) el.href = href;
  };
  show("nav-panel", !!(stack.panel || j.kilroy), surfaces.panel);
  show("nav-queen", !!stack.queen, surfaces.queen);
  show("nav-training", !!stack.training, surfaces.training);
}

async function loadBootManifest() {
  try {
    const r = await fetch("/boot.json", { cache: "no-store" });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function setBootUI(active) {
  if (bootBtn) bootBtn.hidden = !active;
  if (active) modeBanner.classList.add("boot");
  else modeBanner.classList.remove("boot");
}

async function checkStatus() {
  try {
    const r = await fetch("/api/status", { cache: "no-store" });
    if (!r.ok) throw new Error("status");
    const j = await r.json();
    liveBrain = !!(j.brain && j.ok && (j.war_ready || j.mode === "live" || j.posture === "war-ready"));
    showStackNav(j);
    setBootUI(false);
    if (liveBrain) {
      const parts = [];
      if (j.kilroy || j.stack?.panel) parts.push("KILROY");
      if (j.stack?.queen) parts.push("Queen");
      if (j.stack?.training) parts.push("training");
      statusEl.textContent = `Live · brain on · ${j.library_h7 ?? 0} books · ${parts.join(" · ") || "field"}`;
      modeTitle.textContent = "War-ready — Hostess 7 live";
      modeDetail.textContent = "Full brain · KILROY stack · field_superintelligence · never demo";
      modeBanner.classList.add("live");
      modeBanner.classList.add("war");
      return true;
    }
    statusEl.textContent = `Field web · brain=${j.brain ? "on" : "loading"} · ${j.library_h7 ?? 0} books`;
    modeTitle.textContent = "Hostess 7 field web";
    modeDetail.textContent = `Run ${BOOT_CMD} for full brain + KILROY doctrine`;
    return false;
  } catch {
    setBootUI(true);
    modeBanner.classList.remove("live");
    statusEl.textContent = "War-ready mirror — boot for full brain on loopback";
    modeTitle.textContent = "Boot KILROY + Hostess 7 — war posture";
    modeDetail.textContent = `${BOOT_CMD} — always operational, never demo`;
    return false;
  }
}

async function ask(rawQuery) {
  const query = sanitize(rawQuery);
  if (!query) return;
  addMsg(query, "user");
  input.value = "";
  window.HostessGfx?.presentScene(query);
  try {
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!r.ok) throw new Error("ask failed");
    const j = await r.json();
    addMsg(j.text || "(no reply)", "hostess");
    checkStatus();
  } catch {
    if (liveBrain) {
      addMsg("Brain request failed — check Hostess7 logs.", "hostess");
    } else {
      addMsg(
        `Full Hostess 7 is not running here. Boot: ${BOOT_CMD} — or open Codespaces (button above).`,
        "hostess"
      );
    }
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (q) ask(q);
});

document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => ask(btn.dataset.q || ""));
});

bootBtn?.addEventListener("click", () => {
  window.open(bootManifest?.codespaces || CODESPACES, "_blank", "noopener,noreferrer");
});

async function sovereignPulse() {
  try {
    const r = await fetch("/api/sovereign-time", { cache: "no-store" });
    if (r.ok) return await r.json();
  } catch {
    /* static mirror — no sovereign endpoint */
  }
  return null;
}

function bindSovereignRefresh() {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      sovereignPulse().then(() => checkStatus());
    }
  });
  window.addEventListener("focus", () => {
    sovereignPulse().then(() => checkStatus());
  });
  form.addEventListener("focusin", () => checkStatus());
}

(async () => {
  bootManifest = await loadBootManifest();
  bindSovereignRefresh();
  await sovereignPulse();
  const live = await checkStatus();
  addMsg(
    live
      ? "I'm Hostess 7 — war-ready, live on KILROY. Sovereign time only — never demo."
      : `War-ready boot: ${BOOT_CMD}. Sovereign pulse on focus — no wall timers.`,
    "hostess"
  );
})();