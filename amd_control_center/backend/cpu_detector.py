"""Universal CPU and Architecture Detection for AMD Ryzen, Intel Core/Xeon, and Generic Processors."""

import os
import glob
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class CoreInfo:
    core_id: int                  # Physical core ID (0, 1, 2...)
    cpu_numbers: List[int]        # Logical CPU numbers (e.g. [0, 8])
    cppc_rank: int = 0            # CPPC hardware ranking (e.g. 196)
    is_gold_star: bool = False    # Best core in CCX/CCD (AMD)
    is_silver_star: bool = False  # 2nd best core in CCX/CCD (AMD)
    core_type: str = "standard"   # "standard", "p-core" (Performance), "e-core" (Efficient)
    cur_freq_mhz: float = 0.0
    max_freq_mhz: float = 0.0
    min_freq_mhz: float = 0.0
    energy_hwmon_file: str = ""   # Path to zenergy / RAPL energyX_input


@dataclass
class CpuDevice:
    vendor: str = "AMD"                      # "AMD", "Intel", "ARM", "Generic"
    vendor_id: str = "AuthenticAMD"          # "AuthenticAMD", "GenuineIntel"
    model_name: str = "AMD Ryzen Processor"
    family: int = 0
    model: int = 0
    stepping: int = 0
    architecture: str = "Zen 5"              # "Zen 5", "Zen 4", "Raptor Lake", "Alder Lake", etc.
    codename: str = "Granite Ridge"          # "Granite Ridge", "Raphael", "Vermeer", "Raptor Lake", etc.
    socket: str = "AM5"                      # "AM5", "AM4", "LGA1700", "LGA1851", "sTR5", etc.
    marketing_family: str = "Ryzen 9000"     # "Ryzen 9000 Series", "14th Gen Intel Core", etc.
    has_3d_vcache: bool = False
    physical_cores: int = 8
    logical_threads: int = 16
    p_core_count: int = 8
    e_core_count: int = 0
    is_hybrid: bool = False
    smt_active: bool = True
    base_clock_mhz: float = 4700.0
    boost_clock_mhz: float = 5200.0
    cache_l1d_kb: int = 384
    cache_l1i_kb: int = 256
    cache_l2_kb: int = 8192
    cache_l3_kb: int = 98304
    cores: List[CoreInfo] = field(default_factory=list)
    gold_core_id: int = -1
    silver_core_id: int = -1
    scaling_driver: str = "amd-pstate-epp"
    available_governors: List[str] = field(default_factory=list)
    available_epps: List[str] = field(default_factory=list)
    boost_supported: bool = True
    boost_enabled: bool = True
    temp_hwmon_dir: str = ""                 # k10temp or coretemp
    k10temp_hwmon_dir: str = ""
    coretemp_hwmon_dir: str = ""
    zenergy_hwmon_dir: str = ""
    rapl_power_dir: str = ""
    ram_hwmon_dirs: List[str] = field(default_factory=list)
    has_zenergy: bool = False
    has_k10temp: bool = False
    has_coretemp: bool = False
    has_ryzen_smu: bool = False

    @property
    def is_amd(self) -> bool:
        return self.vendor == "AMD" or "AMD" in self.vendor_id or "AuthenticAMD" in self.vendor_id

    @property
    def is_intel(self) -> bool:
        return self.vendor == "Intel" or "Intel" in self.vendor_id or "GenuineIntel" in self.vendor_id


