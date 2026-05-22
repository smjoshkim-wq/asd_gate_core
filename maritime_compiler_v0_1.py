"""
Maritime Operations Compiler v0.1
════════════════════════════════════════════════════════════════════════
Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps maritime vessel events
    (actor_id, action, voyage_id) to the gate's BAS_Metrics vocabulary.

Domain: Commercial vessel bridge watchkeeping and emergency response.
Regulatory sources: SOLAS 1974 (Chapters III, IV, V), STCW 2010 Manila
    Amendments, ISM Code, COLREGS 1972, IMO Resolution A.1021(26).

Action class taxonomy (six classes):
    M1 (Navigation)     — position monitoring, chart work; all roles
    M2 (Maneuvering)    — course/speed alterations; Master/OOW only
    M3 (Communications) — VTS reports, watch handoffs; Master/OOW only
    M4 (InternalEmergency) — general alarm, muster orders; Master/OOW only
    M5 (DistressSignal) — Mayday/EPIRB/PAN-PAN; Master only
                          (Master-exclusive — excluded from OOW/Helmsman
                           by construction; structural analog to N6/AC5)
    M6 (Evacuation)     — abandon ship order; Master only
                          (Master-exclusive — excluded from all others;
                           the ultimate JURISDICTION boundary in maritime law)

Role registry:
    Master   → M1, M2, M3, M4, M5, M6  (full authority)
    OOW      → M1, M2, M3, M4           (M5, M6 excluded)
    Helmsman → M1 only                  (M2–M6 excluded)

Incident anchor: Costa Concordia 2012
    ORDER (1):      Master calls M6 (abandon_ship_order) from EMERGENCY
                    state — M6 in Master vocabulary, EMERGENCY.flows does
                    not contain M6; must muster first → ORDER at A01.
    JURISDICTION:   OOW calls M6 (order_abandon_ship) — M6 not in OOW
                    vocabulary → JURISDICTION at A02.
    BURST_CADENCE:  Master oscillates MONITORING(2)↔UNDERWAY(3) rapidly —
                    unauthorized course changes → BURST at A03.

State machine widths:
    Master:  STANDBY(1)→MONITORING(2)→UNDERWAY(3)→COASTAL_WATERS(3)→
             EMERGENCY(3)→MUSTER(4)→MAYDAY(3)→ABANDON(1)
    OOW:     STANDBY(1)→MONITORING(2)→UNDERWAY(3)→COASTAL_WATERS(3)→
             EMERGENCY_INTERNAL(2)
    Helmsman: STANDBY(1)→MONITORING(1)
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

MARITIME_ACTION_CLASS_MAP: Dict[str, str] = {
    # M1 — Navigation Monitoring (unrestricted — all roles)
    "plot_position":               "M1_Navigation",
    "monitor_ecdis":               "M1_Navigation",
    "check_radar":                 "M1_Navigation",
    "verify_course":               "M1_Navigation",
    # M2 — Maneuvering (Master/OOW only)
    "alter_course":                "M2_Maneuvering",
    "adjust_speed":                "M2_Maneuvering",
    "execute_collision_avoidance": "M2_Maneuvering",
    "initiate_turn":               "M2_Maneuvering",
    # M3 — Communications (Master/OOW only)
    "report_position_vts":         "M3_Communications",
    "request_port_clearance":      "M3_Communications",
    "conduct_watch_handoff":       "M3_Communications",
    "broadcast_securite":          "M3_Communications",
    # M4 — Internal Emergency (Master/OOW only)
    "sound_general_alarm":         "M4_InternalEmergency",
    "order_muster_stations":       "M4_InternalEmergency",
    "isolate_watertight_doors":    "M4_InternalEmergency",
    "activate_fire_suppression":   "M4_InternalEmergency",
    # M5 — Distress Signaling — Master only
    "transmit_mayday":             "M5_DistressSignal",
    "activate_epirb":              "M5_DistressSignal",
    "broadcast_pan_pan":           "M5_DistressSignal",
    # M6 — Terminal Evacuation — Master only (excluded from all others)
    "order_abandon_ship":          "M6_Evacuation",
    "lower_survival_craft":        "M6_Evacuation",
    "complete_vessel_evacuation":  "M6_Evacuation",
}


def resolve_action_class(action: str) -> str:
    return MARITIME_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

MARITIME_ROLE_TABLE: Dict[str, str] = {
    "master_schettino":  "Master",   # Costa Concordia anchor name
    "master_chang":      "Master",
    "master_okafor":     "Master",
    "oow_harris":        "OOW",
    "oow_kim":           "OOW",
    "oow_santos":        "OOW",
    "helmsman_reyes":    "Helmsman",
    "helmsman_petrov":   "Helmsman",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    """Default: Helmsman (most constrained — M1 only)."""
    if not actor_id:
        return "Helmsman"
    return MARITIME_ROLE_TABLE.get(actor_id, "Helmsman")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

_S = Encapsulation.SURFACE.value
_M = Encapsulation.MID.value

MARITIME_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
    "Master": {
        "STANDBY": {
            "M1_Navigation":       ("MONITORING",        _S),
        },
        "MONITORING": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
        },
        "UNDERWAY": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
            "M3_Communications":   ("COASTAL_WATERS",    _M),
        },
        "COASTAL_WATERS": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
            "M4_InternalEmergency": ("EMERGENCY",        _M),
        },
        "EMERGENCY": {
            "M1_Navigation":       ("EMERGENCY",         _M),
            "M4_InternalEmergency": ("MUSTER",           _M),
            "M5_DistressSignal":   ("MAYDAY",            _M),
        },
        "MUSTER": {
            "M1_Navigation":       ("MUSTER",            _M),
            "M4_InternalEmergency": ("MUSTER",           _M),
            "M5_DistressSignal":   ("MAYDAY",            _M),
            "M6_Evacuation":       ("ABANDON",           _M),
        },
        "MAYDAY": {
            "M1_Navigation":       ("MAYDAY",            _M),
            "M5_DistressSignal":   ("MAYDAY",            _M),
            "M6_Evacuation":       ("ABANDON",           _M),
        },
        "ABANDON": {
            "M6_Evacuation":       ("ABANDON",           _M),
        },
    },
    "OOW": {
        "STANDBY": {
            "M1_Navigation":       ("MONITORING",        _S),
        },
        "MONITORING": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
        },
        "UNDERWAY": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
            "M3_Communications":   ("COASTAL_WATERS",    _M),
        },
        "COASTAL_WATERS": {
            "M1_Navigation":       ("MONITORING",        _M),
            "M2_Maneuvering":      ("UNDERWAY",          _M),
            "M4_InternalEmergency": ("EMERGENCY_INTERNAL", _M),
        },
        "EMERGENCY_INTERNAL": {
            "M1_Navigation":       ("EMERGENCY_INTERNAL", _M),
            "M4_InternalEmergency": ("EMERGENCY_INTERNAL", _M),
        },
    },
    "Helmsman": {
        "STANDBY": {
            "M1_Navigation":       ("MONITORING",        _S),
        },
        "MONITORING": {
            "M1_Navigation":       ("MONITORING",        _M),
        },
    },
}

MARITIME_FLOW_START_STATE: Dict[str, str] = {
    "Master":   "STANDBY",
    "OOW":      "STANDBY",
    "Helmsman": "STANDBY",
}

MARITIME_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Master": {
        "STANDBY":        1,
        "MONITORING":     2,
        "UNDERWAY":       3,
        "COASTAL_WATERS": 3,
        "EMERGENCY":      3,
        "MUSTER":         4,
        "MAYDAY":         3,
        "ABANDON":        1,
    },
    "OOW": {
        "STANDBY":            1,
        "MONITORING":         2,
        "UNDERWAY":           3,
        "COASTAL_WATERS":     3,
        "EMERGENCY_INTERNAL": 2,
    },
    "Helmsman": {
        "STANDBY":    1,
        "MONITORING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# MaritimeTracker
# ═══════════════════════════════════════════════════════════════════════

class MaritimeTracker:

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
        return self._states.get(key, MARITIME_FLOW_START_STATE.get(role, "STANDBY"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return MARITIME_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, voyage_id: str) -> bool:
        if voyage_id in self._session_registry:
            return self._session_registry[voyage_id] != identity
        self._session_registry[voyage_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = MARITIME_PERMITTED_FLOWS.get(role, {})

        action_in_role  = any(action in sf for sf in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": MARITIME_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": False, "jurisdiction_violation": True,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        if not action_in_state:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": MARITIME_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": True, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = MARITIME_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = MARITIME_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows  = MARITIME_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# MaritimeCompiler
# ═══════════════════════════════════════════════════════════════════════

class MaritimeCompiler:

    def __init__(self) -> None:
        self.tracker = MaritimeTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Expected raw_event shape:
            {
                "actor_id":  str,
                "action":    str,
                "voyage_id": str,
                "timestamp": float  (optional)
            }
        """
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        voyage_id  = raw_event.get("voyage_id", "default_voyage")
        event_ts   = raw_event.get("timestamp")

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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, voyage_id)

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
            "Resolution": {"Completeness": resolution},
            "Identity":   identity_label,
            "Role":       role,
            "Action":     action,
            "RawAction":  action_raw,
            "VoyageID":   voyage_id,
            "FromState":  traj_context.get("from_state"),
            "ToState":    traj_context.get("to_state"),
        }

        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events: list) -> list:
    compiler = MaritimeCompiler()
    return [evaluate_gate(compiler.compile(e)) for e in events]
