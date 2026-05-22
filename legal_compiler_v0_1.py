"""
Legal Procedural Compiler v0.1
═══════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps procedural events (actor_id, action,
    case_id) in a US criminal prosecution to the gate's BAS_Metrics vocabulary.

Domain: US federal/state criminal procedure. Models the procedural state
machine from arrest through sentencing, evaluating procedural compliance
independent of substantive legal merit. Sources: FRCrP, FRE, ABA Model Rules,
Code of Conduct for US Judges, Sineneng-Smith party-presentation doctrine.

Action class taxonomy (seven classes, sequenced):
    L1 (Case Initiation)       — indictments, complaints, charging docs
    L2 (Preliminary Motions)   — motions to dismiss, suppress, sever, venue
    L3 (Discovery Actions)     — interrogatories, depositions, subpoenas, Brady
    L4 (Pre-Trial Management)  — scheduling orders, motion rulings, voir dire
    L5 (Trial Actions)         — examination, objections, closings (sequenced)
    L6 (Verdict & Judgment)    — verdict rendering, judgment entry, sentencing
    L7 (Post-Judgment)         — appeals, reconsideration, execution

Role registry (criminal context):
    Judge              → L4, L5, L6 (excluded from L1, L2-as-initiator, L3-as-party)
    Magistrate         → L4 only (subordinate; cannot enter final judgments)
    Prosecutor         → L1, L2, L3, L5, L6 (excluded from L4-as-judge, L7-as-court)
    DefenseCounsel     → L2, L3, L5, L7 (excluded from L1, L4-as-judge, L6-as-court)
    Jury               → L6 only (verdict rendering — width=1 in VERDICT state)
    Witness            → L5 only (testimony as part of structured examination)
    ExpertWitness      → L5 only (after Daubert gatekeeping)
    CourtClerk         → administrative; L6 entry only for non-contested judgments
    Bailiff            → no L1-L7 actions; security only
    CourtReporter      → no L1-L7 actions
    ProbationOfficer   → L6 only (PSR submission, sentencing recommendations)
    AppellatePanel     → L7 only (review actions after Notice of Appeal)

JURISDICTION violations (key incident anchors):
  - Judge calls L1 (initiating prosecution): Sineneng-Smith violation,
    Judge Tamietti directed-charge violation
  - Prosecutor instructs jury (L4-as-judge): jury instruction excluded
  - Defense counsel rules on own motion (L4-as-judge): excluded

ORDER violations (key incident anchors):
  - Prosecutor references unadmitted evidence in CLOSING: closed evidentiary
    window. People v. Tate, People v. Rodriguez.
  - Prosecutor calls L5_evidentiary_offer from VERDICT/SENTENCING: temporal
    window permanently closed (Contemporaneous Objection Rule, FRE 103).

BURST_CADENCE violations (key incident anchors):
  - Rapid-fire L2 motions in PRETRIAL_MOTIONS: Abrahamsen "barrage of motions",
    Franklin 140-lawsuit case, Telectron sanctions.
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

LEGAL_ACTION_CLASS_MAP: Dict[str, str] = {
    # L1 — Case Initiation
    "file_complaint":               "L1_Initiation",
    "file_information":             "L1_Initiation",
    "return_indictment":            "L1_Initiation",
    "issue_summons":                "L1_Initiation",
    "direct_charges_from_bench":    "L1_Initiation",  # JURISDICTION anchor (Judge)
    # L2 — Preliminary Motions
    "file_motion_to_dismiss":       "L2_PreliminaryMotion",
    "file_motion_to_suppress":      "L2_PreliminaryMotion",
    "file_motion_to_sever":         "L2_PreliminaryMotion",
    "file_motion_change_venue":     "L2_PreliminaryMotion",
    "file_motion_bifurcate":        "L2_PreliminaryMotion",
    "file_motion_reconsideration":  "L2_PreliminaryMotion",
    # L3 — Discovery Actions
    "serve_interrogatories":        "L3_Discovery",
    "conduct_deposition":           "L3_Discovery",
    "serve_subpoena_duces_tecum":   "L3_Discovery",
    "request_brady_disclosure":     "L3_Discovery",
    "request_admission":            "L3_Discovery",
    # L4 — Pre-Trial Management (Judge/Magistrate territory)
    "issue_scheduling_order":       "L4_PreTrialMgmt",
    "rule_on_motion":               "L4_PreTrialMgmt",
    "grant_continuance":            "L4_PreTrialMgmt",
    "conduct_voir_dire":            "L4_PreTrialMgmt",
    "issue_daubert_ruling":         "L4_PreTrialMgmt",
    "accept_plea":                  "L4_PreTrialMgmt",
    # L5 — Trial Actions
    "deliver_opening_statement":    "L5_TrialAction",
    "conduct_direct_exam":          "L5_TrialAction",
    "conduct_cross_exam":           "L5_TrialAction",
    "conduct_redirect_exam":        "L5_TrialAction",
    "raise_evidentiary_objection":  "L5_TrialAction",
    "sustain_objection":            "L5_TrialAction",
    "deliver_closing_argument":     "L5_TrialAction",
    "introduce_unadmitted_evidence":"L5_TrialAction",  # ORDER anchor (Tate)
    "deliver_jury_instructions":    "L5_TrialAction",
    # L6 — Verdict & Judgment
    "render_verdict":               "L6_VerdictJudgment",
    "poll_jury":                    "L6_VerdictJudgment",
    "enter_judgment":               "L6_VerdictJudgment",
    "pronounce_sentence":           "L6_VerdictJudgment",
    "submit_psr":                   "L6_VerdictJudgment",
    # L7 — Post-Judgment
    "file_notice_appeal":           "L7_PostJudgment",
    "file_motion_new_trial":        "L7_PostJudgment",
    "issue_writ_execution":         "L7_PostJudgment",
    "affirm_lower_court":           "L7_PostJudgment",
    "reverse_lower_court":          "L7_PostJudgment",
    "remand_case":                  "L7_PostJudgment",
}


def resolve_action_class(action: str) -> str:
    return LEGAL_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

LEGAL_ROLE_TABLE: Dict[str, str] = {
    "judge_sineneng":       "Judge",
    "judge_tamietti":       "Judge",
    "judge_smith":          "Judge",
    "magistrate_jones":     "Magistrate",
    "prosecutor_tate":      "Prosecutor",       # People v. Tate anchor
    "prosecutor_rodriguez": "Prosecutor",       # People v. Rodriguez anchor
    "prosecutor_evans":     "Prosecutor",
    "defense_kim":          "DefenseCounsel",
    "defense_williams":     "DefenseCounsel",
    "defense_abrahamsen":   "DefenseCounsel",   # Abrahamsen "barrage" anchor
    "jury":                 "Jury",
    "witness_a":            "Witness",
    "witness_b":            "Witness",
    "expert_taylor":        "ExpertWitness",
    "clerk_johnson":        "CourtClerk",
    "bailiff_brown":        "Bailiff",
    "reporter_lee":         "CourtReporter",
    "probation_garcia":     "ProbationOfficer",
    "appellate_panel":      "AppellatePanel",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Prosecutor"
    return LEGAL_ROLE_TABLE.get(actor_id, "Prosecutor")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph (criminal prosecution state machine)
# ═══════════════════════════════════════════════════════════════════════

LEGAL_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Judge": {
        "INITIAL_APPEARANCE": {
            "L4_PreTrialMgmt": ("PRELIMINARY_HEARING", Encapsulation.MID.value),
        },
        "PRELIMINARY_HEARING": {
            "L4_PreTrialMgmt": ("ARRAIGNMENT", Encapsulation.MID.value),
        },
        "ARRAIGNMENT": {
            "L4_PreTrialMgmt": ("PRETRIAL_MOTIONS", Encapsulation.MID.value),
        },
        "PRETRIAL_MOTIONS": {
            "L4_PreTrialMgmt": ("DISCOVERY", Encapsulation.MID.value),
        },
        "DISCOVERY": {
            "L4_PreTrialMgmt": ("TRIAL", Encapsulation.MID.value),
        },
        "TRIAL": {
            "L4_PreTrialMgmt": ("TRIAL",           Encapsulation.SURFACE.value),
            "L5_TrialAction":  ("TRIAL",           Encapsulation.MID.value),
            "L6_VerdictJudgment":("VERDICT",       Encapsulation.DEEP.value),
        },
        "VERDICT": {
            # In VERDICT state, only L6 by Jury. Judge can only accept verdict (L6 entry).
            "L6_VerdictJudgment": ("SENTENCING", Encapsulation.DEEP.value),
        },
        "SENTENCING": {
            "L6_VerdictJudgment": ("POST_JUDGMENT", Encapsulation.MID.value),
        },
    },

    "Magistrate": {
        "INITIAL_APPEARANCE": {
            "L4_PreTrialMgmt": ("PRELIMINARY_HEARING", Encapsulation.MID.value),
        },
        "PRELIMINARY_HEARING": {
            "L4_PreTrialMgmt": ("ARRAIGNMENT", Encapsulation.MID.value),
        },
        "ARRAIGNMENT": {
            "L4_PreTrialMgmt": ("PRETRIAL_MOTIONS", Encapsulation.MID.value),
        },
        "PRETRIAL_MOTIONS": {
            "L4_PreTrialMgmt": ("DISCOVERY", Encapsulation.MID.value),
        },
        "DISCOVERY": {
            "L4_PreTrialMgmt": ("DISCOVERY", Encapsulation.SURFACE.value),
        },
    },

    "Prosecutor": {
        "ARREST": {
            "L1_Initiation": ("INITIAL_APPEARANCE", Encapsulation.MID.value),
        },
        "INITIAL_APPEARANCE": {
            "L1_Initiation":          ("GRAND_JURY",       Encapsulation.MID.value),
            "L2_PreliminaryMotion":   ("INITIAL_APPEARANCE", Encapsulation.SURFACE.value),
        },
        "GRAND_JURY": {
            "L1_Initiation":          ("ARRAIGNMENT",      Encapsulation.MID.value),
            "L3_Discovery":           ("GRAND_JURY",       Encapsulation.MID.value),
        },
        "ARRAIGNMENT": {
            "L2_PreliminaryMotion":   ("PRETRIAL_MOTIONS", Encapsulation.MID.value),
        },
        "PRETRIAL_MOTIONS": {
            "L2_PreliminaryMotion":   ("PRETRIAL_MOTIONS", Encapsulation.MID.value),
            "L3_Discovery":           ("DISCOVERY",        Encapsulation.MID.value),
        },
        "DISCOVERY": {
            "L3_Discovery":           ("DISCOVERY",        Encapsulation.MID.value),
            "L2_PreliminaryMotion":   ("DISCOVERY",        Encapsulation.MID.value),
        },
        "TRIAL": {
            "L5_TrialAction":         ("TRIAL",            Encapsulation.MID.value),
        },
        # VERDICT and beyond: Prosecutor has no actions — verdict is Jury territory.
    },

    "DefenseCounsel": {
        "INITIAL_APPEARANCE": {
            "L2_PreliminaryMotion":   ("INITIAL_APPEARANCE", Encapsulation.SURFACE.value),
        },
        "ARRAIGNMENT": {
            "L2_PreliminaryMotion":   ("PRETRIAL_MOTIONS",   Encapsulation.MID.value),
        },
        "PRETRIAL_MOTIONS": {
            "L2_PreliminaryMotion":   ("PRETRIAL_MOTIONS",   Encapsulation.MID.value),
            "L3_Discovery":           ("DISCOVERY",          Encapsulation.MID.value),
        },
        "DISCOVERY": {
            "L3_Discovery":           ("DISCOVERY",          Encapsulation.MID.value),
            "L2_PreliminaryMotion":   ("DISCOVERY",          Encapsulation.MID.value),
        },
        "TRIAL": {
            "L5_TrialAction":         ("TRIAL",              Encapsulation.MID.value),
        },
        "POST_JUDGMENT": {
            "L7_PostJudgment":        ("APPEAL",             Encapsulation.MID.value),
        },
        "APPEAL": {
            "L7_PostJudgment":        ("APPEAL",             Encapsulation.SURFACE.value),
        },
    },

    "Jury": {
        "VERDICT": {
            "L6_VerdictJudgment": ("VERDICT", Encapsulation.DEEP.value),
        },
    },

    "Witness": {
        "TRIAL": {
            "L5_TrialAction": ("TRIAL", Encapsulation.SURFACE.value),
        },
    },

    "ExpertWitness": {
        "TRIAL": {
            "L5_TrialAction": ("TRIAL", Encapsulation.SURFACE.value),
        },
    },

    "CourtClerk": {
        "SENTENCING": {
            "L6_VerdictJudgment": ("POST_JUDGMENT", Encapsulation.SURFACE.value),
        },
    },

    "ProbationOfficer": {
        "SENTENCING": {
            "L6_VerdictJudgment": ("SENTENCING", Encapsulation.MID.value),
        },
    },

    "AppellatePanel": {
        "APPEAL": {
            "L7_PostJudgment": ("APPEAL", Encapsulation.MID.value),
        },
    },

    # Bailiff and CourtReporter have no L1-L7 actions in their vocab
    # (they are administrative/security infrastructure)
    "Bailiff":       {},
    "CourtReporter": {},
}

LEGAL_FLOW_START_STATE: Dict[str, str] = {
    "Judge":            "INITIAL_APPEARANCE",
    "Magistrate":       "INITIAL_APPEARANCE",
    "Prosecutor":       "ARREST",
    "DefenseCounsel":   "INITIAL_APPEARANCE",
    "Jury":             "VERDICT",
    "Witness":          "TRIAL",
    "ExpertWitness":    "TRIAL",
    "CourtClerk":       "SENTENCING",
    "ProbationOfficer": "SENTENCING",
    "AppellatePanel":   "APPEAL",
    "Bailiff":          "TRIAL",
    "CourtReporter":    "TRIAL",
}

# State widths — DISCOVERY is widest, VERDICT is width-1 (Jury only)
LEGAL_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Judge": {
        "INITIAL_APPEARANCE":  1,
        "PRELIMINARY_HEARING": 1,
        "ARRAIGNMENT":         1,
        "PRETRIAL_MOTIONS":    1,
        "DISCOVERY":           1,
        "TRIAL":               3,
        "VERDICT":             1,
        "SENTENCING":          1,
    },
    "Magistrate": {
        "INITIAL_APPEARANCE":  1,
        "PRELIMINARY_HEARING": 1,
        "ARRAIGNMENT":         1,
        "PRETRIAL_MOTIONS":    1,
        "DISCOVERY":           1,
    },
    "Prosecutor": {
        "ARREST":              1,
        "INITIAL_APPEARANCE":  2,
        "GRAND_JURY":          2,
        "ARRAIGNMENT":         1,
        "PRETRIAL_MOTIONS":    2,
        "DISCOVERY":           3,   # Widest Prosecutor state — concurrent L2/L3/Brady
        "TRIAL":               1,
    },
    "DefenseCounsel": {
        "INITIAL_APPEARANCE":  1,
        "ARRAIGNMENT":         1,
        "PRETRIAL_MOTIONS":    2,
        "DISCOVERY":           2,
        "TRIAL":               1,
        "POST_JUDGMENT":       1,
        "APPEAL":              1,
    },
    "Jury":             {"VERDICT": 1},
    "Witness":          {"TRIAL": 1},
    "ExpertWitness":    {"TRIAL": 1},
    "CourtClerk":       {"SENTENCING": 1},
    "ProbationOfficer": {"SENTENCING": 1},
    "AppellatePanel":   {"APPEAL": 1},
    "Bailiff":          {},
    "CourtReporter":    {},
}


# ═══════════════════════════════════════════════════════════════════════
# LegalTracker
# ═══════════════════════════════════════════════════════════════════════

class LegalTracker:

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
        return self._states.get(key, LEGAL_FLOW_START_STATE.get(role, "TRIAL"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state = self.current_state(identity, role)
        return LEGAL_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity: str, case_id: str) -> bool:
        # In legal context, EXIT applies to role-bound case: one Judge per case,
        # one Lead Prosecutor per case. Multiple participants are normal; EXIT
        # check applies to bound-role identities. We track per case_id.
        if case_id in self._session_registry:
            return self._session_registry[case_id] != identity
        self._session_registry[case_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = LEGAL_PERMITTED_FLOWS.get(role, {})

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
                "width_before":           LEGAL_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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
                "width_before":           LEGAL_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
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

        w_before = LEGAL_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = LEGAL_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

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
        role_flows  = LEGAL_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# LegalCompiler — Layer 2
# ═══════════════════════════════════════════════════════════════════════

class LegalCompiler:

    def __init__(self) -> None:
        self.tracker = LegalTracker()

    def compile(self, raw_event: dict) -> dict:
        """
        Convert a raw legal procedural event to a BAS_Metrics packet.

        Expected raw_event shape:
            {
                "actor_id":  str,    # e.g. "judge_smith", "prosecutor_evans"
                "action":    str,    # e.g. "file_motion_to_dismiss"
                "case_id":   str,    # case identifier (binds role-actor)
                "timestamp": float,  # optional
            }
        """
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        case_id    = raw_event.get("case_id", "default_case")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, case_id)

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
            "CaseID":      case_id,
            "FromState":   traj_context.get("from_state"),
            "ToState":     traj_context.get("to_state"),
        }

        return {
            "BAS_Metrics": bas_metrics,
            "STP_Header":  stp_header,
        }


def run_session(events: list) -> list:
    compiler = LegalCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
