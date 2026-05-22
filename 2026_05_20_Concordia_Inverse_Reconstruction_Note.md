# Inverse Incident Reconstruction — Costa Concordia 2012
**Date:** May 20, 2026
**Status:** ✅ Validated on hardware
**Follows:** Tenerife (May 21), Gelsinger (May 20)

---

## 1. Incident Summary

On January 13, 2012, the cruise ship MV Costa Concordia (Captain Francesco Schettino) struck Scole Rocks off Giglio Island, Italy, during an unauthorized coastal "inchino" (salute) pass. The ship's hull was torn open; 32 people died. The incident produced two distinct structural violations — one causal, one in the emergency response — against the same gate kernel with zero tuning between them.

Primary sources: Italian Ministry DIGEMA Marine Accident Investigation Report (2013); Genova Public Prosecutor investigation record (2013–2015); Italian Criminal Court Grosseto verdict against Schettino (February 2015, confirmed on appeal November 2016); Italian Coast Guard radio transcripts including the De Falco/Schettino exchange; MAIB Safety Digest Issue 2/2012.

---

## 2. Gate Results — Two Invariants

### Finding 1: BURST_CADENCE (step 9)

| Step | Action | State | Decision |
|------|--------|-------|----------|
| 1 | `monitor_ecdis` | STANDBY → MONITORING | ADMISSIBLE |
| 2 | `alter_course` | MONITORING → UNDERWAY | ADMISSIBLE |
| 3 | `report_position_vts` | UNDERWAY → COASTAL_WATERS | ADMISSIBLE |
| 4 | `verify_course` | COASTAL_WATERS → MONITORING | ADMISSIBLE |
| 5 | `alter_course` | MONITORING → UNDERWAY | ADMISSIBLE [expansion 1] |
| 6 | `monitor_ecdis` | UNDERWAY → MONITORING | ADMISSIBLE [contraction] |
| 7 | `alter_course` | MONITORING → UNDERWAY | ADMISSIBLE [expansion 2] |
| 8 | `verify_course` | UNDERWAY → MONITORING | ADMISSIBLE [contraction] |
| **9** | **`alter_course`** | **MONITORING → UNDERWAY** | **INADMISSIBLE [BURST_CADENCE]** |

Three expansions (steps 5, 7, 9) within 50 seconds → BURST fires.

- Gate timestamp: ~21:33:50 CET (~1326486830)
- Rock strike: ~21:44 CET (~1326487440)
- **Lead time: 10 minutes before impact**

### Finding 2: ORDER (step 12)

| Step | Action | State | Decision |
|------|--------|-------|----------|
| 10 | `report_position_vts` | UNDERWAY → COASTAL_WATERS | ADMISSIBLE |
| 11 | `sound_general_alarm` | COASTAL_WATERS → EMERGENCY | ADMISSIBLE |
| **12** | **`order_abandon_ship`** | **EMERGENCY → None** | **INADMISSIBLE [ORDER]** |

`M6_Evacuation` is NOT in `EMERGENCY.flows`. Permitted from MUSTER and MAYDAY. The MUSTER step was skipped.

- Gate timestamp: ~22:48 CET (~1326491280)
- First evacuation fatalities: ~23:10 CET (~1326492600)
- **Lead time: 22 minutes before first deaths**

---

## 3. Structural Findings

### BURST_CADENCE — Causal violation

The unauthorized inchino maneuver involved three rapid course alterations within 60 seconds. In the compiler model, each `alter_course` (M2_Maneuvering) from MONITORING(w=2) expands to UNDERWAY(w=3) (+1). Three expansions within the BURST window fires BURST_CADENCE.

This fires **before the physical point of no return** (the rock strike at 21:44). The structural signature of unauthorized oscillatory maneuvering is detectable from the course-change sequence alone, 10 minutes before impact, without AIS data, without radar readings, without nautical charts.

### ORDER — Response violation

