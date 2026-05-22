from __future__ import annotations

"""
Domain Compiler v0.9 — Semantic Cyber Defense

Architecture Contract:
  - Layer 1 Execution Gate: TrajectoryTracker + five invariants.
    EXIT, JURISDICTION, ORDER, BURST_CADENCE are mathematically locked and
    UNCHANGED from v0.6.
    HYSTERESIS (ASD Invariant 4) is NEW in v0.9 — see below.
  - Layer 2 Dictionary: domain-specific extractors (cloudtrail / auditd / sysmon)
    feed identical BDO/BAS axes to the same gate.
  - No probabilistic/ML/fuzzy logic. Strings are law.

v0.9 Additions vs v0.8:
  HYSTERESIS INVARIANT (ASD Invariant 4 — fifth and final invariant)
  ─────────────────────────────────────────────────────────────────
  ASD definition: "Once irreversible commitments are crossed under ambiguity,
  the future admissible state space deforms asymmetrically. Rollback does not
  restore prior state."

  Cyber translation: An actor who has violated a constraint cannot subsequently
  claim normal operational status. Their admissible state space is permanently
  scarred — further scope expansion (entering previously unvisited states) is
  structurally inadmissible regardless of whether the next action would otherwise
  be legal.

  Implementation:
  - _violation_history: Dict[str, bool]
      Tracks whether identity has ever produced an INADMISSIBLE verdict
      (JURISDICTION or ORDER). Set True inside evaluate() on inadmissible return.
  - _visited_states: Dict[Tuple[str,str], Set[str]]
      Records every state (identity, role) has reached via ADMISSIBLE transitions.
      Populated inside evaluate() on the admissible path only.
  - check_hysteresis(identity, role, action) -> bool
      Returns True when ALL of:
        1. identity has a prior violation (_violation_history[identity] = True)
        2. visited_states[(identity, role)] is non-empty (legitimate history exists)
        3. the action, if taken, would lead to a state NOT in visited_states
      The non-empty guard prevents locking out an actor whose very first event was
      a violation — they should be able to attempt their first legitimate action.
  - Gate path: check_hysteresis() fires BEFORE tracker.evaluate() so the state
      machine does NOT advance when hysteresis is triggered.
  - evaluate_gate(): HYSTERESIS checked first in the inadmissible branch.
      Invariant label: "HYSTERESIS"
  - BAS_Metrics: new field HysteresisViolation (bool).

  Architectural contract preserved:
    EXIT, JURISDICTION, ORDER, BURST_CADENCE evaluation logic: UNCHANGED.
    PERMITTED_FLOWS: UNCHANGED.
    All v0.8 tests continue to pass.

  What this closes:
    Paper 1 claim changes from "four of five ASD invariants implemented" to
    "all five ASD invariants implemented and validated." The limitation
    acknowledged in the paper series plan is resolved.

v0.8 Additions vs v0.7.3:
  1. TIME-WINDOWED BURST CADENCE
     _timed_widths: Dict[str, List[Tuple[float, int, int]]]
       Each entry: (unix_timestamp, width_before, width_after).
     BURST_TIME_WINDOW_SECONDS = 60 (configurable; replaces event-count window).
     record_width() accepts optional timestamp (float); defaults to time.time().
     check_burst_cadence() filters to events within the time window before counting
     expansions. Required for any production deployment claim — event-count windows
     are session-length-dependent; time windows are invariant across stream rates.
     Backward compatible: _width_history retained for save/load; timed_widths is
     the live evaluation path.

  2. INVERSE ACTOR PIVOT (Windows Sysmon)
     _identity_to_guids: Dict[str, Set[str]]
       Maps identity_label -> set of all ProcessGuids seen for that identity.
     check_inverse_pivot(identity, guid): returns True when a known identity
     presents a GUID not previously registered via EventID 1 spawn chain.
     Catches PsExec re-spawn: attacker drops a new process under an existing
     process name (WIN_PROCESS:cmd) with a fresh GUID that has no spawn record.
     Fired before the standard actor_pivot check in _compile_sysmon.
     New BAS_Metrics field: InversePivot (bool).
     Gate path: InversePivot=True -> EXIT invariant (identity re-spawn without
     legitimate spawn chain is a trajectory geometry collapse).

  3. AUDITD PPID CHAIN (Linux symmetric parent-child tracking)
     _linux_spawn_reg: Dict[str, Tuple[str, str]]
       Maps child_pid -> (ppid, parent_comm).
     register_linux_spawn(pid, ppid, comm): called on execve/fork/clone/vfork
     events when both pid and ppid are present.
     check_linux_spawn_elevation(pid, ppid, child_role): looks up parent comm
     in role_table, compares to child_role using SPAWN_ROLE_HIERARCHY.
     Closes the Linux PID-reuse gap noted in v0.6: ppid chain provides lineage
     context that PID alone cannot. Symmetric with Windows EventID 1 tracking.
     New BAS_Metrics field: LinuxSpawnViolation (bool).

  4. TIMESTAMP EXTRACTION
     extract_event_timestamp(raw_log, domain): extracts wall-clock timestamp
     from CloudTrail eventTime, Sysmon UtcTime, or auditd timestamp fields.
     Returns float (Unix epoch) or None. Used by record_width() for time-windowed
     burst evaluation.

v0.7.3 Fix vs v0.7.2:
  - WebServerProcess PERMITTED_FLOWS: two corrections from ADFA-LD run.

    Fix 1 — PrivilegeChange from Executing state:
      Apache drops root privileges to www-data via setuid() immediately after
      forking worker processes (fork → setuid is the legal sequence).
      setuid maps to PrivilegeChange. This was firing JURISDICTION on 6,700+
      benign ADFA-LD events even after v0.7.2. Adding PrivilegeChange from
      Executing only (mirrors ServiceProcess pattern — idle setuid still
      fires ORDER, which is correct).

    Fix 2 — WriteData self-loop in Writing and Deleting states:
      v0.7.2 accidentally removed the WriteData→Writing self-loop, causing
      768 false ORDER fires on consecutive apache write syscalls. Restored.

    Security invariants preserved:
      PrivilegeChange from Idle/Reading still fires ORDER (unexpected priv drop)
      ModifyPermissions still not in vocabulary → JURISDICTION (chmod attacks)
      Webshell setuid from non-Executing state still fires ORDER

  - CompilerVersion tag updated to v0.7.3
  - Gate logic: ZERO changes.
Unlocks Living-off-the-Land (LotL) detection without modifying the gate.

Architecture Contract:
  - Layer 1 Execution Gate: TrajectoryTracker + five invariants (EXIT, JURISDICTION,
    ORDER, BURST_CADENCE — unchanged from v0.6 — plus HYSTERESIS added v0.9).
  - Layer 2 Dictionary: domain-specific extractors (cloudtrail / auditd / sysmon)
    feed identical BDO/BAS axes to the same gate.
  - No probabilistic/ML/fuzzy logic. Strings are law.

v0.7.1 Additions vs v0.7:
  - _spawn_registry: Dict[str, Tuple[str, str]] in TrajectoryTracker
    maps child_ProcessGuid -> (parent_basename, parent_role)
  - register_spawn(): called on every EventID 1 (ProcessCreate)
  - check_spawn_elevation(): fires if parent role < child role
    StandardUserProcess(0) < ServiceProcess(1) < AdminProcess(2)
  - extract_parent_identity(): pulls ParentImage from EventID 1
  - _compile_sysmon(): on EventID 1, registers spawn and checks elevation
    Spawn violation -> jurisdiction_violation=True -> INADMISSIBLE/JURISDICTION
  - SPAWN_ROLE_HIERARCHY: role-level lookup table for elevation check
  - CompilerVersion tag updated to v0.7.1

v0.7 Additions vs v0.6:
  - SYSMON_ACTION_MAP: 29 Sysmon EventIDs -> core vocabulary
  - SYSMON_EVENT_NAMES: EventID -> human-readable label (for State_Target)
  - detect_domain(): third branch -- "EventID" key -> windows_sysmon
  - extract_sysmon_identity(): Image -> WIN_PROCESS:{name}; User -> WIN_USER:{sid}
  - extract_sysmon_target(): per-EventID target extraction
  - extract_sysmon_source_ref(): ProcessGuid / PID for actor pivot tracking
  - resolve_sysmon_action(): EventID -> vocabulary action
  - _compile_sysmon(): full extraction -> _core_evaluate path
  - NetworkAccess: new vocabulary action, Windows roles only (additive, no gate change)
  - PERMITTED_FLOWS: three new Windows archetypes added
    StandardUserProcess, ServiceProcess, AdminProcess
  - DEFAULT_ROLE_TABLE: Windows process -> role mappings
  - VALID_ROLES / FLOW_START_STATE updated
"""

import json
import re
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class Encapsulation(Enum):
    SURFACE = "SURFACE"
    MID     = "MID"
    DEEP    = "DEEP"

class ResolutionStatus(Enum):
    FULL    = "FULL"
    PARTIAL = "PARTIAL"
    FAILED  = "FAILED"


# Burst cadence parameters
BURST_WINDOW              = 5   # legacy event-count window (retained for regression)
BURST_THRESHOLD           = 3   # expansions required to fire
BURST_TIME_WINDOW_SECONDS = 60  # v0.8: time-windowed burst window (seconds)


# =============================================================================
# CLOUDTRAIL ACTION MAPPING (unchanged from v0.6)
# =============================================================================

CLOUDTRAIL_ACTION_MAP: Dict[str, str] = {
    "ListBuckets":       "ReadData",
    "GetObject":         "ReadData",
    "DescribeInstances": "ReadData",
    "GetParameter":      "ReadData",
    "StartQuery":        "ReadData",
    "ConsoleLogin":      "ReadData",
    "AssumeRole":        "PrivilegeChange",
    "GetSessionToken":   "PrivilegeChange",
    "Invoke":            "ExecuteFunction",
    "SendCommand":       "ExecuteFunction",
    "AttachUserPolicy":              "ModifyPermissions",
    "PassRole":                      "ModifyPermissions",
    "CreateAccessKey":               "ModifyPermissions",
    "PutBucketPolicy":               "ModifyPermissions",
    "DeleteObject":                  "DeleteData",
    "DetachUserPolicy":              "ModifyPermissions",
    "DetachRolePolicy":              "ModifyPermissions",
    "AttachRolePolicy":              "ModifyPermissions",
    "AuthorizeSecurityGroupIngress": "WriteData",
    "CopySnapshot":                  "WriteData",
}

CLOUDTRAIL_PREFIX_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("Get", "List", "Describe", "Head"),                           "ReadData"),
    (("Create", "Put", "Run", "Start", "Update", "Modify",
      "Add", "Set", "Publish", "Register", "Enable", "Launch"),    "WriteData"),
    (("Delete", "Remove", "Terminate", "Stop", "Deregister"),       "DeleteData"),
    (("Invoke", "Execute"),                                         "ExecuteFunction"),
]

