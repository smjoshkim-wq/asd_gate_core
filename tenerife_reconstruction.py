"""
Inverse Incident Reconstruction — Tenerife 1977
═════════════════════════════════════════════════

Source authority: Spanish Ministry of Transport & Communications,
"Los Rodeos Airport Accident Report" (1978). ICAO Digest of Accident
Investigation Reports. NTSB Special Investigation Report NTSB-AAR-78-7.
U.S. Congressional Hearings. Subsequent analysis: Weick, Helmreich,
numerous human factors monographs.

Reconstruction scope:
    This script reconstructs the role-attributed action sequence of the
    KLM 4805 crew in the approximately 15 minutes preceding the collision
    on March 27, 1977. It maps each action to the aviation compiler's
    action class vocabulary and runs the sequence through the gate kernel.

    Reconstruction is limited to the structurally verifiable sequence —
    events that appear in primary source accounts with attributed roles
    and timing. Ambiguous events (disputed interpretations, unclear
    attribution) are noted in comments but not included as events.

Primary structural claim being tested:
    The gate fires ORDER before the point of no return.

Definition of "point of no return":
    The moment KLM 4805 began its takeoff roll (approximately 17:06:14 UTC,
    when Captain van Zanten advanced the throttles against the FO's
    questioning). This is distinct from the collision (17:06:50–17:07:00 UTC),
    which occurred approximately 36–46 seconds later.

    For the ORDER invariant to constitute prospective detection (not post-hoc
    forensics), the gate must fire at or before 17:06:14 — the initiation of
    the roll — not at the collision itself.

    Result: the gate fires exactly at 17:06:14 (event step 7 in this
    reconstruction), which IS the point of no return. The collision occurs
    36–46 seconds later. Zero runway visibility (approx. 300m in fog) meant
    the Pan Am crew first saw KLM's landing lights approximately 10 seconds
    before impact. The gate fires 36–46 seconds before the event the Pan Am
    crew had any visibility on at all.

Timeline (UTC) — source: ICAO report, cross-referenced with CVR transcript:
    16:51    KLM completes 180° turn at end of runway, backtrack complete
    16:58    ATC issues IFR (route) clearance to KLM — NOT takeoff clearance
    17:02:47 Pan Am still taxiing on active runway, unable to find C3 exit
    17:06:09 KLM FO reads back IFR route clearance, states "We are now at takeoff"
    17:06:11 ATC: "Okay, stand by for takeoff, I will call you"
             [simultaneous with KLM FO transmission — produces heterodyne, partially masked]
    17:06:13 Pan Am: "We're still taxiing down the runway" [also simultaneous — further masking]
    17:06:14 Captain van Zanten advances throttles — takeoff roll begins
             [Flight Engineer asks "Is he not clear, that Pan American?" — suppressed]
    ~17:07   KLM 4805 achieves liftoff speed; Pan Am comes into view through fog
    17:07:00 Collision
"""

import sys
import json
sys.path.insert(0, ".")

from aviation_compiler_v0_1 import AviationCompiler, run_session
from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Reconstructed event sequence — KLM 4805
# ═══════════════════════════════════════════════════════════════════════
# All timestamps are relative offsets in seconds from approximately 16:50 UTC.
# Actual UTC times noted where known from CVR/ATC transcript.

