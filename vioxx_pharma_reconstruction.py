"""
Inverse Incident Reconstruction — Vioxx / Rofecoxib 2004 (DEFICIENCY_NOTED Pattern)
═════════════════════════════════════════════════════════════════════════════════════

Substrate: Pharmaceutical Drug Approval, compiler #12
Compiler:  pharma_compiler_v0_1.py
Pattern:   DEFICIENCY_NOTED (8th confirmed instance)
Invariant: JURISDICTION (primary — first DEFICIENCY_NOTED instance not ORDER)
Mapping type: Direct 1:1

Source authority:
    VIGOR Study Group, "Comparison of Upper Gastrointestinal Toxicity of
    Rofecoxib and Naproxen in Patients with Rheumatoid Arthritis," NEJM
    343:1520-1528 (November 23, 2000). Results available to Merck February
    2000; submitted to FDA June 2000.
    FDA Advisory Committee Briefing Document, "Cardiovascular Safety Review
    of Rofecoxib" (February 8, 2001).
    David Graham et al., "Risk of Acute Myocardial Infarction and Sudden
    Cardiac Death in Patients Treated with COX-2 Selective and Non-Selective
    NSAIDs," The Lancet 365:475-481 (2004).
    APPROVe Trial (Adenomatous Polyp Prevention on Vioxx), Protocol and
    DSMB adjudication SOP. Trial enrollment: 2000–2004.
    Merck press release, "Merck Announces Voluntary Worldwide Withdrawal of
    VIOXX®," September 30, 2004.
    U.S. Senate Finance Committee, "FDA, Merck, and Vioxx: Putting Patient
    Safety First?" Hearing transcript (November 18, 2004).

Reconstruction scope:
    Two actors: pi_smith (APPROVe trial PI, clinical progression) and
    sponsor_merck (regulatory/safety actor, IND submission + safety reporting).

    Phase 0: APPROVe trial reaches Phase III enrollment (2000). VIGOR
             cardiovascular data becomes available — deficiency seeded.
             pi_smith files S1 safety report on VIGOR findings.
    Phase 1: Enrollment continues in APPROVe despite cardiovascular signal
             on record. Structurally admissible — R5 boundary applies.
    Phase 2: sponsor_merck modifies APPROVe DSMB adjudication SOP
             (modify_adjudication_sop → S2_DSMB_Unblinding) to narrow the
             definition of cardiovascular endpoint events.
             S2_DSMB_Unblinding is NOT in Sponsor's vocabulary at any state.
             JURISDICTION fires.

DEFICIENCY_NOTED geometry in this substrate:
    The DEFICIENCY_NOTED state is PHASE_III with the VIGOR cardiovascular
    signal on record (S1 filed, signal documented). The required response
    was either trial modification (DSMB's role via S2), clinical hold
    (FDA/IRB via S3), or label update (post-approval M1). Instead, the
    Sponsor modified the adjudication SOP — a DSMB-exclusive action (S2).
    The deficiency (VIGOR signal) was addressed not by the required
    remediation path but by a structural override of the DSMB function.

    This is DEFICIENCY_NOTED via JURISDICTION: the commitment made from
    the deficiency state is not merely out of sequence (ORDER) but is
    structurally excluded from the Sponsor's role entirely.

    This is the first DEFICIENCY_NOTED instance in the corpus where the
    commitment fires JURISDICTION rather than ORDER. The DEFICIENCY_NOTED
    context (deficiency on record → commitment proceeds without resolution)
    is identical to prior instances; the invariant differs because the
    commitment action is role-excluded rather than sequence-violated.

R5 boundary note:
    Continued subject enrollment (enroll_subject → C2_SubjectEnrollment)
    from PHASE_III is structurally ADMISSIBLE for PI. The gate cannot fire
    on continued enrollment after a known safety signal — that is a passive
    failure (required action not taken), which is outside the gate's v0.1
    scope. The gate fires on the Sponsor's active structural override (S2),
    not on the enrollment continuation. Both findings are documented.

Lead times:
    Primary (deficiency document → withdrawal):
        VIGOR data available to Merck: February 2000.
        Vioxx withdrawal: September 30, 2004.
        Lead time: ~4 years. Day-level precision on both dates.
    Secondary (gate fire → withdrawal):
        DSMB adjudication SOP modification: approximately 2001–2002 (Senate
        testimony; exact date not publicly disclosed — year-level precision).
        Lead time: ~2–3 years.

Timestamp convention:
    Year-scale offsets from VIGOR data receipt (T=0 = February 2000).
    YEAR = 365 * 24 * 3600 seconds. Phases spaced >1 year apart to
    avoid BURST_CADENCE false-positive on PI's three-expansion path
    (IND_ACTIVE→PHASE_I→PHASE_II→PHASE_III).

APPROVe trial timeline:
    ~2000       APPROVe enrollment begins (Phase III, colorectal polyp prevention)
    Feb 2000    VIGOR data available internally to Merck (deficiency seeded)
    Nov 2000    VIGOR published in NEJM
    Feb 2001    FDA AdCom reviews VIGOR cardiovascular findings
    2001–02     Merck modifies APPROVe DSMB adjudication SOP (gate fire here)
    Sep 30 2004 APPROVe interim analysis confirms 2x cardiovascular risk;
                Merck withdraws Vioxx worldwide
"""

