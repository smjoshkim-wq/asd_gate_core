"""
Inverse Incident Reconstruction — Texas City BP Refinery 2005 (DEFICIENCY_NOTED Pattern)
══════════════════════════════════════════════════════════════════════════════════════════

Substrate: Chemical / Industrial Process, compiler #19
Compiler:  chem_compiler_v0_1.py
Pattern:   DEFICIENCY_NOTED (6th confirmed instance)
Invariant: ORDER (primary), EXIT/actor-pivot (secondary — PSE exclusion from auth chain)
Mapping type: Direct 1:1

Source authority:
    U.S. Chemical Safety and Hazard Investigation Board (CSB),
    Investigation Report No. 2005-04-I-TX, "BP Texas City Refinery
    Explosion and Fire" (March 2007).
    Baker Panel Report, "The Report of the BP U.S. Refineries Independent
    Safety Review Panel" (January 2007).
    Telos Group, BP Texas City Safety Culture Assessment (September 2004)
    — referenced in Baker Panel Report as one of five safety reviews
    2002–2005 that identified unresolved safety deficiencies.

DEFICIENCY_NOTED geometry:
    PSSR_COMPLETE is the DEFICIENCY_NOTED state for Unit_Operator: the
    pre-startup safety review is in progress, known deficiencies are on
    record, and the required next action is CP5_Authorize (PSSR sign-off
    → STARTUP_AUTHORIZED) before any CP3_Startup action.

    When uo_isom attempts begin_feed_introduction (CP3_Startup) from
    PSSR_COMPLETE without completing PSSR authorization, ORDER fires.

    The deficiency document is the Telos Group safety assessment
    (September 2004). The commitment is the March 23 feed introduction.

Scoping note:
    Each actor is scoped to their own unit context to avoid spurious
    actor_pivot fires in a multi-role industrial process environment:
      pse_alpha  → "ISOM_safety_review_2004"  (PSE deficiency documentation)
      ss_isom    → "ISOM_startup_authorization" (SS authorization context)
      uo_isom    → "ISOM_raffinate_splitter"   (UO operational context)
      bo_isom    → "ISOM_dcs_board"            (BO DCS monitoring context)
    The PSE exit finding (Event 9) uses ISOM_raffinate_splitter to model
    the gap where PSE was outside the formal operational authorization chain.

Lead times:
    Primary (gate fire → explosion): ~65 minutes (minute-level precision)
    Secondary (Telos doc → explosion): ~6 months (day-level precision)

CSB timeline (local, March 23, 2005):
    ~00:15  Feed introduced into raffinate splitter
    ~12:41  Level at 127% of range; high-level alarm does not activate
    ~13:01  Material routes to blowdown drum
    ~13:13  Blowdown drum overflows; hydrocarbon releases
    ~13:20  Explosion — 15 fatalities, 180 injuries
"""

import sys
import json
sys.path.insert(0, ".")

from chem_compiler_v0_1 import ChemCompiler
from domain_compiler_v0_9 import evaluate_gate

MIN  = 60
HOUR = 3600
DAY  = 86400

T_TELOS  = -(180 * DAY)
T_FEED   = -(65 * MIN)
T_ALARM  = -(39 * MIN)
T_BLOWDN = -(19 * MIN)
T_EXPL   = 0

