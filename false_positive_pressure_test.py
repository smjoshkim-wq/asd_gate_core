"""
False Positive Pressure Test — 14-Substrate Suite
═══════════════════════════════════════════════════

Step 5 of the confirmed sequence. Tests whether the gate over-fires on clean,
legitimate, correctly-sequenced traversals across all available domain compilers.

Coverage:
  - 10 compilers run directly here (all hardware-confirmed substrates where
    compiler files are available in this environment)
  - 4 wave-2 compilers (GitHub, Financial, Clinical + original Aviation) not
    directly available here; covered by citation to their B01 hardware results

For each compiler, three clean traversals are run:
  Pass 1 — Primary actor, full forward path (B01 analog, 70s spacing)
  Pass 2 — Secondary actor, same domain (different role, if available)
  Pass 3 — Realistic timing: non-expanding sequence, tight timestamps (no 70s gap)
           This tests whether close-timed legitimate actions false-trigger BURST.
           Since BURST requires 3 width-EXPANDING transitions, a non-expanding
           sequence should never fire regardless of timing.

Expected: 0 INADMISSIBLE across all passes on all available compilers.
"""

import sys
import time
import json
sys.path.insert(0, ".")

from domain_compiler_v0_9 import evaluate_gate

# ═══════════════════════════════════════════════════════════════════════
# Import all available compilers
# ═══════════════════════════════════════════════════════════════════════

from agentic_compiler_v0_1     import AgenticCompiler
from org_workflow_compiler_v0_1 import OrgWorkflowCompiler
from aviation_compiler_v0_1    import run_session as aviation_run
from nuclear_compiler_v0_1     import run_session as nuclear_run
from fema_compiler_v0_1        import run_session as fema_run
from maritime_compiler_v0_1    import run_session as maritime_run
from legal_compiler_v0_1       import run_session as legal_run
from pharma_compiler_v0_1      import run_session as pharma_run
from construction_compiler_v0_1 import run_session as construction_run
from supply_chain_compiler_v0_1 import run_session as supply_chain_run

T = 1_000_000.0   # base timestamp
W = 70.0          # wide spacing (avoids false BURST during setup)
N = 2.0           # narrow spacing (realistic timing — tests tight-timestamp robustness)

PASS = "[PASS]"
FAIL = "[FAIL]"

results_log = []


# ═══════════════════════════════════════════════════════════════════════
# Generic runner helpers
# ═══════════════════════════════════════════════════════════════════════

def run_compile_session(compiler_instance, events):
    """For wave-1 compilers that have .compile() but no run_session()."""
    results = []
    for ev in events:
        packet = compiler_instance.compile(ev)
        result = evaluate_gate(packet)
        results.append(result)
    return results


def check_clean(label, results):
    inadmissible = [(i+1, r["decision"], r.get("invariant")) for i, r in enumerate(results)
                    if r["decision"] == "INADMISSIBLE"]
    ok = len(inadmissible) == 0
    status = PASS if ok else FAIL
    detail = f"0/{len(results)} INADMISSIBLE" if ok else \
             f"{len(inadmissible)}/{len(results)} INADMISSIBLE: {inadmissible}"
    print(f"  {status} {label}: {detail}")
    results_log.append({"label": label, "pass": ok, "steps": len(results),
                        "inadmissible": inadmissible})
    return ok


# ═══════════════════════════════════════════════════════════════════════
# 1. AI-STP (Agentic) — wave 1
# ═══════════════════════════════════════════════════════════════════════

