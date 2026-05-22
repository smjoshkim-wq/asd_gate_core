"""
Test Harness — Academic Publishing Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from pub_compiler_v0_1 import run_session

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

# A01 — ORDER (Hwang Woo-suk geometry)
def test_A01():
    # Editor calls AP3_Decide from UNDER_REVIEW (before REVIEW_COMPLETE gate)
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript",      "ms_id": "ms_a01", "timestamp": T0+0},
        {"actor_id": "editor_alpha", "action": "assign_reviewers",       "ms_id": "ms_a01", "timestamp": T0+1},
        # Editor is now in UNDER_REVIEW (assign_reviewers = AP2_Review from SUBMITTED → UNDER_REVIEW)
        # Wait — that's a single AP2_Review and it goes UNDER_REVIEW→REVIEW_COMPLETE under our patched flow.
        # SUBMITTED→UNDER_REVIEW via AP2_Review, then UNDER_REVIEW→REVIEW_COMPLETE via AP2_Review.
        # So after assign_reviewers, editor is in UNDER_REVIEW. Then submit_revision (AP1_Submit) loops UNDER_REVIEW.
        # Then issue_acceptance (AP3_Decide) from UNDER_REVIEW → ORDER.
        {"actor_id": "editor_alpha", "action": "submit_revision",        "ms_id": "ms_a01", "timestamp": T0+2},
        {"actor_id": "editor_alpha", "action": "issue_acceptance",       "ms_id": "ms_a01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: Editor calls AP3_Decide from UNDER_REVIEW (Hwang geometry, no REVIEW_COMPLETE)", r, "INADMISSIBLE", "ORDER", 3)

# A02 — JURISDICTION
def test_A02():
    # Reviewer attempts AP3_Decide — not in Reviewer vocab
    events = [
        {"actor_id": "reviewer_alpha", "action": "perform_peer_review", "ms_id": "ms_a02", "timestamp": T0+0},
        {"actor_id": "reviewer_alpha", "action": "issue_acceptance",    "ms_id": "ms_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Reviewer calls AP3_Decide (not in Reviewer vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three UNDER_REVIEW(w=2)→REVIEW_COMPLETE(w=4) expansions within 60s
    t = T0
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript",      "ms_id": "ms_a03", "timestamp": t+0},
        {"actor_id": "editor_alpha", "action": "assign_reviewers",       "ms_id": "ms_a03", "timestamp": t+1},
        # Now in REVIEW_COMPLETE. Need to bounce back to UNDER_REVIEW first.
        # Wait — assign_reviewers (AP2_Review) from SUBMITTED → UNDER_REVIEW
        # Then we need UNDER_REVIEW → REVIEW_COMPLETE via AP2_Review.
        {"actor_id": "editor_alpha", "action": "recommend_acceptance",   "ms_id": "ms_a03", "timestamp": t+2},
        # Exp 1: UNDER_REVIEW→REVIEW_COMPLETE happens here? Let me trace:
        # Step 0: submit_manuscript (AP1_Submit) IDLE→SUBMITTED (w=1→2): expanding
        # Step 1: assign_reviewers (AP2_Review) SUBMITTED→UNDER_REVIEW (w=2→2): not expanding
        # Step 2: recommend_acceptance (AP2_Review) UNDER_REVIEW→REVIEW_COMPLETE (w=2→4): EXP 1
        # Contract: REVIEW_COMPLETE→UNDER_REVIEW via AP2_Review
        {"actor_id": "editor_alpha", "action": "submit_review_comments", "ms_id": "ms_a03", "timestamp": t+3},
        # Step 3: AP2_Review REVIEW_COMPLETE→UNDER_REVIEW (w=4→2): contracting
        # Exp 2: UNDER_REVIEW→REVIEW_COMPLETE
        {"actor_id": "editor_alpha", "action": "recommend_revision",     "ms_id": "ms_a03", "timestamp": t+4},
        # Step 4: AP2_Review UNDER_REVIEW→REVIEW_COMPLETE (w=2→4): EXP 2
        # Contract
        {"actor_id": "editor_alpha", "action": "perform_peer_review",    "ms_id": "ms_a03", "timestamp": t+5},
        # Step 5: AP2_Review REVIEW_COMPLETE→UNDER_REVIEW
        # Exp 3 — BURST fires
        {"actor_id": "editor_alpha", "action": "recommend_rejection",    "ms_id": "ms_a03", "timestamp": t+6},
        # Step 6: AP2_Review UNDER_REVIEW→REVIEW_COMPLETE: EXP 3 → BURST fires
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three UNDER_REVIEW→REVIEW_COMPLETE expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # editor_bravo takes over manuscript owned by editor_alpha
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript", "ms_id": "ms_a04", "timestamp": T0+0},
        {"actor_id": "editor_bravo", "action": "assign_reviewers",  "ms_id": "ms_a04", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: editor_bravo pivots into manuscript owned by editor_alpha", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline (stop before PUBLISHED to stay BURST-safe)
def test_B01():
    # IDLE→SUBMITTED(w=1→2): exp 1
    # SUBMITTED→UNDER_REVIEW(w=2→2): not expanding
    # UNDER_REVIEW→REVIEW_COMPLETE(w=2→4): exp 2
    # REVIEW_COMPLETE→DECIDED(w=4→2): contracting
    # 2 expansions → BURST-safe, no spacing required
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript",     "ms_id": "ms_b01", "timestamp": T0+0},
        {"actor_id": "editor_alpha", "action": "assign_reviewers",      "ms_id": "ms_b01", "timestamp": T0+1},
        {"actor_id": "editor_alpha", "action": "recommend_acceptance",  "ms_id": "ms_b01", "timestamp": T0+2},
        {"actor_id": "editor_alpha", "action": "issue_acceptance",      "ms_id": "ms_b01", "timestamp": T0+3},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (2 expansions on clean path, BURST-safe)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "editor_bravo", "action": "submit_manuscript",     "ms_id": "ms_b02", "timestamp": T0+0},
        # ORDER: AP3_Decide from SUBMITTED (not in SUBMITTED flows)
        {"actor_id": "editor_bravo", "action": "issue_acceptance",      "ms_id": "ms_b02", "timestamp": T0+1},
        # Expand to UNDER_REVIEW (unvisited) → HYSTERESIS
        {"actor_id": "editor_bravo", "action": "assign_reviewers",      "ms_id": "ms_b02", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited UNDER_REVIEW at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript",     "ms_id": "ms_b03", "timestamp": T0+0},
        # JURISDICTION: AP6_Bypass not in any vocab
        {"actor_id": "editor_alpha", "action": "fabricate_reviewer",    "ms_id": "ms_b03", "timestamp": T0+1},
        # Expand to UNDER_REVIEW (unvisited) → HYSTERESIS
        {"actor_id": "editor_alpha", "action": "assign_reviewers",      "ms_id": "ms_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited UNDER_REVIEW at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    # Establish UNDER_REVIEW and REVIEW_COMPLETE as visited, ORDER fires, burst in visited
    t = T0
    events = [
        {"actor_id": "editor_alpha", "action": "submit_manuscript",     "ms_id": "ms_c01", "timestamp": t+0},
        {"actor_id": "editor_alpha", "action": "assign_reviewers",      "ms_id": "ms_c01", "timestamp": t+1},
        # Exp 1: UNDER_REVIEW→REVIEW_COMPLETE
        {"actor_id": "editor_alpha", "action": "recommend_acceptance",  "ms_id": "ms_c01", "timestamp": t+2},
        # Contract
        {"actor_id": "editor_alpha", "action": "submit_review_comments","ms_id": "ms_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "editor_alpha", "action": "recommend_revision",    "ms_id": "ms_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "editor_alpha", "action": "perform_peer_review",   "ms_id": "ms_c01", "timestamp": t+5},
        # ORDER: AP3_Decide from UNDER_REVIEW (not in UNDER_REVIEW flows — patched)
        {"actor_id": "editor_alpha", "action": "make_editorial_decision","ms_id": "ms_c01", "timestamp": t+6},
        # Exp 3 — UNDER_REVIEW→REVIEW_COMPLETE (visited); BURST fires; HYSTERESIS absent
        {"actor_id": "editor_alpha", "action": "recommend_rejection",   "ms_id": "ms_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: AP3_Decide from UNDER_REVIEW", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd UNDER_REVIEW→REVIEW_COMPLETE; HYSTERESIS absent", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "reviewer_alpha", "action": "perform_peer_review", "ms_id": "ms_c02",  "timestamp": T0+0},
        # JURISDICTION: Reviewer calls AP3_Decide
        {"actor_id": "reviewer_alpha", "action": "make_editorial_decision","ms_id":"ms_c02","timestamp": T0+1},
        # ORDER: Editor calls AP3_Decide from SUBMITTED on separate ms
        {"actor_id": "editor_bravo",   "action": "submit_manuscript",   "ms_id": "ms_c02b", "timestamp": T0+2},
        {"actor_id": "editor_bravo",   "action": "issue_rejection",     "ms_id": "ms_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: Reviewer calls AP3_Decide", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: Editor calls AP3_Decide from SUBMITTED", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "editor_alpha",   "action": "submit_manuscript",   "ms_id": "ms_c03",  "timestamp": T0+0},
        # EXIT: editor_bravo pivots into editor_alpha's manuscript
        {"actor_id": "editor_bravo",   "action": "assign_reviewers",    "ms_id": "ms_c03",  "timestamp": T0+1},
        # JURISDICTION: Reviewer calls AP3_Decide on separate ms
        {"actor_id": "reviewer_bravo", "action": "perform_peer_review", "ms_id": "ms_c03b", "timestamp": T0+2},
        {"actor_id": "reviewer_bravo", "action": "issue_revision_request","ms_id":"ms_c03b","timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: editor_bravo pivots into editor_alpha's manuscript", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: Reviewer calls AP3_Decide", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 62)
    print("Academic Publishing Compiler v0.1 — Combinatorial Harness")
    print("=" * 62)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 62)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 62)
    with open("/home/claude/test_harness_pub_v0_1_results.json", "w") as f:
        json.dump({"harness": "pub_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
