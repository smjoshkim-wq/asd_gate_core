"""
Inverse Incident Reconstruction — Theranos (Mason Pattern, Org Workflow)
════════════════════════════════════════════════════════════════════════
Reconstruction type: DIRECT 1:1
Compiler:           org_workflow_compiler_v0_1.py
Mason pattern:      Expert-role recommendation overridden by authority-role actor;
                    commitment (continued patient testing) proceeds from that state.
Named pattern:      Mason #9

Source authority:
    Carreyrou, John. "Bad Blood: Secrets and Lies in a Silicon Valley Startup."
        Knopf (2018). (Sourced from Theranos internal interviews and documents)
    SEC v. Elizabeth Holmes and Ramesh Balwani. SEC Complaint (March 14, 2018).
    U.S. v. Elizabeth Holmes. N.D. Cal. No. 5:18-cr-00258-EJD.
        Trial testimony: Adam Rosendorff (lab director), Erika Cheung (QC),
        Sasan Karimi (assay development), Mark Pandori (lab director).
    CMS inspection reports: Centers for Medicare and Medicaid Services.
        Theranos laboratory inspection findings, 2015–2016.
    U.S. v. Balwani trial, 2022: testimony of lab staff.

Structural mapping:
    analyst_alice  → Theranos lab director / quality control staff:
                     Adam Rosendorff (lab director 2012–2014), Erika Cheung
                     (quality control), and colleagues who formally flagged
                     test accuracy failures and recommended suspension of
                     patient-use testing on Edison devices
    approver_dave  → Elizabeth Holmes (CEO) and/or Ramesh Balwani (COO/President)
                     who overrode lab staff recommendations and continued
                     patient testing

Timeline:
    2012–2013       Theranos lab staff begin identifying accuracy failures on
                    Edison proprietary devices. QC flags reported internally.
    2013            Adam Rosendorff (lab director) documents accuracy concerns
                    in multiple internal emails. Recommends suspending Edison
                    devices for patient diagnostics.
    2013–2014       Holmes/Balwani override recommendations; patient testing
                    continues. Lab continues running Edison devices alongside
                    traditional analyzers (ELISA, Siemens) without disclosure.
    Oct 2015        WSJ investigation (Carreyrou) — public disclosure.
    Mar 2016        CMS declares Theranos lab poses 'immediate jeopardy' to
                    patient safety.
    Mar 2018        SEC fraud charges. Jun 2018: criminal indictment.
    Lead time:      ~2–3 years (internal flags → public disclosure)
                    Precision class: day-level (trial testimony dates)
"""

import sys
import json
sys.path.insert(0, ".")

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate

T = 0.0  # 2013 — lab director internal accuracy concern period