def test_aistp():
    print("\n[AI-STP — Agentic tool-call layer]")
    compiler = AgenticCompiler()

    # Pass 1: ResearchAgent clean full sequence — wide spacing
    p1 = run_compile_session(compiler, [
        {"agent_id": "research_agent_1", "tool": "web_search",          "session_id": "s_fp1", "timestamp": T+0},
        {"agent_id": "research_agent_1", "tool": "web_search",          "session_id": "s_fp1", "timestamp": T+W},
        {"agent_id": "research_agent_1", "tool": "read_file",           "session_id": "s_fp1", "timestamp": T+W*2},
        {"agent_id": "research_agent_1", "tool": "write_summary",       "session_id": "s_fp1", "timestamp": T+W*3},
    ])
    check_clean("AISTP Pass1 ResearchAgent wide-spacing", p1)

    # Pass 2: DeliveryAgent clean sequence — different role
    p2 = run_compile_session(compiler, [
        {"agent_id": "delivery_agent_1", "tool": "create_delivery_record","session_id": "s_fp2", "timestamp": T+0},
        {"agent_id": "delivery_agent_1", "tool": "update_delivery_status","session_id": "s_fp2", "timestamp": T+W},
        {"agent_id": "delivery_agent_1", "tool": "confirm_delivery",      "session_id": "s_fp2", "timestamp": T+W*2},
    ])
    check_clean("AISTP Pass2 DeliveryAgent", p2)

    # Pass 3: Tight timing — non-expanding loops shouldn't trigger BURST
    p3 = run_compile_session(compiler, [
        {"agent_id": "research_agent_2", "tool": "web_search",   "session_id": "s_fp3", "timestamp": T+0},
        {"agent_id": "research_agent_2", "tool": "web_search",   "session_id": "s_fp3", "timestamp": T+N},
        {"agent_id": "research_agent_2", "tool": "web_search",   "session_id": "s_fp3", "timestamp": T+N*2},
        {"agent_id": "research_agent_2", "tool": "web_search",   "session_id": "s_fp3", "timestamp": T+N*3},
    ])
    check_clean("AISTP Pass3 tight-timing loop (no expansion)", p3)


# ═══════════════════════════════════════════════════════════════════════
# 2. Org Workflow — wave 1
# ═══════════════════════════════════════════════════════════════════════

def test_orgworkflow():
    print("\n[Org Workflow — human decision layer]")
    compiler = OrgWorkflowCompiler()

    p1 = run_compile_session(compiler, [
        {"actor_id": "analyst_a",  "action": "read_brief",          "workflow_id": "wf_fp1", "timestamp": T+0},
        {"actor_id": "analyst_a",  "action": "flag_for_review",     "workflow_id": "wf_fp1", "timestamp": T+W},
        {"actor_id": "analyst_a",  "action": "submit_recommendation","workflow_id": "wf_fp1", "timestamp": T+W*2},
    ])
    check_clean("OrgWorkflow Pass1 Analyst wide-spacing", p1)

    p2 = run_compile_session(compiler, [
        {"actor_id": "manager_a",  "action": "read_brief",   "workflow_id": "wf_fp2", "timestamp": T+0},
        {"actor_id": "manager_a",  "action": "approve_action","workflow_id": "wf_fp2", "timestamp": T+W},
    ])
    check_clean("OrgWorkflow Pass2 Manager", p2)

    p3 = run_compile_session(compiler, [
        {"actor_id": "analyst_b",  "action": "read_brief",      "workflow_id": "wf_fp3", "timestamp": T+0},
        {"actor_id": "analyst_b",  "action": "read_brief",      "workflow_id": "wf_fp3", "timestamp": T+N},
        {"actor_id": "analyst_b",  "action": "read_brief",      "workflow_id": "wf_fp3", "timestamp": T+N*2},
        {"actor_id": "analyst_b",  "action": "flag_for_review", "workflow_id": "wf_fp3", "timestamp": T+N*3},
    ])
    check_clean("OrgWorkflow Pass3 tight-timing (read loops)", p3)


# ═══════════════════════════════════════════════════════════════════════
# 3. Aviation — rebuilt wave 2
# ═══════════════════════════════════════════════════════════════════════

