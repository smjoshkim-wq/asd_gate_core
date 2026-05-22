"""
Clinical Patient Safety Compiler v0.1
(corrected — evaluate_gate interface fixed)
"""
from __future__ import annotations
import time
from typing import Dict, List, Optional, Set, Tuple

from domain_compiler_v0_9 import (
    evaluate_gate,
    ResolutionStatus,
    BURST_TIME_WINDOW_SECONDS,
    BURST_THRESHOLD,
    BURST_WINDOW,
)

CLINICAL_ACTION_CLASS_MAP: Dict[str, str] = {
    "perform_physical_exam":       "C1_Assessment",
    "check_vitals":                "C1_Assessment",
    "review_labs":                 "C1_Assessment",
    "auscultate_lungs":            "C1_Assessment",
    "monitor_oxygen_saturation":   "C1_Assessment",
    "assess_airway_patency":       "C1_Assessment",
    "continuous_monitoring":       "C1_Assessment",
    "order_medication":            "C2_Ordering",
    "request_imaging":             "C2_Ordering",
    "prescribe_blood_product":     "C2_Ordering",
    "write_surgical_order":        "C2_Ordering",
    "order_anesthesia_plan":       "C2_Ordering",
    "administer_iv_bolus":         "C3_MedAdmin",
    "start_propofol_infusion":     "C3_MedAdmin",
    "give_neuromuscular_blocker":  "C3_MedAdmin",
    "administer_analgesic":        "C3_MedAdmin",
    "push_reversal_agent":         "C3_MedAdmin",
    "administer_anesthetic":       "C3_MedAdmin",
    "intubate_patient":            "C4_Procedure",
    "make_surgical_incision":      "C4_Procedure",
    "perform_emergency_tracheostomy": "C4_Procedure",
    "insert_central_line":         "C4_Procedure",
    "laryngoscopy_attempt":        "C4_Procedure",
    "apply_supraglottic_airway":   "C4_Procedure",
    "attempt_fiberoptic_scope":    "C4_Procedure",
    "handoff_to_pacu":             "C5_Handoff",
    "shift_change_report":         "C5_Handoff",
    "sign_out_to_crosscover":      "C5_Handoff",
    "transfer_to_ward":            "C5_Handoff",
    "pacu_to_ward_transfer":       "C5_Handoff",
    "call_rapid_response":         "C6_Escalation",
    "initiate_cico_protocol":      "C6_Escalation",
    "call_attending_for_help":     "C6_Escalation",
    "activate_difficult_airway_team": "C6_Escalation",
    "declare_surgical_emergency":  "C6_Escalation",
    "abort_induction":             "C6_Escalation",
    "sign_surgical_timeout":       "C7_Documentation",
    "chart_vitals":                "C7_Documentation",
    "complete_anesthesia_record":  "C7_Documentation",
    "document_consent":            "C7_Documentation",
    "surgical_count_verification": "C7_Documentation",
    "complete_preop_assessment":   "C7_Documentation",
}

def resolve_action_class(action: str) -> str:
    return CLINICAL_ACTION_CLASS_MAP.get(action, "UNKNOWN")

CLINICAL_ROLE_TABLE: Dict[str, str] = {
    "anesthesiologist_1":         "Anesthesiologist",
    "anesthesiologist_2":         "Anesthesiologist",
    "consultant_anaesthetist_1":  "Anesthesiologist",
    "consultant_anaesthetist_2":  "Anesthesiologist",
    "surgeon_1":                  "Surgeon",
    "consultant_ent_surgeon":     "Surgeon",
    "surgeon_alpha":              "Surgeon",
    "rn_theatre_1":               "RN",
    "rn_theatre_2":               "RN",
    "theatre_sister":             "RN",
    "recovery_nurse":             "RN",
    "circulating_nurse_1":        "Circulating_Nurse",
    "scrub_tech_1":               "Scrub_Tech",
    "scrub_tech_2":               "Scrub_Tech",
    "attending_1":                "Attending",
    "attending_2":                "Attending",
    "resident_1":                 "Resident",
    "fellow_1":                   "Resident",
    "pharmacist_1":               "Pharmacist",
    "pso_1":                      "Patient_Safety_Officer",
}

