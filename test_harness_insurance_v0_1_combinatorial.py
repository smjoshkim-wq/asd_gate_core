"""
Test Harness — Insurance Claims Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from insurance_compiler_v0_1 import run_session

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

# A01 — ORDER (Katrina geometry)
def test_A01():
    # Supervisor calls IC3_Decide from INTAKE_RECEIVED (skipping IC2_Assess)
    events = [
        {"actor_id": "supervisor_alpha", "action": "file_claim",        "claim_id": "cl_a01", "timestamp": T0+0},
        {"actor_id": "supervisor_alpha", "action": "issue_denial",      "claim_id": "cl_a01", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: Supervisor calls IC3_Decide from INTAKE_RECEIVED (Katrina geometry)", r, "INADMISSIBLE", "ORDER", 1)

# A02 — JURISDICTION
def test_A02():
    # CIA attempts IC3_Decide — not in CIA vocab
    events = [
        {"actor_id": "cia_alpha", "action": "file_claim",        "claim_id": "cl_a02", "timestamp": T0+0},
        {"actor_id": "cia_alpha", "action": "authorize_payment", "claim_id": "cl_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: CIA calls IC3_Decide (not in CIA vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three ASSESSED(w=2)→DECIDED(w=3) expansions within 60s (Claims_Supervisor)
    t = T0
    events = [
        {"actor_id": "supervisor_alpha", "action": "file_claim",              "claim_id": "cl_a03", "timestamp": t+0},
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",          "claim_id": "cl_a03", "timestamp": t+1},
        # Exp 1: ASSESSED→DECIDED
        {"actor_id": "supervisor_alpha", "action": "authorize_payment",       "claim_id": "cl_a03", "timestamp": t+2},
        # Contract: DECIDED→ASSESSED via IC2_Assess
        {"actor_id": "supervisor_alpha", "action": "review_policy_coverage",  "claim_id": "cl_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "supervisor_alpha", "action": "issue_denial",            "claim_id": "cl_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "supervisor_alpha", "action": "calculate_depreciation",  "claim_id": "cl_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "supervisor_alpha", "action": "approve_partial_settlement","claim_id":"cl_a03","timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three ASSESSED→DECIDED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # supervisor_alpha takes over claim owned by adjuster_alpha
    events = [
        {"actor_id": "adjuster_alpha",   "action": "file_claim",         "claim_id": "cl_a04", "timestamp": T0+0},
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",     "claim_id": "cl_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: supervisor_alpha pivots into adjuster_alpha's claim", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # Supervisor clean: IDLE(w=1)→INTAKE_RECEIVED(w=2): exp 1
    # INTAKE_RECEIVED(w=2)→ASSESSED(w=2): not exp
    # ASSESSED(w=2)→DECIDED(w=3): exp 2
    # Only 2 expansions → BURST-safe
    events = [
        {"actor_id": "supervisor_alpha", "action": "file_claim",         "claim_id": "cl_b01", "timestamp": T0+0},
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",     "claim_id": "cl_b01", "timestamp": T0+1},
        {"actor_id": "supervisor_alpha", "action": "authorize_payment",  "claim_id": "cl_b01", "timestamp": T0+2},
        {"actor_id": "supervisor_alpha", "action": "make_settlement_offer","claim_id":"cl_b01","timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (2 expansions on clean path, BURST-safe)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "supervisor_bravo", "action": "file_claim",        "claim_id": "cl_b02", "timestamp": T0+0},
        # ORDER: IC3_Decide from INTAKE_RECEIVED
        {"actor_id": "supervisor_bravo", "action": "issue_denial",      "claim_id": "cl_b02", "timestamp": T0+1},
        # Expand to ASSESSED (unvisited) → HYSTERESIS
        {"actor_id": "supervisor_bravo", "action": "inspect_damage",    "claim_id": "cl_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited ASSESSED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "supervisor_alpha", "action": "file_claim",         "claim_id": "cl_b03", "timestamp": T0+0},
        # JURISDICTION: IC6_Bypass not in any vocab
        {"actor_id": "supervisor_alpha", "action": "deny_without_basis", "claim_id": "cl_b03", "timestamp": T0+1},
        # Expand to ASSESSED (unvisited) → HYSTERESIS
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",     "claim_id": "cl_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited ASSESSED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    t = T0
    events = [
        {"actor_id": "supervisor_alpha", "action": "file_claim",              "claim_id": "cl_c01", "timestamp": t+0},
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",          "claim_id": "cl_c01", "timestamp": t+1},
        # Exp 1: ASSESSED→DECIDED (visited)
        {"actor_id": "supervisor_alpha", "action": "authorize_payment",       "claim_id": "cl_c01", "timestamp": t+2},
        # Contract
        {"actor_id": "supervisor_alpha", "action": "review_policy_coverage",  "claim_id": "cl_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "supervisor_alpha", "action": "issue_denial",            "claim_id": "cl_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "supervisor_alpha", "action": "calculate_depreciation",  "claim_id": "cl_c01", "timestamp": t+5},
        # ORDER: IC4_Escalate from ASSESSED (not in Supervisor's ASSESSED flows)
        {"actor_id": "supervisor_alpha", "action": "refer_to_legal",          "claim_id": "cl_c01", "timestamp": t+6},
        # Exp 3: ASSESSED→DECIDED — BURST fires; DECIDED visited → HYSTERESIS absent
        {"actor_id": "supervisor_alpha", "action": "make_settlement_offer",   "claim_id": "cl_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: IC4_Escalate from ASSESSED (Supervisor)", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd ASSESSED→DECIDED; HYSTERESIS absent", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "cia_alpha",        "action": "file_claim",        "claim_id": "cl_c02",  "timestamp": T0+0},
        # JURISDICTION: CIA calls IC3_Decide
        {"actor_id": "cia_alpha",        "action": "issue_denial",      "claim_id": "cl_c02",  "timestamp": T0+1},
        # ORDER: Supervisor calls IC3_Decide from INTAKE_RECEIVED on separate claim
        {"actor_id": "supervisor_bravo", "action": "file_claim",        "claim_id": "cl_c02b", "timestamp": T0+2},
        {"actor_id": "supervisor_bravo", "action": "authorize_payment", "claim_id": "cl_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: CIA calls IC3_Decide", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: Supervisor calls IC3_Decide from INTAKE_RECEIVED", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "adjuster_alpha",   "action": "file_claim",        "claim_id": "cl_c03",  "timestamp": T0+0},
        # EXIT: supervisor_alpha pivots into adjuster_alpha's claim
        {"actor_id": "supervisor_alpha", "action": "inspect_damage",    "claim_id": "cl_c03",  "timestamp": T0+1},
        # JURISDICTION: CIA calls IC3_Decide on separate claim
        {"actor_id": "cia_bravo",        "action": "file_claim",        "claim_id": "cl_c03b", "timestamp": T0+2},
        {"actor_id": "cia_bravo",        "action": "make_settlement_offer","claim_id":"cl_c03b","timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: supervisor_alpha pivots into adjuster_alpha's claim", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: CIA calls IC3_Decide", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 60)
    print("Insurance Claims Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 60)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 60)
    with open("/home/claude/test_harness_insurance_v0_1_results.json", "w") as f:
        json.dump({"harness": "insurance_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
