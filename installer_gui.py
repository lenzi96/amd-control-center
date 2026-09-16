#!/usr/bin/env python3
"""AMD Software: Adrenalin Edition - Graphical Setup & Deployment Wizard."""

import os
import sys
import subprocess
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QCheckBox, QFrame,
    QStackedWidget, QTextEdit, QMessageBox
)
from PyQt6.QtSvgWidgets import QSvgWidget

# Add repo to sys.path so we can import backend detectors
REPO_DIR = Path(__file__).resolve().parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

try:
    from amd_control_center.backend.gpu_detector import detect_amd_gpus
    from amd_control_center.backend.system_info import audit_system
except Exception:
    detect_amd_gpus = None
    audit_system = None


INSTALLER_STYLESHEET = """
QWidget {
    background-color: transparent;
    color: #FFFFFF;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    font-size: 13px;
    outline: none;
}

QMainWindow {
    background-color: #0B0E14;
}

QFrame.installer-card {
    background-color: #141822;
    border: 1px solid #202736;
    border-radius: 8px;
    padding: 16px;
}

QFrame.installer-card:hover {
    border-color: #2F3B4F;
}

QPushButton {
    background-color: #1A202C;
    color: #FFFFFF;
    border: 1px solid #283244;
    border-radius: 6px;
    padding: 9px 20px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #222B3B;
    border-color: #3C4B63;
}

QPushButton:pressed {
    background-color: #121620;
}

QPushButton.primary-red {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B81327);
    color: #FFFFFF;
    border: 1px solid #E01E37;
    font-weight: 800;
    letter-spacing: 0.8px;
}

QPushButton.primary-red:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #D1152E);
    border: 1px solid #FF334B;
}

QPushButton.ghost-button {
    background-color: transparent;
    border: 1px solid transparent;
    color: #8C9CAE;
}

QPushButton.ghost-button:hover {
    background-color: #1A202C;
    border-color: #2A3345;
    color: #FFFFFF;
}

QPushButton.danger-button {
    background-color: rgba(224, 30, 55, 0.12);
    border: 1px solid #8B1020;
    color: #FF5A6E;
}

QPushButton.danger-button:hover {
    background-color: #E01E37;
    border-color: #FF2E47;
    color: #FFFFFF;
}

QProgressBar {
    background-color: #10131A;
    border: 1px solid #202736;
    border-radius: 4px;
    height: 12px;
    text-align: center;
    font-size: 10px;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B81327, stop:1 #E01E37);
    border-radius: 3px;
}

QCheckBox {
    font-size: 12px;
    font-weight: 600;
    color: #C8D1DC;
    spacing: 8px;
}

QCheckBox:hover {
    color: #FFFFFF;
}

QTextEdit {
    background-color: #090B0E;
    border: 1px solid #1C2330;
    border-radius: 6px;
    font-family: monospace;
    font-size: 11px;
    color: #8E9FB5;
    padding: 8px;
}
"""


class InstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    log_emitted = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str)

    def __init__(self, create_desktop_shortcut: bool = True, enable_autostart: bool = True, repo_dir: Path = REPO_DIR):
        super().__init__()
        self.create_desktop_shortcut = create_desktop_shortcut
        self.enable_autostart = enable_autostart
        self.repo_dir = repo_dir

    def run(self):
        try:
            home = Path.home()
            bin_dir = home / ".local" / "bin"
            app_dir = home / ".local" / "share" / "applications"
            hicolor_base = home / ".local" / "share" / "icons" / "hicolor"
            pixmaps_dir = home / ".local" / "share" / "pixmaps"
            
            share_dir = home / ".local" / "share" / "amd-control-center"
            
            desktop_dir = home / "Schreibtisch"
            if not desktop_dir.is_dir():
                desktop_dir = home / "Desktop"

            self.log_emitted.emit("→ Erstelle Benutzerverzeichnisse...")
            self.progress_changed.emit(10, "Verzeichnisse werden vorbereitet...")
            for d in [bin_dir, app_dir, share_dir, pixmaps_dir]:
                d.mkdir(parents=True, exist_ok=True)
            self.msleep(100)

            # 1. Install application files to ~/.local/share/amd-control-center
            self.log_emitted.emit(f"→ Installiere Anwendungsdateien in {share_dir}...")
            self.progress_changed.emit(20, "Anwendungsdateien werden kopiert...")
            shutil.copytree(self.repo_dir / "amd_control_center", share_dir / "amd_control_center", dirs_exist_ok=True)
            shutil.copyfile(self.repo_dir / "main.py", share_dir / "main.py")
            self.msleep(100)

            # 2. Standalone launcher script in ~/.local/bin/amd-control-center
            self.log_emitted.emit(f"→ Erstelle Starter in {bin_dir}/amd-control-center...")
            self.progress_changed.emit(35, "Anwendungsstarter wird registriert...")
            launcher_dst = bin_dir / "amd-control-center"
            if launcher_dst.is_symlink() or launcher_dst.exists():
                launcher_dst.unlink()

            launcher_script = f"""#!/usr/bin/env bash
# Standalone launcher for AMD Software: Adrenalin Edition
INSTALL_DIR="$HOME/.local/share/amd-control-center"
DEV_DIR="{self.repo_dir}"

if [ -n "$AMD_DEV_DIR" ] && [ -d "$AMD_DEV_DIR" ]; then
    APP_DIR="$AMD_DEV_DIR"
elif [ -d "$INSTALL_DIR" ]; then
    APP_DIR="$INSTALL_DIR"
elif [ -d "$DEV_DIR" ]; then
    APP_DIR="$DEV_DIR"
else
    echo "Error: amd-control-center installation not found." >&2
    exit 1
fi

export PYTHONPATH="$APP_DIR:$PYTHONPATH"
exec python3 "$APP_DIR/main.py" "$@"
"""
            launcher_dst.write_text(launcher_script, encoding="utf-8")
            launcher_dst.chmod(0o755)
            self.msleep(100)

            # 3. Install application icons (Multi-Resolution PNGs + Scalable SVG + Pixmaps fallback)
            self.log_emitted.emit("→ Installiere Symbole (PNG Multi-Resolution & SVG)...")
            self.progress_changed.emit(50, "Icons für alle Auflösungen werden installiert...")
            res_dir = self.repo_dir / "amd_control_center" / "resources"

            # Scalable SVG
            svg_src = res_dir / "app_icon.svg"
            if svg_src.is_file():
                svg_dest_dir = hicolor_base / "scalable" / "apps"
                svg_dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(svg_src, svg_dest_dir / "amd-control-center.svg")
                shutil.copyfile(svg_src, pixmaps_dir / "amd-control-center.svg")

            # Raster PNGs (16, 24, 32, 48, 64, 128, 256, 512)
            for sz in (16, 24, 32, 48, 64, 128, 256, 512):
                png_src = res_dir / f"app_icon_{sz}.png"
                if png_src.is_file():
                    target_dir = hicolor_base / f"{sz}x{sz}" / "apps"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(png_src, target_dir / "amd-control-center.png")

            # Fallback 256px icon to ~/.local/share/pixmaps
            png_fallback = res_dir / "app_icon_256.png"
            if not png_fallback.is_file():
                png_fallback = res_dir / "app_icon.png"
            if png_fallback.is_file():
                shutil.copyfile(png_fallback, pixmaps_dir / "amd-control-center.png")
            self.msleep(100)

            # 3. Install Desktop file in Applications Menu
            self.log_emitted.emit(f"→ Registriere Desktop-Eintrag in {app_dir}...")
            self.progress_changed.emit(65, "Startmenü-Eintrag wird eingerichtet...")
            desktop_tmpl = self.repo_dir / "amd-control-center.desktop"
            if desktop_tmpl.is_file():
                lines = desktop_tmpl.read_text(encoding="utf-8").splitlines()
                out_lines = []
                for line in lines:
                    if line.startswith("Exec="):
                        out_lines.append(f"Exec={launcher_dst}")
                    elif line.startswith("Icon="):
                        out_lines.append("Icon=amd-control-center")
                    else:
                        out_lines.append(line)
                desktop_out = "\n".join(out_lines) + "\n"
                target_desktop = app_dir / "amd-control-center.desktop"
                target_desktop.write_text(desktop_out, encoding="utf-8")
                target_desktop.chmod(0o755)
            self.msleep(100)

            # 4. Optional Desktop Shortcut
            if self.create_desktop_shortcut and desktop_dir.is_dir():
                self.log_emitted.emit(f"→ Erstelle Verknüpfung auf dem Schreibtisch ({desktop_dir})...")
                self.progress_changed.emit(75, "Desktop-Verknüpfung wird erstellt...")
                desk_target = desktop_dir / "amd-control-center.desktop"
                if (app_dir / "amd-control-center.desktop").is_file():
                    shutil.copyfile(app_dir / "amd-control-center.desktop", desk_target)
                    desk_target.chmod(0o755)
                    try:
                        subprocess.run(["gio", "set", str(desk_target), "metadata::trusted", "true"], capture_output=True)
                    except Exception:
                        pass
            self.msleep(100)

            # 5. Optional System Autostart
            if self.enable_autostart:
                self.log_emitted.emit("→ Richte System-Autostart ein...")
                self.progress_changed.emit(85, "Autostart wird konfiguriert...")
                try:
                    from amd_control_center.backend.autostart_manager import set_autostart_enabled
                    set_autostart_enabled(True)
                    self.log_emitted.emit("✔ Autostart im Infobereich aktiviert.")
                except Exception as ex:
                    self.log_emitted.emit(f"⚠️ Warnung bei Autostart: {ex}")
            self.msleep(100)

            # 6. Update Desktop Database & Icon Caches
            self.log_emitted.emit("→ Aktualisiere System-Icon- und Desktop-Caches...")
            self.progress_changed.emit(95, "Desktop- und Symbol-Caches werden aktualisiert...")
            try:
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(hicolor_base)], capture_output=True)
            except Exception:
                pass
            try:
                subprocess.run(["update-desktop-database", str(app_dir)], capture_output=True)
            except Exception:
                pass
            try:
                subprocess.run(["kbuildsycoca6", "--noincremental"], capture_output=True)
            except Exception:
                pass
            self.msleep(100)

            self.progress_changed.emit(100, "Installation abgeschlossen!")
            self.log_emitted.emit("✔ Installation erfolgreich abgeschlossen.")
            self.finished_result.emit(True, "Installation erfolgreich abgeschlossen!")

        except Exception as e:
            self.log_emitted.emit(f"❌ Fehler bei der Installation: {e}")
            self.finished_result.emit(False, str(e))


