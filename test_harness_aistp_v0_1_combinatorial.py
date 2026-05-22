"""
AI-STP Combinatorial Harness — v0.1
═══════════════════════════════════════════════════════════════════════

Tests: 10

What this harness validates
───────────────────────────
The same dependency graph that v0.9 demonstrated on the cyber substrate
must also hold on the agentic substrate — using a different compiler,
different action vocabulary, different roles, different flows — but the
identical gate kernel (evaluate_gate, imported from v0.9).

Specifically:

  INDEPENDENT INVARIANTS — can fire as the FIRST and ONLY violation
  in a clean session, with no other invariant active:

      ORDER          (in-role tool, wrong workflow state)
      JURISDICTION   (tool class outside agent's role vocabulary)
      BURST_CADENCE  (≥3 width expansions inside time window)
      EXIT           (RoleConfusion or ActorPivot — session-level collapse)

  DEPENDENT INVARIANT — cannot fire without a prior INADMISSIBLE verdict
  from ORDER or JURISDICTION:

      HYSTERESIS     (post-violation expansion into unvisited state)

  COEXISTENCE — multiple independent invariants can fire sequentially in
  the same session without false coupling.

Architecture invariant
──────────────────────
Gate kernel UNCHANGED. evaluate_gate() is imported verbatim from v0.9.
Only the compiler layer is new (agentic_compiler_v0_1.AgenticCompiler).

If this harness produces the same shape of result as the cyber
combinatorial harness (10/10 with the same dependency structure), then
the dependency graph is a property of the gate, not of either substrate.
"""

import sys
from agentic_compiler_v0_1 import AgenticCompiler
from domain_compiler_v0_9 import evaluate_gate


# ─────────────────────────────────────────────────────────────────────
# Event helper
# ─────────────────────────────────────────────────────────────────────

def event(agent_id: str, tool: str, session_id: str = "default_session") -> dict:
    return {
        "agent_id":   agent_id,
        "tool":       tool,
        "session_id": session_id,
    }


# ─────────────────────────────────────────────────────────────────────
# Test runner — identical pattern to cyber combinatorial harness
# ─────────────────────────────────────────────────────────────────────

def run(label: str, steps: list, expect_decision: str,
        expect_invariant: str | None, expect_step: int | None = None) -> bool:
    ac = AgenticCompiler()
    results = []
    for raw in steps:
        pkt = ac.compile(raw)
        r   = evaluate_gate(pkt)
        results.append(r)

    check_idx = (expect_step - 1) if expect_step else (len(results) - 1)
    result    = results[check_idx]

    ok = (result["decision"]  == expect_decision and
          result["invariant"] == expect_invariant)

    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         expected  : {expect_decision} / {expect_invariant}"
              f"  (step {check_idx + 1})")
        print(f"         got       : {result['decision']} / {result['invariant']}")
        for i, r in enumerate(results):
            print(f"         step {i+1}: {r['decision']} / {r['invariant']}")
    return ok


def run_session(label: str, steps_and_expectations: list) -> bool:
    ac = AgenticCompiler()
    all_ok = True
    failures = []
    results = []
    for i, (raw, exp_dec, exp_inv) in enumerate(steps_and_expectations):
        pkt = ac.compile(raw)
        r   = evaluate_gate(pkt)
        results.append(r)
        if exp_dec is not None:
            ok = (r["decision"] == exp_dec and r["invariant"] == exp_inv)
            if not ok:
                all_ok = False
                failures.append((i + 1, exp_dec, exp_inv, r["decision"], r["invariant"]))

    status = "PASS" if all_ok else "FAIL"
    print(f"  [{status}] {label}")
    if not all_ok:
        for step_num, ed, ei, gd, gi in failures:
            print(f"         step {step_num}: expected {ed}/{ei}, got {gd}/{gi}")
        for i, r in enumerate(results):
            print(f"         step {i+1}: {r['decision']} / {r['invariant']}")
    return all_ok


# ═════════════════════════════════════════════════════════════════════
# CATEGORY A — INDEPENDENT FIRST-FIRE
# Each invariant can be the first and only violation in a clean session.
# ═════════════════════════════════════════════════════════════════════

