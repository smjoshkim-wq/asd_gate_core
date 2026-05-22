"""
Combinatorial Test Harness — Construction Approval Pipeline Compiler v0.1
══════════════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:         GC calls D1_Structural from PERMIT_ISSUED state.
                       D1 in GC vocab (SITE_PREP, FOUNDATION, STRUCTURAL_FRAMING)
                       but NOT in PERMIT_ISSUED.flows for GC. Structural analog
                       to L'Ambiance Plaza: D1 execution attempted from a state
                       where engineering authorization gate not completed.
  A02 — JURISDICTION:  GC calls B4_PermitIssuance (issue_permit). B4 not in
                       GC vocab anywhere — only PlanReviewer has B4 authority.
                       IBC Section 105: absolute prohibition of GC self-permit.
  A03 — BURST_CADENCE: GC rapid progression PERMIT_ISSUED(1) → SITE_PREP(2) →
                       FOUNDATION(3) → STRUCTURAL_FRAMING(4). Three monotonic
                       expansions = BURST. L'Ambiance analog: rapid construction
                       without inspection hold completion.
  A04 — EXIT:          Second GC presents on project already bound to first GC.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean GC progression, 70s spacing, no HYSTERESIS.
  B02 — ORDER → HYSTERESIS: GC ORDER fires, then admissible D1 to unvisited.
  B03 — JURISDICTION → HYSTERESIS: GC admissible C1, then B4 (JURISDICTION),
                                    then D1 to unvisited FOUNDATION.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST (separate projects).
  C02 — JURISDICTION ×2 — FireMarshal has only E2 at FINAL_INSPECTION; any
                          other action class fires JURISDICTION.
  C03 — EXIT then JURISDICTION (independent projects).

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")
from construction_compiler_v0_1 import run_session, ConstructionCompiler

BASE_TS = 9_000_000.0


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
    ORDER: GC calls D1_Structural (alter_shoring_sequence) from PERMIT_ISSUED
    state. D1 is in GC vocab (SITE_PREP, FOUNDATION, STRUCTURAL_FRAMING) but
    NOT in PERMIT_ISSUED.flows. Structural analog to L'Ambiance Plaza 1987:
    D1 lift-slab procedure change attempted without SER engineering
    authorization gate completion.
    """
    events = [
        # GC starts at PERMIT_ISSUED. D1 not in PERMIT_ISSUED.flows → ORDER
        {"actor_id": "gc_lambiance", "action": "alter_shoring_sequence", "project_id": "LAMBIANCE_A01", "timestamp": BASE_TS+0},
    ]
    return assert_pass("A01", "ORDER: GC calls D1_Structural from PERMIT_ISSUED (L'Ambiance analog)",
                       gate_result(events), "INADMISSIBLE", "ORDER", 0)


def test_A02():
    """
    JURISDICTION: GC calls B4_PermitIssuance (issue_permit). B4 not in GC
    vocab anywhere — only PlanReviewer has B4 authority. IBC Section 105:
    absolute prohibition of GC self-permit issuance.
    """
    events = [
        {"actor_id": "gc_a", "action": "issue_permit", "project_id": "SELF_PERMIT_A02", "timestamp": BASE_TS+0},
    ]
    return assert_pass("A02", "JURISDICTION: GC calls B4_PermitIssuance (IBC 105 self-permit prohibition)",
                       gate_result(events), "INADMISSIBLE", "JURISDICTION", 0)


def test_A03():
    """
    BURST_CADENCE: GC rapid progression through expanding state widths.
    PERMIT_ISSUED(1) → C1 → SITE_PREP(2)[+1]
    SITE_PREP(2) → D1 → FOUNDATION(3)[+1]
    FOUNDATION(3) → D1 → STRUCTURAL_FRAMING(4)[+1]
    = 3 expansions within BURST window = BURST_CADENCE fires.

    L'Ambiance structural analog: rapid construction progression without
    inspection hold completion at each tier.
    """
    t = BASE_TS
    events = [
        {"actor_id": "gc_lambiance", "action": "execute_site_preparation", "project_id": "BURST_A03", "timestamp": t+0},
        {"actor_id": "gc_lambiance", "action": "pour_foundation",          "project_id": "BURST_A03", "timestamp": t+1},
        {"actor_id": "gc_lambiance", "action": "erect_structural_framing", "project_id": "BURST_A03", "timestamp": t+2},
    ]
    results = gate_result(events)
    burst_fired = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in results)
    fired_at = next((idx for idx, (d, i) in enumerate(results)
                     if d == "INADMISSIBLE" and i == "BURST_CADENCE"), None)
    print(f"{'[PASS]' if burst_fired else '[FAIL]'} A03: BURST_CADENCE: GC rapid progression")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired


def test_A04():
    """EXIT: second GC presents on project already bound to first GC."""
    events = [
        {"actor_id": "gc_lambiance", "action": "execute_site_preparation", "project_id": "PROJ_A04", "timestamp": BASE_TS+0},
        {"actor_id": "gc_a",         "action": "execute_site_preparation", "project_id": "PROJ_A04", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A04", "EXIT: gc_a on project bound to gc_lambiance",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01():
    """
    Negative control: clean GC progression with 70s timestamp spacing
    to avoid false BURST during legitimate construction traversal.
    """
    t = BASE_TS
    events = [
        {"actor_id": "gc_a", "action": "execute_site_preparation", "project_id": "CLEAN_B01", "timestamp": t+0},
        {"actor_id": "gc_a", "action": "pour_foundation",          "project_id": "CLEAN_B01", "timestamp": t+70},
        {"actor_id": "gc_a", "action": "erect_structural_framing", "project_id": "CLEAN_B01", "timestamp": t+140},
    ]
    results = gate_result(events)
    ok = all(d == "ADMISSIBLE" for d, _ in results)
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Negative control — clean GC traversal, no HYSTERESIS")
    print(f"       decisions={[d for d, _ in results]}")
    return ok


def test_B02():
    """
    ORDER → HYSTERESIS: GC admissible C1 (visits SITE_PREP). Then GC tries
    D2_Envelope (install_weather_barrier) from SITE_PREP. D2 is in GC vocab
    (STRUCTURAL_FRAMING, ENVELOPE) but NOT in SITE_PREP.flows → ORDER.
    Then GC tries D1 (pour_foundation) from SITE_PREP → FOUNDATION (unvisited)
    → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Admissible: C1 → SITE_PREP (visits SITE_PREP)
        {"actor_id": "gc_lambiance", "action": "execute_site_preparation", "project_id": "HYST_B02", "timestamp": t+0},
        # ORDER: D2 in vocab but not in SITE_PREP.flows
        {"actor_id": "gc_lambiance", "action": "install_weather_barrier",  "project_id": "HYST_B02", "timestamp": t+70},
        # HYSTERESIS: D1 in SITE_PREP.flows → FOUNDATION (unvisited)
        {"actor_id": "gc_lambiance", "action": "pour_foundation",          "project_id": "HYST_B02", "timestamp": t+140},
    ]
    results = gate_result(events)
    order_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "ORDER"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = order_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER → HYSTERESIS (GC D2 from SITE_PREP, then D1 to unvisited)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


def test_B03():
    """
    JURISDICTION → HYSTERESIS: GC admissible C1 (visits SITE_PREP). Then GC
    calls B4 (issue_permit) — B4 not in GC vocab → JURISDICTION. Then GC
    tries D1 from SITE_PREP → FOUNDATION (unvisited) → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Admissible: visits SITE_PREP
        {"actor_id": "gc_a", "action": "execute_site_preparation", "project_id": "HYST_B03", "timestamp": t+0},
        # JURISDICTION: GC calls B4 (issue_permit) — not in GC vocab
        {"actor_id": "gc_a", "action": "issue_permit",             "project_id": "HYST_B03", "timestamp": t+70},
        # HYSTERESIS: D1 from SITE_PREP → FOUNDATION (unvisited)
        {"actor_id": "gc_a", "action": "pour_foundation",          "project_id": "HYST_B03", "timestamp": t+140},
    ]
    results = gate_result(events)
    juris_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = juris_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION → HYSTERESIS (GC B4, then D1 to unvisited)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01():
    """ORDER then BURST_CADENCE (separate projects, same compiler)."""
    t = BASE_TS
    order_events = [
        {"actor_id": "gc_lambiance", "action": "alter_shoring_sequence", "project_id": "ORDER_C01", "timestamp": t+0},
    ]
    burst_events = [
        {"actor_id": "gc_a", "action": "execute_site_preparation", "project_id": "BURST_C01", "timestamp": t+1000},
        {"actor_id": "gc_a", "action": "pour_foundation",          "project_id": "BURST_C01", "timestamp": t+1001},
        {"actor_id": "gc_a", "action": "erect_structural_framing", "project_id": "BURST_C01", "timestamp": t+1002},
    ]
    r_order = gate_result(order_events)
    r_burst = gate_result(burst_events)
    order_ok = r_order[0][0] == "INADMISSIBLE" and r_order[0][1] == "ORDER"
    burst_ok = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in r_burst)
    ok = order_ok and burst_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C01: ORDER then BURST_CADENCE (compound)")
    print(f"       ORDER: {r_order[0]}; BURST fired: {burst_ok}")
    return ok


def test_C02():
    """
    JURISDICTION ×2 — FireMarshal has only E2 at FINAL_INSPECTION; D1 and
    C1 not in FireMarshal vocab → JURISDICTION fires twice.
    """
    events = [
        {"actor_id": "fire_marshal", "action": "pour_foundation",          "project_id": "FM_C02", "timestamp": BASE_TS+0},
        {"actor_id": "fire_marshal", "action": "execute_site_preparation", "project_id": "FM_C02", "timestamp": BASE_TS+1},
    ]
    results = gate_result(events)
    j1 = results[0][0] == "INADMISSIBLE" and results[0][1] == "JURISDICTION"
    j2 = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    ok = j1 and j2
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION ×2 — FireMarshal calls D1 then C1")
    print(f"       step 1: {results[0]}, step 2: {results[1]}")
    return ok


def test_C03():
    """EXIT then JURISDICTION (independent projects)."""
    exit_events = [
        {"actor_id": "gc_lambiance", "action": "execute_site_preparation", "project_id": "EXIT_C03",  "timestamp": BASE_TS+0},
        {"actor_id": "gc_a",         "action": "execute_site_preparation", "project_id": "EXIT_C03",  "timestamp": BASE_TS+1},
    ]
    juris_events = [
        {"actor_id": "fire_marshal", "action": "issue_permit", "project_id": "JURIS_C03", "timestamp": BASE_TS+10},
    ]
    r_exit  = gate_result(exit_events)
    r_juris = gate_result(juris_events)
    exit_ok  = r_exit[1][0]  == "INADMISSIBLE" and r_exit[1][1]  == "EXIT"
    juris_ok = r_juris[0][0] == "INADMISSIBLE" and r_juris[0][1] == "JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION (independent projects)")
    print(f"       EXIT: {r_exit[1]}, JURISDICTION: {r_juris[0]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("Construction Pipeline Compiler v0.1 — Combinatorial Test Harness")
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
