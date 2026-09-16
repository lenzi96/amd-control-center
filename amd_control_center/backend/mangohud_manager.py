"""MangoHud Configuration Manager for AMD Control Center.

Handles reading, updating, applying presets, and persisting MangoHud overlay settings
to ~/.config/MangoHud/MangoHud.conf while safely preserving custom lines, colors, and blacklists.
"""

import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

MANGOHUD_DIR = Path.home() / ".config" / "MangoHud"
MANGOHUD_CONF = MANGOHUD_DIR / "MangoHud.conf"


@dataclass
class MangoHudConfig:
    # 1. Overlay Layout & Appearance
    position: str = "top-left"               # top-left, top-right, bottom-left, bottom-right, top-center, bottom-center
    font_size: int = 24                     # 16 - 48
    background_alpha: float = 0.6           # 0.0 - 1.0
    round_corners: int = 0                  # 0 - 20
    table_columns: int = 3                  # 1 - 6
    toggle_hud: str = "Shift_R+F12"         # Hotkey
    no_display: bool = False                # Start hidden until hotkey

    # 2. Framerate & Timing
    fps: bool = True
    frame_timing: bool = True
    fps_limit: int = 0
    fps_limit_method: str = "late"

    # 3. GPU Metrics (AMD Radeon)
    gpu_stats: bool = True
    gpu_temp: bool = True
    gpu_junction_temp: bool = False
    gpu_core_clock: bool = True
    gpu_mem_clock: bool = True
    gpu_power: bool = True
    gpu_voltage: bool = False
    vram: bool = True

    # 4. CPU & System Metrics
    cpu_stats: bool = True
    cpu_temp: bool = True
    cpu_mhz: bool = True
    cpu_power: bool = True
    core_load: bool = False
    ram: bool = True

    # 5. Advanced & System Info
    arch: bool = False
    wine: bool = False
    vulkan_driver: bool = False
    resolution: bool = False
    gamemode: bool = False
    fsr: bool = False
    time: bool = False

    # Internal storage for unmanaged lines (colors, blacklist, etc.)
    extra_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Recognized boolean flags in MangoHud
BOOLEAN_FLAGS = {
    "gpu_stats", "gpu_temp", "gpu_junction_temp", "gpu_core_clock",
    "gpu_mem_clock", "gpu_power", "gpu_voltage", "vram",
    "cpu_stats", "cpu_temp", "cpu_mhz", "cpu_power", "core_load", "ram",
    "fps", "frame_timing",
    "arch", "wine", "vulkan_driver", "resolution", "gamemode", "fsr", "time",
    "no_display"
}

# Recognized key-value parameters
KV_PARAMETERS = {
    "position", "font_size", "background_alpha", "round_corners",
    "table_columns", "toggle_hud", "fps_limit", "fps_limit_method"
}


def load_mangohud_config() -> MangoHudConfig:
    """Reads ~/.config/MangoHud/MangoHud.conf and parses settings into MangoHudConfig."""
    config = MangoHudConfig()
    if not MANGOHUD_CONF.is_file():
        return config

    try:
        content = MANGOHUD_CONF.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return config

    active_flags = set()
    extra_lines = []

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            extra_lines.append(line)
            continue

        if "=" in stripped:
            key, val = [x.strip() for x in stripped.split("=", 1)]
            k_lower = key.lower()

            if k_lower == "position":
                config.position = val
            elif k_lower == "font_size":
                try:
                    config.font_size = int(val)
                except ValueError:
                    pass
            elif k_lower == "background_alpha":
                try:
                    config.background_alpha = float(val)
                except ValueError:
                    pass
            elif k_lower == "round_corners":
                try:
                    config.round_corners = int(val)
                except ValueError:
                    pass
            elif k_lower == "table_columns":
                try:
                    config.table_columns = int(val)
                except ValueError:
                    pass
            elif k_lower == "toggle_hud":
                config.toggle_hud = val
            elif k_lower == "fps_limit":
                try:
                    first_val = val.split(",")[0].strip()
                    config.fps_limit = int(first_val)
                except ValueError:
                    pass
            elif k_lower == "fps_limit_method":
                config.fps_limit_method = val
            elif k_lower in BOOLEAN_FLAGS:
                if val.lower() in ("1", "true", "yes"):
                    active_flags.add(k_lower)
            else:
                extra_lines.append(line)
        else:
            flag = stripped.lower()
            if flag in BOOLEAN_FLAGS:
                active_flags.add(flag)
            else:
                extra_lines.append(line)

    for flag in BOOLEAN_FLAGS:
        setattr(config, flag, flag in active_flags)

    config.extra_lines = extra_lines
    return config


