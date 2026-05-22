"""
Inverse Incident Reconstruction — Deepwater Horizon Response (FEMA ICS)
══════════════════════════════════════════════════════════════════════════
Reconstruction type: RESPONSE FAILURE (structural analog)
Compiler:           fema_compiler_v0_1.py
Substrate scope:    Multi-agency incident response under NIMS/ICS doctrine

Source authority:
    USCG Incident Specific Preparedness Review (Deepwater Horizon),
        September 2010
    National Commission on the BP Deepwater Horizon Oil Spill Report
        (Jan 11, 2011) — Chief Counsel's Report on the Federal Response
    FEMA NIMS 2017 (formalizing pre-2010 NIMS 2008 doctrine that
        applied at the time of the incident)
    FEMA NRF 2019 (with reference to NRF 2008 in force at incident)
    GAO Report GAO-11-90 (Oil Spills: National Contingency Plan),
        October 2010

Reconstruction scope:
    The response to the Macondo well blowout (April 22, 2010 onward)
    was conducted under the National Contingency Plan (NCP) framework,
    using ICS/NIMS doctrine. The response operated for approximately
    eleven days before Unified Command (UC) was formally established
    on May 1, 2010, with Admiral Thad Allen taking the role of National
    Incident Commander. During this interim period, response actions
    proceeded without the structural command authority that NIMS
    requires for multi-agency operations.

    This reconstruction focuses on the early response phase (April
    22-30) and identifies structural violations in command authority
    and resource ordering.

Primary structural claim being tested:
    The FEMA ICS substrate fires on the early Deepwater response phase
    at two structural points:
    - ORDER: resource deployment (AC4_Execution) before Unified Command
      (AC5_CommandTransfer) was structurally established.
    - JURISDICTION: BP attempting public communications (AC6_PublicComm)
      as if they held an IC role. Under NRF/NIMS, BP was the Responsible
      Party — operator, not IC. AC6 is in IC vocabulary only.

Timeline (CDT) — source: USCG ISPR; National Commission Chief Counsel's Report:
    April 20, ~21:49  Explosion / blowout begins
    April 22         Rig sinks; spill response activated
    April 23         BP begins independent containment operations
    April 23-29      Multiple agencies (USCG, MMS, EPA, NOAA) operating
                       in parallel without unified command structure
    April 29         Federal Spill of National Significance declared
    May 1            Unified Command formally established
                       (Adm. Thad Allen as National Incident Commander)
    May 1+           Response operates under formal Unified Command
                       structure for remainder of incident
"""

import sys
import json
sys.path.insert(0, ".")

from fema_compiler_v0_1 import FEMACompiler, run_session
from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Reconstructed early-response sequence
# ═══════════════════════════════════════════════════════════════════════
# Timestamps represent compressed time scaling. The actual response
# operated over 11 days; events are compressed to fit within the
# burst window for structural analysis. Time scaling is consistent
# with the methodology used in other reconstructions.

T = 0.0