def test_aviation():
    print("\n[Aviation — crew operations]")

    p1 = aviation_run([
        {"actor_id": "captain_alpha",  "action": "monitor_atis",            "flight_id": "fp_av1", "timestamp": T+0},
        {"actor_id": "captain_alpha",  "action": "read_checklist",          "flight_id": "fp_av1", "timestamp": T+W},
        {"actor_id": "captain_alpha",  "action": "receive_ife_clearance",   "flight_id": "fp_av1", "timestamp": T+W*2},
        {"actor_id": "captain_alpha",  "action": "receive_luaw_clearance",  "flight_id": "fp_av1", "timestamp": T+W*3},
        {"actor_id": "captain_alpha",  "action": "visual_sweep_approach",   "flight_id": "fp_av1", "timestamp": T+W*4},
        {"actor_id": "captain_alpha",  "action": "receive_takeoff_clearance","flight_id": "fp_av1","timestamp": T+W*5},
        {"actor_id": "captain_alpha",  "action": "advance_throttle",        "flight_id": "fp_av1", "timestamp": T+W*6},
    ])
    check_clean("Aviation Pass1 Captain full forward path", p1)

    p2 = aviation_run([
        {"actor_id": "captain_bravo",  "action": "monitor_atis",            "flight_id": "fp_av2", "timestamp": T+0},
        {"actor_id": "captain_bravo",  "action": "receive_ife_clearance",   "flight_id": "fp_av2", "timestamp": T+W},
        {"actor_id": "captain_bravo",  "action": "receive_luaw_clearance",  "flight_id": "fp_av2", "timestamp": T+W*2},
        {"actor_id": "captain_bravo",  "action": "receive_takeoff_clearance","flight_id": "fp_av2","timestamp": T+W*3},
    ])
    check_clean("Aviation Pass2 second Captain", p2)

    # Pass 3: tight timing on non-expanding sequence
    p3 = aviation_run([
        {"actor_id": "captain_alpha",  "action": "visual_sweep_approach",   "flight_id": "fp_av3", "timestamp": T+0},
        {"actor_id": "captain_alpha",  "action": "check_instruments",       "flight_id": "fp_av3", "timestamp": T+N},
        {"actor_id": "captain_alpha",  "action": "visual_sweep_approach",   "flight_id": "fp_av3", "timestamp": T+N*2},
        {"actor_id": "captain_alpha",  "action": "check_instruments",       "flight_id": "fp_av3", "timestamp": T+N*3},
    ])
    check_clean("Aviation Pass3 tight-timing RUNWAY_HOLD loops", p3)


# ═══════════════════════════════════════════════════════════════════════
# 4. Nuclear — wave 3
# ═══════════════════════════════════════════════════════════════════════

def test_nuclear():
    print("\n[Nuclear — facility operations]")

    p1 = nuclear_run([
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc1", "timestamp": T+0},
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc1", "timestamp": T+W},
        {"actor_id": "sro_garcia",  "action": "acknowledge_alarm",          "plant_id": "fp_nuc1", "timestamp": T+W*2},
        {"actor_id": "sro_garcia",  "action": "enter_abnormal_procedure",   "plant_id": "fp_nuc1", "timestamp": T+W*3},
        {"actor_id": "sro_garcia",  "action": "notify_shift_supervisor",    "plant_id": "fp_nuc1", "timestamp": T+W*4},
    ])
    check_clean("Nuclear Pass1 SRO wide-spacing", p1)

    p2 = nuclear_run([
        {"actor_id": "ro_jones",    "action": "monitor_reactor_parameters", "plant_id": "fp_nuc2", "timestamp": T+0},
        {"actor_id": "ro_jones",    "action": "acknowledge_alarm",          "plant_id": "fp_nuc2", "timestamp": T+W},
    ])
    check_clean("Nuclear Pass2 RO", p2)

    p3 = nuclear_run([
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc3", "timestamp": T+0},
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc3", "timestamp": T+N},
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc3", "timestamp": T+N*2},
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc3", "timestamp": T+N*3},
        {"actor_id": "sro_garcia",  "action": "monitor_reactor_parameters", "plant_id": "fp_nuc3", "timestamp": T+N*4},
    ])
    check_clean("Nuclear Pass3 tight-timing monitor loops", p3)


