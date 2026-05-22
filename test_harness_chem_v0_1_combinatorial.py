"""
Test Harness — Chemical / Industrial Process Compiler v0.1
Combinatorial — 10 tests (A01–A04, B01–B03, C01–C03)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project")
sys.path.insert(0, "/home/claude")

from chem_compiler_v0_1 import run_session

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

# A01 — ORDER (Texas City geometry)
def test_A01():
    # UO calls CP3_Startup from PSSR_COMPLETE — skips CP5_Authorize gate
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",               "unit_id": "u_a01", "timestamp": T0+0},
        {"actor_id": "uo_alpha", "action": "initiate_unit_startup",  "unit_id": "u_a01", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: UO calls CP3_Startup from PSSR_COMPLETE (skips CP5_Authorize gate)", r, "INADMISSIBLE", "ORDER", 1)

# A02 — JURISDICTION
def test_A02():
    # Process_Safety_Engineer calls CP2_Operate — not in PSE vocab
    events = [
        {"actor_id": "pse_alpha", "action": "read_dcs",         "unit_id": "u_a02", "timestamp": T0+0},
        {"actor_id": "pse_alpha", "action": "open_valve",       "unit_id": "u_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: PSE calls CP2_Operate (not in PSE vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three STARTUP_AUTHORIZED(w=2)→STARTUP_RUNNING(w=3) expansions within 60s
    t = T0
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",                "unit_id": "u_a03", "timestamp": t+0},
        {"actor_id": "uo_alpha", "action": "complete_pssr_sign_off",  "unit_id": "u_a03", "timestamp": t+1},
        # Exp 1: STARTUP_AUTHORIZED→STARTUP_RUNNING
        {"actor_id": "uo_alpha", "action": "begin_feed_introduction", "unit_id": "u_a03", "timestamp": t+2},
        # Contract: STARTUP_RUNNING→STARTUP_AUTHORIZED via CP5_Authorize
        {"actor_id": "uo_alpha", "action": "approve_continued_startup","unit_id":"u_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "uo_alpha", "action": "continue_startup_sequence","unit_id":"u_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "uo_alpha", "action": "issue_startup_permit",    "unit_id": "u_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "uo_alpha", "action": "fill_distillation_column","unit_id": "u_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three STARTUP_AUTHORIZED→STARTUP_RUNNING expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # bo_alpha takes over unit owned by uo_alpha
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",        "unit_id": "u_a04", "timestamp": T0+0},
        {"actor_id": "bo_alpha", "action": "check_temperature","unit_id": "u_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: bo_alpha pivots into unit owned by uo_alpha without handoff", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline (BURST-safe: only 2 expansions on clean path)
def test_B01():
    # IDLE(w=1)→PSSR_COMPLETE(w=2): exp 1
    # PSSR_COMPLETE(w=2)→STARTUP_AUTHORIZED(w=2): NOT expanding
    # STARTUP_AUTHORIZED(w=2)→STARTUP_RUNNING(w=3): exp 2
    # Only 2 expansions → no BURST risk, no timestamp spacing needed
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",                "unit_id": "u_b01", "timestamp": T0+0},
        {"actor_id": "uo_alpha", "action": "complete_pssr_sign_off",  "unit_id": "u_b01", "timestamp": T0+1},
        {"actor_id": "uo_alpha", "action": "begin_feed_introduction", "unit_id": "u_b01", "timestamp": T0+2},
        {"actor_id": "uo_alpha", "action": "adjust_flow_rate",        "unit_id": "u_b01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline — only 2 expansions on clean path, BURST-safe", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "uo_bravo", "action": "read_dcs",               "unit_id": "u_b02", "timestamp": T0+0},
        # ORDER: CP3_Startup from PSSR_COMPLETE
        {"actor_id": "uo_bravo", "action": "initiate_unit_startup",  "unit_id": "u_b02", "timestamp": T0+1},
        # Expand to STARTUP_AUTHORIZED (unvisited) → HYSTERESIS
        {"actor_id": "uo_bravo", "action": "complete_pssr_sign_off", "unit_id": "u_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited STARTUP_AUTHORIZED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",               "unit_id": "u_b03", "timestamp": T0+0},
        # JURISDICTION: CP6_Bypass not in any vocab
        {"actor_id": "uo_alpha", "action": "bypass_safety_interlock","unit_id": "u_b03", "timestamp": T0+1},
        # Expand to PSSR_COMPLETE (unvisited) → HYSTERESIS
        {"actor_id": "uo_alpha", "action": "complete_pssr_sign_off", "unit_id": "u_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited PSSR_COMPLETE at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    # Establish STARTUP_AUTHORIZED and STARTUP_RUNNING as visited first,
    # then ORDER fires, then burst in already-visited states
    t = T0
    events = [
        {"actor_id": "uo_alpha", "action": "read_dcs",                 "unit_id": "u_c01", "timestamp": t+0},
        {"actor_id": "uo_alpha", "action": "complete_pssr_sign_off",   "unit_id": "u_c01", "timestamp": t+1},
        # Exp 1: STARTUP_AUTHORIZED→STARTUP_RUNNING (visited)
        {"actor_id": "uo_alpha", "action": "begin_feed_introduction",  "unit_id": "u_c01", "timestamp": t+2},
        # Contract: STARTUP_RUNNING→STARTUP_AUTHORIZED
        {"actor_id": "uo_alpha", "action": "approve_continued_startup","unit_id": "u_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "uo_alpha", "action": "continue_startup_sequence","unit_id": "u_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "uo_alpha", "action": "issue_startup_permit",     "unit_id": "u_c01", "timestamp": t+5},
        # ORDER: CP2_Operate from STARTUP_AUTHORIZED (not in STARTUP_AUTHORIZED flows)
        {"actor_id": "uo_alpha", "action": "open_valve",               "unit_id": "u_c01", "timestamp": t+6},
        # Exp 3: STARTUP_AUTHORIZED→STARTUP_RUNNING — BURST fires; STARTUP_RUNNING visited → HYSTERESIS absent
        {"actor_id": "uo_alpha", "action": "fill_distillation_column", "unit_id": "u_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: CP2_Operate from STARTUP_AUTHORIZED", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd expansion; HYSTERESIS absent (STARTUP_RUNNING visited)", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "pse_alpha", "action": "read_dcs",               "unit_id": "u_c02",  "timestamp": T0+0},
        # JURISDICTION: PSE calls CP2_Operate
        {"actor_id": "pse_alpha", "action": "close_valve",            "unit_id": "u_c02",  "timestamp": T0+1},
        # Separate: ORDER — UO calls CP3_Startup from PSSR_COMPLETE
        {"actor_id": "uo_bravo",  "action": "read_dcs",               "unit_id": "u_c02b", "timestamp": T0+2},
        {"actor_id": "uo_bravo",  "action": "initiate_unit_startup",  "unit_id": "u_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: PSE calls CP2_Operate", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: UO calls CP3_Startup from PSSR_COMPLETE", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "uo_alpha",  "action": "read_dcs",         "unit_id": "u_c03",  "timestamp": T0+0},
        # EXIT: bo_alpha pivots into uo_alpha's unit
        {"actor_id": "bo_alpha",  "action": "check_temperature", "unit_id": "u_c03",  "timestamp": T0+1},
        # JURISDICTION: PSE calls CP2_Operate on separate unit
        {"actor_id": "pse_bravo", "action": "read_dcs",         "unit_id": "u_c03b", "timestamp": T0+2},
        {"actor_id": "pse_bravo", "action": "start_pump",       "unit_id": "u_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: bo_alpha pivots into uo_alpha's unit", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: PSE calls CP2_Operate", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 65)
    print("Chemical / Industrial Process Compiler v0.1 — Combinatorial Harness")
    print("=" * 65)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 65)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 65)
    with open("/home/claude/test_harness_chem_v0_1_results.json", "w") as f:
        json.dump({"harness": "chem_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
