import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.getElementById("wireframe-canvas");
const hud = document.getElementById("wireframe-hud");
const detail = document.getElementById("node-detail");

if (!canvas) {
  console.warn("wireframe canvas missing");
} else {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x060a12, 1);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x060a12, 0.028);

  const camera = new THREE.PerspectiveCamera(52, 1, 0.1, 400);
  camera.position.set(14, 10, 18);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.maxDistance = 80;
  controls.minDistance = 4;

  const ambient = new THREE.AmbientLight(0x8fb4d9, 0.45);
  scene.add(ambient);
  const key = new THREE.DirectionalLight(0xf4a261, 0.85);
  key.position.set(10, 18, 8);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xe76f8a, 0.35);
  rim.position.set(-12, 4, -10);
  scene.add(rim);

  const grid = new THREE.GridHelper(48, 48, 0x243552, 0x152033);
  grid.position.y = -5.2;
  scene.add(grid);

  const coreRing = new THREE.Mesh(
    new THREE.TorusGeometry(1.2, 0.03, 8, 64),
    new THREE.MeshBasicMaterial({ color: 0xe76f8a, transparent: true, opacity: 0.5 }),
  );
  coreRing.rotation.x = Math.PI / 2;
  scene.add(coreRing);

  const nodeMeshes = new Map();
  const edgeLines = [];
  const labelSprites = [];
  let graphData = null;
  let selectedId = null;
  let pulse = 0;

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function resize() {
    const wrap = canvas.parentElement;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function hexColor(c) {
    if (!c) return 0x64748b;
    const s = String(c).replace("#", "");
    return parseInt(s.length === 6 ? s : "64748b", 16);
  }

  function makeWireNode(node) {
    const group = new THREE.Group();
    const scale = node.group === "core" ? 1.35
      : node.group === "agents7" ? (node.kind === "agents7_hub" ? 1.05 : 0.72)
      : node.group === "connected" ? 0.95 : 0.65;
    const geo = node.group === "core"
      ? new THREE.IcosahedronGeometry(scale, 1)
      : new THREE.OctahedronGeometry(scale, 0);
    const color = hexColor(node.color);
    const mat = new THREE.MeshBasicMaterial({
      color,
      wireframe: true,
      transparent: true,
      opacity: 0.92,
    });
    const mesh = new THREE.Mesh(geo, mat);
    group.add(mesh);

    const glow = new THREE.Mesh(
      new THREE.SphereGeometry(scale * 0.35, 8, 8),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.18 }),
    );
    group.add(glow);

    if (node.group === "core") {
      const ring2 = new THREE.Mesh(
        new THREE.TorusKnotGeometry(1.6, 0.04, 96, 12),
        new THREE.MeshBasicMaterial({ color: 0x60a5fa, wireframe: true, transparent: true, opacity: 0.35 }),
      );
      group.add(ring2);
    }

    group.position.set(node.x, node.y, node.z);
    group.userData = { id: node.id, node };
    return group;
  }

  function makeLabel(text, pos) {
    const c = document.createElement("canvas");
    const ctx = c.getContext("2d");
    const label = String(text || "").slice(0, 20);
    ctx.font = "bold 22px Segoe UI, system-ui, sans-serif";
    const tw = ctx.measureText(label).width;
    c.width = Math.ceil(tw + 16);
    c.height = 34;
    ctx.font = "bold 22px Segoe UI, system-ui, sans-serif";
    ctx.fillStyle = "rgba(10,15,24,0.75)";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = "#e8f2ff";
    ctx.fillText(label, 8, 24);
    const tex = new THREE.CanvasTexture(c);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
    const sprite = new THREE.Sprite(mat);
    sprite.position.copy(pos);
    sprite.position.y += 1.1;
    sprite.scale.set(c.width / 80, c.height / 80, 1);
    sprite.userData = { label: true };
    return sprite;
  }

  function clearGraph() {
    for (const g of nodeMeshes.values()) scene.remove(g);
    nodeMeshes.clear();
    for (const l of edgeLines) scene.remove(l);
    edgeLines.length = 0;
    for (const s of labelSprites) scene.remove(s);
    labelSprites.length = 0;
  }

  function buildGraph(graph) {
    clearGraph();
    graphData = graph;
    const nodes = graph.nodes || [];
    const nodeById = new Map(nodes.map((n) => [n.id, n]));

    for (const node of nodes) {
      const g = makeWireNode(node);
      scene.add(g);
      nodeMeshes.set(node.id, g);
      if (node.group === "core" || node.group === "agents7" || node.group === "connected" || node.group === "training_track" || node.kind === "chamber") {
        const sp = makeLabel(node.label, g.position);
        scene.add(sp);
        labelSprites.push(sp);
      }
    }

    for (const edge of graph.edges || []) {
      const a = nodeById.get(edge.from);
      const b = nodeById.get(edge.to);
      if (!a || !b) continue;
      const pts = [
        new THREE.Vector3(a.x, a.y, a.z),
        new THREE.Vector3(b.x, b.y, b.z),
      ];
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const kind = edge.kind || "meld";
      const col = kind === "fusion" || kind === "agent" ? 0xe76f8a
        : kind === "truth" || kind === "truth_relay" ? 0xf4a261
        : kind === "connected" ? 0xf4a261
        : kind === "meld" ? 0x4ade80
        : kind === "training" ? 0x60a5fa
        : 0x243552;
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.55 }));
      scene.add(line);
      edgeLines.push(line);
    }

    if (hud) {
      hud.textContent = `${nodes.length} nodes · ${(graph.edges || []).length} edges · ${(graph.connected_models || []).length} connected models`;
    }
  }

  function showDetail(node) {
    if (!detail || !node) return;
    detail.innerHTML = `
      <h3>${node.label}</h3>
      <p class="nd-meta"><span class="badge">${node.level}</span> · ${node.group} · score ${Math.round((node.score || 0) * 100)}%</p>
      <p class="nd-detail">${node.detail || "—"}</p>
      <pre class="nd-json">${JSON.stringify(node.payload || {}, null, 2)}</pre>`;
  }

  function pick(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const meshes = [];
    for (const g of nodeMeshes.values()) g.traverse((c) => { if (c.isMesh) meshes.push(c); });
    const hits = raycaster.intersectObjects(meshes, false);
    if (!hits.length) return null;
    let o = hits[0].object;
    while (o && !o.userData?.id) o = o.parent;
    return o?.userData?.node || null;
  }

  canvas.addEventListener("pointerdown", (e) => {
    const node = pick(e.clientX, e.clientY);
    if (node) {
      selectedId = node.id;
      showDetail(node);
      for (const [id, g] of nodeMeshes) {
        const mesh = g.children[0];
        if (mesh?.material) mesh.material.opacity = id === selectedId ? 1 : 0.55;
      }
    }
  });

  function animate() {
    requestAnimationFrame(animate);
    pulse += 0.02;
    controls.update();
    coreRing.rotation.z += 0.004;
    const core = nodeMeshes.get("hostess7_core");
    if (core) core.rotation.y += 0.003;
    for (const [id, g] of nodeMeshes) {
      const n = g.userData.node;
      if (!n) continue;
      const s = 1 + Math.sin(pulse + n.x * 0.3) * (n.level === "mastered" ? 0.06 : 0.03);
      g.scale.setScalar(n.level === "training" ? s : 1);
    }
    renderer.render(scene, camera);
  }

  window.addEventListener("resize", resize);
  resize();
  animate();

  window.H7Wireframe = {
    update(graph) {
      if (graph) buildGraph(graph);
    },
    focusCore() {
      controls.target.set(0, 0, 0);
      camera.position.set(14, 10, 18);
    },
  };
}