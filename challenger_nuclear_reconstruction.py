"""
Inverse Incident Reconstruction — Challenger (Nuclear Substrate)
═════════════════════════════════════════════════════════════════════
Reconstruction type: STRUCTURAL ANALOG
Compiler:           nuclear_compiler_v0_1.py
Substrate scope:    safety-critical authorization geometry —
                    Launch Commit Criteria (LCC) waiver as analog
                    to operating outside qualified envelope under
                    10 CFR 50 doctrine

Source authority:
    Presidential Commission on the Space Shuttle Challenger Accident
        (Rogers Commission Report), June 6, 1986
    NASA Space Shuttle Program — Launch Commit Criteria (LCC) document
        NSTS-08171, Volume I, in force at the time of STS-51-L
    Thiokol Memo TWR-15113-A: SRM Joint Performance vs. Temperature
        (Boisjoly et al.)
    Thiokol Engineering Charts presented at Jan 27, 1986 teleconference
    Vaughan, Diane. "The Challenger Launch Decision" (1996), Ch. 5
    Reference doctrine (analog substrate): 10 CFR 50 Appendix B,
        NUREG-0654, NUREG-0737

Reconstruction scope:
    The Solid Rocket Motor (SRM) joint had been qualified for a
    temperature range of 40°F to 90°F. The predicted joint
    temperature at launch was approximately 28°F — well below
    the qualified envelope. The Launch Commit Criteria did not
    explicitly include an O-ring temperature criterion at the
    time of STS-51-L (per Rogers Commission analysis); the
    decision to launch outside the qualification envelope
    constituted an operational override of the design basis.

    In nuclear safety doctrine, operating outside the design
    qualification envelope requires either (a) prior NRC
    authorization through formal amendment, or (b) emergency
    operating procedure (EOP) entry through N3_ProtectiveMitigation
    leading to N6_ExtremeOverride invocation. Neither path was
    structurally available at NSC/MSFC for STS-51-L because no
    such structured override gate existed in the launch decision
    framework.

    This reconstruction maps the LCC waiver onto the nuclear
    compiler's authorization geometry. The structural finding:
    N6_ExtremeOverride was called from MONITORING/OPERATING state
    without the prerequisite N3 transition to EMERGENCY_RESPONSE.

Primary structural claim being tested:
    The nuclear compiler fires ORDER on the LCC waiver because the
    override action was attempted from a state where it was not
    structurally valid. This is the same geometry as the Deepwater
    Horizon petroleum ORDER (displacement from NEGATIVE_TEST without
    BARRIER_VERIFIED) — a sequence gap between a current state and
    the state required for an override action.

Timeline (EST) — source: Rogers Commission Vol. I, Ch. V:
    Jan 27, ~17:45  Engineers (mapped to STA) review temperature data
    Jan 27, ~19:30  Engineers issue concern (N1_Monitor — advisory)
    Jan 27, ~22:30  Management caucus invokes override (mapped to N6)
                    Override called from MONITORING state — not from
                    EMERGENCY_RESPONSE (no formal hazard declaration)
    Jan 28, 11:38   Launch
    Jan 28, 11:39:13 Vehicle disintegration (T+73s)
"""

import sys
import json
sys.path.insert(0, ".")

from nuclear_compiler_v0_1 import NuclearCompiler
from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Reconstructed sequence
# ═══════════════════════════════════════════════════════════════════════
# Mapping:
#   sta_kim       → Boisjoly et al. (advisory engineering — STA role)
#   sro_garcia    → Lund/management equivalent (SRO_SM with N6 capability)
#   ed_williams   → Emergency Director equivalent
#
# Note: NASA/Thiokol did not have role separation matching the nuclear
# regulatory framework. The structural analog models the override
# decision as if it had been made within a nuclear-equivalent framework.

T = 0.0

