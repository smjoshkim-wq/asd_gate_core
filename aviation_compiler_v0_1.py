"""
Aviation Crew Operations Compiler v0.1
══════════════════════════════════════

Reconstructed from harness signatures (test_harness_aviation_v0_1_combinatorial.py)
for use in the Tenerife 1977 inverse incident reconstruction.

Action class taxonomy (five classes):
    AV1_Read      — monitoring, reading, checking (loops in current state)
    AV2_Expand    — physical expansion: engines, throttle, control surface commands
    AV3_Contract  — return/abort actions: back to taxiway, go-around, abort
    AV4_Pivot     — clearance-receiving transitions: IFR, LUAW, Takeoff, Handoff
    AV5_Override  — bypass/override actions (not in any role's vocab — always JURISDICTION)

Role registry:
    Captain        → AV1, AV2, AV3, AV4 (physical control + clearance receipt)
    FirstOfficer   → AV1, AV3, AV4 (monitoring + support; no AV2 primary control)
    FlightEngineer → AV1, AV4_radio only (systems monitoring; no physical control AV2)
    ATC_Tower      → AV1, AV4_issue (clearance issuance; no physical AV2/AV3)

Key state machine (Captain role):
    IDLE → PREFLIGHT → TAXIING → RUNWAY_HOLD → TAKEOFF_CLEARED → AIRBORNE → APPROACH → LANDED

State widths (Captain):
    IDLE:            1
    PREFLIGHT:       1
    TAXIING:         2  (monitors + IFR clearance loop)
    RUNWAY_HOLD:     3  (monitors + LUAW + loop — waiting for takeoff clearance)
    TAKEOFF_CLEARED: 4  (cleared for takeoff — now AV2_Expand is valid)
    AIRBORNE:        3
    APPROACH:        3
    LANDED:          1
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

AVIATION_ACTION_CLASS_MAP: Dict[str, str] = {
    # AV1 — Read/Monitor
    "monitor_atis":               "AV1_Read",
    "monitor_ground_radar":       "AV1_Read",
    "visual_sweep_approach":      "AV1_Read",
    "check_instruments":          "AV1_Read",
    "monitor_systems":            "AV1_Read",
    "read_checklist":             "AV1_Read",
    # AV2 — Expand (physical control — Captain only)
    "initiate_takeoff_roll":      "AV2_Expand",
    "start_engines":              "AV2_Expand",
    "advance_throttle":           "AV2_Expand",
    "rotate":                     "AV2_Expand",
    "retract_landing_gear":       "AV2_Expand",
    # AV3 — Contract
    "return_to_taxiway":          "AV3_Contract",
    "abort_takeoff":              "AV3_Contract",
    "execute_go_around":          "AV3_Contract",
    # AV4 — Pivot (clearances)
    "receive_ife_clearance":      "AV4_Pivot",
    "receive_luaw_clearance":     "AV4_Pivot",
    "receive_takeoff_clearance":  "AV4_Pivot",
    "receive_landing_clearance":  "AV4_Pivot",
    "vhf_frequency_handoff":      "AV4_Pivot",
    # AV5 — Override (not in any role's vocab)
    "bypass_handshake_protocol":  "AV5_Override",
    "override_atc_instruction":   "AV5_Override",
}


def resolve_action_class(action: str) -> str:
    return AVIATION_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

AVIATION_ROLE_TABLE: Dict[str, str] = {
    # KLM 4805 crew (Tenerife)
    "captain_klm4805":       "Captain",       # Jacob van Zanten
    "fo_klm4805":            "FirstOfficer",  # Klaas Meurs
    "fe_klm4805":            "FlightEngineer",# Willem Schreuder

    # Pan Am 1736 crew (Tenerife)
    "captain_panam1736":     "Captain",       # Victor Grubbs
    "fo_panam1736":          "FirstOfficer",  # Robert Bragg
    "fe_panam1736":          "FlightEngineer",# George Warns

    # ATC
    "atc_tenerife":          "ATC_Tower",

    # Generic
    "captain_alpha":         "Captain",
    "captain_bravo":         "Captain",
    "fo_alpha":              "FirstOfficer",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Captain"
    return AVIATION_ROLE_TABLE.get(actor_id, "Captain")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

AVIATION_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Captain": {
        "IDLE": {
            "AV1_Read":   ("PREFLIGHT",      Encapsulation.MID.value),
        },
        "PREFLIGHT": {
            "AV1_Read":   ("PREFLIGHT",      Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("TAXIING",        Encapsulation.MID.value),
        },
        "TAXIING": {
            "AV1_Read":   ("TAXIING",        Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("RUNWAY_HOLD",    Encapsulation.MID.value),
        },
        "RUNWAY_HOLD": {
            "AV1_Read":   ("RUNWAY_HOLD",    Encapsulation.SURFACE.value),
            "AV3_Contract":("TAXIING",       Encapsulation.MID.value),
            "AV4_Pivot":  ("TAKEOFF_CLEARED",Encapsulation.DEEP.value),
            # NOTE: AV2_Expand NOT in RUNWAY_HOLD.flows → ORDER if attempted here
        },
        "TAKEOFF_CLEARED": {
            "AV1_Read":   ("TAKEOFF_CLEARED",Encapsulation.SURFACE.value),
            "AV2_Expand": ("AIRBORNE",       Encapsulation.DEEP.value),
            "AV3_Contract":("RUNWAY_HOLD",   Encapsulation.MID.value),
        },
        "AIRBORNE": {
            "AV1_Read":   ("AIRBORNE",       Encapsulation.SURFACE.value),
            "AV2_Expand": ("AIRBORNE",       Encapsulation.MID.value),
            "AV3_Contract":("APPROACH",      Encapsulation.MID.value),
        },
        "APPROACH": {
            "AV1_Read":   ("APPROACH",       Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("LANDED",         Encapsulation.MID.value),
            "AV3_Contract":("AIRBORNE",      Encapsulation.MID.value),
        },
        "LANDED": {
            "AV1_Read":   ("LANDED",         Encapsulation.SURFACE.value),
            "AV3_Contract":("TAXIING",       Encapsulation.MID.value),
        },
    },

    "FirstOfficer": {
        "IDLE": {
            "AV1_Read":   ("PREFLIGHT",      Encapsulation.SURFACE.value),
        },
        "PREFLIGHT": {
            "AV1_Read":   ("PREFLIGHT",      Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("TAXIING",        Encapsulation.MID.value),
        },
        "TAXIING": {
            "AV1_Read":   ("TAXIING",        Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("RUNWAY_HOLD",    Encapsulation.MID.value),
        },
        "RUNWAY_HOLD": {
            "AV1_Read":   ("RUNWAY_HOLD",    Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("TAKEOFF_CLEARED",Encapsulation.MID.value),
            "AV3_Contract":("TAXIING",       Encapsulation.MID.value),
        },
        "TAKEOFF_CLEARED": {
            "AV1_Read":   ("TAKEOFF_CLEARED",Encapsulation.SURFACE.value),
            "AV3_Contract":("RUNWAY_HOLD",   Encapsulation.MID.value),
        },
        "AIRBORNE": {
            "AV1_Read":   ("AIRBORNE",       Encapsulation.SURFACE.value),
        },
    },

    "FlightEngineer": {
        # FE has no AV2_Expand — physical control not in FE authority
        "MONITORING": {
            "AV1_Read":   ("MONITORING",     Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("MONITORING",     Encapsulation.SURFACE.value),
        },
    },

    "ATC_Tower": {
        "MONITORING": {
            "AV1_Read":   ("MONITORING",     Encapsulation.SURFACE.value),
            "AV4_Pivot":  ("MONITORING",     Encapsulation.MID.value),
        },
    },
}

AVIATION_FLOW_START_STATE: Dict[str, str] = {
    "Captain":       "IDLE",
    "FirstOfficer":  "IDLE",
    "FlightEngineer":"MONITORING",
    "ATC_Tower":     "MONITORING",
}

AVIATION_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Captain": {
        "IDLE":            1,
        "PREFLIGHT":       1,
        "TAXIING":         2,
        "RUNWAY_HOLD":     3,
        "TAKEOFF_CLEARED": 4,
        "AIRBORNE":        3,
        "APPROACH":        3,
        "LANDED":          1,
    },
    "FirstOfficer": {
        "IDLE":            1,
        "PREFLIGHT":       1,
        "TAXIING":         2,
        "RUNWAY_HOLD":     2,
        "TAKEOFF_CLEARED": 2,
        "AIRBORNE":        1,
    },
    "FlightEngineer": {"MONITORING": 1},
    "ATC_Tower":      {"MONITORING": 2},
}


# ═══════════════════════════════════════════════════════════════════════
# AviationTracker
# ═══════════════════════════════════════════════════════════════════════

class AviationTracker:
    def __init__(self) -> None:
        self._states:            Dict[Tuple[str, str], str]              = {}
        self._history:           Dict[Tuple[str, str], List[Tuple]]      = {}
        self._role_registry:     Dict[str, str]                          = {}
        self._session_registry:  Dict[str, str]                          = {}
        self._width_history:     Dict[str, List[Tuple[int, int]]]        = {}
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]] = {}
        self._violation_history: Dict[str, bool]                         = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]         = {}

    def _key(self, identity, role): return (identity, role)

    def current_state(self, identity, role):
        return self._states.get(self._key(identity, role),
                                AVIATION_FLOW_START_STATE.get(role, "IDLE"))

    def width_at_current_state(self, identity, role):
        state = self.current_state(identity, role)
        return AVIATION_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity, role):
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity, flight_id):
        if flight_id in self._session_registry:
            return self._session_registry[flight_id] != identity
        self._session_registry[flight_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = AVIATION_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": AVIATION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": AVIATION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states: self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = AVIATION_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = AVIATION_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
        if key not in self._history: self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {"admissible": True, "from_state": from_state, "to_state": to_state,
                "encapsulation": encap, "width_before": w_before, "width_after": w_after,
                "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

    def record_width(self, identity, w_before, w_after, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history: self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths: self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity, current_time=None):
        timed = self._timed_widths.get(identity, [])
        if timed:
            now = current_time if current_time is not None else time.time()
            cutoff = now - BURST_TIME_WINDOW_SECONDS
            window = [(wb, wa) for ts, wb, wa in timed if ts >= cutoff]
            if not window: return False
            return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW: return False
        return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD

    def check_hysteresis(self, identity, role, action):
        if not self._violation_history.get(identity): return False
        key = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited: return False
        role_flows = AVIATION_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


class AviationCompiler:
    def __init__(self): self.tracker = AviationTracker()

    def compile(self, raw_event):
        actor_id  = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        flight_id  = raw_event.get("flight_id", "default_flight")
        event_ts   = raw_event.get("timestamp")

        identity_label = actor_id
        role           = resolve_role(actor_id)
        action         = resolve_action_class(action_raw)

        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN": resolution = ResolutionStatus.PARTIAL.value

        is_known = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = actor_pivot = False
        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, flight_id)

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
            "Admissible": tc.get("admissible", False),
            "ExposureEvent": tc.get("exposure_event", False),
            "OrderViolation": tc.get("order_violation", False),
            "JurisdictionViolation": tc.get("jurisdiction_violation", False),
            "RoleConfusion": tc.get("role_confusion", False),
            "ActorPivot": tc.get("actor_pivot", False),
            "HysteresisViolation": tc.get("hysteresis_violation", False),
            "BurstCadence": burst_cadence,
        }
        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header": {"Resolution": {"Completeness": resolution},
                           "Identity": identity_label, "Role": role,
                           "Action": action, "RawAction": action_raw,
                           "FlightID": flight_id,
                           "FromState": tc.get("from_state"),
                           "ToState": tc.get("to_state")},
            # wave-2 compat key
            "verdict":   None,
            "invariant": None,
        }


def run_session(events):
    compiler = AviationCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        # Support both "decision" (gate native) and "verdict" (wave-2 harness compat)
        result["verdict"] = result["decision"]
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
