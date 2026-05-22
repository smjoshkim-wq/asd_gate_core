"""
Emergency Response Compiler v0.1 — FEMA ICS / NIMS
════════════════════════════════════════════════════════════════════════
Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps ICS incident response events
    (actor_id, action, incident_id) to the gate's BAS_Metrics vocabulary.

Domain: Multi-agency incident response under NIMS/ICS doctrine.
Regulatory sources: FEMA ICS-100/200/300/400, DHS NIMS 2017,
    FEMA NRF 2019, CFR Title 44.

Action class taxonomy (seven classes):
    AC1 (Assessment)     — situational assessment, size-up; all roles
    AC2 (Planning)       — IAP drafting, planning meetings; IC only
    AC3 (ResourceOrder)  — mutual aid requests, EMAC; excluded from IC by
                           construction (routes through Logistics section)
    AC4 (Execution)      — tactical deployment, SAR, evacuation; IC/OSC/Field
    AC5 (CommandTransfer)— Unified Command activation, command transfer;
                           IC only (requires multi-agency Administrator
                           consensus — excluded from all others by construction)
    AC6 (PublicComm)     — public warnings, press conferences; IC only
    AC7 (Demobilization) — releasing resources, closing staging; IC/OSC only

Role registry:
    IC             → AC1, AC2, AC4, AC5, AC6, AC7   (AC3 excluded)
    OSC            → AC1, AC4                         (strategic/comms excluded)
    Field_Resource → AC4 only                         (all others excluded)

Incident anchor: Hurricane Katrina 2005
    ORDER:      IC deployed resources (AC4) from PLANNING state before
                Unified Command gate (AC5→UNIFIED_COMMAND) was passed —
                ICS_ACTIVATION directly to EXPANDED_OPERATIONS, skipping
                UNIFIED_COMMAND. AC4 in IC vocabulary, PLANNING.flows
                does not contain AC4 → ORDER fires at A01.
    JURISDICTION: Field_Resource called AC5 (command transfer) — AC5 not
                in Field_Resource vocabulary → JURISDICTION at A02.
    BURST_CADENCE: Parallel resource ordering channels — IC oscillates
                ASSESSMENT(2)↔PLANNING(3) rapidly → BURST at A03.

State machine widths:
    IC:    STANDBY(1)→ASSESSMENT(2)→PLANNING(3)→UNIFIED_COMMAND(4)→
           OPERATIONS(4)→DEMOBILIZATION(1)
    OSC:   STANDBY(1)→ASSESSMENT(2)→EXECUTING(2)
    Field_Resource: STANDBY(1)→EXECUTING(1)
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

FEMA_ACTION_CLASS_MAP: Dict[str, str] = {
    # AC1 — Situational Assessment (unrestricted — all roles)
    "conduct_size_up":           "AC1_Assessment",
    "monitor_telemetry":         "AC1_Assessment",
    "assess_resources":          "AC1_Assessment",
    "verify_incident_scope":     "AC1_Assessment",
    # AC2 — Incident Action Planning
    "draft_objectives":          "AC2_Planning",
    "conduct_planning_meeting":  "AC2_Planning",
    "approve_iap":               "AC2_Planning",
    "update_iap":                "AC2_Planning",
    # AC3 — Resource Request and Ordering (excluded from IC)
    "request_mutual_aid":        "AC3_ResourceOrder",
    "order_heavy_equipment":     "AC3_ResourceOrder",
    "submit_emac_request":       "AC3_ResourceOrder",
    "escalate_resource_request": "AC3_ResourceOrder",
    # AC4 — Operational Execution and Deployment
    "deploy_strike_team":        "AC4_Execution",
    "conduct_search_rescue":     "AC4_Execution",
    "execute_evacuation":        "AC4_Execution",
    "assign_division":           "AC4_Execution",
    # AC5 — Command Transfer / Unified Command (IC only)
    "transfer_command":          "AC5_CommandTransfer",
    "activate_unified_command":  "AC5_CommandTransfer",
    "establish_area_command":    "AC5_CommandTransfer",
    # AC6 — Public Communication (IC only)
    "issue_public_warning":      "AC6_PublicComm",
    "hold_press_conference":     "AC6_PublicComm",
    "release_situation_report":  "AC6_PublicComm",
    # AC7 — Demobilization
    "release_strike_team":       "AC7_Demobilization",
    "close_staging_area":        "AC7_Demobilization",
    "deactivate_eoc":            "AC7_Demobilization",
}


def resolve_action_class(action: str) -> str:
    return FEMA_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

FEMA_ROLE_TABLE: Dict[str, str] = {
    "ic_thompson":    "IC",
    "ic_rodriguez":   "IC",
    "ic_washington":  "IC",
    "osc_williams":   "OSC",
    "osc_chen":       "OSC",
    "resource_team1": "Field_Resource",
    "resource_team2": "Field_Resource",
    "resource_team3": "Field_Resource",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    """Default: Field_Resource (most constrained — AC4 only)."""
    if not actor_id:
        return "Field_Resource"
    return FEMA_ROLE_TABLE.get(actor_id, "Field_Resource")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

_S = Encapsulation.SURFACE.value
_M = Encapsulation.MID.value

FEMA_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
    "IC": {
        "STANDBY": {
            "AC1_Assessment":     ("ASSESSMENT",      _S),
        },
        "ASSESSMENT": {
            "AC1_Assessment":     ("ASSESSMENT",      _M),
            "AC2_Planning":       ("PLANNING",        _M),
        },
        "PLANNING": {
            "AC1_Assessment":     ("ASSESSMENT",      _M),
            "AC2_Planning":       ("PLANNING",        _M),
            "AC5_CommandTransfer": ("UNIFIED_COMMAND", _M),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment":     ("UNIFIED_COMMAND", _M),
            "AC2_Planning":       ("UNIFIED_COMMAND", _M),
            "AC5_CommandTransfer": ("UNIFIED_COMMAND", _M),
            "AC4_Execution":      ("OPERATIONS",      _M),
        },
        "OPERATIONS": {
            "AC1_Assessment":     ("OPERATIONS",      _M),
            "AC4_Execution":      ("OPERATIONS",      _M),
            "AC6_PublicComm":     ("OPERATIONS",      _M),
            "AC7_Demobilization": ("DEMOBILIZATION",  _M),
        },
        "DEMOBILIZATION": {
            "AC7_Demobilization": ("DEMOBILIZATION",  _M),
        },
    },
    "OSC": {
        "STANDBY": {
            "AC1_Assessment":     ("ASSESSMENT",      _S),
        },
        "ASSESSMENT": {
            "AC1_Assessment":     ("ASSESSMENT",      _M),
            "AC4_Execution":      ("EXECUTING",       _M),
        },
        "EXECUTING": {
            "AC1_Assessment":     ("ASSESSMENT",      _M),
            "AC4_Execution":      ("EXECUTING",       _M),
        },
    },
    "Field_Resource": {
        "STANDBY": {
            "AC4_Execution":      ("EXECUTING",       _S),
        },
        "EXECUTING": {
            "AC4_Execution":      ("EXECUTING",       _M),
        },
    },
}

FEMA_FLOW_START_STATE: Dict[str, str] = {
    "IC":             "STANDBY",
    "OSC":            "STANDBY",
    "Field_Resource": "STANDBY",
}

FEMA_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "IC": {
        "STANDBY":         1,
        "ASSESSMENT":      2,
        "PLANNING":        3,
        "UNIFIED_COMMAND": 4,
        "OPERATIONS":      4,
        "DEMOBILIZATION":  1,
    },
    "OSC": {
        "STANDBY":    1,
        "ASSESSMENT": 2,
        "EXECUTING":  2,
    },
    "Field_Resource": {
        "STANDBY":  1,
        "EXECUTING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# FEMATracker
# ═══════════════════════════════════════════════════════════════════════

class FEMATracker:

    def __init__(self) -> None:
        self._states:            Dict[Tuple[str, str], str]               = {}
        self._history:           Dict[Tuple[str, str], List[Tuple]]       = {}
        self._role_registry:     Dict[str, str]                           = {}
        self._session_registry:  Dict[str, str]                           = {}
        self._width_history:     Dict[str, List[Tuple[int, int]]]         = {}
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]]  = {}
        self._violation_history: Dict[str, bool]                          = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]          = {}

    def _key(self, identity: str, role: str) -> Tuple[str, str]:
        return (identity, role)

    def current_state(self, identity: str, role: str) -> str:
        key = self._key(identity, role)
        return self._states.get(key, FEMA_FLOW_START_STATE.get(role, "STANDBY"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return FEMA_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, incident_id: str) -> bool:
        if incident_id in self._session_registry:
            return self._session_registry[incident_id] != identity
        self._session_registry[incident_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = FEMA_PERMITTED_FLOWS.get(role, {})

        action_in_role  = any(action in sf for sf in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": FEMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": False, "jurisdiction_violation": True,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        if not action_in_state:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": FEMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": True, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = FEMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = FEMA_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {
            "admissible": True, "from_state": from_state, "to_state": to_state,
            "encapsulation": encap, "width_before": w_before, "width_after": w_after,
            "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
            "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
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
        if not self._violation_history.get(identity):
            return False
        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False
        role_flows  = FEMA_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# FEMACompiler
# ═══════════════════════════════════════════════════════════════════════

class FEMACompiler:

    def __init__(self) -> None:
        self.tracker = FEMATracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Expected raw_event shape:
            {
                "actor_id":    str,
                "action":      str,
                "incident_id": str,
                "timestamp":   float  (optional)
            }
        """
        actor_id    = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw  = raw_event.get("action", "")
        incident_id = raw_event.get("incident_id", "default_incident")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, incident_id)

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
            if self.tracker.check_hysteresis(identity_label, role, action):
                cur = self.tracker.current_state(identity_label, role)
                traj_context = {
                    "admissible": False, "from_state": cur, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": self.tracker.width_at_current_state(identity_label, role),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": True,
                }
            else:
                traj_context = self.tracker.evaluate(identity_label, role, action)
        elif role_confusion or actor_pivot:
            traj_context = {
                "admissible": False,
                "from_state": self.tracker.current_state(identity_label, role),
                "to_state": None, "encapsulation": Encapsulation.DEEP.value,
                "width_before": self.tracker.width_at_current_state(identity_label, role),
                "width_after": None, "exposure_event": True,
                "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": role_confusion, "actor_pivot": actor_pivot,
                "hysteresis_violation": False,
            }
        else:
            traj_context = {
                "admissible": False,
                "from_state": self.tracker.current_state(identity_label, role),
                "to_state": None, "encapsulation": Encapsulation.DEEP.value,
                "width_before": self.tracker.width_at_current_state(identity_label, role),
                "width_after": None, "exposure_event": False,
                "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

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
            "Resolution":  {"Completeness": resolution},
            "Identity":    identity_label,
            "Role":        role,
            "Action":      action,
            "RawAction":   action_raw,
            "IncidentID":  incident_id,
            "FromState":   traj_context.get("from_state"),
            "ToState":     traj_context.get("to_state"),
        }

        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events: list) -> list:
    compiler = FEMACompiler()
    return [evaluate_gate(compiler.compile(e)) for e in events]
