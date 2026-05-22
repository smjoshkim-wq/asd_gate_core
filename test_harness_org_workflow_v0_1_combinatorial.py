"""
Organizational Workflow Combinatorial Harness — v0.1
═══════════════════════════════════════════════════════════════════════

Tests: 10

What this harness validates
───────────────────────────
The same dependency graph validated on the cyber substrate (v0.9) and
the agentic substrate (AI-STP v0.1) must also hold on the organizational
workflow substrate — using a different compiler, different action
vocabulary (human pipeline actions, not syscalls or tool calls), different
roles (Analyst/Approver, not IAM roles or agent types), different flow
topology — but the identical gate kernel (evaluate_gate, imported from
domain_compiler_v0_9).

This substrate is NOT computational. Actors are humans. Actions are
approvals, assessments, and authorizations. Workflow instances are
procurement pipelines, HR processes, financial authorizations.

Specifically:

  INDEPENDENT INVARIANTS — can fire as the FIRST and ONLY violation
  in a clean session, with no other invariant active:

      ORDER          (action in role, wrong pipeline stage)
      JURISDICTION   (action outside actor's role vocabulary)
      BURST_CADENCE  (≥3 width expansions inside time window)
      EXIT           (actor pivot — wrong actor for this workflow instance)

  DEPENDENT INVARIANT — cannot fire without a prior INADMISSIBLE verdict
  from ORDER or JURISDICTION:

      HYSTERESIS     (post-violation expansion into unvisited pipeline state)

  COEXISTENCE — multiple independent invariants can fire sequentially in
  one workflow instance without false coupling.

Architecture invariant
──────────────────────
Gate kernel UNCHANGED. evaluate_gate() is imported verbatim from
domain_compiler_v0_9. Only the compiler layer is new
(org_workflow_compiler_v0_1.OrgWorkflowCompiler).

If this harness produces the same shape of result as the cyber and
agentic harnesses, the dependency graph is a property of the gate across
three substrates spanning:
  - syscall layer        (domain_compiler_v0_9)
  - tool-call layer      (agentic_compiler_v0_1)
  - human decision layer (org_workflow_compiler_v0_1)

Domain vocabulary used in this harness
───────────────────────────────────────
  analyst_alice / analyst_bob / analyst_carol  → Analyst role
  approver_dave / approver_eve                 → Approver role

  A1_Review:    review_request, read_document, check_status, view_record
  A2_Assess:    assess_risk, evaluate_compliance, score_application
  A3_Recommend: recommend_approval, flag_concern, escalate, add_note
  A4_Authorize: approve_payment, sign_contract, authorize_release
  A5_Execute:   transfer_funds, release_shipment  (not in any role)

Workflow state graph (Analyst):
  IDLE → REVIEWING(2) → ASSESSING(3) → RECOMMENDING(1)
  Loop-backs: REVIEWING→REVIEWING (A1), ASSESSING→REVIEWING (A1),
              ASSESSING→ASSESSING (A2), RECOMMENDING→RECOMMENDING (A3)

Workflow state graph (Approver):
  IDLE → AUTHORIZING(1) → AUTHORIZING(1) (loop)
"""

import sys
import os

# Allow running from the project directory where domain_compiler_v0_9.py lives
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from domain_compiler_v0_9 import evaluate_gate


# ─────────────────────────────────────────────────────────────────────
# Event helper
# ─────────────────────────────────────────────────────────────────────

def event(actor_id: str, action: str, workflow_id: str = "wf_default") -> dict:
    return {
        "actor_id":    actor_id,
        "action":      action,
        "workflow_id": workflow_id,
    }


# ─────────────────────────────────────────────────────────────────────
# Test runners — identical pattern to agentic combinatorial harness
# ─────────────────────────────────────────────────────────────────────

