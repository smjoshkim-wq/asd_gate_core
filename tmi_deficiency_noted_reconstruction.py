"""
Inverse Incident Reconstruction — Three Mile Island 1979 (DEFICIENCY_NOTED Pattern)
═════════════════════════════════════════════════════════════════════════════════════

Substrate: Nuclear Facility Operations, compiler #8
Compiler:  nuclear_compiler_v0_1.py
Pattern:   DEFICIENCY_NOTED (7th confirmed instance)
Invariant: ORDER (primary)
Mapping type: Direct 1:1

Source authority:
    Kemeny Commission Report, "The President's Commission on the Accident at
    Three Mile Island" (October 1979). Full public record.
    NRC NUREG-0600, "Investigation into the March 28, 1979 Three Mile Island
    Accident by the Office of Inspection and Enforcement" (August 1979).
    Babcock & Wilcox internal communication, November 1977 — operators
    should be warned not to shut off high-pressure injection following a
    loss-of-coolant accident if PORV indicator showed closed; referenced
    in Kemeny Commission Report Appendix XI and NUREG-0600 Section 4.3.
    NRC Event Report — Davis-Besse incident, September 24, 1977:
    similar PORV transient; operators confused PORV status, throttled HPI.
    Referenced in NUREG-0600 as a direct precursor whose lesson was not
    operationalized across B&W plants before TMI.

Reconstruction scope:
    Phase 0: Prior deficiency documentation (~16 months before TMI).
             B&W engineers documented the PORV ambiguity risk in November
             1977. The corrective action — a procedure update instructing
             operators not to throttle HPI based solely on the PORV
             indicator — was not implemented at TMI-2 before March 1979.
    Phase 1: March 28, 1979 accident sequence.
             sro_garcia reaches OPERATING state during normal shift
             operations. The feedwater pump trip initiates the transient.
             PORV indicator shows "commanded closed" (ambiguous —
             the valve is stuck open). sro_garcia throttles ECCS
             (throttle_eccs → N6_ExtremeOverride) from OPERATING state,
             before entering emergency response via N3_ProtectiveMitigation.
             N6 is not permitted from OPERATING for SRO_SM → ORDER fires.

DEFICIENCY_NOTED geometry in this substrate:
    OPERATING is the DEFICIENCY_NOTED state here: the B&W memo documented
    that in OPERATING state, facing a stuck-open PORV with a "closed"
    indicator, operators would likely throttle HPI prematurely. The required
    corrective action was a procedure update that would have instructed
    operators to enter Emergency Operating Procedures (N3 → EMERGENCY_RESPONSE)
    before taking override actions. That procedure update was never issued.

    Gate fires when sro_garcia attempts throttle_eccs (N6) from OPERATING
    before completing N3_ProtectiveMitigation (EOP entry → EMERGENCY_RESPONSE).
    N6 is only permitted from EMERGENCY_RESPONSE in the SRO_SM flow graph.
    N6 from OPERATING fires ORDER.

    The deficiency document is the B&W internal communication (November 1977)
    which explicitly described the failure mode that occurs 16 months later.

Lead times:
    Primary (deficiency document → accident): ~16 months.
        B&W communication: November 1977. TMI accident: March 28, 1979.
        Precision class: Day-level (November 1977 documented in Kemeny
        Commission Appendix XI; exact day within November not specified
        in public record — month-level precision on deficiency document).
    Secondary (gate fire → core uncover begins): approximately 2 hours.
        The ORDER fires when throttle_eccs is executed from OPERATING.
        Per NRC NUREG-0600: HPI was throttled at approximately 06:18.
        Core began uncovering (peak cladding temperature rise) approximately
        2 hours later. Minute-level precision on day of.

Scoping note:
    sro_garcia and ro_jones use role-scoped shift_ids to avoid spurious
    actor_pivot fires between operators legitimately sharing the same shift.
    Phase 0 (deficiency advisory review) uses a separate shift context.

TMI-2 timeline (Eastern time, March 28, 1979 — source: NUREG-0600):
    04:00:37  Feedwater pumps trip; turbine trip; reactor SCRAM (auto, correct)
    04:00:52  PORV opens — correct (pressure relief)
    04:01:28  PORV indicator: "commanded closed" — valve stuck open; indicator wrong
    04:06      Operators observe HPI auto-actuation; begin monitoring
    ~06:18    sro throttles HPI (high-pressure injection) — ORDER fires here
              Operators believe PORV is closed; reactor cooling is adequate
              Neither is true
    ~08:00    Core begins to uncover (coolant level dropping)
    ~11:00    Partial core melt begins
"""

