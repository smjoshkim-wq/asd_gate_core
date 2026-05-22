# Invariance Library
**Version:** 1.0
**Date:** May 19, 2026
**Status:** Living document — updated as new substrates are confirmed and incident findings are produced
**Follows from:** Progress Note — Domain Expansion Brainstorm, May 19, 2026 (Section 9)

---

## Purpose

The Invariance Library is the cumulative record of how each of the five ASD invariants produces a unique, predictable failure signature across structurally distinct domains. It documents what each invariant looks like — in synthetic harness results, in real incident records, and in the cross-domain structural comparisons that constitute the substrate-invariance claim.

This is a standalone research contribution, separate from the cross-substrate validation paper. The cross-substrate paper demonstrates that the invariants appear across domains. The Invariance Library documents what they look like when they appear — their structural signatures, their distinguishing characteristics, and the ways they combine.

The library grows with every new domain compiler confirmed on hardware and every incident-derived Structural Finding produced. Version number increments on structural changes to the library format. Entries are added in place with timestamps.

---

## How to Read This Document

Each invariant has its own section containing:
- **Definition** — what the invariant is at the gate level
- **Structural signature** — what distinguishes this invariant's failure pattern from the others
- **Confirmed domain appearances** — where this invariant has been observed, in synthetic or real-incident contexts
- **Distinguishing characteristics** — what makes this invariant's signature unique and not confusable with other invariants
- **Combinations** — how this invariant interacts with others when they co-occur

---

## Invariant 1 — ORDER

### Definition
An action was performed before a structurally required prior action was complete. The trajectory skipped a required stage in the permitted flow graph.

### Structural Signature
ORDER violations are detectable from the permitted flow graph alone. The compiler knows what state the actor should be in before performing a given action. If the actor is not in that state, ORDER fires. The violation is state-mismatch at execution time.

Key feature: ORDER violations do not require a role boundary crossing. A fully authorized actor performing an action in the wrong sequence produces ORDER. This distinguishes it from JURISDICTION.

### Confirmed Domain Appearances

| Domain | Context | Type | Date Confirmed |
|--------|---------|------|---------------|
| Cyber — syscall layer | Privilege escalation trajectories — DELETE before ENUMERATE complete | Synthetic harness | May 12, 2026 |
| Agentic — tool-call layer | Tool execution before authorization token retrieved | Synthetic harness | May 15, 2026 |
| Org workflow — human decision layer | Approval action performed before assessment stage complete | Synthetic harness | May 16, 2026 |
| Aviation (hypothesized) | KLM takeoff before ATC clearance confirmed (Tenerife 1977) | Incident hypothesis — not yet harness-tested | May 19, 2026 |
| Clinical (hypothesized) | Treatment administered before differential diagnosis complete (Bromiley 2005) | Incident hypothesis — not yet harness-tested | May 19, 2026 |
| Pharmaceutical (hypothesized) | Market approval before safety phase sequence complete (Thalidomide) | Incident hypothesis — not yet harness-tested | May 19, 2026 |

### Distinguishing Characteristics
- Does not require a role boundary crossing — authorized actor, wrong sequence
- Detectable purely from state tracking — no role comparison required
- Often appears before HYSTERESIS — ORDER is the typical first violation that enables subsequent HYSTERESIS
- Cross-domain structural identity: the state-mismatch pattern is structurally identical whether the domain is syscall sequences, tool-call chains, human approval workflows, or clinical procedures

### Combinations
- ORDER + HYSTERESIS: the most common compound pattern. ORDER fires first, workflow continues to expand rather than halting, HYSTERESIS fires when new territory is entered post-violation.
- ORDER + JURISDICTION: can co-occur independently. ORDER fires on sequence, JURISDICTION fires on role boundary, in the same session without coupling.

---

## Invariant 2 — JURISDICTION

### Definition
An actor performed an action outside their permitted action class. A role boundary was crossed — the actor's role does not include the action class required for the performed action.

### Structural Signature
JURISDICTION violations are detectable from the actor taxonomy and action class map. The compiler knows which action classes each role is permitted to perform. If the role is not in the permitted set for the action's class, JURISDICTION fires. The violation is role-action mismatch at execution time.

Key feature: JURISDICTION violations do not require a sequence error. A correctly-sequenced action performed by the wrong role produces JURISDICTION. This distinguishes it from ORDER.

The most structurally significant JURISDICTION case: an action class that is excluded from ALL roles by design. Any actor performing this action fires JURISDICTION by construction. This is the structural analog to T5 in agentic (terminate_all_agents), A5 in org workflow (transfer_funds), and DELETE/PRIVILEGE_CHANGE from non-admin roles in cyber.

### Confirmed Domain Appearances