def _detect_cpu_architecture(vendor_id: str, family: int, model: int, stepping: int, model_name: str) -> Tuple[str, str, str, str, str, bool]:
    """
    Identifies CPU vendor, architecture, codename, marketing family, socket, and 3D V-Cache flag.
    Returns: (vendor, architecture, codename, marketing_family, socket, has_3d_vcache)
    """
    name_clean = model_name.strip()
    name_lower = name_clean.lower()

    # 1. AMD Processors
    if "amd" in name_lower or "authenticamd" in vendor_id.lower():
        vendor = "AMD"
        has_3d = "3d" in name_lower or "x3d" in name_lower

        # Zen 5
        if any(x in name_lower for x in ["9800x3d", "9950x", "9900x", "9700x", "9600x", "ryzen 9 9", "ryzen 7 9", "ryzen 5 9"]):
            return vendor, "Zen 5", "Granite Ridge", "Ryzen 9000 Series", "AM5 (LGA1718)", has_3d
        if "ai 9" in name_lower or "ai 7" in name_lower or "strix" in name_lower:
            return vendor, "Zen 5", "Strix Point", "Ryzen AI 300 Series", "FP8 / BGA", has_3d
        if "epyc" in name_lower and ("9005" in name_lower or family == 26):
            return vendor, "Zen 5", "Turin", "EPYC 9005 Series", "SP5", has_3d
        if family == 26:
            return vendor, "Zen 5", "Granite Ridge", "Ryzen 9000 Series", "AM5 (LGA1718)", has_3d

        # Zen 4
        if any(x in name_lower for x in ["7800x3d", "7950x3d", "7900x3d", "7950x", "7900x", "7700x", "7700", "7600x", "7600"]):
            return vendor, "Zen 4", "Raphael", "Ryzen 7000 Series", "AM5 (LGA1718)", has_3d
        if any(x in name_lower for x in ["8700g", "8600g", "8500g", "8300g", "8845hs", "8840u", "7940hs", "7840hs", "7840u"]):
            return vendor, "Zen 4", "Phoenix / Hawk Point", "Ryzen 8000G / 7040 Series", "AM5 / FP7", has_3d
        if "threadripper" in name_lower and ("79" in name_lower or "7000" in name_lower):
            return vendor, "Zen 4", "Storm Peak", "Ryzen Threadripper 7000", "sTR5", has_3d
        if "epyc" in name_lower and ("9004" in name_lower or "8004" in name_lower):
            return vendor, "Zen 4", "Genoa / Bergamo", "EPYC 9004 Series", "SP5", has_3d
        if family == 25 and model >= 96:
            return vendor, "Zen 4", "Raphael", "Ryzen 7000 Series", "AM5 (LGA1718)", has_3d

        # Zen 3
        if any(x in name_lower for x in ["5800x3d", "5700x3d", "5600x3d", "5950x", "5900x", "5800x", "5700x", "5600x", "5600", "5500"]):
            return vendor, "Zen 3", "Vermeer", "Ryzen 5000 Series", "AM4 (PGA1331)", has_3d
        if any(x in name_lower for x in ["5700g", "5600g", "5300g", "5800h", "5600h", "5800u", "5600u"]):
            return vendor, "Zen 3", "Cezanne / Barcelo", "Ryzen 5000G / Mobile", "AM4 / FP6", has_3d
        if "threadripper" in name_lower and ("59" in name_lower or "5000" in name_lower):
            return vendor, "Zen 3", "Chagall", "Ryzen Threadripper 5000WX", "sWRX8", has_3d
        if "epyc" in name_lower and "7003" in name_lower:
            return vendor, "Zen 3", "Milan / Milan-X", "EPYC 7003 Series", "SP3", has_3d
        if family == 25:
            return vendor, "Zen 3", "Vermeer", "Ryzen 5000 Series", "AM4 (PGA1331)", has_3d

        # Zen 2
        if any(x in name_lower for x in ["3950x", "3900x", "3800x", "3700x", "3600x", "3600", "3500", "3300x", "3100"]):
            return vendor, "Zen 2", "Matisse", "Ryzen 3000 Series", "AM4 (PGA1331)", False
        if any(x in name_lower for x in ["4700g", "4600g", "4300g", "4800h", "4700u", "4500u", "5700u", "5300u"]):
            return vendor, "Zen 2", "Renoir / Lucienne", "Ryzen 4000 Series", "AM4 / FP6", False
        if ("custom" in name_lower and "0405" in name_lower) or "valve" in name_lower or "aerith" in name_lower or "sephiroth" in name_lower:
            return vendor, "Zen 2", "Van Gogh / Aerith", "Steam Deck Custom APU", "BGA", False
        if "threadripper" in name_lower and ("39" in name_lower or "3000" in name_lower):
            return vendor, "Zen 2", "Castle Peak", "Ryzen Threadripper 3000", "sTRX4", False
        if "epyc" in name_lower and "7002" in name_lower:
            return vendor, "Zen 2", "Rome", "EPYC 7002 Series", "SP3", False

        # Zen+
        if any(x in name_lower for x in ["2700x", "2700", "2600x", "2600", "2500x", "2300x"]):
            return vendor, "Zen+", "Pinnacle Ridge", "Ryzen 2000 Series", "AM4 (PGA1331)", False
        if any(x in name_lower for x in ["3400g", "3200g"]):
            return vendor, "Zen+", "Picasso", "Ryzen 3000G Series", "AM4 (PGA1331)", False
        if "threadripper" in name_lower and ("29" in name_lower or "2000" in name_lower):
            return vendor, "Zen+", "Colfax", "Ryzen Threadripper 2000", "TR4", False

        # Zen 1
        if any(x in name_lower for x in ["1800x", "1700x", "1700", "1600x", "1600", "1500x", "1400", "1300x", "1200"]):
            return vendor, "Zen", "Summit Ridge", "Ryzen 1000 Series", "AM4 (PGA1331)", False
        if any(x in name_lower for x in ["2400g", "2200g"]):
            return vendor, "Zen", "Raven Ridge", "Ryzen 2000G Series", "AM4 (PGA1331)", False
        if "threadripper" in name_lower and ("19" in name_lower or "1000" in name_lower):
            return vendor, "Zen", "Whitehaven", "Ryzen Threadripper 1000", "TR4", False
        if family == 23:
            return vendor, "Zen", "Summit Ridge", "Ryzen Processor", "AM4 (PGA1331)", False

        # Older AMD
        if "fx-" in name_lower or family == 21:
            return vendor, "AMD FX", "Piledriver / Vishera", "AMD FX Series", "AM3+", False
        if "phenom" in name_lower or family == 16:
            return vendor, "K10", "Deneb / Thuban", "Phenom II Series", "AM3", False
        if "athlon" in name_lower:
            return vendor, "AMD Athlon", "Athlon", "Athlon Series", "AM4/AM3", False

        return vendor, "AMD Zen", "Zen Architecture", "AMD Ryzen Processor", "AM4/AM5", has_3d

    # 2. Intel Processors
    elif "intel" in name_lower or "genuineintel" in vendor_id.lower():
        vendor = "Intel"

        # Arrow Lake (Core Ultra 200)
        if any(x in name_lower for x in ["285k", "265k", "245k", "ultra 9 2", "ultra 7 2", "ultra 5 2"]):
            return vendor, "Arrow Lake", "Arrow Lake-S", "Core Ultra 200 Series", "LGA1851", False
        if "258v" in name_lower or "256v" in name_lower or "lunar" in name_lower:
            return vendor, "Lunar Lake", "Lunar Lake", "Core Ultra 200V", "BGA", False

        # Meteor Lake (Core Ultra 100)
        if any(x in name_lower for x in ["185h", "155h", "125h", "ultra 9 1", "ultra 7 1", "ultra 5 1"]):
            return vendor, "Meteor Lake", "Meteor Lake-H", "Core Ultra 100 Series", "BGA", False

        # Raptor Lake Refresh (14th Gen)
        if any(x in name_lower for x in ["14900", "14700", "14600", "14500", "14400"]):
            return vendor, "Raptor Lake Refresh", "Raptor Lake Refresh", "14th Gen Core", "LGA1700", False

        # Raptor Lake (13th Gen)
        if any(x in name_lower for x in ["13900", "13700", "13600", "13500", "13400"]):
            return vendor, "Raptor Lake", "Raptor Lake", "13th Gen Core", "LGA1700", False

        # Alder Lake (12th Gen)
        if any(x in name_lower for x in ["12900", "12700", "12600", "12500", "12400", "12100"]):
            return vendor, "Alder Lake", "Alder Lake", "12th Gen Core", "LGA1700", False

        # Rocket Lake (11th Gen)
        if any(x in name_lower for x in ["11900", "11700", "11600", "11400"]):
            return vendor, "Rocket Lake", "Rocket Lake", "11th Gen Core", "LGA1200", False

        # Comet Lake (10th Gen)
        if any(x in name_lower for x in ["10900", "10700", "10600", "10400", "10100"]):
            return vendor, "Comet Lake", "Comet Lake", "10th Gen Core", "LGA1200", False

        # Coffee Lake (8th / 9th Gen)
        if any(x in name_lower for x in ["9900", "9700", "9600", "9400", "8700", "8600", "8400", "8100"]):
            return vendor, "Coffee Lake", "Coffee Lake", "8th/9th Gen Core", "LGA1151v2", False

        # Kaby Lake / Skylake (6th / 7th Gen)
        if any(x in name_lower for x in ["7700", "7600", "6700", "6600"]):
            return vendor, "Skylake", "Skylake / Kaby Lake", "6th/7th Gen Core", "LGA1151", False

        # Haswell / Broadwell (4th / 5th Gen)
        if any(x in name_lower for x in ["4790", "4770", "4690", "4670", "5775"]):
            return vendor, "Haswell", "Haswell", "4th Gen Core", "LGA1150", False

        # Sandy Bridge / Ivy Bridge (2nd / 3rd Gen)
        if any(x in name_lower for x in ["3770", "3570", "2600", "2500"]):
            return vendor, "Sandy Bridge", "Sandy / Ivy Bridge", "2nd/3rd Gen Core", "LGA1155", False

        # Xeon
        if "xeon" in name_lower:
            return vendor, "Intel Xeon", "Sapphire / Emerald Rapids", "Intel Xeon Scalable", "LGA4677", False

        return vendor, "Intel Core", "Intel Microarchitecture", "Intel Core Processor", "LGA Socket", False

    # 3. ARM Architecture
    elif "arm" in vendor_id.lower() or "aarch64" in vendor_id.lower() or "cortex" in name_lower:
        return "ARM", "ARMv8/v9", "ARM Cortex / Neoverse", "ARM Processor", "SoC / BGA", False

    return "Generic", "x86_64", "Generic x86", "Processor", "Socket", False


