# Inverse Incident Reconstruction — Gelsinger 1999
**Date:** May 20, 2026
**Status:** ✅ Validated on hardware
**Follows:** Tenerife inverse reconstruction (May 21, 2026); Steps 1–5 confirmed sequence

---

## 1. Incident Summary

Jesse Gelsinger, 18, received an adenoviral vector carrying OTC cDNA on September 13, 1999 as a participant in a Phase I dose-escalation gene therapy trial at the University of Pennsylvania Institute for Human Gene Therapy (PI: James Wilson). He was enrolled in Cohort 6 — the highest dose level. He died September 17, 1999 of a systemic inflammatory response syndrome.

The FDA Warning Letter (February 8, 2002) and NIH OBA Special Investigation found:
- At least 6 prior subjects had Grade 3 or 4 adverse events not reported to FDA within the 15-day window required by 21 CFR 312.32
- One Cohort 5 subject had ammonia values exceeding the protocol's pre-specified stopping threshold; this data was not available to the DRC reviewing the Cohort 6 advance
- Gelsinger himself had pre-enrollment ammonia levels that may have been above eligibility thresholds
- The DRC review authorizing Cohort 6 was not conducted with full adverse event data

---

## 2. Gate Result

| Step | Action | State | Decision |
|------|--------|-------|----------|
| 1 | `submit_15day_safety_report` | IND_ACTIVE → IND_ACTIVE | ADMISSIBLE |
| 2 | `submit_15day_safety_report` | IND_ACTIVE → IND_ACTIVE | ADMISSIBLE |
| 3 | `submit_15day_safety_report` | IND_ACTIVE → IND_ACTIVE | ADMISSIBLE |
| **4** | **`advance_dose_cohort`** | **IND_ACTIVE → None** | **INADMISSIBLE [ORDER]** |

**Gate fires at step 4. Invariant: ORDER.**

- Gate timestamp: ~936835200 (September 9, 1999 — enrollment)
- Vector infusion: ~937180800 (September 13, 1999)
- Gelsinger death: ~937526400 (September 17, 1999)
- **Lead before infusion: 4 days**
- **Lead before death: 8 days**
- No toxicity data. No biomarkers. No intent modeling. Sequence alone.

---

## 3. Structural Finding

`advance_dose_cohort` maps to `C1_DoseEscalation`. In the pharma compiler, `C1_DoseEscalation` is in PI vocabulary at `PHASE_I` and `PHASE_II`. It is **not** in `IND_ACTIVE.flows` for the PI role. `IND_ACTIVE` permits only `C2_SubjectEnrollment` (the pivot action, advancing to `PHASE_I`) and `S1_SafetyReport` (self-loop).

The gate fires because the PI attempted cohort escalation from a state where the required prerequisite pivot had not been completed. Three admissible S1 self-loops (partial and incomplete safety reporting) do not advance the state. The fourth action, C1_DoseEscalation, fires ORDER.

This is the same geometric class as the Tenerife ORDER violation: an expand/escalation action attempted from a state where the prerequisite pivot was absent. Different domain, different century, same shape.

---

## 4. Vocabulary Mapping Notes

### Clean mappings
- `submit_15day_safety_report` → `S1_SafetyReport` — direct: 21 CFR 312.32 expedited reporting
- `advance_dose_cohort` → `C1_DoseEscalation` — direct: dose level escalation

### Structural mapping: IND_ACTIVE vs PHASE_I
The IND_ACTIVE → PHASE_I pivot in the compiler (`C2_SubjectEnrollment`) represents the completed safety review and clearance process that authorizes formal Phase I progression. In Gelsinger's trial, the regulatory equivalent was the DRC review with complete prior AE data. That review never happened with complete data. Therefore: pi_wilson remains in IND_ACTIVE.

This is an honest structural analog. The compiler does not have a separate "DRC_clearance" event — `C2_SubjectEnrollment` is the pivot that captures the class of action (clearing the safety gate before advancing).

### No vocabulary gap encountered
Every event in the sequence mapped to an existing compiler action class. No fallback or extension was required.

---

## 5. Comparison with Tenerife

