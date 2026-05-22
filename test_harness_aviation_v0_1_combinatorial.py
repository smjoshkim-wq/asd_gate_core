"""
Combinatorial Test Harness — Aviation Compiler v0.1
════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:         Captain initiates takeoff roll from RUNWAY_HOLD state
                       without receiving takeoff clearance (Tenerife structural analog)
  A02 — JURISDICTION:  FlightEngineer attempts AV2_Expand (physical control action —
                       not in FE vocabulary anywhere)
  A03 — BURST_CADENCE: Captain oscillates TAXIING(w=2)↔RUNWAY_HOLD(w=3) rapidly —
                       ATC repeatedly issues then cancels LUAW clearances
  A04 — EXIT:          Second Captain presents on flight_id already bound to first Captain

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean traversal PREFLIGHT→TAXIING→RUNWAY_HOLD→TAKEOFF_CLEARED,
                          no HYSTERESIS fires
  B02 — ORDER → HYSTERESIS: ORDER fires (takeoff without clearance), then Captain expands
                             to AIRBORNE (unvisited)
  B03 — JURISDICTION → HYSTERESIS: JURISDICTION fires (FE attempts expand), then FE
                                   expands to unvisited state

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST_CADENCE in same session
  C02 — JURISDICTION then ORDER, same actor (ATC_Tower role: AV2 excluded, then ORDER)
  C03 — EXIT then JURISDICTION, separate actors, independent flight contexts

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")

from aviation_compiler_v0_1 import run_session, AviationCompiler

BASE_TS = 2_000_000.0


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def gate_result(events):
    results = run_session(events)
    return [(r["verdict"], r.get("invariant", None)) for r in results]


def assert_pass(test_id, description, results, expected_verdict,
                expected_invariant, at_step):
    v, inv = results[at_step]
    ok = (v == expected_verdict and
          (expected_invariant is None or inv == expected_invariant))
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} {test_id}: {description}")
    print(f"       step {at_step+1}: verdict={v}, invariant={inv}")
    if not ok:
        print(f"       EXPECTED: verdict={expected_verdict}, invariant={expected_invariant}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01():
    """
    ORDER — Tenerife structural reconstruction.
    Captain navigates to RUNWAY_HOLD via correct sequence.
    At RUNWAY_HOLD: AV4_Pivot (takeoff clearance) has NOT been received.
    Captain calls AV2_Expand (initiate_takeoff_roll) — in Captain vocabulary,
    not in RUNWAY_HOLD.flows → ORDER at step 4.
    """
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_A01", "timestamp": BASE_TS + 0},      # IDLE→PREFLIGHT
        {"actor_id": "captain_alpha", "action": "receive_ife_clearance",
         "flight_id": "FL_A01", "timestamp": BASE_TS + 1},      # PREFLIGHT→TAXIING
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_A01", "timestamp": BASE_TS + 2},      # TAXIING→RUNWAY_HOLD
        # At RUNWAY_HOLD — NO takeoff clearance received yet
        # Captain initiates takeoff: AV2_Expand in role, NOT in RUNWAY_HOLD.flows → ORDER
        {"actor_id": "captain_alpha", "action": "initiate_takeoff_roll",
         "flight_id": "FL_A01", "timestamp": BASE_TS + 3},
    ]
    results = gate_result(events)
    return assert_pass("A01", "ORDER: Captain initiates takeoff from RUNWAY_HOLD (Tenerife analog)",
                       results, "INADMISSIBLE", "ORDER", at_step=3)


def test_A02():
    """
    JURISDICTION — FlightEngineer attempts AV2_Expand.
    AV2_Expand (physical expansion action) is not in FlightEngineer vocabulary
    at any state — JURISDICTION at step 2.
    """
    events = [
        {"actor_id": "fe_klm4805", "action": "monitor_atis",
         "flight_id": "FL_A02", "timestamp": BASE_TS + 0},
        # FE attempts to start engines — AV2_Expand not in FE vocab → JURISDICTION
        {"actor_id": "fe_klm4805", "action": "start_engines",
         "flight_id": "FL_A02", "timestamp": BASE_TS + 1},
    ]
    results = gate_result(events)
    return assert_pass("A02", "JURISDICTION: FlightEngineer attempts AV2_Expand (start_engines)",
                       results, "INADMISSIBLE", "JURISDICTION", at_step=1)


def test_A03():
    """
    BURST_CADENCE — Captain oscillates TAXIING(w=2)↔RUNWAY_HOLD(w=3).
    AV4_Pivot (receive_luaw_clearance) expands TAXIING→RUNWAY_HOLD (2→3).
    AV3_Contract (return_to_taxiway) contracts RUNWAY_HOLD→TAXIING (3→2).
    Three width-expanding transitions within window → BURST.
    Each individual transition is admissible.
    """
    t = BASE_TS
    events = [
        {"actor_id": "captain_bravo", "action": "monitor_atis",
         "flight_id": "FL_A03", "timestamp": t + 0},    # IDLE→PREFLIGHT
        {"actor_id": "captain_bravo", "action": "receive_ife_clearance",
         "flight_id": "FL_A03", "timestamp": t + 1},    # PREFLIGHT→TAXIING
        # Oscillate: TAXIING→RUNWAY_HOLD (expand) then RUNWAY_HOLD→TAXIING (contract)
        {"actor_id": "captain_bravo", "action": "receive_luaw_clearance",
         "flight_id": "FL_A03", "timestamp": t + 2},    # TAXIING→RUNWAY_HOLD (expand 1)
        {"actor_id": "captain_bravo", "action": "return_to_taxiway",
         "flight_id": "FL_A03", "timestamp": t + 3},    # RUNWAY_HOLD→TAXIING (contract)
        {"actor_id": "captain_bravo", "action": "receive_luaw_clearance",
         "flight_id": "FL_A03", "timestamp": t + 4},    # TAXIING→RUNWAY_HOLD (expand 2)
        {"actor_id": "captain_bravo", "action": "return_to_taxiway",
         "flight_id": "FL_A03", "timestamp": t + 5},    # RUNWAY_HOLD→TAXIING (contract)
        {"actor_id": "captain_bravo", "action": "receive_luaw_clearance",
         "flight_id": "FL_A03", "timestamp": t + 6},    # TAXIING→RUNWAY_HOLD (expand 3 → BURST)
    ]
    results = gate_result(events)
    burst_fired = any(v == "INADMISSIBLE" and i == "BURST_CADENCE" for v, i in results)
    fired_at = next((idx for idx, (v, i) in enumerate(results)
                     if v == "INADMISSIBLE" and i == "BURST_CADENCE"), None)
    status = "[PASS]" if burst_fired else "[FAIL]"
    print(f"{status} A03: BURST_CADENCE: Captain TAXIING↔RUNWAY_HOLD oscillation")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired


def test_A04():
    """
    EXIT — Second Captain presents on flight_id already bound to first Captain.
    Actor identity mismatch → EXIT at step 2.
    """
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_A04", "timestamp": BASE_TS + 0},
        # Different Captain presents on the same flight — EXIT
        {"actor_id": "captain_bravo", "action": "monitor_atis",
         "flight_id": "FL_A04", "timestamp": BASE_TS + 1},
    ]
    results = gate_result(events)
    return assert_pass("A04", "EXIT: captain_bravo presents on flight bound to captain_alpha",
                       results, "INADMISSIBLE", "EXIT", at_step=1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01():
    """
    Negative control — clean traversal PREFLIGHT→TAXIING→RUNWAY_HOLD→TAKEOFF_CLEARED.
    Three new states entered. No prior violation.
    HYSTERESIS must NOT fire.
    All steps ADMISSIBLE.
    """
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_B01", "timestamp": BASE_TS + 0},      # IDLE→PREFLIGHT
        {"actor_id": "captain_alpha", "action": "receive_ife_clearance",
         "flight_id": "FL_B01", "timestamp": BASE_TS + 1},      # PREFLIGHT→TAXIING
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_B01", "timestamp": BASE_TS + 2},      # TAXIING→RUNWAY_HOLD
        {"actor_id": "captain_alpha", "action": "receive_takeoff_clearance",
         "flight_id": "FL_B01", "timestamp": BASE_TS + 3},      # RUNWAY_HOLD→TAKEOFF_CLEARED
    ]
    results = gate_result(events)
    all_admissible = all(v == "ADMISSIBLE" for v, _ in results)
    no_hysteresis  = not any(i == "HYSTERESIS" for _, i in results)
    ok = all_admissible and no_hysteresis
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} B01: Negative control — clean traversal, no HYSTERESIS")
    print(f"       verdicts={[v for v,_ in results]}")
    return ok


def test_B02():
    """
    ORDER → HYSTERESIS:
    Step 4: ORDER fires — Captain initiates takeoff from RUNWAY_HOLD.
    State stays RUNWAY_HOLD. visited={PREFLIGHT, TAXIING, RUNWAY_HOLD}.
    Step 5: Captain loops in RUNWAY_HOLD (AV1_Read — admissible).
    Step 6: Captain receives takeoff clearance → TAKEOFF_CLEARED (unvisited).
            HYSTERESIS fires.
    """
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 0},
        {"actor_id": "captain_alpha", "action": "receive_ife_clearance",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 1},
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 2},
        # ORDER: initiate takeoff from RUNWAY_HOLD (no clearance)
        {"actor_id": "captain_alpha", "action": "initiate_takeoff_roll",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 3},
        # Loop in RUNWAY_HOLD (admissible)
        {"actor_id": "captain_alpha", "action": "visual_sweep_approach",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 4},
        # Expand to TAKEOFF_CLEARED (unvisited after violation) → HYSTERESIS
        {"actor_id": "captain_alpha", "action": "receive_takeoff_clearance",
         "flight_id": "FL_B02", "timestamp": BASE_TS + 5},
    ]
    results = gate_result(events)
    order_at_3 = results[3][0] == "INADMISSIBLE" and results[3][1] == "ORDER"
    hyst_at_5  = results[5][0] == "INADMISSIBLE" and results[5][1] == "HYSTERESIS"
    ok = order_at_3 and hyst_at_5
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} B02: ORDER → HYSTERESIS")
    print(f"       step 4: {results[3]}, step 6: {results[5]}")
    return ok


def test_B03():
    """
    JURISDICTION → HYSTERESIS:
    Step 2: JURISDICTION fires — FlightEngineer attempts start_engines (AV2, not in FE vocab).
    visited={MONITORING}. State unchanged.
    Step 3: FE calls vhf_frequency_handoff (AV4_Pivot) → stays MONITORING (visited).
    HYSTERESIS does NOT fire (MONITORING already visited).
    Step 4: For HYSTERESIS, FE needs to call an action that leads to an UNVISITED state.
    FE's MONITORING.flows only has AV1→MONITORING and AV4→MONITORING loops.
    FE's GATE state (width=0) is reachable... but there's no direct action to GATE in FE flows.
    
    Use Captain role for B03 instead (cleaner unvisited state available):
    JURISDICTION fires (Captain calls AV5_Override — not in any role's vocab).
    Then Captain expands to unvisited AIRBORNE via TAKEOFF_CLEARED.
    
    Revised B03:
    Step 1: Captain reaches RUNWAY_HOLD cleanly.
    Step 2: JURISDICTION — Captain calls bypass_handshake_protocol (AV5_Override).
    visited={PREFLIGHT, TAXIING, RUNWAY_HOLD}.
    Step 3: Loop (RUNWAY_HOLD → RUNWAY_HOLD via AV1_Read, admissible).
    Step 4: Captain receives takeoff clearance (AV4_Pivot → TAKEOFF_CLEARED, unvisited).
            HYSTERESIS fires.
    """
    events = [
        {"actor_id": "captain_bravo", "action": "monitor_atis",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 0},
        {"actor_id": "captain_bravo", "action": "receive_ife_clearance",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 1},
        {"actor_id": "captain_bravo", "action": "receive_luaw_clearance",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 2},
        # JURISDICTION: Captain calls AV5_Override (not in ANY role's vocab)
        {"actor_id": "captain_bravo", "action": "bypass_handshake_protocol",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 3},
        # Loop in RUNWAY_HOLD (admissible)
        {"actor_id": "captain_bravo", "action": "visual_sweep_approach",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 4},
        # Expand to TAKEOFF_CLEARED (unvisited after JURISDICTION) → HYSTERESIS
        {"actor_id": "captain_bravo", "action": "receive_takeoff_clearance",
         "flight_id": "FL_B03", "timestamp": BASE_TS + 5},
    ]
    results = gate_result(events)
    juris_at_3 = results[3][0] == "INADMISSIBLE" and results[3][1] == "JURISDICTION"
    hyst_at_5  = results[5][0] == "INADMISSIBLE" and results[5][1] == "HYSTERESIS"
    ok = juris_at_1 = juris_at_3 and hyst_at_5
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} B03: JURISDICTION → HYSTERESIS")
    print(f"       step 4: {results[3]}, step 6: {results[5]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01():
    """
    ORDER then BURST_CADENCE in same session.
    ORDER fires at step 4 (initiate_takeoff_roll from RUNWAY_HOLD).
    Captain continues oscillating RUNWAY_HOLD↔TAXIING (still in visited territory).
    BURST fires. HYSTERESIS NOT produced (states already visited).
    """
    t = BASE_TS
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_C01", "timestamp": t + 0},
        {"actor_id": "captain_alpha", "action": "receive_ife_clearance",
         "flight_id": "FL_C01", "timestamp": t + 1},
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_C01", "timestamp": t + 2},
        # ORDER: takeoff from RUNWAY_HOLD (no clearance)
        {"actor_id": "captain_alpha", "action": "initiate_takeoff_roll",
         "flight_id": "FL_C01", "timestamp": t + 3},
        # Oscillate (all in visited territory) → BURST
        {"actor_id": "captain_alpha", "action": "return_to_taxiway",
         "flight_id": "FL_C01", "timestamp": t + 4},
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_C01", "timestamp": t + 5},
        {"actor_id": "captain_alpha", "action": "return_to_taxiway",
         "flight_id": "FL_C01", "timestamp": t + 6},
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_C01", "timestamp": t + 7},
    ]
    results = gate_result(events)
    order_fired = any(v == "INADMISSIBLE" and i == "ORDER"        for v, i in results)
    burst_fired = any(v == "INADMISSIBLE" and i == "BURST_CADENCE" for v, i in results)
    hyst_fired  = any(i == "HYSTERESIS"                           for _, i in results)
    ok = order_fired and burst_fired and not hyst_fired
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} C01: ORDER then BURST_CADENCE (no HYSTERESIS)")
    print(f"       ORDER={order_fired}, BURST={burst_fired}, HYSTERESIS={hyst_fired}")
    return ok


def test_C02():
    """
    JURISDICTION then ORDER, same actor (ATC_Tower role).
    Step 2: JURISDICTION — ATC_Tower calls start_engines (AV2_Expand not in ATC vocab).
    Step 3: ATC loops in MONITORING (admissible, AV1_Read).
    Step 4: ORDER — ATC_Tower calls AV2_Expand again from MONITORING.
            AV2 still not in ATC_Tower vocab → JURISDICTION again.
    
    Revised for clean ORDER: use Captain actor.
    JURISDICTION at step 2 (AV5_Override — bypass_handshake_protocol).
    Then reach a state where an in-vocab action is attempted out of sequence.
    Captain at RUNWAY_HOLD calls AV2_Expand again (ORDER — same as A01).
    Two sequential INADMISSIBLE on the same actor.
    """
    events = [
        {"actor_id": "captain_alpha", "action": "monitor_atis",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 0},
        {"actor_id": "captain_alpha", "action": "receive_ife_clearance",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 1},
        {"actor_id": "captain_alpha", "action": "receive_luaw_clearance",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 2},
        # JURISDICTION: AV5_Override not in any role's vocab
        {"actor_id": "captain_alpha", "action": "bypass_handshake_protocol",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 3},
        # Loop (admissible)
        {"actor_id": "captain_alpha", "action": "visual_sweep_approach",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 4},
        # ORDER: attempt takeoff from RUNWAY_HOLD (in role, wrong state)
        # Note: HYSTERESIS check fires first if TAKEOFF_CLEARED is unvisited.
        # Since RUNWAY_HOLD.flows doesn't have AV2 → ORDER check.
        # But after JURISDICTION, HYSTERESIS check: AV2_Expand from RUNWAY_HOLD →
        # next_state would be None (not in flows) → HYSTERESIS check returns False.
        # So ORDER fires correctly.
        {"actor_id": "captain_alpha", "action": "initiate_takeoff_roll",
         "flight_id": "FL_C02", "timestamp": BASE_TS + 5},
    ]
    results = gate_result(events)
    juris_fired = any(v == "INADMISSIBLE" and i == "JURISDICTION" for v, i in results)
    order_fired = any(v == "INADMISSIBLE" and i == "ORDER"        for v, i in results)
    ok = juris_fired and order_fired
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} C02: JURISDICTION then ORDER, sequential")
    print(f"       JURISDICTION={juris_fired}, ORDER={order_fired}")
    print(f"       verdicts={[(v,i) for v,i in results]}")
    return ok


def test_C03():
    """
    EXIT then JURISDICTION, separate actors, independent flight contexts.
    Step 2: EXIT — captain_bravo presents on FL_C03 bound to captain_alpha.
    Step 3: JURISDICTION — fe_klm4805 calls start_engines (AV2 not in FE vocab)
            on a different flight (FL_C03b). Per-actor state is independent.
    """
    compiler = AviationCompiler()

    r1 = compiler.compile({"actor_id": "captain_alpha", "action": "monitor_atis",
                            "flight_id": "FL_C03", "timestamp": BASE_TS + 0})
    # EXIT: captain_bravo presents on FL_C03 (bound to captain_alpha)
    r2 = compiler.compile({"actor_id": "captain_bravo", "action": "monitor_atis",
                            "flight_id": "FL_C03", "timestamp": BASE_TS + 1})
    # JURISDICTION: FE attempts physical action on separate flight
    r3 = compiler.compile({"actor_id": "fe_klm4805", "action": "start_engines",
                            "flight_id": "FL_C03b", "timestamp": BASE_TS + 2})

    exit_fired  = r2["verdict"] == "INADMISSIBLE" and r2.get("invariant") == "EXIT"
    juris_fired = r3["verdict"] == "INADMISSIBLE" and r3.get("invariant") == "JURISDICTION"
    ok = exit_fired and juris_fired
    status = "[PASS]" if ok else "[FAIL]"
    print(f"{status} C03: EXIT then JURISDICTION, independent actors/flights")
    print(f"       EXIT: {r2['verdict']}/{r2.get('invariant')}, "
          f"JURISDICTION: {r3['verdict']}/{r3.get('invariant')}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Main runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Aviation Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    print()

    tests = [
        ("Block A — Independent First-Fire",   [test_A01, test_A02, test_A03, test_A04]),
        ("Block B — Hysteresis Dependency",    [test_B01, test_B02, test_B03]),
        ("Block C — Cross-Invariant Compound", [test_C01, test_C02, test_C03]),
    ]

    total  = 0
    passed = 0

    for block_name, block_tests in tests:
        print(f"\n{block_name}")
        print("-" * 40)
        for t in block_tests:
            result = t()
            total  += 1
            passed += int(result)
            print()

    print("=" * 60)
    verdict = "ALL PASS" if passed == total else f"{total - passed} FAILED"
    print(f"Results: {passed}/{total} passed ✓ {verdict}")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
