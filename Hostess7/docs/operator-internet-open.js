(function () {
  "use strict";
  var base = (window.HOSTESS7_PAGES_BASE || "").replace(/\/$/, "");
  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function fetchJson(path) {
    return fetch(base + path, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("http " + r.status);
      return r.json();
    });
  }
  function renderWhole(doc) {
    var el = document.getElementById("whole-internet-status");
    if (!el || !doc) return;
    var lanes = doc.lane_summaries || {};
    var keys = Object.keys(lanes);
    el.innerHTML =
      "<p><strong>Good guys whole internet</strong> · " +
      esc(doc.lanes_ok || 0) +
      "/" +
      esc(doc.lanes_total || keys.length) +
      " lanes · " +
      (doc.delay_killed ? "delay killed" : "") +
      "</p>" +
      "<ul class=\"internet-open-lanes\">" +
      keys
        .map(function (k) {
          var row = lanes[k] || {};
          return (
            "<li>" +
            esc(k) +
            ": " +
            (row.ok ? "✓" : "…") +
            "</li>"
          );
        })
        .join("") +
      "</ul>" +
      "<p class=\"internet-open-note\">" +
      esc(doc.motto || "Free open internet — that's us good guys :D") +
      "</p>";
  }
  function renderGoogle(doc) {
    var el = document.getElementById("internet-open-google");
    if (!el || !doc) return;
    var g = doc.google || doc;
    el.innerHTML =
      "<p><strong>Google core:</strong> " +
      esc(g.verdict || (g.core_open ? "open" : "probe")) +
      (g.delay_killed ? " · delay killed" : "") +
      "</p>" +
      "<p class=\"internet-open-note\">" +
      esc(
        "Local blocks hit ad-tech only — never google.com search or YouTube media."
      ) +
      "</p>";
  }
  function renderYoutube(doc) {
    var meta = document.getElementById("internet-open-meta");
    var videos = document.getElementById("internet-open-videos");
    var comments = document.getElementById("internet-open-comments");
    if (!doc) return;
    var yt = doc.youtube || {};
    if (meta) {
      meta.textContent =
        "Whole internet · good guys · @" +
        esc(doc.operator || "ZacharyGeurts") +
        " · " +
        (yt.video_count || 0) +
        " videos · " +
        (doc.comment_count || 0) +
        " comments · " +
        (doc.release_status || "") +
        (doc.cache_opened ? " · cache opened" : "");
    }
    if (videos) {
      videos.innerHTML = (yt.videos || [])
        .map(function (v) {
          var withheld =
            (v.withheld_comment_slots || []).length > 0
              ? ' <em class="x-withheld">' + v.withheld_comment_slots.length + " withheld slots opened</em>"
              : "";
          return (
            "<li class=\"x-post\"><a href=\"" +
            esc(v.url) +
            "\" target=\"_blank\" rel=\"noopener\">" +
            esc(v.video_id) +
            "</a> · " +
            (v.comment_count || 0) +
            " comments" +
            withheld +
            "</li>"
          );
        })
        .join("");
    }
    if (comments) {
      comments.innerHTML = (doc.comments || [])
        .map(function (c) {
          var cls =
            c.kind && c.kind.indexOf("withheld") >= 0 ? " x-comment x-withheld-open" : " x-comment";
          return (
            "<li class=\"" + cls.trim() + "\"><strong>" +
            esc(c.author_name || c.author) +
            "</strong><p>" +
            esc(c.text) +
            "</p></li>"
          );
        })
        .join("");
    }
  }
  Promise.all([
    fetchJson("/api/operator-whole-internet.json").catch(function () {
      return null;
    }),
    fetchJson("/api/operator-google-youtube-open.json"),
    fetchJson("/api/operator-x-comments.json"),
  ])
    .then(function (rows) {
      if (rows[0]) renderWhole(rows[0]);
      renderGoogle(rows[1]);
      renderYoutube(rows[1]);
    })
    .catch(function () {
      var meta = document.getElementById("internet-open-meta");
      if (meta) meta.textContent = "Run Hostess7.sh whole-internet — good guys :D";
    });
})();