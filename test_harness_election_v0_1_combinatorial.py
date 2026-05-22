"""
Test Harness — Election Administration Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from election_compiler_v0_1 import run_session

PASS_COUNT = 0; FAIL_COUNT = 0; RESULTS = []
T0 = 1000.0

def assert_pass(test_id, desc, results, decision, invariant, step):
    global PASS_COUNT, FAIL_COUNT
    r = results[step]
    ok = r.get("decision") == decision and r.get("invariant") == invariant
    label = "[PASS]" if ok else "[FAIL]"
    if ok: PASS_COUNT += 1
    else:  FAIL_COUNT += 1
    RESULTS.append({"test_id": test_id, "label": label, "description": desc,
                    "expected": {"decision": decision, "invariant": invariant},
                    "got": {"decision": r.get("decision"), "invariant": r.get("invariant")},
                    "step": step, "from_state": r.get("_stp",{}).get("FromState"),
                    "to_state": r.get("_stp",{}).get("ToState")})
    print(f"{label} {test_id} — {desc}")
    return ok

def assert_clean(test_id, desc, results):
    global PASS_COUNT, FAIL_COUNT
    violations = [r for r in results if r.get("decision") == "INADMISSIBLE"]
    ok = len(violations) == 0
    label = "[PASS]" if ok else "[FAIL]"
    if ok: PASS_COUNT += 1
    else:  FAIL_COUNT += 1
    RESULTS.append({"test_id": test_id, "label": label, "description": desc, "violations": violations})
    print(f"{label} {test_id} — {desc}")
    return ok

# A01 — ORDER (Florida 2000 geometry)
def test_A01():
    # Election_Supervisor calls E5_Certify from COUNTING (RECONCILED gate not passed)
    events = [
        {"actor_id": "supervisor_alpha", "action": "verify_voter_id",        "precinct_id": "p_a01", "timestamp": T0+0},
        {"actor_id": "supervisor_alpha", "action": "tabulate_ballot",        "precinct_id": "p_a01", "timestamp": T0+1},
        {"actor_id": "supervisor_alpha", "action": "certify_precinct_total", "precinct_id": "p_a01", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: Supervisor calls E5_Certify from COUNTING (Florida 2000 geometry)", r, "INADMISSIBLE", "ORDER", 2)

# A02 — JURISDICTION
def test_A02():
    # Observer attempts E3_Count — not in Observer vocab
    events = [
        {"actor_id": "observer_alpha", "action": "verify_voter_id",   "precinct_id": "p_a02", "timestamp": T0+0},
        {"actor_id": "observer_alpha", "action": "tabulate_ballot",   "precinct_id": "p_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Observer calls E3_Count (not in Observer vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three COUNTING(w=2)→DISPUTED(w=3) expansions within 60s
    t = T0
    events = [
        {"actor_id": "canvasser_alpha", "action": "verify_voter_id",         "precinct_id": "p_a03", "timestamp": t+0},
        {"actor_id": "canvasser_alpha", "action": "tabulate_ballot",         "precinct_id": "p_a03", "timestamp": t+1},
        # Exp 1: COUNTING→DISPUTED
        {"actor_id": "canvasser_alpha", "action": "log_ballot_dispute",      "precinct_id": "p_a03", "timestamp": t+2},
        # Contract: DISPUTED→COUNTING via E1_Verify
        {"actor_id": "canvasser_alpha", "action": "witness_count",           "precinct_id": "p_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "canvasser_alpha", "action": "determine_voter_intent",  "precinct_id": "p_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "canvasser_alpha", "action": "confirm_eligibility",     "precinct_id": "p_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "canvasser_alpha", "action": "rule_hanging_chad",       "precinct_id": "p_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three COUNTING→DISPUTED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # supervisor_alpha takes over precinct owned by canvasser_alpha
    events = [
        {"actor_id": "canvasser_alpha",  "action": "verify_voter_id", "precinct_id": "p_a04", "timestamp": T0+0},
        {"actor_id": "supervisor_alpha", "action": "tabulate_ballot", "precinct_id": "p_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: supervisor_alpha pivots into canvasser_alpha's precinct", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # Audit: IDLE(w=1)→INTAKE_OPEN(w=2): exp. INTAKE_OPEN→COUNTING(w=2→2): not exp. COUNTING→DISPUTED(w=2→3): exp.
    # Only 2 expansions on clean path → BURST-safe, no spacing needed
    events = [
        {"actor_id": "canvasser_alpha", "action": "verify_voter_id",        "precinct_id": "p_b01", "timestamp": T0+0},
        {"actor_id": "canvasser_alpha", "action": "tabulate_ballot",        "precinct_id": "p_b01", "timestamp": T0+1},
        {"actor_id": "canvasser_alpha", "action": "log_ballot_dispute",     "precinct_id": "p_b01", "timestamp": T0+2},
        {"actor_id": "canvasser_alpha", "action": "determine_voter_intent", "precinct_id": "p_b01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (only 2 expansions on clean path, BURST-safe)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "canvasser_bravo", "action": "verify_voter_id",       "precinct_id": "p_b02", "timestamp": T0+0},
        # ORDER: E4_Adjudicate from INTAKE_OPEN (not in INTAKE_OPEN flows)
        {"actor_id": "canvasser_bravo", "action": "rule_hanging_chad",     "precinct_id": "p_b02", "timestamp": T0+1},
        # Expand to COUNTING (unvisited) → HYSTERESIS
        {"actor_id": "canvasser_bravo", "action": "tabulate_ballot",       "precinct_id": "p_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited COUNTING at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "canvasser_alpha", "action": "verify_voter_id",        "precinct_id": "p_b03", "timestamp": T0+0},
        # JURISDICTION: E6_Bypass not in any vocab
        {"actor_id": "canvasser_alpha", "action": "modify_count_unauthorized","precinct_id":"p_b03","timestamp": T0+1},
        # Expand to INTAKE_OPEN (unvisited) → HYSTERESIS
        {"actor_id": "canvasser_alpha", "action": "tabulate_ballot",        "precinct_id": "p_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited COUNTING at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    t = T0
    events = [
        {"actor_id": "canvasser_alpha", "action": "verify_voter_id",         "precinct_id": "p_c01", "timestamp": t+0},
        {"actor_id": "canvasser_alpha", "action": "tabulate_ballot",         "precinct_id": "p_c01", "timestamp": t+1},
        # Exp 1: COUNTING→DISPUTED (visited)
        {"actor_id": "canvasser_alpha", "action": "log_ballot_dispute",      "precinct_id": "p_c01", "timestamp": t+2},
        # Contract: DISPUTED→COUNTING
        {"actor_id": "canvasser_alpha", "action": "witness_count",           "precinct_id": "p_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "canvasser_alpha", "action": "determine_voter_intent",  "precinct_id": "p_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "canvasser_alpha", "action": "confirm_eligibility",     "precinct_id": "p_c01", "timestamp": t+5},
        # ORDER: E2_Distribute from COUNTING (not in Canvasser vocab → JURISDICTION actually)
        # Better: use E5_Certify which is action in Supervisor vocab but not Canvasser → JURISDICTION
        # For ORDER we need: action in Canvasser vocab but wrong state.
        # E1_Verify, E3_Count, E4_Adjudicate all in COUNTING. None give ORDER from COUNTING.
        # Need a Canvasser action that is in vocab but not in COUNTING.
        # E1_Verify, E3_Count, E4_Adjudicate — all in COUNTING.
        # From DISPUTED — E1, E3, E4 valid.
        # So Canvasser doesn't have a state-restricted action.
        # Switch to supervisor: from COUNTING, E5_Certify is in Supervisor vocab (RECONCILED) but not COUNTING → ORDER
        {"actor_id": "supervisor_alpha", "action": "verify_voter_id",        "precinct_id": "p_c01s","timestamp": t+6},
        {"actor_id": "supervisor_alpha", "action": "tabulate_ballot",        "precinct_id": "p_c01s","timestamp": t+7},
        # ORDER: E5_Certify from COUNTING
        {"actor_id": "supervisor_alpha", "action": "certify_precinct_total", "precinct_id": "p_c01s","timestamp": t+8},
        # Then continue canvasser_alpha burst — exp 3
        {"actor_id": "canvasser_alpha", "action": "review_overvote",         "precinct_id": "p_c01", "timestamp": t+9},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 8: Supervisor calls E5_Certify from COUNTING", r, "INADMISSIBLE", "ORDER", 8)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 9: 3rd COUNTING→DISPUTED expansion (canvasser_alpha); HYSTERESIS absent", r, "INADMISSIBLE", "BURST_CADENCE", 9)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "observer_alpha",   "action": "verify_voter_id",        "precinct_id": "p_c02",  "timestamp": T0+0},
        # JURISDICTION: Observer calls E3_Count
        {"actor_id": "observer_alpha",   "action": "tabulate_ballot",        "precinct_id": "p_c02",  "timestamp": T0+1},
        # ORDER: Supervisor calls E5_Certify from COUNTING
        {"actor_id": "supervisor_bravo", "action": "verify_voter_id",        "precinct_id": "p_c02b", "timestamp": T0+2},
        {"actor_id": "supervisor_bravo", "action": "tabulate_ballot",        "precinct_id": "p_c02b", "timestamp": T0+3},
        {"actor_id": "supervisor_bravo", "action": "certify_precinct_total", "precinct_id": "p_c02b", "timestamp": T0+4},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: Observer calls E3_Count", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 4: Supervisor calls E5_Certify from COUNTING", r, "INADMISSIBLE", "ORDER", 4)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "canvasser_alpha",  "action": "verify_voter_id",        "precinct_id": "p_c03",  "timestamp": T0+0},
        # EXIT: supervisor_alpha pivots into canvasser_alpha's precinct
        {"actor_id": "supervisor_alpha", "action": "tabulate_ballot",        "precinct_id": "p_c03",  "timestamp": T0+1},
        # JURISDICTION: Observer calls E3_Count on separate precinct
        {"actor_id": "observer_bravo",   "action": "verify_voter_id",        "precinct_id": "p_c03b", "timestamp": T0+2},
        {"actor_id": "observer_bravo",   "action": "tabulate_ballot",        "precinct_id": "p_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: supervisor_alpha pivots into canvasser_alpha's precinct", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: Observer calls E3_Count", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 62)
    print("Election Administration Compiler v0.1 — Combinatorial Harness")
    print("=" * 62)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 62)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 62)
    with open("/home/claude/test_harness_election_v0_1_results.json", "w") as f:
        json.dump({"harness": "election_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