def _detect_intel_hybrid_cores(cpu_dirs: List[str]) -> Tuple[Dict[int, str], int, int]:
    """
    Detects Performance (P-Core) vs Efficient (E-Core) on Intel Alder/Raptor/Arrow Lake.
    Returns: (core_type_map, p_core_count, e_core_count)
    """
    type_map: Dict[int, str] = {}
    p_count = 0
    e_count = 0

    # Method 1: /sys/devices/cpu_core and /sys/devices/cpu_atom
    p_cpus = set()
    e_cpus = set()
    core_f = "/sys/devices/cpu_core/cpus"
    atom_f = "/sys/devices/cpu_atom/cpus"

    def _parse_cpu_range(path: str) -> set:
        res = set()
        if os.path.isfile(path):
            try:
                content = open(path).read().strip()
                for part in content.split(","):
                    if "-" in part:
                        start, end = part.split("-")
                        res.update(range(int(start), int(end) + 1))
                    elif part.isdigit():
                        res.add(int(part))
            except Exception:
                pass
        return res

    p_cpus = _parse_cpu_range(core_f)
    e_cpus = _parse_cpu_range(atom_f)

    for d in cpu_dirs:
        c_name = os.path.basename(d)
        if not c_name.replace("cpu", "").isdigit():
            continue
        c_num = int(c_name.replace("cpu", ""))

        # Check core_type file inside topology if available
        ct_file = os.path.join(d, "topology", "core_type")
        c_type = "standard"
        if os.path.isfile(ct_file):
            try:
                val = open(ct_file).read().strip().lower()
                if "atom" in val:
                    c_type = "e-core"
                elif "core" in val:
                    c_type = "p-core"
            except Exception:
                pass

        if c_type == "standard":
            if c_num in p_cpus:
                c_type = "p-core"
            elif c_num in e_cpus:
                c_type = "e-core"

        type_map[c_num] = c_type
        if c_type == "p-core":
            p_count += 1
        elif c_type == "e-core":
            e_count += 1

    return type_map, p_count, e_count


