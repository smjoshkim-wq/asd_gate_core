"""
Supply Chain Custody Transfer Compiler v0.1
════════════════════════════════════════════

Architecture Contract
─────────────────────
Layer 1 (Gate): imported verbatim from domain_compiler_v0_9.evaluate_gate.
Layer 2 (Compiler): this module. Maps custody transfer events (actor_id,
    action, shipment_id) to the gate's BAS_Metrics vocabulary.

Domain: International supply chain custody transfer pipeline from order
placement through delivery and final settlement. Sources: SOLAS Chapter VI
(VGM), 15 CFR 30 (AES filing), 19 CFR Parts 19/141/142 (Customs entry),
21 CFR 1.276-1.285 (FDA Prior Notice), WCO RKC Chapter 3, WTO TFA Article 7,
ICC UCP 600 (Letter of Credit), ICC Incoterms 2020.

Action class taxonomy (eight classes):
    S1 Origination Actions    — PO issuance, supplier confirmation, license
    S2 Documentation Actions  — Commercial Invoice, AES, VGM, Cert of Origin
    S3 Financial Instrument   — LC issuance, presentation, draw (banks only)
    S4 Logistics Coordination — booking, container loading authorization
    S5 Border Clearance       — customs entry, FDA Prior Notice, bond, release
    S6 In-Transit             — carrier custody, transshipment, in-bond
    S7 Delivery & Acceptance  — delivery order, gate-out, warehouse receipt
    S8 Post-Delivery          — final payment, claims, post-clearance audit

Role registry:
    Shipper          → S1, S2 (excluded from border release, sanctions bypass)
    QCInspector      → S2 (internal commercial certificates only)
    ThirdPartyAuditor→ S2 (independent LC compliance certificates)
    FreightForwarder → S4, S6 (excluded from customs entry, LC draws)
    CustomsBroker    → S5 (excluded from physical release, importer of record)
    Carrier          → S4, S6 (excluded from VGM-less loading, customs bypass)
    TerminalOperator → S7 (excluded from release without dual auth)
    WarehouseOp      → S7 (bonded cargo requires license)
    CustomsAuthority → S5 (excluded from commercial ownership transfer)
    ImportInspector  → S5 (FDA/CFIA quarantine override authority)
    TradeAuthority   → S1 (export license approval/denial)
    Consignee        → S1, S7, S8 (excluded from self-certifying entry)
    ProcurementOfc   → S1 (commercial; cannot override regulatory holds)
    FinancialInst    → S3 (banks; excluded from physical good inspection)
    InsuranceUnderwr → S8 (cannot halt physical cargo movement)

Key incident anchors:
  - PPE Procurement 2020: BURST_CADENCE — uncoordinated parallel S1 ordering
    through multiple channels without centralized deduplication.
  - Suez Canal 2021 (Ever Given): ORDER — S7 delivery release attempted from
    IN_TRANSIT before S5 customs clearance. Phase-skipping violation.
  - Hanjin Shipping 2016: JURISDICTION — multiple actors (receivers, terminal
    operators, bankruptcy courts, admiralty marshals) simultaneously asserting
    S7 cargo release authority without clear jurisdictional assignment.
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

SUPPLY_CHAIN_ACTION_CLASS_MAP: Dict[str, str] = {
    # S1 — Origination
    "issue_purchase_order":           "S1_Origination",
    "confirm_supplier_capacity":      "S1_Origination",
    "apply_export_license":           "S1_Origination",
    "issue_proforma_invoice":         "S1_Origination",
    # S2 — Documentation
    "issue_commercial_invoice":       "S2_Documentation",
    "generate_packing_list":          "S2_Documentation",
    "issue_certificate_origin":       "S2_Documentation",
    "issue_phytosanitary_cert":       "S2_Documentation",
    "declare_vgm":                    "S2_Documentation",
    "file_aes_declaration":           "S2_Documentation",
    "submit_dangerous_goods_decl":    "S2_Documentation",
    # S3 — Financial Instrument
    "issue_letter_of_credit":         "S3_Financial",
    "present_lc_documents":           "S3_Financial",
    "verify_lc_compliance":           "S3_Financial",
    "authorize_lc_payment":           "S3_Financial",
    # S4 — Logistics Coordination
    "issue_booking_confirmation":     "S4_Logistics",
    "authorize_container_loading":    "S4_Logistics",
    "transmit_freight_instructions":  "S4_Logistics",
    "dispatch_empty_equipment":       "S4_Logistics",
    # S5 — Border Clearance
    "file_customs_entry":             "S5_BorderClearance",
    "submit_fda_prior_notice":        "S5_BorderClearance",
    "assess_estimated_duties":        "S5_BorderClearance",
    "post_continuous_bond":           "S5_BorderClearance",
    "issue_customs_release":          "S5_BorderClearance",
    "issue_pga_hold":                 "S5_BorderClearance",
    "lift_pga_hold":                  "S5_BorderClearance",
    # S6 — In-Transit
    "accept_carrier_custody":         "S6_InTransit",
    "authorize_transshipment":        "S6_InTransit",
    "execute_in_bond_movement":       "S6_InTransit",
    "issue_arrival_notice":           "S6_InTransit",
    # S7 — Delivery & Acceptance
    "issue_delivery_order":           "S7_Delivery",
    "execute_gate_out":               "S7_Delivery",
    "issue_warehouse_receipt":        "S7_Delivery",
    "perform_quality_inspection":     "S7_Delivery",
    "accept_goods":                   "S7_Delivery",
    "reject_goods":                   "S7_Delivery",
    # S8 — Post-Delivery
    "complete_final_payment":         "S8_PostDelivery",
    "file_insurance_claim":           "S8_PostDelivery",
    "respond_post_clearance_audit":   "S8_PostDelivery",
    "liquidate_customs_entry":        "S8_PostDelivery",
}


def resolve_action_class(action: str) -> str:
    return SUPPLY_CHAIN_ACTION_CLASS_MAP.get(action, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════
# Role registry
# ═══════════════════════════════════════════════════════════════════════

SUPPLY_CHAIN_ROLE_TABLE: Dict[str, str] = {
    "shipper_evergreen":       "Shipper",       # Ever Given Suez anchor
    "shipper_a":               "Shipper",
    "qc_inspector":            "QCInspector",
    "third_party_auditor":     "ThirdPartyAuditor",
    "forwarder_a":             "FreightForwarder",
    "broker_a":                "CustomsBroker",
    "carrier_hanjin":          "Carrier",       # Hanjin collapse anchor
    "carrier_a":               "Carrier",
    "terminal_op":             "TerminalOperator",
    "warehouse_op":            "WarehouseOp",
    "cbp":                     "CustomsAuthority",  # US CBP
    "cbsa":                    "CustomsAuthority",  # Canada CBSA
    "fda_import":              "ImportInspector",
    "cfia_import":             "ImportInspector",
    "trade_authority":         "TradeAuthority",
    "consignee_a":             "Consignee",
    "consignee_b":             "Consignee",
    "procurement_ppe_state_a": "ProcurementOfc",   # PPE 2020 burst anchor
    "procurement_ppe_state_b": "ProcurementOfc",
    "procurement_a":           "ProcurementOfc",
    "issuing_bank":            "FinancialInst",
    "confirming_bank":         "FinancialInst",
    "insurance_underwriter":   "InsuranceUnderwr",
}

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"


def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Shipper"
    return SUPPLY_CHAIN_ROLE_TABLE.get(actor_id, "Shipper")


# ═══════════════════════════════════════════════════════════════════════
# Permitted flow graph
# ═══════════════════════════════════════════════════════════════════════
# States: ORDER_PLACED → PRODUCTION → EXPORT_DOCS_PREPARED → EXPORT_CLEARED →
#         LOADED_FOR_TRANSIT → IN_TRANSIT → PORT_OF_ARRIVAL →
#         CUSTOMS_EXAMINATION → CUSTOMS_CLEARED → DUTY_PAID →
#         RELEASED_TO_IMPORTER → WAREHOUSE_RECEIPT → QUALITY_INSPECTION →
#         DELIVERED → PAYMENT_COMPLETE (terminal)

SUPPLY_CHAIN_PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    "Shipper": {
        "ORDER_PLACED": {
            "S1_Origination": ("PRODUCTION", Encapsulation.MID.value),
        },
        "PRODUCTION": {
            "S1_Origination":   ("PRODUCTION", Encapsulation.SURFACE.value),
            "S2_Documentation": ("EXPORT_DOCS_PREPARED", Encapsulation.MID.value),
        },
        "EXPORT_DOCS_PREPARED": {
            "S2_Documentation": ("EXPORT_CLEARED", Encapsulation.MID.value),
        },
        "EXPORT_CLEARED": {
            "S2_Documentation": ("EXPORT_CLEARED", Encapsulation.SURFACE.value),
        },
    },

    "QCInspector": {
        "PRODUCTION": {
            "S2_Documentation": ("PRODUCTION", Encapsulation.SURFACE.value),
        },
    },

    "ThirdPartyAuditor": {
        "PRODUCTION": {
            "S2_Documentation": ("PRODUCTION", Encapsulation.SURFACE.value),
        },
    },

    "FreightForwarder": {
        "EXPORT_DOCS_PREPARED": {
            "S4_Logistics": ("EXPORT_CLEARED", Encapsulation.MID.value),
        },
        "EXPORT_CLEARED": {
            "S4_Logistics": ("LOADED_FOR_TRANSIT", Encapsulation.MID.value),
        },
        "LOADED_FOR_TRANSIT": {
            "S6_InTransit": ("IN_TRANSIT", Encapsulation.MID.value),
        },
        "IN_TRANSIT": {
            "S6_InTransit": ("PORT_OF_ARRIVAL", Encapsulation.MID.value),
        },
    },

    "CustomsBroker": {
        "PORT_OF_ARRIVAL": {
            "S5_BorderClearance": ("CUSTOMS_EXAMINATION", Encapsulation.MID.value),
        },
        "CUSTOMS_EXAMINATION": {
            "S5_BorderClearance": ("CUSTOMS_CLEARED", Encapsulation.MID.value),
        },
        "CUSTOMS_CLEARED": {
            "S5_BorderClearance": ("DUTY_PAID", Encapsulation.MID.value),
        },
    },

    "Carrier": {
        "EXPORT_CLEARED": {
            "S4_Logistics": ("LOADED_FOR_TRANSIT", Encapsulation.MID.value),
        },
        "LOADED_FOR_TRANSIT": {
            "S6_InTransit": ("IN_TRANSIT", Encapsulation.MID.value),
        },
        "IN_TRANSIT": {
            "S6_InTransit": ("PORT_OF_ARRIVAL", Encapsulation.MID.value),
        },
    },

    "TerminalOperator": {
        "DUTY_PAID": {
            "S7_Delivery": ("RELEASED_TO_IMPORTER", Encapsulation.MID.value),
        },
        "RELEASED_TO_IMPORTER": {
            "S7_Delivery": ("WAREHOUSE_RECEIPT", Encapsulation.MID.value),
        },
    },

    "WarehouseOp": {
        "WAREHOUSE_RECEIPT": {
            "S7_Delivery": ("QUALITY_INSPECTION", Encapsulation.MID.value),
        },
    },

    "CustomsAuthority": {
        "PORT_OF_ARRIVAL": {
            "S5_BorderClearance": ("CUSTOMS_EXAMINATION", Encapsulation.MID.value),
        },
        "CUSTOMS_EXAMINATION": {
            "S5_BorderClearance": ("CUSTOMS_CLEARED", Encapsulation.MID.value),
        },
        "CUSTOMS_CLEARED": {
            "S5_BorderClearance": ("CUSTOMS_CLEARED", Encapsulation.SURFACE.value),
        },
    },

    "ImportInspector": {
        "PORT_OF_ARRIVAL": {
            "S5_BorderClearance": ("PORT_OF_ARRIVAL", Encapsulation.DEEP.value),
        },
        "CUSTOMS_EXAMINATION": {
            "S5_BorderClearance": ("CUSTOMS_EXAMINATION", Encapsulation.DEEP.value),
        },
    },

    "TradeAuthority": {
        "ORDER_PLACED": {
            "S1_Origination": ("ORDER_PLACED", Encapsulation.MID.value),
        },
    },

    "Consignee": {
        "ORDER_PLACED": {
            "S1_Origination": ("PRODUCTION", Encapsulation.MID.value),
        },
        "QUALITY_INSPECTION": {
            "S7_Delivery": ("DELIVERED", Encapsulation.MID.value),
        },
        "DELIVERED": {
            "S8_PostDelivery": ("PAYMENT_COMPLETE", Encapsulation.MID.value),
        },
    },

    "ProcurementOfc": {
        "ORDER_PLACED": {
            "S1_Origination": ("PRODUCTION", Encapsulation.MID.value),
        },
        "PRODUCTION": {
            "S1_Origination": ("PRODUCTION", Encapsulation.SURFACE.value),
        },
        # PPE 2020 BURST anchor: rapid S1 ordering through multiple channels
        # without centralized deduplication.
    },

    "FinancialInst": {
        "PRODUCTION": {
            "S3_Financial": ("PRODUCTION", Encapsulation.MID.value),
        },
        "EXPORT_DOCS_PREPARED": {
            "S3_Financial": ("EXPORT_DOCS_PREPARED", Encapsulation.MID.value),
        },
        "DELIVERED": {
            "S3_Financial": ("DELIVERED", Encapsulation.MID.value),
        },
    },

    "InsuranceUnderwr": {
        "DELIVERED": {
            "S8_PostDelivery": ("PAYMENT_COMPLETE", Encapsulation.MID.value),
        },
    },
}

SUPPLY_CHAIN_FLOW_START_STATE: Dict[str, str] = {
    "Shipper":           "ORDER_PLACED",
    "QCInspector":       "PRODUCTION",
    "ThirdPartyAuditor": "PRODUCTION",
    "FreightForwarder":  "EXPORT_DOCS_PREPARED",
    "CustomsBroker":     "PORT_OF_ARRIVAL",
    "Carrier":           "EXPORT_CLEARED",
    "TerminalOperator":  "DUTY_PAID",
    "WarehouseOp":       "WAREHOUSE_RECEIPT",
    "CustomsAuthority":  "PORT_OF_ARRIVAL",
    "ImportInspector":   "PORT_OF_ARRIVAL",
    "TradeAuthority":    "ORDER_PLACED",
    "Consignee":         "ORDER_PLACED",
    "ProcurementOfc":    "ORDER_PLACED",
    "FinancialInst":     "PRODUCTION",
    "InsuranceUnderwr":  "DELIVERED",
}

# Strict monotonic widths for ProcurementOfc to enable PPE 2020 BURST anchor
SUPPLY_CHAIN_FLOW_WIDTHS: Dict[str, Dict[str, int]] = {
    "Shipper": {
        "ORDER_PLACED":          1,
        "PRODUCTION":            2,   # +1 expansion from ORDER_PLACED
        "EXPORT_DOCS_PREPARED":  3,   # +1 expansion from PRODUCTION
        "EXPORT_CLEARED":        4,   # +1 expansion from EXPORT_DOCS_PREPARED — 3 expansions = BURST
    },
    "QCInspector":       {"PRODUCTION": 1},
    "ThirdPartyAuditor": {"PRODUCTION": 1},
    "FreightForwarder": {
        "EXPORT_DOCS_PREPARED": 1,
        "EXPORT_CLEARED":       1,
        "LOADED_FOR_TRANSIT":   1,
        "IN_TRANSIT":           1,
    },
    "CustomsBroker": {
        "PORT_OF_ARRIVAL":      1,
        "CUSTOMS_EXAMINATION":  1,
        "CUSTOMS_CLEARED":      1,
    },
    "Carrier": {
        "EXPORT_CLEARED":       1,
        "LOADED_FOR_TRANSIT":   1,
        "IN_TRANSIT":           1,
    },
    "TerminalOperator":  {"DUTY_PAID": 1, "RELEASED_TO_IMPORTER": 1},
    "WarehouseOp":       {"WAREHOUSE_RECEIPT": 1},
    "CustomsAuthority": {
        "PORT_OF_ARRIVAL":      1,
        "CUSTOMS_EXAMINATION":  1,
        "CUSTOMS_CLEARED":      1,
    },
    "ImportInspector":   {"PORT_OF_ARRIVAL": 1, "CUSTOMS_EXAMINATION": 1},
    "TradeAuthority":    {"ORDER_PLACED": 1},
    "Consignee": {
        "ORDER_PLACED":      1,
        "QUALITY_INSPECTION":1,
        "DELIVERED":         1,
    },
    "ProcurementOfc": {
        # Strict monotonic for BURST: PPE 2020 — rapid uncoordinated ordering
        "ORDER_PLACED": 1,
        "PRODUCTION":   2,
        # Note: ProcurementOfc has limited forward path; BURST captured via
        # repeated S1 fires within window from procurement officers.
    },
    "FinancialInst":     {"PRODUCTION": 1, "EXPORT_DOCS_PREPARED": 1, "DELIVERED": 1},
    "InsuranceUnderwr":  {"DELIVERED": 1},
}


# ═══════════════════════════════════════════════════════════════════════
# SupplyChainTracker
# ═══════════════════════════════════════════════════════════════════════

class SupplyChainTracker:

    def __init__(self) -> None:
        self._states:            Dict[Tuple[str, str], str]               = {}
        self._history:           Dict[Tuple[str, str], List[Tuple]]       = {}
        self._role_registry:     Dict[str, str]                           = {}
        self._session_registry:  Dict[str, str]                           = {}
        self._width_history:     Dict[str, List[Tuple[int, int]]]         = {}
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]]  = {}
        self._violation_history: Dict[str, bool]                          = {}
        self._visited_states:    Dict[Tuple[str, str], Set[str]]          = {}

    def _key(self, identity, role): return (identity, role)

    def current_state(self, identity, role):
        return self._states.get(self._key(identity, role),
                                SUPPLY_CHAIN_FLOW_START_STATE.get(role, "ORDER_PLACED"))

    def width_at_current_state(self, identity, role):
        state = self.current_state(identity, role)
        return SUPPLY_CHAIN_FLOW_WIDTHS.get(role, {}).get(state, 1)

    def check_role_confusion(self, identity, role):
        if identity in self._role_registry:
            return self._role_registry[identity] != role
        self._role_registry[identity] = role
        return False

    def check_actor_pivot(self, identity, shipment_id):
        if shipment_id in self._session_registry:
            return self._session_registry[shipment_id] != identity
        self._session_registry[shipment_id] = identity
        return False

    def evaluate(self, identity, role, action):
        key        = self._key(identity, role)
        from_state = self.current_state(identity, role)
        role_flows = SUPPLY_CHAIN_PERMITTED_FLOWS.get(role, {})

        action_in_role = any(action in s for s in role_flows.values())
        state_flows     = role_flows.get(from_state, {})
        action_in_state = action in state_flows

        if not action_in_role:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": SUPPLY_CHAIN_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": False, "jurisdiction_violation": True,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        if not action_in_state:
            self._violation_history[identity] = True
            return {"admissible": False, "from_state": from_state, "to_state": None,
                    "encapsulation": Encapsulation.DEEP.value,
                    "width_before": SUPPLY_CHAIN_FLOW_WIDTHS.get(role, {}).get(from_state, 1),
                    "width_after": None, "exposure_event": True,
                    "order_violation": True, "jurisdiction_violation": False,
                    "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

        to_state, encap = state_flows[action]
        self._states[key] = to_state

        if key not in self._visited_states: self._visited_states[key] = set()
        self._visited_states[key].add(to_state)

        w_before = SUPPLY_CHAIN_FLOW_WIDTHS.get(role, {}).get(from_state, 1)
        w_after  = SUPPLY_CHAIN_FLOW_WIDTHS.get(role, {}).get(to_state, 1)

        if key not in self._history: self._history[key] = []
        self._history[key].append((from_state, action, to_state))

        return {"admissible": True, "from_state": from_state, "to_state": to_state,
                "encapsulation": encap, "width_before": w_before, "width_after": w_after,
                "exposure_event": False, "order_violation": False, "jurisdiction_violation": False,
                "role_confusion": False, "actor_pivot": False, "hysteresis_violation": False}

    def record_width(self, identity, w_before, w_after, timestamp=None):
        ts = timestamp if timestamp is not None else time.time()
        if identity not in self._width_history: self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        if identity not in self._timed_widths: self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity, current_time=None):
        timed = self._timed_widths.get(identity, [])
        if timed:
            now = current_time if current_time is not None else time.time()
            cutoff = now - BURST_TIME_WINDOW_SECONDS
            window = [(wb, wa) for ts, wb, wa in timed if ts >= cutoff]
            if not window: return False
            expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
            return expansions >= BURST_THRESHOLD
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW: return False
        expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
        return expansions >= BURST_THRESHOLD

    def check_hysteresis(self, identity, role, action):
        if not self._violation_history.get(identity): return False
        key = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited: return False
        role_flows = SUPPLY_CHAIN_PERMITTED_FLOWS.get(role, {})
        from_state = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows: return False
        to_state, _ = state_flows[action]
        return to_state not in visited


class SupplyChainCompiler:
    def __init__(self): self.tracker = SupplyChainTracker()

    def compile(self, raw_event):
        actor_id    = raw_event.get("actor_id") or EMPTY_IDENTITY
        action_raw  = raw_event.get("action", "")
        shipment_id = raw_event.get("shipment_id", "default_shipment")
        event_ts    = raw_event.get("timestamp")

        identity_label = actor_id
        role           = resolve_role(actor_id)
        action         = resolve_action_class(action_raw)

        resolution = ResolutionStatus.FULL.value
        if action == "UNKNOWN": resolution = ResolutionStatus.PARTIAL.value

        is_known       = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = False
        actor_pivot    = False

        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(identity_label, shipment_id)

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
            "Admissible": tc.get("admissible", False),
            "ExposureEvent": tc.get("exposure_event", False),
            "OrderViolation": tc.get("order_violation", False),
            "JurisdictionViolation": tc.get("jurisdiction_violation", False),
            "RoleConfusion": tc.get("role_confusion", False),
            "ActorPivot": tc.get("actor_pivot", False),
            "HysteresisViolation": tc.get("hysteresis_violation", False),
            "BurstCadence": burst_cadence,
        }
        stp_header = {"Resolution": {"Completeness": resolution},
                      "Identity": identity_label, "Role": role, "Action": action,
                      "RawAction": action_raw, "ShipmentID": shipment_id,
                      "FromState": tc.get("from_state"), "ToState": tc.get("to_state")}
        return {"BAS_Metrics": bas_metrics, "STP_Header": stp_header}


def run_session(events):
    compiler = SupplyChainCompiler()
    results = []
    for ev in events:
        packet = compiler.compile(ev)
        result = evaluate_gate(packet)
        result["_stp"] = packet["STP_Header"]
        results.append(result)
    return results
