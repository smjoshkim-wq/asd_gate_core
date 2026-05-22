"""
Election Administration Compiler v0.1
══════════════════════════════════════

Substrate #20. Election administration authority grammar derived from
Help America Vote Act (HAVA, 52 U.S.C. § 20901 et seq.), state election
codes (Florida Election Code FS Ch. 102 as primary reference), and
US Election Assistance Commission Voluntary Voting System Guidelines.
Incident anchor: Florida 2000 presidential recount (Bush v. Gore,
531 U.S. 98; Florida Supreme Court filings 2000-2001).

Action class taxonomy (six classes):
    E1_Verify     — voter ID check, eligibility verification, signature match
    E2_Distribute — ballot issuance, voting machine access, provisional ballot
    E3_Count      — ballot counting, tabulation, machine reading
    E4_Adjudicate — ballot challenge resolution, intent determination, hanging chad
    E5_Certify    — result certification, recount authorization, final tally
    E6_Bypass     — unauthorized count modification, bypassing chain of custody (not in vocab)

Role registry:
    Polling_Official     → E1, E2          (front line; no count/certify)
    Canvasser            → E1, E3, E4       (counting layer)
    Election_Supervisor  → E1, E3, E4, E5   (certification authority)
    Observer             → E1                (witness only — no operational authority)

Key state machine (Canvasser):
    IDLE → INTAKE_OPEN → COUNTING → DISPUTED → RECONCILED → CERTIFIED

State widths (Canvasser):
    IDLE:        1   (E1_Verify only)
    INTAKE_OPEN: 2   (E1_Verify loop + E3_Count)
    COUNTING:    2   (E1_Verify + E3_Count loop)
    DISPUTED:    3   (E1_Verify + E3_Count + E4_Adjudicate loop)
    RECONCILED:  2   (E1_Verify + E5_Certify)  -- Canvasser has E5 here? No — Supervisor only
    CERTIFIED:   1

Actually: Canvasser ends at RECONCILED. Supervisor handles RECONCILED→CERTIFIED.

BURST geometry (C01):
    COUNTING(w=2) → DISPUTED(w=3) is width-expanding.
    DISPUTED(w=3) → COUNTING(w=2) via E1_Verify (return to count after dispute logged).
    Three COUNTING→DISPUTED expansions within 60s fires BURST_CADENCE.

Florida 2000 anchor:
    ORDER: E5_Certify called from RECONCILED before disputed ballots fully
           adjudicated — Florida SoS certification rushed while disputes
           outstanding. Structural: E5_Certify from DISPUTED state (not in
           Canvasser vocab from DISPUTED) or with disputes unresolved.
    JURISDICTION: Observer attempted E3_Count action — not in Observer vocab.
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

ELECTION_ACTION_CLASS_MAP: Dict[str, str] = {
    # E1 — Verify
    "verify_voter_id":            "E1_Verify",
    "check_registration":         "E1_Verify",
    "match_signature":            "E1_Verify",
    "confirm_eligibility":        "E1_Verify",
    "observe_ballot_handling":    "E1_Verify",
    "witness_count":              "E1_Verify",
    # E2 — Distribute
    "issue_ballot":               "E2_Distribute",
    "issue_provisional_ballot":   "E2_Distribute",
    "grant_machine_access":       "E2_Distribute",
    "distribute_voting_materials":"E2_Distribute",
    # E3 — Count
    "tabulate_ballot":            "E3_Count",
    "read_machine_total":         "E3_Count",
    "manual_recount":             "E3_Count",
    "scan_ballot":                "E3_Count",
    "tally_provisional":          "E3_Count",
    # E4 — Adjudicate
    "resolve_ballot_challenge":   "E4_Adjudicate",
    "determine_voter_intent":     "E4_Adjudicate",
    "rule_hanging_chad":          "E4_Adjudicate",
    "log_ballot_dispute":         "E4_Adjudicate",
    "review_overvote":            "E4_Adjudicate",
    # E5 — Certify
    "certify_precinct_total":     "E5_Certify",
    "issue_canvass_certificate":  "E5_Certify",
    "authorize_recount":          "E5_Certify",
    "publish_final_tally":        "E5_Certify",
    # E6 — Bypass (not in any vocab)
    "modify_count_unauthorized":  "E6_Bypass",
    "bypass_chain_of_custody":    "E6_Bypass",
    "alter_ballot_record":        "E6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return ELECTION_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

ELECTION_ROLE_TABLE: Dict[str, str] = {
    # Florida 2000 actors (public record, Bush v. Gore)
    "supervisor_palm_beach":   "Election_Supervisor",  # Theresa LePore (PBC)
    "canvasser_pbc":           "Canvasser",
    "observer_dem":            "Observer",
    "observer_gop":            "Observer",
    # Generic
    "polling_official_alpha":  "Polling_Official",
    "polling_official_bravo":  "Polling_Official",
    "canvasser_alpha":         "Canvasser",
    "canvasser_bravo":         "Canvasser",
    "supervisor_alpha":        "Election_Supervisor",
    "supervisor_bravo":        "Election_Supervisor",
    "observer_alpha":          "Observer",
    "observer_bravo":          "Observer",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Canvasser"
    return ELECTION_ROLE_TABLE.get(actor_id, "Canvasser")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

ELECTION_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Canvasser": {
        "IDLE": {
            "E1_Verify":     ("INTAKE_OPEN", Encapsulation.MID.value),
        },
        "INTAKE_OPEN": {
            "E1_Verify":     ("INTAKE_OPEN", Encapsulation.SURFACE.value),
            "E3_Count":      ("COUNTING",    Encapsulation.MID.value),
        },
        "COUNTING": {
            "E1_Verify":     ("COUNTING",    Encapsulation.SURFACE.value),
            "E3_Count":      ("COUNTING",    Encapsulation.SURFACE.value),
            "E4_Adjudicate": ("DISPUTED",    Encapsulation.MID.value),
            # NOTE: E5_Certify NOT in Canvasser vocab — always JURISDICTION
        },
        "DISPUTED": {
            "E1_Verify":     ("COUNTING",    Encapsulation.MID.value),
            "E3_Count":      ("DISPUTED",    Encapsulation.SURFACE.value),
            "E4_Adjudicate": ("DISPUTED",    Encapsulation.SURFACE.value),
        },
    },

    "Election_Supervisor": {
        "IDLE": {
            "E1_Verify":     ("INTAKE_OPEN", Encapsulation.MID.value),
        },
        "INTAKE_OPEN": {
            "E1_Verify":     ("INTAKE_OPEN", Encapsulation.SURFACE.value),
            "E3_Count":      ("COUNTING",    Encapsulation.MID.value),
        },
        "COUNTING": {
            "E1_Verify":     ("COUNTING",    Encapsulation.SURFACE.value),
            "E3_Count":      ("COUNTING",    Encapsulation.SURFACE.value),
            "E4_Adjudicate": ("DISPUTED",    Encapsulation.MID.value),
        },
        "DISPUTED": {
            "E1_Verify":     ("COUNTING",    Encapsulation.MID.value),
            "E3_Count":      ("DISPUTED",    Encapsulation.SURFACE.value),
            "E4_Adjudicate": ("RECONCILED",  Encapsulation.MID.value),
        },
        "RECONCILED": {
            "E1_Verify":     ("RECONCILED",  Encapsulation.SURFACE.value),
            "E5_Certify":    ("CERTIFIED",   Encapsulation.DEEP.value),
            # NOTE: E5_Certify NOT in COUNTING flows → ORDER if attempted there
        },
        "CERTIFIED": {
            "E5_Certify":    ("CERTIFIED",   Encapsulation.SURFACE.value),
        },
    },

    "Polling_Official": {
        "IDLE": {
            "E1_Verify":     ("STATION_OPEN",Encapsulation.MID.value),
        },
        "STATION_OPEN": {
            "E1_Verify":     ("STATION_OPEN",Encapsulation.SURFACE.value),
            "E2_Distribute": ("STATION_OPEN",Encapsulation.SURFACE.value),
        },
    },

    "Observer": {
        "IDLE": {
            "E1_Verify":     ("OBSERVING",   Encapsulation.MID.value),
        },
        "OBSERVING": {
            "E1_Verify":     ("OBSERVING",   Encapsulation.SURFACE.value),
            # No other actions — observers only verify/witness
        },
    },
}

ELECTION_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Canvasser": {
        "IDLE":        1,
        "INTAKE_OPEN": 2,
        "COUNTING":    2,
        "DISPUTED":    3,
    },
    "Election_Supervisor": {
        "IDLE":        1,
        "INTAKE_OPEN": 2,
        "COUNTING":    2,
        "DISPUTED":    3,
        "RECONCILED":  2,
        "CERTIFIED":   1,
    },
    "Polling_Official": {
        "IDLE":         1,
        "STATION_OPEN": 2,
    },
    "Observer": {
        "IDLE":      1,
        "OBSERVING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class ElectionTracker:
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
        return ELECTION_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, precinct_id):
        if precinct_id in self._session_registry:
            return self._session_registry[precinct_id] != identity
        self._session_registry[precinct_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = ELECTION_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": ELECTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": ELECTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = ELECTION_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = ELECTION_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows  = ELECTION_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class ElectionCompiler:
    def __init__(self):
        self.tracker = ElectionTracker()

    def compile(self, raw_event):
        actor_id    = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw  = raw_event.get("action", "")
        precinct_id = raw_event.get("precinct_id", "default_precinct")
        event_ts    = raw_event.get("timestamp")

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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, precinct_id)

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
                "PrecinctID": precinct_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = ElectionCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
