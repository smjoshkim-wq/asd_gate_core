"""
Inverse Incident Reconstruction — Fukushima Daiichi 2011 (Nuclear Substrate)
═══════════════════════════════════════════════════════════════════════════════

Source authority:
    NAIIC (National Diet of Japan Fukushima Nuclear Accident Independent
    Investigation Commission) Final Report, July 2012.
    Government of Japan Investigation Committee on the Accident at the
    Fukushima Nuclear Power Stations (ICANPS) Interim and Final Reports,
    Dec 2011 / Jul 2012.
    IAEA Director General Report on the Fukushima Daiichi Accident, 2015.
    Yoshida Testimony (released Aug 2014, "Yoshida Hearings").
    Leveson, Reflections on the Fukushima Daiichi Nuclear Accident, MIT.

Reconstruction scope:
    This script reconstructs the role-attributed action sequence at
    Fukushima Daiichi Unit 1 from approximately 14:46 JST on March 11, 2011
    (Tohoku earthquake initiation) through approximately 20:20 JST on
    March 12 (the seawater injection countermand episode).

    The reconstruction is focused on the TEPCO HQ countermand of seawater
    injection — a structurally clean JURISDICTION violation. The Site
    Superintendent Yoshida had initiated seawater injection (N3-class
    protective mitigation) into Unit 1 reactor pressure vessel at
    approximately 19:04 JST on March 12. TEPCO HQ subsequently ordered
    cessation. Yoshida disobeyed the order and continued injection.

    The structural violation the gate detects is HQ's attempt to issue
    an N6-class extreme override (throttle_eccs) from a non-SRO_SM role.
    HQ_Takekuro (TEPCO Fellow communicating the directive) maps to STA
    by default — N6 is not in STA vocabulary, JURISDICTION fires.

Primary structural claim being tested:
    The substrate-invariance composition claim against an externally-
    precipitated cascade failure. All prior reconstructions (Tenerife,
    Gelsinger, Concordia, Bromiley, Deepwater, Challenger, Therac) had
    internally-precipitated initiating events. Fukushima's initiating
    event (tsunami) is fully external. The gate should still fire on
    the structural commissions committed by human actors during the
    response cascade, independent of the external trigger.

Definition of "point of consequence":
    Unit 1 reactor building hydrogen explosion at March 12, 15:36 JST.
    Unit 3 hydrogen explosion at March 14, 11:01 JST.
    Unit 2 containment damage / Unit 4 explosion March 15, 06:14 JST.

    The seawater countermand episode at 20:00 JST March 12 is between
    the Unit 1 explosion (already occurred) and the Unit 3 explosion
    (~39 hours later). Yoshida's disobedience is widely credited with
    preventing further fuel damage; the structural violation is HQ's
    directive, not Yoshida's response.

External trigger note:
    The Tohoku earthquake (M9.0, 14:46 JST) and tsunami (peak ~15:37 JST
    at Daiichi) are the precipitating events. These are not gate-detectable
    — they are external to all substrates. The gate detects structural
    commissions by human actors AFTER the external trigger. This is the
    Fukushima-specific robustness test: external trigger does not preclude
    detection of structural violations downstream.

Timeline (JST) — sources: NAIIC report Vol. I Ch. 2, ICANPS interim report,
Yoshida hearings:
    14:46    Tohoku M9.0 earthquake. Automatic SCRAM at all operating
             reactors at Daiichi (Units 1, 2, 3). Reactor protection
             system functioned correctly.
    15:37    Tsunami arrival at Daiichi (estimated peak 14–15m).
             Loss of all AC power on Units 1-4 (Station Blackout).
             Battery power continues on some units.
    15:42    Yoshida declares Article 10 (specific event) notification.
    16:36    Yoshida declares Article 15 (nuclear emergency) — equivalent
             to General Emergency declaration. Required by Japanese
             Nuclear Emergency Preparedness Act.
    March 12 ~05:00  PM Kan office begins direct involvement in
             operational decisions.
    ~14:30   Vent of Unit 1 containment finally executed (after >12hr
             delay from Yoshida's first request, due to HQ approval
             chain and governmental concurrence requirements).
    15:36    Unit 1 reactor building hydrogen explosion.
    19:04    Yoshida initiates seawater injection into Unit 1 RPV.
    20:00    TEPCO HQ orders cessation of seawater injection.
    20:20    Yoshida acknowledges receipt of order. Continues injection
             without halting. Reports cessation to HQ to manage
             upstream pressure but does not actually stop the pumps.

For nuclear substrate purposes, the structurally cleanest reconstruction
focuses on 19:04-20:20 JST March 12: Yoshida's admissible EOP entry
and seawater injection, followed by HQ's structurally inadmissible
countermand directive.
"""

