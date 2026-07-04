(function () {
  "use strict";
  var API = "/api/field-grow-watch";
  var tick = 0;
  var hist = [];
  var sparkEl = document.getElementById("fgw-spark");
  var gridEl = document.getElementById("fgw-grid");
  var updatedEl = document.getElementById("fgw-updated");
  var tickEl = document.getElementById("fgw-tick");

  function fmt(n) {
    n = Number(n) || 0;
    if (n >= 1e12) return (n / 1e12).toFixed(3) + "T";
    if (n >= 1e9) return (n / 1e9).toFixed(3) + "B";
    if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
    return String(n);
  }

  function spark() {
    if (!hist.length) return "";
    var min = Math.min.apply(null, hist);
    var max = Math.max.apply(null, hist);
    var span = Math.max(1, max - min);
    var chars = "▁▂▃▄▅▆▇█";
    return hist
      .slice(-64)
      .map(function (v) {
        var i = Math.min(7, Math.floor(((v - min) / span) * 7));
        return chars[i];
      })
      .join("");
  }

  function card(label, value) {
    return (
      '<div class="fgw-card"><label>' +
      label +
      '</label><strong>' +
      value +
      "</strong></div>"
    );
  }

  function render(d) {
    tick += 1;
    tickEl.textContent = String(tick);
    updatedEl.textContent = d.updated || new Date().toISOString();
    hist.push(Number(d.population) || 0);
    if (hist.length > 128) hist.shift();
    sparkEl.textContent = spark();
    gridEl.innerHTML = [
      card("Population", fmt(d.population)),
      card("Devices", fmt(d.devices)),
      card("Logical edges", fmt(d.logical_edges)),
      card("Logical shards", fmt(d.logical_shards)),
      card("Hosts / shard", String(d.hosts_per_shard || 4096)),
      card("Planet DHCP", fmt(d.planet_dhcp)),
      card("Planet DNS", fmt(d.planet_dns)),
      card("Local leases", String(d.local_dhcp_leases || 0)),
      card("Pool slots", String(d.dhcp_pool_slots || 0)),
      card("Quarantined", String(d.quarantined || 0)),
      card("Everyone", String(d.everyone_total || 0)),
      card("Edges real?", String(d.edges_are_real)),
      card("Ingress", String(d.ingress_policy || "")),
    ].join("");
  }

  function poll() {
    fetch(API, { cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(render)
      .catch(function () {
        updatedEl.textContent = "offline — start threat panel :9477";
      });
  }

  poll();
  setInterval(poll, 1000);
})();