"""
Combinatorial Test Harness — Petroleum Operations Compiler v0.1
══════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:         CompanyMan calls P5 (initiate_displacement) from
                       NEGATIVE_TEST state. P5 IS in CompanyMan vocabulary
                       (valid at BARRIER_VERIFIED) but NOT in NEGATIVE_TEST.flows.
                       Deepwater Horizon analog: displacement initiated before
                       barrier verification.
  A02 — JURISDICTION:  CompanyMan calls P6 (submit_displacement_clearance) —
                       P6 not in CompanyMan vocabulary anywhere. Operator
                       self-certifying a regulator gate. Deepwater Horizon
                       analog: BP filed MMS amended permit for displacement.
  A03 — BURST_CADENCE: OIM expands rapidly through well lifecycle states with
                       three width-expanding transitions (STANDBY→DRILLING [+1],
                       CEMENT_EVAL→NEGATIVE_TEST [+1], DISPLACING→EMERGENCY [+1])
                       within the 60-second burst window.
  A04 — EXIT:          Second CompanyMan presents on well already bound to
                       first CompanyMan.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean CompanyMan traversal CEMENT_EVAL→NEGATIVE_TEST
                          →BARRIER_VERIFIED→DISPLACING. Wide timestamp spacing
                          (70s) keeps BURST quiet. No HYSTERESIS.
  B02 — ORDER → HYSTERESIS: CompanyMan ORDER fires (P5 from NEGATIVE_TEST),
                            then attempts valid P4 → BARRIER_VERIFIED
                            (unvisited) → HYSTERESIS.
  B03 — JURISDICTION → HYSTERESIS: CompanyMan calls P6 (JURISDICTION). After
                                    pre-visit of NEGATIVE_TEST via P4, then
                                    P4 valid to BARRIER_VERIFIED (unvisited)
                                    → HYSTERESIS.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST_CADENCE (separate sessions, same compiler instance)
  C02 — JURISDICTION ×2 — CementOperator calls P3 (well control) and P7
                          (emergency response), both outside vocabulary.
  C03 — EXIT then JURISDICTION (independent wells).

Expected: 10/10 PASS

Geometry audit notes:
  C01 single-actor feasibility — CompanyMan path to NEGATIVE_TEST for ORDER
    and OIM with 3 expansions for BURST cannot share actor (different roles).
    Use separate sessions per legal harness pattern.
  BURST-safe traversal — B01 uses CompanyMan with widths CEMENT_EVAL(2)→
    NEGATIVE_TEST(3)[+1]→BARRIER_VERIFIED(3)[same]→DISPLACING(2)[contraction].
    Only 1 expansion. Below threshold. Inter-event spacing of 70s for safety.
  Role reachability — HYSTERESIS requires unvisited state after violation.
    CompanyMan from CEMENT_EVAL via P4 reaches NEGATIVE_TEST (visited).
    Then P5 from NEGATIVE_TEST is ORDER. Then P4 from NEGATIVE_TEST →
    BARRIER_VERIFIED is unvisited. ✓
"""

import sys
sys.path.insert(0, ".")
from petroleum_compiler_v0_1 import run_session, PetroleumCompiler

BASE_TS = 7_000_000.0


def gate_result(events):
    return [(r["decision"], r.get("invariant")) for r in run_session(events)]


