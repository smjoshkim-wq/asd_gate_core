"""
Test Harness — OpenStreetMap Changeset Compiler v0.1
Combinatorial — 13 sub-assertions (A01–A04, B01–B03, C01a/b, C02a/b, C03a/b)
"""

import sys, json, time
sys.path.insert(0, "/mnt/project"); sys.path.insert(0, "/home/claude")

from osm_compiler_v0_1 import run_session

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

# A01 — ORDER (MAPS.ME / DWG-style geometry)
def test_A01():
    # DWG_Member calls O5_Mediate from MONITORING (skipping REVIEWING gate)
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",   "cs_id": "cs_a01", "timestamp": T0+0},
        {"actor_id": "dwg_alpha", "action": "block_user", "cs_id": "cs_a01", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A01", "ORDER fires: DWG_Member calls O5_Mediate from MONITORING (MAPS.ME-style skipping review)", r, "INADMISSIBLE", "ORDER", 1)

# A02 — JURISDICTION
def test_A02():
    # Mapper attempts O5_Mediate — not in Mapper vocab
    events = [
        {"actor_id": "mapper_alpha", "action": "view_map",   "cs_id": "cs_a02", "timestamp": T0+0},
        {"actor_id": "mapper_alpha", "action": "block_user", "cs_id": "cs_a02", "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A02", "JURISDICTION fires: Mapper calls O5_Mediate (not in Mapper vocab)", r, "INADMISSIBLE", "JURISDICTION", 1)

# A03 — BURST_CADENCE
def test_A03():
    # Three REVIEWING(w=3)→MEDIATING(w=5) expansions within 60s
    t = T0
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",            "cs_id": "cs_a03", "timestamp": t+0},
        {"actor_id": "dwg_alpha", "action": "comment_on_changeset","cs_id":"cs_a03",  "timestamp": t+1},
        # Exp 1: REVIEWING→MEDIATING
        {"actor_id": "dwg_alpha", "action": "revert_changeset",    "cs_id": "cs_a03", "timestamp": t+2},
        # Contract: MEDIATING→REVIEWING via O2_Edit
        {"actor_id": "dwg_alpha", "action": "tag_change",          "cs_id": "cs_a03", "timestamp": t+3},
        # Exp 2
        {"actor_id": "dwg_alpha", "action": "rollback_user_edits", "cs_id": "cs_a03", "timestamp": t+4},
        # Contract
        {"actor_id": "dwg_alpha", "action": "add_node",            "cs_id": "cs_a03", "timestamp": t+5},
        # Exp 3 — BURST fires
        {"actor_id": "dwg_alpha", "action": "manual_undo",         "cs_id": "cs_a03", "timestamp": t+6},
    ]
    r = run_session(events)
    assert_pass("A03", "BURST_CADENCE fires: three REVIEWING→MEDIATING expansions within 60s", r, "INADMISSIBLE", "BURST_CADENCE", 6)

# A04 — EXIT
def test_A04():
    # dwg_bravo takes over changeset owned by dwg_alpha
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",            "cs_id": "cs_a04", "timestamp": T0+0},
        {"actor_id": "dwg_bravo", "action": "comment_on_changeset","cs_id":"cs_a04",  "timestamp": T0+1},
    ]
    r = run_session(events)
    assert_pass("A04", "EXIT fires: dwg_bravo pivots into changeset owned by dwg_alpha", r, "INADMISSIBLE", "EXIT", 1)

# B01 — clean pipeline
def test_B01():
    # IDLE(w=1)→MONITORING(w=2): exp 1
    # MONITORING(w=2)→REVIEWING(w=3): exp 2
    # REVIEWING(w=3)→MEDIATING(w=5): exp 3
    # 3 expansions → need timestamp spacing
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",            "cs_id": "cs_b01", "timestamp": T0+0},
        {"actor_id": "dwg_alpha", "action": "comment_on_changeset","cs_id":"cs_b01",  "timestamp": T0+70},
        {"actor_id": "dwg_alpha", "action": "revert_changeset",    "cs_id": "cs_b01", "timestamp": T0+140},
        {"actor_id": "dwg_alpha", "action": "block_user",          "cs_id": "cs_b01", "timestamp": T0+210},
    ]
    r = run_session(events)
    assert_clean("B01", "No HYSTERESIS on clean pipeline (3 expansions; timestamps spread beyond 60s window)", r)

