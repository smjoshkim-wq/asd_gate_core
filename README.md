# asd_gate_core

**ASD Gate Kernel and Domain Compiler Suite**

EchoDriver Stewardship Corp. — Structural Admissibility Research

---

## What This Is

This repository contains the gate kernel, domain compilers, combinatorial test harnesses,
and inverse incident reconstruction scripts for the Applied Structural Admissibility System
(ASD) gate — a deterministic, rule-based enforcement engine that evaluates whether an action
is structurally admissible at the moment it occurs, before any irreversible consequence.

The gate implements five structural invariants derived from the Branch Admissibility System
(BAS) theoretical framework:

| Invariant | What It Catches |
|-----------|----------------|
| **ORDER** | Action taken before required preconditions are satisfied |
| **JURISDICTION** | Action taken by an actor whose role excludes it |
| **BURST\_CADENCE** | Rapid trajectory instability — three or more width-expanding state transitions within the burst window |
| **EXIT** | Action taken after session termination or by an actor entering a workflow they do not own |
| **HYSTERESIS** | Recovery path lock — post-violation session state renders remediation destination unvisited and path untraversed |

The gate kernel (`gate/domain_compiler_v0_9.py`) has been **unchanged since May 15, 2026**
across all 26 domain instantiations.

---

## The Principal Claim

> The same five structural invariants that describe authority violations in cybersecurity
> also describe authority violations in aviation, pharmaceutical development, maritime
> operations, clinical medicine, nuclear operations, emergency management, legal proceedings,
> financial services, construction, supply chain management, petroleum operations, rail
> operations, military operations, chemical/industrial process, election administration,
> academic publishing, insurance claims processing, court records, network infrastructure,
> collaborative editing, and agentic AI systems.

Every new domain compiler is a **falsification attempt**. Every passing combinatorial run
is a failed falsification. The cross-substrate claim strengthens with each failed attempt.

---

## Confirmed Results (as of May 22, 2026)

- **26 substrates confirmed** — 338/338 combinatorial tests passing
- **29 inverse incident reconstructions** against primary-source documentary records
- **15 near-miss reconstructions** (ASRS series — outcome-independent detection confirmed)
- **0/109 false positives** across 30 clean traversal passes
- **3 named cross-incident patterns** — 24 confirmed instances across independent substrates and decades
- **1 confirmed sub-pattern** — Oversight Disconnection (3 instances, 3 domains)
- Gate kernel version 0.9 — unchanged throughout

---

## The 26 Substrates

| # | Domain | Compiler | Real Data |
|---|--------|----------|-----------|
| 1 | Cyber / LotL Detection | `gate/domain_compiler_v0_9.py` | ADFA-LD, Mordor, CloudTrail |
| 2 | Agentic AI (tool-call layer) | `compilers/agentic_compiler_v0_1.py` | Synthetic |
| 3 | Organizational Workflow | `compilers/org_workflow_compiler_v0_1.py` | Synthetic |
| 4 | Aviation | `compilers/aviation_compiler_v0_1.py` | Synthetic |
| 5 | Financial Services | `compilers/financial_compiler_v0_1.py`* | Synthetic |
| 6 | GitHub (VCS / code review) | `compilers/github_compiler_v0_1.py`* | Live GitHub API |
| 7 | Clinical Medicine | `compilers/clinical_compiler_v0_1.py`* | Synthetic |
| 8 | Nuclear Operations | `compilers/nuclear_compiler_v0_1.py` | Synthetic |
| 9 | FEMA ICS | `compilers/fema_compiler_v0_1.py` | Synthetic |
| 10 | Maritime | `compilers/maritime_compiler_v0_1.py` | Synthetic |
| 11 | Legal Proceedings | `compilers/legal_compiler_v0_1.py` | Synthetic |
| 12 | Pharmaceutical Development | `compilers/pharma_compiler_v0_1.py` | Synthetic |
| 13 | Construction | `compilers/construction_compiler_v0_1.py` | Synthetic |
| 14 | Supply Chain | `compilers/supply_chain_compiler_v0_1.py` | Synthetic |
| 15 | Petroleum Operations | `compilers/petroleum_compiler_v0_1.py` | Synthetic |
| 16 | Cyber — Incident Response (human layer) | `compilers/cyber_ir_compiler_v0_1.py` | Synthetic |
| 17 | Rail Operations | `compilers/rail_compiler_v0_1.py` | Synthetic |
| 18 | Military Operations | `compilers/military_compiler_v0_1.py` | Synthetic |
| 19 | Chemical / Industrial Process | `compilers/chem_compiler_v0_1.py` | Synthetic |
| 20 | Election Administration | `compilers/election_compiler_v0_1.py` | Synthetic |
| 21 | Academic Publishing | `compilers/pub_compiler_v0_1.py` | Synthetic |
| 22 | Insurance Claims | `compilers/insurance_compiler_v0_1.py` | Synthetic |
| 23 | PACER Court Records | `compilers/pacer_compiler_v0_1.py` | Synthetic |
| 24 | Network Infrastructure (UNSW-NB15) | `compilers/net_compiler_v0_1.py` | UNSW-NB15 available |
| 25 | Wikipedia Edit Layer | `compilers/wiki_compiler_v0_1.py` | Wikipedia API available |
| 26 | OpenStreetMap Changesets | `compilers/osm_compiler_v0_1.py` | OSM changeset feed available |

