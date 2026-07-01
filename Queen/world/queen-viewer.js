/**
 * Queen Viewer — universal secure preview inside Queen Browser.
 * Text · code · markdown · json · image · hex · every discerned format.
 */
(function (global) {
  "use strict";

  const FILES_API = "/api/queen-file-browser";
  const CODE_API = "/api/queen-code";
  const IMAGE_EXT = new Set([
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif",
  ]);

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function filesApi(body) {
    const r = await fetch(FILES_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  async function codeApi(body) {
    const r = await fetch(CODE_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  function extOf(path) {
    const m = String(path || "").toLowerCase().match(/(\.[a-z0-9]+)$/);
    return m ? m[1] : "";
  }

  function renderMarkdown(md) {
    let html = esc(md);
    html = html.replace(/^###### (.+)$/gm, "<h6>$1</h6>");
    html = html.replace(/^##### (.+)$/gm, "<h5>$1</h5>");
    html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
    html = html.replace(/```([\w]*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const hi = global.QueenCodeHighlight?.highlight(code, lang || "plaintext") || esc(code);
      return `<pre><code class="qs-code">${hi}</code></pre>`;
    });
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    html = html.replace(/^(?:---|\*\*\*|___)\s*$/gm, "<hr />");
    html = html.replace(/\n\n/g, "</p><p>");
    return `<div class="qv-markdown"><p>${html}</p></div>`;
  }

  function renderCode(content, lang) {
    const HL = global.QueenCodeHighlight;
    const body = HL?.highlight(content, lang) || esc(content);
    const gutter = HL?.gutterLines(content) || "1";
    return `
      <div class="qv-code qs-code">
        <div class="qv-gutter" aria-hidden="true">${gutter}</div>
        <pre>${body}</pre>
      </div>`;
  }

  function renderMetaBar(doc) {
    const parts = [];
    if (doc.language) parts.push(`<span><strong>lang</strong> ${esc(doc.language)}</span>`);
    if (doc.bytes != null) parts.push(`<span><strong>size</strong> ${esc(doc.bytes)} B</span>`);
    if (doc.lines != null) parts.push(`<span><strong>lines</strong> ${esc(doc.lines)}</span>`);
    if (doc.type_label) parts.push(`<span class="pill">${esc(doc.type_label)}</span>`);
    if (!parts.length) return "";
    return `<div class="qv-meta-bar">${parts.join("")}</div>`;
  }

  function renderImage(dataUrl, alt) {
    return `
      ${renderMetaBar({ type_label: "image" })}
      <div class="qv-image-wrap">
        <img src="${esc(dataUrl)}" alt="${esc(alt || "preview")}" loading="lazy" />
      </div>`;
  }

  function renderHex(hex, bytes) {
    return `
      ${renderMetaBar({ type_label: "binary", bytes })}
      <pre class="qv-hex">${hex}</pre>`;
  }

  async function loadPreview(path, entry) {
    const ext = extOf(path);
    if (entry?.kind === "dir") {
      return { ok: true, mode: "empty", html: '<div class="qv-empty">Folder — double-click to open</div>' };
    }
    const prev = await filesApi({ action: "preview", path });
    if (!prev.ok) {
      return {
        ok: false,
        mode: "error",
        html: `<div class="qv-empty">${esc(prev.error || "preview failed")}</div>`,
        language: "plaintext",
      };
    }
    const lang = prev.language || global.QueenCodeHighlight?.langFromPath(path) || "plaintext";
    let html = renderMetaBar({
      language: lang,
      bytes: prev.bytes,
      lines: prev.lines,
      type_label: prev.type_label || prev.mode,
    });
    if (prev.mode === "image" && prev.data_url) {
      html += `<div class="qv-image-wrap"><img class="qz-zoomable" src="${esc(prev.data_url)}" alt="${esc(entry?.name || "preview")}" loading="lazy" /></div>`;
      return { ok: true, mode: "image", html, language: lang };
    }
    if (prev.mode === "hex") {
      html += `<pre class="qv-hex">${prev.hex_html || esc(prev.content || "")}</pre>`;
      return { ok: true, mode: "hex", html, language: "binary" };
    }
    const content = prev.content || "";
    if (prev.mode === "markdown" || ext === ".md") {
      html += renderMarkdown(content);
      return { ok: true, mode: "markdown", html, language: "markdown" };
    }
    if (prev.mode === "json" || ext === ".json") {
      let pretty = content;
      try {
        pretty = JSON.stringify(JSON.parse(content), null, 2);
      } catch (_) {
        /* keep raw */
      }
      html += renderCode(pretty, "json");
      return { ok: true, mode: "json", html, language: "json" };
    }
    html += renderCode(content, lang);
    return { ok: true, mode: "code", html, language: lang };
  }

  async function mount(container, path, entry) {
    if (!container) return null;
    container.classList.add("qv-surface");
    container.innerHTML = '<div class="qv-empty">Loading preview…</div>';
    const out = await loadPreview(path, entry);
    container.innerHTML = out.html || '<div class="qv-empty">No preview</div>';
    return out;
  }

  global.QueenViewer = {
    mount,
    loadPreview,
    renderCode,
    renderMarkdown,
    IMAGE_EXT,
    extOf,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);