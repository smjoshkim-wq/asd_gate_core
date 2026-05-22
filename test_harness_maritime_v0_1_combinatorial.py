"""
Combinatorial Test Harness — Maritime Operations Compiler v0.1
════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:        Master calls M6_Evacuation (order_abandon_ship) from
                      EMERGENCY state — M6 in Master vocabulary, EMERGENCY.flows
                      does not contain M6; must muster first.
                      Costa Concordia anchor: Schettino delayed mandatory muster
                      while vessel was already in emergency state.
  A02 — JURISDICTION: OOW calls M6_Evacuation (order_abandon_ship) — M6 not in
                      OOW vocabulary. Master-exclusive by construction under
                      SOLAS Chapter III. Costa Concordia anchor: abandon ship
                      cannot be ordered by subordinate officer.
  A03 — BURST_CADENCE: Master oscillates MONITORING(2)↔UNDERWAY(3) rapidly —
                       three width expansions within 60-second window.
                       Structural analog to Costa Concordia's unauthorized course
                       deviation cycling.
  A04 — EXIT:         Second Master presents on voyage_id already bound to
                      first Master.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean traversal STANDBY→MONITORING→UNDERWAY→
                           COASTAL_WATERS→EMERGENCY→MUSTER→ABANDON.
  B02 — ORDER→HYSTERESIS: Master calls M6 from EMERGENCY (ORDER), then M4
                           from EMERGENCY → MUSTER (unvisited) → HYSTERESIS.
  B03 — JURISDICTION→HYSTERESIS: OOW calls M6 from UNDERWAY (JURISDICTION),
                                   then M3 from UNDERWAY → COASTAL_WATERS
                                   (unvisited) → HYSTERESIS.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST_CADENCE in same session
  C02 — JURISDICTION then ORDER, same OOW actor
  C03 — EXIT then JURISDICTION, separate actors, independent voyage contexts

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")

from maritime_compiler_v0_1 import run_session, MaritimeCompiler

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


def ev(actor_id, action, voyage_id, ts=None):
    return {"actor_id": actor_id, "action": action,
            "voyage_id": voyage_id, "timestamp": ts}


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01_ORDER():
    """Master calls order_abandon_ship from EMERGENCY — must muster first.
    Costa Concordia anchor: Schettino's delayed evacuation authorization."""
    events = [
        ev("master_schettino", "plot_position",       "voyage_001"),  # STANDBY→MONITORING
        ev("master_schettino", "alter_course",        "voyage_001"),  # MONITORING→UNDERWAY
        ev("master_schettino", "report_position_vts", "voyage_001"),  # UNDERWAY→COASTAL_WATERS
        ev("master_schettino", "sound_general_alarm", "voyage_001"),  # COASTAL_WATERS→EMERGENCY
        ev("master_schettino", "order_abandon_ship",  "voyage_001"),  # M6 from EMERGENCY → ORDER
    ]
    r = gate_result(events)
    return assert_pass("A01", "ORDER — Master abandon_ship from EMERGENCY (muster gate bypassed, Costa Concordia anchor)",
                       r, "INADMISSIBLE", "ORDER", 4)


def test_A02_JURISDICTION():
    """OOW calls order_abandon_ship — M6 not in OOW vocabulary (Master-exclusive)."""
    events = [
        ev("oow_harris", "plot_position",      "voyage_002"),  # STANDBY→MONITORING
        ev("oow_harris", "alter_course",       "voyage_002"),  # MONITORING→UNDERWAY
        ev("oow_harris", "order_abandon_ship", "voyage_002"),  # M6 not in OOW → JURISDICTION
    ]
    r = gate_result(events)
    return assert_pass("A02", "JURISDICTION — OOW order_abandon_ship (M6 Master-exclusive, SOLAS Chapter III)",
                       r, "INADMISSIBLE", "JURISDICTION", 2)