\* Financial, GitHub, and Clinical compilers will be added in the next push.
Harnesses for all three are included in `harnesses/`.

**Harness note:** Substrates 1–15 use 10-assertion harnesses (A01–A04, B01–B03, C01–C03).
Substrates 16–26 use 13-assertion harnesses with decomposed C-block sub-assertions. All pass.

**Note on `emergency_response_compiler_v0_1.py`:** This is a precursor file superseded by
`fema_compiler_v0_1.py` (substrate 9, confirmed). Included for reference only.

---

## Inverse Incident Reconstructions

### Primary Reconstructions (29 artifacts)

Single-substrate and multi-substrate reconstructions against primary-source documentary
records, gate kernel unchanged throughout:

| Incident | Domain(s) | Invariant(s) | Lead Time | Precision | Mapping |
|----------|-----------|-------------|-----------|-----------|---------|
| Tenerife (1977) | Aviation | ORDER | 36 sec | CVR-exact | Direct 1:1 |
| Gelsinger (1999) | Pharma | ORDER | 4 days | Day-level | Structural analog |
| Concordia (2012) | Maritime | BURST + ORDER | 10 / 22 min | Court-record | Direct 1:1 |
| Bromiley (2005) | Clinical | BURST\_CADENCE | ~4 min | Estimated | Direct 1:1 |
| TMI (1979) | Nuclear | ORDER + HYSTERESIS† | 27 min / 110 min | Day-level | Direct 1:1 |
| Deepwater Horizon (2010) | Petroleum + Maritime + FEMA | ORDER + BURST + EXIT | Multi-layer | Day-level | Direct 1:1 |
| Challenger (1986) | Org + Nuclear + Aviation | EXIT + JURISDICTION + ORDER | Days | Day-level | Structural analog |
| Therac-25 (1985–87) | AI-STP + Org + Nuclear | BURST + ORDER + EXIT | Per-incident | Court-record | Direct 1:1 |
| Fukushima (2011) | Nuclear + Org + FEMA | EXIT (three layers) | Hours | Day-level | Structural analog |
| Bhopal (1984) | Construction + Org + FEMA | ORDER + EXIT + EXIT | Months | Day-level | Structural analog |
| 2008 Financial Crisis | Financial + Org + Construction | ORDER + EXIT + ORDER | Months–years | Day-level | Structural analog |

† TMI HYSTERESIS finding: after the initial ORDER violation, the correct remediation
sequence fires INADMISSIBLE — HYSTERESIS locks the recovery path. This is the first
instance in the corpus where HYSTERESIS fires on a recovery attempt rather than a
forward violation, structurally modeling the documented TMI operator disorientation.

The remaining 18 reconstruction artifacts comprise named pattern scan instances
(Mason, DEFICIENCY\_NOTED, AC6\_PublicComm) documented below.

### Near-Miss Series (15 artifacts — outcome-independent detection)

Fifteen aviation near-miss incidents reconstructed against ASRS CALLBACK publications,
NTSB safety alerts, ICAO runway safety documentation, and FAA hotline reports.
Each incident involved a runway incursion or sequence violation that was interrupted
before collision — none involved a fatality.

**Result: 15/15 INADMISSIBLE. Zero false negatives.**

| Invariant | Instances | Lead Time Range |
|-----------|-----------|----------------|
| ORDER | 10 | 8–35 sec |
| JURISDICTION | 3 | 25–30 sec |
| BURST\_CADENCE | 2 | 8–14 sec |

This series establishes outcome-independent detection: the gate fires on the structural
geometry of the violation regardless of whether the historical consequence occurred.
See `reconstructions/asrs_near_miss_run.py` and `2026_05_21_ASRS_NearMiss_Note_v1_0.md`.

---

## Named Cross-Incident Patterns

Three structural patterns and one confirmed sub-pattern, spanning independent substrates
and decades. These are not domain findings — they are substrate-invariant geometric
signatures of authority violation.

