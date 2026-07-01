/**
 * Drop AmmoCode into any GUI — one call, g16-ready syntax highlighting.
 *
 *   AmmoCodeEmbed.mount(document.getElementById('host'), {
 *     language: 'cxx',
 *     g16: { beltProfile: 'belt_2_0', apiBase: 'http://127.0.0.1:9555/api/ammocode' },
 *     content: 'int main(){}',
 *   });
 */
(function (global) {
  "use strict";

  const ASSET_BASE = global.AmmoCodeEmbedBase || "./";

  function loadCss(href) {
    if (document.querySelector(`link[href="${href}"]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("script load failed: " + src));
      document.head.appendChild(s);
    });
  }

  async function ensureAssets() {
    loadCss(ASSET_BASE + "assets/syntax.css");
    loadCss(ASSET_BASE + "assets/themes.css");
    loadCss(ASSET_BASE + "assets/editor.css");
    await loadScript(ASSET_BASE + "lib/highlight.js");
    await loadScript(ASSET_BASE + "lib/g16.js");
    await loadScript(ASSET_BASE + "lib/plugins.js");
    await loadScript(ASSET_BASE + "lib/editor.js");
  }

  async function mount(host, opts) {
    if (!host) return null;
    await ensureAssets();
    host.innerHTML =
      '<div class="ac ac-embed">' +
      '<label class="ac-lang-pick">Language <select class="ac-embed-lang"></select></label>' +
      '<div class="ac-editor-wrap">' +
      '<div class="ac-gutter ac-embed-gutter">1</div>' +
      '<div class="ac-editor-stack">' +
      '<pre class="ac-highlight qs-code ac-embed-hi"></pre>' +
      '<textarea class="ac-editor ac-embed-ed" spellcheck="false"></textarea>' +
      '</div></div></div>';
    global.AmmoCodeG16?.config?.(opts?.g16 || {});
    const lang = opts?.language || "cxx";
    const ed = host.querySelector(".ac-embed-ed");
    const hi = host.querySelector(".ac-embed-hi");
    const sel = host.querySelector(".ac-embed-lang");
    const doc = await global.AmmoCodeG16.loadLanguages();
    const langs = doc.g16_discern || doc.languages || ["c", "cxx", "python"];
    sel.innerHTML = langs.map((l) => `<option value="${l}">${l}</option>`).join("");
    sel.value = langs.includes(lang) ? lang : langs[0];
    ed.value = opts?.content || "";
    function repaint() {
      hi.innerHTML = global.AmmoCodeHighlight.highlight(ed.value, sel.value);
      const n = Math.max(1, ed.value.split("\n").length);
      host.querySelector(".ac-embed-gutter").textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
    }
    sel.addEventListener("change", repaint);
    ed.addEventListener("input", repaint);
    ed.addEventListener("scroll", () => {
      hi.scrollTop = ed.scrollTop;
      hi.scrollLeft = ed.scrollLeft;
      host.querySelector(".ac-embed-gutter").scrollTop = ed.scrollTop;
    });
    repaint();
    return {
      getValue() { return ed.value; },
      setValue(v) { ed.value = v; repaint(); },
      getLanguage() { return sel.value; },
      setLanguage(l) { sel.value = l; repaint(); },
    };
  }

  global.AmmoCodeEmbed = { mount, ensureAssets };
})(typeof globalThis !== "undefined" ? globalThis : window);