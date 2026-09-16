"""Real-time GPU telemetry polling worker using QTimer."""

import os
from collections import deque
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .gpu_detector import GpuDevice


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


class GpuTelemetryMonitor(QObject):
    """Telemetry monitor that polls GPU metrics on a timer and emits updates."""
    
    telemetry_updated = pyqtSignal(dict)
    
    def __init__(self, gpu: GpuDevice, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.gpu = gpu
        self.interval_ms = interval_ms
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_and_emit)
        
        # Keep 60 data points rolling history
        self.history_len = 60
        self.history: Dict[str, deque] = {
            "gpu_busy": deque(maxlen=self.history_len),
            "temp_edge": deque(maxlen=self.history_len),
            "temp_junction": deque(maxlen=self.history_len),
            "sclk": deque(maxlen=self.history_len),
            "power": deque(maxlen=self.history_len),
            "vram_used": deque(maxlen=self.history_len),
            "fan_rpm": deque(maxlen=self.history_len),
        }
        
    def start(self):
        self.poll_and_emit()
        self.timer.start(self.interval_ms)
        
    def stop(self):
        self.timer.stop()
        
    def set_interval(self, interval_ms: int):
        self.interval_ms = max(200, interval_ms)
        if self.timer.isActive():
            self.timer.start(self.interval_ms)
            
    def poll_and_emit(self):
        metrics = self._poll_metrics(self.gpu.device_dir, self.gpu.hwmon_dir)
        
        # Append to rolling history
        self.history["gpu_busy"].append(metrics["gpu_busy"])
        self.history["temp_edge"].append(metrics["temp_edge"])
        self.history["temp_junction"].append(metrics["temp_junction"])
        self.history["sclk"].append(metrics["sclk"])
        self.history["power"].append(metrics["power_w"])
        self.history["vram_used"].append(metrics["vram_used_mb"])
        self.history["fan_rpm"].append(metrics["fan_rpm"])
        
        metrics["history"] = {k: list(v) for k, v in self.history.items()}
        self.telemetry_updated.emit(metrics)
        
    def _poll_metrics(self, dev: str, hw: Optional[str]) -> Dict[str, Any]:
        # Utilization
        gpu_busy = _read_int(os.path.join(dev, "gpu_busy_percent"), 0) if dev else 0
        mem_busy = _read_int(os.path.join(dev, "mem_busy_percent"), 0) if dev else 0
        
        # VRAM
        vram_total_b = _read_int(os.path.join(dev, "mem_info_vram_total"), 0) if dev else 0
        vram_used_b = _read_int(os.path.join(dev, "mem_info_vram_used"), 0) if dev else 0
        vram_total_mb = int(vram_total_b / (1024 * 1024)) if vram_total_b else self.gpu.vram_total_mb
        vram_used_mb = int(vram_used_b / (1024 * 1024)) if vram_used_b else 0
        vram_pct = int((vram_used_mb / vram_total_mb * 100)) if vram_total_mb > 0 else 0
        
        # Temperatures
        temp_edge = 0.0
        temp_junction = 0.0
        temp_mem = 0.0
        
        # Clocks & Power
        sclk = 0
        mclk = 0
        power_w = 0.0
        power_cap_w = self.gpu.power_cap_default_w
        fan_rpm = 0
        fan_pwm = 0
        fan_pwm_pct = 0
        voltage_mv = 0
        
        if hw and os.path.isdir(hw):
            t1 = _read_int(os.path.join(hw, "temp1_input"), 0)
            t2 = _read_int(os.path.join(hw, "temp2_input"), 0)
            t3 = _read_int(os.path.join(hw, "temp3_input"), 0)
            temp_edge = round(t1 / 1000.0, 1) if t1 else 0.0
            temp_junction = round(t2 / 1000.0, 1) if t2 else temp_edge
            temp_mem = round(t3 / 1000.0, 1) if t3 else 0.0
            
            f1 = _read_int(os.path.join(hw, "freq1_input"), 0)
            f2 = _read_int(os.path.join(hw, "freq2_input"), 0)
            sclk = int(f1 / 1000000.0) if f1 else 0
            mclk = int(f2 / 1000000.0) if f2 else 0
            
            pw = _read_int(os.path.join(hw, "power1_average"), 0)
            power_w = round(pw / 1000000.0, 1) if pw else 0.0
            
            cap = _read_int(os.path.join(hw, "power1_cap"), 0)
            if cap:
                power_cap_w = round(cap / 1000000.0, 1)
                
            fan_rpm = _read_int(os.path.join(hw, "fan1_input"), 0)
            pwm = _read_int(os.path.join(hw, "pwm1"), 0)
            pwm_max = _read_int(os.path.join(hw, "pwm1_max"), 255) or 255
            fan_pwm = pwm
            fan_pwm_pct = int((pwm / pwm_max) * 100) if pwm_max > 0 else 0
            
            v = _read_int(os.path.join(hw, "in0_input"), 0)
            voltage_mv = v if v else 0
            
        return {
            "gpu_busy": gpu_busy,
            "mem_busy": mem_busy,
            "vram_total_mb": vram_total_mb,
            "vram_used_mb": vram_used_mb,
            "vram_pct": vram_pct,
            "temp_edge": temp_edge,
            "temp_junction": temp_junction,
            "temp_mem": temp_mem,
            "sclk": sclk,
            "mclk": mclk,
            "power_w": power_w,
            "power_cap_w": power_cap_w,
            "fan_rpm": fan_rpm,
            "fan_pwm": fan_pwm,
            "fan_pwm_pct": fan_pwm_pct,
            "voltage_mv": voltage_mv,
        }