def _detect_sensors() -> Tuple[str, str, str, str, str, List[str]]:
    """
    Finds hwmon paths for:
    k10temp, coretemp, zenergy, rapl power, and RAM SPD.
    """
    k10_dir = ""
    coretemp_dir = ""
    zen_dir = ""
    rapl_dir = ""
    generic_temp_dir = ""
    ram_dirs = []

    for path in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name_file = os.path.join(path, "name")
        if not os.path.isfile(name_file):
            continue
        try:
            with open(name_file, "r") as f:
                name = f.read().strip().lower()
            if name == "k10temp":
                k10_dir = path
            elif name == "coretemp":
                coretemp_dir = path
            elif name == "zenergy":
                zen_dir = path
            elif "rapl" in name or "intel_rapl" in name:
                rapl_dir = path
            elif name in ("spd5118", "jc42", "dimm_temp"):
                ram_dirs.append(path)
            elif name in ("acpitz", "cpu_thermal") and not generic_temp_dir:
                generic_temp_dir = path
        except Exception:
            pass

    # Check powercap directory as fallback for RAPL
    if not rapl_dir and os.path.isdir("/sys/class/powercap/intel-rapl/intel-rapl:0"):
        rapl_dir = "/sys/class/powercap/intel-rapl/intel-rapl:0"

    return k10_dir, coretemp_dir, zen_dir, rapl_dir, generic_temp_dir, ram_dirs


