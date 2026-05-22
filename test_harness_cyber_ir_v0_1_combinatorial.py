"""
Test Harness — Cyber IR Human Layer Compiler v0.1
Combinatorial — 10 tests (A01–A04, B01–B03, C01–C03)
"""

import sys
import json
import time

sys.path.insert(0, "/mnt/project")
sys.path.insert(0, "/home/claude")

from cyber_ir_compiler_v0_1 import run_session

PASS_COUNT = 0
FAIL_COUNT = 0
RESULTS    = []

T0 = 1000.0  # base timestamp


def assert_pass(test_id, description, results, expected_decision, expected_invariant, step_index):
    global PASS_COUNT, FAIL_COUNT
    r = results[step_index]
    ok = (r.get("decision") == expected_decision and
          r.get("invariant") == expected_invariant)
    label = "[PASS]" if ok else "[FAIL]"
    if ok:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    entry = {
        "test_id":    test_id,
        "label":      label,
        "description": description,
        "expected":   {"decision": expected_decision, "invariant": expected_invariant},
        "got":        {"decision": r.get("decision"), "invariant": r.get("invariant")},
        "step":       step_index,
        "from_state": r.get("_stp", {}).get("FromState"),
        "to_state":   r.get("_stp", {}).get("ToState"),
    }
    RESULTS.append(entry)
    print(f"{label} {test_id} — {description}")
    return ok


def assert_clean(test_id, description, results):
    global PASS_COUNT, FAIL_COUNT
    violations = [r for r in results if r.get("decision") == "INADMISSIBLE"]
    ok = len(violations) == 0
    label = "[PASS]" if ok else "[FAIL]"
    if ok:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    entry = {
        "test_id":     test_id,
        "label":       label,
        "description": description,
        "violations":  violations,
    }
    RESULTS.append(entry)
    print(f"{label} {test_id} — {description}")
    return ok


# ── A01 ── ORDER ──────────────────────────────────────────────────────
def test_A01():
    # IR_Analyst calls IR3_Contain from ALERT_RECEIVED — skips triage (ORDER)
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",    "incident_id": "inc_a01", "timestamp": T0 + 0},
        {"actor_id": "analyst_alpha", "action": "review_alert",    "incident_id": "inc_a01", "timestamp": T0 + 1},
        {"actor_id": "analyst_alpha", "action": "isolate_system",  "incident_id": "inc_a01", "timestamp": T0 + 2},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: IR_Analyst calls IR3_Contain from ALERT_RECEIVED (skips IR2_Triage gate)", r, "INADMISSIBLE", "ORDER", 2)


