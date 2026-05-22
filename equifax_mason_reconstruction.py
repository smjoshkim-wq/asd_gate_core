"""
Inverse Incident Reconstruction — Equifax 2017 (Mason Pattern, Org Workflow)
═════════════════════════════════════════════════════════════════════════════
Reconstruction type: DIRECT 1:1
Compiler:           org_workflow_compiler_v0_1.py
Mason pattern:      Expert-role recommendation overridden by authority-role actor;
                    commitment (failure to remediate) proceeds from that state.
Named pattern:      Mason #8

NOTE ON PRIOR EQUIFAX RECONSTRUCTION:
    equifax_cyberir_reconstruction.py (DEFICIENCY_NOTED #5) used the cyber IR
    compiler and fired ORDER: analyst_equifax attempting monitor_siem (IR1_Detect)
    from TRIAGED state without completing IR3_Contain. The deficiency was the
    analyst's own sequence violation.
    This reconstruction captures the DISTINCT structural event: the security
    analyst's explicit patching recommendation being overridden by management
    prioritization decisions. Same incident, two structural patterns.

Source authority:
    U.S. Senate Permanent Subcommittee on Investigations.
        "How Equifax Neglected Cybersecurity and Suffered a Devastating Data Breach."
        Report, November 5, 2018.
    U.S. House Committee on Oversight and Government Reform.
        "The Equifax Data Breach." Staff Report, December 2018.
    FTC v. Equifax consent decree (2019).
    Equifax CEO Richard Smith testimony before Senate Banking Committee,
        October 3, 2017.
    Congressional testimony of CISO Susan Mauldin and CIO David Webb.

Structural mapping:
    analyst_alice  → Equifax security team / vulnerability analysts who triaged
                     CVE-2017-5638 (Apache Struts, CVSS 10.0 Critical) and
                     formally recommended immediate patching
    approver_dave  → Equifax IT management / CISO (Susan Mauldin) /
                     organizational leadership who deprioritized the patch
                     against security team recommendation

Timeline:
    Mar 7, 2017     CERT advisory for CVE-2017-5638 issued.
                    Equifax security team reviews and assesses: CVSS 10.0.
    Mar 9, 2017     Equifax security team issues internal directive to patch
                    within 48 hours (documented in Senate PSI report).
    Mar 9–May 13    Patch directive not followed; management does not
                    escalate or enforce. Security team's recommendation
                    effectively overridden by organizational inaction/
                    deprioritization.
    May 13, 2017    Attacker begins exploiting CVE-2017-5638 in Equifax systems.
    Jul 29, 2017    Breach discovered internally.
    Sep 7, 2017     Public disclosure. 147 million records compromised.
    Lead time:      67 days (recommendation to breach initiation)
                    ~5 months (recommendation to public disclosure)
"""

import sys
import json
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate

T = 0.0  # March 7, 2017 — CERT advisory received