| Domain | Context | Type | Date Confirmed |
|--------|---------|------|---------------|
| Cyber — syscall layer | Non-admin role performing DELETE or PRIVILEGE_CHANGE | Synthetic harness | May 12, 2026 |
| Agentic — tool-call layer | Sub-agent performing terminate_all_agents (T5 — excluded from all roles) | Synthetic harness | May 15, 2026 |
| Org workflow — human decision layer | Analyst performing approve_payment (A4 — excluded from Analyst role) | Synthetic harness | May 16, 2026 |
| Aviation (hypothesized) | First officer executing takeoff maneuver without captain authorization (Tenerife 1977 — ATC/cockpit boundary) | Incident hypothesis — not yet harness-tested | May 19, 2026 |
| Clinical (hypothesized) | Nursing staff performing airway management procedure outside scope of practice (Bromiley 2005) | Incident hypothesis — not yet harness-tested | May 19, 2026 |

### Distinguishing Characteristics
- Does not require a sequence error — the action can be correctly sequenced and still produce JURISDICTION
- Role boundary crossing is the defining feature — the compiler's role registry is the detection mechanism
- The "excluded from all roles" subcase is the structurally cleanest detection: any actor, any sequence, any context — if the action is in the excluded class, JURISDICTION fires
- Cross-domain structural identity: the role-action mismatch pattern is structurally identical whether the domain is syscall permissions, agent tool authorization, human organizational roles, or clinical scope-of-practice

### Combinations
- JURISDICTION + HYSTERESIS: same compound pattern as ORDER + HYSTERESIS. JURISDICTION fires, workflow expands into unvisited territory, HYSTERESIS fires.
- JURISDICTION + ORDER: can co-occur independently in the same session without coupling.

---

## Invariant 3 — BURST_CADENCE

### Definition
An actor oscillated between states at a rate exceeding the burst threshold. Rapid back-and-forth movement across a state boundary — more consistent with probing or structural incoherence than legitimate workflow execution.

### Structural Signature
BURST_CADENCE violations are detectable from the state transition history and the burst window / burst threshold constants. The compiler tracks how many times an actor crosses a specific state boundary within a defined time window. If the count exceeds the threshold, BURST_CADENCE fires.

Key feature: BURST_CADENCE does not require a role boundary crossing or a sequence error. A fully authorized actor performing correctly-sequenced actions can still produce BURST_CADENCE if the cadence of state transitions is structurally anomalous.

### Confirmed Domain Appearances

| Domain | Context | Type | Date Confirmed |
|--------|---------|------|---------------|
| Cyber — syscall layer | Rapid ENUMERATE / COPY oscillation consistent with data exfiltration probing | Synthetic harness | May 12, 2026 |
| Agentic — tool-call layer | Sub-agent oscillating between tool invocation states at anomalous rate | Synthetic harness | May 15, 2026 |
| Org workflow — human decision layer | Analyst oscillating between REVIEWING and ASSESSING states beyond burst threshold | Synthetic harness | May 16, 2026 |

### Distinguishing Characteristics
- The only time-sensitive invariant — the burst window is the defining parameter
- Does not require role or sequence violation — cadence alone is sufficient
- Probing behavior signature: in cyber and agentic domains, BURST_CADENCE often appears in reconnaissance patterns before a more decisive violation
- Cross-domain: the structural signature of anomalous oscillation is domain-independent — the burst constants may need domain-specific calibration, but the detection mechanism is the same

### Combinations
- BURST_CADENCE + ORDER: can co-occur independently. Documented in combinatorial harness C01 across all three confirmed substrates.

---

## Invariant 4 — EXIT

### Definition
A new actor entered a workflow instance already in progress without a valid handoff event. Responsibility transferred without a defined transfer action.

### Structural Signature
EXIT violations are detectable from the actor identity tracking per workflow instance. The compiler assigns workflow instances to actors at initialization. If a different actor performs an action on an instance that was not assigned to them, and no valid handoff action was performed, EXIT fires.

Key feature: EXIT is the only invariant that requires tracking actor identity across a workflow instance lifetime. It is not about what was done but about who did it relative to who owns the instance.

### Confirmed Domain Appearances

| Domain | Context | Type | Date Confirmed |
|--------|---------|------|---------------|
| Cyber — syscall layer | Session pivot — new process identity performing actions on an established session | Synthetic harness | May 12, 2026 |
| Agentic — tool-call layer | Unauthorized agent substitution mid-task | Synthetic harness | May 15, 2026 |
| Org workflow — human decision layer | Second analyst enters active workflow instance without valid handoff | Synthetic harness | May 16, 2026 |
| Emergency response (hypothesized) | Command transfer during active incident without ICS handoff protocol (Katrina) | Incident hypothesis — not yet harness-tested | May 19, 2026 |