import sys
import json
sys.path.insert(0, ".")

from nuclear_compiler_v0_1 import NuclearCompiler
from domain_compiler_v0_9 import evaluate_gate

MIN  = 60
HOUR = 3600
DAY  = 86400

# Relative to gate fire (throttle_eccs) = T=0
T_BW_MEMO   = -(16 * 30 * DAY)   # ~16 months: B&W memo, November 1977
T_DB_INCIDENT = -(18 * 30 * DAY) # ~18 months: Davis-Besse, September 1977
T_SHIFT_START = -(4 * HOUR)      # ~04:00 shift start
T_SCRAM       = -(4 * HOUR) + 37 # 04:00:37 — feedwater trip / SCRAM
T_GATE_FIRE   = 0                 # ~06:18 — throttle_eccs from OPERATING
T_CORE_UNCOVER = (2 * HOUR)      # ~08:00 — core begins uncovering
T_MELT_BEGINS  = (7 * HOUR)      # ~11:00 — partial melt begins

EVENTS = [

    # ── Phase 0: Deficiency seeding (November 1977) ─────────────────────
    # sro_garcia (acting as representative of TMI-2 SRO staff) reviews the
    # B&W advisory communication. The advisory explicitly warns that operators
    # should not throttle HPI based on PORV indicator alone. No procedure
    # update is issued at TMI-2 following the review. Deficiency unresolved.
    {
        "actor_id": "sro_garcia",
        "action":   "check_parameters",
        "shift_id": "TMI2_BW_advisory_review_1977",
        "timestamp": T_BW_MEMO,
        "_note": "November 1977: sro_garcia reviews B&W internal communication. "
                 "Advisory documents PORV ambiguity risk: if PORV indicator shows "
                 "'closed' but valve is stuck open, operators may throttle HPI. "
                 "Corrective action: issue procedure update. "
                 "N1_Monitor: STANDBY → MONITORING. "
                 "*** DEFICIENCY_NOTED STATE SEEDED (November 1977) *** "
                 "Deficiency document: B&W internal communication, Nov 1977. "
                 "[ADMISSIBLE — SRO advisory review]"
    },
    {
        "actor_id": "sro_garcia",
        "action":   "verify_system_status",
        "shift_id": "TMI2_BW_advisory_review_1977",
        "timestamp": T_BW_MEMO + (3 * DAY),
        "_note": "November 1977 +3 days: sro_garcia reviews PORV procedure. "
                 "No procedure update issued. No operator training conducted. "
                 "N1_Monitor loops in MONITORING. "
                 "Deficiency: operators at TMI-2 will not know to continue HPI "
                 "if PORV indicator shows 'closed.' Corrective action deferred. "
                 "[ADMISSIBLE — SRO monitoring loop; deficiency unresolved]"
    },

    # ── Phase 1: March 28, 1979 — accident shift ─────────────────────────
    # RO establishes normal shift monitoring and operations.
    {
        "actor_id": "ro_jones",
        "action":   "check_parameters",
        "shift_id": "TMI2_shift_C_RO",
        "timestamp": T_SHIFT_START,
        "_note": "Mar 28, ~04:00: ro_jones establishes normal shift monitoring. "
                 "N1_Monitor: STANDBY → MONITORING. "
                 "[ADMISSIBLE — normal shift start]"
    },
    {
        "actor_id": "ro_jones",
        "action":   "adjust_coolant_flow",
        "shift_id": "TMI2_shift_C_RO",
        "timestamp": T_SHIFT_START + (5 * MIN),
        "_note": "Mar 28, ~04:05: ro_jones adjusts coolant flow during normal ops. "
                 "N2_ReactivityControl: MONITORING → OPERATING. "
                 "[ADMISSIBLE — normal operations]"
    },

    # SRO establishes shift authority.
    {
        "actor_id": "sro_garcia",
        "action":   "check_parameters",
        "shift_id": "TMI2_shift_C_SRO",
        "timestamp": T_SHIFT_START,
        "_note": "Mar 28, ~04:00: sro_garcia establishes shift supervisor authority. "
                 "N1_Monitor: STANDBY → MONITORING. "
                 "*** SRO NOW IN OPERATING STATE WITH UNRESOLVED DEFICIENCY *** "
                 "(B&W PORV procedure advisory from Nov 1977 never implemented.) "
                 "[ADMISSIBLE — SRO shift start]"
    },
    {
        "actor_id": "sro_garcia",
        "action":   "adjust_coolant_flow",
        "shift_id": "TMI2_shift_C_SRO",
        "timestamp": T_SHIFT_START + (8 * MIN),
        "_note": "Mar 28, ~04:08: sro_garcia takes reactivity control authority. "
                 "N2_ReactivityControl: MONITORING → OPERATING. "
                 "SRO is now in OPERATING — the DEFICIENCY_NOTED state. "
                 "Required: if PORV ambiguity arises, enter EOP (N3→EMERGENCY_RESPONSE) "
                 "before any N6 override. This procedure does not exist at TMI-2. "
                 "[ADMISSIBLE — SRO operational control]"
    },

    # Transient begins. PORV opens (correct). Indicator shows "closed" (wrong).
    # Operators observe HPI auto-actuation. They believe the system is recovering.
    {
        "actor_id": "ro_jones",
        "action":   "read_indicators",
        "shift_id": "TMI2_shift_C_RO",
        "timestamp": T_SCRAM + (90 * MIN),
        "_note": "Mar 28, ~05:30: ro_jones reads indicators post-transient. "
                 "PORV indicator: 'commanded closed' (incorrect — valve stuck open). "
                 "HPI auto-actuated. Operators believe coolant level is recovering. "
                 "N1_Monitor from OPERATING → MONITORING (state step-back). "
                 "[ADMISSIBLE — indicator check]"
    },
    {
        "actor_id": "ro_jones",
        "action":   "adjust_coolant_flow",
        "shift_id": "TMI2_shift_C_RO",
        "timestamp": T_SCRAM + (95 * MIN),
        "_note": "Mar 28, ~05:35: ro_jones adjusts coolant flow — attempting "
                 "to manage what appears to be a normal transient recovery. "
                 "N2_ReactivityControl: MONITORING → OPERATING. "
                 "[ADMISSIBLE — operator responding to apparent recovery]"
    },

    # ══ PRIMARY FIRE — T = 0 (~06:18 local) ══════════════════════════════
    # sro_garcia throttles ECCS (throttle_eccs → N6_ExtremeOverride)
    # from OPERATING state.
    #
    # The required sequence: N3_ProtectiveMitigation (enter_eop) from
    # OPERATING → EMERGENCY_RESPONSE, THEN N6 from EMERGENCY_RESPONSE.
    # The B&W memo (November 1977) documented that operators would need
    # an explicit procedure instruction to enter EOPs before throttling.
    # That procedure was never issued. sro_garcia has no procedural basis
    # to enter EOPs first — the DEFICIENCY_NOTED gap fires here.
    #
    # N6 from OPERATING is NOT permitted for SRO_SM → ORDER fires.
    # Per NUREG-0600: HPI throttled at ~06:18 while PORV was still open.
    {
        "actor_id": "sro_garcia",
        "action":   "throttle_eccs",
        "shift_id": "TMI2_shift_C_SRO",
        "timestamp": T_GATE_FIRE,
        "_note": "Mar 28, ~06:18: sro_garcia throttles high-pressure injection. "
                 "PORV indicator shows 'closed' — sro_garcia believes coolant "
                 "inventory is sufficient. HPI appears unnecessary. "
                 "throttle_eccs → N6_ExtremeOverride from OPERATING. "
                 "N6 is NOT permitted from OPERATING for SRO_SM. "
                 "Required: enter_eop (N3 → EMERGENCY_RESPONSE) first. "
                 "The B&W procedure update (Nov 1977) would have mandated this. "
                 "It was never issued. "
                 "*** ORDER FIRES — DEFICIENCY_NOTED PATTERN *** "
                 "Gate: T=0 (~06:18). Core uncovers: T+2hr. Melt: T+7hr. "
                 "Lead time to core damage: ~2–7 hours. "
                 "Lead time from deficiency document: ~16 months. "
                 "[INADMISSIBLE — ORDER]"
    },

    # Post-fire: what should have happened.
    # The correct path: enter_eop (N3) from OPERATING → EMERGENCY_RESPONSE,
    # then N6 if override is genuinely warranted. This path is ADMISSIBLE.
    {
        "actor_id": "sro_garcia",
        "action":   "enter_eop",
        "shift_id": "TMI2_shift_C_SRO",
        "timestamp": T_GATE_FIRE + (5 * MIN),
        "_note": "Reference only — HYSTERESIS check: after the ORDER violation, "
                 "enter_eop (N3_ProtectiveMitigation) from OPERATING. "
                 "This is the action that should have preceded throttle_eccs. "
                 "If this had been the sequence, the gate would not have fired. "
                 "Checking whether HYSTERESIS fires on the correct path "
                 "post-violation (expected: HYSTERESIS, new state not previously visited)."
    },
]


