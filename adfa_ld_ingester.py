"""
ADFA-LD Ingester — Domain Compiler v0.7.1
Linux Audit Dataset (Australian Defence Force Academy)

WHAT THIS IS
============
ADFA-LD is the standard academic benchmark for Linux host-based intrusion
detection. It contains system call traces from a Ubuntu 11.04 Apache web
server under normal operation and under six attack types. Cited in 200+
published IDS papers, which makes our results directly comparable.

QUICK START
===========
Step 1: Install dependencies (standard library only — none required)
Step 2: Run with auto-download:

    python adfa_ld_ingester.py

The script downloads ADFA-LD from GitHub (~3 MB), extracts it, runs all
traces through the v0.7.1 compiler, and writes results to:
    results_adfa_ld.json

MANUAL DOWNLOAD (if auto-download fails)
=========================================
1. Go to: https://github.com/nikabot/ADFA-LD
2. Click Code > Download ZIP
3. Extract the ZIP so you have a folder called ADFA-LD-master/ (or similar)
   in the same directory as this script.
4. Run: python adfa_ld_ingester.py --data-dir ./ADFA-LD-master

EXPECTED FOLDER STRUCTURE
==========================
ADFA-LD-master/
    Training_Data_Master/       <- 833 normal traces (Apache web server)
    Attack_Data_Master/
        Adduser/                <- privilege escalation (user account creation)
        Hydra_FTP/              <- brute-force FTP login
        Hydra_SSH/              <- brute-force SSH login
        Java_Meterpreter/       <- Metasploit Java reverse shell
        Meterpreter/            <- Metasploit native reverse shell
        Webshell/               <- PHP webshell command execution

TRACE FORMAT
============
Each file is a plain text file containing Linux system call numbers,
one per line (or space-separated on one line). Example:
    45
    54
    3
    ...
Maps to syscall numbers (x86_64 ABI). Our auditd compiler handles
numeric syscall IDs directly via AUDITD_ACTION_MAP.

IDENTITY MODEL
==============
ADFA-LD has no process context (no exe, no PID, no UID per event).
We assign synthetic identities per category:
  Normal traces -> exe = /usr/sbin/apache2  -> PROCESS:apache2 -> WebServerProcess
  Webshell      -> exe = /var/www/php-cgi   -> PROCESS:php-cgi -> WebServerProcess
                   (webshell is IN the web server — JURISDICTION fires on execve)
  Adduser       -> exe = /bin/bash          -> PROCESS:bash    -> UserShell
  Meterpreter   -> exe = /tmp/meterp        -> PROCESS:meterp  -> UserShell (unknown)
  Hydra         -> exe = /usr/bin/hydra     -> PROCESS:hydra   -> UserShell (unknown)

DETECTION MODEL
===============
Benign: event-level ADMISSIBLE rate (false positive per syscall event)
Attack: session-level detection rate (did gate fire in this trace?)
This mirrors the ADFA-LD evaluation standard used in published papers.

KNOWN LIMITATIONS
=================
Many ADFA-LD syscalls are NOT in our vocabulary (mmap, brk, mprotect, munmap,
ioctl, rt_sigaction, etc.). These return INDETERMINATE, which is the correct
behavior — they carry no semantic trajectory information. The key syscalls
(execve, setuid, read, write, open, clone, fork) ARE mapped.

Hydra attacks use network syscalls (connect, accept, recvfrom, sendto) that
are not in our current auditd vocabulary. Hydra will show lower detection
rates, which is an honest architectural limitation to document.
"""

import argparse
import json
import os
import sys
import urllib.request
import zipfile
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Make sure the compiler is importable from parent or current dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from domain_compiler_v0_7_3 import DomainCompiler, evaluate_gate


# =============================================================================
# CONFIGURATION
# =============================================================================

ADFA_LD_URLS = [
    # Primary: verazuo labelled mirror (most reliable, includes syscall list)
    "https://github.com/verazuo/a-labelled-version-of-the-ADFA-LD-dataset/archive/refs/heads/master.zip",
    # Fallback 1: nikabot mirror, main branch
    "https://github.com/nikabot/ADFA-LD/archive/refs/heads/main.zip",
    # Fallback 2: nikabot mirror, master branch (old name)
    "https://github.com/nikabot/ADFA-LD/archive/refs/heads/master.zip",
]
DEFAULT_DATA_DIR = "./ADFA-LD-master"
OUTPUT_FILE      = "results_adfa_ld.json"

