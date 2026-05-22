"""
2008 Financial Crisis Inverse Reconstruction — Financial Substrate
═══════════════════════════════════════════════════════════════════════

Substrate: financial_compiler_v0_1 (Underwriter/CRA, F0..F10)
Type:      Direct 1:1 (compiler's A01 anchor is "Underwriter bypasses audit
           (2008 waiver bypass)" — this reconstruction is the historical
           event that anchor was designed for)
Lead time: ~14 months (Bowen first warns Citi senior management Nov 2007
           → Bear Stearns hedge fund collapse March 2008 → Citi writedowns
           Q1 2008 → Lehman collapse Sep 2008 → broader crisis Oct 2008)
Precision: Quarter-level

Historical anchor — Richard Bowen at Citigroup
───────────────────────────────────────────────
Richard M. Bowen III was Senior Vice President and Business Chief
Underwriter for Citigroup's Consumer Lending Group from 2006 onward.
His responsibility included quality control of mortgages purchased by
Citi from correspondent lenders (~$50 billion annually) for securitization
into RMBS/CDO instruments and sale to investors.

By mid-2006, Bowen's quality control teams had documented that 60% of
the prime mortgages Citi was purchasing failed Citi's own underwriting
guidelines. By 2007, the failure rate had risen to 80%. Bowen escalated
internally; deals continued to advance through securitization with
formal "waivers" issued by Citi senior management to bypass the failed
audits.

November 3, 2007: Bowen sent a memo titled "URGENT" to Robert Rubin
(Chairman of Citigroup's Executive Committee), David Bushnell (Chief
Risk Officer), Gary Crittenden (CFO), and Bonnie Howard (Chief Auditor),
explicitly identifying that Citi had "billions of dollars" of unrecognized
losses in defective mortgages already securitized and sold to investors.

Citi management's response: Bowen was relieved of most of his responsibilities,
demoted, and his staff reduced from 220 to 2. No remediation of the
underlying waiver-bypass pattern. Securitizations continued through
Q1 2008 until market collapse made further issuance impractical.

(Sources: Bowen testimony to Financial Crisis Inquiry Commission, April 7,
2010; FCIC Final Report, January 2011, ch. 9-10; Citigroup internal
documents released in SEC v. Citigroup Global Markets Inc., 2010.)

Compiler mapping
────────────────
Citigroup CDO underwriting desk = Underwriter role.
Single deal flow:
  asset_level_verification (F0)    — IDLE → AUDIT_PENDING (Bowen's QC scan)
  advance_to_securitization (F4)   — F4 from AUDIT_PENDING fires ORDER
                                     (the canonical A01 waiver bypass pattern)

This is the cleanest Direct 1:1 reconstruction in the entire 14-substrate
corpus: the compiler's A01 incident anchor is documented as "2008 waiver
bypass" in the source code, and the reconstruction instantiates that
anchor with the historical actor and timeline.

R5 boundary
───────────
Bowen's escalation memo is itself a positive action (would be A3_Recommend
in org_workflow substrate). The R5-passive content is the absence of
follow-up remediation by Citi management. The commission event modeled
in this substrate is the securitization advance itself, which is the
geometric violation regardless of internal escalation.

Follows from
────────────
- 2026_05_19_Inverse_Incident_Methodology_v1_0.md
- 2026_05_21_Bhopal_Three_Substrate_Reconstruction_Note.md
- financial_compiler_v0_1.py (A01 incident anchor)
"""

import json
import sys
sys.path.insert(0, ".")

from financial_compiler_v0_1 import FinancialCompiler, FINANCIAL_ROLE_TABLE

# Register Citigroup CDO underwriting desk as Underwriter role.
# uw_citi_desk is already in the default role table (per A01 harness anchor).
# Adding a named historical actor for traceability.
FINANCIAL_ROLE_TABLE["citi_cdo_underwriting_desk"] = "Underwriter"

# Nov 3, 2007 ≈ 1194048000 Unix (Bowen escalation memo date — anchor
# for the visible commission event in this reconstruction).
BASE_TS = 1_194_048_000.0


