"""AMD Ryzen CPU Tuning, Governors, EPP, Precision Boost, SMT, and Curve Optimizer (SMU) Management."""

import glob
import json
import os
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path


RYZEN_SMU_DIR = "/sys/kernel/ryzen_smu_drv"
SMU_ARGS_PATH = os.path.join(RYZEN_SMU_DIR, "smu_args")
MP1_CMD_PATH = os.path.join(RYZEN_SMU_DIR, "mp1_smu_cmd")
CONFIG_DIR = os.path.expanduser("~/.config/amd-control-center")
CO_CACHE_FILE = os.path.join(CONFIG_DIR, "ryzen_co_profile.json")


def has_ryzen_smu() -> bool:
    """Checks if the ryzen_smu kernel driver is loaded and ready."""
    return os.path.isdir(RYZEN_SMU_DIR) and (
        os.path.exists(MP1_CMD_PATH) or os.path.exists(os.path.join(RYZEN_SMU_DIR, "version"))
    )


@dataclass
class CpuTuningProfile:
    name: str = "Balanced"
    governor: str = "powersave"
    epp: str = "balance_performance"
    boost: bool = True
    smt_enabled: bool = True
    min_freq_mhz: int = 400
    max_freq_mhz: int = 5300
    disabled_cores: List[int] = None      # Physical core IDs to disable
    co_mode: str = "All-Core"             # "All-Core" or "Per-Core"
    co_all_core: int = 0                  # Counts: -30 (max undervolt) to +10 (overvolt)
    co_per_core: Dict[str, int] = None    # {"0": -20, "1": -25, ...}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.disabled_cores is None:
            d["disabled_cores"] = []
        if self.co_per_core is None:
            d["co_per_core"] = {}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CpuTuningProfile":
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


# Preset Profiles with Curve Optimizer Offsets
PRESET_PROFILES = {
    "Balanced": CpuTuningProfile(
        name="Balanced",
        governor="powersave",
        epp="balance_performance",
        boost=True,
        smt_enabled=True,
        min_freq_mhz=400,
        max_freq_mhz=5300,
        co_mode="All-Core",
        co_all_core=0,
    ),
    "Gaming Boost": CpuTuningProfile(
        name="Gaming Boost",
        governor="performance",
        epp="performance",
        boost=True,
        smt_enabled=True,
        min_freq_mhz=3000,
        max_freq_mhz=5400,
        co_mode="All-Core",
        co_all_core=-20,  # -20 Undervolt counts for sustained boost & lower temps
    ),
    "Eco Mode": CpuTuningProfile(
        name="Eco Mode",
        governor="powersave",
        epp="power",
        boost=False,
        smt_enabled=True,
        min_freq_mhz=400,
        max_freq_mhz=3800,
        co_mode="All-Core",
        co_all_core=-30,  # Max undervolt for coolest & quietest operation
    ),
    "Pure Cores (SMT Aus)": CpuTuningProfile(
        name="Pure Cores (SMT Aus)",
        governor="performance",
        epp="performance",
        boost=True,
        smt_enabled=False,
        min_freq_mhz=2500,
        max_freq_mhz=5400,
        co_mode="All-Core",
        co_all_core=-20,
    ),
}


# --- Low-Level SMU Mailbox Communication ---

def _read_file32(path: str) -> Optional[int]:
    try:
        with open(path, "rb") as fp:
            data = fp.read(4)
        if len(data) == 4:
            return struct.unpack("<I", data)[0]
    except Exception:
        pass
    return None


def _write_file32(path: str, val: int) -> bool:
    try:
        with open(path, "wb") as fp:
            return fp.write(struct.pack("<I", val)) == 4
    except Exception:
        return False


def _write_file192(path: str, *values: int) -> bool:
    try:
        vals = list(values) + [0] * (6 - len(values))
        data = struct.pack("<IIIIII", *vals[:6])
        with open(path, "wb") as fp:
            return fp.write(data) == 24
    except Exception:
        return False


