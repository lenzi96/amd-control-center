"""Autostart Manager for AMD Software: Adrenalin Edition.

Manages XDG Autostart (.config/autostart/amd-control-center.desktop) to start the
control center automatically in the system tray on user login.
"""

import os
import shutil
from pathlib import Path


def get_autostart_path() -> Path:
    """Returns the path to the XDG autostart desktop file."""
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_dir / "autostart" / "amd-control-center.desktop"


def is_autostart_enabled() -> bool:
    """Checks if autostart is currently configured and active."""
    target = get_autostart_path()
    if not target.is_file():
        return False

    try:
        content = target.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("Hidden=") and line.split("=", 1)[1].strip().lower() == "true":
                return False
            if line.startswith("X-GNOME-Autostart-enabled=") and line.split("=", 1)[1].strip().lower() == "false":
                return False
        return True
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables autostart on system boot/login."""
    target = get_autostart_path()

    try:
        if not enabled:
            if target.exists():
                target.unlink()
            return True

        # Ensure directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        # Locate executable
        local_bin = Path.home() / ".local" / "bin" / "amd-control-center"
        if local_bin.exists():
            exec_cmd = f"{local_bin} --tray"
        elif shutil.which("amd-control-center"):
            exec_cmd = "amd-control-center --tray"
        else:
            # Fallback to repo root if run in-place
            repo_bin = Path(__file__).resolve().parent.parent.parent / "amd-control-center"
            if repo_bin.exists():
                exec_cmd = f"{repo_bin} --tray"
            else:
                exec_cmd = "amd-control-center --tray"

        content = f"""[Desktop Entry]
Name=AMD Software: Adrenalin Edition
Comment=AMD Radeon GPU Control Center (System Tray)
GenericName=AMD GPU Control Center
Exec={exec_cmd}
Icon=amd-control-center
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;
X-GNOME-Autostart-enabled=true
Hidden=false
StartupNotify=false
X-KDE-autostart-after=panel
"""
        target.write_text(content, encoding="utf-8")
        target.chmod(0o644)
        return True
    except Exception as e:
        print(f"Error updating autostart configuration: {e}")
        return False
