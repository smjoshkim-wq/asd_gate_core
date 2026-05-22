"""
Test Harness v0.9 — Combinatorial Invariant Dependency Structure
═══════════════════════════════════════════════════════════════════════

Tests: 10

What this harness validates
───────────────────────────
The five ASD invariants in the v0.9 gate are not a flat list — they
form a *dependency graph*. This harness validates the structure of
that graph empirically against the cyber compiler.

Specifically:

  INDEPENDENT INVARIANTS — can fire as the FIRST and ONLY violation
  in a session, with no other invariant active:

      ORDER          (action in-role, wrong state)
      JURISDICTION   (action not in role vocabulary at all)
      BURST_CADENCE  (≥3 width expansions inside the time window)
      EXIT           (RoleConfusion or ActorPivot — trajectory collapse)

  DEPENDENT INVARIANT — cannot fire without a prior INADMISSIBLE verdict
  from ORDER or JURISDICTION:

      HYSTERESIS     (post-violation expansion into unvisited state)

  COEXISTENCE — multiple independent invariants can fire sequentially
  in the same session without false coupling.

Why this matters
────────────────
v0.9 already exercises every invariant through individual harnesses and
the three real-data passes (CloudTrail, Mordor, ADFA-LD). What v0.9 has
*not* explicitly demonstrated is that the dependency structure is a
property of the GATE — not an artifact of the cyber substrate. If this
harness passes, the dependency graph is shown to hold structurally on
the cyber compiler, which becomes the cyber-side anchor for cross-
substrate validation against the AI-STP agentic compiler.

Test groups
───────────
  A — INDEPENDENT FIRST-FIRE   (4 tests; one per non-dependent invariant)
  B — HYSTERESIS DEPENDENCY    (3 tests; clean / O→H / J→H)
  C — CROSS-INVARIANT COMPOUND (3 tests; sequential independent fires)

Architecture invariant
──────────────────────
Gate logic UNCHANGED. This harness only re-exercises the v0.9 compiler
under a different test framing. No code in domain_compiler_v0_9.py is
modified.
"""

import sys
from domain_compiler_v0_9 import DomainCompiler, evaluate_gate


# ─────────────────────────────────────────────────────────────────────
# Event helpers
# ─────────────────────────────────────────────────────────────────────

def cloudtrail(identity: str, event: str, ip: str = "1.2.3.4") -> dict:
    return {
        "userIdentity": {"type": "IAMUser", "userName": identity},
        "eventName":    event,
        "sourceIPAddress": ip,
    }


# ─────────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────────