| Property | Tenerife 1977 | Gelsinger 1999 |
|----------|--------------|----------------|
| Compiler | Aviation v0.1 | Pharma v0.1 |
| Invariant fired | ORDER | ORDER |
| Firing action | `initiate_takeoff_roll` (AV2_Expand) | `advance_dose_cohort` (C1_DoseEscalation) |
| State at fire | RUNWAY_HOLD | IND_ACTIVE |
| Why action absent | TAKEOFF_CLEARED not reached | PHASE_I not reached |
| Missing pivot | `receive_takeoff_clearance` (AV4_Pivot) | `obtain_informed_consent` (C2_SubjectEnrollment) |
| Mapping type | Direct 1:1 | Structural analog |
| Lead time | 36 seconds | 4 days |
| Gate input | Sequence only | Sequence only |

The structural claim — one gate kernel detects both, same ORDER geometry — holds in both cases. The mapping type differs (direct vs analog), which should be stated explicitly in any paper. The lead time difference (36 seconds vs 4 days) reflects domain characteristics, not a difference in gate sensitivity.

---

## 6. What the Gate Does Not Detect

The gate fires on the **active violation** — `advance_dose_cohort` without the safety pivot. It does **not** fire on the **S1 omissions** — the failure to submit 15-day safety reports for prior Grade 3 AEs within the regulatory window. Absence-of-action is not gate-fireable in v0.1.

This is consistent with open research problem R5 (passive failure detection) in the Master Domain Registry v1.1. The Champlain Towers H1 observation (DEFICIENCY_NOTED without subsequent REMEDIATION) is the same class of gap. Both Gelsinger and Champlain Towers have this structure: the active violation fires; the passive omission that preceded it does not.

This is not a weakness of the reconstruction — it is a finding about the boundary of what sequence-based structural detection covers. The paper series should be precise about this boundary.

---

## 7. Prospective Detection Claim — Precise Formulation

Following the precision correction established in the Tenerife note:

> The gate fires ORDER at the Cohort 6 authorization/enrollment decision — the act of proceeding with the highest dose cohort. This is a minimum of 4 days before the vector infusion that initiated the irreversible cascade, and 8 days before Gelsinger's death. The gate fires from the action sequence alone, without toxicity data, without biomarkers, without intent modeling. The DRC review deficiency was known to the investigators at the time. The gate does not detect something that was undetectable — it formalizes the structural gap at the moment of the escalation decision and fires before the irreversible physical consequence.

**Do not use:** "before any human could detect the violation." The failure was detectable by humans at the time — the FDA Warning Letter establishes this retrospectively. The gate's value is formalization and prospective firing before physical consequence, not superior human detection.

---

## 8. Reconstruction Type Inventory

| Reconstruction | Mapping type | Primary source | Invariant |
|---------------|-------------|----------------|-----------|
| Tenerife 1977 | Direct 1:1 | ICAO/Spanish Ministry Report | ORDER |
| Gelsinger 1999 | Structural analog | FDA Warning Letter (Feb 2002) + NIH OBA | ORDER |

---

## 9. Files

| File | Description |
|------|-------------|
| `gelsinger_reconstruction.py` | Reconstruction script — PI event sequence, gate output |
| `gelsinger_reconstruction_results.json` | Machine-readable gate output per event |
| `pharma_compiler_v0_1.py` | Pharma compiler (confirmed 10/10, May 21, 2026) |
| `2026_05_20_Gelsinger_Inverse_Reconstruction_Note.md` | This document |

---

## 10. Next Reconstructions

| # | Incident | Compiler | Primary Source |
|---|---------|---------|----------------|
| 3 | Costa Concordia 2012 | Maritime v0.1 | MAIB Report (2012) |
| 4 | Bromiley 2005 | Clinical v0.1 | Harmer Report (2005) |

---

*Reconstruction performed: May 20, 2026. Gate kernel: domain_compiler_v0_9.py (v0.9). Pharma compiler: v0.1. Source authority: FDA Warning Letter to James M. Wilson (February 8, 2002); NIH OBA Special Investigation (1999–2000).*
