"""High-performance custom QPainter real-time graph for CPU telemetry."""

from typing import Dict, List
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox


CPU_SERIES_CONFIG = {
    "cpu_usage": {"label": "CPU Auslastung", "color": QColor("#FF5500"), "unit": "%", "max": 100, "active": True},
    "temp_tctl": {"label": "Tctl Temperatur", "color": QColor("#F39C12"), "unit": "°C", "max": 100, "active": True},
    "package_power": {"label": "Package Power", "color": QColor("#00E676"), "unit": "W", "max": 150, "active": True},
    "peak_freq": {"label": "Peak Takt", "color": QColor("#00D2FF"), "unit": "MHz", "max": 6000, "active": False},
}


class CpuChartCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.data_history: Dict[str, List[float]] = {}
        self.series_meta = CPU_SERIES_CONFIG

    def update_data(self, history: Dict[str, List[float]]):
        self.data_history = history
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_left = 40
        margin_right = 20
        margin_top = 20
        margin_bottom = 30

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        # Background
        painter.fillRect(0, 0, w, h, QColor("#121620"))

        # Grid lines & Axis labels
        grid_pen = QPen(QColor("#1E2636"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        font = QFont("sans-serif", 8)
        painter.setFont(font)

        # 4 horizontal grid lines
        for i in range(5):
            y = margin_top + (chart_h / 4.0) * i
            painter.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))
            val = int(100 - i * 25)
            painter.setPen(QColor("#5D6A7E"))
            painter.drawText(QRectF(0, y - 8, margin_left - 8, 16), Qt.AlignmentFlag.AlignRight, f"{val}%")
            painter.setPen(grid_pen)

        # Plot active series
        for key, meta in self.series_meta.items():
            if not meta["active"]:
                continue
            points_data = self.data_history.get(key, [])
            if len(points_data) < 2:
                continue

            max_scale = meta["max"]
            color: QColor = meta["color"]
            pen = QPen(color, 2)
            painter.setPen(pen)

            step_x = chart_w / (len(points_data) - 1)
            path = QPainterPath()

            pts = []
            for idx, val in enumerate(points_data):
                val_clamped = min(max_scale, max(0.0, float(val)))
                norm_y = 1.0 - (val_clamped / max_scale)
                x = margin_left + idx * step_x
                y = margin_top + norm_y * chart_h
                pts.append(QPointF(x, y))

            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)

            # Draw glowing gradient fill under primary series
            if key == "cpu_usage":
                fill_path = QPainterPath(path)
                fill_path.lineTo(margin_left + (len(pts) - 1) * step_x, margin_top + chart_h)
                fill_path.lineTo(margin_left, margin_top + chart_h)
                fill_path.closeSubpath()

                grad = QLinearGradient(0, margin_top, 0, margin_top + chart_h)
                grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 60))
                grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                painter.fillPath(fill_path, QBrush(grad))

            painter.drawPath(path)


class CpuChartWidget(QWidget):
    """Full chart container with legend toggle checkboxes for CPU telemetry."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = CpuChartCanvas(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Legend Controls
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(10, 0, 10, 0)
        legend_layout.setSpacing(16)

        self.checkboxes = {}
        for key, meta in self.canvas.series_meta.items():
            cb = QCheckBox(f"{meta['label']} ({meta['unit']})")
            cb.setChecked(meta["active"])
            col_str = meta["color"].name()
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: #C8D1DC;
                    font-size: 11px;
                    font-weight: 600;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                    border-radius: 3px;
                    border: 1px solid {col_str};
                    background: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {col_str};
                }}
            """)
            cb.toggled.connect(lambda checked, k=key: self._on_toggle_series(k, checked))
            legend_layout.addWidget(cb)
            self.checkboxes[key] = cb

        legend_layout.addStretch()
        layout.addLayout(legend_layout)
        layout.addWidget(self.canvas)

    def _on_toggle_series(self, key: str, active: bool):
        self.canvas.series_meta[key]["active"] = active
        self.canvas.update()

    def update_telemetry(self, data: dict):
        history = data.get("history", {})
        if history:
            self.canvas.update_data(history)
