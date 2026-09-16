"""FPS Limiter Engine for AMD Control Center.

Applies frame rate caps globally and per-game across:
- MangoHud (Vulkan & OpenGL) via ~/.config/MangoHud/MangoHud.conf and per-game configs
- DXVK (DirectX 9, 10, 11) via dxvk.conf (dxgi.maxFrameRate / d3d9.maxFrameRate)
- VKD3D-Proton (DirectX 12) via environment and MangoHud
- Game drop-in configs in game binary folders
"""

import os
import re
from pathlib import Path
from typing import Optional, List

MANGOHUD_CONF = Path.home() / ".config" / "MangoHud" / "MangoHud.conf"
MANGOHUD_DIR = Path.home() / ".config" / "MangoHud"
DXVK_CONF_GLOBAL = Path.home() / ".config" / "dxvk" / "dxvk.conf"


def sync_global_fps_limit(enabled: bool, fps: int):
    """Updates global MangoHud and DXVK configuration files."""
    MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
    target_fps = fps if (enabled and fps > 0) else 0

    # 1. Update ~/.config/MangoHud/MangoHud.conf
    if MANGOHUD_CONF.exists():
        try:
            content = MANGOHUD_CONF.read_text(encoding="utf-8")
            if re.search(r"^\s*fps_limit\s*=.*$", content, flags=re.MULTILINE):
                content = re.sub(r"^\s*fps_limit\s*=.*$", f"fps_limit={target_fps}", content, flags=re.MULTILINE)
            else:
                content += f"\nfps_limit={target_fps}\n"

            if not re.search(r"^\s*fps_limit_method\s*=.*$", content, flags=re.MULTILINE):
                content += "fps_limit_method=late\n"

            MANGOHUD_CONF.write_text(content, encoding="utf-8")
        except Exception:
            pass
    else:
        try:
            MANGOHUD_CONF.write_text(f"fps_limit_method=late\nfps_limit={target_fps}\n", encoding="utf-8")
        except Exception:
            pass

    # 2. Update ~/.config/dxvk/dxvk.conf
    DXVK_CONF_GLOBAL.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target_fps > 0:
            DXVK_CONF_GLOBAL.write_text(f"dxgi.maxFrameRate = {target_fps}\nd3d9.maxFrameRate = {target_fps}\n", encoding="utf-8")
        else:
            if DXVK_CONF_GLOBAL.exists():
                DXVK_CONF_GLOBAL.unlink()
    except Exception:
        pass


def find_game_executables(install_dir: str) -> List[Path]:
    """Finds primary game executables in install directory."""
    if not install_dir or not os.path.isdir(install_dir):
        return []

    p = Path(install_dir)
    exes: List[Path] = []
    # Search common executable subdirs first
    for sub in ["bin/x64", "bin", "Binaries/Win64", "Game/Binaries/Win64", ""]:
        target = p / sub if sub else p
        if target.is_dir():
            for item in target.glob("*.exe"):
                name_l = item.name.lower()
                if "crash" not in name_l and "reporter" not in name_l and "launcher" not in name_l and "unins" not in name_l and "scc" not in name_l:
                    if item not in exes:
                        exes.append(item)
    return exes


def sync_game_fps_limit(install_dir: str, enabled: bool, fps: int, mangohud_overlay: bool = False):
    """Writes per-game dxvk.conf and MangoHud per-process config files."""
    if not install_dir or not os.path.isdir(install_dir):
        return

    MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
    target_fps = fps if (enabled and fps > 0) else 0

    exes = find_game_executables(install_dir)

    for exe in exes:
        stem = exe.stem  # e.g. Cyberpunk2077

        # 1. Write ~/.config/MangoHud/<exe>.conf and ~/.config/MangoHud/wine-<exe>.conf
        conf_names = [f"{stem}.conf", f"wine-{stem}.conf"]
        for cname in conf_names:
            cpath = MANGOHUD_DIR / cname
            try:
                if target_fps > 0:
                    display_setting = "" if mangohud_overlay else "no_display\n"
                    cpath.write_text(
                        f"# AMD Control Center generated profile for {stem}\n"
                        f"{display_setting}"
                        f"fps_limit={target_fps}\n"
                        f"fps_limit_method=late\n",
                        encoding="utf-8"
                    )
                else:
                    if cpath.exists():
                        cpath.unlink()
            except Exception:
                pass

        # 2. Write dxvk.conf and MangoHud.conf in the executable's directory
        exe_dir = exe.parent
        dxvk_path = exe_dir / "dxvk.conf"
        mghud_path = exe_dir / "MangoHud.conf"

        try:
            if target_fps > 0:
                dxvk_path.write_text(
                    f"# AMD Control Center generated\n"
                    f"dxgi.maxFrameRate = {target_fps}\n"
                    f"d3d9.maxFrameRate = {target_fps}\n",
                    encoding="utf-8"
                )
                display_setting = "" if mangohud_overlay else "no_display\n"
                mghud_path.write_text(
                    f"# AMD Control Center generated\n"
                    f"{display_setting}"
                    f"fps_limit={target_fps}\n"
                    f"fps_limit_method=late\n",
                    encoding="utf-8"
                )
            else:
                if dxvk_path.exists():
                    dxvk_path.unlink()
                if mghud_path.exists():
                    mghud_path.unlink()
        except Exception:
            pass
