(function () {
  "use strict";

  var H7_MANIFEST = "https://raw.githubusercontent.com/ZacharyGeurts/H7updater/main/data/h7updater-stack-index.json";
  var H7_PAGES = "https://zacharygeurts.github.io/H7updater/";

  function pagesBase() {
    return document.body?.dataset?.pagesRuntime === "1" || window.HOSTESS7_PAGES_BASE
      ? window.HOSTESS7_PAGES_BASE || "/Hostess7"
      : "";
  }

  function fixLinks() {
    var base = pagesBase();
    if (!base) return;
    ["aw-local-updater", "aw-desktop", "aw-ironclad", "aw-h7-pages"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var href = el.getAttribute("href") || "";
      if (href.startsWith("/")) el.setAttribute("href", base + href);
    });
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function renderStack(manifest) {
    var host = document.getElementById("aw-stack-tree");
    var status = document.getElementById("aw-stack-status");
    if (!host || !manifest) return;
    host.innerHTML = "";
    var tree = manifest.folder_tree || {};
    Object.keys(tree).sort().forEach(function (letter) {
      var bucket = document.createElement("div");
      bucket.className = "aw-bucket";
      bucket.textContent = "stack/" + letter + "/";
      host.appendChild(bucket);
      (tree[letter] || []).forEach(function (entry) {
        var row = document.createElement("div");
        row.className = "aw-entry";
        var tag = (entry.latest_release && entry.latest_release.tag) || "—";
        var links = entry.pages_url
          ? '<a href="' + esc(entry.pages_url) + '" target="_blank" rel="noopener">Pages</a> · '
          : "";
        links += '<a href="' + esc(entry.releases_url) + '" target="_blank" rel="noopener">Releases</a>';
        row.innerHTML =
          "<div><strong>" + esc(entry.name) + "</strong> "
          + '<span class="aw-meta">z=' + entry.layer_z + "</span></div>"
          + '<div class="aw-tag">' + esc(tag) + "</div>"
          + '<div class="aw-links">' + links + "</div>";
        host.appendChild(row);
      });
    });
    if (status) {
      status.textContent = "Sovereign catalog · " + (manifest.entries || []).length
        + " repos · " + (manifest.generated || "");
    }
  }

  function loadManifest() {
    var status = document.getElementById("aw-stack-status");
    fetch(H7_MANIFEST)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(renderStack)
      .catch(function (err) {
        if (status) status.textContent = "Manifest offline — open H7updater on GitHub (" + err.message + ")";
      });
  }

  function boot() {
    fixLinks();
    loadManifest();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();