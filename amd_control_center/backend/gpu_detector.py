"""AMD GPU detection and capabilities discovery (RX 7000, RX 9000 & Legacy)."""

import glob
import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# Known Device IDs for RDNA 3 (RX 7000 Series) & RDNA 4 (RX 9000 Series)
RDNA_DATABASE = {
    # RDNA 4 (Navi 4x)
    "0x7550": {"model": "AMD Radeon RX 9070 XT", "arch": "RDNA 4 (Navi 48)", "gen": "RX 9000 Series", "fsr4": True},
    "0x7551": {"model": "AMD Radeon RX 9070", "arch": "RDNA 4 (Navi 48)", "gen": "RX 9000 Series", "fsr4": True},
    "0x7552": {"model": "AMD Radeon RX 9070 GRE", "arch": "RDNA 4 (Navi 48)", "gen": "RX 9000 Series", "fsr4": True},
    "0x7558": {"model": "AMD Radeon RX 9060 XT", "arch": "RDNA 4 (Navi 44)", "gen": "RX 9000 Series", "fsr4": True},
    "0x7559": {"model": "AMD Radeon RX 9060", "arch": "RDNA 4 (Navi 44)", "gen": "RX 9000 Series", "fsr4": True},

    # RDNA 3 (Navi 31 - High-End RX 7000)
    "0x7448": {"model": "AMD Radeon RX 7900 XTX", "arch": "RDNA 3 (Navi 31)", "gen": "RX 7000 Series", "fsr4": True},
    "0x744c": {"model": "AMD Radeon RX 7900 XT", "arch": "RDNA 3 (Navi 31)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7479": {"model": "AMD Radeon RX 7900 GRE", "arch": "RDNA 3 (Navi 31)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7449": {"model": "AMD Radeon PRO W7900", "arch": "RDNA 3 (Navi 31)", "gen": "Radeon PRO 7000", "fsr4": True},
    "0x744b": {"model": "AMD Radeon PRO W7800", "arch": "RDNA 3 (Navi 31)", "gen": "Radeon PRO 7000", "fsr4": True},
    "0x744e": {"model": "AMD Radeon RX 7900M", "arch": "RDNA 3 (Navi 31)", "gen": "RX 7000 Mobile", "fsr4": True},

    # RDNA 3 (Navi 32 - Mid-Range RX 7000)
    "0x7460": {"model": "AMD Radeon RX 7800 XT", "arch": "RDNA 3 (Navi 32)", "gen": "RX 7000 Series", "fsr4": True},
    "0x747e": {"model": "AMD Radeon RX 7800 XT", "arch": "RDNA 3 (Navi 32)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7461": {"model": "AMD Radeon RX 7700 XT", "arch": "RDNA 3 (Navi 32)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7470": {"model": "AMD Radeon RX 7800M", "arch": "RDNA 3 (Navi 32)", "gen": "RX 7000 Mobile", "fsr4": True},
    "0x7462": {"model": "AMD Radeon PRO W7700", "arch": "RDNA 3 (Navi 32)", "gen": "Radeon PRO 7000", "fsr4": True},

    # RDNA 3 (Navi 33 - Entry RX 7000)
    "0x7480": {"model": "AMD Radeon RX 7600 XT", "arch": "RDNA 3 (Navi 33)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7483": {"model": "AMD Radeon RX 7600", "arch": "RDNA 3 (Navi 33)", "gen": "RX 7000 Series", "fsr4": True},
    "0x7481": {"model": "AMD Radeon RX 7600M XT", "arch": "RDNA 3 (Navi 33)", "gen": "RX 7000 Mobile", "fsr4": True},
    "0x7482": {"model": "AMD Radeon RX 7700S", "arch": "RDNA 3 (Navi 33)", "gen": "RX 7000 Mobile", "fsr4": True},
    "0x7487": {"model": "AMD Radeon PRO W7600", "arch": "RDNA 3 (Navi 33)", "gen": "Radeon PRO 7000", "fsr4": True},
    "0x748b": {"model": "AMD Radeon PRO W7500", "arch": "RDNA 3 (Navi 33)", "gen": "Radeon PRO 7000", "fsr4": True},

    # RDNA 3 / 3.5 APUs (Phoenix, Hawk Point, Strix Point)
    "0x15bf": {"model": "AMD Radeon 780M Graphics", "arch": "RDNA 3 (Phoenix)", "gen": "Radeon 700M Series", "fsr4": True},
    "0x15c8": {"model": "AMD Radeon 760M Graphics", "arch": "RDNA 3 (Phoenix)", "gen": "Radeon 700M Series", "fsr4": True},
    "0x1900": {"model": "AMD Radeon 890M Graphics", "arch": "RDNA 3.5 (Strix Point)", "gen": "Radeon 800M Series", "fsr4": True},
    "0x1901": {"model": "AMD Radeon 880M Graphics", "arch": "RDNA 3.5 (Strix Point)", "gen": "Radeon 800M Series", "fsr4": True},
}


@dataclass
class GpuDevice:
    card_path: str
    card_name: str
    device_dir: str
    hwmon_dir: Optional[str] = None
    vendor_id: str = "0x1002"
    device_id: str = ""
    subsystem_vendor: str = ""
    subsystem_device: str = ""
    model_name: str = "AMD Radeon GPU"
    architecture: str = "RDNA"
    generation_name: str = "Radeon Series"
    supports_fsr4: bool = False
    ai_acceleration: str = "Keine"
    vbios_version: str = "Unknown"
    vram_total_mb: int = 0
    vram_vendor: str = "Unknown"
    power_cap_default_w: float = 0.0
    power_cap_min_w: float = 0.0
    power_cap_max_w: float = 0.0
    has_overdrive: bool = False
    od_sclk_min: int = 0
    od_sclk_max: int = 0
    od_mclk_min: int = 0
    od_mclk_max: int = 0
    od_vddc_offset_min: int = 0
    od_vddc_offset_max: int = 0
    power_profiles: List[str] = field(default_factory=list)


def _read_file(path: str) -> Optional[str]:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def get_gpu_info_by_device_id(device_id: str) -> Dict[str, Any]:
    dev_id = device_id.lower()
    if not dev_id.startswith("0x"):
        dev_id = "0x" + dev_id
    if dev_id in RDNA_DATABASE:
        return RDNA_DATABASE[dev_id]

    # Fallback via lspci
    try:
        out = subprocess.getoutput("lspci -nn | grep -i '0300: 1002\\|0380: 1002'")
        for line in out.splitlines():
            if dev_id.replace("0x", "") in line.lower():
                parts = line.split(":")
                if len(parts) >= 3:
                    name_part = parts[2].split("[")[0].strip()
                    if name_part.startswith("Advanced Micro Devices, Inc. [AMD/ATI]"):
                        name_part = name_part.replace("Advanced Micro Devices, Inc. [AMD/ATI]", "").strip()
                    if name_part:
                        is_rdna3 = any(x in name_part for x in ["7900", "7800", "7700", "7600", "780M", "760M"])
                        is_rdna4 = any(x in name_part for x in ["9070", "9060", "9080"])
                        arch = "RDNA 4" if is_rdna4 else ("RDNA 3" if is_rdna3 else "RDNA 2 / GCN")
                        return {
                            "model": f"AMD Radeon {name_part}",
                            "arch": arch,
                            "gen": "RX 9000 Series" if is_rdna4 else ("RX 7000 Series" if is_rdna3 else "Radeon"),
                            "fsr4": is_rdna3 or is_rdna4
                        }
    except Exception:
        pass

    return {
        "model": "AMD Radeon RX Series",
        "arch": "RDNA 3 / RDNA 4",
        "gen": "Radeon RX Series",
        "fsr4": True
    }


def parse_overdrive_ranges(od_text: str) -> Dict[str, Any]:
    res = {
        "sclk_min": -500, "sclk_max": 1000,
        "mclk_min": 100, "mclk_max": 1500,
        "vddc_offset_min": -200, "vddc_offset_max": 0
    }
    lines = od_text.splitlines()
    in_range = False
    for line in lines:
        line_s = line.strip()
        if "OD_RANGE:" in line_s:
            in_range = True
            continue
        if in_range:
            parts = line_s.split()
            if len(parts) >= 3:
                key = parts[0].replace(":", "").upper()
                try:
                    val_min = int(parts[1].lower().replace("mhz", "").replace("mv", ""))
                    val_max = int(parts[2].lower().replace("mhz", "").replace("mv", ""))
                    if "SCLK" in key:
                        res["sclk_min"] = val_min
                        res["sclk_max"] = val_max
                    elif "MCLK" in key:
                        res["mclk_min"] = val_min
                        res["mclk_max"] = val_max
                    elif "VDD" in key:
                        res["vddc_offset_min"] = val_min
                        res["vddc_offset_max"] = val_max
                except ValueError:
                    pass
    return res


def parse_power_profile_modes(text: str) -> List[str]:
    profiles = []
    lines = text.splitlines()
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].isdigit():
            name = parts[1].replace("*", "").replace(":", "")
            if name and name not in profiles:
                profiles.append(name)
    return profiles


def detect_amd_gpus() -> List[GpuDevice]:
    gpus: List[GpuDevice] = []
    card_paths = sorted(glob.glob("/sys/class/drm/card[0-9]*"))
    
    for card in card_paths:
        if "-" in os.path.basename(card):
            continue
        
        dev_dir = os.path.realpath(os.path.join(card, "device"))
        if not os.path.isdir(dev_dir):
            continue
        
        vendor = _read_file(os.path.join(dev_dir, "vendor"))
        if vendor != "0x1002":
            continue
        
        card_name = os.path.basename(card)
        dev_id = _read_file(os.path.join(dev_dir, "device")) or ""
        subsys_vendor = _read_file(os.path.join(dev_dir, "subsystem_vendor")) or ""
        subsys_device = _read_file(os.path.join(dev_dir, "subsystem_device")) or ""
        vbios = _read_file(os.path.join(dev_dir, "vbios_version")) or "Unknown"
        vram_vendor = _read_file(os.path.join(dev_dir, "mem_info_vram_vendor")) or "Unknown"
        
        # VRAM capacity
        vram_total_b = _read_file(os.path.join(dev_dir, "mem_info_vram_total"))
        vram_total_mb = int(int(vram_total_b) / (1024 * 1024)) if vram_total_b and vram_total_b.isdigit() else 0
        
        # HWMON
        hwmons = glob.glob(os.path.join(dev_dir, "hwmon", "hwmon*"))
        hwmon_dir = hwmons[0] if hwmons else None
        
        power_cap_def = 0.0
        power_cap_min = 0.0
        power_cap_max = 0.0
        if hwmon_dir:
            def_w = _read_file(os.path.join(hwmon_dir, "power1_cap_default")) or _read_file(os.path.join(hwmon_dir, "power1_cap"))
            min_w = _read_file(os.path.join(hwmon_dir, "power1_cap_min"))
            max_w = _read_file(os.path.join(hwmon_dir, "power1_cap_max"))
            if def_w and def_w.isdigit():
                power_cap_def = float(def_w) / 1000000.0
            if min_w and min_w.isdigit():
                power_cap_min = float(min_w) / 1000000.0
            if max_w and max_w.isdigit():
                power_cap_max = float(max_w) / 1000000.0
        
        # Overdrive
        od_file = os.path.join(dev_dir, "pp_od_clk_voltage")
        has_od = os.path.exists(od_file)
        od_ranges = {"sclk_min": -500, "sclk_max": 1000, "mclk_min": 100, "mclk_max": 1500, "vddc_offset_min": -200, "vddc_offset_max": 0}
        if has_od:
            od_content = _read_file(od_file) or ""
            if od_content:
                od_ranges = parse_overdrive_ranges(od_content)
        
        # Power Profile Modes
        ppm_file = os.path.join(dev_dir, "pp_power_profile_mode")
        profiles = []
        if os.path.exists(ppm_file):
            ppm_text = _read_file(ppm_file) or ""
            profiles = parse_power_profile_modes(ppm_text)
        
        # Query Model & Architecture from RDNA Database
        db_info = get_gpu_info_by_device_id(dev_id)
        
        gpu = GpuDevice(
            card_path=card,
            card_name=card_name,
            device_dir=dev_dir,
            hwmon_dir=hwmon_dir,
            vendor_id=vendor or "0x1002",
            device_id=dev_id,
            subsystem_vendor=subsys_vendor,
            subsystem_device=subsys_device,
            model_name=db_info.get("model", "AMD Radeon GPU"),
            architecture=db_info.get("arch", "RDNA"),
            generation_name=db_info.get("gen", "Radeon Series"),
            supports_fsr4=db_info.get("fsr4", True),
            ai_acceleration="WMMA AI Matrix Cores (Hardware-Beschleunigt)" if db_info.get("fsr4", True) else "Nicht unterstützt",
            vbios_version=vbios,
            vram_total_mb=vram_total_mb,
            vram_vendor=vram_vendor.capitalize(),
            power_cap_default_w=power_cap_def,
            power_cap_min_w=power_cap_min,
            power_cap_max_w=power_cap_max,
            has_overdrive=has_od,
            od_sclk_min=od_ranges["sclk_min"],
            od_sclk_max=od_ranges["sclk_max"],
            od_mclk_min=od_ranges["mclk_min"],
            od_mclk_max=od_ranges["mclk_max"],
            od_vddc_offset_min=od_ranges["vddc_offset_min"],
            od_vddc_offset_max=od_ranges["vddc_offset_max"],
            power_profiles=profiles
        )
        gpus.append(gpu)
        
    return gpus
