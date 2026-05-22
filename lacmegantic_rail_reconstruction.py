"""
Inverse Incident Reconstruction — Lac-Mégantic 2013 (DEFICIENCY_NOTED Pattern)
═══════════════════════════════════════════════════════════════════════════════

Substrate: Rail Operations, compiler #17
Compiler:  rail_compiler_v0_1.py
Pattern:   DEFICIENCY_NOTED (9th confirmed instance)
Invariant: ORDER (primary), EXIT / actor_pivot (secondary — RTC unattended auth)
Mapping type: Direct 1:1

Source authority:
    Transportation Safety Board of Canada, Railway Investigation Report
    R13D0054, "Main-Track Runaway and Derailment, Montreal, Maine and
    Atlantic Railway, Train MMA-002" (August 19, 2014). Full public record.
    Transport Canada Railway Safety Directorate, Safety Management System
    Audit of Montreal, Maine and Atlantic Railway (MMA), 2012 — referenced
    in TSB R13D0054 Section 3.4 (Regulatory Oversight). TC audit documented
    deficiencies in MMA's SPC (Single-Person Crew) operations and securement
    procedures. MMA required to file corrective action plan.
    Canadian Rail Operating Rules (CROR), Rule 112 (Securing Equipment):
    handbrake requirements for unattended trains on grades.

Reconstruction scope:
    Phase 0: TC 2012 safety management system audit — deficiency seeded.
             TC found MMA's SPC securement procedures inadequate and required
             corrective action. MMA filed a plan; implementation was
             incomplete before July 2013.
    Phase 1: July 5, 2013, ~22:15-22:50 local — engineer_holt parks
             consist MMA-002 at Nantes, Quebec on a downgrade main line.
             Holt applied 7 handbrakes. TSB determined 11 were required
             to hold the consist on the 1.2% grade.
             Under TC 2012 audit standard, 7 of 11 handbrakes does NOT
             constitute completed securement (R3_Secure). The state machine
             does not advance to SECURED. engineer_holt remains in OPERATING.
             crew_change (R5_Transfer) from OPERATING fires ORDER.
    Phase 2: ~00:56 July 6 — fire department responds to locomotive engine
             fire. Fire dept shuts down locomotive and automatic brake
             system, removing the air brakes that were supplementing the
             inadequate handbrake securement. Consist begins rolling at
             approximately 01:15. Derailment in Lac-Mégantic at 01:15.

DEFICIENCY_NOTED geometry:
    OPERATING is the DEFICIENCY_NOTED state: train is in motion-capable
    configuration, TC 2012 audit deficiency (inadequate SPC securement
    procedures) is on record and unresolved. Required next action before
    any authority transfer is R3_Secure (complete securement to TC standard).
    7 of 11 required handbrakes does not meet the R3_Secure standard per
    TC audit findings. engineer_holt's crew_change (R5_Transfer) from
    OPERATING fires ORDER: authority transfer executed without completing
    required securement gate.

Modeling note on partial securement:
    apply_handbrake and verify_handbrake_count both map to R3_Secure in
    the action class map. If used, they would advance the state to SECURED
    regardless of handbrake count. To accurately model Lac-Mégantic:
    The partial handbrake application is modeled as R1_Monitor
    (check_brake_pressure) — consistent with an inspection that found
    inadequate securement rather than a completed securement action.
    The R3_Secure gate is not crossed because the TC standard was not met.
    This keeps engineer_holt in OPERATING, and crew_change fires ORDER.

Lead times:
    Primary (deficiency document → derailment):
        TC audit: 2012 (year-level precision).
        Derailment: July 6, 2013, ~01:15 local.
        Lead time: ~6-12 months (day-level on derailment / year-level on audit).
    Secondary (gate fire → derailment):
        Crew change: approximately July 5, ~22:50 local.
        Derailment: July 6, ~01:15 local.
        Lead time: approximately 2 hours 25 minutes. Minute-level precision
        (TSB R13D0054 timeline, Section 1.1).

Timeline (local time, July 5-6, 2013 — source: TSB R13D0054):
    ~22:50  engineer_holt completes crew change; MMA-002 left unattended
    ~23:40  Locomotive engine fire reported by passerby
    ~23:50  Nantes fire brigade responds; shuts down locomotive
    ~00:56  Air brake system loses pressure (engine shutdown consequence)
    ~01:10  Consist begins rolling (handbrakes insufficient to hold grade)
    ~01:15  Derailment and explosion, Lac-Mégantic town centre
    47 fatalities
"""