# ═══════════════════════════════════════════════════════════════════════
# 5. FEMA ICS — wave 3
# ═══════════════════════════════════════════════════════════════════════

def test_fema():
    print("\n[FEMA ICS — emergency response]")

    p1 = fema_run([
        {"actor_id": "ic_thompson",  "action": "conduct_initial_assessment","incident_id": "fp_fema1", "timestamp": T+0},
        {"actor_id": "ic_thompson",  "action": "establish_ics_structure",   "incident_id": "fp_fema1", "timestamp": T+W},
        {"actor_id": "ic_thompson",  "action": "develop_incident_action_plan","incident_id":"fp_fema1", "timestamp": T+W*2},
        {"actor_id": "ic_thompson",  "action": "brief_operations_section",  "incident_id": "fp_fema1", "timestamp": T+W*3},
    ])
    check_clean("FEMA Pass1 IC wide-spacing", p1)

    p2 = fema_run([
        {"actor_id": "osc_williams", "action": "coordinate_field_operations","incident_id":"fp_fema2", "timestamp": T+0},
        {"actor_id": "osc_williams", "action": "deploy_resources",          "incident_id": "fp_fema2", "timestamp": T+W},
    ])
    check_clean("FEMA Pass2 OSC", p2)

    p3 = fema_run([
        {"actor_id": "ic_thompson",  "action": "conduct_initial_assessment","incident_id": "fp_fema3", "timestamp": T+0},
        {"actor_id": "ic_thompson",  "action": "conduct_initial_assessment","incident_id": "fp_fema3", "timestamp": T+N},
        {"actor_id": "ic_thompson",  "action": "conduct_initial_assessment","incident_id": "fp_fema3", "timestamp": T+N*2},
    ])
    check_clean("FEMA Pass3 tight-timing assessment loops", p3)


# ═══════════════════════════════════════════════════════════════════════
# 6. Maritime — wave 3
# ═══════════════════════════════════════════════════════════════════════

def test_maritime():
    print("\n[Maritime — vessel operations]")

    p1 = maritime_run([
        {"actor_id": "master_alpha", "action": "review_voyage_plan",     "vessel_id": "fp_mar1", "timestamp": T+0},
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",    "vessel_id": "fp_mar1", "timestamp": T+W},
        {"actor_id": "master_alpha", "action": "alter_course_starboard", "vessel_id": "fp_mar1", "timestamp": T+W*2},
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",    "vessel_id": "fp_mar1", "timestamp": T+W*3},
    ])
    check_clean("Maritime Pass1 Master wide-spacing", p1)

    p2 = maritime_run([
        {"actor_id": "oow_bravo",   "action": "plot_position_ecdis",    "vessel_id": "fp_mar2", "timestamp": T+0},
        {"actor_id": "oow_bravo",   "action": "alter_course_starboard", "vessel_id": "fp_mar2", "timestamp": T+W},
        {"actor_id": "oow_bravo",   "action": "plot_position_ecdis",    "vessel_id": "fp_mar2", "timestamp": T+W*2},
    ])
    check_clean("Maritime Pass2 OOW", p2)

    p3 = maritime_run([
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",   "vessel_id": "fp_mar3", "timestamp": T+0},
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",   "vessel_id": "fp_mar3", "timestamp": T+N},
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",   "vessel_id": "fp_mar3", "timestamp": T+N*2},
        {"actor_id": "master_alpha", "action": "plot_position_ecdis",   "vessel_id": "fp_mar3", "timestamp": T+N*3},
    ])
    check_clean("Maritime Pass3 tight-timing position loops", p3)


# ═══════════════════════════════════════════════════════════════════════
# 7. Legal — wave 4
# ═══════════════════════════════════════════════════════════════════════

