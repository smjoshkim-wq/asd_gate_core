# Domain Build Package Standard
**Version:** 1.1
**Date:** May 20, 2026
**Status:** Foundry operational standard
**Follows from:** Domain Build Package Standard v1.0 (May 19, 2026)
**Revision basis:** Pattern analysis across 10-domain harness suite. Three geometry checks added to Artifact 2 based on observed intra-harness discovery failures (C01 compromise in GitHub and Maritime, B01 timestamp surprise in Nuclear/FEMA/Maritime/Financial/Clinical, B03 role pivot in Aviation). Output key standardized in Artifact 3. Dead code clause added to completeness check.

---

## Purpose

Every domain compiler built under the Repeatable Compiler Methodology produces a Domain Build Package — a complete, timestamped, reproducible artifact set. The package is the unit of scientific record. Someone else could pick it up and reproduce or extend the work without additional context.

The package is also the audit trail. It documents not just what was built but why each design decision was made, what data was used, and what the gate produced. This matters for the funding narrative, the paper series, and the integrity of the cross-substrate claim.

---

## Required Artifacts — In Order of Production

### Artifact 1 — Deep Research Output

**What it is:** The raw extracted output from the deep research prompt, unedited.

**Format:** Timestamped markdown note. Paste the prompt used and the full response received. Do not clean up or summarize — keep the raw output.

**Naming convention:** `YYYY_MM_DD_[Domain]_Deep_Research_v1_0.md`

**Contents:**
- The exact prompt submitted (use the template from Repeatable Compiler Methodology, or document any variation)
- The full response — actor taxonomy, action class map, permitted flow graph
- Source citations as returned
- Timestamp of when the prompt was run

**Notes:** If a second deep research prompt was run for incident-derived violations, include it as a second section in the same document labeled clearly.

---

### Artifact 2 — Compiler Design Note

**What it is:** The design thinking record. Documents every decision made between the deep research output and the compiler code.

**Format:** Timestamped markdown note.

**Naming convention:** `YYYY_MM_DD_[Domain]_Compiler_Design_v1_0.md`

**Contents:**
- Which role taxonomy was adopted and why
- Which action class map was adopted — how many classes, what each contains, which is excluded from all roles by construction
- Which permitted flow graph was adopted — state names, transition map, terminal states, state widths
- Any design decisions that deviated from the deep research output and why
- Mapping of domain-specific concepts to gate invariants:
  - What produces an ORDER violation in this domain
  - What produces a JURISDICTION violation in this domain
  - What produces a BURST_CADENCE violation in this domain
  - What produces an EXIT violation in this domain
  - What produces a HYSTERESIS violation in this domain (dependency confirmed)
- Any structural anomalies noted — things that don't map cleanly, gaps in the public doctrine, ambiguities resolved by design choice

**Required geometry checks (answer all three before writing any harness code):**

*Check 1 — C01 Feasibility Audit*
For the actor/role where ORDER is most natural to fire: list the states visited on the clean path leading to that ORDER trigger. Is the intended burst oscillation pair (two states between which the actor can expand/contract) a subset of those already-visited states? If yes, C01 is achievable with a single actor and no timestamp engineering. If no, document the workaround strategy here — options are: (a) extend the pre-visit path with wide timestamps before ORDER, (b) use two actors in the same compiler session (document why single-actor is geometrically blocked), or (c) reverse the fire order (BURST first, ORDER second — document why the canonical order is unachievable). The harness must then implement the documented strategy without further exploration at code time.

*Check 2 — BURST-Safe Traversal Audit*
Count the number of consecutive width-expanding transitions on the canonical clean compliance path (the B01 negative control path). If the count is ≥3, the negative control will trip the BURST detector unless events are spaced beyond the burst window. Document the minimum inter-event spacing required (burst window ÷ 2 is a safe default) and note it in the harness B01 inline comment. If the count is < 3, no timestamp engineering is needed — note that explicitly.

*Check 3 — Role Reachability Audit (HYSTERESIS)*
For B02 and B03 to be achievable, at least one role must be able to reach an unvisited state via a structurally valid action after a violation has frozen the trajectory. For each role used in B02/B03: list the states reachable from the violation point that have not been visited on the path to that point. If a role's flow graph has only loopback transitions from the violation point (no unvisited state reachable), B-block tests cannot use that role — document which role is used instead and why.

---

### Artifact 3 — Compiler Code

**What it is:** The Python compiler file.

**Format:** `.py` file.

**Naming convention:** `[domain]_compiler_v0_1.py` (version increments as compiler is updated)

**Required structure:**
```python
# Imports from gate kernel — verbatim, no modifications
from domain_compiler_v0_9 import (
    evaluate_gate, Encapsulation, ResolutionStatus,
    BURST_WINDOW, BURST_THRESHOLD
)

# Role registry
# Action class map
# Permitted flow graph
# State tracker class
# Domain compiler class
```

**Output key rule:** The compiler's `run_session()` function must return per-event dictionaries using the key `"decision"` for the gate verdict (not `"verdict"` or any other label). This matches the gate kernel's native output and is required for cross-substrate comparability. Compilers using `"verdict"` must be patched before inclusion in any unified cross-substrate analysis.

**Gate kernel rule:** `evaluate_gate`, `Encapsulation`, `ResolutionStatus`, and burst constants are imported verbatim. Never re-implemented. If the gate kernel needs updating, that is a separate versioned change to `domain_compiler_v0_9.py` with its own documentation.

---

### Artifact 4 — Harness Code

**What it is:** The combinatorial test harness.

**Format:** `.py` file.

**Naming convention:** `test_harness_[domain]_v0_1_combinatorial.py`

