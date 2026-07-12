(function () {
  "use strict";

  const API = "/api/field-irc";
  const ROOMS = ["fleet-2500", "mesh-global", "sovereign", "iron-warning"];

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  async function api(body) {
    const res = await fetch(API, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  function append(box, role, text) {
    const line = document.createElement("div");
    line.className = "fic-msg fic-msg--" + role;
    line.textContent = text;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
  }

  function mount(root) {
    root.innerHTML =
      '<div class="fic-shell">' +
      '<header class="fic-head"><strong>Chat Terminal</strong>' +
      '<span class="fic-badge" id="fic-badge">Field IRC</span></header>' +
      '<div class="fic-toolbar">' +
      '<select id="fic-room" aria-label="Room">' +
      ROOMS.map(function (r) { return '<option value="' + r + '">' + r + "</option>"; }).join("") +
      "</select>" +
      '<input id="fic-input" type="text" placeholder="Global chat…" spellcheck="false" autocomplete="off" />' +
      '<button type="button" id="fic-send">Send</button>' +
      "</div>" +
      '<p class="fic-hint">H7 Noti fair ban · Ironclad · birth bind</p>' +
      '<div class="fic-log" id="fic-log" role="log"></div>' +
      "</div>";

    const log = root.querySelector("#fic-log");
    const room = root.querySelector("#fic-room");
    const input = root.querySelector("#fic-input");
    const badge = root.querySelector("#fic-badge");

    async function refresh() {
      const j = await api({ action: "read", room_id: room.value });
      if (j.counts) badge.textContent = "rooms " + (j.counts.rooms || "—");
      log.innerHTML = "";
      (j.messages || []).forEach(function (m) {
        append(log, "peer", "[" + (m.from || "?") + "] " + (m.text || ""));
      });
    }

    async function send() {
      const text = (input.value || "").trim();
      if (!text) return;
      append(log, "you", "[" + room.value + "] " + text);
      input.value = "";
      const j = await api({ action: "post", room_id: room.value, text: text, person: "operator" });
      if (!j.ok) append(log, j.iron_warning ? "warn" : "system", j.error || j.detail || "blocked");
      await refresh();
    }

    root.querySelector("#fic-send").addEventListener("click", function () { void send(); });
    input.addEventListener("keydown", function (ev) { if (ev.key === "Enter") void send(); });
    room.addEventListener("change", function () { void refresh(); });
    void api({ action: "seed" }).then(refresh).catch(refresh);
  }

  globalThis.FieldIrcChat = { mount: mount };
})();