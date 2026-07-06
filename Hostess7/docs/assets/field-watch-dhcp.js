(function () {
  var API = "/api/field-watch-dhcp";
  var tick = 0;
  var grid = document.getElementById("fwd-grid");
  var offers = document.getElementById("fwd-offers");
  var banner = document.getElementById("fwd-banner");
  var updated = document.getElementById("fwd-updated");
  var mode = document.getElementById("fwd-mode");

  function card(label, val) {
    return '<div class="fwd-card"><div class="label">' + label + '</div><div class="val">' + val + '</div></div>';
  }

  function render(d) {
    if (!d || !d.ok) {
      banner.textContent = "Watch offline — run ./scripts/field-watch-dhcp.sh ensure";
      return;
    }
    tick += 1;
    updated.textContent = d.updated || "—";
    mode.textContent = d.observe_only ? "observe only" : "—";
    var c = d.counts || {};
    var ours = d.our_dhcp_running ? "our field-dhcp ALSO running (separate)" : "our field-dhcp not serving";
    banner.textContent = (d.motto || "") + " · " + ours + (d.automated ? " · watcher automated" : " · watcher manual");
    grid.innerHTML = [
      card("Foreign listeners", c.foreign_listeners || 0),
      card("DHCP offers seen", c.dhcp_offers_seen || 0),
      card("LAN neigh hosts", c.lan_neigh_hosts || 0),
      card("External leases", c.external_lease_rows || 0),
      card("Foreign servers", c.foreign_servers || 0),
      card("Observed clients", c.observed_clients || 0),
    ].join("");
    offers.textContent = JSON.stringify(d.dhcp_offers || [], null, 2);
  }

  function poll() {
    fetch(API, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () { banner.textContent = "API unreachable — loopback panel :9477"; });
  }

  poll();
  setInterval(poll, 15000);
})();