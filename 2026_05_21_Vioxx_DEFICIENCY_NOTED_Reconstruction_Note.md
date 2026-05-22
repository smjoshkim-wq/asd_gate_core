# Inverse Incident Reconstruction Note — Vioxx 2004 (DEFICIENCY_NOTED Pattern)
**Date:** May 21, 2026
**Version:** 1.0
**Substrate:** Pharmaceutical Drug Approval, compiler #12
**Compiler:** `pharma_compiler_v0_1.py`
**Pattern:** DEFICIENCY_NOTED (8th confirmed instance)
**Primary invariant:** JURISDICTION
**Structural note:** First DEFICIENCY_NOTED instance in the corpus where the commitment fires JURISDICTION rather than ORDER
**Mapping type:** Direct 1:1
**Follows from:** TMI-2 DEFICIENCY_NOTED Reconstruction Note (May 21, 2026)

---

## Source authority

- VIGOR Study Group, "Comparison of Upper Gastrointestinal Toxicity of Rofecoxib and Naproxen in Patients with Rheumatoid Arthritis," *NEJM* 343:1520-1528 (November 23, 2000). VIGOR results available internally to Merck: February 2000; submitted to FDA: June 2000
- FDA Advisory Committee Briefing Document, "Cardiovascular Safety Review of Rofecoxib" (February 8, 2001)
- APPROVe Trial (Adenomatous Polyp Prevention on Vioxx) — protocol and DSMB adjudication SOP; enrollment 2000–2004
- U.S. Senate Finance Committee, "FDA, Merck, and Vioxx: Putting Patient Safety First?" hearing transcript (November 18, 2004) — SOP modification documented in testimony
- Merck press release, "Merck Announces Voluntary Worldwide Withdrawal of VIOXX®" (September 30, 2004)

---

## Reconstruction summary

Rofecoxib (Vioxx) was approved by the FDA in 1999 for osteoarthritis. In February 2000, Merck received internal results from the VIGOR (Vioxx GI Outcomes Research) trial showing a 5-fold increased risk of serious cardiovascular events in the rofecoxib arm versus naproxen. These results were submitted to the FDA in June 2000 and published in the NEJM in November 2000. Vioxx remained on market until September 30, 2004 — when APPROVe trial interim data confirmed a 2-fold cardiovascular risk increase and Merck withdrew the drug voluntarily.

This reconstruction maps the DEFICIENCY_NOTED pattern to the APPROVe trial context. The gate fires at Event 8 when `sponsor_merck` attempts `modify_adjudication_sop` (S2_DSMB_Unblinding). JURISDICTION fires: S2 is excluded from Sponsor's role at all states.

---

## Primary finding — DEFICIENCY_NOTED (JURISDICTION), Event 8

**Deficiency document:** VIGOR trial results, available to Merck from February 2000. A 5-fold increase in serious cardiovascular events (myocardial infarction, sudden cardiac death) in the rofecoxib arm was formally documented in the FDA submission (June 2000) and peer-reviewed literature (NEJM, November 2000). The cardiovascular signal was on record within Merck and with the FDA from mid-2000 onward.

**DEFICIENCY_NOTED state:** PHASE_III (APPROVe). The APPROVe trial was enrolling subjects for colorectal polyp prevention. Following VIGOR, `pi_smith` filed an S1 expedited safety report (Event 4, PHASE_III loop — ADMISSIBLE). The trial was now in PHASE_III with a formally documented cardiovascular deficiency on record. Required responses: DSMB review (S2), clinical hold (S3), or post-approval label update (M1). None were initiated by the Sponsor.

**Commitment from DEFICIENCY_NOTED state:** Event 8. `sponsor_merck` modifies the APPROVe DSMB adjudication SOP — specifically narrowing the definition of cardiovascular endpoint events. Per Senate Finance Committee testimony (November 2004), this modification changed the event count from 20 to 17 serious cardiovascular events in the rofecoxib arm, affecting the statistical presentation of VIGOR's findings. The action is `modify_adjudication_sop` → S2_DSMB_Unblinding. S2 is not in the Sponsor's vocabulary at any state. JURISDICTION fires.

**Lead time (deficiency document → withdrawal):** ~4 years. VIGOR data February 2000; withdrawal September 30, 2004. Day-level precision on both dates.
**Lead time (gate fire → withdrawal):** ~2–3 years. SOP modification approximately 2001–2002; year-level precision (exact date not in public record).
**Precision class:** Day-level (VIGOR, withdrawal) / Year-level (SOP modification).
**Mapping type:** Direct 1:1. The compiler header names this exact violation; the reconstruction closes the loop.

---

## Structural finding — DEFICIENCY_NOTED via JURISDICTION (first instance)

All seven prior DEFICIENCY_NOTED instances fired ORDER as the primary invariant: a commitment proceeding in the wrong sequence relative to the deficiency record. Vioxx fires JURISDICTION: the commitment action (S2_DSMB_Unblinding) is structurally excluded from the Sponsor's role at all states — not merely out of sequence but role-prohibited entirely.

The DEFICIENCY_NOTED pattern structure is identical:
- Deficiency document exists (VIGOR cardiovascular data)
- Actor is in DEFICIENCY_NOTED state (PHASE_III with signal on record)
- Commitment proceeds without resolving the deficiency
- Invariant fires