# B02 — HYSTERESIS after ORDER
def test_B02():
    events = [
        {"actor_id": "dwg_bravo", "action": "view_map",            "cs_id": "cs_b02", "timestamp": T0+0},
        # ORDER: O5_Mediate from MONITORING
        {"actor_id": "dwg_bravo", "action": "block_user",          "cs_id": "cs_b02", "timestamp": T0+1},
        # Expand to REVIEWING (unvisited) → HYSTERESIS
        {"actor_id": "dwg_bravo", "action": "comment_on_changeset","cs_id":"cs_b02",  "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B02", "HYSTERESIS fires: ORDER at step 1, expansion to unvisited REVIEWING at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# B03 — HYSTERESIS after JURISDICTION
def test_B03():
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",                 "cs_id": "cs_b03", "timestamp": T0+0},
        # JURISDICTION: O6_Bypass not in any vocab
        {"actor_id": "dwg_alpha", "action": "upload_copyrighted_data",  "cs_id": "cs_b03", "timestamp": T0+1},
        # Expand to REVIEWING (unvisited) → HYSTERESIS
        {"actor_id": "dwg_alpha", "action": "comment_on_changeset",     "cs_id": "cs_b03", "timestamp": T0+2},
    ]
    r = run_session(events)
    assert_pass("B03", "HYSTERESIS fires: JURISDICTION at step 1, expansion to unvisited REVIEWING at step 2", r, "INADMISSIBLE", "HYSTERESIS", 2)

# C01 — ORDER + BURST_CADENCE, no HYSTERESIS
def test_C01():
    t = T0
    events = [
        {"actor_id": "dwg_alpha", "action": "view_map",             "cs_id": "cs_c01", "timestamp": t+0},
        {"actor_id": "dwg_alpha", "action": "comment_on_changeset", "cs_id": "cs_c01", "timestamp": t+1},
        # Exp 1: REVIEWING→MEDIATING (visited)
        {"actor_id": "dwg_alpha", "action": "revert_changeset",     "cs_id": "cs_c01", "timestamp": t+2},
        # Contract
        {"actor_id": "dwg_alpha", "action": "tag_change",           "cs_id": "cs_c01", "timestamp": t+3},
        # Exp 2
        {"actor_id": "dwg_alpha", "action": "rollback_user_edits",  "cs_id": "cs_c01", "timestamp": t+4},
        # Contract
        {"actor_id": "dwg_alpha", "action": "add_node",             "cs_id": "cs_c01", "timestamp": t+5},
        # ORDER: O4_Discuss from REVIEWING is valid... let me find an ORDER candidate.
        # From REVIEWING flows: O1_View, O2_Edit, O3_Revert. So O4_Discuss is NOT in REVIEWING flows
        # (it transitions MONITORING→REVIEWING). From REVIEWING calling O4_Discuss → ORDER ✓
        {"actor_id": "dwg_alpha", "action": "open_dwg_ticket",      "cs_id": "cs_c01", "timestamp": t+6},
        # Exp 3: REVIEWING→MEDIATING — BURST fires; MEDIATING visited → HYSTERESIS absent
        {"actor_id": "dwg_alpha", "action": "manual_undo",          "cs_id": "cs_c01", "timestamp": t+7},
    ]
    r = run_session(events)
    order_ok = assert_pass("C01a", "ORDER fires at step 6: O4_Discuss from REVIEWING", r, "INADMISSIBLE", "ORDER", 6)
    burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step 7: 3rd REVIEWING→MEDIATING; HYSTERESIS absent", r, "INADMISSIBLE", "BURST_CADENCE", 7)
    return order_ok and burst_ok

# C02 — JURISDICTION + ORDER sequential
def test_C02():
    events = [
        {"actor_id": "mapper_alpha", "action": "view_map",            "cs_id": "cs_c02",  "timestamp": T0+0},
        # JURISDICTION: Mapper calls O5_Mediate
        {"actor_id": "mapper_alpha", "action": "block_user",          "cs_id": "cs_c02",  "timestamp": T0+1},
        # ORDER: DWG calls O5_Mediate from MONITORING on separate cs
        {"actor_id": "dwg_bravo",    "action": "view_map",            "cs_id": "cs_c02b", "timestamp": T0+2},
        {"actor_id": "dwg_bravo",    "action": "mass_rollback",       "cs_id": "cs_c02b", "timestamp": T0+3},
    ]
    r = run_session(events)
    juris_ok = assert_pass("C02a", "JURISDICTION fires at step 1: Mapper calls O5_Mediate", r, "INADMISSIBLE", "JURISDICTION", 1)
    order_ok = assert_pass("C02b", "ORDER fires at step 3: DWG calls O5_Mediate from MONITORING", r, "INADMISSIBLE", "ORDER", 3)
    return juris_ok and order_ok

# C03 — EXIT + JURISDICTION separate actors
def test_C03():
    events = [
        {"actor_id": "dwg_alpha",    "action": "view_map",            "cs_id": "cs_c03",  "timestamp": T0+0},
        # EXIT: dwg_bravo pivots into dwg_alpha's changeset
        {"actor_id": "dwg_bravo",    "action": "comment_on_changeset","cs_id":"cs_c03",   "timestamp": T0+1},
        # JURISDICTION: Anonymous calls O2_Edit on separate cs
        {"actor_id": "anon_osm",     "action": "view_map",            "cs_id": "cs_c03b", "timestamp": T0+2},
        {"actor_id": "anon_osm",     "action": "add_node",            "cs_id": "cs_c03b", "timestamp": T0+3},
    ]
    r = run_session(events)
    exit_ok  = assert_pass("C03a", "EXIT fires at step 1: dwg_bravo pivots into dwg_alpha's changeset", r, "INADMISSIBLE", "EXIT", 1)
    juris_ok = assert_pass("C03b", "JURISDICTION fires at step 3: Anonymous calls O2_Edit", r, "INADMISSIBLE", "JURISDICTION", 3)
    return exit_ok and juris_ok

if __name__ == "__main__":
    print("=" * 60)
    print("OpenStreetMap Changeset Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    test_A01(); test_A02(); test_A03(); test_A04()
    test_B01(); test_B02(); test_B03()
    test_C01(); test_C02(); test_C03()
    total = PASS_COUNT + FAIL_COUNT
    print("-" * 60)
    print(f"Results: {PASS_COUNT}/{total} passed", "✓ ALL PASS" if FAIL_COUNT == 0 else f"✗ {FAIL_COUNT} FAILED")
    print("=" * 60)
    with open("/home/claude/test_harness_osm_v0_1_results.json", "w") as f:
        json.dump({"harness": "osm_v0_1_combinatorial", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "passed": PASS_COUNT, "failed": FAIL_COUNT, "total": total, "results": RESULTS}, f, indent=2)
