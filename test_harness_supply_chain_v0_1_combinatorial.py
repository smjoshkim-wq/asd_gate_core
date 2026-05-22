"""
Combinatorial Test Harness — Supply Chain Custody Transfer Compiler v0.1
═════════════════════════════════════════════════════════════════════════

Block A — Independent First-Fire (4 tests)
  A01 — ORDER:         Consignee calls S7_Delivery from ORDER_PLACED. S7 IS
                       in Consignee vocab (QUALITY_INSPECTION) but NOT in
                       ORDER_PLACED.flows. Suez/Ever Given structural analog:
                       attempting downstream delivery release before reaching
                       the prerequisite custody state.
  A02 — JURISDICTION:  Carrier calls S7_Delivery (issue_delivery_order). S7
                       not in Carrier vocab anywhere. Hanjin Shipping anchor:
                       Carrier asserted S7 cargo release authority where the
                       jurisdictional substrate had collapsed.
  A03 — BURST_CADENCE: Shipper rapid progression ORDER_PLACED(1) →
                       PRODUCTION(2) → EXPORT_DOCS_PREPARED(3) → EXPORT_CLEARED(4).
                       Three monotonic expansions. PPE 2020 analog: rapid S1/S2
                       chaining without centralized hold gates.
  A04 — EXIT:          Second Shipper on shipment bound to first Shipper.

Block B — Hysteresis Dependency (3 tests)
  B01 — Negative control: clean Shipper progression, 70s spacing.
  B02 — ORDER → HYSTERESIS: Shipper visits PRODUCTION and EXPORT_DOCS_PREPARED,
                            then ORDER (S1 from EXPORT_DOCS_PREPARED), then
                            S2 → EXPORT_CLEARED (unvisited) → HYSTERESIS.
  B03 — JURISDICTION → HYSTERESIS: Shipper visits PRODUCTION, then S7
                                   (JURISDICTION), then S2 → EXPORT_DOCS_PREPARED
                                   (unvisited) → HYSTERESIS.

Block C — Cross-Invariant Compound (3 tests)
  C01 — ORDER then BURST (separate shipments).
  C02 — JURISDICTION ×2 — TradeAuthority has only S1 at ORDER_PLACED; other
                          action classes fire JURISDICTION.
  C03 — EXIT then JURISDICTION (independent shipments).

Expected: 10/10 PASS
"""

import sys
sys.path.insert(0, ".")
from supply_chain_compiler_v0_1 import run_session, SupplyChainCompiler

BASE_TS = 10_000_000.0


def gate_result(events):
    return [(r["decision"], r.get("invariant")) for r in run_session(events)]