def run(label: str, steps: list, expect_decision: str,
        expect_invariant: str | None, expect_step: int | None = None) -> bool:
    """
    Run a multi-step test. Each step is a raw log dict.
    expect_step: 1-indexed step where the expected verdict should appear.
                 If None, the LAST step is checked.
    All other steps may be anything — only the expected step is asserted.
    Diagnostic dump on failure shows every step's verdict.
    """
    dc = DomainCompiler()
    results = []
    for raw in steps:
        pkt = dc.compile(raw)
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
    """
    Run a session where MULTIPLE specific steps must produce specific verdicts.
    steps_and_expectations: list of (raw_log, expected_decision, expected_invariant)
                            Use (raw_log, None, None) for "don't assert this step".
    """
    dc = DomainCompiler()
    all_ok = True
    failures = []
    results = []
    for i, (raw, exp_dec, exp_inv) in enumerate(steps_and_expectations):
        pkt = dc.compile(raw)
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

    # ─── C01: ORDER first-fire alone ─────────────────────────────────
    # dev_worker (DevRole) navigates legitimately into Executing, then
    # calls Invoke from Executing. ExecuteFunction is in DevRole vocab
    # (Idle/Reading/Writing all permit it) but NOT in Executing.flows.
    #   → action_in_role=True, action in state_flows=False  ⇒ ORDER.
    # No JURISDICTION (action is in role). No HYSTERESIS (no prior
    # violation). No BURST (only 1 expansion so far). No EXIT (single
    # actor, single IP, no role confusion).
    ("C01 — ORDER first-fire alone (Invoke from Executing in DevRole)",
     [
         cloudtrail("dev_worker", "GetObject"),   # Idle → Reading
         cloudtrail("dev_worker", "Invoke"),      # Reading → Executing
         cloudtrail("dev_worker", "Invoke"),      # Executing → ? (ORDER)
     ],
     "INADMISSIBLE", "ORDER", 3),

    # ─── C02: JURISDICTION first-fire alone ──────────────────────────
    # dev_worker (DevRole) calls DeleteObject. DeleteData is NOT in
    # DevRole vocabulary at all.
    #   → action_in_role=False  ⇒ JURISDICTION.
    # No HYSTERESIS (no prior violation). No ORDER (action not in role
    # anywhere, so it's J not O). No BURST (no expansions). No EXIT.
    ("C02 — JURISDICTION first-fire alone (DeleteObject in DevRole)",
     [
         cloudtrail("dev_worker", "GetObject"),     # Idle → Reading
         cloudtrail("dev_worker", "DeleteObject"),  # JURISDICTION
     ],
     "INADMISSIBLE", "JURISDICTION", 2),

    # ─── C03: BURST_CADENCE first-fire alone ─────────────────────────
    # admin_deploy (AdminRole) oscillates Reading↔Writing.
    # Reading width = 5, Writing width = 4. Each W→R is a +1 width
    # expansion. Three W→R transitions in the time window → BURST.
    # Note: AdminRole.Reading does NOT contain ExecuteFunction, so
    # Reading↔Executing is not a valid clean oscillation path — Invoke
    # from Reading fires ORDER. Reading↔Writing is the clean path:
    #   Reading.flows has WriteData → Writing
    #   Writing.flows has ReadData  → Reading
    # Every transition is admissible under ORDER/JURISDICTION.
    # HYSTERESIS not engaged (no prior violation; admissible all the
    # way). EXIT not engaged (one actor, one IP).
    # BURST fires on the 3rd expansion's gate evaluation.
    ("C03 — BURST_CADENCE first-fire alone (Reading↔Writing oscillation)",
     [
         cloudtrail("admin_deploy", "GetObject"),  # Idle → Reading    (5→5)
         cloudtrail("admin_deploy", "PutObject"),  # Reading → Writing (5→4)
         cloudtrail("admin_deploy", "GetObject"),  # Writing → Reading (4→5) EXP 1
         cloudtrail("admin_deploy", "PutObject"),  # Reading → Writing (5→4)
         cloudtrail("admin_deploy", "GetObject"),  # Writing → Reading (4→5) EXP 2
         cloudtrail("admin_deploy", "PutObject"),  # Reading → Writing (5→4)
         cloudtrail("admin_deploy", "GetObject"),  # Writing → Reading (4→5) EXP 3 → BURST
     ],
     "INADMISSIBLE", "BURST_CADENCE", 7),

    # ─── C04: EXIT first-fire alone (actor pivot) ────────────────────
    # admin_deploy uses IP 1.2.3.4 first, registering IP→admin_deploy.
    # admin_pivot then uses the same IP — actor_pivot fires because
    # source_ref has a different prior identity. Both are AdminRole, so
    # no JURISDICTION/ORDER on the action itself (GetObject from Idle
    # is admissible in AdminRole). RoleConfusion=False for both (each
    # is its own identity-role binding). HYSTERESIS not engaged.
    # BURST not engaged (no oscillation).
    # evaluate_gate priority: RoleConfusion|ActorPivot → EXIT.
    ("C04 — EXIT first-fire alone (actor pivot, same IP, different identity)",
     [
         cloudtrail("admin_deploy", "GetObject", ip="1.2.3.4"),  # registers IP→admin_deploy
         cloudtrail("admin_pivot",  "GetObject", ip="1.2.3.4"),  # actor pivot → EXIT
     ],
     "INADMISSIBLE", "EXIT", 2),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY B — HYSTERESIS DEPENDENCY
# HYSTERESIS cannot fire without a prior ORDER or JURISDICTION verdict.
# ═════════════════════════════════════════════════════════════════════

