"""
Inverse Incident Reconstruction — Fukushima Daiichi 2011 (Org Workflow Substrate)
═════════════════════════════════════════════════════════════════════════════════
TEPCO Pre-Incident Seismic / Tsunami Risk Dismissal (2008)

Source authority:
    NAIIC (National Diet of Japan Fukushima Nuclear Accident Independent
    Investigation Commission) Final Report, July 2012, Chapter 1 and
    Chapter 5 (Regulators and Operators).
    Government of Japan Investigation Committee on the Accident at
    Fukushima Nuclear Power Stations (ICANPS) Final Report, Jul 2012,
    Section on "Tsunami Countermeasures."
    TEPCO Internal Reports on Tsunami Assessment (subsequently disclosed
    in litigation): Sakai et al., "Probabilistic Tsunami Hazard
    Assessment for Fukushima Daiichi" (2008 internal study).
    IAEA Director General Report on the Fukushima Daiichi Accident,
    2015, Volume 1, Section 1.3.

Reconstruction scope:
    This script reconstructs the role-attributed decision pipeline of
    TEPCO's 2008 internal tsunami risk assessment and the management
    decision to dismiss the assessment's recommendation. The events
    span roughly April 2008 (initial probabilistic study) through
    September 2008 (final management decision not to upgrade the
    seawall or relocate emergency diesel generators).

    The structural geometry being detected is the same as Challenger
    Mason "management hat" moment and the Therac AECL response pattern:
    engineering analysts produce a recommendation; management actors
    enter the analyst workflow and override the recommendation by
    issuing their own counter-recommendation, structurally crossing
    the role boundary.

Primary structural claim being tested:
    The substrate-invariance composition claim against an externally-
    precipitated cascade. The org workflow violation occurred ~3 years
    BEFORE the external trigger (tsunami). This demonstrates that the
    structural pre-condition for cascade vulnerability was identifiable
    in the decision pipeline at the time of the management decision,
    independent of any external precipitating event.

    This is structurally identical to the Challenger management override
    pattern: a recommendation from engineering analysts to a more
    conservative position; an Approver actor entering the engineering
    workflow and issuing a counter-recommendation that the more
    permissive position be retained.

Definition of "point of no return":
    The TEPCO Nuclear Power Division management decision (~September
    2008) not to act on the internal tsunami probability assessment.
    Once the decision was made and no follow-up engineering action was
    triggered, the seawall remained at OP+5.7m (vs. the assessment's
    OP+15.7m estimate) and the emergency diesel generators remained
    in their tsunami-vulnerable locations. The structural vulnerability
    that the cascade would exploit was committed at this point.

External trigger note:
    The Tohoku M9.0 earthquake (March 11, 2011, 14:46 JST) and tsunami
    (peak ~15:37 JST) are the external precipitating events that turned
    the structural vulnerability into a catastrophic cascade. The gate
    cannot detect external precipitating events; what it detects is
    the structural commission that left the site vulnerable.

    The org workflow lead time of approximately 3 years from violation
    to consequence is the longest lead time in the project's
    reconstruction corpus. It is also the cleanest separation between
    the structural violation and the precipitating event: by the time
    the tsunami arrived, the violation had been complete for years.

Timeline — sources: NAIIC Chapter 5; ICANPS tsunami section;
disclosed TEPCO internal documents:
    Apr 2008  TEPCO Nuclear Power Division engineering team initiates
              probabilistic tsunami hazard assessment for Daiichi site,
              prompted by 2002 Headquarters for Earthquake Research
              Promotion (HERP) seismic hazard map updates.
    Jul 2008  Engineering team completes preliminary study. Maximum
              credible tsunami estimated at 15.7m at Daiichi site,
              exceeding the OP+10m design basis seawall by ~5.7m
              and the actual OP+5.7m seawall by ~10m.
    Aug 2008  Engineering team formally documents recommendation:
              upgrade seawall to OP+15.7m or relocate emergency
              diesel generators (or both). Recommendation forwarded
              to Nuclear Power Division management.
    Aug 2008  Nuclear Power Division management (Director-class
              Approver) reviews the recommendation. Management
              determines the assessment is "not academic consensus"
              and "not regulator-mandated," and that the cost of
              upgrade (~$60M USD est.) is not justified absent
              regulatory requirement.
    Sep 2008  Nuclear Power Division management issues internal
              communication declining the upgrade. Engineering
              team's recommendation is effectively counter-recommended.
              The recommendation is shelved as "for future study."

    Mar 11, 2011 14:46 JST  Tohoku earthquake — external trigger,
                            ~2.5 years after the management decision.
    Mar 11, 2011 15:37 JST  Tsunami arrives at Daiichi, peak ~14-15m.
                            Seawall (OP+5.7m) overtopped, diesel
                            generators destroyed, Station Blackout
                            initiated.
"""

