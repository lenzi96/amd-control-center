"""System, Driver, and PCIe link information audit."""

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SystemAudit:
    mesa_version: str = "Unknown"
    vulkan_version: str = "Unknown"
    vulkan_driver: str = "Mesa RADV"
    opengl_version: str = "Unknown"
    kernel_version: str = ""
    os_name: str = ""
    desktop_env: str = ""
    session_type: str = ""
    pcie_link_speed: str = "Unknown"
    pcie_link_width: str = "Unknown"


def audit_system(card_device_dir: str = "") -> SystemAudit:
    kernel = platform.release()
    os_name = "Linux"
    if os.path.isfile("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_name = line.split("=")[1].strip().strip('"')
                        break
        except Exception:
            pass

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
    session = os.environ.get("XDG_SESSION_TYPE", "wayland")

    # Mesa version via glxinfo or pacman
    mesa_ver = "Unknown"
    gl_ver = "Unknown"
    try:
        glx = subprocess.getoutput("glxinfo -B 2>/dev/null")
        for line in glx.splitlines():
            if "OpenGL core profile version string:" in line:
                gl_ver = line.split("string:")[1].strip()
            elif "OpenGL version string:" in line and gl_ver == "Unknown":
                gl_ver = line.split("string:")[1].strip()
            if "Mesa" in line and mesa_ver == "Unknown":
                parts = line.split("Mesa")
                if len(parts) > 1:
                    mesa_ver = "Mesa " + parts[1].strip().split()[0]
    except Exception:
        pass

    if mesa_ver == "Unknown":
        try:
            pac = subprocess.getoutput("pacman -Q mesa 2>/dev/null")
            if pac:
                mesa_ver = pac.strip()
        except Exception:
            pass

    # Vulkan
    vk_ver = "1.4"
    vk_driver = "Mesa RADV"
    try:
        vk_info = subprocess.getoutput("vulkaninfo --summary 2>/dev/null")
        for line in vk_info.splitlines():
            if "Vulkan Instance Version:" in line:
                vk_ver = line.split(":")[1].strip()
            if "driverInfo" in line:
                vk_driver = line.split("=")[1].strip()
    except Exception:
        pass

    # PCIe link
    pcie_speed = "Unknown"
    pcie_width = "Unknown"
    if card_device_dir and os.path.isdir(card_device_dir):
        speed_f = os.path.join(card_device_dir, "current_link_speed")
        width_f = os.path.join(card_device_dir, "current_link_width")
        max_s_f = os.path.join(card_device_dir, "max_link_speed")
        max_w_f = os.path.join(card_device_dir, "max_link_width")

        curr_s = open(speed_f).read().strip() if os.path.isfile(speed_f) else ""
        curr_w = open(width_f).read().strip() if os.path.isfile(width_f) else ""
        max_s = open(max_s_f).read().strip() if os.path.isfile(max_s_f) else ""
        max_w = open(max_w_f).read().strip() if os.path.isfile(max_w_f) else ""

        if curr_s:
            pcie_speed = f"{curr_s} (Max: {max_s})" if max_s else curr_s
        if curr_w:
            pcie_width = f"x{curr_w} (Max: x{max_w})" if max_w else f"x{curr_w}"

    return SystemAudit(
        mesa_version=mesa_ver,
        vulkan_version=vk_ver,
        vulkan_driver=vk_driver,
        opengl_version=gl_ver,
        kernel_version=kernel,
        os_name=os_name,
        desktop_env=desktop,
        session_type=session,
        pcie_link_speed=pcie_speed,
        pcie_link_width=pcie_width
    )
