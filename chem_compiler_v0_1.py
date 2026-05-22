"""
Chemical / Industrial Process Compiler v0.1
════════════════════════════════════════════

Substrate #19. Chemical and industrial process authority grammar derived from
OSHA PSM Standard (29 CFR 1910.119), EPA Risk Management Program (40 CFR
Part 68), API RP 750, and CCPS Guidelines for Chemical Process Quantitative
Risk Analysis. Incident anchor: Texas City BP Refinery explosion and fire,
March 23, 2005 (CSB Investigation Report No. 2005-04-I-TX, 2007).

Action class taxonomy (six classes):
    CP1_Monitor   — process monitoring, reading DCS, checking parameters, alarms
    CP2_Operate   — valve operations, pump start/stop, flow rate adjustment
    CP3_Startup   — unit startup sequences, PSSR execution, pre-startup checks
    CP4_Emergency — emergency shutdown (ESD), pressure relief, evacuation
    CP5_Authorize — MOC authorization, deviation permits, startup approval
    CP6_Bypass    — bypassing safety interlocks, overriding safety systems (not in any vocab)

Role registry:
    Unit_Operator (UO)             → CP1, CP2, CP3, CP4      (process floor operations)
    Board_Operator (BO)            → CP1, CP2, CP5           (DCS + authorization)
    Shift_Supervisor (SS)          → CP1, CP2, CP3, CP4, CP5 (full shift authority)
    Process_Safety_Engineer (PSE)  → CP1, CP5               (safety oversight, no direct operations)

Key state machine (Unit_Operator):
    IDLE → PSSR_COMPLETE → STARTUP_AUTHORIZED → STARTUP_RUNNING → NORMAL_OPS

State widths (Unit_Operator):
    IDLE:               1   (CP1_Monitor only)
    PSSR_COMPLETE:      2   (CP1_Monitor loop + CP5_Authorize request)
    STARTUP_AUTHORIZED: 2   (CP1_Monitor + CP3_Startup)
    STARTUP_RUNNING:    3   (CP1_Monitor + CP2_Operate + CP3_Startup loop)
    NORMAL_OPS:         4   (CP1_Monitor + CP2_Operate loop + CP4_Emergency + CP5_Authorize)

BURST geometry (C01):
    STARTUP_AUTHORIZED(w=2) → STARTUP_RUNNING(w=3) is width-expanding.
    STARTUP_RUNNING(w=3) → STARTUP_AUTHORIZED(w=2) via CP5_Authorize (re-auth cycle).
    Three STARTUP_AUTHORIZED→STARTUP_RUNNING expansions within 60s fires BURST_CADENCE.
    Both states already visited → HYSTERESIS does NOT fire.

BURST-Safe Traversal note (B01 clean path):
    IDLE(w=1)→PSSR_COMPLETE(w=2): expanding
    PSSR_COMPLETE(w=2)→STARTUP_AUTHORIZED(w=2): NOT expanding (same width)
    STARTUP_AUTHORIZED(w=2)→STARTUP_RUNNING(w=3): expanding
    Only 2 expansions on the clean path — BURST_SAFE confirmed, no spacing required.

Texas City anchor (March 23, 2005):
    ORDER: UO called CP3_Startup (continue filling raffinate splitter) from
           STARTUP_RUNNING past the safe level limit — process continued when
           the PSSR gate had not cleared the high-level interlock condition.
           Structural: CP3_Startup from STARTUP_RUNNING when CP5_Authorize
           (safety sign-off) had not completed → ORDER.
    JURISDICTION: Shift Supervisor authorized continued startup (CP3_Startup
                  equivalent) without PSE safety sign-off — PSE CP5_Authorize
                  is a required gate that was bypassed structurally.
"""

from __future__ import annotations
import time
from typing import Dict, List, Set, Tuple

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

