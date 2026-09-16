"""MangoHud Overlay Settings Editor and Dialog for AMD Control Center."""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QScrollArea, QFrame, QDialog,
    QMessageBox, QSplitter
)

from ..backend.mangohud_manager import (
    MangoHudConfig, load_mangohud_config, save_mangohud_config,
    get_mangohud_presets, apply_preset
)
from .styled_slider import StyledSlider


class MangoHudPreviewWidget(QFrame):
    """Visual real-time simulation of the in-game MangoHud overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 220)
        self.setStyleSheet("""
            MangoHudPreviewWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121620, stop:1 #080A0E);
                border: 1px solid #232A38;
                border-radius: 8px;
            }
        """)

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)

        # The simulated overlay HUD box
        self.hud_box = QFrame()
        self.hud_layout = QVBoxLayout(self.hud_box)
        self.hud_layout.setContentsMargins(8, 6, 8, 6)
        self.hud_layout.setSpacing(2)

        self.lbl_hud_text = QLabel()
        self.lbl_hud_text.setTextFormat(Qt.TextFormat.RichText)
        self.hud_layout.addWidget(self.lbl_hud_text)

        self.hud_box.setMaximumWidth(280)
        self.layout.addWidget(self.hud_box, 0, 0)

        # Center watermark label
        self.lbl_center = QLabel("Simuliertes Spiel (Live-Vorschau)")
        self.lbl_center.setStyleSheet("color: rgba(255, 255, 255, 0.15); font-weight: 800; font-size: 13px;")
        self.lbl_center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_center, 1, 1)

    def update_preview(self, config: MangoHudConfig):
        # 1. Update Grid Alignment according to position
        self.layout.removeWidget(self.hud_box)

        r, c = 0, 0
        pos = config.position.lower()
        if "top" in pos:
            r = 0
        elif "bottom" in pos:
            r = 2
        else:
            r = 1

        if "left" in pos:
            c = 0
        elif "right" in pos:
            c = 2
        else:
            c = 1

        align = Qt.AlignmentFlag.AlignTop if r == 0 else (Qt.AlignmentFlag.AlignBottom if r == 2 else Qt.AlignmentFlag.AlignVCenter)
        if c == 0:
            align |= Qt.AlignmentFlag.AlignLeft
        elif c == 2:
            align |= Qt.AlignmentFlag.AlignRight
        else:
            align |= Qt.AlignmentFlag.AlignHCenter

        self.layout.addWidget(self.hud_box, r, c, align)

        # 2. Update HUD Box styling
        alpha = int(config.background_alpha * 255)
        rc = config.round_corners
        self.hud_box.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(10, 12, 16, {alpha});
                border: 1px solid rgba(255, 255, 255, {min(100, int(alpha * 0.8))});
                border-radius: {rc}px;
            }}
        """)

        # 3. Generate Simulated Lines
        f_size = max(9, int(config.font_size * 0.45))
        lines = []

        # GPU
        gpu_items = []
        if config.gpu_stats:
            gpu_items.append("<span style='color:#FFFFFF;'>99%</span>")
        if config.gpu_temp:
            gpu_items.append("<span style='color:#2ECC71;'>62°C</span>")
        if config.gpu_junction_temp:
            gpu_items.append("<span style='color:#E67E22;'>74°C Hotspot</span>")
        if config.gpu_core_clock:
            gpu_items.append("<span style='color:#00E5FF;'>2450 MHz</span>")
        if config.gpu_power:
            gpu_items.append("<span style='color:#FF9800;'>280 W</span>")

        if gpu_items:
            lines.append(f"<b><span style='color:#2ECC71;'>GPU:</span></b> " + " | ".join(gpu_items))

        if config.vram:
            lines.append("<b><span style='color:#AD64C1;'>VRAM:</span></b> 9240 MB / 16384 MB")

        # CPU
        cpu_items = []
        if config.cpu_stats:
            cpu_items.append("<span style='color:#FFFFFF;'>48%</span>")
        if config.cpu_temp:
            cpu_items.append("<span style='color:#2E97CB;'>58°C</span>")
        if config.cpu_mhz:
            cpu_items.append("<span style='color:#00E5FF;'>4850 MHz</span>")
        if config.cpu_power:
            cpu_items.append("<span style='color:#FF9800;'>72 W</span>")

        if cpu_items:
            lines.append(f"<b><span style='color:#2E97CB;'>CPU:</span></b> " + " | ".join(cpu_items))

        if config.ram:
            lines.append("<b><span style='color:#C26693;'>RAM:</span></b> 14.8 GB")

        # FPS & Frame Time
        fps_items = []
        if config.fps:
            fps_items.append("<b><span style='color:#00FF00;'>144 FPS</span></b>")
        if config.frame_timing:
            fps_items.append("<span style='color:#FFFFFF;'>6.9 ms</span>")

        if fps_items:
            lines.append(" ".join(fps_items))

        if config.frame_timing:
            lines.append("<span style='color:#00FF00;'>[ ∿∿∿ Frametime Graph ∿∿∿ ]</span>")

        # Advanced
        adv = []
        if config.resolution:
            adv.append("3840x2160")
        if config.fsr:
            adv.append("FSR 4 Neural")
        if config.gamemode:
            adv.append("GameMode")
        if config.arch:
            adv.append("RDNA 4")
        if config.wine:
            adv.append("Proton GE")
        if config.time:
            adv.append("20:45")

        if adv:
            lines.append("<span style='color:#7E8D9F; font-size: 8px;'>" + " • ".join(adv) + "</span>")

        if not lines:
            lines.append("<span style='color:#7E8D9F;'>Keine Metriken aktiv</span>")

        html = f"<div style='font-family: monospace; font-size: {f_size}px; line-height: 1.25;'>" + "<br>".join(lines) + "</div>"
        self.lbl_hud_text.setText(html)


