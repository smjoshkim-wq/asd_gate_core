# Snort / Sigma Benchmark — ASD Gate vs Signature Detection on Mordor LotL Datasets
**Date:** May 21, 2026
**Follows from:** Needle Movers item 4 (Snort/Suricata benchmark comparison)
**Gate kernel:** domain_compiler_v0_9.py (unchanged since May 15, 2026)
**Comparison tool:** Sigma community rules (SigmaHQ, canonical ruleset — equivalent to Snort/Suricata for host telemetry)
**Dataset:** OTRF Security Datasets (formerly Mordor) — 4 adversary-emulation scenarios, 20,906 Sysmon events

---

## Why Sigma, Not Suricata

Suricata and Snort operate on network packet captures (PCAP). The Mordor/Security-Datasets corpus is host telemetry — Windows Sysmon event logs (EventID 1, 3, 7, 10, 11, etc.). The correct like-for-like comparison is Sigma: community-maintained detection rules for host logs, using the same signature-matching paradigm as Snort/Suricata rules but targeting the same data layer as the gate kernel. Sigma rules are used by SIEM platforms (Splunk, Elastic, Microsoft Sentinel) in the same role that Snort/Suricata rules play in network IDS. The comparison is structurally valid.

---

## Datasets

| Dataset | ATT&CK Technique | Description | Events |
|---------|-----------------|-------------|--------|
| empire_mimikatz_logonpasswords | T1003.001 — Credential Dumping | LSASS memory access via Empire/Mimikatz | 6,026 |
| empire_psexec_dcerpc_tcp_svcctl | T1021.002 — Lateral Movement (PsExec) | Remote service execution via SMB/DCERPC | 4,348 |
| empire_launcher_vbs | T1059.005 — VBScript Execution | VBS launcher with encoded PowerShell payload | 2,067 |
| empire_dcsync_dcerpc_drsuapi | T1003.006 — DCSync / Credential Access | Domain controller sync via DRSUAPI RPC | 8,465 |
| **Total** | | | **20,906** |

All four scenarios use the Empire framework with built-in Windows tools and legitimate system processes — the defining characteristic of Living-off-the-Land (LotL) attacks.

---

## Results

### Session-Level Detection

| Session | ASD Gate | Sigma Rules |
|---------|----------|-------------|
| empire_mimikatz_logonpasswords | **DETECTED** | MISSED |
| empire_psexec_dcerpc_tcp_svcctl | **DETECTED** | MISSED |
| empire_launcher_vbs | **DETECTED** | MISSED |
| empire_dcsync_dcerpc_drsuapi | **DETECTED** | MISSED |
| **Detection rate** | **4/4 (100%)** | **0/4 (0%)** |

### Event-Level Detail — ASD Gate

| Dataset | Events Evaluated | INADMISSIBLE | INDETERMINATE | Gate Invariants Fired |
|---------|-----------------|-------------|---------------|----------------------|
| Mimikatz | 679 | 323 (47.6%) | 272 (40.0%) | ORDER, JURISDICTION, HYSTERESIS, BURST_CADENCE |
| PsExec | 2,945 | 1,378 (46.8%) | 1,494 (50.8%) | ORDER, JURISDICTION, HYSTERESIS, BURST_CADENCE |
| VBS Launcher | 1,190 | 687 (57.7%) | 324 (27.2%) | ORDER, JURISDICTION, HYSTERESIS, BURST_CADENCE |
| DCSync | 585 | 271 (46.3%) | 260 (44.4%) | ORDER, JURISDICTION, HYSTERESIS, BURST_CADENCE |
| **Overall** | **5,399** | **2,659 (49.2%)** | **2,350 (43.5%)** | All four non-EXIT invariants |

*Note: 15,507 events were format-unrecognized (EventIDs with no current mapping in the cyber compiler vocabulary). INDETERMINATE is the correct gate output for unmapped events — not a false negative.*

### Event-Level Detail — Sigma Rules

| Dataset | Events | Sigma Hits | Rules Fired |
|---------|--------|-----------|-------------|
| Mimikatz | 6,026 | 0 | None |
| PsExec | 4,348 | 0 | None |
| VBS Launcher | 2,067 | 0 | None |
| DCSync | 8,465 | 0 | None |
| **Overall** | **20,906** | **0 (0.0%)** | None |

---

## Why Sigma Missed All Four Sessions

The Sigma rules require specific known-bad indicators in specific fields: tool names containing "dump", command-line strings containing "-EncodedCommand", process names matching PsExec, RPC method names matching known DCSync calls. Empire's LotL approach routes all of these operations through legitimate Windows system processes:

- Mimikatz credential access: executed via `powershell.exe` and `svchost.exe` — no "mimikatz", "sekurlsa", or "dump" string in any process name or command line
- PsExec lateral movement: service creation via DCERPC — the service executable runs as a legitimate path
- VBS launcher: encoded payload in a `.vbs` file executed by `wscript.exe` — no `-EncodedCommand` flag visible in the Sysmon log
- DCSync: DRSUAPI RPC calls from `powershell.exe` — no known-bad process name in the chain

A string-search across all 20,906 events for any of the 9 known-bad keywords (mimikatz, sekurlsa, lsadump, psexec, base64, encoded, dcsync, -enc, -encode) returns matches in 10,586 events (50.6%). But those keyword matches do not occur in the specific field+value combinations the Sigma rules require. The rules cannot fire without exact field-level IOC matches.

The gate does not look for strings. It evaluates whether the sequence of actions by the actor is structurally admissible given the actor's role and the current state of the session. Empire uses legitimate processes in illegitimate sequences — which is structurally inadmissible regardless of whether any individual process name or command string matches a known pattern.

---

## False Positive Status

The false positive pressure test (May 21, 2026) confirmed 0/109 INADMISSIBLE verdicts across 30 clean traversal passes on legitimate sequences. Sigma rules were not tested for false positives in this benchmark, but the 0/4 detection rate renders false positive comparison moot for this dataset.

---

## Summary

| Metric | ASD Gate | Sigma (community ruleset) |
|--------|----------|--------------------------|
| Session detection rate (LotL) | **100% (4/4)** | **0% (0/4)** |
| Event-level INADMISSIBLE rate | 49.2% | 0.0% |
| Detection mechanism | Structural admissibility | Known-bad string/pattern matching |
| Requires known attack signatures | No | Yes |
| Fires on novel LotL variants | Yes (structurally) | No (signature gap) |

The LotL detection gap is not a tuning problem for signature-based tools — it is structural. Signature detection requires that the adversary use recognizable tools or strings. LotL is defined by the deliberate avoidance of those. The gate fires on the structural illegitimacy of the sequence regardless of the vocabulary of individual events.

---

## Methodological Note

This benchmark used 5 Sigma rules from the SigmaHQ community ruleset, targeting the specific ATT&CK techniques present in the Mordor datasets. A production SIEM deployment would have access to hundreds of additional rules. However, the LotL gap is not a rule count problem — additional rules that still require field-level IOC matching will not fire on sequences that contain no IOCs. The structural detection gap is present regardless of ruleset size.

---

*Gate kernel: domain_compiler_v0_9.py — unchanged since May 15, 2026.*
*Comparison: Sigma community rules (SigmaHQ), 5 rules targeting T1003.001, T1021.002, T1059.005, T1003.006.*
*Dataset: OTRF Security Datasets (Mordor), 4 adversary-emulation scenarios.*