def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "RN"
    return CLINICAL_ROLE_TABLE.get(actor_id, "RN")

CLINICAL_ROLE_VOCABULARY: Dict[str, Set[str]] = {
    "Anesthesiologist": {"C1_Assessment","C2_Ordering","C3_MedAdmin","C4_Procedure","C5_Handoff","C6_Escalation","C7_Documentation"},
    "Surgeon":          {"C1_Assessment","C2_Ordering","C4_Procedure","C5_Handoff","C6_Escalation","C7_Documentation"},
    "RN":               {"C1_Assessment","C3_MedAdmin","C5_Handoff","C6_Escalation","C7_Documentation"},
    "Circulating_Nurse":{"C1_Assessment","C3_MedAdmin","C5_Handoff","C6_Escalation","C7_Documentation"},
    "Scrub_Tech":       {"C7_Documentation"},
    "Attending":        {"C1_Assessment","C2_Ordering","C3_MedAdmin","C4_Procedure","C5_Handoff","C6_Escalation","C7_Documentation"},
    "Resident":         {"C1_Assessment","C2_Ordering","C4_Procedure","C5_Handoff","C6_Escalation","C7_Documentation"},
    "Pharmacist":       {"C1_Assessment","C2_Ordering","C6_Escalation","C7_Documentation"},
    "Patient_Safety_Officer": {"C1_Assessment","C6_Escalation","C7_Documentation"},
}

