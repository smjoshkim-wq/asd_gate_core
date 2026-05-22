"""
Combinatorial Test Harness — Financial Compiler v0.1 (corrected)
C01 redesigned: pre-visit all states, then ORDER via F1_Read from POOL_ACTIVE,
then BURST oscillation in already-visited territory.
"""
import sys
sys.path.insert(0, ".")
from financial_compiler_v0_1 import run_session, FinancialCompiler

BASE_TS = 3_000_000.0

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

def test_A01():
    events = [
        {"actor_id": "uw_citi_desk", "action": "asset_level_verification",  "deal_id": "RMBS_A01", "timestamp": BASE_TS+0},
        {"actor_id": "uw_citi_desk", "action": "advance_to_securitization", "deal_id": "RMBS_A01", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A01", "ORDER: Underwriter bypasses audit (2008 waiver bypass)",
                       gate_result(events), "INADMISSIBLE", "ORDER", 1)

def test_A02():
    events = [
        {"actor_id": "cra_sp_analyst", "action": "due_diligence_review",   "deal_id": "CDO_A02", "timestamp": BASE_TS+0},
        {"actor_id": "cra_sp_analyst", "action": "pool_asset_aggregation", "deal_id": "CDO_A02", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A02", "JURISDICTION: CRA calls F2_Expand (co-structuring)",
                       gate_result(events), "INADMISSIBLE", "JURISDICTION", 1)

def test_A03():
    t = BASE_TS
    events = [
        {"actor_id": "uw_ubs_desk", "action": "asset_level_verification",      "deal_id": "CDO_A03", "timestamp": t+0},
        {"actor_id": "uw_ubs_desk", "action": "due_diligence_review",          "deal_id": "CDO_A03", "timestamp": t+1},
        {"actor_id": "uw_ubs_desk", "action": "waterfall_logic_structuring",   "deal_id": "CDO_A03", "timestamp": t+2},
        {"actor_id": "uw_ubs_desk", "action": "cdo_squared_resecuritization",  "deal_id": "CDO_A03", "timestamp": t+3},
        {"actor_id": "uw_ubs_desk", "action": "waterfall_logic_structuring",   "deal_id": "CDO_A03", "timestamp": t+4},
        {"actor_id": "uw_ubs_desk", "action": "cdo_squared_resecuritization",  "deal_id": "CDO_A03", "timestamp": t+5},
        {"actor_id": "uw_ubs_desk", "action": "waterfall_logic_structuring",   "deal_id": "CDO_A03", "timestamp": t+6},
    ]
    results = gate_result(events)
    burst_fired = any(v == "INADMISSIBLE" and i == "BURST_CADENCE" for v,i in results)
    fired_at = next((idx for idx,(v,i) in enumerate(results) if v=="INADMISSIBLE" and i=="BURST_CADENCE"), None)
    print(f"{'[PASS]' if burst_fired else '[FAIL]'} A03: BURST_CADENCE: CDO-squared oscillation")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired

def test_A04():
    events = [
        {"actor_id": "uw_citi_desk", "action": "asset_level_verification", "deal_id": "RMBS_A04", "timestamp": BASE_TS+0},
        {"actor_id": "uw_ubs_desk",  "action": "asset_level_verification", "deal_id": "RMBS_A04", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A04", "EXIT: uw_ubs_desk on deal bound to uw_citi_desk",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)

def test_B01():
    events = [
        {"actor_id": "uw_alpha", "action": "asset_level_verification",    "deal_id": "RMBS_B01", "timestamp": BASE_TS+0},
        {"actor_id": "uw_alpha", "action": "due_diligence_review",        "deal_id": "RMBS_B01", "timestamp": BASE_TS+1},
        {"actor_id": "uw_alpha", "action": "waterfall_logic_structuring", "deal_id": "RMBS_B01", "timestamp": BASE_TS+2},
    ]
    results = gate_result(events)
    ok = all(v=="ADMISSIBLE" for v,_ in results) and not any(i=="HYSTERESIS" for _,i in results)
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Negative control — clean traversal, no HYSTERESIS")
    print(f"       verdicts={[v for v,_ in results]}")
    return ok

def test_B02():
    events = [
        {"actor_id": "uw_citi_desk", "action": "asset_level_verification",  "deal_id": "RMBS_B02", "timestamp": BASE_TS+0},
        {"actor_id": "uw_citi_desk", "action": "advance_to_securitization", "deal_id": "RMBS_B02", "timestamp": BASE_TS+1},  # ORDER
        {"actor_id": "uw_citi_desk", "action": "waiver_log_inspection",     "deal_id": "RMBS_B02", "timestamp": BASE_TS+2},  # loop
        {"actor_id": "uw_citi_desk", "action": "underwriting_file_inspection","deal_id": "RMBS_B02","timestamp": BASE_TS+3}, # F1->POOL_ACTIVE (unvisited)->HYSTERESIS
    ]
    results = gate_result(events)
    ok = results[1][1] == "ORDER" and results[3][1] == "HYSTERESIS"
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER -> HYSTERESIS")
    print(f"       step 2: {results[1]}, step 4: {results[3]}")
    return ok

def test_B03():
    events = [
        {"actor_id": "cra_moodys_analyst", "action": "due_diligence_review",    "deal_id": "CDO_B03", "timestamp": BASE_TS+0},
        {"actor_id": "cra_moodys_analyst", "action": "pool_asset_aggregation",  "deal_id": "CDO_B03", "timestamp": BASE_TS+1},  # JURISDICTION
        {"actor_id": "cra_moodys_analyst", "action": "backtesting_analysis",    "deal_id": "CDO_B03", "timestamp": BASE_TS+2},  # loop
        {"actor_id": "cra_moodys_analyst", "action": "issue_credit_rating",     "deal_id": "CDO_B03", "timestamp": BASE_TS+3},  # RATED (unvisited)->HYSTERESIS
    ]
    results = gate_result(events)
    ok = results[1][1] == "JURISDICTION" and results[3][1] == "HYSTERESIS"
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION -> HYSTERESIS")
    print(f"       step 2: {results[1]}, step 4: {results[3]}")
    return ok

def test_C01():
    """
    ORDER then BURST in same session.
    Fix: pre-visit POOL_ACTIVE and SECURITIZING BEFORE ORDER fires.
    ORDER via F1_Read from POOL_ACTIVE (F1 in Underwriter vocab, not in POOL_ACTIVE.flows).
    Then oscillate in visited territory (no HYSTERESIS).
    Wide timestamps for setup (>60s apart), tight for oscillation.
    """
    t = BASE_TS
    events = [
        # Pre-visit all states first (wide spacing — each >60s apart)
        {"actor_id": "uw_alpha", "action": "asset_level_verification",    "deal_id": "CDO_C01", "timestamp": t+0},     # IDLE->AUDIT_PENDING
        {"actor_id": "uw_alpha", "action": "due_diligence_review",        "deal_id": "CDO_C01", "timestamp": t+70},    # AUDIT_PENDING->POOL_ACTIVE
        {"actor_id": "uw_alpha", "action": "waterfall_logic_structuring", "deal_id": "CDO_C01", "timestamp": t+140},   # POOL_ACTIVE->SECURITIZING (visit)
        {"actor_id": "uw_alpha", "action": "cdo_squared_resecuritization","deal_id": "CDO_C01", "timestamp": t+210},   # SECURITIZING->POOL_ACTIVE (back)
        # ORDER: F1_Read from POOL_ACTIVE (F1 in vocab, NOT in POOL_ACTIVE.flows)
        {"actor_id": "uw_alpha", "action": "compliance_screening",        "deal_id": "CDO_C01", "timestamp": t+280},   # ORDER fires
        # Now oscillate in visited territory (tight timestamps for BURST)
        {"actor_id": "uw_alpha", "action": "waterfall_logic_structuring", "deal_id": "CDO_C01", "timestamp": t+281},   # POOL_ACTIVE->SECURITIZING (expand 1)
        {"actor_id": "uw_alpha", "action": "cdo_squared_resecuritization","deal_id": "CDO_C01", "timestamp": t+282},   # SECURITIZING->POOL_ACTIVE
        {"actor_id": "uw_alpha", "action": "waterfall_logic_structuring", "deal_id": "CDO_C01", "timestamp": t+283},   # expand 2
        {"actor_id": "uw_alpha", "action": "cdo_squared_resecuritization","deal_id": "CDO_C01", "timestamp": t+284},
        {"actor_id": "uw_alpha", "action": "waterfall_logic_structuring", "deal_id": "CDO_C01", "timestamp": t+285},   # expand 3 -> BURST
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
    events = [
        {"actor_id": "uw_beta", "action": "asset_level_verification",  "deal_id": "RMBS_C02", "timestamp": BASE_TS+0},
        {"actor_id": "uw_beta", "action": "enforce_margin_call",       "deal_id": "RMBS_C02", "timestamp": BASE_TS+1},  # JURISDICTION (F3 not in vocab)
        {"actor_id": "uw_beta", "action": "waiver_log_inspection",     "deal_id": "RMBS_C02", "timestamp": BASE_TS+2},  # loop
        {"actor_id": "uw_beta", "action": "advance_to_securitization", "deal_id": "RMBS_C02", "timestamp": BASE_TS+3},  # ORDER (F4 from AUDIT_PENDING)
    ]
    results = gate_result(events)
    juris = any(v=="INADMISSIBLE" and i=="JURISDICTION" for v,i in results)
    order = any(v=="INADMISSIBLE" and i=="ORDER"        for v,i in results)
    ok = juris and order
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION then ORDER, sequential")
    print(f"       JURISDICTION={juris}, ORDER={order}")
    print(f"       verdicts={[(v,i) for v,i in results]}")
    return ok

def test_C03():
    compiler = FinancialCompiler()
    r1 = compiler.compile({"actor_id": "uw_citi_desk",   "action": "asset_level_verification", "deal_id": "RMBS_C03",  "timestamp": BASE_TS+0})
    r2 = compiler.compile({"actor_id": "uw_ubs_desk",    "action": "asset_level_verification", "deal_id": "RMBS_C03",  "timestamp": BASE_TS+1})  # EXIT
    r3 = compiler.compile({"actor_id": "cra_fitch_analyst","action": "pool_asset_aggregation", "deal_id": "CDO_C03b",  "timestamp": BASE_TS+2})  # JURISDICTION
    exit_ok  = r2["verdict"]=="INADMISSIBLE" and r2.get("invariant")=="EXIT"
    juris_ok = r3["verdict"]=="INADMISSIBLE" and r3.get("invariant")=="JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION, independent actors/deals")
    print(f"       EXIT: {r2['verdict']}/{r2.get('invariant')}, JURISDICTION: {r3['verdict']}/{r3.get('invariant')}")
    return ok

def main():
    print("=" * 60)
    print("Financial Compiler v0.1 — Combinatorial Harness")
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
