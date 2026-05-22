"""
Petroleum Operations Compiler v0.1
════════════════════════════════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps offshore drilling well-completion events
    (actor_id, action, well_id) to the gate's BAS_Metrics vocabulary.

Domain: Offshore drilling well completion under federal regulatory oversight.
Regulatory sources: 30 CFR Part 250 (BSEE Well Operations), API RP 75 (SEMS),
    API STD 53 (Blowout Prevention), API RP 65-2 (Cement Job Design),
    MMS Form BSEE-0123 (Application for Permit to Drill), MMS NTL 2010-N06
    (post-Macondo requirements). Pre-2011 doctrine reconstructed from MMS
    Notice to Lessees 2008-G05 and 30 CFR 250.420–250.428 as in force April 2010.

Action class taxonomy (six classes, sequenced through well lifecycle):
    P1 (Monitor)        — well monitoring, mud weight checks, kick monitor;
                          all roles (universal observation action)
    P2 (DrillingOps)    — drilling ahead, casing run, mud circulation;
                          Driller and OIM
    P3 (WellControl)    — BOP function test, kill operations, well shut-in;
                          Driller and OIM (rig-side well control authority)
    P4 (BarrierTest)    — negative pressure test, positive pressure test,
                          MIT (mechanical integrity test), cement bond log
                          interpretation; Driller and CompanyMan
                          (joint authority — operator approves, contractor
                          executes; this is the load-bearing gate)
    P5 (DisplaceComplete) — displace mud with seawater, cement plug placement,
                          temporary abandonment, transition to production;
                          CompanyMan authorizes, Driller and CementOperator
                          execute
    P6 (RegulatoryGo)   — submit displacement clearance, MMS approval,
                          permit amendment certification; MMSInspector only
                          (excluded from all others by construction —
                          structural analog to AC5/M5/N6: the regulator
                          gate that the operator cannot self-certify)
    P7 (EmergencyResponse) — emergency disconnect sequence (EDS), well
                          isolation, evacuation order; OIM only
                          (Master-equivalent — OIM is rig captain;
                          excluded from all others by construction)

Role registry:
    OIM           → P1, P2, P3, P4, P5, P7         (Transocean rig master;
                                                    full operational authority
                                                    except P6 regulatory gate)
    CompanyMan    → P1, P4, P5                     (BP/operator well site
                                                    leader; well program
                                                    authority, NOT well control
                                                    NOT emergency response —
                                                    P3 and P7 excluded)
    Driller       → P1, P2, P3, P4                 (Transocean rig drilling
                                                    authority; rig-side well
                                                    control)
    CementOperator → P1, P5                        (Halliburton or equivalent;
                                                    cement job execution only)
    MMSInspector  → P1, P6                         (federal regulator;
                                                    monitoring + regulatory
                                                    approval only)

Incident anchor: Deepwater Horizon / Macondo Well — April 20, 2010
    Primary sources: BOEMRE Joint Investigation Report (Sept 2011);
    CSB Final Report Vol. 2 (June 2014); National Commission on the BP
    Deepwater Horizon Oil Spill Report (Jan 2011); 30 CFR 250 as in
    force April 2010; BSEE-0123 amendments filed by BP April 14–20 2010.

    ORDER:        CompanyMan calls P5 (initiate_displacement) from
                  NEGATIVE_TEST state. P5 IS in CompanyMan vocabulary
                  (valid at BARRIER_VERIFIED). NEGATIVE_TEST.flows does
                  not contain P5 — only `accept_barrier_test_pass` (P4)
                  transitions NEGATIVE_TEST → BARRIER_VERIFIED.
                  Displacement was initiated April 20 ~13:00 CDT
                  before barrier verification was structurally complete.
                  Gate fires: ORDER.

    JURISDICTION: CompanyMan calls P6 (submit_displacement_clearance) —
                  P6 not in CompanyMan vocabulary. BP filed MMS amended
                  permit certifying displacement was authorized based on
                  the negative pressure test, when the test had returned
                  anomalous results (250 psi standpipe pressure with
                  closed annular preventer). Operator self-certifying
                  a regulator gate. Gate fires: JURISDICTION.

    BURST_CADENCE: Iterative re-interpretation of negative pressure test.
                  Three successive test cycles within ~90 minutes
                  (~16:00–17:30 CDT April 20). Each cycle expanded width
                  through TEST_RUNNING → TEST_INTERPRETING (wider) →
                  TEST_REINTERPRET (wider still). Structurally identical
                  to Bromiley iterative fixation: actor cycles through
                  expanding interpretation states under anomalous data
                  rather than escalating. Gate fires: BURST_CADENCE.

State machine widths:
    OIM:          STANDBY(1)→DRILLING(2)→CASING_SET(2)→CEMENTING(2)→
                  CEMENT_EVAL(2)→NEGATIVE_TEST(3)→BARRIER_VERIFIED(3)→
                  DISPLACING(2)→ABANDONED(1)
                  Emergency branch: any state → EMERGENCY(3) via P7
    CompanyMan:   DRILLING(2)→CASING_SET(2)→CEMENTING(2)→
                  CEMENT_EVAL(2)→NEGATIVE_TEST(3)→BARRIER_VERIFIED(3)→
                  DISPLACING(2)→ABANDONED(1)
    Driller:      STANDBY(1)→DRILLING(2)→CASING_SET(2)→CEMENTING(1)→
                  CEMENT_EVAL(1)→NEGATIVE_TEST(3)→BARRIER_VERIFIED(2)→
                  DISPLACING(1)
    CementOperator: CEMENTING(1)→CEMENT_EVAL(1)→DISPLACING(1)
    MMSInspector: ONSITE(1)→PERMIT_PENDING(2)→PERMIT_GRANTED(2)
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

PETROLEUM_ACTION_CLASS_MAP: Dict[str, str] = {
    # P1 — Well Monitoring (unrestricted — all roles)
    "monitor_mud_returns":          "P1_Monitor",
    "check_pit_volume":             "P1_Monitor",
    "monitor_standpipe_pressure":   "P1_Monitor",
    "monitor_flow_meter":           "P1_Monitor",
    "verify_mud_weight":            "P1_Monitor",
    # P2 — Drilling Operations (Driller, OIM)
    "drill_ahead":                  "P2_DrillingOps",
    "run_casing":                   "P2_DrillingOps",
    "circulate_bottoms_up":         "P2_DrillingOps",
    "trip_pipe":                    "P2_DrillingOps",
    "ream_hole":                    "P2_DrillingOps",
    # P3 — Well Control (Driller, OIM — rig-side well control authority)
    "function_test_bop":            "P3_WellControl",
    "activate_annular_preventer":   "P3_WellControl",
    "shut_in_well":                 "P3_WellControl",
    "kill_well_via_circulation":    "P3_WellControl",
    "activate_blind_shear_ram":     "P3_WellControl",
    # P4 — Barrier Testing (Driller, CompanyMan)
    "conduct_negative_pressure_test": "P4_BarrierTest",
    "conduct_positive_pressure_test": "P4_BarrierTest",
    "interpret_test_result":        "P4_BarrierTest",
    "accept_barrier_test_pass":     "P4_BarrierTest",
    "perform_cement_bond_log":      "P4_BarrierTest",
    "reject_barrier_test":          "P4_BarrierTest",
    # P5 — Completion / Displacement (CompanyMan authorizes; CementOperator executes)
    "initiate_displacement":        "P5_DisplaceComplete",
    "pump_cement_plug":             "P5_DisplaceComplete",
    "displace_mud_with_seawater":   "P5_DisplaceComplete",
    "set_surface_cement_plug":      "P5_DisplaceComplete",
    "temporarily_abandon_well":     "P5_DisplaceComplete",
    # P6 — Regulatory Approval (MMSInspector only — excluded from all others)
    "submit_displacement_clearance":"P6_RegulatoryGo",
    "approve_permit_amendment":     "P6_RegulatoryGo",
    "issue_mit_clearance":          "P6_RegulatoryGo",
    "certify_well_program":         "P6_RegulatoryGo",
    # P7 — Emergency Response (OIM only — Master-equivalent)
    "activate_emergency_disconnect":"P7_EmergencyResponse",
    "order_rig_evacuation":         "P7_EmergencyResponse",
    "sound_general_alarm_offshore": "P7_EmergencyResponse",
    "isolate_well":                 "P7_EmergencyResponse",
}


def resolve_action_class(action: str) -> str:
    return PETROLEUM_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

PETROLEUM_ROLE_TABLE: Dict[str, str] = {
    # OIM (Transocean rig master)
    "oim_harrell":           "OIM",       # Deepwater Horizon OIM (J. Harrell)
    "oim_kuchta":            "OIM",       # Deepwater Horizon OIM (J. Kuchta)
    "oim_chen":              "OIM",
    # CompanyMan (BP/operator well site leader)
    "companyman_kaluza":     "CompanyMan",  # Deepwater Horizon WSL (R. Kaluza)
    "companyman_vidrine":    "CompanyMan",  # Deepwater Horizon WSL (D. Vidrine)
    "companyman_brown":      "CompanyMan",
    # Driller (Transocean)
    "driller_anderson":      "Driller",
    "driller_revette":       "Driller",
    "driller_morales":       "Driller",
    # CementOperator (Halliburton or equivalent)
    "cement_op_gagliano":    "CementOperator",
    "cement_op_silva":       "CementOperator",
    # MMSInspector (federal regulator)
    "mms_inspector_neal":    "MMSInspector",
    "mms_inspector_patel":   "MMSInspector",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    """Default: CementOperator (most constrained — narrow vocabulary)."""
    if not actor_id:
        return "CementOperator"
    return PETROLEUM_ROLE_TABLE.get(actor_id, "CementOperator")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

_S = Encapsulation.SURFACE.value
_M = Encapsulation.MID.value
_D = Encapsulation.DEEP.value

PETROLEUM_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "OIM": {
        "STANDBY": {
            "P1_Monitor":              ("DRILLING",          _S),
        },
        "DRILLING": {
            "P1_Monitor":              ("DRILLING",          _S),
            "P2_DrillingOps":          ("CASING_SET",        _M),
            "P3_WellControl":          ("DRILLING",          _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "CASING_SET": {
            "P1_Monitor":              ("CASING_SET",        _S),
            "P2_DrillingOps":          ("CEMENTING",         _M),
            "P3_WellControl":          ("CASING_SET",        _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "CEMENTING": {
            "P1_Monitor":              ("CEMENTING",         _S),
            "P5_DisplaceComplete":     ("CEMENT_EVAL",       _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "CEMENT_EVAL": {
            "P1_Monitor":              ("CEMENT_EVAL",       _S),
            "P4_BarrierTest":          ("NEGATIVE_TEST",     _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "NEGATIVE_TEST": {
            "P1_Monitor":              ("NEGATIVE_TEST",     _S),
            "P3_WellControl":          ("NEGATIVE_TEST",     _M),
            "P4_BarrierTest":          ("BARRIER_VERIFIED",  _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "BARRIER_VERIFIED": {
            "P1_Monitor":              ("BARRIER_VERIFIED",  _S),
            "P5_DisplaceComplete":     ("DISPLACING",        _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "DISPLACING": {
            "P1_Monitor":              ("DISPLACING",        _S),
            "P3_WellControl":          ("DISPLACING",        _M),
            "P5_DisplaceComplete":     ("ABANDONED",         _M),
            "P7_EmergencyResponse":    ("EMERGENCY",         _D),
        },
        "ABANDONED": {
            "P1_Monitor":              ("ABANDONED",         _S),
        },
        "EMERGENCY": {
            "P1_Monitor":              ("EMERGENCY",         _S),
            "P7_EmergencyResponse":    ("EMERGENCY",         _M),
        },
    },

    "CompanyMan": {
        "DRILLING": {
            "P1_Monitor":              ("DRILLING",          _S),
        },
        "CASING_SET": {
            "P1_Monitor":              ("CASING_SET",        _S),
        },
        "CEMENTING": {
            "P1_Monitor":              ("CEMENTING",         _S),
            "P5_DisplaceComplete":     ("CEMENT_EVAL",       _M),
        },
        "CEMENT_EVAL": {
            "P1_Monitor":              ("CEMENT_EVAL",       _S),
            "P4_BarrierTest":          ("NEGATIVE_TEST",     _M),
        },
        "NEGATIVE_TEST": {
            "P1_Monitor":              ("NEGATIVE_TEST",     _S),
            "P4_BarrierTest":          ("BARRIER_VERIFIED",  _M),
        },
        "BARRIER_VERIFIED": {
            "P1_Monitor":              ("BARRIER_VERIFIED",  _S),
            "P5_DisplaceComplete":     ("DISPLACING",        _M),
        },
        "DISPLACING": {
            "P1_Monitor":              ("DISPLACING",        _S),
            "P5_DisplaceComplete":     ("ABANDONED",         _M),
        },
        "ABANDONED": {
            "P1_Monitor":              ("ABANDONED",         _S),
        },
    },

    "Driller": {
        "STANDBY": {
            "P1_Monitor":              ("DRILLING",          _S),
        },
        "DRILLING": {
            "P1_Monitor":              ("DRILLING",          _S),
            "P2_DrillingOps":          ("CASING_SET",        _M),
            "P3_WellControl":          ("DRILLING",          _M),
        },
        "CASING_SET": {
            "P1_Monitor":              ("CASING_SET",        _S),
            "P2_DrillingOps":          ("CEMENTING",         _M),
            "P3_WellControl":          ("CASING_SET",        _M),
        },
        "CEMENTING": {
            "P1_Monitor":              ("CEMENTING",         _S),
        },
        "CEMENT_EVAL": {
            "P1_Monitor":              ("CEMENT_EVAL",       _S),
            "P4_BarrierTest":          ("NEGATIVE_TEST",     _M),
        },
        "NEGATIVE_TEST": {
            "P1_Monitor":              ("NEGATIVE_TEST",     _S),
            "P3_WellControl":          ("NEGATIVE_TEST",     _M),
            "P4_BarrierTest":          ("BARRIER_VERIFIED",  _M),
        },
        "BARRIER_VERIFIED": {
            "P1_Monitor":              ("BARRIER_VERIFIED",  _S),
        },
        "DISPLACING": {
            "P1_Monitor":              ("DISPLACING",        _S),
            "P3_WellControl":          ("DISPLACING",        _M),
        },
    },

    "CementOperator": {
        "CEMENTING": {
            "P1_Monitor":              ("CEMENTING",         _S),
            "P5_DisplaceComplete":     ("CEMENT_EVAL",       _M),
        },
        "CEMENT_EVAL": {
            "P1_Monitor":              ("CEMENT_EVAL",       _S),
        },
        "DISPLACING": {
            "P1_Monitor":              ("DISPLACING",        _S),
            "P5_DisplaceComplete":     ("DISPLACING",        _M),
        },
    },

    "MMSInspector": {
        "ONSITE": {
            "P1_Monitor":              ("ONSITE",            _S),
            "P6_RegulatoryGo":         ("PERMIT_PENDING",    _M),
        },
        "PERMIT_PENDING": {
            "P1_Monitor":              ("PERMIT_PENDING",    _S),
            "P6_RegulatoryGo":         ("PERMIT_GRANTED",    _M),
        },
        "PERMIT_GRANTED": {
            "P1_Monitor":              ("PERMIT_GRANTED",    _S),
            "P6_RegulatoryGo":         ("PERMIT_GRANTED",    _M),
        },
    },
}

PETROLEUM_FLOW_START_STATE: Dict[str, str] = {
    "OIM":            "STANDBY",
    "CompanyMan":     "CEMENT_EVAL",  # WSL engages at cement evaluation phase
    "Driller":        "STANDBY",
    "CementOperator": "CEMENTING",
    "MMSInspector":   "ONSITE",
}

PETROLEUM_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "OIM": {
        "STANDBY":          1,
        "DRILLING":         2,
        "CASING_SET":       2,
        "CEMENTING":        2,
        "CEMENT_EVAL":      2,
        "NEGATIVE_TEST":    3,
        "BARRIER_VERIFIED": 3,
        "DISPLACING":       2,
        "ABANDONED":        1,
        "EMERGENCY":        3,
    },
    "CompanyMan": {
        "DRILLING":         2,
        "CASING_SET":       2,
        "CEMENTING":        2,
        "CEMENT_EVAL":      2,
        "NEGATIVE_TEST":    3,
        "BARRIER_VERIFIED": 3,
        "DISPLACING":       2,
        "ABANDONED":        1,
    },
    "Driller": {
        "STANDBY":          1,
        "DRILLING":         2,
        "CASING_SET":       2,
        "CEMENTING":        1,
        "CEMENT_EVAL":      1,
        "NEGATIVE_TEST":    3,
        "BARRIER_VERIFIED": 2,
        "DISPLACING":       1,
    },
    "CementOperator": {
        "CEMENTING":        1,
        "CEMENT_EVAL":      1,
        "DISPLACING":       1,
    },
    "MMSInspector": {
        "ONSITE":           1,
        "PERMIT_PENDING":   2,
        "PERMIT_GRANTED":   2,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# PetroleumTracker
# ═══════════════════════════════════════════════════════════════════════

class PetroleumTracker:

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
        return self._states.get(key, PETROLEUM_FLOW_START_STATE.get(role, "DRILLING"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return PETROLEUM_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, well_id: str) -> bool:
        # EXIT: one CompanyMan, one OIM, one Driller per well at a time.
        # Different identities binding to same well_id with the same role-slot
        # is a structural EXIT violation (handoff without transition event).
        # Per-well_id session registry; first binder owns the slot.
        if well_id in self._session_registry:
            return self._session_registry[well_id] != identity
        self._session_registry[well_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = PETROLEUM_PERMITTED_FLOWS.get(role, {})

        action_in_role = any(
            action in state_flows
            for state_flows in role_flows.values()
        )

        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           PETROLEUM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": True,
                "role_confusion":         False,
                "actor_pivot":            False,
                "hysteresis_violation":   False,
            }

        if not action_in_state:
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           PETROLEUM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        True,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
                "hysteresis_violation":   False,
            }

        to_state, encap = state_flows[action]
        self._states[key] = to_state

        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = PETROLEUM_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = PETROLEUM_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
        role_flows  = PETROLEUM_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# PetroleumCompiler — Layer 2
# ═══════════════════════════════════════════════════════════════════════

class PetroleumCompiler:

    def __init__(self) -> None:
        self.tracker = PetroleumTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Convert a raw petroleum operations event to a BAS_Metrics packet.

        Expected raw_event shape:
            {
                "actor_id":  str,    # e.g. "companyman_kaluza"
                "action":    str,    # e.g. "initiate_displacement"
                "well_id":   str,    # well identifier
                "timestamp": float,  # optional — unix seconds or relative
            }
        """
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        well_id    = raw_event.get("well_id", "default_well")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, well_id)

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
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
            "WellID":      well_id,
            "FromState":   traj_context.get("from_state"),
            "ToState":     traj_context.get("to_state"),
        }

        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header":  stp_header,
        }


def run_session(events: list) -> list:
    compiler = PetroleumCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