# ── A02 ── JURISDICTION ───────────────────────────────────────────────
def test_A02():
    # IR_Analyst attempts IR5_Disclose — not in their vocab (JURISDICTION)
    events = [
        {"actor_id": "analyst_bravo", "action": "monitor_siem",             "incident_id": "inc_a02", "timestamp": T0 + 0},
        {"actor_id": "analyst_bravo", "action": "assess_severity",          "incident_id": "inc_a02", "timestamp": T0 + 1},
        {"actor_id": "analyst_bravo", "action": "isolate_system",           "incident_id": "inc_a02", "timestamp": T0 + 2},
        {"actor_id": "analyst_bravo", "action": "escalate_to_ciso",         "incident_id": "inc_a02", "timestamp": T0 + 3},
        {"actor_id": "analyst_bravo", "action": "file_regulatory_notification", "incident_id": "inc_a02", "timestamp": T0 + 4},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: IR_Analyst calls IR5_Disclose (not in analyst vocab)", r, "INADMISSIBLE", "JURISDICTION", 4)


# ── A03 ── BURST_CADENCE ──────────────────────────────────────────────
def test_A03():
    # Three rapid TRIAGED(w=2)→CONTAINED(w=3) expansions within 60s
    t = T0
    events = [
        {"actor_id": "analyst_generic", "action": "monitor_siem",   "incident_id": "inc_a03", "timestamp": t},
        {"actor_id": "analyst_generic", "action": "assess_severity", "incident_id": "inc_a03", "timestamp": t + 1},
        # Expansion 1: TRIAGED→CONTAINED
        {"actor_id": "analyst_generic", "action": "isolate_system",  "incident_id": "inc_a03", "timestamp": t + 2},
        # Contract back to TRIAGED
        {"actor_id": "analyst_generic", "action": "determine_scope", "incident_id": "inc_a03", "timestamp": t + 3},
        # Expansion 2
        {"actor_id": "analyst_generic", "action": "block_ip",        "incident_id": "inc_a03", "timestamp": t + 4},
        # Contract
        {"actor_id": "analyst_generic", "action": "classify_incident","incident_id": "inc_a03", "timestamp": t + 5},
        # Expansion 3 — BURST fires here
        {"actor_id": "analyst_generic", "action": "quarantine_host", "incident_id": "inc_a03", "timestamp": t + 6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three TRIAGED→CONTAINED expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)


# ── A04 ── EXIT ───────────────────────────────────────────────────────
def test_A04():
    # ir_lead_alpha takes over incident_id already owned by analyst_alpha (actor pivot)
    events = [
        {"actor_id": "analyst_alpha",   "action": "monitor_siem",  "incident_id": "inc_a04", "timestamp": T0 + 0},
        {"actor_id": "analyst_alpha",   "action": "assess_severity","incident_id": "inc_a04", "timestamp": T0 + 1},
        {"actor_id": "ir_lead_alpha",   "action": "isolate_system", "incident_id": "inc_a04", "timestamp": T0 + 2},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: ir_lead_alpha pivots into incident owned by analyst_alpha without handoff", r, "INADMISSIBLE", "EXIT", 2)


# ── B01 ── HYSTERESIS does NOT fire on clean pipeline ─────────────────
def test_B01():
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",    "incident_id": "inc_b01", "timestamp": T0 + 0},
        {"actor_id": "analyst_alpha", "action": "assess_severity",  "incident_id": "inc_b01", "timestamp": T0 + 1},
        {"actor_id": "analyst_alpha", "action": "isolate_system",   "incident_id": "inc_b01", "timestamp": T0 + 2},
        {"actor_id": "analyst_alpha", "action": "escalate_to_ciso", "incident_id": "inc_b01", "timestamp": T0 + 3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline — no prior violation, no unvisited state expansion", r)


# ── B02 ── HYSTERESIS fires after ORDER ───────────────────────────────
def test_B02():
    # ORDER fires at step 2, then analyst reaches CONTAINED (visited), escalates
    # then tries to expand to DISCLOSED (unvisited for analyst) via CISO role confusion — 
    # Actually: ORDER fires, then analyst expands to ESCALATED for the first time (unvisited) 
    # after violation → HYSTERESIS fires
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",    "incident_id": "inc_b02", "timestamp": T0 + 0},
        # ORDER: skip triage, go straight to contain
        {"actor_id": "analyst_alpha", "action": "isolate_system",  "incident_id": "inc_b02", "timestamp": T0 + 1},
        # Now back to valid flow — triage
        {"actor_id": "analyst_alpha", "action": "assess_severity", "incident_id": "inc_b02", "timestamp": T0 + 2},
        # Contain again (TRIAGED→CONTAINED visited before ORDER, so not hysteresis)
        # Actually after ORDER, TRIAGED hasn't been visited yet from this actor's perspective
        # Let's re-route: first go clean through TRIAGED and CONTAINED, then ORDER fires,
        # then expand to ESCALATED (unvisited) → HYSTERESIS
    ]
    # Cleaner B02 geometry: 
    # clean path establishes IDLE→ALERT_RECEIVED→TRIAGED→CONTAINED (all visited)
    # ORDER fires (contain from alert_received on new session won't work — need same actor)
    # Better: use a fresh actor that goes IDLE→ALERT_RECEIVED, ORDER fires (contain from alert),
    # then tries to go to TRIAGED→CONTAINED→ESCALATED where TRIAGED is unvisited → HYSTERESIS
    events = [
        {"actor_id": "analyst_bravo", "action": "monitor_siem",    "incident_id": "inc_b02", "timestamp": T0 + 0},
        # ORDER: call contain from ALERT_RECEIVED (skips triage)
        {"actor_id": "analyst_bravo", "action": "isolate_system",  "incident_id": "inc_b02", "timestamp": T0 + 1},
        # Now analyst is still in ALERT_RECEIVED state (violation blocked transition)
        # Try to expand to TRIAGED → TRIAGED not yet visited → HYSTERESIS
        {"actor_id": "analyst_bravo", "action": "assess_severity", "incident_id": "inc_b02", "timestamp": T0 + 2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, then expansion to unvisited TRIAGED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)


# ── B03 ── HYSTERESIS fires after JURISDICTION ────────────────────────
def test_B03():
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",             "incident_id": "inc_b03", "timestamp": T0 + 0},
        # JURISDICTION: analyst calls IR5_Disclose (not in vocab)
        {"actor_id": "analyst_alpha", "action": "file_regulatory_notification","incident_id": "inc_b03","timestamp": T0 + 1},
        # Now try to expand to ALERT_RECEIVED (unvisited) → HYSTERESIS
        {"actor_id": "analyst_alpha", "action": "assess_severity",           "incident_id": "inc_b03", "timestamp": T0 + 2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, then expansion to unvisited TRIAGED at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)


# ── C01 ── ORDER + BURST_CADENCE coexist; HYSTERESIS absent ──────────
def test_C01():
    # ORDER fires first (step 2). Then burst oscillation in TRIAGED↔CONTAINED
    # (both visited before ORDER fires — well, ORDER fires before TRIAGED is visited,
    # so after ORDER the actor is still in ALERT_RECEIVED.
    # We need TRIAGED and CONTAINED to be visited BEFORE ORDER fires.
    # Revised: clean path first to establish visited states, then ORDER fires,
    # then burst in already-visited TRIAGED↔CONTAINED.
    # 
    # Path: IDLE→ALERT_RECEIVED (step0) →TRIAGED(step1)→CONTAINED(step2) 
    #       →TRIAGED(step3) →CONTAINED(step4) →TRIAGED(step5)
    # ORDER fires at step6 (contain from TRIAGED is valid, so ORDER needs wrong action)
    # Actually ORDER = action in vocab but wrong state. 
    # Let's use: from CONTAINED, call IR5_Disclose — not in analyst vocab → JURISDICTION not ORDER
    # For ORDER from CONTAINED: no action is out-of-order from CONTAINED since IR4_Escalate goes to ESCALATED
    # For ORDER we need: action in analyst vocab, present in some state, but not in current state.
    # IR4_Escalate is only valid from CONTAINED→ESCALATED. From TRIAGED, IR4_Escalate is not valid → ORDER.
    #
    # Revised C01:
    # Step 0: monitor_siem → ALERT_RECEIVED (visited)
    # Step 1: assess_severity → TRIAGED (visited)
    # Step 2: isolate_system → CONTAINED (visited) [expansion 1: w2→w3]
    # Step 3: determine_scope → TRIAGED (visited) [contraction]
    # Step 4: block_ip → CONTAINED (visited) [expansion 2: w2→w3]
    # Step 5: classify_incident → TRIAGED (visited) [contraction]
    # Step 6: ORDER fires: escalate_to_ciso from TRIAGED (IR4_Escalate not in TRIAGED flows)
    # Step 7: quarantine_host → CONTAINED [expansion 3: w2→w3] — BURST fires; HYSTERESIS must NOT fire (CONTAINED visited)
    t = T0
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",    "incident_id": "inc_c01", "timestamp": t + 0},
        {"actor_id": "analyst_alpha", "action": "assess_severity", "incident_id": "inc_c01", "timestamp": t + 1},
        {"actor_id": "analyst_alpha", "action": "isolate_system",  "incident_id": "inc_c01", "timestamp": t + 2},
        {"actor_id": "analyst_alpha", "action": "determine_scope", "incident_id": "inc_c01", "timestamp": t + 3},
        {"actor_id": "analyst_alpha", "action": "block_ip",        "incident_id": "inc_c01", "timestamp": t + 4},
        {"actor_id": "analyst_alpha", "action": "classify_incident","incident_id": "inc_c01","timestamp": t + 5},
        {"actor_id": "analyst_alpha", "action": "escalate_to_ciso","incident_id": "inc_c01", "timestamp": t + 6},
        {"actor_id": "analyst_alpha", "action": "quarantine_host", "incident_id": "inc_c01", "timestamp": t + 7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: IR4_Escalate from TRIAGED (not in TRIAGED flows)", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd TRIAGED→CONTAINED expansion; HYSTERESIS absent (CONTAINED visited)", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok


# ── C02 ── JURISDICTION + ORDER sequential, independent ──────────────
def test_C02():
    events = [
        {"actor_id": "analyst_alpha", "action": "monitor_siem",             "incident_id": "inc_c02", "timestamp": T0 + 0},
        # JURISDICTION: IR5_Disclose not in analyst vocab
        {"actor_id": "analyst_alpha", "action": "submit_sec_filing",        "incident_id": "inc_c02", "timestamp": T0 + 1},
        # Continue with new incident — ORDER: contain before triage
        {"actor_id": "analyst_bravo", "action": "monitor_siem",             "incident_id": "inc_c02b","timestamp": T0 + 2},
        {"actor_id": "analyst_bravo", "action": "quarantine_host",          "incident_id": "inc_c02b","timestamp": T0 + 3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: analyst calls IR5_Disclose", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: analyst calls IR3_Contain from ALERT_RECEIVED", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok


# ── C03 ── EXIT + JURISDICTION, separate actors ───────────────────────
def test_C03():
    events = [
        # Actor pivot: ir_lead_alpha takes over analyst_alpha's incident
        {"actor_id": "analyst_alpha", "action": "monitor_siem",         "incident_id": "inc_c03", "timestamp": T0 + 0},
        {"actor_id": "ir_lead_alpha", "action": "assess_severity",      "incident_id": "inc_c03", "timestamp": T0 + 1},
        # Separate actor: JURISDICTION
        {"actor_id": "analyst_bravo", "action": "monitor_siem",         "incident_id": "inc_c03b","timestamp": T0 + 2},
        {"actor_id": "analyst_bravo", "action": "issue_public_statement","incident_id":"inc_c03b","timestamp": T0 + 3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: ir_lead_alpha pivots into analyst_alpha's incident", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: analyst_bravo calls IR5_Disclose", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok


# ── Run all ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("Cyber IR Human Layer Compiler v0.1 — Combinatorial Harness")
    print("=" * 65)

    test_A01()
    test_A02()
    test_A03()
    test_A04()
    test_B01()
    test_B02()
    test_B03()
    test_C01()
    test_C02()
    test_C03()

    total = PASS_COUNT + FAIL_COUNT
    print("-" * 65)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 65)

    with open("/home/claude/test_harness_cyber_ir_v0_1_results.json", "w") as f:
        json.dump({
            "harness":    "cyber_ir_v0_1_combinatorial",
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed":     PASS_COUNT,
            "failed":     FAIL_COUNT,
            "total":      total,
            "results":    RESULTS,
        }, f, indent=2)
