"""
Rail Operations Compiler v0.1
══════════════════════════════

Substrate #17. Rail operations authority grammar derived from Transport Canada
Railway Safety Act (RSA), Canadian Rail Operating Rules (CROR), and TC
Engineering Standards. Incident anchor: Lac-Mégantic, July 6, 2013
(TSB Railway Investigation Report R13D0054, 2014).

Action class taxonomy (six classes):
    R1_Monitor    — monitoring, reading track orders, checking signals, status queries
    R2_Operate    — locomotive control: throttle, dynamic brake, independent brake
    R3_Secure     — handbrake application, blocking devices, securing consist
    R4_Authorize  — track authority requests/grants (TOD, Form B/T, clearances)
    R5_Transfer   — crew change, locomotive handoff, formal authority transfer
    R6_Bypass     — bypassing TOD, unauthorized movement authority (not in any vocab)

Role registry:
    Locomotive_Engineer (LE)  → R1, R2, R3, R4, R5  (full train operations)
    Conductor                 → R1, R3, R4, R5        (no locomotive R2 control)
    Rail_Traffic_Controller   → R1, R4                (authority dispatch only)
    MoW_Supervisor            → R1, R4                (track access authority)

Key state machine (Locomotive_Engineer):
    IDLE → PRE_DEPARTURE → AUTHORIZED → OPERATING → SECURED

State widths (Locomotive_Engineer):
    IDLE:           1   (R1_Monitor only)
    PRE_DEPARTURE:  2   (R1_Monitor loop + R4_Authorize)
    AUTHORIZED:     2   (R1_Monitor + R2_Operate)
    OPERATING:      3   (R1_Monitor + R2_Operate loop + R3_Secure)
    SECURED:        2   (R1_Monitor + R4_Authorize for new movement authority)

BURST geometry (C01):
    AUTHORIZED(w=2) → OPERATING(w=3) is width-expanding.
    OPERATING(w=3) → AUTHORIZED(w=2) via R4_Authorize (re-authorization cycle).
    Three AUTHORIZED→OPERATING expansions within 60s fires BURST_CADENCE.
    Both states already visited → HYSTERESIS does NOT fire.

Lac-Mégantic anchor:
    ORDER: MMA dispatcher (RTC) granted unattended authority before securement
           verification complete — R4_Authorize called from OPERATING without
           the required R3_Secure gate being fully executed.
    JURISDICTION: Fire department applied locomotive independent brake (R2_Operate)
                  without rail authority — R2_Operate not in any fire dept vocab.
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
# Action class map
# ═══════════════════════════════════════════════════════════════════════

RAIL_ACTION_CLASS_MAP: Dict[str, str] = {
    # R1 — Monitor
    "check_signals":              "R1_Monitor",
    "read_track_order":           "R1_Monitor",
    "monitor_speed":              "R1_Monitor",
    "check_brake_pressure":       "R1_Monitor",
    "verify_clearance":           "R1_Monitor",
    "observe_consist":            "R1_Monitor",
    # R2 — Operate (locomotive control)
    "advance_throttle":           "R2_Operate",
    "apply_dynamic_brake":        "R2_Operate",
    "apply_independent_brake":    "R2_Operate",
    "release_brake":              "R2_Operate",
    "control_speed":              "R2_Operate",
    "initiate_movement":          "R2_Operate",
    # R3 — Secure
    "apply_handbrake":            "R3_Secure",
    "apply_blocking_device":      "R3_Secure",
    "verify_handbrake_count":     "R3_Secure",
    "secure_consist":             "R3_Secure",
    "apply_derail_device":        "R3_Secure",
    # R4 — Authorize
    "request_track_authority":    "R4_Authorize",
    "grant_track_authority":      "R4_Authorize",
    "issue_form_b_clearance":     "R4_Authorize",
    "issue_tod_clearance":        "R4_Authorize",
    "confirm_securement":         "R4_Authorize",
    "authorize_unattended_train": "R4_Authorize",
    # R5 — Transfer
    "crew_change":                "R5_Transfer",
    "locomotive_handoff":         "R5_Transfer",
    "authority_transfer":         "R5_Transfer",
    # R6 — Bypass (not in any role's vocab)
    "bypass_tod_system":          "R6_Bypass",
    "unauthorized_movement":      "R6_Bypass",
    "override_interlocking":      "R6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return RAIL_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

RAIL_ROLE_TABLE: Dict[str, str] = {
    # Lac-Mégantic actors (TSB R13D0054)
    "engineer_holt":          "Locomotive_Engineer",   # Tom Holt, MMA engineer
    "rtc_mma":                "Rail_Traffic_Controller",
    "fire_dept_megantic":     "MoW_Supervisor",        # closest structural analog — no R2 vocab
    # Generic
    "engineer_alpha":         "Locomotive_Engineer",
    "engineer_bravo":         "Locomotive_Engineer",
    "conductor_alpha":        "Conductor",
    "rtc_alpha":              "Rail_Traffic_Controller",
    "rtc_bravo":              "Rail_Traffic_Controller",
    "mow_alpha":              "MoW_Supervisor",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Locomotive_Engineer"
    return RAIL_ROLE_TABLE.get(actor_id, "Locomotive_Engineer")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

RAIL_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Locomotive_Engineer": {
        "IDLE": {
            "R1_Monitor":  ("PRE_DEPARTURE", Encapsulation.MID.value),
        },
        "PRE_DEPARTURE": {
            "R1_Monitor":  ("PRE_DEPARTURE", Encapsulation.SURFACE.value),
            "R4_Authorize":("AUTHORIZED",    Encapsulation.MID.value),
        },
        "AUTHORIZED": {
            "R1_Monitor":  ("AUTHORIZED",    Encapsulation.SURFACE.value),
            "R2_Operate":  ("OPERATING",     Encapsulation.MID.value),
            # NOTE: R3_Secure NOT in AUTHORIZED flows → ORDER if attempted here
        },
        "OPERATING": {
            "R1_Monitor":  ("OPERATING",     Encapsulation.SURFACE.value),
            "R2_Operate":  ("OPERATING",     Encapsulation.SURFACE.value),
            "R3_Secure":   ("SECURED",       Encapsulation.DEEP.value),
            "R4_Authorize":("AUTHORIZED",    Encapsulation.MID.value),
        },
        "SECURED": {
            "R1_Monitor":  ("SECURED",       Encapsulation.SURFACE.value),
            "R4_Authorize":("AUTHORIZED",    Encapsulation.MID.value),
            "R5_Transfer": ("IDLE",          Encapsulation.MID.value),
        },
    },

    "Conductor": {
        "IDLE": {
            "R1_Monitor":  ("PRE_DEPARTURE", Encapsulation.MID.value),
        },
        "PRE_DEPARTURE": {
            "R1_Monitor":  ("PRE_DEPARTURE", Encapsulation.SURFACE.value),
            "R4_Authorize":("AUTHORIZED",    Encapsulation.MID.value),
        },
        "AUTHORIZED": {
            "R1_Monitor":  ("AUTHORIZED",    Encapsulation.SURFACE.value),
            # No R2_Operate — Conductor does not control locomotive
            "R3_Secure":   ("SECURED",       Encapsulation.MID.value),
        },
        "SECURED": {
            "R1_Monitor":  ("SECURED",       Encapsulation.SURFACE.value),
            "R4_Authorize":("AUTHORIZED",    Encapsulation.MID.value),
            "R5_Transfer": ("IDLE",          Encapsulation.MID.value),
        },
    },

    "Rail_Traffic_Controller": {
        "IDLE": {
            "R1_Monitor":  ("MONITORING",    Encapsulation.MID.value),
        },
        "MONITORING": {
            "R1_Monitor":  ("MONITORING",    Encapsulation.SURFACE.value),
            "R4_Authorize":("DISPATCHING",   Encapsulation.MID.value),
        },
        "DISPATCHING": {
            "R1_Monitor":  ("DISPATCHING",   Encapsulation.SURFACE.value),
            "R4_Authorize":("DISPATCHING",   Encapsulation.SURFACE.value),
        },
    },

    "MoW_Supervisor": {
        "IDLE": {
            "R1_Monitor":  ("MONITORING",    Encapsulation.MID.value),
        },
        "MONITORING": {
            "R1_Monitor":  ("MONITORING",    Encapsulation.SURFACE.value),
            "R4_Authorize":("DISPATCHING",   Encapsulation.MID.value),
        },
        "DISPATCHING": {
            "R1_Monitor":  ("DISPATCHING",   Encapsulation.SURFACE.value),
            "R4_Authorize":("DISPATCHING",   Encapsulation.SURFACE.value),
        },
    },
}

RAIL_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Locomotive_Engineer": {
        "IDLE":          1,
        "PRE_DEPARTURE": 2,
        "AUTHORIZED":    2,
        "OPERATING":     3,
        "SECURED":       2,
    },
    "Conductor": {
        "IDLE":          1,
        "PRE_DEPARTURE": 2,
        "AUTHORIZED":    2,
        "SECURED":       2,
    },
    "Rail_Traffic_Controller": {
        "IDLE":        1,
        "MONITORING":  2,
        "DISPATCHING": 2,
    },
    "MoW_Supervisor": {
        "IDLE":        1,
        "MONITORING":  2,
        "DISPATCHING": 2,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker
# ═══════════════════════════════════════════════════════════════════════

class RailTracker:
    def __init__(self):
        self._states:            Dict[str, str]      = {}
        self._visited_states:    Dict[str, Set[str]] = {}
        self._violation_history: Dict[str, bool]     = {}
        self._width_history:     Dict[str, List]     = {}
        self._timed_widths:      Dict[str, List]     = {}
        self._role_history:      Dict[str, str]      = {}
        self._session_registry:  Dict[str, str]      = {}
        self._history:           Dict[str, List]     = {}

    def _key(self, identity: str, role: str) -> str:
        return f"{identity}::{role}"

    def current_state(self, identity: str, role: str) -> str:
        return self._states.get(self._key(identity, role), "IDLE")

    def width_at_current_state(self, identity: str, role: str) -> int:
        s = self.current_state(identity, role)
        return RAIL_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity: str, consist_id: str) -> bool:
        if consist_id in self._session_registry:
            return self._session_registry[consist_id] != identity
        self._session_registry[consist_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = RAIL_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": RAIL_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": RAIL_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = RAIL_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = RAIL_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {"admissible": True, "from_state": from_state, "to_state": to_state,
                "encapsulation": encap, "width_before": w_before, "width_after": w_after,
                "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

    def record_width(self, identity: str, w_before: int, w_after: int, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history:
            self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths:
            self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity: str, current_time=None) -> bool:
        timed = self._timed_widths.get(identity, [])
        if timed:
            now    = current_time if current_time is not None else time.time()
            cutoff = now - BURST_TIME_WINDOW_SECONDS
            window = [(wb, wa) for ts, wb, wa in timed if ts >= cutoff]
            if not window:
                return False
            return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW:
            return False
        return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD

    def check_hysteresis(self, identity: str, role: str, action: str) -> bool:
        if not self._violation_history.get(identity):
            return False
        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False
        role_flows  = RAIL_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class RailCompiler:
    def __init__(self):
        self.tracker = RailTracker()

    def compile(self, raw_event: dict) -> dict:
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        consist_id = raw_event.get("consist_id", "default_consist")
        event_ts   = raw_event.get("timestamp")

        identity_label = actor_id
        role           = resolve_role(actor_id)
        action         = resolve_action_class(action_raw)

        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN":
            resolution = ResolutionStatus.PARTIAL.value

        is_known = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = actor_pivot = False
        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, consist_id)

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
            if self.tracker.check_hysteresis(identity_label, role, action):
                cur = self.tracker.current_state(identity_label, role)
                tc = {"admissible": False, "from_state": cur, "to_state": None,
                      "encapsulation": Encapsulation.DEEP.value,
                      "width_before": self.tracker.width_at_current_state(identity_label, role),
                      "width_after": None, "exposure_event": True,
                      "order_violation": False, "jurisdiction_violation": False,
                      "role_confusion": False, "actor_pivot": False, "hysteresis_violation": True}
            else:
                tc = self.tracker.evaluate(identity_label, role, action)
        elif role_confusion or actor_pivot:
            tc = {"admissible": False,
                  "from_state": self.tracker.current_state(identity_label, role),
                  "to_state": None, "encapsulation": Encapsulation.DEEP.value,
                  "width_before": self.tracker.width_at_current_state(identity_label, role),
                  "width_after": None, "exposure_event": True,
                  "order_violation": False, "jurisdiction_violation": False,
                  "role_confusion": role_confusion, "actor_pivot": actor_pivot,
                  "hysteresis_violation": False}
        else:
            tc = {"admissible": False,
                  "from_state": self.tracker.current_state(identity_label, role),
                  "to_state": None, "encapsulation": Encapsulation.DEEP.value,
                  "width_before": self.tracker.width_at_current_state(identity_label, role),
                  "width_after": None, "exposure_event": False,
                  "order_violation": False, "jurisdiction_violation": False,
                  "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        burst_cadence = False
        if tc.get("admissible") and tc.get("width_after") is not None:
            self.tracker.record_width(identity_label, tc["width_before"], tc["width_after"],
                                      timestamp=event_ts)
            burst_cadence = self.tracker.check_burst_cadence(identity_label, current_time=event_ts)

        bas_metrics = {
            "Admissible":            tc.get("admissible", False),
            "ExposureEvent":         tc.get("exposure_event", False),
            "OrderViolation":        tc.get("order_violation", False),
            "JurisdictionViolation": tc.get("jurisdiction_violation", False),
            "RoleConfusion":         tc.get("role_confusion", False),
            "ActorPivot":            tc.get("actor_pivot", False),
            "HysteresisViolation":   tc.get("hysteresis_violation", False),
            "BurstCadence":          burst_cadence,
        }
        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header": {
                "Resolution": {"Completeness": resolution},
                "Identity":   identity_label,
                "Role":       role,
                "Action":     action,
                "RawAction":  action_raw,
                "ConsistID":  consist_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events: list) -> list:
    compiler = RailCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
