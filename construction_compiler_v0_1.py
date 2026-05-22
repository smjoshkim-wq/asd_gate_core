"""
Construction Approval Pipeline Compiler v0.1
═════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps construction project events (actor_id,
    action, project_id) to the gate's BAS_Metrics vocabulary.

Domain: Commercial construction permit and inspection pipeline from design
through Certificate of Occupancy. Sources: IBC 2021, ACI 318, AISC 360,
ASCE 7, AIA A201/B101, OSHA 29 CFR 1926, Alberta Building Code Schedules.

Action class taxonomy (twelve labels grouped into 6 superclasses):
    A1 Design / A2 PE Seal / A3 Commitment      → DesignDoc
    B1 Zoning / B2 PlanReview / B3 Cycle / B4 PermitIssuance → PermitFlow
    C1 PreConstruction                          → PreConstruction
    D1 Structural / D2 Envelope / D3 MEP / D4 Finishes → Execution
    E1 InspectionRequest / E2 InspectionExecute / E3 Correction → MunicipalInspection
    F1 SpecialInsp / F2 SpecialInspCert         → SpecialInspection
    G1 OccupancyApp / G2 COIssuance             → Occupancy
    H1 RemediationAuthorization                 → Remediation (Algo Centre / Champlain)

Role registry:
    Owner            → A3, G1 (and H1 for remediation authorization)
    Architect        → A1, A2 (excluded from D1 controls; excluded from approving own structural design)
    SER              → A1, A2 (structural design + seal; excluded from temp shoring without contract)
    PE_Record        → A2, A3, B2 (consolidates seals; submits permit application)
    GC               → C1, D1, D2, D3, D4, E1 (excluded from B4 self-issue, E2 self-cert)
    Specialty_Sub    → D3, D4 (within licensed trade scope)
    PlanReviewer     → B3, B4 (plan review + permit issuance)
    BuildingInspector→ E2, E3 (pass/fail notation + correction notices)
    SpecialInspector → F1, F2 (independent material testing — Chapter 17 IBC)
    FireMarshal      → E2 (fire-life-safety final inspection)
    COOfficer        → G2 (CO issuance — terminal)

Key incident anchors:
  - L'Ambiance Plaza (1987): ORDER — D1 (lift-slab procedure change) without
    SER engineering authorization during STRUCTURAL_FRAMING state.
  - Algo Centre Mall (2012): ORDER — H1 (remediation authorization) gate
    never activated from DEFICIENCY_NOTED state after engineering deficiency
    findings. State stalled while physical asset degraded.
  - Champlain Towers South (2021): ORDER — same structural pattern as Algo.
    DEFICIENCY_NOTED state, H1 required but not executed by Owner. Direct
    structural analog to Fukushima containment venting delay.
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

CONSTRUCTION_ACTION_CLASS_MAP: Dict[str, str] = {
    # A — Design Documents
    "draft_schematic_design":          "A1_Design",
    "prepare_construction_docs":       "A1_Design",
    "apply_pe_seal":                   "A2_PESeal",
    "apply_arch_seal":                 "A2_PESeal",
    "sign_schedule_a":                 "A3_Commitment",
    "sign_schedule_b":                 "A3_Commitment",
    "sign_schedule_c":                 "A3_Commitment",
    # B — Permit Flow
    "submit_zoning_review":            "B1_Zoning",
    "submit_plan_review":              "B2_PlanReview",
    "issue_plan_review_comment":       "B3_PlanReviewCycle",
    "respond_to_correction_notice":    "B3_PlanReviewCycle",
    "issue_permit":                    "B4_PermitIssuance",
    # C — Pre-Construction
    "execute_site_preparation":        "C1_PreConstruction",
    "execute_utility_notification":    "C1_PreConstruction",
    # D — Execution
    "pour_foundation":                 "D1_Structural",
    "erect_structural_framing":        "D1_Structural",
    "execute_lift_slab_sequence":      "D1_Structural",  # L'Ambiance anchor
    "alter_shoring_sequence":          "D1_Structural",  # L'Ambiance anchor
    "install_weather_barrier":         "D2_Envelope",
    "install_roofing":                 "D2_Envelope",
    "install_mep_rough":               "D3_MEP",
    "install_electrical_conduit":      "D3_MEP",
    "install_drywall":                 "D4_Finishes",
    "install_flooring":                "D4_Finishes",
    # E — Municipal Inspection
    "request_inspection":              "E1_InspectionRequest",
    "pass_inspection":                 "E2_InspectionExecute",
    "fail_inspection":                 "E2_InspectionExecute",
    "issue_stop_work":                 "E2_InspectionExecute",
    "issue_correction_notice":         "E3_Correction",
    # F — Special Inspection (Chapter 17 IBC)
    "execute_weld_inspection":         "F1_SpecialInsp",
    "execute_concrete_cylinder_test":  "F1_SpecialInsp",
    "submit_special_insp_certificate": "F2_SpecialInspCert",
    # G — Occupancy
    "apply_certificate_occupancy":     "G1_OccupancyApp",
    "issue_certificate_occupancy":     "G2_COIssuance",
    # H — Remediation (incident-anchor class)
    "authorize_remediation":           "H1_RemediationAuth",      # Champlain/Algo anchor
    "execute_remediation":             "H1_RemediationAuth",
}


def resolve_action_class(action: str) -> str:
    return CONSTRUCTION_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

CONSTRUCTION_ROLE_TABLE: Dict[str, str] = {
    "owner_developer":      "Owner",
    "owner_champlain":      "Owner",       # Champlain Towers condo board anchor
    "owner_algo":           "Owner",       # Algo Centre Mall owner anchor
    "owner_a":              "Owner",
    "architect_record":     "Architect",
    "architect_a":          "Architect",
    "ser_record":           "SER",
    "ser_thornton":         "SER",         # Thornton-Tomasetti analysis anchor
    "ser_morabito":         "SER",         # Morabito Consultants (Champlain) anchor
    "pe_record":            "PE_Record",
    "gc_lambiance":         "GC",          # L'Ambiance Plaza GC anchor
    "gc_a":                 "GC",
    "specialty_electric":   "Specialty_Sub",
    "specialty_mech":       "Specialty_Sub",
    "plan_reviewer":        "PlanReviewer",
    "building_inspector":   "BuildingInspector",
    "inspector_wood":       "BuildingInspector",  # Algo Centre — Robert Wood anchor
    "special_inspector":    "SpecialInspector",
    "fire_marshal":         "FireMarshal",
    "co_officer":           "COOfficer",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "GC"
    return CONSTRUCTION_ROLE_TABLE.get(actor_id, "GC")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph (construction state machine)
# ═══════════════════════════════════════════════════════════════════════
# States: DESIGN, PERMIT_APPLICATION, PERMIT_REVIEW, PERMIT_ISSUED, SITE_PREP,
#         FOUNDATION, STRUCTURAL_FRAMING, MEP_ROUGH, ENVELOPE,
#         INSULATION_AIR_BARRIER, MEP_TRIM, FINISHES, FINAL_INSPECTION,
#         CO_ISSUED (terminal), DEFICIENCY_NOTED (incident anchor)

CONSTRUCTION_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Owner": {
        "DESIGN": {
            "A3_Commitment": ("PERMIT_APPLICATION", Encapsulation.MID.value),
        },
        "PERMIT_ISSUED": {
            "A3_Commitment": ("PERMIT_ISSUED", Encapsulation.SURFACE.value),
        },
        "FINAL_INSPECTION": {
            "G1_OccupancyApp": ("CO_ISSUED", Encapsulation.MID.value),
        },
        # Remediation track — incident anchor for Champlain/Algo
        "DEFICIENCY_NOTED": {
            "H1_RemediationAuth": ("REMEDIATION", Encapsulation.DEEP.value),
        },
        "REMEDIATION": {
            "H1_RemediationAuth": ("CO_ISSUED", Encapsulation.MID.value),
        },
    },

    "Architect": {
        "DESIGN": {
            "A1_Design":  ("DESIGN", Encapsulation.SURFACE.value),
            "A2_PESeal":  ("PERMIT_APPLICATION", Encapsulation.MID.value),
        },
        "PERMIT_REVIEW": {
            "B3_PlanReviewCycle": ("PERMIT_REVIEW", Encapsulation.SURFACE.value),
        },
    },

    "SER": {
        "DESIGN": {
            "A1_Design":  ("DESIGN", Encapsulation.SURFACE.value),
            "A2_PESeal":  ("PERMIT_APPLICATION", Encapsulation.MID.value),
        },
    },

    "PE_Record": {
        "DESIGN": {
            "A2_PESeal":     ("PERMIT_APPLICATION", Encapsulation.MID.value),
            "A3_Commitment": ("DESIGN",             Encapsulation.SURFACE.value),
        },
        "PERMIT_APPLICATION": {
            "B2_PlanReview": ("PERMIT_REVIEW", Encapsulation.MID.value),
        },
    },

    "GC": {
        "PERMIT_ISSUED": {
            "C1_PreConstruction": ("SITE_PREP", Encapsulation.MID.value),
        },
        "SITE_PREP": {
            "D1_Structural":        ("FOUNDATION", Encapsulation.MID.value),
            "E1_InspectionRequest": ("SITE_PREP",  Encapsulation.SURFACE.value),
        },
        "FOUNDATION": {
            "D1_Structural":        ("STRUCTURAL_FRAMING", Encapsulation.MID.value),
            "E1_InspectionRequest": ("FOUNDATION",         Encapsulation.SURFACE.value),
        },
        "STRUCTURAL_FRAMING": {
            "D1_Structural":        ("STRUCTURAL_FRAMING", Encapsulation.MID.value),
            "D3_MEP":               ("MEP_ROUGH",          Encapsulation.MID.value),
            "D2_Envelope":          ("ENVELOPE",           Encapsulation.MID.value),
            "E1_InspectionRequest": ("STRUCTURAL_FRAMING", Encapsulation.SURFACE.value),
        },
        "MEP_ROUGH": {
            "D3_MEP":               ("MEP_ROUGH",             Encapsulation.SURFACE.value),
            "E1_InspectionRequest": ("MEP_ROUGH",             Encapsulation.SURFACE.value),
        },
        "ENVELOPE": {
            "D2_Envelope":          ("INSULATION_AIR_BARRIER", Encapsulation.MID.value),
            "E1_InspectionRequest": ("ENVELOPE",               Encapsulation.SURFACE.value),
        },
        "INSULATION_AIR_BARRIER": {
            "D4_Finishes":          ("MEP_TRIM", Encapsulation.MID.value),
            "E1_InspectionRequest": ("INSULATION_AIR_BARRIER", Encapsulation.SURFACE.value),
        },
        "MEP_TRIM": {
            "D4_Finishes":          ("FINISHES", Encapsulation.MID.value),
            "E1_InspectionRequest": ("MEP_TRIM", Encapsulation.SURFACE.value),
        },
        "FINISHES": {
            "D4_Finishes":          ("FINISHES",         Encapsulation.SURFACE.value),
            "E1_InspectionRequest": ("FINAL_INSPECTION", Encapsulation.MID.value),
        },
    },

    "Specialty_Sub": {
        "STRUCTURAL_FRAMING": {
            "D3_MEP": ("MEP_ROUGH", Encapsulation.MID.value),
        },
        "MEP_ROUGH": {
            "D3_MEP": ("MEP_ROUGH", Encapsulation.SURFACE.value),
        },
        "MEP_TRIM": {
            "D4_Finishes": ("MEP_TRIM", Encapsulation.SURFACE.value),
        },
    },

    "PlanReviewer": {
        "PERMIT_REVIEW": {
            "B3_PlanReviewCycle": ("PERMIT_REVIEW",  Encapsulation.SURFACE.value),
            "B4_PermitIssuance":  ("PERMIT_ISSUED", Encapsulation.MID.value),
        },
    },

    "BuildingInspector": {
        "FOUNDATION": {
            "E2_InspectionExecute": ("FOUNDATION", Encapsulation.MID.value),
            "E3_Correction":        ("FOUNDATION", Encapsulation.MID.value),
        },
        "STRUCTURAL_FRAMING": {
            "E2_InspectionExecute": ("STRUCTURAL_FRAMING", Encapsulation.MID.value),
            "E3_Correction":        ("STRUCTURAL_FRAMING", Encapsulation.MID.value),
        },
        "MEP_ROUGH": {
            "E2_InspectionExecute": ("MEP_ROUGH", Encapsulation.MID.value),
            "E3_Correction":        ("MEP_ROUGH", Encapsulation.MID.value),
        },
        "ENVELOPE": {
            "E2_InspectionExecute": ("ENVELOPE", Encapsulation.MID.value),
        },
        "FINAL_INSPECTION": {
            "E2_InspectionExecute": ("FINAL_INSPECTION", Encapsulation.MID.value),
        },
    },

    "SpecialInspector": {
        "STRUCTURAL_FRAMING": {
            "F1_SpecialInsp":     ("STRUCTURAL_FRAMING", Encapsulation.SURFACE.value),
            "F2_SpecialInspCert": ("STRUCTURAL_FRAMING", Encapsulation.MID.value),
        },
        "FOUNDATION": {
            "F1_SpecialInsp":     ("FOUNDATION", Encapsulation.SURFACE.value),
            "F2_SpecialInspCert": ("FOUNDATION", Encapsulation.MID.value),
        },
    },

    "FireMarshal": {
        "FINAL_INSPECTION": {
            "E2_InspectionExecute": ("FINAL_INSPECTION", Encapsulation.MID.value),
        },
    },

    "COOfficer": {
        "CO_ISSUED": {
            "G2_COIssuance": ("CO_ISSUED", Encapsulation.MID.value),
        },
    },
}

CONSTRUCTION_FLOW_START_STATE: Dict[str, str] = {
    "Owner":             "DESIGN",
    "Architect":         "DESIGN",
    "SER":               "DESIGN",
    "PE_Record":         "DESIGN",
    "GC":                "PERMIT_ISSUED",
    "Specialty_Sub":     "STRUCTURAL_FRAMING",
    "PlanReviewer":      "PERMIT_REVIEW",
    "BuildingInspector": "FOUNDATION",
    "SpecialInspector":  "FOUNDATION",
    "FireMarshal":       "FINAL_INSPECTION",
    "COOfficer":         "CO_ISSUED",
}

CONSTRUCTION_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Owner": {
        "DESIGN":            1,
        "PERMIT_ISSUED":     1,
        "FINAL_INSPECTION":  1,
        "DEFICIENCY_NOTED":  1,
        "REMEDIATION":       1,
    },
    "Architect":         {"DESIGN": 2, "PERMIT_REVIEW": 1},
    "SER":               {"DESIGN": 2},
    "PE_Record":         {"DESIGN": 2, "PERMIT_APPLICATION": 1},
    "GC": {
        "PERMIT_ISSUED":          1,
        "SITE_PREP":              2,   # +1 expansion from PERMIT_ISSUED
        "FOUNDATION":             3,   # +1 expansion from SITE_PREP
        "STRUCTURAL_FRAMING":     4,   # +1 expansion from FOUNDATION — 3 expansions = BURST
        "MEP_ROUGH":              2,
        "ENVELOPE":               2,
        "INSULATION_AIR_BARRIER": 2,
        "MEP_TRIM":               2,
        "FINISHES":               2,
    },
    "Specialty_Sub":      {"STRUCTURAL_FRAMING": 1, "MEP_ROUGH": 1, "MEP_TRIM": 1},
    "PlanReviewer":       {"PERMIT_REVIEW": 2},
    "BuildingInspector":  {"FOUNDATION": 2, "STRUCTURAL_FRAMING": 2, "MEP_ROUGH": 2,
                           "ENVELOPE": 1, "FINAL_INSPECTION": 1},
    "SpecialInspector":   {"FOUNDATION": 2, "STRUCTURAL_FRAMING": 2},
    "FireMarshal":        {"FINAL_INSPECTION": 1},
    "COOfficer":          {"CO_ISSUED": 1},
}


# ═══════════════════════════════════════════════════════════════════════
# ConstructionTracker
# ═══════════════════════════════════════════════════════════════════════

class ConstructionTracker:

    def __init__(self) -> None:
        self._states:            Dict[Tuple[str, str], str]               = {}
        self._history:           Dict[Tuple[str, str], List[Tuple]]       = {}
        self._role_registry:     Dict[str, str]                           = {}
        self._session_registry:  Dict[str, str]                           = {}
        self._width_history:     Dict[str, List[Tuple[int, int]]]         = {}
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]]  = {}
        self._violation_history: Dict[str, bool]                          = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]          = {}

    def _key(self, identity, role): return (identity, role)

    def current_state(self, identity, role):
        return self._states.get(self._key(identity, role),
                                CONSTRUCTION_FLOW_START_STATE.get(role, "DESIGN"))

    def width_at_current_state(self, identity, role):
        state = self.current_state(identity, role)
        return CONSTRUCTION_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity, role):
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity, project_id):
        if project_id in self._session_registry:
            return self._session_registry[project_id] != identity
        self._session_registry[project_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = CONSTRUCTION_PERMITTED_FLOWS.get(role, {})

        action_in_role = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": CONSTRUCTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": CONSTRUCTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state

        if key not in self._visited_states: self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = CONSTRUCTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = CONSTRUCTION_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
            expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
            return expansions >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW: return False
        expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
        return expansions >= BURST_THRESHOLD

    def check_hysteresis(self, identity, role, action):
        if not self._violation_history.get(identity): return False
        key = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited: return False
        role_flows = CONSTRUCTION_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


class ConstructionCompiler:
    def __init__(self): self.tracker = ConstructionTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        project_id = raw_event.get("project_id", "default_project")
        event_ts   = raw_event.get("timestamp")

        identity_label = actor_id
        role           = resolve_role(actor_id)
        action         = resolve_action_class(action_raw)

        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN": resolution = ResolutionStatus.PARTIAL.value

        is_known       = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = False
        actor_pivot    = False

        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, project_id)

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
        stp_header = {"Resolution": {"Completeness": resolution},
                      "Identity": identity_label, "Role": role, "Action": action,
                      "RawAction": action_raw, "ProjectID": project_id,
                      "FromState": tc.get("from_state"), "ToState": tc.get("to_state")}
        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events):
    compiler = ConstructionCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
