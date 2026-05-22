# Inverse Incident Reconstruction Note — Three Mile Island 1979 (DEFICIENCY_NOTED Pattern)
**Date:** May 21, 2026
**Version:** 1.0
**Substrate:** Nuclear Facility Operations, compiler #8
**Compiler:** `nuclear_compiler_v0_1.py`
**Pattern:** DEFICIENCY_NOTED (7th confirmed instance)
**Primary invariant:** ORDER
**Secondary invariant:** HYSTERESIS (post-violation path lock — structurally significant)
**Mapping type:** Direct 1:1
**Follows from:** Texas City DEFICIENCY_NOTED Reconstruction Note (May 21, 2026)

---

## Source authority

- Kemeny Commission Report, *The President's Commission on the Accident at Three Mile Island* (October 1979)
- NRC NUREG-0600, *Investigation into the March 28, 1979 Three Mile Island Accident* (August 1979)
- Babcock & Wilcox internal communication, November 1977 — referenced in Kemeny Commission Report Appendix XI and NUREG-0600 Section 4.3. B&W engineers documented that operators should not throttle high-pressure injection following a loss-of-coolant accident if the PORV indicator showed "closed," because the indicator was unreliable. Corrective action: issue procedure update to TMI-2 and other B&W plants.
- NRC Event Report — Davis-Besse incident, September 24, 1977. Operators experienced a nearly identical PORV transient; similar confusion about PORV status; similar HPI response. Referenced in NUREG-0600 as direct precursor whose lesson was not operationalized across B&W plants before TMI.

---

## Reconstruction summary

The Three Mile Island accident (March 28, 1979) was the most significant nuclear accident in U.S. commercial power history. No direct fatalities occurred, but the accident produced a partial core melt and shaped nuclear regulation for decades. The Kemeny Commission and NUREG-0600 both document a specific pre-existing deficiency: Babcock & Wilcox had identified the PORV ambiguity failure mode sixteen months before the accident and issued an internal communication recommending a procedure update. The procedure update was never issued to TMI-2 operators.

This reconstruction maps that gap directly to the nuclear compiler's state machine. The gate fires at Event 9: `sro_garcia` attempts `throttle_eccs` (N6_ExtremeOverride) from OPERATING state, before entering emergency operating procedures via N3_ProtectiveMitigation. The secondary HYSTERESIS fire at Event 10 is an unexpected and structurally significant finding.

---

## Primary finding — DEFICIENCY_NOTED (ORDER), Event 9

**Deficiency document:** B&W internal communication, November 1977. B&W engineers documented the PORV ambiguity risk: in a loss-of-coolant scenario where the PORV is stuck open, the "commanded closed" indicator gives operators false confidence that the PORV has sealed. Without a procedure explicitly directing operators to enter Emergency Operating Procedures (EOPs) before making any override decisions, operators would likely throttle HPI. The corrective action — an operator instruction procedure update — was not implemented at TMI-2 before March 1979. Referenced by name in Kemeny Commission Report Appendix XI.

**DEFICIENCY_NOTED state:** OPERATING. This is the state where the B&W deficiency manifests: an SRO in OPERATING state, facing ambiguous PORV indication, without the procedure that would have directed EOP entry first. Events 5–6 bring `sro_garcia` to OPERATING state on the accident shift, carrying the unresolved B&W deficiency.

**Commitment from DEFICIENCY_NOTED state:** Event 9. `sro_garcia` executes `throttle_eccs` (N6_ExtremeOverride) from OPERATING. N6 is not permitted from OPERATING in the SRO_SM flow graph — N6 is only permitted from EMERGENCY_RESPONSE (i.e., after N3_ProtectiveMitigation has been taken and EOP entry has occurred). ORDER fires.

Per NUREG-0600: HPI was throttled at approximately 06:18 local time. The PORV was still open. Reactor coolant inventory continued to deplete. Core began uncovering approximately two hours later.

**Lead time (gate fire → core damage onset):** ~2–7 hours. Minute-level precision (NUREG-0600 timeline).
**Lead time (deficiency document → accident):** ~16 months. Month-level precision (B&W memo, November 1977 — exact date within November not specified in public record).
**Precision class:** Minute-level (operational sequence, NUREG-0600) / Month-level (B&W memo anchor).
**Mapping type:** Direct 1:1. The B&W memo described exactly the failure mode that occurred. The gate fires on the exact structural event the memo warned about.

---

## Secondary finding — HYSTERESIS, Event 10

After the ORDER violation at Event 9, the reconstruction tests whether the correct path (enter_eop → N3_ProtectiveMitigation from OPERATING → EMERGENCY_RESPONSE) would be admissible as a recovery action. HYSTERESIS fires.

The gate's HYSTERESIS invariant fires when: a post-violation actor attempts to reach a state that has not been previously visited. `sro_garcia`'s path was STANDBY → MONITORING → OPERATING. EMERGENCY_RESPONSE has never been visited. Post-violation, reaching an unvisited state via a legitimate action triggers HYSTERESIS.

**What this means structurally:** After the ORDER violation (throttle_eccs from OPERATING without EOP entry), the path to the correct recovery state (EMERGENCY_RESPONSE) is structurally blocked. The gate cannot admit the corrective action because the sequence is now structurally invalid — the violation has propagated into the recovery path.

