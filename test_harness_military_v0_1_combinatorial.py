"""
Test Harness — Military Operational Compiler v0.1
Combinatorial — 10 tests (A01–A04, B01–B03, C01–C03)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project")
sys.path.insert(0, "/home/claude")

from military_compiler_v0_1 import run_session

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

# A01 — ORDER (Tarnak Farm geometry)
def test_A01():
    # SC advances to CONTACT via M2_Maneuver, then calls M3_Engage without ROE_CLEARED gate
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance", "op_id": "op_a01", "timestamp": T0+0},
        {"actor_id": "sc_alpha", "action": "advance_patrol",       "op_id": "op_a01", "timestamp": T0+1},
        # ORDER: M3_Engage from CONTACT (ROE_CLEARED not passed)
        {"actor_id": "sc_alpha", "action": "open_fire",            "op_id": "op_a01", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: SC calls M3_Engage from CONTACT without ROE_CLEARED gate (Tarnak Farm)", r, "INADMISSIBLE", "ORDER", 2)

# A02 — JURISDICTION
def test_A02():
    # Battle_Captain calls M3_Engage — not in BC vocab
    events = [
        {"actor_id": "bc_alpha", "action": "monitor_radio",    "op_id": "op_a02", "timestamp": T0+0},
        {"actor_id": "bc_alpha", "action": "request_cas",      "op_id": "op_a02", "timestamp": T0+1},
        {"actor_id": "bc_alpha", "action": "authorize_strike", "op_id": "op_a02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Battle_Captain calls M3_Engage (not in BC vocab)", r, "INADMISSIBLE", "JURISDICTION", 2)

# A03 — BURST_CADENCE
def test_A03():
    # Three CONTACT(w=3)→ROE_CLEARED(w=4) expansions within 60s
    # Contract path: ROE_CLEARED→CONTACT via M2_Maneuver
    t = T0
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance", "op_id": "op_a03", "timestamp": t+0},
        {"actor_id": "sc_alpha", "action": "advance_patrol",       "op_id": "op_a03", "timestamp": t+1},
        # Now in CONTACT
        # Exp 1: CONTACT(w=3)→ROE_CLEARED(w=4)
        {"actor_id": "sc_alpha", "action": "request_cas",          "op_id": "op_a03", "timestamp": t+2},
        # Contract: ROE_CLEARED→CONTACT via M2_Maneuver
        {"actor_id": "sc_alpha", "action": "change_position",      "op_id": "op_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "sc_alpha", "action": "coordinate_with_higher","op_id":"op_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "sc_alpha", "action": "take_cover",           "op_id": "op_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "sc_alpha", "action": "call_for_fire",        "op_id": "op_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three CONTACT→ROE_CLEARED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # pc_alpha takes over op owned by sc_alpha
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance", "op_id": "op_a04", "timestamp": T0+0},
        {"actor_id": "pc_alpha", "action": "advance_patrol",       "op_id": "op_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: pc_alpha pivots into op owned by sc_alpha without handoff", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # Clean path has three consecutive expansions: IDLE→PATROL→CONTACT→ROE_CLEARED
    # Timestamps must be spread beyond the 60s BURST_TIME_WINDOW to avoid BURST on clean path
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance", "op_id": "op_b01", "timestamp": T0+0},
        {"actor_id": "sc_alpha", "action": "advance_patrol",       "op_id": "op_b01", "timestamp": T0+70},
        {"actor_id": "sc_alpha", "action": "request_cas",          "op_id": "op_b01", "timestamp": T0+140},
        {"actor_id": "sc_alpha", "action": "engage_target",        "op_id": "op_b01", "timestamp": T0+210},
        {"actor_id": "sc_alpha", "action": "submit_sitrep",        "op_id": "op_b01", "timestamp": T0+280},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (timestamps spread beyond 60s BURST window)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "sc_bravo", "action": "conduct_surveillance", "op_id": "op_b02", "timestamp": T0+0},
        # ORDER: M3_Engage from PATROL (not in PATROL flows)
        {"actor_id": "sc_bravo", "action": "open_fire",            "op_id": "op_b02", "timestamp": T0+1},
        # Expand to CONTACT (unvisited) → HYSTERESIS
        {"actor_id": "sc_bravo", "action": "advance_patrol",       "op_id": "op_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited CONTACT at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance", "op_id": "op_b03", "timestamp": T0+0},
        # JURISDICTION: M6_Bypass not in any vocab
        {"actor_id": "sc_alpha", "action": "bypass_roe_clearance", "op_id": "op_b03", "timestamp": T0+1},
        # Expand to PATROL (unvisited) → HYSTERESIS
        {"actor_id": "sc_alpha", "action": "advance_patrol",       "op_id": "op_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited PATROL at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    # Establish CONTACT and ROE_CLEARED as visited first, then ORDER fires,
    # then burst oscillation in already-visited CONTACT↔ROE_CLEARED
    t = T0
    events = [
        {"actor_id": "sc_alpha", "action": "conduct_surveillance",  "op_id": "op_c01", "timestamp": t+0},
        {"actor_id": "sc_alpha", "action": "advance_patrol",        "op_id": "op_c01", "timestamp": t+1},
        # Exp 1: CONTACT→ROE_CLEARED (visited)
        {"actor_id": "sc_alpha", "action": "request_cas",           "op_id": "op_c01", "timestamp": t+2},
        # Contract: ROE_CLEARED→CONTACT
        {"actor_id": "sc_alpha", "action": "change_position",       "op_id": "op_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "sc_alpha", "action": "coordinate_with_higher","op_id": "op_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "sc_alpha", "action": "take_cover",            "op_id": "op_c01", "timestamp": t+5},
        # ORDER: M3_Engage from CONTACT (not in CONTACT flows)
        {"actor_id": "sc_alpha", "action": "deploy_weapons",        "op_id": "op_c01", "timestamp": t+6},
        # Exp 3: CONTACT→ROE_CLEARED — BURST fires; ROE_CLEARED visited → HYSTERESIS absent
        {"actor_id": "sc_alpha", "action": "call_for_fire",         "op_id": "op_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: M3_Engage from CONTACT", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd expansion; HYSTERESIS absent (ROE_CLEARED visited)", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "bc_alpha",  "action": "monitor_radio",        "op_id": "op_c02",  "timestamp": T0+0},
        # JURISDICTION: BC calls M3_Engage
        {"actor_id": "bc_alpha",  "action": "authorize_strike",     "op_id": "op_c02",  "timestamp": T0+1},
        # Separate: ORDER — SC calls M3_Engage from PATROL
        {"actor_id": "sc_bravo",  "action": "conduct_surveillance", "op_id": "op_c02b", "timestamp": T0+2},
        {"actor_id": "sc_bravo",  "action": "open_fire",            "op_id": "op_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: BC calls M3_Engage", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: SC calls M3_Engage from PATROL", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "sc_alpha",  "action": "conduct_surveillance", "op_id": "op_c03",  "timestamp": T0+0},
        # EXIT: pc_alpha pivots into sc_alpha's op
        {"actor_id": "pc_alpha",  "action": "advance_patrol",       "op_id": "op_c03",  "timestamp": T0+1},
        # JURISDICTION: BC calls M3_Engage on separate op
        {"actor_id": "bc_bravo",  "action": "monitor_radio",        "op_id": "op_c03b", "timestamp": T0+2},
        {"actor_id": "bc_bravo",  "action": "engage_target",        "op_id": "op_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: pc_alpha pivots into sc_alpha's op", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: BC calls M3_Engage", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 62)
    print("Military Operational Compiler v0.1 — Combinatorial Harness")
    print("=" * 62)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 62)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 62)
    with open("/home/claude/test_harness_military_v0_1_results.json", "w") as f:
        json.dump({"harness": "military_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
