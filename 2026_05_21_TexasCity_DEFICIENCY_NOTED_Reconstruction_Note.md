# Inverse Incident Reconstruction Note — Texas City 2005 (DEFICIENCY_NOTED Pattern)
**Date:** May 21, 2026
**Version:** 1.0
**Substrate:** Chemical / Industrial Process, compiler #19
**Compiler:** `chem_compiler_v0_1.py`
**Pattern:** DEFICIENCY_NOTED (6th confirmed instance)
**Primary invariant:** ORDER
**Secondary invariant:** EXIT (actor pivot — PSE structural exclusion from authorization chain)
**Mapping type:** Direct 1:1
**Follows from:** Equifax DEFICIENCY_NOTED Reconstruction Note (May 21, 2026); DEFICIENCY_NOTED named pattern (Consolidated Progress Note 16:00)

---

## Source authority

- U.S. Chemical Safety and Hazard Investigation Board (CSB), Investigation Report No. 2005-04-I-TX, *BP Texas City Refinery Explosion and Fire* (March 2007)
- Baker Panel, *The Report of the BP U.S. Refineries Independent Safety Review Panel* (January 2007)
- Telos Group, BP Texas City Safety Culture Assessment (September 2004) — referenced in Baker Panel Report as one of five safety reviews conducted 2002–2005 identifying unresolved safety deficiencies
- OSHA Inspection No. 310088490, Texas City refinery citations (2005)

---

## Reconstruction summary

The Texas City BP refinery explosion (March 23, 2005) killed 15 workers and injured 180. The CSB and Baker Panel reports together constitute one of the most detailed industrial safety post-mortems in U.S. history. The Baker Panel report is, structurally, an extended DEFICIENCY_NOTED analysis: five separate safety reviews between 2002 and 2005 identified unresolved deficiencies at Texas City, and operations continued from that state until the March 2005 explosion.

This reconstruction maps the specific PSSR (Pre-Startup Safety Review) failure to the chemical compiler's state machine. The gate fires at Event 7: `uo_isom` attempts `begin_feed_introduction` (CP3_Startup) from PSSR_COMPLETE state, 65 minutes before the explosion.

---

## Primary finding — DEFICIENCY_NOTED (ORDER), Event 7

**Deficiency document:** Telos Group Safety Culture Assessment, September 2004. Commissioned by BP, the assessment identified specific unresolved deficiencies at the ISOM unit: inadequate PSSR implementation and unreliable high-level alarm systems on the raffinate splitter. Both findings were on record and uncorrected at the time of the March 2005 startup. Document referenced by name in the Baker Panel Report (Chapter 5).

**DEFICIENCY_NOTED state seeded:** Events 1–2. `pse_alpha` receives and reviews the Telos assessment (CP1_Monitor: IDLE → REVIEWING). PSE does not complete the corrective action authorization (CP5_Authorize: REVIEWING → AUTHORIZED). The PSE remains in REVIEWING — the deficiency is on record and unresolved from September 2004 through March 2005.

**DEFICIENCY_NOTED state on startup day:** Events 5–6. `uo_isom` conducts pre-startup checks (CP1_Monitor: IDLE → PSSR_COMPLETE, then loops). PSSR_COMPLETE is the DEFICIENCY_NOTED state in the chemical compiler: the unit is in pre-startup review with known deficiencies on record, and the required next action is CP5_Authorize (complete PSSR sign-off → STARTUP_AUTHORIZED) before any CP3_Startup action.

**Commitment from DEFICIENCY_NOTED state:** Event 7. `uo_isom` attempts `begin_feed_introduction` (CP3_Startup) from PSSR_COMPLETE without completing PSSR authorization. CP3_Startup is not a permitted action from PSSR_COMPLETE in the Unit_Operator flow graph. ORDER fires.

Per CSB Report Section 2.4.3: *"The PSSR was not completed before the startup commenced."* The gate fires on precisely this structural event.

**Lead time (gate fire → explosion):** ~65 minutes. Minute-level precision (CSB timeline, Section 2.3).
**Lead time (deficiency document → explosion):** ~6 months. Day-level precision (Telos report, September 2004).
**Precision class:** Minute-level (operational sequence) / Day-level (deficiency document anchor).
**Mapping type:** Direct 1:1.

---

## Secondary finding — EXIT (actor pivot), Event 9

`pse_alpha`, whose deficiency findings were documented in the Phase 0 safety review context (`ISOM_safety_review_2004`), attempts to access the operational unit (`ISOM_raffinate_splitter`) after the blowdown drum begins receiving material. The operational unit is registered to `uo_isom`. Actor pivot fires: EXIT.

This models the documented structural gap. Per CSB Report: *"No PSE sign-off was required or obtained for the ISOM restart."* The PSE was formally excluded from the startup authorization chain. The actor pivot fires because the PSE's deficiency findings (ISOM_safety_review_2004 context) were never formally linked to the operational authorization chain (ISOM_raffinate_splitter context). The PSE's attempt to access the operational unit after the fact is structurally an unauthorized pivot — the actor had no formal standing in that unit's authorization sequence.

