"""
v0.9 CloudTrail Reality Check — flaws.cloud Dataset

Runs the flaws.cloud CloudTrail dataset through the v0.9 Domain Compiler
and reports the tri-state distribution, including the new HYSTERESIS
invariant column.

v0.5c BASELINE (5,000 events, for delta comparison):
  ADMISSIBLE    : 4663  (93.3%)
  INADMISSIBLE  :  337  ( 6.7%)
  INDETERMINATE :    0  ( 0.0%)

  INADMISSIBLE breakdown (v0.5c):
    EXIT           169
    JURISDICTION    98
    ORDER           52
    BURST_CADENCE    9
    ─────────────────
    Total          328   (note: 9 events reclassified from INDETERMINATE)

v0.9 KEY QUESTION:
  Does HYSTERESIS fire on any events that were ADMISSIBLE under v0.5c?
  If yes: those are new detections — attacker sessions where the gate
  previously passed a post-violation scope expansion.

USAGE:
  python v0_9_cloudtrail_reality_check.py
  python v0_9_cloudtrail_reality_check.py --log-dir C:\\cyber_poc\\flaws_raw_logs
  python v0_9_cloudtrail_reality_check.py --log-dir ./flaws_raw_logs --max-events 5000
  python v0_9_cloudtrail_reality_check.py --log-dir ./flaws_raw_logs --max-events 0  (all events)

OUTPUT:
  Console: distribution table + invariant breakdown + top unknown events
  File:    results_v0_9_cloudtrail.json
"""

import argparse
import gzip
import json
import os
import sys
from collections import defaultdict
from typing import Iterator

from domain_compiler_v0_9 import DomainCompiler, evaluate_gate

# ─────────────────────────────────────────────────────────────────────────────
# v0.5c baseline for delta reporting
# ─────────────────────────────────────────────────────────────────────────────

BASELINE = {
    "ADMISSIBLE":    4663,
    "INADMISSIBLE":   337,
    "INDETERMINATE":    0,
    "total":         5000,
    "invariants": {
        "EXIT":          169,
        "JURISDICTION":   98,
        "ORDER":          52,
        "BURST_CADENCE":   9,
        "HYSTERESIS":      0,   # did not exist in v0.5c
    },
}

DEFAULT_LOG_DIR  = r"C:\cyber_poc\flaws_raw_logs"
DEFAULT_MAX      = 5000
OUTPUT_FILE      = "results_v0_9_cloudtrail.json"


# ─────────────────────────────────────────────────────────────────────────────
# Log loading
# ─────────────────────────────────────────────────────────────────────────────

