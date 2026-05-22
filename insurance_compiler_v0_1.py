"""
Insurance Claims Compiler v0.1
═══════════════════════════════

Substrate #22. Insurance claims authority grammar derived from NAIC Unfair
Claims Settlement Practices Act (UCSPA), state insurance codes (Mississippi
and Louisiana primary references for Katrina anchor), and federal Fair
Claims Settlement Practices Act. Incident anchor: State Farm bad faith
claims handling, Hurricane Katrina 2005 (Mississippi Attorney General
filings 2006-2008; Broussard v. State Farm 523 F.3d 618).

Action class taxonomy (six classes):
    IC1_Intake     — claim filing, documentation receipt, initial validation
    IC2_Assess     — damage assessment, value determination, coverage analysis
    IC3_Decide     — payment authorization, denial issuance, partial settlement
    IC4_Escalate   — escalation to supervisor, fraud referral, legal hold
    IC5_Investigate — SIU investigation, surveillance authorization, EUO scheduling
    IC6_Bypass     — bypassing assessment, denying without basis (not in vocab)

Role registry:
    Claims_Intake_Agent (CIA) → IC1                  (intake only — no assess/decide)
    Claims_Adjuster (CA)      → IC1, IC2, IC4         (assessment + escalation; no decision)
    Claims_Supervisor (CS)    → IC1, IC2, IC3, IC4    (full claims authority — decision-maker)
    SIU_Investigator (SIU)    → IC1, IC4, IC5         (fraud investigation only)

Key state machine (Claims_Adjuster):
    IDLE → INTAKE_RECEIVED → ASSESSED → ESCALATED → DECIDED

State widths (Claims_Adjuster):
    IDLE:            1
    INTAKE_RECEIVED: 2   (IC1_Intake loop + IC2_Assess)
    ASSESSED:        2   (IC2_Assess loop + IC4_Escalate)
    ESCALATED:       3   (IC2_Assess + IC4_Escalate loop + IC1_Intake additional docs)
    -- IC3_Decide not in CA vocab → JURISDICTION

Key state machine (Claims_Supervisor):
    IDLE → INTAKE_RECEIVED → ASSESSED → DECIDED → RESOLVED

State widths (Claims_Supervisor):
    IDLE:            1
    INTAKE_RECEIVED: 2
    ASSESSED:        2   (IC2_Assess loop + IC3_Decide)
    DECIDED:         3   (IC3_Decide loop + IC4_Escalate + IC2_Assess re-assess)
    RESOLVED:        1

BURST geometry (C01) — Claims_Supervisor:
    ASSESSED(w=2) → DECIDED(w=3) is width-expanding.
    DECIDED(w=3) → ASSESSED(w=2) via IC2_Assess (re-assess after escalation).
    Three ASSESSED→DECIDED expansions within 60s fires BURST_CADENCE.

State Farm Katrina anchor:
    ORDER: IC3_Decide called from INTAKE_RECEIVED — denial issued before
           assessment complete (or with assessment skipped). Structural:
           IC3_Decide from INTAKE_RECEIVED (not in INTAKE_RECEIVED flows).
    JURISDICTION: Claims_Intake_Agent attempts IC3_Decide — intake agents
                  do not have decision authority; decisions are supervisor-only.
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

INS_ACTION_CLASS_MAP: Dict[str, str] = {
    # IC1 — Intake
    "file_claim":                 "IC1_Intake",
    "receive_documentation":      "IC1_Intake",
    "validate_policy_active":     "IC1_Intake",
    "log_claim_intake":           "IC1_Intake",
    "request_supplemental_docs":  "IC1_Intake",
    # IC2 — Assess
    "inspect_damage":             "IC2_Assess",
    "estimate_loss_value":        "IC2_Assess",
    "review_policy_coverage":     "IC2_Assess",
    "calculate_depreciation":     "IC2_Assess",
    "verify_loss_cause":          "IC2_Assess",
    "evaluate_exclusion_clauses": "IC2_Assess",
    # IC3 — Decide
    "authorize_payment":          "IC3_Decide",
    "issue_denial":               "IC3_Decide",
    "approve_partial_settlement": "IC3_Decide",
    "make_settlement_offer":      "IC3_Decide",
    # IC4 — Escalate
    "escalate_to_supervisor":     "IC4_Escalate",
    "refer_to_legal":             "IC4_Escalate",
    "open_appeal":                "IC4_Escalate",
    "request_management_review":  "IC4_Escalate",
    # IC5 — Investigate
    "open_siu_investigation":     "IC5_Investigate",
    "schedule_euo":               "IC5_Investigate",
    "authorize_surveillance":     "IC5_Investigate",
    "subpoena_records":           "IC5_Investigate",
    # IC6 — Bypass (not in any vocab)
    "deny_without_basis":         "IC6_Bypass",
    "alter_policy_record":        "IC6_Bypass",
    "bypass_assessment":          "IC6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return INS_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

INS_ROLE_TABLE: Dict[str, str] = {
    # State Farm Katrina actors (Mississippi AG record)
    "adjuster_lecky":         "Claims_Adjuster",        # Cori Rigsby Moran's territory
    "supervisor_state_farm":  "Claims_Supervisor",
    # Generic
    "cia_alpha":              "Claims_Intake_Agent",
    "cia_bravo":              "Claims_Intake_Agent",
    "adjuster_alpha":         "Claims_Adjuster",
    "adjuster_bravo":         "Claims_Adjuster",
    "supervisor_alpha":       "Claims_Supervisor",
    "supervisor_bravo":       "Claims_Supervisor",
    "siu_alpha":              "SIU_Investigator",
    "siu_bravo":              "SIU_Investigator",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Claims_Adjuster"
    return INS_ROLE_TABLE.get(actor_id, "Claims_Adjuster")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

INS_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Claims_Supervisor": {
        "IDLE": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.MID.value),
        },
        "INTAKE_RECEIVED": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.SURFACE.value),
            "IC2_Assess":     ("ASSESSED",        Encapsulation.MID.value),
            # NOTE: IC3_Decide NOT in INTAKE_RECEIVED → ORDER (Katrina geometry)
        },
        "ASSESSED": {
            "IC2_Assess":     ("ASSESSED",        Encapsulation.SURFACE.value),
            "IC3_Decide":     ("DECIDED",         Encapsulation.MID.value),
        },
        "DECIDED": {
            "IC2_Assess":     ("ASSESSED",        Encapsulation.MID.value),
            "IC3_Decide":     ("DECIDED",         Encapsulation.SURFACE.value),
            "IC4_Escalate":   ("DECIDED",         Encapsulation.SURFACE.value),
        },
    },

    "Claims_Adjuster": {
        "IDLE": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.MID.value),
        },
        "INTAKE_RECEIVED": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.SURFACE.value),
            "IC2_Assess":     ("ASSESSED",        Encapsulation.MID.value),
        },
        "ASSESSED": {
            "IC1_Intake":     ("ASSESSED",        Encapsulation.SURFACE.value),
            "IC2_Assess":     ("ASSESSED",        Encapsulation.SURFACE.value),
            "IC4_Escalate":   ("ESCALATED",       Encapsulation.MID.value),
            # NOTE: IC3_Decide NOT in CA vocab → always JURISDICTION
        },
        "ESCALATED": {
            "IC1_Intake":     ("ESCALATED",       Encapsulation.SURFACE.value),
            "IC2_Assess":     ("ASSESSED",        Encapsulation.MID.value),
            "IC4_Escalate":   ("ESCALATED",       Encapsulation.SURFACE.value),
        },
    },

    "Claims_Intake_Agent": {
        "IDLE": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.MID.value),
        },
        "INTAKE_RECEIVED": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.SURFACE.value),
        },
    },

    "SIU_Investigator": {
        "IDLE": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.MID.value),
        },
        "INTAKE_RECEIVED": {
            "IC1_Intake":     ("INTAKE_RECEIVED", Encapsulation.SURFACE.value),
            "IC5_Investigate":("INVESTIGATING",   Encapsulation.MID.value),
        },
        "INVESTIGATING": {
            "IC1_Intake":     ("INVESTIGATING",   Encapsulation.SURFACE.value),
            "IC4_Escalate":   ("INVESTIGATING",   Encapsulation.SURFACE.value),
            "IC5_Investigate":("INVESTIGATING",   Encapsulation.SURFACE.value),
        },
    },
}

INS_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Claims_Supervisor": {
        "IDLE":            1,
        "INTAKE_RECEIVED": 2,
        "ASSESSED":        2,
        "DECIDED":         3,
    },
    "Claims_Adjuster": {
        "IDLE":            1,
        "INTAKE_RECEIVED": 2,
        "ASSESSED":        3,
        "ESCALATED":       3,
    },
    "Claims_Intake_Agent": {
        "IDLE":            1,
        "INTAKE_RECEIVED": 1,
    },
    "SIU_Investigator": {
        "IDLE":            1,
        "INTAKE_RECEIVED": 2,
        "INVESTIGATING":   3,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class InsTracker:
    def __init__(self):
        self._states = {}; self._visited_states = {}
        self._violation_history = {}; self._width_history = {}
        self._timed_widths = {}; self._role_history = {}
        self._session_registry = {}; self._history = {}

    def _key(self, identity, role): return f"{identity}::{role}"
    def current_state(self, identity, role): return self._states.get(self._key(identity, role), "IDLE")
    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return INS_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, claim_id):
        if claim_id in self._session_registry:
            return self._session_registry[claim_id] != identity
        self._session_registry[claim_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = INS_PERMITTED_FLOWS.get(role, {})
        action_in_role = any(action in s for s in role_flows.values())
        state_flows = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": INS_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": INS_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)
        w_before = INS_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = INS_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows = INS_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class InsCompiler:
    def __init__(self): self.tracker = InsTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        claim_id   = raw_event.get("claim_id", "default_claim")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, claim_id)

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
                "ClaimID":    claim_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = InsCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
