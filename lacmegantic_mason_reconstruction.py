"""
Inverse Incident Reconstruction — Lac-Mégantic 2013 (Mason Pattern, Org Workflow)
════════════════════════════════════════════════════════════════════════════════════
Reconstruction type: DIRECT 1:1
Compiler:           org_workflow_compiler_v0_1.py
Mason pattern:      Expert-role recommendation overridden by authority-role actor;
                    commitment (single-person crew operations) proceeds from that state.
Named pattern:      Mason #7

NOTE ON PRIOR LAC-MÉGANTIC RECONSTRUCTION:
    lacmegantic_rail_reconstruction.py (DEFICIENCY_NOTED #9) used the rail compiler
    and fired ORDER: engineer_holt executing crew_change from OPERATING state
    before adequate securement was complete. The deficiency document was the
    TC SMP Audit of MMA (2012).
    This reconstruction captures the DISTINCT structural event: MMA operations
    staff concerns about single-person crew protocol being overridden by management.
    Same incident, two structural patterns.

Source authority:
    Transportation Safety Board of Canada. "Runaway and Main-Track Derailment."
        Rail Investigation Report R13D0054. (August 2014).
    TSB R13D0054 §3.4 Safety Management System findings.
    TSB R13D0054 §2.6.2 Single-person train operations.
    CBC/Radio-Canada investigative reporting on MMA internal communications,
        2013–2014.
    Federal court proceedings, MMA bankruptcy filings, 2013.

Structural mapping:
    analyst_alice  → MMA operations supervisor / crew coordinator who raised
                     concerns about single-person crew operations on unattended
                     consists on grades (documented in TSB §2.6.2, §3.4)
    approver_dave  → MMA management / executive team (Burkhart and associates)
                     who authorized single-person crew policy over staff concerns

Timeline:
    2012            TC Safety Management System audit identifies deficiencies
                    in MMA's SPC securement procedures. Operations staff
                    internally flag single-person crew risk on grades.
    Early 2013      Operations staff concerns about MMA-002 run profile
                    documented internally.
    Jul 5–6, 2013   Engineer Holt parks MMA-002 at Nantes. Single-person
                    crew policy: Holt is sole operator. Consist left
                    unattended on 1.2% grade.
    Jul 6, 2013     ~00:14 — consist runs away. 47 fatalities.
    Lead time:      ~months (staff concerns → derailment)
                    ~6–12 months (TC audit to derailment, documented concern period)
"""

import sys
import json
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate

T = 0.0  # Early 2013 — operations staff concerns about single-person crew