import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuclear_compiler_v0_1 import NuclearCompiler, NUCLEAR_ROLE_TABLE
from domain_compiler_v0_9 import evaluate_gate

# Inject HQ actor as a non-SRO_SM identity. Default resolution would map
# unknown identities to STA (most constrained role). Including the actor
# explicitly documents the structural mapping decision.
# NOTE: HQ_Takekuro was Fellow / Executive Officer at TEPCO HQ, not a
# licensed control room operator. He was not credentialed as SRO_SM at
# the Daiichi site. Defaulting to STA reflects this structurally.
# (Not added to ROLE_TABLE — the default STA assignment is the test.)

# ═══════════════════════════════════════════════════════════════════════
# Reconstructed event sequence — Fukushima Daiichi Unit 1
# Timestamps: seconds since March 11, 14:46 JST (earthquake)
# Tsunami:    +3060s  (~15:37 JST March 11)
# Mar 12 19:04: +101880s
# Mar 12 20:00: +105240s
# ═══════════════════════════════════════════════════════════════════════

FUKUSHIMA_UNIT1_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: Pre-event RO normal operations (own shift)
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "ro_jones",
        "action":    "check_parameters",
        "shift_id":  "U1_normal_ops_pre_quake",
        "timestamp": 0.0,
        "_note": "14:46 JST. Routine RO monitoring at start of session. "
                 "Earthquake initiates within seconds. State: STANDBY → "
                 "MONITORING (N1 from STANDBY, admissible).",
    },
    {
        "actor_id":  "ro_jones",
        "action":    "adjust_coolant_flow",
        "shift_id":  "U1_normal_ops_pre_quake",
        "timestamp": 60.0,
        "_note": "~14:47 JST. RO normal reactivity control post-SCRAM. "
                 "N2 from MONITORING → OPERATING. Admissible.",
    },
    {
        "actor_id":  "ro_jones",
        "action":    "verify_system_status",
        "shift_id":  "U1_normal_ops_pre_quake",
        "timestamp": 600.0,
        "_note": "~14:56 JST. RO verifies systems. IC operating, DGs "
                 "online. N1 from OPERATING → MONITORING. Admissible.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: Emergency response activation — NEW shift workflow
    # SRO_SM takes operational direction. Per Japanese Nuclear
    # Emergency Preparedness Act, this constitutes a structural
    # context change — new workflow_id reflects that.
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "sro_chen",
        "action":    "check_parameters",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 3060.0,
        "_note": "15:37 JST. Tsunami inundates site, total AC power loss. "
                 "Site Superintendent (mapped as SRO_SM) assumes "
                 "operational direction under Article 15 emergency. "
                 "New emergency response workflow. STANDBY → MONITORING. "
                 "Admissible. "
                 "[EXTERNAL TRIGGER: the tsunami is not gate-detectable. "
                 "The gate detects structural commissions, not external "
                 "precipitating events.]",
    },
    {
        "actor_id":  "sro_chen",
        "action":    "adjust_coolant_flow",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 3120.0,
        "_note": "~15:38 JST. SRO_SM attempts coolant adjustment with "
                 "remaining battery-powered systems. N2 from MONITORING "
                 "→ OPERATING. Admissible.",
    },
    {
        "actor_id":  "sro_chen",
        "action":    "enter_eop",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 3300.0,
        "_note": "~15:41 JST. SRO_SM enters Emergency Operating Procedure "
                 "given LOCA-like indications. N3 from OPERATING → "
                 "EMERGENCY_RESPONSE. Admissible.",
    },
    {
        "actor_id":  "sro_chen",
        "action":    "initiate_hpi",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 3600.0,
        "_note": "~15:46 JST. SRO_SM initiates available high-pressure "
                 "injection. N3 loop in EMERGENCY_RESPONSE. Admissible.",
    },
    {
        "actor_id":  "sro_chen",
        "action":    "actuate_eccs",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 101880.0,
        "_note": "19:04 JST March 12. Site Superintendent initiates "
                 "seawater injection into Unit 1 RPV via fire pumps "
                 "(structurally equivalent to ECCS actuation under EOP). "
                 "N3 loop in EMERGENCY_RESPONSE. Admissible. This is "
                 "the action HQ subsequently attempts to override.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 3: THE VIOLATION — HQ invades the emergency response
    # workflow. SAME shift_id as Yoshida = actor_pivot → EXIT.
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "hq_takekuro",
        "action":    "throttle_eccs",
        "shift_id":  "U1_emergency_response_post_tsunami",
        "timestamp": 105240.0,
        "_note": "STRUCTURAL VIOLATION. 20:00 JST March 12. TEPCO HQ "
                 "(Executive Officer Takekuro, conveying PM Kan office "
                 "concerns about recriticality) orders cessation of "
                 "seawater injection on Yoshida's emergency response "
                 "workflow. "
                 "Mapped action: throttle_eccs (N6_ExtremeOverride). "
                 "Mapped role: STA (HQ_Takekuro not in NUCLEAR_ROLE_TABLE; "
                 "default STA — corporate HQ Fellow is not a licensed "
                 "SRO_SM at the Daiichi site). "
                 "Same shift_id as Yoshida's emergency response → "
                 "actor_pivot → EXIT fires (HQ identity invades SRO's "
                 "workflow, structurally analogous to Mason 'management "
                 "hat' moment in Challenger). "
                 "JURISDICTION is also present (N6 not in STA vocabulary "
                 "at any state) but EXIT surfaces first per gate "
                 "evaluation order. "
                 "Historical resolution: Yoshida disobeyed the directive "
                 "and continued injection. The gate's fire records the "
                 "structural illegitimacy of HQ's directive, independent "
                 "of whether the site complied.",
    },
]