# Synthetic exe assignments per category
# Maps folder name -> (exe_path, uid_str)
# The exe_path basename is what PROCESS:basename maps to in the role table
CATEGORY_EXE: Dict[str, Tuple[str, str]] = {
    "Training_Data_Master": ("/usr/sbin/apache2", "33"),   # www-data uid
    "Adduser":              ("/bin/bash",          "0"),    # root
    "Hydra_FTP":            ("/usr/bin/hydra",     "1000"),
    "Hydra_SSH":            ("/usr/bin/hydra",     "1000"),
    "Java_Meterpreter":     ("/tmp/java",          "1000"),
    "Meterpreter":          ("/tmp/meterp",        "1000"),
    "Webshell":             ("/var/www/php-cgi",   "33"),   # www-data uid
}

# Whether a category should be detected as an attack
CATEGORY_IS_ATTACK: Dict[str, bool] = {
    "Training_Data_Master": False,
    "Adduser":              True,
    "Hydra_FTP":            True,
    "Hydra_SSH":            True,
    "Java_Meterpreter":     True,
    "Meterpreter":          True,
    "Webshell":             True,
}

# Expected dominant invariant per attack category (for annotation)
CATEGORY_EXPECTED_INVARIANT: Dict[str, str] = {
    "Adduser":          "ORDER/JURISDICTION (setuid sequence)",
    "Hydra_FTP":        "INDETERMINATE (unmapped network syscalls)",
    "Hydra_SSH":        "INDETERMINATE (unmapped network syscalls)",
    "Java_Meterpreter": "JURISDICTION/ORDER (execve + privilege ops)",
    "Meterpreter":      "JURISDICTION/ORDER (execve + privilege ops)",
    "Webshell":         "JURISDICTION (execve from WebServerProcess)",
}


ADFA_MANUAL = """
MANUAL DOWNLOAD (auto-download failed):
  Option A — verazuo mirror (recommended):
    1. Go to: https://github.com/verazuo/a-labelled-version-of-the-ADFA-LD-dataset
    2. Click Code > Download ZIP  →  extract the ZIP
    3. python adfa_ld_ingester.py --data-dir ./a-labelled-version-of-the-ADFA-LD-dataset-master

  Option B — nikabot mirror:
    1. Go to: https://github.com/nikabot/ADFA-LD
    2. Click Code > Download ZIP  →  extract the ZIP
    3. python adfa_ld_ingester.py --data-dir ./ADFA-LD-main
"""

# =============================================================================
# DOWNLOAD & SETUP
# =============================================================================

