# Inverse Incident Reconstruction Note — Equifax 2017 (DEFICIENCY_NOTED Pattern)
**Date:** May 21, 2026
**Version:** 1.0
**Substrate:** Cyber — Incident Response (Human Layer), compiler #16
**Compiler:** `cyber_ir_compiler_v0_1.py`
**Pattern:** DEFICIENCY_NOTED (5th confirmed instance)
**Primary invariant:** ORDER
**Secondary invariant:** EXIT (actor pivot — unexpected, structurally valid)
**Mapping type:** Direct 1:1
**Follows from:** 2026_05_21_Consolidated_Progress_Note_1606.md; DEFICIENCY_NOTED named pattern (Part 5, 1600 note)

---

## Source authority

- U.S. Senate Committee on Commerce, Science, and Transportation, *Examining Equifax's Data Security*, Hearing (November 8, 2017)
- U.S. House Committee on Oversight and Government Reform, *The Equifax Data Breach*, Staff Report (December 2018)
- Apache Software Foundation, CVE-2017-5638 advisory (March 7, 2017)
- U.S. Department of Homeland Security / US-CERT notification to Equifax (March 8, 2017) — referenced in Senate testimony
- Equifax Inc., SEC Form 8-K (September 7, 2017)
- Federal Trade Commission, *United States v. Equifax Inc.*, Consent Order (July 2019)

---

## Reconstruction summary

The Equifax 2017 breach is the canonical incident anchor for Cyber IR compiler #16. This reconstruction applies the DEFICIENCY_NOTED pattern to the specific window between CVE receipt (March 7–8, 2017) and breach initiation (May 13, 2017), mapping the structural commitment event to the compiler's state machine.

The reconstruction produced five gate fires across nine events — more than the primary DEFICIENCY_NOTED fire anticipated. Three findings are documented below in order of significance.

---

## Primary finding — DEFICIENCY_NOTED (ORDER), Event 4

**Deficiency document:** CVE-2017-5638 (Apache Software Foundation, March 7, 2017). CVSS score 10.0 (Critical). US-CERT notification issued to Equifax March 8, 2017. Both documents are publicly available primary sources.

**DEFICIENCY_NOTED state seeded:** Event 2 (Day 2, March 9). `analyst_equifax` completes `assess_severity` (IR2_Triage), transitioning from ALERT_RECEIVED → TRIAGED. TRIAGED is the DEFICIENCY_NOTED state in this compiler: a formally documented critical vulnerability is on record and the required next action is IR3_Contain (`patch_vulnerability`).

**Commitment from DEFICIENCY_NOTED state:** Event 4 (Day 9, approximately March 16). Internal patch deadline passes without IR3_Contain. `analyst_equifax` returns to standard SIEM monitoring (`monitor_siem` → IR1_Detect) from TRIAGED state.

IR1_Detect is not a permitted action from TRIAGED in the IR_Analyst flow graph. TRIAGED permits only IR2_Triage (loop) and IR3_Contain (→ CONTAINED). Attempting IR1_Detect from TRIAGED fires ORDER.

**Gate fires:** Day 9 (~March 16, 2017). Breach initiation: Day 67 (May 13, 2017).
**Lead time:** ~59 days (day-level precision).
**Precision class:** Day-level. The March patch deadline is documented in Senate testimony; the exact date of the failed scan within that window is reconstructed from testimony rather than timestamped to the hour.

This is a Direct 1:1 mapping. The Senate report identifies the failure to patch after CVE receipt as the proximate cause. The gate fires at the same structural event.

---

## Secondary finding — Actor pivot (EXIT), Events 5–7

**Unexpected result, structurally valid.**

When `ciso_equifax` attempts to access incident CVE-2017-5638 in Events 5–7, the actor pivot check fires. The session registry records `analyst_equifax` as the primary actor for this incident ID. `ciso_equifax` accessing the same incident from a different actor identity without a formal handoff (IR4_Escalate from analyst to CISO) triggers actor pivot → EXIT.

This was not the anticipated gate fire for these events. However, it is structurally accurate. The Senate testimony explicitly documents that the CISO's awareness of CVE-2017-5638 came through informal channels — there is no formal escalation ticket in the Equifax IR record linking analyst triage to CISO notification. The actor pivot fires precisely because the formal escalation handoff did not occur.

**Finding:** The actor pivot invariant detected the absence of the formal escalation path — the CISO entered the incident response without formal handoff from the analyst layer. This is a structural characterization of what the Senate report describes as a coordination failure between Equifax's security team and CISO function.

**Secondary lead time:** Actor pivot fires Day 10–12 (~March 17–19). Breach initiation Day 67. Lead time: ~55–57 days.

---

## Tertiary finding — ORDER (escalation before containment), Event 9

