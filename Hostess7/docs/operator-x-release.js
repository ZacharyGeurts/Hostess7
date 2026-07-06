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
    var excluded = (doc.excluded_suspects || [])
      .map(function (x) {
        return "<li><s>" + esc(x.actor) + "</s> — " + esc(x.excluded_reason) + "</li>";
      })
      .join("");
    el.innerHTML =
      "<p class=\"x-release-verdict\"><strong>Who censored @ZacharyGeurts:</strong> " +
      esc(doc.verdict_summary || doc.primary_actor) +
      "</p>" +
      "<p class=\"x-release-google\"><strong>Tracker blocks:</strong> " +
      esc(
        (doc.syndication_bypass_proof && doc.syndication_bypass_proof.conclusion) ||
          google.note ||
          "ruled out"
      ) +
      "</p>" +
      (excluded ? "<ul class=\"x-release-excluded\">" + excluded + "</ul>" : "") +
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
            ? ' <em class="x-withheld">' + p.withheld_replies +
              " replies hooked by X (count visible, bodies withheld — NOT tracker blocks)</em>"
            : "";
        var slots = "";
        if (p.withheld_reply_slots && p.withheld_reply_slots.length) {
          slots =
            '<ul class="x-withheld-slots">' +
            p.withheld_reply_slots
              .map(function (s) {
                return "<li>Slot " + esc(s.slot) + ": " + esc(s.note) + "</li>";
              })
              .join("") +
            "</ul>";
        }
        return (
          "<li class=\"x-post\"><a href=\"" +
          esc(p.url) +
          "\" target=\"_blank\" rel=\"noopener\">" +
          esc(p.created_at || p.id) +
          "</a><p>" +
          esc(p.text) +
          "</p>" +
          withheld +
          slots +
          "</li>"
        );
      })
      .join("");
    if (doc.impersonation_alerts && doc.impersonation_alerts.length && comments) {
      comments.innerHTML +=
        '<li class="x-impersonation-alert"><strong>Impersonation/plagiarism harassment flagged in recovered replies</strong></li>' +
        doc.impersonation_alerts
          .map(function (a) {
            return (
              '<li class="x-comment x-risk"><strong>' +
              esc(a.author_name || a.author) +
              "</strong><p>" +
              esc(a.text_excerpt) +
              "</p></li>"
            );
          })
          .join("");
    }
    if (doc.syndication_path && meta) {
      meta.textContent += " · syndication: direct HTTPS (bypasses adblock)";
    }
    if (comments) {
      comments.innerHTML = (doc.comments || [])
        .map(function (c) {
          var cls = c.kind === "reply_withheld_open" ? " x-comment x-withheld-open" : " x-comment";
          var badge = c.opened ? ' <span class="x-opened-badge">opened</span>' : "";
          return (
            "<li class=\"" + cls.trim() + "\"><strong>" +
            esc(c.author_name || c.author) +
            "</strong>" + badge + "<p>" +
            esc(c.text) +
            "</p></li>"
          );
        })
        .join("");
    }
    if (doc.cache_opened && meta) {
      meta.textContent += " · cache opened · delay killed";
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