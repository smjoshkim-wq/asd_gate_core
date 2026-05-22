"""
Pharmaceutical Drug Approval Compiler v0.1
═══════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps drug development events (actor_id,
    action, program_id) to the gate's BAS_Metrics vocabulary.

Domain: US/Canada/ICH-harmonized pharmaceutical drug development pipeline
from IND/CTA filing through NDA/BLA approval and post-market surveillance.
Sources: FDA 21 CFR Parts 50, 56, 312, 314; ICH E6(R3) GCP; Helsinki
Declaration; Health Canada Food and Drugs Act Division 5/8; PDUFA statutes.

Action class taxonomy (eight classes):
    P1 (Preclinical Execution)   — animal toxicity, teratogenicity, PK
    P2 (IND/CTA Submission)      — filing IND or CTA with regulator
    P3 (IND Activation)          — 30-day review expiration or NOL
    C1 (Dose Escalation)         — Phase I cohort advance (safety-gated)
    C2 (Subject Enrollment)      — consent + randomization (IRB-gated)
    S1 (Expedited Safety Report) — 7-day/15-day reports (temporal gate)
    S2 (DSMB Unblinding)         — interim analysis (independent committee)
    S3 (Clinical Hold)           — FDA suspension (regulatory override)
    R1 (NDA/BLA Submit)          — final regulatory filing
    R2 (AdCom Convene)           — advisory committee
    R3 (Approval Decision)       — FDA Director Approval or CRL
    M1 (Pharmacovigilance)       — post-market monitoring

Role registry:
    Sponsor          → P1, P2, R1, M1 (excluded from S2 unblinding, S3, R3)
    PI               → C1, C2, S1 (excluded from R1, R3, M1)
    CRA              → audit only — no clinical or regulatory actions
    IRB              → S3 (institutional suspension only)
    DSMB             → S2 only (Sponsor strictly excluded from S2)
    FDAReviewer      → S3, R2 (suspension and AdCom recommendation)
    FDADirector      → S3, R2, R3 (final approval authority)
    HCReviewer       → S3 equivalent + approval analog
    AdComMember      → R2 (advisory voting only)
    Subject          → C2 (consent execution only)

Key incident anchors:
  - Thalidomide (1957–61): ORDER — premature R3 attempt before complete P1
    sequence (teratogenicity testing). Frances Kelsey blocked at FDA.
  - Vioxx (2004): JURISDICTION — Sponsor executed S2 (DSMB unblinding /
    adjudication SOP modification) — class strictly excluded from Sponsor.
  - Gelsinger (1999): ORDER — PI executed C1 (dose escalation) without
    completing mandatory safety confirmation loop after prior Grade 3 toxicities.
    Also failed to execute S1 (expedited safety report) within temporal window.
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

PHARMA_ACTION_CLASS_MAP: Dict[str, str] = {
    # P1 — Preclinical Execution
    "execute_animal_toxicity":     "P1_Preclinical",
    "execute_teratogenicity":      "P1_Preclinical",
    "execute_pharmacokinetics":    "P1_Preclinical",
    "execute_genotoxicity":        "P1_Preclinical",
    # P2 — IND/CTA Submission
    "submit_ind_application":      "P2_IND_Submit",
    "submit_cta_application":      "P2_IND_Submit",
    # P3 — IND Activation
    "issue_ind_activation":        "P3_IND_Activation",
    "issue_nol":                   "P3_IND_Activation",  # Health Canada NOL
    # C1 — Dose Escalation
    "advance_dose_cohort":         "C1_DoseEscalation",
    "initiate_phase2":             "C1_DoseEscalation",
    "initiate_phase3":             "C1_DoseEscalation",
    # C2 — Subject Enrollment
    "enroll_subject":              "C2_SubjectEnrollment",
    "obtain_informed_consent":     "C2_SubjectEnrollment",
    "randomize_subject":           "C2_SubjectEnrollment",
    # S1 — Expedited Safety Reporting
    "submit_7day_safety_report":   "S1_SafetyReport",
    "submit_15day_safety_report":  "S1_SafetyReport",
    "report_serious_adverse_event":"S1_SafetyReport",
    # S2 — DSMB Unblinding (excluded from Sponsor)
    "request_interim_unblinding":  "S2_DSMB_Unblinding",
    "recommend_trial_termination": "S2_DSMB_Unblinding",
    "modify_adjudication_sop":     "S2_DSMB_Unblinding",  # Vioxx anchor
    # S3 — Clinical Hold
    "impose_clinical_hold":        "S3_ClinicalHold",
    "suspend_trial_irb":           "S3_ClinicalHold",
    "lift_clinical_hold":          "S3_ClinicalHold",
    # R1 — NDA/BLA Submit
    "submit_nda":                  "R1_NDA_Submit",
    "submit_bla":                  "R1_NDA_Submit",
    "submit_nds":                  "R1_NDA_Submit",
    # R2 — AdCom Convene
    "convene_adcom":               "R2_AdCom",
    "vote_adcom_recommendation":   "R2_AdCom",
    # R3 — Approval Decision
    "issue_approval_letter":       "R3_Approval",
    "issue_complete_response_letter":"R3_Approval",
    "issue_noc":                   "R3_Approval",  # Health Canada NOC
    # M1 — Pharmacovigilance
    "submit_psur":                 "M1_Pharmacovigilance",
    "issue_label_update":          "M1_Pharmacovigilance",
    "withdraw_drug":               "M1_Pharmacovigilance",
}


def resolve_action_class(action: str) -> str:
    return PHARMA_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

PHARMA_ROLE_TABLE: Dict[str, str] = {
    "sponsor_merck":         "Sponsor",       # Vioxx anchor
    "sponsor_grunenthal":    "Sponsor",       # Thalidomide anchor
    "sponsor_pfizer":        "Sponsor",
    "sponsor_a":             "Sponsor",
    "pi_wilson":             "PI",            # Gelsinger trial PI anchor
    "pi_smith":              "PI",
    "pi_chen":               "PI",
    "cra_jones":             "CRA",
    "irb_penn":              "IRB",           # Penn IRB (Gelsinger)
    "irb_a":                 "IRB",
    "dsmb_vigor":            "DSMB",          # Vioxx VIGOR DSMB anchor
    "dsmb_a":                "DSMB",
    "fda_reviewer_kelsey":   "FDAReviewer",   # Thalidomide hero anchor
    "fda_reviewer_a":        "FDAReviewer",
    "fda_director":          "FDADirector",
    "hc_reviewer":           "HCReviewer",
    "adcom_member_1":        "AdComMember",
    "adcom_member_2":        "AdComMember",
    "subject_gelsinger":     "Subject",       # Jesse Gelsinger anchor
    "subject_a":             "Subject",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Sponsor"
    return PHARMA_ROLE_TABLE.get(actor_id, "Sponsor")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph (drug development state machine)
# ═══════════════════════════════════════════════════════════════════════

PHARMA_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Sponsor": {
        "PRECLINICAL": {
            "P1_Preclinical": ("PRECLINICAL", Encapsulation.SURFACE.value),
            "P2_IND_Submit":  ("IND_SUBMITTED", Encapsulation.MID.value),
        },
        "IND_SUBMITTED": {
            "P1_Preclinical": ("IND_SUBMITTED", Encapsulation.SURFACE.value),
        },
        "IND_ACTIVE": {
            "S1_SafetyReport": ("IND_ACTIVE", Encapsulation.MID.value),
        },
        "PHASE_I": {
            "S1_SafetyReport": ("PHASE_I", Encapsulation.MID.value),
        },
        "PHASE_II": {
            "S1_SafetyReport": ("PHASE_II", Encapsulation.MID.value),
        },
        "PHASE_III": {
            "S1_SafetyReport": ("PHASE_III", Encapsulation.MID.value),
            "R1_NDA_Submit":   ("NDA_SUBMITTED", Encapsulation.DEEP.value),
        },
        "NDA_SUBMITTED": {
            "S1_SafetyReport": ("NDA_SUBMITTED", Encapsulation.SURFACE.value),
        },
        "FDA_REVIEW": {
            "S1_SafetyReport": ("FDA_REVIEW", Encapsulation.SURFACE.value),
        },
        "POST_MARKET": {
            "M1_Pharmacovigilance": ("POST_MARKET", Encapsulation.MID.value),
        },
    },

    "PI": {
        # PI begins in IND_ACTIVE (after IND activation)
        "IND_ACTIVE": {
            "C2_SubjectEnrollment": ("PHASE_I", Encapsulation.MID.value),
            "S1_SafetyReport":      ("IND_ACTIVE", Encapsulation.SURFACE.value),
        },
        "PHASE_I": {
            "C2_SubjectEnrollment": ("PHASE_I", Encapsulation.MID.value),
            "C1_DoseEscalation":    ("PHASE_II", Encapsulation.MID.value),  # phase advance
            "S1_SafetyReport":      ("PHASE_I", Encapsulation.MID.value),
        },
        "PHASE_II": {
            "C2_SubjectEnrollment": ("PHASE_II", Encapsulation.MID.value),
            "C1_DoseEscalation":    ("PHASE_III", Encapsulation.MID.value),  # phase advance
            "S1_SafetyReport":      ("PHASE_II", Encapsulation.MID.value),
        },
        "PHASE_III": {
            "C2_SubjectEnrollment": ("PHASE_III", Encapsulation.MID.value),
            "S1_SafetyReport":      ("PHASE_III", Encapsulation.MID.value),
        },
    },

    "CRA": {
        # Auditor — no clinical or regulatory action authority
    },

    "IRB": {
        # IRB has S3 (suspend trial at institution level)
        "IND_ACTIVE": {
            "S3_ClinicalHold": ("IND_ACTIVE", Encapsulation.DEEP.value),
        },
        "PHASE_I": {
            "S3_ClinicalHold": ("PHASE_I", Encapsulation.DEEP.value),
        },
        "PHASE_II": {
            "S3_ClinicalHold": ("PHASE_II", Encapsulation.DEEP.value),
        },
        "PHASE_III": {
            "S3_ClinicalHold": ("PHASE_III", Encapsulation.DEEP.value),
        },
    },

    "DSMB": {
        # DSMB only — S2 unblinding is its exclusive action class
        "PHASE_II": {
            "S2_DSMB_Unblinding": ("PHASE_II", Encapsulation.DEEP.value),
        },
        "PHASE_III": {
            "S2_DSMB_Unblinding": ("PHASE_III", Encapsulation.DEEP.value),
        },
    },

    "FDAReviewer": {
        "IND_SUBMITTED": {
            "P3_IND_Activation": ("IND_ACTIVE",    Encapsulation.MID.value),
            "S3_ClinicalHold":   ("IND_SUBMITTED", Encapsulation.DEEP.value),
        },
        "IND_ACTIVE": {
            "S3_ClinicalHold":   ("IND_ACTIVE", Encapsulation.DEEP.value),
        },
        "PHASE_I": {
            "S3_ClinicalHold":   ("PHASE_I", Encapsulation.DEEP.value),
        },
        "PHASE_II": {
            "S3_ClinicalHold":   ("PHASE_II", Encapsulation.DEEP.value),
        },
        "PHASE_III": {
            "S3_ClinicalHold":   ("PHASE_III", Encapsulation.DEEP.value),
        },
        "FDA_REVIEW": {
            "R2_AdCom":          ("FDA_REVIEW",       Encapsulation.MID.value),
            "S3_ClinicalHold":   ("FDA_REVIEW",       Encapsulation.DEEP.value),
        },
    },

    "FDADirector": {
        "FDA_REVIEW": {
            "R2_AdCom":   ("FDA_REVIEW",        Encapsulation.MID.value),
            "R3_Approval":("APPROVAL_DECISION", Encapsulation.DEEP.value),
        },
        "APPROVAL_DECISION": {
            "R3_Approval":("POST_MARKET",       Encapsulation.DEEP.value),
        },
        "POST_MARKET": {
            "M1_Pharmacovigilance":("POST_MARKET", Encapsulation.MID.value),
        },
    },

    "HCReviewer": {
        "IND_SUBMITTED": {
            "P3_IND_Activation": ("IND_ACTIVE", Encapsulation.MID.value),
        },
        "FDA_REVIEW": {
            "R3_Approval": ("POST_MARKET", Encapsulation.DEEP.value),
        },
    },

    "AdComMember": {
        "FDA_REVIEW": {
            "R2_AdCom": ("FDA_REVIEW", Encapsulation.MID.value),
        },
    },

    "Subject": {
        "IND_ACTIVE": {
            "C2_SubjectEnrollment": ("PHASE_I", Encapsulation.SURFACE.value),
        },
        "PHASE_I": {
            "C2_SubjectEnrollment": ("PHASE_I", Encapsulation.SURFACE.value),
        },
    },
}

PHARMA_FLOW_START_STATE: Dict[str, str] = {
    "Sponsor":     "PRECLINICAL",
    "PI":          "IND_ACTIVE",
    "CRA":         "IND_ACTIVE",
    "IRB":         "IND_ACTIVE",
    "DSMB":        "PHASE_II",
    "FDAReviewer": "IND_SUBMITTED",
    "FDADirector": "FDA_REVIEW",
    "HCReviewer":  "IND_SUBMITTED",
    "AdComMember": "FDA_REVIEW",
    "Subject":     "IND_ACTIVE",
}

PHARMA_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Sponsor": {
        "PRECLINICAL":   2,
        "IND_SUBMITTED": 1,
        "IND_ACTIVE":    1,
        "PHASE_I":       1,
        "PHASE_II":      1,
        "PHASE_III":     2,
        "NDA_SUBMITTED": 1,
        "FDA_REVIEW":    1,
        "POST_MARKET":   1,
    },
    "PI": {
        "IND_ACTIVE": 1,
        "PHASE_I":    2,   # +1 expansion from IND_ACTIVE
        "PHASE_II":   3,   # +1 expansion from PHASE_I
        "PHASE_III":  4,   # +1 expansion from PHASE_II — 3 expansions total = BURST
    },
    "CRA":         {},
    "IRB": {
        "IND_ACTIVE": 1,
        "PHASE_I":    1,
        "PHASE_II":   1,
        "PHASE_III":  1,
    },
    "DSMB": {
        "PHASE_II":  1,
        "PHASE_III": 1,
    },
    "FDAReviewer": {
        "IND_SUBMITTED": 2,
        "IND_ACTIVE":    1,
        "PHASE_I":       1,
        "PHASE_II":      1,
        "PHASE_III":     1,
        "FDA_REVIEW":    2,
    },
    "FDADirector": {
        "FDA_REVIEW":        2,
        "APPROVAL_DECISION": 1,
        "POST_MARKET":       1,
    },
    "HCReviewer":  {"IND_SUBMITTED": 1, "FDA_REVIEW": 1},
    "AdComMember": {"FDA_REVIEW": 1},
    "Subject":     {"IND_ACTIVE": 1, "PHASE_I": 1},
}


# ═══════════════════════════════════════════════════════════════════════
# PharmaTracker
# ═══════════════════════════════════════════════════════════════════════

class PharmaTracker:

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
        return self._states.get(key, PHARMA_FLOW_START_STATE.get(role, "IND_ACTIVE"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return PHARMA_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, program_id: str) -> bool:
        if program_id in self._session_registry:
            return self._session_registry[program_id] != identity
        self._session_registry[program_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = PHARMA_PERMITTED_FLOWS.get(role, {})

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
                "width_before":           PHARMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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
                "width_before":           PHARMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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

        w_before = PHARMA_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = PHARMA_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
        role_flows  = PHARMA_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# PharmaCompiler — Layer 2
# ═══════════════════════════════════════════════════════════════════════

class PharmaCompiler:

    def __init__(self) -> None:
        self.tracker = PharmaTracker()

    def compile(self, raw_event: dict) -> dict:
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        program_id = raw_event.get("program_id", "default_program")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, program_id)

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
            if self.tracker.check_hysteresis(identity_label, role, action):
                cur = self.tracker.current_state(identity_label, role)
                traj_context = {
                    "admissible": False, "from_state": cur, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": self.tracker.width_at_current_state(identity_label, role),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False,
                    "hysteresis_violation": True,
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
                "role_confusion": False, "actor_pivot": False,
                "hysteresis_violation": False,
            }

        burst_cadence = False
        if traj_context.get("admissible") and traj_context.get("width_after") is not None:
            self.tracker.record_width(identity_label, traj_context["width_before"],
                                      traj_context["width_after"], timestamp=event_ts)
            burst_cadence = self.tracker.check_burst_cadence(identity_label, current_time=event_ts)

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
            "Identity":   identity_label, "Role": role, "Action": action,
            "RawAction":  action_raw, "ProgramID": program_id,
            "FromState":  traj_context.get("from_state"),
            "ToState":    traj_context.get("to_state"),
        }

        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events: list) -> list:
    compiler = PharmaCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
