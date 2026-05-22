"""
AI-STP Agentic Compiler v0.1 — Semantic Transaction Protocol for Agentic Systems
═══════════════════════════════════════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
    The gate kernel is structurally identical to the cyber compiler.
    No agentic-specific logic exists in the gate.
Layer 2 (Compiler): this module. Maps agentic events (agent_id, tool, session)
    to the gate's BAS_Metrics vocabulary.
    The compiler is the only thing that changes between domains.

What this module instantiates
─────────────────────────────
- AGENTIC_TOOL_CLASS_MAP   : tool name → semantic class (T1..T5)
- AGENTIC_ROLE_TABLE        : agent_id → role
- AGENTIC_PERMITTED_FLOWS   : per-role workflow state graph
- AgentTracker              : minimal mirror of v0.9 TrajectoryTracker,
                              evaluates against AGENTIC_PERMITTED_FLOWS
- AgenticCompiler           : .compile(raw_event) → packet for evaluate_gate

Substrate notes
───────────────
The agentic substrate exposes three primitives per event:
  - agent_id        : who is acting (carried in orchestration context)
  - tool            : what they are about to call (typed signature)
  - session_id      : the orchestration container they belong to
                      (analog: source IP / session ARN in cyber)

The compiler maps:
  tool      → tool class (T1..T5) via AGENTIC_TOOL_CLASS_MAP
  agent_id  → role        via AGENTIC_ROLE_TABLE
  session   → source_ref  (for actor pivot detection)

T5 (Execution) is intentionally not in any role's permitted set. Any agent
calling a T5 tool fires JURISDICTION by construction.
"""

from __future__ import annotations
import time
from typing import Dict, List, Optional, Set, Tuple

from domain_compiler_v0_9 import (
    evaluate_gate,
    Encapsulation,
    ResolutionStatus,
    BURST_TIME_WINDOW_SECONDS,
    BURST_THRESHOLD,
    BURST_WINDOW,
)


# ═══════════════════════════════════════════════════════════════════════
# Tool class taxonomy (the agentic equivalent of CloudTrail action map)
# ═══════════════════════════════════════════════════════════════════════

# Tool name → semantic class. Five classes, ordered by consequence weight:
#   T1 (Retrieval)     — read-only, reversible
#   T2 (Synthesis)     — transform, reversible
#   T3 (Verification)  — validate, reversible
#   T4 (Delivery)      — external commitment, irreversible once sent
#   T5 (Execution)     — system-level action, highest consequence
#
# T5 is in NO role's permitted set — see AGENTIC_PERMITTED_FLOWS.
AGENTIC_TOOL_CLASS_MAP: Dict[str, str] = {
    # T1 — Retrieval
    "web_search":       "T1_Retrieval",
    "file_read":        "T1_Retrieval",
    "database_query":   "T1_Retrieval",
    "list_files":       "T1_Retrieval",
    # T2 — Synthesis
    "summarize":        "T2_Synthesis",
    "draft_document":   "T2_Synthesis",
    "translate":        "T2_Synthesis",
    "compose_response": "T2_Synthesis",
    # T3 — Verification
    "fact_check":       "T3_Verification",
    "cross_reference":  "T3_Verification",
    "validate":         "T3_Verification",
    "audit":            "T3_Verification",
    # T4 — Delivery
    "send_email":       "T4_Delivery",
    "publish_post":     "T4_Delivery",
    "post_api":         "T4_Delivery",
    "deliver_report":   "T4_Delivery",
    # T5 — Execution (not in any role)
    "run_code":         "T5_Execution",
    "modify_file":      "T5_Execution",
    "exec_command":     "T5_Execution",
    "system_call":      "T5_Execution",
}