def _smu_command(op: int, *args: int, timeout: float = 3.0) -> bool:
    """Executes a low-level SMU operation via ryzen_smu_drv."""
    if not os.path.exists(MP1_CMD_PATH) or not os.path.exists(SMU_ARGS_PATH):
        return False

    start = time.monotonic()
    # 1. Wait for SMU ready
    while True:
        st = _read_file32(MP1_CMD_PATH)
        if st == 1:
            break
        if time.monotonic() - start > timeout:
            return False
        time.sleep(0.02)

    # 2. Write arguments and command opcode
    if not _write_file192(SMU_ARGS_PATH, *args):
        return False
    if not _write_file32(MP1_CMD_PATH, op):
        return False

    # 3. Wait for execution completion
    start = time.monotonic()
    while True:
        st = _read_file32(MP1_CMD_PATH)
        if st == 1:
            return True
        if st is not None and st != 0:
            return False
        if time.monotonic() - start > timeout:
            return False
        time.sleep(0.02)


def save_co_cache(profile: CpuTuningProfile):
    """Persists Curve Optimizer settings to local disk."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CO_CACHE_FILE, "w") as fp:
            json.dump({
                "co_mode": profile.co_mode,
                "co_all_core": profile.co_all_core,
                "co_per_core": profile.co_per_core or {}
            }, fp, indent=2)
    except Exception:
        pass


def load_co_cache() -> Optional[Dict[str, Any]]:
    """Loads cached Curve Optimizer settings."""
    if os.path.isfile(CO_CACHE_FILE):
        try:
            with open(CO_CACHE_FILE, "r") as fp:
                return json.load(fp)
        except Exception:
            pass
    return None


def apply_curve_optimizer(profile: CpuTuningProfile, core_count: int = 8) -> Tuple[bool, str]:
    """Applies Curve Optimizer offset values via ryzen_smu driver or caches them."""
    save_co_cache(profile)

    if not has_ryzen_smu():
        return True, "Curve Optimizer Profil gespeichert (Treiber 'ryzen_smu' nicht aktiv)."

    # Calculate offsets per core
    offsets: Dict[int, int] = {}
    if profile.co_mode == "All-Core":
        for i in range(core_count):
            offsets[i] = profile.co_all_core
    else:
        for i in range(core_count):
            c_str = str(i)
            offsets[i] = profile.co_per_core.get(c_str, profile.co_all_core) if profile.co_per_core else profile.co_all_core

    applied = 0
    failed = 0

    # SMU opcodes for Granite Ridge / Zen 5 (0x50 + core) and fallback
    for core_idx, offset in offsets.items():
        # Encoded as signed 32-bit integer in little-endian
        encoded = offset & 0xFFFFFFFF if offset >= 0 else ((offset + 2**32) & 0xFFFFFFFF)
        op = 0x50 + core_idx  # Granite Ridge / Zen 5 opcode
        
        ok = _smu_command(op, encoded)
        if not ok:
            # Try Vermeer / Zen 3 opcode (0x35) with packed APIC id
            arg = ((core_idx & 8) << 5 | (core_idx & 7)) << 20 | (offset & 0xFFFF)
            ok = _smu_command(0x35, arg)

        if ok:
            applied += 1
        else:
            failed += 1

    if failed == 0:
        return True, f"Curve Optimizer: Alle {applied} Kerne erfolgreich auf SMU angewendet."
    elif applied > 0:
        return True, f"Curve Optimizer: {applied} Kerne angewendet ({failed} fehlgeschlagen)."
    else:
        return False, "Curve Optimizer: SMU-Mailbox hat Befehl abgelehnt (evtl. AGESA Lock)."


# --- Main Tuning Dispatcher ---

def apply_cpu_tuning_direct(profile: CpuTuningProfile, core_count: int = 8) -> Tuple[bool, str]:
    """Applies CPU tuning and Curve Optimizer directly to sysfs. Requires write permissions."""
    errors = []
    
    # 1. Energy Performance Preference (EPP)
    if profile.epp:
        for f in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference"):
            try:
                with open(f, "w") as fp:
                    fp.write(profile.epp)
            except Exception as e:
                errors.append(f"EPP ({profile.epp}): {e}")
                break

    # 2. Scaling Governor
    if profile.governor:
        for f in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"):
            try:
                with open(f, "w") as fp:
                    fp.write(profile.governor)
            except Exception as e:
                errors.append(f"Governor ({profile.governor}): {e}")
                break

    # 3. Precision Boost
    boost_val = "1" if profile.boost else "0"
    boost_files = glob.glob("/sys/devices/system/cpu/cpufreq/boost")
    if not boost_files:
        boost_files = glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/boost")
    for bf in boost_files:
        try:
            with open(bf, "w") as fp:
                fp.write(boost_val)
        except Exception as e:
            errors.append(f"Boost: {e}")
            break

    # 4. Scaling Frequencies (Min & Max in kHz)
    if profile.min_freq_mhz > 0:
        min_khz = str(profile.min_freq_mhz * 1000)
        for f in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq"):
            try:
                with open(f, "w") as fp:
                    fp.write(min_khz)
            except Exception as e:
                errors.append(f"Min Freq: {e}")
                break

    if profile.max_freq_mhz > 0:
        max_khz = str(profile.max_freq_mhz * 1000)
        for f in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq"):
            try:
                with open(f, "w") as fp:
                    fp.write(max_khz)
            except Exception as e:
                errors.append(f"Max Freq: {e}")
                break

    # 5. SMT Control (Multi-Threading)
    smt_ctrl = "/sys/devices/system/cpu/smt/control"
    if os.path.isfile(smt_ctrl):
        try:
            target_smt = "on" if profile.smt_enabled else "off"
            with open(smt_ctrl, "w") as fp:
                fp.write(target_smt)
        except Exception as e:
            errors.append(f"SMT: {e}")

    # 6. Core Parking (Per-Core Online/Offline)
    disabled_set = set(profile.disabled_cores or [])
    for d in glob.glob("/sys/devices/system/cpu/cpu[1-9]*"):
        core_id_f = os.path.join(d, "topology", "core_id")
        online_f = os.path.join(d, "online")
        if os.path.isfile(core_id_f) and os.path.isfile(online_f):
            try:
                p_core = int(open(core_id_f).read().strip())
                target_state = "0" if p_core in disabled_set else "1"
                with open(online_f, "w") as fp:
                    fp.write(target_state)
            except Exception as e:
                pass

    # 7. Apply Curve Optimizer (SMU)
    co_ok, co_msg = apply_curve_optimizer(profile, core_count=core_count)

    if errors:
        return False, "; ".join(errors)
    return True, f"CPU Profil '{profile.name}' angewendet. {co_msg}"


def execute_cpu_tuner_pkexec(profile: CpuTuningProfile, core_count: int = 8) -> Tuple[bool, str]:
    """Applies CPU profile and Curve Optimizer using elevated privileges with pkexec."""
    payload = {
        "profile": profile.to_dict(),
        "core_count": core_count
    }
    tmp_path = "/tmp/amd_cpu_tuning_cmd.json"
    try:
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
    except Exception as e:
        return False, f"Failed to write tuning payload: {e}"

    cmd = ["pkexec", sys.executable, __file__, "--apply-json", tmp_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, res.stdout.strip()
        else:
            err = res.stderr.strip() or res.stdout.strip() or "Authorization cancelled or failed."
            return False, err
    except Exception as e:
        return False, str(e)


# Standalone runner for pkexec
if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--apply-json":
        json_file = sys.argv[2]
        if os.path.exists(json_file):
            with open(json_file, "r") as fp:
                data = json.load(fp)
            prof = CpuTuningProfile.from_dict(data["profile"])
            cc = data.get("core_count", 8)
            ok, msg = apply_cpu_tuning_direct(prof, core_count=cc)
            print(msg)
            try:
                os.remove(json_file)
            except Exception:
                pass
            sys.exit(0 if ok else 1)
