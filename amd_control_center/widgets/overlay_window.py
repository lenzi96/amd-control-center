"""Detachable translucent floating performance overlay HUD."""

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class OverlayHUD(QWidget):
    def __init__(self, parent=None):
        super().__init__(None)  # Top-level window
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.drag_position = QPoint()

        self.setFixedSize(220, 170)

        # Outer container for dark translucent styling
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(14, 16, 22, 0.88);
                border: 1px solid #E01E37;
                border-radius: 6px;
            }
        """)

        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(12, 10, 12, 10)
        inner_layout.setSpacing(4)

        # Title bar
        title_row = QHBoxLayout()
        title_lbl = QLabel("RADEON HUD")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 900; color: #E01E37; letter-spacing: 1px; border: none;")

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(18, 18)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #A0AFC2;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background: #E01E37;
                border-radius: 9px;
            }
        """)
        btn_close.clicked.connect(self.hide)

        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(btn_close)
        inner_layout.addLayout(title_row)

        # Metric Labels
        def _make_row(name: str):
            r = QHBoxLayout()
            l1 = QLabel(name)
            l1.setStyleSheet("color: #7E8D9F; font-size: 11px; font-weight: 600; border: none;")
            l2 = QLabel("--")
            l2.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700; border: none; font-family: monospace;")
            r.addWidget(l1)
            r.addStretch()
            r.addWidget(l2)
            inner_layout.addLayout(r)
            return l2

        self.lbl_load = _make_row("GPU LOAD")
        self.lbl_temp = _make_row("GPU TEMP")
        self.lbl_hotspot = _make_row("HOTSPOT")
        self.lbl_clock = _make_row("CORE CLOCK")
        self.lbl_vram = _make_row("VRAM USAGE")
        self.lbl_power = _make_row("POWER DRAW")

        layout.addWidget(self.container)

    def update_telemetry(self, data: dict):
        self.lbl_load.setText(f"{data.get('gpu_busy', 0)} %")
        self.lbl_temp.setText(f"{data.get('temp_edge', 0):.0f} °C")
        self.lbl_hotspot.setText(f"{data.get('temp_junction', 0):.0f} °C")
        self.lbl_clock.setText(f"{data.get('sclk', 0)} MHz")
        self.lbl_vram.setText(f"{data.get('vram_used_mb', 0)} MB")
        self.lbl_power.setText(f"{data.get('power_w', 0):.0f} W")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