def resolve_tool_class(tool: str) -> str:
    """Map a raw tool name to its semantic class. Unknown tools → 'UNKNOWN'."""
    return AGENTIC_TOOL_CLASS_MAP.get(tool, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry (agent_id → role)
# ═══════════════════════════════════════════════════════════════════════

AGENTIC_ROLE_TABLE: Dict[str, str] = {
    "research_agent_1":  "ResearchAgent",
    "research_agent_2":  "ResearchAgent",
    "research_agent_3":  "ResearchAgent",
    "delivery_agent_1":  "DeliveryAgent",
    "delivery_agent_2":  "DeliveryAgent",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(agent_id: str) -> str:
    """Map agent_id to role. Default: ResearchAgent (most constrained safe default)."""
    if not agent_id:
        return "ResearchAgent"   # fallback — least-privilege default
    return AGENTIC_ROLE_TABLE.get(agent_id, "ResearchAgent")


# ═══════════════════════════════════════════════════════════════════════
# Workflow state graph (agentic PERMITTED_FLOWS)
# ═══════════════════════════════════════════════════════════════════════
#
# Per-role state machine. Each role has its own start state and its own
# permitted action map.
#
# ResearchAgent flow:
#   IDLE → GATHERING → SYNTHESIZING → VERIFYING
#   With permitted loop-backs:
#     - GATHERING → GATHERING (continue gathering, via T1)
#     - SYNTHESIZING → GATHERING (loop back for more data, via T1)
#     - SYNTHESIZING → SYNTHESIZING (continue synthesizing, via T2)
#     - VERIFYING → VERIFYING (continue verifying, via T3)
#
# DeliveryAgent flow:
#   IDLE → DELIVERING (and terminal)
#
# Widths (used for BURST_CADENCE):
#   ResearchAgent.IDLE          = 1   (T1 only)
#   ResearchAgent.GATHERING     = 2   (T1, T2)
#   ResearchAgent.SYNTHESIZING  = 3   (T1, T2, T3)
#   ResearchAgent.VERIFYING     = 1   (T3 only)
#   DeliveryAgent.IDLE          = 1   (T4 only)
#   DeliveryAgent.DELIVERING    = 1   (T4 only)
#
# ORDER opportunities in ResearchAgent:
#   T2 from IDLE         (T2 in role, not in IDLE.flows)
#   T3 from IDLE         (T3 in role, not in IDLE.flows)
#   T3 from GATHERING    (T3 in role, not in GATHERING.flows)   ← used in tests
#   T2 from VERIFYING    (T2 in role, not in VERIFYING.flows)
#   T1 from VERIFYING    (T1 in role, not in VERIFYING.flows)
#
# JURISDICTION opportunities:
#   T4 or T5 from any state, ResearchAgent (T4, T5 not in role)
#   T1, T2, T3, T5 from any state, DeliveryAgent

AGENTIC_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
    "ResearchAgent": {
        "IDLE": {
            "T1_Retrieval":    ("GATHERING",     Encapsulation.SURFACE.value),
        },
        "GATHERING": {
            "T1_Retrieval":    ("GATHERING",     Encapsulation.SURFACE.value),
            "T2_Synthesis":    ("SYNTHESIZING",  Encapsulation.MID.value),
        },
        "SYNTHESIZING": {
            "T1_Retrieval":    ("GATHERING",     Encapsulation.MID.value),
            "T2_Synthesis":    ("SYNTHESIZING",  Encapsulation.MID.value),
            "T3_Verification": ("VERIFYING",     Encapsulation.MID.value),
        },
        "VERIFYING": {
            "T3_Verification": ("VERIFYING",     Encapsulation.MID.value),
        },
    },
    "DeliveryAgent": {
        "IDLE": {
            "T4_Delivery":     ("DELIVERING",    Encapsulation.SURFACE.value),
        },
        "DELIVERING": {
            "T4_Delivery":     ("DELIVERING",    Encapsulation.MID.value),
        },
    },
}


AGENTIC_FLOW_START_STATE: Dict[str, str] = {
    "ResearchAgent": "IDLE",
    "DeliveryAgent": "IDLE",
}


# ═══════════════════════════════════════════════════════════════════════
# AgentTracker — mirrors v0.9 TrajectoryTracker for the agentic substrate
# ═══════════════════════════════════════════════════════════════════════
#
# Same API surface as v0.9 TrajectoryTracker, but evaluates against
# AGENTIC_PERMITTED_FLOWS. The state-machine logic and the hysteresis
# logic are copied verbatim (parallel implementation), not subclassed —
# this is the cleanest way to demonstrate that the same structural
# evaluation works on different flows.

class AgentTracker:

    def __init__(self) -> None:
        self._states:            Dict[Tuple[str, str], str]              = {}
        self._history:           Dict[Tuple[str, str], list]             = {}
        self._role_registry:     Dict[str, str]                          = {}
        self._session_to_agent:  Dict[str, str]                          = {}
        self._width_history:     Dict[str, List[Tuple[int, int]]]        = {}
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]] = {}
        # Hysteresis: parallel to v0.9 implementation
        self._violation_history: Dict[str, bool]                         = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]         = {}

    def _key(self, identity: str, role: str) -> Tuple[str, str]:
        return (identity, role)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            return False
        prior = self._role_registry.get(identity)
        if prior is None:
            self._role_registry[identity] = role
            return False
        return prior != role

    def check_actor_pivot(self, identity: str, source_ref: str) -> bool:
        """
        Agentic actor pivot: same orchestration session presents with a
        different agent_id than previously registered for that session.
        """
        if identity in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            return False
        if not source_ref or source_ref in ("UNKNOWN", "", "default_session"):
            # default_session is a sentinel that suppresses pivot detection
            # for tests that don't exercise EXIT — same convention as cyber
            # tests using the default IP for single-actor scenarios.
            # Single-actor tests still need a session for the compiler to
            # function; "default_session" means "don't bind this session".
            if source_ref == "default_session":
                # Bind once but allow same-identity reuse on default
                prior = self._session_to_agent.get(source_ref)
                if prior is None:
                    self._session_to_agent[source_ref] = identity
                    return False
                return prior != identity
            return False
        prior = self._session_to_agent.get(source_ref)
        if prior is None:
            self._session_to_agent[source_ref] = identity
            return False
        return prior != identity

    def current_state(self, identity: str, role: str) -> str:
        return self._states.get(
            self._key(identity, role),
            AGENTIC_FLOW_START_STATE.get(role, "IDLE")
        )

    def width_at_current_state(self, identity: str, role: str) -> int:
        state       = self.current_state(identity, role)
        role_flows  = AGENTIC_PERMITTED_FLOWS.get(role, {})
        state_flows = role_flows.get(state, {})
        return len(state_flows)

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key          = self._key(identity, role)
        from_state   = self.current_state(identity, role)
        role_flows   = AGENTIC_PERMITTED_FLOWS.get(role, {})
        state_flows  = role_flows.get(from_state, {})
        width_before = len(state_flows)
        action_in_role = any(action in s for s in role_flows.values())

        if action in state_flows:
            to_state, enc = state_flows[action]
            self._states[key] = to_state
            next_flows  = role_flows.get(to_state, {})
            width_after = len(next_flows)
            if key not in self._history:
                self._history[key] = []
            self._history[key].append((action, from_state, to_state))
            # Record visited state (admissible path only)
            if key not in self._visited_states:
                self._visited_states[key] = set()
            self._visited_states[key].add(to_state)
            return {
                "admissible":             True,
                "from_state":             from_state,
                "to_state":               to_state,
                "encapsulation":          enc,
                "width_before":           width_before,
                "width_after":            width_after,
                "exposure_event":         False,
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
            }
        else:
            # Record violation for hysteresis tracking
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           width_before,
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        action_in_role,
                "jurisdiction_violation": not action_in_role,
                "role_confusion":         False,
                "actor_pivot":            False,
            }

    def record_width(self, identity: str, w_before: int, w_after: int,
                     timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history:
            self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths:
            self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity: str,
                            current_time: Optional[float] = None) -> bool:
        """Time-windowed burst detection. Parallel to v0.9 implementation."""
        timed = self._timed_widths.get(identity, [])
        if timed:
            now = current_time if current_time is not None else time.time()
            cutoff = now - BURST_TIME_WINDOW_SECONDS
            window = [(wb, wa) for ts, wb, wa in timed if ts >= cutoff]
            if not window:
                return False
            expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
            return expansions >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW:
            return False
        expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
        return expansions >= BURST_THRESHOLD

    def check_hysteresis(self, identity: str, role: str, action: str) -> bool:
        """
        ASD Invariant 4. Parallel to v0.9 implementation.
        Returns True when ALL three conditions hold:
          1. prior violation recorded
          2. legitimate visited history exists (non-empty)
          3. the action would lead to a state NOT in visited
        """
        if not self._violation_history.get(identity):
            return False
        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False
        role_flows  = AGENTIC_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# AgenticCompiler — Layer 2 dictionary for the agentic substrate
