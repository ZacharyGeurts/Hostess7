/**
 * AmmoCode ZNetwork client — hook on open, shield capture/keylog, status pill.
 */
(function (global) {
  "use strict";

  const POLL_MS = 30000;
  let pollTimer = null;
  let lastStatus = null;

  function $(id) {
    return document.getElementById(id);
  }

  function apiBase() {
    return global.AmmoCodeG16?.cfg?.()?.apiBase || "/api/ammocode";
  }

  async function znetworkAction(action, body) {
    const r = await fetch(apiBase(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...body }),
    });
    return r.json();
  }

  function installCaptureGuard() {
    const deny = () => Promise.reject(
      new Error("AmmoCode shield: screen capture not permitted — use File → Screenshot…"),
    );
    const md = navigator.mediaDevices;
    if (!md) return;
    if (md.getDisplayMedia) {
      const orig = md.getDisplayMedia.bind(md);
      md.getDisplayMedia = function guarded(...args) {
        if (global.AmmoCodeScreenshot?.isSanctioned?.()) return orig(...args);
        if (global.AmmoCodeScreenShare?.isSanctioned?.()) return orig(...args);
        return deny();
      };
    }
    if (md.getUserMedia) {
      const origUm = md.getUserMedia.bind(md);
      md.getUserMedia = function guarded(constraints, ...rest) {
        const c = constraints || {};
        if (c.video && !global.AmmoCodeScreenshot?.isSanctioned?.()
            && !global.AmmoCodeScreenShare?.isSanctioned?.()) {
          return deny();
        }
        return origUm(constraints, ...rest);
      };
    }
  }

  function blockKeylogHooks() {
    const blocked = ["onkeydown", "onkeypress", "onkeyup"];
    blocked.forEach((evt) => {
      const desc = Object.getOwnPropertyDescriptor(Document.prototype, evt)
        || Object.getOwnPropertyDescriptor(HTMLElement.prototype, evt);
      if (!desc || !desc.set) return;
      const origSet = desc.set;
      Object.defineProperty(document, evt, {
        configurable: true,
        get: desc.get,
        set(v) {
          if (typeof v === "function" && !document.documentElement.dataset.acShieldOk) {
            console.warn("AmmoCode shield: document key handler blocked");
            return;
          }
          origSet.call(document, v);
        },
      });
    });
    document.documentElement.dataset.acShieldOk = "1";
  }

  function setPill(doc) {
    const pill = $("ac-znetwork-pill");
    const st = $("ac-st-znetwork");
    const z = doc?.znetwork || {};
    const running = !!(z.running ?? doc?.running);
    const hooked = !!(doc?.ammocode_hooked ?? doc?.hooked);
    if (pill) {
      if (running && hooked) {
        pill.textContent = "znet: hooked";
        pill.className = "pill ok";
        pill.title = "ZNetwork running — AmmoCode attached (no interference)";
      } else if (running) {
        pill.textContent = "znet: on";
        pill.className = "pill ok";
        pill.title = "ZNetwork running";
      } else if (hooked) {
        pill.textContent = "znet: hook";
        pill.className = "pill warn";
        pill.title = "AmmoCode shield active — ZNetwork pending";
      } else {
        pill.textContent = "znet: —";
        pill.className = "pill";
        pill.title = "ZNetwork status unknown";
      }
    }
    if (st) {
      st.textContent = running ? "znet secured" : hooked ? "shield on" : "znet —";
    }
  }

  async function refreshStatus() {
    try {
      const j = await znetworkAction("znetwork_status", {});
      if (j.ok !== undefined) {
        lastStatus = j;
        setPill(j);
      }
    } catch (_) {}
    return lastStatus;
  }

  async function hookOnOpen() {
    try {
      const j = await znetworkAction("znetwork_hook", {});
      lastStatus = j;
      setPill(j);
      if (j.message) global.AmmoCodeEditor?.toast?.(j.message, j.ok !== false);
      else if (j.action === "attach_only") {
        global.AmmoCodeEditor?.toast?.("ZNetwork attached — already running", true);
      } else if (j.hooked) {
        global.AmmoCodeEditor?.toast?.("ZNetwork hooked — secured through stack", true);
      }
      return j;
    } catch (e) {
      global.AmmoCodeEditor?.toast?.("ZNetwork hook unavailable", false);
      return { ok: false, error: String(e.message || e) };
    }
  }

  function renderFlyout(el) {
    if (!el) return;
    const z = lastStatus?.znetwork || {};
    const cap = lastStatus?.capture_policy || {};
    el.innerHTML = [
      '<div class="ac-side-head">ZNetwork shield</div>',
      '<div class="ac-flyout-body">',
      `<p class="ac-flyout-desc">NewLatest ZNetwork — hook all the way down when AmmoCode opens. `
        + `If ZNetwork is already running, we <strong>attach only</strong> (no interference).</p>`,
      `<div class="ac-znet-line">Running: <strong>${z.running ? "yes" : "no"}</strong></div>`,
      `<div class="ac-znet-line">AmmoCode hooked: <strong>${lastStatus?.ammocode_hooked ? "yes" : "no"}</strong></div>`,
      `<div class="ac-znet-line">Capture: <strong>${cap.screen_capture || "deny"}</strong> — ${cap.message || ""}</div>`,
      `<div class="ac-znet-line">Screenshot: <strong>${cap.sanctioned_screenshot || "gui only"}</strong></div>`,
      '<button type="button" id="ac-znet-refresh">Refresh status</button>',
      '<button type="button" id="ac-znet-rehook">Re-hook (safe)</button>',
      "</div>",
    ].join("");
    el.querySelector("#ac-znet-refresh")?.addEventListener("click", () => refreshStatus());
    el.querySelector("#ac-znet-rehook")?.addEventListener("click", () => hookOnOpen());
  }

  async function init() {
    installCaptureGuard();
    blockKeylogHooks();
    await hookOnOpen();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(refreshStatus, POLL_MS);
  }

  global.AmmoCodeZNetwork = {
    init,
    hookOnOpen,
    refreshStatus,
    renderFlyout,
    lastStatus: () => lastStatus,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);