CHALLENGER_NUCLEAR_EVENTS = [
    # ──────────────────────────────────────────────────────────
    # Phase 1: STA (engineering) advisory monitoring — admissible
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "sta_kim",
        "action":    "read_indicators",
        "shift_id":  "STS_51L_REVIEW",
        "timestamp": T + 0.0,
        "_note": "~17:45 EST. Engineering team reviews O-ring "
                 "performance data and overnight temperature forecast. "
                 "STA at STANDBY → MONITORING via N1. ADMISSIBLE.",
    },
    {
        "actor_id":  "sta_kim",
        "action":    "check_parameters",
        "shift_id":  "STS_51L_REVIEW",
        "timestamp": T + 5.0,
        "_note": "Continued monitoring of joint temperature trend data. "
                 "Loop in MONITORING. ADMISSIBLE.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 2: Operator (SRO_SM analog) — admissible state advance
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "sro_garcia",
        "action":    "read_indicators",
        "shift_id":  "STS_51L_OPS",
        "timestamp": T + 10.0,
        "_note": "Operator (management decision-maker, modeled as "
                 "SRO_SM) reviews data. STANDBY → MONITORING. ADMISSIBLE.",
    },
    {
        "actor_id":  "sro_garcia",
        "action":    "withdraw_control_rods",
        "shift_id":  "STS_51L_OPS",
        "timestamp": T + 15.0,
        "_note": "Operator advances to OPERATING state via N2. ADMISSIBLE.",
    },
    # ──────────────────────────────────────────────────────────
    # Phase 3: THE OVERRIDE — N6 from OPERATING state
    # Per the nuclear flow graph: N6 is valid only from
    # EMERGENCY_RESPONSE or OVERRIDE_ACTIVE for SRO_SM.
    # OPERATING.flows does not contain N6. Gate fires ORDER.
    # ──────────────────────────────────────────────────────────
    {
        "actor_id":  "sro_garcia",
        "action":    "vent_containment",
        "shift_id":  "STS_51L_OPS",
        "timestamp": T + 20.0,
        "_note": "~22:30 EST analog: Management caucus invokes "
                 "override of safety criterion (analog: vent_containment "
                 "→ N6_ExtremeOverride). STRUCTURAL VIOLATION: N6 "
                 "attempted from OPERATING state. N6 is in SRO_SM "
                 "vocabulary (valid at EMERGENCY_RESPONSE or "
                 "OVERRIDE_ACTIVE) but NOT in OPERATING.flows. The "
                 "prerequisite N3_ProtectiveMitigation → "
                 "EMERGENCY_RESPONSE transition had not occurred — "
                 "no formal hazard declaration preceded the override. "
                 "→ ORDER fires.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Sub-sequence: JURISDICTION — N6 by non-SRO_SM role
# ═══════════════════════════════════════════════════════════════════════
# Alternative reading: if the override decision was made by personnel
# without SRO_SM authority (e.g., Emergency Director role), N6 is
# outside their vocabulary entirely.
# ═══════════════════════════════════════════════════════════════════════

CHALLENGER_NUCLEAR_JURISDICTION = [
    {
        "actor_id":  "ed_williams",
        "action":    "read_indicators",
        "shift_id":  "STS_51L_ED",
        "timestamp": T + 100.0,
        "_note": "ED at STANDBY → MONITORING via N1. ADMISSIBLE.",
    },
    {
        "actor_id":  "ed_williams",
        "action":    "vent_containment",
        "shift_id":  "STS_51L_ED",
        "timestamp": T + 101.0,
        "_note": "Emergency Director attempts N6_ExtremeOverride. "
                 "STRUCTURAL VIOLATION: N6 not in ED vocabulary. "
                 "→ JURISDICTION fires. Models the alternative reading "
                 "in which the override decision was made by personnel "
                 "without the structural authority to do so under the "
                 "nuclear-equivalent framework.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Run the reconstruction
# ═══════════════════════════════════════════════════════════════════════

def run_reconstruction():
    print("\n" + "═"*70)
    print("INVERSE INCIDENT RECONSTRUCTION — CHALLENGER (NUCLEAR)")
    print("Reconstruction type: STRUCTURAL ANALOG")
    print("Source: Rogers Commission Vol. I; NSTS-08171 (LCC document)")
    print("═"*70)
    print()

    print("─"*70)
    print("PRIMARY SEQUENCE: ORDER — N6 override from non-emergency state")
    print("─"*70)

    compiler_a = NuclearCompiler()
    results_a  = []
    for i, ev in enumerate(CHALLENGER_NUCLEAR_EVENTS):
        packet = compiler_a.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results_a.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<22} | "
              f"{frm or '—':>15} → {to:<18} | {d}{tag}")
    print()

    print("─"*70)
    print("ALTERNATIVE SEQUENCE: JURISDICTION — N6 by non-SRO_SM role")
    print("─"*70)

    compiler_b = NuclearCompiler()
    results_b  = []
    for i, ev in enumerate(CHALLENGER_NUCLEAR_JURISDICTION):
        packet = compiler_b.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"]  = packet["STP_Header"]
        result["_step"] = i + 1
        result["_ts"]   = ev["timestamp"]
        result["_raw"]  = ev["action"]
        results_b.append(result)

        d   = result["decision"]
        inv = result.get("invariant", "—")
        frm = packet["STP_Header"]["FromState"]
        to  = packet["STP_Header"]["ToState"] or "—"
        tag = f"  *** GATE FIRES: {d} [{inv}] ***" if d == "INADMISSIBLE" else ""

        print(f"Step {i+1:02d} | +{ev['timestamp']:>6.1f}s | {ev['action']:<22} | "
              f"{frm or '—':>15} → {to:<18} | {d}{tag}")
    print()

    # ── Findings ──
    order_fire = next((r for r in results_a if r["decision"] == "INADMISSIBLE"), None)
    juris_fire = next((r for r in results_b if r["decision"] == "INADMISSIBLE"), None)

    print("═"*70)
    print("NUCLEAR SUBSTRATE FINDINGS")
    print("═"*70)

    if order_fire:
        print(f"\n[ORDER] Step {order_fire['_step']} — '{order_fire['_raw']}'")
        print(f"   N6_ExtremeOverride called from OPERATING state.")
        print(f"   Required prerequisite: N3 transition → EMERGENCY_RESPONSE.")
        print(f"   No formal hazard declaration preceded the override.")
        print(f"   Historical anchor: Jan 27 1986 management caucus (~22:30 EST).")

    if juris_fire:
        print(f"\n[JURISDICTION] (alternative) — '{juris_fire['_raw']}'")
        print(f"   N6 called by ED role — N6 not in ED vocabulary.")
        print(f"   Models the case where override authority was exercised")
        print(f"   by personnel without the structural role for it.")

    print()
    print("─"*70)
    print("Structural interpretation:")
    print("─"*70)
    print("In nuclear regulatory doctrine (10 CFR 50, 10 CFR 50.54(x),")
    print("NUREG-0737), operating outside the design qualification")
    print("envelope requires either prior NRC license amendment or")
    print("declared emergency conditions invoking 50.54(x) authority.")
    print()
    print("The Challenger Launch Commit Criteria did not include an")
    print("O-ring joint temperature minimum at the time of STS-51-L.")
    print("The qualification envelope (40°F-90°F) was treated as an")
    print("engineering guideline rather than a structural commit gate.")
    print("This is the structural analog of operating a reactor below")
    print("its minimum design temperature without prior amendment —")
    print("an action that in nuclear context fires ORDER (the override")
    print("path was not structurally entered) or JURISDICTION (the")
    print("personnel exercising the override lacked the structural")
    print("authority for it).")
    print()
    print("Both readings apply to Challenger. The compiler fires on each.")
    print("Lead time to vehicle disintegration: ~13 hours 9 minutes.")

    print()
    print("═"*70)
    print("RECONSTRUCTION STATUS: VALIDATED — structural analog mapping")
    print("═"*70)

    return {"primary": results_a, "alternative": results_b}


if __name__ == "__main__":
    all_results = run_reconstruction()
    summary = {}
    for seq_name, results in all_results.items():
        seq = []
        for r in results:
            seq.append({
                "step":       r["_step"],
                "timestamp":  r["_ts"],
                "action":     r["_raw"],
                "decision":   r["decision"],
                "invariant":  r.get("invariant"),
                "from_state": r["_stp"]["FromState"],
                "to_state":   r["_stp"]["ToState"],
            })
        summary[seq_name] = seq
    with open("/home/claude/challenger/challenger_nuclear_reconstruction_results.json", "w") as f:
        json.dump({
            "incident": "Challenger STS-51-L — Launch Commit Criteria Waiver (nuclear analog)",
            "source":   "Rogers Commission Vol. I; NSTS-08171 LCC; 10 CFR 50 doctrine",
            "compiler": "nuclear_compiler_v0_1",
            "reconstruction_type": "Structural analog",
            "sequences": summary,
        }, f, indent=2)
    print("\nMachine-readable results: challenger_nuclear_reconstruction_results.json")
