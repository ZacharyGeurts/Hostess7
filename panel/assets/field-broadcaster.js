/**
 * Broadcaster — launches OBS Studio verbatim (OBS-Field source build).
 * Web surface is a thin launcher only; scenes/sources/mixer live in native OBS.
 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  function apiUrl(path) {
    if (global.H7Api) return global.H7Api(path);
    if (global.H7Base) return global.H7Base(path);
    return path;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function setStatus(msg, kind) {
    const el = $("bc-status");
    if (!el) return;
    el.textContent = msg;
    el.className = "bc-launcher-status" + (kind ? " " + kind : "");
  }

  function setHint(html) {
    const el = $("bc-hint");
    if (!el) return;
    if (!html) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    el.innerHTML = html;
  }

  async function api(sub, opts) {
    const path = "/api/field-broadcaster" + (sub ? "/" + sub : "");
    const res = await fetch(apiUrl(path), Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function renderMeta(doc) {
    const el = $("bc-meta");
    if (!el || !doc) return;
    const eng = doc.engine || {};
    const senses = doc.senses || {};
    const eye = senses.final_eye || {};
    const ear = senses.final_ear || {};
    const mouth = senses.final_mouth || {};
    const rows = [
      ["Engine", eng.backend || "obs-studio"],
      ["UI", eng.ui || "verbatim OBS"],
      ["Binary", doc.binary || "—"],
      ["Profile", doc.profile || "—"],
      ["Collection", doc.collection || "—"],
      ["Final_Eye", eye.reachable ? "live" : eye.ok ? "ready" : "—"],
      ["Final_Ear", ear.present ? "wired" : "optional"],
      ["Final_Mouth", mouth.present ? "wired" : "optional"],
      ["Running", eng.running ? "yes" : "no"],
      ["g16 build", (doc.g16 || {}).ok ? "ready" : "pending"],
    ];
    el.innerHTML = rows
      .map(
        ([k, v]) =>
          "<div><dt>" + esc(k) + "</dt><dd>" + esc(String(v)) + "</dd></div>"
      )
      .join("");
  }

  function obsMissingHint(doc) {
    return (
      "<strong>OBS binary not found.</strong> Broadcaster uses OBS Studio rebuilt from source. " +
      "Run <code>OBS-Field/forge/clone-upstream.sh</code> then <code>OBS-Field/build-field-obs.sh</code>, " +
      "or install system <code>obs</code>. Source tree: " +
      esc((doc.build || {}).upstream || "OBS-Field/upstream/obs-studio")
    );
  }

  async function refresh() {
    try {
      const doc = await api("");
      renderMeta(doc);
      if (!doc.ok) {
        setStatus("OBS not installed — prepare the source build.", "err");
        setHint(obsMissingHint(doc));
        return doc;
      }
      if (doc.engine && doc.engine.running) {
        setStatus("Broadcaster is running — use the native OBS window.", "ok");
      } else {
        setStatus("Ready — opens Broadcaster (OBS Studio verbatim).", "ok");
      }
      setHint("");
      return doc;
    } catch (e) {
      setStatus("Could not reach Broadcaster API: " + e.message, "err");
      return null;
    }
  }

  async function launch(mode) {
    setStatus("Launching Broadcaster…", "busy");
    setHint("");
    const sub = mode === "record" ? "record" : mode === "studio" ? "studio" : "launch";
    try {
      const out = await api(sub, { method: "POST", body: "{}" });
      if (!out.ok) {
        const err = out.error || "launch_failed";
        setStatus(err === "obs_missing" ? "Broadcaster binary missing — run source build." : "Launch failed: " + err, "err");
        if (err === "obs_missing") {
          const doc = await api("");
          setHint(obsMissingHint(doc || {}));
        }
        return out;
      }
      setStatus("Broadcaster launched (pid " + (out.pid || "?") + "). Use the native OBS window.", "ok");
      setTimeout(refresh, 1200);
      return out;
    } catch (e) {
      setStatus("Launch error: " + e.message, "err");
      return null;
    }
  }

  async function prepareBuild() {
    setStatus("Preparing OBS source tree…", "busy");
    try {
      const out = await api("build", { method: "POST", body: "{}" });
      if (!out.ok) {
        setStatus(out.error || "Build prep failed", "err");
        setHint(esc(out.hint || out.log_tail || ""));
        return out;
      }
      setStatus(out.message || "Source tree ready — run build-field-obs.sh to compile.", "ok");
      setHint(esc(out.hint || ""));
      await refresh();
      return out;
    } catch (e) {
      setStatus("Build prep error: " + e.message, "err");
      return null;
    }
  }

  function bind() {
    $("bc-launch")?.addEventListener("click", () => launch("open"));
    $("bc-record")?.addEventListener("click", () => launch("record"));
    $("bc-studio")?.addEventListener("click", () => launch("studio"));
    $("bc-build")?.addEventListener("click", prepareBuild);
  }

  bind();
  refresh().then(function (doc) {
    if (doc && doc.ok && !(doc.engine && doc.engine.running)) {
      const params = new URLSearchParams(global.location.search);
      if (params.get("autolaunch") !== "0") {
        launch("open");
      }
    }
  });
  setInterval(refresh, 12000);
})();