### Pattern 1 — Mason (10 instances, 8 domains, 4 decades)

An analyst-role actor establishes workflow ownership by executing the full review pipeline.
An authority-role actor then enters the same workflow and calls an analyst-only action.

- **Invariant sequence:** EXIT (actor pivot into owned workflow), then JURISDICTION (isolated)
- **Confirmation:** 10 instances, 8 domains, 1984–2023, zero deviations

| Instance | Domain | Incident | Year |
|----------|--------|----------|------|
| Mason #1 | Pharmaceutical | Gelsinger — Wilson/Penn IRB override | 1999 |
| Mason #2 | Pharmaceutical | Vioxx — Bombardier/Merck safety override | 2000 |
| Mason #3 | Cyber IR | Equifax — security team recommendation override | 2017 |
| Mason #4 | Rail | Lac-Mégantic — TC audit override | 2013 |
| Mason #5 | Pharmaceutical | Theranos — lab director override | 2013 |
| Mason #6 | Org Workflow | Gelsinger — protocol review override (org layer) | 1999 |
| Mason #7 | Org Workflow | Vioxx — safety data override (org layer) | 2000 |
| Mason #8 | Org Workflow | Equifax — patch approval override (org layer) | 2017 |
| Mason #9 | Org Workflow | Lac-Mégantic — crew protocol override (org layer) | 2013 |
| Mason #10 | Financial | 2008 Crisis — cross-firm CDO approval override | 2005–07 |

### Pattern 2 — DEFICIENCY\_NOTED (9 instances, 7 domains)

An actor proceeds with a forward action in a state where a required prior authorization
step was skipped or a known deficiency was documented but not resolved.

- **Invariant sequence:** ORDER (step skipped) or JURISDICTION (known-gap override)
- **Confirmation:** 9 instances, 7 domains, zero deviations

| Instance | Domain | Incident | Year | Deficiency Document |
|----------|--------|----------|------|---------------------|
| DN #1 | Construction | Algo Centre Mall | 2012 | Structural inspection report |
| DN #2 | Construction | Champlain Towers South | 2021 | 2018 engineering report |
| DN #3 | Chemical | Bhopal | 1984 | UCIL engineering findings |
| DN #4 | Financial | Lehman Repo 105 | 2008 | Matthew Lee letter (May 16) |
| DN #5 | Cyber IR | Equifax CVE | 2017 | CVE-2017-5638 (March 7) |
| DN #6 | Chemical | Texas City BP | 2005 | Telos Group Assessment (Sep 2004) |
| DN #7 | Nuclear | Three Mile Island | 1979 | B&W memo (November 1977) |
| DN #8 | Pharma | Vioxx APPROVe | 2004 | VIGOR results (February 2000) |
| DN #9 | Rail | Lac-Mégantic | 2013 | TC SMP Audit (2012) |

**Sub-pattern — Oversight Disconnection (3 instances, 3 domains):** In three of nine
DEFICIENCY\_NOTED instances, the actor holding oversight authority for the documented
deficiency was structurally separated from the operational response chain in the permitted
flow graph — Equifax (Cyber IR, 2017), Texas City BP (Chemical, 2005), Lac-Mégantic
(Rail, 2013). The gate fires ORDER on the operational actor; the disconnection is the
structural explanation for why the violation persists.

### Pattern 3 — AC6\_PublicComm (5 instances, FEMA ICS compiler)

A non-IC actor in an incident command structure attempts to execute an action belonging
exclusively to the Incident Commander communications pipeline.

- **Invariant sequence:** EXIT (non-IC entering IC-owned workflow), then JURISDICTION (isolated)
- **Confirmation:** 5 instances, all FEMA ICS compiler, zero deviations

| Instance | Incident | Year | IC | Non-IC |
|----------|----------|------|----|--------|
| AC6 #1 | Deepwater Horizon | 2010 | USCG / MMS IC | BP communications |
| AC6 #2 | Fukushima | 2011 | Japanese government IC | TEPCO communications |
| AC6 #3 | Bhopal | 1984 | Local emergency IC | UCC/UCIL communications |
| AC6 #4 | Costa Concordia | 2012 | Coast Guard MRCC (De Falco) | Schettino (vessel master) |
| AC6 #5 | Three Mile Island | 1979 | NRC / Governor Thornburgh | Metropolitan Edison PR |

---

## False Positive Pressure Test

```bash
python reconstructions/false_positive_pressure_test.py
```

Expected: **0 INADMISSIBLE across 109 events** (30 clean traversal passes, 14 compilers).

