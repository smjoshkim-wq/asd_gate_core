"""
PACER Court Records Compiler v0.1
══════════════════════════════════

Substrate #23. Court records / documentary layer authority grammar derived
from Federal Rules of Civil Procedure (FRCP), Federal Rules of Criminal
Procedure (FRCrP), Federal Rules of Evidence (FRE), local court rules,
and PACER public access protocols. Incident anchor: Theranos criminal
proceedings, U.S. v. Holmes (3:18-cr-00258, N.D. Cal., 2018-2022);
SEC v. Theranos Inc. (5:18-cv-01602, 2018).

Distinct from substrate #11 (Legal proceedings) — that compiler targets the
courtroom sequence; this one targets the documentary record layer.

Action class taxonomy (six classes):
    PR1_File       — document filing, motion submission, evidence filing
    PR2_Serve      — service of process, notice issuance, certificate of service
    PR3_Docket     — clerk docketing, file stamping, public access provisioning
    PR4_Rule       — judicial ruling, order issuance, sanction
    PR5_Seal       — sealing motion, unsealing motion, in-camera review
    PR6_Bypass     — ex parte filing without notice, sealing without judicial order (not in vocab)

Role registry:
    Filing_Party (counsel) → PR1, PR2          (filing + service)
    Court_Clerk           → PR1, PR3, PR5      (intake, docketing, sealing per court order)
    Judge                 → PR4, PR5            (rulings + sealing authority)
    Court_Reporter        → PR3                 (transcript docketing only — no rulings)

Key state machine (Filing_Party):
    IDLE → PREPARED → FILED → SERVED → RULED → APPEALED

State widths (Filing_Party):
    IDLE:      1   (PR1_File only)
    PREPARED:  2   (PR1_File loop + PR2_Serve)  -- but only after filing
    FILED:     2   (PR1_File supplements + PR2_Serve)
    SERVED:    3   (PR1_File response + PR2_Serve loop + PR4_Rule await -- pseudo)

Actually filing party can't trigger PR4_Rule themselves. Let me re-design.

Key state machine (Filing_Party):
    IDLE → FILED → SERVED → AWAITING_RULING → POST_RULING

Widths (Filing_Party):
    IDLE:            1   (PR1_File only)
    FILED:           2   (PR1_File supplements + PR2_Serve)
    SERVED:          3   (PR1_File response + PR2_Serve add'l + PR5_Seal motion)
    AWAITING_RULING: 2   (PR1_File supplemental + PR5_Seal motion)
    POST_RULING:     2   (PR1_File appeal/motion to reconsider + PR2_Serve)

BURST geometry (C01) — Filing_Party:
    FILED(w=2) → SERVED(w=3) is width-expanding.
    SERVED(w=3) → FILED(w=2) via PR1_File (additional document filed before final service).
    Three FILED→SERVED expansions within 60s fires BURST_CADENCE.

Theranos anchor:
    ORDER: PR4_Rule called from FILED state (before SERVED) — Judge ruling on
           motion before opposing party properly served. Structural analog:
           PR4_Rule from a state where PR2_Serve gate has not been satisfied.
    JURISDICTION: Court_Reporter attempts PR4_Rule — reporter has no ruling
                  authority; only Judge can issue PR4_Rule.
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

PACER_ACTION_CLASS_MAP: Dict[str, str] = {
    # PR1 — File
    "file_motion":             "PR1_File",
    "file_complaint":          "PR1_File",
    "file_response":           "PR1_File",
    "file_reply":              "PR1_File",
    "file_exhibit":            "PR1_File",
    "file_supplemental":       "PR1_File",
    "file_appeal":             "PR1_File",
    # PR2 — Serve
    "serve_process":           "PR2_Serve",
    "issue_summons":           "PR2_Serve",
    "file_certificate_of_service":"PR2_Serve",
    "serve_subpoena":          "PR2_Serve",
    "notice_of_motion":        "PR2_Serve",
    # PR3 — Docket
    "docket_filing":           "PR3_Docket",
    "stamp_received":          "PR3_Docket",
    "assign_case_number":      "PR3_Docket",
    "publish_to_pacer":        "PR3_Docket",
    "docket_transcript":       "PR3_Docket",
    # PR4 — Rule
    "issue_order":             "PR4_Rule",
    "grant_motion":            "PR4_Rule",
    "deny_motion":             "PR4_Rule",
    "issue_sanction":          "PR4_Rule",
    "issue_summary_judgment":  "PR4_Rule",
    # PR5 — Seal
    "grant_motion_to_seal":    "PR5_Seal",
    "deny_motion_to_seal":     "PR5_Seal",
    "order_in_camera_review":  "PR5_Seal",
    "unseal_document":         "PR5_Seal",
    "motion_to_seal":          "PR5_Seal",
    # PR6 — Bypass (not in any vocab)
    "ex_parte_without_notice": "PR6_Bypass",
    "seal_without_order":      "PR6_Bypass",
    "alter_docket_record":     "PR6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return PACER_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

PACER_ROLE_TABLE: Dict[str, str] = {
    # Theranos proceedings (US v. Holmes 3:18-cr-00258 N.D.Cal.)
    "doj_counsel":           "Filing_Party",
    "holmes_counsel":        "Filing_Party",
    "judge_davila":          "Judge",            # Hon. Edward J. Davila
    "clerk_ndcal":           "Court_Clerk",
    "reporter_ndcal":        "Court_Reporter",
    # Generic
    "filing_alpha":          "Filing_Party",
    "filing_bravo":          "Filing_Party",
    "clerk_alpha":           "Court_Clerk",
    "clerk_bravo":           "Court_Clerk",
    "judge_alpha":           "Judge",
    "judge_bravo":           "Judge",
    "reporter_alpha":        "Court_Reporter",
    "reporter_bravo":        "Court_Reporter",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Filing_Party"
    return PACER_ROLE_TABLE.get(actor_id, "Filing_Party")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

PACER_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Filing_Party": {
        "IDLE": {
            "PR1_File":   ("FILED",           Encapsulation.MID.value),
        },
        "FILED": {
            "PR1_File":   ("FILED",           Encapsulation.SURFACE.value),
            "PR2_Serve":  ("SERVED",          Encapsulation.MID.value),
        },
        "SERVED": {
            "PR1_File":   ("FILED",           Encapsulation.MID.value),
            "PR2_Serve":  ("SERVED",          Encapsulation.SURFACE.value),
            "PR5_Seal":   ("SERVED",          Encapsulation.SURFACE.value),
        },
        "AWAITING_RULING": {
            "PR1_File":   ("AWAITING_RULING", Encapsulation.SURFACE.value),
            "PR5_Seal":   ("AWAITING_RULING", Encapsulation.SURFACE.value),
        },
        "POST_RULING": {
            "PR1_File":   ("FILED",           Encapsulation.MID.value),
            "PR2_Serve":  ("POST_RULING",     Encapsulation.SURFACE.value),
        },
    },

    "Judge": {
        "IDLE": {
            "PR4_Rule":   ("RULING",          Encapsulation.MID.value),
            "PR5_Seal":   ("RULING",          Encapsulation.MID.value),
        },
        "RULING": {
            "PR4_Rule":   ("RULING",          Encapsulation.SURFACE.value),
            "PR5_Seal":   ("RULING",          Encapsulation.SURFACE.value),
        },
    },

    "Court_Clerk": {
        "IDLE": {
            "PR1_File":   ("INTAKE",          Encapsulation.MID.value),
        },
        "INTAKE": {
            "PR1_File":   ("INTAKE",          Encapsulation.SURFACE.value),
            "PR3_Docket": ("DOCKETED",        Encapsulation.MID.value),
        },
        "DOCKETED": {
            "PR1_File":   ("INTAKE",          Encapsulation.MID.value),
            "PR3_Docket": ("DOCKETED",        Encapsulation.SURFACE.value),
            "PR5_Seal":   ("DOCKETED",        Encapsulation.SURFACE.value),
        },
    },

    "Court_Reporter": {
        "IDLE": {
            "PR3_Docket": ("DOCKETING",       Encapsulation.MID.value),
        },
        "DOCKETING": {
            "PR3_Docket": ("DOCKETING",       Encapsulation.SURFACE.value),
        },
    },
}

PACER_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Filing_Party": {
        "IDLE":            1,
        "FILED":           2,
        "SERVED":          3,
        "AWAITING_RULING": 2,
        "POST_RULING":     2,
    },
    "Judge": {
        "IDLE":   2,
        "RULING": 2,
    },
    "Court_Clerk": {
        "IDLE":     1,
        "INTAKE":   2,
        "DOCKETED": 3,
    },
    "Court_Reporter": {
        "IDLE":      1,
        "DOCKETING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class PacerTracker:
    def __init__(self):
        self._states = {}; self._visited_states = {}
        self._violation_history = {}; self._width_history = {}
        self._timed_widths = {}; self._role_history = {}
        self._session_registry = {}; self._history = {}

    def _key(self, identity, role): return f"{identity}::{role}"
    def current_state(self, identity, role): return self._states.get(self._key(identity, role), "IDLE")
    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return PACER_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, case_id):
        if case_id in self._session_registry:
            return self._session_registry[case_id] != identity
        self._session_registry[case_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = PACER_PERMITTED_FLOWS.get(role, {})
        action_in_role = any(action in s for s in role_flows.values())
        state_flows = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": PACER_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": PACER_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)
        w_before = PACER_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = PACER_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows = PACER_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class PacerCompiler:
    def __init__(self): self.tracker = PacerTracker()

    def compile(self, raw_event):
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

        is_known = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = actor_pivot = False
        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, case_id)

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
                "CaseID":     case_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = PacerCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
