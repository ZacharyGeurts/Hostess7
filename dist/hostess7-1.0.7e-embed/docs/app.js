const termOut = document.getElementById("term-out");
const termForm = document.getElementById("term-form");
const termIn = document.getElementById("term-in");
const surfacesPanel = document.getElementById("surfaces");
const surfaceList = document.getElementById("surface-list");
const codespacesBtn = document.getElementById("codespaces-btn");

const BOOT_CMD = "./Hostess7.sh boot";
const CODESPACES =
  "https://github.com/codespaces/new?hide_repo_select=true&repo=ZacharyGeurts/Hostess7";

const SURFACES = [
  { id: "hostess7", label: "Hostess 7 web", url: "http://127.0.0.1:8080/", path: "/api/status" },
  { id: "panel", label: "NEXUS Field C2", url: "http://127.0.0.1:9477/field", path: "/field" },
  { id: "queen", label: "Queen Browser", url: "http://127.0.0.1:9481/world/browser.html", path: "/api/status?fast=1" },
  { id: "training", label: "Training chamber", url: "http://127.0.0.1:9488/", path: "/" },
];

let bootManifest = null;
let liveStack = false;

function line(text, cls) {
  const el = document.createElement("div");
  el.className = cls ? `term-line ${cls}` : "term-line";
  el.textContent = text;
  termOut.appendChild(el);
  termOut.scrollTop = termOut.scrollHeight;
}

function block(lines, cls) {
  lines.forEach((t) => line(t, cls));
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

async function probeSurface(s) {
  try {
    const origin = new URL(s.url).origin;
    const r = await fetch(`${origin}${s.path}`, { cache: "no-store", mode: "cors" });
    return r.ok;
  } catch {
    return false;
  }
}

function renderSurfaces(results) {
  surfaceList.innerHTML = "";
  let any = false;
  results.forEach(({ s, up }) => {
    const li = document.createElement("li");
    if (up) {
      any = true;
      const a = document.createElement("a");
      a.href = s.url;
      a.textContent = `${s.label} — ${s.url}`;
      a.target = "_blank";
      a.rel = "noopener";
      li.appendChild(a);
    } else {
      li.textContent = `${s.label} — ${s.url} (offline)`;
      li.className = "offline";
    }
    surfaceList.appendChild(li);
  });
  surfacesPanel.hidden = !any;
  liveStack = any;
}

async function scanLoopback() {
  const checks = await Promise.all(
    SURFACES.map(async (s) => ({ s, up: await probeSurface(s) }))
  );
  renderSurfaces(checks);
  return checks.some((c) => c.up);
}

function showBootHelp() {
  block([
    "",
    "This GitHub Pages site is a BOOT TERMINAL only.",
    "It does not host the brain, talk UI, or Queen shell.",
    "",
    "On your machine (or Codespaces):",
    "  git clone https://github.com/ZacharyGeurts/Hostess7.git",
    "  cd Hostess7",
    `  ${BOOT_CMD}`,
    "",
    "Then open your local browser at:",
    "  http://127.0.0.1:8080/     — Hostess 7",
    "  http://127.0.0.1:9477/field — NEXUS C2",
    "  http://127.0.0.1:9481/world/browser.html — Queen",
    "",
    "Commands: help | boot | scan | surfaces | codespaces",
    "",
  ], "muted");
}

function handleCommand(raw) {
  const cmd = (raw || "").trim().toLowerCase();
  line(`hostess7@pages:~$ ${raw || ""}`, "cmd");

  if (!cmd || cmd === "help" || cmd === "?") {
    showBootHelp();
    return;
  }
  if (cmd === "boot") {
    block([
      "Boot sequence (run on your host, not on github.io):",
      `  ${BOOT_CMD}`,
      "",
      "Steps: deps → zac-restore → stack-learn → on → alert-posture → web-start",
      "Posture: war-ready · never demo",
    ]);
    return;
  }
  if (cmd === "scan" || cmd === "status") {
    line("Scanning loopback surfaces…", "info");
    scanLoopback().then((up) => {
      if (up) {
        line("Stack LIVE — open 127.0.0.1 links in your browser (panel right).", "ok");
      } else {
        line("No loopback stack detected. Run boot locally first.", "warn");
      }
    });
    return;
  }
  if (cmd === "surfaces" || cmd === "urls") {
    SURFACES.forEach((s) => line(`  ${s.label}: ${s.url}`));
    return;
  }
  if (cmd === "codespaces") {
    window.open(bootManifest?.codespaces || CODESPACES, "_blank", "noopener,noreferrer");
    line("Opening GitHub Codespaces…", "info");
    return;
  }
  if (cmd === "clear") {
    termOut.innerHTML = "";
    return;
  }
  line(`Unknown: ${raw}. Type 'help'.`, "warn");
}

function bindSovereignRefresh() {
  const pulse = () => scanLoopback();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") pulse();
  });
  window.addEventListener("focus", pulse);
}

termForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const v = termIn.value;
  termIn.value = "";
  handleCommand(v);
});

codespacesBtn?.addEventListener("click", () => handleCommand("codespaces"));

(async () => {
  bootManifest = await loadBootManifest();
  if (bootManifest?.version) {
    const verEl = document.getElementById("ver");
    if (verEl) verEl.textContent = bootManifest.version;
  }

  block([
    "Hostess 7 — Boot Terminal (GitHub Pages)",
    "========================================",
    "Pages URL is NOT the live brain.",
    "Boot here → use 127.0.0.1 in your browser.",
    "",
  ], "head");

  showBootHelp();
  bindSovereignRefresh();
  const up = await scanLoopback();
  if (up) {
    line("Loopback stack detected — local surfaces ready.", "ok");
  } else {
    line(`Type 'boot' for instructions, or 'codespaces' to boot in cloud.`, "info");
  }
  termIn.focus();
})();