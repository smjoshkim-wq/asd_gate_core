# Inverse Incident Methodology
**Version:** 1.0
**Date:** May 19, 2026
**Status:** Foundry research methodology — active
**Follows from:** Progress Note — Domain Expansion Brainstorm, May 19, 2026 (Section 4 and Section 9)

---

## Purpose

The Inverse Incident Methodology is a structured process for deriving structural invariant violation hypotheses from real-world failure events and testing them using synthetic harness scenarios. It connects the gate's structural findings to observable reality in a way that is independently legible — to a non-technical audience, to a funding reviewer, and to a domain expert who has never seen the gate before.

The forward direction of the compiler methodology is: given a structural setup, what violations does the gate detect?

The inverse direction is: given a known real-world failure outcome, what invariant violations were *necessary* for that outcome to be possible?

These are complementary. The forward direction validates the gate. The inverse direction grounds the gate in reality.

---

## When to Use This Methodology

Use it in two situations:

**Situation 1 — Pressure testing an existing compiler.** A compiler exists for a domain and has passed its combinatorial harness. You have a documented real-world incident in that domain. Use the inverse methodology to derive structural hypotheses from the incident and test them against the compiler. This extends the compiler's validation beyond synthetic scenarios.

**Situation 2 — Building a new compiler.** The deep research phase for a new domain identifies one or more public incident post-mortems with sufficient detail. The inverse methodology extracts additional compiler design inputs — specifically, what violations the permitted flow graph must be capable of detecting.

---

## What You Need to Begin

**Minimum viable incident record:**
- You do not need to know *how* the failure happened
- You need to know *what* happened — who was involved, what roles, what the outcome was, what the timeline looked like at a coarse level
- A public post-mortem, NTSB report, Joint Commission report, news investigation, or regulatory finding is sufficient
- The incident does not need to be fully explained — partially explained or "cause unknown" incidents are valid inputs

**What makes an incident record stronger:**
- Named roles (not just "an employee" but "the first officer" or "the attending physician")
- A documented sequence of events with approximate ordering
- An identified gap between what should have happened and what did happen
- A regulatory or professional standard that was violated or absent

---

## The Four-Step Process

### Step 1 — Incident Summary

Produce a structured summary of the incident. This is not a narrative retelling — it is a structural extraction.

