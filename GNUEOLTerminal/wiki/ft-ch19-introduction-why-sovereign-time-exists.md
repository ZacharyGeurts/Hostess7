# Ch 19 · Introduction — why sovereign time exists

Introduction — why sovereign time exists

 Chapter 19 is the operator perimeter for time . Not cosmological time. Not poetic time. The clocks your logs, your GPS sub-micron nodes, your thermo receipts, and your threat panel agree on — or refuse to agree on, loudly, with a verdict you can grep .

 Assume adversaries know field literacy. Assume they have read this book, or something like it. Assume pool NTP, remote RTC chips, hypervisor clocks, and silicon frequency tables can be squidgied : nudged just enough to desync correlated evidence without tripping naive alarms. A squidgie is not a cartoon hack. It is a micron-scale tamper — RTC nudged, monotonic story disagrees, or the sysfs CPU frequency fingerprint jumps without a logged thermal step that explains the jump.

 Under terror-threat posture, you do not let the internet set your epoch alone. You run your timeserver. You sign pulses. You verify at receive. You seal forward. Entropy cannot be reversed; neither can honest time. This chapter teaches the mechanism, the grep discipline, and the honest rocks.

 If you completed Chapter 11's observability lab, you already read STATUS lines as a timeline. Sovereign time makes that timeline defensible when adversaries target correlation rather than availability. Availability attacks are loud. Squidgie attacks are quiet. Quiet attacks are why verify-at-receive exists.

 Threat model — what adversaries actually do to clocks

 Pool NTP is a convenience mesh, not a covenant. Clients ask strangers for the time; strangers answer; clients step their clocks. Under terror-threat knowledge, that model leaks trust at every hop. An adversary who controls any influential stratum source — or merely influences RTT — can nudge many hosts together, hiding tamper inside statistically normal offset noise.

 Remote RTC tamper is subtler still. Battery-backed clocks on motherboards and BMCs survive reboots. A small persistent bias accumulates across days until log correlation between your engine thermo receipts and your NEXUS packet field sentences drifts. Forensics then mis-orders cause and effect: did the connection precede the entropy spike, or did bad wall labels make it look that way?

 Hypervisors add a third surface. Guest CLOCK_REALTIME can be warped by host policy without the guest's monotonic story noticing immediately. That is why monotonic alone is insufficient for cross-host agreement: monotonic is session-local truth, not universal UTC truth.

 Sysfs frequency tables are the Puny-tier witness Spiderweb already reads. Adversaries with kernel foothold can spoof scaling_cur_freq reads while thermal governor narratives lag. Micron witness binds monotonic instants to those tables so fast flips without DVFS story become first-class issues, not debugging curiosities.

 Field Technology does not claim magic detection of every FPGA timestamp attack. It claims Implemented operator-owned pulses, signed receipts, and receiver double-check with a named verdict. Name the verdict. Grep the verdict. Act on the verdict.

 Three clocks, three jobs

 Sovereign time is not one clock wearing three hats. It is three witnesses with three jobs, cross-checked every pulse.

 The monotonic clock ( CLOCK_MONOTONIC ) answers ordering within a boot session. Ticks never go backward. It is the spine for pulse spacing, verify deltas, and session-local sealed time in FieldSocket . Trust the host kernel for monotonic — but never confuse monotonic with wall truth.

 The realtime clock ( CLOCK_REALTIME ) answers human-correlatable wall labels. Grep uses realtime. Panel timestamps use realtime. UTC ISO strings in receipts use realtime. Under sovereign posture, realtime labels on enrolled hosts trace to your operator timeserver pulses , not pool consensus alone.

 The sysfs freq witness reads per-core scaling_cur_freq (or cpuinfo_cur_freq ) at pulse instants. Spiderweb Puny tier already treats these MHz tables as honest silicon telemetry for dashboards. Sovereign time hashes them into micron_witness so pulse receipts carry a silicon fingerprint, not only software clocks.

 Naive NTP clients collapse these questions into one adjusted offset. Field Technology refuses that collapse. When GPS precision nodes report sub-micron ENU coordinates but sovereign verify returns SQUIDGIE , trust the triple verify — not the prettiest map dot.

 Session-local spine — TotalTime::seal()

 Inside AMOURANTHRTX, TotalTime::seal() in ELLIE.hpp locks session genesis into FieldSocket::sealed_time . Frame-rate jitter cannot rewrite physics time. That is session-local monotonic discipline: one engine process, one sealed genesis, one forward-only story per run.

 Sovereign sync extends the same posture across hosts . The engine seals time inside the dispatch loop; the operator node issues signed pulses on UDP; every receiver pulls a pulse and runs verify_receipt() before accepting wall labels for perimeter services. Captain Ellie seals time forward in C++; sovereign-time.py seals it forward on the LAN mesh. Same ethics, different scale.

 The coupling is intentional. Operators who run Queen browser beside AMOURANTHRTX should not maintain two incompatible time stories. Sealed session time governs fabric evolution; sovereign pulses govern perimeter services and log correlation across processes. Chapter 21 binds Queen navigation receipts to the same witness Chapter 19 verifies.

 When TotalTime::verify() fails in-engine, abort posture is fail-closed. When sovereign verify fails, perimeter daemons gate replies — NTP blocks, panel flags red, grep finds SQUIDGIE . The C++ abort and Python gate are siblings, not duplicates.

 SQUIDGIE — the tamper verdict

 SQUIDGIE is the sovereign-time tamper verdict returned by verify_receipt() when issues are non-empty. It is not humor. It is the word you grep when clocks disagree at receive.

 Detection paths include bad_signature when HMAC from the operator key in NEXUS_STATE_DIR does not match the receipt body; monotonic_backward when remote mono_ns decreases versus the previous pulse; realtime_backward when remote realtime_ns decreases; mono_real_skew when realtime and monotonic deltas diverge beyond NEXUS_TIME_MAX_SKEW_MS (default 50 ms).

 Hardware-story paths include micron_squidgie when micron_witness flips in under 50 ms of monotonic window while frequency sum jumps or skew is high; freq_rtc_squidgie when freq_sum_khz delta exceeds NEXUS_TIME_MAX_FREQ_DELTA_KHZ (default 250000) with suspicious skew. Receive-side receive_wall_skew compares local realtime to remote at pull time with generous RTT slack.

 Verdict is either USER_OK or SQUIDGIE . There is no partial credit. Perimeter services treat SQUIDGIE as fail-closed input. field-ntp-2026.py increments squidgie_blocks when sovereign cache is dirty. Operators treat repeated squidgie as incident response, not calibration trivia.

 The name evokes silent drift — squid ink in the water. Your job is to make ink visible in jsonl. Archive receipts. Correlate with thermo. Do not silence the verdict because the panel is pretty.

 Micron witness — binding monotonic to silicon

 Each pulse carries micron_witness : the first 16 hex characters of SHA-256 over mono_ns concatenated with sorted per-CPU frequency entries from sysfs. The witness binds a monotonic instant to the silicon table at that instant.

 If adversaries nudge RTC silently, monotonic may still advance while realtime labels drift. If adversaries manipulate reported frequencies without thermal narrative, witness flips faster than DVFS alone explains. The witness is not electron microscopy. It is Implemented correlation discipline aligned with Spiderweb Puny tier reads.

 Operators should sample witness across idle and load. Under honest DVFS, witness changes should correlate with workload steps you can see in Spiderweb status or entropyThisFrame under probe injection. Witness flips during apparent idle with simultaneous freq sum jumps are exactly the squidgie story.

 Micron witness also supports enrollment audits: new hosts pulling pulses should show stable witness continuity when clocks are honest. A fresh host with wild witness divergence on first sync is a enrollment stop signal, not a prompt to widen NTP.

 sovereign-time.py — anatomy and artifacts

 The module lives at NEXUS_INSTALL_ROOT/lib/sovereign-time.py . Schema sovereign-time/v1 . State defaults to NEXUS_STATE_DIR ( /var/lib/nexus-shield ).

 Artifacts: sovereign-time-key.bin holds the 32-byte HMAC key (mode 0600 on create); sovereign-time-pulse.json stores pulse counter and last receipt; sovereign-time-receipts.jsonl is append-only audit. UDP port defaults to NEXUS_SOVEREIGN_TIME_PORT=9123 .

 Commands: serve runs operator UDP loop; pulse issues one local signed pulse; sync [host] [port] pulls and verifies; status / json emit panel slice. Verify mode accepts saved receipt JSON for offline forensics.

 Each receipt includes schema, pulse number, chain label, host, mono_ns, realtime_ns, utc ISO, freq_sum_khz, micron_witness, entropy_tag (12 hex chars), and sig (HMAC-SHA256 over sorted JSON body). UDP server accepts {"op":"pulse","client":"hostname"} and returns fresh signed receipt.

 Default bind is loopback via NEXUS_SOVEREIGN_TIME_BIND . Widening to LAN is explicit operator choice — terror-threat posture assumes loopback until you document otherwise in your covenant file.

 Receiver verify — pipeline step by step

 Every receiving end that cares about honest wall labels runs sync on schedule or gates daemons on sovereign health.

 Step one: pull signed receipt via UDP. Step two: load previous receipt from local pulse state. Step three: recompute HMAC with operator key material. Step four: compare monotonic and realtime deltas pulse-to-pulse. Step five: evaluate freq sum delta against MAX_FREQ_DELTA_KHZ. Step six: evaluate micron witness flip speed. Step seven: cross-check local clocks at receive. Step eight: write verdict and issues to pulse state; append to jsonl on issue.

 Grep discipline: grep SQUIDGIE /var/lib/nexus-shield/sovereign-time-receipts.jsonl and inspect sovereign-time-pulse.json last verify block. Pair with threat-panel sovereign slice from field-services-2026.py json .

 Offline verify: pythong sovereign-time.py verify RECEIPT.json PREV.json replays checks without network — useful when archiving incidents.

 Do not auto-retry sync into silence. Repeated USER_OK after SQUIDGIE requires demonstrated fix: clock source corrected, key rotation documented, thermal story matches freq table.

 Environment variables — operator reference

 NEXUS_SOVEREIGN_TIME enables sovereign time in the NEXUS daemon stack. NEXUS_SOVEREIGN_TIME_BIND defaults to 127.0.0.1 for serve mode. NEXUS_SOVEREIGN_TIME_PORT defaults to 9123 .

 NEXUS_SOVEREIGN_TIME_FIRST=1 (default in 2026 seed) makes sovereign pulses authoritative over pool NTP — see grok_world.sh flow 20. NEXUS_TIME_MAX_SKEW_MS defaults to 50 ms. NEXUS_TIME_MAX_FREQ_DELTA_KHZ defaults to 250000.

 NEXUS_STATE_DIR centralizes keys and receipts. NEXUS_INSTALL_ROOT locates lib modules for panel importers. Document these in your operator runbook beside DNS and DHCP binds.

 Changing skew bounds is not tuning for comfort. Tighter bounds catch smaller squidgies; looser bounds reduce false positives on busy lab hosts. Production last-host nodes should justify any loosening in writing.

 Coupling to precision GPS and Spiderweb

 gps-precision.py sub-micron ENU nodes need stable UTC labels for map correlation. If sovereign verify fails while GPS draws confident dots, the dots are art until clocks recover.

 Spiderweb Adept tier SimulateSubMicron uses sysfs clocks as freq witness alongside fabric averages. Sovereign micron witness should not wildly diverge from Puny-tier sysfs reads on the same host without explanation.

 Cross-host GPS fusion assumes time agreement. Sovereign sync is the cheap test before trusting fused tracks. Skip it and you build pretty multi-host stories on sand.

 ThermoAccountant entropyThisFrame is the per-frame receipt that time ran forward in fabric. Clock tamper does not directly spoof thermo — but mis-ordered logs make thermo spikes look like network causes. Fix time first; then grep thermo.

 Coupling to NEXUS panel and field-ntp-2026

 Threat panel merges sovereign slice from field-services-2026.py : posture flags, last pulse, last verify, squidgie blocks on NTP side.

 field-ntp-2026.py serves RFC 5905 mode-4 on UDP 123, gated on sovereign pulse health. Stratum defaults to 2; NEXUS_LAST_HOST=1 can elevate stratum 1 on sole survivor node.

 When sovereign cache is dirty, NTP replies may stop — clients should fail visibly rather than drift to pool silently. That is sovereign-first ethics.

 Panel DNS tab time column should match grep-able receipts. If panel says OK but jsonl says SQUIDGIE, trust jsonl and file a panel stale-cache bug — not the other way around.

 Single-source discipline — grok_world.sh flow 20

 Gradient chaos from many NTP sources helps adversaries hide micron nudges. Flow 20 enforces single source when NEXUS_SOVEREIGN_TIME_FIRST=1 : your signed pulses win.

 This is not anti-NTP ideology. Stratum labels still matter — but must trace to verifiable pulses. Pool fallback remains opt-in via NEXUS_POOL_NTP_FALLBACK=1 , never default in 2026 seed.

 Operators document upstream when last-host mode serves global TIME. Sole survivor is not casual toggle — it is covenant posture (Chapter 20).

 ELLIE alignment — seal forward across covenant

 Captain Ellie's TotalTime::verify() abort posture is the spiritual parent of sovereign SQUIDGIE. Session entropy corruption triggers apocalypse handler fail-closed in C++.

 ellie-last-host.py verify checks entropy covenant; sovereign-time.py sync checks clock covenant. Under NEXUS_LAST_HOST=1 , both run on sole survivor — DNS, DHCP, TIME, grep one story.

 FieldSocket::sealed_time in engine push constants parallels sovereign pulse → NTP stratum chain in perimeter. Teach both in onboarding.

 Forensic workflow — week-two operator lab

 Start operator timeserver: pythong sovereign-time.py serve . Issue baseline: pythong sovereign-time.py pulse . Sync from second context: pythong sovereign-time.py sync 127.0.0.1 9123 . Confirm verdict: USER_OK .

 Archive sovereign-time-receipts.jsonl with threat-panel exports. Correlate with LOG_THERMO during same window. Lab-only: induce VM skew; confirm SQUIDGIE and issues list populated.

 Document recovery steps in runbook: stop serve, fix clock source, re-pulse, verify three consecutive OK, then re-enable NTP gate.

 Troubleshooting common operator mistakes

 Mistake: running serve on 0.0.0.0 without firewall story. Fix: bind loopback or LAN IP explicitly; document in covenant.

 Mistake: copying key.bin between hosts without enrollment procedure. Fix: treat key as operator root; rotate on compromise.

 Mistake: ignoring SQUIDGIE because browsing still works. Fix: browsing is not time truth; perimeter may be lying quietly.

 Mistake: max skew set to seconds to silence alerts. Fix: you built a squidgie muffler; restore bounds or admit defeat in writing.

 Honest rocks

 UDP signed pulses on localhost: Implemented . HMAC verify + micron witness + freq fingerprint: Implemented .

 Tamper abort like TotalTime::verify() in all NEXUS daemons: Posture — engine abort is C++. Sub-micron SEM from clock sync alone: Correlation discipline .

 Pool NTP fully retired globally: Operator policy — sovereign-first is default, not universal law.

 Case study — correlating thermo spikes with clock skew

 An operator notices entropy spikes in LOG_THERMO coinciding with unexplained packet field bursts. Screenshots blame a browser tab. Sovereign grep shows SQUIDGIE entries 200 ms before the spike cluster — wall labels were wrong, not the fabric.

 Recovery: stop NTP serve to clients, re-sync sovereign, confirm three USER_OK pulses, re-export jsonl with corrected timeline. The tab may still be guilty — but time truth comes first in forensic ordering.

 Lesson: thermo is forward-running receipt; sovereign time is correlatable wall label. Neither replaces the other. Together they beat screenshots.

 Case study — lab VM clock nudge

 In a controlled lab VM, advance guest realtime by 400 ms without touching monotonic. Next sovereign sync returns receive_wall_skew and possibly mono_real_skew issues. Verdict SQUIDGIE.

 Document issues list in incident notes. Revert VM clock. Re-pulse until USER_OK. This drill proves the stack works — run it before production enrollment.

 Pulse chain integrity and entropy_tag

 Each pulse increments a monotonic pulse counter stored in sovereign-time-pulse.json. Chain labels record whether pulse was operator-local or serve:client issued.

 entropy_tag is 12 hex chars from SHA-256 over mono_ns and pulse number — lightweight tie between thermo ethic and time receipts. Grep entropy_tag beside LOG_THERMO hashes when building cross-subsystem timelines.

 Key rotation and compromise posture

 sovereign-time-key.bin is operator root for HMAC. Compromise requires rotate: stop serve, archive old jsonl, generate new key, re-enroll receivers, document rotation in covenant file.

 Do not chmod key world-readable. Do not store key in git. Treat loss of key like loss of DNS admin passkey — full perimeter re-seal.

 Integration checklist — before declaring production time

 Confirm NEXUS_SOVEREIGN_TIME_FIRST=1 in daemon env. Confirm serve bind matches network diagram. Confirm field-ntp-2026 squidgie_blocks visible in panel. Confirm chrony disabled or hooked per policy.

 Confirm Queen browser slice shows sovereign_time_witness true. Confirm gps-precision scripts read UTC from same receipt chain. Archive baseline receipts.jsonl.

 Reading receipts.jsonl — field forensic grammar

 Each jsonl row has ts ISO and receipt object. Sort by pulse number for chain analysis. Diff freq_sum_khz between consecutive pulses during CPU stress — expect gradual change, not step discontinuities without workload.

 Pair micron_witness changes with Spiderweb STATUS lines. Mismatch between witness and Puny-tier sysfs manual read indicates deeper kernel spoof — escalate, do not tune skew.

 Comparison to naive ntpdate behavior

 ntpdate-style step changes wall clock instantly without signed chain or silicon witness. Under terror threat that is unacceptable for enrolled hosts. Sovereign sync is pull-verify-store, not blind step.

 Clients may still use NTP for coarse sync if gated — but authority is sovereign pulse health, not pool vote.

 Multi-host mesh — LAN enrollment story

 Second host syncs to operator serve bind on LAN IP when covenant allows. RTT adds receive_wall_skew slack — defaults allow generous milliseconds on LAN, tighter on WAN if you must widen bind.

 All enrolled hosts should share verification policy documentation — max skew, max freq delta, response playbook for SQUIDGIE.

 Captain Ellie LOG categories and time

 LOG_MAIN and LOG_STATUS timestamps should align with sovereign utc field after sync. If engine log and sovereign utc diverge systematically, suspect dual clock sources on one host — pool still running beside sovereign.

 Disable pool when sovereign-first — grep pool in process list and config.

 Spiderweb Puny tier — manual witness corroboration

 Run list Hardware in prompt terminal while pulsing. Compare operationalFreqMHz narrative to freq_sum_khz in receipts. Large unexplained gaps trigger review even if verdict USER_OK — USER_OK is not absence of all anomaly, only absence of threshold issues.

 ThermoAccountant and time — philosophical alignment

 Landauer discipline says erase has cost. Time discipline says forward seal has receipt. ThermoAccountant counts proxy entropy per frame; sovereign-time counts proxy entropy_tag per pulse. Both refuse silent rewind.

 When to widen NEXUS_SOVEREIGN_TIME_BIND

 Widen only with documented LAN trust boundary — firewall rules, MAC allowlist, VPN. Loopback is default because UDP signed pulse is powerful; exposing serve to internet without story is retired-vulnerability thinking.

 FAQ — will sovereign time fix my laptop sleeping

 Sleep discontinuities affect monotonic versus realtime relationship across suspend — expect issues after resume until re-sync. Document resume playbook: pulse, sync, verify OK before serving NTP to others.

 FAQ — is SQUIDGIE a false positive on laptops

 Aggressive DVFS on battery can move freq_sum_khz quickly. Tune MAX_FREQ_DELTA only with logged thermal narrative — do not silence to comfort. Compare witness flip rate on AC versus battery in lab.

 Long-form primer — sovereign time as operator covenant

 Sovereign time is where Chapter 11 observability meets Chapter 18 covenant. You promised to build locally, grep truth, and hold gates. None of that works if wall labels lie. A threat panel timestamp that looks authoritative while RTC was squidgied is worse than no panel — it is false confidence. Sovereign time exists to deny false confidence a home on your perimeter.

 Consider the full stack timeline on a single operator machine during a heavy session: AMOURANTHRTX dispatches fabric frames with sealed_time monotonic in FieldSocket; ThermoAccountant writes entropyThisFrame each tick; NEXUS captures socket sentences into field jsonl; Queen browser navigation adds honorability and WebRTC peer events; precision GPS may append sub-micron fixes; sovereign-time.py issues pulses tying realtime to micron_witness. Forensics after an incident require these streams to interleave without contradiction. If thermo spikes appear before the socket event that supposedly caused them because NTP stepped backward, you will chase the wrong process path. If GPS dots drift while clocks are clean, you suspect antenna or simulation tier — correct division of suspicion saves hours.

 The operator timeserver is deliberately boring technology: UDP, JSON, HMAC, append-only jsonl. Boring is good. Fancy distributed consensus algorithms make pretty papers and ugly incident responses when you cannot explain who authorized a skew. Here the authority is the operator key in NEXUS_STATE_DIR and the serve bind you document. Pulses increment. Receipts append. Receivers verify. The story is grep-able start to finish.

 Teach new operators three gestures before anything else: serve , pulse , sync . Then teach one grep: SQUIDGIE . Then open field-services-2026 panel slice and point at sovereign_time block. If they understand those four surfaces, they will not panic when pool NTP disagrees — they already know which source wins under sovereign-first policy.

 Micron witness deserves repetition because it is easily underestimated. Operators who live in software stacks forget silicon tables exist until performance tuning touches cpufreq. Spiderweb already surfaces MHz in Puny tier. Sovereign time hashes MHz into every pulse. That design choice links Chapter 10 hardware mirror literacy with Chapter 19 perimeter literacy — same sysfs read, two receipts. When witness flips fast, you are not required to immediately shout attacker; you are required to stop treating wall labels as evidence until the flip is explained. Explanation might be benign stress test; explanation might be squidgie. The verdict names the latter when thresholds trip.

 Cross-host deployment adds latency but not complexity. Second machine pulls pulse, verifies signature with enrolled key material, compares deltas, writes local pulse state. receive_wall_skew accounts for RTT on LAN. Enrollment documentation should list allowed skew and forbidden clock sources on child hosts — chrony pointing at pool while parent serves sovereign is a common self-inflicted wound. grep processes and configs during onboarding.

 Integration with field-ntp-2026 is the bridge to legacy clients that only speak NTP. Many tools still query UDP 123. Gating mode-4 replies on sovereign health means those tools fail closed when time is dirty — preferable to answering from a stepped pool clock. Stratum semantics remain meaningful: stratum 2 on normal nodes tells clients they are one hop from operator authority; stratum 1 on last host tells survivors there is no higher authority left on the wire. Do not abuse stratum 1 on everyday laptops — honesty labels matter in NTP sociology as much as in Chapter 12 rocks.

 Captain Ellie alignment is not mythology. TotalTime::seal and TotalTime::verify are real C++ paths operators grep via engine logs. ellie-last-host.py verify is real Python path operators grep via covenant files. sovereign-time.py sync is real Python path operators grep via jsonl. Three seals, one ethic: forward only, verify before trust, abort or gate on failure. When students ask which seal is supreme, answer by scope: in-process fabric uses FieldSocket sealed_time; perimeter uses sovereign pulses; last host uses ellie-last-host seal at boot. Scopes nest, they do not compete.

 Landauer and Shannon sit in the creditor chapters, but time is the hidden variable in every entropy story. Shannon surprise without timestamp is a bag of letters. Thermo entropy without timeline is a number without narrative. Sovereign time does not replace thermodynamic measurement — it orders measurement so narratives can be defended in front of another human who was not at your keyboard. That is operator covenant in practice.

 Honest rocks close this primer: implemented UDP signed pulses, implemented verify paths, posture fail-closed parity with engine abort, metaphor correlation for sub-micron SEM claims, philosophy for pool retirement policy. We do not hide rocks. If your deployment cannot run serve on loopback because container networking forbids it, document the container exception in writing and widen bind with firewall story — do not pretend default loopback is optional because convenience complained.

 Architecture diagram in prose — pulse lifecycle

 Issue: operator host samples mono_ns, realtime_ns, sysfs freqs, computes micron_witness and freq_sum_khz, increments pulse counter, signs body, appends receipts.jsonl, optionally serves UDP response.

 Transit: UDP datagram carries JSON receipt to enrolled receiver; no TLS in v1 — LAN trust boundary is operator responsibility; terror-threat posture assumes bind restriction and firewall.

 Verify: receiver validates sig, compares to prev pulse, evaluates skew and witness flip rules, records verdict USER_OK or SQUIDGIE, updates local pulse state.

 Consume: field-ntp-2026 reads sovereign cache; panel reads status json; Queen slice reads sovereign_time_witness flag; operator grep archives jsonl for incidents.

 Recover: fix clock source, rotate key if compromised, re-pulse until three consecutive OK, re-enable gated services, document incident with issues list preserved — never delete SQUIDGIE rows from jsonl.

 Operator runbook template — sovereign time incident

 Detect: grep SQUIDGIE in receipts.jsonl or panel sovereign slice shows dirty cache. Contain: stop field-ntp-2026 client serve if you are downstream; do not delete jsonl. Diagnose: read issues list in last verify block — signature, skew, witness, freq. Remediate: eliminate dual clock sources; fix VM/host clock; rotate key if sig bad. Verify: three consecutive USER_OK from sync. Restore: re-enable NTP gate; archive incident bundle. Postmortem: correlate thermo and packet field with corrected timeline.

 Clock Role Trust

 Monotonic ( CLOCK_MONOTONIC ) Ordering — ticks never go backward Host kernel

 Realtime ( CLOCK_REALTIME ) Wall labels for grep and correlation Your timeserver only

 Sysfs freq witness Spiderweb Puny tier — MHz per core Read-only hardware

 Seal forward. Session genesis and pulse chains only advance.

 Verify at receive. Every downstream host double-checks before trusting wall labels.

 Grep SQUIDGIE. Tamper is a verdict, not a vibe.

 NEXUS_SOVEREIGN_TIME_BIND=127.0.0.1 pythong sovereign-time.py serve