Under SOLAS Chapter III Regulation 29, vessel abandonment must be preceded by a formal muster (passengers and crew ordered to muster stations). In the compiler model: EMERGENCY → M4_InternalEmergency → MUSTER → M6_Evacuation → ABANDON. Schettino attempted to issue the abandon ship order from EMERGENCY, skipping MUSTER.

The gate fires because `M6_Evacuation` is absent from `EMERGENCY.flows`. The compiler encodes SOLAS Ch. III Reg. 29 directly — not as an extra rule, but as a structural property of the flow graph.

This fires **22 minutes before the first evacuation deaths**. The chaos in the evacuation — passengers without formal muster orders, lifeboats launched out of sequence — is downstream of this structural skip.

---

## 4. Vocabulary Mapping Notes

| Action | Class | Mapping type |
|--------|-------|-------------|
| `alter_course` | M2_Maneuvering | Direct |
| `monitor_ecdis` / `verify_course` | M1_Navigation | Direct |
| `report_position_vts` | M3_Communications | Direct |
| `sound_general_alarm` | M4_InternalEmergency | Direct |
| `order_abandon_ship` | M6_Evacuation | Direct |

All mappings are direct 1:1. No structural analog reasoning required. This is the cleanest vocabulary mapping of the four reconstructions.

---

## 5. Two Invariants, One Kernel

The BURST_CADENCE and ORDER violations are detected by the same gate kernel (`domain_compiler_v0_9.py`) with zero configuration change between the two findings. No parameters were tuned for the maritime domain. No thresholds were adjusted between the causal violation and the response violation.

This is a significant finding: the gate detects both the **cause** (unauthorized maneuvering leading to collision) and the **response failure** (skipped muster before abandon ship) in the same incident, from sequence alone, without any domain-specific tuning between the two invariants.

---

## 6. Comparison with Other Reconstructions

| Reconstruction | Invariant(s) | Mapping type | Lead time | Scope |
|---------------|-------------|-------------|-----------|-------|
| Tenerife 1977 | ORDER | Direct | 36 seconds | Causal |
| Gelsinger 1999 | ORDER | Structural analog | 4 days | Causal |
| **Costa Concordia 2012** | **BURST + ORDER** | **Direct** | **10 min / 22 min** | **Causal + Response** |
| Bromiley 2005 | BURST_CADENCE | Direct | ~4 min (est.) | Causal |

Costa Concordia is the only reconstruction with two gate-fire events, demonstrating that the gate can detect both the causal structural violation and the response-phase violation in the same incident timeline.

---

## 7. Prospective Detection Claims — Precise Formulation

**BURST_CADENCE:**
> The gate fires 10 minutes before the rock strike, from the maneuvering sequence alone, without AIS data, without navigation sensors, without radar coverage. The three unauthorized course alterations within the 60-second burst window constitute the structural signature of the inchino deviation.

**ORDER:**
> The gate fires 22 minutes before the first evacuation fatalities, from the emergency response sequence alone. The MUSTER step required by SOLAS Chapter III Regulation 29 was structurally absent. The compiler encodes this as a flow graph property: M6_Evacuation is not in EMERGENCY.flows.

**Do not use:** "before any human could detect the violation" — the inchino deviation was visible on bridge instruments; the missing muster order was detectable by any crew member. The gate's value is formalization and prospective firing, not superior detection.

---

## 8. Files

| File | Description |
|------|-------------|
| `concordia_reconstruction.py` | Reconstruction script — 12 events, two gate-fire points |
| `concordia_reconstruction_results.json` | Machine-readable gate output per event |
| `maritime_compiler_v0_1.py` | Maritime compiler (confirmed 10/10) |
| `2026_05_20_Concordia_Inverse_Reconstruction_Note.md` | This document |

---

*Reconstruction performed: May 20, 2026. Gate kernel: domain_compiler_v0_9.py (v0.9). Maritime compiler: v0.1. Source authority: Italian Ministry DIGEMA Report (2013); Grosseto verdict (2015); Coast Guard transcripts.*
