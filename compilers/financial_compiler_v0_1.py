"""
Financial Structured Product Authorization Compiler v0.1
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

FINANCIAL_ACTION_CLASS_MAP: Dict[str, str] = {
    "asset_level_verification":     "F1_Read",
    "model_validation_audit":       "F1_Read",
    "due_diligence_review":         "F1_Read",
    "underwriting_file_inspection": "F1_Read",
    "backtesting_analysis":         "F1_Read",
    "mark_to_market_review":        "F1_Read",
    "regulatory_disclosure_check":  "F1_Read",
    "waiver_log_inspection":        "F1_Read",
    "compliance_screening":         "F1_Read",
    "originate_mortgage_loan":      "F2_Expand",
    "pool_asset_aggregation":       "F2_Expand",
    "establish_spv_trust":          "F2_Expand",
    "fund_warehouse_line":          "F2_Expand",
    "cdo_squared_resecuritization": "F2_Expand",
    "add_synthetic_reference":      "F2_Expand",
    "aggregate_mezzanine_tranche":  "F2_Expand",
    "enforce_margin_call":          "F3_Contract",
    "portfolio_deleveraging":       "F3_Contract",
    "halt_origination_pipeline":    "F3_Contract",
    "issue_cease_desist":           "F3_Contract",
    "adjust_capital_reserve":       "F3_Contract",
    "unwind_synthetic_holding":     "F3_Contract",
    "approve_regulatory_filing":    "F3_Contract",
    "waterfall_logic_structuring":  "F4_Pivot",
    "tranche_sizing":               "F4_Pivot",
    "issue_credit_rating":          "F4_Pivot",
    "apply_underwriting_waiver":    "F4_Pivot",
    "execute_credit_default_swap":  "F4_Pivot",
    "advance_to_securitization":    "F4_Pivot",
    "submit_reg_ab_filing":         "F4_Pivot",
    "lock_spv_trust_assets":        "F4_Pivot",
    "execute_distribution":         "F4_Pivot",
    "self_rating_conflict":         "F5_Prohibited",
    "bypass_all_clearance_gates":   "F5_Prohibited",
    "costructure_and_rate":         "F5_Prohibited",
    "unilateral_trust_dissolution": "F5_Prohibited",
}

def resolve_action_class(action: str) -> str:
    return FINANCIAL_ACTION_CLASS_MAP.get(action, "UNKNOWN")

FINANCIAL_ROLE_TABLE: Dict[str, str] = {
    "originator_countrywide": "Originator",
    "originator_ameriquest":  "Originator",
    "originator_alpha":       "Originator",
    "originator_beta":        "Originator",
    "uw_citi_desk":           "Structuring_Underwriter",
    "uw_ubs_desk":            "Structuring_Underwriter",
    "uw_morgan_stanley":      "Structuring_Underwriter",
    "uw_alpha":               "Structuring_Underwriter",
    "uw_beta":                "Structuring_Underwriter",
    "cra_sp_analyst":         "CRA",
    "cra_moodys_analyst":     "CRA",
    "cra_fitch_analyst":      "CRA",
    "cra_alpha":              "CRA",
    "cro_alpha":              "Risk_Officer",
    "cro_beta":               "Risk_Officer",
    "risk_officer_bowen":     "Risk_Officer",
    "sec_examiner_1":         "Regulator",
    "occ_examiner_1":         "Regulator",
    "fed_examiner_1":         "Regulator",
    "regulator_alpha":        "Regulator",
}

def resolve_role(actor_id: str) -> str:
    if not actor_id:
        return "Originator"
    return FINANCIAL_ROLE_TABLE.get(actor_id, "Originator")

FINANCIAL_ROLE_VOCABULARY: Dict[str, Set[str]] = {
    "Originator":             {"F1_Read", "F2_Expand"},
    "Structuring_Underwriter":{"F1_Read", "F2_Expand", "F4_Pivot"},
    "CRA":                    {"F1_Read", "F4_Pivot"},
    "Risk_Officer":           {"F1_Read", "F3_Contract"},
    "Regulator":              {"F1_Read", "F3_Contract"},
}

FINANCIAL_PERMITTED_FLOWS: Dict[str, Dict] = {
    "Originator": {
        "IDLE":       {"flows": {"F1_Read": "ORIGINATING"}, "width": 1},
        "ORIGINATING":{"flows": {"F1_Read": "ORIGINATING", "F2_Expand": "WAREHOUSING"}, "width": 2},
        "WAREHOUSING":{"flows": {"F1_Read": "WAREHOUSING"}, "width": 1},
    },
    "Structuring_Underwriter": {
        "IDLE":          {"flows": {"F1_Read": "AUDIT_PENDING"}, "width": 1},
        "AUDIT_PENDING": {"flows": {"F1_Read": "POOL_ACTIVE"}, "width": 1},
        "POOL_ACTIVE":   {"flows": {"F2_Expand": "POOL_ACTIVE", "F4_Pivot": "SECURITIZING"}, "width": 2},
        "SECURITIZING":  {"flows": {"F1_Read": "SECURITIZING", "F4_Pivot": "DISTRIBUTING", "F2_Expand": "POOL_ACTIVE"}, "width": 3},
        "DISTRIBUTING":  {"flows": {}, "width": 0},
    },
    "CRA": {
        "IDLE":      {"flows": {"F1_Read": "REVIEWING"}, "width": 1},
        "REVIEWING": {"flows": {"F1_Read": "REVIEWING", "F4_Pivot": "RATED"}, "width": 2},
        "RATED":     {"flows": {}, "width": 0},
    },
    "Risk_Officer": {
        "IDLE":       {"flows": {"F1_Read": "VALIDATING"}, "width": 1},
        "VALIDATING": {"flows": {"F1_Read": "VALIDATING", "F3_Contract": "CLEARED"}, "width": 2},
        "CLEARED":    {"flows": {}, "width": 0},
    },
    "Regulator": {
        "IDLE":              {"flows": {"F1_Read": "REVIEWING_FILING"}, "width": 1},
        "REVIEWING_FILING":  {"flows": {"F1_Read": "REVIEWING_FILING", "F3_Contract": "APPROVED"}, "width": 2},
        "APPROVED":          {"flows": {}, "width": 0},
    },
}


class FinancialTracker:
    def __init__(self) -> None:
        self._states:             Dict[Tuple[str,str], str]                        = {}
        self._timed_widths:       Dict[Tuple[str,str], List[Tuple[float,int,int]]] = {}
        self._session_actor_binding: Dict[str, str]    = {}  # session_id -> first actor
        self._visited_states:     Dict[Tuple[str,str], Set[str]]                   = {}
        self._violation_history:  Dict[str, bool]                                  = {}

    def current_state(self, actor: str, deal_id: str) -> str:
        return self._states.get((actor, deal_id), "IDLE")

    def advance_state(self, actor: str, deal_id: str, next_state: str, role: str, ts: float) -> None:
        key  = (actor, deal_id)
        prev = self._states.get(key, "IDLE")
        fg   = FINANCIAL_PERMITTED_FLOWS.get(role, {})
        pw   = fg.get(prev,       {}).get("width", 0)
        nw   = fg.get(next_state, {}).get("width", 0)
        self._states[key] = next_state
        self._timed_widths.setdefault(key, []).append((ts, pw, nw))
        self._visited_states.setdefault((actor, role), set()).add(next_state)

    def check_order(self, actor: str, deal_id: str, role: str, action_class: str) -> Tuple[bool, Optional[str]]:
        state = self.current_state(actor, deal_id)
        flows = FINANCIAL_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        vocab = FINANCIAL_ROLE_VOCABULARY.get(role, set())
        if action_class not in vocab:
            return False, None
        if action_class in flows:
            return False, flows[action_class]
        return True, None

    def check_jurisdiction(self, role: str, action_class: str) -> bool:
        return action_class not in FINANCIAL_ROLE_VOCABULARY.get(role, set())

    def check_burst_cadence(self, actor: str, deal_id: str, ts: float) -> bool:
        key    = (actor, deal_id)
        cutoff = ts - BURST_TIME_WINDOW_SECONDS
        recent = [(t,wb,wa) for t,wb,wa in self._timed_widths.get(key, []) if t >= cutoff]
        return sum(1 for _,wb,wa in recent if wa > wb) >= BURST_THRESHOLD

    def check_exit(self, actor: str, deal_id: str) -> bool:
        prior = self._session_actor_binding.get(deal_id)
        return prior is not None and prior != actor

    def bind_actor(self, actor: str, deal_id: str) -> None:
        if deal_id not in self._session_actor_binding:
            self._session_actor_binding[deal_id] = actor

    def check_hysteresis(self, actor: str, role: str, action_class: str, deal_id: str) -> bool:
        if not self._violation_history.get(actor, False):
            return False
        visited = self._visited_states.get((actor, role), set())
        if not visited:
            return False
        state = self.current_state(actor, deal_id)
        flows = FINANCIAL_PERMITTED_FLOWS.get(role, {}).get(state, {}).get("flows", {})
        nxt   = flows.get(action_class)
        return nxt is not None and nxt not in visited

    def record_violation(self, actor: str) -> None:
        self._violation_history[actor] = True


class FinancialCompiler:
    def __init__(self) -> None:
        self.tracker = FinancialTracker()

    def compile(self, raw_event: dict) -> dict:
        actor        = raw_event.get("actor_id", "")
        action       = raw_event.get("action", "")
        deal_id      = raw_event.get("deal_id", "deal_unknown")
        ts           = raw_event.get("timestamp", time.time())
        role         = resolve_role(actor)
        action_class = resolve_action_class(action)

        self.tracker.bind_actor(actor, deal_id)

        actor_pivot  = self.tracker.check_exit(actor, deal_id)
        jurisdiction = (not actor_pivot) and self.tracker.check_jurisdiction(role, action_class)
        hysteresis   = (not actor_pivot and not jurisdiction) and \
                       self.tracker.check_hysteresis(actor, role, action_class, deal_id)
        order_violation, next_state = False, None
        if not actor_pivot and not jurisdiction and not hysteresis:
            order_violation, next_state = self.tracker.check_order(actor, deal_id, role, action_class)

        admissible = not (actor_pivot or jurisdiction or order_violation or hysteresis)

        burst_cadence = False
        if admissible and next_state:
            self.tracker.advance_state(actor, deal_id, next_state, role, ts)
            burst_cadence = self.tracker.check_burst_cadence(actor, deal_id, ts)

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
            "SessionRef": deal_id,
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
    compiler = FinancialCompiler()
    return [compiler.compile(e) for e in events]
