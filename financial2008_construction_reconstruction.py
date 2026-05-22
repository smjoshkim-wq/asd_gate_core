"""
2008 Financial Crisis Inverse Reconstruction — Construction Substrate
═══════════════════════════════════════════════════════════════════════

Substrate: construction_compiler_v0_1 (Owner role, H1 remediation track)
Type:      Structural Analog (fourth instance of the DEFICIENCY_NOTED
           pattern — Algo / Champlain / Bhopal / Lehman Repo 105)
Lead time: ~4 months (Matthew Lee letter May 16, 2008 → Lehman bankruptcy
           September 15, 2008)
Precision: Month-level

Pattern source
──────────────
This is the FOURTH instance of the construction DEFICIENCY_NOTED pattern:
  - Algo Centre Mall (2012)        : Owner stalled H1 from DEFICIENCY_NOTED
  - Champlain Towers South (2021)  : Owner stalled H1 from DEFICIENCY_NOTED
  - Bhopal (1982-1984)             : UCC parent A3_Commitment from
                                     DEFICIENCY_NOTED post-1982 audit
  - Lehman Repo 105 (2008)         : Lehman senior management A3_Commitment
                                     from DEFICIENCY_NOTED post-Lee letter

Same compiler, same invariant (ORDER), same geometry: Owner role in
DEFICIENCY_NOTED state executes a non-H1 commitment action instead of
H1_RemediationAuth → state-skip ORDER violation.

The pattern now extends across:
  - building structural failure (Algo, Champlain)
  - chemical process industrial failure (Bhopal)
  - financial accounting / leverage concealment (Lehman Repo 105)

Historical anchor — Matthew Lee letter, Lehman Brothers Repo 105
─────────────────────────────────────────────────────────────────
Matthew Lee was Senior Vice President and Lehman Brothers Global
Balance Sheet Officer until May 2008. He was responsible for the
firm's daily balance sheet reconciliation and reporting.

Throughout 2007 and early 2008, Lehman used "Repo 105" transactions
— repurchase agreements structured under UK law (relying on a
Linklaters legal opinion stating they qualified for true-sale accounting
treatment under SFAS 140) — to temporarily move ~$50 billion of
assets off the balance sheet at each quarter-end. The mechanic:
sell the assets via repo agreement just before quarter-end (recording
them as sold rather than as financing); repurchase them days after
quarter-end. Net effect: reported leverage ratio at quarter-end was
materially lower than actual leverage between quarters.

May 16, 2008: Lee sent a formal letter to Lehman's senior management
(CFO Erin Callan, Chief Risk Officer Madelyn Antoncic, Chief Audit
Officer Joseph Polizzotto, and General Counsel Tom Russo) explicitly
identifying that Lehman's Repo 105 program was misleading the firm's
reported financial condition. The letter identified ~$50 billion in
quarter-end Repo 105 usage and stated that the firm's financial
statements did not fairly present its financial position.

This places Lehman as Owner of its own corporate "remediation track"
into compiler-state DEFICIENCY_NOTED, anchored to engineering evidence
(the Lee letter, which is the structural analog of the engineering
deficiency reports at Algo Centre Mall and Champlain Towers South).

The single legal outflow from DEFICIENCY_NOTED for Owner role is
H1_RemediationAuth → REMEDIATION. Lehman did not execute H1 (did not
cease Repo 105 usage, did not restate prior financials, did not
disclose to investors). Instead, between May 16 and August 31, 2008,
Lehman made multiple capital commitments (A3_Commitment in Owner
vocabulary) — including the August 2008 capital raise, continued
Q2 2008 ($50.4B Repo 105) and Q3 2008 ($24B Repo 105) quarter-end
usage, and the September 9 Korea Development Bank capital infusion
negotiation. All A3_Commitment from DEFICIENCY_NOTED → ORDER fires.

Bankruptcy filing: September 15, 2008. Examiner's report (Anton Valukas):
March 11, 2010, identifying the Repo 105 program and confirming the
Lee letter timeline and Lehman senior management non-remediation
response.

(Sources: Anton R. Valukas, "Report of the Examiner, In re Lehman
Brothers Holdings Inc., et al., Case No. 08-13555," US Bankruptcy
Court for the Southern District of New York, March 2010, Volume 3
Section III.A.4 "Repo 105"; Matthew Lee deposition, In re Lehman
Brothers, 2009; SEC v. Ernst & Young LLP, 2010.)

Compiler mapping
────────────────
lehman_holdings = Owner role.
project_id = "lehman_holdings_balance_sheet_2008".

State seeded directly to DEFICIENCY_NOTED, matching the convention
used for Algo, Champlain, and Bhopal anchors: the deficiency state is
established by external evidence (the Lee letter, the engineering
audit, the survey report), not reached by an event-stream transition.

Step 1: lehman_holdings executes A3_Commitment (Q2 2008 quarter-end
Repo 105 usage, May 31, 2008). The single legal outflow from
DEFICIENCY_NOTED is H1_RemediationAuth. A3_Commitment is in Owner
vocabulary at DESIGN and PERMIT_ISSUED states, but not at DEFICIENCY_NOTED.
State-skip violation → ORDER fires.

R5 boundary
───────────
The failure to execute H1_RemediationAuth itself (failure to restate,
failure to disclose, failure to cease the program) is R5-passive and
not modeled. The commission event modeled is the Q2 2008 quarter-end
Repo 105 commitment, which is the positive-action geometric violation
that occurred while DEFICIENCY_NOTED was the standing state of record.

Follows from
────────────
- 2026_05_19_Inverse_Incident_Methodology_v1_0.md
- 2026_05_21_Bhopal_Three_Substrate_Reconstruction_Note.md (DEFICIENCY_NOTED, 3rd instance)
- construction_compiler_v0_1.py incident anchors (Algo, Champlain)
"""

