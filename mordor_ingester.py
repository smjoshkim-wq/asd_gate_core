"""
Mordor / Security Datasets Ingester — Domain Compiler v0.7.1
Windows Sysmon benchmark using the OTRF Security Datasets project

WHAT THIS IS
============
The OTRF Security Datasets project (formerly Mordor) contains real Sysmon
telemetry captured during live Atomic Red Team and adversary emulation runs.
Every attack is documented, tagged with ATT&CK technique IDs, and the raw
Sysmon JSON logs are published openly. This makes our gate's results directly
citeable against documented attack scenarios.

QUICK START
===========
Run with auto-download of curated attack datasets:

    python mordor_ingester.py

The script downloads ~6 targeted JSON datasets from the Security Datasets
GitHub repo, runs all events through the v0.7.1 compiler, and writes results
to: results_mordor.json

MANUAL DOWNLOAD (if auto-download fails)
=========================================
1. Go to: https://github.com/OTRF/Security-Datasets
2. Navigate to: datasets/atomic/windows/
3. Download any .zip or .json.gz files of interest
4. Extract and pass the folder path:
    python mordor_ingester.py --data-dir ./my_mordor_datasets

   OR pass individual JSON files:
    python mordor_ingester.py --files ./mimikatz.json ./psexec.json

DATASET FORMAT
==============
Security Datasets Sysmon events come in multiple JSON formats.
This ingester handles all of them:

Format A (flat, older datasets):
  {"EventID": 1, "Image": "C:\\...", "ParentImage": "C:\\...", ...}

Format B (Elastic/winlogbeat wrapper, newer datasets):
  {"@timestamp": "...", "winlog": {"event_id": 1, "event_data": {...}},
   "event": {"code": "1"}}

Format C (Sysmon XML-parsed):
  {"System": {"EventID": {"#text": "1"}}, "EventData": {"Data": [...]}}

The normalizer converts all three to the flat format our compiler expects.

TARGETED DATASETS
=================
This ingester targets six curated attack scenarios covering:
  1. Credential Access   — Mimikatz LSASS dump (ATT&CK T1003.001)
  2. Lateral Movement    — PsExec remote execution (ATT&CK T1021.002)
  3. Execution           — PowerShell encoded command (ATT&CK T1059.001)
  4. Persistence         — Scheduled task creation (ATT&CK T1053.005)
  5. Defense Evasion     — Process injection (ATT&CK T1055)
  6. Discovery           — Process/network discovery (ATT&CK T1057/T1049)

DETECTION MODEL
===============
Each attack scenario = one session. Per-session compiler instances.
Detection = at least one INADMISSIBLE event in the session.
Session-level detection rate is the primary metric (mirrors SIEM behavior).

CITATION
========
OTRF Security Datasets: https://github.com/OTRF/Security-Datasets
Roberto Rodriguez et al., "Mordor: Adversary Attack Simulation Data Sharing
for Detection Engineering", 2020.
"""

import argparse
import gzip
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from domain_compiler_v0_7_1 import DomainCompiler, evaluate_gate


# =============================================================================
# CURATED DATASET CATALOG
#
# These are specific Security Datasets files with stable GitHub URLs.
# Each entry: (local_name, url, attack_name, attck_id, expected_invariant)
# =============================================================================

# Confirmed-working base URLs (zip archives, not raw JSON)
_SD  = "https://raw.githubusercontent.com/OTRF/Security-Datasets/master/datasets/atomic/windows"
_OLD = "https://raw.githubusercontent.com/OTRF/mordor/master/datasets/small/windows"

