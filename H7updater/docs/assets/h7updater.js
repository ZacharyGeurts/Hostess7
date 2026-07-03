(function () {
  "use strict";

  var MANIFEST_URL = "../data/h7updater-stack-index.json";
  var OAUTH_URL = "../data/h7updater-oauth-doctrine.json";
  var API = "https://api.github.com";
  var TOKEN_KEY = "h7updater_github_token";
  var CLIENT_ID_KEY = "h7updater_oauth_client_id";

  var state = {
    manifest: null,
    oauth: null,
    lane: "sovereign",
    token: null,
    user: null,
    personalRepos: null,
  };

  function $(id) { return document.getElementById(id); }

  function ghHeaders() {
    var h = { Accept: "application/vnd.github+json" };
    if (state.token) h.Authorization = "Bearer " + state.token;
    return h;
  }

  function fetchJson(url, opts) {
    opts = opts || {};
    return fetch(url, Object.assign({ headers: ghHeaders() }, opts))
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + " " + url);
        return r.json();
      });
  }

  function loadDoctrine() {
    return Promise.all([
      fetch(MANIFEST_URL).then(function (r) { return r.json(); }),
      fetch(OAUTH_URL).then(function (r) { return r.json(); }),
    ]).then(function (pair) {
      state.manifest = pair[0];
      state.oauth = pair[1];
      state.token = sessionStorage.getItem(TOKEN_KEY);
      renderManifest();
      bindLanes();
      if (state.token) refreshPersonalUser();
    }).catch(function (err) {
      setStatus("Failed to load manifest: " + err.message);
    });
  }

  function setStatus(msg) {
    var el = $("h7-status");
    if (el) el.textContent = msg;
  }

  function clientId() {
    return sessionStorage.getItem(CLIENT_ID_KEY)
      || (state.oauth && state.oauth.lanes.personal.oauth_app.client_id_placeholder)
      || "";
  }

  function bindLanes() {
    document.querySelectorAll("[data-lane]").forEach(function (el) {
      el.addEventListener("click", function () {
        var lane = el.getAttribute("data-lane");
        state.lane = lane;
        document.querySelectorAll("[data-lane]").forEach(function (n) {
          n.classList.toggle("active", n.getAttribute("data-lane") === lane);
        });
        $("h7-personal-panel").hidden = lane !== "personal";
        $("h7-sovereign-panel").hidden = lane !== "sovereign";
        if (lane === "personal" && state.token) loadPersonalRepos();
      });
    });
    var authBtn = $("h7-auth-btn");
    if (authBtn) authBtn.addEventListener("click", startDeviceFlow);
    var disconnect = $("h7-disconnect-btn");
    if (disconnect) disconnect.addEventListener("click", disconnectGitHub);
    var saveCid = $("h7-save-client-id");
    if (saveCid) saveCid.addEventListener("click", saveClientId);
  }

  function saveClientId() {
    var inp = $("h7-client-id");
    if (!inp || !inp.value.trim()) return;
    sessionStorage.setItem(CLIENT_ID_KEY, inp.value.trim());
    setStatus("OAuth client ID saved for this session.");
  }

  function renderManifest() {
    var m = state.manifest;
    if (!m) return;
    var tree = $("h7-folder-tree");
    if (!tree) return;
    tree.innerHTML = "";
    Object.keys(m.folder_tree || {}).forEach(function (letter) {
      var bucket = document.createElement("div");
      bucket.className = "h7-bucket";
      bucket.textContent = "stack/" + letter + "/";
      tree.appendChild(bucket);
      (m.folder_tree[letter] || []).forEach(function (entry) {
        var row = document.createElement("div");
        row.className = "h7-entry";
        var tag = (entry.latest_release && entry.latest_release.tag) || "—";
        row.innerHTML =
          "<div><strong>" + entry.name + "</strong> "
          + "<span class=\"meta\">z=" + entry.layer_z + " · " + entry.role + "</span></div>"
          + "<div class=\"tag\">" + tag + "</div>";
        tree.appendChild(row);
      });
    });
    setStatus("Sovereign catalog · " + (m.entries || []).length + " repos · generated " + (m.generated || ""));
  }

  function startDeviceFlow() {
    var cid = clientId();
    if (!cid || cid.indexOf("PLACEHOLDER") >= 0) {
      setStatus("Set your GitHub OAuth App client ID first (read-only device flow).");
      return;
    }
    setStatus("Requesting device code…");
    fetch("https://github.com/login/device/code", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: cid,
        scope: "read:user repo:read",
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) throw new Error(data.error_description || data.error);
        var box = $("h7-device-code");
        if (box) {
          box.hidden = false;
          box.innerHTML =
            "<p>1. Open <a href=\"" + data.verification_uri + "\" target=\"_blank\" rel=\"noopener\">"
            + data.verification_uri + "</a></p>"
            + "<p>2. Enter code: <code>" + data.user_code + "</code></p>"
            + "<p class=\"meta\">Read-only — cannot push to ZacharyGeurts repos.</p>";
        }
        pollDeviceToken(cid, data.device_code, data.interval || 5);
      })
      .catch(function (err) { setStatus("Device flow failed: " + err.message); });
  }

  function pollDeviceToken(cid, deviceCode, interval) {
    function tick() {
      fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: cid,
          device_code: deviceCode,
          grant_type: "urn:ietf:params:oauth:grant-type:device_code",
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error === "authorization_pending") {
            setTimeout(tick, (interval || 5) * 1000);
            return;
          }
          if (data.error) throw new Error(data.error_description || data.error);
          state.token = data.access_token;
          sessionStorage.setItem(TOKEN_KEY, state.token);
          setStatus("GitHub connected (read-only).");
          refreshPersonalUser();
          loadPersonalRepos();
        })
        .catch(function (err) { setStatus("Auth: " + err.message); });
    }
    tick();
  }

  function refreshPersonalUser() {
    fetchJson(API + "/user").then(function (u) {
      state.user = u;
      var el = $("h7-user-line");
      if (el) el.textContent = "Signed in as @" + u.login + " — your repos only.";
      $("h7-auth-btn").hidden = true;
      $("h7-disconnect-btn").hidden = false;
    }).catch(function () {
      disconnectGitHub();
    });
  }

  function disconnectGitHub() {
    state.token = null;
    state.user = null;
    state.personalRepos = null;
    sessionStorage.removeItem(TOKEN_KEY);
    $("h7-auth-btn").hidden = false;
    $("h7-disconnect-btn").hidden = true;
    var el = $("h7-user-line");
    if (el) el.textContent = "";
    var box = $("h7-device-code");
    if (box) { box.hidden = true; box.innerHTML = ""; }
    var tree = $("h7-personal-tree");
    if (tree) tree.innerHTML = "";
    setStatus("Disconnected.");
  }

  function loadPersonalRepos() {
    if (!state.token) return;
    setStatus("Loading your repos…");
    fetchJson(API + "/user/repos?per_page=100&sort=updated&type=owner")
      .then(function (repos) {
        state.personalRepos = repos;
        var tree = $("h7-personal-tree");
        if (!tree) return;
        tree.innerHTML = "";
        var buckets = {};
        repos.forEach(function (r) {
          var L = (r.name[0] || "#").toUpperCase();
          if (!/[A-Z]/.test(L)) L = "#";
          (buckets[L] = buckets[L] || []).push(r);
        });
        Object.keys(buckets).sort().forEach(function (letter) {
          var b = document.createElement("div");
          b.className = "h7-bucket";
          b.textContent = "your-stack/" + letter + "/";
          tree.appendChild(b);
          buckets[letter].sort(function (a, b2) {
            return a.name.localeCompare(b2.name);
          }).forEach(function (r) {
            var row = document.createElement("div");
            row.className = "h7-entry";
            row.innerHTML =
              "<div><a href=\"" + r.html_url + "\" target=\"_blank\" rel=\"noopener\">"
              + r.name + "</a> <span class=\"meta\">" + (r.description || "") + "</span></div>"
              + "<div class=\"tag\">" + (r.default_branch || "main") + "</div>";
            tree.appendChild(row);
          });
        });
        setStatus("Personal lane · " + repos.length + " repos (read-only).");
      })
      .catch(function (err) { setStatus("Repos: " + err.message); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadDoctrine);
  } else {
    loadDoctrine();
  }
})();