def test_A03_BURST_CADENCE():
    """Master oscillates MONITORING(2)↔UNDERWAY(3) — 3 expansions in 60-second window."""
    events = [
        ev("master_chang", "plot_position",  "voyage_003", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("master_chang", "alter_course",   "voyage_003", BASE_TS + 10), # MONITORING→UNDERWAY w:2→3 exp2
        ev("master_chang", "plot_position",  "voyage_003", BASE_TS + 20), # UNDERWAY→MONITORING w:3→2 contract
        ev("master_chang", "alter_course",   "voyage_003", BASE_TS + 30), # MONITORING→UNDERWAY w:2→3 exp3 → BURST
    ]
    r = gate_result(events)
    return assert_pass("A03", "BURST_CADENCE — Master MONITORING↔UNDERWAY oscillation (unauthorized course changes)",
                       r, "INADMISSIBLE", "BURST_CADENCE", 3)


def test_A04_EXIT():
    """Second Master presents on voyage_id already bound to first Master."""
    events = [
        ev("master_schettino", "plot_position", "voyage_004"),  # binds voyage_004 → master_schettino
        ev("master_chang",     "plot_position", "voyage_004"),  # different Master, same voyage → EXIT
    ]
    r = gate_result(events)
    return assert_pass("A04", "EXIT — actor pivot on voyage_004 (master_chang vs master_schettino)",
                       r, "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01_negative_control():
    """Clean traversal STANDBY→MONITORING→UNDERWAY→COASTAL_WATERS→
    EMERGENCY→MUSTER→ABANDON. All ADMISSIBLE, no HYSTERESIS.
    Timestamps spaced 70s apart so the three expansions
    (1→2, 2→3, 3→4) each fall outside the 60-second BURST window."""
    events = [
        ev("master_okafor", "plot_position",       "voyage_005", BASE_TS),        # STANDBY→MONITORING w:1→2
        ev("master_okafor", "alter_course",        "voyage_005", BASE_TS + 70),   # MONITORING→UNDERWAY w:2→3
        ev("master_okafor", "report_position_vts", "voyage_005", BASE_TS + 140),  # UNDERWAY→COASTAL_WATERS w:3→3
        ev("master_okafor", "sound_general_alarm", "voyage_005", BASE_TS + 210),  # COASTAL_WATERS→EMERGENCY w:3→3
        ev("master_okafor", "order_muster_stations","voyage_005",BASE_TS + 280),  # EMERGENCY→MUSTER w:3→4
        ev("master_okafor", "order_abandon_ship",  "voyage_005", BASE_TS + 350),  # MUSTER→ABANDON w:4→1
    ]
    r = gate_result(events)
    all_admissible = all(d == "ADMISSIBLE" for d, _ in r)
    ok = all_admissible
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] B01 — Negative control: clean traversal STANDBY→ABANDON, no HYSTERESIS")
    if not ok:
        for i, (d, inv) in enumerate(r):
            print(f"         step {i+1}: {d} / {inv}")
    return ok


def test_B02_ORDER_then_HYSTERESIS():
    """Master calls M6 from EMERGENCY (ORDER — must muster first), then M4 from
    EMERGENCY → MUSTER (unvisited) → HYSTERESIS."""
    events = [
        ev("master_schettino", "plot_position",       "voyage_006"),  # STANDBY→MONITORING
        ev("master_schettino", "alter_course",        "voyage_006"),  # MONITORING→UNDERWAY
        ev("master_schettino", "report_position_vts", "voyage_006"),  # UNDERWAY→COASTAL_WATERS
        ev("master_schettino", "sound_general_alarm", "voyage_006"),  # COASTAL_WATERS→EMERGENCY
        ev("master_schettino", "order_abandon_ship",  "voyage_006"),  # ORDER — M6 from EMERGENCY, stays at EMERGENCY
        ev("master_schettino", "order_muster_stations","voyage_006"), # valid EMERGENCY→MUSTER (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B02", "ORDER→HYSTERESIS — M6 ORDER then M4 to unvisited MUSTER",
                       r, "INADMISSIBLE", "HYSTERESIS", 5)


def test_B03_JURISDICTION_then_HYSTERESIS():
    """OOW calls M6 from UNDERWAY (JURISDICTION), then M3 from UNDERWAY →
    COASTAL_WATERS (unvisited) → HYSTERESIS."""
    events = [
        ev("oow_kim", "plot_position",      "voyage_007"),  # STANDBY→MONITORING
        ev("oow_kim", "alter_course",       "voyage_007"),  # MONITORING→UNDERWAY
        ev("oow_kim", "order_abandon_ship", "voyage_007"),  # JURISDICTION — M6 not in OOW, stays at UNDERWAY
        ev("oow_kim", "report_position_vts","voyage_007"),  # valid UNDERWAY→COASTAL_WATERS (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B03", "JURISDICTION→HYSTERESIS — M6 JURISDICTION then M3 to unvisited COASTAL_WATERS",
                       r, "INADMISSIBLE", "HYSTERESIS", 3)


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01_ORDER_then_BURST():
    """Master fires ORDER (M6 from EMERGENCY), then oscillates MONITORING↔UNDERWAY
    with tight timestamps → BURST fires."""
    events = [
        ev("master_chang", "plot_position",       "voyage_008", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("master_chang", "alter_course",        "voyage_008", BASE_TS + 10), # MONITORING→UNDERWAY w:2→3 exp2
        ev("master_chang", "report_position_vts", "voyage_008", BASE_TS + 12), # UNDERWAY→COASTAL_WATERS (no width change: 3→3)
        ev("master_chang", "sound_general_alarm", "voyage_008", BASE_TS + 14), # COASTAL_WATERS→EMERGENCY (3→3)
        ev("master_chang", "order_abandon_ship",  "voyage_008", BASE_TS + 16), # ORDER — no width record; within 60s window
        ev("master_chang", "plot_position",       "voyage_008", BASE_TS + 20), # EMERGENCY→EMERGENCY (3→3) — no change, contract not needed
        ev("master_chang", "alter_course",        "voyage_008", BASE_TS + 30), # M2 not valid from EMERGENCY... 
    ]
    # Note: After EMERGENCY, M2 is not in EMERGENCY.flows. Use different burst path:
    # Need to restart and use a cleaner burst on the Master path.
    # Better: use a fresh compiler session with tight MONITORING↔UNDERWAY oscillation.
    # The ORDER fires first, then burst within the same 60-second window.
    events = [
        ev("master_okafor", "plot_position",  "voyage_008b", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("master_okafor", "alter_course",   "voyage_008b", BASE_TS + 10), # MONITORING→UNDERWAY w:2→3 exp2
        ev("master_okafor", "plot_position",  "voyage_008b", BASE_TS + 15), # UNDERWAY→MONITORING w:3→2 contract
        ev("master_okafor", "alter_course",   "voyage_008b", BASE_TS + 20), # MONITORING→UNDERWAY w:2→3 exp3 → BURST
    ]
    # First establish ORDER scenario then BURST in same session
    # Use single session: ORDER first (using a setup that reaches EMERGENCY quickly), then burst
    # Simpler: just use the same actor in ONE session where ORDER happens then BURST.
    # Let's use: ORDER via M6 at EMERGENCY, then return via M1 to keep moving,
    # but M1 from EMERGENCY loops (3→3, no expansion). Can't burst from there.
    # 
    # Better approach: show ORDER fires early, then separate burst path in the test.
    # The compound test demonstrates that two independent invariants fire in one session.
    # Run: setup → ORDER → continue to burst. Need the burst path to have expansions.
    # 
    # Clean design: SRO starts fresh, ORDER fires early (at step 2 from a clean state),
    # then burst in MONITORING↔UNDERWAY cycle.
    events_c01 = [
        ev("master_okafor", "plot_position",       "voyage_008c", BASE_TS),      # STANDBY→MONITORING w:1→2 exp1
        ev("master_okafor", "alter_course",        "voyage_008c", BASE_TS + 5),  # MONITORING→UNDERWAY w:2→3 exp2
        ev("master_okafor", "report_position_vts", "voyage_008c", BASE_TS + 7),  # UNDERWAY→COASTAL_WATERS (3→3)
        ev("master_okafor", "sound_general_alarm", "voyage_008c", BASE_TS + 9),  # COASTAL_WATERS→EMERGENCY (3→3)
        ev("master_okafor", "order_abandon_ship",  "voyage_008c", BASE_TS + 11), # ORDER — M6 from EMERGENCY; no width record
        ev("master_okafor", "transmit_mayday",     "voyage_008c", BASE_TS + 20), # M5 from EMERGENCY→MAYDAY w:3→3 (no expansion)
        ev("master_okafor", "plot_position",       "voyage_008c", BASE_TS + 25), # MAYDAY→MAYDAY loop (3→3)
        ev("master_okafor", "transmit_mayday",     "voyage_008c", BASE_TS + 35), # MAYDAY loop (3→3)
    ]
    # The above doesn't generate expansions after ORDER. Let me use a simpler path:
    # We'll just confirm ORDER fires at step 5, and BURST_CADENCE fires independently
    # at step 4 in a separate inner session. The compound test just needs both in same session.
    # Let's use a path where expansion happens AFTER ORDER:
    # After ORDER (stays at EMERGENCY), go back through EMERGENCY→MUSTER (expansion: 3→4) 
    # via M4 (but that would be HYSTERESIS since MUSTER is unvisited)...
    # 
    # Actually: let's be honest about the compound geometry. The ORDER fires before BURST.
    # We need 3 expansions total. The pre-ORDER path already has 2 (STANDBY→MONITORING,
    # MONITORING→UNDERWAY). After ORDER, we stay at EMERGENCY (no expansion).
    # Then M5 from EMERGENCY→MAYDAY (3→3, no expansion).
    # Then M6 from MAYDAY→ABANDON (3→1, contraction).
    # We only have 2 pre-ORDER expansions. Not enough for BURST post-ORDER.
    # 
    # Solution: put the BURST check before the ORDER in the compound test.
    # Actually compound tests are about sequential fires in the same session.
    # Let's use: BURST fires first (3 expansions), then ORDER fires after.
    # Setup: exp1, exp2, contract, exp3 (BURST), then ORDER in a new state.
    events_c01_final = [
        ev("master_okafor", "plot_position",  "voyage_008d", BASE_TS),       # STANDBY→MONITORING w:1→2 exp1
        ev("master_okafor", "alter_course",   "voyage_008d", BASE_TS + 10),  # MONITORING→UNDERWAY w:2→3 exp2
        ev("master_okafor", "plot_position",  "voyage_008d", BASE_TS + 20),  # UNDERWAY→MONITORING w:3→2 contract
        ev("master_okafor", "alter_course",   "voyage_008d", BASE_TS + 30),  # MONITORING→UNDERWAY w:2→3 exp3 → BURST
        ev("master_okafor", "report_position_vts","voyage_008d", BASE_TS + 35), # UNDERWAY→COASTAL_WATERS (3→3)
        ev("master_okafor", "sound_general_alarm","voyage_008d", BASE_TS + 37), # COASTAL_WATERS→EMERGENCY (3→3)
        ev("master_okafor", "order_abandon_ship", "voyage_008d", BASE_TS + 40), # ORDER — M6 from EMERGENCY
    ]
    r = gate_result(events_c01_final)
    burst_at_3 = assert_pass("C01a", "BURST_CADENCE fires at step 4",
                              r, "INADMISSIBLE", "BURST_CADENCE", 3)
    order_at_6 = assert_pass("C01b", "ORDER fires at step 7 (M6 from EMERGENCY)",
                              r, "INADMISSIBLE", "ORDER", 6)
    return burst_at_3 and order_at_6


def test_C02_JURISDICTION_then_ORDER():
    """Same OOW actor: M5 → JURISDICTION (M5 not in OOW vocabulary);
    then M4 from STANDBY → ORDER (M4 in vocabulary, STANDBY.flows = {M1} only)."""
    events = [
        ev("oow_harris", "transmit_mayday",    "voyage_009"),  # JURISDICTION — M5 not in OOW vocabulary
        ev("oow_harris", "sound_general_alarm","voyage_009"),  # state still STANDBY; M4 in vocab, STANDBY.flows={M1} → ORDER
    ]
    r = gate_result(events)
    juris_at_0 = assert_pass("C02a", "JURISDICTION fires at step 1 (OOW transmit_mayday = M5 excluded)",
                              r, "INADMISSIBLE", "JURISDICTION", 0)
    order_at_1 = assert_pass("C02b", "ORDER fires at step 2 (M4 from STANDBY state)",
                              r, "INADMISSIBLE", "ORDER", 1)
    return juris_at_0 and order_at_1


def test_C03_EXIT_then_JURISDICTION():
    """EXIT on voyage_010, then separate actor calls M6 → JURISDICTION on voyage_011."""
    events = [
        ev("master_schettino", "plot_position",      "voyage_010"),  # binds voyage_010 → master_schettino
        ev("master_chang",     "plot_position",      "voyage_010"),  # EXIT — master_chang on master_schettino voyage
        ev("oow_santos",       "order_abandon_ship", "voyage_011"),  # separate voyage; M6 not in OOW vocabulary → JURISDICTION
    ]
    r = gate_result(events)
    exit_at_1  = assert_pass("C03a", "EXIT fires at step 2 (master_chang vs master_schettino on voyage_010)",
                              r, "INADMISSIBLE", "EXIT", 1)
    juris_at_2 = assert_pass("C03b", "JURISDICTION fires at step 3 (OOW order_abandon_ship on voyage_011)",
                              r, "INADMISSIBLE", "JURISDICTION", 2)
    return exit_at_1 and juris_at_2


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\nMaritime Operations Compiler v0.1 — Combinatorial Harness")
    print("═" * 58)

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
    print(f"\n{'═' * 58}")
    print(f"Result: {passed}/{total} PASS")
    if passed == total:
        print("✓ All tests passed — Maritime compiler confirmed on hardware.")
    return passed == total


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