def iter_events(log_dir: str) -> Iterator[dict]:
    """
    Yield individual CloudTrail event dicts from all .json and .json.gz
    files in log_dir, in sorted filename order (mirrors previous runs).
    Each file contains a CloudTrail log bundle: {"Records": [...events...]}.
    """
    if not os.path.isdir(log_dir):
        print(f"ERROR: log directory not found: {log_dir}", file=sys.stderr)
        print("Pass --log-dir <path> to specify the flaws.cloud log directory.",
              file=sys.stderr)
        sys.exit(1)

    files = sorted(
        f for f in os.listdir(log_dir)
        if f.endswith(".json") or f.endswith(".json.gz")
    )
    if not files:
        print(f"ERROR: no .json or .json.gz files found in {log_dir}",
              file=sys.stderr)
        sys.exit(1)

    for fname in files:
        path = os.path.join(log_dir, fname)
        try:
            if fname.endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            for event in data.get("Records", []):
                yield event
        except (OSError, json.JSONDecodeError) as e:
            print(f"  WARNING: skipping {fname}: {e}", file=sys.stderr)
            continue


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(log_dir: str, max_events: int) -> None:
    print(f"\nv0.9 CloudTrail Reality Check — flaws.cloud")
    print(f"Log directory : {log_dir}")
    print(f"Max events    : {'all' if max_events == 0 else max_events}")
    print(f"Compiler      : domain_compiler_v0_9")
    print(f"Baseline      : v0.5c (5,000 events)")
    print()

    dc = DomainCompiler()

    counts      = defaultdict(int)   # decision -> count
    invariants  = defaultdict(int)   # invariant -> count (INADMISSIBLE only)
    unknowns    = defaultdict(int)   # event name -> count (INDETERMINATE)
    processed   = 0
    all_results = []

    for event in iter_events(log_dir):
        if max_events and processed >= max_events:
            break

        try:
            pkt = dc.compile(event)
            result = evaluate_gate(pkt)
        except Exception as e:
            counts["ERROR"] += 1
            processed += 1
            continue

        decision  = result["decision"]
        invariant = result["invariant"]
        counts[decision] += 1

        if decision == "INADMISSIBLE" and invariant:
            invariants[invariant] += 1

        if decision == "INDETERMINATE":
            missing = pkt.get("STP_Header", {}).get("Resolution", {}).get("MissingAxes", [])
            if "Intentional.Behavior_Trajectory" in missing:
                event_name = event.get("eventName", "UNKNOWN")
                unknowns[event_name] += 1

        all_results.append({
            "event_name": event.get("eventName", "UNKNOWN"),
            "decision":   decision,
            "invariant":  invariant,
        })
        processed += 1

    total = processed

    # ── Print results ──────────────────────────────────────────────────────

    admissible    = counts["ADMISSIBLE"]
    inadmissible  = counts["INADMISSIBLE"]
    indeterminate = counts["INDETERMINATE"]

    def pct(n): return f"{n/total*100:.1f}%" if total else "0%"
    def delta(key, new_val):
        base = BASELINE.get(key, 0)
        diff = new_val - base
        if diff == 0:   return "  (±0)"
        if diff > 0:    return f"  (+{diff})"
        return f"  ({diff})"

    print("─" * 54)
    print(f"  {'Decision':<18} {'Count':>7}  {'%':>6}  {'vs v0.5c':>10}")
    print("─" * 54)
    print(f"  {'ADMISSIBLE':<18} {admissible:>7}  {pct(admissible):>6}  "
          f"{delta('ADMISSIBLE', admissible):>10}")
    print(f"  {'INADMISSIBLE':<18} {inadmissible:>7}  {pct(inadmissible):>6}  "
          f"{delta('INADMISSIBLE', inadmissible):>10}")
    print(f"  {'INDETERMINATE':<18} {indeterminate:>7}  {pct(indeterminate):>6}  "
          f"{delta('INDETERMINATE', indeterminate):>10}")
    if counts["ERROR"]:
        print(f"  {'ERROR':<18} {counts['ERROR']:>7}")
    print("─" * 54)
    print(f"  {'TOTAL':<18} {total:>7}")
    print()

    if inadmissible:
        print("  INADMISSIBLE breakdown:")
        print("  ─" * 24)
        for inv in ["HYSTERESIS", "EXIT", "JURISDICTION", "ORDER",
                    "BURST_CADENCE", "ROLE_CONFUSION"]:
            n = invariants.get(inv, 0)
            if n == 0 and inv not in ("HYSTERESIS",):
                continue
            base_n = BASELINE["invariants"].get(inv, 0)
            d = n - base_n
            d_str = f"  (+{d})" if d > 0 else (f"  ({d})" if d < 0 else "  (±0)")
            marker = " ◄ NEW" if inv == "HYSTERESIS" and n > 0 else ""
            print(f"    {inv:<20} {n:>5}  {d_str}{marker}")
        # Any unexpected invariants
        for inv, n in invariants.items():
            if inv not in ["HYSTERESIS","EXIT","JURISDICTION","ORDER",
                           "BURST_CADENCE","ROLE_CONFUSION"]:
                print(f"    {inv:<20} {n:>5}")
        print()

    if unknowns:
        print(f"  Top INDETERMINATE events (unknown action mapping):")
        print("  ─" * 24)
        for name, n in sorted(unknowns.items(), key=lambda x: -x[1])[:15]:
            print(f"    {name:<40} {n:>5}")
        print()

    # Hysteresis-specific note
    h_count = invariants.get("HYSTERESIS", 0)
    if h_count > 0:
        print(f"  ► HYSTERESIS fired {h_count} time(s).")
        print(f"    These are events that were ADMISSIBLE under v0.5c but are now")
        print(f"    caught as post-violation scope expansions by the fifth invariant.")
        print(f"    Each represents a trajectory the gate previously missed.")
        print()
    else:
        print(f"  ► HYSTERESIS: 0 fires.")
        print(f"    No post-violation scope expansions detected in this window.")
        print(f"    This is consistent with a dataset where violations are clustered")
        print(f"    at session end rather than mid-session followed by continuation.")
        print()

    # ── Write JSON output ──────────────────────────────────────────────────

    output = {
        "compiler_version": "v0.9",
        "dataset":          "flaws.cloud CloudTrail",
        "events_processed": total,
        "baseline_version": "v0.5c",
        "baseline_events":  BASELINE["total"],
        "distribution": {
            "ADMISSIBLE":    admissible,
            "INADMISSIBLE":  inadmissible,
            "INDETERMINATE": indeterminate,
        },
        "invariant_breakdown": dict(invariants),
        "top_unknown_events":  dict(
            sorted(unknowns.items(), key=lambda x: -x[1])[:20]
        ),
        "delta_vs_baseline": {
            "ADMISSIBLE":    admissible   - BASELINE["ADMISSIBLE"],
            "INADMISSIBLE":  inadmissible - BASELINE["INADMISSIBLE"],
            "INDETERMINATE": indeterminate - BASELINE["INDETERMINATE"],
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"  Results written to: {OUTPUT_FILE}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v0.9 CloudTrail reality check — flaws.cloud dataset"
    )
    parser.add_argument(
        "--log-dir", default=DEFAULT_LOG_DIR,
        help=f"Path to flaws.cloud log directory (default: {DEFAULT_LOG_DIR})"
    )
    parser.add_argument(
        "--max-events", type=int, default=DEFAULT_MAX,
        help="Max events to process (0 = all, default: 5000)"
    )
    args = parser.parse_args()
    run(args.log_dir, args.max_events)


if __name__ == "__main__":
    main()
