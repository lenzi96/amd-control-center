"""Home View (Startseite) for AMD Control Center."""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea
)

from ..backend.gpu_detector import GpuDevice
from ..backend.game_scanner import GameInfo
from ..backend.game_profiles import ProfileManager
from ..backend.system_info import SystemAudit
from ..backend.display_manager import DisplayInfo
from ..widgets.toggle_switch import ToggleSwitch
from ..widgets.metric_card import MetricCard


class HomeView(QWidget):
    navigate_to_tab = pyqtSignal(int)
    play_game_requested = pyqtSignal(str)

    def __init__(self, gpu: GpuDevice, top_game: GameInfo, audit: SystemAudit, display: DisplayInfo, profile_mgr: ProfileManager, parent=None):
        super().__init__(parent)
        self.gpu = gpu
        self.top_game = top_game
        self.audit = audit
        self.display = display
        self.profile_mgr = profile_mgr

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        # 1. Top Section: Left (Hero Game Card) & Right (Performance Snapshot)
        top_grid = QHBoxLayout()
        top_grid.setSpacing(18)

        # Hero Game Banner Card
        hero_card = self._create_hero_game_card()
        top_grid.addWidget(hero_card, stretch=3)

        # Performance Snapshot Tile
        perf_card = self._create_perf_snapshot_card()
        top_grid.addWidget(perf_card, stretch=2)

        layout.addLayout(top_grid)

        # 2. Bottom Section: Driver & Software Card + System Overview Card
        bot_grid = QHBoxLayout()
        bot_grid.setSpacing(18)

        driver_card = self._create_driver_card()
        bot_grid.addWidget(driver_card, stretch=1)

        system_card = self._create_system_card()
        bot_grid.addWidget(system_card, stretch=1)

        layout.addLayout(bot_grid)
        layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_hero_game_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "adrenalin-card")
        card.setStyleSheet("""
            QFrame {
                background-color: #141822;
                border: 1px solid #202838;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header: Recently Played
        top_row = QHBoxLayout()
        lbl_badge = QLabel("RADEON™ SPIELE-DASHBOARD")
        lbl_badge.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")

        lbl_recent_pill = QLabel("ZULETZT GESPIELT")
        lbl_recent_pill.setStyleSheet("background-color: rgba(224, 30, 55, 0.15); border: 1px solid #E01E37; color: #FF4256; font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 4px;")
        
        btn_all = QPushButton("Alle Spiele anzeigen →")
        btn_all.setProperty("class", "ghost-button")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.clicked.connect(lambda: self.navigate_to_tab.emit(1))

        top_row.addWidget(lbl_badge)
        top_row.addWidget(lbl_recent_pill)
        top_row.addStretch()
        top_row.addWidget(btn_all)
        layout.addLayout(top_row)

        # Hero Banner
        banner_container = QHBoxLayout()
        banner_container.setSpacing(18)

        # Poster Image
        lbl_art = QLabel()
        lbl_art.setFixedSize(115, 160)
        lbl_art.setStyleSheet("background-color: #0B0E14; border: 1px solid #202736; border-radius: 6px;")
        lbl_art.setAlignment(Qt.AlignmentFlag.AlignCenter)

        game_name = self.top_game.name if self.top_game else "Kein Spiel erkannt"
        if self.top_game and self.top_game.poster_image and os.path.isfile(self.top_game.poster_image):
            pm = QPixmap(self.top_game.poster_image).scaled(115, 160, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            lbl_art.setPixmap(pm.copy(0, 0, 115, 160))
        else:
            pix = QPixmap(115, 160)
            pix.fill(QColor("#131720"))
            p = QPainter(pix)
            p.setPen(QColor("#E01E37"))
            p.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))
            p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, game_name)
            p.end()
            lbl_art.setPixmap(pix)

        banner_container.addWidget(lbl_art)

        # Game Details & Launch
        game_info = QVBoxLayout()
        game_info.setSpacing(6)

        lbl_title = QLabel(game_name)
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF;")
        
        status_line = QHBoxLayout()
        status_line.setSpacing(8)
        lbl_platform = QLabel(f"Plattform: {self.top_game.platform.upper() if self.top_game else 'PC'}")
        lbl_platform.setStyleSheet("font-size: 11px; color: #7E8D9F; font-weight: 700;")
        
        badge_hypr = QLabel("HYPR-RX BEREIT")
        badge_hypr.setStyleSheet("background-color: rgba(0, 210, 255, 0.12); border: 1px solid #00D2FF; color: #00D2FF; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px;")
        status_line.addWidget(lbl_platform)
        status_line.addWidget(badge_hypr)
        status_line.addStretch()

        btn_launch = QPushButton("▶  SPIEL STARTEN")
        btn_launch.setProperty("class", "primary-red")
        btn_launch.setFixedHeight(40)
        btn_launch.setCursor(Qt.CursorShape.PointingHandCursor)
        if self.top_game:
            btn_launch.clicked.connect(lambda: self.play_game_requested.emit(self.top_game.app_id))

        game_info.addWidget(lbl_title)
        game_info.addLayout(status_line)
        game_info.addStretch()
        game_info.addWidget(btn_launch)

        banner_container.addLayout(game_info)
        layout.addLayout(banner_container)

        # Quick Graphic Features Panel (Adrenalin HYPR-RX style)
        feat_panel = QFrame()
        feat_panel.setStyleSheet("""
            QFrame {
                background-color: #0E121A;
                border: 1px solid #1C2330;
                border-radius: 6px;
                padding: 10px 14px;
            }
        """)
        fp_layout = QVBoxLayout(feat_panel)
        fp_layout.setContentsMargins(10, 8, 10, 8)
        fp_layout.setSpacing(10)

        toggles_grid = QGridLayout()
        toggles_grid.setHorizontalSpacing(24)
        toggles_grid.setVerticalSpacing(8)

        prof = self.profile_mgr.get_profile(self.top_game.app_id if self.top_game else "global")

        def _add_toggle(row: int, col: int, label_text: str, desc: str, checked: bool, on_change):
            box = QHBoxLayout()
            box.setSpacing(8)
            t_box = QVBoxLayout()
            t_box.setSpacing(1)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #E1E7EE;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("font-size: 9px; color: #6F7F93;")
            t_box.addWidget(lbl)
            t_box.addWidget(lbl_d)
            sw = ToggleSwitch(checked=checked)
            sw.toggled.connect(on_change)
            box.addLayout(t_box)
            box.addStretch()
            box.addWidget(sw)
            toggles_grid.addLayout(box, row, col)

        def _update_anti_lag(c):
            prof.anti_lag = c
            self.profile_mgr.save()

        def _update_fps_limit(c):
            prof.fps_limit_enabled = c
            self.profile_mgr.save()

        def _update_boost(c):
            prof.radeon_boost = c
            self.profile_mgr.save()

        def _update_mangohud(c):
            prof.mangohud = c
            self.profile_mgr.save()

        _add_toggle(0, 0, "⚡ Radeon Anti-Lag", "Eingabelatenz minimieren", prof.anti_lag, _update_anti_lag)
        _add_toggle(0, 1, "🎯 FPS-Begrenzer (Chill)", "Bildrate & Energie limitieren", prof.fps_limit_enabled, _update_fps_limit)
        _add_toggle(1, 0, "🚀 Radeon Boost", "Dynamische VRS-Skalierung", prof.radeon_boost, _update_boost)
        _add_toggle(1, 1, "📊 MangoHud Overlay", "Hardware-Telemetrie im Spiel", prof.mangohud, _update_mangohud)

        fp_layout.addLayout(toggles_grid)
        layout.addWidget(feat_panel)

        # Quick link to Swapper
        quick_row = QHBoxLayout()
        btn_swapper_link = QPushButton("⚡ FSR 4 KI-Upscaling & AFMF 2 Frame Generation im Swapper verwalten →")
        btn_swapper_link.setProperty("class", "ghost-button")
        btn_swapper_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_swapper_link.setStyleSheet("color: #E01E37; font-weight: 800; font-size: 11px; text-align: left; padding: 2px 0px;")
        btn_swapper_link.clicked.connect(lambda: self.navigate_to_tab.emit(1))
        quick_row.addWidget(btn_swapper_link)
        quick_row.addStretch()
        layout.addLayout(quick_row)
        return card

    def _create_perf_snapshot_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "adrenalin-card")
        card.setStyleSheet("""
            QFrame {
                background-color: #171B23;
                border: 1px solid #28303F;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        top_row = QHBoxLayout()
        lbl_badge = QLabel("LEISTUNGSÜBERSICHT")
        lbl_badge.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")

        btn_metrics = QPushButton("GPU Metriken →")
        btn_metrics.setProperty("class", "ghost-button")
        btn_metrics.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_metrics.clicked.connect(lambda: self.navigate_to_tab.emit(2))

        btn_ryzen = QPushButton("Ryzen Master →")
        btn_ryzen.setProperty("class", "ghost-button")
        btn_ryzen.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ryzen.setStyleSheet("color: #FF5500; font-weight: 800;")
        btn_ryzen.clicked.connect(lambda: self.navigate_to_tab.emit(3))

        top_row.addWidget(lbl_badge)
        top_row.addStretch()
        top_row.addWidget(btn_metrics)
        top_row.addWidget(btn_ryzen)
        layout.addLayout(top_row)

        # Telemetry cards mini grid (GPU + CPU)
        grid = QGridLayout()
        grid.setSpacing(10)

        self.card_temp = MetricCard("GPU TEMP", "°C", 110)
        self.card_load = MetricCard("GPU LOAD", "%", 100)
        self.card_cpu_temp = MetricCard("CPU TEMP", "°C", 100)
        self.card_cpu_temp.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F39C12, stop:1 #FF5500); border-radius: 2px; }
        """)
        self.card_cpu_power = MetricCard("CPU POWER", "W", 150)
        self.card_cpu_power.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00B0FF, stop:1 #00E676); border-radius: 2px; }
        """)
        self.card_vram = MetricCard("VRAM", "MB", self.gpu.vram_total_mb)
        self.card_clock = MetricCard("GPU TAKT", "MHz", 3500)

        grid.addWidget(self.card_temp, 0, 0)
        grid.addWidget(self.card_load, 0, 1)
        grid.addWidget(self.card_cpu_temp, 1, 0)
        grid.addWidget(self.card_cpu_power, 1, 1)
        grid.addWidget(self.card_vram, 2, 0)
        grid.addWidget(self.card_clock, 2, 1)

        layout.addLayout(grid)
        return card

    def _create_driver_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "adrenalin-card")
        card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px;")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        lbl_h = QLabel("TREIBER & SOFTWARE")
        lbl_h.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        layout.addWidget(lbl_h)

        # GPU Model & Driver status
        gpu_name = QLabel(self.gpu.model_name)
        gpu_name.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        layout.addWidget(gpu_name)

        status_row = QHBoxLayout()
        lbl_status = QLabel("Status:")
        lbl_status.setStyleSheet("color: #7E8D9F; font-size: 12px; font-weight: 600;")
        
        badge_ok = QLabel("✓ Auf dem neuesten Stand")
        badge_ok.setProperty("class", "badge-green")

        status_row.addWidget(lbl_status)
        status_row.addWidget(badge_ok)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Details
        info_lines = [
            ("Architektur", self.gpu.architecture),
            ("FSR 4 AI-Kerne", "Aktiviert (WMMA Matrix Cores)" if self.gpu.supports_fsr4 else "Nicht verfügbar"),
            ("Treiberversion", self.audit.mesa_version),
            ("Vulkan API", f"{self.audit.vulkan_version} ({self.audit.vulkan_driver})"),
            ("Kernel", self.audit.kernel_version),
            ("VBIOS", self.gpu.vbios_version)
        ]
        for k, v in info_lines:
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet("color: #7E8D9F; font-size: 11px;")
            l2 = QLabel(v)
            l2.setStyleSheet("color: #C5CFDC; font-size: 11px; font-weight: bold;")
            r.addWidget(l1)
            r.addStretch()
            r.addWidget(l2)
            layout.addLayout(r)

        layout.addStretch()
        btn_check = QPushButton("Nach Updates suchen")
        btn_check.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_check)

        return card

    def _create_system_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "adrenalin-card")
        card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px;")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        lbl_h = QLabel("SYSTEM & ANZEIGE")
        lbl_h.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        layout.addWidget(lbl_h)

        disp_title = QLabel(f"Display: {self.display.connector} ({self.display.resolution} @ {self.display.refresh_rate_hz}Hz)")
        disp_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        layout.addWidget(disp_title)

        vrr_badge = QLabel("✓ FreeSync / VRR Aktiv" if self.display.vrr_enabled else "FreeSync Aus")
        vrr_badge.setProperty("class", "badge-green" if self.display.vrr_enabled else "badge-gray")
        layout.addWidget(vrr_badge, alignment=Qt.AlignmentFlag.AlignLeft)

        info_lines = [
            ("VRAM Kapazität", f"{self.gpu.vram_total_mb} MB ({self.gpu.vram_vendor})"),
            ("Power Limit (PPT)", f"{self.gpu.power_cap_default_w} W"),
            ("PCIe Interface", f"{self.audit.pcie_link_width} ({self.audit.pcie_link_speed})"),
            ("Desktop / Server", f"{self.audit.desktop_env} ({self.audit.session_type.capitalize()})")
        ]
        for k, v in info_lines:
            r = QHBoxLayout()
            l1 = QLabel(k)
            l1.setStyleSheet("color: #7E8D9F; font-size: 11px;")
            l2 = QLabel(v)
            l2.setStyleSheet("color: #C5CFDC; font-size: 11px; font-weight: bold;")
            r.addWidget(l1)
            r.addStretch()
            r.addWidget(l2)
            layout.addLayout(r)

        layout.addStretch()
        btn_disp = QPushButton("Anzeigeeinstellungen verwalten")
        btn_disp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_disp.clicked.connect(lambda: self.navigate_to_tab.emit(4))
        layout.addWidget(btn_disp)

        return card

    def update_telemetry(self, data: dict):
        temp = data.get("temp_edge", 0.0)
        hotspot = data.get("temp_junction", 0.0)
        self.card_temp.set_value(temp, display_str=f"{temp:.0f}", sub_str=f"Hotspot: {hotspot:.0f}°C")
        
        load = data.get("gpu_busy", 0)
        self.card_load.set_value(load, display_str=f"{load}")
        
        vram_used = data.get("vram_used_mb", 0)
        vram_pct = data.get("vram_pct", 0)
        self.card_vram.set_value(vram_used, display_str=f"{vram_used}", sub_str=f"{vram_pct}% belegt")
        
        clock = data.get("sclk", 0)
        power = data.get("power_w", 0)
        self.card_clock.set_value(clock, display_str=f"{clock}", sub_str=f"Power: {power:.0f} W")

    def update_cpu_telemetry(self, data: dict):
        if hasattr(self, "card_cpu_temp"):
            tctl = data.get("temp_tctl", 0.0)
            tccd1 = data.get("temp_tccd1", 0.0)
            self.card_cpu_temp.set_value(tctl, display_str=f"{tctl:.0f}", sub_str=f"CCD: {tccd1:.0f}°C" if tccd1 > 0 else "")
        if hasattr(self, "card_cpu_power"):
            pkg_w = data.get("package_power_w", 0.0)
            peak_mhz = data.get("peak_freq_mhz", 0.0)
            self.card_cpu_power.set_value(pkg_w, display_str=f"{pkg_w:.1f}", sub_str=f"{peak_mhz:.0f} MHz Peak")