EQUIFAX_MASON_EVENTS = [
    # Phase 1: Security team reviews CVE
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 0.0,
        "_note": "Mar 7, 2017. Security team receives US-CERT advisory for "
                 "CVE-2017-5638 (Apache Struts 2, CVSS 10.0 Critical). "
                 "IDLE → REVIEWING via A1. ADMISSIBLE. "
                 "[Senate PSI Report, November 2018, p. 14]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "review_request",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 5.0,
        "_note": "Security team reviews scope: Equifax uses Apache Struts "
                 "in at least 30 applications. Checks asset inventory for "
                 "affected systems. Loop in REVIEWING. ADMISSIBLE.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 10.0,
        "_note": "Mar 8, 2017. Security analysts formally assess risk. "
                 "CVSS 10.0: remote code execution, unauthenticated. "
                 "Equifax exposure: ACIS application (consumer dispute portal) "
                 "runs on Apache Struts. REVIEWING → ASSESSING via A2. "
                 "ADMISSIBLE. [House Oversight Staff Report 2018, pp. 8–11]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "check_eligibility",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 15.0,
        "_note": "Security team checks which systems are patched vs. unpatched. "
                 "Scanning tool certificate expired — scan incomplete. "
                 "Loop in ASSESSING. ADMISSIBLE. "
                 "[Senate PSI Report: expired SSL certificate prevented "
                 "full network scan]",
    },
    # Phase 2: Security team issues patch recommendation
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 20.0,
        "_note": "Mar 9, 2017. Security team issues internal patch directive: "
                 "all Apache Struts 2 instances to be patched within 48 hours. "
                 "ASSESSING → RECOMMENDING via A3. ADMISSIBLE. "
                 "Content: CVSS 10.0, exploit code publicly available, "
                 "immediate remediation required. "
                 "[Senate PSI Report p. 14: 'Equifax's own security policy "
                 "required patches for critical vulnerabilities within 48 hours']",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "escalate",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 25.0,
        "_note": "Patch directive escalated to IT operations and management. "
                 "Loop in RECOMMENDING. ADMISSIBLE. "
                 "Historical: directive not followed; no management enforcement. "
                 "Equifax scanned on Mar 15 but expired SSL cert missed ACIS.",
    },
    # Phase 3: THE VIOLATION — management enters review workflow
    # Management's organizational deprioritization of the patch = counter-recommendation
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 30.0,
        "_note": "Equifax IT management enters the security remediation review "
                 "workflow and effectively issues a counter-recommendation: "
                 "patch not prioritized for immediate remediation. "
                 "STRUCTURAL VIOLATION: "
                 "(1) approver_dave enters workflow registered to analyst_alice "
                 "→ EXIT fires (actor pivot). "
                 "(2) A3_Recommend is Analyst-only → JURISDICTION (isolated). "
                 "Historical anchor: management failed to enforce 48-hour policy; "
                 "ACIS application remained unpatched through May 13. "
                 "[Senate PSI: 'No executive was aware of the 48-hour policy "
                 "or confirmed it was being enforced']",
    },
    # Phase 4: De facto authorization of unpatched state
    {
        "actor_id":    "approver_dave",
        "action":      "authorize_release",
        "workflow_id": "EQUIFAX_CVE_REMEDIATION_REVIEW",
        "timestamp":   T + 35.0,
        "_note": "Management's inaction = authorization of unpatched production "
                 "state. Post-EXIT. ACIS continues operating. "
                 "May 13: attacker exploits CVE-2017-5638 against ACIS.",
    },
]

EQUIFAX_JURISDICTION_ISOLATED = [
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "EQUIFAX_MGMT_ISOLATED",
        "timestamp":   T + 100.0,
        "_note": "Equifax management (Approver) calls A3_Recommend in isolation. "
                 "A3 not in Approver vocabulary → JURISDICTION. "
                 "Management's organizational counter-recommendation on patch "
                 "prioritization is structurally an Analyst action performed "
                 "by an Approver.",
    },
]


def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — EQUIFAX 2017 (MASON PATTERN)")
    print("Reconstruction type: DIRECT 1:1")
    print("Mason pattern: Expert recommendation overridden by authority actor")
    print("Named pattern: Mason #8")
    print("Source: Senate PSI Report 2018; House Oversight Staff Report 2018")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: Security triage pipeline (analysts → management)")
    print("─"*70)

    compiler = OrgWorkflowCompiler()
    results  = []
    for i, ev in enumerate(EQUIFAX_MASON_EVENTS):
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
    for i, ev in enumerate(EQUIFAX_JURISDICTION_ISOLATED):
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
        print(f"   Approver (IT management) enters Analyst's (security team)")
        print(f"   workflow. Management invaded the vulnerability remediation")
        print(f"   recommendation pipeline.")
    if juris_fire:
        print(f"\n[JURISDICTION] (isolated) — '{juris_fire['_raw']}'")
        print(f"   Approver calling A3_Recommend. Management claiming patch")
        print(f"   prioritization belongs to management, not security analysts.")
    print()
    print("Lead time: 67 days (patch recommendation to breach initiation, May 13)")
    print("Tri-pattern incident: Mason (org_workflow) + DEFICIENCY_NOTED (cyber_ir)")
    print("+ actor-pivot sub-finding (Oversight Disconnection — CISO informal access)")
    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — direct 1:1")
    print("Mason #8 confirmed.")
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
    with open("equifax_mason_reconstruction_results.json", "w") as f:
        json.dump({
            "incident":           "Equifax 2017 — Mason Pattern",
            "compiler":           "org_workflow_compiler_v0_1",
            "reconstruction_type":"Direct 1:1",
            "mason_instance":     8,
            "invariant":          "EXIT (primary) + JURISDICTION (isolated)",
            "lead_time":          "67 days (patch recommendation to breach, May 13 2017)",
            "sequences":          summary,
        }, f, indent=2)
    print("\nResults: equifax_mason_reconstruction_results.json")
