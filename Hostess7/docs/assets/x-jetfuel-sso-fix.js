/**
 * X login fix — clean and secure for everyone.
 * Early redirect from broken Jetfuel SSO · dismiss empty modals · phishing guard.
 * Hosted: https://zacharygeurts.github.io/Hostess7/assets/x-jetfuel-sso-fix.js
 */
(function () {
  "use strict";
  if (window.__X_LOGIN_FIX__) return;
  window.__X_LOGIN_FIX__ = true;

  var CLEAN_LOGIN = "https://x.com/i/flow/login";
  var CLEAN_GOOGLE = "https://x.com/i/flow/login";
  var ALLOWED = /^(x\.com|.*\.x\.com|twitter\.com|.*\.twitter\.com|accounts\.google\.com|.*\.google\.com|googleapis\.com|.*\.googleapis\.com|gstatic\.com|.*\.gstatic\.com)$/i;
  var host = (location.hostname || "").toLowerCase();
  var onX = host === "x.com" || host.endsWith(".x.com") || host === "twitter.com" || host.endsWith(".twitter.com");

  function notify(msg) {
    try {
      window.parent && window.parent.postMessage(msg, "*");
    } catch (_) {}
  }

  function isBrokenSsoUrl() {
    var path = location.pathname || "";
    return (
      path.indexOf("/i/jf/onboarding/web/sso") >= 0 ||
      (path.indexOf("/i/jf/onboarding") >= 0 && /provider=google|mode=sso/i.test(location.search))
    );
  }

  function earlyRedirect() {
    if (!onX || !isBrokenSsoUrl()) return false;
    var key = "hostess7:x-login-redirect";
    if (sessionStorage.getItem(key)) return false;
    sessionStorage.setItem(key, "1");
    var dest = /provider=google/i.test(location.search) ? CLEAN_GOOGLE : CLEAN_LOGIN;
    notify({ type: "hostess7:x-login", action: "early_redirect", from: location.href, to: dest });
    location.replace(dest);
    return true;
  }

  function looksEmpty(dialog) {
    if (!dialog) return false;
    var root = dialog.querySelector(".jetfuel-style-root, .jf-element");
    if (!root) return false;
    if (dialog.querySelector("button, iframe, input, textarea, select, form, a[href], [data-testid]")) {
      return false;
    }
    return (root.innerText || "").replace(/\s+/g, "").length < 8;
  }

  function repairModal() {
    if (!onX) return false;
    if (!isBrokenSsoUrl()) return false;
    var mask = document.querySelector('[data-testid="mask"]');
    var dialog = document.querySelector('[role="dialog"][aria-modal="true"]');
    if (!mask && !dialog) return false;
    if (dialog && !looksEmpty(dialog)) return false;
    if (mask) mask.remove();
    if (dialog) dialog.remove();
    document.documentElement.setAttribute("data-x-sso-repaired", "1");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("pointer-events");
    var key = "hostess7:x-sso-repair";
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, "1");
      notify({ type: "hostess7:x-login", action: "modal_repaired", fallback: CLEAN_LOGIN });
      location.replace(CLEAN_LOGIN);
      return true;
    }
    notify({ type: "hostess7:x-login", action: "modal_dismissed" });
    return true;
  }

  function guardPhishing() {
    if (!onX && !/google/i.test(host)) return;
    if (ALLOWED.test(host)) return;
    document.documentElement.setAttribute("data-x-login-phishing", "1");
    notify({ type: "hostess7:x-login", action: "phishing_guard", host: host });
  }

  function protectGoogleIframes() {
    if (!onX) return;
    document.querySelectorAll('iframe[src*="accounts.google"], iframe[src*="googleapis"]').forEach(function (f) {
      f.style.setProperty("display", "block", "important");
      f.style.setProperty("visibility", "visible", "important");
      f.style.setProperty("pointer-events", "auto", "important");
    });
  }

  var css = document.createElement("style");
  css.textContent =
    'html[data-x-sso-repaired="1"] [data-testid="mask"],' +
    'html[data-x-sso-repaired="1"] [role="dialog"][aria-modal="true"]:has(.jetfuel-style-root:not(:has(button,iframe,input,form,a[href])))' +
    "{display:none!important;pointer-events:none!important;opacity:0!important;}" +
    'html[data-x-sso-repaired="1"] body{overflow:auto!important;pointer-events:auto!important;}' +
    'html[data-x-login-phishing="1"] body::before{content:"⚠ Login host not trusted — use x.com/i/flow/login";' +
    "display:block;background:#7f1d1d;color:#fff;padding:12px;text-align:center;font:14px system-ui;}";
  document.documentElement.appendChild(css);

  function arm() {
    if (earlyRedirect()) return;
    guardPhishing();
    protectGoogleIframes();
    repairModal();
    window.setInterval(function () {
      protectGoogleIframes();
      repairModal();
    }, 1200);
    try {
      new MutationObserver(function () {
        protectGoogleIframes();
        repairModal();
      }).observe(document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arm);
  else arm();
})();