class UninstallWorker(QThread):
    progress_changed = pyqtSignal(int, str)
    log_emitted = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str)

    def run(self):
        try:
            home = Path.home()
            bin_file = home / ".local" / "bin" / "amd-control-center"
            app_file = home / ".local" / "share" / "applications" / "amd-control-center.desktop"
            autostart_file = home / ".config" / "autostart" / "amd-control-center.desktop"
            hicolor_base = home / ".local" / "share" / "icons" / "hicolor"
            pixmaps_dir = home / ".local" / "share" / "pixmaps"

            self.progress_changed.emit(20, "Entferne Anwendungsdateien...")
            share_dir = home / ".local" / "share" / "amd-control-center"
            if share_dir.exists():
                shutil.rmtree(share_dir)
                self.log_emitted.emit(f"Entfernt: {share_dir}")

            if bin_file.is_symlink() or bin_file.exists():
                bin_file.unlink()
                self.log_emitted.emit(f"Entfernt: {bin_file}")

            self.progress_changed.emit(40, "Entferne Desktop- und Autostart-Einträge...")
            if app_file.exists():
                app_file.unlink()
                self.log_emitted.emit(f"Entfernt: {app_file}")

            if autostart_file.exists():
                autostart_file.unlink()
                self.log_emitted.emit(f"Entfernt: {autostart_file}")

            for desk in [home / "Schreibtisch" / "amd-control-center.desktop", home / "Desktop" / "amd-control-center.desktop"]:
                if desk.exists():
                    desk.unlink()
                    self.log_emitted.emit(f"Entfernt: {desk}")

            self.progress_changed.emit(65, "Entferne Symbole...")
            for sz in (16, 24, 32, 48, 64, 128, 256, 512):
                png_file = hicolor_base / f"{sz}x{sz}" / "apps" / "amd-control-center.png"
                if png_file.exists():
                    png_file.unlink()
            svg_file = hicolor_base / "scalable" / "apps" / "amd-control-center.svg"
            if svg_file.exists():
                svg_file.unlink()

            for pix in [pixmaps_dir / "amd-control-center.png", pixmaps_dir / "amd-control-center.svg"]:
                if pix.exists():
                    pix.unlink()

            self.progress_changed.emit(85, "Aktualisiere Caches...")
            try:
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(hicolor_base)], capture_output=True)
            except Exception:
                pass
            try:
                subprocess.run(["update-desktop-database", str(home / ".local" / "share" / "applications")], capture_output=True)
            except Exception:
                pass
            try:
                subprocess.run(["kbuildsycoca6", "--noincremental"], capture_output=True)
            except Exception:
                pass

            self.progress_changed.emit(100, "Deinstallation abgeschlossen.")
            self.finished_result.emit(True, "AMD Software wurde erfolgreich entfernt.")

        except Exception as e:
            self.finished_result.emit(False, str(e))


