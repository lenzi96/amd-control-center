"""Real-time AMD Ryzen CPU telemetry polling worker using QTimer."""

import os
import time
from collections import deque
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .cpu_detector import CpuDevice


def _read_int(path: str, default: int = 0) -> int:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
                    return int(val)
    except Exception:
        pass
    return default


def _read_float(path: str, default: float = 0.0) -> float:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return float(val)
    except Exception:
        pass
    return default


class CpuTelemetryMonitor(QObject):
    """Telemetry monitor that polls AMD Ryzen CPU metrics and emits updates."""
    
    telemetry_updated = pyqtSignal(dict)
    
    def __init__(self, cpu: CpuDevice, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.cpu = cpu
        self.interval_ms = interval_ms
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_and_emit)
        
        # Power & Energy Tracking
        self._last_poll_time: float = 0.0
        self._last_socket_uj: int = 0
        self._last_core_uj: Dict[int, int] = {}
        self._socket_energy_file = ""
        if self.cpu.zenergy_hwmon_dir:
            # Socket energy file is usually energy9_input or label 'Esocket0'
            for idx in range(1, 15):
                lbl_f = os.path.join(self.cpu.zenergy_hwmon_dir, f"energy{idx}_label")
                inp_f = os.path.join(self.cpu.zenergy_hwmon_dir, f"energy{idx}_input")
                if os.path.isfile(lbl_f) and os.path.isfile(inp_f):
                    try:
                        with open(lbl_f) as f:
                            if "Esocket" in f.read():
                                self._socket_energy_file = inp_f
                                break
                    except Exception:
                        pass
        elif self.cpu.rapl_power_dir:
            # Intel / generic RAPL powercap or hwmon
            for candidate in ["energy_uj", "energy1_input", "power1_input"]:
                f_cand = os.path.join(self.cpu.rapl_power_dir, candidate)
                if os.path.isfile(f_cand):
                    self._socket_energy_file = f_cand
                    break

        # CPU Utilization tracking via /proc/stat
        self._last_stat_total: int = 0
        self._last_stat_idle: int = 0
        self._last_cpu_stats: Dict[int, tuple] = {} # cpu_idx -> (total, idle)
        
        # Rolling History (60 points)
        self.history_len = 60
        self.history: Dict[str, deque] = {
            "cpu_usage": deque(maxlen=self.history_len),
            "temp_tctl": deque(maxlen=self.history_len),
            "temp_tccd1": deque(maxlen=self.history_len),
            "package_power": deque(maxlen=self.history_len),
            "peak_freq": deque(maxlen=self.history_len),
            "avg_freq": deque(maxlen=self.history_len),
        }
        
    def start(self):
        self._init_baselines()
        self.poll_and_emit()
        self.timer.start(self.interval_ms)
        
    def stop(self):
        self.timer.stop()
        
    def set_interval(self, interval_ms: int):
        self.interval_ms = max(200, interval_ms)
        if self.timer.isActive():
            self.timer.start(self.interval_ms)

    def _init_baselines(self):
        self._last_poll_time = time.time()
        if self._socket_energy_file:
            self._last_socket_uj = _read_int(self._socket_energy_file, 0)
            
        for c in self.cpu.cores:
            if c.energy_hwmon_file:
                self._last_core_uj[c.core_id] = _read_int(c.energy_hwmon_file, 0)
                
        # Baseline /proc/stat
        if os.path.isfile("/proc/stat"):
            try:
                with open("/proc/stat", "r") as f:
                    for line in f:
                        parts = line.split()
                        if not parts:
                            continue
                        name = parts[0]
                        if name == "cpu":
                            vals = [int(x) for x in parts[1:8]]
                            self._last_stat_idle = vals[3] + vals[4]
                            self._last_stat_total = sum(vals)
                        elif name.startswith("cpu") and name[3:].isdigit():
                            c_idx = int(name[3:])
                            vals = [int(x) for x in parts[1:8]]
                            idle = vals[3] + vals[4]
                            total = sum(vals)
                            self._last_cpu_stats[c_idx] = (total, idle)
            except Exception:
                pass
            
    def poll_and_emit(self):
        metrics = self._poll_metrics()
        
        # Append to history
        self.history["cpu_usage"].append(metrics["cpu_usage_pct"])
        self.history["temp_tctl"].append(metrics["temp_tctl"])
        self.history["temp_tccd1"].append(metrics["temp_tccd1"])
        self.history["package_power"].append(metrics["package_power_w"])
        self.history["peak_freq"].append(metrics["peak_freq_mhz"])
        self.history["avg_freq"].append(metrics["avg_freq_mhz"])
        
        metrics["history"] = {k: list(v) for k, v in self.history.items()}
        self.telemetry_updated.emit(metrics)

    def _poll_metrics(self) -> Dict[str, Any]:
        now = time.time()
        delta_t = now - self._last_poll_time if self._last_poll_time > 0 else 1.0
        self._last_poll_time = now
        
        # 1. Package & Core Power (Watts) via zenergy
        package_power_w = 0.0
        if self._socket_energy_file:
            cur_sock_uj = _read_int(self._socket_energy_file, 0)
            if cur_sock_uj >= self._last_socket_uj and self._last_socket_uj > 0 and delta_t > 0:
                diff_uj = cur_sock_uj - self._last_socket_uj
                package_power_w = round((diff_uj / 1_000_000.0) / delta_t, 1)
            self._last_socket_uj = cur_sock_uj
            
        core_power_w: Dict[int, float] = {}
        for c in self.cpu.cores:
            if c.energy_hwmon_file:
                cur_c_uj = _read_int(c.energy_hwmon_file, 0)
                last_c_uj = self._last_core_uj.get(c.core_id, 0)
                if cur_c_uj >= last_c_uj and last_c_uj > 0 and delta_t > 0:
                    diff_uj = cur_c_uj - last_c_uj
                    w = round((diff_uj / 1_000_000.0) / delta_t, 2)
                    core_power_w[c.core_id] = w
                else:
                    core_power_w[c.core_id] = 0.0
                self._last_core_uj[c.core_id] = cur_c_uj
            else:
                core_power_w[c.core_id] = 0.0

        # 2. Temperatures (k10temp for AMD, coretemp for Intel, or generic hwmon)
        temp_tctl = 0.0
        temp_tccd1 = 0.0
        if self.cpu.k10temp_hwmon_dir:
            # AMD k10temp
            for idx in range(1, 10):
                lbl_f = os.path.join(self.cpu.k10temp_hwmon_dir, f"temp{idx}_label")
                inp_f = os.path.join(self.cpu.k10temp_hwmon_dir, f"temp{idx}_input")
                if os.path.isfile(lbl_f) and os.path.isfile(inp_f):
                    try:
                        lbl = open(lbl_f).read().strip()
                        raw_temp = _read_float(inp_f, 0.0) / 1000.0
                        if lbl == "Tctl":
                            temp_tctl = round(raw_temp, 1)
                        elif lbl in ("Tccd1", "Tccd"):
                            temp_tccd1 = round(raw_temp, 1)
                    except Exception:
                        pass
            if temp_tctl == 0.0:
                raw_t = _read_float(os.path.join(self.cpu.k10temp_hwmon_dir, "temp1_input"), 0.0)
                temp_tctl = round(raw_t / 1000.0, 1)
        elif self.cpu.coretemp_hwmon_dir:
            # Intel coretemp
            core_temps = []
            for idx in range(1, 32):
                lbl_f = os.path.join(self.cpu.coretemp_hwmon_dir, f"temp{idx}_label")
                inp_f = os.path.join(self.cpu.coretemp_hwmon_dir, f"temp{idx}_input")
                if os.path.isfile(inp_f):
                    try:
                        raw_temp = _read_float(inp_f, 0.0) / 1000.0
                        lbl = open(lbl_f).read().strip() if os.path.isfile(lbl_f) else ""
                        if "package" in lbl.lower() or idx == 1:
                            temp_tctl = round(raw_temp, 1)
                        elif "core" in lbl.lower() and raw_temp > 0:
                            core_temps.append(raw_temp)
                    except Exception:
                        pass
            if core_temps:
                temp_tccd1 = round(max(core_temps), 1)
            if temp_tctl == 0.0 and core_temps:
                temp_tctl = round(max(core_temps), 1)
        elif self.cpu.temp_hwmon_dir:
            # Generic thermal sensor
            t_inp = os.path.join(self.cpu.temp_hwmon_dir, "temp1_input")
            if os.path.isfile(t_inp):
                temp_tctl = round(_read_float(t_inp, 0.0) / 1000.0, 1)

        # 3. DDR5 RAM Temperatures
        ram_temps: List[float] = []
        for r_dir in self.cpu.ram_hwmon_dirs:
            t_file = os.path.join(r_dir, "temp1_input")
            if os.path.isfile(t_file):
                raw_t = _read_float(t_file, 0.0)
                if raw_t > 0:
                    ram_temps.append(round(raw_t / 1000.0, 1))

        # 4. CPU Clocks per Core
        core_freqs_mhz: Dict[int, float] = {}
        all_freqs: List[float] = []
        for c in self.cpu.cores:
            freq = 0.0
            lead_cpu = c.cpu_numbers[0] if c.cpu_numbers else 0
            cur_f_path = f"/sys/devices/system/cpu/cpu{lead_cpu}/cpufreq/scaling_cur_freq"
            if os.path.isfile(cur_f_path):
                freq = _read_float(cur_f_path, 0.0) / 1000.0
            core_freqs_mhz[c.core_id] = round(freq, 0)
            if freq > 0:
                all_freqs.append(freq)

        peak_freq_mhz = round(max(all_freqs), 0) if all_freqs else self.cpu.boost_clock_mhz
        avg_freq_mhz = round(sum(all_freqs) / len(all_freqs), 0) if all_freqs else self.cpu.base_clock_mhz

        # Find which core has peak clock
        peak_core_id = -1
        for cid, f in core_freqs_mhz.items():
            if f == peak_freq_mhz:
                peak_core_id = cid
                break

        # 5. CPU Utilization via /proc/stat
        total_cpu_pct = 0.0
        thread_usage_pct: Dict[int, float] = {}
        if os.path.isfile("/proc/stat"):
            try:
                with open("/proc/stat", "r") as f:
                    for line in f:
                        parts = line.split()
                        if not parts:
                            continue
                        name = parts[0]
                        if name == "cpu":
                            vals = [int(x) for x in parts[1:8]]
                            idle = vals[3] + vals[4]
                            total = sum(vals)
                            diff_total = total - self._last_stat_total
                            diff_idle = idle - self._last_stat_idle
                            if diff_total > 0:
                                total_cpu_pct = round(100.0 * (1.0 - (diff_idle / diff_total)), 1)
                            self._last_stat_total = total
                            self._last_stat_idle = idle
                        elif name.startswith("cpu") and name[3:].isdigit():
                            c_idx = int(name[3:])
                            vals = [int(x) for x in parts[1:8]]
                            idle = vals[3] + vals[4]
                            total = sum(vals)
                            last_t, last_i = self._last_cpu_stats.get(c_idx, (total, idle))
                            diff_t = total - last_t
                            diff_i = idle - last_i
                            if diff_t > 0:
                                thread_usage_pct[c_idx] = round(100.0 * (1.0 - (diff_i / diff_t)), 1)
                            else:
                                thread_usage_pct[c_idx] = 0.0
                            self._last_cpu_stats[c_idx] = (total, idle)
            except Exception:
                pass

        # Calculate physical core usage (average of sibling threads)
        core_usage_pct: Dict[int, float] = {}
        for c in self.cpu.cores:
            usages = [thread_usage_pct.get(num, 0.0) for num in c.cpu_numbers]
            core_usage_pct[c.core_id] = round(sum(usages) / len(usages), 1) if usages else 0.0

        # 6. Online Status per Core
        core_online: Dict[int, bool] = {}
        for c in self.cpu.cores:
            lead_cpu = c.cpu_numbers[0] if c.cpu_numbers else 0
            online_f = f"/sys/devices/system/cpu/cpu{lead_cpu}/online"
            if os.path.isfile(online_f):
                core_online[c.core_id] = open(online_f).read().strip() == "1"
            else:
                core_online[c.core_id] = True # cpu0 often doesn't have 'online' file and is always on

        # 7. Governor and EPP Current State
        cur_governor = ""
        cur_epp = ""
        cpu0_freq = "/sys/devices/system/cpu/cpu0/cpufreq"
        if os.path.isdir(cpu0_freq):
            gov_f = os.path.join(cpu0_freq, "scaling_governor")
            if os.path.isfile(gov_f):
                cur_governor = open(gov_f).read().strip()
            epp_f = os.path.join(cpu0_freq, "energy_performance_preference")
            if os.path.isfile(epp_f):
                cur_epp = open(epp_f).read().strip()

        return {
            "cpu_usage_pct": total_cpu_pct,
            "core_usage_pct": core_usage_pct,
            "thread_usage_pct": thread_usage_pct,
            "package_power_w": package_power_w,
            "core_power_w": core_power_w,
            "temp_tctl": temp_tctl,
            "temp_tccd1": temp_tccd1,
            "ram_temps": ram_temps,
            "core_freqs_mhz": core_freqs_mhz,
            "peak_freq_mhz": peak_freq_mhz,
            "avg_freq_mhz": avg_freq_mhz,
            "peak_core_id": peak_core_id,
            "core_online": core_online,
            "cur_governor": cur_governor,
            "cur_epp": cur_epp,
        }
