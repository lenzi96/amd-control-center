"""High-performance custom QPainter real-time multi-metric graph."""

from typing import Dict, List
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox


SERIES_CONFIG = {
    "gpu_busy": {"label": "GPU Load", "color": QColor("#E01E37"), "unit": "%", "max": 100, "active": True},
    "temp_edge": {"label": "GPU Temp", "color": QColor("#F39C12"), "unit": "°C", "max": 110, "active": True},
    "temp_junction": {"label": "Hotspot", "color": QColor("#FF4256"), "unit": "°C", "max": 115, "active": True},
    "sclk": {"label": "Clock", "color": QColor("#00D2FF"), "unit": "MHz", "max": 3500, "active": False},
    "power": {"label": "Power", "color": QColor("#2ECC71"), "unit": "W", "max": 400, "active": False},
}


class ChartCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.data_history: Dict[str, List[float]] = {}
        self.series_meta = SERIES_CONFIG

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
        painter.fillRect(0, 0, w, h, QColor("#14171E"))

        # Grid lines & Axis labels
        grid_pen = QPen(QColor("#242B38"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        font = QFont("sans-serif", 8)
        painter.setFont(font)

        # 4 horizontal grid lines
        for i in range(5):
            y = margin_top + (chart_h / 4.0) * i
            painter.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))
            # Label
            val = int(100 - i * 25)
            painter.setPen(QColor("#5D6A7E"))
            painter.drawText(QRectF(0, y - 8, margin_left - 8, 16), Qt.AlignmentFlag.AlignRight, f"{val}%")
            painter.setPen(grid_pen)

        # Bottom time labels
        painter.setPen(QColor("#5D6A7E"))
        painter.drawText(int(margin_left), int(h - 8), "-60s")
        painter.drawText(int(margin_left + chart_w / 2 - 15), int(h - 8), "-30s")
        painter.drawText(int(w - margin_right - 25), int(h - 8), "Now")

        # Draw Series
        for key, meta in self.series_meta.items():
            if not meta["active"]:
                continue
            series = self.data_history.get(key, [])
            if not series or len(series) < 2:
                continue

            max_val = meta["max"]
            color = meta["color"]

            pts: List[QPointF] = []
            num_points = 60
            dx = chart_w / (num_points - 1)

            # Pad or align to right
            offset = num_points - len(series)
            for idx, val in enumerate(series):
                x = margin_left + (offset + idx) * dx
                norm_y = min(1.0, max(0.0, float(val) / max_val))
                y = margin_top + chart_h * (1.0 - norm_y)
                pts.append(QPointF(x, y))

            if len(pts) >= 2:
                path = QPainterPath()
                path.moveTo(pts[0])
                for pt in pts[1:]:
                    path.lineTo(pt)

                # Gradient fill under curve
                fill_path = QPainterPath(path)
                fill_path.lineTo(pts[-1].x(), margin_top + chart_h)
                fill_path.lineTo(pts[0].x(), margin_top + chart_h)
                fill_path.closeSubpath()

                grad = QLinearGradient(0, margin_top, 0, margin_top + chart_h)
                c_trans = QColor(color)
                c_trans.setAlpha(45)
                c_zero = QColor(color)
                c_zero.setAlpha(0)
                grad.setColorAt(0.0, c_trans)
                grad.setColorAt(1.0, c_zero)

                painter.fillPath(fill_path, QBrush(grad))

                # Stroke line
                pen = QPen(color, 2.0)
                painter.setPen(pen)
                painter.drawPath(path)

                # Glowing last point dot
                last_pt = pts[-1]
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
                painter.drawEllipse(last_pt, 4, 4)


class RealtimeChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Legend / Toggle Row
        self.legend_row = QHBoxLayout()
        self.legend_row.setSpacing(16)
        self.canvas = ChartCanvas(self)

        for key, meta in SERIES_CONFIG.items():
            cb = QCheckBox(f"{meta['label']} ({meta['unit']})")
            cb.setChecked(meta["active"])
            col_hex = meta["color"].name()
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: #A4B2C4;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {col_hex};
                    border: 1px solid {col_hex};
                    border-radius: 2px;
                }}
                QCheckBox::indicator:unchecked {{
                    background-color: #1A1F29;
                    border: 1px solid #364052;
                    border-radius: 2px;
                }}
            """)
            cb.toggled.connect(lambda chk, k=key: self._on_toggle(k, chk))
            self.legend_row.addWidget(cb)

        self.legend_row.addStretch()
        layout.addLayout(self.legend_row)
        layout.addWidget(self.canvas)

    def _on_toggle(self, key: str, active: bool):
        SERIES_CONFIG[key]["active"] = active
        self.canvas.update()

    def update_history(self, history: Dict[str, List[float]]):
        self.canvas.update_data(history)
