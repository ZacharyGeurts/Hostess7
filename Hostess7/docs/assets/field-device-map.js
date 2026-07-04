/**
 * DeviceMap — 3D sub-micron operator lattice · every connected device
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.getElementById("dm-canvas");
const hud = document.getElementById("dm-hud");
const opEl = document.getElementById("dm-operator");
const listEl = document.getElementById("dm-device-list");
const statusEl = document.getElementById("dm-status");

const API = (window.Hostess7ApiShim?.apiUrl?.("field-device-map.json"))
  || "/Hostess7/api/field-device-map.json";

let mapData = null;
let selectedId = null;
const nodeMeshes = new Map();

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x060a12, 1);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x060a12, 0.012);

const camera = new THREE.PerspectiveCamera(52, 1, 0.05, 8000);
camera.position.set(12, 18, 24);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.maxDistance = 2000;
controls.minDistance = 2;

scene.add(new THREE.AmbientLight(0x8fb4d9, 0.45));
const key = new THREE.DirectionalLight(0xf4a261, 0.85);
key.position.set(10, 18, 8);
scene.add(key);

const grid = new THREE.GridHelper(120, 60, 0x243552, 0x152033);
grid.position.y = -0.01;
scene.add(grid);

const opGroup = new THREE.Group();
scene.add(opGroup);

function resize() {
  const wrap = canvas.parentElement;
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function colorFor(d) {
  if (d.role === "operator" || d.id === "operator") return 0xd4af37;
  if (d.flying) return 0xa78bfa;
  if (d.kind === "hostile" || d.kind === "terror") return 0xff5c3a;
  if (d.connected) return 0x5ec8ff;
  return 0x64748b;
}

function makeNode(d, scale = 1) {
  const group = new THREE.Group();
  const col = colorFor(d);
  const geo = d.flying
    ? new THREE.ConeGeometry(0.35 * scale, 0.9 * scale, 6)
    : new THREE.OctahedronGeometry(0.45 * scale, 0);
  const mat = new THREE.MeshBasicMaterial({
    color: col,
    wireframe: true,
    transparent: true,
    opacity: 0.92,
  });
  const mesh = new THREE.Mesh(geo, mat);
  if (d.flying) mesh.rotation.x = Math.PI;
  group.add(mesh);

  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.2 * scale, 8, 8),
    new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.2 }),
  );
  group.add(glow);

  const pos = d.scene || { x: 0, y: 0, z: 0 };
  group.position.set(pos.x || 0, pos.y || 0, pos.z || 0);
  group.userData = { id: d.id, device: d };
  return group;
}

function bearingArrow(d, anchor) {
  if (!d.bearing_deg || d.id === "operator") return null;
  const len = Math.min(8, Math.max(1.5, Math.log10((d.distance_km || 1) + 1) * 3));
  const br = (d.bearing_deg * Math.PI) / 180;
  const dir = new THREE.Vector3(Math.sin(br), 0, -Math.cos(br)).normalize();
  const origin = new THREE.Vector3(0, 0.2, 0);
  const arrow = new THREE.ArrowHelper(dir, origin, len, colorFor(d), 0.4, 0.25);
  arrow.position.copy(origin);
  return arrow;
}

function clearNodes() {
  nodeMeshes.forEach((g) => scene.remove(g));
  nodeMeshes.clear();
  opGroup.clear();
}

function renderMap(data) {
  clearNodes();
  const op = data.operator || {};
  const opMesh = makeNode(op, 1.4);
  opGroup.add(opMesh);
  nodeMeshes.set("operator", opMesh);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(1.5, 0.03, 8, 64),
    new THREE.MeshBasicMaterial({ color: 0xd4af37, transparent: true, opacity: 0.45 }),
  );
  ring.rotation.x = Math.PI / 2;
  opGroup.add(ring);

  (data.devices || []).forEach((d) => {
    const g = makeNode(d, d.flying ? 0.85 : 0.7);
    scene.add(g);
    nodeMeshes.set(d.id, g);
    const arr = bearingArrow(d, op);
    if (arr) {
      arr.position.copy(g.position);
      scene.add(arr);
    }
  });

  const total = data.stats?.total || 0;
  const fly = data.stats?.flying || 0;
  hud.textContent = `${total} devices · ${fly} flying · sub-micron anchor`;
  if (statusEl) {
    statusEl.textContent = `Precision ${data.stats?.precision || "sub_micron"} · ${data.stats?.sub_micron_placed || 0} placed`;
  }
}

function renderOperator(op) {
  if (!opEl || !op) return;
  opEl.innerHTML = `
    <strong>${esc(op.label || "Operator")}</strong><br>
    <span class="meta">${esc(op.lat_str || op.lat)} · ${esc(op.lon_str || op.lon)}</span><br>
    <span class="meta">ENU E ${fmtNm(op.enu_e_nm)} · N ${fmtNm(op.enu_n_nm)} · U ${fmtNm(op.enu_u_nm)}</span><br>
    <span class="meta">${esc(op.precision || "sub_micron")} · ${esc(op.resolution_nm ? op.resolution_nm + " nm LSB" : "~0.11 nm")}</span>
  `;
}

function renderList(devices) {
  if (!listEl) return;
  listEl.innerHTML = "";
  devices.forEach((d) => {
    const li = document.createElement("li");
    li.dataset.id = d.id;
    if (d.id === selectedId) li.classList.add("active");
    const badges = [
      d.flying ? '<span class="dm-badge fly">FLY</span>' : "",
      d.connected ? '<span class="dm-badge conn">ON</span>' : "",
    ].join("");
    li.innerHTML = `
      <div><strong>${esc(d.label || d.id)}</strong>${badges}</div>
      <div class="meta">${esc(d.direction)} ${d.bearing_deg?.toFixed?.(1) || d.bearing_deg}° · ${esc(d.distance_label || "")}</div>
      <div class="meta">${d.flying ? "Airborne" : "Ground"} · ${esc(d.source || "")}</div>
    `;
    li.addEventListener("click", () => focusDevice(d.id));
    listEl.appendChild(li);
  });
}

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
}

function fmtNm(v) {
  try {
    const n = BigInt(String(v || "0"));
    const sign = n < 0n ? "-" : "";
    const abs = n < 0n ? -n : n;
    if (abs >= 1000000n) return `${sign}${(Number(abs) / 1e6).toFixed(2)} mm`;
    if (abs >= 1000n) return `${sign}${(Number(abs) / 1e3).toFixed(1)} µm`;
    return `${sign}${abs} nm`;
  } catch {
    return "0 nm";
  }
}

function focusDevice(id) {
  selectedId = id;
  const g = nodeMeshes.get(id);
  if (g) {
    controls.target.copy(g.position);
    camera.position.set(
      g.position.x + 6,
      g.position.y + 8,
      g.position.z + 10,
    );
  }
  if (mapData?.devices) renderList(mapData.devices);
}

async function loadMap() {
  try {
    const res = await fetch(API, { cache: "no-store" });
    mapData = await res.json();
    renderMap(mapData);
    renderOperator(mapData.operator);
    renderList(mapData.devices || []);
  } catch (e) {
    if (statusEl) statusEl.textContent = `Load failed: ${e.message}`;
  }
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  const t = performance.now() * 0.001;
  opGroup.rotation.y = Math.sin(t * 0.2) * 0.05;
  renderer.render(scene, camera);
}

window.addEventListener("resize", resize);
document.getElementById("dm-refresh")?.addEventListener("click", loadMap);
document.getElementById("dm-focus-op")?.addEventListener("click", () => focusDevice("operator"));

resize();
loadMap();
animate();
setInterval(loadMap, 12000);