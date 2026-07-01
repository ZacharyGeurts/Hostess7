/* NEXUS SDF Ops Menu — radial SDF chrome + launch AMOURANTHRTX on GPU */
(function (global) {
  "use strict";

  const ITEMS = [
    { id: "command", label: "Command", tab: "command" },
    { id: "packets", label: "Packets", tab: "packets" },
    { id: "threats", label: "Threats", tab: "threats" },
    { id: "signals", label: "Signals", tab: "signals" },
    { id: "library", label: "Library", tab: "library" },
    { id: "gpu", label: "GPU Field Die", action: "gpu", gpu: true },
  ];

  let open = false;
  let gpuStatus = null;

  function roundRectSdf(ctx, x, y, w, h, r, fill, stroke) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }

  function drawRadialMenu(canvas) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(global.devicePixelRatio || 1, 2);
    const size = 200;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#040c14";
    ctx.fillRect(0, 0, size, size);
    const cx = size / 2;
    const cy = size / 2;
    const n = ITEMS.length;
    ITEMS.forEach((item, i) => {
      const ang = (i / n) * Math.PI * 2 - Math.PI / 2;
      const bx = cx + Math.cos(ang) * 62 - 28;
      const by = cy + Math.sin(ang) * 62 - 14;
      const col = item.gpu ? "rgba(34, 211, 238, 0.35)" : "rgba(56, 189, 248, 0.18)";
      const edge = item.gpu ? "#22d3ee" : "rgba(56, 189, 248, 0.55)";
      roundRectSdf(ctx, bx, by, 56, 28, 8, col, edge);
      ctx.fillStyle = item.gpu ? "#e0f7ff" : "#9ac8e8";
      ctx.font = "9px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText(item.label.split(" ")[0], bx + 28, by + 17);
    });
    ctx.beginPath();
    ctx.arc(cx, cy, 22, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(14, 116, 144, 0.5)";
    ctx.fill();
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = "#22d3ee";
    ctx.font = "bold 10px Impact, sans-serif";
    ctx.fillText("SDF", cx, cy + 4);
  }

  async function fetchGpuStatus() {
    try {
      const res = await fetch("/api/field-die/gpu", { cache: "no-store" });
      if (res.ok) gpuStatus = await res.json();
    } catch (_) {
      gpuStatus = null;
    }
    return gpuStatus;
  }

  async function launchGpu() {
    const status = document.getElementById("nexus-sdf-menu-status");
    if (status) status.textContent = "Launching GPU Field Die…";
    try {
      const res = await fetch("/api/field-die/gpu-launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ extended: true, infinite_sdf: true }),
      });
      const doc = await res.json();
      if (status) {
        status.textContent = doc.ok
          ? `GPU pid ${doc.pid || "—"} · log ${(doc.log || "").split("/").pop()}`
          : `Launch failed: ${doc.error || res.status}`;
      }
      global.NexusRtxZero?.toast?.(doc.ok ? "Field Die on GPU" : "GPU launch failed", doc.ok ? "ok" : "err");
    } catch (e) {
      if (status) status.textContent = `Launch error: ${e}`;
    }
  }

  function jumpTab(tab) {
    if (!tab) return;
    if (typeof global.showView === "function") {
      global.showView(tab);
    } else {
      global.location.hash = `#${tab}`;
    }
    toggle(false);
  }

  function onItemClick(item) {
    if (item.action === "gpu") {
      launchGpu();
      return;
    }
    jumpTab(item.tab);
  }

  function toggle(force) {
    open = typeof force === "boolean" ? force : !open;
    const panel = document.getElementById("nexus-sdf-menu-panel");
    if (panel) panel.classList.toggle("open", open);
    if (open) {
      drawRadialMenu(document.getElementById("nexus-sdf-menu-canvas"));
      fetchGpuStatus().then(() => {
        const st = document.getElementById("nexus-sdf-menu-status");
        if (!st || !gpuStatus) return;
        const g = gpuStatus.gpu || gpuStatus;
        st.textContent = g.binary
          ? `Prebuilt GPU ready · ${g.binary.split("/").pop()}`
          : g.panel_only
            ? "RTX Zero panel — no build deps"
            : "RTX panel + SDF chrome";
      });
    }
  }

  function mount() {
    const header = document.querySelector("header.app-header h1");
    if (!header || document.getElementById("nexus-sdf-menu-root")) return;
    const root = document.createElement("div");
    root.id = "nexus-sdf-menu-root";
    root.innerHTML = `
      <button type="button" class="nexus-sdf-menu-btn" id="nexus-sdf-menu-toggle" title="SDF ops menu — GPU Field Die + tab jumps">SDF · GPU</button>
      <div class="nexus-sdf-menu-panel" id="nexus-sdf-menu-panel">
        <canvas class="nexus-sdf-menu-canvas" id="nexus-sdf-menu-canvas" width="200" height="200" aria-hidden="true"></canvas>
        <div class="nexus-sdf-menu-list" id="nexus-sdf-menu-list"></div>
        <div class="nexus-sdf-menu-status" id="nexus-sdf-menu-status">Zero-cost SDF chrome — launch runs on video card</div>
      </div>`;
    header.appendChild(root);
    const list = document.getElementById("nexus-sdf-menu-list");
    ITEMS.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `nexus-sdf-menu-item${item.gpu ? " gpu" : ""}`;
      btn.textContent = item.label;
      btn.addEventListener("click", () => onItemClick(item));
      list.appendChild(btn);
    });
    document.getElementById("nexus-sdf-menu-toggle")?.addEventListener("click", () => toggle());
    document.addEventListener("click", (ev) => {
      if (!open) return;
      if (!root.contains(ev.target)) toggle(false);
    });
  }

  function boot() {
    mount();
  }

  global.NexusSdfMenu = { toggle, launchGpu, drawRadialMenu, fetchGpuStatus };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);