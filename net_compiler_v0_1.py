"""
Network Layer Compiler v0.1
════════════════════════════

Substrate #24. Network protocol authority grammar derived from TCP/IP RFC
793/9293, IETF transport layer specifications, NIST SP 800-94 (Intrusion
Detection Systems), and MITRE ATT&CK network kill chain. Empirical anchor:
UNSW-NB15 dataset (Moustafa & Slay 2015) — labeled network flow records
across nine attack categories (Fuzzers, Analysis, Backdoors, DoS, Exploits,
Generic, Reconnaissance, Shellcode, Worms).

Distinct from substrate #1 (Cyber — syscall layer, ADFA-LD) and substrate
#16 (Cyber IR — human response layer). This one targets the network flow
layer: endpoint-to-endpoint protocol conformance.

Action class taxonomy (six classes):
    N1_Connect      — TCP handshake (SYN/SYN-ACK/ACK), UDP send, connection setup
    N2_Transfer     — payload data exchange, file transfer, protocol data units
    N3_Probe        — port scan, banner grab, vulnerability enumeration (recon)
    N4_Authenticate — credential exchange, TLS handshake, certificate validation
    N5_Terminate    — graceful close (FIN), reset (RST), session termination
    N6_Bypass       — malformed packets, protocol smuggling, ill-formed handshake (not in vocab)

Role registry:
    Client_Host  → N1, N2, N4, N5   (initiates connections, full client lifecycle)
    Server_Host  → N1, N2, N4, N5   (accepts; same vocab but state machine differs)
    Gateway      → N1, N2, N5        (routes; no application-layer N4)
    Monitor      → N3                (passive observer / IDS — no transfer/auth/terminate)

Key state machine (Client_Host):
    IDLE → CONNECTING → AUTHENTICATED → ESTABLISHED → CLOSING

State widths (Client_Host):
    IDLE:          1   (N1_Connect only)
    CONNECTING:    2   (N1_Connect loop + N4_Authenticate)
    AUTHENTICATED: 2   (N4_Authenticate loop + N2_Transfer)
    ESTABLISHED:   3   (N2_Transfer loop + N1_Connect (new sub-flow) + N5_Terminate)
    CLOSING:       1   (N5_Terminate)

BURST geometry (C01):
    AUTHENTICATED(w=2) → ESTABLISHED(w=3) is width-expanding.
    ESTABLISHED(w=3) → AUTHENTICATED(w=2) via N4_Authenticate (re-key, rotation).
    Three AUTHENTICATED→ESTABLISHED expansions within 60s fires BURST_CADENCE.

UNSW-NB15 mapping:
    ORDER: N2_Transfer from CONNECTING — data sent before handshake/auth complete
           (matches UNSW Exploits / Shellcode patterns where payload is delivered
           in the connection phase).
    JURISDICTION: Monitor attempts N2_Transfer — IDS / passive monitor has no
                  transmission rights in this model (matches anomaly profile of
                  a tap-line attempting to inject).
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

NET_ACTION_CLASS_MAP: Dict[str, str] = {
    # N1 — Connect
    "tcp_syn":                 "N1_Connect",
    "tcp_syn_ack":             "N1_Connect",
    "tcp_ack_handshake":       "N1_Connect",
    "udp_send":                "N1_Connect",
    "open_socket":             "N1_Connect",
    # N2 — Transfer
    "transfer_payload":        "N2_Transfer",
    "send_data":               "N2_Transfer",
    "receive_data":            "N2_Transfer",
    "http_request":            "N2_Transfer",
    "http_response":           "N2_Transfer",
    "file_transfer":           "N2_Transfer",
    # N3 — Probe
    "port_scan":               "N3_Probe",
    "banner_grab":             "N3_Probe",
    "ping_sweep":              "N3_Probe",
    "service_enumeration":     "N3_Probe",
    "vuln_scan":               "N3_Probe",
    # N4 — Authenticate
    "tls_client_hello":        "N4_Authenticate",
    "tls_server_hello":        "N4_Authenticate",
    "tls_certificate":         "N4_Authenticate",
    "tls_finished":            "N4_Authenticate",
    "credential_exchange":     "N4_Authenticate",
    "rekey":                   "N4_Authenticate",
    # N5 — Terminate
    "tcp_fin":                 "N5_Terminate",
    "tcp_rst":                 "N5_Terminate",
    "graceful_close":          "N5_Terminate",
    "session_timeout":         "N5_Terminate",
    # N6 — Bypass (not in any vocab)
    "malformed_packet":        "N6_Bypass",
    "protocol_smuggling":      "N6_Bypass",
    "ill_formed_handshake":    "N6_Bypass",
}


def resolve_action_class(action: str) -> str:
    return NET_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

NET_ROLE_TABLE: Dict[str, str] = {
    # UNSW-NB15 inspired actor IDs (synthetic — dataset uses IPs)
    "client_192_168_0_10":     "Client_Host",
    "server_unsw_apache":      "Server_Host",
    "gateway_unsw_edge":       "Gateway",
    "ids_unsw_monitor":        "Monitor",
    # Generic
    "client_alpha":            "Client_Host",
    "client_bravo":            "Client_Host",
    "server_alpha":            "Server_Host",
    "server_bravo":            "Server_Host",
    "gateway_alpha":           "Gateway",
    "gateway_bravo":           "Gateway",
    "monitor_alpha":           "Monitor",
    "monitor_bravo":           "Monitor",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Client_Host"
    return NET_ROLE_TABLE.get(actor_id, "Client_Host")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════

NET_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Client_Host": {
        "IDLE": {
            "N1_Connect":      ("CONNECTING",    Encapsulation.MID.value),
        },
        "CONNECTING": {
            "N1_Connect":      ("CONNECTING",    Encapsulation.SURFACE.value),
            "N4_Authenticate": ("AUTHENTICATED", Encapsulation.MID.value),
            # NOTE: N2_Transfer NOT in CONNECTING → ORDER (data before auth)
        },
        "AUTHENTICATED": {
            "N4_Authenticate": ("AUTHENTICATED", Encapsulation.SURFACE.value),
            "N2_Transfer":     ("ESTABLISHED",   Encapsulation.MID.value),
        },
        "ESTABLISHED": {
            "N1_Connect":      ("CONNECTING",    Encapsulation.MID.value),
            "N2_Transfer":     ("ESTABLISHED",   Encapsulation.SURFACE.value),
            "N4_Authenticate": ("AUTHENTICATED", Encapsulation.MID.value),
            "N5_Terminate":    ("CLOSING",       Encapsulation.DEEP.value),
        },
        "CLOSING": {
            "N5_Terminate":    ("CLOSING",       Encapsulation.SURFACE.value),
        },
    },

    "Server_Host": {
        "IDLE": {
            "N1_Connect":      ("LISTENING",     Encapsulation.MID.value),
        },
        "LISTENING": {
            "N1_Connect":      ("LISTENING",     Encapsulation.SURFACE.value),
            "N4_Authenticate": ("AUTHENTICATED", Encapsulation.MID.value),
        },
        "AUTHENTICATED": {
            "N4_Authenticate": ("AUTHENTICATED", Encapsulation.SURFACE.value),
            "N2_Transfer":     ("ESTABLISHED",   Encapsulation.MID.value),
        },
        "ESTABLISHED": {
            "N2_Transfer":     ("ESTABLISHED",   Encapsulation.SURFACE.value),
            "N5_Terminate":    ("CLOSING",       Encapsulation.DEEP.value),
        },
        "CLOSING": {
            "N5_Terminate":    ("CLOSING",       Encapsulation.SURFACE.value),
        },
    },

    "Gateway": {
        "IDLE": {
            "N1_Connect":      ("ROUTING",       Encapsulation.MID.value),
        },
        "ROUTING": {
            "N1_Connect":      ("ROUTING",       Encapsulation.SURFACE.value),
            "N2_Transfer":     ("ROUTING",       Encapsulation.SURFACE.value),
            "N5_Terminate":    ("ROUTING",       Encapsulation.SURFACE.value),
        },
    },

    "Monitor": {
        "IDLE": {
            "N3_Probe":        ("OBSERVING",     Encapsulation.MID.value),
        },
        "OBSERVING": {
            "N3_Probe":        ("OBSERVING",     Encapsulation.SURFACE.value),
        },
    },
}

NET_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Client_Host": {
        "IDLE":          1,
        "CONNECTING":    2,
        "AUTHENTICATED": 2,
        "ESTABLISHED":   4,
        "CLOSING":       1,
    },
    "Server_Host": {
        "IDLE":          1,
        "LISTENING":     2,
        "AUTHENTICATED": 2,
        "ESTABLISHED":   2,
        "CLOSING":       1,
    },
    "Gateway": {
        "IDLE":    1,
        "ROUTING": 3,
    },
    "Monitor": {
        "IDLE":      1,
        "OBSERVING": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Tracker (standard pattern)
# ═══════════════════════════════════════════════════════════════════════

class NetTracker:
    def __init__(self):
        self._states = {}; self._visited_states = {}
        self._violation_history = {}; self._width_history = {}
        self._timed_widths = {}; self._role_history = {}
        self._session_registry = {}; self._history = {}

    def _key(self, identity, role): return f"{identity}::{role}"
    def current_state(self, identity, role): return self._states.get(self._key(identity, role), "IDLE")
    def width_at_current_state(self, identity, role):
        s = self.current_state(identity, role)
        return NET_FLOW_WIDTHS.get(role, {}).get(s, 1)

    def check_role_confusion(self, identity, role):
        prev = self._role_history.get(identity)
        if prev is None:
            self._role_history[identity] = role
            return False
        return prev != role

    def check_actor_pivot(self, identity, flow_id):
        if flow_id in self._session_registry:
            return self._session_registry[flow_id] != identity
        self._session_registry[flow_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = NET_PERMITTED_FLOWS.get(role, {})
        action_in_role = any(action in s for s in role_flows.values())
        state_flows = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": NET_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": NET_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state
        if key not in self._visited_states:
            self._visited_states[key] = set()
        self._visited_states[key].add(to_state)
        w_before = NET_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = NET_FLOW_WIDTHS.get(role, {}).get(to_state, 1)
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
        role_flows = NET_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


# ═══════════════════════════════════════════════════════════════════════
# Compiler
# ═══════════════════════════════════════════════════════════════════════

class NetCompiler:
    def __init__(self): self.tracker = NetTracker()

    def compile(self, raw_event):
        actor_id   = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw = raw_event.get("action", "")
        flow_id    = raw_event.get("flow_id", "default_flow")
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
            actor_pivot = self.tracker.check_actor_pivot(identity_label, flow_id)

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
                "FlowID":     flow_id,
                "FromState":  tc.get("from_state"),
                "ToState":    tc.get("to_state"),
            },
            "decision": None,
            "invariant": None,
        }


def run_session(events):
    compiler = NetCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
