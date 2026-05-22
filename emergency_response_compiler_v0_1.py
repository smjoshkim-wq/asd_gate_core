"""
Emergency Response Compiler v0.1 — FEMA ICS / NIMS
════════════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
    Gate kernel unchanged. No ICS-specific logic in the gate.
Layer 2 (Compiler): this module. Maps ICS/NIMS emergency response events
    (actor_id, action, incident_id) to the gate's BAS_Metrics vocabulary.

Domain: Multi-agency NIMS/ICS-compliant emergency response operations.
Regulatory sources: FEMA NIMS 2017, NRF 2019, ICS-100/200/300/400,
CFR Title 44 Emergency Management.

Action class taxonomy (seven classes):
    AC1 (Situational Assessment) — READ; unrestricted, continuous
    AC2 (Incident Action Planning) — PLAN; gated by IC/UC authorization
    AC3 (Resource Ordering)       — EXPAND; gated by escalation chain
    AC4 (Operational Execution)   — EXECUTE; Unity of Command enforced
    AC5 (Command Transfer/Pivot)  — PIVOT; excluded from single IC unilaterally
    AC6 (Public Communication)    — BROADCAST; gated by IC/UC authorization
    AC7 (Demobilization)          — CONTRACT; gated by IC authorization

Role registry:
    IncidentCommander   → AC1, AC2, AC3, AC4, AC6, AC7 (AC5 excluded unilaterally)
    SafetyOfficer       → AC1 (monitoring only; stop-work is structural interrupt
                           not modeled as a separate action class)
    PIO                 → AC1, AC6 (public comms only; IC auth required for AC6)
    LiaisonOfficer      → AC1 (coordination only; no tactical authority)
    OperationsSectionChief → AC1, AC4 (tactical execution within span of control)
    PlanningSectionChief   → AC1, AC2 (planning only; no tactical commands)
    LogisticsSectionChief  → AC1, AC3 (resource ordering within delegated limits)
    FinanceAdminChief      → AC1 (fiscal gating; no tactical authority)
    DivisionSupervisor     → AC1, AC4 (execution within assigned geographic area)
    StrikeTeamLeader       → AC4 only (terminal execution; Unity of Command)
    AgencyRepresentative   → AC1 (advisory; no tactical command)
    MACGroupMember         → AC1, AC3, AC5 (macro-policy; no tactical command)

AC5 (Command Transfer/Pivot) is excluded from all single roles except
MACGroupMember — Unified Command activation requires Agency Administrator
concurrence. Single IC calling AC5 unilaterally fires JURISDICTION.

Incident anchor: Hurricane Katrina 2005 (FEMA/DHS after-action report,
House Select Committee "A Failure of Initiative"):
    ORDER:          Federal resources deployed (AC4) before Unified Command
                    established (AC5) — ICS_ACTIVATION → EXPANDED_OPERATIONS
                    without passing through UNIFIED_COMMAND gate.
    JURISDICTION:   FEMA and LANG operated parallel command structures with
                    overlapping geographic authority — two ICs executing AC4
                    in same sector without UC integration.
    BURST_CADENCE:  Parallel AC3 resource requests fired through multiple
                    channels simultaneously within single operational period,
                    bypassing mandatory state→federal escalation sequence.
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

ICS_ACTION_CLASS_MAP: Dict[str, str] = {
    # AC1 — Situational Assessment (READ; unrestricted)
    "conduct_size_up":              "AC1_Assessment",
    "monitor_incident_status":      "AC1_Assessment",
    "review_ics_form":              "AC1_Assessment",
    "identify_essential_info":      "AC1_Assessment",
    "observe_operations":           "AC1_Assessment",
    "track_resource_status":        "AC1_Assessment",
    # AC2 — Incident Action Planning
    "draft_iap_objectives":         "AC2_Planning",
    "conduct_planning_meeting":     "AC2_Planning",
    "approve_iap":                  "AC2_Planning",
    "issue_incident_action_plan":   "AC2_Planning",
    "update_operational_period":    "AC2_Planning",
    # AC3 — Resource Ordering (EXPAND)
    "request_local_mutual_aid":     "AC3_ResourceOrder",
    "request_state_resources":      "AC3_ResourceOrder",
    "activate_emac":                "AC3_ResourceOrder",
    "request_federal_resources":    "AC3_ResourceOrder",
    "order_heavy_equipment":        "AC3_ResourceOrder",
    "deploy_national_guard":        "AC3_ResourceOrder",
    # AC4 — Operational Execution (EXECUTE)
    "deploy_strike_team":           "AC4_Execution",
    "conduct_search_rescue":        "AC4_Execution",
    "execute_evacuation":           "AC4_Execution",
    "manage_staging_area":          "AC4_Execution",
    "conduct_damage_assessment":    "AC4_Execution",
    "establish_shelter_operations": "AC4_Execution",
    # AC5 — Command Transfer / Unified Command (PIVOT — excluded from IC alone)
    "transfer_command":             "AC5_CommandTransfer",
    "activate_unified_command":     "AC5_CommandTransfer",
    "establish_area_command":       "AC5_CommandTransfer",
    "declare_multiagency_coord":    "AC5_CommandTransfer",
    # AC6 — Public Communication (BROADCAST; IC auth required)
    "issue_public_evacuation_order":"AC6_PublicComm",
    "conduct_press_briefing":       "AC6_PublicComm",
    "release_casualty_data":        "AC6_PublicComm",
    "issue_shelter_in_place":       "AC6_PublicComm",
    # AC7 — Demobilization (CONTRACT; IC auth required)
    "release_task_force":           "AC7_Demobilization",
    "close_staging_area":           "AC7_Demobilization",
    "deactivate_eoc":               "AC7_Demobilization",
    "terminate_ics_structure":      "AC7_Demobilization",
}


def resolve_action_class(action: str) -> str:
    return ICS_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

ICS_ROLE_TABLE: Dict[str, str] = {
    "ic_johnson":       "IncidentCommander",
    "ic_rivera":        "IncidentCommander",
    "so_chen":          "SafetyOfficer",
    "pio_adams":        "PIO",
    "lno_baker":        "LiaisonOfficer",
    "osc_white":        "OperationsSectionChief",
    "osc_green":        "OperationsSectionChief",
    "psc_hall":         "PlanningSectionChief",
    "lsc_torres":       "LogisticsSectionChief",
    "fsc_kim":          "FinanceAdminChief",
    "div_sup_alpha":    "DivisionSupervisor",
    "div_sup_bravo":    "DivisionSupervisor",
    "stl_task1":        "StrikeTeamLeader",
    "stl_task2":        "StrikeTeamLeader",
    "arep_fema":        "AgencyRepresentative",
    "arep_state":       "AgencyRepresentative",
    "mac_director":     "MACGroupMember",
    "eoc_director":     "MACGroupMember",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "DivisionSupervisor"
    return ICS_ROLE_TABLE.get(actor_id, "DivisionSupervisor")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

ICS_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "IncidentCommander": {
        "INCIDENT_NOTIFICATION": {
            "AC1_Assessment":  ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
        },
        "INITIAL_RESPONSE": {
            "AC1_Assessment":  ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
            "AC2_Planning":    ("ICS_ACTIVATION",    Encapsulation.MID.value),
            "AC4_Execution":   ("INITIAL_RESPONSE",  Encapsulation.MID.value),
        },
        "ICS_ACTIVATION": {
            "AC1_Assessment":  ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
            "AC2_Planning":    ("ICS_ACTIVATION",    Encapsulation.MID.value),
            "AC3_ResourceOrder":("ICS_ACTIVATION",   Encapsulation.MID.value),
            "AC4_Execution":   ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment":  ("UNIFIED_COMMAND",   Encapsulation.SURFACE.value),
            "AC2_Planning":    ("UNIFIED_COMMAND",   Encapsulation.MID.value),
            "AC5_CommandTransfer":("EXPANDED_OPS",   Encapsulation.DEEP.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment":  ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
            "AC2_Planning":    ("OPS_PERIOD_1",      Encapsulation.MID.value),
            "AC3_ResourceOrder":("OPS_PERIOD_1",     Encapsulation.MID.value),
            "AC4_Execution":   ("OPS_PERIOD_1",      Encapsulation.MID.value),
            "AC6_PublicComm":  ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment":  ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
            "AC3_ResourceOrder":("EXPANDED_OPS",     Encapsulation.MID.value),
            "AC4_Execution":   ("EXPANDED_OPS",      Encapsulation.MID.value),
            "AC6_PublicComm":  ("EXPANDED_OPS",      Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC1_Assessment":  ("RECOVERY",          Encapsulation.SURFACE.value),
            "AC4_Execution":   ("RECOVERY",          Encapsulation.MID.value),
            "AC7_Demobilization":("DEMOBILIZATION",  Encapsulation.MID.value),
        },
        "DEMOBILIZATION": {
            "AC7_Demobilization":("END_EX",          Encapsulation.MID.value),
        },
    },

    "SafetyOfficer": {
        "INCIDENT_NOTIFICATION": {
            "AC1_Assessment": ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
        },
        "INITIAL_RESPONSE": {
            "AC1_Assessment": ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
        },
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
        },
        "RECOVERY": {
            "AC1_Assessment": ("RECOVERY",          Encapsulation.SURFACE.value),
        },
    },

    "PIO": {
        "INITIAL_RESPONSE": {
            "AC1_Assessment": ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
        },
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
            "AC6_PublicComm": ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
            "AC6_PublicComm": ("EXPANDED_OPS",      Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC1_Assessment": ("RECOVERY",          Encapsulation.SURFACE.value),
            "AC6_PublicComm": ("RECOVERY",          Encapsulation.MID.value),
        },
    },

    "LiaisonOfficer": {
        "INITIAL_RESPONSE": {
            "AC1_Assessment": ("INITIAL_RESPONSE",  Encapsulation.SURFACE.value),
        },
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment": ("UNIFIED_COMMAND",   Encapsulation.SURFACE.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
        },
    },

    "OperationsSectionChief": {
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
            "AC4_Execution":  ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
            "AC4_Execution":  ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
            "AC4_Execution":  ("EXPANDED_OPS",      Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC1_Assessment": ("RECOVERY",          Encapsulation.SURFACE.value),
            "AC4_Execution":  ("RECOVERY",          Encapsulation.MID.value),
        },
    },

    "PlanningSectionChief": {
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
            "AC2_Planning":   ("ICS_ACTIVATION",    Encapsulation.MID.value),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment": ("UNIFIED_COMMAND",   Encapsulation.SURFACE.value),
            "AC2_Planning":   ("UNIFIED_COMMAND",   Encapsulation.MID.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
            "AC2_Planning":   ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
            "AC2_Planning":   ("EXPANDED_OPS",      Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC1_Assessment": ("RECOVERY",          Encapsulation.SURFACE.value),
            "AC2_Planning":   ("RECOVERY",          Encapsulation.MID.value),
        },
    },

    "LogisticsSectionChief": {
        "ICS_ACTIVATION": {
            "AC1_Assessment":   ("ICS_ACTIVATION",  Encapsulation.SURFACE.value),
            "AC3_ResourceOrder":("ICS_ACTIVATION",  Encapsulation.MID.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment":   ("OPS_PERIOD_1",    Encapsulation.SURFACE.value),
            "AC3_ResourceOrder":("OPS_PERIOD_1",    Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment":   ("EXPANDED_OPS",    Encapsulation.SURFACE.value),
            "AC3_ResourceOrder":("EXPANDED_OPS",    Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC1_Assessment":   ("RECOVERY",        Encapsulation.SURFACE.value),
        },
    },

    "FinanceAdminChief": {
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
        },
        "RECOVERY": {
            "AC1_Assessment": ("RECOVERY",          Encapsulation.SURFACE.value),
        },
    },

    "DivisionSupervisor": {
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
            "AC4_Execution":  ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
            "AC4_Execution":  ("OPS_PERIOD_1",      Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
            "AC4_Execution":  ("EXPANDED_OPS",      Encapsulation.MID.value),
        },
    },

    "StrikeTeamLeader": {
        # Terminal execution node — AC4 only; in any active ops state
        "OPS_PERIOD_1": {
            "AC4_Execution": ("OPS_PERIOD_1",       Encapsulation.MID.value),
        },
        "EXPANDED_OPS": {
            "AC4_Execution": ("EXPANDED_OPS",       Encapsulation.MID.value),
        },
        "RECOVERY": {
            "AC4_Execution": ("RECOVERY",           Encapsulation.MID.value),
        },
    },

    "AgencyRepresentative": {
        "ICS_ACTIVATION": {
            "AC1_Assessment": ("ICS_ACTIVATION",    Encapsulation.SURFACE.value),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment": ("UNIFIED_COMMAND",   Encapsulation.SURFACE.value),
        },
        "OPS_PERIOD_1": {
            "AC1_Assessment": ("OPS_PERIOD_1",      Encapsulation.SURFACE.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment": ("EXPANDED_OPS",      Encapsulation.SURFACE.value),
        },
    },

    "MACGroupMember": {
        "ICS_ACTIVATION": {
            "AC1_Assessment":    ("ICS_ACTIVATION",  Encapsulation.SURFACE.value),
            "AC3_ResourceOrder": ("ICS_ACTIVATION",  Encapsulation.MID.value),
        },
        "UNIFIED_COMMAND": {
            "AC1_Assessment":    ("UNIFIED_COMMAND",  Encapsulation.SURFACE.value),
            "AC5_CommandTransfer":("EXPANDED_OPS",    Encapsulation.DEEP.value),
        },
        "EXPANDED_OPS": {
            "AC1_Assessment":    ("EXPANDED_OPS",    Encapsulation.SURFACE.value),
            "AC3_ResourceOrder": ("EXPANDED_OPS",    Encapsulation.MID.value),
            "AC5_CommandTransfer":("EXPANDED_OPS",   Encapsulation.DEEP.value),
        },
        "RECOVERY": {
            "AC1_Assessment":    ("RECOVERY",        Encapsulation.SURFACE.value),
        },
    },
}

ICS_FLOW_START_STATE: Dict[str, str] = {
    "IncidentCommander":     "INCIDENT_NOTIFICATION",
    "SafetyOfficer":         "INCIDENT_NOTIFICATION",
    "PIO":                   "INITIAL_RESPONSE",
    "LiaisonOfficer":        "INITIAL_RESPONSE",
    "OperationsSectionChief":"ICS_ACTIVATION",
    "PlanningSectionChief":  "ICS_ACTIVATION",
    "LogisticsSectionChief": "ICS_ACTIVATION",
    "FinanceAdminChief":     "ICS_ACTIVATION",
    "DivisionSupervisor":    "ICS_ACTIVATION",
    "StrikeTeamLeader":      "OPS_PERIOD_1",
    "AgencyRepresentative":  "ICS_ACTIVATION",
    "MACGroupMember":        "ICS_ACTIVATION",
}

ICS_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "IncidentCommander": {
        "INCIDENT_NOTIFICATION": 1,
        "INITIAL_RESPONSE":      3,
        "ICS_ACTIVATION":        4,
        "UNIFIED_COMMAND":       3,
        "OPS_PERIOD_1":          5,
        "EXPANDED_OPS":          4,
        "RECOVERY":              3,
        "DEMOBILIZATION":        1,
    },
    "SafetyOfficer":         {s: 1 for s in ["INCIDENT_NOTIFICATION","INITIAL_RESPONSE","ICS_ACTIVATION","OPS_PERIOD_1","EXPANDED_OPS","RECOVERY"]},
    "PIO":                   {"INITIAL_RESPONSE":1,"ICS_ACTIVATION":1,"OPS_PERIOD_1":2,"EXPANDED_OPS":2,"RECOVERY":2},
    "LiaisonOfficer":        {s: 1 for s in ["INITIAL_RESPONSE","ICS_ACTIVATION","UNIFIED_COMMAND","OPS_PERIOD_1","EXPANDED_OPS"]},
    "OperationsSectionChief":{"ICS_ACTIVATION":2,"OPS_PERIOD_1":2,"EXPANDED_OPS":2,"RECOVERY":2},
    "PlanningSectionChief":  {"ICS_ACTIVATION":2,"UNIFIED_COMMAND":2,"OPS_PERIOD_1":2,"EXPANDED_OPS":2,"RECOVERY":2},
    "LogisticsSectionChief": {"ICS_ACTIVATION":2,"OPS_PERIOD_1":2,"EXPANDED_OPS":2,"RECOVERY":1},
    "FinanceAdminChief":     {s: 1 for s in ["ICS_ACTIVATION","OPS_PERIOD_1","EXPANDED_OPS","RECOVERY"]},
    "DivisionSupervisor":    {"ICS_ACTIVATION":2,"OPS_PERIOD_1":2,"EXPANDED_OPS":2},
    "StrikeTeamLeader":      {"OPS_PERIOD_1":1,"EXPANDED_OPS":1,"RECOVERY":1},
    "AgencyRepresentative":  {s: 1 for s in ["ICS_ACTIVATION","UNIFIED_COMMAND","OPS_PERIOD_1","EXPANDED_OPS"]},
    "MACGroupMember":        {"ICS_ACTIVATION":2,"UNIFIED_COMMAND":2,"EXPANDED_OPS":3,"RECOVERY":1},
}


# ═══════════════════════════════════════════════════════════════════════
# ICSTracker
# ═══════════════════════════════════════════════════════════════════════

class ICSTracker:

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
        return self._states.get(key, ICS_FLOW_START_STATE.get(role, "ICS_ACTIVATION"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return ICS_FLOW_WIDTHS.get(role, {}).get(state, 1)

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
        role_flows = ICS_PERMITTED_FLOWS.get(role, {})

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
                "width_before":           ICS_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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
                "width_before":           ICS_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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

        w_before = ICS_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = ICS_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
        role_flows  = ICS_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# ICSCompiler — Layer 2
# ═══════════════════════════════════════════════════════════════════════

class ICSCompiler:

    def __init__(self) -> None:
        self.tracker = ICSTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Convert a raw ICS event to a BAS_Metrics packet.

        Expected raw_event shape:
            {
                "actor_id":    str,    # e.g. "ic_johnson", "osc_white"
                "action":      str,    # e.g. "deploy_strike_team", "activate_unified_command"
                "incident_id": str,    # incident identifier
                "timestamp":   float,  # optional
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
            "IncidentID":  incident_id,
            "FromState":   traj_context.get("from_state"),
            "ToState":     traj_context.get("to_state"),
        }

        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header":  stp_header,
        }


def run_session(events: list) -> list:
    compiler = ICSCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