**Required structure:** Block A (4 tests), Block B (3 tests), Block C (3 tests) as specified in Repeatable Compiler Methodology. Structurally parallel to existing three harnesses.

**Synthetic scenario documentation:** Each test must include an inline comment explaining:
- What real-world scenario this synthetic event sequence represents
- Which invariant is expected to fire and why
- Why this specific sequence was chosen as the boundary test

**Clean code rule:** Harness files must not contain commented-out or dead event sequences from discarded design attempts. Exploration of alternative event sequences belongs in the Compiler Design Note (Artifact 2), specifically in the C01 Feasibility Audit section. Harness code is the confirmed implementation, not a record of the search process.

---

### Artifact 5 — Harness Results (JSON)

**What it is:** The raw gate output from running the harness on hardware.

**Format:** JSON file plus a summary markdown note.

**Naming convention:** `YYYY_MM_DD_[Domain]_Harness_Results_v1_0.json` and `YYYY_MM_DD_[Domain]_Harness_Results_v1_0.md`

**JSON contents:** Gate output per test — verdict, invariant fired, trajectory state at time of firing, encapsulation state.

**Markdown summary contents:**
- Hardware confirmation line: OS, shell, timestamp
- Results table: test ID, pass/fail, invariant fired, one-line description
- Final count: `Results: 10/10 passed ✓ ALL PASS`
- Any anomalies, unexpected results, or tests that required harness revision and why

---

### Artifact 6 — Pressure Test Record (Optional but Recommended)

**What it is:** Additional synthetic boundary testing beyond the 10-test combinatorial harness. Documents the compiler's boundary behavior — where it fires and where it doesn't.

**Format:** Timestamped markdown note with inline JSON snippets.

**Naming convention:** `YYYY_MM_DD_[Domain]_Pressure_Test_v1_0.md`

**Contents:**
- Boundary cases tested — what scenario was designed to probe the edge of each invariant
- Negative controls — scenarios designed to NOT fire the gate, confirming no over-triggering
- Results per boundary case
- Any compiler adjustments made as a result and why

**Negative control rule:** If a synthetic scenario collapses without a structural invariant violation, the result is discarded. The gate must produce the violation that explains the collapse. If it does not, the compiler design has a gap. Document the gap and the resolution.

---

### Artifact 7 — Progress Note

**What it is:** The session record. Written at the end of the build session.

**Format:** Timestamped markdown note.

**Naming convention:** `YYYY_MM_DD_Cyber_Progress_Note_[Domain].md`

**Contents:**
- Session context — what was built, what was not built
- What was accomplished — summary of each artifact produced
- Hardware confirmation details
- What this does not mean — falsificationist qualifier, synthetic data limitations
- What comes next
- Pointers to all artifacts produced

---

## Package Completeness Check

Before closing a domain build, verify all required artifacts are present:

- [ ] Deep Research Output — timestamped, raw, prompt included
- [ ] Compiler Design Note — all five invariant mappings documented; C01 feasibility audit, BURST-safe traversal audit, and role reachability audit all answered
- [ ] Compiler Code — gate kernel imported verbatim, not re-implemented; `"decision"` key used in output
- [ ] Harness Code — Block A / B / C structure, inline scenario comments, no dead code
- [ ] Harness Results JSON — raw gate output
- [ ] Harness Results Markdown Summary — hardware confirmation, pass/fail table
- [ ] Progress Note — session record, what this does not mean, what comes next
- [ ] Pressure Test Record — optional but recommended for new domains

---

## Work-as-Imagined vs Work-as-Done

Every compiler built under this methodology is built against the codified permitted flows — the work-as-imagined. This is intentional and must be stated explicitly in every Domain Build Package.

The compiler does not model what actors in a domain actually do. It models what they are structurally required to do under the governing statute, regulation, or operational doctrine. When real data eventually enters a deployed compiler and produces INADMISSIBLE verdicts at high rates, that is not a compiler failure — it is a structural finding. It means the institution is systematically deviating from its own codified structure. That deviation is itself a research result and a deployment signal.

This distinction must be documented in Artifact 2 (Compiler Design Note) for every domain build. One line is sufficient: *"This compiler is built against [source] as the codified permitted flow standard. Deviations observed in real data are treated as structural findings, not compiler errors."*

Failure to document this distinction leaves the compiler vulnerable to the objection that INADMISSIBLE verdicts on real data represent noise rather than signal.

---

## Three Conditions for a Valid Synthetic Testbed

Every synthetic scenario in every harness and pressure test must meet these three conditions. These are the methodological guardrails that make synthetic validation scientifically defensible.

**Condition 1 — Fully Specified**
Roles, constraints, and permitted flows are immutable once the simulation starts. No adjustments mid-run to fit the expected outcome. All design choices are made in Artifact 2 (Compiler Design Note) before any code is written.

**Condition 2 — Trajectory-Bound**
Clear separation between compile-time (the structural setup) and execution-time (the runtime sequence). The gate fires at execution-time against compile-time constraints. The compiler does not change during a run.

**Condition 3 — Observation-Capped**
A confirmation is only counted if the gate's structural verdict matches the observed failure signature before any interpretive explanation is applied. The gate must find it first. Post-hoc rationalization of a gate result is not a confirmation.

---

## Reproducibility Standard

A Domain Build Package is complete when a researcher unfamiliar with the domain could:

1. Read the Deep Research Output and understand the three inputs
2. Read the Compiler Design Note and understand every design decision
3. Run the Compiler Code and Harness Code and reproduce the results
4. Read the Progress Note and understand what was built and what it means

If any of those four steps would require additional context not in the package, the package is incomplete.

---

*Document scope: operational standard for artifact production per domain build. Version increments when the standard changes. Individual domain packages are not versioned here — they are versioned in their own files.*