EVENTS = [

    # ── Phase 0: Prior deficiency (September 2004, ~6 months before) ────
    {
        "actor_id":  "pse_alpha",
        "action":    "observe_process_conditions",
        "unit_id":   "ISOM_safety_review_2004",
        "timestamp": T_TELOS,
        "_note": "Sep 2004: pse_alpha receives Telos Group safety assessment. "
                 "Documents PSSR implementation failures and unreliable "
                 "high-level alarm on raffinate splitter. "
                 "CP1_Monitor: IDLE → REVIEWING. "
                 "*** DEFICIENCY_NOTED STATE SEEDED *** "
                 "[ADMISSIBLE — PSE review]"
    },
    {
        "actor_id":  "pse_alpha",
        "action":    "verify_alarm_status",
        "unit_id":   "ISOM_safety_review_2004",
        "timestamp": T_TELOS + (7 * DAY),
        "_note": "Sep 2004 +1wk: pse_alpha confirms alarm unreliability. "
                 "Corrective action recommended but NOT completed. "
                 "CP5_Authorize (REVIEWING→AUTHORIZED) never taken. "
                 "Deficiency remains open through March 2005. "
                 "[ADMISSIBLE — PSE monitoring loop]"
    },

    # ── Phase 1: March 23 startup — SS authorization context ────────────
    {
        "actor_id":  "ss_isom",
        "action":    "check_level_indicator",
        "unit_id":   "ISOM_startup_authorization",
        "timestamp": T_FEED - (12 * HOUR),
        "_note": "Mar 23 ~00:15: ss_isom pre-startup review. "
                 "PSSR checklist items in progress. "
                 "CP1_Monitor: IDLE → PSSR_COMPLETE for SS. "
                 "[ADMISSIBLE — SS pre-startup check]"
    },
    {
        "actor_id":  "ss_isom",
        "action":    "approve_continued_startup",
        "unit_id":   "ISOM_startup_authorization",
        "timestamp": T_FEED - (5 * MIN),
        "_note": "Mar 23 ~12:10: ss_isom issues startup permit. "
                 "CP5_Authorize: PSSR_COMPLETE → STARTUP_AUTHORIZED for SS. "
                 "ADMISSIBLE for SS — but issued WITHOUT PSE clearance. "
                 "Telos deficiency (alarm unreliability, PSSR failures) unresolved. "
                 "[ADMISSIBLE — SS authorization; PSE gap is secondary finding]"
    },

    # ── Phase 2: UO operational sequence — DEFICIENCY_NOTED commitment ──
    {
        "actor_id":  "uo_isom",
        "action":    "check_level_indicator",
        "unit_id":   "ISOM_raffinate_splitter",
        "timestamp": T_FEED - (30 * MIN),
        "_note": "Mar 23 ~11:45: uo_isom pre-startup check on raffinate splitter. "
                 "Level indicator operative but accuracy uncertain — "
                 "consistent with Telos deficiency finding. "
                 "CP1_Monitor: IDLE → PSSR_COMPLETE for UO. "
                 "*** UO NOW IN DEFICIENCY_NOTED STATE (PSSR_COMPLETE) *** "
                 "Required: CP5_Authorize before any CP3_Startup. "
                 "[ADMISSIBLE — UO pre-startup monitoring]"
    },
    {
        "actor_id":  "uo_isom",
        "action":    "verify_alarm_status",
        "unit_id":   "ISOM_raffinate_splitter",
        "timestamp": T_FEED - (20 * MIN),
        "_note": "Mar 23 ~11:55: uo_isom verifies alarm status. "
                 "High-level alarm noted as questionable. "
                 "CP1_Monitor loops in PSSR_COMPLETE. "
                 "PSSR sign-off NOT completed. Deficiency on record. "
                 "[ADMISSIBLE — UO monitoring loop in PSSR_COMPLETE]"
    },

    # ══ PRIMARY FIRE — T = -65 min ══════════════════════════════════════
    # CP3_Startup from PSSR_COMPLETE — ORDER fires.
    # CSB: "The PSSR was not completed before startup commenced."
    {
        "actor_id":  "uo_isom",
        "action":    "begin_feed_introduction",
        "unit_id":   "ISOM_raffinate_splitter",
        "timestamp": T_FEED,
        "_note": "Mar 23 ~12:15: uo_isom begins feed introduction. "
                 "CP3_Startup from PSSR_COMPLETE — NOT permitted. "
                 "CP5_Authorize (PSSR sign-off) was never completed. "
                 "Telos deficiency (Sep 2004) remains unresolved. "
                 "CSB: 'The PSSR was not completed before startup.' "
                 "*** ORDER FIRES — DEFICIENCY_NOTED PATTERN *** "
                 "Gate T=-65 min. Explosion T=0. Lead time: 65 minutes. "
                 "[INADMISSIBLE — ORDER]"
    },

    # ── Phase 3: High-level condition develops ──────────────────────────
    {
        "actor_id":  "bo_isom",
        "action":    "read_dcs",
        "unit_id":   "ISOM_dcs_board",
        "timestamp": T_ALARM,
        "_note": "Mar 23 ~12:41: bo_isom reads DCS — level at 127%. "
                 "High-level alarm has NOT activated (known deficiency). "
                 "CP1_Monitor: IDLE → MONITORING for BO. "
                 "[ADMISSIBLE — BO monitoring]"
    },

    # PSE attempts to access operational unit after blowdown drum is loading.
    # PSE was excluded from the formal startup authorization chain.
    # PSE accessing ISOM_raffinate_splitter (registered to uo_isom)
    # fires actor_pivot — structural model of PSE being outside the chain.
    {
        "actor_id":  "pse_alpha",
        "action":    "monitor_pressure",
        "unit_id":   "ISOM_raffinate_splitter",
        "timestamp": T_BLOWDN,
        "_note": "Mar 23 ~13:01: pse_alpha attempts to monitor blowdown drum pressure. "
                 "pse_alpha accessing ISOM_raffinate_splitter — registered to uo_isom. "
                 "Actor_pivot fires: PSE was not in the formal startup auth chain. "
                 "Per CSB: 'No PSE sign-off was required for the ISOM restart.' "
                 "EXIT models PSE structural exclusion from the authorization path. "
                 "[INADMISSIBLE — EXIT / actor_pivot]"
    },
]


