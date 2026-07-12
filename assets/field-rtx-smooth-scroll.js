/**
 * RTX-quality infinite smooth scroll — momentum, GPU layer, no jank.
 */
(function (global) {
  "use strict";

  function wire(el, opts) {
    if (!el || el.dataset.rtxScroll === "1") return;
    opts = opts || {};
    el.dataset.rtxScroll = "1";
    el.classList.add("rtx-smooth-scroll");
    if (opts.infinite) el.classList.add("rtx-smooth-scroll--infinite");

    let target = el.scrollTop;
    let current = el.scrollTop;
    let velocity = 0;
    let raf = 0;

    function clamp() {
      const max = Math.max(0, el.scrollHeight - el.clientHeight);
      if (opts.infinite && el.scrollTop >= max - 2) {
        el.scrollTop = 0;
        current = 0;
        target = 0;
      }
      target = Math.max(0, Math.min(max, target));
    }

    function tick() {
      const diff = target - current;
      velocity = velocity * 0.82 + diff * 0.18;
      current += velocity;
      if (Math.abs(velocity) < 0.25 && Math.abs(diff) < 0.5) {
        current = target;
        velocity = 0;
        raf = 0;
        el.scrollTop = Math.round(current);
        return;
      }
      el.scrollTop = current;
      raf = requestAnimationFrame(tick);
    }

    function nudge(delta) {
      target += delta;
      clamp();
      if (!raf) raf = requestAnimationFrame(tick);
    }

    el.addEventListener(
      "wheel",
      function (ev) {
        if (el.scrollHeight <= el.clientHeight) return;
        ev.preventDefault();
        nudge(ev.deltaY * (opts.wheelGain || 0.85));
      },
      { passive: false },
    );

    return { nudge: nudge, element: el };
  }

  function wireAll(sel, opts) {
    document.querySelectorAll(sel).forEach(function (node) {
      wire(node, opts);
    });
  }

  global.FieldRtxSmoothScroll = { wire: wire, wireAll: wireAll };
})(typeof window !== "undefined" ? window : globalThis);