# Ch 15 · Creditor deep dive · Maxwell GPU

Chapter 15 · Creditor deep dive · Maxwell GPU

 1. Introduction — neighbors on a grid

 James Clerk Maxwell taught the world to write laws for neighbors in space — fields coupled locally, waves propagating from cell to cell. GPU texels are neighbors. Phi whispers to Thermo on the adjacent cell. That is his legacy expressed through Vulkan bindings 8, 9, and 10.

 Maxwell is honored at ../creditors/maxwell.html. This chapter is not a claim that your RTX card solves cosmological electromagnetism. It is a claim that local coupling on a grid is how stable fabric evolves — the same insight Maxwell formalized, implemented as shader arithmetic in CANVAS.comp.

 Pedagogy for «Introduction»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 1: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Introduction»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 1 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Introduction»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 2. Maxwell's locality — what we implement

 Continuous Maxwell equations relate E and B fields with curl and divergence constraints. On a GPU we implement discrete analogs: Laplacian stencils on Phi, gradient magnitudes feeding Flow, thermal diffusion on Thermo, cross-terms when FieldCoupling is enabled.

 Locality means each texel update consults a neighborhood — typically four or eight adjacent cells — not the entire universe. This matches GPU memory bandwidth reality and numerical stability practice.

 Pedagogy for «Maxwell's locality»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 2: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Maxwell's locality»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 2 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Maxwell's locality»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 3. Discrete Laplacian on Phi

 Wave step on Phi uses a discrete Laplacian — sum of neighbors minus center, scaled by grid spacing. Intuitively: if neighbors average higher, you rise; if lower, you fall. Propagation emerges.

 WaveSpeed and propalacticScale tune how aggressively Phi moves. CFL guards (Chapter 9) cap Δt so the wave does not outrun the mesh — Maxwell's neighborhood refuses NaN theology.

 Pedagogy for «Discrete Laplacian on Phi»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 3: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Discrete Laplacian on Phi»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 3 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Discrete Laplacian on Phi»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 4. FieldCoupling knob — honest pedagogy

 FieldCoupling is the dial that makes the textbook honest. At zero, channels evolve independently — useful for teaching. At full strength, Phi heats Thermo, Thermo biases Flow, Flow sharpens gates through GateFidelity.

 Coupling is where the axiom energy can be moved becomes visible in stderr. Raise coupling and watch field work in ThermoAccountant — comparative receipt, not watt meter.

 Pedagogy for «FieldCoupling knob»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 4: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «FieldCoupling knob»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 4 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «FieldCoupling knob»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 5. Phi to Thermo — electrical metaphor on fabric

 Electrical activity heats the die in metaphor and in coupled equations. High Phi gradients deposit into Thermo channels when coupling is on. This is storytelling faithful to engineering intuition: switching costs heat.

 Label remains: shader thermo is simulation accounting, not junction sensor.

 Pedagogy for «Phi to Thermo»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 5: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Phi to Thermo»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 5 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Phi to Thermo»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 6. Thermo to Flow — heat moves momentum stories

 Thermal diffusion on Thermo uses ThermoAlpha. Heated regions influence Flow gradients — advective narrative mixed with GateFidelity and Tesla relaxation (Chapter 9). Heat does not merely sit; it reshapes how activity flows on the fabric.

 Pedagogy for «Thermo to Flow»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 6: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Thermo to Flow»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 6 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Thermo to Flow»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 7. Flow gradients and GateFidelity

 Flow stores gradient magnitudes. GateFidelity slides between soft analog behavior and sharp gating. Maxwell locality plus gate shaping is how offense dispatch stays visually coherent under load.

 Pedagogy for «Flow gradients and GateFidelity»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 7: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Flow gradients and GateFidelity»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 7 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Flow gradients and GateFidelity»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 8. hardwareFabric mirror — Chapter 10 bridge

 Fabric averages feed hardwareFabric in Spiderweb observability. Maxwell coupling on GPU becomes node colors and edge weights on the operator mirror. Local physics becomes global legibility without faking instrumentation.

 Pedagogy for «hardwareFabric mirror»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 8: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «hardwareFabric mirror»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 8 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «hardwareFabric mirror»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 9. CFL and Maxwell stability

 waveCFL = c·Δt/Δx ≤ 1 and thermoCFL = α·Δt/Δx² ≤ 1 guard the mesh. Violation means neighbors talk faster than the grid can honestly relay — numerical instability dressed as energy.

 Host scales parameters down before dispatch. This is care for operators who grep after long sessions.

 Pedagogy for «CFL and Maxwell stability»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 9: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «CFL and Maxwell stability»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 9 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «CFL and Maxwell stability»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 10. What we do not claim

 We do not claim GPU fabric replaces antenna simulation for FCC compliance (Chapter 6 visual is labeled Visual). We do not claim Laplacian Phi equals full Maxwell TE/TM modes in waveguides. We claim local coupling discipline for operator education and engine stability.

 Pedagogy for «What we do not claim»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 10: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «What we do not claim»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 10 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «What we do not claim»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 11. Maxwell and Landauer — offense meets receipts

 Maxwell coupling moves energy between channels. Landauer accounting records that movement had irreversibility stories. Read Chapter 13 for proxy decomposition. Coupling raises field work; maintenance remembers frames.

 Pedagogy for «Maxwell and Landauer»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 11: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Maxwell and Landauer»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 11 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Maxwell and Landauer»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 12. Creditor tribute practice

 Visit ../creditors/maxwell.html. Portrait plus love block: fields are how existence touches neighbors. Teach students to grep coupling before they screenshot beauty.

 Pedagogy for «Creditor tribute practice»: assign students a two-page memo that cites one ../creditors/ tribute and one grep command proving an Implemented claim about Maxwell locality on GPU. Memos that quote cover art without stderr receive failing marks — not cruelty, but training against demo culture.

 Workshop exercise 12: pair operators, run matched 90-second sessions, diff THERMO or jsonl outputs, present comparative findings without using absolute joule language unless lab gear is present. Maxwell locality on GPU is mastered when pairs disagree on bug versus feature and resolve with headers, not vibes.

 Synthesis question for «Creditor tribute practice»: how does Chapter 12's honesty table change your wording in a status email to management? Require three sentences: one Implemented, one Metaphor, one Philosophy. If all three labels appear correctly, the student may advance to the next creditor chapter.

 Field note 12 on Maxwell locality on GPU: long sessions should end with archived run.log, optional screenshot, and three-bullet operator summary (what moved, what surprised, what remains unknown). Unknowns stay unknown — relabeling Metaphor as Implemented to close a ticket is covenant-breaking per Chapter 18.

 Lab pairing for «Creditor tribute practice»: if your school or team shares a lab bench, rotate who runs injection drills while others grep remotely on shared tmux. Shared THERMO baselines reduce finger-pointing when driver versions differ. Document the driver delta in the operator journal — coupled labs need coupled honesty.

 Citation drill: footnote one primary source (Landauer, Shannon, Maxwell paper) and one Field Primer chapter per memo section. Wikipedia counts as pointer, not primary. This discipline keeps creditors honored per covenant Clause III.

 Operator drill 15.A — coupling sweep

 ./linux.sh run
