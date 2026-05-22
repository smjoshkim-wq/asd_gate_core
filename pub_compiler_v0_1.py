"""
Academic Publishing Compiler v0.1
══════════════════════════════════

Substrate #21. Academic publishing authority grammar derived from COPE
(Committee on Publication Ethics) Core Practices, ICMJE Recommendations
for the Conduct, Reporting, Editing and Publication of Scholarly Work,
and journal-specific peer review protocols. Incident anchor: Hwang Woo-suk
fabricated stem cell results, Science 2004-05 (Science retraction 2006;
Seoul National University Investigation Committee report, 2006).

Action class taxonomy (six classes):
    AP1_Submit     — manuscript submission, revision submission, ethics declaration
    AP2_Review     — peer review execution, comment provision, recommendation
    AP3_Decide     — editorial decision (accept/reject/major revision)
    AP4_Investigate — ethics inquiry, plagiarism check, fraud investigation
    AP5_Retract    — retraction, correction, expression of concern
    AP6_Bypass     — ghost authorship, fabricated reviewers, undisclosed conflicts (not in vocab)

Role registry:
    Author    → AP1                       (submission only — no review/decide/retract)
    Reviewer  → AP2                       (review only — no decision authority)
    Editor    → AP1, AP2, AP3, AP4, AP5    (full editorial authority)
    Editorial_Board_Member → AP3, AP4, AP5  (oversight; can investigate and retract; no review)

Key state machine (Editor):
    IDLE → SUBMITTED → UNDER_REVIEW → REVIEW_COMPLETE → DECIDED → PUBLISHED → INVESTIGATED → RETRACTED

State widths (Editor):
    IDLE:            1   (AP1_Submit receipt)
    SUBMITTED:       2   (AP1_Submit loop + AP2_Review assignment)
    UNDER_REVIEW:    2   (AP2_Review loop + AP3_Decide pre-decision)
    REVIEW_COMPLETE: 3   (AP3_Decide + AP1_Submit revision-request + AP4_Investigate)
    DECIDED:         2   (AP3_Decide loop + AP1_Submit final version)
    PUBLISHED:       3   (AP4_Investigate + AP5_Retract + AP1_Submit correction)
    INVESTIGATED:    2   (AP4_Investigate loop + AP5_Retract)
    RETRACTED:       1   (AP5_Retract loop)

BURST geometry (C01):
    UNDER_REVIEW(w=2) → REVIEW_COMPLETE(w=3) is width-expanding.
    REVIEW_COMPLETE(w=3) → UNDER_REVIEW(w=2) via AP2_Review (re-review after revision).
    Three UNDER_REVIEW→REVIEW_COMPLETE expansions within 60s fires BURST_CADENCE.

Hwang Woo-suk anchor (Science retraction 2006):
    ORDER: AP3_Decide called from UNDER_REVIEW before reviews complete — editor
           accepted publication while peer review still outstanding or with
           insufficient peer scrutiny. Structural: AP3_Decide from UNDER_REVIEW
           state without REVIEW_COMPLETE gate.
    JURISDICTION: Reviewer attempted AP3_Decide — reviewers do not have decision
                  authority; editorial decision is editor-exclusive.
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

PUB_ACTION_CLASS_MAP: Dict[str, str] = {
    # AP1 — Submit
    "submit_manuscript":          "AP1_Submit",
    "submit_revision":            "AP1_Submit",
    "submit_correction":          "AP1_Submit",
    "submit_ethics_declaration":  "AP1_Submit",
    "submit_final_version":       "AP1_Submit",
    # AP2 — Review
    "perform_peer_review":        "AP2_Review",
    "submit_review_comments":     "AP2_Review",
    "recommend_acceptance":       "AP2_Review",
    "recommend_revision":         "AP2_Review",
    "recommend_rejection":        "AP2_Review",
    "assign_reviewers":           "AP2_Review",
    # AP3 — Decide
    "issue_acceptance":           "AP3_Decide",
    "issue_rejection":            "AP3_Decide",
    "issue_revision_request":     "AP3_Decide",
    "make_editorial_decision":    "AP3_Decide",
    # AP4 — Investigate
    "initiate_ethics_review":     "AP4_Investigate",
    "conduct_plagiarism_check":   "AP4_Investigate",
    "investigate_data_fabrication":"AP4_Investigate",
    "review_author_response":     "AP4_Investigate",
    "convene_ethics_committee":   "AP4_Investigate",
    # AP5 — Retract
    "issue_retraction":           "AP5_Retract",
    "publish_correction":         "AP5_Retract",
    "issue_expression_of_concern":"AP5_Retract",
    "publish_erratum":            "AP5_Retract",
    # AP6 — Bypass (not in any vocab)
    "ghost_authorship":           "AP6_Bypass",
    "fabricate_reviewer":         "AP6_Bypass",
    "undisclosed_coi":            "AP6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return PUB_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

PUB_ROLE_TABLE: Dict[str, str] = {
    # Hwang Woo-suk actors (Science retraction 2006)
    "editor_science":          "Editor",
    "reviewer_science_a":      "Reviewer",
    "reviewer_science_b":      "Reviewer",
    # Generic
    "author_alpha":            "Author",
    "author_bravo":            "Author",
    "reviewer_alpha":          "Reviewer",
    "reviewer_bravo":          "Reviewer",
    "editor_alpha":            "Editor",
    "editor_bravo":            "Editor",
    "ebm_alpha":               "Editorial_Board_Member",
    "ebm_bravo":               "Editorial_Board_Member",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Editor"
    return PUB_ROLE_TABLE.get(actor_id, "Editor")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

PUB_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Editor": {
        "IDLE": {
            "AP1_Submit":      ("SUBMITTED",       Encapsulation.MID.value),
        },
        "SUBMITTED": {
            "AP1_Submit":      ("SUBMITTED",       Encapsulation.SURFACE.value),
            "AP2_Review":      ("UNDER_REVIEW",    Encapsulation.MID.value),
            # NOTE: AP3_Decide NOT in SUBMITTED → ORDER (decision before review)
        },
        "UNDER_REVIEW": {
            "AP2_Review":      ("REVIEW_COMPLETE", Encapsulation.MID.value),
            "AP1_Submit":      ("UNDER_REVIEW",    Encapsulation.SURFACE.value),
            # NOTE: AP3_Decide NOT in UNDER_REVIEW → ORDER (Hwang geometry)
            # AP3_Decide only valid from REVIEW_COMPLETE
        },
        "REVIEW_COMPLETE": {
            "AP3_Decide":      ("DECIDED",         Encapsulation.DEEP.value),
            "AP1_Submit":      ("UNDER_REVIEW",    Encapsulation.MID.value),
            "AP2_Review":      ("UNDER_REVIEW",    Encapsulation.MID.value),
            "AP4_Investigate": ("INVESTIGATED",    Encapsulation.MID.value),
        },
        "DECIDED": {
            "AP3_Decide":      ("DECIDED",         Encapsulation.SURFACE.value),
            "AP1_Submit":      ("PUBLISHED",       Encapsulation.MID.value),
        },
        "PUBLISHED": {
            "AP1_Submit":      ("PUBLISHED",       Encapsulation.SURFACE.value),
            "AP4_Investigate": ("INVESTIGATED",    Encapsulation.MID.value),
            "AP5_Retract":     ("RETRACTED",       Encapsulation.DEEP.value),
        },
        "INVESTIGATED": {
            "AP4_Investigate": ("INVESTIGATED",    Encapsulation.SURFACE.value),
            "AP5_Retract":     ("RETRACTED",       Encapsulation.DEEP.value),
        },
        "RETRACTED": {
            "AP5_Retract":     ("RETRACTED",       Encapsulation.SURFACE.value),
        },
    },

    "Editorial_Board_Member": {
        "IDLE": {
            "AP4_Investigate": ("INVESTIGATED",    Encapsulation.MID.value),
        },
        "INVESTIGATED": {
            "AP4_Investigate": ("INVESTIGATED",    Encapsulation.SURFACE.value),
            "AP3_Decide":      ("DECIDED",         Encapsulation.MID.value),
            "AP5_Retract":     ("RETRACTED",       Encapsulation.DEEP.value),
        },
        "DECIDED": {
            "AP3_Decide":      ("DECIDED",         Encapsulation.SURFACE.value),
        },
        "RETRACTED": {
            "AP5_Retract":     ("RETRACTED",       Encapsulation.SURFACE.value),
        },
    },

    "Author": {
        "IDLE": {
            "AP1_Submit":      ("SUBMITTED",       Encapsulation.MID.value),
        },
        "SUBMITTED": {
            "AP1_Submit":      ("SUBMITTED",       Encapsulation.SURFACE.value),
        },
    },

    "Reviewer": {
        "IDLE": {
            "AP2_Review":      ("REVIEWING",       Encapsulation.MID.value),
        },
        "REVIEWING": {
            "AP2_Review":      ("REVIEWING",       Encapsulation.SURFACE.value),
        },
    },
}

PUB_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Editor": {
        "IDLE":            1,
        "SUBMITTED":       2,
        "UNDER_REVIEW":    2,
        "REVIEW_COMPLETE": 4,
        "DECIDED":         2,
        "PUBLISHED":       3,
        "INVESTIGATED":    2,
        "RETRACTED":       1,
    },
    "Editorial_Board_Member": {
        "IDLE":         1,
        "INVESTIGATED": 3,
        "DECIDED":      1,
        "RETRACTED":    1,
    },
    "Author": {
        "IDLE":      1,
        "SUBMITTED": 1,
    },
    "Reviewer": {
        "IDLE":      1,
        "REVIEWING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class PubTracker:
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
        return PUB_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, ms_id):
        if ms_id in self._session_registry:
            return self._session_registry[ms_id] != identity
        self._session_registry[ms_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = PUB_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": PUB_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": PUB_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = PUB_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = PUB_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows  = PUB_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class PubCompiler:
    def __init__(self):
        self.tracker = PubTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        ms_id      = raw_event.get("ms_id", "default_ms")  # manuscript id
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, ms_id)

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
                "MSID":       ms_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = PubCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