pythong sovereign-time.py pulse
pythong sovereign-time.py sync 127.0.0.1 9123
grep SQUIDGIE /var/lib/nexus-shield/sovereign-time-receipts.jsonl

 micron_witness = sha256(mono_ns | cpu0:freq | cpu1:freq | ...)[0:16]
TotalTime::seal() → FieldSocket::sealed_time (in-process)
sovereign-time.py pulse → HMAC receipt chain (cross-host)

 Operator drills

 Drill 19-A — Baseline seal. Serve, pulse, sync, archive receipts. Goal: three consecutive USER_OK verdicts with stable micron_witness across 60 seconds idle.

 Drill 19-B — Grep discipline. Run engine + NEXUS 10 minutes. Grep SQUIDGIE in sovereign logs and THERMO in engine log. Goal: zero unexplained squidgie; thermo moves when fabric moves.

 Drill 19-C — Freq witness read. While pulsing, read scaling_cur_freq manually. Goal: witness changes only on expected DVFS steps.

 Drill 19-D — NTP gate. With field-ntp-2026.py running, confirm NTP replies stop when sovereign cache dirty after lab skew test.

 Drill 19-E — Cross-host enrollment. Sync from second machine with shared state dir or enrolled key. Goal: document latency and receive_wall_skew within bounds.

 Study questions

 Why three clocks instead of CLOCK_REALTIME alone?

 Difference between TotalTime::seal() and cross-host sovereign pulses?

 Define SQUIDGIE using three detection paths from verify_receipt().

 How is micron_witness computed; what does fast flip imply?

 When GPS and sovereign time disagree, which wins and why?

 What does NEXUS_SOVEREIGN_TIME_FIRST=1 change?

 Where are signing keys stored; what file mode on create?

 How does field-ntp-2026.py gate on sovereign health?

 Why is single-source NTP discipline flow 20 not anti-NTP?

 What forensic artifacts do you archive after a SQUIDGIE incident?

 Chapter 20 — Public DNS, DHCP & Time →

 Sovereign time receipts should be archived with the same discipline as packet field jsonl and thermo log exports. When an auditor asks prove this connection happened before that entropy spike, you interleave three files by pulse number and utc — not by screenshot collage.

 Pool NTP clients on the same host as sovereign serve are a configuration smell. grep unit files and crontab for ntpd chrony systemd-timesyncd. Sovereign-first means those services are disabled or slaved to gated NTP — document the chosen pattern.

 Hypervisor guests enrolled in sovereign mesh should disable host time sync override or verify after every migration. vMotion without re-sync is a classic squidgie source in enterprise labs.

 Precision GPS operators should log sovereign pulse number alongside each ENU fix in local tooling. Correlation field makes sub-micron claims defensible in postmortems.

 Teaching sovereign time to students: use lab VM skew first, production stories second. Students remember SQUIDGIE after they cause it safely themselves.

 The entropy_tag on pulses is twelve hex characters — small enough to grep, large enough to disambiguate adjacent pulses in merged logs.

 Frame-rate jitter in AMOURANTHRTX cannot rewrite sealed_time — that invariant is why session-local and cross-host seals are named differently. Do not merge the concepts when writing runbooks.

 NEXUS daemon restarts should not rotate signing keys automatically — stability of key material is feature for enrolled receivers.

 When LAST_HOST mode serves global TIME, sovereign serve bind may widen — document firewall rules alongside covenant invocation.

 Micron witness flips during kernel cpufreq governor stress tests are expected — witness is witness, not verdict alone. Verdict combines witness speed with skew and freq sum delta.

 Sovereign time receipts should be archived with the same discipline as packet field jsonl and thermo log exports. When an auditor asks prove this connection happened before that entropy spike, you interleave three files by pulse number and utc — not by screenshot collage.