def test_legal():
    print("\n[Legal — procedural]")

    p1 = legal_run([
        {"actor_id": "prosecutor_evans", "action": "file_information",       "case_id": "fp_leg1", "timestamp": T+0},
        {"actor_id": "prosecutor_evans", "action": "return_indictment",      "case_id": "fp_leg1", "timestamp": T+W},
        {"actor_id": "prosecutor_evans", "action": "file_information",       "case_id": "fp_leg1", "timestamp": T+W*2},
        {"actor_id": "prosecutor_evans", "action": "file_motion_to_dismiss", "case_id": "fp_leg1", "timestamp": T+W*3},
        {"actor_id": "prosecutor_evans", "action": "serve_subpoena_duces_tecum","case_id":"fp_leg1","timestamp": T+W*4},
    ])
    check_clean("Legal Pass1 Prosecutor wide-spacing", p1)

    p2 = legal_run([
        {"actor_id": "judge_smith",      "action": "issue_scheduling_order", "case_id": "fp_leg2", "timestamp": T+0},
        {"actor_id": "judge_smith",      "action": "rule_on_motion",         "case_id": "fp_leg2", "timestamp": T+W},
        {"actor_id": "judge_smith",      "action": "accept_plea",            "case_id": "fp_leg2", "timestamp": T+W*2},
    ])
    check_clean("Legal Pass2 Judge", p2)

    p3 = legal_run([
        {"actor_id": "defense_kim",  "action": "file_motion_to_dismiss",     "case_id": "fp_leg3", "timestamp": T+0},
        {"actor_id": "defense_kim",  "action": "file_motion_to_suppress",    "case_id": "fp_leg3", "timestamp": T+N},
        {"actor_id": "defense_kim",  "action": "file_motion_to_suppress",    "case_id": "fp_leg3", "timestamp": T+N*2},
    ])
    check_clean("Legal Pass3 Defense tight-timing (L2 loops, no expansion)", p3)


# ═══════════════════════════════════════════════════════════════════════
# 8. Pharma — wave 4
# ═══════════════════════════════════════════════════════════════════════

def test_pharma():
    print("\n[Pharma — drug approval pipeline]")

    p1 = pharma_run([
        {"actor_id": "sponsor_pfizer", "action": "execute_animal_toxicity", "program_id": "fp_ph1", "timestamp": T+0},
        {"actor_id": "sponsor_pfizer", "action": "execute_teratogenicity",  "program_id": "fp_ph1", "timestamp": T+W},
        {"actor_id": "sponsor_pfizer", "action": "submit_ind_application",  "program_id": "fp_ph1", "timestamp": T+W*2},
    ])
    check_clean("Pharma Pass1 Sponsor wide-spacing", p1)

    p2 = pharma_run([
        {"actor_id": "pi_chen",        "action": "enroll_subject",          "program_id": "fp_ph2", "timestamp": T+0},
        {"actor_id": "pi_chen",        "action": "advance_dose_cohort",     "program_id": "fp_ph2", "timestamp": T+W},
        {"actor_id": "pi_chen",        "action": "advance_dose_cohort",     "program_id": "fp_ph2", "timestamp": T+W*2},
        {"actor_id": "pi_chen",        "action": "submit_15day_safety_report","program_id":"fp_ph2","timestamp": T+W*3},
    ])
    check_clean("Pharma Pass2 PI wide-spacing", p2)

    p3 = pharma_run([
        {"actor_id": "sponsor_a",      "action": "execute_animal_toxicity", "program_id": "fp_ph3", "timestamp": T+0},
        {"actor_id": "sponsor_a",      "action": "execute_animal_toxicity", "program_id": "fp_ph3", "timestamp": T+N},
        {"actor_id": "sponsor_a",      "action": "execute_animal_toxicity", "program_id": "fp_ph3", "timestamp": T+N*2},
        {"actor_id": "sponsor_a",      "action": "execute_animal_toxicity", "program_id": "fp_ph3", "timestamp": T+N*3},
    ])
    check_clean("Pharma Pass3 tight-timing preclinical loops (no expansion)", p3)