def assert_pass(test_id, desc, results, decision, invariant, at_step):
    d, inv = results[at_step]
    ok = (d == decision and (invariant is None or inv == invariant))
    print(f"{'[PASS]' if ok else '[FAIL]'} {test_id}: {desc}")
    print(f"       step {at_step+1}: decision={d}, invariant={inv}")
    if not ok:
        print(f"       EXPECTED: decision={decision}, invariant={invariant}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01():
    """
    ORDER: CompanyMan calls P5_DisplaceComplete (initiate_displacement) from
    NEGATIVE_TEST state. P5 IS in CompanyMan vocabulary (valid at
    BARRIER_VERIFIED) but NOT in NEGATIVE_TEST.flows for CompanyMan.

    Direct anchor: Deepwater Horizon — BP CompanyMan authorized displacement
    of mud with seawater before negative pressure test result was structurally
    verified as passed. Compiler verdict: ORDER.
    """
    events = [
        # Start at CEMENT_EVAL; advance to NEGATIVE_TEST via P4
        {"actor_id": "companyman_kaluza", "action": "conduct_negative_pressure_test",
         "well_id": "MACONDO_A01", "timestamp": BASE_TS+0},
        # Now at NEGATIVE_TEST; call P5 (initiate_displacement) — P5 in vocab,
        # not in NEGATIVE_TEST.flows → ORDER
        {"actor_id": "companyman_kaluza", "action": "initiate_displacement",
         "well_id": "MACONDO_A01", "timestamp": BASE_TS+70},
    ]
    return assert_pass("A01", "ORDER: CompanyMan calls P5 from NEGATIVE_TEST (displace before barrier verified)",
                       gate_result(events), "INADMISSIBLE", "ORDER", 1)


def test_A02():
    """
    JURISDICTION: CompanyMan calls P6_RegulatoryGo (submit_displacement_clearance).
    P6 not in CompanyMan vocabulary — only MMSInspector can call P6.

    Direct anchor: Deepwater Horizon — BP filed MMS amended permit
    (BSEE-0123) certifying displacement was authorized based on negative
    pressure test results. Operator self-certifying a regulator gate.
    """
    events = [
        {"actor_id": "companyman_vidrine", "action": "submit_displacement_clearance",
         "well_id": "MACONDO_A02", "timestamp": BASE_TS+0},
    ]
    return assert_pass("A02", "JURISDICTION: CompanyMan calls P6 (operator self-certifying regulator gate)",
                       gate_result(events), "INADMISSIBLE", "JURISDICTION", 0)


def test_A03():
    """
    BURST_CADENCE: OIM expands through well lifecycle with three width
    expansions within the 60-second burst window:
      STANDBY(1) → DRILLING(2):           expansion #1
      DRILLING(2) → CASING_SET(2):        same
      CASING_SET(2) → CEMENTING(2):       same
      CEMENTING(2) → CEMENT_EVAL(2):      same
      CEMENT_EVAL(2) → NEGATIVE_TEST(3):  expansion #2
      NEGATIVE_TEST(3) → BARRIER_VER(3):  same
      BARRIER_VER(3) → DISPLACING(2):     contraction
      DISPLACING(2) → EMERGENCY(3):       expansion #3 → BURST fires

    Structurally analogous to iterative well program expansion under time
    pressure — the rig advances through phases faster than barrier
    verification can complete.
    """
    t = BASE_TS
    events = [
        {"actor_id": "oim_harrell", "action": "monitor_mud_returns",
         "well_id": "BURST_A03", "timestamp": t+0},   # STANDBY→DRILLING [+1]
        {"actor_id": "oim_harrell", "action": "drill_ahead",
         "well_id": "BURST_A03", "timestamp": t+1},   # DRILLING→CASING_SET [same]
        {"actor_id": "oim_harrell", "action": "run_casing",
         "well_id": "BURST_A03", "timestamp": t+2},   # CASING_SET→CEMENTING [same]
        {"actor_id": "oim_harrell", "action": "pump_cement_plug",
         "well_id": "BURST_A03", "timestamp": t+3},   # CEMENTING→CEMENT_EVAL [same]
        {"actor_id": "oim_harrell", "action": "conduct_negative_pressure_test",
         "well_id": "BURST_A03", "timestamp": t+4},   # CEMENT_EVAL→NEGATIVE_TEST [+1]
        {"actor_id": "oim_harrell", "action": "accept_barrier_test_pass",
         "well_id": "BURST_A03", "timestamp": t+5},   # NEGATIVE_TEST→BARRIER_VER [same]
        {"actor_id": "oim_harrell", "action": "initiate_displacement",
         "well_id": "BURST_A03", "timestamp": t+6},   # BARRIER_VER→DISPLACING [contraction]
        {"actor_id": "oim_harrell", "action": "activate_emergency_disconnect",
         "well_id": "BURST_A03", "timestamp": t+7},   # DISPLACING→EMERGENCY [+1] → BURST
    ]
    results = gate_result(events)
    burst_fired = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in results)
    ok = burst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} A03: BURST_CADENCE — OIM 3 expansions in 60-sec window")
    if not ok:
        for i, r in enumerate(results):
            print(f"       step {i+1}: {r}")
    return ok


