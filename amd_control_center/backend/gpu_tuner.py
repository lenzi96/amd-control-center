"""GPU Overclocking, Undervolting, Fan Control, and Power Limit management."""

import json
import os
import subprocess
import sys
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class TuningProfile:
    name: str = "Default"
    sclk_offset_mhz: int = 0
    vddc_offset_mv: int = 0
    mclk_mhz: int = 0
    power_limit_w: float = 330.0
    zero_rpm: bool = True
    manual_fan: bool = False
    fan_speed_pct: int = 50
    fan_curve: list = None  # [[temp, speed_pct], ...]
    power_profile_mode: str = "BOOTUP_DEFAULT"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.fan_curve is None:
            d["fan_curve"] = [[30, 0], [50, 35], [65, 55], [75, 75], [85, 100]]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TuningProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def apply_tuning_direct(card_dir: str, hwmon_dir: str, profile: TuningProfile) -> Tuple[bool, str]:
    """Applies tuning parameters directly to sysfs. Requires write permissions."""
    errors = []
    
    # 1. Power Limit
    if profile.power_limit_w > 0 and hwmon_dir:
        cap_file = os.path.join(hwmon_dir, "power1_cap")
        if os.path.exists(cap_file):
            try:
                microwatts = int(profile.power_limit_w * 1000000)
                with open(cap_file, "w") as f:
                    f.write(str(microwatts))
            except Exception as e:
                errors.append(f"Power Cap error: {e}")

    # 2. Overdrive Clock & Voltage
    od_file = os.path.join(card_dir, "pp_od_clk_voltage")
    if os.path.exists(od_file):
        try:
            # Set performance level to manual if needed
            perf_level_file = os.path.join(card_dir, "power_dpm_force_performance_level")
            if os.path.exists(perf_level_file):
                with open(perf_level_file, "w") as f:
                    f.write("manual")

            with open(od_file, "w") as f:
                # SCLK offset
                f.write(f"s 0 {profile.sclk_offset_mhz}\n")
                f.flush()
                # Voltage offset
                f.write(f"vo {profile.vddc_offset_mv}\n")
                f.flush()
                # MCLK if set
                if profile.mclk_mhz > 0:
                    f.write(f"m 1 {profile.mclk_mhz}\n")
                    f.flush()
                # Commit
                f.write("c\n")
                f.flush()
        except Exception as e:
            errors.append(f"Overdrive error: {e}")

    # 3. Power Profile Mode
    ppm_file = os.path.join(card_dir, "pp_power_profile_mode")
    if os.path.exists(ppm_file) and profile.power_profile_mode:
        try:
            # Read available profiles to find index
            with open(ppm_file, "r") as f:
                lines = f.readlines()
            prof_idx = None
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].isdigit():
                    name = parts[1].replace("*", "").replace(":", "")
                    if name == profile.power_profile_mode:
                        prof_idx = parts[0]
                        break
            if prof_idx is not None:
                with open(ppm_file, "w") as f:
                    f.write(str(prof_idx))
        except Exception as e:
            errors.append(f"Power profile error: {e}")

    # 4. Fan Control
    if hwmon_dir:
        pwm_enable = os.path.join(hwmon_dir, "pwm1_enable")
        pwm_file = os.path.join(hwmon_dir, "pwm1")
        if profile.manual_fan:
            if os.path.exists(pwm_enable):
                try:
                    with open(pwm_enable, "w") as f:
                        f.write("1")  # Manual
                except Exception:
                    pass
            if os.path.exists(pwm_file):
                try:
                    val = int((profile.fan_speed_pct / 100.0) * 255)
                    with open(pwm_file, "w") as f:
                        f.write(str(val))
                except Exception as e:
                    errors.append(f"Fan speed error: {e}")
        else:
            # Automatic fan mode
            if os.path.exists(pwm_enable):
                try:
                    with open(pwm_enable, "w") as f:
                        f.write("2")  # Auto
                except Exception:
                    pass

    if errors:
        return False, "; ".join(errors)
    return True, "Settings applied successfully."


def reset_tuning_direct(card_dir: str, hwmon_dir: str, default_power_w: float) -> Tuple[bool, str]:
    """Resets tuning to factory defaults."""
    errors = []
    
    # 1. Reset Overdrive
    od_file = os.path.join(card_dir, "pp_od_clk_voltage")
    if os.path.exists(od_file):
        try:
            with open(od_file, "w") as f:
                f.write("r\n")
                f.flush()
                f.write("c\n")
                f.flush()
        except Exception as e:
            errors.append(f"Overdrive reset error: {e}")

    # 2. Reset Performance level to auto
    perf_file = os.path.join(card_dir, "power_dpm_force_performance_level")
    if os.path.exists(perf_file):
        try:
            with open(perf_file, "w") as f:
                f.write("auto")
        except Exception as e:
            errors.append(f"Perf level error: {e}")

    # 3. Reset Power Cap
    if hwmon_dir and default_power_w > 0:
        cap_file = os.path.join(hwmon_dir, "power1_cap")
        if os.path.exists(cap_file):
            try:
                microwatts = int(default_power_w * 1000000)
                with open(cap_file, "w") as f:
                    f.write(str(microwatts))
            except Exception as e:
                errors.append(f"Power cap reset error: {e}")

    # 4. Reset Fan to Auto
    if hwmon_dir:
        pwm_enable = os.path.join(hwmon_dir, "pwm1_enable")
        if os.path.exists(pwm_enable):
            try:
                with open(pwm_enable, "w") as f:
                    f.write("2")
            except Exception:
                pass

    if errors:
        return False, "; ".join(errors)
    return True, "GPU reset to default settings."


def execute_via_pkexec(card_dir: str, hwmon_dir: str, profile: Optional[TuningProfile], reset: bool = False, default_power_w: float = 330.0) -> Tuple[bool, str]:
    """Executes the tuner with elevated privileges using pkexec."""
    payload = {
        "card_dir": card_dir,
        "hwmon_dir": hwmon_dir,
        "reset": reset,
        "default_power_w": default_power_w,
        "profile": profile.to_dict() if profile else None
    }
    tmp_path = "/tmp/amd_tuning_cmd.json"
    with open(tmp_path, "w") as f:
        json.dump(payload, f)

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
            c_dir = data["card_dir"]
            h_dir = data["hwmon_dir"]
            is_reset = data.get("reset", False)
            def_p = data.get("default_power_w", 330.0)
            
            if is_reset:
                ok, msg = reset_tuning_direct(c_dir, h_dir, def_p)
            else:
                prof = TuningProfile.from_dict(data["profile"])
                ok, msg = apply_tuning_direct(c_dir, h_dir, prof)
                
            print(msg)
            try:
                os.remove(json_file)
            except Exception:
                pass
            sys.exit(0 if ok else 1)
