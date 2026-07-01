/**
 * AmmoCode sanctioned screenshot — GUI save menu only. No getDisplayMedia.
 */
(function (global) {
  "use strict";

  let sanctioned = false;

  function isSanctioned() {
    return sanctioned === true;
  }

  function svgEscape(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function captureElement(el, opts) {
    if (!el) throw new Error("nothing to capture");
    const rect = el.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    const clone = el.cloneNode(true);
    clone.querySelectorAll("textarea").forEach((ta) => {
      const pre = document.createElement("pre");
      pre.textContent = ta.value;
      pre.style.cssText = window.getComputedStyle(ta).cssText;
      ta.replaceWith(pre);
    });
    const xhtml = new XMLSerializer().serializeToString(clone);
    const svg = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">`,
      `<foreignObject width="100%" height="100%">`,
      `<div xmlns="http://www.w3.org/1999/xhtml" style="width:${w}px;height:${h}px;overflow:hidden;">`,
      xhtml,
      "</div></foreignObject></svg>",
    ].join("");
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("svg render failed"));
      i.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = opts?.bg || "#010302";
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0);
    return canvas;
  }

  async function saveScreenshot(target) {
    sanctioned = true;
    try {
      const el = typeof target === "string" ? document.querySelector(target) : target;
      const canvas = await captureElement(el || document.querySelector(".ac-app"), { bg: "#010302" });
      const blob = await new Promise((res) => canvas.toBlob(res, "image/png"));
      if (!blob) throw new Error("png encode failed");
      const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
      const name = `ammocode-screenshot-${stamp}.png`;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
      URL.revokeObjectURL(a.href);
      return { ok: true, filename: name, bytes: blob.size };
    } finally {
      sanctioned = false;
    }
  }

  global.AmmoCodeScreenshot = {
    isSanctioned,
    saveScreenshot,
    captureElement,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);