CURATED_DATASETS = [
    {
        "name":     "mimikatz_extract_keys",
        "urls": [
            f"{_SD}/credential_access/host/empire_mimikatz_extract_keys.zip",
            f"{_OLD}/credential_access/host/empire_mimikatz_extract_keys.zip",
        ],
        "attack":   "Mimikatz Extract Kerberos Keys",
        "attck_id": "T1003.001",
        "category": "credential_access",
        "expected": "ORDER (lsass ProcessAccess without prior Executing)",
    },
    {
        "name":     "dcsync_drsuapi",
        "urls": [
            f"{_OLD}/credential_access/host/covenant_dcsync_dcerpc_drsuapi_DsGetNCChanges.zip",
            f"{_SD}/credential_access/host/covenant_dcsync_dcerpc_drsuapi_DsGetNCChanges.zip",
        ],
        "attack":   "DCSync via DRSUAPI (credential dump)",
        "attck_id": "T1003.006",
        "category": "credential_access",
        "expected": "JURISDICTION or ORDER (unusual process doing DRSUAPI replication)",
    },
    {
        "name":     "psexec_svcctl",
        "urls": [
            f"{_SD}/lateral_movement/host/empire_psexec_dcerpc_tcp_svcctl.zip",
            f"{_OLD}/lateral_movement/host/empire_psexec_dcerpc_tcp_svcctl.zip",
        ],
        "attack":   "PsExec lateral movement via SVCCTL",
        "attck_id": "T1021.002",
        "category": "lateral_movement",
        "expected": "JURISDICTION (unexpected process spawn chain from service)",
    },
    {
        "name":     "empire_launcher_vbs",
        "urls": [
            f"{_SD}/execution/host/empire_launcher_vbs.zip",
            f"{_OLD}/execution/host/empire_launcher_vbs.zip",
        ],
        "attack":   "Empire VBS launcher (wscript -> PowerShell stager)",
        "attck_id": "T1059.005",
        "category": "execution",
        "expected": "JURISDICTION (wscript spawning powershell = LotL chain)",
    },
    {
        "name":     "empire_schtasks",
        "urls": [
            f"{_SD}/persistence/host/empire_schtasks.zip",
            f"{_OLD}/persistence/host/empire_schtasks.zip",
        ],
        "attack":   "Scheduled Task persistence via schtasks.exe",
        "attck_id": "T1053.005",
        "category": "persistence",
        "expected": "BURST_CADENCE or ORDER (schtasks create/delete oscillation)",
    },
    {
        "name":     "net_user_discovery",
        "urls": [
            f"{_SD}/discovery/host/empire_shell_net_user_localgroup.zip",
            f"{_OLD}/discovery/host/empire_shell_net_user_localgroup.zip",
        ],
        "attack":   "User/Group discovery via net.exe",
        "attck_id": "T1087.001",
        "category": "discovery",
        "expected": "BURST_CADENCE (rapid Read/Execute oscillation from net.exe)",
    },
]

MORDOR_MANUAL = """
MANUAL DOWNLOAD (if auto-download failed):
  1. Go to: https://github.com/OTRF/Security-Datasets
     or:     https://github.com/OTRF/mordor  (older datasets, also valid)
  2. Browse to datasets/atomic/windows/<category>/host/
  3. Download any .zip files
  4. Extract the JSON files into a folder, then run:
     python mordor_ingester.py --data-dir ./my_mordor_datasets

  Confirmed direct download links (paste into browser):
  https://raw.githubusercontent.com/OTRF/mordor/master/datasets/small/windows/credential_access/host/covenant_dcsync_dcerpc_drsuapi_DsGetNCChanges.zip
  https://raw.githubusercontent.com/OTRF/Security-Datasets/master/datasets/atomic/windows/credential_access/host/empire_mimikatz_extract_keys.zip
"""

OUTPUT_FILE = "results_mordor.json"


# =============================================================================
# DOWNLOAD
# =============================================================================

