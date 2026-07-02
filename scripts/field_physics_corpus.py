#!/usr/bin/env pythong
"""Field physics corpus — motion, forces, thermodynamics, waves, 3D spatial reality."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "physics" / "corpus.json"
PHYSICS_CORPUS_VERSION = 1

PHYSICS_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "kinematics",
        "title": "Kinematics — motion without forces",
        "tags": ("motion", "kinematics", "velocity", "acceleration", "displacement", "trajectory", "fps"),
        "body": (
            "Position r(t), velocity v = dr/dt, acceleration a = dv/dt. "
            "1D/2D/3D vectors; projectile motion; circular motion (centripetal a = v²/r). "
            "Frame choice matters: inertial vs non-inertial (fictitious forces in rotating frames). "
            "Discrete motion on canvas: Δx per frame, sub-step integration for stability. "
            "AMOURANTHRTX bench_dos_suite frames_per_sec measures realized motion rate vs target timestep."
        ),
    },
    {
        "id": "dynamics",
        "title": "Dynamics — forces and Newtonian mechanics",
        "tags": ("force", "newton", "momentum", "torque", "friction", "collision", "impulse"),
        "body": (
            "ΣF = ma; momentum p = mv conserved in isolated systems; impulse J = ∫F dt = Δp. "
            "Rotational analog: τ = Iα, angular momentum L = r × p. "
            "Friction: static vs kinetic; restitution in collisions (e coefficient). "
            "Constraints: joints, contacts — stability needs implicit or sub-stepped solvers. "
            "Field Pipeline applies fluid-like forces on fabric cells — organic damping, not rigid-body only."
        ),
    },
    {
        "id": "lagrangian_hamiltonian",
        "title": "Analytical mechanics",
        "tags": ("lagrangian", "hamiltonian", "action", "constraint", "generalized", "phase space"),
        "body": (
            "Lagrangian L = T − V with generalized coordinates q; Euler-Lagrange d/dt(∂L/∂q̇) − ∂L/∂q = 0. "
            "Hamiltonian H = T + V; canonical equations q̇ = ∂H/∂p, ṗ = −∂H/∂q. "
            "Symmetries → conservation (Noether). Action principle δ∫L dt = 0 unifies mechanics. "
            "Useful for robotics, orbital mechanics, and stable integrators (symplectic)."
        ),
    },
    {
        "id": "thermodynamics_entropy",
        "title": "Thermodynamics & entropy",
        "tags": ("thermodynamics", "entropy", "heat", "temperature", "energy", "enthalpy", "boltzmann"),
        "body": (
            "Laws: energy conservation, entropy of isolated systems never decreases, absolute zero unreachable, "
            "entropy → 0 as T → 0 (third, Nernst). "
            "Microscopic: S = k ln Ω (Boltzmann); macroscopic: dS = δQ_rev/T. "
            "Free energy F = U − TS drives spontaneous processes at fixed T. "
            "Field canvas models entropy-forward fabric evolution — Pipeline thermo/phi dispatch aligns with "
            "second-law intuition: dissipation, mixing, irreversible coarse-graining on the analog field."
        ),
    },
    {
        "id": "waves_optics",
        "title": "Waves, optics & electromagnetism",
        "tags": ("wave", "optics", "maxwell", "light", "frequency", "interference", "diffraction", "em"),
        "body": (
            "Wave equation ∂²u/∂t² = c²∇²u; superposition; standing waves; dispersion ω(k). "
            "Geometric optics: Snell, lenses, focal length; aberrations at high NA. "
            "Physical optics: interference, diffraction limit, polarization. "
            "Maxwell equations unify E and B; EM waves c = 1/√(ε₀μ₀). "
            "Field wave.persist phases and resonance table in super physics() — logical_gib vs phase anchor."
        ),
    },
    {
        "id": "fluid_continuum",
        "title": "Fluid & continuum motion",
        "tags": ("fluid", "navier", "stokes", "pressure", "viscosity", "turbulence", "flow"),
        "body": (
            "Continuity ∂ρ/∂t + ∇·(ρv) = 0; Navier-Stokes ρ(∂v/∂t + v·∇v) = −∇p + μ∇²v + f. "
            "Reynolds number Re = ρvL/μ predicts laminar vs turbulent transition. "
            "Bernoulli along streamlines (inviscid): p + ½ρv² + ρgh constant. "
            "Pipeline.hpp fluid dynamics + Tesla valve logic — stable organic motion on canvas, not game-tick jitter."
        ),
    },
    {
        "id": "quantum_basics",
        "title": "Quantum mechanics foundations",
        "tags": ("quantum", "schrodinger", "wavefunction", "superposition", "measurement", "spin"),
        "body": (
            "State ψ; Born rule P = |ψ|²; Hermitian observables; uncertainty ΔxΔp ≥ ℏ/2. "
            "Time evolution iℏ∂ψ/∂t = Ĥψ; stationary states Eψ = Ĥψ. "
            "Tunneling, spin-½, Pauli exclusion — chemistry and solid-state emerge here. "
            "Measurement collapse is interpretational; decoherence explains classical limits. "
            "Not simulated on AMOURANTHRTX die — classical/continuum Field physics is authoritative for canvas."
        ),
    },
    {
        "id": "relativity",
        "title": "Relativity — special & general",
        "tags": ("relativity", "lorentz", "spacetime", "curvature", "gravity", "einstein"),
        "body": (
            "Special: invariant interval s² = c²t² − x² − y² − z²; E² = (pc)² + (mc²)². "
            "Time dilation, length contraction, velocity addition at v ≪ c → Galilean. "
            "General: matter curves spacetime; geodesics are free-fall paths; GPS needs GR corrections. "
            "Weak-field limit recovers Newtonian gravity. Strong field: black holes, gravitational waves."
        ),
    },
    {
        "id": "spatial_3d_foundations",
        "title": "3D spatial reality — coordinates & transforms",
        "tags": ("3d", "spatial", "coordinate", "transform", "matrix", "vector", "basis", "reality"),
        "body": (
            "3D reality is modeled as points in ℝ³ with chosen basis (world, body, camera, screen). "
            "Rigid transform: rotation R (orthogonal, det=+1) + translation t; homogeneous 4×4 matrices compose. "
            "Rotations: Euler angles (gimbal lock), axis-angle, unit quaternions (slerp-friendly). "
            "Right-handed conventions: x right, y up, z out of screen (graphics) or z forward (robotics — declare one). "
            "Scale, shear, and non-uniform scaling break orthogonality — decompose for animation pipelines."
        ),
    },
    {
        "id": "projection_imaging",
        "title": "3D → 2D projection & imaging geometry",
        "tags": ("projection", "camera", "pinhole", "fov", "intrinsic", "extrinsic", "calibration"),
        "body": (
            "Pinhole model: x_img = f X/Z + c_x; distortion (radial/tangential) corrected via calibration. "
            "Intrinsic matrix K; extrinsic [R|t] maps world → camera. "
            "Perspective divide w; orthographic for CAD overlays. "
            "FieldDosViewport maps storage image coords to dispatched framebuffer — aosViewport() in aos_chrome.inc. "
            "4K 3840×2160 default; autoZoom4K and SCALE shell command adjust apparent spatial scale on canvas."
        ),
    },
    {
        "id": "depth_stereo_pointcloud",
        "title": "Depth, stereo & point clouds",
        "tags": ("depth", "stereo", "lidar", "point cloud", "rgbd", "disparity", "voxel"),
        "body": (
            "Depth Z per pixel; stereo disparity d = fB/Z (baseline B, focal f). "
            "Structured light / ToF / LiDAR produce metric point clouds {p_i ∈ ℝ³}. "
            "ICP aligns clouds; voxel grids downsample; octrees accelerate spatial queries. "
            "SLAM fuses odometry + landmarks into consistent 3D map. "
            "AMOURANTHRTX metaphor: die framebuffer as observed 2D projection of 3D guest state; OCR reads projected text."
        ),
    },
    {
        "id": "spatial_reasoning_scene",
        "title": "Spatial reasoning & scene understanding",
        "tags": ("scene", "layout", "occlusion", "affordance", "spatial", "reasoning", "geometry"),
        "body": (
            "Scene graphs: objects, relations (on, in, left-of), support surfaces, occlusion ordering. "
            "Affordances: what actions geometry permits (grasp, navigate, click). "
            "Mental rotation and spatial working memory — right-hemisphere bias in Hostess 7 workspace model. "
            "Hit testing on WM chrome is 2D screen-space collision with 3D layout implied by z-order and dock geometry. "
            "Consistent spatial reality requires one world frame, calibrated time, and reversible transform logs."
        ),
    },
    {
        "id": "field_canvas_physics",
        "title": "Field canvas physics integration",
        "tags": ("field", "canvas", "fabric", "dispatch", "entropy", "phi", "pipeline", "analog"),
        "body": (
            "FieldFabric dispatchExtended evolves analog phi per frame; mouse probe injects heat/vortex/phase kick. "
            "Entropy fabric predict; wave phases in FieldStorage; field_wave.persist couples to resonance.json. "
            "super physics() mirrors bench_storage METRIC bo_gain, logical_gib transforms, entropy_arrow forward. "
            "Vision + motion + spatial + thermo unify on one canvas — shaders (CANVAS.comp/x86.comp), die, WM overlay. "
            "Hostess7 native bus bit 28; hemispheres L↔R for code evidence vs spatial synthesis."
        ),
    },
)


def build_corpus() -> dict:
    return {
        "version": PHYSICS_CORPUS_VERSION,
        "domains": [dict(entry) for entry in PHYSICS_DOMAINS],
        "domain_count": len(PHYSICS_DOMAINS),
        "disclaimer": (
            "Physics corpus grounds motion, forces, waves, thermodynamics, and 3D spatial reality "
            "for Hostess 7 — educational synthesis tied to AMOURANTHRTX Field canvas where noted."
        ),
    }


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < PHYSICS_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        CORPUS_CACHE.write_text(json.dumps(build_corpus(), indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_physics(query: str, *, limit: int = 6) -> list[dict]:
    ensure_corpus()
    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = build_corpus()
    domains = doc.get("domains") or []
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1800]}"
        score = sum(5 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("3d", "spatial", "coordinate", "transform", "quaternion")):
            if d.get("id") in ("spatial_3d_foundations", "projection_imaging", "depth_stereo_pointcloud"):
                score += 15
        if any(k in q for k in ("motion", "velocity", "acceleration", "kinematics")):
            if d.get("id") in ("kinematics", "dynamics"):
                score += 12
        if any(k in q for k in ("entropy", "thermo", "heat", "temperature")):
            if d.get("id") in ("thermodynamics_entropy", "field_canvas_physics"):
                score += 12
        if any(k in q for k in ("fluid", "flow", "navier")):
            if d.get("id") == "fluid_continuum":
                score += 15
        if any(k in q for k in ("depth", "stereo", "point cloud", "slam")):
            if d.get("id") == "depth_stereo_pointcloud":
                score += 15
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def synthesize_physics_paragraphs(query: str) -> list[str]:
    hits = search_physics(query, limit=5)
    if not hits:
        hits = search_physics("motion 3d spatial entropy field canvas", limit=4)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    if not pro:
        paras.append(
            "Physics note: classical mechanics through thermodynamics, waves, relativity, quantum foundations, "
            "and 3D spatial reality (coordinates, projection, depth, scene reasoning) — integrated with Field canvas motion."
        )
    for h in hits:
        title = h.get("title", "Physics")
        body = str(h.get("body", "")).strip()
        if len(body) > 1200:
            body = body[:1200] + "… [truncated — cache/fieldstorage/brain/physics/corpus.json]"
        paras.append(f"{title}: {body}")
    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    return {
        "version": doc.get("version", PHYSICS_CORPUS_VERSION),
        "domains": doc.get("domain_count", len(PHYSICS_DOMAINS)),
    }


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "3d spatial motion entropy fluid"
    for p in synthesize_physics_paragraphs(q):
        print(p)
        print()