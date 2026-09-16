"""Radeon styled slider with value labels and numeric controls."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QSpinBox


class StyledSlider(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, title: str, min_val: int, max_val: int, current_val: int, unit: str = "", step: int = 1, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.step = step

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(4)

        # Header row: Title + Current Value
        header = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: 600; color: #E1E7EE;")
        
        self.spin = QSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setValue(current_val)
        self.spin.setSingleStep(step)
        self.spin.setSuffix(f" {unit}" if unit else "")
        self.spin.setStyleSheet("""
            QSpinBox {
                background-color: #161920;
                border: 1px solid #2A313F;
                border-radius: 4px;
                padding: 2px 8px;
                color: #FFFFFF;
                font-weight: bold;
                min-width: 80px;
            }
        """)

        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.spin)
        layout.addLayout(header)

        # Slider row
        slider_row = QHBoxLayout()
        self.lbl_min = QLabel(f"{min_val}{unit}")
        self.lbl_min.setStyleSheet("color: #727F93; font-size: 11px;")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(current_val)
        self.slider.setSingleStep(step)

        self.lbl_max = QLabel(f"{max_val}{unit}")
        self.lbl_max.setStyleSheet("color: #727F93; font-size: 11px;")

        slider_row.addWidget(self.lbl_min)
        slider_row.addWidget(self.slider)
        slider_row.addWidget(self.lbl_max)
        layout.addLayout(slider_row)

        # Sync slider and spin
        self.slider.valueChanged.connect(self._on_slider_change)
        self.spin.valueChanged.connect(self._on_spin_change)

    def _on_slider_change(self, val: int):
        self.spin.blockSignals(True)
        self.spin.setValue(val)
        self.spin.blockSignals(False)
        self.valueChanged.emit(val)

    def _on_spin_change(self, val: int):
        self.slider.blockSignals(True)
        self.slider.setValue(val)
        self.slider.blockSignals(False)
        self.valueChanged.emit(val)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, val: int):
        self.slider.setValue(val)
        self.spin.setValue(val)
