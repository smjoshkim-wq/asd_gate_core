"""
Bhopal Inverse Reconstruction — Org Workflow Substrate
═══════════════════════════════════════════════════════════════════════

Substrate: org_workflow_compiler_v0_1 (Approver/Analyst, A1..A5)
Type:      Structural Analog (org_workflow on chemical-plant decision pipeline)
Lead time: ~30 months (May 1982 → 2-3 December 1984)
Precision: Month-level

Historical anchor
─────────────────
Bhopal, Madhya Pradesh, India. Union Carbide India Ltd (UCIL) Pesticide
Plant, Sevin manufacturing using methyl isocyanate (MIC) intermediate.
Parent: Union Carbide Corporation (UCC), Danbury, Connecticut, USA.

May 1982: Three UCC corporate engineers conducted operational safety
survey of Bhopal plant. Audit report identified 61 hazards, including
explicit warning of "runaway reaction in MIC unit". UCIL engineering
management forwarded recommendations to UCC HQ for funding to maintain
refrigeration system, retain MIC tank inventory limits, and preserve
operator staffing levels (12 operators per MIC shift).

UCC HQ response (1982-83): Denied capital expenditure for refrigeration
maintenance (~$33,000/year freon costs); endorsed cost reductions including
reduced operator staffing (12 → 6 per shift on MIC unit) and "for future
study" deferral of the seawall-equivalent layered safety system upgrades.
Plant operated to December 1984 with refrigeration disabled, flare tower
disconnected, vent gas scrubber undersized, and MIC inventory exceeding
audit-recommended limits.

Reconstruction geometry
───────────────────────
This is the fourth instance of the Mason pattern:
  - Challenger (1986): Mason (Approver) overrode Boisjoly (Analyst) on
    O-ring temperature concern.
  - Therac-25 (1987): AECL response team (Approver) overrode Tyler
    (Analyst) on dose-discrepancy bug investigations.
  - Fukushima (2008): TEPCO Nuclear Power Division (Approver) overrode
    Tsunami Risk Assessment Group (Analyst) on OP+15.7m seawall upgrade.
  - Bhopal (1982): UCC HQ Engineering (Approver) overrode UCIL Plant
    Engineering (Analyst) on safety system funding.

Mechanism is structurally identical across all four:
  Analyst executes A1_Review → A2_Assess → A3_Recommend in workflow_id.
  Approver (different actor, Approver role) enters same workflow_id and
  issues A3_Recommend as counter-recommendation → actor_pivot → EXIT fires.

R5 boundary
───────────
UCC HQ also failed to execute follow-up audits between 1982 and 1984.
Per Inverse Incident Methodology v1.0 R5 scope constraint, the missing
follow-ups are not modeled as gate fires; the gate models the commission
of the counter-recommendation, which is the observable structural event.

Follows from
────────────
- 2026_05_19_Inverse_Incident_Methodology_v1_0.md
- 2026_05_21_Fukushima_Three_Substrate_Reconstruction_Note.md
- Repeatable_Compiler_Methodology_v1_1.md
"""

import json
import sys
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import (
    OrgWorkflowCompiler,
    ORG_ROLE_TABLE,
)
from domain_compiler_v0_9 import evaluate_gate

# Register the historical actors with their organizational roles.
# UCIL engineering = Analyst; UCC HQ executive engineering = Approver.
ORG_ROLE_TABLE["analyst_ucil_eng"] = "Analyst"
ORG_ROLE_TABLE["approver_ucc_hq"] = "Approver"

BASE_TS = 1_336_867_200.0  # May 13, 1982 (~ audit completion week)
ONE_WEEK = 7 * 24 * 3600.0
ONE_MONTH = 30 * 24 * 3600.0


def run_reconstruction():
    compiler = OrgWorkflowCompiler()
    workflow_id = "1982_safety_audit_response"

    # Step 1: UCIL engineering reviews the UCC operational safety survey
    # findings (May 1982 audit, 70-page report, 61 hazards documented).
    step1 = {
        "actor_id": "analyst_ucil_eng",
        "action": "read_document",
        "workflow_id": workflow_id,
        "timestamp": BASE_TS + 0,
    }

    # Step 2: UCIL engineering assesses risk severity of the identified
    # hazards (including runaway reaction risk in MIC unit).
    step2 = {
        "actor_id": "analyst_ucil_eng",
        "action": "assess_risk",
        "workflow_id": workflow_id,
        "timestamp": BASE_TS + 2 * 24 * 3600,
    }

    # Step 3: UCIL engineering recommends remediation — funding for
    # refrigeration maintenance, MIC inventory limits, staffing retention.
    step3 = {
        "actor_id": "analyst_ucil_eng",
        "action": "flag_concern",
        "workflow_id": workflow_id,
        "timestamp": BASE_TS + 7 * 24 * 3600,
    }

    # Step 4: UCC HQ (Danbury) enters the same workflow_id and issues
    # counter-recommendation — defer remediation, cut staffing, save costs.
    # This is the actor_pivot: a different actor in the Approver role
    # asserting recommendation authority over the analyst's workflow.
    step4 = {
        "actor_id": "approver_ucc_hq",
        "action": "flag_concern",
        "workflow_id": workflow_id,
        "timestamp": BASE_TS + 3 * ONE_MONTH,
    }

    events = [step1, step2, step3, step4]
    results = []
    for i, ev in enumerate(events):
        packet = compiler.compile(ev)
        r = evaluate_gate(packet)
        results.append({
            "step": i + 1,
            "actor_id": ev["actor_id"],
            "action": ev["action"],
            "decision": r["decision"],
            "invariant": r["invariant"],
        })
        print(f"step {i+1}: {ev['actor_id']:24s} {ev['action']:20s} "
              f"→ {r['decision']:14s} ({r['invariant'] or '—'})")

    return results


def main():
    print("=" * 72)
    print("Bhopal Org-Workflow Reconstruction — UCC HQ Override Geometry")
    print("=" * 72)
    print()
    results = run_reconstruction()
    print()

    # Validate: EXIT must fire at the approver actor_pivot step (step 4).
    exit_fires = [r for r in results if r["invariant"] == "EXIT"]
    pre_exit_admissible = all(
        r["decision"] == "ADMISSIBLE"
        for r in results[:3]
    )

    summary = {
        "incident": "Bhopal Disaster — UCC 1982 Audit Override",
        "substrate": "org_workflow",
        "reconstruction_type": "Structural Analog",
        "precision_class": "Month-level",
        "lead_time_months": 31,
        "lead_time_description": "May 1982 audit response → Dec 2-3, 1984 release",
        "invariants_fired": [
            {"step": r["step"], "invariant": r["invariant"]}
            for r in results if r["invariant"]
        ],
        "exit_fired_at_step": exit_fires[0]["step"] if exit_fires else None,
        "pre_exit_admissible_steps": pre_exit_admissible,
        "geometry": "Fourth instance of Mason pattern: Approver actor_pivot into Analyst workflow_id triggers EXIT via actor_pivot detection",
        "cross_incident_stability": [
            "Challenger 1986 (Mason/Boisjoly)",
            "Therac-25 1987 (AECL/Tyler)",
            "Fukushima 2008 (TEPCO NPD/Tsunami Risk Group)",
            "Bhopal 1982 (UCC HQ/UCIL Engineering)",
        ],
        "events": results,
    }

    out_path = "/home/claude/bhopal/bhopal_org_reconstruction_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results written: {out_path}")
    return exit_fires and pre_exit_admissible


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