_VERSION_SUFFIX = re.compile(r'\d{5,}(v\d+)?$', re.IGNORECASE)

def normalize_event_name(name: str) -> str:
    cleaned = _VERSION_SUFFIX.sub("", name)
    return cleaned[0].upper() + cleaned[1:] if cleaned else cleaned

def resolve_cloudtrail_action(event_name: str) -> str:
    action = CLOUDTRAIL_ACTION_MAP.get(event_name)
    if action:
        return action
    normalized = normalize_event_name(event_name)
    action = CLOUDTRAIL_ACTION_MAP.get(normalized)
    if action:
        return action
    for prefixes, label in CLOUDTRAIL_PREFIX_RULES:
        for prefix in prefixes:
            if normalized.startswith(prefix):
                return label
    return "UNKNOWN"


# =============================================================================
# AUDITD ACTION MAPPING (unchanged from v0.6)
# =============================================================================

AUDITD_ACTION_MAP: Dict[str, str] = {
    # Reads
    "open":        "ReadData",      "2":   "ReadData",
    "openat":      "ReadData",      "257": "ReadData",
    "read":        "ReadData",      "0":   "ReadData",
    "pread64":     "ReadData",      "17":  "ReadData",
    "readv":       "ReadData",      "19":  "ReadData",
    "stat":        "ReadData",      "4":   "ReadData",
    "fstat":       "ReadData",      "5":   "ReadData",
    "lstat":       "ReadData",      "6":   "ReadData",
    "newfstatat":  "ReadData",      "262": "ReadData",
    "access":      "ReadData",      "21":  "ReadData",
    "faccessat":   "ReadData",      "269": "ReadData",
    "readlink":    "ReadData",      "89":  "ReadData",
    "readlinkat":  "ReadData",      "267": "ReadData",
    # Writes
    "write":       "WriteData",     "1":   "WriteData",
    "pwrite64":    "WriteData",     "18":  "WriteData",
    "writev":      "WriteData",     "20":  "WriteData",
    "truncate":    "WriteData",     "76":  "WriteData",
    "ftruncate":   "WriteData",     "77":  "WriteData",
    "creat":       "WriteData",     "85":  "WriteData",
    "rename":      "WriteData",     "82":  "WriteData",
    "renameat":    "WriteData",     "264": "WriteData",
    "renameat2":   "WriteData",     "316": "WriteData",
    "mkdir":       "WriteData",     "83":  "WriteData",
    "mkdirat":     "WriteData",     "258": "WriteData",
    "symlink":     "WriteData",     "88":  "WriteData",
    "symlinkat":   "WriteData",     "266": "WriteData",
    # Delete
    "unlink":      "DeleteData",    "87":  "DeleteData",
    "unlinkat":    "DeleteData",    "263": "DeleteData",
    "rmdir":       "DeleteData",    "84":  "DeleteData",
    # ModifyPermissions
    "chmod":       "ModifyPermissions","90": "ModifyPermissions",
    "fchmod":      "ModifyPermissions","91": "ModifyPermissions",
    "chown":       "ModifyPermissions","92": "ModifyPermissions",
    "lchown":      "ModifyPermissions","94": "ModifyPermissions",
    "fchownat":    "ModifyPermissions","260":"ModifyPermissions",
    "fchmodat":    "ModifyPermissions","268":"ModifyPermissions",
    # Execute
    "execve":      "ExecuteFunction","59": "ExecuteFunction",
    "execveat":    "ExecuteFunction","322":"ExecuteFunction",
    "clone":       "ExecuteFunction","56": "ExecuteFunction",
    "clone3":      "ExecuteFunction","435":"ExecuteFunction",
    "fork":        "ExecuteFunction","57": "ExecuteFunction",
    "vfork":       "ExecuteFunction","58": "ExecuteFunction",
    # Privilege
    "setuid":      "PrivilegeChange","105":"PrivilegeChange",
    "setgid":      "PrivilegeChange","106":"PrivilegeChange",
    "setreuid":    "PrivilegeChange","113":"PrivilegeChange",
    "setregid":    "PrivilegeChange","114":"PrivilegeChange",
    "setresuid":   "PrivilegeChange","117":"PrivilegeChange",
    "setresgid":   "PrivilegeChange","119":"PrivilegeChange",
    "capset":      "PrivilegeChange","126":"PrivilegeChange",
}

_O_WRONLY = 0x1
_O_RDWR   = 0x2

def decode_open_flags(raw_log: dict, syscall: str) -> str:
    flag_field = "a2" if syscall == "openat" else "a1"
    raw = raw_log.get(flag_field)
    if raw is None:
        return "ReadData"
    try:
        if isinstance(raw, str):
            flags = int(raw, 16) if raw.startswith(("0x", "0X")) else int(raw)
        else:
            flags = int(raw)
        access_mode = flags & 0x3
        return "WriteData" if access_mode in (_O_WRONLY, _O_RDWR) else "ReadData"
    except (ValueError, TypeError):
        return "ReadData"

def resolve_auditd_action(raw_log: dict) -> str:
    syscall = (raw_log.get("syscall") or "").lower().strip()
    if not syscall:
        return "UNKNOWN"
    action = AUDITD_ACTION_MAP.get(syscall)
    if action:
        if syscall in ("open", "openat"):
            return decode_open_flags(raw_log, syscall)
        return action
    return "UNKNOWN"


# =============================================================================
# SYSMON ACTION MAPPING (new in v0.7)
#
# Maps Sysmon EventIDs to the core BAS vocabulary.
# Vocabulary: ReadData | WriteData | DeleteData | ExecuteFunction |
#             PrivilegeChange | ModifyPermissions | NetworkAccess
#
# Design rationale per EventID:
#   1  ProcessCreate          -> ExecuteFunction  (new process born)
#   2  FileCreateTime         -> WriteData        (timestomping writes metadata)
#   3  NetworkConnect         -> NetworkAccess    (outbound socket)
#   4  SysmonStateChange      -> ReadData         (service heartbeat, benign read)
#   5  ProcessTerminate       -> ExecuteFunction  (process lifecycle -- scope closes)
#   6  DriverLoad             -> ExecuteFunction  (kernel module loaded)
#   7  ImageLoad              -> ExecuteFunction  (DLL injected into process space)
#   8  CreateRemoteThread     -> PrivilegeChange  (cross-process code injection) [ATTACK]
#   9  RawAccessRead          -> ReadData         (direct disk/MBR read)
#   10 ProcessAccess          -> PrivilegeChange  (OpenProcess for token theft)   [ATTACK]
#   11 FileCreate             -> WriteData        (new file written to disk)
#   12 RegistryCreateDelete   -> WriteData        (registry key created)
#   13 RegistrySetValue       -> WriteData        (registry value written)
#   14 RegistryDeleteKey      -> DeleteData       (registry key/value removed)
#   15 FileCreateStreamHash   -> WriteData        (Alternate Data Stream created)
#   16 SysmonConfigChange     -> ModifyPermissions (audit config modified)
#   17 PipeCreated            -> WriteData        (named pipe endpoint created)
#   18 PipeConnected          -> NetworkAccess    (IPC channel opened)
#   19 WmiFilter              -> ExecuteFunction  (WMI persistence filter)  [ATTACK]
#   20 WmiConsumer            -> ExecuteFunction  (WMI consumer registered) [ATTACK]
#   21 WmiBinding             -> ExecuteFunction  (WMI filter bound)        [ATTACK]
#   22 DnsQuery               -> NetworkAccess    (C2 beacon / recon indicator)
#   23 FileDelete             -> DeleteData       (file removed -- track/block)
#   24 ClipboardChange        -> ReadData         (clipboard data accessed)
#   25 ProcessTampering       -> PrivilegeChange  (hollowing/herpaderping) [ATTACK]
#   26 FileDeleteDetected     -> DeleteData       (blocked delete attempt)
#   27 FileBlockExecutable    -> ExecuteFunction  (blocked exec -- still trajectory)
#   28 FileBlockShredding     -> DeleteData       (blocked secure delete)
#   29 FileExecutableDetected -> ExecuteFunction  (executable file dropped)
# =============================================================================

SYSMON_ACTION_MAP: Dict[int, str] = {
    1:  "ExecuteFunction",   # ProcessCreate
    2:  "WriteData",         # FileCreateTime (timestomp)
    3:  "NetworkAccess",     # NetworkConnect
    4:  "ReadData",          # SysmonStateChange
    5:  "ExecuteFunction",   # ProcessTerminate
    6:  "ExecuteFunction",   # DriverLoad
    7:  "ExecuteFunction",   # ImageLoad
    8:  "PrivilegeChange",   # CreateRemoteThread  <- ATTACK INDICATOR
    9:  "ReadData",          # RawAccessRead
    10: "PrivilegeChange",   # ProcessAccess       <- ATTACK INDICATOR
    11: "WriteData",         # FileCreate
    12: "WriteData",         # RegistryCreateDelete
    13: "WriteData",         # RegistrySetValue
    14: "DeleteData",        # RegistryDeleteKey
    15: "WriteData",         # FileCreateStreamHash (ADS)
    16: "ModifyPermissions", # SysmonConfigChange
    17: "WriteData",         # PipeCreated
    18: "NetworkAccess",     # PipeConnected
    19: "ExecuteFunction",   # WmiFilter
    20: "ExecuteFunction",   # WmiConsumer
    21: "ExecuteFunction",   # WmiBinding
    22: "NetworkAccess",     # DnsQuery
    23: "DeleteData",        # FileDelete
    24: "ReadData",          # ClipboardChange
    25: "PrivilegeChange",   # ProcessTampering    <- ATTACK INDICATOR
    26: "DeleteData",        # FileDeleteDetected
    27: "ExecuteFunction",   # FileBlockExecutable
    28: "DeleteData",        # FileBlockShredding
    29: "ExecuteFunction",   # FileExecutableDetected
}

# Human-readable event names for BDO State_Target field
SYSMON_EVENT_NAMES: Dict[int, str] = {
    1:  "ProcessCreate",
    2:  "FileCreateTime",
    3:  "NetworkConnect",
    4:  "SysmonStateChange",
    5:  "ProcessTerminate",
    6:  "DriverLoad",
    7:  "ImageLoad",
    8:  "CreateRemoteThread",
    9:  "RawAccessRead",
    10: "ProcessAccess",
    11: "FileCreate",
    12: "RegistryCreateDelete",
    13: "RegistrySetValue",
    14: "RegistryDeleteKey",
    15: "FileCreateStreamHash",
    16: "SysmonConfigChange",
    17: "PipeCreated",
    18: "PipeConnected",
    19: "WmiFilter",
    20: "WmiConsumer",
    21: "WmiBinding",
    22: "DnsQuery",
    23: "FileDelete",
    24: "ClipboardChange",
    25: "ProcessTampering",
    26: "FileDeleteDetected",
    27: "FileBlockExecutable",
    28: "FileBlockShredding",
    29: "FileExecutableDetected",
}