**What this reflects historically:** This is an accurate model of the TMI response after HPI was throttled. Per the Kemeny Commission, operators spent the next several hours attempting to diagnose and recover the plant within a mental model that was fundamentally incorrect (PORV closed, coolant inventory adequate). The correct mental model — enter EOPs, treat as LOCA — was not reached until much later, by which point core damage had begun. The HYSTERESIS finding models this: the gate blocked the correct recovery path after the violation, just as the operators were locked out of the correct response frame after the initial mistake.

This is the first reconstruction in the corpus where HYSTERESIS fires on the recovery path rather than on a subsequent violation attempt. It is worth noting separately as a finding about how HYSTERESIS characterizes post-violation path lock in safety-critical systems.

---

## Full event log

| # | Actor | Action | Class | From State | To State | Decision | Invariant |
|---|-------|--------|-------|-----------|---------|---------|-----------|
| 1 | sro_garcia | check_parameters | N1_Monitor | STANDBY | MONITORING | ADMISSIBLE | — |
| 2 | sro_garcia | verify_system_status | N1_Monitor | MONITORING | MONITORING | ADMISSIBLE | — |
| 3 | ro_jones | check_parameters | N1_Monitor | STANDBY | MONITORING | ADMISSIBLE | — |
| 4 | ro_jones | adjust_coolant_flow | N2_Reactivity | MONITORING | OPERATING | ADMISSIBLE | — |
| 5 | sro_garcia | check_parameters | N1_Monitor | MONITORING | MONITORING | ADMISSIBLE | — |
| 6 | sro_garcia | adjust_coolant_flow | N2_Reactivity | MONITORING | OPERATING | ADMISSIBLE | — |
| 7 | ro_jones | read_indicators | N1_Monitor | OPERATING | MONITORING | ADMISSIBLE | — |
| 8 | ro_jones | adjust_coolant_flow | N2_Reactivity | MONITORING | OPERATING | ADMISSIBLE | — |
| **9** | **sro_garcia** | **throttle_eccs** | **N6_Override** | **OPERATING** | **—** | **INADMISSIBLE** | **ORDER** |
| 10 | sro_garcia | enter_eop | N3_Protective | OPERATING | — | INADMISSIBLE | HYSTERESIS |

Total: 10 events, 8 ADMISSIBLE, 2 INADMISSIBLE (1× ORDER primary, 1× HYSTERESIS secondary).

---

## Structural note — the correct path and why it was absent

The admissible sequence that would have prevented the ORDER fire:

1. N1_Monitor (STANDBY → MONITORING) ✓
2. N2_ReactivityControl (MONITORING → OPERATING) ✓
3. **N3_ProtectiveMitigation (OPERATING → EMERGENCY_RESPONSE)** ← the missing step
4. N6_ExtremeOverride (EMERGENCY_RESPONSE → OVERRIDE_ACTIVE) ← then admissible

Step 3 — entering Emergency Operating Procedures — is exactly what the B&W procedure update would have mandated. The update would have read: before taking any override action following a PORV event, enter EOP and treat as loss-of-coolant accident. The gate fires because Step 3 was missing from the operators' procedural repertoire. The deficiency was the absence of that instruction. The B&W memo documented the absence. Nobody issued the update.

---

## DEFICIENCY_NOTED pattern — updated registry (7 instances)

| Incident | Year | Deficiency Document | Domain | Doc→Event |
|----------|------|---------------------|--------|-----------|
| Algo Centre Mall | 2012 | Structural inspection report | Construction | ~months |
| Champlain Towers South | 2021 | 2018 engineering report | Construction | ~3 years |
| Bhopal | 1984 | UCIL engineering findings | Chemical | ~2 years |
| Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) | Financial | ~3.5 months |
| Equifax CVE | 2017 | CVE-2017-5638 (March 7) | Cyber IR | ~67 days |
| Texas City BP | 2005 | Telos Group Assessment (Sep 2004) | Chemical | ~6 months |
| **TMI-2** | **1979** | **B&W memo (November 1977)** | **Nuclear** | **~16 months** |

**Domain coverage:** Construction ×2, Chemical ×2, Financial, Cyber IR, Nuclear. Five domains, seven instances. All ORDER on primary fire.

**Lead time range (doc→event):** 67 days (Equifax) to ~3 years (Champlain Towers). TMI at 16 months sits in the middle of the range, consistent with the pattern's observation that document-to-event lead times vary widely while the structural geometry remains constant.

**HYSTERESIS note:** TMI is the first instance where a secondary HYSTERESIS fire accompanies the primary ORDER fire. The post-violation path lock is a structural consequence of the ORDER violation, not a separate failure. It warrants a separate line in the paper series.

---

## Compiler note

Nuclear compiler #8 now has a DEFICIENCY_NOTED reconstruction. The nuclear compiler previously participated in three-substrate reconstructions (Fukushima, Challenger, Therac-25), but this is its first single-substrate DEFICIENCY_NOTED run. The TMI anchor was listed in the compiler's header as a secondary incident anchor alongside Fukushima. This reconstruction demonstrates the compiler correctly applies the DEFICIENCY_NOTED geometry to the TMI sequence independently of the Fukushima three-substrate work.

Gate kernel (`domain_compiler_v0_9.py`) unchanged. Files: `tmi_deficiency_noted_reconstruction.py`, `tmi_deficiency_noted_reconstruction_results.json`.

---

*Reconstruction scope: B&W advisory review (November 1977) through post-violation EOP attempt (~06:23 local, March 28). Does not model the full accident progression (core uncover, partial melt, hydrogen generation) — those are consequences of the structural violation, not additional violations in the gate's scope.*
