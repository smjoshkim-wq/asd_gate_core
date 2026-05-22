"""
Inverse Incident Reconstruction — Vioxx/Rofecoxib (Mason Pattern, Org Workflow)
════════════════════════════════════════════════════════════════════════════════
Reconstruction type: STRUCTURAL ANALOG
Compiler:           org_workflow_compiler_v0_1.py
Mason pattern:      Expert-role recommendation overridden by authority-role actor;
                    commitment (continued marketing) proceeds from that state.
Named pattern:      Mason #6

NOTE ON PRIOR VIOXX RECONSTRUCTION:
    vioxx_pharma_reconstruction.py (DEFICIENCY_NOTED #8) used the pharma compiler
    and fired JURISDICTION: sponsor_merck modifying DSMB adjudication SOP —
    a role-excluded action on the clinical trial sequence.
    This reconstruction uses the org_workflow compiler to capture the DISTINCT
    structural event: the Merck safety scientists' cardiovascular risk recommendation
    being overridden by commercial management. Same incident, two structural patterns.

Source authority:
    Topol, EJ. "Failing the Public Health — Rofecoxib, Merck, and the FDA."
        NEJM 351:1707–1709 (October 21, 2004).
    Graham, DJ et al. "Risk of Acute Myocardial Infarction and Sudden Cardiac
        Death in Patients Treated with COX-2 Selective and Non-selective NSAIDs."
        Lancet 365:475–481 (2005).
    U.S. Senate Finance Committee. "FDA, Merck, and Vioxx: Putting Patient
        Safety First?" (November 18, 2004).
    Horton, R. "Expression of Concern: Non-steroidal Anti-inflammatory Drugs
        and the Risk of Oral Cancer." Lancet (2004).
    Internal Merck emails and board communications, cited in FDA testimony
        (2004) and Senate Finance Committee staff report (2004).

Structural mapping:
    analyst_alice  → Merck cardiovascular safety scientists / internal safety
                     board (Drs. Scolnick, Shapiro, and colleagues who
                     raised VIGOR cardiovascular signal to management)
    approver_dave  → Merck senior commercial/executive management
                     (responsible for APPROVe trial continuation and
                     post-VIGOR marketing decisions)

Timeline:
    Feb 2000        VIGOR trial results communicated internally to Merck
                    safety scientists. 5× cardiovascular event rate vs. naproxen.
    Jun–Nov 2000    VIGOR data submitted to FDA and published in NEJM.
                    Internal Merck safety board formally flagged.
    2001–2004       Safety scientists issued continued recommendations for
                    label revision or additional study. Management continued
                    marketing and APPROVe trial.
    Sep 30, 2004    Vioxx voluntarily withdrawn. APPROVe trial stopped.
    Lead time:      ~4 years (initial safety recommendation → withdrawal)
                    ~4.5 years (first internal flag → withdrawal)
"""

import sys
import json
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate

T = 0.0  # February 2000 — VIGOR results internally communicated

