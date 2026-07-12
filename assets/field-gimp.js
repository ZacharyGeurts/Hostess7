(function () {
  "use strict";

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function init() {
    const main = document.getElementById("fg-main");
    if (!main) return;
    try {
      const res = await fetch("/api/field-gimp", { credentials: "same-origin" });
      const doc = await res.json();
      const pill = document.getElementById("fg-os-pill");
      if (pill) pill.textContent = doc.os_brand || "AmmoOS";

      const phases = (doc.phases || [])
        .map(function (p) {
          return (
            '<div class="fg-phase' +
            (p.status === "active" ? " active" : "") +
            '"><strong>' +
            esc(p.label) +
            '</strong><span>' +
            esc(p.status || "") +
            "</span></div>"
          );
        })
        .join("");

      const rtx = doc.rtx || {};
      const rtxCls = rtx.permit_rtx ? "ok" : "cpu";
      const rtxLine = rtx.permit_rtx
        ? "RTX detected — gated tools available (" + esc(rtx.profile_active || "queen_rtx") + ")"
        : "No RTX — CPU field_opt path (" + esc(rtx.profile_active || "field_opt") + "); gated tools hidden";

      const stats = (doc.upstream || {}).rewrite_stats || {};
      const cons = doc.consolidation_manifest || (doc.upstream || {}).consolidation || {};
      const rewriteLine =
        (stats.rewritten || 0) +
        " rewritten · " +
        (cons.files_removed || 0) +
        " consolidated away · libammoos";

      const formats = doc.field_formats || {};
      const magics = formats.magics || {};
      const io = doc.field_io || {};
      const formatLine = Object.keys(magics)
        .map(function (k) {
          const m = magics[k];
          const ext = (m.ext || []).join(", ");
          return "<span class='fg-fmt'>" + esc(k) + (ext ? " <em>" + esc(ext) + "</em>" : "") + "</span>";
        })
        .join("");
      const pathLine =
        "CPU <code>" +
        esc((formats.paths || {}).cpu || "field_opt") +
        "</code> · RTX <code>" +
        esc((formats.paths || {}).rtx || "queen_rtx") +
        "</code> · active <code>" +
        esc(io.rtx && io.rtx.profile_active ? io.rtx.profile_active : "field_opt") +
        "</code>";

      main.innerHTML =
        '<div class="fg-card"><strong>' +
        esc(doc.product || "AmmoOS Image") +
        " " +
        esc(doc.version || "1.0") +
        '</strong><p class="fg-rtx ' +
        rtxCls +
        '">' +
        rtxLine +
        "</p><p style='margin:8px 0 0;font-size:12px;color:var(--fg-dim)'>" +
        rewriteLine +
        "</p></div>" +
        '<div class="fg-card"><strong>Tree</strong><p>' +
        esc((doc.upstream || {}).path || "") +
        " · " +
        esc((doc.upstream || {}).version_hint || "") +
        " · " +
        ((doc.upstream || {}).total_files || 0) +
        " files</p></div>" +
        '<div class="fg-card"><strong>Field formats</strong><p class="fg-fmt-row">' +
        (formatLine || "WRDT · WRZC · ZAC7 · FLD · plate") +
        "</p><p style='margin:8px 0 0;font-size:11px;color:var(--fg-dim)'>" +
        pathLine +
        "</p></div>" +
        '<div class="fg-card"><strong>Rewrite phases</strong>' +
        phases +
        "</div>" +
        '<div class="fg-card"><p style="margin:0;font-size:12px;color:var(--fg-dim)">' +
        esc(doc.posture || "") +
        "</p></div>";
    } catch (e) {
      main.textContent = "AmmoOS Image load failed: " + e.message;
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();