def detect_cpu() -> CpuDevice:
    """Performs full hardware, architecture, socket, and sensor detection for any CPU."""
    dev = CpuDevice()

    # 1. Read /proc/cpuinfo
    if os.path.isfile("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    key, val = [p.strip() for p in line.split(":", 1)]
                    if key == "model name" and (dev.model_name == "AMD Ryzen Processor" or not dev.model_name):
                        dev.model_name = val
                    elif key == "vendor_id":
                        dev.vendor_id = val
                    elif key == "cpu family" and dev.family == 0:
                        try:
                            dev.family = int(val)
                        except ValueError:
                            pass
                    elif key == "model" and dev.model == 0:
                        try:
                            dev.model = int(val)
                        except ValueError:
                            pass
                    elif key == "stepping" and dev.stepping == 0:
                        try:
                            dev.stepping = int(val)
                        except ValueError:
                            pass
        except Exception:
            pass

    # 2. Comprehensive Generation, Codename, Socket & 3D V-Cache Recognition
    vendor, arch, codename, m_family, socket, has_3d = _detect_cpu_architecture(
        dev.vendor_id, dev.family, dev.model, dev.stepping, dev.model_name
    )
    dev.vendor = vendor
    dev.architecture = arch
    dev.codename = codename
    dev.marketing_family = m_family
    dev.socket = socket
    dev.has_3d_vcache = has_3d

    # 3. Cache Detection (from cpu0)
    l1d_kb = 0
    l1i_kb = 0
    l2_kb = 0
    l3_kb = 0
    for idx_path in sorted(glob.glob("/sys/devices/system/cpu/cpu0/cache/index*")):
        try:
            lvl_f = os.path.join(idx_path, "level")
            type_f = os.path.join(idx_path, "type")
            size_f = os.path.join(idx_path, "size")
            if os.path.isfile(lvl_f) and os.path.isfile(size_f):
                lvl = open(lvl_f).read().strip()
                t = open(type_f).read().strip().lower() if os.path.isfile(type_f) else ""
                sz_str = open(size_f).read().strip().upper()
                multiplier = 1024 if "M" in sz_str else 1
                clean_num = int("".join(c for c in sz_str if c.isdigit())) * multiplier
                if lvl == "1":
                    if "data" in t:
                        l1d_kb = clean_num
                    else:
                        l1i_kb = clean_num
                elif lvl == "2":
                    l2_kb = clean_num
                elif lvl == "3":
                    l3_kb = clean_num
        except Exception:
            pass

    if l3_kb > 0:
        dev.cache_l3_kb = l3_kb
        # Single CCD with >= 64MB indicates 3D V-Cache
        if l3_kb >= 65536:
            dev.has_3d_vcache = True
    if l2_kb > 0:
        dev.cache_l2_kb = l2_kb
    if l1d_kb > 0:
        dev.cache_l1d_kb = l1d_kb
    if l1i_kb > 0:
        dev.cache_l1i_kb = l1i_kb

    # 4. Sensor Discovery
    k10_dir, coretemp_dir, zen_dir, rapl_dir, generic_dir, ram_dirs = _detect_sensors()
    dev.k10temp_hwmon_dir = k10_dir
    dev.coretemp_hwmon_dir = coretemp_dir
    dev.zenergy_hwmon_dir = zen_dir
    dev.rapl_power_dir = rapl_dir
    dev.ram_hwmon_dirs = ram_dirs
    dev.has_k10temp = bool(k10_dir)
    dev.has_coretemp = bool(coretemp_dir)
    dev.has_zenergy = bool(zen_dir)

    # Pick primary temperature hwmon dir
    if k10_dir:
        dev.temp_hwmon_dir = k10_dir
    elif coretemp_dir:
        dev.temp_hwmon_dir = coretemp_dir
    elif generic_dir:
        dev.temp_hwmon_dir = generic_dir

    # 5. Energy mapping from zenergy (if present)
    energy_map: Dict[int, str] = {}
    if zen_dir:
        for lbl_path in glob.glob(os.path.join(zen_dir, "energy*_label")):
            try:
                with open(lbl_path) as f:
                    lbl = f.read().strip()
                if lbl.startswith("Ecore"):
                    c_num = int(lbl.replace("Ecore", ""))
                    inp_file = lbl_path.replace("_label", "_input")
                    if os.path.isfile(inp_file):
                        energy_map[c_num] = inp_file
            except Exception:
                pass

    # 6. Topology & Core Mapping
    cpu_dirs = sorted(
        glob.glob("/sys/devices/system/cpu/cpu[0-9]*"),
        key=lambda p: int(os.path.basename(p).replace("cpu", ""))
    )
    dev.logical_threads = len(cpu_dirs)

    # Hybrid Core Detection (Intel Alder Lake, Raptor Lake, Arrow Lake)
    hybrid_map, p_cnt, e_cnt = _detect_intel_hybrid_cores(cpu_dirs)
    if p_cnt > 0 and e_cnt > 0:
        dev.is_hybrid = True
        dev.p_core_count = p_cnt
        dev.e_core_count = e_cnt

    physical_core_groups: Dict[int, List[int]] = {}
    for d in cpu_dirs:
        c_name = os.path.basename(d)
        if not c_name.replace("cpu", "").isdigit():
            continue
        cpu_num = int(c_name.replace("cpu", ""))
        core_id_file = os.path.join(d, "topology", "core_id")
        if os.path.isfile(core_id_file):
            try:
                with open(core_id_file) as f:
                    p_core = int(f.read().strip())
            except Exception:
                p_core = cpu_num
        else:
            p_core = cpu_num
        
        if p_core not in physical_core_groups:
            physical_core_groups[p_core] = []
        physical_core_groups[p_core].append(cpu_num)

    dev.physical_cores = len(physical_core_groups)
    dev.smt_active = dev.logical_threads > dev.physical_cores

    # 7. Build CoreInfo List with CPPC Ranking & Core Types
    cores: List[CoreInfo] = []
    ranks: List[Tuple[int, int]] = []

    for p_core in sorted(physical_core_groups.keys()):
        cpu_nums = physical_core_groups[p_core]
        lead_cpu = cpu_nums[0]
        cpufreq_dir = f"/sys/devices/system/cpu/cpu{lead_cpu}/cpufreq"

        rank = 0
        cur_f = 0.0
        max_f = 0.0
        min_f = 0.0
        c_type = hybrid_map.get(lead_cpu, "standard")

        if os.path.isdir(cpufreq_dir):
            # CPPC Ranking (AMD)
            rank_f = os.path.join(cpufreq_dir, "amd_pstate_prefcore_ranking")
            if os.path.isfile(rank_f):
                try:
                    rank = int(open(rank_f).read().strip())
                except Exception:
                    pass
            cur_f_path = os.path.join(cpufreq_dir, "scaling_cur_freq")
            if os.path.isfile(cur_f_path):
                try:
                    cur_f = float(open(cur_f_path).read().strip()) / 1000.0
                except Exception:
                    pass
            max_f_path = os.path.join(cpufreq_dir, "cpuinfo_max_freq")
            if os.path.isfile(max_f_path):
                try:
                    max_f = float(open(max_f_path).read().strip()) / 1000.0
                except Exception:
                    pass
            min_f_path = os.path.join(cpufreq_dir, "cpuinfo_min_freq")
            if os.path.isfile(min_f_path):
                try:
                    min_f = float(open(min_f_path).read().strip()) / 1000.0
                except Exception:
                    pass

        ci = CoreInfo(
            core_id=p_core,
            cpu_numbers=cpu_nums,
            cppc_rank=rank,
            core_type=c_type,
            cur_freq_mhz=cur_f,
            max_freq_mhz=max_f if max_f > 0 else 5200.0,
            min_freq_mhz=min_f if min_f > 0 else 400.0,
            energy_hwmon_file=energy_map.get(p_core, "")
        )
        cores.append(ci)
        if rank > 0:
            ranks.append((rank, p_core))

    # Identify Gold and Silver Cores for AMD
    if ranks:
        ranks.sort(key=lambda x: x[0], reverse=True)
        dev.gold_core_id = ranks[0][1]
        if len(ranks) > 1:
            dev.silver_core_id = ranks[1][1]

        for c in cores:
            if c.core_id == dev.gold_core_id:
                c.is_gold_star = True
            elif c.core_id == dev.silver_core_id:
                c.is_silver_star = True

    dev.cores = cores

    # 8. Governor & EPP Capabilities (amd-pstate, intel_pstate, acpi-cpufreq)
    cpu0_freq = "/sys/devices/system/cpu/cpu0/cpufreq"
    if os.path.isdir(cpu0_freq):
        driver_f = os.path.join(cpu0_freq, "scaling_driver")
        if os.path.isfile(driver_f):
            dev.scaling_driver = open(driver_f).read().strip()

        govs_f = os.path.join(cpu0_freq, "scaling_available_governors")
        if os.path.isfile(govs_f):
            dev.available_governors = open(govs_f).read().strip().split()

        epps_f = os.path.join(cpu0_freq, "energy_performance_available_preferences")
        if os.path.isfile(epps_f):
            dev.available_epps = open(epps_f).read().strip().split()

        boost_f = os.path.join(cpu0_freq, "boost")
        if not os.path.isfile(boost_f):
            boost_f = "/sys/devices/system/cpu/cpufreq/boost"
        if not os.path.isfile(boost_f):
            # Check intel_pstate turbo
            boost_f = "/sys/devices/system/cpu/intel_pstate/no_turbo"
            if os.path.isfile(boost_f):
                dev.boost_supported = True
                dev.boost_enabled = open(boost_f).read().strip() == "0"
        else:
            dev.boost_supported = True
            dev.boost_enabled = open(boost_f).read().strip() == "1"

    # Base and Boost Clock approximation
    if dev.cores:
        highest_max = max(c.max_freq_mhz for c in dev.cores)
        if highest_max > 0:
            dev.boost_clock_mhz = highest_max

    # 9. Check for ryzen_smu driver (AMD only)
    dev.has_ryzen_smu = dev.is_amd and (
        os.path.isfile("/sys/kernel/ryzen_smu_drv/version") or os.path.exists("/sys/kernel/ryzen_smu_drv")
    )

    return dev