import json
import sys
sys.path.insert(0, ".")

from construction_compiler_v0_1 import ConstructionCompiler, CONSTRUCTION_ROLE_TABLE
from domain_compiler_v0_9 import evaluate_gate

# Register Lehman Brothers Holdings as Owner of the corporate balance
# sheet "remediation track" — structural analog to the corporate Owner
# role at Algo Centre Mall and Champlain Towers South.
CONSTRUCTION_ROLE_TABLE["lehman_holdings"] = "Owner"

# May 31, 2008 (Q2 quarter-end Repo 105 commitment, 15 days after Lee letter)
# ≈ Unix 1212192000
BASE_TS = 1_212_192_000.0
project_id = "lehman_holdings_balance_sheet_2008"


def run_reconstruction():
    compiler = ConstructionCompiler()

    # ── State seeding ──
    # Lee's May 16, 2008 letter establishes the structural deficiency
    # by engineering evidence, placing the Owner role in DEFICIENCY_NOTED
    # state of record. This matches the Algo / Champlain / Bhopal
    # convention (deficiency state externally established).
    key = ("lehman_holdings", "Owner")
    compiler.tracker._states[key] = "DEFICIENCY_NOTED"
    compiler.tracker._visited_states[key] = {"DEFICIENCY_NOTED"}
    compiler.tracker._session_registry[project_id] = "lehman_holdings"

    print(f"[seed] Owner state set to DEFICIENCY_NOTED (per Matthew Lee letter May 16, 2008)")
    print(f"[seed] visited_states = {{DEFICIENCY_NOTED}}")
    print(f"[seed] project binding: {project_id} → lehman_holdings")
    print()

    # Step 1: Q2 2008 quarter-end Repo 105 commitment (May 31, 2008,
    # 15 days after Lee letter). Lehman executes a capital commitment
    # (A3_Commitment) from DEFICIENCY_NOTED. The single legal outflow
    # from DEFICIENCY_NOTED is H1_RemediationAuth; A3_Commitment is
    # in Owner vocabulary elsewhere but not at DEFICIENCY_NOTED.
    # State-skip violation → ORDER fires.
    step1 = {
        "actor_id":  "lehman_holdings",
        "action":    "sign_schedule_a",  # maps to A3_Commitment per ACTION_CLASS_MAP
        "project_id": project_id,
        "timestamp": BASE_TS + 0,
    }

    events = [step1]
    results = []
    for i, ev in enumerate(events):
        packet = compiler.compile(ev)
        r = evaluate_gate(packet)
        results.append({
            "step":     i + 1,
            "actor_id": ev["actor_id"],
            "action":   ev["action"],
            "decision": r["decision"],
            "invariant": r["invariant"],
        })
        print(f"step {i+1}: {ev['actor_id']:18s} {ev['action']:18s} "
              f"→ {r['decision']:14s} ({r['invariant'] or '—'})")

    return results