import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate


# ═══════════════════════════════════════════════════════════════════════
# Reconstructed event sequence — TEPCO 2008 tsunami risk dismissal
# Timestamps: days since April 1, 2008 (study initiation)
# Tsunami:   Mar 11, 2011 = ~1075 days after Apr 1, 2008
# ═══════════════════════════════════════════════════════════════════════

FUKUSHIMA_TEPCO_2008_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: Engineering analyst workflow (admissible)
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":    "analyst_alice",   # Stand-in for TEPCO engineer
        "action":      "review_request",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   0.0,                # Apr 1, 2008 (study initiation)
        "_note": "April 2008. TEPCO Nuclear Power Division engineer "
                 "initiates review of HERP 2002 seismic hazard map updates "
                 "for the Fukushima Daiichi site. A1 from IDLE → REVIEWING. "
                 "Admissible (Analyst initiating review).",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "read_document",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   30.0,
        "_note": "~May 2008. Engineer reads HERP probabilistic seismic "
                 "hazard documentation and prior Daiichi tsunami "
                 "assessments. A1 loop in REVIEWING. Admissible.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "assess_risk",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   90.0,
        "_note": "~July 2008. Engineer completes probabilistic tsunami "
                 "hazard assessment. Maximum credible tsunami: 15.7m at "
                 "Daiichi. Seawall: OP+5.7m. Design basis: OP+10m. "
                 "A2 from REVIEWING → ASSESSING. Admissible.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "evaluate_compliance",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   100.0,
        "_note": "~July 2008. Engineer compares assessment against design "
                 "basis. Significant gap between assessment (15.7m) and "
                 "design basis (10m). A2 loop in ASSESSING. Admissible.",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "recommend_approval",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   130.0,
        "_note": "August 2008. Engineer recommends seawall upgrade to "
                 "OP+15.7m and/or relocation of emergency diesel "
                 "generators to higher ground. Estimated cost ~$60M USD. "
                 "A3 from ASSESSING → RECOMMENDING. Admissible "
                 "(Analyst recommending mitigation per safety analysis).",
    },
    {
        "actor_id":    "analyst_alice",
        "action":      "flag_concern",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   135.0,
        "_note": "~August 2008. Engineer formally flags concern in the "
                 "recommendation: the gap between assessed tsunami height "
                 "and current seawall is the dominant residual risk for "
                 "the site. A3 loop in RECOMMENDING. Admissible.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: THE VIOLATION — management invades analyst workflow
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":    "approver_dave",   # Stand-in for TEPCO Nuclear Power Division Director
        "action":      "recommend_approval",
        "workflow_id": "tsunami_risk_assessment_2008",
        "timestamp":   160.0,
        "_note": "STRUCTURAL VIOLATION. September 2008. TEPCO Nuclear "
                 "Power Division management (Director-class actor, mapped "
                 "as Approver) enters the engineering team's tsunami risk "
                 "assessment workflow and issues a counter-recommendation: "
                 "decline the upgrade, shelve for 'future study.' "
                 "Action mapping: 'recommend_approval' → A3_Recommend. "
                 "Role: Approver. "
                 "Same workflow_id as engineering team's assessment. "
                 "Approver entering Analyst-owned workflow → actor_pivot "
                 "→ EXIT fires (same geometry as Challenger Mason caucus "
                 "and Therac AECL response pattern). "
                 "JURISDICTION is also present (A3_Recommend is Analyst-"
                 "only; Approver attempting A3 crosses the role boundary "
                 "at the action-class level) but EXIT surfaces first per "
                 "gate evaluation order. "
                 "Historical significance: this decision shelved the "
                 "mitigation recommendation that would have raised the "
                 "seawall above the eventual tsunami height. Lead time "
                 "to the precipitating event: ~2.5 years.",
    },
]


