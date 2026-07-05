/**
 * X login overlay killer — clean secure login for everyone.
 * Kills mask/div bullshit on x.com/onboarding/* and /i/jf/onboarding/*.
 */
(function () {
  "use strict";
  if (window.__X_LOGIN_FIX__) return;
  window.__X_LOGIN_FIX__ = true;

  var CLEAN_LOGIN = "https://x.com/i/flow/login";
  var host = (location.hostname || "").toLowerCase();
  var onX = /(^|\.)x\.com$|(^|\.)twitter\.com$/.test(host);

  function notify(msg) {
    try { window.parent && window.parent.postMessage(msg, "*"); } catch (_) {}
  }

  function isLoginSurface() {
    var path = (location.pathname || "").toLowerCase();
    return (
      /\/onboarding\/web\/sso/i.test(path) ||
      /\/i\/jf\/onboarding/i.test(path) ||
      /\/i\/onboarding/i.test(path) ||
      /\/i\/flow\/login/i.test(path) ||
      (/onboarding/i.test(path) && /mode=sso|provider=google/i.test(location.search))
    );
  }

  function loginFormVisible() {
    var body = (document.body && document.body.innerText) || "";
    return /continue with (google|apple|phone)|email or username|sign up/i.test(body);
  }

  function restorePage() {
    document.documentElement.setAttribute("data-x-login-killed", "1");
    document.body && document.body.style.setProperty("overflow", "auto", "important");
    document.body && document.body.style.setProperty("pointer-events", "auto", "important");
    document.documentElement.style.removeProperty("overflow");
  }

  function killNode(el) {
    if (!el || !el.parentNode) return;
    el.setAttribute("data-x-overlay-killed", "1");
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("pointer-events", "none", "important");
    el.style.setProperty("opacity", "0", "important");
    el.style.setProperty("visibility", "hidden", "important");
    try { el.remove(); } catch (_) {}
  }

  function killMasksAndDialogs() {
    var killed = 0;
    document.querySelectorAll('[data-testid="mask"]').forEach(function (m) {
      killNode(m);
      killed++;
    });
    document.querySelectorAll('[role="dialog"][aria-modal="true"]').forEach(function (dlg) {
      var hasLogin = dlg.querySelector("button, input, iframe, form, a[href]");
      var isJetfuel = dlg.querySelector(".jetfuel-style-root, .jf-element");
      var text = (dlg.innerText || "").replace(/\s+/g, "");
      var empty = text.length < 12 && !hasLogin;
      if (empty || (isJetfuel && !hasLogin) || (loginFormVisible() && !dlg.querySelector("button"))) {
        killNode(dlg);
        killed++;
      }
    });
    return killed;
  }

  function killFixedOverlays() {
    var killed = 0;
    var vw = window.innerWidth || 800;
    var vh = window.innerHeight || 600;
    document.querySelectorAll("div, section").forEach(function (el) {
      if (el.getAttribute("data-x-overlay-killed")) return;
      if (el.closest("button, input, form, main, [role='main']")) return;
      var st = window.getComputedStyle(el);
      if (st.position !== "fixed" && st.position !== "absolute") return;
      var r = el.getBoundingClientRect();
      if (r.width < vw * 0.35 || r.height < vh * 0.35) return;
      var bg = st.backgroundColor || "";
      var dark = /rgba?\(\s*0\s*,\s*0\s*,\s*0|rgb\(\s*0\s*,\s*0\s*,\s*0/i.test(bg);
      var opaque = parseFloat(st.opacity || "1") > 0.3;
      var blocks = st.pointerEvents !== "none" || dark;
      var noInteract = !el.querySelector("button, input, iframe, a[href], form");
      var jetfuel = el.classList.contains("jf-element") || el.querySelector(".jf-element, .jetfuel-style-root");
      if (blocks && opaque && noInteract && (dark || jetfuel) && isLoginSurface()) {
        killNode(el);
        killed++;
      }
    });
    return killed;
  }

  function protectGoogleIframes() {
    document.querySelectorAll('iframe[src*="accounts.google"], iframe[src*="googleapis"], iframe[src*="gstatic"]').forEach(function (f) {
      f.style.setProperty("display", "block", "important");
      f.style.setProperty("visibility", "visible", "important");
      f.style.setProperty("pointer-events", "auto", "important");
      f.style.setProperty("z-index", "2147483646", "important");
    });
  }

  function killAll() {
    if (!onX || !isLoginSurface()) return 0;
    var n = killMasksAndDialogs() + killFixedOverlays();
    if (n > 0) {
      restorePage();
      notify({ type: "hostess7:x-login", action: "overlay_killed", count: n, path: location.pathname });
    }
    protectGoogleIframes();
    if (loginFormVisible()) return n;
    if (/\/onboarding\/web\/sso|\/i\/jf\/onboarding\/web\/sso/i.test(location.pathname)) {
      var key = "hostess7:x-login-fallback";
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, "1");
        notify({ type: "hostess7:x-login", action: "fallback_redirect", to: CLEAN_LOGIN });
        location.replace(CLEAN_LOGIN);
      }
    }
    return n;
  }

  var css = document.createElement("style");
  css.id = "hostess7-x-login-kill-css";
  css.textContent =
    "html[data-x-login-killed='1'] [data-testid='mask']," +
    "html[data-x-login-killed='1'] [role='dialog'][aria-modal='true']:not(:has(button,input,iframe))," +
    "html[data-x-login-killed='1'] .jetfuel-style-root:empty," +
    "html[data-x-login-killed='1'] [data-x-overlay-killed='1']" +
    "{display:none!important;pointer-events:none!important;opacity:0!important;visibility:hidden!important;}" +
    "html[data-x-login-killed='1'] body{overflow:auto!important;pointer-events:auto!important;}" +
    "iframe[src*='accounts.google'],iframe[src*='googleapis']{display:block!important;visibility:visible!important;}";
  (document.documentElement || document.head).appendChild(css);

  function arm() {
    killAll();
    var iv = window.setInterval(killAll, 400);
    try {
      new MutationObserver(killAll).observe(document.documentElement, { childList: true, subtree: true, attributes: true });
    } catch (_) {}
    window.addEventListener("load", killAll);
    setTimeout(function () { window.clearInterval(iv); window.setInterval(killAll, 800); }, 15000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arm);
  else arm();
})();