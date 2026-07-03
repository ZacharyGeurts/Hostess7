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
  function renderExposure(doc) {
    var el = document.getElementById("x-release-exposure");
    if (!el || !doc) return;
    var suspects = (doc.suspects_ranked || [])
      .map(function (s) {
        return (
          "<li><strong>" +
          esc(s.actor) +
          "</strong> (" +
          esc(s.role) +
          ", " +
          Math.round((s.confidence || 0) * 100) +
          "%) — " +
          esc(s.reason) +
          "</li>"
        );
      })
      .join("");
    var google = doc.google_involvement || {};
    el.innerHTML =
      "<p class=\"x-release-verdict\"><strong>Who censored @ZacharyGeurts:</strong> " +
      esc(doc.verdict_summary || doc.primary_actor) +
      "</p>" +
      "<p class=\"x-release-google\"><strong>Google:</strong> " +
      esc(google.note || "no direct account censorship evidenced") +
      "</p>" +
      "<ol class=\"x-release-suspects\">" +
      suspects +
      "</ol>";
  }
  function renderComments(doc) {
    var meta = document.getElementById("x-release-meta");
    var posts = document.getElementById("x-release-posts");
    var comments = document.getElementById("x-release-comments");
    if (!posts || !doc) return;
    if (meta) {
      meta.textContent =
        (doc.profile && doc.profile.name ? doc.profile.name + " " : "") +
        "@" +
        (doc.profile && doc.profile.handle ? doc.profile.handle : "ZacharyGeurts") +
        " · " +
        (doc.post_count || 0) +
        " posts mirrored · " +
        (doc.comment_count || 0) +
        " replies recovered · " +
        (doc.release_status || "");
    }
    posts.innerHTML = (doc.posts || [])
      .map(function (p) {
        var withheld =
          p.withheld_replies > 0
            ? ' <em class="x-withheld">' + p.withheld_replies + " replies withheld by X</em>"
            : "";
        return (
          "<li class=\"x-post\"><a href=\"" +
          esc(p.url) +
          "\" target=\"_blank\" rel=\"noopener\">" +
          esc(p.created_at || p.id) +
          "</a><p>" +
          esc(p.text) +
          "</p>" +
          withheld +
          "</li>"
        );
      })
      .join("");
    if (comments) {
      comments.innerHTML = (doc.comments || [])
        .map(function (c) {
          return (
            "<li class=\"x-comment\"><strong>" +
            esc(c.author_name || c.author) +
            "</strong><p>" +
            esc(c.text) +
            "</p></li>"
          );
        })
        .join("");
    }
    if ((doc.censorship_notes || []).length && meta) {
      meta.textContent += " · " + doc.censorship_notes.join(" · ");
    }
  }
  Promise.all([
    fetchJson("/api/operator-x-comments.json"),
    fetchJson("/api/operator-censorship-exposure.json"),
  ])
    .then(function (rows) {
      renderComments(rows[0]);
      renderExposure(rows[1]);
    })
    .catch(function () {
      var meta = document.getElementById("x-release-meta");
      if (meta) meta.textContent = "Run publish-hostess7-pages to refresh operator-x-comments.json";
    });
})();