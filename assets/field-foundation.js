/* NEXUS Field Foundation — live fetch only (/api/status). No client cache. */
(function (global) {
  function fetchField() {
    return global.fetch("/api/status", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }

  function boot(dest) {
    fetchField().then((d) => {
      if (d) global.NEXUS_FIELD = d;
      if (dest) global.location.replace(dest);
    });
  }

  global.NexusField = { boot, fetchField };
})(window);