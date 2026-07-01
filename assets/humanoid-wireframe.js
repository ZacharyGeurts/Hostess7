/* Humanoid wireframe — 60fps render · training 85% blast */
(function (global) {
  "use strict";

  const WIREFRAME_FPS = 60;
  const FRAME_MS = 1000 / WIREFRAME_FPS;
  const HUD_REFRESH_MS = 400;
  const TRAIN_BLAST_MS = 250;
  const TRAIN_INTENSITY_DEFAULT = 0.85;
  const TRAIN_READY_VERDICTS = new Set(["train_continue", "technique_ready"]);
  const TRAIN_POPUP_NAME = "nexus-humanoid-train";
  const TRAIN_DISMISS_KEY = "nexus-train-gui-dismissed";

  const JOINTS = {
    head: [0, -0.38],
    neck: [0, -0.28],
    spine_upper: [0, -0.22],
    spine_mid: [0, -0.18],
    spine_lower: [0, -0.14],
    chest: [0, -0.12],
    hip: [0, 0.08],
    shoulder_l: [-0.14, -0.22],
    shoulder_r: [0.14, -0.22],
    elbow_l: [-0.2, -0.04],
    elbow_r: [0.2, -0.04],
    wrist_l: [-0.23, 0.03],
    wrist_r: [0.23, 0.03],
    hand_l: [-0.26, 0.1],
    hand_r: [0.26, 0.1],
    knee_l: [-0.1, 0.3],
    knee_r: [0.1, 0.3],
    ankle_l: [-0.105, 0.4],
    ankle_r: [0.105, 0.4],
    foot_l: [-0.11, 0.5],
    foot_r: [0.11, 0.5],
    toe_l: [-0.11, 0.54],
    toe_r: [0.11, 0.54],
  };
  const BONES = [
    ["head", "neck"], ["neck", "spine_upper"], ["spine_upper", "spine_mid"],
    ["spine_mid", "spine_lower"], ["spine_lower", "chest"], ["chest", "hip"],
    ["neck", "shoulder_l"], ["shoulder_l", "elbow_l"], ["elbow_l", "wrist_l"], ["wrist_l", "hand_l"],
    ["neck", "shoulder_r"], ["shoulder_r", "elbow_r"], ["elbow_r", "wrist_r"], ["wrist_r", "hand_r"],
    ["hip", "knee_l"], ["knee_l", "ankle_l"], ["ankle_l", "foot_l"], ["foot_l", "toe_l"],
    ["hip", "knee_r"], ["knee_r", "ankle_r"], ["ankle_r", "foot_r"], ["foot_r", "toe_r"],
  ];

  let raf = 0;
  let phase = 0;
  let lastFrame = 0;
  let lastDoc = null;
  let catalog = [];
  let blastBusy = false;
  let fullBlast = true;
  let wireframeFps = WIREFRAME_FPS;
  let trainIntensity = TRAIN_INTENSITY_DEFAULT;
  let displayFps = 0;
  let frameCount = 0;
  let fpsTimer = 0;
  let blastTicks = 40;
  let blastTimer = 0;
  let hudTimer = 0;
  let trainModalOpen = false;
  let lastPromptVerdict = "";
  let trainPopupWin = null;

  function $(id) {
    return document.getElementById(id);
  }

  function stanceOffsets(stance) {
    const s = String(stance || "orthodox").toLowerCase();
    if (s === "southpaw") {
      return { hand_l: [0.04, -0.02], hand_r: [-0.06, 0.04], foot_l: [0.03, 0], foot_r: [-0.02, 0] };
    }
    if (s === "clinch") {
      return { hand_l: [0.12, -0.08], hand_r: [-0.12, -0.08], elbow_l: [0.08, -0.05], elbow_r: [-0.08, -0.05] };
    }
    if (s === "static") {
      return { hand_l: [0, 0.06], hand_r: [0, 0.06] };
    }
    if (s === "aggressive") {
      return { hand_r: [0.08, -0.06], hand_l: [-0.02, 0.02], foot_r: [0.05, -0.02] };
    }
    return { hand_r: [0.05, -0.03], foot_l: [0.02, 0] };
  }

  function motionOffset(motions, joint) {
    if (!motions || !motions.length) return [0, 0];
    let dx = 0;
    let dy = 0;
    for (const m of motions) {
      const zoneMap = {
        hands: ["hand_l", "hand_r", "wrist_l", "wrist_r"],
        elbows: ["elbow_l", "elbow_r"],
        shoulders: ["shoulder_l", "shoulder_r"],
        spine: ["spine_upper", "spine_mid", "spine_lower", "chest"],
        centerline: ["chest", "spine_mid", "hip"],
        hips: ["hip"],
        knees: ["knee_l", "knee_r"],
        ankles: ["ankle_l", "ankle_r"],
        feet: ["foot_l", "foot_r"],
        toes: ["toe_l", "toe_r"],
        head: ["head", "neck"],
      };
      const zones = zoneMap[m.zone] || [];
      if (!zones.includes(joint)) continue;
      dx += (m.norm_x || 0) * (m.weight || 0) * 0.18;
      dy -= (m.norm_z || 0) * (m.weight || 0) * 0.12;
    }
    return [dx, dy];
  }

  function colorForKind(kind, wireframe) {
    const k = wireframe || kind || "training";
    if (k === "hostile" || kind === "hostile") return { stroke: "#ef4444", glow: "rgba(239,68,68,0.55)", fill: "#7f1d1d" };
    if (k === "sparring" || kind === "sparring") return { stroke: "#a78bfa", glow: "rgba(167,139,250,0.4)", fill: "#4c1d95" };
    return { stroke: "#f59e0b", glow: "rgba(245,158,11,0.35)", fill: "#78350f" };
  }

  function drawGrid(ctx, w, h) {
    ctx.save();
    ctx.strokeStyle = "rgba(56,189,248,0.12)";
    ctx.lineWidth = 1;
    const step = Math.max(24, Math.floor(w / 20));
    for (let x = 0; x <= w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, h * 0.42);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = h * 0.42; y <= h; y += step * 0.65) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawHumanoid(ctx, cx, cy, scale, opts) {
    const {
      stroke = "#38bdf8",
      glow = "rgba(56,189,248,0.45)",
      jointAmps = {},
      motions = [],
      stance = "orthodox",
      pulse = 0,
      label = "",
      mirror = false,
    } = opts || {};
    const off = stanceOffsets(stance);
    const m = mirror ? -1 : 1;

    function pt(name) {
      const base = JOINTS[name];
      if (!base) return [cx, cy];
      const so = off[name] || [0, 0];
      const mo = motionOffset(motions, name);
      const amp = jointAmps[name] || 0;
      const px = cx + (base[0] * m + so[0] * m + mo[0] * m) * scale;
      const py = cy + (base[1] + so[1] + mo[1]) * scale;
      return [px, py, amp];
    }

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const [a, b] of BONES) {
      const p1 = pt(a);
      const p2 = pt(b);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.shadowColor = glow;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.stroke();
    }

    for (const name of Object.keys(JOINTS)) {
      const p = pt(name);
      const amp = p[2] || 0;
      const r = 3 + amp * 7 + (amp > 0.5 ? Math.sin(pulse) * 1.5 : 0);
      ctx.shadowBlur = 8 + amp * 14;
      ctx.fillStyle = amp > 0.55 ? "#f0d060" : stroke;
      ctx.beginPath();
      ctx.arc(p[0], p[1], r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;

    if (label) {
      ctx.fillStyle = stroke;
      ctx.font = `${Math.max(10, scale * 0.22)}px system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(label, cx, cy + scale * 0.62);
    }
    ctx.restore();
  }

  function motionVerdict(doc) {
    return String(
      doc?.motion_verdict || doc?.iron_plate_motion?.motion_verdict || ""
    ).trim();
  }

  function isTrainReady(doc) {
    return TRAIN_READY_VERDICTS.has(motionVerdict(doc));
  }

  function trainReadyLabel(doc) {
    const v = motionVerdict(doc);
    const phys = doc?.physics_mode !== false;
    if (v === "technique_ready") {
      return phys ? "Technique ready — gravity-coupled chamber saturated" : "Technique ready — Matrix chamber saturated";
    }
    if (v === "train_continue") {
      return phys ? "Assemblage supports physics training under gravity" : "Assemblage supports continued Matrix training";
    }
    return phys ? "Physics motion chamber ready" : "Motion chamber ready";
  }

  function gravityOffsetY(doc, scale) {
    const ps = doc?.physics_state || doc?.training?.physics_sim || {};
    const ground = 0.12;
    const comY = Number(ps.com_y ?? ground);
    const grounded = ps.grounded !== false;
    const vy = Number(ps.com_vy ?? 0);
    const lift = grounded ? 0 : Math.max(-0.08, Math.min(0.12, (ground - comY) * 0.35));
    const bounce = grounded && Math.abs(vy) > 0.02 ? Math.sin(phase * 2) * vy * scale * 0.08 : 0;
    return (lift + bounce) * scale;
  }

  function trainDismissedVerdict() {
    try {
      return sessionStorage.getItem(TRAIN_DISMISS_KEY) || "";
    } catch (_) {
      return "";
    }
  }

  function setTrainDismissed(verdict) {
    try {
      sessionStorage.setItem(TRAIN_DISMISS_KEY, verdict || "");
    } catch (_) {}
  }

  function drawArenaOnCanvas(canvas, doc) {
    if (!canvas) return;
    const wrap = canvas.parentElement;
    const rect = wrap ? wrap.getBoundingClientRect() : canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(320, Math.floor(rect.width));
    const h = Math.max(200, Math.floor(rect.height));
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "#060a14");
    grad.addColorStop(1, "#0a1220");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
    drawGrid(ctx, w, h);

    const envMesh = doc?.environment_mesh || doc?.training_floor?.floor?.environment || {};
    const walls = envMesh.walls || [];
    const cover = envMesh.cover || [];
    for (const wall of walls) {
      const wx = w * (wall.x ?? 0.5);
      const wy = h * (wall.y ?? 0.5);
      ctx.strokeStyle = "rgba(100,116,139,0.55)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(wx - w * 0.08, wy);
      ctx.lineTo(wx + w * 0.08, wy);
      ctx.stroke();
    }
    for (const c of cover) {
      const cx = w * (c.x ?? 0.5);
      const cy = h * (c.y ?? 0.5);
      const ch = h * (c.height ?? 0.3) * 0.5;
      ctx.fillStyle = "rgba(71,85,105,0.45)";
      ctx.strokeStyle = "rgba(148,163,184,0.5)";
      ctx.lineWidth = 1;
      ctx.fillRect(cx - w * 0.04, cy - ch, w * 0.08, ch * 2);
      ctx.strokeRect(cx - w * 0.04, cy - ch, w * 0.08, ch * 2);
    }

    const arena = doc?.arena || {};
    const anchor = arena.fighter_anchor || { x: 0.32, y: 0.58 };
    const fighterX = w * anchor.x;
    const scale = Math.min(w, h) * 0.42;
    const gravDy = doc?.physics_mode !== false ? gravityOffsetY(doc, 1) : 0;
    const fighterY = h * anchor.y + gravDy;

    if (doc?.physics_mode !== false) {
      const g = Number(doc?.gravity_m_s2 ?? doc?.physics_state?.gravity_m_s2 ?? 9.80665);
      const gx = fighterX - scale * 0.55;
      const gy = fighterY - scale * 0.35;
      ctx.strokeStyle = "rgba(56,189,248,0.55)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(gx, gy);
      ctx.lineTo(gx, gy + scale * 0.22);
      ctx.stroke();
      ctx.fillStyle = "rgba(56,189,248,0.85)";
      ctx.beginPath();
      ctx.moveTo(gx, gy + scale * 0.22);
      ctx.lineTo(gx - 5, gy + scale * 0.14);
      ctx.lineTo(gx + 5, gy + scale * 0.14);
      ctx.fill();
      ctx.font = "10px system-ui,sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(`g ${g.toFixed(2)} m/s²`, gx - 8, gy - 6);
    }

    drawHumanoid(ctx, fighterX, fighterY, scale, {
      stroke: "#38bdf8",
      glow: "rgba(56,189,248,0.5)",
      jointAmps: doc?.joint_amplitudes || {},
      motions: doc?.body_motion || [],
      stance: "orthodox",
      pulse: phase,
      label: doc?.active_label ? `YOU · ${doc.active_label}` : "YOU · Universal Protector",
    });

    const opps = doc?.opponents || [];
    for (const opp of opps) {
      const col = colorForKind(opp.kind, opp.wireframe);
      const ox = w * (opp.arena_x ?? 0.75);
      const oy = h * (opp.arena_y ?? 0.52);
      drawHumanoid(ctx, ox, oy, scale * 0.92, {
        stroke: col.stroke,
        glow: col.glow,
        stance: opp.stance || "orthodox",
        pulse: phase + 1,
        label: opp.label || opp.id,
        mirror: opp.stance === "southpaw",
      });
      if (opp.live && opp.bearing_deg != null) {
        ctx.strokeStyle = "rgba(239,68,68,0.35)";
        ctx.setLineDash([4, 6]);
        ctx.beginPath();
        ctx.moveTo(fighterX, fighterY);
        ctx.lineTo(ox, oy);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    const mv = doc?.spatial?.movement_vector;
    const verdict = doc?.motion_verdict || doc?.iron_plate_motion?.motion_verdict;
    const ironClad = doc?.iron_clad ?? doc?.iron_plate_motion?.iron_clad;
    const asmScore = doc?.assemblage_score ?? doc?.assemblage_remaining?.assemblage_score;
    if (verdict) {
      const verdictColor = ironClad
        ? (verdict.includes("engage") || verdict.includes("defend") ? "#ef4444" : "#38bdf8")
        : "#f59e0b";
      ctx.fillStyle = verdictColor;
      ctx.font = "bold 11px system-ui,sans-serif";
      ctx.textAlign = "left";
      const asmTxt = asmScore != null ? ` · asm ${Math.round(asmScore * 100)}%` : "";
      ctx.fillText(`${ironClad ? "IRON-CLAD" : "HOLD"} · ${String(verdict).replace(/_/g, " ").toUpperCase()}${asmTxt}`, 12, 28);
    }
    if (mv?.approach && opps.some((o) => o.live)) {
      ctx.fillStyle = "rgba(239,68,68,0.85)";
      ctx.font = "11px system-ui,sans-serif";
      ctx.fillText("APPROACH VECTOR", 12, h - 12);
    }

    const sp = doc?.sense_plates || {};
    const visLive = doc?.vision_live ?? sp?.vision?.live ?? doc?.full_assemblage_meld?.vision_live;
    const earLive = doc?.hearing_live ?? sp?.hearing?.live ?? doc?.full_assemblage_meld?.hearing_live;
    const brainOk = doc?.brain_verified ?? doc?.hostess7_brain?.verification?.verified;
    const brainTag = brainOk ? "H7✓" : "H7…";
    const plateTag = `${brainTag} · EYE ${visLive ? "✓" : "…"} · EAR ${earLive ? "✓" : "…"}`;
    ctx.fillStyle = visLive && earLive ? "rgba(110,231,183,0.85)" : "rgba(156,179,212,0.75)";
    ctx.font = "10px system-ui,sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(plateTag, 12, h - 12);

    const trainPct = Math.round(trainIntensity * 100);
    const fused = doc?.full_assemblage_meld?.fused_score ?? doc?.assemblage_score;
    const fusedTxt = fused != null ? ` · asm ${Math.round(fused * 100)}%` : "";
    ctx.fillStyle = "rgba(156,179,212,0.7)";
    ctx.textAlign = "right";
    ctx.fillText(`${wireframeFps}fps · training ${trainPct}% · ${displayFps}fps measured${fusedTxt}`, w - 10, 14);
  }

  function drawArena(doc) {
    const canvases = document.querySelectorAll("#humanoid-wireframe-canvas, .humanoid-wireframe-canvas, #humanoid-train-modal-canvas");
    if (!canvases.length) return;
    canvases.forEach((canvas) => drawArenaOnCanvas(canvas, doc));
  }

  function ensureTrainModal() {
    if ($("humanoid-train-modal")) return;
    const modal = document.createElement("div");
    modal.id = "humanoid-train-modal";
    modal.className = "humanoid-train-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "humanoid-train-modal-title");
    modal.innerHTML = `
      <div class="humanoid-train-modal__panel">
        <div class="humanoid-train-modal__head">
          <div>
            <h2 id="humanoid-train-modal-title">Motion ready — physics training</h2>
            <p id="humanoid-train-modal-sub">Gravity-coupled body lattice — iron-clad assemblage supports training.</p>
          </div>
          <span class="humanoid-train-modal__badge" id="humanoid-train-modal-badge">TRAIN READY</span>
        </div>
        <div class="humanoid-train-modal__canvas-wrap">
          <canvas id="humanoid-train-modal-canvas" class="humanoid-wireframe-canvas" aria-label="Training wireframe modal"></canvas>
        </div>
        <div class="humanoid-train-modal__actions">
          <button type="button" class="primary" id="humanoid-train-modal-go">Begin training</button>
          <button type="button" id="humanoid-train-modal-popup">Open training window</button>
          <button type="button" id="humanoid-train-modal-data">Data window</button>
          <button type="button" id="humanoid-train-modal-dismiss">Dismiss</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.addEventListener("click", (ev) => {
      if (ev.target === modal) closeTrainModal();
    });
    $("humanoid-train-modal-go")?.addEventListener("click", async () => {
      await trainBlast();
      await refresh();
      if (lastDoc) drawArena(lastDoc);
      closeTrainModal(false);
    });
    $("humanoid-train-modal-popup")?.addEventListener("click", () => {
      openTrainPopupWindow(lastDoc);
    });
    $("humanoid-train-modal-data")?.addEventListener("click", () => openDataWindow());
    $("humanoid-train-modal-dismiss")?.addEventListener("click", () => closeTrainModal(true));
  }

  function closeTrainModal(dismiss) {
    const modal = $("humanoid-train-modal");
    if (modal) modal.classList.remove("open");
    trainModalOpen = false;
    $("humanoid-arena")?.classList.remove("humanoid-arena--train-ready");
    if (dismiss && lastDoc) setTrainDismissed(motionVerdict(lastDoc));
  }

  function openTrainPopupWindow(doc) {
    const url = `${location.origin}/humanoid-train.html`;
    if (trainPopupWin && !trainPopupWin.closed) {
      trainPopupWin.focus();
      try {
        trainPopupWin.postMessage({ type: "nexus-humanoid-train-ready", doc }, location.origin);
      } catch (_) {}
      return trainPopupWin;
    }
    if (global.QueenProgramLaunch?.open) {
      global.QueenProgramLaunch.open(url, {
        id: TRAIN_POPUP_NAME,
        title: "Training Chamber",
        icon: "/assets/hostess7-training-chamber.svg",
      });
      return null;
    }
    trainPopupWin = window.open(
      url,
      TRAIN_POPUP_NAME,
      "width=980,height=760,menubar=no,toolbar=no,location=no,status=no"
    );
    if (trainPopupWin && doc) {
      setTimeout(() => {
        try {
          trainPopupWin.postMessage({ type: "nexus-humanoid-train-ready", doc }, location.origin);
        } catch (_) {}
      }, 400);
    }
    return trainPopupWin;
  }

  function focusCommandArena() {
    if (typeof global.showView === "function") global.showView("command");
    const arena = $("humanoid-arena");
    if (arena) {
      arena.classList.add("humanoid-arena--train-ready");
      arena.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function openTrainGui(doc) {
    if (!doc || !isTrainReady(doc)) return;
    ensureTrainModal();
    const verdict = motionVerdict(doc);
    const sub = $("humanoid-train-modal-sub");
    const badge = $("humanoid-train-modal-badge");
    if (sub) sub.textContent = doc?.iron_plate_motion?.reason || trainReadyLabel(doc);
    if (badge) {
      badge.textContent = verdict === "technique_ready" ? "TECHNIQUE READY" : "TRAIN CONTINUE";
    }
    focusCommandArena();
    $("humanoid-train-modal")?.classList.add("open");
    trainModalOpen = true;
    drawArena(doc);
    openTrainPopupWindow(doc);
    const popupSub = document.getElementById("humanoid-train-popup-sub");
    const popupBadge = document.getElementById("humanoid-train-popup-badge");
    if (popupSub) popupSub.textContent = doc?.iron_plate_motion?.reason || trainReadyLabel(doc);
    if (popupBadge) {
      popupBadge.textContent = verdict === "technique_ready" ? "TECHNIQUE READY" : "TRAIN CONTINUE";
    }
  }

  function maybeOpenTrainGui(doc) {
    if (!doc) return;
    const verdict = motionVerdict(doc);
    if (!isTrainReady(doc)) {
      if (!isTrainReady({ motion_verdict: lastPromptVerdict })) {
        closeTrainModal(false);
      }
      lastPromptVerdict = verdict;
      return;
    }
    if (trainGuiDismissedVerdict() === verdict && !trainModalOpen) {
      lastPromptVerdict = verdict;
      return;
    }
    if (verdict !== lastPromptVerdict || !trainModalOpen) {
      openTrainGui(doc);
    }
    lastPromptVerdict = verdict;
  }

  function applyDocMeta(doc) {
    if (!doc) return;
    if (doc.wireframe_fps) wireframeFps = doc.wireframe_fps;
    if (doc.train_intensity != null) trainIntensity = doc.train_intensity;
    if (doc.train_blast_ticks) blastTicks = doc.train_blast_ticks;
    if (doc.full_blast != null) fullBlast = !!doc.full_blast;
  }

  function updateHud(doc) {
    const voiceEl = document.getElementById("humanoid-train-voice");
    if (voiceEl && doc.training_room?.voice) {
      voiceEl.textContent = doc.training_room.voice;
    } else if (voiceEl && doc.earth_mandate?.role) {
      voiceEl.textContent = `I am Hostess 7 — ${doc.earth_mandate.role}.`;
    }
    const status = $("humanoid-motion-status");
    const prof = $("humanoid-motion-prof");
    const chips = $("humanoid-opponent-chips");
    if (status) {
      const profPct = Math.round((doc?.active_proficiency || 0) * 100);
      const ticks = doc?.total_training_ticks ?? 0;
      const oppN = doc?.opponent_count ?? 0;
      const phys = doc?.physics_mode !== false;
      const ps = doc?.physics_state || {};
      const quote = phys
        ? (doc?.training?.physics_sim?.grounded ? "Grounded stance" : "Airborne — gravity sim")
        : (doc?.matrix_quote || "Matrix skill load ready");
      const trainPct = Math.round(trainIntensity * 100);
      const gTag = phys ? ` · g ${Number(doc?.gravity_m_s2 ?? ps.gravity_m_s2 ?? 9.81).toFixed(1)} m/s²` : "";
      const stabTag = phys && ps.stance_stability != null
        ? ` · stability ${Math.round(Number(ps.stance_stability) * 100)}%`
        : "";
      const verdict = doc?.motion_verdict || doc?.iron_plate_motion?.motion_verdict;
      const ironClad = doc?.iron_clad ?? doc?.iron_plate_motion?.iron_clad;
      const asm = doc?.assemblage_score ?? doc?.assemblage_remaining?.assemblage_score;
      const motionTag = verdict
        ? ` · ${ironClad ? "iron-clad" : "hold"} ${String(verdict).replace(/_/g, " ")}${asm != null ? ` ${Math.round(asm * 100)}%` : ""}`
        : "";
      const lifeVerdict = doc?.life_sustain_verdict || doc?.creatable_lives?.sustain?.verdict;
      const lifeTag = lifeVerdict ? ` · ${String(lifeVerdict).replace(/_/g, " ")}` : "";
      const sp = doc?.sense_plates || {};
      const vis = doc?.vision_live ?? sp?.vision?.live;
      const ear = doc?.hearing_live ?? sp?.hearing?.live;
      const h7 = doc?.brain_verified ?? doc?.hostess7_brain?.verification?.verified;
      const senseTag = ` · H7 ${h7 ? "verified" : "…"} · eye ${vis ? "live" : "…"} · ear ${ear ? "live" : "…"}`;
      status.textContent = `${quote} · ${profPct}% · ${ticks} ticks · ${oppN} opponents · training ${trainPct}% · ${wireframeFps}fps${gTag}${stabTag}${senseTag}${motionTag}${lifeTag}`;
    }
    if (prof) {
      prof.style.width = `${Math.round((doc?.active_proficiency || 0) * 100)}%`;
    }
    if (chips) {
      chips.innerHTML = (doc?.opponents || []).map((o) => {
        const cls = o.kind === "hostile" ? "hostile" : o.kind === "sparring" ? "sparring" : "training";
        const extra = o.live ? ` · ${o.bearing_deg ?? "—"}° · ${o.distance_km ?? "—"} km` : "";
        return `<span class="humanoid-opp-chip ${cls}">${o.label}${extra}</span>`;
      }).join("");
    }
    const sel = $("humanoid-skill-select");
    if (sel && catalog.length && !sel.dataset.filled) {
      sel.innerHTML = catalog.map((s) =>
        `<option value="${s.id}">${s.label} (${s.family})</option>`
      ).join("");
      if (doc?.active_skill) sel.value = doc.active_skill;
      sel.dataset.filled = "1";
    }
  }

  async function fetchWireframe() {
    const res = await fetch("/api/humanoid-motion/wireframe", { credentials: "same-origin" });
    if (!res.ok) throw new Error("wireframe fetch failed");
    return res.json();
  }

  async function fetchCatalog() {
    const res = await fetch("/api/humanoid-motion/catalog", { credentials: "same-origin" });
    if (res.ok) {
      const j = await res.json();
      catalog = j.skills || [];
    }
  }

  async function refresh() {
    try {
      lastDoc = await fetchWireframe();
      applyDocMeta(lastDoc);
      updateHud(lastDoc);
      maybeOpenTrainGui(lastDoc);
    } catch (_) {}
  }

  function tick(now) {
    raf = requestAnimationFrame(tick);
    if (!lastFrame) lastFrame = now;
    const elapsed = now - lastFrame;
    const frameMs = 1000 / (wireframeFps || WIREFRAME_FPS);
    if (elapsed < frameMs) return;
    lastFrame = now - (elapsed % frameMs);

    if (!fpsTimer) fpsTimer = now;
    frameCount += 1;
    if (now - fpsTimer >= 1000) {
      displayFps = frameCount;
      frameCount = 0;
      fpsTimer = now;
    }
    phase += 0.08 * (elapsed / frameMs);
    if (lastDoc) drawArena(lastDoc);

    if (fullBlast && now - blastTimer >= TRAIN_BLAST_MS) {
      blastTimer = now;
      trainBlast().catch(() => {});
    }
    if (now - hudTimer >= HUD_REFRESH_MS) {
      hudTimer = now;
      refresh().catch(() => {});
    }
  }

  async function runTrainingRoom(sub, extra) {
    const q = extra?.skill ? `?skill=${encodeURIComponent(extra.skill)}` : "";
    const getSubs = new Set(["needs", "try-body", "complete-all"]);
    try {
      const res = await fetch(`/api/hostess7/training-room/${sub}${q}`, {
        method: getSubs.has(sub) ? "GET" : "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: sub === "combat" ? JSON.stringify({ action: "combat_drill", skill: extra?.skill }) : undefined,
      });
      const doc = await res.json();
      const voice = doc.voice || doc.needs?.voice || doc.message || "";
      const el = document.getElementById("humanoid-train-voice");
      if (el && voice) el.textContent = voice;
      if (sub === "try-body" || sub === "combat" || sub === "complete-all") await refresh();
      return doc;
    } catch (e) {
      console.warn("training room", e);
      return null;
    }
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return res.json();
  }

  async function trainBlast() {
    if (blastBusy) return;
    const sid = $("humanoid-skill-select")?.value || lastDoc?.active_skill;
    blastBusy = true;
    try {
      const out = await postJson("/api/humanoid-motion/train-blast", {
        skill_id: sid || undefined,
        ticks: blastTicks,
      });
      if (out?.ok && out.skill) {
        if (!lastDoc) lastDoc = {};
        lastDoc.active_skill = out.skill.id;
        lastDoc.active_label = out.skill.label;
        lastDoc.active_proficiency = out.skill.proficiency;
        lastDoc.total_training_ticks = out.total_ticks;
        if (out.train_intensity != null) trainIntensity = out.train_intensity;
        updateHud(lastDoc);
      }
    } finally {
      blastBusy = false;
    }
  }

  function openDataWindow() {
    const url = `${location.origin}/humanoid-data.html`;
    if (global.QueenProgramLaunch?.open) {
      return global.QueenProgramLaunch.open(url, {
        id: "nexus-humanoid-data",
        title: "Humanoid Data",
        icon: "/assets/hostess7-training-chamber.svg",
      });
    }
    const win = window.open(url, "nexus-humanoid-data", "width=1120,height=900,menubar=no,toolbar=no,location=no,status=no");
    if (win) win.focus();
    return win;
  }

  function bindControls() {
    $("humanoid-data-window-btn")?.addEventListener("click", openDataWindow);
    $("humanoid-hands-btn")?.addEventListener("click", () => {
      const url = `${location.origin}/hands-attachments.html`;
      if (global.QueenProgramLaunch?.open) {
        global.QueenProgramLaunch.open(url, {
          id: "nexus-hands-attachments",
          title: "Hands & Attachments",
          icon: "/assets/hostess7-hands-chamber.svg",
        });
        return;
      }
      window.open(url, "nexus-hands-attachments", "noopener,width=1100,height=720");
    });
    $("humanoid-try-body-btn")?.addEventListener("click", () => runTrainingRoom("try-body"));
    $("humanoid-combat-room-btn")?.addEventListener("click", () => {
      const sid = $("humanoid-skill-select")?.value || "wing_chun";
      runTrainingRoom("combat", { skill: sid });
    });
    $("humanoid-needs-btn")?.addEventListener("click", () => runTrainingRoom("needs"));
    $("humanoid-complete-all-btn")?.addEventListener("click", () => {
      const sid = $("humanoid-skill-select")?.value || "wing_chun";
      runTrainingRoom("complete-all", { skill: sid });
    });
    $("humanoid-load-btn")?.addEventListener("click", async () => {
      const sid = $("humanoid-skill-select")?.value;
      if (!sid) return;
      await postJson("/api/humanoid-motion/load", { skill_id: sid });
      await refresh();
      if (lastDoc) drawArena(lastDoc);
    });
    $("humanoid-train-btn")?.addEventListener("click", async () => {
      const sid = $("humanoid-skill-select")?.value;
      await postJson("/api/humanoid-motion/train-blast", { skill_id: sid, ticks: blastTicks * 4 });
      await refresh();
      if (lastDoc) drawArena(lastDoc);
    });
  }

  function boot() {
    if (!$("humanoid-wireframe-canvas")) return;
    ensureTrainModal();
    bindControls();
    window.addEventListener("message", (ev) => {
      if (ev.origin !== location.origin) return;
      if (ev.data?.type === "nexus-humanoid-train-ready" && ev.data.doc) {
        lastDoc = ev.data.doc;
        applyDocMeta(lastDoc);
        updateHud(lastDoc);
        drawArena(lastDoc);
      }
    });
    fetchCatalog().then(() => refresh().then(() => {
      if (lastDoc) drawArena(lastDoc);
    })).catch(() => {});
    cancelAnimationFrame(raf);
    lastFrame = 0;
    fpsTimer = 0;
    frameCount = 0;
    blastTimer = 0;
    hudTimer = 0;
    raf = requestAnimationFrame(tick);
    window.addEventListener("resize", () => lastDoc && drawArena(lastDoc));
  }

  global.NexusHumanoidWireframe = {
    boot,
    refresh,
    drawArena,
    trainBlast,
    openDataWindow,
    openTrainGui,
    isTrainReady,
    motionVerdict,
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);