def assert_pass(test_id, desc, results, decision, invariant, at_step):
    d, inv = results[at_step]
    ok = (d == decision and (invariant is None or inv == invariant))
    print(f"{'[PASS]' if ok else '[FAIL]'} {test_id}: {desc}")
    print(f"       step {at_step+1}: decision={d}, invariant={inv}")
    if not ok:
        print(f"       EXPECTED: decision={decision}, invariant={invariant}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block A — Independent First-Fire
# ═══════════════════════════════════════════════════════════════════════

def test_A01():
    """
    ORDER: Consignee calls S7_Delivery (accept_goods) from ORDER_PLACED.
    S7 IS in Consignee vocab (QUALITY_INSPECTION → DELIVERED) but NOT in
    ORDER_PLACED.flows. Suez/Ever Given structural analog: downstream
    delivery release attempted before reaching prerequisite custody state.
    """
    events = [
        # Consignee starts at ORDER_PLACED. S7 not in ORDER_PLACED.flows → ORDER
        {"actor_id": "consignee_a", "action": "accept_goods", "shipment_id": "EVER_GIVEN_A01", "timestamp": BASE_TS+0},
    ]
    return assert_pass("A01", "ORDER: Consignee calls S7_Delivery from ORDER_PLACED (Suez/Ever Given analog)",
                       gate_result(events), "INADMISSIBLE", "ORDER", 0)


def test_A02():
    """
    JURISDICTION: Carrier calls S7_Delivery (issue_delivery_order). S7 not
    in Carrier vocab anywhere — Carrier authority is S4 (loading) and S6
    (transit). Hanjin Shipping 2016 anchor: Carrier asserted S7 cargo
    release authority where the jurisdictional substrate had collapsed.
    """
    events = [
        {"actor_id": "carrier_hanjin", "action": "issue_delivery_order", "shipment_id": "HANJIN_A02", "timestamp": BASE_TS+0},
    ]
    return assert_pass("A02", "JURISDICTION: Carrier calls S7_Delivery (Hanjin authority collision)",
                       gate_result(events), "INADMISSIBLE", "JURISDICTION", 0)


def test_A03():
    """
    BURST_CADENCE: Shipper rapid progression through expanding state widths.
    ORDER_PLACED(1) → S1 → PRODUCTION(2)[+1]
    PRODUCTION(2) → S2 → EXPORT_DOCS_PREPARED(3)[+1]
    EXPORT_DOCS_PREPARED(3) → S2 → EXPORT_CLEARED(4)[+1]
    = 3 expansions within BURST window = BURST_CADENCE fires.

    PPE 2020 analog: rapid S1/S2 chaining without intermediate hold gates.
    """
    t = BASE_TS
    events = [
        {"actor_id": "shipper_evergreen", "action": "issue_purchase_order",       "shipment_id": "PPE_A03", "timestamp": t+0},
        {"actor_id": "shipper_evergreen", "action": "issue_commercial_invoice",   "shipment_id": "PPE_A03", "timestamp": t+1},
        {"actor_id": "shipper_evergreen", "action": "declare_vgm",                "shipment_id": "PPE_A03", "timestamp": t+2},
    ]
    results = gate_result(events)
    burst_fired = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in results)
    fired_at = next((idx for idx, (d, i) in enumerate(results)
                     if d == "INADMISSIBLE" and i == "BURST_CADENCE"), None)
    print(f"{'[PASS]' if burst_fired else '[FAIL]'} A03: BURST_CADENCE: Shipper rapid progression")
    print(f"       BURST fired at step {fired_at+1 if fired_at is not None else 'N/A'}")
    return burst_fired


def test_A04():
    """EXIT: second Shipper on shipment bound to first Shipper."""
    events = [
        {"actor_id": "shipper_evergreen", "action": "issue_purchase_order", "shipment_id": "SHIP_A04", "timestamp": BASE_TS+0},
        {"actor_id": "shipper_a",         "action": "issue_purchase_order", "shipment_id": "SHIP_A04", "timestamp": BASE_TS+1},
    ]
    return assert_pass("A04", "EXIT: shipper_a on shipment bound to shipper_evergreen",
                       gate_result(events), "INADMISSIBLE", "EXIT", 1)


# ═══════════════════════════════════════════════════════════════════════
# Block B — Hysteresis Dependency
# ═══════════════════════════════════════════════════════════════════════

def test_B01():
    """
    Negative control: clean Shipper progression with 70s timestamp spacing
    to avoid false BURST during legitimate document chain.
    """
    t = BASE_TS
    events = [
        {"actor_id": "shipper_a", "action": "issue_purchase_order",     "shipment_id": "CLEAN_B01", "timestamp": t+0},
        {"actor_id": "shipper_a", "action": "issue_commercial_invoice", "shipment_id": "CLEAN_B01", "timestamp": t+70},
        {"actor_id": "shipper_a", "action": "declare_vgm",              "shipment_id": "CLEAN_B01", "timestamp": t+140},
    ]
    results = gate_result(events)
    ok = all(d == "ADMISSIBLE" for d, _ in results)
    print(f"{'[PASS]' if ok else '[FAIL]'} B01: Negative control — clean Shipper traversal, no HYSTERESIS")
    print(f"       decisions={[d for d, _ in results]}")
    return ok


