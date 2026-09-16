"""Main Application Window for AMD Control Center with Lazy-Loading."""

import os
import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QSystemTrayIcon, QMenu, QApplication
)

from .styles import ADRENALIN_STYLESHEET
from .backend.gpu_detector import detect_amd_gpus, GpuDevice
from .backend.gpu_monitor import GpuTelemetryMonitor
from .backend.game_scanner import scan_steam_games, scan_all_games, GameInfo
from .backend.game_profiles import ProfileManager
from .backend.display_manager import detect_displays, DisplayInfo
from .backend.system_info import audit_system, SystemAudit
from .widgets.top_nav_bar import TopNavBar
from .widgets.overlay_window import OverlayHUD
from .views.home_view import HomeView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AMD Software: Adrenalin Edition")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 700)
        self.minimize_to_tray = True
        self._really_quit = False


        # Set Window Icon
        from .icon import get_app_icon
        self.setWindowIcon(get_app_icon())

        # Fast Hardware & System Detection
        gpus = detect_amd_gpus()
        self.gpu: GpuDevice = gpus[0] if gpus else GpuDevice(
            card_path="/sys/class/drm/card1",
            card_name="card1",
            device_dir="",
            model_name="AMD Radeon GPU"
        )
        
        # Display detection
        displays = detect_displays()
        self.display: DisplayInfo = displays[0] if displays else DisplayInfo(
            connector="DP-1", connected=True, resolution="3840x2160", refresh_rate_hz=144.0
        )
        
        # Fast initial scan for recently played games
        self.games = scan_steam_games()
        self.all_games_loaded = False
        top_game = self.games[0] if self.games else None

        # System Audit
        self.audit: SystemAudit = audit_system(self.gpu.device_dir)
        self.profile_mgr = ProfileManager()
        for g in self.games:
            self.profile_mgr.register_game_directory(g.app_id, g.install_dir)
        self.profile_mgr.sync_fps_limits()


        # Apply Global Adrenalin Theme
        self.setStyleSheet(ADRENALIN_STYLESHEET)

        # Main Layout
        central = QWidget()
        central.setStyleSheet("background-color: #0E1015;")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Navigation Bar
        driver_str = f"{self.audit.mesa_version} • Up to date"
        self.top_nav = TopNavBar(gpu_name=self.gpu.model_name, driver_ver=driver_str)
        main_layout.addWidget(self.top_nav)

        # Views Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #12151B;")

        # Initialize HomeView immediately
        self.home_view = HomeView(self.gpu, top_game, self.audit, self.display, self.profile_mgr)
        self.stack.addWidget(self.home_view)

        # Placeholders for Lazy Loading (Gaming, Performance, Settings)
        self.gaming_view = None
        self.perf_view = None
        self.settings_view = None

        self.dummy_gaming = QWidget()
        self.dummy_perf = QWidget()
        self.dummy_settings = QWidget()

        self.stack.addWidget(self.dummy_gaming)     # idx 1
        self.stack.addWidget(self.dummy_perf)       # idx 2
        self.stack.addWidget(self.dummy_settings)   # idx 3

        main_layout.addWidget(self.stack)

        # Floating Overlay Window (instantiated on-demand)
        self._overlay = None

        # Connect Navigation Signals
        self.top_nav.tab_changed.connect(self._on_tab_changed)
        self.top_nav.overlay_toggle_requested.connect(self._toggle_overlay)
        self.top_nav.update_requested.connect(self._open_update_dialog)
        self.home_view.navigate_to_tab.connect(self._navigate_to)
        self.home_view.play_game_requested.connect(self._launch_game)

        # Telemetry Monitor (using QTimer)
        self.monitor = GpuTelemetryMonitor(self.gpu, interval_ms=1000, parent=self)
        self.monitor.telemetry_updated.connect(self._on_telemetry_updated)
        self.monitor.start()

        # System Tray Icon
        self._init_tray()

        # Background silent GitHub update check
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2500, self._start_background_update_check)

    @property
    def overlay(self) -> OverlayHUD:
        if self._overlay is None:
            self._overlay = OverlayHUD()
        return self._overlay

    def bring_to_front(self):
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def handle_remote_args(self, args: list):
        if "--overlay" in args:
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
        elif "--tuning" in args or "--performance" in args:
            self._navigate_to(2)
            self.bring_to_front()
        elif "--gaming" in args:
            self._navigate_to(1)
            self.bring_to_front()
        else:
            self.bring_to_front()

    def _init_tray(self):
        from .icon import get_app_icon
        self.tray = QSystemTrayIcon(get_app_icon(), self)
        self.tray.setToolTip("AMD Software: Adrenalin Edition")
        tray_menu = QMenu()
        action_show = tray_menu.addAction("AMD Software öffnen")
        action_show.triggered.connect(self.bring_to_front)
        action_overlay = tray_menu.addAction("HUD Overlay umschalten")
        action_overlay.triggered.connect(self._toggle_overlay)
        action_update = tray_menu.addAction("Nach Updates suchen...")
        action_update.triggered.connect(self._open_update_dialog)
        tray_menu.addSeparator()
        action_quit = tray_menu.addAction("Beenden")
        action_quit.triggered.connect(self._quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.bring_to_front()

    def _on_tab_changed(self, idx: int):
        # Lazy load views on tab click
        if idx == 1 and self.gaming_view is None:
            self._init_gaming_view()
        elif idx == 2 and self.perf_view is None:
            self._init_perf_view()
        elif idx == 3 and self.settings_view is None:
            self._init_settings_view()

        self.stack.setCurrentIndex(idx)

    def _init_gaming_view(self):
        from .views.gaming_view import GamingView
        if not self.all_games_loaded:
            self.games = scan_all_games()
            self.all_games_loaded = True
            for g in self.games:
                self.profile_mgr.register_game_directory(g.app_id, g.install_dir)
            self.profile_mgr.sync_fps_limits()
        self.gaming_view = GamingView(self.games, self.profile_mgr)
        self.gaming_view.play_game_requested.connect(self._launch_game)
        
        # Replace dummy widget at index 1
        self.stack.removeWidget(self.dummy_gaming)
        self.stack.insertWidget(1, self.gaming_view)

    def _init_perf_view(self):
        from .views.performance_view import PerformanceView
        self.perf_view = PerformanceView(self.gpu)
        self.perf_view.interval_changed.connect(self._on_interval_changed)
        
        # Replace dummy widget at index 2
        self.stack.removeWidget(self.dummy_perf)
        self.stack.insertWidget(2, self.perf_view)

    def _init_settings_view(self):
        from .views.settings_view import SettingsView
        self.settings_view = SettingsView(self.gpu, self.audit, self.display)
        self.settings_view.tray_minimize_changed.connect(self._on_tray_minimize_changed)
        self.settings_view.update_center_requested.connect(self._open_update_dialog)
        
        # Replace dummy widget at index 3
        self.stack.removeWidget(self.dummy_settings)
        self.stack.insertWidget(3, self.settings_view)

    def _on_tray_minimize_changed(self, enabled: bool):
        self.minimize_to_tray = enabled

    def _navigate_to(self, idx: int):
        self.top_nav.select_tab(idx)
        self._on_tab_changed(idx)

    def _toggle_overlay(self):
        ov = self.overlay
        if ov.isVisible():
            ov.hide()
        else:
            ov.show()

    def _on_interval_changed(self, interval_ms: int):
        self.monitor.set_interval(interval_ms)

    def _launch_game(self, app_id: str):
        game = next((g for g in self.games if g.app_id == app_id), None)
        if game:
            self.profile_mgr.launch_game(app_id, game.launch_command)

    def _on_telemetry_updated(self, data: dict):
        self.home_view.update_telemetry(data)
        if self.perf_view is not None:
            self.perf_view.update_telemetry(data)
        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.update_telemetry(data)
        if hasattr(self, "tray"):
            temp = data.get("temp_edge", 0.0)
            load = data.get("gpu_busy", 0)
            self.tray.setToolTip(f"AMD Radeon: {temp:.0f}°C | {load}% Auslastung")

    def _quit_app(self):
        self._really_quit = True
        self.monitor.stop()
        if self._overlay is not None:
            self._overlay.close()
        if hasattr(self, "tray"):
            self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if not self._really_quit and getattr(self, "minimize_to_tray", True) and hasattr(self, "tray") and self.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            self._quit_app()
            event.accept()

    def _open_update_dialog(self):
        from .dialogs.github_update_dialog import GitHubUpdateDialog
        dlg = GitHubUpdateDialog(self)
        dlg.exec()
        self.top_nav.reset_update_status()

    def _start_background_update_check(self):
        from .backend.github_updater import GitHubUpdateCheckerWorker
        self._bg_updater = GitHubUpdateCheckerWorker(self)
        self._bg_updater.finished.connect(self._on_bg_update_finished)
        self._bg_updater.start()

    def _on_bg_update_finished(self, info):
        if info.has_update:
            self.top_nav.set_update_available(info.remote_version)
            if hasattr(self, "tray") and self.tray.isVisible():
                self.tray.showMessage(
                    "AMD Software: Adrenalin Edition",
                    f"Ein neues Update (v{info.remote_version}) ist auf GitHub verfügbar!",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000,
                )

