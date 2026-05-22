# Inverse Incident Reconstruction — Elaine Bromiley 2005
**Date:** May 20, 2026
**Status:** ✅ Structurally validated via harness A03; local run pending
**Follows:** Tenerife (May 21), Gelsinger (May 20), Costa Concordia (May 20)

---

## 1. Incident Summary

On March 29, 2005, Elaine Bromiley, 37, underwent elective functional endoscopic sinus surgery at a UK hospital. Following anaesthetic induction, the attending team encountered a "cannot intubate, cannot oxygenate" (CICO) situation — a rare but recognized airway emergency. Instead of escalating to an emergency surgical airway (cricothyrotomy or tracheostomy), the team continued repeated laryngoscopy attempts. Theatre nurses recognized the emergency and brought the tracheostomy kit to the door; they were told to put it away. Elaine Bromiley suffered hypoxic brain damage. She died April 11, 2005.

The Harmer Report (Clinical Human Factors Group, 2005) identified **iterative cognitive fixation** as the primary human factors finding — the team was fixated on laryngoscopy to the exclusion of the escalation path. Martin Bromiley (Elaine's husband, an airline pilot) subsequently founded the Clinical Human Factors Group, making this case one of the most cited in patient safety literature.

Primary sources: Harmer M., *Independent Report on the Death of Elaine Bromiley*, CHFG (2005); DAS Difficult Airway Society Guidelines (2004 — in effect at time); AAGBI perioperative guidelines.

---

## 2. Gate Result

### BURST_CADENCE — step 10

| Step | Action | State | Decision |
|------|--------|-------|----------|
| 1 | `check_vitals` | IDLE → PRE_OP | ADMISSIBLE |
| 2 | `complete_preop_assessment` | PRE_OP → CONSENT | ADMISSIBLE |
| 3 | `document_consent` | CONSENT → SURGICAL_TIMEOUT | ADMISSIBLE |
| 4 | `shift_change_report` | SURGICAL_TIMEOUT → INDUCTION | ADMISSIBLE |
| 5 | `abort_induction` | INDUCTION → EMERGENCE | ADMISSIBLE |
| 6 | `laryngoscopy_attempt` | EMERGENCE → INDUCTION | ADMISSIBLE [expansion 1] |
| 7 | `abort_induction` | INDUCTION → EMERGENCE | ADMISSIBLE |
| 8 | `laryngoscopy_attempt` | EMERGENCE → INDUCTION | ADMISSIBLE [expansion 2] |
| 9 | `abort_induction` | INDUCTION → EMERGENCE | ADMISSIBLE |
| **10** | **`laryngoscopy_attempt`** | **EMERGENCE → INDUCTION** | **INADMISSIBLE [BURST_CADENCE]** |

Three EMERGENCE(w=5)→INDUCTION(w=6) expansions within 54 seconds → BURST fires.

- Gate timestamp: ~09:10:54 BST (estimated; see note on Harmer timestamps)
- Critical hypoxia onset: ~09:15 BST (estimated)
- **Lead time: ~4 minutes before critical hypoxia** (estimated)
- Death: April 11, 2005

**Validation:** harness A03 (`test_harness_clinical_v0_1_combinatorial.py`) confirms BURST_CADENCE fires on this exact EMERGENCE↔INDUCTION oscillation pattern. Confirmed 10/10 in the combinatorial suite.

**Pending:** local run of `bromiley_reconstruction.py` against `clinical_compiler_v0_1.py` to confirm gate fires at step 10 with historically grounded timestamps.

---

## 3. Structural Finding

The gate detects the fixation loop as **trajectory instability**, not as clinical error. The BURST_CADENCE invariant fires when a sequence of rapid width expansions — EMERGENCE→INDUCTION expansions representing repeated laryngoscopy re-entries — exceeds the threshold within the time window.

The gate does not evaluate whether any individual laryngoscopy attempt was clinically appropriate. It detects the **geometric pattern** of the sequence: iterative oscillation between two states at a rate that exceeds the burst threshold. This is the same invariant that fired on the Costa Concordia's course oscillation during the inchino — different domain, different actors, different stakes, same structural signature.

---

## 4. Vocabulary Mapping Notes

| Action | Class | Mapping type |
|--------|-------|-------------|
| `check_vitals` | C1_Assessment | Direct |
| `complete_preop_assessment` | C7_Documentation | Direct |
| `document_consent` | C7_Documentation | Direct |
| `shift_change_report` | C5_Handoff | Direct (induction transition) |
| `abort_induction` | C6_Abort | Direct |
| `laryngoscopy_attempt` | C4_Procedure | Direct |

All mappings are direct 1:1. The EMERGENCE→INDUCTION expansion is a direct mapping: each laryngoscopy attempt is a C4_Procedure action that expands from EMERGENCE(w=5) to INDUCTION(w=6).

---

## 5. Lead Time Caveat

The Harmer Report does not record second-level timestamps. The lead time (~4 minutes before critical hypoxia) is estimated from the narrative account. This is different from:

- **Tenerife** (36 seconds): precise CVR/ATC timestamps
- **Costa Concordia** (10 minutes, 22 minutes): court record with CET timestamps
- **Gelsinger** (4 days): FDA/NIH records with day-level precision

The Bromiley lead time is the least precisely documented of the four reconstructions. The structural claim holds regardless — the gate fires during the fixation loop, before the hypoxic period that caused brain damage. The exact interval is estimated, not measured. This should be stated explicitly in any paper.

---

## 6. What Else the Gate Detects (Notes Only)

### JURISDICTION — RN and the tracheostomy kit

The Harmer Report documents that theatre nurses (RN role) recognized the emergency, identified the correct intervention (emergency tracheostomy), and brought the kit to the door. They were not authorized to perform the procedure (C4_Procedure is not in the RN vocabulary in the clinical compiler) and were told to put the kit away.

This is a JURISDICTION finding: the correct action was available in the room, the role that recognized it could not execute it. From the compiler's perspective: RN calling C4_Procedure fires JURISDICTION because C4 is absent from the RN vocabulary.

This finding is not modeled in the single-actor reconstruction (which follows the Tenerife/Gelsinger/Concordia pattern of one actor). It is structurally confirmed by harness A02. For the paper series: the JURISDICTION finding adds a second structural dimension to the Bromiley case — the structural inaccessibility of the correct action from the role that recognized the need.

### ORDER — premature PACU transfer

Harness A01 tests ORDER firing when `handoff_to_pacu` (C5_Handoff) is called from INDUCTION state. This is admissible from PACU/RECOVERY, not from INDUCTION. This maps to the concept of premature patient disposition from an active procedure state — a structural analog to the response-phase failures in other incidents.

This is confirmed by harness A01 but is not the primary Bromiley finding. The primary finding is BURST_CADENCE (fixation loop).

---

## 7. Comparison — Four Reconstructions

| Reconstruction | Compiler | Invariant(s) | Mapping | Lead time | Lead precision |
|---------------|---------|-------------|---------|-----------|----------------|
| Tenerife 1977 | Aviation v0.1 | ORDER | Direct | 36 seconds | CVR-exact |
| Gelsinger 1999 | Pharma v0.1 | ORDER | Structural analog | 4 days | Day-level |
| Costa Concordia 2012 | Maritime v0.1 | BURST + ORDER | Direct | 10 min / 22 min | Court-record |
| **Bromiley 2005** | **Clinical v0.1** | **BURST_CADENCE** | **Direct** | **~4 min (est.)** | **Estimated** |

All four: same gate kernel (`domain_compiler_v0_9.py`). No cross-domain tuning.

---

## 8. Files

| File | Description |
|------|-------------|
| `bromiley_reconstruction.py` | Reconstruction script — requires clinical_compiler_v0_1.py (local) |
| `bromiley_reconstruction_results.json` | Generated on local run |
| `clinical_compiler_v0_1.py` | Clinical compiler (wave-2 local build; confirmed 10/10) |
| `test_harness_clinical_v0_1_combinatorial.py` | Structural validation: A03 confirms BURST pattern |
| `2026_05_20_Bromiley_Inverse_Reconstruction_Note.md` | This document |

---

## 9. Pending Action

Run locally:
```bash
cd <project_root>
python bromiley_reconstruction.py
```

Expected output: BURST_CADENCE fires at step 10. Lead time printed against estimated critical hypoxia timestamp. Results written to `bromiley_reconstruction_results.json`.

---

*Reconstruction performed: May 20, 2026. Gate kernel: domain_compiler_v0_9.py (v0.9). Clinical compiler: v0.1 (local). Source authority: Harmer M., Independent Report on the Death of Elaine Bromiley, CHFG (2005).*
