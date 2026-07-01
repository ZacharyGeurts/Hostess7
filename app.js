const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatIn = document.getElementById("chat-in");
const searchForm = document.getElementById("search-form");
const searchDomain = document.getElementById("search-domain");
const searchQ = document.getElementById("search-q");
const searchOut = document.getElementById("search-out");
const statusList = document.getElementById("status-list");
const apiList = document.getElementById("api-list");
const surfaceList = document.getElementById("surface-list");
const brainBadge = document.getElementById("brain-badge");
const routeLabel = document.getElementById("route-label");
const codespacesBtn = document.getElementById("codespaces-btn");
const btnStatus = document.getElementById("btn-status");

const LOOPBACK = Hostess7ApiShim.LOOPBACK;
const CODESPACES =
  "https://github.com/codespaces/new?hide_repo_select=true&repo=ZacharyGeurts/Hostess7";

const API_ROUTES = [
  "/api/status",
  "/api/brain",
  "/api/ask",
  "/api/hearing",
  "/api/world",
  "/api/library/search",
  "/api/videogames",
];

let manifest = null;
let corpus = null;
let loopbackUp = false;

function chatLine(text, cls, who) {
  const el = document.createElement("div");
  el.className = "chat-line " + (cls || "");
  if (who) {
    const tag = document.createElement("span");
    tag.className = "chat-who";
    tag.textContent = who;
    el.appendChild(tag);
  }
  const body = document.createElement("div");
  body.className = "chat-text";
  body.textContent = text;
  el.appendChild(body);
  chatLog.appendChild(el);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setStatus(items) {
  statusList.innerHTML = "";
  items.forEach(([k, v]) => {
    const li = document.createElement("li");
    li.innerHTML = "<strong>" + k + "</strong> " + v;
    statusList.appendChild(li);
  });
}

function renderApiList() {
  apiList.innerHTML = "";
  API_ROUTES.forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    apiList.appendChild(li);
  });
}

async function probeLoopback() {
  try {
    const r = await fetch(LOOPBACK + "/health", { cache: "no-store", mode: "cors" });
    return r.ok;
  } catch {
    return false;
  }
}

async function scanSurfaces() {
  surfaceList.innerHTML = "";
  loopbackUp = await probeLoopback();
  if (loopbackUp) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = LOOPBACK + "/";
    a.textContent = "Full stack LIVE — " + LOOPBACK;
    a.target = "_blank";
    a.rel = "noopener";
    li.appendChild(a);
    surfaceList.appendChild(li);
    brainBadge.textContent = "loopback + pages";
    brainBadge.className = "badge live";
  } else {
    const li = document.createElement("li");
    li.className = "offline";
    li.textContent = "Pages package active (static API + corpus)";
    surfaceList.appendChild(li);
    brainBadge.textContent = "full package";
    brainBadge.className = "badge";
  }
}

async function refreshStatus() {
  try {
    const st = await fetch("/api/status").then((r) => r.json());
    setStatus([
      ["mode", st.mode || "pages-full-package"],
      ["brain", st.brain ? "ready" : "export"],
      ["library", String(st.library_h7 || 0) + " H7"],
      ["posture", st.posture || "war-ready"],
      ["route", loopbackUp ? "loopback" : "pages"],
    ]);
    if (routeLabel) routeLabel.textContent = st.mode || "pages-full-package";
  } catch (err) {
    chatLine("Status error: " + err.message, "warn", "sys");
  }
}

async function handleAsk(raw) {
  const q = Hostess7Brain.sanitize(raw);
  if (!q) return;
  chatLine(q, "user", "you");
  chatIn.disabled = true;
  chatLine("…", "thinking", "H7");

  const r = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: q }),
  });
  const res = await r.json();

  const thinking = chatLog.querySelector(".chat-line.thinking");
  if (thinking) thinking.remove();

  chatLine(res.text || res.error || "No response.", "hostess", "H7");
  if (routeLabel && res.route) routeLabel.textContent = res.route;
  chatIn.disabled = false;
  chatIn.focus();
}

async function handleSearch(e) {
  e.preventDefault();
  const domain = searchDomain.value;
  const q = Hostess7Brain.sanitize(searchQ.value || "overview");
  const paths = {
    hearing: "/api/hearing?q=" + encodeURIComponent(q),
    world: "/api/world?q=" + encodeURIComponent(q),
    library: "/api/library/search?q=" + encodeURIComponent(q),
    videogames: "/api/videogames?q=" + encodeURIComponent(q),
  };
  const path = paths[domain] || paths.world;
  try {
    const doc = await fetch(path).then((r) => r.json());
    searchOut.textContent = JSON.stringify(doc, null, 2);
  } catch (err) {
    searchOut.textContent = String(err);
  }
}

function bindSovereignRefresh() {
  const pulse = () => {
    scanSurfaces().then(refreshStatus);
  };
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") pulse();
  });
  window.addEventListener("focus", pulse);
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const v = chatIn.value;
  chatIn.value = "";
  handleAsk(v);
});

searchForm.addEventListener("submit", handleSearch);
btnStatus?.addEventListener("click", refreshStatus);
codespacesBtn?.addEventListener("click", () => {
  window.open(manifest?.codespaces || CODESPACES, "_blank", "noopener,noreferrer");
});

document.querySelectorAll("[data-scene]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.dispatchEvent(new CustomEvent("hostess7-gfx-scene", { detail: btn.dataset.scene }));
  });
});

(async () => {
  renderApiList();
  try {
    const init = await Hostess7Brain.initPagesBrain();
    manifest = init.manifest;
    corpus = init.corpus;
    window.__H7_BRAIN__ = { manifest: manifest, corpus: corpus, loopbackUrl: null };

    const verEl = document.getElementById("ver");
    if (verEl && manifest.version) verEl.textContent = manifest.version;

    chatLine(
      "I'm the GitHub brain — a read-only mirror of Hostess 7. Same knowledge, isolated lane. " +
        "Your chat here never writes to cache/fieldstorage/brain or brain/state. " +
        "Corpus: " + (corpus.chunk_count || corpus.chunks?.length || 0) + " chunks. " +
        "Full sovereign stack: ./Hostess7.sh boot on loopback.",
      "hostess",
      "H7"
    );
  } catch (err) {
    chatLine("Brain init: " + err.message, "warn", "sys");
    brainBadge.textContent = "degraded";
  }

  bindSovereignRefresh();
  await scanSurfaces();
  await refreshStatus();
  chatIn.focus();
})();