# =============================================================================
# SPAWN ROLE HIERARCHY (new in v0.7.1)
#
# Used by check_spawn_elevation() to determine if a parent process has spawned
# a higher-privilege child. A violation means a low-privilege process is using
# a trusted Windows binary as a stepping stone -- the core LotL shape.
#
# Hierarchy:
#   StandardUserProcess (0) -- desktop apps, browsers, Office
#   ServiceProcess      (1) -- system services, LSASS, svchost
#   AdminProcess        (2) -- shells, interpreters, LOLBins
#
# Violation = child_level > parent_level
# e.g. winword(0) -> powershell(2): VIOLATION -> JURISDICTION
#      svchost(1) -> cmd(2):        VIOLATION -> JURISDICTION
#      cmd(2)    -> powershell(2):  NO violation (same level)
# =============================================================================

SPAWN_ROLE_HIERARCHY: Dict[str, int] = {
    "StandardUserProcess": 0,
    "ServiceProcess":      1,
    "AdminProcess":        2,
}

def extract_parent_identity(raw_log: dict) -> Optional[str]:
    """
    Extract the parent process basename from EventID 1 (ProcessCreate).
    Returns WIN_PROCESS:{basename} if ParentImage present, else None.
    Only meaningful on EventID 1 — other events don't carry ParentImage.
    """
    parent_image = raw_log.get("ParentImage") or ""
    if not parent_image or not isinstance(parent_image, str):
        return None
    normalized = parent_image.strip().replace("\\", "/")
    basename   = os.path.basename(normalized)
    if not basename or basename.lower() in ("", "(none)", "-"):
        return None
    name = basename.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return f"WIN_PROCESS:{name}" if name else None


def resolve_sysmon_action(raw_log: dict) -> str:
    """Resolve Sysmon EventID to BAS vocabulary action. Returns UNKNOWN if unmapped."""
    event_id_raw = raw_log.get("EventID")
    if event_id_raw is None:
        return "UNKNOWN"
    try:
        event_id = int(event_id_raw)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return SYSMON_ACTION_MAP.get(event_id, "UNKNOWN")

def extract_sysmon_identity(raw_log: dict) -> str:
    """
    Derive a stable identity label from a Sysmon JSON event.

    Priority order:
      1. Image field  -> WIN_PROCESS:{basename_no_ext}   (process executable)
      2. User field   -> WIN_USER:{domain\\username}      (account SID label)
      3. ProcessGuid  -> WIN_GUID:{guid_prefix}           (last resort)
    """
    if not isinstance(raw_log, dict):
        return UNKNOWN_IDENTITY

    # 1. Image field: "C:\\Windows\\System32\\svchost.exe" -> "WIN_PROCESS:svchost"
    image = raw_log.get("Image") or raw_log.get("image") or ""
    if image and isinstance(image, str) and image.strip():
        normalized = image.strip().replace("\\", "/")
        basename   = os.path.basename(normalized)
        if basename and basename.lower() not in ("", "(none)", "-"):
            name = basename.lower()
            if name.endswith(".exe"):
                name = name[:-4]
            if name:
                return f"WIN_PROCESS:{name}"

    # 2. User field: "DESKTOP-ABC\\john" or "NT AUTHORITY\\SYSTEM"
    user = raw_log.get("User") or raw_log.get("user") or ""
    if user and isinstance(user, str):
        user = user.strip()
        if user and user not in ("-", "N/A", "NULL", ""):
            return f"WIN_USER:{user}"

    # 3. ProcessGuid as last-resort anchor
    pguid = raw_log.get("ProcessGuid") or raw_log.get("SourceProcessGuid") or ""
    if pguid and isinstance(pguid, str):
        pguid = pguid.strip()
        null_guid = "{00000000-0000-0000-0000-000000000000}"
        if pguid and pguid != null_guid:
            return f"WIN_GUID:{pguid[:18]}"

    return UNKNOWN_IDENTITY

def extract_sysmon_target(raw_log: dict, event_id: int) -> str:
    """
    Derive a meaningful target reference from a Sysmon event.
    Used as BDO Intentional.State_Target (the 'what was acted upon').
    """
    # Network events: destination endpoint
    if event_id == 3:
        dst_ip   = raw_log.get("DestinationIp") or raw_log.get("DestinationHostname") or ""
        dst_port = raw_log.get("DestinationPort") or ""
        if dst_ip:
            return f"{dst_ip}:{dst_port}" if dst_port else str(dst_ip)

    # DNS query: queried hostname
    if event_id == 22:
        return raw_log.get("QueryName") or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

    # File operations: target path
    if event_id in (2, 11, 15, 23, 26, 27, 28, 29):
        return raw_log.get("TargetFilename") or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

    # Registry operations: key/value path
    if event_id in (12, 13, 14):
        return raw_log.get("TargetObject") or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

    # Remote thread / process access: target process image
    if event_id in (8, 10):
        return raw_log.get("TargetImage") or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

    # Process creation: command line (richest signal)
    if event_id == 1:
        return raw_log.get("CommandLine") or raw_log.get("Image") or "ProcessCreate"

    # Driver / image load: loaded module path
    if event_id in (6, 7):
        return (raw_log.get("ImageLoaded") or raw_log.get("Image")
                or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}"))

    # Pipe events: pipe name
    if event_id in (17, 18):
        return raw_log.get("PipeName") or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

    # WMI events: filter/consumer name
    if event_id in (19, 20, 21):
        return (raw_log.get("Name") or raw_log.get("Consumer")
                or SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}"))

    return SYSMON_EVENT_NAMES.get(event_id, f"EventID:{event_id}")

def extract_sysmon_source_ref(raw_log: dict) -> str:
    """
    Extract a stable source reference for actor pivot detection.
    ProcessGuid is the preferred anchor -- stable within one process lifetime.
    Falls back to PID string.
    """
    pguid = raw_log.get("ProcessGuid") or ""
    if pguid and isinstance(pguid, str) and pguid.strip():
        null_guid = "{00000000-0000-0000-0000-000000000000}"
        if pguid.strip() != null_guid:
            return pguid.strip()
    pid = (raw_log.get("ProcessId") or raw_log.get("ProcessID")
           or raw_log.get("pid") or "UNKNOWN")
    return f"PID:{pid}"


# =============================================================================
# TIMESTAMP EXTRACTION (new in v0.8)
# =============================================================================

_CT_TIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S",
]

def extract_event_timestamp(raw_log: dict, domain: str) -> Optional[float]:
    """
    Extract wall-clock event timestamp as Unix epoch float.
    Returns None if no parseable timestamp found — callers default to time.time().

    CloudTrail:    raw_log["eventTime"]  e.g. "2024-03-15T12:34:56Z"
    Sysmon:        raw_log["UtcTime"]    e.g. "2024-03-15 12:34:56.123"
    auditd:        raw_log["timestamp"]  numeric string or float
    """
    raw: Optional[str] = None

    if domain == "cloudtrail":
        raw = raw_log.get("eventTime")
    elif domain == "windows_sysmon":
        raw = raw_log.get("UtcTime") or raw_log.get("EventTime")
    elif domain == "auditd":
        ts = raw_log.get("timestamp")
        if ts is not None:
            try:
                return float(str(ts).split(":")[0].strip())
            except (ValueError, TypeError):
                pass
        return None

    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip().replace("T", " ").rstrip("Z")
    for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


# =============================================================================
# DOMAIN DETECTION (updated for v0.7 -- three branches)
# =============================================================================

def detect_domain(raw_log: dict) -> str:
    if not isinstance(raw_log, dict):
        return "unknown"
    # CloudTrail checked first: "userIdentity" and "eventName" are CF-unique
    if "userIdentity" in raw_log or "eventName" in raw_log:
        return "cloudtrail"
    # Linux auditd: "syscall" key is auditd-specific
    if "syscall" in raw_log:
        return "auditd"
    # Windows Sysmon/EVTX: "EventID" integer key (1-29 for Sysmon)
    if "EventID" in raw_log:
        return "windows_sysmon"
    return "unknown"


# =============================================================================
# PERMITTED FLOWS (v0.7: CloudTrail + Linux + Windows archetypes)
#
# GATE CONTRACT (immutable): PERMITTED_FLOWS is a dictionary layer only.
# The gate reads it; it does not contain gate logic. Adding new roles/actions
# here is purely additive and does NOT change invariant evaluation.
#
# WINDOWS ARCHETYPE DESIGN:
#
# StandardUserProcess (explorer.exe, chrome.exe, office apps):
#   - Permitted: ReadData, WriteData, ExecuteFunction, NetworkAccess
#   - PROHIBITED: PrivilegeChange, ModifyPermissions, DeleteData
#   - Gate fires JURISDICTION if any excluded action appears
#   - Detects: LOLBin abuse (office spawning cmd), ADS creation, browser DL+exec
#
# ServiceProcess (svchost.exe, lsass.exe, winlogon.exe, csrss.exe):
#   - Permitted: same as Standard + PrivilegeChange (token ops are expected)
#   - PROHIBITED: ModifyPermissions, DeleteData
#   - PrivilegeChange permitted only from Executing state (ORDER enforcement)
#   - Detects: credential dumping chains, svchost->cmd spawn, service DLL injection
#
# AdminProcess (cmd.exe, powershell.exe, SYSTEM, all LOLBins):
#   - Full vocabulary: all seven actions permitted from all states
#   - Gate focuses on ORDER (trajectory sequencing) and BURST_CADENCE (oscillation)
#   - Detects: recon bursts (Read*N->Exec->Network), staged drops (Exec->Write->Exec),
#     token theft chains (Pivot->Exec->Network->Write), certutil download cradles
# =============================================================================