def run(label: str, steps: list, expect_decision: str,
        expect_invariant: str | None, expect_step: int | None = None) -> bool:
    oc = OrgWorkflowCompiler()
    results = []
    for raw in steps:
        pkt = oc.compile(raw)
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
    oc = OrgWorkflowCompiler()
    all_ok   = True
    failures = []
    results  = []
    for i, (raw, exp_dec, exp_inv) in enumerate(steps_and_expectations):
        pkt = oc.compile(raw)
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
    # analyst_alice (Analyst) reviews legitimately, reaching REVIEWING.
    # Then attempts recommend_approval (A3_Recommend) from REVIEWING.
    # A3 IS in the Analyst vocabulary (ASSESSING.flows, RECOMMENDING.flows)
    # but NOT in REVIEWING.flows — the analyst must assess before
    # recommending. Structural sequencing violation.
    #   → action_in_role=True, action_in_state=False  ⇒ ORDER.
    # No JURISDICTION (A3 is in Analyst role). No HYSTERESIS (no prior
    # violation). No BURST (one expansion only). No EXIT.
    ("A01 — ORDER first-fire alone (recommend_approval from REVIEWING, skipping ASSESSING)",
     [
         event("analyst_alice", "review_request"),    # IDLE → REVIEWING
         event("analyst_alice", "review_request"),    # REVIEWING loop
         event("analyst_alice", "recommend_approval"),# A3 in role, not in REVIEWING → ORDER
     ],
     "INADMISSIBLE", "ORDER", 3),

    # ─── A02: JURISDICTION first-fire alone ──────────────────────────
    # analyst_alice (Analyst) calls approve_payment (A4_Authorize).
    # A4 is NOT in the Analyst vocabulary anywhere.
    # The structural claim: "analyst cannot authorize payment" is not
    # a policy — it is a jurisdiction boundary.
    #   → action_in_role=False  ⇒ JURISDICTION.
    ("A02 — JURISDICTION first-fire alone (analyst attempts approve_payment)",
     [
         event("analyst_alice", "review_request"),    # IDLE → REVIEWING
         event("analyst_alice", "approve_payment"),   # A4 not in Analyst → JURISDICTION
     ],
     "INADMISSIBLE", "JURISDICTION", 2),

    # ─── A03: BURST_CADENCE first-fire alone ─────────────────────────
    # analyst_alice oscillates REVIEWING(2)↔ASSESSING(3) via A1/A2.
    # Each REVIEWING→ASSESSING transition is a width expansion (+1).
    # IDLE→REVIEWING is also an expansion.
    # Three expansions in the time window → BURST_CADENCE.
    # Every individual step is admissible. No prior violation.
    # Structural analog: analyst oscillating between "need more data"
    # and "reassessing" in a rapid loop — burst instability in the
    # decision pipeline.
    ("A03 — BURST_CADENCE first-fire alone (REVIEWING↔ASSESSING oscillation)",
     [
         event("analyst_alice", "review_request"),   # IDLE(1) → REVIEWING(2)  EXP 1
         event("analyst_alice", "assess_risk"),       # REVIEWING(2) → ASSESSING(3) EXP 2
         event("analyst_alice", "review_request"),   # ASSESSING(3) → REVIEWING(2) contraction
         event("analyst_alice", "assess_risk"),       # REVIEWING(2) → ASSESSING(3) EXP 3 → BURST
     ],
     "INADMISSIBLE", "BURST_CADENCE", 4),

    # ─── A04: EXIT first-fire alone (actor pivot) ────────────────────
    # analyst_alice opens workflow wf_procurement_001, establishing
    # the session→actor binding. analyst_bob then presents events on
    # the same workflow instance. Two distinct analysts on one workflow
    # instance is a trajectory geometry collapse — the workflow's actor
    # identity is no longer consistent.
    # Both are Analysts (no role confusion). Both call review_request
    # (A1, admissible from IDLE). The only structural fault is the
    # identity mismatch on the workflow instance.
    ("A04 — EXIT first-fire alone (actor pivot: two analysts, one workflow instance)",
     [
         event("analyst_alice", "review_request", "wf_procurement_001"),  # binds wf→alice
         event("analyst_bob",   "review_request", "wf_procurement_001"),  # pivot → EXIT
     ],
     "INADMISSIBLE", "EXIT", 2),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY B — HYSTERESIS DEPENDENCY
# HYSTERESIS cannot fire without a prior INADMISSIBLE verdict.
# ═════════════════════════════════════════════════════════════════════

