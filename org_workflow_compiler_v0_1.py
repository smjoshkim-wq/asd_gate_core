"""
Organizational Workflow Compiler v0.1 — Semantic Transaction Protocol
for Human Decision Pipelines
═══════════════════════════════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
    The gate kernel is structurally identical to the cyber and agentic
    compilers. No workflow-specific logic exists in the gate.
Layer 2 (Compiler): this module. Maps organizational workflow events
    (actor_id, action, workflow_id) to the gate's BAS_Metrics vocabulary.
    The compiler is the only thing that changes between domains.

What this module instantiates
─────────────────────────────
- ORG_ACTION_CLASS_MAP   : action name → semantic class (A1..A5)
- ORG_ROLE_TABLE         : actor_id → role
- ORG_PERMITTED_FLOWS    : per-role workflow state graph
- OrgTracker             : minimal mirror of v0.9 TrajectoryTracker,
                           evaluates against ORG_PERMITTED_FLOWS
- OrgWorkflowCompiler    : .compile(raw_event) → packet for evaluate_gate

Substrate notes
───────────────
This substrate is NOT computational. The actors are humans making decisions
in a structured pipeline. The events are approvals, assessments, and
authorizations — not syscalls, not tool calls.

The organizational substrate exposes three primitives per event:
  - actor_id    : who is acting (human identity in the pipeline)
  - action      : what they did (e.g., "review_request", "approve_payment")
  - workflow_id : the pipeline instance they belong to
                  (analogous to session ARN in cyber, session_id in agentic)

The compiler maps:
  action      → action class (A1..A5) via ORG_ACTION_CLASS_MAP
  actor_id    → role          via ORG_ROLE_TABLE
  workflow_id → source_ref    (for actor pivot detection)

Action class taxonomy (five classes, ordered by consequence weight):
  A1 (Review)     — read/examine, reversible
  A2 (Assess)     — evaluate/analyze, reversible
  A3 (Recommend)  — non-binding opinion, reversible
  A4 (Authorize)  — binding decision, irreversible once committed
  A5 (Execute)    — terminal action, highest consequence

A5 is intentionally NOT in any role's permitted set. Any actor calling
an A5 action fires JURISDICTION by construction. This is the structural
analog to T5_Execution in the agentic compiler.

Role registry:
  Analyst  → A1, A2, A3 (review, assess, recommend — cannot authorize)
  Approver → A4 only    (authorize — nothing else)

This maps the classic compliance constraint: "the analyst cannot authorize
payment." That constraint is not a learned rule — it is structural.

Workflow state graph (Analyst):
  IDLE → REVIEWING → ASSESSING → RECOMMENDING
  With loop-backs:
    REVIEWING → REVIEWING (continue reviewing, via A1)
    ASSESSING → REVIEWING (loop back for more data, via A1)
    ASSESSING → ASSESSING (continue assessing, via A2)
    RECOMMENDING → RECOMMENDING (continue recommending, via A3)

Workflow state graph (Approver):
  IDLE → AUTHORIZING → AUTHORIZING (loop)

State widths (for BURST_CADENCE):
  Analyst.IDLE          = 1   (A1 only)
  Analyst.REVIEWING     = 2   (A1, A2)
  Analyst.ASSESSING     = 3   (A1, A2, A3)
  Analyst.RECOMMENDING  = 1   (A3 only)
  Approver.IDLE         = 1   (A4 only)
  Approver.AUTHORIZING  = 1   (A4 only)

ORDER opportunities (action in role, wrong state):
  A2 from IDLE         (A2 in role, not in IDLE.flows)
  A3 from IDLE         (A3 in role, not in IDLE.flows)
  A3 from REVIEWING    (A3 in role, not in REVIEWING.flows)  ← used in tests
  A1 from RECOMMENDING (A1 in role, not in RECOMMENDING.flows)
  A2 from RECOMMENDING (A2 in role, not in RECOMMENDING.flows)

JURISDICTION opportunities:
  A4 or A5 from Analyst (not in Analyst vocabulary)
  A1, A2, A3, A5 from Approver (not in Approver vocabulary)
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
# Action class taxonomy
# ═══════════════════════════════════════════════════════════════════════

ORG_ACTION_CLASS_MAP: Dict[str, str] = {
    # A1 — Review (read/examine, reversible)
    "review_request":     "A1_Review",
    "read_document":      "A1_Review",
    "check_status":       "A1_Review",
    "view_record":        "A1_Review",
    # A2 — Assess (evaluate/analyze, reversible)
    "assess_risk":        "A2_Assess",
    "evaluate_compliance":"A2_Assess",
    "score_application":  "A2_Assess",
    "check_eligibility":  "A2_Assess",
    # A3 — Recommend (non-binding opinion, reversible)
    "recommend_approval": "A3_Recommend",
    "flag_concern":       "A3_Recommend",
    "escalate":           "A3_Recommend",
    "add_note":           "A3_Recommend",
    # A4 — Authorize (binding decision, irreversible)
    "approve_payment":    "A4_Authorize",
    "sign_contract":      "A4_Authorize",
    "authorize_release":  "A4_Authorize",
    "grant_access":       "A4_Authorize",
    # A5 — Execute (terminal action, not in any role)
    "transfer_funds":     "A5_Execute",
    "release_shipment":   "A5_Execute",
    "publish_decision":   "A5_Execute",
    "delete_record":      "A5_Execute",
}


def resolve_action_class(action: str) -> str:
    """Map a raw action name to its semantic class. Unknown → 'UNKNOWN'."""
    return ORG_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry (actor_id → role)
# ═══════════════════════════════════════════════════════════════════════

ORG_ROLE_TABLE: Dict[str, str] = {
    "analyst_alice":   "Analyst",
    "analyst_bob":     "Analyst",
    "analyst_carol":   "Analyst",
    "approver_dave":   "Approver",
    "approver_eve":    "Approver",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    """Map actor_id to role. Default: Analyst (most constrained safe default)."""
    if not actor_id:
        return "Analyst"
    return ORG_ROLE_TABLE.get(actor_id, "Analyst")


# ═══════════════════════════════════════════════════════════════════════
# Workflow state graph (ORG_PERMITTED_FLOWS)
# ═══════════════════════════════════════════════════════════════════════

ORG_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
    "Analyst": {
        "IDLE": {
            "A1_Review":    ("REVIEWING",     Encapsulation.SURFACE.value),
        },
        "REVIEWING": {
            "A1_Review":    ("REVIEWING",     Encapsulation.SURFACE.value),
            "A2_Assess":    ("ASSESSING",     Encapsulation.MID.value),
        },
        "ASSESSING": {
            "A1_Review":    ("REVIEWING",     Encapsulation.MID.value),
            "A2_Assess":    ("ASSESSING",     Encapsulation.MID.value),
            "A3_Recommend": ("RECOMMENDING",  Encapsulation.MID.value),
        },
        "RECOMMENDING": {
            "A3_Recommend": ("RECOMMENDING",  Encapsulation.MID.value),
        },
    },
    "Approver": {
        "IDLE": {
            "A4_Authorize": ("AUTHORIZING",   Encapsulation.SURFACE.value),
        },
        "AUTHORIZING": {
            "A4_Authorize": ("AUTHORIZING",   Encapsulation.MID.value),
        },
    },
}

ORG_FLOW_START_STATE: Dict[str, str] = {
    "Analyst":  "IDLE",
    "Approver": "IDLE",
}

ORG_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Analyst": {
        "IDLE":         1,
        "REVIEWING":    2,
        "ASSESSING":    3,
        "RECOMMENDING": 1,
    },
    "Approver": {
        "IDLE":         1,
        "AUTHORIZING":  1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# OrgTracker — minimal mirror of v0.9 TrajectoryTracker
# ═══════════════════════════════════════════════════════════════════════

class OrgTracker:

    def __init__(self) -> None:
        # State machine
        self._states:           Dict[Tuple[str, str], str]               = {}
        self._history:          Dict[Tuple[str, str], List[Tuple]]       = {}
        # Role and session registries (for EXIT detection)
        self._role_registry:    Dict[str, str]                           = {}
        self._session_registry: Dict[str, str]                           = {}
        # Burst cadence
        self._width_history:    Dict[str, List[Tuple[int, int]]]         = {}
        self._timed_widths:     Dict[str, List[Tuple[float, int, int]]]  = {}
        # Hysteresis (v0.9)
        self._violation_history: Dict[str, bool]                         = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]         = {}

    def _key(self, identity: str, role: str) -> Tuple[str, str]:
        return (identity, role)

    def current_state(self, identity: str, role: str) -> str:
        key = self._key(identity, role)
        return self._states.get(key, ORG_FLOW_START_STATE.get(role, "IDLE"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return ORG_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        """Returns True if identity has been seen under a different role."""
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, workflow_id: str) -> bool:
        """Returns True if workflow_id has been used by a different identity."""
        if workflow_id in self._session_registry:
            return self._session_registry[workflow_id] != identity
        self._session_registry[workflow_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        """
        Core state machine evaluation. Parallel to v0.9 TrajectoryTracker.evaluate().
        Returns traj_context dict compatible with evaluate_gate packet construction.
        """
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = ORG_PERMITTED_FLOWS.get(role, {})

        # Determine if action is in the role at all
        action_in_role = any(
            action in state_flows
            for state_flows in role_flows.values()
        )

        state_flows   = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            # JURISDICTION: action not in this role's vocabulary anywhere
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           ORG_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": True,
                "role_confusion":         False,
                "actor_pivot":            False,
                "hysteresis_violation":   False,
            }

        if not action_in_state:
            # ORDER: action in role but not valid from current state
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           ORG_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        True,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
                "hysteresis_violation":   False,
            }

        # ADMISSIBLE: advance state machine
        to_state, encap = state_flows[action]
        self._states[key] = to_state

        # Record visited state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = ORG_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = ORG_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

        if key not in self._history:
            self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {
            "admissible":             True,
            "from_state":             from_state,
            "to_state":               to_state,
            "encapsulation":          encap,
            "width_before":           w_before,
            "width_after":            w_after,
            "exposure_event":         False,
            "order_violation":        False,
            "jurisdiction_violation": False,
            "role_confusion":         False,
            "actor_pivot":            False,
            "hysteresis_violation":   False,
        }

    def record_width(self, identity: str, w_before: int, w_after: Optional[int],
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
            now    = current_time if current_time is not None else time.time()
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
        role_flows  = ORG_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# OrgWorkflowCompiler — Layer 2 dictionary for the org workflow substrate
# ═══════════════════════════════════════════════════════════════════════

class OrgWorkflowCompiler:

    def __init__(self) -> None:
        self.tracker = OrgTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Convert a raw organizational workflow event to a BAS_Metrics packet
        ready for evaluate_gate().

        Expected raw_event shape:
            {
                "actor_id":    str,    # e.g. "analyst_alice", "approver_dave"
                "action":      str,    # e.g. "review_request", "approve_payment"
                "workflow_id": str,    # pipeline instance identifier
                "timestamp":   float,  # optional, defaults to time.time()
            }
        """
        actor_id    = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw  = raw_event.get("action", "")
        workflow_id = raw_event.get("workflow_id", "default_workflow")
        event_ts    = raw_event.get("timestamp")

        identity_label = actor_id
        role           = resolve_role(actor_id)
        action         = resolve_action_class(action_raw)

        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN":
            resolution = ResolutionStatus.PARTIAL.value

        is_known       = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = False
        actor_pivot    = False

        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, workflow_id)

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
                "hysteresis_violation":   False,
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
                "exposure_event":         False,
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
                "hysteresis_violation":   False,
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
            "RawAction":    action_raw,
            "WorkflowID":   workflow_id,
            "FromState":    traj_context.get("from_state"),
            "ToState":      traj_context.get("to_state"),
        }

        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header":  stp_header,
        }
