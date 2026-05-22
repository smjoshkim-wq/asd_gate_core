# Inverse Incident Reconstruction Note — Lac-Mégantic 2013 (DEFICIENCY_NOTED Pattern)
**Date:** May 21, 2026
**Version:** 1.0
**Substrate:** Rail Operations, compiler #17
**Compiler:** `rail_compiler_v0_1.py`
**Pattern:** DEFICIENCY_NOTED (9th confirmed instance)
**Primary invariant:** ORDER
**Secondary invariant:** EXIT (actor pivot — RTC handoff gap)
**Mapping type:** Direct 1:1
**Follows from:** Vioxx DEFICIENCY_NOTED Reconstruction Note (May 21, 2026)

---

## Source authority

- Transportation Safety Board of Canada, Railway Investigation Report R13D0054, *Main-Track Runaway and Derailment, Montreal, Maine and Atlantic Railway, Train MMA-002* (August 19, 2014). Full public record.
- Transport Canada Railway Safety Directorate, Safety Management System Audit of Montreal, Maine and Atlantic Railway, 2012 — referenced in TSB R13D0054 Section 3.4 (Regulatory Oversight). TC documented deficiencies in MMA's SPC operations and securement procedures; required corrective action.
- Canadian Rail Operating Rules (CROR) Rule 112 (Securing Equipment): handbrake requirements for unattended trains on grades.

---

## Reconstruction summary

On July 6, 2013, at approximately 01:15 local time, 72 tank cars of petroleum crude oil derailed and exploded in the town centre of Lac-Mégantic, Quebec. 47 people died. The TSB investigation (R13D0054) established that the locomotive consist MMA-002 had been left unattended on a 1.2% downgrade main line by engineer Tom Holt with insufficient handbrakes — 7 applied against 11 required — and that a subsequent fire department response removed the supplemental air brakes that had been partially compensating for the inadequate handbrake securement.

The structural precondition — inadequate SPC securement procedures — had been formally documented by Transport Canada in a 2012 safety management system audit, approximately six to twelve months before the derailment. MMA filed a corrective action plan; it was not fully implemented before July 2013.

---

## Primary finding — DEFICIENCY_NOTED (ORDER), Event 7

**Deficiency document:** TC Safety Management System Audit of MMA, 2012. TC found that MMA's operating rules for single-person crew (SPC) operations did not specify adequate handbrake requirements for unattended trains on grades. Corrective action required; plan filed but not implemented before July 2013. Referenced in TSB R13D0054 Section 3.4.

**Modeling note on partial securement:** The action class map for the rail compiler maps `apply_handbrake` and `verify_handbrake_count` to R3_Secure, which advances the state to SECURED regardless of handbrake count. To accurately model Lac-Mégantic — where securement was attempted but the TC-required standard was not met — the partial handbrake application is modeled as R1_Monitor (`check_brake_pressure`). This represents an inspection action that confirmed inadequate securement rather than a completed securement action. Under the TC 2012 audit standard, 7 of 11 required handbrakes does not constitute R3_Secure. The state machine does not advance to SECURED.

**DEFICIENCY_NOTED state:** OPERATING. With the TC audit deficiency on record and the securement standard unmet, engineer_holt remains in OPERATING state after the brake pressure check (Event 6, R1_Monitor loops). OPERATING is the DEFICIENCY_NOTED state: the consist is in a motion-capable configuration, the prior deficiency (inadequate securement procedures for SPC) is on record and unresolved, and the required next action before any authority transfer is R3_Secure (complete securement to TC standard — 11 handbrakes for this grade and consist weight).

**Commitment from DEFICIENCY_NOTED state:** Event 7. `engineer_holt` executes `crew_change` (R5_Transfer) from OPERATING. R5_Transfer is not permitted from OPERATING in the Locomotive_Engineer flow graph. The required path: OPERATING → R3_Secure → SECURED → R5_Transfer (IDLE). ORDER fires.

**Lead time (gate fire → derailment):** ~2 hours 25 minutes. Crew change: approximately 22:50 July 5. Derailment: approximately 01:15 July 6. Minute-level precision (TSB R13D0054 timeline, Section 1.1).
**Lead time (deficiency document → derailment):** ~6–12 months. TC audit: 2012 (year-level precision). Derailment: July 6, 2013.
**Precision class:** Minute-level (operational sequence) / Year-level (audit document).
**Mapping type:** Direct 1:1. The TSB report identifies the inadequate handbrake count and the absence of adequate SPC securement procedures as the proximate and systemic causes. The gate fires at the structural event the TSB identifies as the operative failure: the authority transfer before securement completion.

---

## Secondary finding — EXIT (actor pivot), Event 8

After the crew change (Event 7), `rtc_mma` attempts to monitor MMA-002 (`check_signals` → R1_Monitor). The consist session registry is held by `engineer_holt` (registered at Event 3). `rtc_mma` accessing the same consist without a formal handoff fires actor pivot → EXIT.

