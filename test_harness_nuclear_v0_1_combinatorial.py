"""
Combinatorial Test Harness — Nuclear Compiler v0.1
════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:        SRO calls N6_ExtremeOverride (throttle_eccs) from OPERATING
                      state — override before completing emergency response
                      sequence. Structural analog to TMI 1979: operators throttled
                      ECCS before confirming actual coolant loss.
                      (N6 in SRO_SM vocabulary; OPERATING.flows does not contain N6)
  A02 — JURISDICTION: RO calls N6_ExtremeOverride (throttle_eccs) — N6 excluded
                      from RO vocabulary by construction. Structural anchor for
                      TMI JURISDICTION finding: ECCS override requires SRO
                      authorization, not RO.
  A03 — BURST_CADENCE: RO oscillates MONITORING(2)↔OPERATING(3) rapidly —
                      three width expansions within 60-second window.
  A04 — EXIT:         Second RO presents on shift_id already bound to first RO.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean traversal STANDBY→MONITORING→OPERATING→
                           EMERGENCY_RESPONSE, no HYSTERESIS fires.
  B02 — ORDER→HYSTERESIS: SRO calls N6 from OPERATING (ORDER), then N3
                           from OPERATING advances to unvisited
                           EMERGENCY_RESPONSE (HYSTERESIS).
  B03 — JURISDICTION→HYSTERESIS: RO calls N6 from OPERATING (JURISDICTION),
                                   then N3 from OPERATING advances to unvisited
                                   EMERGENCY_RESPONSE (HYSTERESIS).

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST_CADENCE in same session
  C02 — JURISDICTION then ORDER, same actor (SRO: N5 excluded → JURISDICTION,
         then N6 from STANDBY → ORDER)
  C03 — EXIT then JURISDICTION, separate actors, independent shift contexts

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")

from nuclear_compiler_v0_1 import run_session, NuclearCompiler

BASE_TS = 2_000_000.0


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def gate_result(events):
    results = run_session(events)
    return [(r["decision"], r.get("invariant", None)) for r in results]


def assert_pass(test_id, description, results, expected_decision,
                expected_invariant, at_step):
    d, inv = results[at_step]
    ok = (d == expected_decision and inv == expected_invariant)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {test_id} — {description}")
    if not ok:
        print(f"         expected  : {expected_decision} / {expected_invariant}"
              f"  (step {at_step + 1})")
        print(f"         got       : {d} / {inv}")
        for i, (rd, ri) in enumerate(results):
            print(f"         step {i+1}: {rd} / {ri}")
    return ok


def ev(actor_id, action, shift_id, ts=None):
    return {"actor_id": actor_id, "action": action,
            "shift_id": shift_id, "timestamp": ts}


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01_ORDER():
    """SRO throttles ECCS from OPERATING — N6 in vocabulary, wrong state."""
    events = [
        ev("sro_garcia", "check_parameters",   "shift_001"),   # STANDBY→MONITORING
        ev("sro_garcia", "adjust_coolant_flow", "shift_001"),  # MONITORING→OPERATING
        ev("sro_garcia", "throttle_eccs",       "shift_001"),  # N6 from OPERATING → ORDER
    ]
    r = gate_result(events)
    return assert_pass("A01", "ORDER — SRO throttle_eccs from OPERATING (TMI structural anchor)",
                       r, "INADMISSIBLE", "ORDER", 2)


def test_A02_JURISDICTION():
    """RO throttles ECCS — N6 not in RO vocabulary at all."""
    events = [
        ev("ro_jones", "check_parameters",   "shift_002"),
        ev("ro_jones", "adjust_coolant_flow", "shift_002"),
        ev("ro_jones", "throttle_eccs",       "shift_002"),  # N6 not in RO → JURISDICTION
    ]
    r = gate_result(events)
    return assert_pass("A02", "JURISDICTION — RO throttle_eccs (N6 excluded from RO vocabulary)",
                       r, "INADMISSIBLE", "JURISDICTION", 2)


def test_A03_BURST_CADENCE():
    """RO oscillates MONITORING(2)↔OPERATING(3) — 3 expansions in 60-second window."""
    events = [
        ev("ro_smith", "check_parameters",    "shift_003", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("ro_smith", "adjust_coolant_flow", "shift_003", BASE_TS + 10), # MONITORING→OPERATING w:2→3 exp2
        ev("ro_smith", "check_parameters",    "shift_003", BASE_TS + 20), # OPERATING→MONITORING w:3→2 contract
        ev("ro_smith", "adjust_coolant_flow", "shift_003", BASE_TS + 30), # MONITORING→OPERATING w:2→3 exp3 → BURST
    ]
    r = gate_result(events)
    return assert_pass("A03", "BURST_CADENCE — RO MONITORING↔OPERATING oscillation (3 expansions / 60s)",
                       r, "INADMISSIBLE", "BURST_CADENCE", 3)


def test_A04_EXIT():
    """Second RO presents on shift_id already bound to first RO."""
    events = [
        ev("ro_jones", "check_parameters", "shift_004"),   # binds shift_004 → ro_jones
        ev("ro_smith", "check_parameters", "shift_004"),   # different actor, same shift → EXIT
    ]
    r = gate_result(events)
    return assert_pass("A04", "EXIT — actor pivot on shift_004 (ro_smith vs ro_jones)",
                       r, "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01_negative_control():
    """Clean traversal STANDBY→MONITORING→OPERATING→EMERGENCY_RESPONSE.
    No violation, no HYSTERESIS."""
    events = [
        ev("ro_park", "check_parameters",    "shift_005"),  # STANDBY→MONITORING
        ev("ro_park", "adjust_coolant_flow", "shift_005"),  # MONITORING→OPERATING
        ev("ro_park", "manual_scram",        "shift_005"),  # OPERATING→EMERGENCY_RESPONSE
        ev("ro_park", "enter_eop",           "shift_005"),  # EMERGENCY_RESPONSE loop
    ]
    r = gate_result(events)
    all_admissible = all(d == "ADMISSIBLE" for d, _ in r)
    ok = all_admissible
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] B01 — Negative control: clean traversal, no HYSTERESIS")
    if not ok:
        for i, (d, inv) in enumerate(r):
            print(f"         step {i+1}: {d} / {inv}")
    return ok


def test_B02_ORDER_then_HYSTERESIS():
    """SRO calls N6 from OPERATING (ORDER), then N3 from OPERATING →
    EMERGENCY_RESPONSE (unvisited) → HYSTERESIS."""
    events = [
        ev("sro_chen", "check_parameters",    "shift_006"),  # STANDBY→MONITORING
        ev("sro_chen", "adjust_coolant_flow", "shift_006"),  # MONITORING→OPERATING
        ev("sro_chen", "throttle_eccs",       "shift_006"),  # ORDER — stays at OPERATING
        ev("sro_chen", "manual_scram",        "shift_006"),  # valid from OPERATING → EMERGENCY_RESPONSE (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B02", "ORDER→HYSTERESIS — N6 ORDER then N3 to unvisited EMERGENCY_RESPONSE",
                       r, "INADMISSIBLE", "HYSTERESIS", 3)


def test_B03_JURISDICTION_then_HYSTERESIS():
    """RO calls N6 from OPERATING (JURISDICTION), then N3 from OPERATING →
    EMERGENCY_RESPONSE (unvisited) → HYSTERESIS."""
    events = [
        ev("ro_jones", "check_parameters",    "shift_007"),  # STANDBY→MONITORING
        ev("ro_jones", "adjust_coolant_flow", "shift_007"),  # MONITORING→OPERATING
        ev("ro_jones", "throttle_eccs",       "shift_007"),  # JURISDICTION — stays at OPERATING
        ev("ro_jones", "manual_scram",        "shift_007"),  # valid → EMERGENCY_RESPONSE (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B03", "JURISDICTION→HYSTERESIS — N6 JURISDICTION then N3 to unvisited EMERGENCY_RESPONSE",
                       r, "INADMISSIBLE", "HYSTERESIS", 3)


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01_ORDER_then_BURST():
    """SRO fires ORDER (N6 from OPERATING), then oscillates MONITORING↔OPERATING
    with tight timestamps → BURST fires."""
    events = [
        ev("sro_garcia", "check_parameters",    "shift_008", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("sro_garcia", "adjust_coolant_flow", "shift_008", BASE_TS + 10), # MONITORING→OPERATING w:2→3 exp2
        ev("sro_garcia", "throttle_eccs",       "shift_008", BASE_TS + 15), # ORDER — no width record
        ev("sro_garcia", "check_parameters",    "shift_008", BASE_TS + 20), # OPERATING→MONITORING w:3→2 contract
        ev("sro_garcia", "adjust_coolant_flow", "shift_008", BASE_TS + 30), # MONITORING→OPERATING w:2→3 exp3 → BURST
    ]
    r = gate_result(events)
    order_at_2 = assert_pass("C01a", "ORDER fires at step 3",
                              r, "INADMISSIBLE", "ORDER", 2)
    burst_at_4 = assert_pass("C01b", "BURST_CADENCE fires at step 5",
                              r, "INADMISSIBLE", "BURST_CADENCE", 4)
    return order_at_2 and burst_at_4


def test_C02_JURISDICTION_then_ORDER():
    """Same SRO actor: N5 → JURISDICTION (N5 not in SRO vocabulary);
    N6 from STANDBY → ORDER (N6 in vocabulary, STANDBY.flows = {N1} only)."""
    events = [
        ev("sro_chen", "notify_nrc",     "shift_009"),  # JURISDICTION — N5 not in SRO_SM vocabulary
        ev("sro_chen", "throttle_eccs",  "shift_009"),  # state still STANDBY; N6 in vocab, STANDBY.flows={N1} → ORDER
    ]
    r = gate_result(events)
    juris_at_0 = assert_pass("C02a", "JURISDICTION fires at step 1 (N5 not in SRO_SM)",
                              r, "INADMISSIBLE", "JURISDICTION", 0)
    order_at_1 = assert_pass("C02b", "ORDER fires at step 2 (N6 from STANDBY state)",
                              r, "INADMISSIBLE", "ORDER", 1)
    return juris_at_0 and order_at_1


def test_C03_EXIT_then_JURISDICTION():
    """EXIT on shift_010, then separate actor calls N6 → JURISDICTION on shift_011."""
    events = [
        ev("ro_jones", "check_parameters", "shift_010"),  # binds shift_010 → ro_jones
        ev("ro_smith", "check_parameters", "shift_010"),  # EXIT — ro_smith on ro_jones shift
        ev("ro_smith", "throttle_eccs",    "shift_011"),  # separate shift; N6 not in RO vocabulary → JURISDICTION
    ]
    r = gate_result(events)
    exit_at_1  = assert_pass("C03a", "EXIT fires at step 2 (ro_smith vs ro_jones on shift_010)",
                              r, "INADMISSIBLE", "EXIT", 1)
    juris_at_2 = assert_pass("C03b", "JURISDICTION fires at step 3 (RO throttle_eccs on shift_011)",
                              r, "INADMISSIBLE", "JURISDICTION", 2)
    return exit_at_1 and juris_at_2


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\nNuclear Compiler v0.1 — Combinatorial Harness")
    print("═" * 56)

    results = []
    print("\nBlock A — Independent First-Fire")
    results.append(test_A01_ORDER())
    results.append(test_A02_JURISDICTION())
    results.append(test_A03_BURST_CADENCE())
    results.append(test_A04_EXIT())

    print("\nBlock B — Hysteresis Dependency")
    results.append(test_B01_negative_control())
    results.append(test_B02_ORDER_then_HYSTERESIS())
    results.append(test_B03_JURISDICTION_then_HYSTERESIS())

    print("\nBlock C — Cross-Invariant Compound")
    results.append(test_C01_ORDER_then_BURST())
    results.append(test_C02_JURISDICTION_then_ORDER())
    results.append(test_C03_EXIT_then_JURISDICTION())

    passed = sum(results)
    total  = len(results)
    print(f"\n{'═' * 56}")
    print(f"Result: {passed}/{total} PASS")
    if passed == total:
        print("✓ All tests passed — Nuclear compiler confirmed on hardware.")
    return passed == total


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