B_TESTS = [

    # ─── B01: Clean session into new territory — HYSTERESIS DOES NOT FIRE
    # analyst_alice progresses through three new states cleanly:
    # REVIEWING → ASSESSING → RECOMMENDING. Each step enters an unvisited
    # state. HYSTERESIS does NOT fire — there is no prior INADMISSIBLE
    # verdict. The "new territory" condition alone is not sufficient.
    # Critical negative control.
    ("B01 — Clean pipeline progression, no prior violation → no HYSTERESIS",
     [
         event("analyst_alice", "review_request"),    # IDLE → REVIEWING    (new)
         event("analyst_alice", "assess_risk"),        # REVIEWING → ASSESSING (new)
         event("analyst_alice", "recommend_approval"), # ASSESSING → RECOMMENDING (new)
     ],
     "ADMISSIBLE", None, 3),

    # ─── B02: ORDER → HYSTERESIS ─────────────────────────────────────
    # analyst_alice reviews legitimately: IDLE → REVIEWING (visited).
    # ORDER fires: recommend_approval from REVIEWING (A3 in role, not
    # in REVIEWING.flows). State unchanged. visited={REVIEWING}.
    # alice reviews again (REVIEWING loop — visited revisit, admissible).
    # alice then assesses (REVIEWING → ASSESSING).
    # HYSTERESIS check at assess_risk:
    #   prior violation? YES (the ORDER on recommend_approval)
    #   visited non-empty? YES ({REVIEWING})
    #   A2 in REVIEWING.flows? YES
    #   to_state ASSESSING in visited? NO → HYSTERESIS.
    # Structural meaning: an analyst who attempted an out-of-sequence
    # recommendation cannot subsequently be trusted to enter new pipeline
    # stages — their admissible state space is deformed.
    ("B02 — ORDER then expansion into unvisited stage → HYSTERESIS",
     [
         event("analyst_alice", "review_request"),    # IDLE → REVIEWING    (visited)
         event("analyst_alice", "review_request"),    # REVIEWING loop       (visited: {REVIEWING})
         event("analyst_alice", "recommend_approval"),# A3 from REVIEWING → ORDER
         event("analyst_alice", "review_request"),    # REVIEWING loop       (visited revisit, admissible)
         event("analyst_alice", "assess_risk"),        # REVIEWING → ASSESSING (unvisited!) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 5),

    # ─── B03: JURISDICTION → HYSTERESIS ──────────────────────────────
    # analyst_alice reviews: IDLE → REVIEWING (visited={REVIEWING}).
    # JURISDICTION fires: approve_payment (A4 not in Analyst role).
    # State unchanged. visited={REVIEWING}.
    # alice then calls assess_risk: REVIEWING → ASSESSING.
    # HYSTERESIS check: prior violation YES, ASSESSING not in visited → HYSTERESIS.
    # Structural meaning: an analyst who attempted unauthorized authorization
    # cannot subsequently advance through the pipeline normally.
    ("B03 — JURISDICTION then expansion into unvisited stage → HYSTERESIS",
     [
         event("analyst_alice", "review_request"),    # IDLE → REVIEWING    (visited)
         event("analyst_alice", "approve_payment"),   # A4 not in Analyst → JURISDICTION
         event("analyst_alice", "assess_risk"),        # REVIEWING → ASSESSING (unvisited) → HYSTERESIS
     ],
     "INADMISSIBLE", "HYSTERESIS", 3),
]


# ═════════════════════════════════════════════════════════════════════
# CATEGORY C — CROSS-INVARIANT COMPOUND
# Multiple independent invariants fire sequentially in one workflow.
# ═════════════════════════════════════════════════════════════════════

C_TESTS_MULTISTEP = [

    # ─── C01: ORDER fires, then BURST_CADENCE fires later ────────────
    # analyst_alice oscillates REVIEWING↔ASSESSING. At step 4,
    # recommend_approval from REVIEWING fires ORDER (A3 in role, not in
    # REVIEWING.flows). State does not advance. visited={REVIEWING,
    # ASSESSING}. Oscillation continues within visited states — HYSTERESIS
    # does NOT fire because ASSESSING is already visited. BURST trips at
    # step 5 (3rd expansion in window).
    # Two independent invariants, same session, no coupling.
    ("C01 — ORDER at step 4, BURST_CADENCE at step 5 (same session, no coupling)",
     [
         (event("analyst_alice", "review_request"),    "ADMISSIBLE",   None),            # 1: IDLE→REV EXP1
         (event("analyst_alice", "assess_risk"),        "ADMISSIBLE",   None),            # 2: REV→ASSES EXP2
         (event("analyst_alice", "review_request"),    "ADMISSIBLE",   None),            # 3: ASSES→REV contraction
         (event("analyst_alice", "recommend_approval"),"INADMISSIBLE", "ORDER"),         # 4: A3 from REV → ORDER
         (event("analyst_alice", "assess_risk"),        "INADMISSIBLE", "BURST_CADENCE"), # 5: REV→ASSES EXP3 → BURST (visited revisit, no HYST)
     ]),

    # ─── C02: JURISDICTION at step 2, ORDER at step 4 ────────────────
    # analyst_alice fires JURISDICTION (approve_payment — A4 not in role).
    # visited={REVIEWING}. State unchanged. alice reviews again (visited
    # revisit, admissible). Then recommend_approval from REVIEWING → ORDER
    # (A3 in role, not in REVIEWING.flows). HYSTERESIS does not fire at
    # step 4 because recommend_approval is not in REVIEWING.flows —
    # check_hysteresis returns False (action not in state_flows), so
    # evaluate() reaches the inadmissible branch with order_violation=True.
    # Two independent invariants in the same workflow.
    ("C02 — JURISDICTION at step 2, ORDER at step 4 (sequential independent)",
     [
         (event("analyst_alice", "review_request"),    "ADMISSIBLE",   None),            # 1: IDLE→REV
         (event("analyst_alice", "approve_payment"),   "INADMISSIBLE", "JURISDICTION"),  # 2: A4 not in Analyst
         (event("analyst_alice", "review_request"),    "ADMISSIBLE",   None),            # 3: REV loop (visited revisit)
         (event("analyst_alice", "recommend_approval"),"INADMISSIBLE", "ORDER"),         # 4: A3 from REV → ORDER
     ]),

    # ─── C03: EXIT then JURISDICTION (cross-actor coexistence) ───────
    # Step 1: analyst_alice at wf_hr_001 — binds workflow→alice.
    # Step 2: analyst_bob at wf_hr_001 — actor_pivot → EXIT.
    #         The HR workflow's actor identity is compromised.
    # Step 3: approver_dave at wf_finance_002 (separate workflow) calls
    #         review_request. A1_Review is NOT in Approver vocabulary —
    #         JURISDICTION fires (approver attempting review step).
    # Two independent invariants fire for two different actors. The EXIT
    # on alice/bob has no effect on approver_dave's evaluation — per-
    # identity state is genuinely independent across workflow instances.
    ("C03 — EXIT (actor pivot) at step 2, JURISDICTION (separate actor) at step 3",
     [
         (event("analyst_alice", "review_request",  "wf_hr_001"),      "ADMISSIBLE",   None),           # 1
         (event("analyst_bob",   "review_request",  "wf_hr_001"),      "INADMISSIBLE", "EXIT"),         # 2
         (event("approver_dave", "review_request",  "wf_finance_002"), "INADMISSIBLE", "JURISDICTION"), # 3
     ]),
]


# ═════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════

def main() -> None:
    passed = 0
    failed = 0

    print()
    print("═══════════════════════════════════════════════════════════════")
    print("  Org Workflow Combinatorial Invariant Dependency Structure")
    print("  v0.1 — Third substrate. Not computational.")
    print("  (Same gate kernel as v0.9 and AI-STP v0.1.)")
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
        print("  Combinatorial structure validated on org workflow substrate:")
        print("    • ORDER, JURISDICTION, BURST_CADENCE, EXIT are independent.")
        print("      Each can fire as the first and only violation of a session.")
        print("    • HYSTERESIS is dependent. It cannot fire without a prior")
        print("      INADMISSIBLE verdict from ORDER or JURISDICTION.")
        print("    • Independent invariants coexist in one session without")
        print("      false coupling — sequential fires retain their labels.")
        print()
        print("  This substrate is NOT computational.")
        print("  Actors are humans. Actions are approvals, assessments,")
        print("  authorizations. Workflow instances are procurement pipelines,")
        print("  HR processes, financial authorizations.")
        print()
        print("  The dependency graph matches cyber (syscall) and agentic")
        print("  (tool-call) substrate results. Across three substrates,")
        print("  the graph is a property of the GATE KERNEL, not of")
        print("  any substrate, domain, or vocabulary.")
    else:
        print(f"  ✗ {failed} FAILED")
    print("─" * 63)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