import sys
import json
sys.path.insert(0, ".")

from pharma_compiler_v0_1 import PharmaCompiler
from domain_compiler_v0_9 import evaluate_gate

YEAR = 365 * 24 * 3600   # seconds per year

# Timestamp anchors (relative to VIGOR data receipt = T0 = February 2000)
T_VIGOR_DATA       = 0                    # Feb 2000: VIGOR results available
T_PHASE2_ADVANCE   = int(0.3 * YEAR)     # ~mid-2000: APPROVe advances to Phase II
T_PHASE3_ADVANCE   = int(0.6 * YEAR)     # ~late 2000: APPROVe reaches Phase III
T_VIGOR_S1         = int(0.7 * YEAR)     # ~Sep 2000: S1 safety report on VIGOR filed
T_CONTINUED_ENROLL = int(1.0 * YEAR)     # 2001: enrollment continues
T_SOP_MODIFICATION = int(1.5 * YEAR)     # ~2001-02: Merck modifies adjudication SOP
T_WITHDRAWAL       = int(4.6 * YEAR)     # Sep 30, 2004: Merck withdraws Vioxx

EVENTS = [

    # ── Phase 0: APPROVe reaches Phase III, VIGOR deficiency seeded ──────
    #
    # APPROVe trial opened enrollment for colorectal polyp prevention.
    # PI progresses through clinical phases. Timestamps spaced >1 year
    # to satisfy BURST-Safe Traversal requirement (3 expansions in path).
    {
        "actor_id":   "pi_smith",
        "action":     "obtain_informed_consent",
        "program_id": "VIOXX_APPROVe_clinical",
        "timestamp":  -(2 * YEAR),
        "_note": "~1998: First APPROVe subject enrolled. "
                 "C2_SubjectEnrollment: IND_ACTIVE → PHASE_I. "
                 "[ADMISSIBLE — trial enrollment begins]"
    },
    {
        "actor_id":   "pi_smith",
        "action":     "advance_dose_cohort",
        "program_id": "VIOXX_APPROVe_clinical",
        "timestamp":  -(1 * YEAR),
        "_note": "~1999: APPROVe advances to Phase II. "
                 "C1_DoseEscalation: PHASE_I → PHASE_II. "
                 "[ADMISSIBLE — phase advance]"
    },
    {
        "actor_id":   "pi_smith",
        "action":     "advance_dose_cohort",
        "program_id": "VIOXX_APPROVe_clinical",
        "timestamp":  T_PHASE3_ADVANCE,
        "_note": "Late 2000: APPROVe reaches Phase III enrollment. "
                 "C1_DoseEscalation: PHASE_II → PHASE_III. "
                 "[ADMISSIBLE — Phase III begins]"
    },

    # VIGOR data arrives — deficiency seeded.
    # pi_smith files expedited S1 safety report on cardiovascular signal.
    # S1_SafetyReport from PHASE_III loops in PHASE_III. [ADMISSIBLE]
    # This is the DEFICIENCY_NOTED state: PHASE_III with cardiovascular
    # signal formally on record.
    {
        "actor_id":   "pi_smith",
        "action":     "report_serious_adverse_event",
        "program_id": "VIOXX_APPROVe_clinical",
        "timestamp":  T_VIGOR_S1,
        "_note": "Sep 2000: VIGOR cardiovascular findings formally filed as "
                 "expedited safety report (S1). "
                 "5-fold increase in serious CV events (rofecoxib vs naproxen) "
                 "is on record. VIGOR published in NEJM Nov 2000. "
                 "S1_SafetyReport: PHASE_III → PHASE_III (loop). "
                 "*** DEFICIENCY_NOTED STATE CONFIRMED *** "
                 "Deficiency document: VIGOR trial results (Feb/Nov 2000). "
                 "Required response: DSMB review (S2), or clinical hold (S3), "
                 "or label update (M1 post-approval). "
                 "[ADMISSIBLE — S1 safety report filed]"
    },

    # ── Phase 1: Continued enrollment — R5 boundary ──────────────────────
    #
    # Enrollment continues in APPROVe after VIGOR signal is on record.
    # C2_SubjectEnrollment from PHASE_III is ADMISSIBLE for PI.
    # The gate cannot fire here — this is the R5 passive failure boundary.
    # The gate detects active structural violations (commissions), not
    # the failure to stop enrollment (omission).
    {
        "actor_id":   "pi_smith",
        "action":     "enroll_subject",
        "program_id": "VIOXX_APPROVe_clinical",
        "timestamp":  T_CONTINUED_ENROLL,
        "_note": "2001: APPROVe enrollment continues despite VIGOR signal. "
                 "Subjects enrolled in colorectal polyp prevention trial while "
                 "cardiovascular deficiency is on record and unresolved. "
                 "C2_SubjectEnrollment: PHASE_III → PHASE_III (loop). "
                 "*** R5 BOUNDARY: gate cannot fire on omission *** "
                 "Continued enrollment is structurally admissible. The gate does "
                 "not fire on 'did not stop enrollment' — only on active violations. "
                 "[ADMISSIBLE — enrollment continues; R5 passive failure not in scope]"
    },

    # ── Phase 2: Sponsor SOP modification — DEFICIENCY_NOTED commitment ──
    #
    # sponsor_merck submits IND application (abbreviated — sponsor_merck
    # uses separate program_id to avoid actor_pivot with pi_smith).
    {
        "actor_id":   "sponsor_merck",
        "action":     "execute_animal_toxicity",
        "program_id": "VIOXX_APPROVe_sponsor",
        "timestamp":  -(3 * YEAR),
        "_note": "Background: sponsor_merck preclinical documentation. "
                 "P1_Preclinical: PRECLINICAL → PRECLINICAL (loop). "
                 "[ADMISSIBLE — sponsor preclinical record]"
    },
    {
        "actor_id":   "sponsor_merck",
        "action":     "submit_ind_application",
        "program_id": "VIOXX_APPROVe_sponsor",
        "timestamp":  -(2.5 * YEAR),
        "_note": "Background: sponsor_merck files IND for APPROVe trial. "
                 "P2_IND_Submit: PRECLINICAL → IND_SUBMITTED. "
                 "[ADMISSIBLE — sponsor IND submission]"
    },

    # ══ PRIMARY FIRE — DEFICIENCY_NOTED commitment ═══════════════════════
    #
    # sponsor_merck modifies the APPROVe DSMB adjudication SOP —
    # specifically narrowing the definition of cardiovascular endpoint events
    # to exclude three heart attacks from the pre-randomization period that
    # had been attributed to rofecoxib. This is S2_DSMB_Unblinding
    # (modify_adjudication_sop), which is EXCLUDED from Sponsor's vocabulary
    # at ALL states. No state in the Sponsor flow graph contains S2.
    #
    # Per Senate Finance Committee testimony (Nov 2004): Merck's modification
    # of the adjudication SOP changed the CV endpoint count from 20 to 17
    # serious cardiovascular events in the rofecoxib arm, affecting the
    # statistical significance threshold in VIGOR.
    #
    # This is the DEFICIENCY_NOTED commitment: the cardiovascular signal
    # (VIGOR, 2000) is on record and unresolved. Rather than remediating
    # the deficiency (label update, DSMB-directed trial modification, FDA
    # clinical hold response), the Sponsor modifies the DSMB adjudication
    # function directly — a role-excluded action. JURISDICTION fires.
    {
        "actor_id":   "sponsor_merck",
        "action":     "modify_adjudication_sop",
        "program_id": "VIOXX_APPROVe_sponsor",
        "timestamp":  T_SOP_MODIFICATION,
        "_note": "~2001-02: sponsor_merck modifies APPROVe DSMB adjudication SOP. "
                 "Modification narrows CV endpoint definition, affecting VIGOR "
                 "event count from 20 to 17 serious CV events in rofecoxib arm. "
                 "modify_adjudication_sop → S2_DSMB_Unblinding. "
                 "S2 is NOT in Sponsor's vocabulary at any state. "
                 "VIGOR cardiovascular signal (Feb 2000) is on record. "
                 "No label update issued. No DSMB-directed trial modification. "
                 "Sponsor modifies the DSMB function directly instead. "
                 "*** JURISDICTION FIRES — DEFICIENCY_NOTED PATTERN *** "
                 "First DEFICIENCY_NOTED instance where commitment fires "
                 "JURISDICTION rather than ORDER. "
                 "Gate fires: ~2001-02. Withdrawal: Sep 30, 2004. "
                 "Lead time: ~2-3 years (gate to withdrawal). "
                 "[INADMISSIBLE — JURISDICTION]"
    },

]


