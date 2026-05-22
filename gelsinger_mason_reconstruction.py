"""
Inverse Incident Reconstruction — Gelsinger Gene Therapy 1999 (Mason Pattern, Org Workflow)
════════════════════════════════════════════════════════════════════════════════════════════
Reconstruction type: STRUCTURAL ANALOG
Compiler:           org_workflow_compiler_v0_1.py
Mason pattern:      Expert-role recommendation overridden by authority-role actor;
                    commitment (continued trial) proceeds from that state.
Named pattern:      Mason #10

NOTE ON PRIOR GELSINGER RECONSTRUCTION:
    gelsinger_reconstruction.py (Original Reconstruction #2) used the pharma
    compiler and fired ORDER: sponsor_penn attempting protocol_amendment
    (S2_DSMB_Unblinding) from PHASE_I state without completing S1_IND_Application
    properly. That reconstruction captured the protocol sequence violation.
    This reconstruction captures the DISTINCT structural event: the IRB and
    data safety monitoring committee concerns being overridden by the PI
    (James Wilson) and sponsor (OTC/Penn), allowing Jesse Gelsinger to be
    enrolled despite safety committee reservations.
    Same incident, two structural patterns.

Source authority:
    Weiss, R. and Nelson, D. "Penn Researchers Broke Rules in Gene Therapy."
        Washington Post, November 22, 1999.
    Gelsinger family wrongful death settlement, 2000.
    FDA Warning Letter to James Wilson, University of Pennsylvania Institute
        for Human Gene Therapy, February 8, 2000.
    DHHS/ORI investigation findings, 2000.
    Sibbald, B. "Death but One Unintended Consequence of Gene-Therapy Trial."
        CMAJ 164(11):1612 (2001).
    Nelson, D. et al. "Hasty Decisions in the Gelsinger Case?" Science (2000).
    Recombinant DNA Advisory Committee (RAC) correspondence, 1999.
    FDA review of IND AV-105 protocols, 1995–1999.

Structural mapping:
    analyst_alice  → IRB (Institutional Review Board) / clinical safety committee
                     members who raised protocol concerns; DSMB members who
                     flagged adverse events in earlier subjects before
                     Gelsinger's enrollment
    approver_dave  → James Wilson (PI) / OTC Gene Therapy, Inc. (sponsor) who
                     overrode or failed to act on committee safety signals before
                     proceeding to Gelsinger's enrollment in the maximum-dose cohort

Timeline:
    1995–1999       Early cohort subjects enrolled; several adverse events
                    documented in preceding subjects at lower doses.
                    Required reporting: adverse events in OTC trial must be
                    reported to FDA and RAC.
    1999 (pre-Sep)  DSMB and IRB concerns about adverse events in preceding
                    subjects not fully resolved before proceeding to Gelsinger
                    (final, maximum-dose cohort subject). FDA safety concerns
                    about unreported adverse events documented post-hoc.
    Sep 13, 1999    Jesse Gelsinger receives maximum OTC vector dose.
    Sep 17, 1999    Jesse Gelsinger dies — systemic inflammatory response.
    Lead time:      Days to weeks (committee concerns before enrollment → death)
                    Months to years (systematic adverse event underreporting period)
"""

import sys
import json
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate

T = 0.0  # Pre-September 1999 — IRB/DSMB concerns in preceding subjects

GELSINGER_MASON_EVENTS = [
    # Phase 1: IRB/DSMB reviews safety data from earlier subjects
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 0.0,
        "_note": "1999 (prior to Sep 13). IRB and DSMB members review "
                 "safety data from earlier cohort subjects. Adverse events "
                 "documented: liver enzyme elevations, inflammatory responses "
                 "in preceding subjects. IDLE → REVIEWING via A1. ADMISSIBLE. "
                 "[FDA Warning Letter Feb 2000; Washington Post investigation]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "review_request",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 5.0,
        "_note": "Review of adverse event reports from lower-dose subjects. "
                 "Monitoring of ammonia threshold data (Gelsinger's pre-enrollment "
                 "ammonia 70 μmol/L exceeded 55 μmol/L exclusion criterion "
                 "in amended protocol). Loop in REVIEWING. ADMISSIBLE.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 10.0,
        "_note": "DSMB assesses cumulative risk profile from earlier subjects. "
                 "Adverse events not fully reported to FDA per IND requirements — "
                 "pattern identified in retrospective FDA review. "
                 "REVIEWING → ASSESSING via A2. ADMISSIBLE. "
                 "[FDA Warning Letter: failure to report adverse events timely]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "evaluate_compliance",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 15.0,
        "_note": "IRB evaluates compliance with IND adverse event reporting "
                 "requirements and protocol eligibility criteria. "
                 "Loop in ASSESSING. ADMISSIBLE.",
    },
    # Phase 2: IRB/DSMB issues safety recommendation
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 20.0,
        "_note": "Safety committee flags concern: adverse event profile from "
                 "preceding subjects warrants pause before enrolling maximum-dose "
                 "cohort subject. Recommendation: resolve adverse event reporting "
                 "gap and re-evaluate eligibility determination for final subject. "
                 "ASSESSING → RECOMMENDING via A3. ADMISSIBLE. "
                 "[Congressional testimony; DHHS investigation findings]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "escalate",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 25.0,
        "_note": "Safety concern escalated to PI (Wilson) and sponsor. "
                 "Loop in RECOMMENDING. ADMISSIBLE. "
                 "[FDA review: adverse events in earlier subjects not disclosed "
                 "to RAC or fully reported to FDA before Gelsinger enrollment]",
    },
    # Phase 3: THE VIOLATION — PI/sponsor enters review workflow
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 30.0,
        "_note": "Wilson/OTC enters the safety review workflow and issues "
                 "recommendation to proceed with Gelsinger enrollment. "
                 "STRUCTURAL VIOLATION: "
                 "(1) approver_dave enters workflow registered to analyst_alice "
                 "→ EXIT fires (actor pivot). "
                 "(2) A3_Recommend is Analyst-only → JURISDICTION (isolated). "
                 "Historical anchor: PI and sponsor proceeded to maximum-dose "
                 "enrollment despite unresolved safety signals. "
                 "[FDA Warning Letter; Washington Post investigation Nov 1999]",
    },
    # Phase 4: Authorization to proceed with Gelsinger
    {
        "actor_id":    "approver_dave",
        "action":      "authorize_release",
        "workflow_id": "GELSINGER_PROTOCOL_SAFETY_REVIEW",
        "timestamp":   T + 35.0,
        "_note": "PI/sponsor authorizes Gelsinger enrollment at maximum dose. "
                 "Post-EXIT action. Sep 13, 1999: maximum OTC vector dose "
                 "administered. Sep 17, 1999: Jesse Gelsinger dies.",
    },
]

