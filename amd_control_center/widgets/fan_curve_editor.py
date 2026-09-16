"""Interactive 5-point fan curve editor."""

from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget


class FanCurveEditor(QWidget):
    curveChanged = pyqtSignal(list)

    def __init__(self, initial_points: Optional[List[List[int]]] = None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.points = initial_points or [[30, 0], [50, 35], [65, 55], [75, 75], [85, 100]]
        self.dragging_idx = -1
        self.hover_idx = -1

        self.margin_left = 40
        self.margin_right = 20
        self.margin_top = 20
        self.margin_bottom = 30

        self.setMouseTracking(True)

    def _to_screen(self, temp: int, speed: int) -> QPointF:
        w = self.width() - self.margin_left - self.margin_right
        h = self.height() - self.margin_top - self.margin_bottom

        x = self.margin_left + ((temp - 20) / 80.0) * w
        y = self.margin_top + h * (1.0 - (speed / 100.0))
        return QPointF(x, y)

    def _to_values(self, pt: QPointF) -> List[int]:
        w = self.width() - self.margin_left - self.margin_right
        h = self.height() - self.margin_top - self.margin_bottom

        norm_x = (pt.x() - self.margin_left) / w
        norm_y = 1.0 - ((pt.y() - self.margin_top) / h)

        temp = int(20 + norm_x * 80)
        temp = max(20, min(100, temp))

        speed = int(norm_y * 100)
        speed = max(0, min(100, speed))
        return [temp, speed]

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for idx, pt in enumerate(self.points):
                s_pt = self._to_screen(pt[0], pt[1])
                dist = (s_pt.x() - pos.x()) ** 2 + (s_pt.y() - pos.y()) ** 2
                if dist <= 120:  # ~11px radius
                    self.dragging_idx = idx
                    self.update()
                    break

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.dragging_idx >= 0:
            vals = self._to_values(pos)
            # Maintain temperature monotonicity
            min_temp = 20 if self.dragging_idx == 0 else self.points[self.dragging_idx - 1][0] + 1
            max_temp = 100 if self.dragging_idx == len(self.points) - 1 else self.points[self.dragging_idx + 1][0] - 1
            vals[0] = max(min_temp, min(max_temp, vals[0]))

            self.points[self.dragging_idx] = vals
            self.curveChanged.emit(self.points)
            self.update()
        else:
            # Check hover
            found = -1
            for idx, pt in enumerate(self.points):
                s_pt = self._to_screen(pt[0], pt[1])
                dist = (s_pt.x() - pos.x()) ** 2 + (s_pt.y() - pos.y()) ** 2
                if dist <= 120:
                    found = idx
                    break
            if found != self.hover_idx:
                self.hover_idx = found
                self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_idx = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        c_w = w - self.margin_left - self.margin_right
        c_h = h - self.margin_top - self.margin_bottom

        # Background
        painter.fillRect(0, 0, w, h, QColor("#14171E"))

        # Grid
        grid_pen = QPen(QColor("#242B38"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.setFont(QFont("sans-serif", 8))

        # Horizontal (Speed %)
        for i in range(5):
            y = self.margin_top + (c_h / 4.0) * i
            painter.drawLine(int(self.margin_left), int(y), int(w - self.margin_right), int(y))
            val = int(100 - i * 25)
            painter.setPen(QColor("#5D6A7E"))
            painter.drawText(QRectF(0, y - 8, self.margin_left - 8, 16), Qt.AlignmentFlag.AlignRight, f"{val}%")
            painter.setPen(grid_pen)

        # Vertical (Temp °C)
        for i in range(5):
            x = self.margin_left + (c_w / 4.0) * i
            painter.drawLine(int(x), int(self.margin_top), int(x), int(self.margin_top + c_h))
            val = int(20 + i * 20)
            painter.setPen(QColor("#5D6A7E"))
            painter.drawText(QRectF(x - 20, h - 22, 40, 16), Qt.AlignmentFlag.AlignCenter, f"{val}°C")
            painter.setPen(grid_pen)

        # Curve line
        pts = [self._to_screen(p[0], p[1]) for p in self.points]
        path = QPainterPath()
        path.moveTo(self.margin_left, pts[0].y())
        path.lineTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        path.lineTo(w - self.margin_right, pts[-1].y())

        painter.setPen(QPen(QColor("#E01E37"), 2.5))
        painter.drawPath(path)

        # Control points
        for idx, (p, pt_val) in enumerate(zip(pts, self.points)):
            is_active = (idx == self.dragging_idx or idx == self.hover_idx)
            r = 7 if is_active else 5

            painter.setBrush(QBrush(QColor("#FF2A42") if is_active else QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#E01E37"), 2))
            painter.drawEllipse(p, r, r)

            # Label on active
            if is_active:
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
                txt = f"{pt_val[0]}°C : {pt_val[1]}%"
                painter.drawText(int(p.x() - 30), int(p.y() - 14), txt)
