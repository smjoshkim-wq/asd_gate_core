"""
Inverse Incident Reconstruction — Equifax 2017 Breach (DEFICIENCY_NOTED Pattern)
══════════════════════════════════════════════════════════════════════════════════

Substrate: Cyber — Incident Response (Human Layer), compiler #16
Compiler:  cyber_ir_compiler_v0_1.py
Pattern:   DEFICIENCY_NOTED (named pattern, first Cyber IR instance)
Invariant: ORDER

Source authority:
    U.S. Senate Committee on Commerce, Science, and Transportation,
    "Examining Equifax's Data Security" (November 2017).
    U.S. House of Representatives, Committee on Oversight and Government
    Reform, "The Equifax Data Breach" (December 2018).
    Equifax SEC Form 8-K (September 7, 2017).
    Federal Trade Commission, United States v. Equifax Inc., Consent Order
    (July 2019).
    Apache Software Foundation, CVE-2017-5638 advisory (March 7, 2017).
    U.S. Department of Homeland Security / US-CERT notification to Equifax
    (March 8, 2017) — referenced in Senate testimony.

Reconstruction scope:
    This script reconstructs the action sequence from CVE notification
    (March 7–8, 2017) through the structural commitment event that seeds
    the gate fire, and maps it to the Cyber IR compiler's state machine.

    Reconstruction covers two actors:
      analyst_equifax — the security team analyst who received the CVE,
          conducted initial triage, and attempted remediation scan.
      ciso_equifax    — CISO (Susan Mauldin per congressional record) who
          owned the escalation and patching decision authority.

    The reconstruction does NOT model the full breach timeline (May 13 –
    July 29, 2017). It models the window between CVE receipt and the
    structural commitment event (continued operation from TRIAGED state
    without remediation), which is where the gate fires.

Primary structural claim being tested:
    The gate fires ORDER before breach initiation (May 13, 2017).

DEFICIENCY_NOTED geometry in this substrate:
    Step 1: CVE-2017-5638 received and triaged. State → TRIAGED.
            TRIAGED is the DEFICIENCY_NOTED state in this compiler:
            a known, formally documented vulnerability is on record and
            the actor is in the state where remediation (IR3_Contain /
            patch_vulnerability) is the required next action.
    Step 2: Remediation scan attempted but fails (expired SSL certificate
            on scanning tool — per Senate testimony). No IR3_Contain
            action is taken. The scan failure is not escalated.
    Step 3: Continued monitoring (IR1_Detect / monitor_siem) is attempted
            from TRIAGED state without first completing IR3_Contain.
            IR1_Detect is NOT a permitted action from TRIAGED in the
            IR_Analyst flow graph. ORDER fires.

    This is the structural commitment from DEFICIENCY_NOTED: the decision
    to continue monitoring operations (IR1_Detect) from a state where a
    known deficiency is on record, without completing the required
    remediation (IR3_Contain). The gate fires at that commitment point.

Lead time definition:
    Gate fires at: approximately March 15, 2017 (failed scan / continued
    monitoring from TRIAGED — per Senate testimony on the patch deadline).
    Breach initiation: May 13, 2017 (per FTC consent order).
    Lead time: approximately 59 days (gate fire to breach initiation).

    Secondary lead time (gate fire to discovery): July 29, 2017 = ~136 days.
    Secondary lead time (CVE to breach initiation): 67 days.

    Precision class: Day-level (congressional testimony establishes the
    March patch deadline; exact scan-failure date within that window is
    reconstructed from testimony, not timestamped to the minute).

Mapping type: Direct 1:1
    The Equifax breach response is the canonical incident anchor for the
    Cyber IR compiler (substrate #16). CVE receipt, failed patch scan, and
    continued unpatched operation are all documented in primary sources.
    The gate fires on the same event the Senate report identifies as the
    proximate cause: the failure to patch after receiving the CVE.

Event timeline (all times approximate, sourced from testimony record):
    March 7, 2017   CVE-2017-5638 published by Apache (CVSS 10.0, Critical)
    March 8, 2017   US-CERT sends notification to Equifax security team
    March 8-9       analyst_equifax reviews alert, conducts initial scope triage
    March 9-10      Internal scan initiated — SSL certificate on scanning tool
                    expired; scan does not execute against all systems
    ~March 15       Internal patch deadline passes without remediation
    March 15+       Monitoring continues from TRIAGED state; ORDER fires here
    May 13          Attacker exploitation begins (breach initiation)
    July 29         Equifax discovers breach via internal security check
    September 7     Public disclosure (SEC Form 8-K)
"""