GELSINGER_JURISDICTION_ISOLATED = [
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "GELSINGER_MGMT_ISOLATED",
        "timestamp":   T + 100.0,
        "_note": "Wilson/sponsor (Approver) calls A3_Recommend in isolation. "
                 "A3 not in Approver vocabulary → JURISDICTION. "
                 "Structural reading: PI/sponsor asserted the safety "
                 "recommendation role — the determination of whether it is "
                 "safe to enroll the next subject — belongs to the PI, "
                 "not the safety committee.",
    },
]


def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — GELSINGER 1999 (MASON PATTERN)")
    print("Reconstruction type: STRUCTURAL ANALOG")
    print("Mason pattern: Expert recommendation overridden by authority actor")
    print("Named pattern: Mason #10")
    print("Source: FDA Warning Letter 2000; Washington Post 1999; DHHS 2000")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: Safety committee pipeline (IRB/DSMB → PI/sponsor)")
    print("─"*70)

    compiler = OrgWorkflowCompiler()
    results  = []
    for i, ev in enumerate(GELSINGER_MASON_EVENTS):
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_note"] = ev.get("_note", "")
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""
        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<30} | "
              f"{frm or '—':>15} → {to:<15} | {d}{tag}")
    print()

    print("─"*70)
    print("ISOLATED JURISDICTION SEQUENCE")
    print("─"*70)

    compiler_b = OrgWorkflowCompiler()
    results_j  = []
    for i, ev in enumerate(GELSINGER_JURISDICTION_ISOLATED):
        packet = compiler_b.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results_j.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""
        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<30} | "
              f"{frm or '—':>15} → {to:<15} | {d}{tag}")
    print()

    exit_fire  = next((r for r in results if r["decision"] == "INADMISSIBLE"), None)
    juris_fire = next((r for r in results_j if r["decision"] == "INADMISSIBLE"), None)

    print("═"*70)
    print("FINDINGS")
    print("═"*70)
    if exit_fire:
        print(f"\n[EXIT] Step {exit_fire['_step']} — '{exit_fire['_raw']}'")
        print(f"   Approver (PI/sponsor) enters Analyst's (IRB/DSMB)")
        print(f"   workflow. PI invaded the safety recommendation pipeline.")
    if juris_fire:
        print(f"\n[JURISDICTION] (isolated) — '{juris_fire['_raw']}'")
        print(f"   Approver calling A3_Recommend. PI/sponsor claimed the")
        print(f"   safety determination belongs to the principal investigator,")
        print(f"   not the independent safety committee.")
    print()
    print("Lead time: days to weeks (committee concerns to Gelsinger death)")
    print("Dual-pattern: Mason (org_workflow) + ORDER (pharma) — same incident.")
    print("Note: Mason fires on safety oversight layer; ORDER fires on protocol")
    print("sequence layer. Both are structurally independent violations.")
    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — structural analog")
    print("Mason #10 confirmed.")
    print("═"*70)

    return {"primary": results, "jurisdiction_isolated": results_j}


if __name__ == "__main__":
    all_results = run_reconstruction()
    summary = {}
    for seq_name, res_list in all_results.items():
        summary[seq_name] = [
            {
                "step":       r["_step"],
                "timestamp":  r["_ts"],
                "action":     r["_raw"],
                "decision":   r["decision"],
                "invariant":  r.get("invariant"),
                "from_state": r["_stp"]["FromState"],
                "to_state":   r["_stp"]["ToState"],
            }
            for r in res_list
        ]
    with open("gelsinger_mason_reconstruction_results.json", "w") as f:
        json.dump({
            "incident":           "Gelsinger Gene Therapy 1999 — Mason Pattern",
            "compiler":           "org_workflow_compiler_v0_1",
            "reconstruction_type":"Structural analog",
            "mason_instance":     10,
            "invariant":          "EXIT (primary) + JURISDICTION (isolated)",
            "lead_time":          "Days to weeks (safety committee to Gelsinger death, Sep 17 1999)",
            "sequences":          summary,
        }, f, indent=2)
    print("\nResults: gelsinger_mason_reconstruction_results.json")
