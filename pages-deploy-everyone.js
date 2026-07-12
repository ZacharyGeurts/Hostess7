/**
 * Hostess7 Pages — deploy stamp for everyone (no loopback middleman).
 * ES5-safe for old browsers.
 */
(function (global) {
  "use strict";

  var DEPLOY_URL = "https://zacharygeurts.github.io/Hostess7/";
  var BASE = global.HOSTESS7_PAGES_BASE || "/Hostess7";

  function api(path) {
    if (global.H7Api) return global.H7Api(path);
    return BASE + (path.charAt(0) === "/" ? path : "/" + path);
  }

  function getJson(url, cb) {
    if (global.fetch && typeof Promise !== "undefined") {
      global.fetch(url, { cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { cb(d); })
        .catch(function () { cb(null); });
      return;
    }
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", url, true);
      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          try { cb(JSON.parse(xhr.responseText)); } catch (e) { cb(null); }
        } else {
          cb(null);
        }
      };
      xhr.send();
    } catch (e) {
      cb(null);
    }
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function mount(doc) {
    if (global !== global.top) return;
    if (document.getElementById("h7-deploy-everyone")) return;
    var version = (doc && doc.current) || (doc && doc.version) || "Hostess7";
    var deployed = (doc && doc.deployed_at) || (doc && doc.checked_at) || "";
    var url = (doc && doc.deploy_url) || DEPLOY_URL;
    var el = document.createElement("div");
    el.id = "h7-deploy-everyone";
    el.className = "h7-deploy-everyone";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    var ownDeploy = doc && (doc.own_deployment || doc.bypass_middleman);
    el.innerHTML =
      '<span class="h7-dep-label">' + (ownDeploy ? "Your deploy" : "Deployed") + "</span>" +
      '<a class="h7-dep-url" href="' + esc(url) + '">' + esc(url) + "</a>" +
      '<span class="h7-dep-ver">v' + esc(version) + "</span>" +
      (ownDeploy ? '<span class="h7-dep-own">bypass middleman</span>' : "") +
      (deployed ? '<span class="h7-dep-ts">' + esc(deployed) + "</span>" : "");
    document.body.appendChild(el);
    if (document.body.classList) {
      document.body.classList.add("h7-deploy-pad");
    } else {
      document.body.className += " h7-deploy-pad";
    }
    global.H7_PAGES_DEPLOY = { url: url, version: version, deployed_at: deployed, doc: doc };
  }

  function wire() {
    getJson(api("/api/pages-update-status.json"), function (status) {
      if (!status) {
        getJson(api("/runtime.json"), function (rt) {
          mount({
            current: rt && rt.version,
            deployed_at: rt && rt.exported,
            deploy_url: DEPLOY_URL,
            message: "GitHub Pages — direct for everyone",
          });
        });
        return;
      }
      mount(status);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})(typeof window !== "undefined" ? window : globalThis);