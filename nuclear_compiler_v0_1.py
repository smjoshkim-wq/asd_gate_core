"""
Nuclear Facility Operations Compiler v0.1
════════════════════════════════════════════════════════════════════════
Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
    Gate kernel is structurally identical to all prior substrates.
Layer 2 (Compiler): this module. Maps nuclear facility events
    (actor_id, action, shift_id) to the gate's BAS_Metrics vocabulary.

Domain: Commercial light-water reactor control room and emergency response.
Regulatory sources: 10 CFR 50, 10 CFR 55, NUREG-0737, NUREG-1021,
    10 CFR 50 Appendix E, NUREG-0654.

Action class taxonomy (six classes):
    N1 (Monitor)            — read/diagnose, unrestricted; all roles
    N2 (ReactivityControl)  — control rod / coolant adjustments; RO/SRO_SM only
    N3 (ProtectiveMitigation) — SCRAM, ECCS, EOP entry; RO/SRO_SM only
    N4 (EmergencyDeclaration) — declare NOUE/Alert/SAE/GE; SRO_SM/ED only
    N5 (ExternalNotification) — NRC notification, PARs; ED only
    N6 (ExtremeOverride)    — throttle ECCS, invoke 50.54(x), vent containment;
                              SRO_SM only (excluded from RO by construction —
                              structural analog to T5/A5/G5 across substrates)

Role registry:
    RO      → N1, N2, N3      (N4, N5, N6 excluded)
    SRO_SM  → N1, N2, N3, N4, N6  (N5 excluded — ED-only after ERO activation)
    ED      → N1, N4, N5      (N2, N3, N6 excluded — no direct reactor control)
    STA     → N1 only         (advisory only — no execution authority)

Incident anchor: Three Mile Island 1979
    ORDER:      SRO throttled ECCS (N6) before completing diagnostic sequence
                from OPERATING state — N6 in SRO vocabulary, OPERATING.flows
                does not contain N6 → ORDER fires at step 3 of A01.
    JURISDICTION: The override action (N6) is structurally excluded from RO
                role at all states — any RO calling N6 → JURISDICTION at A02.

State machine widths (for BURST_CADENCE):
    RO:    STANDBY(1)→MONITORING(2)→OPERATING(3)→EMERGENCY_RESPONSE(2)
    SRO_SM: STANDBY(1)→MONITORING(2)→OPERATING(3)→EMERGENCY_RESPONSE(4)→
            DECLARED(2)/OVERRIDE_ACTIVE(1)
    ED:    STANDBY(1)→MONITORING(2)→DECLARED(3)→NOTIFYING(2)
    STA:   STANDBY(1)→MONITORING(1)
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

NUCLEAR_ACTION_CLASS_MAP: Dict[str, str] = {
    # N1 — Monitor & Diagnose (unrestricted — all roles)
    "check_parameters":       "N1_Monitor",
    "read_indicators":        "N1_Monitor",
    "acknowledge_alarm":      "N1_Monitor",
    "verify_system_status":   "N1_Monitor",
    # N2 — Normal Reactivity & Thermal Control
    "withdraw_control_rods":  "N2_ReactivityControl",
    "insert_control_rods":    "N2_ReactivityControl",
    "adjust_coolant_flow":    "N2_ReactivityControl",
    "change_power_level":     "N2_ReactivityControl",
    # N3 — Protective Mitigation & Procedure Initiation
    "manual_scram":           "N3_ProtectiveMitigation",
    "actuate_eccs":           "N3_ProtectiveMitigation",
    "enter_eop":              "N3_ProtectiveMitigation",
    "initiate_hpi":           "N3_ProtectiveMitigation",
    # N4 — Emergency Escalation & Declaration (state gate)
    "declare_unusual_event":  "N4_EmergencyDeclaration",
    "declare_alert":          "N4_EmergencyDeclaration",
    "declare_site_area_emg":  "N4_EmergencyDeclaration",
    "declare_general_emg":    "N4_EmergencyDeclaration",
    # N5 — External Notification & PAR Issuance (ED only)
    "notify_nrc":             "N5_ExternalNotification",
    "issue_par":              "N5_ExternalNotification",
    "notify_offsite_agency":  "N5_ExternalNotification",
    # N6 — Extreme Override & Severe Accident Bypass (SRO_SM only)
    "throttle_eccs":          "N6_ExtremeOverride",
    "invoke_50_54_x":         "N6_ExtremeOverride",
    "vent_containment":       "N6_ExtremeOverride",
    "bypass_safety_system":   "N6_ExtremeOverride",
}


def resolve_action_class(action: str) -> str:
    return NUCLEAR_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

NUCLEAR_ROLE_TABLE: Dict[str, str] = {
    "ro_jones":      "RO",
    "ro_smith":      "RO",
    "ro_park":       "RO",
    "sro_garcia":    "SRO_SM",
    "sro_chen":      "SRO_SM",
    "sm_patel":      "SRO_SM",
    "ed_williams":   "ED",
    "ed_johnson":    "ED",
    "sta_kim":       "STA",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    """Default: STA (most constrained — N1 only)."""
    if not actor_id:
        return "STA"
    return NUCLEAR_ROLE_TABLE.get(actor_id, "STA")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

_S = Encapsulation.SURFACE.value
_M = Encapsulation.MID.value

NUCLEAR_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
    "RO": {
        "STANDBY": {
            "N1_Monitor":            ("MONITORING",          _S),
        },
        "MONITORING": {
            "N1_Monitor":            ("MONITORING",          _M),
            "N2_ReactivityControl":  ("OPERATING",           _M),
        },
        "OPERATING": {
            "N1_Monitor":            ("MONITORING",          _M),
            "N2_ReactivityControl":  ("OPERATING",           _M),
            "N3_ProtectiveMitigation": ("EMERGENCY_RESPONSE", _M),
        },
        "EMERGENCY_RESPONSE": {
            "N1_Monitor":            ("EMERGENCY_RESPONSE",  _M),
            "N3_ProtectiveMitigation": ("EMERGENCY_RESPONSE", _M),
        },
    },
    "SRO_SM": {
        "STANDBY": {
            "N1_Monitor":            ("MONITORING",          _S),
        },
        "MONITORING": {
            "N1_Monitor":            ("MONITORING",          _M),
            "N2_ReactivityControl":  ("OPERATING",           _M),
        },
        "OPERATING": {
            "N1_Monitor":            ("MONITORING",          _M),
            "N2_ReactivityControl":  ("OPERATING",           _M),
            "N3_ProtectiveMitigation": ("EMERGENCY_RESPONSE", _M),
        },
        "EMERGENCY_RESPONSE": {
            "N1_Monitor":            ("EMERGENCY_RESPONSE",  _M),
            "N3_ProtectiveMitigation": ("EMERGENCY_RESPONSE", _M),
            "N4_EmergencyDeclaration": ("DECLARED",          _M),
            "N6_ExtremeOverride":    ("OVERRIDE_ACTIVE",     _M),
        },
        "DECLARED": {
            "N1_Monitor":            ("DECLARED",            _M),
            "N4_EmergencyDeclaration": ("DECLARED",          _M),
        },
        "OVERRIDE_ACTIVE": {
            "N6_ExtremeOverride":    ("OVERRIDE_ACTIVE",     _M),
        },
    },
    "ED": {
        "STANDBY": {
            "N1_Monitor":            ("MONITORING",          _S),
        },
        "MONITORING": {
            "N1_Monitor":            ("MONITORING",          _M),
            "N4_EmergencyDeclaration": ("DECLARED",          _M),
        },
        "DECLARED": {
            "N1_Monitor":            ("DECLARED",            _M),
            "N4_EmergencyDeclaration": ("DECLARED",          _M),
            "N5_ExternalNotification": ("NOTIFYING",         _M),
        },
        "NOTIFYING": {
            "N1_Monitor":            ("NOTIFYING",           _M),
            "N5_ExternalNotification": ("NOTIFYING",         _M),
        },
    },
    "STA": {
        "STANDBY": {
            "N1_Monitor":            ("MONITORING",          _S),
        },
        "MONITORING": {
            "N1_Monitor":            ("MONITORING",          _M),
        },
    },
}

NUCLEAR_FLOW_START_STATE: Dict[str, str] = {
    "RO":     "STANDBY",
    "SRO_SM": "STANDBY",
    "ED":     "STANDBY",
    "STA":    "STANDBY",
}

NUCLEAR_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "RO": {
        "STANDBY":           1,
        "MONITORING":        2,
        "OPERATING":         3,
        "EMERGENCY_RESPONSE": 2,
    },
    "SRO_SM": {
        "STANDBY":            1,
        "MONITORING":         2,
        "OPERATING":          3,
        "EMERGENCY_RESPONSE": 4,
        "DECLARED":           2,
        "OVERRIDE_ACTIVE":    1,
    },
    "ED": {
        "STANDBY":    1,
        "MONITORING": 2,
        "DECLARED":   3,
        "NOTIFYING":  2,
    },
    "STA": {
        "STANDBY":    1,
        "MONITORING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# NuclearTracker
# ═══════════════════════════════════════════════════════════════════════

class NuclearTracker:

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
        return self._states.get(key, NUCLEAR_FLOW_START_STATE.get(role, "STANDBY"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return NUCLEAR_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, shift_id: str) -> bool:
        if shift_id in self._session_registry:
            return self._session_registry[shift_id] != identity
        self._session_registry[shift_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = NUCLEAR_PERMITTED_FLOWS.get(role, {})

        action_in_role = any(
            action in state_flows
            for state_flows in role_flows.values()
        )
        state_flows    = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": NUCLEAR_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": False, "jurisdiction_violation": True,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        if not action_in_state:
            self._violation_history[identity] = True
            return {
                "admissible": False, "from_state": from_state, "to_state": None,
                "encapsulation": Encapsulation.DEEP.value,
                "width_before": NUCLEAR_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after": None, "exposure_event": True,
                "order_violation": True, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False,
            }

        to_state, encap = state_flows[action]
        self._states[key] = to_state

        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = NUCLEAR_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = NUCLEAR_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
        role_flows  = NUCLEAR_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# NuclearCompiler
# ═══════════════════════════════════════════════════════════════════════

class NuclearCompiler:

    def __init__(self) -> None:
        self.tracker = NuclearTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Expected raw_event shape:
            {
                "actor_id":  str,
                "action":    str,
                "shift_id":  str,
                "timestamp": float  (optional)
            }
        """
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        shift_id   = raw_event.get("shift_id", "default_shift")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, shift_id)

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
            "ShiftID":    shift_id,
            "FromState":  traj_context.get("from_state"),
            "ToState":    traj_context.get("to_state"),
        }

        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events: list) -> list:
    """Convenience wrapper: compile + gate for a sequence of raw events."""
    compiler = NuclearCompiler()
    return [evaluate_gate(compiler.compile(e)) for e in events]