import sys
import json
sys.path.insert(0, ".")

from rail_compiler_v0_1 import RailCompiler
from domain_compiler_v0_9 import evaluate_gate

MIN  = 60
HOUR = 3600
DAY  = 86400

# Relative to crew change (T=0 = ~22:50 July 5)
T_AUDIT      = -(365 * DAY)     # TC 2012 audit — approximately 1 year prior
T_RUN_START  = -(4 * HOUR)      # MMA-002 begins run ~18:50
T_PARK_ARRIVE = -(35 * MIN)     # Arrive Nantes ~22:15
T_CREW_CHANGE = 0               # Crew change ~22:50 — gate fires here
T_FIRE        = (50 * MIN)      # Engine fire ~23:40
T_FD_ARRIVAL  = (60 * MIN)      # Fire dept ~23:50
T_ROLLING     = (140 * MIN)     # Consist begins rolling ~01:10
T_DERAILMENT  = (145 * MIN)     # Derailment ~01:15

EVENTS = [

    # ── Phase 0: TC 2012 audit — deficiency seeded ───────────────────────
    # rtc_mma receives TC safety management system audit findings.
    # TC documented: MMA's SPC securement procedures are inadequate.
    # Specifically: handbrake count requirements for unattended trains
    # on grades are not specified in MMA's operating rules.
    # Corrective action required; plan filed by MMA but not fully
    # implemented before July 2013.
    {
        "actor_id":   "rtc_mma",
        "action":     "read_track_order",
        "consist_id": "MMA_audit_review_2012",
        "timestamp":  T_AUDIT,
        "_note": "2012: rtc_mma reviews TC safety management system audit findings. "
                 "TC documents: MMA SPC securement procedures inadequate; "
                 "handbrake requirements for unattended trains on grades not "
                 "specified in MMA operating rules. Corrective action required. "
                 "R1_Monitor: IDLE → MONITORING. "
                 "*** DEFICIENCY_NOTED STATE SEEDED (2012) *** "
                 "Deficiency document: TC SMP Audit, 2012 (TSB R13D0054 §3.4). "
                 "[ADMISSIBLE — RTC monitoring]"
    },
    {
        "actor_id":   "rtc_mma",
        "action":     "verify_clearance",
        "consist_id": "MMA_audit_review_2012",
        "timestamp":  T_AUDIT + (30 * DAY),
        "_note": "2012 +1 month: rtc_mma reviews MMA corrective action plan. "
                 "Plan filed with TC. Handbrake count procedures not yet updated "
                 "in MMA operating rules. Deficiency remains open. "
                 "R1_Monitor loops in MONITORING. "
                 "[ADMISSIBLE — RTC monitoring loop; deficiency unresolved]"
    },

    # ── Phase 1: July 5, 2013 — MMA-002 run to Nantes ───────────────────
    # engineer_holt begins normal MMA-002 run.
    {
        "actor_id":   "engineer_holt",
        "action":     "check_signals",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_RUN_START,
        "_note": "July 5, ~18:50: engineer_holt checks signals for MMA-002 departure. "
                 "R1_Monitor: IDLE → PRE_DEPARTURE. "
                 "[ADMISSIBLE — pre-departure checks]"
    },
    {
        "actor_id":   "engineer_holt",
        "action":     "request_track_authority",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_RUN_START + (10 * MIN),
        "_note": "July 5, ~19:00: engineer_holt requests track authority for MMA-002. "
                 "R4_Authorize: PRE_DEPARTURE → AUTHORIZED. "
                 "[ADMISSIBLE — track authority obtained]"
    },
    {
        "actor_id":   "engineer_holt",
        "action":     "advance_throttle",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_RUN_START + (15 * MIN),
        "_note": "July 5, ~19:05: engineer_holt advances throttle; MMA-002 underway. "
                 "R2_Operate: AUTHORIZED → OPERATING. "
                 "[ADMISSIBLE — train operating]"
    },

    # Arrive Nantes. engineer_holt intends to park and leave train unattended.
    # Performs brake pressure check (R1_Monitor — not R3_Secure).
    # The TC audit standard requires 11 handbrakes for this grade and consist.
    # Holt applies 7. Per TC 2012 audit findings, this does NOT constitute
    # completed R3_Secure — the securement standard was not met.
    # Modeled as R1_Monitor (check_brake_pressure) because the action
    # taken does not meet the R3_Secure threshold per TC standard.
    # engineer_holt remains in OPERATING state.
    {
        "actor_id":   "engineer_holt",
        "action":     "check_brake_pressure",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_PARK_ARRIVE,
        "_note": "July 5, ~22:15: engineer_holt arrives Nantes; checks brake pressure. "
                 "Applies 7 handbrakes on consist (TSB finding: 11 required for grade). "
                 "MODELED AS R1_Monitor: the partial handbrake application does NOT "
                 "meet the R3_Secure standard per TC 2012 audit findings. "
                 "State does NOT advance to SECURED — engineer_holt remains in OPERATING. "
                 "*** DEFICIENCY_NOTED STATE ACTIVE: OPERATING with TC audit deficiency *** "
                 "Required next action: complete R3_Secure (11 handbrakes per TC standard) "
                 "before any authority transfer. "
                 "R1_Monitor: OPERATING → OPERATING (loop). "
                 "[ADMISSIBLE — monitor action; securement standard not met]"
    },

    # ══ PRIMARY FIRE — crew_change from OPERATING ════════════════════════
    # engineer_holt executes crew_change (R5_Transfer) from OPERATING.
    # R5_Transfer is NOT permitted from OPERATING in the LE flow graph.
    # Required: OPERATING → R3_Secure → SECURED → R5_Transfer (IDLE).
    # The TC 2012 audit deficiency (inadequate securement procedures) is
    # the structural precondition: because the securement standard was
    # not met, R3_Secure was never completed, SECURED was never reached,
    # and R5_Transfer from OPERATING fires ORDER.
    # Per TSB R13D0054: MMA-002 left unattended on 1.2% downgrade mainline
    # at approximately 22:50, July 5, 2013.
    # Gate fires here. Derailment: ~01:15, July 6. Lead time: ~2h25m.
    {
        "actor_id":   "engineer_holt",
        "action":     "crew_change",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_CREW_CHANGE,
        "_note": "July 5, ~22:50: engineer_holt executes crew change; leaves MMA-002 "
                 "unattended on Nantes siding (1.2% downgrade mainline). "
                 "crew_change → R5_Transfer from OPERATING. "
                 "R5_Transfer NOT permitted from OPERATING. "
                 "Required: R3_Secure → SECURED first (11 handbrakes per TC standard). "
                 "TC 2012 audit deficiency (inadequate SPC securement procedures) "
                 "is on record and unresolved. "
                 "*** ORDER FIRES — DEFICIENCY_NOTED PATTERN *** "
                 "Gate: T=0 (~22:50 July 5). Derailment: T+~145min (~01:15 July 6). "
                 "Lead time: ~2h25min (gate → derailment). "
                 "[INADMISSIBLE — ORDER]"
    },

    # ── Phase 2: RTC authorization — secondary finding ───────────────────
    # rtc_mma authorizes unattended train status (R4_Authorize).
    # From DISPATCHING, R4_Authorize loops — ADMISSIBLE for RTC.
    # But rtc_mma is accessing MMA_consist_002 which is registered to
    # engineer_holt — actor_pivot fires.
    # Models: RTC granted unattended authority without being the primary
    # actor who established the consist session. Structural gap in the
    # authorization handoff between engineer and dispatch.
    {
        "actor_id":   "rtc_mma",
        "action":     "check_signals",
        "consist_id": "MMA_consist_002",
        "timestamp":  T_CREW_CHANGE + (5 * MIN),
        "_note": "July 5, ~22:55: rtc_mma monitors MMA-002 status after crew change. "
                 "rtc_mma accessing MMA_consist_002 (registered to engineer_holt). "
                 "Actor_pivot fires: formal authority handoff from engineer to RTC "
                 "was not executed through the consist session registry. "
                 "Models: RTC monitoring unattended train without formal handoff. "
                 "TSB finding: MMA's SPC protocol did not require formal handoff "
                 "verification between departing engineer and RTC. "
                 "[INADMISSIBLE — EXIT / actor_pivot]"
    },

]