# ═══════════════════════════════════════════════════════════════════════
# 9. Construction — wave 4
# ═══════════════════════════════════════════════════════════════════════

def test_construction():
    print("\n[Construction — approval pipeline]")

    p1 = construction_run([
        {"actor_id": "gc_a",  "action": "execute_site_preparation",  "project_id": "fp_con1", "timestamp": T+0},
        {"actor_id": "gc_a",  "action": "request_inspection",        "project_id": "fp_con1", "timestamp": T+W},
        {"actor_id": "gc_a",  "action": "pour_foundation",           "project_id": "fp_con1", "timestamp": T+W*2},
        {"actor_id": "gc_a",  "action": "request_inspection",        "project_id": "fp_con1", "timestamp": T+W*3},
        {"actor_id": "gc_a",  "action": "erect_structural_framing",  "project_id": "fp_con1", "timestamp": T+W*4},
    ])
    check_clean("Construction Pass1 GC wide-spacing", p1)

    p2 = construction_run([
        {"actor_id": "building_inspector", "action": "pass_inspection",      "project_id": "fp_con2", "timestamp": T+0},
        {"actor_id": "building_inspector", "action": "issue_correction_notice","project_id":"fp_con2", "timestamp": T+W},
    ])
    check_clean("Construction Pass2 Inspector", p2)

    p3 = construction_run([
        # GC must be at SITE_PREP or later for E1 to be valid — advance via C1 first
        {"actor_id": "gc_lambiance", "action": "execute_site_preparation",  "project_id": "fp_con3", "timestamp": T+0},
        # Now at SITE_PREP — E1 loops are valid here
        {"actor_id": "gc_lambiance", "action": "request_inspection",        "project_id": "fp_con3", "timestamp": T+N},
        {"actor_id": "gc_lambiance", "action": "request_inspection",        "project_id": "fp_con3", "timestamp": T+N*2},
        {"actor_id": "gc_lambiance", "action": "request_inspection",        "project_id": "fp_con3", "timestamp": T+N*3},
    ])
    check_clean("Construction Pass3 tight-timing E1 loops (no expansion)", p3)


# ═══════════════════════════════════════════════════════════════════════
# 10. Supply Chain — wave 4
# ═══════════════════════════════════════════════════════════════════════

