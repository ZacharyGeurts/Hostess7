/**
 * Queen zoom lightbox — click image to fullscreen, click again to dismiss.
 */
(function (global) {
  "use strict";

  let overlay = null;

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.className = "qz-lightbox";
    overlay.hidden = true;
    overlay.innerHTML =
      '<button type="button" class="qz-lightbox-close" aria-label="Close">×</button>' +
      '<img class="qz-lightbox-img" alt="" />' +
      '<p class="qz-lightbox-cap"></p>';
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay || e.target.closest(".qz-lightbox-close")) close();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay && !overlay.hidden) close();
    });
    return overlay;
  }

  function open(src, caption) {
    if (!src) return;
    const el = ensureOverlay();
    const img = el.querySelector(".qz-lightbox-img");
    const cap = el.querySelector(".qz-lightbox-cap");
    img.src = src;
    img.alt = caption || "";
    cap.textContent = caption || "";
    el.hidden = false;
    document.body.classList.add("qz-lightbox-open");
  }

  function close() {
    if (!overlay) return;
    overlay.hidden = true;
    document.body.classList.remove("qz-lightbox-open");
    const img = overlay.querySelector(".qz-lightbox-img");
    if (img) img.removeAttribute("src");
  }

  function bind(root) {
    const scope = root || document;
    scope.querySelectorAll("img.qz-zoomable, .qf-lib-cover img, .qf-lib-row img, .qv-image-wrap img, .nes-theater img").forEach((img) => {
      if (img.dataset.qzBound) return;
      img.dataset.qzBound = "1";
      img.classList.add("qz-zoomable");
      img.style.cursor = "zoom-in";
      img.addEventListener("click", (e) => {
        e.stopPropagation();
        open(img.currentSrc || img.src, img.alt || img.title || "");
      });
    });
  }

  global.QueenZoomLightbox = { open, close, bind };
})(typeof window !== "undefined" ? window : globalThis);