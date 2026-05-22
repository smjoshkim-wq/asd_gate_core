"""
Combinatorial Test Harness — FEMA ICS / Emergency Response Compiler v0.1
═════════════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:        IC calls AC4_Execution (deploy_strike_team) from PLANNING
                      state — resources deployed before Unified Command established.
                      Structural anchor for Katrina: FEMA deployed resources into
                      the theater before a unified federal-state-local command
                      structure was legally established.
                      (AC4 in IC vocabulary; PLANNING.flows does not contain AC4)
  A02 — JURISDICTION: Field_Resource calls AC5_CommandTransfer
                      (activate_unified_command) — AC5 not in Field_Resource
                      vocabulary. Structural anchor: subordinate resources cannot
                      restructure the command hierarchy.
  A03 — BURST_CADENCE: IC oscillates ASSESSMENT(2)↔PLANNING(3) rapidly —
                       three width expansions within 60-second window.
                       Structural analog to Katrina's parallel resource channels:
                       repeated AC2/AC1 cycling without converging on UC.
  A04 — EXIT:         Second IC presents on incident_id already bound to
                      first IC. Structural analog to Katrina dual command
                      (Title 10 and Title 32 both claiming IC authority).

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean traversal STANDBY→ASSESSMENT→PLANNING→
                           UNIFIED_COMMAND→OPERATIONS, no HYSTERESIS fires.
  B02 — ORDER→HYSTERESIS: IC calls AC4 from PLANNING (ORDER), then AC5
                           from PLANNING → UNIFIED_COMMAND (unvisited) → HYSTERESIS.
  B03 — JURISDICTION→HYSTERESIS: OSC calls AC2_Planning from ASSESSMENT
                                   (JURISDICTION — AC2 not in OSC vocabulary),
                                   then AC4 from ASSESSMENT → EXECUTING
                                   (unvisited) → HYSTERESIS.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST_CADENCE in same session
  C02 — JURISDICTION then ORDER, same IC actor
  C03 — EXIT then JURISDICTION, separate actors, independent incident contexts

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")

from fema_compiler_v0_1 import run_session, FEMACompiler

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


def ev(actor_id, action, incident_id, ts=None):
    return {"actor_id": actor_id, "action": action,
            "incident_id": incident_id, "timestamp": ts}


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01_ORDER():
    """IC deploys resources from PLANNING — bypasses Unified Command gate.
    Katrina anchor: resources deployed before UC established."""
    events = [
        ev("ic_thompson", "conduct_size_up",     "incident_001"),  # STANDBY→ASSESSMENT
        ev("ic_thompson", "draft_objectives",    "incident_001"),  # ASSESSMENT→PLANNING
        ev("ic_thompson", "deploy_strike_team",  "incident_001"),  # AC4 from PLANNING → ORDER
    ]
    r = gate_result(events)
    return assert_pass("A01", "ORDER — IC deploy_strike_team from PLANNING (Katrina anchor)",
                       r, "INADMISSIBLE", "ORDER", 2)


def test_A02_JURISDICTION():
    """Field_Resource calls activate_unified_command — AC5 not in vocabulary."""
    events = [
        ev("resource_team1", "deploy_strike_team",        "incident_002"),  # STANDBY→EXECUTING
        ev("resource_team1", "activate_unified_command",  "incident_002"),  # AC5 not in Field_Resource → JURISDICTION
    ]
    r = gate_result(events)
    return assert_pass("A02", "JURISDICTION — Field_Resource activate_unified_command (AC5 excluded)",
                       r, "INADMISSIBLE", "JURISDICTION", 1)


def test_A03_BURST_CADENCE():
    """IC oscillates ASSESSMENT(2)↔PLANNING(3) — 3 expansions in 60-second window."""
    events = [
        ev("ic_rodriguez", "conduct_size_up",   "incident_003", BASE_TS),      # STANDBY→ASSESSMENT w:1→2 exp1
        ev("ic_rodriguez", "draft_objectives",  "incident_003", BASE_TS + 10), # ASSESSMENT→PLANNING w:2→3 exp2
        ev("ic_rodriguez", "conduct_size_up",   "incident_003", BASE_TS + 20), # PLANNING→ASSESSMENT w:3→2 contract
        ev("ic_rodriguez", "draft_objectives",  "incident_003", BASE_TS + 30), # ASSESSMENT→PLANNING w:2→3 exp3 → BURST
    ]
    r = gate_result(events)
    return assert_pass("A03", "BURST_CADENCE — IC ASSESSMENT↔PLANNING oscillation (Katrina parallel channels)",
                       r, "INADMISSIBLE", "BURST_CADENCE", 3)


def test_A04_EXIT():
    """Second IC presents on incident already bound to first IC.
    Katrina anchor: Title 10 and Title 32 parallel command structures."""
    events = [
        ev("ic_thompson",  "conduct_size_up", "incident_004"),  # binds incident_004 → ic_thompson
        ev("ic_rodriguez", "conduct_size_up", "incident_004"),  # different IC, same incident → EXIT
    ]
    r = gate_result(events)
    return assert_pass("A04", "EXIT — dual IC on incident_004 (Katrina command structure anchor)",
                       r, "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01_negative_control():
    """Clean traversal STANDBY→ASSESSMENT→PLANNING→UNIFIED_COMMAND→OPERATIONS.
    All steps ADMISSIBLE, no HYSTERESIS.
    Timestamps spaced 70s apart so the three consecutive expansions
    (1→2, 2→3, 3→4) each fall outside the 60-second BURST window."""
    events = [
        ev("ic_washington", "conduct_size_up",          "incident_005", BASE_TS),        # STANDBY→ASSESSMENT w:1→2
        ev("ic_washington", "draft_objectives",         "incident_005", BASE_TS + 70),   # ASSESSMENT→PLANNING w:2→3
        ev("ic_washington", "activate_unified_command", "incident_005", BASE_TS + 140),  # PLANNING→UNIFIED_COMMAND w:3→4
        ev("ic_washington", "deploy_strike_team",       "incident_005", BASE_TS + 210),  # UNIFIED_COMMAND→OPERATIONS w:4→4
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
    """IC calls AC4 from PLANNING (ORDER), then AC5 from PLANNING →
    UNIFIED_COMMAND (unvisited) → HYSTERESIS."""
    events = [
        ev("ic_thompson", "conduct_size_up",          "incident_006"),  # STANDBY→ASSESSMENT
        ev("ic_thompson", "draft_objectives",         "incident_006"),  # ASSESSMENT→PLANNING
        ev("ic_thompson", "deploy_strike_team",       "incident_006"),  # ORDER — stays at PLANNING
        ev("ic_thompson", "activate_unified_command", "incident_006"),  # valid PLANNING→UNIFIED_COMMAND (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B02", "ORDER→HYSTERESIS — AC4 ORDER then AC5 to unvisited UNIFIED_COMMAND",
                       r, "INADMISSIBLE", "HYSTERESIS", 3)


def test_B03_JURISDICTION_then_HYSTERESIS():
    """OSC calls AC2 (JURISDICTION), then AC4 from ASSESSMENT → EXECUTING
    (unvisited) → HYSTERESIS."""
    events = [
        ev("osc_williams", "conduct_size_up",     "incident_007"),  # STANDBY→ASSESSMENT
        ev("osc_williams", "draft_objectives",    "incident_007"),  # JURISDICTION — AC2 not in OSC vocabulary
        ev("osc_williams", "deploy_strike_team",  "incident_007"),  # valid ASSESSMENT→EXECUTING (unvisited) → HYSTERESIS
    ]
    r = gate_result(events)
    return assert_pass("B03", "JURISDICTION→HYSTERESIS — AC2 JURISDICTION then AC4 to unvisited EXECUTING",
                       r, "INADMISSIBLE", "HYSTERESIS", 2)


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01_ORDER_then_BURST():
    """IC fires ORDER (AC4 from PLANNING), then oscillates ASSESSMENT↔PLANNING
    with tight timestamps → BURST fires."""
    events = [
        ev("ic_rodriguez", "conduct_size_up",   "incident_008", BASE_TS),       # STANDBY→ASSESSMENT w:1→2 exp1
        ev("ic_rodriguez", "draft_objectives",  "incident_008", BASE_TS + 10),  # ASSESSMENT→PLANNING w:2→3 exp2
        ev("ic_rodriguez", "deploy_strike_team","incident_008", BASE_TS + 15),  # ORDER — no width record
        ev("ic_rodriguez", "conduct_size_up",   "incident_008", BASE_TS + 20),  # PLANNING→ASSESSMENT w:3→2 contract
        ev("ic_rodriguez", "draft_objectives",  "incident_008", BASE_TS + 30),  # ASSESSMENT→PLANNING w:2→3 exp3 → BURST
    ]
    r = gate_result(events)
    order_at_2 = assert_pass("C01a", "ORDER fires at step 3",
                              r, "INADMISSIBLE", "ORDER", 2)
    burst_at_4 = assert_pass("C01b", "BURST_CADENCE fires at step 5",
                              r, "INADMISSIBLE", "BURST_CADENCE", 4)
    return order_at_2 and burst_at_4


def test_C02_JURISDICTION_then_ORDER():
    """Same IC actor: AC3_ResourceOrder → JURISDICTION (AC3 not in IC vocabulary);
    then AC4 from STANDBY → ORDER (AC4 in vocabulary, STANDBY.flows = {AC1} only)."""
    events = [
        ev("ic_thompson", "request_mutual_aid", "incident_009"),  # JURISDICTION — AC3 not in IC vocabulary
        ev("ic_thompson", "deploy_strike_team", "incident_009"),  # state still STANDBY; AC4 in vocab, STANDBY.flows={AC1} → ORDER
    ]
    r = gate_result(events)
    juris_at_0 = assert_pass("C02a", "JURISDICTION fires at step 1 (IC request_mutual_aid = AC3 excluded)",
                              r, "INADMISSIBLE", "JURISDICTION", 0)
    order_at_1 = assert_pass("C02b", "ORDER fires at step 2 (AC4 from STANDBY state)",
                              r, "INADMISSIBLE", "ORDER", 1)
    return juris_at_0 and order_at_1


def test_C03_EXIT_then_JURISDICTION():
    """EXIT on incident_010, then separate actor calls AC3 → JURISDICTION on incident_011."""
    events = [
        ev("ic_thompson",  "conduct_size_up",   "incident_010"),  # binds incident_010 → ic_thompson
        ev("ic_rodriguez", "conduct_size_up",   "incident_010"),  # EXIT — ic_rodriguez on ic_thompson incident
        ev("ic_rodriguez", "request_mutual_aid", "incident_011"), # separate incident; AC3 not in IC vocabulary → JURISDICTION
    ]
    r = gate_result(events)
    exit_at_1  = assert_pass("C03a", "EXIT fires at step 2 (dual IC on incident_010)",
                              r, "INADMISSIBLE", "EXIT", 1)
    juris_at_2 = assert_pass("C03b", "JURISDICTION fires at step 3 (IC request_mutual_aid = AC3)",
                              r, "INADMISSIBLE", "JURISDICTION", 2)
    return exit_at_1 and juris_at_2


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\nFEMA ICS / Emergency Response Compiler v0.1 — Combinatorial Harness")
    print("═" * 70)

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
    print(f"\n{'═' * 70}")
    print(f"Result: {passed}/{total} PASS")
    if passed == total:
        print("✓ All tests passed — FEMA ICS compiler confirmed on hardware.")
    return passed == total


if __name__ == "__main__":
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
