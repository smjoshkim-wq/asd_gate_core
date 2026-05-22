"""
Combinatorial Test Harness — Clinical Compiler v0.1 (corrected)

Root causes fixed:
1. Helper used C7 action to advance SURGICAL_TIMEOUT->INDUCTION — changed to C5_Handoff
   (shift_change_report maps to C5_Handoff and is already in action map)
2. Normal path produces 3 width expansions within 60s — fixed by wide timestamps in setup
3. BURST oscillation uses EMERGENCE(5)<->INDUCTION(6) with tight timestamps after setup

All 10 tests expected: PASS
"""
import sys
sys.path.insert(0, ".")
from clinical_compiler_v0_1 import run_session, ClinicalCompiler

BASE_TS = 4_000_000.0

def gate_result(events):
    return [(r["verdict"], r.get("invariant")) for r in run_session(events)]

def assert_pass(test_id, desc, results, verdict, invariant, at_step):
    v, inv = results[at_step]
    ok = v == verdict and (invariant is None or inv == invariant)
    print(f"{'[PASS]' if ok else '[FAIL]'} {test_id}: {desc}")
    print(f"       step {at_step+1}: verdict={v}, invariant={inv}")
    if not ok:
        print(f"       EXPECTED: verdict={verdict}, invariant={invariant}")
    return ok

def _reach_induction_anesthesiologist(actor_id, patient_id, t0):
    """
    Cleanly navigate Anesthesiologist to INDUCTION state.
    Wide timestamps (70s apart) prevent false BURST from setup expansions.
    IDLE->PRE_OP (expand, t0), PRE_OP->CONSENT (contract, t0+70),
    CONSENT->SURGICAL_TIMEOUT (expand, t0+140), SURGICAL_TIMEOUT->INDUCTION (expand, t0+210).
    At t0+210, burst window=[t0+150,t0+210]: only 1 expansion. No false BURST.
    Uses shift_change_report (C5_Handoff) to advance SURGICAL_TIMEOUT->INDUCTION.
    """
    return [
        {"actor_id": actor_id, "action": "check_vitals",           "patient_id": patient_id, "timestamp": t0+0},    # IDLE->PRE_OP   (C1, expand 1->3)
        {"actor_id": actor_id, "action": "complete_preop_assessment","patient_id": patient_id,"timestamp": t0+70},   # PRE_OP->CONSENT (C7, contract 3->2)
        {"actor_id": actor_id, "action": "document_consent",       "patient_id": patient_id, "timestamp": t0+140},  # CONSENT->SURGICAL_TIMEOUT (C7, expand 2->3)
        {"actor_id": actor_id, "action": "shift_change_report",    "patient_id": patient_id, "timestamp": t0+210},  # SURGICAL_TIMEOUT->INDUCTION (C5, expand 3->6)
    ]

def _reach_induction_rn(actor_id, patient_id, t0):
    """Same wide-spaced path for RN."""
    return [
        {"actor_id": actor_id, "action": "check_vitals",           "patient_id": patient_id, "timestamp": t0+0},
        {"actor_id": actor_id, "action": "complete_preop_assessment","patient_id": patient_id,"timestamp": t0+70},
        {"actor_id": actor_id, "action": "document_consent",       "patient_id": patient_id, "timestamp": t0+140},
        {"actor_id": actor_id, "action": "shift_change_report",    "patient_id": patient_id, "timestamp": t0+210},  # C5->INDUCTION
    ]

def test_A01():
    """
    ORDER — Bromiley: premature PACU transfer from INDUCTION.
    handoff_to_pacu = C5_Handoff. C5 in Anesthesiologist vocab but NOT in INDUCTION.flows -> ORDER.
    Wide timestamps prevent false BURST. Wide final timestamp keeps it outside burst window.
    """
    t = BASE_TS
    setup = _reach_induction_anesthesiologist("consultant_anaesthetist_1", "PT_A01", t)
    events = setup + [
        {"actor_id": "consultant_anaesthetist_1", "action": "handoff_to_pacu",
         "patient_id": "PT_A01", "timestamp": t+280},  # C5 from INDUCTION -> ORDER
    ]
    results = gate_result(events)
    return assert_pass("A01", "ORDER: Anesthesiologist C5_Handoff from INDUCTION (Bromiley)",
                       results, "INADMISSIBLE", "ORDER", 4)