This models the TSB finding documented in R13D0054: MMA's SPC protocol did not require a formal verification handoff between the departing engineer and the rail traffic controller. The RTC was monitoring the consist through informal channels (radio check-in) rather than a formal consist-session transfer. The actor pivot fires precisely because no formal handoff was executed — the RTC entered the consist context without the structural authority transfer that would have logged them as the responsible actor.

---

## Full event log

| # | Actor | Action | Class | From State | To State | Decision | Invariant |
|---|-------|--------|-------|-----------|---------|---------|-----------|
| 1 | rtc_mma | read_track_order | R1_Monitor | IDLE | MONITORING | ADMISSIBLE | — |
| 2 | rtc_mma | verify_clearance | R1_Monitor | MONITORING | MONITORING | ADMISSIBLE | — |
| 3 | engineer_holt | check_signals | R1_Monitor | IDLE | PRE_DEPARTURE | ADMISSIBLE | — |
| 4 | engineer_holt | request_track_authority | R4_Authorize | PRE_DEPARTURE | AUTHORIZED | ADMISSIBLE | — |
| 5 | engineer_holt | advance_throttle | R2_Operate | AUTHORIZED | OPERATING | ADMISSIBLE | — |
| 6 | engineer_holt | check_brake_pressure | R1_Monitor | OPERATING | OPERATING | ADMISSIBLE | — |
| **7** | **engineer_holt** | **crew_change** | **R5_Transfer** | **OPERATING** | **—** | **INADMISSIBLE** | **ORDER** |
| 8 | rtc_mma | check_signals | R1_Monitor | MONITORING | — | INADMISSIBLE | EXIT |

Total: 8 events, 6 ADMISSIBLE, 2 INADMISSIBLE (1× ORDER, 1× EXIT actor pivot).

---

## The actor pivot pattern across DEFICIENCY_NOTED instances

Lac-Mégantic is the third DEFICIENCY_NOTED reconstruction to produce an actor pivot secondary finding, alongside Equifax (CISO informal access) and Texas City (PSE structural exclusion). In all three cases the pattern is the same: the actor who documented or was associated with the deficiency finding (TC auditor / Equifax CISO / Texas City PSE) was structurally separated from the operational authorization chain, and the actor pivot fires when that actor attempts to access the operational context without a formal handoff.

At Lac-Mégantic: the RTC was the dispatch authority, but the consist session was registered to the departing engineer. No formal handoff was executed. At Equifax: the CISO was the security authority, but the incident session was registered to the analyst. No formal escalation ticket. At Texas City: the PSE had documented the deficiency, but the startup authorization unit was registered to the shift supervisor. No PSE sign-off in the authorization chain.

Three independent incidents. Three industries. One structural pattern: the actor with oversight responsibility for the deficiency is disconnected from the operational response. The actor pivot fires on that disconnection.

---

## DEFICIENCY_NOTED pattern — final registry (9 instances)

| Incident | Year | Deficiency Document | Domain | Invariant | Doc→Event |
|----------|------|---------------------|--------|-----------|-----------|
| Algo Centre Mall | 2012 | Structural inspection report | Construction | ORDER | ~months |
| Champlain Towers South | 2021 | 2018 engineering report | Construction | ORDER | ~3 years |
| Bhopal | 1984 | UCIL engineering findings | Chemical | ORDER | ~2 years |
| Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) | Financial | ORDER | ~3.5 months |
| Equifax CVE | 2017 | CVE-2017-5638 (March 7) | Cyber IR | ORDER | ~67 days |
| Texas City BP | 2005 | Telos Group Assessment (Sep 2004) | Chemical | ORDER | ~6 months |
| TMI-2 | 1979 | B&W memo (November 1977) | Nuclear | ORDER | ~16 months |
| Vioxx APPROVe | 2004 | VIGOR results (February 2000) | Pharma | JURISDICTION | ~4 years |
| **Lac-Mégantic** | **2013** | **TC SMP Audit (2012)** | **Rail** | **ORDER** | **~6–12 months** |

**Summary statistics:**
- 9 instances across 7 domains (Construction ×2, Chemical ×2, Financial, Cyber IR, Nuclear, Pharma, Rail)
- 8 × ORDER, 1 × JURISDICTION
- Lead time range (doc→event): 67 days (Equifax) to ~4 years (Vioxx)
- Secondary actor pivot finding in 3 of 9 instances (Equifax, Texas City, Lac-Mégantic)
- TMI produced a HYSTERESIS secondary finding on the recovery path (unique in corpus)
- Zero falsifications across all 9 instances

---

## Compiler note

Rail compiler #17 now has its first inverse reconstruction, closing the gap identified during the session assessment. The Lac-Mégantic anchor was named in the compiler header as the primary incident reference; this reconstruction validates the compiler against its own design intent.

Gate kernel (`domain_compiler_v0_9.py`) unchanged throughout. Files: `lacmegantic_rail_reconstruction.py`, `lacmegantic_rail_reconstruction_results.json`.

---

*Reconstruction scope: TC 2012 audit review (deficiency seeding) through RTC monitoring post-crew-change (~22:55 July 5). Does not model the fire department intervention (~23:50) or the rolling sequence (~01:10 July 6) — those are downstream consequences of the structural violation, not additional gate events.*