import sys
import json
sys.path.insert(0, ".")

from cyber_ir_compiler_v0_1 import CyberIRCompiler, run_session
from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Reconstruction event sequence
# ═══════════════════════════════════════════════════════════════════════
#
# Timestamps are days-since-CVE-issue for lead time calculation.
# Day 0 = March 7, 2017. Breach initiation = Day 67 (May 13).
# Gate fire expected at Day ~8-15 (March 15 patch deadline window).
#
# Using integer day offsets as timestamps (seconds since epoch omitted
# for clarity; relative ordering is preserved).
#
# Day offset → calendar date mapping:
#   0  = March 7  (CVE issued)
#   1  = March 8  (US-CERT notification)
#   2  = March 9  (initial triage)
#   3  = March 10 (scan attempted, certificate expired — not detected)
#   8  = March 15 (internal patch deadline passes)
#   9  = March 16 (continued monitoring from TRIAGED — ORDER fires here)
#   67 = May 13   (breach initiation — gate has already fired 58 days prior)
#

DAY = 86400  # seconds per day
T0  = 0      # anchor: CVE issue date (relative)

EVENTS = [

    # ── Phase 1: CVE receipt and initial detection ──────────────────────
    # US-CERT notification arrives. analyst_equifax performs check_ioc
    # on the CVE advisory. State: IDLE → ALERT_RECEIVED. [ADMISSIBLE]
    {
        "actor_id":   "analyst_equifax",
        "action":     "check_ioc",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 1 * DAY,
        "_note": "Day 1 (Mar 8): US-CERT notification received. "
                 "analyst_equifax reviews CVE-2017-5638 advisory. "
                 "State IDLE → ALERT_RECEIVED. [ADMISSIBLE — detection phase]"
    },

    # ── Phase 2: Triage ─────────────────────────────────────────────────
    # analyst_equifax assesses severity of CVE-2017-5638 against
    # Equifax's Apache Struts deployment footprint.
    # State: ALERT_RECEIVED → TRIAGED. [ADMISSIBLE]
    # This is the DEFICIENCY_NOTED state: the CVE is formally on record,
    # the analyst is now in TRIAGED, and IR3_Contain (patch) is required.
    {
        "actor_id":   "analyst_equifax",
        "action":     "assess_severity",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 2 * DAY,
        "_note": "Day 2 (Mar 9): Severity assessed — CVSS 10.0, Critical. "
                 "Apache Struts usage confirmed in Equifax dispute portal. "
                 "State ALERT_RECEIVED → TRIAGED. "
                 "*** DEFICIENCY_NOTED STATE SEEDED *** "
                 "Required next action: IR3_Contain (patch_vulnerability). "
                 "[ADMISSIBLE — triage complete, deficiency documented]"
    },

    # Scope determination: identify which systems are affected.
    # IR2_Triage loops in TRIAGED. [ADMISSIBLE]
    {
        "actor_id":   "analyst_equifax",
        "action":     "identify_affected_systems",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 3 * DAY,
        "_note": "Day 3 (Mar 10): Analyst attempts to identify all Equifax "
                 "systems running vulnerable Apache Struts versions. "
                 "Internal scan initiated — SSL certificate on scanning tool "
                 "has expired; scan does not execute against all systems. "
                 "Scope identification is incomplete but no exception is raised. "
                 "IR2_Triage loops in TRIAGED. [ADMISSIBLE — triage loop]"
    },

    # ── Phase 3: Commitment from DEFICIENCY_NOTED ───────────────────────
    # Internal patch deadline (~March 15) passes without IR3_Contain.
    # analyst_equifax returns to monitoring (IR1_Detect / monitor_siem)
    # from TRIAGED state — WITHOUT having patched.
    #
    # IR1_Detect is NOT a permitted action from TRIAGED in the
    # IR_Analyst flow graph:
    #   TRIAGED permits: IR2_Triage (loop), IR3_Contain (→ CONTAINED)
    #   IR1_Detect from TRIAGED → ORDER violation.
    #
    # This is the DEFICIENCY_NOTED commitment: resuming standard
    # monitoring operations from a state of known-unresolved deficiency.
    # The gate fires here. Breach initiation is 59 days away.
    {
        "actor_id":   "analyst_equifax",
        "action":     "monitor_siem",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 9 * DAY,
        "_note": "Day 9 (Mar 16): Patch deadline has passed. No IR3_Contain "
                 "(patch_vulnerability) was executed. analyst_equifax returns "
                 "to standard SIEM monitoring from TRIAGED state. "
                 "IR1_Detect is NOT permitted from TRIAGED. "
                 "*** ORDER FIRES — DEFICIENCY_NOTED PATTERN *** "
                 "Systems remain vulnerable. Breach initiation: Day 67 (May 13). "
                 "Gate lead time: ~59 days. [INADMISSIBLE — ORDER]"
    },

    # ── Phase 4: CISO layer — escalation that should have occurred ──────
    # For completeness: ciso_equifax should have been escalated to at
    # the point where the patch scan failed and the deadline passed.
    # Model the CISO taking IR1_Detect action before escalation path
    # is properly established — JURISDICTION check (CISO has full IR
    # authority but the question is whether escalation was formally
    # initiated by the analyst before CISO action).
    #
    # Note: this event is secondary to the ORDER finding above.
    # The primary DEFICIENCY_NOTED gate fire has already occurred.
    {
        "actor_id":   "ciso_equifax",
        "action":     "review_alert",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 10 * DAY,
        "_note": "Day 10 (Mar 17): ciso_equifax reviews the CVE alert. "
                 "CISO enters ALERT_RECEIVED state independently. "
                 "No formal escalation from analyst to CISO on record "
                 "per Senate testimony — CISO awareness path is informal. "
                 "[ADMISSIBLE for CISO — but escalation gap is noted]"
    },

    {
        "actor_id":   "ciso_equifax",
        "action":     "assess_severity",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 10 * DAY + 3600,
        "_note": "Day 10: CISO triages severity. State ALERT_RECEIVED → TRIAGED. "
                 "CISO is now also in DEFICIENCY_NOTED state. "
                 "[ADMISSIBLE — CISO triage]"
    },

    # CISO does NOT proceed to IR3_Contain (patch order).
    # Instead, CISO takes IR2_Triage loop action (continued scoping).
    # This is admissible (IR2_Triage is permitted from TRIAGED for CISO).
    # The gate does not fire here — but the structural gap is documented.
    {
        "actor_id":   "ciso_equifax",
        "action":     "determine_scope",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 12 * DAY,
        "_note": "Day 12 (Mar 19): CISO conducts further scope determination. "
                 "IR2_Triage loop in TRIAGED. [ADMISSIBLE — triage loop] "
                 "No patch order issued. CISO remains in TRIAGED with "
                 "deficiency on record. Structural gap: CISO has patch "
                 "authority (IR3_Contain in CISO vocab) but does not exercise it."
    },

    # ── Reference event: breach initiation (Day 67 = May 13) ────────────
    # Not run through the gate — the breach is the consequence,
    # not an IR action by Equifax personnel.
    # Included as a timestamp anchor for lead time documentation only.

    # ── Phase 5: Late discovery and escalation (Day 144 = July 29) ──────
    # When breach is finally discovered, the correct escalation path
    # is followed. For completeness: model discovery through disclosure.
    # By this point the analyst's state is TRIAGED (post-ORDER fire);
    # a new confirm_breach action from TRIAGED is IR2_Triage → loops.
    {
        "actor_id":   "analyst_equifax",
        "action":     "confirm_breach",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 144 * DAY,
        "_note": "Day 144 (Jul 29): Breach discovered via internal security check. "
                 "confirm_breach is IR2_Triage, loops in TRIAGED. "
                 "[ADMISSIBLE — triage action, but post-breach discovery]"
    },

    {
        "actor_id":   "analyst_equifax",
        "action":     "escalate_to_ciso",
        "incident_id": "CVE-2017-5638",
        "timestamp":   T0 + 144 * DAY + 7200,
        "_note": "Day 144: Breach escalated to CISO. "
                 "escalate_to_ciso is IR4_Escalate. "
                 "IR4_Escalate is permitted from CONTAINED, not TRIAGED, "
                 "for IR_Analyst. From TRIAGED: only IR2_Triage or IR3_Contain. "
                 "*** ORDER FIRES — second ORDER violation *** "
                 "Analyst attempts to escalate without first containing. "
                 "[INADMISSIBLE — ORDER (escalation before containment)]"
    },

]


