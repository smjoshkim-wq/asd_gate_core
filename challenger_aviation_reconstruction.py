"""
Inverse Incident Reconstruction — Challenger (Aviation Substrate)
═════════════════════════════════════════════════════════════════════
Reconstruction type: SUBSTRATE-SPECIFICITY TEST
Compiler:           aviation_compiler_v0_1.py
Substrate scope:    launch sequence as flight phase analog (T-minus
                    countdown → liftoff → ascent → vehicle disintegration)

Source authority:
    Presidential Commission on the Space Shuttle Challenger Accident
        (Rogers Commission Report), June 6, 1986
    NASA Mission Control / KSC launch sequence transcripts
    STS-51-L Air-to-Ground (A/G) and Operational Recorder data

Reconstruction scope:
    This reconstructs the formal launch sequence of STS-51-L from
    final hold (T-9 minutes) through ascent and disintegration. It
    maps each phase of the launch onto the aviation compiler's flight
    state geometry (PREFLIGHT → TAXIING → RUNWAY_HOLD → TAKEOFF_CLEARED
    → AIRBORNE) and runs the sequence through the gate.

    The reconstruction tests whether the aviation substrate fires on
    Challenger. The hypothesis: it does NOT. The structural failure
    at Challenger was the decision to launch outside the qualified
    envelope (org workflow / nuclear substrates). Once the launch
    decision was committed, the launch sequence itself ran structurally
    compliantly. The crew followed standard procedures. Mission Control
    issued standard "Go for launch" calls. The vehicle initiated
    ascent under documented authorization.

    The structural failure was upstream of the launch — not in the
    sequence of actions executed during launch.

Primary structural claim being tested:
    Substrate-specificity. The gate fires on the substrate where the
    structural geometry was violated. The aviation substrate captures
    flight-phase sequencing. The Challenger flight-phase sequencing
    was structurally compliant. The gate should NOT fire.

    If this hypothesis holds, it is a positive finding for the
    substrate-specificity claim — the gate is not a generic
    "something went wrong" detector. It identifies WHERE the
    structural violation occurred.

Timeline (EST) — source: Rogers Commission Vol. III; STS-51-L A/G:
    Jan 28, ~05:00  Final crew prep, suit-up
    Jan 28, ~08:30  Crew ingress to vehicle
    Jan 28, 11:29   Final hold cleared (T-9 min)
    Jan 28, 11:33   T-5 min — APU start, vehicle on internal power
    Jan 28, 11:38:00 SRB ignition, liftoff (T-0)
    Jan 28, 11:38:07 Roll program initiated (T+7s)
    Jan 28, 11:38:17 Roll program complete (T+17s)
    Jan 28, 11:38:30 First flash from joint (T+30s, post-incident analysis)
    Jan 28, 11:38:58 "Max Q throttle up" call (T+58s)
    Jan 28, 11:38:59 Scobee acknowledges: "Roger, go at throttle up" (T+59s)
    Jan 28, 11:39:13 Vehicle disintegration (T+73s)
"""

import sys
import json
sys.path.insert(0, ".")

from aviation_compiler_v0_1 import AviationCompiler
from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Reconstructed launch sequence
# ═══════════════════════════════════════════════════════════════════════
# Mapping:
#   captain_alpha → Commander Francis "Dick" Scobee
#   fo_alpha      → Pilot Michael Smith
#   atc_tenerife  → Mission Control (CAPCOM analog)

T = 0.0  # 11:29 EST Jan 28 — final hold cleared

