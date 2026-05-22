# Master Domain Registry
**Version:** 1.6
**Date:** May 21, 2026
**Status:** Living document — Tier 3 build wave complete (substrates 24–26); total now 26 substrates, 338/338 combinatorial tests
**Follows from:** Master Domain Registry v1.5 (May 21, 2026); Tier 3 build session (May 21, 2026)

**Version 1.6 changes:**

- Section 1 updated: substrates 24–26 confirmed (UNSW-NB15 Network Layer, Wikipedia Edit Layer, OpenStreetMap Changesets); total 26 substrates, 338/338 tests (26 × 13)
- Section 2 Tier 3 entries removed; remaining planned items (only #27 nuScenes AV physical layer) carried forward
- Notable: Tier 3 substrates are the first three with publicly-accessible empirical data sources (UNSW-NB15 download, Wikipedia API Special:Log, OSM changeset feed) — empirical validation can follow without further compiler work
- Notable: Wikipedia and OSM admin-tool BURST geometries map to substrate-specific named patterns — Wikipedia BURST is the structural analog of WP:3RR (three-revert-rule). The doctrine codifies the BURST invariant explicitly. This is the first substrate where the invariant has a named regulatory analog inside the domain's own doctrine.
- Notable: Wikipedia and OSM B01 clean paths require timestamp spacing (3 expansions: IDLE→MONITORING→REVIEWING→ACTIONABLE/MEDIATING) — same pattern as Military #18
- All 26 active substrates now confirmed; only #27 nuScenes (autonomous-vehicle physical layer) remains deferred

**Version 1.5 changes (retained):**

- Section 1 updated: substrates 20–23 confirmed; total 23 substrates, 299/299 tests
- Academic Publishing required mid-build flow patch — second instance after Military #18

**Version 1.4 changes (retained):**

- Section 1 updated: substrates 16–19 confirmed (Cyber IR, Rail, Military, Chemical/Industrial); total 19 substrates, 247/247 tests (19 × 13)
- Section 2 Tier 1 entries removed (now confirmed); Tier 2 promoted accordingly
- Notable: Military B01 required BURST-Safe timestamp spacing (three consecutive expansions on clean path); Chemical B01 confirmed BURST-safe without spacing

**Version 1.3 changes (retained):**

- Section 1 updated: Petroleum Operations added as substrate 15; total now 15 substrates, 150/150 combinatorial tests
- Section 2 restructured: build sequence reorganized into four tiers (Immediate / Strong / Dataset-Driven / Deferred) replacing unordered planned list; two new substrates added (Rail Operations #17; Chemical/Industrial Process #19); numbering of all planned substrates revised accordingly
- Section 5 updated: 10 total reconstructions now documented (4 single-substrate + 6 three-substrate); three named cross-incident patterns added; cross-domain finding updated
- Section 6 added: Meta-Compiler Architecture note capturing the architectural insight from the May 21 session
- Funding door summary updated to reflect new substrates

---

## Purpose

This registry is the foundry's queue. Every substrate identified as buildable under the Repeatable Compiler Methodology is logged here with its status, data sources, incident anchors, and funding relevance. The registry does not contain compiler designs — those live in their own Domain Build Packages. This document tells you what to build next and why.

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| ✓ Confirmed | Compiler built, harness run, confirmed on hardware |
| Planned — Tier 1 | Immediate build; clean doctrine, strong incident anchor, high strategic value |
| Planned — Tier 2 | Strong build; slightly more sourcing prep required |
| Planned — Tier 3 | Dataset-driven; real data available, incident-light |
| Deferred | Architecturally distinct; requires separate design decision before building |
| Open Research Problem | Structural question identified, no compiler design yet |

---

## Tier Definitions

| Tier | Meaning |
|------|---------|
| 1 | Legally codified — statute, regulation, zero ambiguity |
| 2 | Professionally standardized — industry standards, extensively documented |
| 3 | Operationally standardized — published doctrine, procedure manuals |

---

## Section 1 — Confirmed on Hardware

**Current total: 26 substrates, 338/338 combinatorial tests.**

| # | Domain | Tier | Compiler File | Incident Anchors | Tests | Confirmed |
|---|--------|------|---------------|-----------------|-------|-----------|
| 1 | Cyber — syscall layer | 1 | `domain_compiler_v0_9.py` | SolarWinds, Equifax (public post-mortems) | 10/10 | May 15, 2026 |
| 2 | Agentic — tool-call layer | 2 | `agentic_compiler_v0_1.py` | N/A | 10/10 | May 16, 2026 |
| 3 | Org workflow — human decision layer | 1 | `org_workflow_compiler_v0_1.py` | N/A | 10/10 | May 16, 2026 |
| 4 | GitHub — software dev workflow | 2 | `github_compiler_v0_1.py` | Log4Shell release sequence failure | 10/10 | May 20, 2026 |
| 5 | Aviation — crew operations | 1 | `aviation_compiler_v0_1.py` | Tenerife 1977 (ICAO report) | 10/10 | May 20, 2026 |
| 6 | Financial — structured products | 1 | `financial_compiler_v0_1.py` | 2008 Financial Crisis (FCIC report) | 10/10 | May 20, 2026 |
| 7 | Clinical — perioperative safety | 1 | `clinical_compiler_v0_1.py` | Bromiley 2005 (Harmer Report) | 10/10 | May 20, 2026 |
| 8 | Nuclear facility operations | 1 | `nuclear_compiler_v0_1.py` | TMI 1979, Fukushima 2011 | 10/10 | May 20, 2026 |
| 9 | Emergency response — FEMA ICS | 3 | `fema_compiler_v0_1.py` | Hurricane Katrina 2005 | 10/10 | May 20, 2026 |
| 10 | Maritime operations | 1 | `maritime_compiler_v0_1.py` | Costa Concordia 2012 | 10/10 | May 20, 2026 |
| 11 | Legal proceedings | 1 | `legal_compiler_v0_1.py` | Sineneng-Smith; Tate/Rodriguez; Abrahamsen | 10/10 | May 21, 2026 |
| 12 | Pharmaceutical — clinical trials | 1 | `pharma_compiler_v0_1.py` | Thalidomide; Vioxx; Gelsinger 1999 | 10/10 | May 21, 2026 |
| 13 | Construction / engineering approvals | 2 | `construction_compiler_v0_1.py` | L'Ambiance Plaza 1987; Algo Centre 2012; Champlain Towers 2021 | 10/10 | May 21, 2026 |
| 14 | Supply chain — custody transfer | 2 | `supply_chain_compiler_v0_1.py` | PPE Procurement 2020; Suez/Ever Given 2021; Hanjin 2016 | 10/10 | May 21, 2026 |
| 15 | Petroleum operations | 1 | `petroleum_compiler_v0_1.py` | Deepwater Horizon 2010 (30 CFR Part 250) | 10/10 | May 21, 2026 |
| 16 | Cyber — incident response (human layer) | 1 | `cyber_ir_compiler_v0_1.py` | Equifax 2017 breach response | 13/13 | May 21, 2026 |
| 17 | Rail operations | 1 | `rail_compiler_v0_1.py` | Lac-Mégantic 2013 (TSB R13D0054) | 13/13 | May 21, 2026 |
| 18 | Military — operational | 3 | `military_compiler_v0_1.py` | Tarnak Farm 2002 (CF BOI) | 13/13 | May 21, 2026 |
| 19 | Chemical / industrial process | 2 | `chem_compiler_v0_1.py` | Texas City 2005 (CSB 2005-04-I-TX) | 13/13 | May 21, 2026 |
| 20 | Election administration | 4 | `election_compiler_v0_1.py` | Florida 2000 (Bush v. Gore) | 13/13 | May 21, 2026 |
| 21 | Academic publishing | 4 | `pub_compiler_v0_1.py` | Hwang Woo-suk 2006 (Science retraction; SNU report) | 13/13 | May 21, 2026 |
| 22 | Insurance claims | 4 | `insurance_compiler_v0_1.py` | State Farm Katrina 2005 (MS AG; Broussard 523 F.3d 618) | 13/13 | May 21, 2026 |
| 23 | PACER court records | 4 | `pacer_compiler_v0_1.py` | Theranos 2018-2022 (US v. Holmes 3:18-cr-00258) | 13/13 | May 21, 2026 |
| 24 | UNSW-NB15 — network layer | 5 | `net_compiler_v0_1.py` | UNSW-NB15 dataset (Moustafa & Slay 2015) | 13/13 | May 21, 2026 |
| 25 | Wikipedia — edit layer | 5 | `wiki_compiler_v0_1.py` | Essjay controversy 2007 (public WP record) | 13/13 | May 21, 2026 |
| 26 | OpenStreetMap — changesets | 5 | `osm_compiler_v0_1.py` | MAPS.ME mass-edit dispute 2018 (DWG record) | 13/13 | May 21, 2026 |

**Real data substrates (confirmed):** Cyber syscall (CloudTrail, Mordor, ADFA-LD), GitHub (live Events API). All others synthetic against public regulatory doctrine.

**Harness note:** Substrates 1–15 run 10/10 (A01–A04 + B01–B03 + C01–C03 = 10 assertions). Substrates 16–19 run 13/13 (C01–C03 decomposed into sub-assertions C01a/b, C02a/b, C03a/b). All pass.

**Output key note:** All compilers return `"decision"` as primary key. Wave-2 compiler-side one-line patch ("verdict" → "decision") pending on hardware for aviation, financial, github, clinical. Harnesses already patched.

---

## Section 2 — Planned Build Sequence

All planned substrates use the reconstruction-driven vocabulary discovery approach: select a well-documented incident, run the reconstruction, let the incident surface the vocabulary, populate the registry entry, run the harness. Vocabulary acquisition is the intellectual work. Compiler instantiation follows mechanically.

### Tier 1 — Build Immediately

Clean doctrine, strong incident anchor, high strategic value. Each build is one focused session.

| # | Domain | Tier | Incident Anchor | Primary Source | Funding Door | Notes |
|---|--------|------|----------------|----------------|--------------|-------|
| 16 | Cyber — incident response (human layer) | 1 | Equifax 2017 breach response | SEC filing; congressional testimony record | IDEaS, NSERC | Distinct from syscall compiler (#1) — same incident, two compilers, different structural layers. New evidentiary claim: same event fires on two substrates simultaneously. |
| 17 | Rail operations | 1 | Lac-Mégantic 2013 | TSB Railway Investigation Report R13D0054 (2014) | Transport Canada, NSERC | **New substrate — not in v1.2.** TSB report is among the most detailed transportation safety records publicly available. Canadian anchor. ORDER/JURISDICTION cascade. Transport Canada funding door. |
| 18 | Military — operational | 3 | Tarnak Farm 2002 | Canadian Forces Board of Inquiry (fully public) | IDEaS / DND | Tarnak Farm BOI is fully public — military compiler buildable without DND data access. Closes the IDEaS objection surface ("does this work in a military context?") immediately. DND data access is a deployment question, not a build question. |
| 19 | Chemical / industrial process | 2 | Texas City 2005 BP refinery | CSB Investigation Report No. 2005-04-I-TX (2007) | NSERC, NRCan | **New substrate — not in v1.2.** Fills the gap exposed by Bhopal reconstruction — Bhopal was reconstructed on existing compilers but no dedicated chemical process substrate exists. CSB report is the gold standard of industrial post-mortems. |

### Tier 2 — Strong; Slightly More Sourcing Prep

| # | Domain | Tier | Incident Anchor | Primary Source | Funding Door | Notes |
|---|--------|------|----------------|----------------|--------------|-------|
| 20 | Election administration | 1 | Florida 2000 recount | Congressional record; Florida Supreme Court filings | SSHRC, Public Safety Canada | Chain of custody failures across canvassers, supervisors, certifiers exhaustively documented. Politically sensitive but structurally clean — procedural rules are unambiguous. |
| 21 | Academic publishing | 2 | Hwang Woo-suk 2004–05 | Science retraction notice; Seoul National University investigation (2006) | SSHRC | Peer review role violations fully documented. Retraction Watch provides systematic real data as follow-on. |
| 22 | Insurance claims | 2 | State Farm — Hurricane Katrina bad faith | Public litigation record; Mississippi AG filings (2006–08) | SSHRC, Finance Canada | Role separation failures in claims handling documented through court records. Intake, assessment, adjudication sequences. |
| 23 | Court records — documentary layer | 1 | Theranos criminal proceedings | PACER public record; SEC complaint (2018); DOJ indictment (2018) | SSHRC | Filing sequence and procedural role violations extensively documented. Distinct from legal proceedings compiler (#11) — this is the documentary record layer, not the courtroom sequence. |

### Tier 3 — Dataset-Driven; Real Data Available, Incident-Light

| # | Domain | Tier | Data Source | Incident Anchors | Funding Door | Notes |
|---|--------|------|------------|-----------------|--------------|-------|
| 24 | UNSW-NB15 / CIC-IDS — network layer | 1 | Free download (UNSW-NB15; CIC-IDS-2017) | N/A — attack taxonomy in dataset | NSERC, IDEaS | No single incident anchor. Compiler built against attack taxonomy; dataset is the evidence base. Extends syscall compiler into network traffic layer. |
| 25 | Wikipedia edit logs | 2 | Full history downloadable, free | Qworty sockpuppet case (documented) | NSERC, SSHRC | Qworty is the cleanest documented incident — role separation between editors, reviewers, admins with confirmed JURISDICTION violation pattern. Real data freely downloadable. |
| 26 | OpenStreetMap changesets | 2 | Full history downloadable, free | N/A | NSERC | Dataset-driven. Contributor roles, structured action types. Real data, free, no credentialing. Build after Wikipedia (#25) — structural grammar is similar. |

### Deferred — Architecturally Distinct

| # | Domain | Tier | Data Source | Notes |
|---|--------|------|------------|-------|
| 27 | nuScenes — physical / AV layer | 2 | nuScenes mini split ~4GB, free | Uber Tempe 2018 (NTSB report) is the best incident anchor. Substrate is architecturally different — sensor data, not authority grammar. The reconstruction approach requires a separate design decision before building. Not blocking any other substrate. |

---

## Section 3 — Open Research Problems

Structural questions identified from the project. No compiler design yet. Named here for roadmap visibility.

| # | Problem | Description | Status | Potential Paper |
|---|---------|-------------|--------|-----------------|
| R1 | Meta-Compiler / multi-compiler interactions | What are the structural properties of handoff points between two independently valid compilers? Aviation cockpit + ATC is the natural first candidate. Requires both domain compilers confirmed. See also Section 6 — Meta-Compiler Architecture. | Open | Yes — standalone paper |
| R2 | Near-miss detection | Aviation ASRS near-miss database. Gate should fire on near-misses the same way it fires on accidents — structural violation present either way. No body count required. Empirical closer for the prospective detection claim. | Open | Methodology note at minimum |
| R3 | Invariance Library | Cumulative documented failure signatures per invariant across all substrates. ORDER failures look structurally different from JURISDICTION failures. HYSTERESIS has a unique dependency signature. **Invariance Library v1.0 drafted May 19, 2026. Reconstructions in Section 5 extend this empirically.** | Active — v1.0 drafted | Yes — standalone reference |
| R4 | Continuous structural monitoring | Once a compiler exists for a substrate, run it against live data streams. Static validation work done now becomes foundation for real-time structural monitoring in deployment. | Open | Deployment roadmap note — not a current claim |
| R5 | Passive failure detection | Gate fires on active violations. It does not detect required actions that did not happen (Champlain Towers, Fukushima containment venting, Gelsinger S1 omissions). Architecturally distinct — requires temporal gate extension. Known scope constraint, not a weakness; must be stated in all papers. | Open | Methodology extension paper |

---

## Section 4 — Inverse Incident Reconstructions

**Purpose:** Cross-substrate empirical validation against historically documented incidents. Distinct from combinatorial harness work — reconstructions use primary source event sequences against real incident timelines. They test whether the gate fires before the recorded irreversible consequence, not merely whether synthetic adversarial inputs produce the expected invariant.

**Current status:** 10 total reconstructions confirmed. 4 single-substrate + 6 three-substrate. Gate kernel `domain_compiler_v0_9.py` unchanged throughout. No inter-compiler tuning between any reconstruction.

---

### Single-Substrate Reconstructions (4)

| # | Incident | Date | Compiler | Invariant(s) | Mapping Type | Lead Time | Primary Source |
|---|---------|------|---------|-------------|-------------|-----------|----------------|
| 1 | Tenerife Airport Disaster | 1977-03-27 | Aviation v0.1 | ORDER | Direct 1:1 | 36 sec before collision | ICAO Digest; Spanish Ministry of Transport (1978); NTSB-AAR-78-7 |
| 2 | Jesse Gelsinger gene therapy death | 1999-09-17 | Pharma v0.1 | ORDER | Structural analog | 4 days before infusion; 8 days before death | FDA Warning Letter to Wilson (Feb 8, 2002); NIH OBA Special Investigation (1999–2000) |
| 3 | Costa Concordia grounding | 2012-01-13 | Maritime v0.1 | BURST_CADENCE + ORDER | Direct 1:1 | 10 min before rock strike; 22 min before first deaths | Italian Ministry DIGEMA Report (2013); Grosseto Criminal Court verdict (Feb 2015) |
| 4 | Elaine Bromiley perioperative death | 2005-03-29 | Clinical v0.1 | BURST_CADENCE | Direct 1:1 | ~4 min before critical hypoxia (estimated) | Harmer M., Independent Report, CHFG (2005) |

---

### Three-Substrate Reconstructions (6)

Each three-substrate reconstruction treats the incident as a falsification attempt against the substrate-invariance composition claim. All six failed to falsify the claim.

| # | Incident | Substrates | Total Violations | Key Finding | Note Files |
|---|---------|-----------|-----------------|-------------|------------|
| 5 | Deepwater Horizon 2010 | Petroleum, Maritime, FEMA ICS | 7 | First multi-invariant reconstruction (ORDER + JURISDICTION + BURST_CADENCE on petroleum alone). First project demonstration of simultaneous multi-substrate fire on a single event. | `2026_05_21_Deepwater_Three_Substrate_Reconstruction_Note.md` |
| 6 | Challenger 1986 | Org Workflow, Nuclear, Aviation | 4 + 2 principled non-fires | First project demonstration of substrate-specificity as a positive finding — aviation correctly does not fire because the structural failure was upstream of the launch. | `2026_05_21_Challenger_Three_Substrate_Reconstruction_Note.md` |
| 7 | Therac-25 1985–87 | AI-STP, Org Workflow, Nuclear | 12 (cross-incident stability across 6 incidents) | First demonstration of cross-incident stability — same gate fires identically across 6 independent incidents from the same failure pattern. Nuclear correctly does not fire (substrate-specificity, second form). | `2026_05_21_Therac_Three_Substrate_Reconstruction_Note.md` |
| 8 | Fukushima Daiichi 2011 | Nuclear, Org Workflow, FEMA ICS | 3 + external-trigger robustness demonstrated | First external-trigger reconstruction — gate fires on externally-precipitated cascade, not only internally-precipitated failures. Longest lead time in corpus: 2.5 years (org workflow). | `2026_05_21_Fukushima_Three_Substrate_Reconstruction_Note.md` |
| 9 | Bhopal 1984 | Org Workflow, Construction, FEMA ICS | 3 | Third Mason pattern instance (org workflow). Third DEFICIENCY_NOTED instance (construction). Third AC6_PublicComm instance (FEMA ICS). All three named patterns instantiated in a single incident. | `2026_05_21_Bhopal_Three_Substrate_Reconstruction_Note.md` |
| 10 | 2008 Financial Crisis | Financial, Org Workflow, Construction | 3 | Fifth Mason pattern instance (org workflow). Fourth DEFICIENCY_NOTED instance (construction, Lehman Repo 105). Companion cross-firm reconstruction (Lehman/AIG/Citi, org workflow only) confirms cross-firm pattern stability. | `2026_05_21_2008_Three_Substrate_Reconstruction_Note.md` |

---

### Named Cross-Incident Patterns (3)

Patterns with three or more independent instances across distinct incidents. Same compiler, same invariant, same geometry, no compiler-side modifications between instances.

**Mason pattern — 5 instances**

Org workflow compiler, EXIT invariant. Analyst layer produces finding; approver layer overrides with management authority. Gate fires at the moment the override action is called from a state that requires the analyst's output to gate it.

| Instance | Year | Analyst | Approver | Domain |
|----------|------|---------|----------|--------|
| Bhopal | 1982 | UCIL Engineering | UCC HQ parent | Chemical industrial |
| Challenger | 1986 | Mason / Boisjoly | MTI management | Aerospace |
| Therac-25 | 1987 | Tyler / users | AECL response team | Medical software |
| Fukushima | 2008 | Tsunami Risk Group | TEPCO NPD | Nuclear |
| 2008 Crisis | 2005–07 | Gorton/Park quant team | Cassano (AIGFP) | Financial |

**DEFICIENCY_NOTED pattern — 4 instances**

Construction compiler, ORDER invariant. Commitment action called from DEFICIENCY_NOTED state before the required remediation gate is cleared.

| Instance | Year | Geometry | Domain |
|----------|------|---------|--------|
| Algo Centre Mall | 2012 | H1 stall → ORDER | Building structural |
| Champlain Towers South | 2021 | H1 stall → ORDER | Building structural |
| Bhopal | 1982–84 | A3_Commitment from DEFICIENCY_NOTED | Chemical industrial |
| Lehman Repo 105 | 2008 | A3_Commitment from DEFICIENCY_NOTED | Financial accounting |

**FEMA AC6_PublicComm actor-pivot pattern — 3 instances**

FEMA ICS compiler, EXIT invariant. Non-IC actor calls into AC6_PublicComm action class, displacing the incident commander's communications authority.

| Instance | Year | IC Actor Displaced | Domain |
|----------|------|-------------------|--------|
| Deepwater Horizon | 2010 | BP comms vs. Coast Guard IC | Industrial emergency |
| Fukushima | 2011 | PM Kan Office vs. LNERH IC | Nuclear emergency |
| Bhopal | 1984 | Security guard vs. IC Mukund | Industrial emergency |

---

### Cross-Domain Structural Finding (Updated)

Ten incidents. Ten or more substrate-instances. Incidents spanning 1977–2021. Four decades. Five engineering domains plus financial, legal, software, and governance domains. One gate kernel (`domain_compiler_v0_9.py`). No parameters changed between substrates. No inter-domain tuning.

Every single-substrate reconstruction fires before the recorded irreversible physical consequence. Every three-substrate reconstruction demonstrates that the same invariant logic applies across structurally distinct authority grammars operating within a single event.

Three named cross-incident patterns are each instantiated three or more times across completely independent incidents, with the same compiler, same invariant, and no compiler-side modifications. This constitutes cross-incident structural stability.

Four catastrophe shapes have now been reconstructed: operational sequence failure (Deepwater), decision pipeline failure (Challenger), recurring software failure (Therac-25), and externally-precipitated cascade (Fukushima). The framework handles all four.

---

### Reconstruction Type Definitions

| Type | Definition | Instances |
|------|-----------|-----------|
| Direct 1:1 | Primary source action maps without interpretive step onto a compiler action class; state at fire time maps without interpretive step onto the compiler state | Tenerife, Costa Concordia, Bromiley, and all three-substrate reconstructions |
| Structural analog | Compiler's state geometry captures the shape of the violation; action-to-class and state mapping involves an interpretive step that must be stated and defended | Gelsinger |

Mapping type must be stated explicitly in any paper. Both types are valid.

---

### Lead Time Precision Classes

| Precision | Basis | Instances |
|-----------|-------|-----------|
| CVR/ATC-exact (seconds) | Second-level timestamps from cockpit voice recorder and ATC transcript | Tenerife (36 sec) |
| Court-record (minutes) | Court record CET timestamps from investigation | Costa Concordia (10 min, 22 min) |
| Day-level | FDA/NIH records, day-level precision | Gelsinger (4 days) |
| Year-level | Management record, board minutes | Fukushima org workflow (2.5 years) |
| Estimated (minutes) | Narrative account reconstruction; source does not record second-level times | Bromiley (~4 min) |

Lead time precision class must be stated in any paper. The structural claim holds at all precision levels.

---

### Passive Failure Boundary (R5)

The gate fires on active violations. Absence-of-action detection (Gelsinger S1 omissions, Fukushima containment venting, Champlain Towers remediation non-performance) requires a temporal gate extension (R5 in Section 3). This boundary applies to all reconstructions and must be stated in papers as a known scope constraint, not a weakness.

---

## Section 5 — Meta-Compiler Architecture

**Insight recorded:** May 21, 2026. Source: session analysis of multi-substrate reconstruction results.

**The current architecture is already one compiler.** `domain_compiler_v0_9.py` is the gate kernel. Every substrate compiler is a vocabulary wrapper around the same kernel. The fifteen Python files are fifteen instantiations of the same structure with different lexicons, not fifteen independent compilers.

**Three things actually change between substrates:**

- **Vocabulary:** Actor taxonomy, action class map, permitted flow graph. These are substrate-specific and sourced from doctrine.
- **Invariant detection parameters:** Window width and threshold count are calibrated per substrate. BURST_CADENCE fires at 60 seconds in cyber (lateral movement), ~4 minutes in clinical (fixation loop), longer in financial (approval pipeline). The invariant definition does not change. The clock is substrate-specific.
- **State space topology:** The shape of the permitted flow graph differs — linear pipeline, nested retry loop, parallel authority tracks, branching decision tree. The topology biases which invariants are geometrically reachable in a given substrate. This is a finding, not a limitation.

**Meta-compiler implication:** The fifteen individual compiler files should eventually be replaced by one file and a vocabulary registry. Each substrate is a named configuration block. The gate kernel runs against each block. This is the architecturally correct representation of what the system is.

**Multi-substrate auto-identification:** In a meta-compiler architecture, substrate selection can shift from researcher pre-selection to computed output. Feed a raw event stream, run against all vocabulary blocks simultaneously, get back which substrates fired. The Deepwater Horizon multi-substrate result — petroleum fires ORDER, maritime fires JURISDICTION, FEMA ICS fires EXIT — would be a computed result rather than a researcher-directed reconstruction. This removes a judgment step and strengthens the evidentiary position.

**Build implication for the remaining eleven substrates:** The intellectual work per substrate is vocabulary acquisition — sourcing actor taxonomy, action class map, and permitted flow graph from doctrine. The Python instantiation follows in under an hour once the vocabulary is clean. Under the reconstruction-driven approach, the incident surfaces the vocabulary; the harness confirms the topology. One pipeline per substrate. Vocabulary collection *is* the domain build.

---

## Funding Door Summary (Updated)

| Council / Agency | Relevant Substrates |
|-----------------|-----------------|
| NSERC | 1, 2, 3, 4, 5, 16, 17, 19, 24, 25, 26 |
| CIHR | 7, 12 |
| SSHRC | 3, 6, 11, 20, 21, 22, 23, 25 |
| IDEaS / DND | 1, 5, 9, 10, 16, 18, 24 |
| Transport Canada / NavCanada | 5, 10, 17 |
| Public Safety Canada | 9, 20 |
| NRCan | 8, 19 |
| Finance Canada | 6, 22 |
| Infrastructure Canada | 13 |
| Innovation Canada | 14 |

---

## Version Provenance

| Document | Version | Date | Key Change |
|----------|---------|------|-----------|
| `2026_05_19_Master_Domain_Registry_v1_0.md` | 1.0 | May 19, 2026 | Original — 10 planned domains identified |
| `2026_05_19_Master_Domain_Registry_v1_1.md` | 1.1 | May 21, 2026 | Updated to 14 confirmed substrates; Section 2 cleared of confirmed entries |
| `2026_05_20_Master_Domain_Registry_v1_2.md` | 1.2 | May 20, 2026 | Section 5 added — 4 inverse incident reconstructions |
| `2026_05_21_Master_Domain_Registry_v1_3.md` | 1.3 | May 21, 2026 | Substrate 15 (Petroleum) confirmed; Section 2 restructured into four build tiers; two new substrates added (Rail #17, Chemical/Industrial #19); Section 5 updated to 10 reconstructions and 3 named patterns; Section 6 added (Meta-Compiler Architecture) |
| `2026_05_21_Master_Domain_Registry_v1_4.md` | 1.4 | May 21, 2026 | Tier 1 build wave complete — substrates 16–19 confirmed; total 19 substrates, 247/247 tests |
| `2026_05_21_Master_Domain_Registry_v1_5.md` | 1.5 | May 21, 2026 | Tier 2 build wave complete — substrates 20–23 confirmed; total 23 substrates, 299/299 tests |
| `2026_05_21_Master_Domain_Registry_v1_6.md` | 1.6 | May 21, 2026 | Tier 3 build wave complete — substrates 24–26 confirmed; total 26 substrates, 338/338 tests |

---

*Registry scope: living document. Updated each time a substrate build is completed, a new substrate is identified, or a reconstruction is confirmed. Version number increments on structural changes to the registry format or significant status changes.*

*Gate kernel: `domain_compiler_v0_9.py` — unchanged since May 15, 2026.*