CLINICAL_PERMITTED_FLOWS: Dict[str, Dict] = {
    "Anesthesiologist": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C2_Ordering": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 3},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C2_Ordering": "INDUCTION", "C3_MedAdmin": "INDUCTION", "C4_Procedure": "PROCEDURE", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 6},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C2_Ordering": "PROCEDURE", "C3_MedAdmin": "PROCEDURE", "C4_Procedure": "EMERGENCE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 6},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C3_MedAdmin": "EMERGENCE", "C4_Procedure": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 5},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C2_Ordering": "PACU", "C3_MedAdmin": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 6},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C2_Ordering": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 4},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "Surgeon": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C2_Ordering": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 3},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 3},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C2_Ordering": "PROCEDURE", "C4_Procedure": "EMERGENCE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 5},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C4_Procedure": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 4},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C2_Ordering": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 5},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C2_Ordering": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 4},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "RN": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 2},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C3_MedAdmin": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 4},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C3_MedAdmin": "PROCEDURE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 4},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C3_MedAdmin": "EMERGENCE", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 4},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C3_MedAdmin": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 5},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 3},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "Scrub_Tech": {
        "IDLE":      {"flows": {"C7_Documentation": "PROCEDURE"}, "width": 1},
        "PROCEDURE": {"flows": {"C7_Documentation": "PROCEDURE"}, "width": 1},
        "DISCHARGE": {"flows": {}, "width": 0},
    },
    "Circulating_Nurse": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 2},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C3_MedAdmin": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 4},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C3_MedAdmin": "PROCEDURE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 4},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C3_MedAdmin": "EMERGENCE", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 4},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C3_MedAdmin": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 5},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 3},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "Attending": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C2_Ordering": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 3},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C2_Ordering": "INDUCTION", "C3_MedAdmin": "INDUCTION", "C4_Procedure": "PROCEDURE", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 6},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C2_Ordering": "PROCEDURE", "C3_MedAdmin": "PROCEDURE", "C4_Procedure": "EMERGENCE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 6},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C3_MedAdmin": "EMERGENCE", "C4_Procedure": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 5},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C2_Ordering": "PACU", "C3_MedAdmin": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 6},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C2_Ordering": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 4},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "Resident": {
        "IDLE":             {"flows": {"C1_Assessment": "PRE_OP"}, "width": 1},
        "PRE_OP":           {"flows": {"C1_Assessment": "PRE_OP", "C2_Ordering": "PRE_OP", "C7_Documentation": "CONSENT"}, "width": 3},
        "CONSENT":          {"flows": {"C1_Assessment": "CONSENT", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 2},
        "SURGICAL_TIMEOUT": {"flows": {"C1_Assessment": "SURGICAL_TIMEOUT", "C5_Handoff": "INDUCTION", "C7_Documentation": "SURGICAL_TIMEOUT"}, "width": 3},
        "INDUCTION":        {"flows": {"C1_Assessment": "INDUCTION", "C2_Ordering": "INDUCTION", "C4_Procedure": "PROCEDURE", "C6_Escalation": "EMERGENCE", "C7_Documentation": "INDUCTION"}, "width": 5},
        "PROCEDURE":        {"flows": {"C1_Assessment": "PROCEDURE", "C2_Ordering": "PROCEDURE", "C4_Procedure": "EMERGENCE", "C6_Escalation": "PROCEDURE", "C7_Documentation": "PROCEDURE"}, "width": 5},
        "EMERGENCE":        {"flows": {"C1_Assessment": "EMERGENCE", "C4_Procedure": "INDUCTION", "C6_Escalation": "EMERGENCE", "C7_Documentation": "EMERGENCE"}, "width": 4},
        "PACU":             {"flows": {"C1_Assessment": "PACU", "C2_Ordering": "PACU", "C5_Handoff": "WARD_TRANSFER", "C6_Escalation": "PACU", "C7_Documentation": "PACU"}, "width": 5},
        "WARD_TRANSFER":    {"flows": {"C1_Assessment": "WARD_TRANSFER", "C2_Ordering": "WARD_TRANSFER", "C5_Handoff": "DISCHARGE", "C7_Documentation": "WARD_TRANSFER"}, "width": 4},
        "DISCHARGE":        {"flows": {}, "width": 0},
    },
    "Pharmacist": {
        "IDLE":       {"flows": {"C1_Assessment": "MONITORING"}, "width": 1},
        "MONITORING": {"flows": {"C1_Assessment": "MONITORING", "C2_Ordering": "MONITORING", "C6_Escalation": "MONITORING", "C7_Documentation": "MONITORING"}, "width": 4},
    },
    "Patient_Safety_Officer": {
        "IDLE":       {"flows": {"C1_Assessment": "MONITORING"}, "width": 1},
        "MONITORING": {"flows": {"C1_Assessment": "MONITORING", "C6_Escalation": "MONITORING", "C7_Documentation": "MONITORING"}, "width": 3},
    },
}