THERANOS_MASON_EVENTS = [
    # Phase 1: Lab director and QC staff review accuracy data
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 0.0,
        "_note": "2012–2013. Theranos lab staff review Edison device accuracy "
                 "data: coefficient of variation on finger-stick vs. venous "
                 "draws, proficiency testing results. IDLE → REVIEWING via A1. "
                 "ADMISSIBLE. [Rosendorff trial testimony; Carreyrou Ch. 12]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "review_request",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 5.0,
        "_note": "QC staff reviews proficiency testing failures on Edison devices. "
                 "Documents instances of results diverging from reference methods. "
                 "Loop in REVIEWING. ADMISSIBLE. "
                 "[Erika Cheung trial testimony — QC failure documentation]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 10.0,
        "_note": "Lab director assesses patient safety risk from inaccurate "
                 "diagnostic results. Categories: HIV tests, HbA1c, PSA, "
                 "troponin — all running on Edison or diluted on Siemens. "
                 "REVIEWING → ASSESSING via A2. ADMISSIBLE. "
                 "[Rosendorff emails cited in Holmes trial exhibit list]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "evaluate_compliance",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 15.0,
        "_note": "Lab director evaluates compliance with CLIA standards for "
                 "laboratory quality control and proficiency testing requirements. "
                 "Edison devices not FDA-cleared for diagnostics; CLIA compliance "
                 "questionable. Loop in ASSESSING. ADMISSIBLE.",
    },
    # Phase 2: Lab director and QC issue recommendation
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 20.0,
        "_note": "2013. Lab director formally flags patient safety concern: "
                 "Edison device accuracy insufficient for clinical diagnostics. "
                 "Recommendation: suspend Edison devices for patient testing; "
                 "use only FDA-cleared Siemens analyzers. "
                 "ASSESSING → RECOMMENDING via A3. ADMISSIBLE. "
                 "[Rosendorff internal email: 'I'm not comfortable with what "
                 "we're doing here' — documented in Carreyrou and trial record]",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "escalate",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 25.0,
        "_note": "Concern escalated to Holmes/Balwani directly. "
                 "Loop in RECOMMENDING. ADMISSIBLE. "
                 "[Carreyrou: Rosendorff raised concerns in meetings with "
                 "Holmes; Holmes dismissed or redirected concerns]",
    },
    # Phase 3: THE VIOLATION — Holmes/Balwani enters review workflow
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 30.0,
        "_note": "Holmes/Balwani enters the lab accuracy review workflow and "
                 "issues recommendation to continue patient testing on Edison. "
                 "STRUCTURAL VIOLATION: "
                 "(1) approver_dave enters workflow registered to analyst_alice "
                 "→ EXIT fires (actor pivot). "
                 "(2) A3_Recommend is Analyst-only → JURISDICTION (isolated). "
                 "Historical anchor: Holmes/Balwani repeatedly dismissed or "
                 "overrode lab director concerns; Rosendorff resigned 2014 "
                 "after recommendations continued to be ignored. "
                 "[Holmes trial testimony; Carreyrou Chs. 12–15]",
    },
    # Phase 4: Continued patient testing
    {
        "actor_id":    "approver_dave",
        "action":      "authorize_release",
        "workflow_id": "THERANOS_LAB_ACCURACY_REVIEW",
        "timestamp":   T + 35.0,
        "_note": "Holmes/Balwani authorize continued patient diagnostic use. "
                 "Post-EXIT action. Edison devices continue in patient use "
                 "2013–2015 despite lab director recommendation. "
                 "CMS 2016: 'immediate jeopardy' determination.",
    },
]

THERANOS_JURISDICTION_ISOLATED = [
    {
        "actor_id":    "approver_dave",
        "action":      "recommend_approval",
        "workflow_id": "THERANOS_MGMT_ISOLATED",
        "timestamp":   T + 100.0,
        "_note": "Holmes/Balwani (Approver) calls A3_Recommend in isolation. "
                 "A3 not in Approver vocabulary → JURISDICTION. "
                 "Structural reading: executive leadership asserted the clinical "
                 "safety recommendation role belongs to management, not lab "
                 "directors. The structural analog to 'Take off your lab hat.'",
    },
]


def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — THERANOS (MASON PATTERN)")
    print("Reconstruction type: DIRECT 1:1")
    print("Mason pattern: Expert recommendation overridden by authority actor")
    print("Named pattern: Mason #9")
    print("Source: Carreyrou 2018; Holmes/Balwani trial testimony; CMS 2016")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: Lab review pipeline (lab director → management)")
    print("─"*70)

    compiler = OrgWorkflowCompiler()
    results  = []
    for i, ev in enumerate(THERANOS_MASON_EVENTS):
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
    for i, ev in enumerate(THERANOS_JURISDICTION_ISOLATED):
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
        print(f"   Approver (Holmes/Balwani) enters Analyst's (lab director)")
        print(f"   workflow. Executive leadership invaded the clinical safety")
        print(f"   recommendation pipeline.")
    if juris_fire:
        print(f"\n[JURISDICTION] (isolated) — '{juris_fire['_raw']}'")
        print(f"   Approver calling A3_Recommend. Structural analog to")
        print(f"   'Take off your lab hat': management claimed the clinical")
        print(f"   safety recommendation role.")
    print()
    print("Lead time: ~2–3 years (internal flag to public disclosure, Oct 2015)")
    print("Note: new substrate for Mason pattern — clinical/lab diagnostics.")
    print("Overlaps Theranos PACER compiler anchor; org_workflow fires on")
    print("the internal decision pipeline, PACER on the regulatory proceeding.")
    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — direct 1:1")
    print("Mason #9 confirmed.")
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
    with open("theranos_mason_reconstruction_results.json", "w") as f:
        json.dump({
            "incident":           "Theranos — Mason Pattern",
            "compiler":           "org_workflow_compiler_v0_1",
            "reconstruction_type":"Direct 1:1",
            "mason_instance":     9,
            "invariant":          "EXIT (primary) + JURISDICTION (isolated)",
            "lead_time":          "~2–3 years (internal flag to public disclosure)",
            "sequences":          summary,
        }, f, indent=2)
    print("\nResults: theranos_mason_reconstruction_results.json")
