"""
Wikipedia Edit Layer Compiler v0.1
═══════════════════════════════════

Substrate #25. Wikipedia editor authority grammar derived from Wikipedia
community policies (WP:USER, WP:BLOCK, WP:PROT, WP:3RR, WP:RFA) and
MediaWiki user-rights framework. Empirical anchor: public Wikipedia
edit logs and admin action logs (Special:Log) — fully accessible via
MediaWiki Action API. Documented incident: Essjay controversy 2007
(admin claimed false academic credentials while taking enforcement actions).

Action class taxonomy (six classes):
    W1_Read    — page view, history view, watchlist (passive)
    W2_Edit    — article edit, talk page edit, user page edit
    W3_Revert  — undo, rollback (rollback tool is admin/rollbacker-restricted)
    W4_Protect — page protection, semi-protection, full protection
    W5_Block   — user block, IP block, range block, sitewide ban
    W6_Bypass  — sockpuppetry, paid editing without disclosure, vandalism (not in vocab)

Role registry:
    Anonymous_Editor     → W1, W2 (subset — no semi-protected pages)
    Registered_Editor    → W1, W2, W3 (undo only — no rollback tool)
    Administrator        → W1, W2, W3, W4, W5
    Bureaucrat           → W1, W2, W3, W4, W5 (plus user rights grants)

Key state machine (Administrator):
    IDLE → MONITORING → REVIEWING → ACTIONABLE

State widths (Administrator):
    IDLE:        1   (W1_Read only)
    MONITORING:  2   (W1_Read loop + W2_Edit observations)
    REVIEWING:   3   (W1_Read + W2_Edit + W3_Revert — gathering context)
    ACTIONABLE:  4   (W1_Read + W3_Revert + W4_Protect + W5_Block)

BURST geometry (C01):
    REVIEWING(w=3) → ACTIONABLE(w=4) is width-expanding.
    ACTIONABLE(w=4) → REVIEWING(w=3) via W2_Edit (return to review after action logged).
    Three REVIEWING→ACTIONABLE expansions within 60s fires BURST_CADENCE.

Note: This BURST signature maps cleanly to WP:3RR (three-revert-rule)
edit warring patterns — a substrate-specific instance of the universal
BURST_CADENCE invariant.

Essjay-style anchor:
    ORDER: W5_Block called from MONITORING — admin issued block without
           the proper review step (no diffs gathered, no warning history
           checked). Structural: W5_Block from MONITORING (not in MONITORING
           flows; requires REVIEWING → ACTIONABLE gate).
    JURISDICTION: Registered_Editor attempts W5_Block — non-admins cannot
                  issue blocks. Anonymous editors cannot even edit semi-protected
                  pages.
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

WIKI_ACTION_CLASS_MAP: Dict[str, str] = {
    # W1 — Read
    "view_page":              "W1_Read",
    "view_history":            "W1_Read",
    "view_diff":               "W1_Read",
    "view_user_contribs":      "W1_Read",
    "view_talk":               "W1_Read",
    "check_watchlist":         "W1_Read",
    # W2 — Edit
    "edit_article":            "W2_Edit",
    "create_page":             "W2_Edit",
    "edit_talk_page":          "W2_Edit",
    "edit_user_page":          "W2_Edit",
    "tag_edit":                "W2_Edit",
    "post_to_anb":             "W2_Edit",
    # W3 — Revert
    "undo_edit":               "W3_Revert",
    "rollback_edit":           "W3_Revert",
    "revert_to_prior":         "W3_Revert",
    # W4 — Protect
    "semi_protect_page":       "W4_Protect",
    "fully_protect_page":      "W4_Protect",
    "move_protect_page":       "W4_Protect",
    "extended_confirmed_protect": "W4_Protect",
    # W5 — Block
    "block_user":              "W5_Block",
    "block_ip":                "W5_Block",
    "range_block":             "W5_Block",
    "sitewide_ban":            "W5_Block",
    # W6 — Bypass (not in any vocab)
    "create_sockpuppet":       "W6_Bypass",
    "evade_block":             "W6_Bypass",
    "undisclosed_paid_edit":   "W6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return WIKI_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

WIKI_ROLE_TABLE: Dict[str, str] = {
    # Essjay-era actors (public record)
    "user_essjay":           "Administrator",
    "user_jimbo_wales":      "Bureaucrat",
    # Generic
    "anon_192":              "Anonymous_Editor",
    "user_alpha":            "Registered_Editor",
    "user_bravo":            "Registered_Editor",
    "admin_alpha":           "Administrator",
    "admin_bravo":           "Administrator",
    "crat_alpha":            "Bureaucrat",
    "crat_bravo":            "Bureaucrat",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Registered_Editor"
    return WIKI_ROLE_TABLE.get(actor_id, "Registered_Editor")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

WIKI_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Administrator": {
        "IDLE": {
            "W1_Read":     ("MONITORING",  Encapsulation.MID.value),
        },
        "MONITORING": {
            "W1_Read":     ("MONITORING",  Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.MID.value),
            # NOTE: W5_Block NOT in MONITORING → ORDER (Essjay geometry)
        },
        "REVIEWING": {
            "W1_Read":     ("REVIEWING",   Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.SURFACE.value),
            "W3_Revert":   ("ACTIONABLE",  Encapsulation.DEEP.value),
        },
        "ACTIONABLE": {
            "W1_Read":     ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.MID.value),
            "W3_Revert":   ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W4_Protect":  ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W5_Block":    ("ACTIONABLE",  Encapsulation.SURFACE.value),
        },
    },

    "Bureaucrat": {
        "IDLE": {
            "W1_Read":     ("MONITORING",  Encapsulation.MID.value),
        },
        "MONITORING": {
            "W1_Read":     ("MONITORING",  Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.MID.value),
        },
        "REVIEWING": {
            "W1_Read":     ("REVIEWING",   Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.SURFACE.value),
            "W3_Revert":   ("ACTIONABLE",  Encapsulation.DEEP.value),
        },
        "ACTIONABLE": {
            "W1_Read":     ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W2_Edit":     ("REVIEWING",   Encapsulation.MID.value),
            "W3_Revert":   ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W4_Protect":  ("ACTIONABLE",  Encapsulation.SURFACE.value),
            "W5_Block":    ("ACTIONABLE",  Encapsulation.SURFACE.value),
        },
    },

    "Registered_Editor": {
        "IDLE": {
            "W1_Read":     ("VIEWING",     Encapsulation.MID.value),
        },
        "VIEWING": {
            "W1_Read":     ("VIEWING",     Encapsulation.SURFACE.value),
            "W2_Edit":     ("EDITING",     Encapsulation.MID.value),
        },
        "EDITING": {
            "W1_Read":     ("VIEWING",     Encapsulation.MID.value),
            "W2_Edit":     ("EDITING",     Encapsulation.SURFACE.value),
            "W3_Revert":   ("EDITING",     Encapsulation.SURFACE.value),
        },
    },

    "Anonymous_Editor": {
        "IDLE": {
            "W1_Read":     ("VIEWING",     Encapsulation.MID.value),
        },
        "VIEWING": {
            "W1_Read":     ("VIEWING",     Encapsulation.SURFACE.value),
            "W2_Edit":     ("EDITING",     Encapsulation.MID.value),
        },
        "EDITING": {
            "W1_Read":     ("VIEWING",     Encapsulation.MID.value),
            "W2_Edit":     ("EDITING",     Encapsulation.SURFACE.value),
        },
    },
}

WIKI_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Administrator": {
        "IDLE":        1,
        "MONITORING":  2,
        "REVIEWING":   3,
        "ACTIONABLE":  5,
    },
    "Bureaucrat": {
        "IDLE":        1,
        "MONITORING":  2,
        "REVIEWING":   3,
        "ACTIONABLE":  5,
    },
    "Registered_Editor": {
        "IDLE":    1,
        "VIEWING": 2,
        "EDITING": 3,
    },
    "Anonymous_Editor": {
        "IDLE":    1,
        "VIEWING": 2,
        "EDITING": 2,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class WikiTracker:
    def __init__(self):
        self._states = {}; self._visited_states = {}
        self._violation_history = {}; self._width_history = {}
        self._timed_widths = {}; self._role_history = {}
        self._session_registry = {}; self._history = {}

    def _key(self, identity, role): return f"{identity}::{role}"
    def current_state(self, identity, role): return self._states.get(self._key(identity, role), "IDLE")
    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return WIKI_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, page_id):
        if page_id in self._session_registry:
            return self._session_registry[page_id] != identity
        self._session_registry[page_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = WIKI_PERMITTED_FLOWS.get(role, {})
        action_in_role = any(action in s for s in role_flows.values())
        state_flows = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": WIKI_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": WIKI_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)
        w_before = WIKI_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = WIKI_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
            if not window: return False
            return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW: return False
        return sum(1 for wb, wa in window if wa is not None and wa > wb) >= BURST_THRESHOLD

    def check_hysteresis(self, identity, role, action):
        if not self._violation_history.get(identity): return False
        key = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited: return False
        role_flows = WIKI_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class WikiCompiler:
    def __init__(self): self.tracker = WikiTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        page_id    = raw_event.get("page_id", "default_page")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, page_id)

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
                "PageID":     page_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = WikiCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