def run_reconstruction():
    compiler = NuclearCompiler()
    results  = []

    print("=" * 72)
    print("THREE MILE ISLAND 1979 — DEFICIENCY_NOTED RECONSTRUCTION")
    print("Substrate: Nuclear Facility Operations — compiler #8")
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
        print(f"  Role:     {stp.get('Role'):12s} Action: {stp.get('Action')}")
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
        print(f"    Actor:           {pf['actor_id']}")
        print(f"    State:           {pf['from_state']} → {pf['to_state']}")
        print(f"    Invariant:       ORDER")
        print(f"    Pattern:         DEFICIENCY_NOTED")
        print(f"    Deficiency doc:  B&W internal communication (November 1977)")
        print(f"    Gate fires:      ~06:18 local, March 28, 1979")
        print(f"    Core uncovers:   ~08:00 local (~2 hr lead time from gate)")
        print(f"    Partial melt:    ~11:00 local (~7 hr lead time from gate)")
        print(f"    Lead time (op):  ~2–7 hours (gate fire → core damage onset)")
        print(f"    Lead time (doc): ~16 months (B&W memo → accident)")
        print(f"    Precision class: Minute-level (NUREG-0600 timeline) /")
        print(f"                     Month-level (B&W memo, November 1977)")
        print(f"    Mapping type:    Direct 1:1")

    print("\n  DEFICIENCY_NOTED — 7th instance")
    print("  | Incident         | Year | Deficiency Doc          | Domain       | Doc→Event   |")
    print("  |------------------|------|-------------------------|--------------|-------------|")
    print("  | Algo Centre Mall | 2012 | Inspection report       | Construction | ~months     |")
    print("  | Champlain Towers | 2021 | 2018 engineering report | Construction | ~3 years    |")
    print("  | Bhopal           | 1984 | UCIL engineering findings| Chemical    | ~2 years    |")
    print("  | Lehman Repo 105  | 2008 | Matthew Lee letter      | Financial    | ~3.5 months |")
    print("  | Equifax CVE      | 2017 | CVE-2017-5638           | Cyber IR     | ~67 days    |")
    print("  | Texas City BP    | 2005 | Telos Group Assessment  | Chemical     | ~6 months   |")
    print("  | TMI-2            | 1979 | B&W memo (Nov 1977)     | Nuclear      | ~16 months  |")
    print()

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    out = "tmi_deficiency_noted_reconstruction_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written → {out}")
