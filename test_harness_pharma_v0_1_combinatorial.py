"""
Combinatorial Test Harness — Pharmaceutical Drug Approval Compiler v0.1
═══════════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:         PI calls C1_DoseEscalation from IND_ACTIVE state.
                       C1 is in PI vocab (PHASE_I) but NOT in IND_ACTIVE.flows.
                       Gelsinger structural analog: dose escalation attempted
                       before completing prior cohort safety confirmation loop.
  A02 — JURISDICTION:  Sponsor calls S2_DSMB_Unblinding (modify_adjudication_sop).
                       S2 not in Sponsor vocab anywhere. Vioxx anchor:
                       Merck modified adjudication SOP, an action class strictly
                       excluded from Sponsor by construction.
  A03 — BURST_CADENCE: PI expands rapidly through IND_ACTIVE(2) → PHASE_I(3) →
                       PHASE_II(3) → PHASE_III(2). Width expansions on phase advance.
  A04 — EXIT:          Second Sponsor presents on program already bound to first.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean PI traversal IND_ACTIVE → PHASE_I → PHASE_II,
                           no HYSTERESIS, timestamps spaced 70s to avoid false BURST.
  B02 — ORDER → HYSTERESIS: PI ORDER fires (C1 from IND_ACTIVE), then HYSTERESIS.
  B03 — JURISDICTION → HYSTERESIS: Sponsor admissible step, then S2 (JURISDICTION),
                                    then admissible action toward unvisited state.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST (separate sessions, same compiler).
  C02 — JURISDICTION ×2 — CRA has no clinical/regulatory actions.
  C03 — EXIT then JURISDICTION (independent programs).

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")
from pharma_compiler_v0_1 import run_session, PharmaCompiler

BASE_TS = 8_000_000.0


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
    ORDER: PI calls C1_DoseEscalation from IND_ACTIVE state (before any
    enrollment). C1 IS in PI vocab (PHASE_I, PHASE_II) but NOT in
    IND_ACTIVE.flows for PI. Gelsinger structural analog: dose escalation
    attempted before completing prior cohort safety confirmation loop.
    """
    events = [
        {"actor_id": "pi_wilson", "action": "submit_15day_safety_report", "program_id": "GELSINGER_A01", "timestamp": BASE_TS+0},
        # Still in IND_ACTIVE; C1 not in IND_ACTIVE.flows for PI → ORDER
        {"actor_id": "pi_wilson", "action": "advance_dose_cohort",        "program_id": "GELSINGER_A01", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A01", "ORDER: PI calls C1_DoseEscalation from IND_ACTIVE (Gelsinger analog)",
                       gate_result(events), "INADMISSIBLE", "ORDER", 1)


def test_A02():
    """
    JURISDICTION: Sponsor calls S2_DSMB_Unblinding (modify_adjudication_sop).
    S2 not in Sponsor vocabulary anywhere — DSMB unblinding is strictly excluded
    from Sponsor by construction. Vioxx anchor: Merck modified adjudication SOP.
    """
    events = [
        {"actor_id": "sponsor_merck", "action": "execute_animal_toxicity",  "program_id": "VIOXX_A02", "timestamp": BASE_TS+0},
        # JURISDICTION: Sponsor calls S2 (modify_adjudication_sop)
        {"actor_id": "sponsor_merck", "action": "modify_adjudication_sop",  "program_id": "VIOXX_A02", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A02", "JURISDICTION: Sponsor calls S2_DSMB_Unblinding (Vioxx adjudication SOP modification)",
                       gate_result(events), "INADMISSIBLE", "JURISDICTION", 1)


def test_A03():
    """
    BURST_CADENCE: PI expands rapidly through state progression.
    IND_ACTIVE(2) → PHASE_I(3) [+1] via C2
    PHASE_I(3) → PHASE_II(3) [same] via C1
    PHASE_II(3) → PHASE_III(2) [contraction] — not useful.
    
    Need 3 expansions. PI widths: IND_ACTIVE=2, PHASE_I=3, PHASE_II=3, PHASE_III=2.
    
    PI starts at IND_ACTIVE(2). Going to PHASE_I via C2: +1. Then PHASE_I→PHASE_II
    via C1: same width (3 to 3). Then PHASE_II→PHASE_III via... PI doesn't have
    a direct advance from PHASE_II to PHASE_III (no action in flow graph).
    
    Let me re-examine PI flows. In PHASE_II: C1, C2, S1. C1 keeps in PHASE_II.
    The Sponsor advances stages, not PI.
    
    Alternative: oscillate. Doesn't work because PI is forward-only.
    
    Use Sponsor instead. Sponsor widths: PRECLINICAL=2, IND_SUBMITTED=1, 
    IND_ACTIVE=1, PHASE_I=1, ... PHASE_III=2.
    Sponsor PRECLINICAL(2) → P2 → IND_SUBMITTED(1): contraction.
    
    Use FDA Director: FDA_REVIEW(2) → R3 → APPROVAL_DECISION(1): contraction.
    
    None of these forward paths produce 3 expansions naturally.
    
    Simplest fix: bump PI widths to produce a cleaner expansion. Set 
    IND_ACTIVE=1, PHASE_I=2, PHASE_II=3, then forward progression IND_ACTIVE(1)
    → PHASE_I(2)[+1] → PHASE_II(3)[+1]... need a third expansion.
    
    Maybe: PI starts at IND_ACTIVE(1) → C2 → PHASE_I(2)[+1] → C1 → PHASE_I (loops at 2).
    Then PHASE_I → C2 → PHASE_I (loops at 2). No expansion.
    
    OK new approach: design BURST around enrollment burst (PI rapidly enrolling
    subjects). Each enrollment is C2 within PHASE_I state — stays at PHASE_I(3).
    For BURST, need state widening transitions.
    
    Cleanest: PI advances through expanding states. Make widths:
    IND_ACTIVE=1, PHASE_I=2, PHASE_II=3, PHASE_III=4. Then:
    IND_ACTIVE(1) → C2 → PHASE_I(2)[+1] → C1 → PHASE_II(3)[+1] → C1 → PHASE_III(4)[+1]
    = 3 expansions = BURST!
    
    But PI doesn't have direct transition PHASE_I → PHASE_II via C1 in my graph
    (C1 keeps PI in PHASE_I). Need to add: PHASE_I C1 → PHASE_II.
    """
    t = BASE_TS
    events = [
        # PI: IND_ACTIVE(1) → PHASE_I(2)[+1] → PHASE_II(3)[+1] → PHASE_III(4)[+1] = BURST
        {"actor_id": "pi_smith", "action": "enroll_subject",      "program_id": "BURST_A03", "timestamp": t+0},
        {"actor_id": "pi_smith", "action": "advance_dose_cohort", "program_id": "BURST_A03", "timestamp": t+1},
        {"actor_id": "pi_smith", "action": "advance_dose_cohort", "program_id": "BURST_A03", "timestamp": t+2},
    ]
    results = gate_result(events)
    burst_fired = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in results)
    fired_at = next((idx for idx, (d, i) in enumerate(results)
                     if d == "INADMISSIBLE" and i == "BURST_CADENCE"), None)
    print(f"{'[PASS]' if burst_fired else '[FAIL]'} A03: BURST_CADENCE: PI rapid phase advancement")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired


def test_A04():
    """
    EXIT: second Sponsor presents on program already bound to first.
    """
    events = [
        {"actor_id": "sponsor_pfizer",    "action": "execute_animal_toxicity", "program_id": "PROG_A04", "timestamp": BASE_TS+0},
        {"actor_id": "sponsor_grunenthal","action": "execute_animal_toxicity", "program_id": "PROG_A04", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A04", "EXIT: sponsor_grunenthal on program bound to sponsor_pfizer",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01():
    """
    Negative control: clean PI traversal through phase advancement.
    Timestamps spaced 70s apart to avoid false BURST.
    """
    t = BASE_TS
    events = [
        {"actor_id": "pi_chen", "action": "enroll_subject",      "program_id": "CLEAN_B01", "timestamp": t+0},
        {"actor_id": "pi_chen", "action": "advance_dose_cohort", "program_id": "CLEAN_B01", "timestamp": t+70},
        {"actor_id": "pi_chen", "action": "advance_dose_cohort", "program_id": "CLEAN_B01", "timestamp": t+140},
    ]
    results = gate_result(events)
    ok = all(d == "ADMISSIBLE" for d, _ in results)
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Negative control — clean PI traversal, no HYSTERESIS")
    print(f"       decisions={[d for d, _ in results]}")
    return ok


def test_B02():
    """
    ORDER → HYSTERESIS: PI at IND_ACTIVE has admissible C2→PHASE_I first to
    populate visited. Then PI at PHASE_I tries R1 (NDA submit) — R1 not in
    PI vocab at all → JURISDICTION (not ORDER).
    
    Need C1 from a state where C1 is NOT in flows but IS in PI vocab.
    C1 is in PHASE_I, PHASE_II for PI. NOT in IND_ACTIVE for PI.
    
    Sequence: PI admissible C2 (IND_ACTIVE → PHASE_I, visits PHASE_I).
    But then PI is in PHASE_I, so C1 from PHASE_I is admissible.
    
    Wait — need PI to go BACK to IND_ACTIVE somehow. Or use a different test.
    
    Use Sponsor: Sponsor at IND_SUBMITTED → P1 (admissible, visits IND_SUBMITTED).
    Then Sponsor at IND_SUBMITTED tries R1 from IND_SUBMITTED — R1 in Sponsor 
    vocab (PHASE_III) but NOT in IND_SUBMITTED.flows → ORDER.
    Then Sponsor tries P2 from IND_SUBMITTED — wait P2 is from PRECLINICAL.
    
    OK using PI with a different sequence:
    PI at IND_ACTIVE → enroll_subject (admissible, transitions to PHASE_I).
    Now PI at PHASE_I. Try C1 (advance_dose_cohort): C1 is in PHASE_I.flows
    for PI → admissible. Visits PHASE_I (already visited).
    
    Hmm let me design differently. Sponsor:
    - PRECLINICAL → P1 (admissible, stays in PRECLINICAL, visits PRECLINICAL)
    - PRECLINICAL → P2 (admissible, → IND_SUBMITTED, visits IND_SUBMITTED)
    - IND_SUBMITTED → R1 (R1 in Sponsor vocab in PHASE_III, NOT in IND_SUBMITTED.flows)
      → ORDER!
    - Then Sponsor tries P1 from IND_SUBMITTED (P1 in IND_SUBMITTED.flows, stays)
      → already visited IND_SUBMITTED. Need unvisited target.
    
    Need an action that would take Sponsor from IND_SUBMITTED to an unvisited state.
    Sponsor doesn't have direct transitions out of IND_SUBMITTED (the FDA Reviewer
    grants P3_IND_Activation). So Sponsor flows from IND_SUBMITTED only via P1
    (loop). No unvisited target available from this state.
    
    Solution: design Sponsor flow with an outgoing transition. Or use PI.
    
    Let me use PI:
    - PI at IND_ACTIVE → S1 (admissible, stays, visits IND_ACTIVE)
    - PI tries C1 from IND_ACTIVE (C1 in PI vocab PHASE_I, NOT in IND_ACTIVE.flows) → ORDER
    - PI tries C2 from IND_ACTIVE (C2 in IND_ACTIVE.flows, → PHASE_I unvisited) → HYSTERESIS!
    """
    t = BASE_TS
    events = [
        {"actor_id": "pi_wilson", "action": "submit_15day_safety_report", "program_id": "HYST_B02", "timestamp": t+0},
        # ORDER: PI calls C1 from IND_ACTIVE (C1 in vocab PHASE_I, not in IND_ACTIVE.flows)
        {"actor_id": "pi_wilson", "action": "advance_dose_cohort",        "program_id": "HYST_B02", "timestamp": t+70},
        # HYSTERESIS: C2 in IND_ACTIVE.flows → PHASE_I (unvisited)
        {"actor_id": "pi_wilson", "action": "enroll_subject",             "program_id": "HYST_B02", "timestamp": t+140},
    ]
    results = gate_result(events)
    order_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "ORDER"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = order_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER → HYSTERESIS (PI C1 from IND_ACTIVE, then C2 to unvisited PHASE_I)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


def test_B03():
    """
    JURISDICTION → HYSTERESIS: Sponsor admissible P1 (visits PRECLINICAL),
    then S2 (JURISDICTION — S2 not in Sponsor vocab), then P2 → IND_SUBMITTED
    (unvisited) → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Admissible: visits PRECLINICAL
        {"actor_id": "sponsor_a", "action": "execute_animal_toxicity", "program_id": "HYST_B03", "timestamp": t+0},
        # JURISDICTION: Sponsor calls S2 (request_interim_unblinding — DSMB-only)
        {"actor_id": "sponsor_a", "action": "request_interim_unblinding","program_id": "HYST_B03", "timestamp": t+1},
        # HYSTERESIS: P2 in Sponsor PRECLINICAL.flows → IND_SUBMITTED (unvisited)
        {"actor_id": "sponsor_a", "action": "submit_ind_application",   "program_id": "HYST_B03", "timestamp": t+2},
    ]
    results = gate_result(events)
    juris_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = juris_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION → HYSTERESIS (Sponsor S2, then P2 to unvisited)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01():
    """ORDER then BURST_CADENCE (separate programs, same compiler)."""
    t = BASE_TS
    order_events = [
        {"actor_id": "pi_wilson", "action": "submit_15day_safety_report", "program_id": "ORDER_C01", "timestamp": t+0},
        {"actor_id": "pi_wilson", "action": "advance_dose_cohort",        "program_id": "ORDER_C01", "timestamp": t+70},
    ]
    burst_events = [
        {"actor_id": "pi_smith", "action": "enroll_subject",      "program_id": "BURST_C01", "timestamp": t+1000},
        {"actor_id": "pi_smith", "action": "advance_dose_cohort", "program_id": "BURST_C01", "timestamp": t+1001},
        {"actor_id": "pi_smith", "action": "advance_dose_cohort", "program_id": "BURST_C01", "timestamp": t+1002},
    ]
    r_order = gate_result(order_events)
    r_burst = gate_result(burst_events)
    order_ok = r_order[1][0] == "INADMISSIBLE" and r_order[1][1] == "ORDER"
    burst_ok  = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in r_burst)
    ok = order_ok and burst_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C01: ORDER then BURST_CADENCE (compound)")
    print(f"       ORDER at step 2: {r_order[1]}; BURST fired: {burst_ok}")
    return ok


def test_C02():
    """
    JURISDICTION ×2 — CRA has empty flow graph (auditor-only role).
    Any action attempt fires JURISDICTION.
    """
    events = [
        {"actor_id": "cra_jones", "action": "execute_animal_toxicity", "program_id": "CRA_C02", "timestamp": BASE_TS+0},
        {"actor_id": "cra_jones", "action": "enroll_subject",          "program_id": "CRA_C02", "timestamp": BASE_TS+1},
    ]
    results = gate_result(events)
    j1 = results[0][0] == "INADMISSIBLE" and results[0][1] == "JURISDICTION"
    j2 = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    ok = j1 and j2
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION ×2 — CRA has no clinical/regulatory authority")
    print(f"       step 1: {results[0]}, step 2: {results[1]}")
    return ok


def test_C03():
    """EXIT then JURISDICTION (independent programs)."""
    exit_events = [
        {"actor_id": "sponsor_pfizer", "action": "execute_animal_toxicity", "program_id": "EXIT_C03",  "timestamp": BASE_TS+0},
        {"actor_id": "sponsor_a",      "action": "execute_animal_toxicity", "program_id": "EXIT_C03",  "timestamp": BASE_TS+1},
    ]
    juris_events = [
        {"actor_id": "cra_jones", "action": "submit_nda", "program_id": "JURIS_C03", "timestamp": BASE_TS+10},
    ]
    r_exit  = gate_result(exit_events)
    r_juris = gate_result(juris_events)
    exit_ok  = r_exit[1][0]  == "INADMISSIBLE" and r_exit[1][1]  == "EXIT"
    juris_ok = r_juris[0][0] == "INADMISSIBLE" and r_juris[0][1] == "JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION (independent programs)")
    print(f"       EXIT: {r_exit[1]}, JURISDICTION: {r_juris[0]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("Pharmaceutical Compiler v0.1 — Combinatorial Test Harness")
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