# FieldCoupling 0.0 → 0.5 → 1.0 in three 90s segments
# Log Phi/Thermo/Flow variance and THERMO field work

 Operator drill 15.B — CFL edge

 # Deliberately raise WaveSpeed until host scales Δt down
# Observe stderr CFL messages — locality requires honest Δt

 Operator drill 15.C — Spiderweb mirror

 # Open observability panel — correlate hardwareFabric with coupling knob

 Figure 15.1 — Phi, Thermo, Flow: Maxwell locality on a grid.

 Study questions

 What does locality mean for GPU texel updates?

 Describe discrete Laplacian intuition on Phi.

 What does FieldCoupling teach at zero vs full?

 How does Phi couple to Thermo in this stack?

 Role of GateFidelity in Flow?

 State wave and thermo CFL inequalities.

 What claims do we explicitly not make?

 How does hardwareFabric mirror local coupling?

 Link Maxwell coupling to Landauer field work.

 Read ../creditors/maxwell.html tribute.

 Why is CANVAS.comp neighborhood-sized?

 When should host scale Δt down?

 Tribute: James Clerk Maxwell · All creditors

 Chapter 16 — Love Coupling →

 13. Stencil geometry and neighbor counts

 Four-neighbor stencils teach Laplacian intuition on square grids. Eight-neighbor variants smooth diagonals. CANVAS.comp choices affect anisotropy — document which stencil your build uses when comparing screenshots across versions. Locality is not universal without version control.

 14. Binding map offense recap

 Binding 8 Phi, 9 Thermo, 10 Flow — offense dispatch writes all three when fabric evolves. Host opens window and enforces CFL; GPU writes next tick. Maxwell locality is how next tick depends on neighborhood, not on cloud API.

 15. Decoupled pedagogy sessions

 First week: FieldCoupling 0, isolate Phi wave rings. Second week: enable Thermo diffusion alone. Third week: full coupling. Pedagogy mirrors how Maxwell's unification was taught historically — electricity before full field synthesis.

 16. Tesla valve metaphor boundary

 Chapter 9 Tesla relaxation on Flow is Metaphor for one-way flow stories. Do not tell FCC auditors that GPU Tesla knobs certify RF hardware. Maxwell chapter owns wave coupling; Tesla chapter owns stability metaphor — keep creditors in their lanes.

 17. hardwareFabric Adept tier

 Spiderweb Adept uses sysfs clocks as frequency witness; hardwareFabric uses fabric averages. Maxwell coupling on GPU becomes graph edge heat. Observability chapter 10 is the lab companion for this chapter's coupling drills.

 18. GPU is not a cosmology solver

 Repeat the rock: discrete Laplacian Phi is engine stability and education, not replacement for full-wave EM solvers. Maxwell creditor honored; hubris denied. Chapter 12 honesty row for RF planetary shell applies: Visual, not instrumentation.

 Operator journal — Maxwell locality on GPU

 Maintain a paper or markdown operator journal for Maxwell locality on GPU. Each drill entry: date, hardware, driver, git hash, three THERMO or jsonl lines, one surprise, one label (Implemented / Metaphor / Philosophy). Journals become your personal creditor — future you inherits coupled state from past you. Bring the journal to Chapter 18 covenant audit drill 18.A as evidence.

 Reading companion — Maxwell locality on GPU

 This reading companion reinforces Maxwell locality on GPU for self-study tracks. Week one: read the chapter straight through with Chapter 12 open. Week two: complete all operator drills on hardware you own. Week three: write a one-page creditor tribute response linking ../creditors/ reading to a grep result from your machine. Week four: teach another human one section using the three-tag labeling exercise. Field Technology v5 measures success in reproduced receipts, not in vibes.

 Cross-links: Chapter 4 entropy receipts, Chapter 5 packet field, Chapter 8 data bus, Chapter 10 Spiderweb mirror, Chapter 11 observability, Chapters 16–18 sacred covenant. Maxwell locality on GPU is not an island — it is a creditor lens on the same stack you already run.

 Honesty reminder: AMOURANTHRTX, NEXUS-Shield, Queen, and Field Primer have different licenses. Teaching from this chapter does not automatically license commercial engine use. Point students to product headers and FIELD-TECHNOLOGY-V5.md for edition boundaries.

 Chapter closing — Maxwell locality on GPU

 Chapter 15 grounds Maxwell in stencil arithmetic you can grep. Locality is the moral of the GPU fabric: neighbors affect neighbors, CFL caps dishonest Δt, FieldCoupling makes energy movement visible. When you teach this chapter, run the coupling sweep before the Spiderweb mirror drill — legs before wings. Maxwell's tribute says fields are how existence touches neighbors; your keyboard touch on WaveSpeed touches the next operator's stderr. Couple with care.