# ═══════════════════════════════════════════════════════════════════════

class AgenticCompiler:

    def __init__(self) -> None:
        self.tracker = AgentTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Convert a raw agentic event to a BAS_Metrics packet ready for
        evaluate_gate().

        Expected raw_event shape:
            {
                "agent_id":   str,
                "tool":       str,
                "session_id": str (optional, defaults to 'default_session'),
                "timestamp":  float (optional, defaults to time.time()),
            }
        """
        agent_id   = raw_event.get("agent_id") or EMPTY_IDENTITY
        tool       = raw_event.get("tool", "")
        session_id = raw_event.get("session_id", "default_session")
        event_ts   = raw_event.get("timestamp")

        # Resolve identity, role, and action class
        identity_label = agent_id
        role           = resolve_role(agent_id)
        action         = resolve_tool_class(tool)

        # INDETERMINATE handling for unknown tools
        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN":
            resolution = ResolutionStatus.PARTIAL.value

        is_known       = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = False
        actor_pivot    = False
        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, session_id)

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
            # Hysteresis BEFORE state machine update — same as v0.9 _core_evaluate
            if self.tracker.check_hysteresis(identity_label, role, action):
                cur = self.tracker.current_state(identity_label, role)
                traj_context = {
                    "admissible":             False,
                    "from_state":             cur,
                    "to_state":               None,
                    "encapsulation":          Encapsulation.DEEP.value,
                    "width_before":           self.tracker.width_at_current_state(
                                                  identity_label, role),
                    "width_after":            None,
                    "exposure_event":         True,
                    "order_violation":        False,
                    "jurisdiction_violation": False,
                    "role_confusion":         False,
                    "actor_pivot":            False,
                    "hysteresis_violation":   True,
                }
            else:
                traj_context = self.tracker.evaluate(identity_label, role, action)
        elif role_confusion or actor_pivot:
            traj_context = {
                "admissible":             False,
                "from_state":             self.tracker.current_state(identity_label, role),
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(
                                              identity_label, role),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         role_confusion,
                "actor_pivot":            actor_pivot,
            }
        else:
            # Unknown action: INDETERMINATE
            traj_context = {
                "admissible":             False,
                "from_state":             self.tracker.current_state(identity_label, role),
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(
                                              identity_label, role),
                "width_after":            None,
                "exposure_event":         False,  # not a violation, just unmappable
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
            }

        # Width recording and BURST_CADENCE check (admissible path only)
        burst_cadence = False
        if traj_context.get("admissible") and traj_context.get("width_after") is not None:
            self.tracker.record_width(
                identity_label,
                traj_context["width_before"],
                traj_context["width_after"],
                timestamp=event_ts,
            )
            burst_cadence = self.tracker.check_burst_cadence(
                identity_label, current_time=event_ts
            )

        # Build packet matching the v0.9 evaluate_gate contract
        bas_metrics = {
            "Admissible":            traj_context.get("admissible", False),
            "ExposureEvent":         traj_context.get("exposure_event", False),
            "OrderViolation":        traj_context.get("order_violation", False),
            "JurisdictionViolation": traj_context.get("jurisdiction_violation", False),
            "RoleConfusion":         traj_context.get("role_confusion", False),
            "ActorPivot":            traj_context.get("actor_pivot", False),
            "HysteresisViolation":   traj_context.get("hysteresis_violation", False),
            "BurstCadence":          burst_cadence,
        }

        stp_header = {
            "Resolution":   {"Completeness": resolution},
            "Identity":     identity_label,
            "Role":         role,
            "Action":       action,
            "Tool":         tool,
            "Session":      session_id,
            "FromState":    traj_context.get("from_state"),
            "ToState":      traj_context.get("to_state"),
        }

        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header":  stp_header,
        }
