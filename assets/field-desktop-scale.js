/**
 * Field desktop scale — unified UI scale for C2 shell, taskbar, toast, control panel.
 */
(function (global) {
  "use strict";

  const DEFAULT_PCT = 125;
  const MIN_PCT = 50;
  const MAX_PCT = 200;
  const BASE_FONT_PX = 16;
  const BASE_FSB_H = 44;
  const BASE_ICON = 40;

  function clamp(pct) {
    const n = parseInt(pct, 10);
    if (!Number.isFinite(n)) return DEFAULT_PCT;
    return Math.max(MIN_PCT, Math.min(MAX_PCT, n));
  }

  function iconSize(settings, scale) {
    const raw = parseInt(settings?.desktop_icon_size, 10);
    if (Number.isFinite(raw)) return Math.max(24, Math.min(96, raw));
    return Math.max(24, Math.min(96, Math.round(BASE_ICON * scale)));
  }

  function apply(settings, opts) {
    opts = opts || {};
    const s = settings || {};
    const pct = clamp(s.ui_scale != null ? s.ui_scale : DEFAULT_PCT);
    const scale = pct / 100;
    const root = document.documentElement;
    const iconPx = iconSize(s, scale);

    root.classList.add("fds-scaled", "fds-quality");
    root.dataset.desktopScale = String(pct);
    root.style.setProperty("--fds-scale", String(scale));
    root.style.setProperty("--fds-ui-scale-pct", String(pct));
    root.style.setProperty("--fsb-h", Math.round(BASE_FSB_H * scale) + "px");
    root.style.setProperty("--hd-icon-size", iconPx + "px");
    root.style.setProperty("--fds-base-font", Math.round(BASE_FONT_PX * scale) + "px");
    root.style.fontSize = Math.round(BASE_FONT_PX * scale) + "px";

    const toast = document.getElementById("hd-toast");
    if (toast) {
      toast.style.bottom = Math.round(52 * scale) + "px";
    }

    if (!opts.silent && global.FieldHostDesktop?.toast && opts.toast) {
      global.FieldHostDesktop.toast(opts.toast);
    }

    return {
      ui_scale: pct,
      scale_factor: Math.round(scale * 1000) / 1000,
      icon_size_px: iconPx,
      min_pct: MIN_PCT,
      max_pct: MAX_PCT,
      default_pct: DEFAULT_PCT,
    };
  }

  function defaults() {
    return {
      ui_scale: DEFAULT_PCT,
      desktop_icon_size: 50,
      min_pct: MIN_PCT,
      max_pct: MAX_PCT,
      default_pct: DEFAULT_PCT,
    };
  }

  global.FieldDesktopScale = {
    apply: apply,
    clamp: clamp,
    defaults: defaults,
    DEFAULT_PCT: DEFAULT_PCT,
    MIN_PCT: MIN_PCT,
    MAX_PCT: MAX_PCT,
  };
})(window);