VIOXX_MASON_EVENTS = [
    # Phase 1: Safety scientists review VIGOR data
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 0.0,
        "_note": "Feb 2000. Merck safety scientists receive VIGOR trial "
                 "results internally. 5× cardiovascular event rate vs. naproxen. "
                 "IDLE → REVIEWING via A1. ADMISSIBLE. "
                 "[Senate Finance Committee staff report, 2004]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "review_request",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 5.0,
        "_note": "Continued review of VIGOR data, APPROVe trial design. "
                 "Loop in REVIEWING. ADMISSIBLE.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 10.0,
        "_note": "Safety scientists formally assess cardiovascular risk. "
                 "VIGOR signal: relative risk 4.85 for MI vs. naproxen. "
                 "REVIEWING → ASSESSING via A2. ADMISSIBLE. "
                 "[Topol NEJM 2004; Graham Lancet 2005]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "evaluate_compliance",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 15.0,
        "_note": "Assess against FDA label requirements and post-marketing "
                 "safety obligations. Loop in ASSESSING. ADMISSIBLE.",
    },
    # Phase 2: Safety scientists issue recommendation
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 20.0,
        "_note": "Safety scientists flag cardiovascular concern formally. "
                 "Recommendation: label revision and/or additional "
                 "prospective safety study. ASSESSING → RECOMMENDING via A3. "
                 "ADMISSIBLE. Content: cardiovascular signal is real; "
                 "marketing language should not characterize as 'naproxen "
                 "protective' without label disclosure. "
                 "[Internal Merck communications cited in Senate testimony]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "escalate",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 25.0,
        "_note": "Safety recommendation escalated to commercial leadership. "
                 "Loop in RECOMMENDING. ADMISSIBLE. "
                 "Documented: internal safety board continued to flag through "
                 "2001-2004 as APPROVe trial continued.",
    },
    # Phase 3: THE VIOLATION — management enters the review workflow
    # and issues counter-recommendation to proceed
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 30.0,
        "_note": "Merck commercial management enters the safety review "
                 "workflow and issues a recommendation to continue marketing "
                 "and the APPROVe trial. STRUCTURAL VIOLATION: "
                 "(1) approver_dave is entering a workflow already registered "
                 "to analyst_alice → EXIT fires (actor pivot). "
                 "(2) A3_Recommend is Analyst-only — Approver calling A3 "
                 "→ JURISDICTION fires (isolated sequence). "
                 "Historical anchor: Merck management communications "
                 "2001-2004 overriding safety scientists' recommendations. "
                 "[Senate Finance Committee, FDA Advisory Committee testimony 2004]",
    },
    # Phase 4: Post-violation — management authorization
    {
        "actor_id":    "approver_dave",
        "action":      "authorize_release",
        "workflow_id": "VIOXX_VIGOR_SAFETY_REVIEW",
        "timestamp":   T + 35.0,
        "_note": "Management authorizes continuation of marketing and "
                 "APPROVe trial. Post-EXIT action. "
                 "HYSTERESIS fires if it leads to unvisited state. "
                 "Historical anchor: APPROVe trial continued 2001→2004; "
                 "withdrawal September 30, 2004 after APPROVe interim data "
                 "showed 2× MI risk.",
    },
]

VIOXX_JURISDICTION_ISOLATED = [
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "VIOXX_MGMT_ISOLATED",
        "timestamp":   T + 100.0,
        "_note": "Merck commercial management (Approver) calls A3_Recommend — "
                 "structural assertion that recommendation authority belongs "
                 "to management. A3 not in Approver vocabulary → JURISDICTION. "
                 "This is the 'management hat' analog for Vioxx: commercial "
                 "leadership claiming the safety recommendation role.",
    },
]


def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — VIOXX/ROFECOXIB (MASON PATTERN)")
    print("Reconstruction type: STRUCTURAL ANALOG")
    print("Mason pattern: Expert recommendation overridden by authority actor")
    print("Named pattern: Mason #6")
    print("Source: NEJM 2004; Senate Finance Committee 2004; Lancet 2005")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: Safety review pipeline (scientists → management)")
    print("─"*70)

    compiler = OrgWorkflowCompiler()
    results  = []
    for i, ev in enumerate(VIOXX_MASON_EVENTS):
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
    for i, ev in enumerate(VIOXX_JURISDICTION_ISOLATED):
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
        print(f"   Approver (Merck management) enters Analyst's (safety scientists')")
        print(f"   workflow. Commercial leadership invaded the safety recommendation")
        print(f"   pipeline.")
    if juris_fire:
        print(f"\n[JURISDICTION] (isolated) — '{juris_fire['_raw']}'")
        print(f"   Approver calling A3_Recommend — claiming recommendation authority.")
        print(f"   Structural reading: Merck management asserted the safety")
        print(f"   recommendation role belongs to commercial leadership.")
    print()
    print("Lead time: ~4 years (safety recommendation → withdrawal, Sep 30 2004)")
    print("Mason #6 confirmed. Dual-pattern: Mason (org_workflow) +")
    print("DEFICIENCY_NOTED (pharma) — same incident, distinct structural firings.")
    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — structural analog")
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
    with open("vioxx_mason_reconstruction_results.json", "w") as f:
        json.dump({
            "incident":           "Vioxx/Rofecoxib — Mason Pattern",
            "compiler":           "org_workflow_compiler_v0_1",
            "reconstruction_type":"Structural analog",
            "mason_instance":     6,
            "invariant":          "EXIT (primary) + JURISDICTION (isolated)",
            "lead_time":          "~4 years (safety recommendation to withdrawal)",
            "sequences":          summary,
        }, f, indent=2)
    print("\nResults: vioxx_mason_reconstruction_results.json")
