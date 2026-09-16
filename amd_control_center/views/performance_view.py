"""Performance View (Metriken & Tuning) for AMD Control Center."""

from typing import Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QGridLayout, QComboBox,
    QMessageBox
)

from ..backend.gpu_detector import GpuDevice
from ..backend.gpu_tuner import TuningProfile, execute_via_pkexec
from ..widgets.metric_card import MetricCard
from ..widgets.realtime_chart import RealtimeChartWidget
from ..widgets.styled_slider import StyledSlider
from ..widgets.toggle_switch import ToggleSwitch
from ..widgets.fan_curve_editor import FanCurveEditor
from ..widgets.mangohud_editor import MangoHudSettingsWidget


class PerformanceView(QWidget):
    interval_changed = pyqtSignal(int)
    overlay_toggle_requested = pyqtSignal()

    def __init__(self, gpu: GpuDevice, parent=None):
        super().__init__(parent)
        self.gpu = gpu
        self.profile = TuningProfile(
            sclk_offset_mhz=0,
            vddc_offset_mv=0,
            mclk_mhz=0,
            power_limit_w=gpu.power_cap_default_w,
            zero_rpm=True,
            manual_fan=False,
            fan_speed_pct=50
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(14)

        # Subtabs Row
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.btn_metrics = QPushButton("METRIKEN")
        self.btn_tuning = QPushButton("TUNING")
        self.btn_overlay = QPushButton("OVERLAY (MANGOHUD)")

        self.subtabs = [self.btn_metrics, self.btn_tuning, self.btn_overlay]
        for idx, b in enumerate(self.subtabs):
            b.setCheckable(True)
            b.setProperty("class", "subnav-tab")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, i=idx: self._switch_subtab(i))

        self.btn_metrics.setChecked(True)

        top_bar.addWidget(self.btn_metrics)
        top_bar.addWidget(self.btn_tuning)
        top_bar.addWidget(self.btn_overlay)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        # Stack: 0 -> Metrics, 1 -> Tuning, 2 -> MangoHud Overlay
        self.stack = QStackedWidget()
        self.metrics_page = self._create_metrics_page()
        self.tuning_page = self._create_tuning_page()
        self.overlay_page = self._create_overlay_page()

        self.stack.addWidget(self.metrics_page)
        self.stack.addWidget(self.tuning_page)
        self.stack.addWidget(self.overlay_page)

        layout.addWidget(self.stack)

    def _switch_subtab(self, idx: int):
        self.btn_metrics.setChecked(idx == 0)
        self.btn_tuning.setChecked(idx == 1)
        self.btn_overlay.setChecked(idx == 2)
        self.stack.setCurrentIndex(idx)

    def _create_overlay_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(14)

        # Header Banner
        banner = QFrame()
        banner.setProperty("class", "adrenalin-banner")
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #181C26, stop:1 #11141B);
                border: 1px solid #28303F;
                border-top: 2px solid #E01E37;
                border-radius: 8px;
                padding: 14px 18px;
            }
        """)
        b_l = QVBoxLayout(banner)
        b_l.setSpacing(4)
        t = QLabel("🎮 MANGOHUD IN-GAME OVERLAY-EINSTELLUNGEN")
        t.setStyleSheet("font-size: 15px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        d = QLabel("Konfiguriere das In-Game Hardware-Overlay für Vulkan & DirectX Spiele (FPS, Latenz-Graphen, AMD Radeon GPU- & CPU-Telemetrie).")
        d.setStyleSheet("color: #7E8D9F; font-size: 11px;")
        b_l.addWidget(t)
        b_l.addWidget(d)
        layout.addWidget(banner)

        # Editor
        self.mangohud_editor = MangoHudSettingsWidget()
        layout.addWidget(self.mangohud_editor)

        scroll.setWidget(container)
        return scroll

    def _create_metrics_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(18)

        # 6 Telemetry Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.c_load = MetricCard("GPU AUSLASTUNG", "%", 100)
        self.c_clock = MetricCard("GPU TAKT", "MHz", 3500)
        self.c_temp = MetricCard("GPU TEMPERATUR", "°C", 110)
        self.c_vram = MetricCard("VRAM SPEICHER", "MB", self.gpu.vram_total_mb)
        self.c_power = MetricCard("LEISTUNGSAUFNAHME", "W", self.gpu.power_cap_max_w or 400)
        self.c_fan = MetricCard("LÜFTERDREHZAHL", "RPM", 3600)

        grid.addWidget(self.c_load, 0, 0)
        grid.addWidget(self.c_clock, 0, 1)
        grid.addWidget(self.c_temp, 0, 2)
        grid.addWidget(self.c_vram, 1, 0)
        grid.addWidget(self.c_power, 1, 1)
        grid.addWidget(self.c_fan, 1, 2)

        layout.addLayout(grid)

        # Chart Container Card
        chart_card = QFrame()
        chart_card.setProperty("class", "adrenalin-card")
        chart_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        cc_layout = QVBoxLayout(chart_card)
        cc_layout.setSpacing(12)

        # Chart Header
        ch_row = QHBoxLayout()
        lbl_ct = QLabel("ECHTZEIT-HISTORIE")
        lbl_ct.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        
        lbl_rate = QLabel("Abtastrate:")
        lbl_rate.setStyleSheet("color: #7E8D9F; font-size: 11px; font-weight: bold;")
        
        combo_rate = QComboBox()
        combo_rate.addItems(["0.5 s", "1.0 s", "2.0 s"])
        combo_rate.setCurrentText("1.0 s")
        combo_rate.currentIndexChanged.connect(self._on_rate_change)

        ch_row.addWidget(lbl_ct)
        ch_row.addStretch()
        ch_row.addWidget(lbl_rate)
        ch_row.addWidget(combo_rate)
        cc_layout.addLayout(ch_row)

        # Custom QPainter Chart
        self.chart = RealtimeChartWidget()
        cc_layout.addWidget(self.chart)

        layout.addWidget(chart_card)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _on_rate_change(self, idx: int):
        intervals = [500, 1000, 2000]
        self.interval_changed.emit(intervals[idx])

    def _create_tuning_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(16)

        # Safety & Unlock Card
        warn_card = QFrame()
        warn_card.setStyleSheet("background-color: #1F1912; border: 1px solid #F39C12; border-radius: 8px; padding: 14px;")
        w_layout = QHBoxLayout(warn_card)
        w_layout.setSpacing(12)

        lbl_w_icon = QLabel("⚠️")
        lbl_w_icon.setStyleSheet("font-size: 24px;")
        
        w_text = QVBoxLayout()
        l1 = QLabel("LEISTUNGSTUNING & ÜBERTAKTUNG")
        l1.setStyleSheet("font-weight: 800; color: #F39C12; font-size: 12px; letter-spacing: 1px;")
        l2 = QLabel("Das Modifizieren von Taktfrequenzen, Spannungen und Leistungsgrenzen erfolgt auf eigene Verantwortung. Stelle sicher, dass die Kühlung ausreichend dimensioniert ist.")
        l2.setStyleSheet("color: #D1D7E0; font-size: 11px;")
        w_text.addWidget(l1)
        w_text.addWidget(l2)

        self.sw_unlock = ToggleSwitch(checked=False)
        self.sw_unlock.toggled.connect(self._on_unlock_toggled)

        w_layout.addWidget(lbl_w_icon)
        w_layout.addLayout(w_text)
        w_layout.addStretch()
        w_layout.addWidget(QLabel("Tuning Freischalten:"))
        w_layout.addWidget(self.sw_unlock)

        layout.addWidget(warn_card)

        # Tuning Container (disabled until unlocked)
        self.tuning_container = QWidget()
        self.tuning_container.setEnabled(False)
        t_layout = QVBoxLayout(self.tuning_container)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(16)

        # 1. GPU Tuning Card (Offset & Undervolt)
        gpu_card = QFrame()
        gpu_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        gc_layout = QVBoxLayout(gpu_card)
        lbl_gt = QLabel("GPU TAKT & SPANNUNG (UNDERVOLTING)")
        lbl_gt.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        gc_layout.addWidget(lbl_gt)

        self.sl_sclk = StyledSlider(
            "GPU Taktfrequenz-Offset (SCLK)",
            self.gpu.od_sclk_min or -500,
            self.gpu.od_sclk_max or 1000,
            0,
            "MHz",
            step=10
        )
        self.sl_sclk.valueChanged.connect(lambda v: setattr(self.profile, "sclk_offset_mhz", v))
        gc_layout.addWidget(self.sl_sclk)

        self.sl_vddc = StyledSlider(
            "GPU Spannungs-Offset (Undervolting)",
            self.gpu.od_vddc_offset_min or -200,
            self.gpu.od_vddc_offset_max or 0,
            0,
            "mV",
            step=5
        )
        self.sl_vddc.valueChanged.connect(lambda v: setattr(self.profile, "vddc_offset_mv", v))
        gc_layout.addWidget(self.sl_vddc)

        t_layout.addWidget(gpu_card)

        # 2. VRAM Tuning Card
        vram_card = QFrame()
        vram_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        vc_layout = QVBoxLayout(vram_card)
        lbl_vt = QLabel("VRAM SPEICHERTUNING")
        lbl_vt.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        vc_layout.addWidget(lbl_vt)

        self.sl_mclk = StyledSlider(
            "Speichertakt (MCLK)",
            self.gpu.od_mclk_min or 97,
            self.gpu.od_mclk_max or 1500,
            self.gpu.od_mclk_min or 97,
            "MHz",
            step=10
        )
        self.sl_mclk.valueChanged.connect(lambda v: setattr(self.profile, "mclk_mhz", v))
        vc_layout.addWidget(self.sl_mclk)

        t_layout.addWidget(vram_card)

        # 3. Fan Tuning Card
        fan_card = QFrame()
        fan_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        fc_layout = QVBoxLayout(fan_card)
        lbl_ft = QLabel("LÜFTERSTEUERUNG & ZERO-RPM")
        lbl_ft.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        fc_layout.addWidget(lbl_ft)

        fan_top = QHBoxLayout()
        fan_top.addWidget(QLabel("Zero-RPM Modus (Lüfterstopp bei niedriger Temperatur):"))
        self.sw_zero_rpm = ToggleSwitch(checked=True)
        self.sw_zero_rpm.toggled.connect(lambda c: setattr(self.profile, "zero_rpm", c))
        fan_top.addWidget(self.sw_zero_rpm)
        fan_top.addStretch()
        fc_layout.addLayout(fan_top)

        # Fan curve editor
        fc_layout.addSpacing(6)
        lbl_curve = QLabel("Benutzerdefinierte 5-Punkte-Lüfterkurve (Temperatur vs. Lüfterdrehzahl %):")
        lbl_curve.setStyleSheet("font-weight: bold; color: #C5CFDC;")
        fc_layout.addWidget(lbl_curve)

        self.fan_curve = FanCurveEditor()
        self.fan_curve.curveChanged.connect(lambda c: setattr(self.profile, "fan_curve", c))
        fc_layout.addWidget(self.fan_curve)

        t_layout.addWidget(fan_card)

        # 4. Power Tuning Card
        power_card = QFrame()
        power_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        pc_layout = QVBoxLayout(power_card)
        lbl_pt = QLabel("LEISTUNGSGRENZE (PPT POWER LIMIT)")
        lbl_pt.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        pc_layout.addWidget(lbl_pt)

        min_w = int(self.gpu.power_cap_min_w) if self.gpu.power_cap_min_w > 0 else 231
        max_w = int(self.gpu.power_cap_max_w) if self.gpu.power_cap_max_w > 0 else 374
        def_w = int(self.gpu.power_cap_default_w) if self.gpu.power_cap_default_w > 0 else 330

        self.sl_power = StyledSlider(
            "Board Power Limit (PPT)",
            min_w,
            max_w,
            def_w,
            "W",
            step=1
        )
        self.sl_power.valueChanged.connect(lambda v: setattr(self.profile, "power_limit_w", float(v)))
        pc_layout.addWidget(self.sl_power)

        # Power Profile Mode
        ppm_row = QHBoxLayout()
        ppm_row.addWidget(QLabel("DPM Power Profile Mode:"))
        self.combo_dpm = QComboBox()
        profiles = self.gpu.power_profiles or ["BOOTUP_DEFAULT", "3D_FULL_SCREEN", "POWER_SAVING"]
        self.combo_dpm.addItems(profiles)
        self.combo_dpm.currentTextChanged.connect(lambda t: setattr(self.profile, "power_profile_mode", t))
        ppm_row.addWidget(self.combo_dpm)
        ppm_row.addStretch()
        pc_layout.addLayout(ppm_row)

        t_layout.addWidget(power_card)

        # Apply & Reset Buttons
        action_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: bold;")

        btn_reset = QPushButton("Auf Standard zurücksetzen")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_defaults)

        btn_apply = QPushButton("ÄNDERUNGEN ANWENDEN")
        btn_apply.setProperty("class", "primary-red")
        btn_apply.setFixedHeight(38)
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._apply_tuning)

        action_row.addWidget(self.lbl_status)
        action_row.addStretch()
        action_row.addWidget(btn_reset)
        action_row.addWidget(btn_apply)
        t_layout.addLayout(action_row)

        layout.addWidget(self.tuning_container)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _on_unlock_toggled(self, checked: bool):
        self.tuning_container.setEnabled(checked)

    def _apply_tuning(self):
        ok, msg = execute_via_pkexec(
            self.gpu.device_dir,
            self.gpu.hwmon_dir,
            self.profile,
            reset=False,
            default_power_w=self.gpu.power_cap_default_w
        )
        if ok:
            self.lbl_status.setText("✓ Tuning erfolgreich angewendet!")
            self.lbl_status.setStyleSheet("color: #2ECC71; font-weight: bold;")
        else:
            self.lbl_status.setText(f"Fehler: {msg}")
            self.lbl_status.setStyleSheet("color: #E01E37; font-weight: bold;")

    def _reset_defaults(self):
        ok, msg = execute_via_pkexec(
            self.gpu.device_dir,
            self.gpu.hwmon_dir,
            None,
            reset=True,
            default_power_w=self.gpu.power_cap_default_w
        )
        self.sl_sclk.setValue(0)
        self.sl_vddc.setValue(0)
        self.sl_power.setValue(int(self.gpu.power_cap_default_w))
        if ok:
            self.lbl_status.setText("✓ Alle Werte auf Standard zurückgesetzt.")
            self.lbl_status.setStyleSheet("color: #2ECC71; font-weight: bold;")
        else:
            self.lbl_status.setText(f"Reset-Fehler: {msg}")
            self.lbl_status.setStyleSheet("color: #E01E37; font-weight: bold;")

    def update_telemetry(self, data: dict):
        load = data.get("gpu_busy", 0)
        self.c_load.set_value(load, display_str=f"{load}")
        
        sclk = data.get("sclk", 0)
        self.c_clock.set_value(sclk, display_str=f"{sclk}")
        
        temp = data.get("temp_edge", 0.0)
        hotspot = data.get("temp_junction", 0.0)
        self.c_temp.set_value(temp, display_str=f"{temp:.0f}", sub_str=f"Hotspot: {hotspot:.0f}°C")
        
        vram_used = data.get("vram_used_mb", 0)
        vram_pct = data.get("vram_pct", 0)
        self.c_vram.set_value(vram_used, display_str=f"{vram_used}", sub_str=f"{vram_pct}% ({self.gpu.vram_total_mb} MB)")
        
        power = data.get("power_w", 0)
        cap = data.get("power_cap_w", self.gpu.power_cap_default_w)
        self.c_power.set_value(power, display_str=f"{power:.0f}", sub_str=f"Limit: {cap:.0f} W")
        
        fan = data.get("fan_rpm", 0)
        pwm = data.get("fan_pwm_pct", 0)
        self.c_fan.set_value(fan, display_str=f"{fan}", sub_str=f"{pwm}% PWM")

        # Update Chart
        if "history" in data:
            self.chart.update_history(data["history"])