PERMITTED_FLOWS: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {

    # ----- CloudTrail roles (unchanged from v0.6) --------------------------------

    "ReadOnlyUser": {
        "Idle":    {"ReadData": ("Reading", Encapsulation.SURFACE.value)},
        "Reading": {"ReadData": ("Reading", Encapsulation.SURFACE.value)},
    },

    "DevRole": {
        "Idle": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":  ("Reading", Encapsulation.SURFACE.value),
            "WriteData": ("Writing", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
    },

    "AdminRole": {
        "Idle": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.SURFACE.value),
            "PrivilegeChange": ("Pivoting",  Encapsulation.SURFACE.value),
            "DeleteData":      ("Deleting",  Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":          ("Reading",        Encapsulation.SURFACE.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
        },
        "ModifyingPerms": {
            "ReadData":  ("Reading", Encapsulation.MID.value),
            "WriteData": ("Writing", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.MID.value),
        },
        "Pivoting": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Deleting": {
            "ReadData":  ("Reading", Encapsulation.MID.value),
            "WriteData": ("Writing", Encapsulation.MID.value),
        },
        "PivotPending": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
    },

    # ----- Linux roles (unchanged from v0.6) -------------------------------------

    # WebServerProcess — apache2, nginx, httpd, php-cgi
    # v0.7.3: two corrections from ADFA-LD benchmark run.
    #
    # Permitted:  ReadData, WriteData, ExecuteFunction, PrivilegeChange, DeleteData
    # Prohibited: ModifyPermissions (chmod/chown attacks still fire JURISDICTION)
    #
    # PrivilegeChange from Executing only:
    #   Apache forks (ExecuteFunction -> Executing), then drops root via setuid
    #   (PrivilegeChange from Executing -> Pivoting). Normal Apache worker init.
    #   setuid from Idle/Reading still fires ORDER — correct behavior.
    #
    # WriteData self-loop restored in Writing/Deleting:
    #   Consecutive write syscalls are normal (log writes, response bodies).
    #   v0.7.2 accidentally dropped this, causing 768 false ORDER fires.
    "WebServerProcess": {
        "Idle": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "DeleteData":      ("Deleting",  Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "PrivilegeChange": ("Pivoting",  Encapsulation.MID.value),
        },
        "Pivoting": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Deleting": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
        },
    },

    "DatabaseProcess": {
        "Idle": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":  ("Reading",   Encapsulation.MID.value),
            "WriteData": ("Writing",   Encapsulation.MID.value),
        },
    },

    "UserShell": {
        "Idle": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing", Encapsulation.SURFACE.value),
            "DeleteData":      ("Deleting",  Encapsulation.SURFACE.value),
            "PrivilegeChange": ("Pivoting",  Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",   Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "DeleteData":      ("Deleting",  Encapsulation.MID.value),
            "PrivilegeChange": ("Pivoting",  Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "DeleteData":      ("Deleting",  Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":   ("Reading",  Encapsulation.MID.value),
            "WriteData":  ("Writing",  Encapsulation.MID.value),
            "DeleteData": ("Deleting", Encapsulation.MID.value),
        },
        "Deleting": {
            "ReadData":  ("Reading", Encapsulation.MID.value),
            "WriteData": ("Writing", Encapsulation.MID.value),
        },
        "Pivoting": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
    },

    # ----- Windows archetypes (new in v0.7) ---------------------------------------

    # StandardUserProcess -- explorer.exe, chrome.exe, notepad.exe, Office apps
    # Permitted:  ReadData | WriteData | ExecuteFunction | NetworkAccess
    # Prohibited: PrivilegeChange | ModifyPermissions | DeleteData
    # Gate fires JURISDICTION on EventID 8, 10, 16, 25 from these identities.
    "StandardUserProcess": {
        "Idle": {
            "ReadData":        ("Reading",    Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing",  Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",    Encapsulation.SURFACE.value),
            "NetworkAccess":   ("Networking", Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",    Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing",  Encapsulation.MID.value),
            "WriteData":       ("Writing",    Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":      ("Reading",    Encapsulation.MID.value),
            "WriteData":     ("Writing",    Encapsulation.MID.value),
            "NetworkAccess": ("Networking", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":        ("Reading",    Encapsulation.MID.value),
            "ExecuteFunction": ("Executing",  Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
        },
        "Networking": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
    },

    # ServiceProcess -- svchost.exe, lsass.exe, winlogon.exe, csrss.exe
    # Permitted:  ReadData | WriteData | ExecuteFunction | NetworkAccess | PrivilegeChange
    # Prohibited: ModifyPermissions | DeleteData
    # PrivilegeChange only permitted from Executing state (ORDER enforcement):
    #   idle svchost->PrivilegeChange fires ORDER; only exec->PrivilegeChange is legal.
    # Gate fires JURISDICTION on ModifyPermissions or DeleteData from these identities.
    "ServiceProcess": {
        "Idle": {
            "ReadData":        ("Reading",    Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing",  Encapsulation.SURFACE.value),
            "WriteData":       ("Writing",    Encapsulation.SURFACE.value),
            "NetworkAccess":   ("Networking", Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":        ("Reading",    Encapsulation.SURFACE.value),
            "ExecuteFunction": ("Executing",  Encapsulation.MID.value),
            "WriteData":       ("Writing",    Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":        ("Reading",    Encapsulation.MID.value),
            "WriteData":       ("Writing",    Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
            "PrivilegeChange": ("Pivoting",   Encapsulation.MID.value),  # token ops
        },
        "Writing": {
            "ReadData":        ("Reading",    Encapsulation.MID.value),
            "ExecuteFunction": ("Executing",  Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
        },
        "Networking": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
        "Pivoting": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
        },
    },

    # AdminProcess -- cmd.exe, powershell.exe, SYSTEM, all LOLBins
    # Full vocabulary: all seven actions permitted from all states.
    # Gate enforces ORDER (trajectory sequencing) and BURST_CADENCE (oscillation rate).
    # Key detection patterns:
    #   Recon burst:     Read*N -> Execute -> NetworkAccess in tight window (BURST)
    #   Staged drop:     Execute -> Write -> Execute without Read (ORDER)
    #   Token theft:     Pivot -> Execute -> NetworkAccess -> Write (ORDER shape)
    #   Certutil cradle: NetworkAccess -> Write -> Execute in sequence (BURST on repeat)
    "AdminProcess": {
        "Idle": {
            "ReadData":          ("Reading",        Encapsulation.SURFACE.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.SURFACE.value),
            "WriteData":         ("Writing",        Encapsulation.SURFACE.value),
            "NetworkAccess":     ("Networking",     Encapsulation.SURFACE.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.SURFACE.value),
            "DeleteData":        ("Deleting",       Encapsulation.SURFACE.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.SURFACE.value),
        },
        "Reading": {
            "ReadData":          ("Reading",        Encapsulation.SURFACE.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "NetworkAccess":     ("Networking",     Encapsulation.MID.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
        },
        "Executing": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "NetworkAccess":     ("Networking",     Encapsulation.MID.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
        },
        "Writing": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "NetworkAccess":     ("Networking",     Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
        },
        "Networking": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "NetworkAccess":     ("Networking",     Encapsulation.MID.value),
            "PrivilegeChange":   ("Pivoting",       Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
        },
        "Pivoting": {
            "ReadData":          ("Reading",        Encapsulation.MID.value),
            "ExecuteFunction":   ("Executing",      Encapsulation.MID.value),
            "WriteData":         ("Writing",        Encapsulation.MID.value),
            "NetworkAccess":     ("Networking",     Encapsulation.MID.value),
            "ModifyPermissions": ("ModifyingPerms", Encapsulation.MID.value),
            "DeleteData":        ("Deleting",       Encapsulation.MID.value),
        },
        "Deleting": {
            "ReadData":        ("Reading",    Encapsulation.MID.value),
            "WriteData":       ("Writing",    Encapsulation.MID.value),
            "ExecuteFunction": ("Executing",  Encapsulation.MID.value),
            "NetworkAccess":   ("Networking", Encapsulation.MID.value),
        },
        "ModifyingPerms": {
            "ReadData":        ("Reading",   Encapsulation.MID.value),
            "WriteData":       ("Writing",   Encapsulation.MID.value),
            "ExecuteFunction": ("Executing", Encapsulation.MID.value),
        },
    },
}

FLOW_START_STATE: Dict[str, str] = {
    # CloudTrail
    "ReadOnlyUser":        "Idle",
    "DevRole":             "Idle",
    "AdminRole":           "Idle",
    # Linux
    "WebServerProcess":    "Idle",
    "DatabaseProcess":     "Idle",
    "UserShell":           "Idle",
    # Windows (new v0.7)
    "StandardUserProcess": "Idle",
    "ServiceProcess":      "Idle",
    "AdminProcess":        "Idle",
}

VALID_ROLES = {
    # CloudTrail
    "ReadOnlyUser", "DevRole", "AdminRole",
    # Linux
    "WebServerProcess", "DatabaseProcess", "UserShell",
    # Windows
    "StandardUserProcess", "ServiceProcess", "AdminProcess",
}


# =============================================================================
# ROLE TABLE & RESOLUTION
# =============================================================================

DEFAULT_ROLE_TABLE: Dict[str, str] = {
    # -- CloudTrail (unchanged from v0.6) -----------------------------------------
    "IAM_USER:audit_service":      "ReadOnlyUser",
    "IAM_USER:dev_worker":         "DevRole",
    "IAM_USER:dev_builder":        "DevRole",
    "IAM_USER:admin_deploy":       "AdminRole",
    "IAM_USER:admin_pivot":        "AdminRole",
    "IAM_USER:ROOT":               "AdminRole",
    "IAM_ROLE:dev_role":           "DevRole",
    "IAM_ROLE:admin_deploy":       "AdminRole",
    "AWS_SERVICE:SYSTEM":          "DevRole",
    "IAM_USER:user_alpha":         "ReadOnlyUser",
    "IAM_USER:user_beta":          "ReadOnlyUser",
    "IAM_USER:clean_user":         "ReadOnlyUser",
    "IAM_USER:attacker_user":      "ReadOnlyUser",
    "IAM_USER:slow_attacker":      "ReadOnlyUser",
    "IAM_USER:compromised_guest":  "ReadOnlyUser",
    "IAM_USER:pivot_attacker":     "ReadOnlyUser",
    "IAM_USER:burst_attacker":     "DevRole",
    "IAM_USER:temp_credential":    "ReadOnlyUser",
    "IAM_USER:user_alice":         "ReadOnlyUser",
    "IAM_USER:user_bob":           "ReadOnlyUser",
    "IAM_USER:arn_pivot_attacker": "ReadOnlyUser",
    "IAM_USER:prod_service":       "DevRole",
    # -- Linux (unchanged from v0.6) ----------------------------------------------
    "PROCESS:nginx":               "WebServerProcess",
    "PROCESS:apache2":             "WebServerProcess",
    "PROCESS:httpd":               "WebServerProcess",
    "PROCESS:mysqld":              "DatabaseProcess",
    "PROCESS:postgres":            "DatabaseProcess",
    "PROCESS:bash":                "UserShell",
    "PROCESS:sh":                  "UserShell",
    "LINUX_USER:0":                "UserShell",
    "LINUX_USER:1000":             "UserShell",
    # -- Windows: Standard user processes -----------------------------------------
    # Low-privilege GUI / desktop apps.
    # Expected to Read/Write/Execute/Network.
    # PrivilegeChange or ModifyPermissions -> JURISDICTION violation.
    "WIN_PROCESS:explorer":        "StandardUserProcess",
    "WIN_PROCESS:chrome":          "StandardUserProcess",
    "WIN_PROCESS:firefox":         "StandardUserProcess",
    "WIN_PROCESS:msedge":          "StandardUserProcess",
    "WIN_PROCESS:iexplore":        "StandardUserProcess",
    "WIN_PROCESS:notepad":         "StandardUserProcess",
    "WIN_PROCESS:wordpad":         "StandardUserProcess",
    "WIN_PROCESS:mspaint":         "StandardUserProcess",
    "WIN_PROCESS:calc":            "StandardUserProcess",
    "WIN_PROCESS:winword":         "StandardUserProcess",
    "WIN_PROCESS:excel":           "StandardUserProcess",
    "WIN_PROCESS:powerpnt":        "StandardUserProcess",
    "WIN_PROCESS:outlook":         "StandardUserProcess",
    "WIN_PROCESS:teams":           "StandardUserProcess",
    "WIN_PROCESS:slack":           "StandardUserProcess",
    "WIN_PROCESS:onedrive":        "StandardUserProcess",
    "WIN_PROCESS:taskmgr":         "StandardUserProcess",
    # -- Windows: Service processes -----------------------------------------------
    # Privileged background services.
    # PrivilegeChange expected (token ops); ModifyPermissions/DeleteData -> JURISDICTION.
    "WIN_PROCESS:svchost":         "ServiceProcess",
    "WIN_PROCESS:services":        "ServiceProcess",
    "WIN_PROCESS:lsass":           "ServiceProcess",
    "WIN_PROCESS:winlogon":        "ServiceProcess",
    "WIN_PROCESS:wininit":         "ServiceProcess",
    "WIN_PROCESS:csrss":           "ServiceProcess",
    "WIN_PROCESS:smss":            "ServiceProcess",
    "WIN_PROCESS:spoolsv":         "ServiceProcess",
    "WIN_PROCESS:taskhost":        "ServiceProcess",
    "WIN_PROCESS:taskhostw":       "ServiceProcess",
    "WIN_PROCESS:searchindexer":   "ServiceProcess",
    "WIN_PROCESS:msdtc":           "ServiceProcess",
    "WIN_PROCESS:dllhost":         "ServiceProcess",
    # -- Windows: Admin / LOLBin processes ----------------------------------------
    # Full vocabulary permitted. Gate enforces ORDER and BURST shape.
    # High-value attack primitives -- any trajectory anomaly is signal.
    "WIN_PROCESS:cmd":             "AdminProcess",
    "WIN_PROCESS:powershell":      "AdminProcess",
    "WIN_PROCESS:pwsh":            "AdminProcess",
    "WIN_PROCESS:mshta":           "AdminProcess",
    "WIN_PROCESS:wscript":         "AdminProcess",
    "WIN_PROCESS:cscript":         "AdminProcess",
    "WIN_PROCESS:rundll32":        "AdminProcess",
    "WIN_PROCESS:regsvr32":        "AdminProcess",
    "WIN_PROCESS:msiexec":         "AdminProcess",
    "WIN_PROCESS:wmic":            "AdminProcess",
    "WIN_PROCESS:net":             "AdminProcess",
    "WIN_PROCESS:net1":            "AdminProcess",
    "WIN_PROCESS:netsh":           "AdminProcess",
    "WIN_PROCESS:reg":             "AdminProcess",
    "WIN_PROCESS:sc":              "AdminProcess",
    "WIN_PROCESS:certutil":        "AdminProcess",
    "WIN_PROCESS:bitsadmin":       "AdminProcess",
    "WIN_PROCESS:forfiles":        "AdminProcess",
    "WIN_PROCESS:at":              "AdminProcess",
    "WIN_PROCESS:schtasks":        "AdminProcess",
    "WIN_PROCESS:eventvwr":        "AdminProcess",
    "WIN_PROCESS:ftp":             "AdminProcess",
    # -- Windows: SID-based identity mapping --------------------------------------
    "WIN_USER:NT AUTHORITY\\SYSTEM":          "AdminProcess",
    "WIN_USER:NT AUTHORITY\\NETWORK SERVICE": "ServiceProcess",
    "WIN_USER:NT AUTHORITY\\LOCAL SERVICE":   "ServiceProcess",
}

def load_role_table(path: Optional[str]) -> Dict[str, str]:
    table = dict(DEFAULT_ROLE_TABLE)
    if not path:
        return table
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str) and v in VALID_ROLES:
                    table[k] = v
    except (FileNotFoundError, IOError, json.JSONDecodeError):
        pass
    return table


# =============================================================================
# IDENTITY & SESSION EXTRACTION (CloudTrail / auditd -- unchanged from v0.6)
# =============================================================================

EMPTY_IDENTITY   = "EMPTY_IDENTITY"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"

def extract_identity_label(user_identity: Any) -> str:
    if not isinstance(user_identity, dict):
        return UNKNOWN_IDENTITY
    id_type = user_identity.get("type", "UNKNOWN")
    if id_type == "IAMUser":
        name = user_identity.get("userName")
        if not name or not str(name).strip():
            return EMPTY_IDENTITY
        return f"IAM_USER:{name}"
    if id_type == "AssumedRole":
        try:
            name = user_identity["sessionContext"]["sessionIssuer"]["userName"]
            if not name or not str(name).strip():
                return EMPTY_IDENTITY
            return f"IAM_ROLE:{name}"
        except (KeyError, TypeError):
            return UNKNOWN_IDENTITY
    if id_type == "AWSService":
        return "AWS_SERVICE:SYSTEM"
    if id_type == "Root":
        return "IAM_USER:ROOT"
    return UNKNOWN_IDENTITY

def extract_session_arn(user_identity: Any) -> Optional[str]:
    if not isinstance(user_identity, dict):
        return None
    arn = user_identity.get("arn")
    if arn and isinstance(arn, str) and arn.startswith("arn:"):
        return arn
    try:
        arn = user_identity["sessionContext"]["sessionIssuer"]["arn"]
        if arn and isinstance(arn, str) and arn.startswith("arn:"):
            return arn
    except (KeyError, TypeError):
        pass
    return None

def extract_auditd_identity(raw_log: dict) -> str:
    if not isinstance(raw_log, dict):
        return UNKNOWN_IDENTITY
    exe = raw_log.get("exe")
    if exe and isinstance(exe, str) and exe.strip() and exe != "(none)":
        basename = os.path.basename(exe.strip())
        if basename:
            return f"PROCESS:{basename}"
    uid = raw_log.get("uid")
    if uid is not None and str(uid).strip() not in ("", "-1", "4294967295"):
        return f"LINUX_USER:{str(uid).strip()}"
    return UNKNOWN_IDENTITY


# =============================================================================
# TRAJECTORY TRACKER (gate logic locked from v0.6; v0.9 adds Hysteresis invariant)
# =============================================================================

class TrajectoryTracker:
    def __init__(self) -> None:
        self._states:          Dict[Tuple[str, str], str]             = {}
        self._history:         Dict[Tuple[str, str], list]            = {}
        self._role_registry:   Dict[str, str]                         = {}
        self._ip_to_identity:  Dict[str, str]                         = {}
        self._arn_to_identity: Dict[str, str]                         = {}
        self._width_history:   Dict[str, List[Tuple[int, int]]]       = {}
        # v0.7.1: parent-child spawn registry (Windows)
        self._spawn_registry:  Dict[str, Tuple[str, str]]             = {}
        # v0.8: inverse actor pivot — identity -> set of registered GUIDs
        self._identity_to_guids: Dict[str, Set[str]]                  = {}
        # v0.8: Linux ppid chain — child_pid -> (ppid, parent_comm)
        self._linux_spawn_reg:   Dict[str, Tuple[str, str]]           = {}
        # v0.8: Linux pid -> comm registry (populated from any auditd event)
        self._linux_pid_comm:    Dict[str, str]                        = {}
        # v0.8: time-windowed burst — identity -> [(unix_ts, w_before, w_after)]
        self._timed_widths:      Dict[str, List[Tuple[float, int, int]]] = {}
        # v0.9: Hysteresis — violation flag per identity
        self._violation_history: Dict[str, bool]                          = {}
        # v0.9: Hysteresis — states reached via admissible transitions per (identity, role)
        self._visited_states:    Dict[Tuple[str, str], Set[str]]          = {}

    def _key(self, identity: str, role: str) -> Tuple[str, str]:
        return (identity, role)

    def check_role_confusion(self, identity: str, role: str) -> bool:
        if identity in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            return False
        prior = self._role_registry.get(identity)
        if prior is None:
            self._role_registry[identity] = role
            return False
        return prior != role

    def check_actor_pivot(self, identity: str, source_ref: str,
                          session_arn: Optional[str] = None) -> bool:
        if identity in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            return False
        if session_arn:
            prior = self._arn_to_identity.get(session_arn)
            if prior is None:
                self._arn_to_identity[session_arn] = identity
                return False
            return prior != identity
        else:
            if not source_ref or source_ref in ("UNKNOWN", "0", ""):
                return False
            prior = self._ip_to_identity.get(source_ref)
            if prior is None:
                self._ip_to_identity[source_ref] = identity
                return False
            return prior != identity

    def current_state(self, identity: str, role: str) -> str:
        return self._states.get(self._key(identity, role),
                                FLOW_START_STATE.get(role, "Idle"))

    def width_at_current_state(self, identity: str, role: str) -> int:
        state       = self.current_state(identity, role)
        role_flows  = PERMITTED_FLOWS.get(role, {})
        state_flows = role_flows.get(state, {})
        return len(state_flows)

    def evaluate(self, identity: str, role: str, action: str) -> dict:
        key          = self._key(identity, role)
        from_state   = self.current_state(identity, role)
        role_flows   = PERMITTED_FLOWS.get(role, {})
        state_flows  = role_flows.get(from_state, {})
        width_before = len(state_flows)
        action_in_role = any(action in s for s in role_flows.values())

        if action in state_flows:
            to_state, enc = state_flows[action]
            self._states[key] = to_state
            next_flows  = role_flows.get(to_state, {})
            width_after = len(next_flows)
            if key not in self._history:
                self._history[key] = []
            self._history[key].append((action, from_state, to_state))
            # v0.9: record visited state (admissible path only)
            if key not in self._visited_states:
                self._visited_states[key] = set()
            self._visited_states[key].add(to_state)
            return {
                "admissible":             True,
                "from_state":             from_state,
                "to_state":               to_state,
                "encapsulation":          enc,
                "width_before":           width_before,
                "width_after":            width_after,
                "exposure_event":         False,
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         False,
                "actor_pivot":            False,
            }
        else:
            # v0.9: record violation for hysteresis tracking
            self._violation_history[identity] = True
            return {
                "admissible":             False,
                "from_state":             from_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           width_before,
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        action_in_role,
                "jurisdiction_violation": not action_in_role,
                "role_confusion":         False,
                "actor_pivot":            False,
            }

    def record_width(self, identity: str, w_before: int, w_after: int,
                     timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        # Legacy event-count path (regression compatibility)
        if identity not in self._width_history:
            self._width_history[identity] = []
        self._width_history[identity].append((w_before, w_after))
        # v0.8 time-windowed path
        if identity not in self._timed_widths:
            self._timed_widths[identity] = []
        self._timed_widths[identity].append((ts, w_before, w_after))

    def check_burst_cadence(self, identity: str,
                            current_time: Optional[float] = None) -> bool:
        """
        v0.8: time-windowed burst detection.
        Counts width expansions within BURST_TIME_WINDOW_SECONDS of current_time.
        Falls back to legacy event-count window when no timed entries exist
        (e.g. synthetic test events with no timestamp).
        """
        timed = self._timed_widths.get(identity, [])
        if timed:
            now = current_time if current_time is not None else time.time()
            cutoff = now - BURST_TIME_WINDOW_SECONDS
            window = [(wb, wa) for ts, wb, wa in timed if ts >= cutoff]
            if not window:
                return False
            expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
            return expansions >= BURST_THRESHOLD
        # Legacy fallback: event-count window (synthetic tests, no timestamp)
        history = self._width_history.get(identity, [])
        window  = history[-BURST_WINDOW:]
        if len(window) < BURST_WINDOW:
            return False
        expansions = sum(1 for wb, wa in window if wa is not None and wa > wb)
        return expansions >= BURST_THRESHOLD

    # -- v0.9: Hysteresis invariant -------------------------------------------

    def check_hysteresis(self, identity: str, role: str, action: str) -> bool:
        """
        ASD Invariant 4 — Irreversibility / Hysteresis.

        Returns True when ALL three conditions hold:
          1. identity has a prior violation recorded in _violation_history
          2. (identity, role) has a non-empty _visited_states set
             (guard: an actor whose very first event was a violation has built
              no legitimate history and should not be locked out of their
              first admissible action)
          3. the action, if taken, would transition to a state NOT in
             _visited_states[(identity, role)]

        Semantics: after an irreversible violation crossing, the actor's
        admissible state space is deformed — they may revisit states they
        have already occupied, but may not expand into new territory.
        "Rollback does not restore prior state."

        Gate path: checked BEFORE tracker.evaluate() in _core_evaluate so
        the state machine does not advance when hysteresis fires.
        """
        if not self._violation_history.get(identity):
            return False   # No prior violations — clean session

        key     = self._key(identity, role)
        visited = self._visited_states.get(key)
        if not visited:
            return False   # No legitimate history yet — don't deform first action

        role_flows  = PERMITTED_FLOWS.get(role, {})
        from_state  = self.current_state(identity, role)
        state_flows = role_flows.get(from_state, {})
        if action not in state_flows:
            return False   # Already inadmissible (ORDER/JURISDICTION) — gate handles it

        to_state, _ = state_flows[action]
        return to_state not in visited

    # -- v0.7.1: Parent-child spawn tracking ----------------------------------

    def register_spawn(self, child_guid: str, parent_basename: str,
                       parent_role: str) -> None:
        """
        Record that child_guid was spawned by parent_basename with parent_role.
        Called on every EventID 1 that carries a ParentImage field.
        The registry persists for the compiler session so that subsequent
        events from the child can be correlated to its parent if needed.
        """
        if child_guid and parent_basename:
            self._spawn_registry[child_guid] = (parent_basename, parent_role)

    def check_spawn_elevation(self, child_guid: str, child_role: str) -> bool:
        """
        Returns True if the parent process spawned a higher-privilege child.
        This is the core LotL detection primitive.

        Fires when:
          StandardUserProcess(0) spawns ServiceProcess(1) or AdminProcess(2)
          ServiceProcess(1)      spawns AdminProcess(2)

        Does NOT fire:
          AdminProcess spawning AdminProcess (cmd -> powershell is normal)
          Unknown parent (no ParentImage on EventID 1 = cannot assess)

        When True -> caller sets jurisdiction_violation=True -> INADMISSIBLE/JURISDICTION
        Semantic: the parent process has no jurisdictional authority to elevate
        execution scope to a higher-privilege binary.
        """
        entry = self._spawn_registry.get(child_guid)
        if not entry:
            return False
        _, parent_role = entry
        parent_level = SPAWN_ROLE_HIERARCHY.get(parent_role, -1)
        child_level  = SPAWN_ROLE_HIERARCHY.get(child_role,  -1)
        return child_level > parent_level

    # -- v0.8: Inverse actor pivot (Windows) ----------------------------------

    def register_guid_for_identity(self, identity: str, guid: str) -> None:
        """
        Register a ProcessGuid as a known GUID for this identity.
        Called on every EventID 1 (ProcessCreate) after spawn registration.
        Builds the inverse map: identity -> set of legitimate GUIDs.
        """
        if not identity or not guid:
            return
        if identity not in self._identity_to_guids:
            self._identity_to_guids[identity] = set()
        self._identity_to_guids[identity].add(guid)

    def check_inverse_pivot(self, identity: str, guid: str) -> bool:
        """
        Inverse actor pivot: same identity, different GUID, no spawn record.

        Detects PsExec-style re-spawn:
          1. Attacker sees WIN_PROCESS:cmd is registered with GUID_A.
          2. PsExec drops a new cmd.exe process under GUID_B.
          3. GUID_B has no EventID 1 spawn record (not registered via register_spawn).
          4. WIN_PROCESS:cmd already has GUID_A registered.
          -> check_inverse_pivot returns True -> EXIT invariant.

        Does NOT fire:
          - First time an identity is seen (no prior GUIDs -> register and return False)
          - GUID already known for this identity (same process, same session)
          - GUID is in _spawn_registry (legitimate child, registered via EventID 1)
          - Identity or GUID is empty/unknown
        """
        if not identity or not guid:
            return False
        if identity in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            return False
        known_guids = self._identity_to_guids.get(identity)
        if known_guids is None:
            # First time seeing this identity — register and allow
            self._identity_to_guids[identity] = {guid}
            return False
        if guid in known_guids:
            return False
        # New GUID for known identity — check if it has a legitimate spawn record
        if guid in self._spawn_registry:
            # Legitimate child: registered via EventID 1, allow and record
            known_guids.add(guid)
            return False
        # Unregistered new GUID for known identity -> re-spawn signal
        known_guids.add(guid)
        return True

    # -- v0.8: Linux ppid chain -----------------------------------------------

    def register_linux_spawn(self, pid: str, ppid: str, comm: str) -> None:
        """
        Record Linux parent-child relationship from ppid field.
        Called on execve/fork/clone/vfork events when both pid and ppid present.
        Also records comm for this pid so parent lookups work transitively.
        """
        if pid and comm:
            self._linux_pid_comm[str(pid)] = comm
        if pid and ppid and comm:
            self._linux_spawn_reg[str(pid)] = (str(ppid), comm)

    def register_linux_comm(self, pid: str, comm: str) -> None:
        """
        Record pid -> comm mapping from any auditd event.
        Enables parent resolution even when parent hasn't done a spawn syscall.
        Called on every _compile_auditd invocation when pid and comm are present.
        """
        if pid and comm:
            self._linux_pid_comm[str(pid)] = comm

    def check_linux_spawn_elevation(self, pid: str, ppid: str,
                                    child_role: str,
                                    role_table: Dict[str, str]) -> bool:
        """
        Returns True if Linux parent process spawned a higher-privilege child.
        Symmetric with check_spawn_elevation() for Windows.

        Uses _linux_pid_comm to look up parent's process name from ppid,
        then resolves parent_role via role_table, compares privilege levels.

        Fires when:
          WebServerProcess(1) spawns UserShell(2) via execve
          DatabaseProcess(1) spawns UserShell(2) via execve

        Does NOT fire:
          Parent pid not in _linux_pid_comm (unknown parent -> no assessment)
          Parent and child at same privilege level
        """
        if not ppid or ppid in ("", "0", "UNKNOWN"):
            return False
        parent_comm = self._linux_pid_comm.get(str(ppid))
        if not parent_comm:
            return False
        parent_identity = f"PROCESS:{parent_comm}"
        parent_role = role_table.get(parent_identity)
        if not parent_role:
            return False
        linux_levels = {
            "WebServerProcess": 1,
            "DatabaseProcess":  1,
            "UserShell":        2,
        }
        parent_level = linux_levels.get(parent_role, -1)
        child_level  = linux_levels.get(child_role,  -1)
        return child_level > parent_level

    def save(self, path: str) -> None:
        data = {
            "_states":  {f"{k[0]}::{k[1]}": v for k, v in self._states.items()},
            "_history": {f"{k[0]}::{k[1]}": [[a, f, t] for a, f, t in v]
                         for k, v in self._history.items()},
            "_role_registry":    self._role_registry,
            "_ip_to_identity":   self._ip_to_identity,
            "_arn_to_identity":  self._arn_to_identity,
            "_width_history":    {k: [[wb, wa] for wb, wa in v]
                                  for k, v in self._width_history.items()},
            # v0.8
            "_identity_to_guids": {k: list(v)
                                    for k, v in self._identity_to_guids.items()},
            "_linux_spawn_reg":   self._linux_spawn_reg,
            "_linux_pid_comm":    self._linux_pid_comm,
            "_timed_widths":      {k: [[ts, wb, wa] for ts, wb, wa in v]
                                    for k, v in self._timed_widths.items()},
            # v0.9
            "_violation_history": self._violation_history,
            "_visited_states":    {f"{k[0]}::{k[1]}": list(v)
                                   for k, v in self._visited_states.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._states = {
                tuple(k.split("::", 1)): v
                for k, v in data.get("_states", {}).items()
            }
            self._history = {
                tuple(k.split("::", 1)): [tuple(e) for e in v]
                for k, v in data.get("_history", {}).items()
            }
            self._role_registry   = data.get("_role_registry",   {})
            self._ip_to_identity  = data.get("_ip_to_identity",  {})
            self._arn_to_identity = data.get("_arn_to_identity", {})
            self._width_history   = {
                k: [tuple(pair) for pair in v]
                for k, v in data.get("_width_history", {}).items()
            }
            # v0.8
            self._identity_to_guids = {
                k: set(v)
                for k, v in data.get("_identity_to_guids", {}).items()
            }
            self._linux_spawn_reg = data.get("_linux_spawn_reg", {})
            self._linux_pid_comm  = data.get("_linux_pid_comm",  {})
            self._timed_widths    = {
                k: [tuple(entry) for entry in v]
                for k, v in data.get("_timed_widths", {}).items()
            }
            # v0.9
            self._violation_history = data.get("_violation_history", {})
            self._visited_states    = {
                tuple(k.split("::", 1)): set(v)
                for k, v in data.get("_visited_states", {}).items()
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self.__init__()


# =============================================================================
# EXECUTION GATE (EXIT/JURISDICTION/ORDER/BURST_CADENCE unchanged from v0.6;
#                 HYSTERESIS added v0.9 — five invariants total)
# =============================================================================

def evaluate_gate(packet: dict) -> dict:
    """
    Layer 1 Execution Gate.  Domain-agnostic.  Five invariants in order:
    HYSTERESIS -> EXIT -> JURISDICTION -> ORDER -> BURST_CADENCE.

    HYSTERESIS is checked first in the inadmissible branch: it is a compound
    signal (requires prior violation context) and should be labelled
    specifically before falling through to the other violation types.

    Returns {decision, invariant, packet}.
    """
    bas = packet.get("BAS_Metrics", {})
    hdr = packet.get("STP_Header", {})

    # INDETERMINATE fast-path
    if hdr.get("Resolution", {}).get("Completeness") == ResolutionStatus.PARTIAL.value:
        admissible = bas.get("Admissible", False)
        if not admissible:
            return {"decision": "INDETERMINATE", "invariant": None, "packet": packet}

    admissible = bas.get("Admissible", False)

    if not admissible:
        # HYSTERESIS invariant — history deforms future admissibility (v0.9: fifth invariant)
        if bas.get("HysteresisViolation"):
            return {"decision": "INADMISSIBLE", "invariant": "HYSTERESIS",
                    "packet": packet}
        # EXIT invariant -- trajectory geometry collapse
        if bas.get("RoleConfusion") or bas.get("ActorPivot"):
            return {"decision": "INADMISSIBLE", "invariant": "EXIT", "packet": packet}
        if bas.get("ExposureEvent"):
            if bas.get("JurisdictionViolation"):
                return {"decision": "INADMISSIBLE", "invariant": "JURISDICTION",
                        "packet": packet}
            if bas.get("OrderViolation"):
                return {"decision": "INADMISSIBLE", "invariant": "ORDER",
                        "packet": packet}
            return {"decision": "INADMISSIBLE", "invariant": "EXIT", "packet": packet}
        return {"decision": "INDETERMINATE", "invariant": None, "packet": packet}

    # BURST_CADENCE invariant -- trajectory width oscillation
    if bas.get("BurstCadence"):
        return {"decision": "INADMISSIBLE", "invariant": "BURST_CADENCE",
                "packet": packet}

    return {"decision": "ADMISSIBLE", "invariant": None, "packet": packet}


# =============================================================================
# DOMAIN COMPILER
# =============================================================================

class DomainCompiler:
    def __init__(self,
                 role_table_path: Optional[str] = None,
                 state_path:      Optional[str] = None) -> None:
        self.role_table = load_role_table(role_table_path)
        self.state_path = state_path
        self.tracker    = TrajectoryTracker()
        if state_path:
            self.tracker.load(state_path)

    # -- Public entry point --------------------------------------------------------

    def compile(self, raw_log: dict) -> dict:
        if not isinstance(raw_log, dict):
            raw_log = {}
        domain = detect_domain(raw_log)
        if domain == "cloudtrail":
            return self._compile_cloudtrail(raw_log)
        elif domain == "auditd":
            return self._compile_auditd(raw_log)
        elif domain == "windows_sysmon":          # NEW in v0.7
            return self._compile_sysmon(raw_log)
        else:
            return self._compile_unknown(raw_log)

    # -- Domain-specific extractors -----------------------------------------------

    def _compile_cloudtrail(self, raw_log: dict) -> dict:
        event_name     = raw_log.get("eventName") or ""
        source_ip      = raw_log.get("sourceIPAddress") or "UNKNOWN"
        user_identity  = raw_log.get("userIdentity") or {}
        identity_label = extract_identity_label(user_identity)
        role           = self.role_table.get(identity_label, "ReadOnlyUser")
        session_arn    = extract_session_arn(user_identity)
        action         = resolve_cloudtrail_action(event_name)
        return self._core_evaluate(
            raw_log, identity_label, role, action,
            source_ip, session_arn, event_name, "cloudtrail",
        )

    def _compile_auditd(self, raw_log: dict) -> dict:
        identity_label = extract_auditd_identity(raw_log)
        role           = self.role_table.get(identity_label, "UserShell")
        action         = resolve_auditd_action(raw_log)
        syscall        = (raw_log.get("syscall") or "").lower().strip()
        pid            = str(raw_log.get("pid") or "UNKNOWN")
        ppid           = str(raw_log.get("ppid") or "")
        comm           = (raw_log.get("comm") or "").strip()

        # v0.8: register pid->comm from every event (enables parent lookups)
        if pid and pid != "UNKNOWN" and comm:
            self.tracker.register_linux_comm(pid, comm)

        # v0.8: Linux ppid chain registration and elevation check
        linux_spawn_violation = False
        if syscall in ("execve", "execveat", "fork", "vfork", "clone", "clone3"):
            if pid and ppid and comm:
                self.tracker.register_linux_spawn(pid, ppid, comm)
            if ppid and ppid not in ("", "0", "UNKNOWN"):
                linux_spawn_violation = self.tracker.check_linux_spawn_elevation(
                    pid, ppid, role, self.role_table
                )

        if linux_spawn_violation:
            cur_state = self.tracker.current_state(identity_label, role)
            traj_context = {
                "admissible":             False,
                "from_state":             cur_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(identity_label, role),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": True,
                "role_confusion":         False,
                "actor_pivot":            False,
                "linux_spawn_violation":  True,
            }
            # Build packet directly for Linux spawn violation
            domain         = "auditd"
            behavior_protocol = "SYSCALL"
            source_domain     = "Linux_auditd"
            dict_version      = "auditd_v1"
            behavior_cadence  = "STEADY"
            bdo = {
                "Substrate":  {"State_Resource": pid, "Behavior_Cadence": behavior_cadence},
                "Expressive": {"State_Identity": identity_label, "State_Role": role,
                               "Behavior_Protocol": behavior_protocol},
                "Intentional": {"State_Target": syscall or "UNKNOWN",
                                "Behavior_Trajectory": action,
                                "Flow_State_Before": traj_context["from_state"],
                                "Flow_State_After": None},
            }
            bas_metrics = {
                "Width_Before":          traj_context["width_before"],
                "Width_After":           None,
                "Encapsulation":         traj_context["encapsulation"],
                "Admissible":            False,
                "ExposureEvent":         True,
                "OrderViolation":        False,
                "JurisdictionViolation": True,
                "RoleConfusion":         False,
                "ActorPivot":            False,
                "BurstCadence":          False,
                "LinuxSpawnViolation":   True,
            }
            raw_str = json.dumps(raw_log, sort_keys=True, default=str)
            bdo_str = json.dumps(bdo, sort_keys=True, default=str)
            packet = {
                "STP_Header": {
                    "TransactionID":  f"req-{hashlib.md5(raw_str.encode()).hexdigest()[:8]}",
                    "Timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "SourceDomain":   source_domain,
                    "Lineage": {
                        "CompilerVersion":   "v0.9",
                        "DictionaryVersion": dict_version,
                        "RawInputHash":      f"sha256:{hashlib.sha256(raw_str.encode()).hexdigest()}",
                        "BDOHash":           f"sha256:{hashlib.sha256(bdo_str.encode()).hexdigest()}",
                    },
                    "Resolution": {"Completeness": ResolutionStatus.FULL.value, "MissingAxes": []},
                },
                "BDO_Geometry": bdo,
                "BAS_Metrics":  bas_metrics,
            }
            if self.state_path:
                self.tracker.save(self.state_path)
            return packet

        return self._core_evaluate(
            raw_log, identity_label, role, action,
            pid, None, syscall or "UNKNOWN", "auditd",
        )

    def _compile_sysmon(self, raw_log: dict) -> dict:
        """
        Windows Sysmon / EVTX extraction path (v0.7.1 — with parent tracking).

        Identity:      WIN_PROCESS:{exe_basename} | WIN_USER:{domain\\user}
        Role:          looked up in DEFAULT_ROLE_TABLE; fallback = StandardUserProcess
        Action:        SYSMON_ACTION_MAP[EventID]
        Source ref:    ProcessGuid (stable across events for the same process instance)
        Event ref:     per-EventID target string (filename, IP, registry key, etc.)
        Session anchor: ProcessGuid reused as ARN-equivalent for actor-pivot detection

        v0.7.1 addition — EventID 1 (ProcessCreate) parent tracking:
          1. Extract ParentImage -> parent_identity -> parent_role
          2. Register spawn: child_guid -> (parent_basename, parent_role)
          3. check_spawn_elevation: if parent_role < child_role -> JURISDICTION violation
             (e.g. winword spawning powershell = StandardUser elevating to Admin)
             Gate fires INADMISSIBLE / JURISDICTION without knowing what either process is.
        """
        identity_label = extract_sysmon_identity(raw_log)
        role           = self.role_table.get(identity_label, "StandardUserProcess")
        action         = resolve_sysmon_action(raw_log)

        event_id_raw = raw_log.get("EventID")
        try:
            event_id = int(event_id_raw) if event_id_raw is not None else 0
        except (TypeError, ValueError):
            event_id = 0

        # ProcessGuid as stable source ref and session anchor
        pguid     = raw_log.get("ProcessGuid") or ""
        null_guid = "{00000000-0000-0000-0000-000000000000}"
        proc_guid = pguid.strip() if pguid and pguid.strip() != null_guid else ""
        source_ref     = proc_guid if proc_guid else f"PID:{raw_log.get('ProcessId', 'UNKNOWN')}"
        session_anchor = proc_guid if proc_guid else None

        # v0.7.1: Parent-child spawn tracking on EventID 1 (ProcessCreate)
        spawn_violation = False
        if event_id == 1:
            parent_identity = extract_parent_identity(raw_log)
            if parent_identity:
                parent_role    = self.role_table.get(parent_identity, "StandardUserProcess")
                parent_basename = parent_identity.split(":", 1)[-1]
                # Register this spawn for future correlation
                self.tracker.register_spawn(source_ref, parent_basename, parent_role)
                # Immediately check: did a lower-privilege parent spawn this child?
                spawn_violation = self.tracker.check_spawn_elevation(source_ref, role)
            # v0.8: register this GUID as a legitimate GUID for this identity
            if proc_guid and not spawn_violation:
                self.tracker.register_guid_for_identity(identity_label, proc_guid)

        # v0.8: Inverse actor pivot check (non-EventID-1 events only)
        # EventID 1 events are registrations; all others are checked for re-spawn.
        inverse_pivot = False
        if event_id != 1 and proc_guid and not spawn_violation:
            inverse_pivot = self.tracker.check_inverse_pivot(identity_label, proc_guid)

        event_ref = extract_sysmon_target(raw_log, event_id)

        # If spawn violation OR inverse pivot: build JURISDICTION traj_context directly.
        if spawn_violation or inverse_pivot:
            parent_identity = extract_parent_identity(raw_log) if spawn_violation else None
            parent_role_label = self.role_table.get(
                parent_identity or "", "StandardUserProcess"
            ) if parent_identity else None
            cur_state = self.tracker.current_state(identity_label, role)
            traj_context = {
                "admissible":             False,
                "from_state":             cur_state,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(identity_label, role),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": True,
                "role_confusion":         False,
                "actor_pivot":            False,
                "spawn_violation":        spawn_violation,
                "inverse_pivot":          inverse_pivot,
                "parent_role":            parent_role_label,
            }
            return self._build_packet(
                raw_log, identity_label, role, action,
                source_ref, session_anchor, event_ref,
                "windows_sysmon", traj_context,
            )

        return self._core_evaluate(
            raw_log, identity_label, role, action,
            source_ref, session_anchor, event_ref, "windows_sysmon",
        )

    def _compile_unknown(self, raw_log: dict) -> dict:
        return self._core_evaluate(
            raw_log, UNKNOWN_IDENTITY, "ReadOnlyUser", "UNKNOWN",
            "UNKNOWN", None, "UNKNOWN", "unknown",
        )

    # -- Spawn-violation fast path (v0.7.1) -----------------------------------

    def _build_packet(self, raw_log, identity_label, role, action,
                      source_ref, session_anchor, event_ref, domain,
                      traj_context: dict) -> dict:
        """
        Build a BDO/BAS/STP packet directly from a pre-computed traj_context.
        Used by _compile_sysmon when a spawn_violation short-circuits normal
        trajectory evaluation. Shares packet construction logic with _core_evaluate.
        """
        burst_cadence    = False
        behavior_cadence = "STEADY"
        behavior_protocol = "WIN_EVENT"
        source_domain     = "Windows_Sysmon"
        dict_version      = "sysmon_v1"

        bdo = {
            "Substrate": {
                "State_Resource":   source_ref,
                "Behavior_Cadence": behavior_cadence,
            },
            "Expressive": {
                "State_Identity":    identity_label,
                "State_Role":        role,
                "Behavior_Protocol": behavior_protocol,
            },
            "Intentional": {
                "State_Target":        event_ref,
                "Behavior_Trajectory": action,
                "Flow_State_Before":   traj_context["from_state"],
                "Flow_State_After":    traj_context.get("to_state"),
            },
        }

        bas_metrics = {
            "Width_Before":          traj_context["width_before"],
            "Width_After":           traj_context.get("width_after"),
            "Encapsulation":         traj_context["encapsulation"],
            "Admissible":            traj_context["admissible"],
            "ExposureEvent":         traj_context["exposure_event"],
            "OrderViolation":        traj_context["order_violation"],
            "JurisdictionViolation": traj_context["jurisdiction_violation"],
            "RoleConfusion":         traj_context.get("role_confusion", False),
            "ActorPivot":            traj_context.get("actor_pivot", False),
            "BurstCadence":          burst_cadence,
            "SpawnViolation":        traj_context.get("spawn_violation", False),
            "ParentRole":            traj_context.get("parent_role", None),
        }

        raw_str = json.dumps(raw_log, sort_keys=True, default=str)
        bdo_str = json.dumps(bdo,     sort_keys=True, default=str)

        packet = {
            "STP_Header": {
                "TransactionID":  f"req-{hashlib.md5(raw_str.encode()).hexdigest()[:8]}",
                "Timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "SourceDomain":   source_domain,
                "Lineage": {
                    "CompilerVersion":   "v0.9",
                    "DictionaryVersion": dict_version,
                    "RawInputHash":      f"sha256:{hashlib.sha256(raw_str.encode()).hexdigest()}",
                    "BDOHash":           f"sha256:{hashlib.sha256(bdo_str.encode()).hexdigest()}",
                },
                "Resolution": {
                    "Completeness": ResolutionStatus.FULL.value,
                    "MissingAxes":  [],
                },
            },
            "BDO_Geometry": bdo,
            "BAS_Metrics":  bas_metrics,
        }

        if self.state_path:
            self.tracker.save(self.state_path)

        return packet

    # -- Shared evaluation core (UNCHANGED -- gate logic is locked) ----------------

    def _core_evaluate(self, raw_log, identity_label, role, action,
                       source_ref, session_arn, event_ref, domain):
        missing_axes = []
        resolution   = ResolutionStatus.FULL.value
        if identity_label in (UNKNOWN_IDENTITY, EMPTY_IDENTITY):
            missing_axes.append("Expressive.State_Identity")
            resolution = ResolutionStatus.PARTIAL.value
        if action == "UNKNOWN":
            missing_axes.append("Intentional.Behavior_Trajectory")
            resolution = ResolutionStatus.PARTIAL.value

        is_known       = identity_label not in (UNKNOWN_IDENTITY, EMPTY_IDENTITY)
        role_confusion = False
        actor_pivot    = False
        if action != "UNKNOWN" and is_known:
            role_confusion = self.tracker.check_role_confusion(identity_label, role)
        if not role_confusion and action != "UNKNOWN" and is_known:
            actor_pivot = self.tracker.check_actor_pivot(
                identity_label, source_ref, session_arn
            )

        if action != "UNKNOWN" and not role_confusion and not actor_pivot:
            # v0.9: Hysteresis check BEFORE state machine update.
            # If it fires, state does not advance — the actor is locked out of
            # new territory by their prior violation history.
            if self.tracker.check_hysteresis(identity_label, role, action):
                cur = self.tracker.current_state(identity_label, role)
                traj_context = {
                    "admissible":             False,
                    "from_state":             cur,
                    "to_state":               None,
                    "encapsulation":          Encapsulation.DEEP.value,
                    "width_before":           self.tracker.width_at_current_state(
                                                  identity_label, role),
                    "width_after":            None,
                    "exposure_event":         True,
                    "order_violation":        False,
                    "jurisdiction_violation": False,
                    "role_confusion":         False,
                    "actor_pivot":            False,
                    "hysteresis_violation":   True,
                }
            else:
                traj_context = self.tracker.evaluate(identity_label, role, action)
        elif role_confusion or actor_pivot:
            cur = self.tracker.current_state(identity_label, role)
            traj_context = {
                "admissible":             False,
                "from_state":             cur,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(identity_label, role),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": False,
                "role_confusion":         role_confusion,
                "actor_pivot":            actor_pivot,
            }
        else:
            cur = self.tracker.current_state(identity_label, role)
            traj_context = {
                "admissible":             False,
                "from_state":             cur,
                "to_state":               None,
                "encapsulation":          Encapsulation.DEEP.value,
                "width_before":           self.tracker.width_at_current_state(identity_label, role),
                "width_after":            None,
                "exposure_event":         True,
                "order_violation":        False,
                "jurisdiction_violation": True,
                "role_confusion":         False,
                "actor_pivot":            False,
            }
            resolution = ResolutionStatus.PARTIAL.value

        burst_cadence = False
        if traj_context.get("admissible") and traj_context.get("width_after") is not None:
            # v0.8: extract event timestamp for time-windowed burst evaluation
            event_ts = extract_event_timestamp(raw_log, domain)
            self.tracker.record_width(
                identity_label,
                traj_context["width_before"],
                traj_context["width_after"],
                timestamp=event_ts,
            )
            burst_cadence = self.tracker.check_burst_cadence(
                identity_label, current_time=event_ts
            )

        behavior_cadence = "BURST" if burst_cadence else "STEADY"

        # Domain metadata tagging
        if domain == "cloudtrail":
            behavior_protocol = "REST_HTTPS"
            source_domain     = "AWS_CloudTrail_API"
            dict_version      = "cloudtrail_v1"
        elif domain == "auditd":
            behavior_protocol = "SYSCALL"
            source_domain     = "Linux_auditd"
            dict_version      = "auditd_v1"
        elif domain == "windows_sysmon":
            behavior_protocol = "WIN_EVENT"
            source_domain     = "Windows_Sysmon"
            dict_version      = "sysmon_v1"
        else:
            behavior_protocol = "UNKNOWN"
            source_domain     = "UNKNOWN"
            dict_version      = "unknown_v0"

        bdo = {
            "Substrate": {
                "State_Resource":   source_ref,
                "Behavior_Cadence": behavior_cadence,
            },
            "Expressive": {
                "State_Identity":    identity_label,
                "State_Role":        role,
                "Behavior_Protocol": behavior_protocol,
            },
            "Intentional": {
                "State_Target":        event_ref,
                "Behavior_Trajectory": action,
                "Flow_State_Before":   traj_context["from_state"],
                "Flow_State_After":    traj_context.get("to_state"),
            },
        }

        bas_metrics = {
            "Width_Before":          traj_context["width_before"],
            "Width_After":           traj_context.get("width_after"),
            "Encapsulation":         traj_context["encapsulation"],
            "Admissible":            traj_context["admissible"],
            "ExposureEvent":         traj_context["exposure_event"],
            "OrderViolation":        traj_context["order_violation"],
            "JurisdictionViolation": traj_context["jurisdiction_violation"],
            "RoleConfusion":         traj_context.get("role_confusion", False),
            "ActorPivot":            traj_context.get("actor_pivot", False),
            "BurstCadence":          burst_cadence,
            # v0.8
            "InversePivot":          traj_context.get("inverse_pivot", False),
            "LinuxSpawnViolation":   traj_context.get("linux_spawn_violation", False),
            # v0.9
            "HysteresisViolation":   traj_context.get("hysteresis_violation", False),
        }

        raw_str = json.dumps(raw_log, sort_keys=True, default=str)
        bdo_str = json.dumps(bdo,     sort_keys=True, default=str)

        packet = {
            "STP_Header": {
                "TransactionID":  f"req-{hashlib.md5(raw_str.encode()).hexdigest()[:8]}",
                "Timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "SourceDomain":   source_domain,
                "Lineage": {
                    "CompilerVersion":   "v0.9",
                    "DictionaryVersion": dict_version,
                    "RawInputHash":      f"sha256:{hashlib.sha256(raw_str.encode()).hexdigest()}",
                    "BDOHash":           f"sha256:{hashlib.sha256(bdo_str.encode()).hexdigest()}",
                },
                "Resolution": {
                    "Completeness": resolution,
                    "MissingAxes":  missing_axes,
                },
            },
            "BDO_Geometry": bdo,
            "BAS_Metrics":  bas_metrics,
        }

        if self.state_path:
            self.tracker.save(self.state_path)

        return packet
