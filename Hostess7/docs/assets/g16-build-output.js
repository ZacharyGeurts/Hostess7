/**
 * Grok16 Build Output Window — streams full per-language build log.
 */
(function () {
  "use strict";

  const output = document.getElementById("output");
  const footer = document.getElementById("footer");
  const btnStart = document.getElementById("btn-start");
  const btnClear = document.getElementById("btn-clear");
  const btnScroll = document.getElementById("btn-scroll");
  const statTotal = document.getElementById("stat-total");
  const statDone = document.getElementById("stat-done");
  const statPass = document.getElementById("stat-pass");
  const statFail = document.getElementById("stat-fail");
  const statState = document.getElementById("stat-state");

  let offset = 0;
  let polling = null;
  let autoScroll = true;
  const API = window.G16_TEST_API || "/api/g16/language-test";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function appendLine(entry) {
    const kind = entry.kind || "build";
    const div = document.createElement("div");
    div.className = `line line--${kind}`;
    const prefix = entry.lang ? `[${entry.lang}] ` : "";
    div.textContent = prefix + (entry.text || "");
    output.appendChild(div);
    if (autoScroll) {
      output.scrollTop = output.scrollHeight;
    }
  }

  function updateStats(st) {
    if (!st) return;
    if (st.total != null) statTotal.textContent = String(st.total);
    if (st.done != null) statDone.textContent = String(st.done);
    if (st.passed != null) statPass.textContent = String(st.passed);
    if (st.failed != null) statFail.textContent = String(st.failed);
    if (st.running) statState.textContent = "running";
    else if (st.done && st.total && st.done >= st.total) statState.textContent = "done";
    else statState.textContent = st.running === false && st.done ? "done" : "idle";
  }

  async function pollLog() {
    try {
      const res = await fetch(`${API}/log?offset=${offset}`);
      const j = await res.json();
      if (!j.ok) return;
      for (const line of j.lines || []) {
        if (line.kind === "summary" && line.data) {
          appendLine({ kind: "summary", text: `SUMMARY: ${line.data.passed} passed, ${line.data.failed} failed` });
          updateStats(line.data);
        } else {
          appendLine(line);
        }
      }
      offset = j.next_offset ?? offset;
      updateStats(j.status);
      if (j.status && !j.status.running && j.status.done >= j.status.total && j.status.total > 0) {
        footer.textContent = `Build complete — ${j.status.passed} passed · ${j.status.failed} failed`;
        stopPolling();
        btnStart.disabled = false;
      }
    } catch (err) {
      footer.textContent = `Poll error: ${err.message}`;
    }
  }

  function startPolling() {
    if (polling) return;
    polling = setInterval(pollLog, 400);
    pollLog();
  }

  function stopPolling() {
    if (polling) {
      clearInterval(polling);
      polling = null;
    }
  }

  async function startMatrix() {
    btnStart.disabled = true;
    footer.textContent = "Starting Grok16 language test matrix…";
    try {
      const res = await fetch(`${API}/start`, { method: "POST" });
      const j = await res.json();
      if (j.started === false && j.message === "already_running") {
        footer.textContent = "Matrix already running — streaming log…";
      } else {
        footer.textContent = "Build running — streaming full output…";
      }
      startPolling();
    } catch (err) {
      footer.textContent = `Start failed: ${err.message}`;
      btnStart.disabled = false;
    }
  }

  async function loadMatrix() {
    try {
      const res = await fetch(`${API}/matrix`);
      const j = await res.json();
      if (j.matrix) {
        statTotal.textContent = String(j.matrix.length);
      }
    } catch (_) {
      /* standalone may not have matrix until server up */
    }
  }

  btnStart?.addEventListener("click", () => startMatrix());
  btnClear?.addEventListener("click", () => {
    output.innerHTML = "";
    offset = 0;
    footer.textContent = "Cleared.";
  });
  btnScroll?.addEventListener("click", () => {
    autoScroll = !autoScroll;
    btnScroll.setAttribute("aria-pressed", String(autoScroll));
    btnScroll.textContent = autoScroll ? "Auto-scroll" : "Scroll paused";
  });

  loadMatrix();
  startPolling();

  if (new URLSearchParams(location.search).get("autostart") === "1") {
    setTimeout(() => startMatrix(), 600);
  }
})();