def test_A02():
    """JURISDICTION — RN calls C4_Procedure (tracheostomy). Not in RN vocab."""
    t = BASE_TS
    setup = _reach_induction_rn("rn_theatre_1", "PT_A02", t)
    events = setup + [
        {"actor_id": "rn_theatre_1", "action": "perform_emergency_tracheostomy",
         "patient_id": "PT_A02", "timestamp": t+280},
    ]
    results = gate_result(events)
    return assert_pass("A02", "JURISDICTION: RN calls C4_Procedure (tracheostomy)",
                       results, "INADMISSIBLE", "JURISDICTION", 4)

def test_A03():
    """
    BURST — Bromiley fixation loop: INDUCTION(6)<->EMERGENCE(5).
    Setup with wide timestamps, then tight oscillation.
    C6 (abort_induction): INDUCTION->EMERGENCE (contract 6->5).
    C4 (laryngoscopy_attempt): EMERGENCE->INDUCTION (expand 5->6).
    Three expansions within window -> BURST.
    """
    t = BASE_TS
    setup = _reach_induction_anesthesiologist("consultant_anaesthetist_1", "PT_A03", t)
    tight = t + 211  # just after last setup event
    events = setup + [
        {"actor_id": "consultant_anaesthetist_1", "action": "abort_induction",     "patient_id": "PT_A03", "timestamp": tight+0},   # INDUCTION->EMERGENCE (contract)
        {"actor_id": "consultant_anaesthetist_1", "action": "laryngoscopy_attempt","patient_id": "PT_A03", "timestamp": tight+1},   # EMERGENCE->INDUCTION (expand 1)
        {"actor_id": "consultant_anaesthetist_1", "action": "abort_induction",     "patient_id": "PT_A03", "timestamp": tight+2},
        {"actor_id": "consultant_anaesthetist_1", "action": "laryngoscopy_attempt","patient_id": "PT_A03", "timestamp": tight+3},   # expand 2
        {"actor_id": "consultant_anaesthetist_1", "action": "abort_induction",     "patient_id": "PT_A03", "timestamp": tight+4},
        {"actor_id": "consultant_anaesthetist_1", "action": "laryngoscopy_attempt","patient_id": "PT_A03", "timestamp": tight+5},   # expand 3 -> BURST
    ]
    results = gate_result(events)
    burst_fired = any(v=="INADMISSIBLE" and i=="BURST_CADENCE" for v,i in results)
    fired_at = next((idx for idx,(v,i) in enumerate(results) if v=="INADMISSIBLE" and i=="BURST_CADENCE"), None)
    print(f"{'[PASS]' if burst_fired else '[FAIL]'} A03: BURST_CADENCE: EMERGENCE<->INDUCTION fixation loop")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired

def test_A04():
    events = [
        {"actor_id": "consultant_anaesthetist_1", "action": "check_vitals", "patient_id": "PT_A04", "timestamp": BASE_TS+0},
        {"actor_id": "consultant_anaesthetist_2", "action": "check_vitals", "patient_id": "PT_A04", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A04", "EXIT: anaesthetist_2 on patient bound to anaesthetist_1",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)

def test_B01():
    setup = _reach_induction_anesthesiologist("anesthesiologist_1", "PT_B01", BASE_TS)
    results = gate_result(setup)
    ok = all(v=="ADMISSIBLE" for v,_ in results) and not any(i=="HYSTERESIS" for _,i in results)
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Negative control — clean traversal to INDUCTION, no HYSTERESIS")
    print(f"       verdicts={[v for v,_ in results]}")
    return ok

def test_B02():
    """ORDER fires (C5 from INDUCTION). Then C6->EMERGENCE (unvisited) -> HYSTERESIS."""
    t = BASE_TS
    setup = _reach_induction_anesthesiologist("anesthesiologist_1", "PT_B02", t)
    events = setup + [
        {"actor_id": "anesthesiologist_1", "action": "handoff_to_pacu",         "patient_id": "PT_B02", "timestamp": t+280},  # ORDER
        {"actor_id": "anesthesiologist_1", "action": "monitor_oxygen_saturation","patient_id": "PT_B02", "timestamp": t+281},  # loop in INDUCTION
        {"actor_id": "anesthesiologist_1", "action": "abort_induction",          "patient_id": "PT_B02", "timestamp": t+282},  # C6->EMERGENCE (unvisited) -> HYSTERESIS
    ]
    results = gate_result(events)
    ok = results[4][1] == "ORDER" and results[6][1] == "HYSTERESIS"
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER -> HYSTERESIS")
    print(f"       step 5: {results[4]}, step 7: {results[6]}")
    return ok

def test_B03():
    """JURISDICTION fires (RN calls C4). Then C6->EMERGENCE (unvisited) -> HYSTERESIS."""
    t = BASE_TS
    setup = _reach_induction_rn("rn_theatre_2", "PT_B03", t)
    events = setup + [
        {"actor_id": "rn_theatre_2", "action": "perform_emergency_tracheostomy", "patient_id": "PT_B03", "timestamp": t+280},  # JURISDICTION
        {"actor_id": "rn_theatre_2", "action": "monitor_oxygen_saturation",      "patient_id": "PT_B03", "timestamp": t+281},  # loop
        {"actor_id": "rn_theatre_2", "action": "call_rapid_response",            "patient_id": "PT_B03", "timestamp": t+282},  # C6->EMERGENCE (unvisited) -> HYSTERESIS
    ]
    results = gate_result(events)
    ok = results[4][1] == "JURISDICTION" and results[6][1] == "HYSTERESIS"
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION -> HYSTERESIS")
    print(f"       step 5: {results[4]}, step 7: {results[6]}")
    return ok

def test_C01():
    """ORDER then BURST in same session. Pre-visit EMERGENCE first, then ORDER, then oscillate in visited territory."""
    t = BASE_TS
    setup = _reach_induction_anesthesiologist("anesthesiologist_2", "PT_C01", t)
    tight = t + 211
    events = setup + [
        # Visit EMERGENCE (C6 from INDUCTION) - admissible, visits EMERGENCE
        {"actor_id": "anesthesiologist_2", "action": "abort_induction",          "patient_id": "PT_C01", "timestamp": tight+0},   # INDUCTION->EMERGENCE
        # Return to INDUCTION (C4, admissible, INDUCTION already visited)
        {"actor_id": "anesthesiologist_2", "action": "laryngoscopy_attempt",     "patient_id": "PT_C01", "timestamp": tight+1},   # EMERGENCE->INDUCTION
        # ORDER: C5 from INDUCTION (now EMERGENCE and INDUCTION both visited)
        {"actor_id": "anesthesiologist_2", "action": "handoff_to_pacu",          "patient_id": "PT_C01", "timestamp": tight+2},   # ORDER
        # Oscillate in visited territory (INDUCTION<->EMERGENCE both visited, no HYSTERESIS)
        {"actor_id": "anesthesiologist_2", "action": "abort_induction",          "patient_id": "PT_C01", "timestamp": tight+3},
        {"actor_id": "anesthesiologist_2", "action": "laryngoscopy_attempt",     "patient_id": "PT_C01", "timestamp": tight+4},   # expand 1
        {"actor_id": "anesthesiologist_2", "action": "abort_induction",          "patient_id": "PT_C01", "timestamp": tight+5},
        {"actor_id": "anesthesiologist_2", "action": "laryngoscopy_attempt",     "patient_id": "PT_C01", "timestamp": tight+6},   # expand 2
        {"actor_id": "anesthesiologist_2", "action": "abort_induction",          "patient_id": "PT_C01", "timestamp": tight+7},
        {"actor_id": "anesthesiologist_2", "action": "laryngoscopy_attempt",     "patient_id": "PT_C01", "timestamp": tight+8},   # expand 3 -> BURST
    ]
    results = gate_result(events)
    order_fired = any(v=="INADMISSIBLE" and i=="ORDER"         for v,i in results)
    burst_fired = any(v=="INADMISSIBLE" and i=="BURST_CADENCE" for v,i in results)
    hyst_fired  = any(i=="HYSTERESIS"                          for _,i in results)
    ok = order_fired and burst_fired and not hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} C01: ORDER then BURST_CADENCE (no HYSTERESIS)")
    print(f"       ORDER={order_fired}, BURST={burst_fired}, HYSTERESIS={hyst_fired}")
    return ok

def test_C02():
    """JURISDICTION (RN calls C4), then ORDER (RN calls C5_Handoff from INDUCTION). Both in vocab, wrong states."""
    t = BASE_TS
    setup = _reach_induction_rn("rn_theatre_1", "PT_C02", t)
    events = setup + [
        {"actor_id": "rn_theatre_1", "action": "intubate_patient", "patient_id": "PT_C02", "timestamp": t+280},  # JURISDICTION (C4 not in RN vocab)
        {"actor_id": "rn_theatre_1", "action": "chart_vitals",     "patient_id": "PT_C02", "timestamp": t+281},  # loop
        {"actor_id": "rn_theatre_1", "action": "handoff_to_pacu",  "patient_id": "PT_C02", "timestamp": t+282},  # ORDER (C5 in vocab, not in INDUCTION.flows)
    ]
    results = gate_result(events)
    juris = any(v=="INADMISSIBLE" and i=="JURISDICTION" for v,i in results)
    order = any(v=="INADMISSIBLE" and i=="ORDER"        for v,i in results)
    ok = juris and order
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION then ORDER (RN)")
    print(f"       JURISDICTION={juris}, ORDER={order}")
    print(f"       verdicts={[(v,i) for v,i in results]}")
    return ok

def test_C03():
    compiler = ClinicalCompiler()
    r1 = compiler.compile({"actor_id": "consultant_anaesthetist_1", "action": "check_vitals",                 "patient_id": "PT_C03a", "timestamp": BASE_TS+0})
    r2 = compiler.compile({"actor_id": "consultant_anaesthetist_2", "action": "check_vitals",                 "patient_id": "PT_C03a", "timestamp": BASE_TS+1})  # EXIT
    r3 = compiler.compile({"actor_id": "scrub_tech_1",              "action": "order_medication",             "patient_id": "PT_C03b", "timestamp": BASE_TS+2})  # JURISDICTION (C2 not in Scrub_Tech vocab)
    exit_ok  = r2["verdict"]=="INADMISSIBLE" and r2.get("invariant")=="EXIT"
    juris_ok = r3["verdict"]=="INADMISSIBLE" and r3.get("invariant")=="JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION, independent actors/patients")
    print(f"       EXIT: {r2['verdict']}/{r2.get('invariant')}, JURISDICTION: {r3['verdict']}/{r3.get('invariant')}")
    return ok

def main():
    print("=" * 60)
    print("Clinical Compiler v0.1 — Combinatorial Harness")
    print("=" * 60)
    tests = [
        ("Block A — Independent First-Fire",   [test_A01, test_A02, test_A03, test_A04]),
        ("Block B — Hysteresis Dependency",    [test_B01, test_B02, test_B03]),
        ("Block C — Cross-Invariant Compound", [test_C01, test_C02, test_C03]),
    ]
    total = passed = 0
    for name, block in tests:
        print(f"\n{name}\n" + "-"*40)
        for t in block:
            passed += int(t()); total += 1; print()
    print("=" * 60)
    print(f"Results: {passed}/{total} passed ✓ {'ALL PASS' if passed==total else f'{total-passed} FAILED'}")
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    import sys; sys.exit(0 if main() else 1)
