/**
 * After AmmoOS desktop mounts on Pages — auto-launch Queen Browser window.
 */
(function () {
  "use strict";

  const BASE = window.HOSTESS7_PAGES_BASE || "";
  const QUEEN_URL = BASE + "/queen/browser.html";
  let launched = false;

  function tryLaunchQueen() {
    if (launched) return;
    const shell = window.NexusFieldShell;
    const data = window.__H7_DESKTOP_DOC__;
    if (!shell || !data) return;
    const bootId = data.shell?.boot_program || data.policy?.boot_program || "queen-browser";
    const prog = (data.programs || []).find(function (p) { return p.id === bootId; });
    const target = prog || {
      id: "queen-browser",
      name: "Queen Browser",
      exec: QUEEN_URL,
      icon_url: BASE + "/assets/ammoos-field-48.png",
      shell: true,
      fullscreen: true,
    };
    target.exec = QUEEN_URL;
    launched = true;
    setTimeout(function () {
      shell.launch(target, { newWindow: true });
      window.FieldHostDesktop?.toast?.("Queen Browser · Pages runtime");
    }, 180);
  }

  const origRefresh = window.FieldHostDesktop?.refresh;
  if (origRefresh) {
    window.FieldHostDesktop.refresh = async function () {
      await origRefresh.apply(this, arguments);
      try {
        const res = await fetch("/api/field-host-desktop");
        window.__H7_DESKTOP_DOC__ = await res.json();
      } catch (_e) {}
      tryLaunchQueen();
    };
  }

  document.addEventListener("DOMContentLoaded", function () {
    let n = 0;
    const t = setInterval(function () {
      n += 1;
      if (window.NexusFieldShell && window.__H7_DESKTOP_DOC__) {
        clearInterval(t);
        tryLaunchQueen();
      }
      if (n > 80) clearInterval(t);
    }, 150);
  });
})();