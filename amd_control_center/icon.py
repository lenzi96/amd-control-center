"""App icon provider supporting multi-resolution PNG assets and XDG theme icons."""

from pathlib import Path
from PyQt6.QtGui import QIcon


def get_app_icon() -> QIcon:
    """Returns a QIcon containing all available resolutions (PNG 16..512 + SVG).

    Checks the desktop environment's current icon theme first, falling back to
    bundled multi-resolution PNGs and SVG.
    """
    if QIcon.hasThemeIcon("amd-control-center"):
        theme_icon = QIcon.fromTheme("amd-control-center")
        if not theme_icon.isNull() and len(theme_icon.availableSizes()) > 0:
            return theme_icon

    icon = QIcon()
    res_dir = Path(__file__).resolve().parent / "resources"
    for sz in (16, 24, 32, 48, 64, 128, 256, 512):
        png = res_dir / f"app_icon_{sz}.png"
        if png.is_file():
            icon.addFile(str(png))

    png_fallback = res_dir / "app_icon.png"
    if png_fallback.is_file():
        icon.addFile(str(png_fallback))

    svg = res_dir / "app_icon.svg"
    if svg.is_file():
        icon.addFile(str(svg))

    return icon
