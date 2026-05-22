# Repeatable Compiler Methodology
**Version:** 1.1
**Date:** May 20, 2026
**Status:** Foundry operational standard
**Follows from:** Repeatable Compiler Methodology v1.0 (May 19, 2026)
**Revision basis:** Pattern analysis across 10-domain harness suite. Geometry pre-check step inserted into execution path. C01 harness description clarified. Sub-assertion pattern documented as standard for C-block compound tests.

---

## Purpose

This document is the foundry's how-to for building a new domain compiler. It does not require domain specialist knowledge. It requires knowing what structure looks like and asking for the three inputs precisely. The pattern has been confirmed across three substrates — cyber syscall, agentic tool-call, org workflow human decision layer — and is transferable to any domain where permitted flows are publicly codified.

The org workflow compiler was not built by an HR specialist. The agentic compiler was not built by an AI orchestration engineer. The gate does not change. Only the compiler changes.

---

## The Compiler-Compiler Pattern

This methodology is formally a compiler-compiler: it takes domain knowledge as input and produces a domain compiler as output. The three-input structure below is the interface spec. Every compiler built under this methodology is an instantiation of the same pattern against a different domain vocabulary.

---

## Three Inputs, One Output

### Input 1 — Actor Taxonomy

**What it is:** The complete set of roles in this domain, their hierarchy, and which roles are permitted or excluded from which action classes.

**What to extract:**
- Role names and hierarchy
- Which roles can initiate actions
- Which roles are excluded from certain action classes by construction
- Whether any action class is excluded from ALL roles by design (structural analog to T5 in agentic, A5 in org workflow, DELETE/PRIVILEGE_CHANGE from non-admin in cyber)

**Where to find it:** Statutes, regulations, operational doctrine, professional standards, licensing frameworks

---

### Input 2 — Action Class Map

**What it is:** The complete set of actions in this domain, organized into classes, with gating status per class.

**What to extract:**
- All actions observable in this domain
- Which action class each belongs to (equivalent to A1–A5 in org workflow, T1–T5 in agentic, syscall categories in cyber)
- Which classes are gated (require role authorization)
- Which classes are unrestricted
- Which classes are excluded from all roles by construction

**Where to find it:** Same sources as actor taxonomy — statutes, regulations, operational checklists, procedure manuals

---

### Input 3 — Permitted Flow Graph

**What it is:** The required sequence of actions. What state transitions are valid. What ordering constraints exist between action classes.

**What to extract:**
- Valid state transitions per role
- Required ordering constraints between action classes
- States where certain actions are permitted that are not permitted in other states
- Terminal states — where does a correctly executed workflow end?
- State widths — how many valid actions exist at each state?

**Where to find it:** Procedural rules, checklists, approval workflows, regulatory filing sequences, operational doctrine

---

### Output — Domain Compiler

A Python compiler that:
- Imports `evaluate_gate`, `Encapsulation`, `ResolutionStatus`, and burst constants from `domain_compiler_v0_9` verbatim
- Does NOT re-implement the gate kernel
- Implements only the compiler layer — role registry, action class map, permitted flow graph, state tracker
- Follows the established structural pattern of the three confirmed compilers

---

## Deep Research Prompt Template

Use this prompt verbatim (substituting DOMAIN NAME) when extracting the three inputs from Claude or Gemini. One prompt is typically sufficient for a well-documented domain. A second prompt incorporating incident-derived violations (see Inverse Incident Methodology) may follow.

---

```
I am building a structural domain compiler for [DOMAIN NAME]. 
The compiler needs three inputs extracted from public sources only. 
Please provide all three as completely as possible.

INPUT 1 — ACTOR TAXONOMY
List every role in [DOMAIN NAME] that can initiate or authorize actions.
For each role:
- Role name
- Position in hierarchy (superior / subordinate / peer)
- Which action classes this role is PERMITTED to perform
- Which action classes this role is EXPLICITLY EXCLUDED from
- Whether any action class exists that NO role is permitted to perform

Sources to draw from: statutes, regulations, licensing frameworks, 
professional standards, operational doctrine.

INPUT 2 — ACTION CLASS MAP
List every observable action in [DOMAIN NAME].
Group them into action classes (5–7 classes is typical).
For each class:
- Class name and label (e.g. A1, A2...)
- Actions belonging to this class
- Whether this class is gated (requires role authorization), 
  unrestricted, or excluded from all roles by construction
- Which roles are permitted to perform actions in this class

Sources: same as above, plus operational checklists and procedure manuals.

INPUT 3 — PERMITTED FLOW GRAPH
Describe the required sequence of actions for a correctly executed 
workflow in [DOMAIN NAME].
For each state in the workflow:
- State name
- Which actions are valid from this state
- Which state each valid action transitions to
- Whether this is a terminal state
- State width (how many valid actions exist here)

Also identify:
- Any ordering constraints between action classes that exist 
  regardless of state (e.g. class A2 must always precede class A4)
- Any actions that can loop within a state
- Any actions that are valid in multiple states

Sources: procedural rules, checklists, approval workflows, 
regulatory filing sequences.

Format your response with clear section headers for each input. 
Be as specific as possible. Include the regulatory or doctrinal 
source for each element where known.
```

---

