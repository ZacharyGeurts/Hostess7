(function () {
  "use strict";

  const STREAM = "/api/field-popcorn/stream";
  const API = "/api/field-popcorn";
  const THUMB = API + "/thumb";
  const DETAILS = API + "/details";
  const INSPECT = API + "/inspect";
  const ELLIE = "/api/field-ellie-fier";
  const SOURCE_LABELS = {
    grok: "Grok",
    openai: "OpenAI",
    midjourney: "Midjourney",
    stable_diffusion: "Stable Diffusion",
    adobe_firefly: "Adobe Firefly",
    google_imagen: "Google Imagen",
    runway: "Runway",
    leonardo: "Leonardo",
    camera: "Camera",
    unknown: "Unknown",
  };
  const LONG_PRESS_MS = 480;
  const POSITION_SAVE_MS = 8000;

  let doc = null;
  let items = [];
  let filter = "all";
  let current = null;
  let currentMeta = null;
  let thumbMode = "viewing";
  let zoomScale = 1;
  let pinchStartDist = 0;
  let pinchStartScale = 1;
  let longPressTimer = null;
  let thumbSeekTimer = null;
  let positionTimer = null;
  let rotationIdx = 0;
  const rotations = ["auto", "90", "180", "270"];

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return "0:00";
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    if (h > 0) return h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    return m + ":" + String(s).padStart(2, "0");
  }

  function sourceLabel(id) {
    return SOURCE_LABELS[id] || id || "Unknown";
  }

  function threatClass(verdict) {
    const v = String(verdict || "clear").toLowerCase();
    if (v === "threat" || v === "fier") return "pc-threat-bad";
    if (v === "review" || v === "watch") return "pc-threat-warn";
    return "pc-threat-ok";
  }

  function fmtSize(n) {
    if (!n) return "";
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
    return (n / 1073741824).toFixed(2) + " GB";
  }

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    return res.json();
  }

  function streamUrl(id) {
    return STREAM + "?id=" + encodeURIComponent(id);
  }

  function thumbUrl(id, mode) {
    return THUMB + "?id=" + encodeURIComponent(id) + "&mode=" + encodeURIComponent(mode || "viewing") + "&t=" + Date.now();
  }

  function activeMediaEl() {
    const v = $("pc-video");
    if (v && v.classList.contains("active")) return v;
    const a = $("pc-audio");
    if (a && a.classList.contains("active")) return a;
    const img = $("pc-image");
    if (img && img.classList.contains("active")) return img;
    return null;
  }

  function videoEl() {
    const v = $("pc-video");
    return v && v.classList.contains("active") ? v : null;
  }

  function aspectFromVideo(video) {
    const w = video?.videoWidth || 0;
    const h = video?.videoHeight || 0;
    if (w > 0 && h > 0) return w / h;
    return currentMeta?.aspect_ratio || 16 / 9;
  }

  function drawFrameToCanvas(canvas, source, ar) {
    if (!canvas || !source) return null;
    const ratio = ar || aspectFromVideo(source) || 16 / 9;
    const maxW = 480;
    const w = maxW;
    const h = Math.max(1, Math.round(maxW / ratio));
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, w, h);
    try {
      const sw = source.videoWidth || source.naturalWidth || w;
      const sh = source.videoHeight || source.naturalHeight || h;
      const sar = sw / sh;
      let dw = w;
      let dh = h;
      let dx = 0;
      let dy = 0;
      if (sar > ratio) {
        dh = w / sar;
        dy = (h - dh) / 2;
      } else {
        dw = h * sar;
        dx = (w - dw) / 2;
      }
      ctx.drawImage(source, dx, dy, dw, dh);
    } catch (e) {
      return null;
    }
    return canvas.toDataURL("image/jpeg", 0.88);
  }

  function cardThumbStyle(it) {
    const ar = it.aspect_ratio || (it.kind === "video" ? 16 / 9 : it.kind === "image" ? 4 / 3 : 1);
    return "aspect-ratio:" + ar + ";";
  }

  function cardThumbHtml(it) {
    const url = it.thumb_url || (it.kind === "image" ? streamUrl(it.id) : null);
    const badge = it.thumb_mode === "custom" && it.has_custom ? '<span class="pc-card-badge">Custom</span>' : "";
    const resume =
      it.resume_sec > 3
        ? '<span class="pc-card-resume">▶ ' + esc(fmtTime(it.resume_sec)) + "</span>"
        : "";
    if (url) {
      return (
        '<div class="pc-card-thumb" style="' +
        cardThumbStyle(it) +
        '">' +
        badge +
        resume +
        '<img src="' +
        esc(url) +
        '" alt="" loading="lazy" decoding="async" /></div>'
      );
    }
    const glyph = it.kind === "audio" ? "♪" : it.kind === "video" ? "▶" : "◻";
    return (
      '<div class="pc-card-thumb placeholder" style="' +
      cardThumbStyle(it) +
      '">' +
      badge +
      resume +
      glyph +
      "</div>"
    );
  }

  function showView(name) {
    $("pc-library").classList.toggle("hidden", name !== "library");
    $("pc-player").classList.toggle("hidden", name !== "player");
  }

  function setRotation(mode) {
    $("pc-root")?.setAttribute("data-rotation", mode || "auto");
  }

  function applyStageTransform() {
    const stage = $("pc-stage");
    if (!stage) return;
    const rot = $("pc-root")?.getAttribute("data-rotation") || "auto";
    let t = "";
    if (rot !== "auto") t += "rotate(" + rot + "deg) ";
    if (zoomScale !== 1) t += "scale(" + zoomScale + ")";
    stage.style.transform = t.trim() || "";
    stage.classList.toggle("zoomed", zoomScale > 1.01);
  }

  function updateThumbToggle() {
    document.querySelectorAll(".pc-thumb-mode").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-mode") === thumbMode);
    });
  }

  function updatePausePoster() {
    const poster = $("pc-pause-poster");
    const img = $("pc-pause-poster-img");
    const el = activeMediaEl();
    if (!poster || !img || !current) return;
    const paused = el && el.tagName !== "IMG" && el.paused;
    if (!paused) {
      poster.classList.add("hidden");
      return;
    }
    const mode = thumbMode === "custom" && currentMeta?.has_custom ? "custom" : "viewing";
    const url =
      (mode === "custom" && currentMeta?.custom_url) ||
      currentMeta?.viewing_url ||
      currentMeta?.thumb_url;
    if (url) {
      img.src = url + (url.includes("?") ? "&" : "?") + "t=" + Date.now();
      poster.classList.remove("hidden");
    } else {
      poster.classList.add("hidden");
    }
  }

  async function persistThumb(mode, dataUrl, extra) {
    if (!current) return;
    const out = await api(THUMB, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        Object.assign(
          {
            media_id: current.id,
            mode: mode,
            data_url: dataUrl,
            title: current.name,
            aspect_ratio: aspectFromVideo(videoEl() || $("pc-image")),
          },
          extra || {}
        )
      ),
    });
    if (out.ok && out.meta) {
      currentMeta = out.meta;
      mergeItemMeta(current.id, out.meta);
      if (mode === "custom") {
        thumbMode = "custom";
        updateThumbToggle();
      }
      renderGrid();
      updatePausePoster();
    }
    return out;
  }

  async function captureViewingThumb() {
    const video = videoEl();
    const img = $("pc-image");
    const source = video || (img?.classList.contains("active") ? img : null);
    if (!source || !current) return;
    const canvas = document.createElement("canvas");
    const el = activeMediaEl();
    const dataUrl = drawFrameToCanvas(canvas, source, aspectFromVideo(video));
    if (!dataUrl) return;
    await persistThumb("viewing", dataUrl, {
      time_sec: el && el.currentTime != null ? el.currentTime : 0,
      title: current.name,
    });
  }

  async function setCustomFromPause() {
    const video = videoEl();
    if (!video) return;
    const canvas = document.createElement("canvas");
    const dataUrl = drawFrameToCanvas(canvas, video, aspectFromVideo(video));
    if (!dataUrl) return;
    await persistThumb("custom", dataUrl, {
      time_sec: video.currentTime,
      title: (current?.name || "") + " @ " + fmtTime(video.currentTime),
    });
    thumbMode = "custom";
    updateThumbToggle();
  }

  async function setThumbModeRemote(mode) {
    if (!current) return;
    const out = await api(API + "/thumb-mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: current.id, mode: mode }),
    });
    if (out.ok && out.meta) {
      thumbMode = mode;
      currentMeta = out.meta;
      mergeItemMeta(current.id, out.meta);
      updateThumbToggle();
      renderGrid();
      updatePausePoster();
    }
  }

  async function savePosition() {
    const el = activeMediaEl();
    if (!el || !current || el.tagName === "IMG") return;
    const t = el.currentTime || 0;
    const out = await api(API + "/position", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: current.id, position_sec: t }),
    });
    if (out.ok && out.meta) {
      mergeItemMeta(current.id, out.meta);
    }
  }

  function mergeItemMeta(id, meta) {
    const idx = items.findIndex(function (x) {
      return x.id === id;
    });
    if (idx >= 0) items[idx] = Object.assign({}, items[idx], meta);
  }

  function renderCounts(counts) {
    const c = counts || doc?.library?.by_kind || {};
    const total = (c.video || 0) + (c.audio || 0) + (c.image || 0);
    ["pc-count-all", "pc-count-video", "pc-count-audio", "pc-count-image"].forEach(function (id, i) {
      const el = $(id);
      if (!el) return;
      const vals = [total, c.video, c.audio, c.image];
      el.textContent = String(vals[i] ?? 0);
    });
  }

  function filteredItems() {
    const q = ($("pc-search")?.value || "").toLowerCase().trim();
    return items.filter(function (it) {
      if (filter !== "all" && it.kind !== filter) return false;
      if (q && !(it.name || "").toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function showCtxMenu(menuId, x, y, html, onClick) {
    const menu = $(menuId);
    if (!menu) return;
    menu.innerHTML = html;
    menu.classList.remove("hidden");
    menu.style.left = Math.min(x, window.innerWidth - 240) + "px";
    menu.style.top = Math.min(y, window.innerHeight - 280) + "px";
    menu.querySelectorAll("[data-act]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        menu.classList.add("hidden");
        onClick(btn.getAttribute("data-act"));
      });
    });
  }

  function renderGrid() {
    const grid = $("pc-grid");
    if (!grid) return;
    grid.innerHTML = filteredItems()
      .map(function (it) {
        return (
          '<button type="button" class="pc-card" role="listitem" data-id="' +
          esc(it.id) +
          '">' +
          cardThumbHtml(it) +
          '<div class="pc-card-body">' +
          '<span class="pc-card-kind">' +
          esc(it.kind) +
          "</span>" +
          '<span class="pc-card-name">' +
          esc(it.name) +
          "</span>" +
          (it.generation_source
            ? '<span class="pc-card-source ' +
              (it.ai_generated ? "pc-ai" : "") +
              '">' +
              esc(sourceLabel(it.generation_source)) +
              "</span>"
            : "") +
          (it.content_threat?.verdict
            ? '<span class="pc-card-threat ' +
              threatClass(it.content_threat.verdict) +
              '">' +
              esc(it.content_threat.verdict) +
              "</span>"
            : "") +
          '<span class="pc-card-meta">' +
          esc(fmtSize(it.size)) +
          " · ." +
          esc(it.ext) +
          (it.viewing?.time_sec ? " · pause " + esc(fmtTime(it.viewing.time_sec)) : "") +
          "</span></div></button>"
        );
      })
      .join("");

    grid.querySelectorAll(".pc-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openMedia(card.getAttribute("data-id"));
      });
      card.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        const it = items.find(function (x) {
          return x.id === card.getAttribute("data-id");
        });
        if (!it) return;
        showCtxMenu(
          "pc-card-ctx",
          ev.clientX,
          ev.clientY,
          '<button type="button" data-act="open">Open</button>' +
            (it.resume_sec > 3
              ? '<button type="button" data-act="resume">Resume at ' + esc(fmtTime(it.resume_sec)) + "</button>"
              : "") +
            '<button type="button" data-act="viewing">Use Viewing thumbnail</button>' +
            (it.has_custom ? '<button type="button" data-act="custom">Use Custom thumbnail</button>' : "") +
              '<button type="button" data-act="details">File details</button>' +
            '<button type="button" data-act="copy">Copy path</button>',
          async function (act) {
            if (act === "open") openMedia(it.id);
            else if (act === "details") showDetails(it.id);
            else if (act === "resume") openMedia(it.id, { forceResume: true });
            else if (act === "viewing" || act === "custom") {
              await api(API + "/thumb-mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ media_id: it.id, mode: act }),
              });
              await load(false);
            } else if (act === "copy") navigator.clipboard?.writeText(it.path || it.name);
          }
        );
      });
    });
  }

  function hideAllMedia() {
    if (positionTimer) clearInterval(positionTimer);
    ["pc-video", "pc-audio", "pc-image"].forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.classList.remove("active");
      if (el.tagName === "VIDEO" || el.tagName === "AUDIO") {
        el.pause();
        el.removeAttribute("src");
        el.load();
      } else {
        el.removeAttribute("src");
      }
    });
    $("pc-pause-poster")?.classList.add("hidden");
  }

  function bindPositionSaver() {
    if (positionTimer) clearInterval(positionTimer);
    positionTimer = setInterval(function () {
      savePosition().catch(function () {});
    }, POSITION_SAVE_MS);
  }

  function openMedia(id, opts) {
    opts = opts || {};
    const item = items.find(function (x) {
      return x.id === id;
    });
    if (!item) return;
    if (current && current.id !== id) {
      savePosition().catch(function () {});
    }
    current = item;
    currentMeta = item;
    thumbMode = item.thumb_mode || "viewing";
    updateThumbToggle();
    hideAllMedia();
    zoomScale = 1;
    applyStageTransform();

    $("pc-now-title").textContent = item.name || "";
    const url = streamUrl(item.id);

    if (item.kind === "video") {
      const v = $("pc-video");
      v.src = url;
      v.classList.add("active");
      v.onloadedmetadata = function () {
        mergeItemMeta(id, { aspect_ratio: aspectFromVideo(v) });
        const resume = opts.forceResume || item.resume_sec > 3 ? item.resume_sec : 0;
        if (resume > 1) {
          v.currentTime = resume;
          $("pc-now-title").textContent = (item.name || "") + " · resumed " + fmtTime(resume);
        }
        v.play().catch(function () {});
        bindSeekMedia();
      };
    } else if (item.kind === "audio") {
      const a = $("pc-audio");
      a.src = url;
      a.classList.add("active");
      if (item.resume_sec > 3) a.currentTime = item.resume_sec;
      a.play().catch(function () {});
      bindSeekMedia();
    } else {
      const img = $("pc-image");
      img.src = url;
      img.classList.add("active");
      img.onload = function () {
        const ar = img.naturalWidth / img.naturalHeight;
        persistThumb("viewing", drawFrameToCanvas(document.createElement("canvas"), img, ar), {
          time_sec: 0,
          title: item.name,
        }).catch(function () {});
      };
    }

    showView("player");
    api(API + "/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ last_media_id: id }),
    }).catch(function () {});
    bindPositionSaver();
  }

  function bindSeekMedia() {
    const el = activeMediaEl();
    if (!el || el.tagName === "IMG") {
      updateSeekUI(0, 0);
      return;
    }
    el.ontimeupdate = function () {
      updateSeekUI(el.currentTime, el.duration);
    };
    el.onpause = function () {
      $("pc-play").textContent = "▶";
      captureViewingThumb().catch(function () {});
      updatePausePoster();
      savePosition().catch(function () {});
    };
    el.onplay = function () {
      $("pc-play").textContent = "❚❚";
      $("pc-pause-poster")?.classList.add("hidden");
    };
    el.onended = function () {
      $("pc-play").textContent = "▶";
      savePosition().catch(function () {});
    };
    if (el.readyState >= 1) updateSeekUI(el.currentTime, el.duration);
  }

  function updateSeekUI(t, dur) {
    const pct = dur > 0 ? (t / dur) * 100 : 0;
    $("pc-time").textContent = fmtTime(t) + " / " + fmtTime(dur);
    $("pc-seek-fill").style.width = pct + "%";
    $("pc-seek-thumb").style.left = pct + "%";
  }

  function togglePlay() {
    const el = activeMediaEl();
    if (!el || el.tagName === "IMG") return;
    if (el.paused) {
      el.play().catch(function () {});
    } else {
      el.pause();
    }
  }

  function seekTo(ratio) {
    const el = activeMediaEl();
    if (!el || !isFinite(el.duration)) return;
    el.currentTime = Math.max(0, Math.min(el.duration, ratio * el.duration));
    updateSeekUI(el.currentTime, el.duration);
  }

  function seekBy(delta) {
    const el = activeMediaEl();
    if (!el || el.tagName === "IMG") return;
    el.currentTime = Math.max(0, Math.min(el.duration || 0, (el.currentTime || 0) + delta));
  }

  function showThumbPreview(clientX, ratio) {
    const preview = $("pc-thumb-preview");
    const canvas = $("pc-thumb-canvas");
    const video = videoEl();
    if (!preview || !canvas || !video?.duration) {
      preview?.classList.add("hidden");
      preview && (preview.hidden = true);
      return;
    }
    const wrap = $("pc-seek-wrap");
    const rect = wrap.getBoundingClientRect();
    preview.hidden = false;
    preview.classList.remove("hidden");
    preview.style.left = clientX - rect.left + "px";
    const t = ratio * video.duration;
    $("pc-thumb-time").textContent = fmtTime(t);
    clearTimeout(thumbSeekTimer);
    thumbSeekTimer = setTimeout(function () {
      const saved = video.currentTime;
      const wasPaused = video.paused;
      video.currentTime = t;
      video.addEventListener(
        "seeked",
        function onSeeked() {
          video.removeEventListener("seeked", onSeeked);
          drawFrameToCanvas(canvas, video, aspectFromVideo(video));
          video.currentTime = saved;
          if (!wasPaused) video.play().catch(function () {});
        },
        { once: true }
      );
    }, 50);
  }

  function toggleZoom(cx, cy) {
    const stageWrap = $("pc-stage-wrap");
    if (!stageWrap) return;
    if (zoomScale > 1.01) {
      zoomScale = 1;
      stageWrap.style.transformOrigin = "center center";
    } else {
      zoomScale = 2;
      const r = stageWrap.getBoundingClientRect();
      $("pc-stage").style.transformOrigin =
        (((cx || r.width / 2) / r.width) * 100).toFixed(1) + "% " +
        (((cy || r.height / 2) / r.height) * 100).toFixed(1) + "%";
    }
    applyStageTransform();
  }

  function touchDist(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.hypot(dx, dy);
  }

  function hideMenus() {
    ["pc-mobile-menu", "pc-ctx-menu", "pc-card-ctx", "pc-stage-ctx"].forEach(function (id) {
      $(id)?.classList.add("hidden");
    });
  }

  function detailsRow(label, value) {
    if (value === undefined || value === null || value === "") return "";
    return (
      '<div class="pc-detail-row"><span class="pc-detail-k">' +
      esc(label) +
      '</span><span class="pc-detail-v">' +
      esc(String(value)) +
      "</span></div>"
    );
  }

  function renderDetailsPanel(item, inspect) {
    const body = $("pc-details-body");
    if (!body) return;
    const gen = inspect?.generation || {};
    const fd = inspect?.file_details || item?.file_details || {};
    const ct = inspect?.content_threat || item?.content_threat || {};
    const issues = (fd.encoding_issues || ct.threats || []).join(", ");
    const dims =
      fd.width && fd.height ? fd.width + "×" + fd.height : fd.color_space || "";
    const audio =
      fd.sample_rate && fd.channels
        ? fd.sample_rate + " Hz · " + fd.channels + " ch · " + (fd.bit_depth || "?") + "-bit"
        : "";
    body.innerHTML =
      '<div class="pc-detail-section">' +
      detailsRow("Name", item?.name) +
      detailsRow("Kind", item?.kind) +
      detailsRow("Format", fd.container || item?.ext) +
      detailsRow("MIME", fd.mime || item?.mime) +
      detailsRow("Size", fmtSize(item?.size)) +
      detailsRow("Dimensions", dims) +
      detailsRow("Audio", audio) +
      detailsRow("Codec", fd.codec) +
      detailsRow("Bitrate est.", fd.bitrate_est) +
      "</div>" +
      '<div class="pc-detail-section">' +
      detailsRow("Generation source", sourceLabel(gen.generation_source || item?.generation_source)) +
      detailsRow("AI generated", gen.ai_generated ?? item?.ai_generated ? "yes" : "no") +
      detailsRow("Confidence", gen.generation_confidence ?? item?.generation_confidence) +
      detailsRow("Neural signals", (gen.neural_signals || []).join(", ")) +
      detailsRow("OCR", fd.ocr_text ? fd.ocr_text.slice(0, 240) : "") +
      detailsRow("OCR confidence", fd.ocr_confidence) +
      "</div>" +
      '<div class="pc-detail-section ' + threatClass(ct.verdict) + '">' +
      detailsRow("Content threat", ct.verdict || "clear") +
      detailsRow("Threat score", ct.score) +
      detailsRow("Ironclad", ct.ironclad_verdict || ct.ironclad_sealed) +
      detailsRow("Issues", issues) +
      "</div>";
  }

  async function showDetails(mediaId) {
    const item = items.find(function (x) {
      return x.id === mediaId;
    });
    const panel = $("pc-details");
    if (!panel) return;
    panel.classList.remove("hidden");
    renderDetailsPanel(item || { id: mediaId }, null);
    const body = $("pc-details-body");
    if (body) body.innerHTML += '<p class="pc-detail-loading">Inspecting…</p>';
    try {
      const out = await api(DETAILS + "?id=" + encodeURIComponent(mediaId));
      if (out.ok && out.inspect) {
        renderDetailsPanel(item || out.inspect, out.inspect);
        if (item && out.inspect.generation) {
          mergeItemMeta(mediaId, {
            generation_source: out.inspect.generation.generation_source,
            generation_confidence: out.inspect.generation.generation_confidence,
            ai_generated: out.inspect.generation.ai_generated,
            content_threat: out.inspect.content_threat,
            file_details: out.inspect.file_details,
          });
          renderGrid();
        }
      }
    } catch (e) {
      if (body) body.innerHTML += '<p class="pc-detail-error">Details unavailable.</p>';
    }
  }

  function wireSeekBar() {
    const track = $("pc-seek-track");
    if (!track) return;
    function ratioFromEvent(ev) {
      const rect = track.getBoundingClientRect();
      return Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    }
    track.addEventListener("click", function (ev) {
      seekTo(ratioFromEvent(ev));
    });
    track.addEventListener("mousemove", function (ev) {
      showThumbPreview(ev.clientX, ratioFromEvent(ev));
    });
    track.addEventListener("mouseleave", function () {
      const p = $("pc-thumb-preview");
      if (p) p.hidden = true;
    });
    track.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      $("pc-ctx-menu")?.classList.remove("hidden");
      $("pc-ctx-menu").style.left = ev.clientX + "px";
      $("pc-ctx-menu").style.top = ev.clientY + "px";
    });
    let dragging = false;
    track.addEventListener("mousedown", function () {
      dragging = true;
    });
    document.addEventListener("mousemove", function (ev) {
      if (!dragging) return;
      seekTo(ratioFromEvent(ev));
      showThumbPreview(ev.clientX, ratioFromEvent(ev));
    });
    document.addEventListener("mouseup", function () {
      dragging = false;
    });
  }

  function wireStage() {
    const wrap = $("pc-stage-wrap");
    if (!wrap) return;
    wrap.addEventListener("dblclick", function (ev) {
      toggleZoom(ev.clientX, ev.clientY);
    });
    wrap.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      if (!videoEl()) return;
      showCtxMenu(
        "pc-stage-ctx",
        ev.clientX,
        ev.clientY,
        '<button type="button" data-act="set-custom">Set custom thumbnail from pause</button>' +
          '<button type="button" data-act="set-viewing">Update viewing thumbnail</button>' +
          '<button type="button" data-act="viewing">Use Viewing</button>' +
          '<button type="button" data-act="custom">Use Custom</button>',
        async function (act) {
          if (act === "set-custom") await setCustomFromPause();
          else if (act === "set-viewing") await captureViewingThumb();
          else if (act === "viewing" || act === "custom") await setThumbModeRemote(act);
        }
      );
    });
    wrap.addEventListener("touchstart", function (ev) {
      if (ev.touches.length === 2) {
        pinchStartDist = touchDist(ev.touches);
        pinchStartScale = zoomScale;
      } else if (ev.touches.length === 1) {
        const t = ev.touches[0];
        longPressTimer = setTimeout(function () {
          $("pc-mobile-menu")?.classList.remove("hidden");
          $("pc-mobile-menu").style.left = Math.min(window.innerWidth - 210, t.clientX) + "px";
          $("pc-mobile-menu").style.top = Math.min(window.innerHeight - 280, t.clientY) + "px";
        }, LONG_PRESS_MS);
      }
    }, { passive: true });
    wrap.addEventListener("touchmove", function (ev) {
      if (ev.touches.length === 2) {
        clearTimeout(longPressTimer);
        const dist = touchDist(ev.touches);
        zoomScale = Math.max(1, Math.min(4, pinchStartScale * (dist / pinchStartDist)));
        applyStageTransform();
      }
    }, { passive: true });
    wrap.addEventListener("touchend", function () {
      clearTimeout(longPressTimer);
    });
  }

  function wireControls() {
    $("pc-play")?.addEventListener("click", togglePlay);
    $("pc-back")?.addEventListener("click", function () {
      savePosition()
        .catch(function () {})
        .finally(function () {
          hideAllMedia();
          showView("library");
          load(false).catch(function () {});
        });
    });
    $("pc-rotate")?.addEventListener("click", function () {
      rotationIdx = (rotationIdx + 1) % rotations.length;
      setRotation(rotations[rotationIdx]);
      applyStageTransform();
    });
    $("pc-scan")?.addEventListener("click", function () {
      load(true);
    });
    $("pc-details-btn")?.addEventListener("click", function () {
      if (current?.id) showDetails(current.id);
    });
    $("pc-details-close")?.addEventListener("click", function () {
      $("pc-details")?.classList.add("hidden");
    });

    document.querySelectorAll(".pc-thumb-mode").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setThumbModeRemote(btn.getAttribute("data-mode"));
      });
    });

    document.addEventListener("keydown", function (ev) {
      if ($("pc-player").classList.contains("hidden")) return;
      if (ev.code === "Space") {
        ev.preventDefault();
        togglePlay();
      } else if (ev.code === "ArrowRight") seekBy(10);
      else if (ev.code === "ArrowLeft") seekBy(-10);
      else if (ev.code === "Escape") {
        hideMenus();
        if (zoomScale > 1) toggleZoom();
      }
    });

    $("pc-ctx-menu")?.querySelectorAll("[data-act]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        const act = btn.getAttribute("data-act");
        const el = activeMediaEl();
        hideMenus();
        if (act === "frame-back" && el) seekBy(-1 / 30);
        else if (act === "frame-fwd" && el) seekBy(1 / 30);
        else if (act === "speed-05" && el) el.playbackRate = 0.5;
        else if (act === "speed-1" && el) el.playbackRate = 1;
        else if (act === "speed-15" && el) el.playbackRate = 1.5;
        else if (act === "set-thumb-custom") await setCustomFromPause();
        else if (act === "set-thumb-viewing") await captureViewingThumb();
        else if (act === "thumb-viewing") await setThumbModeRemote("viewing");
        else if (act === "thumb-custom") await setThumbModeRemote("custom");
        else if (act === "copy-time" && el) navigator.clipboard?.writeText(fmtTime(el.currentTime));
      });
    });

    document.querySelectorAll(".pc-filter").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".pc-filter").forEach(function (b) {
          b.classList.remove("active");
        });
        btn.classList.add("active");
        filter = btn.getAttribute("data-filter") || "all";
        renderGrid();
      });
    });

    $("pc-search")?.addEventListener("input", renderGrid);
    document.addEventListener("click", function (ev) {
      if (!ev.target.closest(".pc-mobile-menu") && !ev.target.closest(".pc-ctx-menu") &&
          !ev.target.closest("#pc-card-ctx") && !ev.target.closest("#pc-stage-ctx")) {
        hideMenus();
      }
    });
  }

  async function load(rescan) {
    doc = await api(API + (rescan ? "?rescan=1" : ""));
    const lib = await api(API + "/library");
    items = lib.items || [];
    renderCounts(doc.library?.by_kind);
    $("pc-tagline").textContent = doc.posture || doc.motto || "";
    renderGrid();
  }

  async function init() {
    if (globalThis.FieldShellDock) FieldShellDock.init({ activeIcon: "popcorn" });
    wireSeekBar();
    wireStage();
    wireControls();
    try {
      await load(false);
    } catch (e) {
      $("pc-grid").innerHTML = "<p>Popcorn could not load library.</p>";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();