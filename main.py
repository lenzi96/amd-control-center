#!/usr/bin/env python3
"""Launcher for AMD Control Center."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from amd_control_center.app import main

if __name__ == "__main__":
    main()
