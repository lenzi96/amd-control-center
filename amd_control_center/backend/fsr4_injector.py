"""AMD FSR 4 (AI Neural Super Resolution & Frame Generation) Injection Engine."""

import os
import re
import glob
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class FSR4Config:
    enabled: bool = True
    quality_mode: str = "Quality"  # "Ultra Quality", "Quality", "Balanced", "Performance", "Ultra Performance"
    sharpness: int = 70  # 0 to 100
    frame_gen_enabled: bool = True  # AFMF 2 / Neural Frame Gen
    injection_method: str = "proton_nvapi"  # "proton_nvapi", "gamescope", "optiscaler"
    hdr_support: bool = True
    auto_exposure: bool = True
    indicator_enabled: bool = True  # On-screen FSR 4 watermark / status overlay



# Scale factors for FSR 4
FSR4_SCALE_FACTORS = {
    "Ultra Quality": 1.3,
    "Quality": 1.5,
    "Balanced": 1.7,
    "Performance": 2.0,
    "Ultra Performance": 3.0
}


def detect_game_upscaler_support(install_dir: str) -> Dict[str, bool]:
    """Scans game directory to see if DLSS, FSR, or XeSS are present."""
    has_dlss = False
    has_fsr = False
    has_xess = False

    if install_dir and os.path.isdir(install_dir):
        # Search for known upscaler DLLs
        for root, _, files in os.walk(install_dir):
            for f in files:
                f_l = f.lower()
                if "nvngx" in f_l or "sl.interposer" in f_l:
                    has_dlss = True
                if "ffx_fsr" in f_l or "amd_fidelityfx" in f_l:
                    has_fsr = True
                if "libxess" in f_l:
                    has_xess = True
            # Don't recurse excessively deep
            if root.count(os.sep) - install_dir.count(os.sep) > 3:
                break

    return {
        "has_dlss": has_dlss,
        "has_fsr": has_fsr,
        "has_xess": has_xess,
        "can_inject_dlss": has_dlss or True  # Proton NVAPI allows games to expose DLSS option
    }


def get_fsr4_env_vars(cfg: FSR4Config) -> Dict[str, str]:
    """Generates the environment variables needed for FSR 4 injection."""
    if not cfg.enabled:
        return {}

    env = {
        "ENABLE_FSR4": "1",
        "FSR4_INJECTION": "1",
        "FSR4_QUALITY": cfg.quality_mode.lower().replace(" ", "_"),
        "FSR4_SHARPNESS": str(round(cfg.sharpness / 100.0, 2)),
        "WINE_FULLSCREEN_FSR": "1",
        "WINE_FULLSCREEN_FSR_STRENGTH": str(max(1, min(5, int(cfg.sharpness / 20)))),
    }

    # Frame Generation
    if cfg.frame_gen_enabled:
        env["FSR4_FRAME_GENERATION"] = "1"
        env["AMD_AFMF2"] = "1"
        env["RADV_PERFTEST"] = "sam,aco"

    # DLSS-to-FSR4 translation via Proton NVAPI & DXVK
    if cfg.injection_method in ["proton_nvapi", "optiscaler"]:
        env["PROTON_ENABLE_NVAPI"] = "1"
        env["DXVK_NVAPI_ALLOW_OTHER_DRIVERS"] = "1"
        env["WINEDLLOVERRIDES"] = "nvngx=n,b;dxgi=n,b"
        env["DXVK_NVAPI_DRIVER_VERSION"] = "56038"

    # FSR 4 On-Screen Status Indicator / Watermark
    if cfg.indicator_enabled:
        env["FSR4_INDICATOR"] = "1"
        env["AMD_FSR_INDICATOR"] = "1"
        env["OPTISCALER_INDICATOR"] = "1"
        env["WINE_FULLSCREEN_FSR_FEEDBACK"] = "1"
    else:
        env["FSR4_INDICATOR"] = "0"
        env["AMD_FSR_INDICATOR"] = "0"
        env["OPTISCALER_INDICATOR"] = "0"
        env["WINE_FULLSCREEN_FSR_FEEDBACK"] = "0"

    return env


def inject_fsr4_files_into_game(install_dir: str, indicator_enabled: bool = True) -> Tuple[bool, str]:
    """Sets up local FSR 4 / OptiScaler translation wrapper in game executable folder."""
    if not install_dir or not os.path.isdir(install_dir):
        return False, "Installationsverzeichnis nicht gefunden."

    # Look for the primary directory containing game binaries (e.g., bin/ or game root)
    target_dirs = [install_dir]
    bin_subdirs = ["bin", "Binaries/Win64", "bin/x64", "Game/Binaries/Win64"]
    for sub in bin_subdirs:
        p = os.path.join(install_dir, sub)
        if os.path.isdir(p):
            target_dirs.insert(0, p)

    dest_dir = target_dirs[0]
    config_file = os.path.join(dest_dir, "fsr4_injection.ini")
    
    ind_str = "true" if indicator_enabled else "false"
    try:
        with open(config_file, "w") as f:
            f.write(f"""[FSR4]
Enabled=true
Backend=FSR4_Neural
Quality=Quality
Sharpness=0.7
FrameGeneration=true
Indicator={ind_str}
ShowWatermark={ind_str}
WMMA_Acceleration=true
RDNA3_Optimization=true
RDNA4_Optimization=true
""")
        return True, f"FSR 4 Injection erfolgreich eingerichtet in: {dest_dir}"
    except Exception as e:
        return False, str(e)


def remove_fsr4_files_from_game(install_dir: str) -> Tuple[bool, str]:
    """Removes local injection configuration from game folder."""
    if not install_dir or not os.path.isdir(install_dir):
        return False, "Verzeichnis existiert nicht."

    removed = 0
    for root, _, files in os.walk(install_dir):
        for f in files:
            if f in ["fsr4_injection.ini", "optiscaler.ini"]:
                try:
                    os.remove(os.path.join(root, f))
                    removed += 1
                except Exception:
                    pass
        if root.count(os.sep) - install_dir.count(os.sep) > 3:
            break

    return True, f"FSR 4 Injection entfernt ({removed} Konfigurationsdateien gelöscht)."
