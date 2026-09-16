"""Game scanner for Steam, Heroic, Lutris, and Linux desktop games."""

import glob
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple


@dataclass
class GameInfo:
    app_id: str
    name: str
    platform: str  # "steam", "heroic", "lutris", "system"
    install_dir: str = ""
    executable: str = ""
    launch_command: str = ""
    banner_image: Optional[str] = None
    poster_image: Optional[str] = None
    last_played: int = 0
    size_mb: int = 0


def _parse_appmanifest(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        appid_m = re.search(r'"appid"\s+"(\d+)"', content)
        name_m = re.search(r'"name"\s+"([^"]+)"', content)
        dir_m = re.search(r'"installdir"\s+"([^"]+)"', content)
        last_played_m = re.search(r'"LastPlayed"\s+"(\d+)"', content)
        size_m = re.search(r'"SizeOnDisk"\s+"(\d+)"', content)
        
        if appid_m and name_m:
            appid = appid_m.group(1)
            name = name_m.group(1)
            if "Steamworks" in name or "Proton" in name or "Steam Linux Runtime" in name:
                return None
            return {
                "appid": appid,
                "name": name,
                "installdir": dir_m.group(1) if dir_m else "",
                "last_played": int(last_played_m.group(1)) if last_played_m else 0,
                "size_mb": int(int(size_m.group(1)) / (1024 * 1024)) if size_m else 0
            }
    except Exception:
        pass
    return None


def _find_steam_art(steam_cache_dir: str, appid: str) -> Tuple[Optional[str], Optional[str]]:
    base = os.path.join(steam_cache_dir, appid)
    poster = None
    banner = None
    if os.path.isdir(base):
        for root, _, files in os.walk(base):
            for f in files:
                if f in ["library_600x900.jpg", "library_capsule.jpg"] and not poster:
                    poster = os.path.join(root, f)
                elif f in ["library_hero.jpg", "library_header.jpg", "header.jpg"] and not banner:
                    banner = os.path.join(root, f)
    return poster, banner


def scan_steam_games() -> List[GameInfo]:
    games: List[GameInfo] = []
    home = os.path.expanduser("~")
    steam_roots = [
        os.path.join(home, ".local/share/Steam"),
        os.path.join(home, ".steam/steam"),
        os.path.join(home, ".var/app/com.valvesoftware.Steam/.local/share/Steam")
    ]
    
    steam_cache_dir = os.path.join(home, ".local/share/Steam/appcache/librarycache")
    
    library_folders = set()
    for root in steam_roots:
        if os.path.isdir(root):
            library_folders.add(root)
            vdf_path = os.path.join(root, "steamapps", "libraryfolders.vdf")
            if os.path.isfile(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    matches = re.findall(r'"path"\s+"([^"]+)"', text)
                    for p in matches:
                        if os.path.isdir(p):
                            library_folders.add(p)
                except Exception:
                    pass

    for lib in library_folders:
        steamapps = os.path.join(lib, "steamapps")
        if not os.path.isdir(steamapps):
            continue
            
        manifests = glob.glob(os.path.join(steamapps, "appmanifest_*.acf"))
        for mf in manifests:
            data = _parse_appmanifest(mf)
            if not data:
                continue
                
            appid = data["appid"]
            poster, banner = _find_steam_art(steam_cache_dir, appid)
            if not poster and banner:
                poster = banner
            if not banner and poster:
                banner = poster
                    
            game = GameInfo(
                app_id=f"steam_{appid}",
                name=data["name"],
                platform="steam",
                install_dir=os.path.join(steamapps, "common", data["installdir"]),
                launch_command=f"steam steam://rungameid/{appid}",
                poster_image=poster,
                banner_image=banner,
                last_played=data["last_played"],
                size_mb=data["size_mb"]
            )
            games.append(game)
            
    return games


def scan_desktop_games() -> List[GameInfo]:
    games: List[GameInfo] = []
    paths = [
        "/usr/share/applications/*.desktop",
        os.path.expanduser("~/.local/share/applications/*.desktop")
    ]
    seen_names = set()
    for pattern in paths:
        for f in glob.glob(pattern):
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                if "Categories=" in content and "Game;" in content:
                    name_m = re.search(r"^Name=(.+)$", content, re.MULTILINE)
                    exec_m = re.search(r"^Exec=(.+)$", content, re.MULTILINE)
                    icon_m = re.search(r"^Icon=(.+)$", content, re.MULTILINE)
                    if name_m and exec_m:
                        name = name_m.group(1).strip()
                        if name in seen_names or "Steam" in name:
                            continue
                        seen_names.add(name)
                        cmd = exec_m.group(1).strip().split("%")[0].strip()
                        icon = icon_m.group(1).strip() if icon_m else None
                        games.append(GameInfo(
                            app_id=f"desktop_{os.path.basename(f).replace('.desktop', '')}",
                            name=name,
                            platform="system",
                            launch_command=cmd,
                            poster_image=icon if icon and os.path.isfile(icon) else None,
                            last_played=0
                        ))
            except Exception:
                pass
    return games


def scan_all_games() -> List[GameInfo]:
    """Scans all platforms and returns games sorted by last played descending."""
    all_games = []
    steam = scan_steam_games()
    all_games.extend(steam)
    
    desktop = scan_desktop_games()
    all_games.extend(desktop)
    
    # Sort by last played descending (most recently played first), then alphabetical
    all_games.sort(key=lambda g: (-g.last_played, g.name.lower()))
    return all_games
