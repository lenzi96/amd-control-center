"""Custom Radeon-styled animated toggle switch."""

from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_position = 1.0 if checked else 0.0
        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)

    @pyqtProperty(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._anim.stop()
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
            self.toggled.emit(self._checked)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track background
        w, h = self.width(), self.height()
        r = h / 2.0

        if self._checked:
            track_color = QColor("#E01E37")  # Radeon Red
            border_color = QColor("#FF2E47")
        else:
            track_color = QColor("#222834")
            border_color = QColor("#364052")

        # Blend colors during animation
        if self._anim.state() == QPropertyAnimation.State.Running:
            pos = self._thumb_position
            r_c = int(34 + (224 - 34) * pos)
            g_c = int(40 + (30 - 40) * pos)
            b_c = int(52 + (55 - 52) * pos)
            track_color = QColor(r_c, g_c, b_c)

        painter.setBrush(QBrush(track_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)

        # Thumb
        thumb_radius = r - 3.5
        thumb_x = 3.5 + self._thumb_position * (w - 2 * thumb_radius - 7.0)
        thumb_y = (h - 2 * thumb_radius) / 2.0

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_radius * 2, thumb_radius * 2))
