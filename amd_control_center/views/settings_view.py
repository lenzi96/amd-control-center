"""Settings View (System, Display, Optionen, Über) for AMD Control Center."""

import os
import subprocess
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QFrame, QGridLayout, QComboBox
)

from ..backend.gpu_detector import GpuDevice
from ..backend.system_info import SystemAudit
from ..backend.display_manager import DisplayInfo
from ..widgets.toggle_switch import ToggleSwitch


class SettingsView(QWidget):
    tray_minimize_changed = pyqtSignal(bool)
    update_center_requested = pyqtSignal()

    def __init__(self, gpu: GpuDevice, audit: SystemAudit, display: DisplayInfo, parent=None):
        super().__init__(parent)
        self.gpu = gpu
        self.audit = audit
        self.display = display

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(14)

        # Subtabs Row
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.btn_system = QPushButton("SYSTEM")
        self.btn_display = QPushButton("ANZEIGE")
        self.btn_options = QPushButton("OPTIONEN")
        self.btn_about = QPushButton("ÜBER")

        self.subtab_buttons = [self.btn_system, self.btn_display, self.btn_options, self.btn_about]
        for idx, b in enumerate(self.subtab_buttons):
            b.setCheckable(True)
            b.setProperty("class", "subnav-tab")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, i=idx: self._switch_subtab(i))

        self.btn_system.setChecked(True)
        for b in self.subtab_buttons:
            top_bar.addWidget(b)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_system_page())
        self.stack.addWidget(self._create_display_page())
        self.stack.addWidget(self._create_options_page())
        self.stack.addWidget(self._create_about_page())

        layout.addWidget(self.stack)

    def _switch_subtab(self, idx: int):
        for i, b in enumerate(self.subtab_buttons):
            b.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)

    def _create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 20px;")
        l = QVBoxLayout(card)
        l.setSpacing(12)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        l.addWidget(lbl)
        return card

    def _add_table_row(self, layout: QVBoxLayout, key: str, val: str):
        r = QHBoxLayout()
        l1 = QLabel(key)
        l1.setStyleSheet("color: #7E8D9F; font-size: 12px;")
        l2 = QLabel(val)
        l2.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        r.addWidget(l1)
        r.addStretch()
        r.addWidget(l2)
        layout.addLayout(r)

    def _create_system_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(16)

        # 1. Hardware Details Card
        hw_card = self._create_card("Grafikhardware & Architektur")
        l_hw = hw_card.layout()
        self._add_table_row(l_hw, "Grafikkarte", self.gpu.model_name)
        self._add_table_row(l_hw, "Architektur", self.gpu.architecture)
        self._add_table_row(l_hw, "Produktserie", self.gpu.generation_name)
        self._add_table_row(l_hw, "FSR 4 AI-Beschleunigung", self.gpu.ai_acceleration)
        self._add_table_row(l_hw, "Device ID", self.gpu.device_id)
        self._add_table_row(l_hw, "Subsystem ID", f"{self.gpu.subsystem_vendor}:{self.gpu.subsystem_device}")
        self._add_table_row(l_hw, "VBIOS Version", self.gpu.vbios_version)
        self._add_table_row(l_hw, "Videospeicher (VRAM)", f"{self.gpu.vram_total_mb} MB ({self.gpu.vram_vendor} GDDR6)")
        self._add_table_row(l_hw, "PCIe Schnittstelle", f"{self.audit.pcie_link_width} ({self.audit.pcie_link_speed})")
        self._add_table_row(l_hw, "Standard Power Limit (PPT)", f"{self.gpu.power_cap_default_w} W")
        self._add_table_row(l_hw, "Einstellbarer Power-Bereich", f"{self.gpu.power_cap_min_w} W bis {self.gpu.power_cap_max_w} W")
        layout.addWidget(hw_card)

        # 2. Driver & Software Stack
        sw_card = self._create_card("Treiber & Software Stack")
        l_sw = sw_card.layout()
        self._add_table_row(l_sw, "Mesa Version", self.audit.mesa_version)
        self._add_table_row(l_sw, "Vulkan Version", f"{self.audit.vulkan_version} ({self.audit.vulkan_driver})")
        self._add_table_row(l_sw, "OpenGL Version", self.audit.opengl_version)
        self._add_table_row(l_sw, "Linux Kernel", self.audit.kernel_version)
        self._add_table_row(l_sw, "Betriebssystem", self.audit.os_name)
        self._add_table_row(l_sw, "Desktop-Umgebung", f"{self.audit.desktop_env} ({self.audit.session_type.capitalize()})")
        layout.addWidget(sw_card)

        # 3. Application Updates (GitHub)
        from .. import __version__
        upd_card = self._create_card("Software- & Release-Aktualisierung (GitHub)")
        l_upd = upd_card.layout()
        self._add_table_row(l_upd, "Installierte Version", f"v{__version__} (AMD Software: Adrenalin Edition)")
        self._add_table_row(l_upd, "Update-Kanal", "GitHub Releases / Tags")

        row_upd = QHBoxLayout()
        lbl_info = QLabel("Auf neue Versionen und Fehlerbehebungen auf GitHub prüfen:")
        lbl_info.setStyleSheet("color: #7E8D9F; font-size: 12px;")
        row_upd.addWidget(lbl_info)
        row_upd.addStretch()

        btn_open_updater = QPushButton("⚡ Update-Center öffnen")
        btn_open_updater.setProperty("class", "primary-red")
        btn_open_updater.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_updater.clicked.connect(self.update_center_requested.emit)
        row_upd.addWidget(btn_open_updater)
        l_upd.addLayout(row_upd)
        layout.addWidget(upd_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_display_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(16)

        card = self._create_card("Angeschlossener Monitor")
        l = card.layout()
        self._add_table_row(l, "Anschluss", self.display.connector)
        self._add_table_row(l, "Aktuelle Auflösung", self.display.resolution)
        self._add_table_row(l, "Bildwiederholrate", f"{self.display.refresh_rate_hz} Hz")
        self._add_table_row(l, "Adaptive Sync / FreeSync", "Aktiviert (Automatisch)" if self.display.vrr_enabled else "Deaktiviert")
        self._add_table_row(l, "HDR (High Dynamic Range)", "Aktiviert" if self.display.hdr_enabled else "Deaktiviert")
        layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_options_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(16)

        card = self._create_card("Anwendungsoptionen")
        l = card.layout()

        def _opt_row(name: str, desc: str, chk: bool):
            r = QHBoxLayout()
            v = QVBoxLayout()
            l1 = QLabel(name)
            l1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
            l2 = QLabel(desc)
            l2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
            v.addWidget(l1)
            v.addWidget(l2)
            sw = ToggleSwitch(checked=chk)
            r.addLayout(v)
            r.addStretch()
            r.addWidget(sw)
            l.addLayout(r)
            return sw

        from ..backend.autostart_manager import is_autostart_enabled, set_autostart_enabled
        sw_autostart = _opt_row(
            "Mit System starten",
            "Startet AMD Control Center automatisch im Infobereich (System Tray)",
            is_autostart_enabled()
        )
        sw_autostart.toggled.connect(set_autostart_enabled)

        sw_tray = _opt_row("In System-Tray minimieren", "Beim Schließen im Infobereich aktiv bleiben", True)
        sw_tray.toggled.connect(self.tray_minimize_changed.emit)
        _opt_row("Desktop-Benachrichtigungen", "Meldungen bei Temperatur-Warnungen oder Tuning-Änderungen", True)

        # Permissions / udev setup
        l.addSpacing(10)
        lbl_p = QLabel("ERWEITERTE BERECHTIGUNGEN")
        lbl_p.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        l.addWidget(lbl_p)

        p_row = QHBoxLayout()
        p_info = QVBoxLayout()
        p1 = QLabel("Passwortloses Tuning aktivieren (udev Regel)")
        p1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        p2 = QLabel("Erlaubt das Anwenden von Overclocking und Lüftereinstellungen ohne Root-Passwort-Prompt")
        p2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        p_info.addWidget(p1)
        p_info.addWidget(p2)

        self.btn_udev = QPushButton("Regel installieren")
        self.btn_udev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_udev.clicked.connect(self._install_udev_rule)

        p_row.addLayout(p_info)
        p_row.addStretch()
        p_row.addWidget(self.btn_udev)
        l.addLayout(p_row)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _install_udev_rule(self):
        cmd = [
            "pkexec", "bash", "-c",
            'echo \'ACTION=="add", SUBSYSTEM=="pci", DRIVERS=="amdgpu", ATTR{power_dpm_force_performance_level}="manual", RUN+="/bin/chmod a+w /sys/class/drm/card*/device/pp_od_clk_voltage"\' > /etc/udev/rules.d/99-amdgpu-tuning.rules && udevadm control --reload'
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                self.btn_udev.setText("✓ Installiert")
                self.btn_udev.setEnabled(False)
        except Exception:
            pass

    def _create_about_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(16)

        card = self._create_card("Über AMD Control Center (Radeon Software Linux)")
        l = card.layout()

        title = QLabel("AMD Software: Adrenalin Edition for Linux")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: #FFFFFF;")
        l.addWidget(title)

        desc = QLabel(
            "Ein modernes AMD GPU Control Center für Linux, inspiriert vom Design und der "
            "Funktionalität der AMD Radeon Software (Adrenalin Edition). Entwickelt mit PyQt6 "
            "und nativer Linux-Kernel-Sysfs-Integration für AMD Radeon GPUs.\n\n"
            "Features:\n"
            "• Echtzeit-Telemetrie (GPU Auslastung, Core/VRAM Takte, Temperaturen, Hotspot, Watt, Lüfter)\n"
            "• Performance-Tuning: Overclocking, Undervolting, Lüfterkurven & PPT Power Limit\n"
            "• Automatische Spielebibliothek-Erkennung (Steam Multi-Drive, Heroic, Desktop)\n"
            "• Game-Profile mit Radeon Anti-Lag, FSR, Radeon Boost (VRS) und MangoHud Integration\n"
            "• Floating Performance-HUD Overlay"
        )
        desc.setStyleSheet("color: #C5CFDC; font-size: 12px; line-height: 1.6;")
        desc.setWordWrap(True)
        l.addWidget(desc)

        from .. import __version__
        l.addSpacing(10)
        row_about_upd = QHBoxLayout()
        lbl_ver = QLabel(f"Version: v{__version__}")
        lbl_ver.setStyleSheet("font-size: 13px; font-weight: 800; color: #E01E37;")
        row_about_upd.addWidget(lbl_ver)
        row_about_upd.addStretch()

        btn_about_upd = QPushButton("⚡ Update-Center (GitHub) öffnen")
        btn_about_upd.setProperty("class", "primary-red")
        btn_about_upd.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_about_upd.clicked.connect(self.update_center_requested.emit)
        row_about_upd.addWidget(btn_about_upd)
        l.addLayout(row_about_upd)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll
