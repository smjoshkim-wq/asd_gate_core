"""
Test Harness — PACER Court Records Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from pacer_compiler_v0_1 import run_session

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

# A01 — ORDER (Theranos geometry)
def test_A01():
    # Judge calls PR4_Rule normally from IDLE/RULING. For ORDER from a state perspective,
    # Filing_Party doesn't have PR4 in vocab → JURISDICTION.
    # The Theranos geometry is structural: ruling before proper service.
    # Best ORDER for this domain: Filing_Party calls PR5_Seal from IDLE (PR5 not in IDLE flows but is in vocab for SERVED state)
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",            "case_id": "c_a01", "timestamp": T0+0},
        # ORDER: PR5_Seal from FILED (not in FILED flows; only valid from SERVED state)
        {"actor_id": "filing_alpha", "action": "motion_to_seal",          "case_id": "c_a01", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: Filing_Party calls PR5_Seal from FILED (Theranos: action before service gate)", r, "INADMISSIBLE", "ORDER", 1)

# A02 — JURISDICTION
def test_A02():
    # Court_Reporter attempts PR4_Rule — not in Reporter vocab
    events = [
        {"actor_id": "reporter_alpha", "action": "docket_transcript", "case_id": "c_a02", "timestamp": T0+0},
        {"actor_id": "reporter_alpha", "action": "issue_order",       "case_id": "c_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Court_Reporter calls PR4_Rule (not in Reporter vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three FILED(w=2)→SERVED(w=3) expansions within 60s (Filing_Party)
    t = T0
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",                  "case_id": "c_a03", "timestamp": t+0},
        # Exp 1: FILED→SERVED
        {"actor_id": "filing_alpha", "action": "serve_process",                "case_id": "c_a03", "timestamp": t+1},
        # Contract: SERVED→FILED via PR1_File (additional doc)
        {"actor_id": "filing_alpha", "action": "file_supplemental",            "case_id": "c_a03", "timestamp": t+2},
        # Exp 2
        {"actor_id": "filing_alpha", "action": "issue_summons",                "case_id": "c_a03", "timestamp": t+3},
        # Contract
        {"actor_id": "filing_alpha", "action": "file_exhibit",                 "case_id": "c_a03", "timestamp": t+4},
        # Exp 3 — BURST fires
        {"actor_id": "filing_alpha", "action": "file_certificate_of_service",  "case_id": "c_a03", "timestamp": t+5},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three FILED→SERVED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 5)

# A04 — EXIT
def test_A04():
    # filing_bravo takes over case owned by filing_alpha
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",   "case_id": "c_a04", "timestamp": T0+0},
        {"actor_id": "filing_bravo", "action": "serve_process", "case_id": "c_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: filing_bravo pivots into case owned by filing_alpha", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # Audit: IDLE(w=1)→FILED(w=2): exp 1
    # FILED(w=2)→SERVED(w=3): exp 2
    # 2 expansions on clean path → BURST-safe (no spacing required)
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",     "case_id": "c_b01", "timestamp": T0+0},
        {"actor_id": "filing_alpha", "action": "serve_process",   "case_id": "c_b01", "timestamp": T0+1},
        {"actor_id": "filing_alpha", "action": "file_reply",      "case_id": "c_b01", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (2 expansions on clean path, BURST-safe)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "filing_bravo", "action": "file_motion",     "case_id": "c_b02", "timestamp": T0+0},
        # ORDER: PR5_Seal from FILED (not in FILED flows)
        {"actor_id": "filing_bravo", "action": "motion_to_seal",  "case_id": "c_b02", "timestamp": T0+1},
        # Expand to SERVED (unvisited) → HYSTERESIS
        {"actor_id": "filing_bravo", "action": "serve_process",   "case_id": "c_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited SERVED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",          "case_id": "c_b03", "timestamp": T0+0},
        # JURISDICTION: PR6_Bypass not in any vocab
        {"actor_id": "filing_alpha", "action": "ex_parte_without_notice","case_id":"c_b03","timestamp": T0+1},
        # Expand to SERVED (unvisited) → HYSTERESIS
        {"actor_id": "filing_alpha", "action": "serve_process",        "case_id": "c_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited SERVED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    t = T0
    events = [
        {"actor_id": "filing_alpha", "action": "file_motion",                  "case_id": "c_c01", "timestamp": t+0},
        # Exp 1: FILED→SERVED (visited)
        {"actor_id": "filing_alpha", "action": "serve_process",                "case_id": "c_c01", "timestamp": t+1},
        # Contract: SERVED→FILED
        {"actor_id": "filing_alpha", "action": "file_supplemental",            "case_id": "c_c01", "timestamp": t+2},
        # Exp 2
        {"actor_id": "filing_alpha", "action": "issue_summons",                "case_id": "c_c01", "timestamp": t+3},
        # Contract
        {"actor_id": "filing_alpha", "action": "file_exhibit",                 "case_id": "c_c01", "timestamp": t+4},
        # ORDER: PR5_Seal from FILED (not in FILED flows)
        {"actor_id": "filing_alpha", "action": "motion_to_seal",               "case_id": "c_c01", "timestamp": t+5},
        # Exp 3: FILED→SERVED — BURST fires; SERVED visited → HYSTERESIS absent
        {"actor_id": "filing_alpha", "action": "file_certificate_of_service",  "case_id": "c_c01", "timestamp": t+6},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 5: PR5_Seal from FILED", r, "INADMISSIBLE", "ORDER", 5)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 6: 3rd FILED→SERVED; HYSTERESIS absent (SERVED visited)", r, "INADMISSIBLE", "BURST_CADENCE", 6)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "reporter_alpha", "action": "docket_transcript",   "case_id": "c_c02",  "timestamp": T0+0},
        # JURISDICTION: Reporter calls PR4_Rule
        {"actor_id": "reporter_alpha", "action": "grant_motion",        "case_id": "c_c02",  "timestamp": T0+1},
        # ORDER: Filing_Party calls PR5_Seal from FILED on separate case
        {"actor_id": "filing_bravo",   "action": "file_motion",         "case_id": "c_c02b", "timestamp": T0+2},
        {"actor_id": "filing_bravo",   "action": "motion_to_seal",      "case_id": "c_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: Reporter calls PR4_Rule", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: Filing_Party calls PR5_Seal from FILED", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "filing_alpha",   "action": "file_motion",      "case_id": "c_c03",  "timestamp": T0+0},
        # EXIT: filing_bravo pivots into filing_alpha's case
        {"actor_id": "filing_bravo",   "action": "serve_process",    "case_id": "c_c03",  "timestamp": T0+1},
        # JURISDICTION: Reporter calls PR4_Rule on separate case
        {"actor_id": "reporter_bravo", "action": "docket_transcript","case_id": "c_c03b", "timestamp": T0+2},
        {"actor_id": "reporter_bravo", "action": "deny_motion",      "case_id": "c_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: filing_bravo pivots into filing_alpha's case", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: Reporter calls PR4_Rule", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 60)
    print("PACER Court Records Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 60)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 60)
    with open("/home/claude/test_harness_pacer_v0_1_results.json", "w") as f:
        json.dump({"harness": "pacer_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