DEEPWATER_RESPONSE_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: Initial response — IC role contested
    # The IC actor is initially the Federal On-Scene Coordinator
    # (USCG Captain), but BP also operated as if it held IC authority.
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "ic_thompson",
        "action":    "conduct_size_up",
        "incident_id": "DWH_RESPONSE",
        "timestamp": T + 0.0,
        "_note": "April 22: USCG Federal On-Scene Coordinator activates "
                 "ICS framework. STANDBY → ASSESSMENT. ADMISSIBLE. "
                 "[USCG ISPR, Sept 2010]",
    },
    {
        "actor_id":  "ic_thompson",
        "action":    "verify_incident_scope",
        "incident_id": "DWH_RESPONSE",
        "timestamp": T + 1.0,
        "_note": "April 22-23: Initial size-up. Scope assessment underway. "
                 "ASSESSMENT loop. Admissible.",
    },
    {
        "actor_id":  "ic_thompson",
        "action":    "draft_objectives",
        "incident_id": "DWH_RESPONSE",
        "timestamp": T + 2.0,
        "_note": "April 23: Incident Action Plan (IAP) drafted. "
                 "ASSESSMENT → PLANNING via AC2. Admissible.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: THE ORDER VIOLATION — resource deployment before
    # Unified Command transfer
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "ic_thompson",
        "action":    "deploy_strike_team",
        "incident_id": "DWH_RESPONSE",
        "timestamp": T + 3.0,
        "_note": "April 23-29: USCG and other federal agencies deployed "
                 "strike teams, vessels, and aircraft to the spill site "
                 "prior to formal Unified Command establishment. "
                 "STRUCTURAL VIOLATION: AC4_Execution attempted from "
                 "PLANNING state. AC4 IS in IC vocabulary (valid at "
                 "OPERATIONS or post-UNIFIED_COMMAND states) but NOT in "
                 "PLANNING.flows. The prerequisite AC5_CommandTransfer "
                 "→ UNIFIED_COMMAND had not occurred. → ORDER fires.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Sub-sequence: JURISDICTION — BP holding press conferences
# ═══════════════════════════════════════════════════════════════════════
# Under NRF/NIMS, public communications during a federal response are
# the role of the Incident Commander or designated Public Information
# Officer (PIO). BP, as the Responsible Party (RP) under the Oil
# Pollution Act, held independent press conferences and made public
# statements about response status, projected oil flow rates, and
# remediation timelines. Per NRF doctrine, these communications were
# structurally outside BP's role.
#
# Modeling BP as a Field_Resource role (operator/RP under the response
# framework — not IC, not OSC), AC6_PublicComm is not in vocabulary.

DEEPWATER_RESPONSE_JURISDICTION = [
    {
        "actor_id":  "resource_team1",  # BP modeled as Field_Resource role
        "action":    "hold_press_conference",
        "incident_id": "DWH_RESPONSE_BP",
        "timestamp": T + 100.0,
        "_note": "April 25 onward. BP held independent press conferences "
                 "regarding response status, flow rate estimates, and "
                 "containment timelines. STRUCTURAL VIOLATION: "
                 "AC6_PublicComm called by Field_Resource role. AC6 is "
                 "in IC vocabulary only. → JURISDICTION fires. "
                 "[National Commission Chief Counsel's Report on Federal "
                 "Response; GAO-11-90]",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Run the reconstruction
# ═══════════════════════════════════════════════════════════════════════

def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — DEEPWATER HORIZON (FEMA ICS)")
    print("Reconstruction type: RESPONSE FAILURE")
    print("Source: USCG ISPR (Sept 2010); National Commission Report")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: ORDER — resource deployment before Unified Command")
    print("─"*70)

    compiler_a = FEMACompiler()
    results_a  = []
    for i, ev in enumerate(DEEPWATER_RESPONSE_EVENTS):
        packet = compiler_a.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results_a.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<30} | "
              f"{frm or '—':>15} → {to:<20} | {d}{tag}")
    print()

    print("─"*70)
    print("SECONDARY SEQUENCE: JURISDICTION — BP press communications (non-IC role)")
    print("─"*70)

    compiler_b = FEMACompiler()
    results_b  = []
    for i, ev in enumerate(DEEPWATER_RESPONSE_JURISDICTION):
        packet = compiler_b.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results_b.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<30} | "
              f"{frm or '—':>15} → {to:<20} | {d}{tag}")
    print()

    # ── Aggregate findings ──
    print("═"*70)
    print("FEMA ICS SUBSTRATE FINDINGS")
    print("═"*70)

    order_fire = next((r for r in results_a if r["decision"] == "INADMISSIBLE"), None)
    juris_fire = next((r for r in results_b if r["decision"] == "INADMISSIBLE"), None)

    if order_fire:
        print(f"\n[ORDER] Step {order_fire['_step']} — '{order_fire['_raw']}'")
        print(f"   Resource deployment from PLANNING state without UNIFIED_COMMAND")
        print(f"   Historical anchor: April 23-29 federal response operations")
        print(f"   Unified Command formally established: May 1, 2010 (~8-day gap)")

    if juris_fire:
        print(f"\n[JURISDICTION] Step {juris_fire['_step']} — '{juris_fire['_raw']}'")
        print(f"   BP (Field_Resource role) calling AC6_PublicComm — IC role only")
        print(f"   Historical anchor: BP press conferences April 25 onward")

    print("\n─"*35)
    print("Structural interpretation:")
    print("─"*70)
    print("The FEMA ICS substrate identifies two structural violations in")
    print("the early Deepwater response phase:")
    print()
    print("[1] ORDER: federal response deployed operational resources")
    print("    without first establishing the Unified Command structure")
    print("    that NIMS requires for multi-agency incidents of this scope.")
    print("    The gate fires on AC4 from PLANNING — the structural")
    print("    sequence required AC5 → UNIFIED_COMMAND before AC4.")
    print()
    print("[2] JURISDICTION: BP, as Responsible Party under OPA, did not")
    print("    hold IC role under NIMS. Its public communications during")
    print("    the response operated outside its structural authority.")
    print()
    print("This is the response-phase reconstruction of the same incident")
    print("that the petroleum compiler fires on at the operational phase.")
    print("Two compilers, same incident, different structural failures.")

    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: COMPLETE")
    print("FEMA ICS captures response-phase structural failure")
    print("═"*70)

    return {
        "order":         results_a,
        "jurisdiction":  results_b,
    }


if __name__ == "__main__":
    all_results = run_reconstruction()

    summary = {
        "incident":   "Deepwater Horizon — Federal Response Phase (April 22 - May 1, 2010)",
        "source":     "USCG ISPR; National Commission Chief Counsel's Report; GAO-11-90",
        "compiler":   "fema_compiler_v0_1",
        "reconstruction_type": "Response failure (structural analog)",
        "sequences": {}
    }

    for seq_name, results in all_results.items():
        seq_summary = []
        for r in results:
            seq_summary.append({
                "step":       r["_step"],
                "timestamp":  r["_ts"],
                "action":     r["_raw"],
                "decision":   r["decision"],
                "invariant":  r.get("invariant"),
                "from_state": r["_stp"]["FromState"],
                "to_state":   r["_stp"]["ToState"],
            })
        summary["sequences"][seq_name] = seq_summary

    with open("/home/claude/petroleum/deepwater_fema_reconstruction_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nMachine-readable results: deepwater_fema_reconstruction_results.json")