## Harness Construction Pattern

Every combinatorial harness built under this methodology follows the same three-block structure. This pattern is confirmed across the three existing harnesses and must be preserved for all new domains.

### Block A — Independent First-Fire (4 tests)

Each test fires exactly one invariant in isolation. The other four invariants must NOT fire. This confirms each invariant is detectable independently.

| Test | Invariant | Description |
|------|-----------|-------------|
| A01 | ORDER | Sequence violation — action performed out of required order |
| A02 | JURISDICTION | Role boundary violation — actor performs action excluded from their class |
| A03 | BURST_CADENCE | Oscillation violation — actor moves back and forth across a state boundary at a rate exceeding burst threshold |
| A04 | EXIT | Actor pivot — new actor enters a workflow instance already in progress without valid handoff |

### Block B — Hysteresis Dependency (3 tests)

HYSTERESIS cannot fire without a prior ORDER or JURISDICTION violation. These tests confirm the dependency structure.

| Test | Setup | Expected Result |
|------|-------|----------------|
| B01 | Clean pipeline, no prior violation | No HYSTERESIS |
| B02 | ORDER fires, then actor expands into unvisited stage | HYSTERESIS fires |
| B03 | JURISDICTION fires, then actor expands into unvisited stage | HYSTERESIS fires |

### Block C — Cross-Invariant Compound (3 tests)

Multiple invariants fire in the same session. They must coexist without false coupling — one invariant firing must not suppress or trigger another.

| Test | Setup | Expected Result |
|------|-------|----------------|
| C01 | ORDER fires, BURST_CADENCE fires, same session — HYSTERESIS must NOT fire | Both fire independently; HYSTERESIS absent |
| C02 | JURISDICTION fires, ORDER fires, sequential — same or different actor | Both fire independently |
| C03 | EXIT fires, JURISDICTION fires, separate actors / separate instances | Both fire independently |

**C01 note:** The HYSTERESIS-must-not-fire constraint is what makes C01 the geometrically hardest test. The burst oscillation must occur entirely within already-visited states. This geometry must be confirmed in the Compiler Design Note (C01 Feasibility Audit) before writing harness code. See Domain Build Package Standard Artifact 2 for the required pre-check.

**C-block sub-assertion standard:** Compound tests (C01, C02, C03) should assert each expected fire independently and combine the results. C01 in particular should produce two named sub-assertions (e.g. `C01a` for ORDER, `C01b` for BURST_CADENCE) so that a partial pass is diagnosable. Example pattern:
```python
order_ok = assert_pass("C01a", "ORDER fires at step N", r, "INADMISSIBLE", "ORDER", N)
burst_ok = assert_pass("C01b", "BURST_CADENCE fires at step M", r, "INADMISSIBLE", "BURST_CADENCE", M)
return order_ok and burst_ok
```

### Harness Result Format

Each test must produce:
- `[PASS]` or `[FAIL]` label
- Test ID (A01–C03)
- One-line description of what was tested
- JSON output from the gate for that test

Final line: `Results: 10/10 passed ✓ ALL PASS` or failure count with details.

---

## Execution Path Per New Domain

1. Run the Deep Research Prompt Template for the target domain. Extract all three inputs. Paste results into a timestamped design note.

2. If incorporating incident-derived violations, run a second deep research prompt following the Inverse Incident Methodology document. Append to the design note.

3. Complete the three geometry pre-checks in the Compiler Design Note before writing any code:
   - **C01 Feasibility Audit** — identify the pre-visited state set available before ORDER fires and confirm whether the burst oscillation pair is a subset of it. Document the implementation strategy if not.
   - **BURST-Safe Traversal Audit** — count consecutive width-expanding transitions on the B01 clean path. If ≥3, document the required inter-event spacing.
   - **Role Reachability Audit** — confirm each role used in B02/B03 can reach an unvisited state after a violation. Document the fallback role if not.

4. Build the compiler against the established pattern. Gate kernel imported verbatim — not re-implemented. Output key `"decision"` used throughout.

5. Build the combinatorial harness following the Block A / B / C structure above. Implement the C01 geometry confirmed in step 3. No dead exploration code in the harness file.

6. Run on hardware. Document results as JSON. Confirm 10/10.

7. Assemble the Domain Build Package per the Domain Build Package Standard document.

---

## What This Methodology Does Not Require

- Domain specialist knowledge
- Institutional data access
- Proprietary datasets
- Re-implementation of the gate kernel
- A new harness structure

## What This Methodology Does Require

- A domain where permitted flows are publicly codified (see Master Domain Registry for confirmed candidates)
- Accurate extraction of the three inputs from public sources
- Discipline in keeping the gate kernel unchanged
- Adherence to the harness construction pattern for comparability across substrates

---

## Scientific Framing

Every new domain built under this methodology is an attempt to falsify the universality of the five invariants across structurally distinct domains. Every 10/10 harness result is not just a validation — it is a failed falsification attempt. The cross-substrate claim grows stronger with each failed attempt. This is the correct scientific framing and must be preserved in all documentation and outreach.

---

*Methodology scope: operational standard for new compiler builds. Version increments when the methodology itself changes — not when new compilers are built. Each compiler build is documented in its own Domain Build Package.*
