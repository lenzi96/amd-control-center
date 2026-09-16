"""Adrenalin top navigation bar."""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QFrame
from PyQt6.QtSvgWidgets import QSvgWidget


class TopNavBar(QWidget):
    tab_changed = pyqtSignal(int)
    overlay_toggle_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    update_requested = pyqtSignal()

    def __init__(self, gpu_name: str = "AMD Radeon GPU", driver_ver: str = "Mesa Up to date", parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setStyleSheet("""
            TopNavBar {
                background-color: #0B0D11;
                border-bottom: 1px solid #1E2430;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # Radeon Logo
        res_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
        logo_svg = os.path.join(res_dir, "radeon_logo.svg")
        if os.path.isfile(logo_svg):
            self.logo = QSvgWidget(logo_svg)
            self.logo.setFixedSize(180, 32)
            layout.addWidget(self.logo)
        else:
            lbl = QLabel("RADEON")
            lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF; letter-spacing: 2px;")
            layout.addWidget(lbl)

        # Subtle separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("color: #1E2430; background-color: #1E2430; width: 1px; margin-top: 14px; margin-bottom: 14px;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)

        layout.addSpacing(6)

        # Tab Button Group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.tab_home = QPushButton("HOME")
        self.tab_gaming = QPushButton("GAMING")
        self.tab_perf = QPushButton("PERFORMANCE")
        self.tab_settings = QPushButton("SETTINGS")

        tabs = [self.tab_home, self.tab_gaming, self.tab_perf, self.tab_settings]
        for idx, tab in enumerate(tabs):
            tab.setCheckable(True)
            tab.setProperty("class", "nav-tab")
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_group.addButton(tab, idx)
            layout.addWidget(tab)

        self.tab_home.setChecked(True)
        self.btn_group.idClicked.connect(self.tab_changed.emit)

        layout.addStretch()

        # System / GPU Badge Container (Adrenalin Hardware Pill)
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #121620;
                border: 1px solid #1E2534;
                border-radius: 16px;
                padding: 3px 12px;
            }
        """)
        status_box = QHBoxLayout(status_frame)
        status_box.setContentsMargins(8, 2, 8, 2)
        status_box.setSpacing(10)

        self.lbl_gpu = QLabel(gpu_name)
        self.lbl_gpu.setStyleSheet("font-size: 11px; font-weight: 700; color: #C8D1DC; border: none; background: transparent;")

        self.lbl_driver = QLabel(f"● {driver_ver}")
        self.lbl_driver.setStyleSheet("font-size: 10px; font-weight: 800; color: #00E676; border: none; background: transparent;")

        status_box.addWidget(self.lbl_gpu)
        status_box.addWidget(self.lbl_driver)
        layout.addWidget(status_frame)

        layout.addSpacing(6)

        # Quick Actions - HUD Overlay Button
        self.btn_overlay = QPushButton("🗗  HUD OVERLAY")
        self.btn_overlay.setToolTip("Freistehendes Performance-HUD Overlay ein-/ausblenden")
        self.btn_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_overlay.setStyleSheet("""
            QPushButton {
                background-color: #161A24;
                border: 1px solid #252D3D;
                border-radius: 16px;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 0.6px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background-color: #E01E37;
                border: 1px solid #FF2E47;
                color: #FFFFFF;
            }
        """)
        self.btn_overlay.clicked.connect(self.overlay_toggle_requested.emit)
        layout.addWidget(self.btn_overlay)

        # Quick Actions - Updates Button
        self.btn_update = QPushButton("↻  UPDATES")
        self.btn_update.setToolTip("GitHub Software- & Release-Aktualisierungen prüfen")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet("""
            QPushButton {
                background-color: #161A24;
                border: 1px solid #252D3D;
                border-radius: 16px;
                color: #C8D1DC;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 0.6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #232B3B;
                border-color: #3C4B63;
                color: #FFFFFF;
            }
        """)
        self.btn_update.clicked.connect(self.update_requested.emit)
        layout.addWidget(self.btn_update)

    def set_update_available(self, remote_version: str):
        self.btn_update.setText(f"● UPDATE v{remote_version}")
        self.btn_update.setToolTip(f"Neue Version v{remote_version} auf GitHub verfügbar! Klicken zum Aktualisieren.")
        self.btn_update.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B81327);
                border: 1px solid #FF334B;
                border-radius: 16px;
                color: #FFFFFF;
                font-weight: 900;
                font-size: 11px;
                letter-spacing: 0.6px;
                padding: 5px 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #D1152E);
                border-color: #FF5A6E;
            }
        """)

    def reset_update_status(self):
        self.btn_update.setText("↻  UPDATES")
        self.btn_update.setToolTip("GitHub Software- & Release-Aktualisierungen prüfen")
        self.btn_update.setStyleSheet("""
            QPushButton {
                background-color: #161A24;
                border: 1px solid #252D3D;
                border-radius: 16px;
                color: #C8D1DC;
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 0.6px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #232B3B;
                border-color: #3C4B63;
                color: #FFFFFF;
            }
        """)

    def select_tab(self, index: int):
        btn = self.btn_group.button(index)
        if btn:
            btn.setChecked(True)