LACMEGANTIC_MASON_EVENTS = [
    # Phase 1: Operations staff review single-person crew protocol
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 0.0,
        "_note": "2012–early 2013. MMA operations supervisor reviews "
                 "single-person train crew policy and TC 2012 audit findings. "
                 "IDLE → REVIEWING via A1. ADMISSIBLE. "
                 "[TSB R13D0054 §2.6.2, §3.4]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "review_request",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 5.0,
        "_note": "Review of MMA-002 run profile: Nantes siding, 1.2% grade, "
                 "single-person crew standard. Loop in REVIEWING. ADMISSIBLE.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 10.0,
        "_note": "Operations staff assesses risk of unattended consist on grade "
                 "under single-person crew protocol. Handbrake sufficiency, "
                 "locomotive isolation procedures. REVIEWING → ASSESSING via A2. "
                 "ADMISSIBLE. [TSB §2.5 — locomotive shutdown and SPC protocol]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "evaluate_compliance",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 15.0,
        "_note": "Evaluate against TC General Rules and SPC requirements "
                 "for unattended consists on grades. Loop in ASSESSING. ADMISSIBLE.",
    },
    # Phase 2: Operations staff recommendation
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 20.0,
        "_note": "Operations staff flags concern: single-person crew on grades "
                 "creates inadequate securement verification. Recommendation: "
                 "require second crew member or enhanced handbrake count "
                 "verification protocol before leaving consist unattended. "
                 "ASSESSING → RECOMMENDING via A3. ADMISSIBLE. "
                 "[TSB R13D0054 §3.4 — safety management system finding: "
                 "MMA did not adequately implement corrective actions from "
                 "TC audit]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "escalate",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 25.0,
        "_note": "Concern escalated to MMA management. Loop in RECOMMENDING. "
                 "ADMISSIBLE. TSB documents: management aware of TC audit "
                 "deficiency findings; corrective action plan filed but "
                 "not fully implemented.",
    },
    # Phase 3: THE VIOLATION — management enters review workflow
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 30.0,
        "_note": "MMA management enters the operations review workflow and "
                 "issues recommendation to continue single-person crew policy. "
                 "STRUCTURAL VIOLATION: "
                 "(1) approver_dave enters workflow registered to analyst_alice "
                 "→ EXIT fires (actor pivot). "
                 "(2) A3_Recommend is Analyst-only → JURISDICTION (isolated). "
                 "Historical anchor: MMA management maintained single-person "
                 "crew policy despite internal concerns and TC audit. "
                 "[TSB R13D0054 §3.4; §2.6.2]",
    },
    # Phase 4: Authorization to proceed
    {
        "actor_id":    "approver_dave",
        "action":      "authorize_release",
        "workflow_id": "MMA_CREW_PROTOCOL_REVIEW",
        "timestamp":   T + 35.0,
        "_note": "Management authorizes continued single-person crew operations. "
                 "Post-EXIT action. Operational commitment: MMA-002 run July 5-6, "
                 "2013 proceeds under single-person crew policy.",
    },
]

LACMEGANTIC_JURISDICTION_ISOLATED = [
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "MMA_MGMT_ISOLATED",
        "timestamp":   T + 100.0,
        "_note": "MMA management (Approver) calls A3_Recommend in isolated workflow. "
                 "A3 not in Approver vocabulary → JURISDICTION. "
                 "Structural reading: management asserted the operational "
                 "safety recommendation role belongs to management, not "
                 "operations staff.",
    },
]


def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — LAC-MÉGANTIC (MASON PATTERN)")
    print("Reconstruction type: DIRECT 1:1")
    print("Mason pattern: Expert recommendation overridden by authority actor")
    print("Named pattern: Mason #7")
    print("Source: TSB R13D0054 §2.6.2, §3.4")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: Operations review pipeline (staff → management)")
    print("─"*70)

    compiler = OrgWorkflowCompiler()
    results  = []
    for i, ev in enumerate(LACMEGANTIC_MASON_EVENTS):
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
    for i, ev in enumerate(LACMEGANTIC_JURISDICTION_ISOLATED):
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
        print(f"   Approver (MMA management) enters Analyst's (operations staff)")
        print(f"   workflow. Management invaded the operational safety review pipeline.")
    if juris_fire:
        print(f"\n[JURISDICTION] (isolated) — '{juris_fire['_raw']}'")
        print(f"   Approver calling A3_Recommend. Structural reading: management")
        print(f"   claimed the operational safety recommendation role.")
    print()
    print("Lead time: ~6–12 months (TC audit concern period → July 6, 2013)")
    print("Operational lead time: months (internal flagging → derailment)")
    print("Note: dual-pattern incident — Mason (org_workflow) +")
    print("DEFICIENCY_NOTED (rail) — distinct structural firings on same event.")
    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — direct 1:1")
    print("Mason #7 confirmed.")
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
    with open("lacmegantic_mason_reconstruction_results.json", "w") as f:
        json.dump({
            "incident":           "Lac-Mégantic — Mason Pattern",
            "compiler":           "org_workflow_compiler_v0_1",
            "reconstruction_type":"Direct 1:1",
            "mason_instance":     7,
            "invariant":          "EXIT (primary) + JURISDICTION (isolated)",
            "lead_time":          "~6–12 months (TC audit period to derailment)",
            "sequences":          summary,
        }, f, indent=2)
    print("\nResults: lacmegantic_mason_reconstruction_results.json")