**Extract:**
- Domain
- Roles involved (use the compiler's role taxonomy if it exists; otherwise use roles as named in the report)
- Outcome — what failed, what the consequence was
- Timeline — what happened in what order, as specifically as the record allows
- The gap — what was supposed to happen that didn't, or what happened that wasn't supposed to

**Format:** Timestamped markdown section. Keep it to one page or less. Do not editorialize.

---

### Step 2 — Abductive Hypothesis Generation

Work backward from the outcome. For each of the five invariants, ask: could a violation of this invariant have been a structural precondition for this outcome?

**The five questions:**

| Invariant | Question |
|-----------|----------|
| ORDER | Was there an action performed before a required prior action was complete? Did the sequence skip a required stage? |
| JURISDICTION | Did an actor perform an action outside their permitted class? Did a role boundary get crossed? |
| BURST_CADENCE | Did any actor oscillate between states at a rate that suggests loss of structural coherence rather than legitimate workflow? |
| EXIT | Did a new actor enter a workflow instance mid-flight without a valid handoff? Did responsibility transfer without a defined transfer event? |
| HYSTERESIS | After an ORDER or JURISDICTION violation occurred, did the workflow continue to expand into new territory rather than halting or correcting? |

**Output:** A hypothesis statement per invariant that fired. Format:

> *"Hypothesis [Invariant]: [Role] performed [Action] at [State] before [Required Prior Action] was complete. This is an ORDER violation under the [Domain] compiler. The structural precondition for [Outcome] includes this violation."*

Not every invariant will fire for every incident. Document which ones are hypothesized and which are not, and why.

---

### Step 3 — Synthetic Scenario Construction

For each hypothesis generated in Step 2, construct a synthetic event sequence that encodes the hypothesized violation and test it against the compiler.

**Scenario construction rules:**
- The scenario must be fully specified before running (Condition 1 of the valid synthetic testbed standard)
- The scenario must isolate the hypothesized invariant — do not combine multiple hypothesized violations in one scenario unless testing compound effects deliberately
- The scenario must include a negative control variant — the same sequence without the violation — to confirm the gate does not over-trigger

**What the scenario must produce:**
- The gate fires the hypothesized invariant on the violation scenario
- The gate does NOT fire on the negative control variant
- If the gate does not fire on the violation scenario, the hypothesis is wrong or the compiler design has a gap — document which and why

---

### Step 4 — Structural Finding Documentation

If the scenarios confirm the hypotheses, produce a Structural Finding document for the incident.

**Contents:**
- Incident name, date, domain, public source
- Invariants confirmed by scenario testing
- The synthetic scenarios used and their results (JSON)
- **Incident-to-Synthetic Mapping Table** (required — see format below)
- The structural explanation: what combination of violations, in what sequence, creates the structural preconditions for this outcome
- The gap layer: is this violation combination detectable under current regulation or policy? If not, what structural correction would close the gap?
- A one-paragraph plain-language summary suitable for a non-technical audience

**Incident-to-Synthetic Mapping Table — Required Format**

This table is the primary defense against the "toy model" objection. It makes the structural correspondence between the real-world incident record and the synthetic scenario explicitly visible. One table per incident, included in every Structural Finding document.

| # | Incident Record (Real) | Synthetic Event Sequence (Compiler) | Invariant | Gate Verdict |
|---|----------------------|-------------------------------------|-----------|-------------|
| 1 | [Exact role name from report] performs [action] at [timestamp or sequence position] | Actor: [role], Action: [action], State: [state] | ORDER / JURISDICTION / etc. | INADMISSIBLE |
| 2 | [Next event from report] | [Corresponding synthetic event] | | |
| ... | | | | |

**Mapping table rules:**
- Left column draws directly from the public incident record — use the report's own language for role names and action descriptions
- Right column shows the exact synthetic event submitted to the compiler
- The structural correspondence must be visible without additional explanation — if it requires a paragraph to explain the mapping, the synthetic scenario needs to be redesigned
- Every row where the gate fires must have an explicit invariant and verdict
- Rows where the gate does not fire are included — they show the negative space of the finding

This table is what separates a structural finding from a toy model. The gate was locked before the scenario was designed. The permitted flows were fixed before the run started. The mapping table makes that visible.

**What a Structural Finding is not:**
- It is not a policy recommendation
- It is not a causal claim about what actually happened (the incident may have had other causes)
- It is not a verdict on any individual or organization

**What a Structural Finding is:**
- A documented structural explanation — this combination of invariant violations creates the conditions under which this outcome becomes possible
- A testable claim — the synthetic scenarios that produced these gate results are reproducible
- A structural policy input — here is what the gate would need to detect to prevent the preconditions from going unnoticed

---

## Incident Anchor Library — Confirmed Candidates

These incidents have sufficient public documentation to begin Step 1 immediately.

| Incident | Domain | Year | Source | Hypothesized Invariants | Notes |
|----------|--------|------|--------|------------------------|-------|
| Tenerife runway collision | Aviation | 1977 | ICAO report (public) | JURISDICTION, ORDER | ATC/cockpit boundary failure. Role boundary crossed. Most cited aviation disaster. |
| Elaine Bromiley | Clinical | 2005 | UK report (public) | JURISDICTION, ORDER | Anaesthetic complication. Landmark in clinical human factors. Became foundation of UK patient safety training. |
| 2008 Financial Crisis | Financial | 2008 | FCIC report, 662pp (public) | JURISDICTION, ORDER, HYSTERESIS, multi-compiler boundary | Trading desk / risk management compiler boundary. FCIC report is the most detailed public causal narrative available. |
| Equifax breach | Cyber — response layer | 2017 | Public post-mortem, Senate testimony | ORDER, EXIT | Failure was in the response sequence, not just the intrusion. Patch available 2 months before breach. |
| SolarWinds | Cyber — response layer | 2020 | Public post-mortem, CISA advisory | ORDER, JURISDICTION | Supply chain insertion. Response sequence failures documented publicly. |
| Costa Concordia | Maritime | 2012 | MAIB report (public) | JURISDICTION, ORDER, EXIT | Captain's deviation from protocol. Command structure breakdown. |
| Thalidomide | Pharmaceutical | 1957–1961 | FDA historical record (public) | ORDER | Approval before phase sequence completion. Classic ORDER violation in regulatory context. |
| Log4Shell | Software development | 2021 | Public post-mortem | ORDER, JURISDICTION | Release authorization sequence failure. Patch deployment sequence failures. |
| Hurricane Katrina response | Emergency response | 2005 | Congressional report (public) | JURISDICTION, EXIT, ORDER | ICS breakdown at command boundaries. Multi-agency jurisdiction failures. |

---

## Near-Miss Extension

The inverse methodology applies equally to near-misses. A near-miss is a structural violation that did not propagate to a terminal failure outcome — but the violation was present. The gate fires on near-misses the same way it fires on accidents.

**Why near-misses matter:**
- The gate does not need a body count to detect the precondition
- Near-miss data is often more abundant and better documented than accident data
- NASA ASRS (Aviation Safety Reporting System) contains tens of thousands of anonymized near-miss reports, free and searchable
- Near-miss confirmation strengthens the claim that the gate detects structural preconditions, not outcomes

**Near-miss handling:** Use the same four-step process. In Step 4, note explicitly that this is a near-miss case and that the gate fired on the precondition in the absence of a terminal outcome.

---

## Relationship to the Invariance Library

Every Structural Finding produced under this methodology feeds into the Invariance Library. Specifically:

- The failure signature of each invariant — what it looks like in a real incident, not just a synthetic scenario — is a library entry
- Cross-domain comparisons of the same invariant's failure signature are the library's primary scientific contribution
- ORDER in aviation looks structurally the same as ORDER in clinical looks structurally the same as ORDER in financial — that cross-domain structural identity is the claim the library documents

See Invariance Library v1.0 for the current accumulated signatures.

---

## Scientific Framing

The inverse methodology is abductive reasoning formalized through a structural gate. It generates structural hypotheses from empirical evidence and tests them with reproducible synthetic scenarios. It does not prove what happened in a specific incident. It demonstrates that the structural preconditions for that outcome are detectable by the gate — and that those preconditions appear across structurally distinct domains.

This is a genuine contribution to safety engineering and human factors research, independent of the gate validation work. It is publishable as a standalone paper series.

---

*Methodology scope: operational standard for incident-derived structural analysis. Version increments when the methodology changes. Individual Structural Findings are documented in their own files within the relevant domain's build package.*
