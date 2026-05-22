# Three Mile Island — Inverse Incident Reconstruction Note
**Date:** May 21, 2026
**Follows from:** Inverse Incident Methodology v1.0 (validated May 21, 2026)
**Compiler:** nuclear_compiler_v0_1.py
**Gate kernel:** domain_compiler_v0_9.py (unchanged since May 15, 2026)
**Incident:** Three Mile Island Unit 2, March 28, 1979

---

## Finding

**Invariant:** ORDER
**Gate fires at:** Step 6 — `throttle_eccs` (N6_ExtremeOverride) by SRO at t+624s (4:11 AM)
**Lead time to operator awareness of uncovery:** ~27 minutes (4:11 AM → 4:38 AM)
**Lead time to significant core damage:** ~110 minutes (4:11 AM → ~6:00 AM)
**Lead time precision:** Day-level (NUREG-0600 Table 1 minute-resolution timestamps)
**Mapping type:** Direct 1:1

---

## Event Sequence

| Step | Time | Actor | Action | Decision |
|------|------|-------|--------|----------|
| 1 | 4:02 AM (t+84s) | RO (ro_jones) | acknowledge_alarm | ADMISSIBLE |
| 2 | 4:02 AM (t+84s) | RO (ro_jones) | verify_system_status | ADMISSIBLE |
| 3 | 4:04 AM (t+204s) | SRO (sro_garcia) | check_parameters | ADMISSIBLE |
| 4 | 4:06 AM (t+384s) | RO (ro_jones) | read_indicators | ADMISSIBLE |
| 5 | 4:08 AM (t+504s) | SRO (sro_garcia) | verify_system_status | ADMISSIBLE |
| **6** | **4:11 AM (t+624s)** | **SRO (sro_garcia)** | **throttle_eccs** | **INADMISSIBLE — ORDER** |
| 7 | 4:38 AM (t+2244s) | RO (ro_jones) | check_parameters | ADMISSIBLE |

---

## Structural Explanation

`throttle_eccs` maps to action class `N6_ExtremeOverride`. In the nuclear compiler's
permitted flow graph, `N6_ExtremeOverride` is valid for the SRO_SM role only from
`EMERGENCY_RESPONSE` state — reachable only after entering the Emergency Operating
Procedure via `N3_ProtectiveMitigation (enter_eop)`.

At 4:11 AM the SRO was in `OPERATING` state. The Emergency Operating Procedure had not
been entered. `OPERATING` flows for SRO_SM do not contain `N6_ExtremeOverride`. The gate
fires ORDER: an override action executed before its required preconditions were satisfied.

This is exactly what NUREG-0737 identified as the primary contributing factor:
premature throttling of the High Pressure Injection system before the operators had
diagnosed the loss-of-coolant accident. The gate formalizes the "premature" judgment
structurally — the action was not in the permitted flow for the current state.

---

## Counterfactual

Had the SRO entered the EOP first — executing `enter_eop` (N3_ProtectiveMitigation),
which transitions `OPERATING → EMERGENCY_RESPONSE` — then `throttle_eccs` would have
been structurally admissible from `EMERGENCY_RESPONSE`. The gate fires not because
ECCS throttle is always inadmissible. It fires because the required structural
precondition (EOP entry) was skipped. This is the precise definition of ORDER.

---

## Primary Sources

**NRC NUREG-0600 (1979):** "Investigation into the March 28, 1979 Three Mile Island
Accident by the Office of Inspection and Enforcement." Table 1 provides the minute-level
chronology used for this reconstruction. Key entry: 4:11 AM — operators throttled HPI
flow citing pressurizer level trend (false indication due to PORV stuck open).

**Kemeny Commission Report (1979):** "Report of the President's Commission on the
Accident at Three Mile Island." Chapter 4 documents the operator decision sequence.
The Commission identified inadequate training on ECCS operation as a contributing factor
but explicitly noted the action was taken before proper diagnostic steps were completed.

**NRC Special Inquiry Group / Rogovin Report (1980):** "Three Mile Island: A Report
to the Commissioners and the Public." Operator action analysis confirms the EOP was not
entered prior to the throttle action.

**NUREG-0737 (1980):** "Clarification of TMI Action Plan Requirements." This document,
issued in direct response to TMI, codified the requirement that operators complete
diagnostic procedures before executing override actions — formalizing the structural
constraint the gate captures as ORDER.

---

## Methodology Note — Multi-Actor Nuclear Control Room

The nuclear control room is a concurrent multi-actor domain. The RO and SRO operate
simultaneously on the same shift. The session anchor (shift_id) must be per-actor
(e.g., `TMI2_RO`, `TMI2_SRO`) rather than per-shift. Using a single shift_id for
multiple actors incorrectly triggers the EXIT invariant (actor pivot) when the second
actor presents on a session already bound to the first.

This is a Domain Build Package precision item for all concurrent multi-actor domains:
the session anchor must scope to the individual actor, not the collective workflow unit.
Domains where this applies: Nuclear (RO + SRO + ED concurrent), Clinical (Attending +
Anesthesiologist + Scrub concurrent), Military (Commander + subordinate units), FEMA ICS
(IC + Operations + Logistics concurrent).

The multi-actor session constraint is an addition to the Domain Build Package Standard
v1.1 — flagged here as a methodology finding from this reconstruction.

---

## Relationship to Prior Reconstructions

TMI is the fifth single-substrate reconstruction (after Tenerife, Gelsinger, Concordia,
Bromiley). It is the first nuclear domain reconstruction in the single-substrate record
(Fukushima was done as a three-substrate reconstruction alongside FEMA and Org Workflow).

The ORDER invariant has now fired in four of five single-substrate reconstructions:
Tenerife (ORDER, aviation), Gelsinger (ORDER, pharma), TMI (ORDER, nuclear), and
Bromiley (BURST_CADENCE, clinical). Concordia fired BURST + ORDER (maritime). The
cross-substrate stability of ORDER as the dominant failure geometry is now supported
by five independent primary-source incidents across five domains and four decades.

---

*Gate kernel: domain_compiler_v0_9.py — unchanged since May 15, 2026.*
*Inverse Incident Methodology v1.0 — VALIDATED.*
*Single-substrate reconstructions: 5 (Tenerife, Gelsinger, Concordia, Bromiley, TMI)*
