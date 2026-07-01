/**
 * Queen 2026 theme seal — delegates to Queen Styles (rebranded theming).
 * Forward-only: refuses retrograde themes; blocks hostile head injection.
 */
(function () {
  "use strict";

  const THEME_ID = "black_emerald_rose_2026";
  const SURFACE = "browser";

  if (window.QueenStyles) {
    window.QueenStyles.sealHead();
    if (document.body?.dataset?.queenSurface === SURFACE || document.readyState === "loading") {
      window.QueenStyles.boot();
    } else {
      document.addEventListener(
        "DOMContentLoaded",
        () => window.QueenStyles.boot(),
        { once: true },
      );
    }
    return;
  }

  function basename(href) {
    try {
      return new URL(href, location.href).pathname.split("/").pop() || "";
    } catch {
      return "";
    }
  }

  function applyColors(colors) {
    const root = document.documentElement;
    for (const [k, v] of Object.entries(colors || {})) {
      root.style.setProperty(`--qb-${k.replace(/_/g, "-")}`, String(v));
    }
  }

  async function legacyApply() {
    if (document.body?.dataset?.queenSurface !== SURFACE) return;
    const res = await fetch("/gui/queen-theme-2026.json", { cache: "no-store" });
    if (!res.ok) return;
    const theme = await res.json();
    if (theme.chrome_name !== THEME_ID) return;
    applyColors(theme.colors);
    document.documentElement.dataset.queenTheme = THEME_ID;
    document.body.dataset.queenTheme = THEME_ID;
  }

  if (document.body?.dataset?.queenSurface === SURFACE) {
    legacyApply();
  } else {
    document.addEventListener("DOMContentLoaded", legacyApply, { once: true });
  }
})();