def test_B02():
    """
    ORDER → HYSTERESIS: Shipper admissible S1 (visits PRODUCTION), then
    admissible S2 (visits EXPORT_DOCS_PREPARED). Then S1 from
    EXPORT_DOCS_PREPARED — S1 in Shipper vocab (PRODUCTION) but NOT in
    EXPORT_DOCS_PREPARED.flows → ORDER. Then S2 from EXPORT_DOCS_PREPARED
    → EXPORT_CLEARED (unvisited) → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Admissible: visits PRODUCTION
        {"actor_id": "shipper_evergreen", "action": "issue_purchase_order",     "shipment_id": "HYST_B02", "timestamp": t+0},
        # Admissible: visits EXPORT_DOCS_PREPARED
        {"actor_id": "shipper_evergreen", "action": "issue_commercial_invoice", "shipment_id": "HYST_B02", "timestamp": t+70},
        # ORDER: S1 in vocab but not in EXPORT_DOCS_PREPARED.flows
        {"actor_id": "shipper_evergreen", "action": "issue_purchase_order",     "shipment_id": "HYST_B02", "timestamp": t+140},
        # HYSTERESIS: S2 from EXPORT_DOCS_PREPARED → EXPORT_CLEARED (unvisited)
        {"actor_id": "shipper_evergreen", "action": "declare_vgm",              "shipment_id": "HYST_B02", "timestamp": t+210},
    ]
    results = gate_result(events)
    order_fired = results[2][0] == "INADMISSIBLE" and results[2][1] == "ORDER"
    hyst_fired  = results[3][0] == "INADMISSIBLE" and results[3][1] == "HYSTERESIS"
    ok = order_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B02: ORDER → HYSTERESIS (Shipper S1 from EXPORT_DOCS, then S2 to unvisited)")
    print(f"       step 3: {results[2]}, step 4: {results[3]}")
    return ok


def test_B03():
    """
    JURISDICTION → HYSTERESIS: Shipper admissible S1 (visits PRODUCTION).
    Then S7 (accept_goods) from PRODUCTION — S7 not in Shipper vocab →
    JURISDICTION. Then S2 from PRODUCTION → EXPORT_DOCS_PREPARED (unvisited)
    → HYSTERESIS.
    """
    t = BASE_TS
    events = [
        # Admissible: visits PRODUCTION
        {"actor_id": "shipper_a", "action": "issue_purchase_order", "shipment_id": "HYST_B03", "timestamp": t+0},
        # JURISDICTION: S7 not in Shipper vocab
        {"actor_id": "shipper_a", "action": "accept_goods",         "shipment_id": "HYST_B03", "timestamp": t+70},
        # HYSTERESIS: S2 from PRODUCTION → EXPORT_DOCS_PREPARED (unvisited)
        {"actor_id": "shipper_a", "action": "issue_commercial_invoice","shipment_id": "HYST_B03", "timestamp": t+140},
    ]
    results = gate_result(events)
    juris_fired = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    hyst_fired  = results[2][0] == "INADMISSIBLE" and results[2][1] == "HYSTERESIS"
    ok = juris_fired and hyst_fired
    print(f"{'[PASS]' if ok else '[FAIL]'} B03: JURISDICTION → HYSTERESIS (Shipper S7, then S2 to unvisited)")
    print(f"       step 2: {results[1]}, step 3: {results[2]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Block C — Cross-Invariant Compound
# ═══════════════════════════════════════════════════════════════════════

def test_C01():
    """ORDER then BURST_CADENCE (separate shipments, same compiler)."""
    t = BASE_TS
    order_events = [
        {"actor_id": "consignee_b", "action": "accept_goods", "shipment_id": "ORDER_C01", "timestamp": t+0},
    ]
    burst_events = [
        {"actor_id": "shipper_a", "action": "issue_purchase_order",     "shipment_id": "BURST_C01", "timestamp": t+1000},
        {"actor_id": "shipper_a", "action": "issue_commercial_invoice", "shipment_id": "BURST_C01", "timestamp": t+1001},
        {"actor_id": "shipper_a", "action": "declare_vgm",              "shipment_id": "BURST_C01", "timestamp": t+1002},
    ]
    r_order = gate_result(order_events)
    r_burst = gate_result(burst_events)
    order_ok = r_order[0][0] == "INADMISSIBLE" and r_order[0][1] == "ORDER"
    burst_ok = any(d == "INADMISSIBLE" and i == "BURST_CADENCE" for d, i in r_burst)
    ok = order_ok and burst_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C01: ORDER then BURST_CADENCE (compound)")
    print(f"       ORDER: {r_order[0]}; BURST fired: {burst_ok}")
    return ok


def test_C02():
    """
    JURISDICTION ×2 — TradeAuthority has only S1 at ORDER_PLACED. Other
    action classes (S5, S7) fire JURISDICTION.
    """
    events = [
        {"actor_id": "trade_authority", "action": "issue_customs_release", "shipment_id": "TA_C02", "timestamp": BASE_TS+0},
        {"actor_id": "trade_authority", "action": "accept_goods",          "shipment_id": "TA_C02", "timestamp": BASE_TS+1},
    ]
    results = gate_result(events)
    j1 = results[0][0] == "INADMISSIBLE" and results[0][1] == "JURISDICTION"
    j2 = results[1][0] == "INADMISSIBLE" and results[1][1] == "JURISDICTION"
    ok = j1 and j2
    print(f"{'[PASS]' if ok else '[FAIL]'} C02: JURISDICTION ×2 — TradeAuthority calls S5 then S7")
    print(f"       step 1: {results[0]}, step 2: {results[1]}")
    return ok


def test_C03():
    """EXIT then JURISDICTION (independent shipments)."""
    exit_events = [
        {"actor_id": "shipper_evergreen", "action": "issue_purchase_order", "shipment_id": "EXIT_C03",  "timestamp": BASE_TS+0},
        {"actor_id": "shipper_a",         "action": "issue_purchase_order", "shipment_id": "EXIT_C03",  "timestamp": BASE_TS+1},
    ]
    juris_events = [
        {"actor_id": "carrier_hanjin", "action": "issue_delivery_order", "shipment_id": "JURIS_C03", "timestamp": BASE_TS+10},
    ]
    r_exit  = gate_result(exit_events)
    r_juris = gate_result(juris_events)
    exit_ok  = r_exit[1][0]  == "INADMISSIBLE" and r_exit[1][1]  == "EXIT"
    juris_ok = r_juris[0][0] == "INADMISSIBLE" and r_juris[0][1] == "JURISDICTION"
    ok = exit_ok and juris_ok
    print(f"{'[PASS]' if ok else '[FAIL]'} C03: EXIT then JURISDICTION (independent shipments)")
    print(f"       EXIT: {r_exit[1]}, JURISDICTION: {r_juris[0]}")
    return ok


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("Supply Chain Compiler v0.1 — Combinatorial Test Harness")
    print("═"*60 + "\n")

    tests = [
        ("Block A — Independent First-Fire", [test_A01, test_A02, test_A03, test_A04]),
        ("Block B — Hysteresis Dependency",  [test_B01, test_B02, test_B03]),
        ("Block C — Cross-Invariant Compound",[test_C01, test_C02, test_C03]),
    ]

    total = passed = 0
    for block_name, block_tests in tests:
        print(f"\n{block_name}")
        print("-" * 40)
        for t in block_tests:
            result = t()
            total += 1
            if result:
                passed += 1
            print()

    print("═"*60)
    print(f"RESULT: {passed}/{total} PASS")
    print("═"*60)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
