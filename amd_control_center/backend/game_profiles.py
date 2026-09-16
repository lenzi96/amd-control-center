"""Game graphic profile manager and launcher with FSR 4 Injection."""

import json
import os
import subprocess
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from .fsr4_injector import FSR4Config, get_fsr4_env_vars
from .fps_limiter import sync_global_fps_limit, sync_game_fps_limit


@dataclass
class GameGraphicProfile:
    app_id: str
    anti_lag: bool = True
    fsr_enabled: bool = False
    fsr_sharpness: int = 2
    # FSR 4 (AI Neural Super Resolution & Frame Gen)
    fsr4_enabled: bool = True
    fsr4_quality: str = "Quality"  # "Ultra Quality", "Quality", "Balanced", "Performance", "Ultra Performance"
    fsr4_sharpness: int = 70       # 0 - 100
    fsr4_frame_gen: bool = True    # AFMF 2 / AI Frame Gen
    fsr4_injection_method: str = "proton_nvapi"  # "proton_nvapi", "gamescope", "optiscaler"
    fsr4_indicator: bool = True    # On-screen FSR 4 status watermark
    # FPS Limiter (Radeon Chill / FRTC)
    fps_limit_enabled: bool = False
    fps_limit: int = 144
    radeon_boost: bool = False
    image_sharpening: bool = True
    mangohud: bool = False
    gamescope: bool = False
    gamescope_res: str = "3840x2160"
    power_profile: str = "3D_FULL_SCREEN"
    custom_env: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameGraphicProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProfileManager:
    """Manages persistent profiles for games and global graphics defaults."""

    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/amd-control-center")
        self.config_file = os.path.join(self.config_dir, "game_profiles.json")
        self.profiles: Dict[str, GameGraphicProfile] = {}
        self.game_dirs: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self.profiles[k] = GameGraphicProfile.from_dict(v)
            except Exception:
                pass

    def register_game_directory(self, app_id: str, install_dir: str):
        if install_dir:
            self.game_dirs[app_id] = install_dir

    def sync_fps_limits(self):
        try:
            glob = self.get_profile("global")
            sync_global_fps_limit(glob.fps_limit_enabled, glob.fps_limit)

            for app_id, prof in self.profiles.items():
                if app_id != "global":
                    idir = self.game_dirs.get(app_id, "")
                    if idir:
                        sync_game_fps_limit(idir, prof.fps_limit_enabled, prof.fps_limit, prof.mangohud)
        except Exception:
            pass

    def save(self):
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            data = {k: v.to_dict() for k, v in self.profiles.items()}
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
        self.sync_fps_limits()

    def get_profile(self, app_id: str) -> GameGraphicProfile:
        if app_id not in self.profiles:
            self.profiles[app_id] = GameGraphicProfile(app_id=app_id)
        return self.profiles[app_id]

    def set_profile(self, app_id: str, profile: GameGraphicProfile):
        self.profiles[app_id] = profile
        self.save()

    def launch_game(self, app_id: str, base_command: str) -> bool:
        """Launches game with applied graphic & FSR 4 environment variables."""
        profile = self.get_profile(app_id)
        env = os.environ.copy()

        # 1. Anti-Lag & Low Latency
        if profile.anti_lag:
            env["MESA_VK_WSI_PRESENT_MODE"] = "mailbox"

        # 2. Legacy FSR 1/2
        if profile.fsr_enabled:
            env["WINE_FULLSCREEN_FSR"] = "1"
            env["WINE_FULLSCREEN_FSR_STRENGTH"] = str(profile.fsr_sharpness)

        # 3. Next-Gen FSR 4 AI Neural Injection
        if profile.fsr4_enabled:
            fsr4_cfg = FSR4Config(
                enabled=True,
                quality_mode=profile.fsr4_quality,
                sharpness=profile.fsr4_sharpness,
                frame_gen_enabled=profile.fsr4_frame_gen,
                injection_method=profile.fsr4_injection_method,
                indicator_enabled=profile.fsr4_indicator
            )
            fsr4_env = get_fsr4_env_vars(fsr4_cfg)
            env.update(fsr4_env)

        # 4. FPS Limiter (Radeon Chill / FRTC / DXVK / VKD3D / MangoHud)
        if profile.fps_limit_enabled and profile.fps_limit > 0:
            limit_str = str(profile.fps_limit)
            env["DXVK_FRAME_RATE"] = limit_str
            env["VKD3D_FRAME_RATE"] = limit_str
            env["FSR4_FPS_LIMIT"] = limit_str
            if "MANGOHUD_CONFIG" in env:
                env["MANGOHUD_CONFIG"] = f"{env['MANGOHUD_CONFIG']},fps_limit={limit_str}"
            else:
                env["MANGOHUD_CONFIG"] = f"fps_limit={limit_str}"

        # 5. Boost / VRS
        if profile.radeon_boost:
            env["RADV_FORCE_VRS"] = "2x2"

        # 6. MangoHud
        if profile.mangohud:
            env["MANGOHUD"] = "1"

        # Custom env overrides
        if profile.custom_env:
            for item in profile.custom_env.split():
                if "=" in item:
                    k, v = item.split("=", 1)
                    env[k.strip()] = v.strip()

        # Wrapper: Gamescope
        cmd = base_command
        if profile.gamescope:
            res_w, res_h = "3840", "2160"
            if "x" in profile.gamescope_res:
                parts = profile.gamescope_res.split("x")
                res_w, res_h = parts[0], parts[1]
            fsr_flag = "-F fsr" if profile.fsr4_enabled or profile.fsr_enabled else ""
            fps_flag = f"-r {profile.fps_limit}" if profile.fps_limit_enabled and profile.fps_limit > 0 else ""
            cmd = f"gamescope -W {res_w} -H {res_h} {fsr_flag} {fps_flag} -f -- {base_command}"

        try:
            subprocess.Popen(cmd, shell=True, env=env)
            return True
        except Exception:
            return False
