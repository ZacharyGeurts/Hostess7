/* X Producer — hardened profile timeline + intruder flatten (Hostess7) */
(function () {
  "use strict";
  var HANDLE = "ZacharyGeurts";
  var PRODUCER = "https://zacharygeurts.github.io/Hostess7/x-producer/";
  var MIRROR = "https://zacharygeurts.github.io/Hostess7/x-profile/";
  var API_SOURCES = [
    "https://zacharygeurts.github.io/Hostess7/api/hostess7-x-profile-fix.json",
    "http://127.0.0.1:9477/api/hostess7-x-profile-fix",
    "http://127.0.0.1:9477/api/hostess7/x-profile-fix",
  ];
  var host = (location.hostname || "").toLowerCase();
  if (!/^(x|twitter)\.com$/.test(host)) return;

  var path = (location.pathname || "").replace(/\/$/, "") || "/";
  var isProfile = new RegExp("^/" + HANDLE + "$", "i").test(path);
  var cache = null;
  var fetching = false;

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function flattenIntruders() {
    var killed = 0;
    document.querySelectorAll('[data-testid="mask"]').forEach(function (el) {
      el.style.setProperty("display", "none", "important");
      el.style.setProperty("pointer-events", "none", "important");
      try { el.remove(); } catch (_) {}
      killed++;
    });
    document.querySelectorAll('[role="dialog"][aria-modal="true"]').forEach(function (dlg) {
      var hasLogin = dlg.querySelector("button, input, iframe, form, a[href]");
      var empty = (dlg.innerText || "").replace(/\s+/g, "").length < 12 && !hasLogin;
      if (empty) {
        dlg.style.setProperty("display", "none", "important");
        try { dlg.remove(); } catch (_) {}
        killed++;
      }
    });
    document.querySelectorAll(".jetfuel-style-root:empty, .jf-element:empty").forEach(function (el) {
      try { el.remove(); } catch (_) {}
      killed++;
    });
    if (killed) document.documentElement.setAttribute("data-x-producer-flat", "1");
    return killed;
  }

  function detectProfileLie() {
    if (!isProfile) return false;
    var body = document.body ? document.body.innerText || "" : "";
    return /hasn.t posted/i.test(body) || /when they do/i.test(body);
  }

  function removeLieNodes() {
    var removed = 0;
    document.querySelectorAll("h1,h2,h3,div,span,p").forEach(function (el) {
      if (el.id === "h7-x-producer-banner" || el.id === "h7-x-producer-feed") return;
      var t = (el.innerText || "").trim();
      if (/hasn.t posted/i.test(t) && t.length < 80) {
        var box = el.closest("section,article,div[data-testid]") || el;
        box.style.setProperty("display", "none", "important");
        removed++;
      }
    });
    return removed;
  }

  function fetchFeed(cb) {
    if (cache) { cb(cache); return; }
    if (fetching) return;
    fetching = true;
    var i = 0;
    function next() {
      if (i >= API_SOURCES.length) { fetching = false; cb(null); return; }
      var url = API_SOURCES[i++];
      fetch(url, { cache: "no-store", credentials: "omit", mode: "cors" })
        .then(function (r) { if (!r.ok) throw new Error("http"); return r.json(); })
        .then(function (d) { cache = d; fetching = false; cb(d); })
        .catch(next);
    }
    next();
  }

  function producerBanner(doc) {
    if (document.getElementById("h7-x-producer-banner")) return;
    var n = (doc && doc.censorship && doc.censorship.tweet_count_truth) || (doc && doc.post_count) || "6855+";
    var el = document.createElement("div");
    el.id = "h7-x-producer-banner";
    el.setAttribute("role", "alert");
    el.style.cssText =
      "position:fixed;top:0;left:0;right:0;z-index:2147483647;background:linear-gradient(90deg,#000,#14532d);" +
      "color:#fff;padding:10px 16px;font:600 13px/1.4 system-ui,sans-serif;border-bottom:2px solid #1d9bf0;" +
      "display:flex;flex-wrap:wrap;align-items:center;gap:8px;box-shadow:0 4px 24px rgba(0,0,0,.5);";
    el.innerHTML =
      '<span style="color:#1d9bf0">𝕏 Producer</span> ' +
      '<span>X hid ' + n + ' posts — timeline restored below.</span>' +
      '<a href="' + PRODUCER + '" style="color:#7dd3fc;margin-left:auto">Open Producer →</a>' +
      '<a href="' + MIRROR + '" style="color:#86efac">Mirror</a>';
    document.documentElement.appendChild(el);
    document.documentElement.setAttribute("data-x-producer", "1");
  }

  function injectFeed(doc) {
    if (!doc || !doc.posts || !doc.posts.length) return;
    flattenIntruders();
    removeLieNodes();
    var target =
      document.querySelector('[data-testid="primaryColumn"]') ||
      document.querySelector('[data-testid="emptyState"]')?.parentElement ||
      document.querySelector("main") ||
      document.body;
    if (!target) return;
    var box = document.getElementById("h7-x-producer-feed");
    if (!box) {
      box = document.createElement("section");
      box.id = "h7-x-producer-feed";
      box.style.cssText =
        "margin:56px 0 24px;padding:0 16px 24px;color:#e7e9ea;font-family:system-ui,sans-serif;";
      target.insertBefore(box, target.firstChild);
    }
    var html =
      '<div style="border:1px solid #2f3336;border-radius:16px;overflow:hidden;background:#000">' +
      '<div style="padding:12px 16px;border-bottom:1px solid #2f3336;font-weight:700;color:#1d9bf0">' +
      "Posts @ZacharyGeurts — Producer restore (" + doc.posts.length + ")</div>";
    doc.posts.slice(0, 30).forEach(function (p) {
      html +=
        '<article style="padding:12px 16px;border-bottom:1px solid #2f3336">' +
        '<div style="font-weight:700;color:#e7e9ea">BIG GRIN <span style="color:#71767b;font-weight:400">@' + HANDLE + "</span></div>" +
        '<div style="margin:8px 0;white-space:pre-wrap;word-break:break-word">' + esc(p.text) + "</div>" +
        '<a href="' + esc(p.url) + '" style="color:#1d9bf0;font-size:13px" target="_blank" rel="noopener">View on X →</a>' +
        "</article>";
    });
    html +=
      '<div style="padding:12px 16px;text-align:center">' +
      '<a href="' + PRODUCER + '" style="color:#1d9bf0;font-weight:700">𝕏 Producer — full feed + Grok beta →</a></div></div>';
    box.innerHTML = html;
  }

  function run() {
    flattenIntruders();
    if (!isProfile) return;
    if (!detectProfileLie() && !document.getElementById("h7-x-producer-feed")) {
      fetchFeed(function (d) {
        if (d && d.posts && d.posts.length && detectProfileLie()) run();
      });
      return;
    }
    removeLieNodes();
    fetchFeed(function (d) {
      producerBanner(d);
      injectFeed(d);
    });
  }

  run();
  setInterval(run, 800);
  var obs = new MutationObserver(run);
  if (document.documentElement) obs.observe(document.documentElement, { childList: true, subtree: true });
})();