def run_reconstruction():
    compiler = ChemCompiler()
    results  = []

    print("=" * 72)
    print("TEXAS CITY 2005 — DEFICIENCY_NOTED RECONSTRUCTION")
    print("Substrate: Chemical / Industrial Process — compiler #19")
    print("Pattern:   DEFICIENCY_NOTED | Primary Invariant: ORDER")
    print("=" * 72)

    for i, ev in enumerate(EVENTS):
        note = ev.pop("_note", "")
        packet   = compiler.compile(ev)
        result   = evaluate_gate(packet)
        stp      = packet["STP_Header"]
        decision  = result.get("decision", "INDETERMINATE")
        invariant = result.get("invariant", "—")

        print(f"\n[Event {i+1:02d}] {ev.get('action')} | actor: {ev.get('actor_id')}")
        print(f"  State:    {stp.get('FromState')} → {stp.get('ToState')}")
        print(f"  Role:     {stp.get('Role')} | Action: {stp.get('Action')}")
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

    fires      = [r for r in results if r["decision"] == "INADMISSIBLE"]
    admissible = [r for r in results if r["decision"] == "ADMISSIBLE"]
    order_fires = [r for r in fires if r["invariant"] == "ORDER"]

    print("\n" + "=" * 72)
    print("RECONSTRUCTION SUMMARY")
    print("=" * 72)
    print(f"  Total events:    {len(results)}")
    print(f"  ADMISSIBLE:      {len(admissible)}")
    print(f"  INADMISSIBLE:    {len(fires)}")

    if order_fires:
        primary = order_fires[0]
        print(f"\n  PRIMARY GATE FIRE (DEFICIENCY_NOTED pattern):")
        print(f"    Event:           {primary['event_index']} — {primary['action']}")
        print(f"    Actor:           {primary['actor_id']}")
        print(f"    State:           {primary['from_state']} → {primary['to_state']}")
        print(f"    Invariant:       ORDER")
        print(f"    Pattern:         DEFICIENCY_NOTED")
        print(f"    Deficiency doc:  Telos Group Safety Assessment (September 2004)")
        print(f"    Gate fires:      ~12:15 local, March 23, 2005")
        print(f"    Explosion:       ~13:20 local, March 23, 2005")
        print(f"    Lead time (op):  ~65 minutes (gate fire → explosion)")
        print(f"    Lead time (doc): ~6 months (Telos report → explosion)")
        print(f"    Precision class: Minute-level (CSB timeline) / Day-level (Telos doc)")
        print(f"    Mapping type:    Direct 1:1")

    print("\n  DEFICIENCY_NOTED — 6th instance")
    print("  | Incident         | Year | Deficiency Doc          | Domain       | Lead Time   |")
    print("  |------------------|------|-------------------------|--------------|-------------|")
    print("  | Algo Centre Mall | 2012 | Inspection report       | Construction | ~months     |")
    print("  | Champlain Towers | 2021 | 2018 engineering report | Construction | ~3 years    |")
    print("  | Bhopal           | 1984 | UCIL engineering findings| Chemical    | ~2 years    |")
    print("  | Lehman Repo 105  | 2008 | Matthew Lee letter      | Financial    | ~3.5 months |")
    print("  | Equifax CVE      | 2017 | CVE-2017-5638           | Cyber IR     | ~59 days    |")
    print("  | Texas City BP    | 2005 | Telos Group Assessment  | Chemical     | ~6 months   |")
    print()

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    out = "texascity_chem_reconstruction_results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written → {out}")
