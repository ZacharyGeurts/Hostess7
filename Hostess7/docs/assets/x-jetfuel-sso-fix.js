/**
 * X Jetfuel SSO fix — dismiss stuck empty modal divs on x.com.
 * Hosted: https://zacharygeurts.github.io/Hostess7/assets/x-jetfuel-sso-fix.js
 */
(function () {
  "use strict";
  if (window.__X_JF_SSO_FIX__) return;
  window.__X_JF_SSO_FIX__ = true;

  var host = (location.hostname || "").toLowerCase();
  var onX = host === "x.com" || host.endsWith(".x.com") || host === "twitter.com";

  function notify(msg) {
    try {
      window.parent && window.parent.postMessage(msg, "*");
    } catch (_) {}
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

  function repair() {
    if (!onX) return false;
    var path = location.pathname || "";
    var onSso =
      path.indexOf("/i/jf/onboarding/web/sso") >= 0 ||
      (path.indexOf("/i/jf/onboarding") >= 0 && location.search.indexOf("provider=google") >= 0);
    if (!onSso) return false;
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
      notify({ type: "hostess7:x-sso", action: "repaired", fallback: "/i/flow/login" });
      location.replace("/i/flow/login");
      return true;
    }
    notify({ type: "hostess7:x-sso", action: "dismissed_empty_modal" });
    return true;
  }

  var css = document.createElement("style");
  css.textContent =
    'html[data-x-sso-repaired="1"] [data-testid="mask"],' +
    'html[data-x-sso-repaired="1"] [role="dialog"][aria-modal="true"]:has(.jetfuel-style-root:not(:has(button,iframe,input,form,a[href])))' +
    "{display:none!important;pointer-events:none!important;opacity:0!important;}" +
    'html[data-x-sso-repaired="1"] body{overflow:auto!important;pointer-events:auto!important;}';
  document.documentElement.appendChild(css);

  function arm() {
    repair();
    window.setInterval(repair, 1200);
    try {
      new MutationObserver(repair).observe(document.documentElement, { childList: true, subtree: true });
    } catch (_) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arm);
  else arm();
})();