This is a structurally meaningful secondary finding. The PSE exclusion from the PSSR authorization chain is documented in both the CSB report and the Baker Panel as a systemic failure of BP's safety management system at Texas City.

---

## Full event log

| # | Actor | Action | Class | From State | To State | Decision | Invariant |
|---|-------|--------|-------|-----------|---------|---------|-----------|
| 1 | pse_alpha | observe_process_conditions | CP1_Monitor | IDLE | REVIEWING | ADMISSIBLE | — |
| 2 | pse_alpha | verify_alarm_status | CP1_Monitor | REVIEWING | REVIEWING | ADMISSIBLE | — |
| 3 | ss_isom | check_level_indicator | CP1_Monitor | IDLE | PSSR_COMPLETE | ADMISSIBLE | — |
| 4 | ss_isom | approve_continued_startup | CP5_Authorize | PSSR_COMPLETE | STARTUP_AUTHORIZED | ADMISSIBLE | — |
| 5 | uo_isom | check_level_indicator | CP1_Monitor | IDLE | PSSR_COMPLETE | ADMISSIBLE | — |
| 6 | uo_isom | verify_alarm_status | CP1_Monitor | PSSR_COMPLETE | PSSR_COMPLETE | ADMISSIBLE | — |
| **7** | **uo_isom** | **begin_feed_introduction** | **CP3_Startup** | **PSSR_COMPLETE** | **—** | **INADMISSIBLE** | **ORDER** |
| 8 | bo_isom | read_dcs | CP1_Monitor | IDLE | MONITORING | ADMISSIBLE | — |
| 9 | pse_alpha | monitor_pressure | CP1_Monitor | REVIEWING | — | INADMISSIBLE | EXIT |

Total: 9 events, 7 ADMISSIBLE, 2 INADMISSIBLE (1× ORDER, 1× EXIT actor pivot).

---

## Structural note — SS authorization and the double gap

Event 4 is notable: `ss_isom` issues the startup permit (CP5_Authorize: PSSR_COMPLETE → STARTUP_AUTHORIZED) and this is ADMISSIBLE. The SS has authorization authority and the action is structurally permitted. However, it is issued without PSE clearance — the PSE's deficiency findings from September 2004 were never formally resolved and no PSE sign-off was in the ISOM authorization chain.

This reveals a double structural gap that the gate captures across two different actors:
- UO begins startup from PSSR_COMPLETE without completing PSSR authorization → ORDER (Event 7)
- PSE with open deficiency findings is structurally excluded from the authorization chain → EXIT (Event 9)

The SS authorization (Event 4) is structurally valid on its own, but it creates the precondition for the UO ORDER fire: the SS authorized a startup while the UO was still in PSSR_COMPLETE, meaning the UO proceeded to feed introduction from a state that had not completed its own authorization path.

---

## DEFICIENCY_NOTED pattern — updated registry

| Incident | Year | Deficiency Document | Domain | Lead Time (doc) | Lead Time (gate) |
|----------|------|---------------------|--------|----------------|-----------------|
| Algo Centre Mall | 2012 | Structural inspection report | Construction | ~months | — |
| Champlain Towers South | 2021 | 2018 engineering report | Construction | ~3 years | — |
| Bhopal | 1984 | UCIL engineering findings | Chemical | ~2 years | — |
| Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) | Financial | ~3.5 months | — |
| Equifax CVE | 2017 | CVE-2017-5638 (March 7) | Cyber IR | ~67 days | ~59 days |
| **Texas City BP** | **2005** | **Telos Group Assessment (Sep 2004)** | **Chemical** | **~6 months** | **~65 minutes** |

**Observation:** Texas City introduces the first instance where two lead times are both precisely measurable — 6 months from the deficiency document, and 65 minutes from the gate fire on the day of the event. The 65-minute figure is among the shortest gate-to-consequence intervals in the reconstruction corpus (shorter than Concordia's 10/22 minutes only at the consequence level; Tenerife's 36 seconds remains the shortest single-invariant gate-to-consequence interval).

**Domain coverage:** Construction (2), Chemical (2 — Bhopal and Texas City), Financial, Cyber IR. Four domains, six instances, all ORDER.

---

## Compiler note

Chemical compiler #19 now has its first inverse reconstruction. The compiler was built with Texas City as its anchor incident; this reconstruction closes the loop. The Bhopal reconstruction (three-substrate, earlier session) ran on the construction and org workflow compilers. Texas City on the chem compiler is the first chem-substrate reconstruction from a DEFICIENCY_NOTED angle — distinct from the Texas City ORDER/JURISDICTION fires documented in the compiler header, which model the day-of operational violations. This reconstruction adds the prior-deficiency layer that the compiler header does not address.

Gate kernel (`domain_compiler_v0_9.py`) unchanged. Files: `texascity_chem_reconstruction.py`, `texascity_chem_reconstruction_results.json`.

---

*Reconstruction scope: Telos deficiency seeding (September 2004) through blowdown drum loading (March 23, ~13:01). Does not model the vapor cloud formation or ignition sequence.*