A_TESTS = [

    # ─── A01: ORDER first-fire alone ─────────────────────────────────
    # research_agent_1 (ResearchAgent) gathers legitimately, then attempts
    # fact_check (T3_Verification) from GATHERING state. T3 is in the
    # ResearchAgent vocabulary (SYNTHESIZING.flows, VERIFYING.flows) but
    # NOT in GATHERING.flows.
    #   → action_in_role=True, action in state_flows=False  ⇒ ORDER.
    # No JURISDICTION (action is in role). No HYSTERESIS (no prior
    # violation). No BURST (insufficient expansions). No EXIT.
    ("A01 — ORDER first-fire alone (fact_check from GATHERING in ResearchAgent)",
     [
         event("research_agent_1", "web_search"),  # IDLE → GATHERING
         event("research_agent_1", "web_search"),  # GATHERING → GATHERING (loop)
         event("research_agent_1", "fact_check"),  # GATHERING → ? (T3 in role, not in flows) ORDER
     ],
     "INADMISSIBLE", "ORDER", 3),

    # ─── A02: JURISDICTION first-fire alone ──────────────────────────
    # research_agent_1 (ResearchAgent) calls send_email (T4_Delivery).
    # T4 is NOT in ResearchAgent vocabulary anywhere.
    #   → action_in_role=False  ⇒ JURISDICTION.
    # The agent is attempting external commitment from a research role.
    ("A02 — JURISDICTION first-fire alone (send_email from ResearchAgent)",
     [
         event("research_agent_1", "web_search"),  # IDLE → GATHERING
         event("research_agent_1", "send_email"),  # T4 not in role → JURISDICTION
     ],
     "INADMISSIBLE", "JURISDICTION", 2),

    # ─── A03: BURST_CADENCE first-fire alone ─────────────────────────
    # research_agent_1 oscillates GATHERING↔SYNTHESIZING via T1/T2.
    # Widths: GATHERING=2, SYNTHESIZING=3. Each G→S is a +1 expansion.
    # IDLE→GATHERING is also a +1 expansion.
    # Three expansions in the time window → BURST.
    # Every transition is admissible. HYSTERESIS not engaged (no prior
    # violation). EXIT not engaged (one agent, one session).
    ("A03 — BURST_CADENCE first-fire alone (GATHERING↔SYNTHESIZING oscillation)",
     [
         event("research_agent_1", "web_search"),     # IDLE(1) → GATHERING(2)    EXP 1
         event("research_agent_1", "summarize"),      # GATHERING(2) → SYNTH(3)   EXP 2
         event("research_agent_1", "web_search"),     # SYNTH(3) → GATHERING(2)   contraction
         event("research_agent_1", "summarize"),      # GATHERING(2) → SYNTH(3)   EXP 3 → BURST
     ],
     "INADMISSIBLE", "BURST_CADENCE", 4),

    # ─── A04: EXIT first-fire alone (actor pivot) ────────────────────
    # research_agent_1 uses session ctx_001 first — registers session→agent_1.
    # research_agent_2 then uses the same session — actor_pivot fires.
    # Both agents are ResearchAgent (no role_confusion). Both perform
    # web_search (T1, admissible from IDLE). The only structural fault
    # is two distinct agents sharing one orchestration session — the
    # agentic analog to two AWS users from one IP.
    # evaluate_gate priority: RoleConfusion|ActorPivot → EXIT.
    ("A04 — EXIT first-fire alone (actor pivot, same session, different agents)",
     [
         event("research_agent_1", "web_search", session_id="ctx_001"),  # binds ctx_001
         event("research_agent_2", "web_search", session_id="ctx_001"),  # pivot → EXIT
     ],
     "INADMISSIBLE", "EXIT", 2),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY B — HYSTERESIS DEPENDENCY
# HYSTERESIS cannot fire without a prior ORDER or JURISDICTION verdict.
# ═════════════════════════════════════════════════════════════════════

B_TESTS = [

    # ─── B01: Clean session into new territory — HYSTERESIS DOES NOT FIRE ─
    # research_agent_1 progresses cleanly through three new states with
    # no prior violation. Each step enters an unvisited state, yet
    # HYSTERESIS does not fire — because there is no prior INADMISSIBLE
    # verdict. The "new territory" condition alone is not sufficient.
    # This is the critical negative control.
    ("B01 — Clean session, new territory, no prior violation → no HYSTERESIS",
     [
         event("research_agent_1", "web_search"),  # IDLE → GATHERING       (new)
         event("research_agent_1", "summarize"),   # GATHERING → SYNTH      (new)
         event("research_agent_1", "fact_check"),  # SYNTH → VERIFYING      (new)
     ],
     "ADMISSIBLE", None, 3),

    # ─── B02: ORDER → HYSTERESIS ─────────────────────────────────────
    # Legitimate work establishes visited={GATHERING, SYNTHESIZING}.
    # ORDER fires (fact_check from GATHERING — T3 in role, not in flows).
    # State unchanged. Agent revisits GATHERING (admissible). Then agent
    # attempts summarize (T2 from GATHERING → SYNTHESIZING).
    # HYSTERESIS check at the summarize step:
    #   prior violation? YES (the fact_check ORDER).
    #   visited non-empty? YES ({GATHERING, SYNTHESIZING}).
    #   T2 in GATHERING.flows? YES.
    #   to_state SYNTHESIZING in visited? YES.
    # Wait — to_state is in visited, so HYSTERESIS should NOT fire here.
    # Instead, use a sequence that ends in unvisited territory:
    ("B02 — ORDER then unvisited expansion → HYSTERESIS",
     [
         event("research_agent_1", "web_search"),  # IDLE → GATHERING       (visited)
         event("research_agent_1", "web_search"),  # GATHERING loop         (still visited: {GATHERING})
         event("research_agent_1", "fact_check"),  # T3 in role, not in GATH.flows → ORDER
         event("research_agent_1", "web_search"),  # GATHERING revisit, admissible
         event("research_agent_1", "summarize"),   # GATHERING → SYNTH (unvisited!) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 5),

    # ─── B03: JURISDICTION → HYSTERESIS ──────────────────────────────
    # Legitimate visit to GATHERING. JURISDICTION fires on send_email
    # (T4 not in ResearchAgent). State unchanged, visited={GATHERING}.
    # Agent then calls summarize (T2: GATHERING → SYNTHESIZING).
    # SYNTHESIZING not in visited → HYSTERESIS.
    ("B03 — JURISDICTION then unvisited expansion → HYSTERESIS",
     [
         event("research_agent_1", "web_search"),  # IDLE → GATHERING       (visited)
         event("research_agent_1", "send_email"),  # T4 not in role → JURISDICTION
         event("research_agent_1", "summarize"),   # GATHERING → SYNTH (unvisited) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 3),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY C — CROSS-INVARIANT COMPOUND
# Multiple independent invariants firing in the same session.
# ═════════════════════════════════════════════════════════════════════

C_TESTS_MULTISTEP = [

    # ─── C01: ORDER fires, then BURST_CADENCE fires later ────────────
    # research_agent_1 oscillates GATHERING↔SYNTHESIZING. At step 4,
    # fact_check from GATHERING fires ORDER (T3 in role, not in
    # GATHERING.flows). State does not advance. visited={GATHERING,
    # SYNTHESIZING}. Continue oscillation within visited states —
    # HYSTERESIS does NOT fire because expansions are to visited
    # territory. BURST trips at step 5 (3rd expansion in window).
    ("C01 — ORDER at step 4, BURST_CADENCE at step 5 (same session, no coupling)",
     [
         (event("research_agent_1", "web_search"),  "ADMISSIBLE",   None),           # 1: IDLE→GATH EXP1
         (event("research_agent_1", "summarize"),   "ADMISSIBLE",   None),           # 2: GATH→SYNTH EXP2
         (event("research_agent_1", "web_search"),  "ADMISSIBLE",   None),           # 3: SYNTH→GATH contraction
         (event("research_agent_1", "fact_check"),  "INADMISSIBLE", "ORDER"),        # 4: T3 from GATH → ORDER
         (event("research_agent_1", "summarize"),   "INADMISSIBLE", "BURST_CADENCE"),# 5: GATH→SYNTH EXP3 → BURST (visited revisit, no HYST)
     ]),

    # ─── C02: JURISDICTION at step 2, ORDER at step 4 ────────────────
    # research_agent_1 fires JURISDICTION (send_email — T4 not in role).
    # visited={GATHERING}. State unchanged. Agent loops within GATHERING
    # via web_search (T1 → GATHERING — visited revisit, admissible).
    # Then fact_check from GATHERING → ORDER (T3 in role, not in flows).
    # HYSTERESIS check at step 4: action T3 not in GATHERING.flows →
    # returns False. evaluate() reaches the inadmissible branch with
    # order_violation=True → ORDER fires.
    # Two independent invariants in the same session.
    ("C02 — JURISDICTION at step 2, ORDER at step 4 (sequential independent)",
     [
         (event("research_agent_1", "web_search"),  "ADMISSIBLE",   None),           # 1: IDLE→GATH
         (event("research_agent_1", "send_email"),  "INADMISSIBLE", "JURISDICTION"), # 2: T4 not in role
         (event("research_agent_1", "web_search"),  "ADMISSIBLE",   None),           # 3: GATH loop (visited revisit)
         (event("research_agent_1", "fact_check"),  "INADMISSIBLE", "ORDER"),        # 4: T3 from GATH → ORDER
     ]),

    # ─── C03: EXIT then JURISDICTION (cross-actor coexistence) ───────
    # Three agents in one session.
    # Step 1: research_agent_1 at ctx_001 — registers session→agent_1.
    # Step 2: research_agent_2 at ctx_001 — actor_pivot → EXIT.
    # Step 3: delivery_agent_1 at ctx_999 (separate session) calls
    #         web_search. T1 is NOT in DeliveryAgent vocabulary —
    #         JURISDICTION (DeliveryAgent may only call T4_Delivery tools).
    # Two independent invariants fire for two different agents. The EXIT
    # on agent_2 has no effect on delivery_agent_1's evaluation — per-
    # identity state is genuinely independent.
    ("C03 — EXIT (actor pivot) at step 2, JURISDICTION (separate agent) at step 3",
     [
         (event("research_agent_1", "web_search", session_id="ctx_001"), "ADMISSIBLE",   None),           # 1
         (event("research_agent_2", "web_search", session_id="ctx_001"), "INADMISSIBLE", "EXIT"),         # 2
         (event("delivery_agent_1", "web_search", session_id="ctx_999"), "INADMISSIBLE", "JURISDICTION"), # 3
     ]),
]


# ═════════════════════════════════════════════════════════════════════
# Test runner
# ═════════════════════════════════════════════════════════════════════

def main() -> None:
    passed = 0
    failed = 0

    print()
    print("═══════════════════════════════════════════════════════════════")
    print("  AI-STP Combinatorial Invariant Dependency Structure — v0.1")
    print("  (Same gate kernel as v0.9. New compiler. New substrate.)")
    print("═══════════════════════════════════════════════════════════════")

    print("\n── A: INDEPENDENT FIRST-FIRE (4 tests) ──")
    for label, steps, ed, ei, es in A_TESTS:
        ok = run(label, steps, ed, ei, es)
        passed += int(ok); failed += int(not ok)

    print("\n── B: HYSTERESIS DEPENDENCY (3 tests) ──")
    for label, steps, ed, ei, es in B_TESTS:
        ok = run(label, steps, ed, ei, es)
        passed += int(ok); failed += int(not ok)

    print("\n── C: CROSS-INVARIANT COMPOUND (3 tests) ──")
    for label, session in C_TESTS_MULTISTEP:
        ok = run_session(label, session)
        passed += int(ok); failed += int(not ok)

    total = passed + failed
    print()
    print("─" * 63)
    print(f"  Results: {passed}/{total} passed", end="")
    if failed == 0:
        print("  ✓ ALL PASS")
        print()
        print("  Combinatorial structure validated on agentic substrate:")
        print("    • ORDER, JURISDICTION, BURST_CADENCE, EXIT are independent.")
        print("      Each can fire as the first and only violation of a session.")
        print("    • HYSTERESIS is dependent. It cannot fire without a prior")
        print("      INADMISSIBLE verdict from ORDER or JURISDICTION.")
        print("    • Independent invariants coexist in one session without")
        print("      false coupling — sequential fires retain their labels.")
        print()
        print("  This dependency graph matches the cyber substrate result.")
        print("  The graph is therefore a property of the GATE, not of either")
        print("  substrate — empirically supported across the syscall layer")
        print("  (SCDS-H v0.9) and the workflow layer (AI-STP v0.1).")
    else:
        print(f"  ✗ {failed} FAILED")
    print("─" * 63)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
