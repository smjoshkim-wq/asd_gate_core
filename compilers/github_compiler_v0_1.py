"""
GitHub Software Development Workflow Compiler v0.1
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

GITHUB_EVENT_CLASS_MAP: Dict[str, str] = {
    "PushEvent":               "G1_Contribution",
    "CreateEvent":             "G1_Contribution",
    "ForkEvent":               "G1_Contribution",
    "open_pull_request":       "G1_Contribution",
    "push_commit":             "G1_Contribution",
    "create_branch":           "G1_Contribution",
    "PullRequestReviewEvent":          "G2_Review",
    "PullRequestReviewCommentEvent":   "G2_Review",
    "IssueCommentEvent":               "G2_Review",
    "request_review":                  "G2_Review",
    "approve_pr":                      "G2_Review",
    "request_changes":                 "G2_Review",
    "review_comment":                  "G2_Review",
    "merge_pull_request":      "G3_Integration",
    "PullRequestEvent_merged": "G3_Integration",
    "ReleaseEvent":            "G4_Release",
    "create_tag":              "G4_Release",
    "publish_release":         "G4_Release",
    "force_push":              "G5_Admin",
    "bypass_protection":       "G5_Admin",
    "delete_branch":           "G5_Admin",
    "add_collaborator":        "G5_Admin",
    "change_permissions":      "G5_Admin",
    "MemberEvent":             "G5_Admin",
    "PublicEvent":             "G5_Admin",
}

def resolve_event_class(event_type: str) -> str:
    return GITHUB_EVENT_CLASS_MAP.get(event_type, "UNKNOWN")

GITHUB_ROLE_TABLE: Dict[str, str] = {
    "repo_owner_1":     "Owner",
    "repo_owner_2":     "Owner",
    "maintainer_alice": "Maintainer",
    "maintainer_bob":   "Maintainer",
    "contributor_dev1": "Contributor",
    "contributor_dev2": "Contributor",
    "contributor_dev3": "Contributor",
    "reviewer_carol":   "Reviewer",
    "reviewer_dave":    "Reviewer",
}

def resolve_role(actor_login: str) -> str:
    if not actor_login:
        return "Contributor"
    return GITHUB_ROLE_TABLE.get(actor_login, "Contributor")

GITHUB_ROLE_VOCABULARY: Dict[str, Set[str]] = {
    "Owner":       {"G1_Contribution", "G2_Review", "G3_Integration", "G4_Release", "G5_Admin"},
    "Maintainer":  {"G1_Contribution", "G2_Review", "G3_Integration", "G4_Release"},
    "Contributor": {"G1_Contribution", "G2_Review"},
    "Reviewer":    {"G2_Review"},
}

GITHUB_PERMITTED_FLOWS: Dict[str, Dict] = {
    "Owner": {
        "IDLE":         {"flows": {"G1_Contribution": "OPEN"}, "width": 1},
        "OPEN":         {"flows": {"G1_Contribution": "OPEN", "G2_Review": "UNDER_REVIEW", "G5_Admin": "OPEN"}, "width": 3},
        "UNDER_REVIEW": {"flows": {"G2_Review": "APPROVED", "G1_Contribution": "OPEN", "G5_Admin": "UNDER_REVIEW"}, "width": 3},
        "APPROVED":     {"flows": {"G3_Integration": "MERGED", "G1_Contribution": "UNDER_REVIEW"}, "width": 2},
        "MERGED":       {"flows": {"G4_Release": "RELEASED", "G5_Admin": "MERGED"}, "width": 2},
        "RELEASED":     {"flows": {}, "width": 0},
    },
    "Maintainer": {
        "IDLE":         {"flows": {"G1_Contribution": "OPEN"}, "width": 1},
        "OPEN":         {"flows": {"G1_Contribution": "OPEN", "G2_Review": "UNDER_REVIEW"}, "width": 2},
        "UNDER_REVIEW": {"flows": {"G2_Review": "APPROVED", "G1_Contribution": "OPEN"}, "width": 2},
        "APPROVED":     {"flows": {"G3_Integration": "MERGED", "G1_Contribution": "UNDER_REVIEW"}, "width": 2},
        "MERGED":       {"flows": {"G4_Release": "RELEASED"}, "width": 1},
        "RELEASED":     {"flows": {}, "width": 0},
    },
    "Contributor": {
        "IDLE":         {"flows": {"G1_Contribution": "OPEN"}, "width": 1},
        "OPEN":         {"flows": {"G1_Contribution": "OPEN", "G2_Review": "UNDER_REVIEW"}, "width": 2},
        "UNDER_REVIEW": {"flows": {"G2_Review": "APPROVED", "G1_Contribution": "OPEN"}, "width": 2},
        "APPROVED":     {"flows": {"G1_Contribution": "UNDER_REVIEW"}, "width": 1},
        "MERGED":       {"flows": {}, "width": 0},
        "RELEASED":     {"flows": {}, "width": 0},
    },
    "Reviewer": {
        "IDLE":         {"flows": {"G2_Review": "UNDER_REVIEW"}, "width": 1},
        "OPEN":         {"flows": {"G2_Review": "UNDER_REVIEW"}, "width": 1},
        "UNDER_REVIEW": {"flows": {"G2_Review": "APPROVED"}, "width": 1},
        "APPROVED":     {"flows": {"G2_Review": "UNDER_REVIEW"}, "width": 1},
        "MERGED":       {"flows": {}, "width": 0},
        "RELEASED":     {"flows": {}, "width": 0},
    },
}


class GitHubTracker:
    def __init__(self) -> None:
        self._states:           Dict[Tuple[str,str], str]                         = {}
        self._timed_widths:     Dict[Tuple[str,str], List[Tuple[float,int,int]]]  = {}
        self._session_actor_binding: Dict[str, str]                               = {}  # pr_id → first actor
        self._visited_states:   Dict[Tuple[str,str], Set[str]]                    = {}
        self._violation_history: Dict[str, bool]                                  = {}

    def current_state(self, actor: str, pr_id: str) -> str:
        return self._states.get((actor, pr_id), "IDLE")

    def advance_state(self, actor: str, pr_id: str, next_state: str, role: str, ts: float) -> None:
        key = (actor, pr_id)
        prev = self._states.get(key, "IDLE")
        fg   = GITHUB_PERMITTED_FLOWS.get(role, {})
        pw   = fg.get(prev,       {}).get("width", 0)
        nw   = fg.get(next_state, {}).get("width", 0)
        self._states[key] = next_state
        self._timed_widths.setdefault(key, []).append((ts, pw, nw))
        self._visited_states.setdefault((actor, role), set()).add(next_state)

    def check_order(self, actor: str, pr_id: str, role: str, action_class: str) -> Tuple[bool, Optional[str]]:
        state = self.current_state(actor, pr_id)
        flows = GITHUB_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        vocab = GITHUB_ROLE_VOCABULARY.get(role, set())
        if action_class not in vocab:
            return False, None
        if action_class in flows:
            return False, flows[action_class]
        return True, None

    def check_jurisdiction(self, role: str, action_class: str) -> bool:
        return action_class not in GITHUB_ROLE_VOCABULARY.get(role, set())

    def check_burst_cadence(self, actor: str, pr_id: str, ts: float) -> bool:
        key    = (actor, pr_id)
        cutoff = ts - BURST_TIME_WINDOW_SECONDS
        recent = [(t,wb,wa) for t,wb,wa in self._timed_widths.get(key, []) if t >= cutoff]
        return sum(1 for _,wb,wa in recent if wa > wb) >= BURST_THRESHOLD

    def check_exit(self, actor: str, pr_id: str) -> bool:
        prior = self._session_actor_binding.get(pr_id)
        return prior is not None and prior != actor

    def bind_actor(self, actor: str, pr_id: str) -> None:
        if pr_id not in self._session_actor_binding:
            self._session_actor_binding[pr_id] = actor

    def check_hysteresis(self, actor: str, role: str, action_class: str, pr_id: str) -> bool:
        if not self._violation_history.get(actor, False):
            return False
        visited = self._visited_states.get((actor, role), set())
        if not visited:
            return False
        state  = self.current_state(actor, pr_id)
        flows  = GITHUB_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        nxt    = flows.get(action_class)
        return nxt is not None and nxt not in visited

    def record_violation(self, actor: str) -> None:
        self._violation_history[actor] = True


class GitHubCompiler:
    def __init__(self) -> None:
        self.tracker = GitHubTracker()

    def compile(self, raw_event: dict) -> dict:
        actor        = raw_event.get("actor_login", "")
        event_type   = raw_event.get("event_type", "")
        pr_id        = raw_event.get("pr_id", "pr_unknown")
        ts           = raw_event.get("timestamp", time.time())
        role         = resolve_role(actor)
        action_class = resolve_event_class(event_type)

        self.tracker.bind_actor(actor, pr_id)

        actor_pivot  = self.tracker.check_exit(actor, pr_id)
        jurisdiction = (not actor_pivot) and self.tracker.check_jurisdiction(role, action_class)
        hysteresis   = (not actor_pivot and not jurisdiction) and \
                       self.tracker.check_hysteresis(actor, role, action_class, pr_id)
        order_violation, next_state = False, None
        if not actor_pivot and not jurisdiction and not hysteresis:
            order_violation, next_state = self.tracker.check_order(actor, pr_id, role, action_class)

        admissible = not (actor_pivot or jurisdiction or order_violation or hysteresis)

        burst_cadence = False
        if admissible and next_state:
            self.tracker.advance_state(actor, pr_id, next_state, role, ts)
            burst_cadence = self.tracker.check_burst_cadence(actor, pr_id, ts)

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
            "SessionRef": pr_id,
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
    compiler = GitHubCompiler()
    return [compiler.compile(e) for e in events]
