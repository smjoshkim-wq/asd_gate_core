"""
Test Harness — UNSW-NB15 Network Layer Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from net_compiler_v0_1 import run_session

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

# A01 — ORDER (UNSW Exploits/Shellcode pattern: data before auth)
def test_A01():
    # Client_Host calls N2_Transfer from CONNECTING (skipping N4_Authenticate)
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",         "flow_id": "f_a01", "timestamp": T0+0},
        {"actor_id": "client_alpha", "action": "transfer_payload","flow_id": "f_a01", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: Client_Host calls N2_Transfer from CONNECTING (UNSW data-before-auth pattern)", r, "INADMISSIBLE", "ORDER", 1)

# A02 — JURISDICTION
def test_A02():
    # Monitor attempts N2_Transfer — Monitor is N3-only
    events = [
        {"actor_id": "monitor_alpha", "action": "port_scan",       "flow_id": "f_a02", "timestamp": T0+0},
        {"actor_id": "monitor_alpha", "action": "transfer_payload","flow_id": "f_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Monitor calls N2_Transfer (Monitor is N3-only)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three AUTHENTICATED(w=2)→ESTABLISHED(w=4) expansions within 60s
    t = T0
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",           "flow_id": "f_a03", "timestamp": t+0},
        {"actor_id": "client_alpha", "action": "tls_client_hello",  "flow_id": "f_a03", "timestamp": t+1},
        # Exp 1: AUTHENTICATED→ESTABLISHED
        {"actor_id": "client_alpha", "action": "transfer_payload",  "flow_id": "f_a03", "timestamp": t+2},
        # Contract: ESTABLISHED→AUTHENTICATED via N4_Authenticate (rekey)
        {"actor_id": "client_alpha", "action": "rekey",             "flow_id": "f_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "client_alpha", "action": "send_data",         "flow_id": "f_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "client_alpha", "action": "tls_finished",      "flow_id": "f_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "client_alpha", "action": "http_request",      "flow_id": "f_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three AUTHENTICATED→ESTABLISHED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # client_bravo takes over flow owned by client_alpha
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",          "flow_id": "f_a04", "timestamp": T0+0},
        {"actor_id": "client_bravo", "action": "tls_client_hello", "flow_id": "f_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: client_bravo pivots into flow owned by client_alpha", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # Audit: IDLE(w=1)→CONNECTING(w=2): exp 1
    # CONNECTING(w=2)→AUTHENTICATED(w=2): not exp
    # AUTHENTICATED(w=2)→ESTABLISHED(w=4): exp 2
    # 2 expansions → BURST-safe
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",          "flow_id": "f_b01", "timestamp": T0+0},
        {"actor_id": "client_alpha", "action": "tls_client_hello", "flow_id": "f_b01", "timestamp": T0+1},
        {"actor_id": "client_alpha", "action": "transfer_payload", "flow_id": "f_b01", "timestamp": T0+2},
        {"actor_id": "client_alpha", "action": "send_data",        "flow_id": "f_b01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (2 expansions on clean path, BURST-safe)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "client_bravo", "action": "tcp_syn",          "flow_id": "f_b02", "timestamp": T0+0},
        # ORDER: N2_Transfer from CONNECTING
        {"actor_id": "client_bravo", "action": "transfer_payload", "flow_id": "f_b02", "timestamp": T0+1},
        # Expand to AUTHENTICATED (unvisited) → HYSTERESIS
        {"actor_id": "client_bravo", "action": "tls_client_hello", "flow_id": "f_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited AUTHENTICATED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",            "flow_id": "f_b03", "timestamp": T0+0},
        # JURISDICTION: N6_Bypass not in any vocab
        {"actor_id": "client_alpha", "action": "malformed_packet",   "flow_id": "f_b03", "timestamp": T0+1},
        # Expand to AUTHENTICATED (unvisited) → HYSTERESIS
        {"actor_id": "client_alpha", "action": "tls_client_hello",   "flow_id": "f_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited AUTHENTICATED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    t = T0
    events = [
        {"actor_id": "client_alpha", "action": "tcp_syn",           "flow_id": "f_c01", "timestamp": t+0},
        {"actor_id": "client_alpha", "action": "tls_client_hello",  "flow_id": "f_c01", "timestamp": t+1},
        # Exp 1: AUTHENTICATED→ESTABLISHED (visited)
        {"actor_id": "client_alpha", "action": "transfer_payload",  "flow_id": "f_c01", "timestamp": t+2},
        # Contract
        {"actor_id": "client_alpha", "action": "rekey",             "flow_id": "f_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "client_alpha", "action": "send_data",         "flow_id": "f_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "client_alpha", "action": "tls_finished",      "flow_id": "f_c01", "timestamp": t+5},
        # ORDER: N5_Terminate from AUTHENTICATED (not in AUTHENTICATED flows)
        {"actor_id": "client_alpha", "action": "tcp_fin",           "flow_id": "f_c01", "timestamp": t+6},
        # Exp 3: AUTHENTICATED→ESTABLISHED — BURST fires; ESTABLISHED visited → HYSTERESIS absent
        {"actor_id": "client_alpha", "action": "http_request",      "flow_id": "f_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: N5_Terminate from AUTHENTICATED", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd AUTHENTICATED→ESTABLISHED; HYSTERESIS absent", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "monitor_alpha", "action": "port_scan",         "flow_id": "f_c02",  "timestamp": T0+0},
        # JURISDICTION: Monitor calls N2_Transfer
        {"actor_id": "monitor_alpha", "action": "transfer_payload",  "flow_id": "f_c02",  "timestamp": T0+1},
        # ORDER: Client calls N2_Transfer from CONNECTING on separate flow
        {"actor_id": "client_bravo",  "action": "tcp_syn",           "flow_id": "f_c02b", "timestamp": T0+2},
        {"actor_id": "client_bravo",  "action": "http_request",      "flow_id": "f_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: Monitor calls N2_Transfer", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: Client calls N2_Transfer from CONNECTING", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "client_alpha",  "action": "tcp_syn",          "flow_id": "f_c03",  "timestamp": T0+0},
        # EXIT: client_bravo pivots into client_alpha's flow
        {"actor_id": "client_bravo",  "action": "tls_client_hello", "flow_id": "f_c03",  "timestamp": T0+1},
        # JURISDICTION: Monitor calls N1_Connect on separate flow
        {"actor_id": "monitor_bravo", "action": "port_scan",        "flow_id": "f_c03b", "timestamp": T0+2},
        {"actor_id": "monitor_bravo", "action": "open_socket",      "flow_id": "f_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: client_bravo pivots into client_alpha's flow", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: Monitor calls N1_Connect", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 60)
    print("UNSW-NB15 Network Layer Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 60)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 60)
    with open("/home/claude/test_harness_net_v0_1_results.json", "w") as f:
        json.dump({"harness": "net_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