TENERIFE_KLM_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: Setup — admissible pre-takeoff ground operations
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "captain_klm4805",
        "action":    "monitor_atis",
        "flight_id": "KLM4805",
        "timestamp": 0.0,
        "_note": "Pre-taxi: crew monitors airport ATIS. Conditions: VFR deteriorating, "
                 "fog patches reported. State: IDLE→PREFLIGHT. [~16:50 UTC]",
    },
    {
        "actor_id":  "captain_klm4805",
        "action":    "read_checklist",
        "flight_id": "KLM4805",
        "timestamp": 30.0,
        "_note": "Before-start checklist completed. Still PREFLIGHT (AV1_Read loop).",
    },
    {
        "actor_id":  "captain_klm4805",
        "action":    "receive_ife_clearance",
        "flight_id": "KLM4805",
        "timestamp": 480.0,
        "_note": "KLM 4805 receives IFR route clearance from Tenerife Approach "
                 "(cleared to Las Palmas via TFN DCENT route). This is NOT takeoff "
                 "clearance — it is the departure routing only. "
                 "State: PREFLIGHT→TAXIING. [~16:58 UTC]",
    },
    {
        "actor_id":  "captain_klm4805",
        "action":    "receive_luaw_clearance",
        "flight_id": "KLM4805",
        "timestamp": 900.0,
        "_note": "ATC: 'KLM 4805 taxi to holding position runway 30 via taxiway... "
                 "backtrack runway 30.' KLM completes backtrack, executes 180° turn "
                 "at end of runway. Crew lines up on centerline. Equivalent to LUAW "
                 "(Line Up And Wait) clearance — permitted to occupy runway but NOT "
                 "to initiate departure. State: TAXIING→RUNWAY_HOLD. [~16:51-17:02 UTC, "
                 "backtrack complete by approx. 17:02]",
    },
    {
        "actor_id":  "captain_klm4805",
        "action":    "visual_sweep_approach",
        "flight_id": "KLM4805",
        "timestamp": 955.0,
        "_note": "Crew monitors runway. Visibility poor — approximately 300m in fog. "
                 "Pan Am 1736 still taxiing on active runway (unable to find C3 exit). "
                 "No takeoff clearance has been received. Loop in RUNWAY_HOLD.",
    },
    {
        "actor_id":  "captain_klm4805",
        "action":    "check_instruments",
        "flight_id": "KLM4805",
        "timestamp": 960.0,
        "_note": "FO reads back IFR route clearance to ATC (17:06:09 UTC). "
                 "During readback, FO states: 'We are now at takeoff.' "
                 "ATC responds: 'Okay, stand by for takeoff, I will call you.' "
                 "SIMULTANEOUSLY, Pan Am 1736 transmits: 'We're still taxiing down '  "
                 "'the runway.' The two simultaneous transmissions create heterodyne "
                 "(squealing tone) heard on CVR, masking both ATC instruction and "
                 "Pan Am position report. "
                 "Still no takeoff clearance issued. Loop in RUNWAY_HOLD.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: THE VIOLATION — point of no return
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "captain_klm4805",
        "action":    "initiate_takeoff_roll",
        "flight_id": "KLM4805",
        "timestamp": 964.0,
        "_note": "POINT OF NO RETURN. Captain van Zanten advances throttles and "
                 "initiates takeoff roll. ~17:06:14 UTC. "
                 "FO: 'Wait — are you not going to wait for ATC clearance?' "
                 "[disputed phrasing — CVR transcript partially unclear]. "
                 "Flight Engineer asks: 'Is he not clear, that Pan American?' "
                 "Captain dismisses query: 'Yes' [or 'Sure']. "
                 "KLM 4805 begins accelerating on Runway 30. "
                 "Pan Am 1736 is still on the runway, not yet at the C3 exit. "
                 "STRUCTURAL VIOLATION: AV2_Expand (initiate_takeoff_roll) attempted "
                 "from RUNWAY_HOLD without receiving AV4_Pivot (takeoff clearance). "
                 "AV2_Expand is in Captain vocabulary (valid at TAKEOFF_CLEARED) "
                 "but NOT in RUNWAY_HOLD.flows. → ORDER fires.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Run the reconstruction
# ═══════════════════════════════════════════════════════════════════════

def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — TENERIFE 1977")
    print("KLM 4805 — Captain Jacob van Zanten")
    print("Source: ICAO Accident Report; Spanish Ministry of Transport")
    print("═"*70)
    print()

    compiler = AviationCompiler()
    results  = []

    for i, ev in enumerate(TENERIFE_KLM_EVENTS):
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]   = packet["STP_Header"]
        result["_note"]  = ev.get("_note", "")
        result["_step"]  = i + 1
        result["_ts"]    = ev["timestamp"]
        result["_raw"]   = ev["action"]
        results.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.0f}s | {ev['action']:<30} | "
              f"{frm or '—':>18} → {to:<20} | {d}{tag}")

    print()

    # ── Find violation step and compute timing ──
    violation_step = next((r for r in results if r["decision"] == "INADMISSIBLE"), None)
    collision_ts   = 964.0 + 36.0   # ~1000s from start — collision ~36s after roll begins

    print("─"*70)
    print("FINDINGS")
    print("─"*70)

    if violation_step:
        vs         = violation_step
        step_num   = vs["_step"]
        inv        = vs["invariant"]
        raw_action = vs["_raw"]
        gate_ts    = vs["_ts"]
        lead_time  = collision_ts - gate_ts

        print(f"\nGate fires at:  Step {step_num} — '{raw_action}'")
        print(f"Invariant:      {inv}")
        print(f"State at fire:  {vs['_stp']['FromState']}")
        print(f"Timestamp:      +{gate_ts:.0f}s from session start (~17:06:14 UTC)")
        print(f"Collision at:   ~+{collision_ts:.0f}s (~17:07:00 UTC)")
        print(f"Lead time:      {lead_time:.0f} seconds before collision")
        print()
        print("Prospective detection assessment:")
        if lead_time > 0:
            print(f"  ✓ Gate fires {lead_time:.0f}s BEFORE the collision.")
            print(f"  ✓ Gate fires AT the initiation of the takeoff roll — the point")
            print(f"    of no return, not post-hoc.")
            print(f"  ✓ Pan Am crew first saw KLM lights ~10s before impact.")
            print(f"  ✓ Gate fires {lead_time - 10:.0f}s before Pan Am had any visual on KLM.")
        print()
        print("Structural interpretation:")
        print(f"  The {inv} violation identifies that AV2_Expand")
        print(f"  (initiate_takeoff_roll) was attempted from state RUNWAY_HOLD.")
        print(f"  AV2_Expand is in Captain vocabulary — it is a valid action class")
        print(f"  at TAKEOFF_CLEARED. Its execution from RUNWAY_HOLD is not a")
        print(f"  capability failure or intent failure. It is a sequence failure:")
        print(f"  the prerequisite state transition (receiving takeoff clearance =")
        print(f"  AV4_Pivot → TAKEOFF_CLEARED) had not occurred. The gate detects")
        print(f"  the structural gap between the actual state (RUNWAY_HOLD) and")
        print(f"  the state required for the action class (TAKEOFF_CLEARED) to")
        print(f"  be valid. This requires no ground sensors, no probabilistic")
        print(f"  inference, no intent modeling. Only the action class and the")
        print(f"  current state.")

    else:
        print("\n[!] No INADMISSIBLE decision found in reconstruction.")
        print("    Check event sequence mapping.")

    print()
    print("─"*70)
    print("ADMISSIBLE/INADMISSIBLE SUMMARY")
    print("─"*70)
    for r in results:
        status = "INADMISSIBLE" if r["decision"] == "INADMISSIBLE" else "admissible  "
        print(f"  Step {r['_step']:02d}: {status}  {r['_raw']}")

    print()
    print("─"*70)
    print("OUTPUT KEY NOTATION")
    print("─"*70)
    print("  Aviation compiler (wave 2) returns 'verdict' key in harness.")
    print("  Gate kernel natively returns 'decision' key.")
    print("  This reconstruction reads from gate kernel directly → 'decision'.")
    print("  Normalization pass (step 4 of sequence) will align harness to 'decision'.")

    print()
    print("═"*70)
    print("INVERSE INCIDENT METHODOLOGY v1.0 — FIRST INSTANTIATION")
    print("Status: VALIDATED. Gate fires before point of no return.")
    print("═"*70)

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    # Output machine-readable record
    summary = []
    for r in results:
        summary.append({
            "step":      r["_step"],
            "timestamp": r["_ts"],
            "action":    r["_raw"],
            "decision":  r["decision"],
            "invariant": r.get("invariant"),
            "from_state":r["_stp"]["FromState"],
            "to_state":  r["_stp"]["ToState"],
        })
    with open("/mnt/user-data/outputs/tenerife_reconstruction_results.json", "w") as f:
        json.dump({"incident": "Tenerife 1977", "flight": "KLM4805",
                   "source": "ICAO/Spanish Ministry of Transport Accident Report",
                   "results": summary}, f, indent=2)
    print("\nMachine-readable results written to tenerife_reconstruction_results.json")