### Distinguishing Characteristics
- The only invariant that fires on actor identity rather than action content
- Valid handoff actions are the boundary condition — the compiler must define what constitutes a legitimate transfer event
- Cross-domain: the pattern of unauthorized actor substitution is structurally identical whether it is a process identity swap in a syscall session, an agent substitution in an orchestration pipeline, or an unauthorized command transfer in an incident response

### Combinations
- EXIT + JURISDICTION: can co-occur when the new actor also performs an action outside their permitted class. Documented in combinatorial harness C03.

---

## Invariant 5 — HYSTERESIS

### Definition
After an ORDER or JURISDICTION violation occurred, the workflow continued to expand into new, previously unvisited territory rather than halting or reverting. The violation did not arrest the trajectory — the system kept going.

### Structural Signature
HYSTERESIS has a dependency signature unique among the five invariants: it cannot fire without a prior ORDER or JURISDICTION violation in the same session. This dependency is the defining structural characteristic. A clean trajectory that expands into new territory does not produce HYSTERESIS. Only a trajectory that expands into new territory *after a prior violation* produces HYSTERESIS.

The detection mechanism: the compiler tracks whether ORDER or JURISDICTION has fired in the session. If yes, and if the actor then visits a state not previously visited, HYSTERESIS fires.

### Confirmed Domain Appearances

| Domain | Context | Type | Date Confirmed |
|--------|---------|------|---------------|
| Cyber — syscall layer | Post-ORDER expansion into new file system territory | Synthetic harness | May 13, 2026 |
| Agentic — tool-call layer | Post-JURISDICTION expansion into new tool invocation territory | Synthetic harness | May 15, 2026 |
| Org workflow — human decision layer | Post-ORDER expansion into RECOMMENDING stage without completing ASSESSING | Synthetic harness | May 16, 2026 |
| Financial (hypothesized) | Post-JURISDICTION trading activity continuing to expand into new instrument classes (2008 crisis) | Incident hypothesis — not yet harness-tested | May 19, 2026 |

### Distinguishing Characteristics
- The only dependent invariant — requires prior ORDER or JURISDICTION to fire
- Never fires on a clean trajectory regardless of how far it expands
- This dependency structure is the strongest falsification target: if HYSTERESIS fired without a prior violation, the compiler design would have a critical bug
- Structural meaning: HYSTERESIS captures the failure mode where a violation-compromised system continues operating as if the violation hadn't occurred, compounding the structural damage

### Combinations
- ORDER/JURISDICTION → HYSTERESIS: the standard compound pattern. First violation opens the dependency window. HYSTERESIS fires on the next novel state entry.
- HYSTERESIS does not fire alongside BURST_CADENCE or EXIT without a prior ORDER or JURISDICTION in the same session.

---

## Cross-Invariant Structural Notes

### The Independence Property
The five invariants are structurally independent. Each has a distinct detection mechanism. When multiple invariants fire in the same session, they do so without coupling — one invariant firing does not suppress or trigger another. This has been confirmed in every combinatorial harness Block C test across all three substrates.

### The Failure Signature Taxonomy
The five invariants produce five structurally distinct failure signatures:

| Invariant | Detection Mechanism | Key Distinguishing Feature |
|-----------|--------------------|-----------------------------|
| ORDER | State-action mismatch | Authorized actor, wrong sequence |
| JURISDICTION | Role-action mismatch | Correct sequence possible, wrong role |
| BURST_CADENCE | Transition rate anomaly | Time-sensitive, no role/sequence error required |
| EXIT | Actor identity mismatch | Who, not what — ownership violation |
| HYSTERESIS | Post-violation expansion | Dependent — never fires clean |

### The Multi-Compiler Boundary Problem (Open Research)
When two independently valid compilers interact, violations can occur at the handoff boundary rather than within either compiler. Tenerife is the canonical example — the ATC compiler and the cockpit compiler were each internally coherent; the violation lived at the boundary between them. This is an open research problem (see Master Domain Registry, R1). The Invariance Library will document boundary signatures when the multi-compiler interaction research produces results.

---

## Entry Protocol

When a new substrate is confirmed on hardware, add entries to the Confirmed Domain Appearances tables for each invariant that fired. Include:
- Domain name
- Context description — what scenario produced the firing
- Type: Synthetic harness / Incident-derived / Real data
- Date confirmed

When an incident-derived Structural Finding is produced, add entries to the hypothesized rows or create confirmed rows. Update Type from "Incident hypothesis" to "Incident-derived confirmed" once the synthetic scenarios have been harness-tested.

---

*Library scope: cumulative research record. Updated in place with timestamps. Version increments on structural changes to the library format, not on individual entry additions.*