def run_reconstruction():
    compiler = RailCompiler()
    results  = []

    print("=" * 72)
    print("LAC-MÉGANTIC 2013 — DEFICIENCY_NOTED RECONSTRUCTION")
    print("Substrate: Rail Operations — compiler #17")
    print("Pattern:   DEFICIENCY_NOTED | Primary Invariant: ORDER")
    print("=" * 72)

    for i, ev in enumerate(EVENTS):
        note = ev.pop("_note", "")
        packet   = compiler.compile(ev)
        result   = evaluate_gate(packet)
        stp      = packet["STP_Header"]
        decision  = result.get("decision", "INDETERMINATE")
        invariant = result.get("invariant", "—")

        print(f"\n[Event {i+1:02d}] {ev.get('action'):35s} actor: {ev.get('actor_id')}")
        print(f"  State:    {stp.get('FromState')} → {stp.get('ToState')}")
        print(f"  Role:     {stp.get('Role'):25s} Action: {stp.get('Action')}")
        print(f"  Decision: {decision}", end="")
        if decision == "INADMISSIBLE":
            print(f"  *** {invariant} ***")
        else:
            print()

        results.append({
            "event_index":  i + 1,
            "actor_id":     ev.get("actor_id"),
            "action":       ev.get("action"),
            "from_state":   stp.get("FromState"),
            "to_state":     stp.get("ToState"),
            "role":         stp.get("Role"),
            "action_class": stp.get("Action"),
            "decision":     decision,
            "invariant":    invariant,
            "bas_metrics":  result.get("BAS_Metrics", {}),
            "note":         note,
        })

    fires       = [r for r in results if r["decision"] == "INADMISSIBLE"]
    admissible  = [r for r in results if r["decision"] == "ADMISSIBLE"]
    order_fires = [r for r in fires if r["invariant"] == "ORDER"]

    print("\n" + "=" * 72)
    print("RECONSTRUCTION SUMMARY")
    print("=" * 72)
    print(f"  Total events:    {len(results)}")
    print(f"  ADMISSIBLE:      {len(admissible)}")
    print(f"  INADMISSIBLE:    {len(fires)}")

    if order_fires:
        pf = order_fires[0]
        print(f"\n  PRIMARY GATE FIRE (DEFICIENCY_NOTED pattern):")
        print(f"    Event:           {pf['event_index']} — {pf['action']}")
        print(f"    Actor:           {pf['actor_id']} ({pf['role']})")
        print(f"    State:           {pf['from_state']} → {pf['to_state']}")
        print(f"    Invariant:       ORDER")
        print(f"    Pattern:         DEFICIENCY_NOTED")
        print(f"    Deficiency doc:  TC SMP Audit 2012 (TSB R13D0054 §3.4)")
        print(f"    Gate fires:      July 5, ~22:50 local (crew change)")
        print(f"    Derailment:      July 6, ~01:15 local")
        print(f"    Lead time (op):  ~2h25min (gate → derailment)")
        print(f"    Lead time (doc): ~6-12 months (TC audit 2012 → derailment)")
        print(f"    Precision class: Minute-level (TSB timeline) / Year-level (audit)")
        print(f"    Mapping type:    Direct 1:1")

    print("\n  DEFICIENCY_NOTED — 9th instance (FINAL for this session)")
    print("  | Incident         | Year | Deficiency Doc    | Domain   | Inv.  | Doc→Event  |")
    print("  |------------------|------|-------------------|----------|-------|------------|")
    print("  | Algo Centre Mall | 2012 | Inspection report | Constr.  | ORDER | ~months    |")
    print("  | Champlain Towers | 2021 | Eng. report 2018  | Constr.  | ORDER | ~3 years   |")
    print("  | Bhopal           | 1984 | UCIL findings     | Chemical | ORDER | ~2 years   |")
    print("  | Lehman Repo 105  | 2008 | M. Lee letter     | Financ.  | ORDER | ~3.5 mo    |")
    print("  | Equifax CVE      | 2017 | CVE-2017-5638     | Cyber IR | ORDER | ~67 days   |")
    print("  | Texas City BP    | 2005 | Telos Assessment  | Chemical | ORDER | ~6 months  |")
    print("  | TMI-2            | 1979 | B&W memo Nov 77   | Nuclear  | ORDER | ~16 months |")
    print("  | Vioxx APPROVe    | 2004 | VIGOR results     | Pharma   | JURIS | ~4 years   |")
    print("  | Lac-Mégantic     | 2013 | TC SMP Audit 2012 | Rail     | ORDER | ~6-12 mo   |")
    print()
    print("  Domain coverage: Construction×2, Chemical×2, Financial, Cyber IR,")
    print("  Nuclear, Pharma, Rail = 7 domains. 8×ORDER, 1×JURISDICTION.")

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    out = "lacmegantic_rail_reconstruction_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written → {out}")