Key architectural finding: BURST\_CADENCE requires **width-expanding state transitions**,
not rapid-fire events. An actor executing repeated legitimate actions within a single state
cannot false-trigger it — no state width expansion occurs. Only three or more
width-expanding transitions within the burst window triggers the invariant.

---

## Repository Structure

```
asd_gate_core/
│
├── gate/                              # Gate kernel and real-data ingesters
│   ├── domain_compiler_v0_9.py        # The gate kernel — do not modify
│   ├── adfa_ld_ingester.py
│   ├── mordor_ingester.py
│   └── v0_9_cloudtrail_reality_check.py
│
├── compilers/                         # 23 of 26 domain compilers (mapping layer only)
│   └── [financial, github, clinical adding in next push]
│
├── harnesses/                         # Combinatorial test harnesses — one per compiler
│   └── [27 harness files — all 26 domains + v0.9 hysteresis harness]
│
├── reconstructions/                   # Inverse incident reconstructions + benchmarks
│   ├── [primary reconstruction scripts + results JSON]
│   ├── [named pattern scan scripts + results JSON]
│   ├── [ASRS near-miss run + results]
│   ├── [FDA enforcement run + results]
│   ├── [false positive pressure test + results]
│   └── [reconstruction notes — .md per incident]
│
├── docs/
│   ├── PAPERS.md
│   └── methodology/
│       ├── Repeatable_Compiler_Methodology_v1_1.md
│       ├── Domain_Build_Package_Standard_v1_1.md
│       ├── 2026_05_19_Inverse_Incident_Methodology_v1_0.md
│       ├── 2026_05_19_Invariance_Library_v1_0.md
│       └── 2026_05_21_Master_Domain_Registry_v1_6.md
│
└── data/                              # Place real datasets here (not included)
```

---

## Running the Harnesses

```bash
# Single domain
python harnesses/test_harness_aviation_v0_1_combinatorial.py

# All harnesses
for f in harnesses/test_harness_*.py; do echo "=== $f ==="; python "$f"; done
```

Expected: all pass. Substrates 1–15 print 10/10; substrates 16–26 print 13/13.

---

## Running a Reconstruction

```bash
# Single-substrate
python reconstructions/tenerife_reconstruction.py
python reconstructions/gelsinger_reconstruction.py
python reconstructions/concordia_reconstruction.py
python reconstructions/bromiley_reconstruction.py
python reconstructions/tmi_reconstruction.py

# Near-miss series
python reconstructions/asrs_near_miss_run.py

# Multi-substrate (requires relevant compilers present)
python reconstructions/deepwater_petroleum_reconstruction.py
python reconstructions/deepwater_maritime_reconstruction.py
python reconstructions/deepwater_fema_reconstruction.py
```

---

## Architecture

```
Raw domain event
      │
      ▼
Domain Compiler         ← role registry, action class map,
(mapping layer)           permitted flow graph, state tracker
      │
      │  BAS_Metrics packet
      ▼
Gate Kernel             ← five invariants, TrajectoryTracker,
evaluate_gate()           burst window computation
      │
      ▼
{ "decision": "ADMISSIBLE" | "INADMISSIBLE" | "INDETERMINATE",
  "invariant": <label if INADMISSIBLE> }
```

The gate kernel is a fixed, versioned dependency. Domain compilers implement the
mapping layer only — no gate logic is re-implemented in any compiler.

---

## Open Research Problems

- **R1 Meta-Compiler** — multi-compiler interactions on a single event stream; Aviation cockpit + ATC is the natural first case; Deepwater multi-compiler reconstruction surfaced this empirically
- **R3 Invariance Library v1.0** — systematic documentation of invariant fire signatures per domain (draft available in `docs/methodology/`)
- **R4 Continuous monitoring** — deployment roadmap (not a current claim)
- **R5 Passive failure detection** — required actions that did not happen (Champlain Towers, Gelsinger S1 omissions); requires temporal gate extension; not in v0.1

---

## IP Notice

Relates to U.S. Provisional Patent Application No. 64/057,192 (filed May 4, 2026) and
U.S. Provisional Patent Application No. 64/071,955 (filed May 22, 2026). Code released
under MIT License. The MIT License does not convey any patent license.

---

## Theoretical Corpus

The BAS/ASD theoretical corpus (Papers 1–32) will be available on Zenodo.
See `docs/PAPERS.md` for status and DOIs once published.

---

*Gate kernel: v0.9 — unchanged since May 15, 2026*
*Substrates confirmed: 26 — 338/338 tests*
*Reconstructions: 29 primary + 15 ASRS near-miss series*
*Named patterns: Mason 10×, DEFICIENCY\_NOTED 9×, AC6\_PublicComm 5× — 24 total instances*
*Last updated: May 22, 2026*