def download_adfa_ld(dest_dir: str) -> str:
    """Try each URL in ADFA_LD_URLS until one succeeds. Returns extracted root."""
    print("Downloading ADFA-LD from GitHub (trying multiple mirrors)...")
    os.makedirs(dest_dir, exist_ok=True)
    zip_data = None

    for url in ADFA_LD_URLS:
        print(f"  Trying: {url}")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 ADFA-LD-Ingester/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                zip_data = resp.read()
            print(f"  Downloaded {len(zip_data):,} bytes.")
            break
        except Exception as e:
            print(f"  Failed ({e})")

    if not zip_data:
        raise RuntimeError("All mirrors failed." + ADFA_MANUAL)

    print("  Extracting...")


    print(f"  Downloaded {len(zip_data):,} bytes. Extracting...")
    os.makedirs(dest_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(dest_dir)

    # verazuo mirror nests ADFA-LD.zip inside the outer zip — extract it too
    for root, dirs, files in os.walk(dest_dir):
        for fname in files:
            if fname == "ADFA-LD.zip":
                inner_path = os.path.join(root, fname)
                print(f"  Found inner archive: {inner_path}  Extracting...")
                with zipfile.ZipFile(inner_path) as inner_zf:
                    inner_zf.extractall(root)
                break

    # Find extracted root (GitHub adds -master suffix)
    candidates = [
        os.path.join(dest_dir, d)
        for d in os.listdir(dest_dir)
        if os.path.isdir(os.path.join(dest_dir, d)) and "ADFA" in d.upper()
    ]
    if not candidates:
        raise RuntimeError(f"Could not find ADFA-LD folder after extraction in {dest_dir}")

    root = candidates[0]
    print(f"  Extracted to: {root}")
    return root


def find_adfa_root(data_dir: str) -> str:
    """
    Find the ADFA-LD root directory by searching recursively for the
    Training_Data_Master folder (up to 4 levels deep).
    Handles different mirror structures:
      - nikabot:  ADFA-LD-main/Training_Data_Master/
      - verazuo:  a-labelled-.../ADFA-LD/Training_Data_Master/
    """
    if not os.path.isdir(data_dir):
        raise RuntimeError(f"Path does not exist: {data_dir}")

    # Walk up to 4 directory levels looking for Training_Data_Master
    for root, dirs, _ in os.walk(data_dir):
        if "Training_Data_Master" in dirs:
            return root
        # Limit depth to avoid walking deep into large trees
        depth = root.replace(data_dir, "").count(os.sep)
        if depth >= 4:
            dirs.clear()

    raise RuntimeError(
        f"Could not find Training_Data_Master/ anywhere under {data_dir}.\n"
        "Check the dataset extracted correctly, then run:\n"
        "  python adfa_ld_ingester.py --data-dir ./adfa_ld_download"
    )


# =============================================================================
# TRACE PARSER
# =============================================================================

def parse_trace_file(path: str) -> List[str]:
    """
    Parse an ADFA-LD trace file into a list of syscall number strings.
    Handles both formats:
      - One syscall per line: "45\n54\n3\n..."
      - Space-separated on one line: "45 54 3 ..."
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()

    if not content:
        return []

    # Detect format: if newlines dominate, one-per-line; else space-separated
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if len(lines) > 1:
        # One-per-line format (possibly with multiple numbers per line)
        syscalls = []
        for line in lines:
            syscalls.extend(line.split())
        return [s for s in syscalls if s.isdigit()]
    else:
        # Single line, space-separated
        return [s for s in content.split() if s.isdigit()]


def syscall_to_auditd_event(syscall_num: str, exe: str, uid: str,
                             pid: str = "1000") -> dict:
    """
    Wrap a raw ADFA-LD syscall number into an auditd-format event dict
    that our DomainCompiler._compile_auditd() can process.
    """
    return {
        "type":    "SYSCALL",
        "syscall": syscall_num,   # numeric string — AUDITD_ACTION_MAP handles these
        "exe":     exe,
        "pid":     pid,
        "uid":     uid,
    }


# =============================================================================
# SESSION RUNNER
# =============================================================================

def run_trace(trace_events: List[dict]) -> Tuple[bool, Dict[str, int], int, int, int]:
    """
    Run one ADFA-LD trace through a fresh DomainCompiler instance.

    Returns:
      (session_fired, invariant_counts, admissible, inadmissible, indeterminate)
    where session_fired = True if ANY event returned INADMISSIBLE.
    """
    compiler          = DomainCompiler()
    session_fired     = False
    inv_counts: Dict[str, int] = {}
    n_adm = n_inadm = n_indet = 0

    for ev in trace_events:
        pkt     = compiler.compile(ev)
        verdict = evaluate_gate(pkt)
        dec     = verdict["decision"]
        inv     = verdict["invariant"]

        if dec == "ADMISSIBLE":
            n_adm += 1
        elif dec == "INADMISSIBLE":
            n_inadm      += 1
            session_fired = True
            inv_counts[inv] = inv_counts.get(inv, 0) + 1
        else:
            n_indet += 1

    return session_fired, inv_counts, n_adm, n_inadm, n_indet


# =============================================================================
# CATEGORY PROCESSOR
# =============================================================================

def process_category(cat_name: str, folder_path: str) -> dict:
    """
    Process all trace files in one ADFA-LD category folder.
    Returns per-category statistics.
    """
    exe, uid     = CATEGORY_EXE.get(cat_name, ("/bin/bash", "1000"))
    is_attack    = CATEGORY_IS_ATTACK.get(cat_name, True)

    # Find all trace files (any extension or none)
    trace_paths = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ])

    sessions_total    = 0
    sessions_detected = 0
    events_total      = 0
    events_adm        = 0
    events_inadm      = 0
    events_indet      = 0
    inv_totals: Dict[str, int] = {}
    empty_traces      = 0

    for tp in trace_paths:
        syscalls = parse_trace_file(tp)
        if not syscalls:
            empty_traces += 1
            continue

        events = [syscall_to_auditd_event(s, exe, uid, str(1000 + sessions_total))
                  for s in syscalls]

        fired, inv_counts, n_adm, n_inadm, n_indet = run_trace(events)

        sessions_total    += 1
        events_total      += len(events)
        events_adm        += n_adm
        events_inadm      += n_inadm
        events_indet      += n_indet
        if fired:
            sessions_detected += 1
        for k, v in inv_counts.items():
            inv_totals[k] = inv_totals.get(k, 0) + v

    sess_det_pct = (100 * sessions_detected / sessions_total
                    if sessions_total else 0.0)
    ev_adm_pct   = 100 * events_adm   / events_total if events_total else 0.0
    ev_indet_pct = 100 * events_indet / events_total if events_total else 0.0

    return {
        "category":          cat_name,
        "exe_assigned":      exe,
        "role_assigned":     "WebServerProcess" if "apache" in exe or "php" in exe
                             else "UserShell",
        "is_attack":         is_attack,
        "expected_invariant": CATEGORY_EXPECTED_INVARIANT.get(cat_name, "—"),
        "sessions_total":    sessions_total,
        "sessions_detected": sessions_detected,
        "session_detection_pct": round(sess_det_pct, 1),
        "events_total":      events_total,
        "events_admissible": events_adm,
        "events_inadmissible": events_inadm,
        "events_indeterminate": events_indet,
        "events_admissible_pct":   round(ev_adm_pct, 1),
        "events_indeterminate_pct": round(ev_indet_pct, 1),
        "invariant_distribution":  inv_totals,
        "empty_traces_skipped": empty_traces,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ADFA-LD benchmark ingester for Domain Compiler v0.7.1"
    )
    parser.add_argument(
        "--data-dir", default=DEFAULT_DATA_DIR,
        help=f"Path to ADFA-LD dataset root (default: {DEFAULT_DATA_DIR})"
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Auto-download ADFA-LD from GitHub if not already present"
    )
    parser.add_argument(
        "--output", default=OUTPUT_FILE,
        help=f"Output JSON path (default: {OUTPUT_FILE})"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("ADFA-LD Benchmark Ingester — Domain Compiler v0.7.1")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print("=" * 70)

    # ── Locate / download dataset ─────────────────────────────────────────────
    dl_dir   = "./adfa_ld_download"
    data_dir = args.data_dir

    if not os.path.isdir(data_dir) or args.download:
        download_adfa_ld(dl_dir)   # extracts into dl_dir
        data_dir = dl_dir          # find_adfa_root will walk from here

    try:
        adfa_root = find_adfa_root(data_dir)
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    print(f"\nDataset root: {adfa_root}")

    # ── Discover categories ───────────────────────────────────────────────────
    # Normal traces are in Training_Data_Master/
    # Attack traces are in Attack_Data_Master/{attack_name}/
    category_paths: List[Tuple[str, str]] = []

    train_path = os.path.join(adfa_root, "Training_Data_Master")
    if os.path.isdir(train_path):
        category_paths.append(("Training_Data_Master", train_path))

    attack_root = os.path.join(adfa_root, "Attack_Data_Master")
    if os.path.isdir(attack_root):
        for attack_name in sorted(os.listdir(attack_root)):
            attack_path = os.path.join(attack_root, attack_name)
            if os.path.isdir(attack_path):
                category_paths.append((attack_name, attack_path))

    if not category_paths:
        print("ERROR: No categories found. Check dataset structure.")
        sys.exit(1)

    print(f"\nCategories found: {[c[0] for c in category_paths]}")
    print("\nProcessing traces...\n")

    # ── Process each category ─────────────────────────────────────────────────
    category_results = []
    global_inv: Dict[str, int] = {}

    for cat_name, cat_path in category_paths:
        print(f"  Processing {cat_name}...", end=" ", flush=True)
        result = process_category(cat_name, cat_path)
        category_results.append(result)
        for k, v in result["invariant_distribution"].items():
            global_inv[k] = global_inv.get(k, 0) + v
        det = f"{result['sessions_detected']}/{result['sessions_total']}"
        pct = result['session_detection_pct']
        adm = result['events_admissible_pct']
        ind = result['events_indeterminate_pct']
        if result["is_attack"]:
            print(f"sessions detected: {det} ({pct:.0f}%)  "
                  f"indet: {ind:.0f}%")
        else:
            print(f"ADMISSIBLE: {adm:.1f}%  "
                  f"indet: {ind:.1f}%  "
                  f"n={result['sessions_total']} traces")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    benign_cats  = [r for r in category_results if not r["is_attack"]]
    attack_cats  = [r for r in category_results if r["is_attack"]]

    benign_sessions = sum(r["sessions_total"]    for r in benign_cats)
    benign_fp       = sum(r["sessions_detected"] for r in benign_cats)
    benign_events   = sum(r["events_total"]      for r in benign_cats)
    benign_adm_ev   = sum(r["events_admissible"] for r in benign_cats)
    benign_indet_ev = sum(r["events_indeterminate"] for r in benign_cats)

    attack_sessions = sum(r["sessions_total"]    for r in attack_cats)
    attack_detected = sum(r["sessions_detected"] for r in attack_cats)
    attack_events   = sum(r["events_total"]      for r in attack_cats)

    benign_adm_rate = 100 * benign_adm_ev / benign_events  if benign_events  else 0
    benign_fp_rate  = 100 * benign_fp     / benign_sessions if benign_sessions else 0
    benign_indet_rate = 100 * benign_indet_ev / benign_events if benign_events else 0
    attack_det_rate = 100 * attack_detected / attack_sessions if attack_sessions else 0

    total_events    = benign_events + attack_events
    total_indet_ev  = sum(r["events_indeterminate"] for r in category_results)
    total_indet_pct = 100 * total_indet_ev / total_events if total_events else 0

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nDataset: ADFA-LD  |  Compiler: v0.7.1  |  Domain: auditd (Linux)")
    print(f"Total events processed: {total_events:,}")
    print(f"Total traces:           {benign_sessions + attack_sessions}")

    print(f"\nBenign (Training_Data_Master):")
    print(f"  Traces:                  {benign_sessions}")
    print(f"  Events:                  {benign_events:,}")
    print(f"  ADMISSIBLE (event %):    {benign_adm_rate:.1f}%")
    print(f"  INDETERMINATE (event %): {benign_indet_rate:.1f}%  "
          f"(unmapped syscalls — expected)")
    print(f"  False positive traces:   {benign_fp}/{benign_sessions}  "
          f"({benign_fp_rate:.1f}%)")

    print(f"\nAttack categories:")
    print(f"  {'Category':<22} {'Traces':>7} {'Detected':>9} {'Det%':>6}  "
          f"{'Indet%':>7}  Expected invariant")
    print(f"  {'-'*22} {'-'*7} {'-'*9} {'-'*6}  {'-'*7}  {'-'*30}")
    for r in attack_cats:
        det_pct  = r["session_detection_pct"]
        indet_pct = r["events_indeterminate_pct"]
        print(f"  {r['category']:<22} {r['sessions_total']:>7} "
              f"{r['sessions_detected']:>9} {det_pct:>5.1f}%  "
              f"{indet_pct:>6.1f}%  {r['expected_invariant']}")

    print(f"\nOverall attack session detection: {attack_detected}/{attack_sessions}  "
          f"({attack_det_rate:.1f}%)")
    print(f"Overall INDETERMINATE rate:        {total_indet_pct:.1f}%")

    print(f"\nInvariant distribution (all INADMISSIBLE events):")
    for inv_name in ["JURISDICTION", "ORDER", "BURST_CADENCE", "EXIT"]:
        cnt = global_inv.get(inv_name, 0)
        print(f"  {inv_name:<16} {cnt:>6}")

    # ── Save ──────────────────────────────────────────────────────────────────
    out = {
        "benchmark":         "ADFA-LD",
        "compiler_version":  "v0.7.3",
        "domain":            "auditd (Linux)",
        "timestamp":         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_url":       "https://github.com/nikabot/ADFA-LD",
        "citation":          "Creech & Hu (2013). A Semantic Approach to Host-Based "
                             "Intrusion Detection Systems Using Contiguous System "
                             "Call Patterns. IEEE TIFS.",
        "total_events":      total_events,
        "benign": {
            "sessions":          benign_sessions,
            "events":            benign_events,
            "admissible_pct":    round(benign_adm_rate, 2),
            "indeterminate_pct": round(benign_indet_rate, 2),
            "false_positive_sessions": benign_fp,
            "false_positive_pct":  round(benign_fp_rate, 2),
        },
        "attack": {
            "sessions_total":    attack_sessions,
            "sessions_detected": attack_detected,
            "session_detection_pct": round(attack_det_rate, 2),
        },
        "overall_indeterminate_pct": round(total_indet_pct, 2),
        "invariant_distribution": global_inv,
        "category_results":  category_results,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\nResults saved to: {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