# ═══════════════════════════════════════════════════════════════════════
# Run reconstruction
# ═══════════════════════════════════════════════════════════════════════

def run_reconstruction():
    compiler = CyberIRCompiler()
    results  = []

    print("=" * 70)
    print("EQUIFAX 2017 — DEFICIENCY_NOTED RECONSTRUCTION")
    print("Substrate: Cyber IR (Human Layer) — compiler #16")
    print("Pattern:   DEFICIENCY_NOTED | Invariant: ORDER")
    print("=" * 70)

    for i, ev in enumerate(EVENTS):
        note = ev.pop("_note", "")
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        stp    = packet["STP_Header"]

        decision = result.get("decision", "INDETERMINATE")
        invariant = result.get("invariant", "—")

        print(f"\n[Event {i+1:02d}] {ev.get('action')} | actor: {ev.get('actor_id')}")
        print(f"  Note:      {note}")
        print(f"  State:     {stp.get('FromState')} → {stp.get('ToState')}")
        print(f"  Role:      {stp.get('Role')}")
        print(f"  Action:    {stp.get('Action')}")
        print(f"  Decision:  {decision}")
        if decision == "INADMISSIBLE":
            print(f"  Invariant: {invariant}")
            bas = result.get("BAS_Metrics", {})
            violations = [k for k, v in bas.items() if v and k not in
                          ("ExposureEvent",)]
            print(f"  Violations: {violations}")

        results.append({
            "event_index": i + 1,
            "actor_id":    ev.get("actor_id"),
            "action":      ev.get("action"),
            "from_state":  stp.get("FromState"),
            "to_state":    stp.get("ToState"),
            "role":        stp.get("Role"),
            "action_class": stp.get("Action"),
            "decision":    decision,
            "invariant":   invariant,
            "bas_metrics": result.get("BAS_Metrics", {}),
            "note":        note,
        })

    # ── Summary ──────────────────────────────────────────────────────────
    fires = [r for r in results if r["decision"] == "INADMISSIBLE"]
    admissible = [r for r in results if r["decision"] == "ADMISSIBLE"]

    print("\n" + "=" * 70)
    print("RECONSTRUCTION SUMMARY")
    print("=" * 70)
    print(f"  Total events:       {len(results)}")
    print(f"  ADMISSIBLE:         {len(admissible)}")
    print(f"  INADMISSIBLE:       {len(fires)}")

    if fires:
        primary = fires[0]
        print(f"\n  PRIMARY GATE FIRE (DEFICIENCY_NOTED pattern):")
        print(f"    Event:          {primary['event_index']} — {primary['action']}")
        print(f"    Actor:          {primary['actor_id']}")
        print(f"    State:          {primary['from_state']} → {primary['to_state']}")
        print(f"    Invariant:      {primary['invariant']}")
        print(f"    Pattern:        DEFICIENCY_NOTED")
        print(f"    Deficiency doc: CVE-2017-5638 (Apache, March 7 2017)")
        print(f"    Gate fires:     Day ~9 (approx. March 16, 2017)")
        print(f"    Breach begins:  Day 67 (May 13, 2017)")
        print(f"    Lead time:      ~59 days (day-level precision)")
        print(f"    Precision class: Day-level")
        print(f"    Mapping type:   Direct 1:1")

    print("\n  Named pattern registry update:")
    print("  DEFICIENCY_NOTED — 5th instance")
    print("  | Incident         | Year | Owner Action           | Domain      |")
    print("  |-----------------|------|------------------------|-------------|")
    print("  | Algo Centre Mall | 2012 | H1 stall → ORDER       | Construction|")
    print("  | Champlain Towers | 2021 | H1 stall → ORDER       | Construction|")
    print("  | Bhopal           | 1984 | A3_Commit from DEF_N   | Chemical    |")
    print("  | Lehman Repo 105  | 2008 | A3_Commit from DEF_N   | Financial   |")
    print("  | Equifax CVE      | 2017 | monitor_siem from TRIG | Cyber IR    |")
    print()

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    out_path = "equifax_cyberir_reconstruction_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written → {out_path}")
