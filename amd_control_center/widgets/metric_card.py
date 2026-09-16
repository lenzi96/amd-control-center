"""Adrenalin style telemetry metric card."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QColor


class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "", max_val: float = 100.0, parent=None):
        super().__init__(parent)
        self.setProperty("class", "adrenalin-card")
        self.unit = unit
        self.max_val = max_val

        self.setStyleSheet("""
            QFrame {
                background-color: #161A23;
                border: 1px solid #222A38;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                border: 1px solid #333F54;
                background-color: #1A1F2B;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header
        top_row = QHBoxLayout()
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #8C9CAE; letter-spacing: 1.2px;")
        
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("font-size: 11px; font-weight: 700; color: #5D6D82;")
        
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()
        top_row.addWidget(self.lbl_sub)
        layout.addLayout(top_row)

        # Main Value Display
        val_row = QHBoxLayout()
        val_row.setSpacing(4)
        self.lbl_val = QLabel("--")
        self.lbl_val.setStyleSheet("font-size: 32px; font-weight: 900; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet("font-size: 14px; font-weight: 800; color: #E01E37; margin-bottom: 5px;")
        
        val_row.addWidget(self.lbl_val)
        val_row.addWidget(self.lbl_unit, alignment=Qt.AlignmentFlag.AlignBottom)
        val_row.addStretch()
        layout.addLayout(val_row)

        # Mini gauge / progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #10131A;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B81327, stop:1 #E01E37);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

    def set_value(self, val: float, display_str: str = None, sub_str: str = None):
        if display_str is not None:
            self.lbl_val.setText(display_str)
        else:
            if isinstance(val, float):
                self.lbl_val.setText(f"{val:.1f}")
            else:
                self.lbl_val.setText(str(val))

        if sub_str is not None:
            self.lbl_sub.setText(sub_str)

        # Update bar
        pct = int(min(100, max(0, (val / self.max_val) * 100))) if self.max_val > 0 else 0
        self.progress.setValue(pct)