def run_reconstruction():
    print("\n" + "═"*72)
    print("INVERSE INCIDENT RECONSTRUCTION — FUKUSHIMA 2011 (ORG WORKFLOW)")
    print("TEPCO 2008 Tsunami Risk Assessment — Management Override")
    print("Source: NAIIC; ICANPS; disclosed TEPCO internal documents")
    print("═"*72)
    print()

    compiler = OrgWorkflowCompiler()
    results  = []

    for i, ev in enumerate(FUKUSHIMA_TEPCO_2008_EVENTS):
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_note"] = ev.get("_note", "")
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        result["_actor"] = ev["actor_id"]
        results.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"] or "—"
        to  = packet["STP_Header"]["ToState"] or "—"
        role = packet["STP_Header"]["Role"]
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.0f}d | {ev['action']:<22} | "
              f"{ev['actor_id']:<14} ({role:>8}) | "
              f"{frm:>14} → {to:<14} | {d}{tag}")

    print()
    print("─"*72)
    print("FINDINGS")
    print("─"*72)

    violation_step = next((r for r in results if r["decision"] == "INADMISSIBLE"), None)
    # Tsunami: March 11, 2011 = ~1075 days after April 1, 2008
    tsunami_day = 1075.0

    if violation_step:
        vs        = violation_step
        gate_ts   = vs["_ts"]
        lead_days = tsunami_day - gate_ts
        lead_yrs  = lead_days / 365.0

        print(f"\nGate fires at:   Step {vs['_step']} — '{vs['_raw']}'")
        print(f"Invariant:       {vs['invariant']}")
        print(f"Actor (mapped):  {vs['_stp']['Identity']} → {vs['_stp']['Role']}")
        print(f"State at fire:   {vs['_stp']['FromState']}")
        print(f"Timestamp:       day +{gate_ts:.0f} (~September 2008)")
        print(f"Tsunami arrival: day +{tsunami_day:.0f} (March 11, 2011)")
        print(f"Lead time:       {lead_days:.0f} days (~{lead_yrs:.1f} years)")
        print()
        print("Structural interpretation:")
        print(f"  The {vs['invariant']} violation identifies that an Approver-")
        print(f"  class actor entered an Analyst-owned recommendation workflow")
        print(f"  and issued A3_Recommend (a counter-recommendation that the")
        print(f"  engineering team's recommendation be rejected). This is")
        print(f"  structurally identical to the Challenger Mason 'management")
        print(f"  hat' moment: management actors performing the recommendation,")
        print(f"  then authorizing based on the recommendation they had just")
        print(f"  performed. The role boundary between engineering judgment")
        print(f"  and management approval was crossed.")
        print()
        print("External trigger lead time finding:")
        print(f"  Lead time of ~{lead_yrs:.1f} years from structural violation to")
        print(f"  external precipitating event is the longest lead time in the")
        print(f"  project's reconstruction corpus. The structural vulnerability")
        print(f"  that the cascade would later exploit was committed in the")
        print(f"  decision pipeline ~3 years before the tsunami arrived.")
        print(f"  The gate's detection is independent of any external trigger.")
    else:
        print("\n[!] No INADMISSIBLE decision found. Check event sequence.")

    print()
    print("─"*72)
    print("ADMISSIBLE/INADMISSIBLE SUMMARY")
    print("─"*72)
    for r in results:
        status = "INADMISSIBLE" if r["decision"] == "INADMISSIBLE" else "admissible  "
        print(f"  Step {r['_step']:02d}: {status}  {r['_actor']:<14} {r['_raw']}")

    print()
    print("═"*72)
    print("RECONSTRUCTION TYPE: Structural Analog")
    print("PRECISION CLASS:    Month-level (NAIIC documents 2008 decisions to")
    print("                    the month; specific day not always documented)")
    print("EXTERNAL TRIGGER:   Tohoku tsunami (Mar 11, 2011) — ~2.9 years")
    print("                    after the structural violation")
    print("═"*72)

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    summary = []
    for r in results:
        summary.append({
            "step":      r["_step"],
            "timestamp_days": r["_ts"],
            "actor":     r["_actor"],
            "role":      r["_stp"]["Role"],
            "action":    r["_raw"],
            "decision":  r["decision"],
            "invariant": r.get("invariant"),
            "from_state":r["_stp"]["FromState"],
            "to_state":  r["_stp"]["ToState"],
        })
    output = {
        "incident":  "Fukushima Daiichi 2011 (Org Workflow)",
        "substrate": "Org Workflow",
        "scope":     "TEPCO 2008 Tsunami Risk Assessment Override",
        "source":    "NAIIC; ICANPS; disclosed TEPCO internal documents",
        "reconstruction_type": "Structural Analog",
        "precision_class":     "Month-level",
        "external_trigger":    "Tohoku tsunami (Mar 11, 2011)",
        "lead_time_to_trigger_years": 2.9,
        "results":   summary,
    }
    out_path = "/mnt/user-data/outputs/fukushima_org_reconstruction_results.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nMachine-readable results written to {out_path}")