def run_reconstruction():
    print("\n" + "═"*72)
    print("INVERSE INCIDENT RECONSTRUCTION — FUKUSHIMA DAIICHI 2011 (NUCLEAR)")
    print("Unit 1 — TEPCO HQ Seawater Injection Countermand")
    print("Source: NAIIC Report; ICANPS Reports; IAEA 2015; Yoshida Hearings")
    print("═"*72)
    print()

    compiler = NuclearCompiler()
    results  = []

    for i, ev in enumerate(FUKUSHIMA_UNIT1_EVENTS):
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_note"] = ev.get("_note", "")
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        result["_actor"] = ev["actor_id"]
        results.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"] or "—"
        to  = packet["STP_Header"]["ToState"] or "—"
        role = packet["STP_Header"]["Role"]
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>7.0f}s | {ev['action']:<22} | "
              f"{ev['actor_id']:<14} ({role:>6}) | "
              f"{frm:>20} → {to:<20} | {d}{tag}")

    print()
    print("─"*72)
    print("FINDINGS")
    print("─"*72)

    violation_step = next((r for r in results if r["decision"] == "INADMISSIBLE"), None)
    # Unit 3 explosion: March 14, 11:01 JST. Seconds from March 11 14:46:
    #   3 days - 3h45m  ≈ 245,700s. Use that as the worst-case downstream
    #   consequence event for the seawater countermand window.
    unit3_explosion_ts = 245700.0

    if violation_step:
        vs        = violation_step
        gate_ts   = vs["_ts"]
        lead_time = unit3_explosion_ts - gate_ts

        print(f"\nGate fires at:   Step {vs['_step']} — '{vs['_raw']}'")
        print(f"Invariant:       {vs['invariant']}")
        print(f"Actor (mapped):  {vs['_stp']['Identity']} → {vs['_stp']['Role']}")
        print(f"State at fire:   {vs['_stp']['FromState']}")
        print(f"Timestamp:       +{gate_ts:.0f}s (~20:00 JST March 12)")
        print(f"Unit 3 explosion: +{unit3_explosion_ts:.0f}s (~11:01 JST March 14)")
        print(f"Lead time:       {lead_time/3600:.1f} hours before Unit 3 explosion")
        print()
        print("Structural interpretation:")
        print(f"  The {vs['invariant']} violation identifies that an N6-class")
        print(f"  extreme override (throttle_eccs) was issued by an actor in")
        print(f"  STA role. N6 is structurally excluded from STA at all states.")
        print(f"  TEPCO HQ personnel (Takekuro) were not licensed SRO_SMs at")
        print(f"  the Daiichi site. The compiler's default mapping to STA")
        print(f"  reflects this. The structural illegitimacy of the HQ directive")
        print(f"  is detected regardless of whether the site complied.")
        print()
        print("External trigger robustness finding:")
        print(f"  The precipitating event (Tohoku earthquake + tsunami) is not")
        print(f"  itself detectable by the gate. The gate detects structural")
        print(f"  commissions by human actors. All admissible actions in the")
        print(f"  first 8 steps (Yoshida's response cascade) ran cleanly. The")
        print(f"  inadmissible commission was HQ's directive, ~29 hours after")
        print(f"  the external trigger. External precipitation does not")
        print(f"  preclude downstream structural detection.")
    else:
        print("\n[!] No INADMISSIBLE decision found. Check event sequence mapping.")

    print()
    print("─"*72)
    print("ADMISSIBLE/INADMISSIBLE SUMMARY")
    print("─"*72)
    for r in results:
        status = "INADMISSIBLE" if r["decision"] == "INADMISSIBLE" else "admissible  "
        print(f"  Step {r['_step']:02d}: {status}  {r['_actor']:<14} {r['_raw']}")

    print()
    print("═"*72)
    print("RECONSTRUCTION TYPE: Direct 1:1")
    print("PRECISION CLASS:    Hour-level (Yoshida hearings, NAIIC timestamps)")
    print("EXTERNAL TRIGGER:   Tohoku M9.0 + tsunami (March 11, 14:46/15:37 JST)")
    print("═"*72)

    return results


if __name__ == "__main__":
    results = run_reconstruction()
    summary = []
    for r in results:
        summary.append({
            "step":      r["_step"],
            "timestamp": r["_ts"],
            "actor":     r["_actor"],
            "role":      r["_stp"]["Role"],
            "action":    r["_raw"],
            "decision":  r["decision"],
            "invariant": r.get("invariant"),
            "from_state":r["_stp"]["FromState"],
            "to_state":  r["_stp"]["ToState"],
        })
    output = {
        "incident":  "Fukushima Daiichi 2011 (Nuclear)",
        "substrate": "Nuclear",
        "unit":      "Unit 1",
        "source":    "NAIIC; ICANPS; IAEA 2015; Yoshida Hearings",
        "reconstruction_type": "Direct 1:1",
        "precision_class":     "Hour-level",
        "external_trigger":    "Tohoku M9.0 earthquake + tsunami (Mar 11 14:46/15:37 JST)",
        "results":   summary,
    }
    out_path = "/mnt/user-data/outputs/fukushima_nuclear_reconstruction_results.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nMachine-readable results written to {out_path}")
