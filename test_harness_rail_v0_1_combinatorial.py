"""
Test Harness — Rail Operations Compiler v0.1
Combinatorial — 10 tests (A01–A04, B01–B03, C01–C03)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project")
sys.path.insert(0, "/home/claude")

from rail_compiler_v0_1 import run_session

PASS_COUNT = 0; FAIL_COUNT = 0; RESULTS = []
T0 = 1000.0

def assert_pass(test_id, desc, results, decision, invariant, step):
    global PASS_COUNT, FAIL_COUNT
    r  = results[step]
    ok = r.get("decision") == decision and r.get("invariant") == invariant
    label = "[PASS]" if ok else "[FAIL]"
    if ok: PASS_COUNT += 1
    else:  FAIL_COUNT += 1
    entry = {"test_id": test_id, "label": label, "description": desc,
             "expected": {"decision": decision, "invariant": invariant},
             "got": {"decision": r.get("decision"), "invariant": r.get("invariant")},
             "step": step, "from_state": r.get("_stp",{}).get("FromState"),
             "to_state": r.get("_stp",{}).get("ToState")}
    RESULTS.append(entry)
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

# A01 — ORDER
def test_A01():
    # LE calls R3_Secure from AUTHORIZED (skips OPERATING — must R2_Operate first)
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",      "consist_id": "c_a01", "timestamp": T0+0},
        {"actor_id": "engineer_alpha", "action": "request_track_authority","consist_id":"c_a01","timestamp": T0+1},
        {"actor_id": "engineer_alpha", "action": "secure_consist",      "consist_id": "c_a01", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: LE calls R3_Secure from AUTHORIZED (R3 not in AUTHORIZED flows)", r, "INADMISSIBLE", "ORDER", 2)

# A02 — JURISDICTION
def test_A02():
    # fire_dept_megantic calls R2_Operate (not in MoW_Supervisor vocab)
    events = [
        {"actor_id": "fire_dept_megantic", "action": "check_signals",         "consist_id": "c_a02", "timestamp": T0+0},
        {"actor_id": "fire_dept_megantic", "action": "apply_independent_brake","consist_id":"c_a02","timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: fire_dept_megantic calls R2_Operate (not in MoW_Supervisor vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three AUTHORIZED(w=2)→OPERATING(w=3) expansions within 60s
    t = T0
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",          "consist_id": "c_a03", "timestamp": t+0},
        {"actor_id": "engineer_alpha", "action": "request_track_authority","consist_id": "c_a03", "timestamp": t+1},
        # Exp 1: AUTHORIZED→OPERATING
        {"actor_id": "engineer_alpha", "action": "initiate_movement",      "consist_id": "c_a03", "timestamp": t+2},
        # Contract: OPERATING→AUTHORIZED
        {"actor_id": "engineer_alpha", "action": "issue_form_b_clearance", "consist_id": "c_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "engineer_alpha", "action": "control_speed",          "consist_id": "c_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "engineer_alpha", "action": "confirm_securement",     "consist_id": "c_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "engineer_alpha", "action": "advance_throttle",       "consist_id": "c_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three AUTHORIZED→OPERATING expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # conductor_alpha takes over consist owned by engineer_alpha
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",      "consist_id": "c_a04", "timestamp": T0+0},
        {"actor_id": "conductor_alpha", "action": "read_track_order",  "consist_id": "c_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: conductor_alpha pivots into consist owned by engineer_alpha", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",          "consist_id": "c_b01", "timestamp": T0+0},
        {"actor_id": "engineer_alpha", "action": "request_track_authority","consist_id": "c_b01", "timestamp": T0+1},
        {"actor_id": "engineer_alpha", "action": "initiate_movement",      "consist_id": "c_b01", "timestamp": T0+2},
        {"actor_id": "engineer_alpha", "action": "secure_consist",         "consist_id": "c_b01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "engineer_bravo", "action": "check_signals",      "consist_id": "c_b02", "timestamp": T0+0},
        # ORDER: R3_Secure from PRE_DEPARTURE (not in PRE_DEPARTURE flows)
        {"actor_id": "engineer_bravo", "action": "secure_consist",     "consist_id": "c_b02", "timestamp": T0+1},
        # Expand to AUTHORIZED (unvisited) → HYSTERESIS
        {"actor_id": "engineer_bravo", "action": "request_track_authority","consist_id":"c_b02","timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited AUTHORIZED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",       "consist_id": "c_b03", "timestamp": T0+0},
        # JURISDICTION: R6_Bypass not in any vocab
        {"actor_id": "engineer_alpha", "action": "bypass_tod_system",   "consist_id": "c_b03", "timestamp": T0+1},
        # Expand to PRE_DEPARTURE (unvisited) → HYSTERESIS
        {"actor_id": "engineer_alpha", "action": "request_track_authority","consist_id":"c_b03","timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited PRE_DEPARTURE at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    # Establish AUTHORIZED and OPERATING as visited states first, then ORDER fires,
    # then burst oscillation in already-visited AUTHORIZED↔OPERATING
    t = T0
    events = [
        {"actor_id": "engineer_alpha", "action": "check_signals",          "consist_id": "c_c01", "timestamp": t+0},
        {"actor_id": "engineer_alpha", "action": "request_track_authority","consist_id": "c_c01", "timestamp": t+1},
        # Exp 1: AUTHORIZED→OPERATING (visited)
        {"actor_id": "engineer_alpha", "action": "initiate_movement",      "consist_id": "c_c01", "timestamp": t+2},
        # Contract: OPERATING→AUTHORIZED
        {"actor_id": "engineer_alpha", "action": "confirm_securement",     "consist_id": "c_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "engineer_alpha", "action": "control_speed",          "consist_id": "c_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "engineer_alpha", "action": "issue_form_b_clearance", "consist_id": "c_c01", "timestamp": t+5},
        # ORDER: R3_Secure from AUTHORIZED (not in AUTHORIZED flows)
        {"actor_id": "engineer_alpha", "action": "apply_handbrake",        "consist_id": "c_c01", "timestamp": t+6},
        # Exp 3 — BURST fires; OPERATING is visited → HYSTERESIS absent
        {"actor_id": "engineer_alpha", "action": "advance_throttle",       "consist_id": "c_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: R3_Secure from AUTHORIZED", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd expansion; HYSTERESIS absent (OPERATING visited)", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "fire_dept_megantic", "action": "check_signals",          "consist_id": "c_c02",  "timestamp": T0+0},
        # JURISDICTION: MoW_Supervisor calls R2_Operate
        {"actor_id": "fire_dept_megantic", "action": "apply_dynamic_brake",    "consist_id": "c_c02",  "timestamp": T0+1},
        # Separate: ORDER — LE calls R3_Secure from PRE_DEPARTURE
        {"actor_id": "engineer_bravo",     "action": "check_signals",          "consist_id": "c_c02b", "timestamp": T0+2},
        {"actor_id": "engineer_bravo",     "action": "secure_consist",         "consist_id": "c_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: MoW_Supervisor calls R2_Operate", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: LE calls R3_Secure from PRE_DEPARTURE", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "engineer_alpha",     "action": "check_signals",         "consist_id": "c_c03",  "timestamp": T0+0},
        # EXIT: conductor_alpha pivots into engineer_alpha's consist
        {"actor_id": "conductor_alpha",    "action": "read_track_order",      "consist_id": "c_c03",  "timestamp": T0+1},
        # JURISDICTION: fire dept calls R2_Operate on separate consist
        {"actor_id": "fire_dept_megantic", "action": "check_signals",         "consist_id": "c_c03b", "timestamp": T0+2},
        {"actor_id": "fire_dept_megantic", "action": "release_brake",         "consist_id": "c_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: conductor_alpha pivots into engineer_alpha's consist", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: fire_dept calls R2_Operate", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 60)
    print("Rail Operations Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 60)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 60)
    with open("/home/claude/test_harness_rail_v0_1_results.json", "w") as f:
        json.dump({"harness": "rail_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
