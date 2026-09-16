"""Display and FreeSync/VRR discovery."""

import glob
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DisplayInfo:
    connector: str
    connected: bool
    resolution: str = "3840x2160"
    refresh_rate_hz: float = 144.0
    is_primary: bool = False
    vrr_enabled: bool = True
    vrr_supported: bool = True
    hdr_enabled: bool = False


def detect_displays() -> List[DisplayInfo]:
    displays: List[DisplayInfo] = []

    # First attempt: kscreen-doctor (Most accurate on KDE Plasma Wayland)
    try:
        ks = subprocess.getoutput("kscreen-doctor -o 2>/dev/null")
        if "Output:" in ks:
            blocks = ks.split("Output:")
            for b in blocks[1:]:
                conn_m = re.search(r"^\s*\d+\s+([A-Za-z0-9\-_]+)", b)
                conn = conn_m.group(1) if conn_m else "Display"
                connected = "connected" in b
                if not connected:
                    continue

                res = "3840x2160"
                hz = 144.0
                mode_m = re.search(r"Modes:\s+.*?(\d+x\d+)@([\d\.]+)\*!", b)
                if mode_m:
                    res = mode_m.group(1)
                    hz = float(mode_m.group(2))

                vrr_m = re.search(r"Vrr:\s+([A-Za-z]+)", b)
                vrr_val = vrr_m.group(1) if vrr_m else "Automatic"
                vrr_supported = vrr_val.lower() != "unsupported"
                vrr_enabled = vrr_val.lower() in ["automatic", "always", "enabled"]

                hdr_m = re.search(r"HDR:\s+([A-Za-z]+)", b)
                hdr_enabled = "enabled" in (hdr_m.group(1).lower() if hdr_m else "")

                displays.append(DisplayInfo(
                    connector=conn,
                    connected=True,
                    resolution=res,
                    refresh_rate_hz=round(hz, 1),
                    is_primary=True,
                    vrr_enabled=vrr_enabled,
                    vrr_supported=vrr_supported,
                    hdr_enabled=hdr_enabled
                ))
            if displays:
                return displays
    except Exception:
        pass

    # Fallback: sysfs DRM connectors
    connectors = glob.glob("/sys/class/drm/card*-*")
    for conn_path in connectors:
        status_f = os.path.join(conn_path, "status")
        if os.path.isfile(status_f):
            try:
                with open(status_f) as fp:
                    st = fp.read().strip()
                if st == "connected":
                    name = os.path.basename(conn_path).split("-", 1)[1] if "-" in os.path.basename(conn_path) else os.path.basename(conn_path)
                    modes_f = os.path.join(conn_path, "modes")
                    res = "3840x2160"
                    if os.path.isfile(modes_f):
                        with open(modes_f) as mfp:
                            lines = mfp.readlines()
                            if lines:
                                res = lines[0].strip()
                    displays.append(DisplayInfo(
                        connector=name,
                        connected=True,
                        resolution=res,
                        refresh_rate_hz=144.0,
                        vrr_enabled=True,
                        vrr_supported=True
                    ))
            except Exception:
                pass

    return displays