class InstallerWindow(QMainWindow):
    def __init__(self, test_mode: bool = False, parent=None):
        super().__init__(parent)
        self.test_mode = test_mode
        self.setWindowTitle("AMD Software: Adrenalin Edition - Setup")
        self.resize(760, 520)
        self.setMinimumSize(720, 480)
        self.setStyleSheet(INSTALLER_STYLESHEET)

        # Set Icon
        try:
            from amd_control_center.icon import get_app_icon
            self.setWindowIcon(get_app_icon())
        except Exception:
            res_icon = REPO_DIR / "amd_control_center" / "resources" / "app_icon.svg"
            if res_icon.is_file():
                self.setWindowIcon(QIcon(str(res_icon)))

        # Hardware Detection
        self.gpu_name = "AMD Radeon Grafikkarte"
        self.gpu_arch = "RDNA 3 / RDNA 4"
        self.fsr4_ready = True
        self.driver_str = "Mesa Graphics Driver"

        if detect_amd_gpus:
            gpus = detect_amd_gpus()
            if gpus:
                g = gpus[0]
                self.gpu_name = g.model_name
                self.gpu_arch = g.architecture
                self.fsr4_ready = g.supports_fsr4
        if audit_system:
            audit = audit_system("")
            if audit and audit.mesa_version:
                self.driver_str = f"Mesa {audit.mesa_version} • Vulkan {audit.vulkan_version}"

        central = QWidget()
        central.setStyleSheet("background-color: #0B0E14;")
        self.setCentralWidget(central)
        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 1. Top Header Banner
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("background-color: #080A0F; border-bottom: 1px solid #1C2330;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        h_layout.setSpacing(16)

        logo_svg = REPO_DIR / "amd_control_center" / "resources" / "radeon_logo.svg"
        if logo_svg.is_file():
            self.logo = QSvgWidget(str(logo_svg))
            self.logo.setFixedSize(170, 30)
            h_layout.addWidget(self.logo)
        else:
            lbl = QLabel("RADEON")
            lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF; letter-spacing: 2px;")
            h_layout.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #202736; background-color: #202736; width: 1px; margin-top: 16px; margin-bottom: 16px;")
        sep.setFixedWidth(1)
        h_layout.addWidget(sep)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_t = QLabel("SOFTWARE: ADRENALIN EDITION")
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;")
        lbl_sub = QLabel("Linux Setup & Deployment Assistent")
        lbl_sub.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        title_col.addWidget(lbl_t)
        title_col.addWidget(lbl_sub)
        h_layout.addLayout(title_col)

        h_layout.addStretch()

        badge_status = QLabel("● BEREIT ZUR INSTALLATION")
        badge_status.setStyleSheet("background-color: rgba(0, 230, 118, 0.12); border: 1px solid #00E676; color: #00E676; font-size: 10px; font-weight: 800; padding: 4px 10px; border-radius: 12px;")
        h_layout.addWidget(badge_status)

        main_vbox.addWidget(header)

        # 2. Main Stacked Pages
        self.stack = QStackedWidget()
        self.page_welcome = self._create_welcome_page()
        self.page_progress = self._create_progress_page()
        self.page_finish = self._create_finish_page()

        self.stack.addWidget(self.page_welcome)   # 0
        self.stack.addWidget(self.page_progress)  # 1
        self.stack.addWidget(self.page_finish)    # 2
        main_vbox.addWidget(self.stack)

        self.worker = None

    def _create_welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Headline
        head_row = QVBoxLayout()
        head_row.setSpacing(4)
        h1 = QLabel("Willkommen bei AMD Software: Adrenalin Edition für Linux")
        h1.setStyleSheet("font-size: 18px; font-weight: 900; color: #FFFFFF;")
        h2 = QLabel("Konfiguriere und installiere das moderne AMD Radeon Steuerungszentrum, den FSR 4 Neural Swapper und das MangoHud Overlay.")
        h2.setStyleSheet("font-size: 12px; color: #8C9BAE;")
        head_row.addWidget(h1)
        head_row.addWidget(h2)
        layout.addLayout(head_row)

        # Two Columns Grid: Hardware on left, Options on right
        grid = QHBoxLayout()
        grid.setSpacing(16)

        # Left Column: Hardware Check
        card_hw = QFrame()
        card_hw.setProperty("class", "installer-card")
        hw_vbox = QVBoxLayout(card_hw)
        hw_vbox.setSpacing(10)

        lbl_hw_title = QLabel("ERKANNTES SYSTEM")
        lbl_hw_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        hw_vbox.addWidget(lbl_hw_title)

        def _add_hw_row(k: str, v: str):
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet("color: #7E8D9F; font-size: 11px; font-weight: 600;")
            l2 = QLabel(v)
            l2.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold;")
            r.addWidget(l1)
            r.addStretch()
            r.addWidget(l2)
            hw_vbox.addLayout(r)

        _add_hw_row("Grafikkarte:", self.gpu_name)
        _add_hw_row("Architektur:", self.gpu_arch)
        _add_hw_row("Treiber & API:", self.driver_str)
        _add_hw_row("FSR 4 AI-Support:", "Bereit (WMMA Matrix Cores)" if self.fsr4_ready else "Kompatibel")
        _add_hw_row("Zielverzeichnis:", "~/.local/bin")

        hw_vbox.addStretch()
        grid.addWidget(card_hw, stretch=1)

        # Right Column: Features & Options
        card_opt = QFrame()
        card_opt.setProperty("class", "installer-card")
        opt_vbox = QVBoxLayout(card_opt)
        opt_vbox.setSpacing(10)

        lbl_opt_title = QLabel("INSTALLATIONS-OPTIONEN")
        lbl_opt_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        opt_vbox.addWidget(lbl_opt_title)

        self.chk_start_menu = QCheckBox("Im Startmenü registrieren (Anwendungsmenü)")
        self.chk_start_menu.setChecked(True)
        self.chk_start_menu.setEnabled(False)  # Core requirement
        opt_vbox.addWidget(self.chk_start_menu)

        self.chk_desktop = QCheckBox("Desktop-Verknüpfung auf dem Schreibtisch erstellen")
        self.chk_desktop.setChecked(True)
        opt_vbox.addWidget(self.chk_desktop)

        self.chk_autostart = QCheckBox("Mit System starten (im Infobereich / System Tray starten)")
        self.chk_autostart.setChecked(True)
        opt_vbox.addWidget(self.chk_autostart)

        self.chk_swapper = QCheckBox("FSR 4 Neural Swapper (OptiScaler & DLSS-Drop-In) aktivieren")
        self.chk_swapper.setChecked(True)
        self.chk_swapper.setEnabled(False)
        opt_vbox.addWidget(self.chk_swapper)

        self.chk_mangohud = QCheckBox("MangoHud Overlay Editor & Profile integrieren")
        self.chk_mangohud.setChecked(True)
        self.chk_mangohud.setEnabled(False)
        opt_vbox.addWidget(self.chk_mangohud)

        opt_vbox.addStretch()
        grid.addWidget(card_opt, stretch=1)

        layout.addLayout(grid)
        layout.addStretch()

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        # Check if already installed
        bin_installed = (Path.home() / ".local" / "bin" / "amd-control-center").exists()
        if bin_installed:
            btn_uninstall = QPushButton("🗑 Deinstallieren")
            btn_uninstall.setProperty("class", "danger-button")
            btn_uninstall.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_uninstall.clicked.connect(self._start_uninstallation)
            bottom_bar.addWidget(btn_uninstall)

        bottom_bar.addStretch()

        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.setProperty("class", "ghost-button")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.close)
        bottom_bar.addWidget(btn_cancel)

        btn_install = QPushButton("⚡ JETZT INSTALLIEREN" if not bin_installed else "🔄 AKTUALISIEREN / REPARIEREN")
        btn_install.setProperty("class", "primary-red")
        btn_install.setFixedHeight(42)
        btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_install.clicked.connect(self._start_installation)
        bottom_bar.addWidget(btn_install)

        layout.addLayout(bottom_bar)
        return page

    def _create_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        self.lbl_progress_title = QLabel("Installation wird durchgeführt...")
        self.lbl_progress_title.setStyleSheet("font-size: 18px; font-weight: 900; color: #FFFFFF;")
        layout.addWidget(self.lbl_progress_title)

        self.lbl_progress_status = QLabel("Bereite Dateien vor...")
        self.lbl_progress_status.setStyleSheet("font-size: 12px; color: #A8B2C4;")
        layout.addWidget(self.lbl_progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        lbl_log = QLabel("Detailliertes Installationsprotokoll:")
        lbl_log.setStyleSheet("font-size: 11px; font-weight: 700; color: #7E8D9F; margin-top: 10px;")
        layout.addWidget(lbl_log)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(self.txt_log)

        return page

    def _create_finish_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success Icon
        lbl_icon = QLabel("✔")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setFixedSize(72, 72)
        lbl_icon.setStyleSheet("""
            background-color: rgba(0, 230, 118, 0.15);
            border: 2px solid #00E676;
            color: #00E676;
            font-size: 36px;
            font-weight: 900;
            border-radius: 36px;
        """)
        layout.addWidget(lbl_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_finish_head = QLabel("Installation erfolgreich abgeschlossen!")
        self.lbl_finish_head.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF;")
        self.lbl_finish_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_finish_head)

        self.lbl_finish_sub = QLabel(
            "AMD Software: Adrenalin Edition ist nun einsatzbereit.\n"
            "Du kannst die Anwendung jederzeit über das Startmenü oder im Terminal mit 'amd-control-center' starten."
        )
        self.lbl_finish_sub.setStyleSheet("font-size: 12px; color: #A8B2C4; line-height: 1.5;")
        self.lbl_finish_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_finish_sub)

        self.chk_launch_now = QCheckBox("AMD Software: Adrenalin Edition jetzt sofort starten")
        self.chk_launch_now.setChecked(True)
        self.chk_launch_now.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF; margin-top: 10px;")
        layout.addWidget(self.chk_launch_now, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        btn_finish = QPushButton("FERTIGSTELLEN")
        btn_finish.setProperty("class", "primary-red")
        btn_finish.setFixedHeight(42)
        btn_finish.setFixedWidth(240)
        btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finish.clicked.connect(self._on_finish_clicked)
        layout.addWidget(btn_finish, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _start_installation(self):
        self.stack.setCurrentIndex(1)
        self.lbl_progress_title.setText("Installation wird durchgeführt...")
        self.txt_log.clear()

        self.worker = InstallWorker(
            create_desktop_shortcut=self.chk_desktop.isChecked(),
            enable_autostart=self.chk_autostart.isChecked(),
            repo_dir=REPO_DIR
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.log_emitted.connect(self._on_log)
        self.worker.finished_result.connect(self._on_install_finished)
        self.worker.start()

    def _start_uninstallation(self):
        ret = QMessageBox.question(
            self,
            "Deinstallation bestätigen",
            "Möchtest du AMD Software: Adrenalin Edition wirklich aus deinem System entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        self.stack.setCurrentIndex(1)
        self.lbl_progress_title.setText("Deinstallation wird durchgeführt...")
        self.txt_log.clear()

        self.worker = UninstallWorker()
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.log_emitted.connect(self._on_log)
        self.worker.finished_result.connect(self._on_uninstall_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.lbl_progress_status.setText(msg)

    def _on_log(self, text: str):
        self.txt_log.append(text)

    def _on_install_finished(self, success: bool, msg: str):
        if success:
            self.lbl_finish_head.setText("Installation erfolgreich abgeschlossen!")
            self.lbl_finish_sub.setText(
                "AMD Software: Adrenalin Edition ist nun einsatzbereit.\n"
                "Du kannst die Anwendung jederzeit über das Startmenü oder im Terminal mit 'amd-control-center' starten."
            )
            self.chk_launch_now.setVisible(True)
            self.stack.setCurrentIndex(2)
        else:
            QMessageBox.critical(self, "Fehler bei der Installation", f"Die Installation ist fehlgeschlagen:\n{msg}")
            self.stack.setCurrentIndex(0)

    def _on_uninstall_finished(self, success: bool, msg: str):
        if success:
            self.lbl_finish_head.setText("Deinstallation erfolgreich abgeschlossen!")
            self.lbl_finish_sub.setText("Die Verknüpfungen und Starter von AMD Software wurden vollständig entfernt.")
            self.chk_launch_now.setVisible(False)
            self.stack.setCurrentIndex(2)
        else:
            QMessageBox.critical(self, "Fehler bei der Deinstallation", f"Deinstallation fehlgeschlagen:\n{msg}")
            self.stack.setCurrentIndex(0)

    def _on_finish_clicked(self):
        if self.chk_launch_now.isVisible() and self.chk_launch_now.isChecked():
            launcher = Path.home() / ".local" / "bin" / "amd-control-center"
            if launcher.exists():
                subprocess.Popen([str(launcher)], start_new_session=True)
        self.close()


def main():
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