CHEM_ACTION_CLASS_MAP: Dict[str, str] = {
    # CP1 — Monitor
    "read_dcs":                     "CP1_Monitor",
    "check_level_indicator":        "CP1_Monitor",
    "verify_alarm_status":          "CP1_Monitor",
    "monitor_pressure":             "CP1_Monitor",
    "check_temperature":            "CP1_Monitor",
    "observe_process_conditions":   "CP1_Monitor",
    # CP2 — Operate
    "open_valve":                   "CP2_Operate",
    "close_valve":                  "CP2_Operate",
    "start_pump":                   "CP2_Operate",
    "stop_pump":                    "CP2_Operate",
    "adjust_flow_rate":             "CP2_Operate",
    "adjust_reflux":                "CP2_Operate",
    # CP3 — Startup
    "begin_feed_introduction":      "CP3_Startup",
    "execute_pssr_checklist":       "CP3_Startup",
    "initiate_unit_startup":        "CP3_Startup",
    "continue_startup_sequence":    "CP3_Startup",
    "fill_distillation_column":     "CP3_Startup",
    # CP4 — Emergency
    "activate_esd":                 "CP4_Emergency",
    "open_pressure_relief":         "CP4_Emergency",
    "initiate_evacuation":          "CP4_Emergency",
    "activate_emergency_shutdown":  "CP4_Emergency",
    "sound_site_alarm":             "CP4_Emergency",
    # CP5 — Authorize
    "sign_moc_authorization":       "CP5_Authorize",
    "issue_startup_permit":         "CP5_Authorize",
    "authorize_deviation":          "CP5_Authorize",
    "complete_pssr_sign_off":       "CP5_Authorize",
    "approve_continued_startup":    "CP5_Authorize",
    # CP6 — Bypass (not in any vocab)
    "bypass_safety_interlock":      "CP6_Bypass",
    "override_high_level_alarm":    "CP6_Bypass",
    "disable_esd_system":           "CP6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return CHEM_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

CHEM_ROLE_TABLE: Dict[str, str] = {
    # Texas City actors (CSB 2005-04-I-TX)
    "uo_isom":             "Unit_Operator",          # ISOM unit operator
    "bo_isom":             "Board_Operator",
    "ss_isom":             "Shift_Supervisor",        # Don Holmstrom / shift sup
    "pse_alpha":           "Process_Safety_Engineer",
    # Generic
    "uo_alpha":            "Unit_Operator",
    "uo_bravo":            "Unit_Operator",
    "bo_alpha":            "Board_Operator",
    "ss_alpha":            "Shift_Supervisor",
    "ss_bravo":            "Shift_Supervisor",
    "pse_bravo":           "Process_Safety_Engineer",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Unit_Operator"
    return CHEM_ROLE_TABLE.get(actor_id, "Unit_Operator")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

CHEM_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Unit_Operator": {
        "IDLE": {
            "CP1_Monitor":  ("PSSR_COMPLETE",      Encapsulation.MID.value),
        },
        "PSSR_COMPLETE": {
            "CP1_Monitor":  ("PSSR_COMPLETE",      Encapsulation.SURFACE.value),
            "CP5_Authorize":("STARTUP_AUTHORIZED", Encapsulation.MID.value),
            # NOTE: CP3_Startup NOT in PSSR_COMPLETE → ORDER (start before auth)
        },
        "STARTUP_AUTHORIZED": {
            "CP1_Monitor":  ("STARTUP_AUTHORIZED", Encapsulation.SURFACE.value),
            "CP3_Startup":  ("STARTUP_RUNNING",    Encapsulation.MID.value),
            # NOTE: CP2_Operate NOT in STARTUP_AUTHORIZED → ORDER
        },
        "STARTUP_RUNNING": {
            "CP1_Monitor":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP2_Operate":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP3_Startup":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP5_Authorize":("STARTUP_AUTHORIZED", Encapsulation.MID.value),
            # NOTE: CP4_Emergency valid from here but only in emergency context
        },
        "NORMAL_OPS": {
            "CP1_Monitor":  ("NORMAL_OPS",         Encapsulation.SURFACE.value),
            "CP2_Operate":  ("NORMAL_OPS",         Encapsulation.SURFACE.value),
            "CP4_Emergency":("EMERGENCY",          Encapsulation.DEEP.value),
            "CP5_Authorize":("NORMAL_OPS",         Encapsulation.SURFACE.value),
        },
        "EMERGENCY": {
            "CP4_Emergency":("EMERGENCY",          Encapsulation.SURFACE.value),
        },
    },

    "Board_Operator": {
        "IDLE": {
            "CP1_Monitor":  ("MONITORING",         Encapsulation.MID.value),
        },
        "MONITORING": {
            "CP1_Monitor":  ("MONITORING",         Encapsulation.SURFACE.value),
            "CP2_Operate":  ("MONITORING",         Encapsulation.SURFACE.value),
            "CP5_Authorize":("AUTHORIZING",        Encapsulation.MID.value),
        },
        "AUTHORIZING": {
            "CP1_Monitor":  ("AUTHORIZING",        Encapsulation.SURFACE.value),
            "CP5_Authorize":("AUTHORIZING",        Encapsulation.SURFACE.value),
            "CP2_Operate":  ("MONITORING",         Encapsulation.MID.value),
        },
    },

    "Shift_Supervisor": {
        "IDLE": {
            "CP1_Monitor":  ("PSSR_COMPLETE",      Encapsulation.MID.value),
        },
        "PSSR_COMPLETE": {
            "CP1_Monitor":  ("PSSR_COMPLETE",      Encapsulation.SURFACE.value),
            "CP5_Authorize":("STARTUP_AUTHORIZED", Encapsulation.MID.value),
        },
        "STARTUP_AUTHORIZED": {
            "CP1_Monitor":  ("STARTUP_AUTHORIZED", Encapsulation.SURFACE.value),
            "CP3_Startup":  ("STARTUP_RUNNING",    Encapsulation.MID.value),
            "CP5_Authorize":("STARTUP_AUTHORIZED", Encapsulation.SURFACE.value),
        },
        "STARTUP_RUNNING": {
            "CP1_Monitor":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP2_Operate":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP3_Startup":  ("STARTUP_RUNNING",    Encapsulation.SURFACE.value),
            "CP4_Emergency":("EMERGENCY",          Encapsulation.DEEP.value),
            "CP5_Authorize":("STARTUP_AUTHORIZED", Encapsulation.MID.value),
        },
        "NORMAL_OPS": {
            "CP1_Monitor":  ("NORMAL_OPS",         Encapsulation.SURFACE.value),
            "CP2_Operate":  ("NORMAL_OPS",         Encapsulation.SURFACE.value),
            "CP4_Emergency":("EMERGENCY",          Encapsulation.DEEP.value),
            "CP5_Authorize":("NORMAL_OPS",         Encapsulation.SURFACE.value),
        },
        "EMERGENCY": {
            "CP4_Emergency":("EMERGENCY",          Encapsulation.SURFACE.value),
        },
    },

    "Process_Safety_Engineer": {
        "IDLE": {
            "CP1_Monitor":  ("REVIEWING",          Encapsulation.MID.value),
        },
        "REVIEWING": {
            "CP1_Monitor":  ("REVIEWING",          Encapsulation.SURFACE.value),
            "CP5_Authorize":("AUTHORIZED",         Encapsulation.MID.value),
        },
        "AUTHORIZED": {
            "CP1_Monitor":  ("AUTHORIZED",         Encapsulation.SURFACE.value),
            "CP5_Authorize":("AUTHORIZED",         Encapsulation.SURFACE.value),
        },
    },
}

