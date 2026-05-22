"""
OpenStreetMap Changeset Compiler v0.1
══════════════════════════════════════

Substrate #26. OpenStreetMap editor authority grammar derived from OSM
Foundation policies, ODbL license terms, Data Working Group (DWG) action
documentation, and OSM API access framework. Empirical anchor: public
OSM changeset feed (https://planet.openstreetmap.org/replication/) —
fully accessible. Documented incidents: MAPS.ME mass-edit dispute (2018),
several DWG account actions over copyrighted data uploads.

Action class taxonomy (six classes):
    O1_View      — map view, history view, changeset feed (passive)
    O2_Edit      — changeset creation, node/way/relation editing, tag changes
    O3_Revert    — changeset revert via DWG tool, manual revert
    O4_Discuss   — changeset comment, diary entry, issue report
    O5_Mediate   — DWG account action, mass-rollback, block, license enforcement
    O6_Bypass    — mass automated edits without bot flag, copyright violation upload (not in vocab)

Role registry:
    Anonymous     → O1                  (read only — OSM requires account to edit)
    Mapper        → O1, O2, O4          (standard editor — no revert/mediate tools)
    Moderator     → O1, O2, O3, O4      (community moderator — revert + discuss)
    DWG_Member    → O1, O2, O3, O4, O5  (full moderation including account actions)

Key state machine (DWG_Member):
    IDLE → MONITORING → REVIEWING → MEDIATING

State widths (DWG_Member):
    IDLE:       1   (O1_View only)
    MONITORING: 2   (O1_View loop + O4_Discuss)
    REVIEWING:  3   (O1_View + O2_Edit + O3_Revert)
    MEDIATING:  4   (O1_View + O3_Revert + O4_Discuss + O5_Mediate)

BURST geometry (C01):
    REVIEWING(w=3) → MEDIATING(w=4) is width-expanding.
    MEDIATING(w=4) → REVIEWING(w=3) via O2_Edit (return to review).
    Three REVIEWING→MEDIATING expansions within 60s fires BURST_CADENCE.

MAPS.ME / DWG-style anchor:
    ORDER: O5_Mediate called from MONITORING — DWG took account action without
           the proper review/revert step first. Structural: O5_Mediate from
           MONITORING (not in MONITORING flows; requires REVIEWING → MEDIATING gate).
    JURISDICTION: Mapper attempts O5_Mediate — only DWG members can issue
                  account actions. Anonymous editors cannot edit at all.
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

OSM_ACTION_CLASS_MAP: Dict[str, str] = {
    # O1 — View
    "view_map":                   "O1_View",
    "view_changeset":             "O1_View",
    "view_user_history":          "O1_View",
    "view_changeset_feed":        "O1_View",
    "view_diary_entry":           "O1_View",
    # O2 — Edit
    "create_changeset":           "O2_Edit",
    "add_node":                   "O2_Edit",
    "modify_way":                 "O2_Edit",
    "add_relation":               "O2_Edit",
    "tag_change":                 "O2_Edit",
    "upload_gps_trace":           "O2_Edit",
    # O3 — Revert
    "revert_changeset":           "O3_Revert",
    "rollback_user_edits":        "O3_Revert",
    "manual_undo":                "O3_Revert",
    # O4 — Discuss
    "comment_on_changeset":       "O4_Discuss",
    "post_diary_entry":           "O4_Discuss",
    "open_dwg_ticket":            "O4_Discuss",
    "raise_data_issue":           "O4_Discuss",
    # O5 — Mediate
    "block_user":                 "O5_Mediate",
    "mass_rollback":              "O5_Mediate",
    "issue_dmca_response":        "O5_Mediate",
    "redact_object":              "O5_Mediate",
    "remove_license_violation":   "O5_Mediate",
    # O6 — Bypass (not in any vocab)
    "mass_edit_without_botflag":  "O6_Bypass",
    "upload_copyrighted_data":    "O6_Bypass",
    "tag_with_disputed_source":   "O6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return OSM_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

OSM_ROLE_TABLE: Dict[str, str] = {
    # MAPS.ME dispute era actors (public DWG record)
    "user_mapsme_bot":     "Mapper",
    "dwg_2018":            "DWG_Member",
    # Generic
    "anon_osm":            "Anonymous",
    "mapper_alpha":        "Mapper",
    "mapper_bravo":        "Mapper",
    "mod_alpha":           "Moderator",
    "mod_bravo":           "Moderator",
    "dwg_alpha":           "DWG_Member",
    "dwg_bravo":           "DWG_Member",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Mapper"
    return OSM_ROLE_TABLE.get(actor_id, "Mapper")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

OSM_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "DWG_Member": {
        "IDLE": {
            "O1_View":     ("MONITORING", Encapsulation.MID.value),
        },
        "MONITORING": {
            "O1_View":     ("MONITORING", Encapsulation.SURFACE.value),
            "O4_Discuss":  ("REVIEWING",  Encapsulation.MID.value),
            # NOTE: O5_Mediate NOT in MONITORING → ORDER (skipping review)
        },
        "REVIEWING": {
            "O1_View":     ("REVIEWING",  Encapsulation.SURFACE.value),
            "O2_Edit":     ("REVIEWING",  Encapsulation.SURFACE.value),
            "O3_Revert":   ("MEDIATING",  Encapsulation.DEEP.value),
        },
        "MEDIATING": {
            "O1_View":     ("MEDIATING",  Encapsulation.SURFACE.value),
            "O2_Edit":     ("REVIEWING",  Encapsulation.MID.value),
            "O3_Revert":   ("MEDIATING",  Encapsulation.SURFACE.value),
            "O4_Discuss":  ("MEDIATING",  Encapsulation.SURFACE.value),
            "O5_Mediate":  ("MEDIATING",  Encapsulation.SURFACE.value),
        },
    },

    "Moderator": {
        "IDLE": {
            "O1_View":     ("MONITORING", Encapsulation.MID.value),
        },
        "MONITORING": {
            "O1_View":     ("MONITORING", Encapsulation.SURFACE.value),
            "O4_Discuss":  ("REVIEWING",  Encapsulation.MID.value),
        },
        "REVIEWING": {
            "O1_View":     ("REVIEWING",  Encapsulation.SURFACE.value),
            "O2_Edit":     ("REVIEWING",  Encapsulation.SURFACE.value),
            "O3_Revert":   ("REVIEWING",  Encapsulation.SURFACE.value),
            "O4_Discuss":  ("REVIEWING",  Encapsulation.SURFACE.value),
        },
    },

    "Mapper": {
        "IDLE": {
            "O1_View":     ("VIEWING",    Encapsulation.MID.value),
        },
        "VIEWING": {
            "O1_View":     ("VIEWING",    Encapsulation.SURFACE.value),
            "O2_Edit":     ("EDITING",    Encapsulation.MID.value),
        },
        "EDITING": {
            "O1_View":     ("VIEWING",    Encapsulation.MID.value),
            "O2_Edit":     ("EDITING",    Encapsulation.SURFACE.value),
            "O4_Discuss":  ("EDITING",    Encapsulation.SURFACE.value),
        },
    },

    "Anonymous": {
        "IDLE": {
            "O1_View":     ("VIEWING",    Encapsulation.MID.value),
        },
        "VIEWING": {
            "O1_View":     ("VIEWING",    Encapsulation.SURFACE.value),
        },
    },
}

OSM_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "DWG_Member": {
        "IDLE":       1,
        "MONITORING": 2,
        "REVIEWING":  3,
        "MEDIATING":  5,
    },
    "Moderator": {
        "IDLE":       1,
        "MONITORING": 2,
        "REVIEWING":  4,
    },
    "Mapper": {
        "IDLE":    1,
        "VIEWING": 2,
        "EDITING": 3,
    },
    "Anonymous": {
        "IDLE":    1,
        "VIEWING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class OsmTracker:
    def __init__(self):
        self._states = {}; self._visited_states = {}
        self._violation_history = {}; self._width_history = {}
        self._timed_widths = {}; self._role_history = {}
        self._session_registry = {}; self._history = {}

    def _key(self, identity, role): return f"{identity}::{role}"
    def current_state(self, identity, role): return self._states.get(self._key(identity, role), "IDLE")
    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return OSM_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, cs_id):
        if cs_id in self._session_registry:
            return self._session_registry[cs_id] != identity
        self._session_registry[cs_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = OSM_PERMITTED_FLOWS.get(role, {})
        action_in_role = any(action in s for s in role_flows.values())
        state_flows = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": OSM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": OSM_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)
        w_before = OSM_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = OSM_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows = OSM_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class OsmCompiler:
    def __init__(self): self.tracker = OsmTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        cs_id      = raw_event.get("cs_id", "default_changeset")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, cs_id)

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
                "ChangesetID":cs_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = OsmCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