class MangoHudSettingsWidget(QWidget):
    """Full-featured MangoHud configuration interface with presets and real-time preview."""
    config_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_mangohud_config()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        # 1. Preset Selector Bar
        p_frame = QFrame()
        p_frame.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 6px; padding: 10px 14px;")
        p_layout = QHBoxLayout(p_frame)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(10)

        lbl_p = QLabel("⚡ SCHNELL-PROFIL:")
        lbl_p.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1px;")
        p_layout.addWidget(lbl_p)

        self.btn_preset_min = QPushButton("Minimal (Nur FPS)")
        self.btn_preset_komp = QPushButton("Kompakt")
        self.btn_preset_std = QPushButton("Standard (Adrenalin)")
        self.btn_preset_full = QPushButton("Vollständig (Alle Details)")

        preset_style = """
            QPushButton {
                background-color: #12151B;
                border: 1px solid #28303F;
                color: #A8B2C4;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """
        for b, name in [
            (self.btn_preset_min, "Minimal"),
            (self.btn_preset_komp, "Kompakt"),
            (self.btn_preset_std, "Standard (Adrenalin)"),
            (self.btn_preset_full, "Vollständig (Alle Details)")
        ]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(preset_style)
            b.clicked.connect(lambda _, n=name: self._on_preset_clicked(n))
            p_layout.addWidget(b)

        p_layout.addStretch()
        main_layout.addWidget(p_frame)

        # 2. Main Content Split: Settings Left, Live Preview Right
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(16)

        # Left Column: Scrollable Settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        settings_container = QWidget()
        s_layout = QVBoxLayout(settings_container)
        s_layout.setContentsMargins(0, 0, 8, 0)
        s_layout.setSpacing(14)

        # --- A. Layout & Appearance Card ---
        card_layout, cl_layout = self._create_card("LAYOUT & ERSCHEINUNGSBILD", is_grid=False)

        # Position Selector
        pos_row = QHBoxLayout()
        pos_lbl = QLabel("Bildschirm-Position:")
        pos_lbl.setStyleSheet("font-weight: bold; color: #FFFFFF; font-size: 11px;")
        self.combo_pos = QComboBox()
        self.combo_pos.addItems([
            "Oben Links (top-left)",
            "Oben Rechts (top-right)",
            "Unten Links (bottom-left)",
            "Unten Rechts (bottom-right)",
            "Oben Mitte (top-center)",
            "Unten Mitte (bottom-center)"
        ])
        pos_map = {
            "top-left": 0, "top-right": 1, "bottom-left": 2,
            "bottom-right": 3, "top-center": 4, "bottom-center": 5
        }
        self.combo_pos.setCurrentIndex(pos_map.get(self.config.position.lower(), 0))
        self.combo_pos.currentIndexChanged.connect(self._sync_to_preview)
        pos_row.addWidget(pos_lbl)
        pos_row.addWidget(self.combo_pos)
        pos_row.addStretch()
        cl_layout.addLayout(pos_row)

        # Sliders
        self.slider_font = StyledSlider("Schriftgröße", 16, 44, self.config.font_size, " px", step=1)
        self.slider_font.valueChanged.connect(self._sync_to_preview)
        cl_layout.addWidget(self.slider_font)

        self.slider_alpha = StyledSlider("Hintergrund-Deckkraft", 0, 100, int(self.config.background_alpha * 100), " %", step=5)
        self.slider_alpha.valueChanged.connect(self._sync_to_preview)
        cl_layout.addWidget(self.slider_alpha)

        # Round corners & columns row
        rc_row = QHBoxLayout()
        rc_lbl = QLabel("Ecken abrunden:")
        rc_lbl.setStyleSheet("color: #C5CFDC; font-size: 11px;")
        self.spin_corners = QSpinBox()
        self.spin_corners.setRange(0, 20)
        self.spin_corners.setValue(self.config.round_corners)
        self.spin_corners.valueChanged.connect(self._sync_to_preview)

        col_lbl = QLabel("Spalten:")
        col_lbl.setStyleSheet("color: #C5CFDC; font-size: 11px; margin-left: 16px;")
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 6)
        self.spin_cols.setValue(self.config.table_columns)
        self.spin_cols.valueChanged.connect(self._sync_to_preview)

        hotkey_lbl = QLabel("Umschalt-Taste:")
        hotkey_lbl.setStyleSheet("color: #C5CFDC; font-size: 11px; margin-left: 16px;")
        self.combo_hotkey = QComboBox()
        self.combo_hotkey.addItems(["Shift_R+F12", "F12", "Shift_L+F12", "Control_L+F12", "F11", "Shift_R+F11"])
        self.combo_hotkey.setCurrentText(self.config.toggle_hud)
        self.combo_hotkey.currentTextChanged.connect(self._sync_to_preview)

        rc_row.addWidget(rc_lbl)
        rc_row.addWidget(self.spin_corners)
        rc_row.addWidget(col_lbl)
        rc_row.addWidget(self.spin_cols)
        rc_row.addWidget(hotkey_lbl)
        rc_row.addWidget(self.combo_hotkey)
        rc_row.addStretch()
        cl_layout.addLayout(rc_row)

        self.chk_no_display = QCheckBox("Overlay beim Spielstart ausgeblendet lassen (erst per Hotkey einblenden)")
        self.chk_no_display.setChecked(self.config.no_display)
        self.chk_no_display.setStyleSheet("font-size: 11px; color: #A8B2C4;")
        self.chk_no_display.toggled.connect(self._sync_to_preview)
        cl_layout.addWidget(self.chk_no_display)

        s_layout.addWidget(card_layout)

        # --- B. Framerate & Timing Card ---
        card_fps, cf_layout = self._create_card("FRAMERATE & TIMING", is_grid=False)
        self.chk_fps = self._add_checkbox(cf_layout, "FPS-Zähler (Aktuelle Bildrate anzeigen)", self.config.fps)
        self.chk_frame_timing = self._add_checkbox(cf_layout, "Frametime & Latenz-Verlaufsgraph anzeigen", self.config.frame_timing)
        s_layout.addWidget(card_fps)

        # --- C. GPU Metrics Card ---
        card_gpu, cg_layout = self._create_card("AMD RADEON GPU-METRIKEN", is_grid=True)
        self.chk_gpu_stats = self._grid_checkbox(cg_layout, "GPU-Auslastung (%)", self.config.gpu_stats, 0, 0)
        self.chk_gpu_temp = self._grid_checkbox(cg_layout, "GPU Edge-Temperatur (°C)", self.config.gpu_temp, 0, 1)
        self.chk_gpu_junction = self._grid_checkbox(cg_layout, "GPU Hotspot-Temperatur (°C)", self.config.gpu_junction_temp, 1, 0)
        self.chk_gpu_clock = self._grid_checkbox(cg_layout, "GPU Kerntakt (MHz)", self.config.gpu_core_clock, 1, 1)
        self.chk_gpu_mem_clock = self._grid_checkbox(cg_layout, "VRAM Speichertakt (MHz)", self.config.gpu_mem_clock, 2, 0)
        self.chk_gpu_power = self._grid_checkbox(cg_layout, "Leistungsaufnahme (Watt)", self.config.gpu_power, 2, 1)
        self.chk_gpu_voltage = self._grid_checkbox(cg_layout, "GPU Spannung (mV)", self.config.gpu_voltage, 3, 0)
        self.chk_vram = self._grid_checkbox(cg_layout, "VRAM-Nutzung (MB)", self.config.vram, 3, 1)
        s_layout.addWidget(card_gpu)

        # --- D. CPU & RAM Metrics Card ---
        card_cpu, cc_layout = self._create_card("CPU & ARBEITSSPEICHER (RAM)", is_grid=True)
        self.chk_cpu_stats = self._grid_checkbox(cc_layout, "CPU-Auslastung (%)", self.config.cpu_stats, 0, 0)
        self.chk_cpu_temp = self._grid_checkbox(cc_layout, "CPU-Temperatur (°C)", self.config.cpu_temp, 0, 1)
        self.chk_cpu_mhz = self._grid_checkbox(cc_layout, "CPU-Taktfrequenz (MHz)", self.config.cpu_mhz, 1, 0)
        self.chk_cpu_power = self._grid_checkbox(cc_layout, "CPU Leistungsaufnahme (Watt)", self.config.cpu_power, 1, 1)
        self.chk_core_load = self._grid_checkbox(cc_layout, "Einzellast aller CPU-Kerne", self.config.core_load, 2, 0)
        self.chk_ram = self._grid_checkbox(cc_layout, "RAM-Speichernutzung (GB)", self.config.ram, 2, 1)
        s_layout.addWidget(card_cpu)

        # --- E. Advanced Info Card ---
        card_adv, ca_layout = self._create_card("ERWEITERTE SPIEL- & SYSTEM-INFOS", is_grid=True)
        self.chk_fsr = self._grid_checkbox(ca_layout, "FSR Status-Anzeige", self.config.fsr, 0, 0)
        self.chk_resolution = self._grid_checkbox(ca_layout, "Render-Auflösung", self.config.resolution, 0, 1)
        self.chk_vulkan = self._grid_checkbox(ca_layout, "Vulkan / Mesa Treiber", self.config.vulkan_driver, 1, 0)
        self.chk_arch = self._grid_checkbox(ca_layout, "GPU Architektur (RDNA)", self.config.arch, 1, 1)
        self.chk_wine = self._grid_checkbox(ca_layout, "Proton / Wine Version", self.config.wine, 2, 0)
        self.chk_gamemode = self._grid_checkbox(ca_layout, "Feral GameMode", self.config.gamemode, 2, 1)
        self.chk_time = self._grid_checkbox(ca_layout, "Aktuelle Uhrzeit", self.config.time, 3, 0)
        s_layout.addWidget(card_adv)

        scroll.setWidget(settings_container)
        split_layout.addWidget(scroll, stretch=3)

        # Right Column: Live Preview & Save Actions
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        prev_header = QLabel("LIVE-VORSCHAU:")
        prev_header.setStyleSheet("font-size: 11px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;")
        right_panel.addWidget(prev_header)

        self.preview_widget = MangoHudPreviewWidget()
        right_panel.addWidget(self.preview_widget, stretch=1)

        btn_save = QPushButton("💾 MANGOHUD EINSTELLUNGEN SPEICHERN")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B31227);
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: 900;
                font-size: 12px;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #CC172F);
            }
        """)
        btn_save.clicked.connect(self._save_config)
        right_panel.addWidget(btn_save)

        btn_reload = QPushButton("↺ Auf aktuelle Datei zurücksetzen")
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.setStyleSheet("""
            QPushButton {
                background-color: #171B23;
                border: 1px solid #28303F;
                color: #A8B2C4;
                font-size: 11px;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        btn_reload.clicked.connect(self._reload_from_disk)
        right_panel.addWidget(btn_reload)

        split_layout.addLayout(right_panel, stretch=2)
        main_layout.addWidget(split_widget)

        self._sync_to_preview()

    def _create_card(self, title: str, is_grid: bool = False):
        card = QFrame()
        card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 12px;")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1px; margin-bottom: 4px;")
        v.addWidget(lbl)
        if is_grid:
            g = QGridLayout()
            g.setSpacing(8)
            v.addLayout(g)
            return card, g
        else:
            inner_v = QVBoxLayout()
            inner_v.setSpacing(8)
            v.addLayout(inner_v)
            return card, inner_v

    def _add_checkbox(self, layout: QVBoxLayout, text: str, checked: bool) -> QCheckBox:
        chk = QCheckBox(text)
        chk.setChecked(checked)
        chk.setStyleSheet("font-size: 11px; font-weight: bold; color: #E1E7EE;")
        chk.toggled.connect(self._sync_to_preview)
        layout.addWidget(chk)
        return chk

    def _grid_checkbox(self, layout: QGridLayout, text: str, checked: bool, row: int, col: int) -> QCheckBox:
        chk = QCheckBox(text)
        chk.setChecked(checked)
        chk.setStyleSheet("font-size: 11px; color: #C5CFDC;")
        chk.toggled.connect(self._sync_to_preview)
        layout.addWidget(chk, row, col)
        return chk

    def _on_preset_clicked(self, name: str):
        apply_preset(name, self.config)
        self._update_ui_from_config()

    def _update_ui_from_config(self):
        self._is_updating = True
        try:
            self.slider_font.setValue(self.config.font_size)
            self.slider_alpha.setValue(int(self.config.background_alpha * 100))
            self.spin_corners.setValue(self.config.round_corners)
            self.spin_cols.setValue(self.config.table_columns)
            self.combo_hotkey.setCurrentText(self.config.toggle_hud)
            self.chk_no_display.setChecked(self.config.no_display)

            # FPS
            self.chk_fps.setChecked(self.config.fps)
            self.chk_frame_timing.setChecked(self.config.frame_timing)

            # GPU
            self.chk_gpu_stats.setChecked(self.config.gpu_stats)
            self.chk_gpu_temp.setChecked(self.config.gpu_temp)
            self.chk_gpu_junction.setChecked(self.config.gpu_junction_temp)
            self.chk_gpu_clock.setChecked(self.config.gpu_core_clock)
            self.chk_gpu_mem_clock.setChecked(self.config.gpu_mem_clock)
            self.chk_gpu_power.setChecked(self.config.gpu_power)
            self.chk_gpu_voltage.setChecked(self.config.gpu_voltage)
            self.chk_vram.setChecked(self.config.vram)

            # CPU
            self.chk_cpu_stats.setChecked(self.config.cpu_stats)
            self.chk_cpu_temp.setChecked(self.config.cpu_temp)
            self.chk_cpu_mhz.setChecked(self.config.cpu_mhz)
            self.chk_cpu_power.setChecked(self.config.cpu_power)
            self.chk_core_load.setChecked(self.config.core_load)
            self.chk_ram.setChecked(self.config.ram)

            # Advanced
            self.chk_fsr.setChecked(self.config.fsr)
            self.chk_resolution.setChecked(self.config.resolution)
            self.chk_vulkan.setChecked(self.config.vulkan_driver)
            self.chk_arch.setChecked(self.config.arch)
            self.chk_wine.setChecked(self.config.wine)
            self.chk_gamemode.setChecked(self.config.gamemode)
            self.chk_time.setChecked(self.config.time)
        finally:
            self._is_updating = False
        self._sync_to_preview()

    def _sync_to_preview(self):
        if getattr(self, '_is_updating', False):
            return
        # Read UI to self.config
        pos_keys = ["top-left", "top-right", "bottom-left", "bottom-right", "top-center", "bottom-center"]
        self.config.position = pos_keys[self.combo_pos.currentIndex()]
        self.config.font_size = self.slider_font.value()
        self.config.background_alpha = self.slider_alpha.value() / 100.0
        self.config.round_corners = self.spin_corners.value()
        self.config.table_columns = self.spin_cols.value()
        self.config.toggle_hud = self.combo_hotkey.currentText()
        self.config.no_display = self.chk_no_display.isChecked()

        # Metrics
        self.config.fps = self.chk_fps.isChecked()
        self.config.frame_timing = self.chk_frame_timing.isChecked()

        self.config.gpu_stats = self.chk_gpu_stats.isChecked()
        self.config.gpu_temp = self.chk_gpu_temp.isChecked()
        self.config.gpu_junction_temp = self.chk_gpu_junction.isChecked()
        self.config.gpu_core_clock = self.chk_gpu_clock.isChecked()
        self.config.gpu_mem_clock = self.chk_gpu_mem_clock.isChecked()
        self.config.gpu_power = self.chk_gpu_power.isChecked()
        self.config.gpu_voltage = self.chk_gpu_voltage.isChecked()
        self.config.vram = self.chk_vram.isChecked()

        self.config.cpu_stats = self.chk_cpu_stats.isChecked()
        self.config.cpu_temp = self.chk_cpu_temp.isChecked()
        self.config.cpu_mhz = self.chk_cpu_mhz.isChecked()
        self.config.cpu_power = self.chk_cpu_power.isChecked()
        self.config.core_load = self.chk_core_load.isChecked()
        self.config.ram = self.chk_ram.isChecked()

        self.config.fsr = self.chk_fsr.isChecked()
        self.config.resolution = self.chk_resolution.isChecked()
        self.config.vulkan_driver = self.chk_vulkan.isChecked()
        self.config.arch = self.chk_arch.isChecked()
        self.config.wine = self.chk_wine.isChecked()
        self.config.gamemode = self.chk_gamemode.isChecked()
        self.config.time = self.chk_time.isChecked()

        self.preview_widget.update_preview(self.config)

    def _save_config(self):
        self._sync_to_preview()
        ok, msg = save_mangohud_config(self.config)
        if ok:
            QMessageBox.information(self, "MangoHud Overlay", "Die MangoHud Konfiguration wurde erfolgreich gespeichert!\nAlle nachfolgend gestarteten Spiele nutzen die neuen Overlay-Einstellungen.")
            self.config_saved.emit()
        else:
            QMessageBox.critical(self, "Fehler beim Speichern", msg)

    def _reload_from_disk(self):
        self.config = load_mangohud_config()
        self._update_ui_from_config()
        self._sync_to_preview()


class MangoHudSettingsDialog(QDialog):
    """Modal dialog displaying MangoHudSettingsWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MangoHud Overlay-Einstellungen (In-Game Telemetrie)")
        self.resize(960, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #0E1015;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Row
        h_row = QHBoxLayout()
        t_lbl = QLabel("🎮 MANGOHUD OVERLAY-EINSTELLUNGEN")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        h_row.addWidget(t_lbl)
        h_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        btn_close.clicked.connect(self.accept)
        h_row.addWidget(btn_close)
        layout.addLayout(h_row)

        desc = QLabel("Konfiguriere das in DirectX & Vulkan Spielen angezeigte Hardware-Overlay (FPS, Frametimes, GPU/CPU Temperaturen & Taktraten).")
        desc.setStyleSheet("color: #7E8D9F; font-size: 11px;")
        layout.addWidget(desc)

        self.editor = MangoHudSettingsWidget()
        layout.addWidget(self.editor, stretch=1)
