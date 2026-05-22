"""
Cyber Incident Response — Human Layer Compiler v0.1
════════════════════════════════════════════════════

Substrate #16. Distinct from Cyber syscall compiler (#1) — this compiler
targets the human response layer: the analyst/lead/CISO/legal decision
pipeline that runs on top of the technical detection layer.

Primary doctrine: NIST SP 800-61 Rev 2 (Computer Security Incident Handling
Guide); CISA IR Playbook (2021); SEC Regulation S-K Item 106 (cybersecurity
disclosure); Equifax 2017 breach response (congressional record, SEC filing).

Action class taxonomy (six classes):
    IR1_Detect    — detection, monitoring, initial alert triage (loops in state)
    IR2_Triage    — severity assessment, scope determination, breach confirmation
    IR3_Contain   — isolation, blocking, credential rotation, quarantine
    IR4_Escalate  — formal escalation up the IR chain; incident ticket creation
    IR5_Disclose  — regulatory notification, public disclosure, SEC filing
    IR6_Bypass    — bypassing approval gate or escalation path (not in any vocab)

Role registry:
    IR_Analyst      → IR1, IR2, IR3, IR4         (no disclosure authority)
    IR_Lead         → IR1, IR2, IR3, IR4         (no unilateral disclosure)
    CISO            → IR1, IR2, IR3, IR4, IR5    (full IR authority)
    Legal_Compliance → IR4, IR5                  (approval + disclosure only)

Key state machine (IR_Analyst):
    IDLE → ALERT_RECEIVED → TRIAGED → CONTAINED → ESCALATED

State widths (IR_Analyst):
    IDLE:           1   (IR1_Detect only)
    ALERT_RECEIVED: 2   (IR1_Detect loop + IR2_Triage)
    TRIAGED:        2   (IR2_Triage loop + IR3_Contain)
    CONTAINED:      3   (IR3_Contain loop + IR4_Escalate + IR2_Triage re-assess)
    ESCALATED:      1   (IR4_Escalate loop — no IR5 in analyst vocab)

BURST geometry (C01):
    TRIAGED(w=2) → CONTAINED(w=3) is width-expanding.
    CONTAINED(w=3) → TRIAGED(w=2) contracts (re-assess path).
    Three TRIAGED→CONTAINED expansions within 60 s fires BURST_CADENCE.
    Both states already visited when burst runs → HYSTERESIS does NOT fire.
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
# Action class map
# ═══════════════════════════════════════════════════════════════════════

IR_ACTION_CLASS_MAP: Dict[str, str] = {
    # IR1 — Detect / Monitor
    "monitor_siem":                  "IR1_Detect",
    "review_alert":                  "IR1_Detect",
    "check_ioc":                     "IR1_Detect",
    "query_logs":                    "IR1_Detect",
    "scan_endpoint":                 "IR1_Detect",
    "review_network_traffic":        "IR1_Detect",
    # IR2 — Triage
    "assess_severity":               "IR2_Triage",
    "determine_scope":               "IR2_Triage",
    "classify_incident":             "IR2_Triage",
    "confirm_breach":                "IR2_Triage",
    "identify_affected_systems":     "IR2_Triage",
    # IR3 — Contain
    "isolate_system":                "IR3_Contain",
    "block_ip":                      "IR3_Contain",
    "rotate_credentials":            "IR3_Contain",
    "patch_vulnerability":           "IR3_Contain",
    "quarantine_host":               "IR3_Contain",
    "revoke_access":                 "IR3_Contain",
    # IR4 — Escalate
    "escalate_to_lead":              "IR4_Escalate",
    "escalate_to_ciso":              "IR4_Escalate",
    "notify_legal":                  "IR4_Escalate",
    "open_incident_ticket":          "IR4_Escalate",
    "brief_exec":                    "IR4_Escalate",
    "request_legal_hold":            "IR4_Escalate",
    # IR5 — Disclose
    "file_regulatory_notification":  "IR5_Disclose",
    "issue_public_statement":        "IR5_Disclose",
    "notify_affected_parties":       "IR5_Disclose",
    "submit_sec_filing":             "IR5_Disclose",
    "notify_dhs_cisa":               "IR5_Disclose",
    # IR6 — Bypass (not in any role's vocab)
    "bypass_approval_gate":          "IR6_Bypass",
    "skip_escalation":               "IR6_Bypass",
    "self_authorize_disclosure":     "IR6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return IR_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

IR_ROLE_TABLE: Dict[str, str] = {
    # Equifax 2017 response actors (congressional record)
    "analyst_mandiant":       "IR_Analyst",
    "analyst_alpha":          "IR_Analyst",
    "analyst_bravo":          "IR_Analyst",
    "ir_lead_alpha":          "IR_Lead",
    "ciso_equifax":           "CISO",        # Susan Mauldin (Equifax CISO)
    "ciso_alpha":             "CISO",
    "legal_equifax":          "Legal_Compliance",
    "legal_alpha":            "Legal_Compliance",
    # Generic
    "analyst_generic":        "IR_Analyst",
    "ir_lead_generic":        "IR_Lead",
    "ciso_generic":           "CISO",
    "legal_generic":          "Legal_Compliance",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "IR_Analyst"
    return IR_ROLE_TABLE.get(actor_id, "IR_Analyst")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

IR_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "IR_Analyst": {
        "IDLE": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.MID.value),
        },
        "ALERT_RECEIVED": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
        },
        "TRIAGED": {
            "IR2_Triage":   ("TRIAGED",         Encapsulation.SURFACE.value),
            "IR3_Contain":  ("CONTAINED",       Encapsulation.MID.value),
            # NOTE: IR5_Disclose NOT in analyst vocab → always JURISDICTION
            # NOTE: IR3_Contain from ALERT_RECEIVED → ORDER
        },
        "CONTAINED": {
            "IR3_Contain":  ("CONTAINED",       Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
            "IR4_Escalate": ("ESCALATED",       Encapsulation.DEEP.value),
        },
        "ESCALATED": {
            "IR4_Escalate": ("ESCALATED",       Encapsulation.SURFACE.value),
            # No IR5_Disclose — analyst cannot disclose
        },
    },

    "IR_Lead": {
        "IDLE": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.MID.value),
        },
        "ALERT_RECEIVED": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
        },
        "TRIAGED": {
            "IR2_Triage":   ("TRIAGED",         Encapsulation.SURFACE.value),
            "IR3_Contain":  ("CONTAINED",       Encapsulation.MID.value),
        },
        "CONTAINED": {
            "IR3_Contain":  ("CONTAINED",       Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
            "IR4_Escalate": ("ESCALATED",       Encapsulation.DEEP.value),
        },
        "ESCALATED": {
            "IR4_Escalate": ("ESCALATED",       Encapsulation.SURFACE.value),
        },
    },

    "CISO": {
        "IDLE": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.MID.value),
        },
        "ALERT_RECEIVED": {
            "IR1_Detect":   ("ALERT_RECEIVED", Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
        },
        "TRIAGED": {
            "IR2_Triage":   ("TRIAGED",         Encapsulation.SURFACE.value),
            "IR3_Contain":  ("CONTAINED",       Encapsulation.MID.value),
        },
        "CONTAINED": {
            "IR3_Contain":  ("CONTAINED",       Encapsulation.SURFACE.value),
            "IR2_Triage":   ("TRIAGED",         Encapsulation.MID.value),
            "IR4_Escalate": ("ESCALATED",       Encapsulation.DEEP.value),
        },
        "ESCALATED": {
            "IR4_Escalate": ("ESCALATED",       Encapsulation.SURFACE.value),
            "IR5_Disclose": ("DISCLOSED",       Encapsulation.DEEP.value),
        },
        "DISCLOSED": {
            "IR5_Disclose": ("DISCLOSED",       Encapsulation.SURFACE.value),
        },
    },

    "Legal_Compliance": {
        "IDLE": {
            "IR4_Escalate": ("ESCALATED",       Encapsulation.MID.value),
        },
        "ESCALATED": {
            "IR4_Escalate": ("ESCALATED",       Encapsulation.SURFACE.value),
            "IR5_Disclose": ("DISCLOSED",       Encapsulation.DEEP.value),
        },
        "DISCLOSED": {
            "IR5_Disclose": ("DISCLOSED",       Encapsulation.SURFACE.value),
        },
    },
}

# State widths per role
IR_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "IR_Analyst": {
        "IDLE":           1,
        "ALERT_RECEIVED": 2,
        "TRIAGED":        2,
        "CONTAINED":      3,
        "ESCALATED":      1,
    },
    "IR_Lead": {
        "IDLE":           1,
        "ALERT_RECEIVED": 2,
        "TRIAGED":        2,
        "CONTAINED":      3,
        "ESCALATED":      1,
    },
    "CISO": {
        "IDLE":           1,
        "ALERT_RECEIVED": 2,
        "TRIAGED":        2,
        "CONTAINED":      3,
        "ESCALATED":      2,
        "DISCLOSED":      1,
    },
    "Legal_Compliance": {
        "IDLE":           1,
        "ESCALATED":      2,
        "DISCLOSED":      1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker
# ═══════════════════════════════════════════════════════════════════════

class IRTracker:
    def __init__(self):
        self._states:           Dict[str, str]        = {}
        self._visited_states:   Dict[str, Set[str]]   = {}
        self._violation_history: Dict[str, bool]      = {}
        self._width_history:    Dict[str, List]       = {}
        self._timed_widths:     Dict[str, List]       = {}
        self._role_history:     Dict[str, str]        = {}
        self._session_registry: Dict[str, str]        = {}
        self._history:          Dict[str, List]       = {}

    def _key(self, identity: str, role: str) -> str:
        return f"{identity}::{role}"

    def current_state(self, identity: str, role: str) -> str:
        return self._states.get(self._key(identity, role), "IDLE")

    def width_at_current_state(self, identity: str, role: str) -> int:
        s = self.current_state(identity, role)
        return IR_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity: str, incident_id: str) -> bool:
        if incident_id in self._session_registry:
            return self._session_registry[incident_id] != identity
        self._session_registry[incident_id] = identity
        return False

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = IR_PERMITTED_FLOWS.get(role, {})
        action_in_role  = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": IR_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": IR_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = IR_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = IR_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {"admissible": True, "from_state": from_state, "to_state": to_state,
                "encapsulation": encap, "width_before": w_before, "width_after": w_after,
                "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

    def record_width(self, identity: str, w_before: int, w_after: int, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history:
            self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths:
            self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity: str, current_time=None) -> bool:
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

    def check_hysteresis(self, identity: str, role: str, action: str) -> bool:
        if not self._violation_history.get(identity):
            return False
        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False
        role_flows  = IR_PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class CyberIRCompiler:
    def __init__(self):
        self.tracker = IRTracker()

    def compile(self, raw_event: dict) -> dict:
        actor_id    = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw  = raw_event.get("action", "")
        incident_id = raw_event.get("incident_id", "default_incident")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, incident_id)

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
                "IncidentID": incident_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events: list) -> list:
    compiler = CyberIRCompiler()
    results  = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