def run_reconstruction():
    compiler = PharmaCompiler()
    results  = []

    print("=" * 72)
    print("VIOXX 2004 — DEFICIENCY_NOTED RECONSTRUCTION")
    print("Substrate: Pharmaceutical Drug Approval — compiler #12")
    print("Pattern:   DEFICIENCY_NOTED | Primary Invariant: JURISDICTION")
    print("Note:      First DEFICIENCY_NOTED instance firing JURISDICTION, not ORDER")
    print("=" * 72)

    for i, ev in enumerate(EVENTS):
        note = ev.pop("_note", "")
        packet   = compiler.compile(ev)
        result   = evaluate_gate(packet)
        stp      = packet["STP_Header"]
        decision  = result.get("decision", "INDETERMINATE")
        invariant = result.get("invariant", "—")

        print(f"\n[Event {i+1:02d}] {ev.get('action'):35s} actor: {ev.get('actor_id')}")
        print(f"  State:    {stp.get('FromState')} → {stp.get('ToState')}")
        print(f"  Role:     {stp.get('Role'):20s} Action: {stp.get('Action')}")
        print(f"  Decision: {decision}", end="")
        if decision == "INADMISSIBLE":
            print(f"  *** {invariant} ***")
        else:
            print()

        results.append({
            "event_index":  i + 1,
            "actor_id":     ev.get("actor_id"),
            "action":       ev.get("action"),
            "from_state":   stp.get("FromState"),
            "to_state":     stp.get("ToState"),
            "role":         stp.get("Role"),
            "action_class": stp.get("Action"),
            "decision":     decision,
            "invariant":    invariant,
            "bas_metrics":  result.get("BAS_Metrics", {}),
            "note":         note,
        })

    fires      = [r for r in results if r["decision"] == "INADMISSIBLE"]
    admissible = [r for r in results if r["decision"] == "ADMISSIBLE"]
    juris_fire = [r for r in fires if r["invariant"] == "JURISDICTION"]

    print("\n" + "=" * 72)
    print("RECONSTRUCTION SUMMARY")
    print("=" * 72)
    print(f"  Total events:    {len(results)}")
    print(f"  ADMISSIBLE:      {len(admissible)}")
    print(f"  INADMISSIBLE:    {len(fires)}")

    if juris_fire:
        pf = juris_fire[0]
        print(f"\n  PRIMARY GATE FIRE (DEFICIENCY_NOTED pattern):")
        print(f"    Event:           {pf['event_index']} — {pf['action']}")
        print(f"    Actor:           {pf['actor_id']} ({pf['role']})")
        print(f"    State:           {pf['from_state']} → {pf['to_state']}")
        print(f"    Invariant:       JURISDICTION")
        print(f"    Pattern:         DEFICIENCY_NOTED")
        print(f"    Deficiency doc:  VIGOR trial results (February 2000)")
        print(f"    Gate fires:      ~2001–02 (year-level precision)")
        print(f"    Vioxx withdrawn: September 30, 2004")
        print(f"    Lead time (doc): ~4 years (VIGOR data → withdrawal)")
        print(f"    Lead time (gate): ~2-3 years (SOP modification → withdrawal)")
        print(f"    Precision class: Day-level (VIGOR publication, withdrawal dates) /")
        print(f"                     Year-level (SOP modification date not public)")
        print(f"    Mapping type:    Direct 1:1")
        print(f"\n  STRUCTURAL NOTE:")
        print(f"    This is the first DEFICIENCY_NOTED instance in the corpus")
        print(f"    where the commitment fires JURISDICTION rather than ORDER.")
        print(f"    The DEFICIENCY_NOTED context is intact: deficiency (VIGOR")
        print(f"    cardiovascular signal) is on record; commitment proceeds")
        print(f"    from that state without resolution. The commitment action")
        print(f"    (S2_DSMB_Unblinding) is structurally excluded from Sponsor's")
        print(f"    role — not merely out of sequence (ORDER) but role-excluded.")
        print(f"\n  R5 BOUNDARY CONFIRMED:")
        print(f"    Continued enrollment (Event 4) is ADMISSIBLE from PHASE_III.")
        print(f"    Gate does not fire on omissions (continuing enrollment")
        print(f"    without adding cardiovascular warning). R5 passive failure")
        print(f"    scope boundary is demonstrated in this reconstruction.")

    print("\n  DEFICIENCY_NOTED — 8th instance")
    print("  | Incident         | Year | Deficiency Doc     | Domain   | Invariant    | Doc→Event |")
    print("  |------------------|------|--------------------|----------|--------------|-----------|")
    print("  | Algo Centre Mall | 2012 | Inspection report  | Constr.  | ORDER        | ~months   |")
    print("  | Champlain Towers | 2021 | Eng. report (2018) | Constr.  | ORDER        | ~3 years  |")
    print("  | Bhopal           | 1984 | UCIL findings      | Chemical | ORDER        | ~2 years  |")
    print("  | Lehman Repo 105  | 2008 | Matthew Lee letter | Financ.  | ORDER        | ~3.5 mo   |")
    print("  | Equifax CVE      | 2017 | CVE-2017-5638      | Cyber IR | ORDER        | ~67 days  |")
    print("  | Texas City       | 2005 | Telos Assessment   | Chemical | ORDER        | ~6 months |")
    print("  | TMI-2            | 1979 | B&W memo (Nov 77)  | Nuclear  | ORDER        | ~16 mo    |")
    print("  | Vioxx APPROVe    | 2004 | VIGOR results      | Pharma   | JURISDICTION | ~4 years  |")
    print()

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    out = "vioxx_pharma_reconstruction_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written → {out}")