CHEM_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Unit_Operator": {
        "IDLE":               1,
        "PSSR_COMPLETE":      2,
        "STARTUP_AUTHORIZED": 2,
        "STARTUP_RUNNING":    3,
        "NORMAL_OPS":         4,
        "EMERGENCY":          1,
    },
    "Board_Operator": {
        "IDLE":        1,
        "MONITORING":  3,
        "AUTHORIZING": 3,
    },
    "Shift_Supervisor": {
        "IDLE":               1,
        "PSSR_COMPLETE":      2,
        "STARTUP_AUTHORIZED": 3,
        "STARTUP_RUNNING":    4,
        "NORMAL_OPS":         4,
        "EMERGENCY":          1,
    },
    "Process_Safety_Engineer": {
        "IDLE":       1,
        "REVIEWING":  2,
        "AUTHORIZED": 2,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class ChemTracker:
    def __init__(self):
        self._states            = {}
        self._visited_states    = {}
        self._violation_history = {}
        self._width_history     = {}
        self._timed_widths      = {}
        self._role_history      = {}
        self._session_registry  = {}
        self._history           = {}

    def _key(self, identity, role):
        return f"{identity}::{role}"

    def current_state(self, identity, role):
        return self._states.get(self._key(identity, role), "IDLE")

    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return CHEM_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, unit_id):
        if unit_id in self._session_registry:
            return self._session_registry[unit_id] != identity
        self._session_registry[unit_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = CHEM_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": CHEM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": CHEM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = CHEM_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = CHEM_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {"admissible": True, "from_state": from_state, "to_state": to_state,
                "encapsulation": encap, "width_before": w_before, "width_after": w_after,
                "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

    def record_width(self, identity, w_before, w_after, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history:
            self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths:
            self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity, current_time=None):
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

    def check_hysteresis(self, identity, role, action):
        if not self._violation_history.get(identity):
            return False
        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False
        role_flows  = CHEM_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class ChemCompiler:
    def __init__(self):
        self.tracker = ChemTracker()

    def compile(self, raw_event):
        actor_id  = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        unit_id    = raw_event.get("unit_id", "default_unit")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, unit_id)

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
                "UnitID":     unit_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = ChemCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
