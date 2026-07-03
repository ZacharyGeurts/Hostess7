/**
 * GitHub Pages — All Rights Reserved license strip on every surface.
 */
(function (global) {
  "use strict";

  var DOC = {
    schema: "hostess7-pages-license/v1",
    owner: "Zachary Robert Geurts",
    years: "2025–2026",
    rights: "All Rights Reserved",
    posture: "War-ready operational",
    notice:
      "No permission without written license. Unauthorized use prohibited.",
    license_url: "https://github.com/ZacharyGeurts/Hostess7/blob/main/LICENSE",
    contact: "gzac5314@gmail.com",
  };

  function skip() {
    if (global !== global.top) return false;
    var b = document.body;
    if (!b) return true;
    if (b.dataset && b.dataset.noLicenseStrip === "1") return true;
    return false;
  }

  function mount() {
    if (skip() || document.getElementById("h7-license-strip")) return;

    if (!document.getElementById("h7-license-style")) {
      var link = document.createElement("link");
      link.id = "h7-license-style";
      link.rel = "stylesheet";
      var base = global.HOSTESS7_PAGES_BASE || "";
      link.href = (base || "") + "/pages-license.css";
      document.head.appendChild(link);
    }

    var foot = document.createElement("footer");
    foot.id = "h7-license-strip";
    foot.className = "h7-license-strip";
    foot.setAttribute("role", "contentinfo");
    foot.innerHTML =
      "<strong>© " +
      DOC.years +
      " " +
      DOC.owner +
      "</strong>" +
      '<span class="h7-lic-rose">' +
      DOC.rights +
      "</span>" +
      "<span>" +
      DOC.posture +
      " · " +
      DOC.notice +
      "</span>" +
      '<a href="' +
      DOC.license_url +
      '" target="_blank" rel="noopener">License</a>' +
      '<a href="mailto:' +
      DOC.contact +
      '">Contact</a>';

    document.body.appendChild(foot);
    document.body.classList.add("h7-license-pad");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  global.Hostess7PagesLicense = DOC;
})(typeof window !== "undefined" ? window : globalThis);