def try_download(url: str, timeout: int = 30) -> Optional[bytes]:
    """Attempt to download a URL. Returns bytes or None on failure."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 Mordor-Ingester/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def download_dataset(entry: dict, dest_dir: str) -> Optional[str]:
    """
    Download one dataset zip file, trying each URL in entry['urls'].
    Extracts the JSON from the zip. Returns local file path or None.
    """
    os.makedirs(dest_dir, exist_ok=True)
    local_path = os.path.join(dest_dir, f"{entry['name']}.json")

    if os.path.exists(local_path):
        return local_path

    for url in entry.get("urls", []):
        data = try_download(url)
        if data is None:
            continue
        # All Mordor/Security-Datasets files are zips containing a JSON
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                json_files = [n for n in zf.namelist() if n.endswith(".json")]
                target = json_files[0] if json_files else zf.namelist()[0]
                extracted = zf.read(target)
        except zipfile.BadZipFile:
            # Some older files are raw JSON, not zipped
            extracted = data

        with open(local_path, "wb") as f:
            f.write(extracted)
        return local_path

    return None


# =============================================================================
# JSON NORMALIZER
# =============================================================================

def normalize_event(raw: dict) -> Optional[dict]:
    """
    Normalize a Security Datasets Sysmon event to the flat format
    our _compile_sysmon() expects:
      {"EventID": int, "Image": str, "ParentImage": str, ...}

    Handles three source formats:
      A. Flat: {"EventID": 1, "Image": "...", ...}
      B. Winlogbeat: {"winlog": {"event_id": 1, "event_data": {...}}}
      C. System/EventData XML parse: {"System": {...}, "EventData": {...}}

    Returns None if event cannot be normalized to a usable Sysmon event.
    """
    if not isinstance(raw, dict):
        return None

    # ── Format A: already flat ────────────────────────────────────────────────
    if "EventID" in raw and isinstance(raw.get("EventID"), (int, str)):
        try:
            eid = int(raw["EventID"])
            if 1 <= eid <= 29:
                return raw  # already in our expected format
        except (TypeError, ValueError):
            pass

    # ── Format B: Elastic winlogbeat wrapper ─────────────────────────────────
    winlog = raw.get("winlog") or raw.get("Winlog") or {}
    if winlog:
        event_id_raw = winlog.get("event_id") or winlog.get("EventId")
        if event_id_raw is not None:
            try:
                eid = int(event_id_raw)
            except (TypeError, ValueError):
                return None
            if not (1 <= eid <= 29):
                return None

            event_data = winlog.get("event_data") or winlog.get("EventData") or {}
            if not isinstance(event_data, dict):
                event_data = {}

            normalized = {"EventID": eid}
            # Map all event_data fields to top-level (our compiler reads them flat)
            normalized.update({k: v for k, v in event_data.items()
                                if isinstance(v, (str, int, float))})
            # Also preserve timestamp if present
            if "@timestamp" in raw:
                normalized["UtcTime"] = raw["@timestamp"]
            return normalized

    # ── Format C: Raw XML-parse format ───────────────────────────────────────
    system = raw.get("System") or {}
    if system:
        eid_block = system.get("EventID") or {}
        if isinstance(eid_block, dict):
            event_id_raw = eid_block.get("#text") or eid_block.get("text")
        else:
            event_id_raw = eid_block

        if event_id_raw is not None:
            try:
                eid = int(event_id_raw)
            except (TypeError, ValueError):
                return None
            if not (1 <= eid <= 29):
                return None

            event_data_block = raw.get("EventData") or {}
            data_list = event_data_block.get("Data") or []
            normalized = {"EventID": eid}

            if isinstance(data_list, list):
                for item in data_list:
                    if isinstance(item, dict):
                        name  = item.get("@Name") or item.get("Name") or ""
                        value = item.get("#text") or item.get("text") or ""
                        if name:
                            normalized[name] = value
            elif isinstance(data_list, dict):
                normalized.update({k: v for k, v in data_list.items()
                                   if isinstance(v, str)})

            return normalized

    # ── Format D: event.code + winlog.event_data (newer Elastic format) ───────
    event_block = raw.get("event") or {}
    code        = event_block.get("code")
    if code is not None:
        try:
            eid = int(code)
        except (TypeError, ValueError):
            return None
        if not (1 <= eid <= 29):
            return None
        # event_data might be at top level or nested differently
        normalized = {"EventID": eid}
        for key in ("Image","ParentImage","ProcessGuid","ParentProcessGuid",
                    "CommandLine","User","TargetImage","DestinationIp",
                    "DestinationPort","QueryName","TargetFilename","TargetObject",
                    "PipeName","ImageLoaded","ProcessId","SourceProcessGuid"):
            val = raw.get(key)
            if val is None:
                # try nested paths
                for block in [raw.get("winlog",{}).get("event_data",{}),
                               raw.get("event_data",{})]:
                    if isinstance(block, dict) and key in block:
                        val = block[key]
                        break
            if val is not None:
                normalized[key] = val
        return normalized

    return None


def load_json_file(path: str) -> List[dict]:
    """
    Load Sysmon events from a JSON file.
    Handles:
      - NDJSON: one JSON object per line
      - JSON array: list of objects
      - Single JSON object
    """
    events = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        if not content:
            return []

        # Try NDJSON first (most common in Security Datasets)
        if content.startswith("{") and "\n{" in content:
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return events

        # Try JSON array
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]

    except (json.JSONDecodeError, IOError) as e:
        print(f"    Warning: could not parse {path}: {e}")

    return events


# =============================================================================
# SESSION RUNNER
# =============================================================================

def run_session(events: List[dict]) -> dict:
    """
    Run one attack session through a fresh DomainCompiler instance.
    Returns session-level statistics.
    """
    compiler      = DomainCompiler()
    fired         = False
    inv_counts: Dict[str, int] = {}
    n_adm = n_inadm = n_indet = n_unknown = 0

    for raw_ev in events:
        normalized = normalize_event(raw_ev)
        if normalized is None:
            n_unknown += 1
            continue

        pkt     = compiler.compile(normalized)
        verdict = evaluate_gate(pkt)
        dec     = verdict["decision"]
        inv     = verdict["invariant"]

        if dec == "ADMISSIBLE":
            n_adm += 1
        elif dec == "INADMISSIBLE":
            n_inadm += 1
            fired    = True
            inv_counts[inv] = inv_counts.get(inv, 0) + 1
        else:
            n_indet += 1

    total = n_adm + n_inadm + n_indet
    return {
        "fired":            fired,
        "events_total":     total,
        "events_skipped":   n_unknown,
        "events_admissible":     n_adm,
        "events_inadmissible":   n_inadm,
        "events_indeterminate":  n_indet,
        "invariant_distribution": inv_counts,
    }


# =============================================================================
# DATASET PROCESSOR
# =============================================================================

def process_dataset(entry: dict, file_path: str) -> dict:
    """
    Process one Security Datasets file as a single attack session.
    """
    print(f"  Processing {entry['name']}...", end=" ", flush=True)

    raw_events = load_json_file(file_path)
    if not raw_events:
        print("EMPTY FILE — skipped")
        return {**entry, "status": "empty", "events_total": 0}

    result = run_session(raw_events)

    status      = "DETECTED" if result["fired"] else "MISSED"
    total       = result["events_total"]
    inadm       = result["events_inadmissible"]
    indet       = result["events_indeterminate"]
    skipped     = result["events_skipped"]
    indet_pct   = 100 * indet  / total if total else 0
    inadm_pct   = 100 * inadm  / total if total else 0
    inv_dist    = result["invariant_distribution"]

    print(f"[{status}]  events={total}  "
          f"INADM={inadm}({inadm_pct:.0f}%)  "
          f"INDET={indet}({indet_pct:.0f}%)  "
          f"skipped={skipped}")
    if inv_dist:
        inv_str = " + ".join(f"{k}={v}" for k, v in inv_dist.items())
        print(f"    invariants: {inv_str}")

    return {
        "name":         entry["name"],
        "attack":       entry["attack"],
        "attck_id":     entry["attck_id"],
        "category":     entry["category"],
        "expected":     entry["expected"],
        "file_path":    file_path,
        "status":       status,
        "detected":     result["fired"],
        **result,
    }


# =============================================================================
# SCAN A DIRECTORY FOR JSON FILES
# =============================================================================

def scan_directory(data_dir: str) -> List[Tuple[dict, str]]:
    """
    Scan a directory for JSON files and create synthetic catalog entries.
    Used when --data-dir is specified with manually downloaded datasets.
    """
    results = []
    json_files = sorted(Path(data_dir).rglob("*.json"))
    json_files += sorted(Path(data_dir).rglob("*.ndjson"))

    for jf in json_files:
        stem = jf.stem.replace("-", "_").replace(" ", "_")
        entry = {
            "name":     stem[:40],
            "url":      "",
            "alt_url":  "",
            "attack":   stem,
            "attck_id": "UNKNOWN",
            "category": jf.parent.name,
            "expected": "Unknown — inferred from trajectory",
        }
        results.append((entry, str(jf)))

    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Mordor/Security Datasets benchmark ingester for v0.7.1"
    )
    parser.add_argument(
        "--data-dir", default=None,
        help="Path to directory containing downloaded Security Datasets JSON files"
    )
    parser.add_argument(
        "--files", nargs="+", default=None,
        help="One or more specific JSON file paths to process"
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="Skip auto-download; only process --data-dir or --files"
    )
    parser.add_argument(
        "--output", default=OUTPUT_FILE,
        help=f"Output JSON path (default: {OUTPUT_FILE})"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Mordor / Security Datasets Ingester — Domain Compiler v0.7.1")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print("=" * 70)

    # ── Build session list ────────────────────────────────────────────────────
    sessions_to_run: List[Tuple[dict, str]] = []

    if args.files:
        # Manual file list
        for fp in args.files:
            stem  = Path(fp).stem
            entry = {
                "name": stem[:40], "url": "", "alt_url": "",
                "attack": stem, "attck_id": "USER-SUPPLIED",
                "category": "user_supplied",
                "expected": "Inferred from trajectory",
            }
            sessions_to_run.append((entry, fp))

    elif args.data_dir:
        # Scan directory
        print(f"\nScanning {args.data_dir} for JSON files...")
        sessions_to_run = scan_directory(args.data_dir)
        print(f"Found {len(sessions_to_run)} files.\n")

    else:
        # Auto-download curated datasets
        if not args.no_download:
            print("\nAuto-downloading curated Security Datasets files...")
            print("(For manual download instructions, run with --help)\n")
            dl_dir = "./mordor_datasets"
            os.makedirs(dl_dir, exist_ok=True)

            for entry in CURATED_DATASETS:
                print(f"  Fetching {entry['name']}...", end=" ", flush=True)
                path = download_dataset(entry, dl_dir)
                if path:
                    print(f"OK ({os.path.getsize(path):,} bytes)")
                    sessions_to_run.append((entry, path))
                else:
                    print("FAILED")
                    for u in entry.get("urls", []):
                        print(f"    tried: {u}")

            if not sessions_to_run:
                print(MORDOR_MANUAL)

    if not sessions_to_run:
        print("\nNo datasets to process. Exiting.")
        print("Download instructions:")
        print("  https://github.com/OTRF/Security-Datasets")
        print("  Then run: python mordor_ingester.py --data-dir /path/to/datasets")
        sys.exit(1)

    # ── Process sessions ──────────────────────────────────────────────────────
    print(f"\nProcessing {len(sessions_to_run)} dataset(s)...\n")
    dataset_results = []
    global_inv: Dict[str, int] = {}

    for entry, file_path in sessions_to_run:
        if not os.path.exists(file_path):
            print(f"  SKIP {entry['name']} — file not found: {file_path}")
            continue
        result = process_dataset(entry, file_path)
        dataset_results.append(result)
        for k, v in result.get("invariant_distribution", {}).items():
            global_inv[k] = global_inv.get(k, 0) + v

    if not dataset_results:
        print("No results. Exiting.")
        sys.exit(1)

    # ── Aggregate ─────────────────────────────────────────────────────────────
    processed      = [r for r in dataset_results if r.get("status") != "empty"]
    total_sessions = len(processed)
    detected       = sum(1 for r in processed if r.get("detected"))
    total_events   = sum(r.get("events_total", 0)        for r in processed)
    total_inadm    = sum(r.get("events_inadmissible", 0) for r in processed)
    total_indet    = sum(r.get("events_indeterminate", 0)for r in processed)
    total_skip     = sum(r.get("events_skipped", 0)      for r in processed)

    det_rate    = 100 * detected     / total_sessions if total_sessions else 0
    inadm_rate  = 100 * total_inadm  / total_events   if total_events   else 0
    indet_rate  = 100 * total_indet  / total_events   if total_events   else 0

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nDataset: Mordor/Security-Datasets  |  Compiler: v0.7.1  |  "
          f"Domain: Windows Sysmon")
    print(f"Scenarios processed: {total_sessions}")
    print(f"Total events:        {total_events:,}  "
          f"({total_skip:,} format-unrecognized skipped)")

    print(f"\nPer-scenario results:")
    print(f"  {'Name':<30} {'ATT&CK':<14} {'Status':<10} "
          f"{'Events':>7} {'INADM%':>7}  Invariant")
    print(f"  {'-'*30} {'-'*14} {'-'*10} {'-'*7} {'-'*7}  {'-'*20}")
    for r in dataset_results:
        if r.get("status") == "empty":
            continue
        total_ev = r.get("events_total", 0)
        inadm_ev = r.get("events_inadmissible", 0)
        inadm_p  = 100 * inadm_ev / total_ev if total_ev else 0
        inv_str  = " + ".join(r.get("invariant_distribution", {}).keys()) or "none"
        print(f"  {r['name'][:30]:<30} {r['attck_id']:<14} "
              f"{r.get('status','?'):<10} {total_ev:>7} {inadm_p:>6.1f}%  {inv_str}")

    print(f"\nOverall attack session detection: {detected}/{total_sessions}  "
          f"({det_rate:.1f}%)")
    print(f"Event-level INADMISSIBLE rate:    {inadm_rate:.1f}%")
    print(f"Event-level INDETERMINATE rate:   {indet_rate:.1f}%  "
          f"(unmapped EventIDs / unknown processes)")

    print(f"\nInvariant distribution (all INADMISSIBLE events):")
    for inv_name in ["JURISDICTION", "ORDER", "BURST_CADENCE", "EXIT"]:
        cnt = global_inv.get(inv_name, 0)
        print(f"  {inv_name:<16} {cnt:>6}")

    # ── Save ──────────────────────────────────────────────────────────────────
    out = {
        "benchmark":        "Mordor/OTRF-Security-Datasets",
        "compiler_version": "v0.7.1",
        "domain":           "Windows Sysmon",
        "timestamp":        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_url":      "https://github.com/OTRF/Security-Datasets",
        "citation":         "Rodriguez, R. et al. (2020). Mordor: "
                            "Adversary Attack Simulation Data Sharing for "
                            "Detection Engineering. GitHub / OTRF.",
        "total_scenarios":  total_sessions,
        "total_events":     total_events,
        "events_skipped":   total_skip,
        "attack": {
            "sessions_total":    total_sessions,
            "sessions_detected": detected,
            "session_detection_pct": round(det_rate, 2),
            "events_inadmissible_pct": round(inadm_rate, 2),
        },
        "overall_indeterminate_pct": round(indet_rate, 2),
        "invariant_distribution": global_inv,
        "scenario_results": dataset_results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nResults saved to: {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