def save_mangohud_config(config: MangoHudConfig) -> Tuple[bool, str]:
    """Writes MangoHudConfig to ~/.config/MangoHud/MangoHud.conf while preserving extra lines."""
    try:
        MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)

        lines: List[str] = [
            "################### AMD Software: Adrenalin Edition (Linux) ###################",
            "### Generated / Updated by AMD Control Center (MangoHud Manager)",
            "legacy_layout=0",
            f"position={config.position}",
            f"font_size={config.font_size}",
            f"background_alpha={config.background_alpha:.2f}",
            f"round_corners={config.round_corners}",
            f"table_columns={config.table_columns}",
            f"toggle_hud={config.toggle_hud}",
            f"fps_limit={config.fps_limit}",
            f"fps_limit_method={config.fps_limit_method}",
            ""
        ]

        if config.no_display:
            lines.append("no_display")

        # Performance & Timing
        lines.append("\n### Framerate & Timing")
        if config.fps:
            lines.append("fps")
        if config.frame_timing:
            lines.append("frame_timing")

        # GPU Metrics
        lines.append("\n### GPU Metrics (AMD Radeon)")
        if config.gpu_stats:
            lines.append("gpu_stats")
        if config.gpu_temp:
            lines.append("gpu_temp")
        if config.gpu_junction_temp:
            lines.append("gpu_junction_temp")
        if config.gpu_core_clock:
            lines.append("gpu_core_clock")
        if config.gpu_mem_clock:
            lines.append("gpu_mem_clock")
        if config.gpu_power:
            lines.append("gpu_power")
        if config.gpu_voltage:
            lines.append("gpu_voltage")
        if config.vram:
            lines.append("vram")

        # CPU & RAM Metrics
        lines.append("\n### CPU & RAM Metrics")
        if config.cpu_stats:
            lines.append("cpu_stats")
        if config.cpu_temp:
            lines.append("cpu_temp")
        if config.cpu_mhz:
            lines.append("cpu_mhz")
        if config.cpu_power:
            lines.append("cpu_power")
        if config.core_load:
            lines.append("core_load")
        if config.ram:
            lines.append("ram")

        # Advanced Info
        lines.append("\n### Advanced System Info")
        if config.arch:
            lines.append("arch")
        if config.wine:
            lines.append("wine")
        if config.vulkan_driver:
            lines.append("vulkan_driver")
        if config.resolution:
            lines.append("resolution")
        if config.gamemode:
            lines.append("gamemode")
        if config.fsr:
            lines.append("fsr")
        if config.time:
            lines.append("time")

        # Append extra lines (like colors, blacklist, log output folder)
        if config.extra_lines:
            lines.append("\n### Custom & User Settings (Preserved)")
            for el in config.extra_lines:
                if not el.startswith("### Generated"):
                    lines.append(el)

        lines.append("")
        MANGOHUD_CONF.write_text("\n".join(lines), encoding="utf-8")
        return True, "MangoHud Konfiguration erfolgreich gespeichert."
    except Exception as e:
        return False, f"Fehler beim Speichern der MangoHud Konfiguration: {e}"


def get_mangohud_presets() -> Dict[str, Dict[str, Any]]:
    """Returns standard preconfigured overlay profiles."""
    return {
        "Minimal": {
            "font_size": 22,
            "table_columns": 2,
            "fps": True,
            "frame_timing": False,
            "gpu_stats": False,
            "gpu_temp": False,
            "gpu_junction_temp": False,
            "gpu_core_clock": False,
            "gpu_mem_clock": False,
            "gpu_power": False,
            "vram": False,
            "cpu_stats": False,
            "cpu_temp": False,
            "cpu_mhz": False,
            "cpu_power": False,
            "core_load": False,
            "ram": False,
            "arch": False,
            "wine": False,
            "vulkan_driver": False,
            "resolution": False,
            "gamemode": False,
            "fsr": False,
            "time": False,
        },
        "Kompakt": {
            "font_size": 22,
            "table_columns": 3,
            "fps": True,
            "frame_timing": True,
            "gpu_stats": True,
            "gpu_temp": True,
            "gpu_junction_temp": False,
            "gpu_core_clock": False,
            "gpu_mem_clock": False,
            "gpu_power": False,
            "vram": True,
            "cpu_stats": True,
            "cpu_temp": True,
            "cpu_mhz": False,
            "cpu_power": False,
            "core_load": False,
            "ram": True,
            "arch": False,
            "wine": False,
            "vulkan_driver": False,
            "resolution": False,
            "gamemode": False,
            "fsr": False,
            "time": False,
        },
        "Standard (Adrenalin)": {
            "font_size": 24,
            "table_columns": 3,
            "fps": True,
            "frame_timing": True,
            "gpu_stats": True,
            "gpu_temp": True,
            "gpu_junction_temp": True,
            "gpu_core_clock": True,
            "gpu_mem_clock": True,
            "gpu_power": True,
            "vram": True,
            "cpu_stats": True,
            "cpu_temp": True,
            "cpu_mhz": True,
            "cpu_power": True,
            "core_load": False,
            "ram": True,
            "arch": False,
            "wine": False,
            "vulkan_driver": False,
            "resolution": False,
            "gamemode": False,
            "fsr": True,
            "time": False,
        },
        "Vollständig (Alle Details)": {
            "font_size": 24,
            "table_columns": 3,
            "fps": True,
            "frame_timing": True,
            "gpu_stats": True,
            "gpu_temp": True,
            "gpu_junction_temp": True,
            "gpu_core_clock": True,
            "gpu_mem_clock": True,
            "gpu_power": True,
            "gpu_voltage": True,
            "vram": True,
            "cpu_stats": True,
            "cpu_temp": True,
            "cpu_mhz": True,
            "cpu_power": True,
            "core_load": True,
            "ram": True,
            "arch": True,
            "wine": True,
            "vulkan_driver": True,
            "resolution": True,
            "gamemode": True,
            "fsr": True,
            "time": True,
        }
    }


def apply_preset(preset_name: str, config: MangoHudConfig):
    """Applies a named preset to the given config object in-place."""
    presets = get_mangohud_presets()
    if preset_name in presets:
        for k, v in presets[preset_name].items():
            if hasattr(config, k):
                setattr(config, k, v)