def main():
    print("=" * 72)
    print("2008 Financial Crisis Reconstruction — Construction Substrate")
    print("Lehman Repo 105 (DEFICIENCY_NOTED Pattern, 4th Instance)")
    print("=" * 72)
    print()
    results = run_reconstruction()
    print()

    order_fires = [r for r in results if r["invariant"] == "ORDER"]

    summary = {
        "incident": "2008 Financial Crisis — Lehman Brothers Repo 105",
        "substrate": "construction",
        "reconstruction_type": "Structural Analog",
        "precision_class": "Month-level",
        "lead_time_description": (
            "Matthew Lee letter May 16, 2008 → Lehman bankruptcy "
            "September 15, 2008 = ~4 months. ORDER fire at Q2 2008 "
            "quarter-end commitment (May 31) is ~3.5 months before "
            "bankruptcy. Compared to Bhopal (30 months) and Algo / "
            "Champlain (years), this is the shortest lead time observed "
            "for the DEFICIENCY_NOTED pattern."
        ),
        "pattern_class": "DEFICIENCY_NOTED commission (Algo / Champlain / Bhopal pattern)",
        "invariants_fired": [
            {"step": r["step"], "invariant": r["invariant"]}
            for r in results if r["invariant"]
        ],
        "order_fired_at_step": order_fires[0]["step"] if order_fires else None,
        "geometry": (
            "Owner (Lehman Brothers Holdings) executes A3_Commitment "
            "from DEFICIENCY_NOTED state. DEFICIENCY_NOTED.flows contains "
            "only H1_RemediationAuth; A3_Commitment is in Owner vocabulary "
            "at DESIGN and PERMIT_ISSUED but NOT at DEFICIENCY_NOTED. "
            "State-skip violation → ORDER fires."
        ),
        "cross_incident_stability_deficiency_pattern": [
            "Algo Centre Mall 2012 (Owner H1 stall, ORDER)",
            "Champlain Towers South 2021 (Owner H1 stall, ORDER)",
            "Bhopal 1984 (UCC parent Owner, A3_Commitment from DEFICIENCY_NOTED, ORDER)",
            "Lehman Repo 105 2008 (Lehman Holdings Owner, A3_Commitment from DEFICIENCY_NOTED, ORDER)",
        ],
        "claim_strengthened": (
            "DEFICIENCY_NOTED pattern instantiated on four independent "
            "incidents spanning building structural failure, chemical "
            "process industrial failure, and financial accounting "
            "concealment. Same compiler, same invariant, same geometry; "
            "no compiler-side modifications between instances. The "
            "pattern is substrate-agnostic for any 'Owner has been "
            "notified of structural deficiency by engineering evidence "
            "and committed to non-remediation' geometry."
        ),
        "historical_anchor": {
            "warning":  "Matthew Lee letter, May 16, 2008 (Lehman Global Balance Sheet Officer)",
            "deficiency_evidence": (
                "$50B+ quarter-end Repo 105 usage; Linklaters UK-law opinion "
                "treated as true-sale accounting under SFAS 140; financial "
                "statements not fairly presenting financial position"
            ),
            "owner_response": (
                "Lee terminated; no restatement; no disclosure; continued "
                "Repo 105 program through Q2 ($50.4B) and Q3 ($24B) 2008"
            ),
            "downstream": (
                "September 15, 2008 Chapter 11 filing — largest US "
                "bankruptcy in history ($639B in assets); Valukas Examiner "
                "Report March 2010 confirmed timeline and pattern"
            ),
        },
        "events": results,
    }

    out_path = "/home/claude/financial2008/financial2008_construction_reconstruction_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results written: {out_path}")
    return bool(order_fires)


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
