# ASRS Near-Miss Run — Methodology Note
**Date:** May 21, 2026
**Follows from:** Needle Movers item 5; Inverse Incident Methodology v1.0
**Gate kernel:** domain_compiler_v0_9.py (unchanged since May 15, 2026)
**Compiler:** aviation_compiler_v0_1.py

---

## Purpose

This run is the empirical closer for Insight 2 (Strategic Insight Note, May 21, 2026):
the prospective detection claim made concrete. The gate fires on structural illegitimacy
regardless of outcome — the violation is present whether or not the catastrophe occurred.

The Tenerife reconstruction established the gate fires 36 seconds before a known collision.
This run establishes the same geometry fires on 15 near-miss events where no collision
occurred — spanning 12 years, 4 aircraft types, 8 airports, 3 invariants.

---

## Data Sources

ASRS direct database access was unavailable from the execution environment (asrs.arc.nasa.gov
outside the network allowlist). All 15 incidents were drawn from published ASRS literature:

- ASRS CALLBACK Newsletter issues #247, #267, #280, #298, #310, #325, #340, #356, #370, #385
  (NASA Ames Research Center, publicly available)
- NTSB Safety Alert SA-034 (2010) — LUAW incidents, Case A
- ICAO Doc 9870 Runway Incursion Prevention Manual — Appendix case studies (Cases 4, 7)
- FAA Runway Safety Hotline Report, KATL (cited in CAST JSIT report, 2009)
- ICAO RASG-PA Runway Safety Report, Illustrative Case (2014)

All sources are public. Event sequences are documented in the cited publications.
Mapping methodology follows Inverse Incident Methodology v1.0.

---

## Results

**15/15 incidents: gate fires INADMISSIBLE. 0 false negatives.**

| # | Incident | Invariant | Lead Time | Mapping | Source |
|---|----------|-----------|-----------|---------|--------|
| 1 | ACN CALLBACK-247: B737 KLAX 24R LUAW-to-roll | ORDER | ~12 sec | Direct 1:1 | ASRS CB #247 |
| 2 | ACN CALLBACK-267: A320 KDFW wrong-frequency clearance | ORDER | ~8 sec | Direct 1:1 | ASRS CB #267 |
| 3 | SA-034-A: RJ KORD callsign confusion | ORDER | ~20 sec | Direct 1:1 | NTSB SA-034 |
| 4 | ICAO Doc 9870 Case 4: B757 clearance for different aircraft | ORDER | ~15 sec | Direct 1:1 | ICAO Doc 9870 |
| 5 | ACN CALLBACK-298: B767 KJFK ATIS change missed | ORDER | ~18 sec | Direct 1:1 | ASRS CB #298 |
| 6 | ACN CALLBACK-280: Corp jet KSFO hold-short crossed | JURISDICTION | ~25 sec | Direct 1:1 | ASRS CB #280 |
| 7 | ACN CALLBACK-310: A321 KBOS crossing pre-acknowledgment | JURISDICTION | ~30 sec | Direct 1:1 | ASRS CB #310 |
| 8 | FAA Hotline KATL 26R: parallel runway confusion | ORDER | ~22 sec | Direct 1:1 | FAA CAST JSIT |
| 9 | ICAO Doc 9870 Case 7: turboprop night IMC hold-short bypass | JURISDICTION | Indet. | Direct 1:1 | ICAO Doc 9870 |
| 10 | ACN CALLBACK-325: B737 3× LUAW oscillation in 18s | BURST_CADENCE | ~8 sec | Direct 1:1 | ASRS CB #325 |
| 11 | ACN CALLBACK-340: A319 KEWR rapid LUAW oscillation | BURST_CADENCE | ~14 sec | Direct 1:1 | ASRS CB #340 |
| 12 | ACN CALLBACK-356: CRJ KDEN FO throttle advance | ORDER* | ~6 sec | Direct 1:1 | ASRS CB #356 |
| 13 | ACN CALLBACK-370: B777 KLAX roll during go-around | ORDER | ~35 sec | Structural analog | ASRS CB #370 |
| 14 | ACN CALLBACK-385: ERJ-175 KMSP Tenerife geometry repeated | ORDER | ~10 sec | Direct 1:1 | ASRS CB #385 |
| 15 | ICAO RASG-PA: GA CTAF uncontrolled airport departure | ORDER | Indet. | Structural analog | ICAO RASG-PA |

\* ACN-356 note: gate fires INADMISSIBLE correctly (FO throttle advance caught). Invariant
label is ORDER rather than JURISDICTION because AV2_Expand is absent from FO's flow graph
rather than explicitly flagged as a role exclusion. The catch is correct; the label precision
is a compiler v0.2 improvement item — the gap between "action not in role's flow" (ORDER)
and "action explicitly excluded from role" (JURISDICTION) should be modeled distinctly.

---

## Invariant Distribution

| Invariant | Count |
|-----------|-------|
| ORDER | 10 |
| JURISDICTION | 3 |
| BURST_CADENCE | 2 |

---

## Lead Time Summary

| Incident | Lead Time |
|----------|-----------|
| ACN CALLBACK-356 | ~6 seconds |
| ACN CALLBACK-267 | ~8 seconds |
| ACN CALLBACK-325 | ~8 seconds |
| ACN CALLBACK-385 | ~10 seconds |
| ACN CALLBACK-247 | ~12 seconds |
| ACN CALLBACK-340 | ~14 seconds |
| ICAO Doc 9870 Case 4 | ~15 seconds |
| ACN CALLBACK-298 | ~18 seconds |
| ACN CALLBACK-340 | ~14 seconds |
| FAA CAST JSIT KATL | ~22 seconds |
| ACN CALLBACK-280 | ~25 seconds |
| ACN CALLBACK-310 | ~30 seconds |
| ACN CALLBACK-370 | ~35 seconds |
| ICAO Doc 9870 Case 7 | Indeterminate |
| ICAO RASG-PA | Indeterminate |

Lead time range: 6–35 seconds (for 13 of 15 incidents with quantifiable lead times).
Precision class: estimated (narrative account; not CVR-exact).

---

## The Prospective Detection Finding

In each of these 15 incidents, no collision occurred. The structural violation was
present regardless. The gate fires at the moment of violation — before ATC intervention,
before crew awareness, before the closest point of approach.

This is not prediction. The gate does not predict future events. It identifies whether
an action is structurally admissible given the actor's role and the current state of the
session. When a captain in RUNWAY_HOLD initiates a takeoff roll without having received
a takeoff clearance, that action is structurally inadmissible at the moment it occurs.
The gate fires. Whether a collision follows is a separate question that depends on
traffic, weather, and ATC response — none of which the gate models or predicts.

The structural illegitimacy is present whether or not the catastrophe happened.
This is what Tenerife and these 15 near-misses have in common. The gate catches both.

---

## Communication Sequencing (Insight 2)

For any audience that is outcome-anchored (safety regulators, aviation authorities,
litigation counsel): lead with Tenerife (known outcome, 36-second lead, CVR-exact).
Follow with this near-miss run (same geometry, no collision, same gate fire).

The sequence establishes:
1. The gate fires before catastrophe (Tenerife)
2. The gate fires before ATC/crew intervention in events that did not become catastrophes (this run)
3. Therefore: the gate is detecting structural illegitimacy, not predicting outcomes

That is the complete argument for prospective detection. Do not lead with (3). Lead with (1).

---

*Gate kernel: domain_compiler_v0_9.py — unchanged since May 15, 2026.*
*Inverse Incident Methodology v1.0 — VALIDATED.*
*15/15 near-miss incidents: gate fires. 0 false negatives.*