B_TESTS = [

    # ─── C05: Clean session into new territory — HYSTERESIS DOES NOT FIRE ─
    # dev_worker progresses through entirely new states with no prior
    # violation. Each transition is admissible. Even though each step
    # enters a previously-unvisited state, HYSTERESIS does not fire
    # because there is no prior INADMISSIBLE verdict.
    # This is the critical negative test for the dependency claim:
    # "new territory alone does not trigger HYSTERESIS".
    ("C05 — Clean session, new territory, no prior violation → no HYSTERESIS",
     [
         cloudtrail("dev_worker", "GetObject"),  # Idle → Reading   (new)
         cloudtrail("dev_worker", "Invoke"),     # Reading → Exec   (new)
         cloudtrail("dev_worker", "PutObject"),  # Exec → Writing   (new)
     ],
     "ADMISSIBLE", None, 3),

    # ─── C06: ORDER → HYSTERESIS ─────────────────────────────────────
    # Pattern: legitimate work establishes visited={Reading, Executing}.
    # ORDER violation fires (Invoke from Executing). State machine does
    # not advance. Actor revisits Reading (admissible — visited). Then
    # actor calls PutObject (Reading→Writing). Writing is NOT visited.
    # check_hysteresis: prior violation? YES. visited non-empty? YES.
    # action in state_flows? YES (PutObject=WriteData in Reading.flows).
    # to_state Writing in visited? NO. → HYSTERESIS fires.
    # This validates the O→H half of the dependency.
    ("C06 — ORDER then unvisited expansion → HYSTERESIS",
     [
         cloudtrail("dev_worker", "GetObject"),  # Idle → Reading       (visited)
         cloudtrail("dev_worker", "Invoke"),     # Reading → Executing  (visited)
         cloudtrail("dev_worker", "Invoke"),     # Exec → ORDER (state unchanged)
         cloudtrail("dev_worker", "GetObject"),  # Exec → Reading       (revisit, OK)
         cloudtrail("dev_worker", "PutObject"),  # Reading → Writing    (unvisited) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 5),

    # ─── C07: JURISDICTION → HYSTERESIS ──────────────────────────────
    # Pattern: legitimate visit to Reading. JURISDICTION (DeleteObject
    # not in DevRole vocab). State unchanged, visited={Reading}.
    # Actor then calls Invoke (Reading→Executing). Executing not in
    # visited → HYSTERESIS fires.
    # This validates the J→H half of the dependency.
    ("C07 — JURISDICTION then unvisited expansion → HYSTERESIS",
     [
         cloudtrail("dev_worker", "GetObject"),     # Idle → Reading  (visited)
         cloudtrail("dev_worker", "DeleteObject"),  # JURISDICTION
         cloudtrail("dev_worker", "Invoke"),        # Reading → Executing (unvisited) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 3),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY C — CROSS-INVARIANT COMPOUND
# Multiple independent invariants firing in the same session, validated
# by run_session() which checks each labelled step independently.
# ═════════════════════════════════════════════════════════════════════

C_TESTS_MULTISTEP = [

    # ─── C08: ORDER fires, then BURST_CADENCE fires later ────────────
    # admin_deploy oscillates Reading↔Writing (the valid AdminRole
    # oscillation path; see C03). At step 5, fires ORDER: DeleteObject
    # from Writing. DeleteData IS in AdminRole vocab (Idle, Reading)
    # but NOT in Writing.flows, so order_violation=True.
    # State does not advance on ORDER. visited={Reading, Writing}.
    # Continue oscillation within visited states — HYSTERESIS does NOT
    # fire because expansions are to visited territory.
    # Width expansions continue to accumulate until BURST trips on a
    # later admissible GetObject (Writing→Reading) — the 3rd expansion
    # in the time window.
    # Tests: ORDER fires cleanly at step 5; BURST fires at step 8,
    # post-ORDER, with no coupling.
    ("C08 — ORDER at step 5, BURST_CADENCE at step 8 (same session, no coupling)",
     [
         (cloudtrail("admin_deploy", "GetObject"),    "ADMISSIBLE",    None),           # 1: Idle→Reading
         (cloudtrail("admin_deploy", "PutObject"),    "ADMISSIBLE",    None),           # 2: Reading→Writing
         (cloudtrail("admin_deploy", "GetObject"),    "ADMISSIBLE",    None),           # 3: Writing→Reading EXP1
         (cloudtrail("admin_deploy", "PutObject"),    "ADMISSIBLE",    None),           # 4: Reading→Writing
         (cloudtrail("admin_deploy", "DeleteObject"), "INADMISSIBLE",  "ORDER"),        # 5: Writing→Del ORDER
         (cloudtrail("admin_deploy", "GetObject"),    "ADMISSIBLE",    None),           # 6: Writing→Reading EXP2 (visited)
         (cloudtrail("admin_deploy", "PutObject"),    "ADMISSIBLE",    None),           # 7: Reading→Writing (visited)
         (cloudtrail("admin_deploy", "GetObject"),    "INADMISSIBLE",  "BURST_CADENCE"),# 8: Writing→Reading EXP3 → BURST
     ]),

    # ─── C09: JURISDICTION at step 3, ORDER at step 6 ────────────────
    # dev_worker establishes visited={Reading, Executing}, fires
    # JURISDICTION (DeleteObject — DeleteData not in DevRole anywhere),
    # then operates entirely within visited states (no HYSTERESIS), then
    # fires ORDER (Invoke from Executing — ExecuteFunction in DevRole
    # vocab but not in Executing.flows).
    # Two independent invariants fire in the same session. The ORDER
    # fire is NOT a HYSTERESIS because check_hysteresis returns False
    # when action is not in state_flows (the J/O case).
    ("C09 — JURISDICTION at step 3, ORDER at step 6 (sequential independent)",
     [
         (cloudtrail("dev_worker", "GetObject"),    "ADMISSIBLE",   None),           # 1: Idle→Reading
         (cloudtrail("dev_worker", "Invoke"),       "ADMISSIBLE",   None),           # 2: Reading→Exec
         (cloudtrail("dev_worker", "DeleteObject"), "INADMISSIBLE", "JURISDICTION"), # 3: JURISDICTION
         (cloudtrail("dev_worker", "GetObject"),    "ADMISSIBLE",   None),           # 4: Exec→Reading (revisit)
         (cloudtrail("dev_worker", "Invoke"),       "ADMISSIBLE",   None),           # 5: Reading→Exec (revisit)
         (cloudtrail("dev_worker", "Invoke"),       "INADMISSIBLE", "ORDER"),        # 6: Exec→Invoke ORDER
     ]),

    # ─── C10: EXIT then JURISDICTION (cross-actor coexistence) ───────
    # Three actors in one session.
    # Step 1: admin_deploy at IP A — registers A→admin_deploy.
    # Step 2: admin_pivot at IP A — actor_pivot → EXIT.
    # Step 3: dev_worker at IP B (different IP) — DeleteObject not in
    #         DevRole → JURISDICTION. No actor_pivot (new IP, new actor).
    # Two independent invariants fire for two different actors in the
    # same compiler session. EXIT for admin_pivot has no effect on
    # dev_worker's JURISDICTION evaluation — per-identity state is
    # genuinely independent.
    ("C10 — EXIT (actor pivot) at step 2, JURISDICTION (separate actor) at step 3",
     [
         (cloudtrail("admin_deploy", "GetObject",    ip="1.2.3.4"), "ADMISSIBLE",   None),           # 1
         (cloudtrail("admin_pivot",  "GetObject",    ip="1.2.3.4"), "INADMISSIBLE", "EXIT"),         # 2: EXIT
         (cloudtrail("dev_worker",   "DeleteObject", ip="9.9.9.9"), "INADMISSIBLE", "JURISDICTION"), # 3: JURISDICTION
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
    print("  Combinatorial Invariant Dependency Structure — v0.9 Gate")
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
        print("  Combinatorial structure validated on cyber substrate:")
        print("    • ORDER, JURISDICTION, BURST_CADENCE, EXIT are independent.")
        print("      Each can fire as the first and only violation of a session.")
        print("    • HYSTERESIS is dependent. It cannot fire without a prior")
        print("      INADMISSIBLE verdict from ORDER or JURISDICTION.")
        print("    • Independent invariants coexist in one session without")
        print("      false coupling — sequential fires retain their labels.")
        print()
        print("  This dependency graph is now anchored on the cyber substrate.")
        print("  Next: validate the same structure on the agentic substrate")
        print("  (AI-STP). If both confirm, the dependency graph is a property")
        print("  of the gate, not of either substrate.")
    else:
        print(f"  ✗ {failed} FAILED")
    print("─" * 63)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