CHALLENGER_LAUNCH_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: Pre-launch preparation
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "captain_alpha",
        "action":    "monitor_systems",
        "flight_id": "STS_51L",
        "timestamp": T + 0.0,
        "_note": "11:29 EST. Commander Scobee monitoring vehicle systems "
                 "during final hold. IDLE → PREFLIGHT via AV1. ADMISSIBLE.",
    },
    {
        "actor_id":  "captain_alpha",
        "action":    "read_checklist",
        "flight_id": "STS_51L",
        "timestamp": T + 100.0,
        "_note": "Final pre-launch checklist execution. Loop in PREFLIGHT. "
                 "ADMISSIBLE.",
    },
    {
        "actor_id":  "captain_alpha",
        "action":    "check_instruments",
        "flight_id": "STS_51L",
        "timestamp": T + 200.0,
        "_note": "11:33 EST — T-5 min. APU start, vehicle on internal "
                 "power. Crew verifies instruments. Loop in PREFLIGHT. "
                 "ADMISSIBLE.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: Launch clearance and ignition sequence
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "captain_alpha",
        "action":    "receive_ife_clearance",
        "flight_id": "STS_51L",
        "timestamp": T + 300.0,
        "_note": "Mission Control issues launch clearance equivalent. "
                 "PREFLIGHT → TAXIING via AV4_Pivot. ADMISSIBLE. "
                 "(Aviation analog: Shuttle launch was structurally "
                 "authorized through the standard Launch Director chain.)",
    },
    {
        "actor_id":  "captain_alpha",
        "action":    "receive_luaw_clearance",
        "flight_id": "STS_51L",
        "timestamp": T + 400.0,
        "_note": "Vehicle armed; SRB armed signal. TAXIING → RUNWAY_HOLD "
                 "via AV4_Pivot. ADMISSIBLE.",
    },
    {
        "actor_id":  "captain_alpha",
        "action":    "receive_takeoff_clearance",
        "flight_id": "STS_51L",
        "timestamp": T + 500.0,
        "_note": "Final 'Go for launch' from Launch Director. "
                 "RUNWAY_HOLD → TAKEOFF_CLEARED via AV4_Pivot. "
                 "ADMISSIBLE. The launch was structurally cleared "
                 "under all in-force documented procedures.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 3: Launch execution — admissible
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "captain_alpha",
        "action":    "initiate_takeoff_roll",
        "flight_id": "STS_51L",
        "timestamp": T + 540.0,
        "_note": "11:38:00 EST — T-0. SRB ignition, liftoff. "
                 "TAKEOFF_CLEARED → AIRBORNE via AV2_Expand. ADMISSIBLE. "
                 "The physical action of initiating ascent was "
                 "structurally permitted at the moment it occurred.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 4: Ascent — vehicle disintegrates at T+73s
    # No further admissible action by crew; disintegration is
    # not modeled as an event in the compiler vocabulary.
    # ──────────────────────────────────────────────────────────
]

# ═══════════════════════════════════════════════════════════════════════
# Run the reconstruction
# ═══════════════════════════════════════════════════════════════════════

def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — CHALLENGER (AVIATION)")
    print("Reconstruction type: SUBSTRATE-SPECIFICITY TEST")
    print("Source: Rogers Commission Vol. III; STS-51-L A/G transcripts")
    print("═"*70)
    print()

    compiler = AviationCompiler()
    results  = []
    for i, ev in enumerate(CHALLENGER_LAUNCH_EVENTS):
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<28} | "
              f"{frm or '—':>18} → {to:<18} | {d}{tag}")
    print()

    # ── Findings ──
    violation = next((r for r in results if r["decision"] == "INADMISSIBLE"), None)

    print("═"*70)
    print("AVIATION SUBSTRATE FINDINGS")
    print("═"*70)

    if violation:
        print(f"\n[!] Gate fires unexpectedly at Step {violation['_step']}.")
        print(f"    Invariant: {violation['invariant']}")
        print(f"    Substrate-specificity hypothesis: refuted.")
        print(f"    The aviation substrate fires on Challenger.")
    else:
        print("\nGate does NOT fire on the Challenger launch sequence.")
        print()
        print("This is the substrate-specificity finding:")
        print("─"*70)
        print("The aviation substrate captures flight-phase sequencing.")
        print("The Challenger flight-phase sequencing was structurally")
        print("compliant. Mission Control issued standard clearances,")
        print("the crew followed standard procedures, the vehicle")
        print("initiated ascent under documented authorization.")
        print()
        print("The structural failure was upstream of the launch — in")
        print("the LCC waiver decision (nuclear substrate) and the")
        print("management override of engineering recommendation")
        print("(org workflow substrate).")
        print()
        print("The aviation gate is not a generic 'something went wrong'")
        print("detector. It does not fire on Challenger because the")
        print("failure geometry was not on this substrate. This is")
        print("substrate-specificity in operation: the gate fires WHERE")
        print("the structural violation occurred, not on a chaotic spread")
        print("across all substrates of a catastrophe.")
        print()
        print("This is a positive finding for the substrate-invariance")
        print("claim. If the gate fired on every compiler regardless of")
        print("substrate, the framework would be detecting noise. It")
        print("does not. It detects geometry.")

    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: substrate-specificity test complete")
    print(f"Result: gate does {'NOT ' if not violation else ''}fire on launch sequence")
    print("═"*70)

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    summary = []
    for r in results:
        summary.append({
            "step":       r["_step"],
            "timestamp":  r["_ts"],
            "action":     r["_raw"],
            "decision":   r["decision"],
            "invariant":  r.get("invariant"),
            "from_state": r["_stp"]["FromState"],
            "to_state":   r["_stp"]["ToState"],
        })
    with open("/home/claude/challenger/challenger_aviation_reconstruction_results.json", "w") as f:
        json.dump({
            "incident": "Challenger STS-51-L — Launch Sequence",
            "source":   "Rogers Commission Vol. III; STS-51-L A/G transcripts",
            "compiler": "aviation_compiler_v0_1",
            "reconstruction_type": "Substrate-specificity test",
            "events":   summary,
        }, f, indent=2)
    print("\nMachine-readable results: challenger_aviation_reconstruction_results.json")