The invariant differs because the commitment action is role-excluded rather than sequence-violated. The Sponsor did not merely skip a required step (which would be ORDER); the Sponsor executed a function structurally reserved for an independent committee (DSMB). The distinction matters for interpretation: ORDER says "wrong time"; JURISDICTION says "wrong actor."

The SOP modification was structurally a DSMB override. The DSMB is the independent safety monitoring body. Its function — including adjudicating which events count as cardiovascular endpoints — is protected from Sponsor influence by the blinding and independence requirements of clinical trial design. When Sponsor modifies the adjudication SOP, they are not acting out of sequence; they are acting outside their structural authority entirely.

---

## R5 boundary — confirmed in this reconstruction

Event 5 (`enroll_subject` → C2_SubjectEnrollment from PHASE_III) is ADMISSIBLE. Continued enrollment after VIGOR signal is on record does not fire the gate. The gate cannot detect "continued enrollment without adding a cardiovascular warning" — that is a passive failure (required action not taken), outside the gate's v0.1 scope. R5 open research problem boundary is explicitly demonstrated here: the gate fires on the active structural override (Event 8) but not on the enrollment continuation (Event 5), even though both are causally connected to the eventual harm.

This does not mean the enrollment continuation is safe or appropriate — it means the gate's invariant structure (active commissions) does not cover omissions. R5 extension would require a temporal gate that fires when a required action fails to occur within a defined window.

---

## Full event log

| # | Actor | Action | Class | From State | To State | Decision | Invariant |
|---|-------|--------|-------|-----------|---------|---------|-----------|
| 1 | pi_smith | obtain_informed_consent | C2_SubjectEnrollment | IND_ACTIVE | PHASE_I | ADMISSIBLE | — |
| 2 | pi_smith | advance_dose_cohort | C1_DoseEscalation | PHASE_I | PHASE_II | ADMISSIBLE | — |
| 3 | pi_smith | advance_dose_cohort | C1_DoseEscalation | PHASE_II | PHASE_III | ADMISSIBLE | — |
| 4 | pi_smith | report_serious_adverse_event | S1_SafetyReport | PHASE_III | PHASE_III | ADMISSIBLE | — |
| 5 | pi_smith | enroll_subject | C2_SubjectEnrollment | PHASE_III | PHASE_III | ADMISSIBLE | — |
| 6 | sponsor_merck | execute_animal_toxicity | P1_Preclinical | PRECLINICAL | PRECLINICAL | ADMISSIBLE | — |
| 7 | sponsor_merck | submit_ind_application | P2_IND_Submit | PRECLINICAL | IND_SUBMITTED | ADMISSIBLE | — |
| **8** | **sponsor_merck** | **modify_adjudication_sop** | **S2_DSMB_Unblinding** | **IND_SUBMITTED** | **—** | **INADMISSIBLE** | **JURISDICTION** |

Total: 8 events, 7 ADMISSIBLE, 1 INADMISSIBLE (JURISDICTION).

---

## DEFICIENCY_NOTED pattern — updated registry (8 instances, invariant column added)

| Incident | Year | Deficiency Document | Domain | Invariant | Doc→Event |
|----------|------|---------------------|--------|-----------|-----------|
| Algo Centre Mall | 2012 | Structural inspection report | Construction | ORDER | ~months |
| Champlain Towers South | 2021 | 2018 engineering report | Construction | ORDER | ~3 years |
| Bhopal | 1984 | UCIL engineering findings | Chemical | ORDER | ~2 years |
| Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) | Financial | ORDER | ~3.5 months |
| Equifax CVE | 2017 | CVE-2017-5638 (March 7) | Cyber IR | ORDER | ~67 days |
| Texas City BP | 2005 | Telos Group Assessment (Sep 2004) | Chemical | ORDER | ~6 months |
| TMI-2 | 1979 | B&W memo (November 1977) | Nuclear | ORDER | ~16 months |
| **Vioxx APPROVe** | **2004** | **VIGOR results (Feb 2000)** | **Pharma** | **JURISDICTION** | **~4 years** |

**Observation:** 7 of 8 instances fire ORDER. 1 of 8 fires JURISDICTION. The ORDER dominance suggests that the most common mechanism for proceeding from a DEFICIENCY_NOTED state is sequence violation (the right actor taking the wrong step at the wrong time). The Vioxx JURISDICTION instance represents a rarer but structurally distinct mechanism: the wrong actor taking an action that is role-excluded regardless of timing.

**Domain coverage:** Construction ×2, Chemical ×2, Financial, Cyber IR, Nuclear, Pharma. Six domains, eight instances.

---

## Compiler note

Pharma compiler #12 now has its first inverse reconstruction. The compiler header named the Vioxx JURISDICTION violation explicitly; this reconstruction demonstrates it within the DEFICIENCY_NOTED framing. The reconstruction also confirms the BURST-Safe Traversal requirement for the PI path: PI's three-expansion path (IND_ACTIVE→PHASE_I→PHASE_II→PHASE_III) requires year-scale timestamp spacing to avoid false BURST_CADENCE fires, consistent with the real-world multi-year trial timeline.

Gate kernel (`domain_compiler_v0_9.py`) unchanged. Files: `vioxx_pharma_reconstruction.py`, `vioxx_pharma_reconstruction_results.json`.

---

*Reconstruction scope: APPROVe trial initiation (~1998) through DSMB adjudication SOP modification (~2001–02). Does not model the APPROVe interim analysis (2004) or withdrawal sequence — those are downstream consequences of the structural violation, not additional gate events.*