def run_reconstruction():
    compiler = FinancialCompiler()
    deal_id = "CITI_RMBS_2007_Q4_typical"

    # Step 1: Citigroup CDO desk performs initial asset-level
    # verification on a typical correspondent-lender mortgage pool.
    # IDLE → AUDIT_PENDING. Admissible.
    step1 = {
        "actor_id": "citi_cdo_underwriting_desk",
        "action":   "asset_level_verification",
        "deal_id":  deal_id,
        "timestamp": BASE_TS + 0,
    }

    # Step 2: Citi senior management issues a waiver and advances the
    # deal to securitization despite the audit having identified
    # defective mortgages. AUDIT_PENDING.flows does NOT contain F4_Advance
    # (waiver bypass anchor). ORDER fires.
    step2 = {
        "actor_id": "citi_cdo_underwriting_desk",
        "action":   "advance_to_securitization",
        "deal_id":  deal_id,
        "timestamp": BASE_TS + 14 * 24 * 3600,  # ~2 weeks later (Nov 17, 2007)
    }

    events = [step1, step2]
    results = []
    for i, ev in enumerate(events):
        r = compiler.compile(ev)
        results.append({
            "step":     i + 1,
            "actor_id": ev["actor_id"],
            "action":   ev["action"],
            "decision": r["decision"],
            "invariant": r["invariant"],
        })
        print(f"step {i+1}: {ev['actor_id']:28s} {ev['action']:28s} "
              f"→ {r['decision']:14s} ({r['invariant'] or '—'})")

    return results


def main():
    print("=" * 72)
    print("2008 Financial Crisis Reconstruction — Financial Substrate")
    print("Citigroup CDO Waiver Bypass (Bowen FCIC Testimony Anchor)")
    print("=" * 72)
    print()
    results = run_reconstruction()
    print()

    order_fires = [r for r in results if r["invariant"] == "ORDER"]
    pre_order_admissible = results[0]["decision"] == "ADMISSIBLE"

    summary = {
        "incident": "2008 Financial Crisis — Citigroup CDO Waiver Bypass",
        "substrate": "financial",
        "reconstruction_type": "Direct 1:1",
        "compiler_anchor": "A01 (Underwriter bypasses audit, 2008 waiver bypass)",
        "precision_class": "Quarter-level",
        "lead_time_description": (
            "November 2007 Bowen URGENT memo → ~10 months to Lehman "
            "collapse September 2008; ORDER fire on the geometric "
            "violation precedes market collapse by ~10 months"
        ),
        "invariants_fired": [
            {"step": r["step"], "invariant": r["invariant"]}
            for r in results if r["invariant"]
        ],
        "order_fired_at_step": order_fires[0]["step"] if order_fires else None,
        "pre_order_admissible": pre_order_admissible,
        "geometry": (
            "Underwriter executes F4_Advance from AUDIT_PENDING. "
            "F4_Advance is in Underwriter vocabulary at POOL_ACTIVE.flows "
            "(legitimate post-audit advance) but explicitly excluded from "
            "AUDIT_PENDING.flows. The action-class is in the role's "
            "global vocabulary but not in the current state's outflow "
            "graph — ORDER fires on the state-skip violation."
        ),
        "historical_anchor": {
            "actor":     "Richard Bowen, SVP and Business Chief Underwriter, Citigroup CLG",
            "audit":     "60% (2006) → 80% (2007) failure rate against Citi guidelines",
            "warning":   "Nov 3, 2007 'URGENT' memo to Rubin / Bushnell / Crittenden / Howard",
            "response":  "Bowen demoted, staff cut 220→2; no remediation of bypass pattern",
            "downstream": "Q1 2008 Citi writedowns ~$15B; Q4 2008 federal bailout ~$45B + ~$300B guarantees"
        },
        "events": results,
    }

    out_path = "/home/claude/financial2008/financial2008_financial_reconstruction_results.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results written: {out_path}")
    return bool(order_fires) and pre_order_admissible


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