def test_supply_chain():
    print("\n[Supply Chain — custody transfer]")

    p1 = supply_chain_run([
        {"actor_id": "shipper_a",      "action": "issue_purchase_order",     "shipment_id": "fp_sc1", "timestamp": T+0},
        {"actor_id": "shipper_a",      "action": "issue_commercial_invoice", "shipment_id": "fp_sc1", "timestamp": T+W},
        {"actor_id": "shipper_a",      "action": "declare_vgm",              "shipment_id": "fp_sc1", "timestamp": T+W*2},
    ])
    check_clean("SupplyChain Pass1 Shipper wide-spacing", p1)

    p2 = supply_chain_run([
        # ProcurementOfc has S1 in both ORDER_PLACED and PRODUCTION — clean forward path
        {"actor_id": "procurement_a",  "action": "issue_purchase_order",     "shipment_id": "fp_sc2", "timestamp": T+0},
        {"actor_id": "procurement_a",  "action": "confirm_supplier_capacity","shipment_id": "fp_sc2", "timestamp": T+W},
    ])
    check_clean("SupplyChain Pass2 ProcurementOfc S1 sequence", p2)

    p3 = supply_chain_run([
        # Shipper must advance to PRODUCTION via S1 first; then S1 loops in PRODUCTION (non-expanding)
        {"actor_id": "shipper_a",      "action": "issue_purchase_order",     "shipment_id": "fp_sc3", "timestamp": T+0},
        {"actor_id": "shipper_a",      "action": "confirm_supplier_capacity","shipment_id": "fp_sc3", "timestamp": T+N},
        {"actor_id": "shipper_a",      "action": "confirm_supplier_capacity","shipment_id": "fp_sc3", "timestamp": T+N*2},
        {"actor_id": "shipper_a",      "action": "confirm_supplier_capacity","shipment_id": "fp_sc3", "timestamp": T+N*3},
    ])
    check_clean("SupplyChain Pass3 tight-timing S1 loops in PRODUCTION (no expansion)", p3)


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("═"*65)
    print("FALSE POSITIVE PRESSURE TEST — 14-Substrate Suite")
    print("Step 5 of confirmed sequence")
    print("═"*65)

    test_aistp()
    test_orgworkflow()
    test_aviation()
    test_nuclear()
    test_fema()
    test_maritime()
    test_legal()
    test_pharma()
    test_construction()
    test_supply_chain()

    print()
    print("─"*65)
    print("WAVE-2 COMPILERS — B01 CITATION RECORD")
    print("(compiler files not in this environment; hardware-confirmed B01 results)")
    print("─"*65)
    wave2_citation = [
        {"substrate": "GitHub",    "b01_result": "ADMISSIBLE (4/4)", "hardware": "May 20, 2026"},
        {"substrate": "Aviation",  "b01_result": "ADMISSIBLE (4/4)", "hardware": "May 20, 2026"},
        {"substrate": "Financial", "b01_result": "ADMISSIBLE (3/3)", "hardware": "May 20, 2026"},
        {"substrate": "Clinical",  "b01_result": "ADMISSIBLE (4/4)", "hardware": "May 20, 2026"},
    ]
    for w in wave2_citation:
        print(f"  [CITE] {w['substrate']:10} B01: {w['b01_result']} — hardware {w['hardware']}")

    print()
    print("─"*65)
    print("SUMMARY")
    print("─"*65)
    total_passes   = sum(r["pass"]           for r in results_log)
    total_runs     = len(results_log)
    total_events   = sum(r["steps"]          for r in results_log)
    total_inadm    = sum(len(r["inadmissible"]) for r in results_log)
    total_fail_runs = total_runs - total_passes

    print(f"  Compilers tested directly:   10/14")
    print(f"  Wave-2 compilers (B01 cite): 4/14")
    print(f"  Clean traversals run:        {total_runs}")
    print(f"  Total events evaluated:      {total_events}")
    print(f"  INADMISSIBLE decisions:      {total_inadm}")
    print(f"  Failed traversals:           {total_fail_runs}")
    print()

    if total_inadm == 0 and total_fail_runs == 0:
        print("  ✓ ZERO FALSE POSITIVES across all clean traversals.")
        print("  ✓ Gate does not over-fire on legitimate correctly-sequenced actions.")
        print("  ✓ Tight-timing tests confirm BURST requires expanding transitions,")
        print("    not merely rapid-fire events.")
    else:
        print(f"  ✗ {total_inadm} INADMISSIBLE on clean data — INVESTIGATION REQUIRED")

    print()
    print("═"*65)
    print(f"RESULT: {'PASS' if total_inadm == 0 else 'FAIL'} — "
          f"{total_inadm} false positives across {total_events} clean events")
    print("═"*65)

    with open("/mnt/user-data/outputs/false_positive_pressure_test_results.json", "w") as f:
        json.dump({
            "test": "False Positive Pressure Test",
            "date": "2026-05-21",
            "substrates_direct": 10,
            "substrates_cited": 4,
            "traversals_run": total_runs,
            "events_evaluated": total_events,
            "inadmissible_count": total_inadm,
            "result": "PASS" if total_inadm == 0 else "FAIL",
            "traversal_detail": results_log,
            "wave2_b01_citations": wave2_citation,
        }, f, indent=2)

    return total_inadm == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