At breach discovery (Day 144, July 29, 2017), `analyst_equifax` attempts `escalate_to_ciso` (IR4_Escalate) directly from TRIAGED state. IR4_Escalate is permitted only from CONTAINED in the IR_Analyst flow graph — the analyst cannot escalate without first completing containment actions (IR3_Contain).

This fires a second ORDER violation: escalation attempted before containment. The analyst's state has been in TRIAGED since Event 2, with the ORDER violation from Event 4 having already fired. The system had been in a structurally inadmissible state for 135 days between the first ORDER fire and breach discovery.

---

## Full event log

| # | Actor | Action | Class | From State | To State | Decision | Invariant |
|---|-------|--------|-------|-----------|---------|---------|-----------|
| 1 | analyst_equifax | check_ioc | IR1_Detect | IDLE | ALERT_RECEIVED | ADMISSIBLE | — |
| 2 | analyst_equifax | assess_severity | IR2_Triage | ALERT_RECEIVED | TRIAGED | ADMISSIBLE | — |
| 3 | analyst_equifax | identify_affected_systems | IR2_Triage | TRIAGED | TRIAGED | ADMISSIBLE | — |
| 4 | analyst_equifax | monitor_siem | IR1_Detect | TRIAGED | — | **INADMISSIBLE** | **ORDER** |
| 5 | ciso_equifax | review_alert | IR1_Detect | IDLE | — | **INADMISSIBLE** | **EXIT** |
| 6 | ciso_equifax | assess_severity | IR2_Triage | IDLE | — | **INADMISSIBLE** | **EXIT** |
| 7 | ciso_equifax | determine_scope | IR2_Triage | IDLE | — | **INADMISSIBLE** | **EXIT** |
| 8 | analyst_equifax | confirm_breach | IR2_Triage | TRIAGED | TRIAGED | ADMISSIBLE | — |
| 9 | analyst_equifax | escalate_to_ciso | IR4_Escalate | TRIAGED | — | **INADMISSIBLE** | **ORDER** |

Total: 9 events, 4 ADMISSIBLE, 5 INADMISSIBLE (2× ORDER, 3× EXIT actor pivot).

---

## DEFICIENCY_NOTED pattern — updated registry

This reconstruction adds a 5th confirmed instance. It is the first instance on the Cyber IR substrate, the first with a named CVE as the deficiency document, and the first with day-level precision from a publicly available advisory date.

| Incident | Year | Deficiency Document | Commitment | Domain | Lead Time |
|----------|------|---------------------|-----------|--------|-----------|
| Algo Centre Mall | 2012 | Inspection report (roof pool) | Continued operations | Construction | ~months |
| Champlain Towers South | 2021 | 2018 engineering report | Continued occupancy | Construction | ~3 years |
| Bhopal | 1984 | UCIL engineering findings | A3_Commitment | Chemical | ~2 years |
| Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) | Q2 quarter-end commitment | Financial | ~3.5 months |
| **Equifax CVE** | **2017** | **CVE-2017-5638 (March 7)** | **monitor_siem from TRIAGED** | **Cyber IR** | **~59 days** |

**Lead time range across all instances:** ~59 days (Equifax) to ~3 years (Champlain Towers).
**Domain spread:** Construction (2), Chemical, Financial, Cyber IR. Three different compilers.
**Invariant:** ORDER in all five instances.

---

## Architectural note — actor pivot as secondary DEFICIENCY_NOTED signal

The actor pivot finding (Events 5–7) is not the DEFICIENCY_NOTED pattern itself, but it is structurally connected. The CISO's informal awareness path is both a consequence of the deficiency not being escalated through proper channels AND a precondition for the escalation failure at breach discovery (Event 9). The three-fire cluster maps to: no formal escalation from analyst → CISO works informally → no formal containment order issued → continued unpatched operation.

This is the Equifax response failure described across five Senate hearings, expressed as a structural sequence in two invariants across two actor identities.

---

## Compiler note

The Cyber IR compiler (#16) now has its first inverse reconstruction. The compiler was built with Equifax 2017 as its anchor incident; this reconstruction closes the loop between the compiler design and its own incident origin. The DEFICIENCY_NOTED pattern and the actor pivot finding are both consistent with the compiler's documented flow graph and role registry. No compiler modifications were made.

Gate kernel (`domain_compiler_v0_9.py`) unchanged. Result files: `equifax_cyberir_reconstruction.py`, `equifax_cyberir_reconstruction_results.json`.

---

*Reconstruction scope: CVE receipt window (March 7–8) through breach discovery (July 29, 2017). Does not model the exfiltration period (May 13 – July 29) or the disclosure timeline (July 29 – September 7). Those periods are outside the scope of the DEFICIENCY_NOTED pattern test.*