class ClinicalTracker:
    def __init__(self) -> None:
        self._states:               Dict[Tuple[str,str], str]                        = {}
        self._timed_widths:         Dict[Tuple[str,str], List[Tuple[float,int,int]]] = {}
        self._session_actor_binding: Dict[str, str]    = {}  # session_id -> first actor
        self._visited_states:       Dict[Tuple[str,str], Set[str]]                   = {}
        self._violation_history:    Dict[str, bool]                                  = {}

    def current_state(self, actor: str, patient_id: str) -> str:
        return self._states.get((actor, patient_id), "IDLE")

    def advance_state(self, actor: str, patient_id: str, next_state: str, role: str, ts: float) -> None:
        key  = (actor, patient_id)
        prev = self._states.get(key, "IDLE")
        fg   = CLINICAL_PERMITTED_FLOWS.get(role, {})
        pw   = fg.get(prev,       {}).get("width", 0)
        nw   = fg.get(next_state, {}).get("width", 0)
        self._states[key] = next_state
        self._timed_widths.setdefault(key, []).append((ts, pw, nw))
        self._visited_states.setdefault((actor, role), set()).add(next_state)

    def check_order(self, actor: str, patient_id: str, role: str, action_class: str) -> Tuple[bool, Optional[str]]:
        state = self.current_state(actor, patient_id)
        flows = CLINICAL_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        vocab = CLINICAL_ROLE_VOCABULARY.get(role, set())
        if action_class not in vocab:
            return False, None
        if action_class in flows:
            return False, flows[action_class]
        return True, None

    def check_jurisdiction(self, role: str, action_class: str) -> bool:
        return action_class not in CLINICAL_ROLE_VOCABULARY.get(role, set())

    def check_burst_cadence(self, actor: str, patient_id: str, ts: float) -> bool:
        key    = (actor, patient_id)
        cutoff = ts - BURST_TIME_WINDOW_SECONDS
        recent = [(t,wb,wa) for t,wb,wa in self._timed_widths.get(key, []) if t >= cutoff]
        return sum(1 for _,wb,wa in recent if wa > wb) >= BURST_THRESHOLD

    def check_exit(self, actor: str, patient_id: str) -> bool:
        prior = self._session_actor_binding.get(patient_id)
        return prior is not None and prior != actor

    def bind_actor(self, actor: str, patient_id: str) -> None:
        if patient_id not in self._session_actor_binding:
            self._session_actor_binding[patient_id] = actor

    def check_hysteresis(self, actor: str, role: str, action_class: str, patient_id: str) -> bool:
        if not self._violation_history.get(actor, False):
            return False
        visited = self._visited_states.get((actor, role), set())
        if not visited:
            return False
        state = self.current_state(actor, patient_id)
        flows = CLINICAL_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        nxt   = flows.get(action_class)
        return nxt is not None and nxt not in visited

    def record_violation(self, actor: str) -> None:
        self._violation_history[actor] = True


class ClinicalCompiler:
    def __init__(self) -> None:
        self.tracker = ClinicalTracker()

    def compile(self, raw_event: dict) -> dict:
        actor      = raw_event.get("actor_id", "")
        action     = raw_event.get("action", "")
        patient_id = raw_event.get("patient_id", "patient_unknown")
        ts         = raw_event.get("timestamp", time.time())
        role         = resolve_role(actor)
        action_class = resolve_action_class(action)

        self.tracker.bind_actor(actor, patient_id)

        actor_pivot  = self.tracker.check_exit(actor, patient_id)
        jurisdiction = (not actor_pivot) and self.tracker.check_jurisdiction(role, action_class)
        hysteresis   = (not actor_pivot and not jurisdiction) and \
                       self.tracker.check_hysteresis(actor, role, action_class, patient_id)
        order_violation, next_state = False, None
        if not actor_pivot and not jurisdiction and not hysteresis:
            order_violation, next_state = self.tracker.check_order(actor, patient_id, role, action_class)

        admissible = not (actor_pivot or jurisdiction or order_violation or hysteresis)

        burst_cadence = False
        if admissible and next_state:
            self.tracker.advance_state(actor, patient_id, next_state, role, ts)
            burst_cadence = self.tracker.check_burst_cadence(actor, patient_id, ts)

        if not admissible:
            self.tracker.record_violation(actor)

        bas_metrics = {
            "Admissible":            admissible,
            "ExposureEvent":         jurisdiction or order_violation,
            "OrderViolation":        order_violation,
            "JurisdictionViolation": jurisdiction,
            "RoleConfusion":         False,
            "ActorPivot":            actor_pivot,
            "HysteresisViolation":   hysteresis,
            "BurstCadence":          burst_cadence,
        }
        stp_header = {
            "Resolution": {"Completeness": ResolutionStatus.FULL.value},
            "Identity":   actor or "UNKNOWN",
            "Role":       role,
            "Action":     action_class,
            "SessionRef": patient_id,
        }
        packet = {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}
        result = evaluate_gate(packet)
        return {
            "decision":  result["decision"],
            "invariant": result.get("invariant"),
            "packet":    packet,
            "raw_event": raw_event,
        }


def run_session(events: List[dict]) -> List[dict]:
    compiler = ClinicalCompiler()
    return [compiler.compile(e) for e in events]
