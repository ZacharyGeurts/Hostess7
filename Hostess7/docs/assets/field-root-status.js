(function () {
  "use strict";

  const pre = document.getElementById("frs-pre");
  const cards = {
    dns: document.getElementById("frs-dns"),
    dhcp: document.getElementById("frs-dhcp"),
    watch: document.getElementById("frs-watch"),
    phase: document.getElementById("frs-phase"),
  };
  const updated = document.getElementById("frs-updated");

  function yn(v) {
    return v ? "YES" : "NO";
  }

  function paint(doc) {
    const svc = doc.services || {};
    const dns = svc.dns || {};
    const dhcp = svc.dhcp || {};
    const watch = svc.dhcp_watch || {};
    if (pre) {
      fetch("/api/root-status?fmt=telnet", { cache: "no-store" })
        .then((r) => r.text())
        .then((t) => { pre.textContent = t; })
        .catch(() => { pre.textContent = "status unavailable"; });
    }
    if (cards.dns) {
      cards.dns.textContent = `${yn(dns.running)} / healthy ${yn(dns.healthy)}`;
      cards.dns.className = "frs-val " + (dns.healthy ? "ok" : "bad");
    }
    if (cards.dhcp) {
      cards.dhcp.textContent = `p67 ${yn(dhcp.port_67)} · serve ${yn(dhcp.may_serve)}`;
      cards.dhcp.className = "frs-val " + (dhcp.port_67 ? "ok" : "bad");
    }
    if (cards.watch) {
      cards.watch.textContent = yn(watch.ok);
      cards.watch.className = "frs-val " + (watch.ok ? "ok" : "bad");
    }
    if (cards.phase) {
      cards.phase.textContent = dhcp.takeover_phase || "—";
    }
    if (updated) updated.textContent = doc.updated || "—";
  }

  function poll() {
    fetch("/api/root-status", { cache: "no-store" })
      .then((r) => r.json())
      .then(paint)
      .catch(() => {});
  }

  poll();
  setInterval(poll, 15000);
})();