def test_A04():
    """
    EXIT: Second CompanyMan presents on well already bound to first
    CompanyMan. Structural analog to maritime watch handoff without
    handoff event — well program continuity requires actor binding.
    """
    events = [
        {"actor_id": "companyman_kaluza", "action": "monitor_mud_returns",
         "well_id": "EXIT_A04", "timestamp": BASE_TS+0},
        {"actor_id": "companyman_vidrine", "action": "monitor_mud_returns",
         "well_id": "EXIT_A04", "timestamp": BASE_TS+70},
    ]
    return assert_pass("A04", "EXIT: Second CompanyMan presents on bound well",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01():
    """
    Negative control: clean CompanyMan traversal.
    CEMENT_EVAL → NEGATIVE_TEST → BARRIER_VERIFIED → DISPLACING → ABANDONED.
    All admissible. Wide timestamp spacing (70s) to keep BURST quiet.
    """
    events = [
        {"actor_id": "companyman_brown", "action": "conduct_negative_pressure_test",
         "well_id": "B01_CLEAN", "timestamp": BASE_TS+0},
        {"actor_id": "companyman_brown", "action": "accept_barrier_test_pass",
         "well_id": "B01_CLEAN", "timestamp": BASE_TS+70},
        {"actor_id": "companyman_brown", "action": "initiate_displacement",
         "well_id": "B01_CLEAN", "timestamp": BASE_TS+140},
        {"actor_id": "companyman_brown", "action": "displace_mud_with_seawater",
         "well_id": "B01_CLEAN", "timestamp": BASE_TS+210},
    ]
    results = gate_result(events)
    all_admissible = all(d == "ADMISSIBLE" for d, _ in results)
    ok = all_admissible
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Clean CompanyMan traversal — all ADMISSIBLE")
    if not ok:
        for i, r in enumerate(results):
            print(f"       step {i+1}: {r}")
    return ok


def test_B02():
    """
    ORDER → HYSTERESIS: CompanyMan at NEGATIVE_TEST calls P5 (ORDER fires);
    then attempts valid P4 → BARRIER_VERIFIED (unvisited) → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Pre-visit: CEMENT_EVAL → NEGATIVE_TEST (visited)
        {"actor_id": "companyman_kaluza", "action": "conduct_negative_pressure_test",
         "well_id": "HYST_B02", "timestamp": t+0},
        # ORDER: P5 from NEGATIVE_TEST — in vocab but not in state.flows
        {"actor_id": "companyman_kaluza", "action": "initiate_displacement",
         "well_id": "HYST_B02", "timestamp": t+70},
        # HYSTERESIS: P4 valid from NEGATIVE_TEST → BARRIER_VERIFIED (unvisited)
        {"actor_id": "companyman_kaluza", "action": "accept_barrier_test_pass",
         "well_id": "HYST_B02", "timestamp": t+140},
    ]
    results = gate_result(events)
    order_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "ORDER"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = order_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER → HYSTERESIS chain")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


def test_B03():
    """
    JURISDICTION → HYSTERESIS: CompanyMan calls P6 (JURISDICTION). Need
    a prior admissible visit to populate visited_states, then JURISDICTION,
    then valid action to an unvisited state.

    Sequence:
      1. CompanyMan admissible: CEMENT_EVAL → NEGATIVE_TEST via P4 (visited)
      2. JURISDICTION: call P6 (not in vocab)
      3. HYSTERESIS: P4 valid from NEGATIVE_TEST → BARRIER_VERIFIED (unvisited)
    """
    events = [
        # Admissible P4: CEMENT_EVAL → NEGATIVE_TEST (now visited)
        {"actor_id": "companyman_vidrine", "action": "conduct_negative_pressure_test",
         "well_id": "HYST_B03", "timestamp": BASE_TS+0},
        # JURISDICTION: call P6 (submit_displacement_clearance) — not in CompanyMan vocab
        {"actor_id": "companyman_vidrine", "action": "submit_displacement_clearance",
         "well_id": "HYST_B03", "timestamp": BASE_TS+70},
        # HYSTERESIS: P4 valid from NEGATIVE_TEST → BARRIER_VERIFIED (unvisited)
        {"actor_id": "companyman_vidrine", "action": "accept_barrier_test_pass",
         "well_id": "HYST_B03", "timestamp": BASE_TS+140},
    ]
    results = gate_result(events)
    juris_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = juris_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION → HYSTERESIS (CompanyMan P6, then P4 to unvisited)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01():
    """
    ORDER then BURST_CADENCE (separate sessions, same compiler instance).
    Different actors required — ORDER on CompanyMan, BURST on OIM (only OIM
    has the EMERGENCY branch needed for 3 expansions).
    """
    t = BASE_TS
    order_events = [
        {"actor_id": "companyman_kaluza", "action": "conduct_negative_pressure_test",
         "well_id": "ORDER_C01", "timestamp": t+0},
        {"actor_id": "companyman_kaluza", "action": "initiate_displacement",
         "well_id": "ORDER_C01", "timestamp": t+70},
    ]
    burst_events = [
        {"actor_id": "oim_kuchta", "action": "monitor_mud_returns",
         "well_id": "BURST_C01", "timestamp": t+1000},
        {"actor_id": "oim_kuchta", "action": "drill_ahead",
         "well_id": "BURST_C01", "timestamp": t+1001},
        {"actor_id": "oim_kuchta", "action": "run_casing",
         "well_id": "BURST_C01", "timestamp": t+1002},
        {"actor_id": "oim_kuchta", "action": "pump_cement_plug",
         "well_id": "BURST_C01", "timestamp": t+1003},
        {"actor_id": "oim_kuchta", "action": "conduct_negative_pressure_test",
         "well_id": "BURST_C01", "timestamp": t+1004},
        {"actor_id": "oim_kuchta", "action": "accept_barrier_test_pass",
         "well_id": "BURST_C01", "timestamp": t+1005},
        {"actor_id": "oim_kuchta", "action": "initiate_displacement",
         "well_id": "BURST_C01", "timestamp": t+1006},
        {"actor_id": "oim_kuchta", "action": "activate_emergency_disconnect",
         "well_id": "BURST_C01", "timestamp": t+1007},
    ]
    r_order = gate_result(order_events)
    r_burst = gate_result(burst_events)
    order_ok = r_order[1][0] == "INADMISSIBLE" and r_order[1][1] == "ORDER"
    burst_ok = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in r_burst)
    ok = order_ok and burst_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C01: ORDER then BURST_CADENCE (compound)")
    print(f"       ORDER at step 2: {r_order[1]}; BURST fired: {burst_ok}")
    return ok


def test_C02():
    """
    JURISDICTION ×2 — CementOperator calls P3 (well control) and P7
    (emergency response), both outside CementOperator vocabulary.
    Documents that CementOperator has no rig-wide authority.
    """
    events = [
        {"actor_id": "cement_op_gagliano", "action": "shut_in_well",
         "well_id": "CEMENT_C02", "timestamp": BASE_TS+0},
        {"actor_id": "cement_op_gagliano", "action": "activate_emergency_disconnect",
         "well_id": "CEMENT_C02", "timestamp": BASE_TS+70},
    ]
    results = gate_result(events)
    j1 = results[0][0] == "INADMISSIBLE" and results[0][1] == "JURISDICTION"
    j2 = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    ok = j1 and j2
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION ×2 — CementOperator calls P3 then P7")
    print(f"       step 1: {results[0]}, step 2: {results[1]}")
    return ok


def test_C03():
    """
    EXIT then JURISDICTION — independent wells.
    EXIT: second OIM on well bound to first OIM.
    JURISDICTION: CementOperator calls P6 (regulatory go) — not in vocab.
    """
    exit_events = [
        {"actor_id": "oim_harrell", "action": "monitor_mud_returns",
         "well_id": "EXIT_C03", "timestamp": BASE_TS+0},
        {"actor_id": "oim_kuchta", "action": "monitor_mud_returns",
         "well_id": "EXIT_C03", "timestamp": BASE_TS+70},
    ]
    juris_events = [
        {"actor_id": "cement_op_silva", "action": "submit_displacement_clearance",
         "well_id": "JURIS_C03", "timestamp": BASE_TS+1000},
    ]
    r_exit  = gate_result(exit_events)
    r_juris = gate_result(juris_events)
    exit_ok  = r_exit[1][0]  == "INADMISSIBLE" and r_exit[1][1]  == "EXIT"
    juris_ok = r_juris[0][0] == "INADMISSIBLE" and r_juris[0][1] == "JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION (independent wells)")
    print(f"       EXIT: {r_exit[1]}, JURISDICTION: {r_juris[0]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("Petroleum Operations Compiler v0.1 — Combinatorial Test Harness")
    print("═"*60 + "\n")

    tests = [
        ("Block A — Independent First-Fire", [test_A01, test_A02, test_A03, test_A04]),
        ("Block B — Hysteresis Dependency",  [test_B01, test_B02, test_B03]),
        ("Block C — Cross-Invariant Compound",[test_C01, test_C02, test_C03]),
    ]

    total = passed = 0
    for block_name, block_tests in tests:
        print(f"\n{block_name}")
        print("-" * 40)
        for t in block_tests:
            result = t()
            total += 1
            if result:
                passed += 1
            print()

    print("═"*60)
    print(f"RESULT: {passed}/{total} PASS")
    print("═"*60)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
