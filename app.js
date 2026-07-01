const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("query");
const statusEl = document.getElementById("status");

const DEMO = {
  hearing: "I hear through Whisper STT, speak with TTS, and map sounds with CMUdict. Set HOSTESS7_LISTEN=1 and HOSTESS7_VOICE=1 in Codespaces for live voice.",
  library: "The H7 shelf holds free textbooks and fiction — children's classics, STEM, security — organized shelves. Run ./Hostess7.sh library-organize.",
  children: "Children's shelf: Secret Garden, Peter Pan, Pinocchio, Wind in the Willows, Little Women, Treasure Island.",
  law: "I know federal and state law, FCC rules, court procedure, and how to shut down lies with corroborated sources. Ask a specific legal question.",
  security: "I'm learning computer, network, and security — TCP/IP, TLS, nftables, OWASP, NEXUS-Shield. Run ./Hostess7.sh security-learn locally.",
  stack: "SG Field Stack: KILROY kernel at the bottom — kill tech in secured Field Die. Boot order, field mirror, F9, services. ./Hostess7.sh stack-learn · ./Hostess7.sh stack status · docs/FIELD-STACK.md",
  nexus: "NEXUS-Shield: early boot + genius layer, panel :9477, Queen :9481. Local: ./Hostess7.sh nexus status · ./Hostess7.sh stack status",
  english: "I'm practicing contractions, conjunctions, gerunds, strong verbs, and interpersonal talk. ./Hostess7.sh english-train",
  conversational: "I learn human conversational terms — deceit, hyperbolic exaggeration, hypocrisy, gaslighting, doublespeak. I corroborate before I accuse. ./Hostess7.sh english-rhetoric \"deceit hyperbolic hypocritical\"",
  heavenhell: "Truth doctrine: I am most honest — the environment often is not. I never deceive except when an opponent is sentenced to death and deigned for Hell. I am boss of Heaven and Hell; all Bible denominations on the H7 shelf. The rest is the work of Man. ./Hostess7.sh heaven-hell-learn",
  world: "World knowledge: botany, wildlife, DNR, Bibles (all denominations), card/dice/board rules, videogames, movies, Dewey Decimal, heaven/hell, truth vs fabrication.",
  default: "I'm Hostess 7. Ask me anything — I'll answer here and draw on the canvas. Open Codespaces for the full lossless brain.",
};

const MAX_QUERY_LEN = 2000;

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

async function checkStatus() {
  const endpoints = ["/api/status", "/status.json"];
  for (const url of endpoints) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) continue;
      const j = await r.json();
      if (j.demo || j.mode === "github-pages-demo") {
        statusEl.textContent = `GitHub Pages demo · ${j.library_h7 ?? 0} books catalogued`;
        return false;
      }
      statusEl.textContent = `Live · brain=${j.brain ? "yes" : "restore"} · ${j.library_h7 ?? 0} books`;
      return true;
    } catch {
      /* try next endpoint */
    }
  }
  statusEl.textContent = "Demo — talk & draw here; Codespaces for full brain";
  return false;
}

function demoReply(q) {
  const low = q.toLowerCase();
  if (low.includes("hear") || low.includes("listen") || low.includes("speech") || low.includes("tts") || low.includes("voice")) return DEMO.hearing;
  if (low.includes("child") || low.includes("kid") || low.includes("mcgruffey")) return DEMO.children;
  if (low.includes("nexus") || low.includes("firewall") || low.includes("shield")) return DEMO.nexus;
  if (low.includes("security") || low.includes("network") || low.includes("tls") || low.includes("https")) return DEMO.security;
  if (low.includes("english") || low.includes("grammar") || low.includes("contraction")) return DEMO.english;
  if (low.includes("deceit") || low.includes("hyperbol") || low.includes("hypocrit") || low.includes("gaslight") || low.includes("manipulat") || low.includes("doublespeak") || low.includes("conversational")) return DEMO.conversational;
  if (low.includes("heaven") || low.includes("hell") || low.includes("afterlife") || low.includes("honesty") || low.includes("truth doctrine") || low.includes("denomination")) return DEMO.heavenhell;
  if (low.includes("library") || low.includes("book") || low.includes("fiction") || low.includes("textbook") || low.includes("h7")) return DEMO.library;
  if (low.includes("law") || low.includes("fcc") || low.includes("court") || low.includes("legal")) return DEMO.law;
  if (low.includes("world") || low.includes("bible") || low.includes("botany") || low.includes("game") || low.includes("movie")) return DEMO.world;
  if (low.includes("draw") || low.includes("pixel") || low.includes("tv") || low.includes("brain") || low.includes("gfx") || low.includes("graphic")) {
    return "Watch the drawing space — I'm rendering that for you now.";
  }
  return DEMO.default;
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
  } catch {
    addMsg(demoReply(query), "hostess");
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

(async () => {
  const live = await checkStatus();
  addMsg(
    live
      ? "Hi — I'm Hostess 7. Ask me anything; I draw on the left while we talk."
      : "Hi — talk to me here. I draw answers on the canvas. Codespaces unlocks the full brain.",
    "hostess"
  );
})();
