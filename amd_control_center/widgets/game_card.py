"""Game library card component."""

import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from ..backend.game_scanner import GameInfo


class GameCard(QFrame):
    clicked = pyqtSignal(str)  # game app_id
    play_requested = pyqtSignal(str)

    def __init__(self, game: GameInfo, parent=None):
        super().__init__(parent)
        self.game = game
        self.setFixedSize(160, 245)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet("""
            GameCard {
                background-color: #161A23;
                border: 1px solid #222A38;
                border-radius: 8px;
            }
            GameCard:hover {
                border: 1px solid #E01E37;
                background-color: #1D2330;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Poster Image
        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(144, 175)
        self.lbl_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_art.setStyleSheet("background-color: #0E1117; border-radius: 6px;")

        if game.poster_image and os.path.isfile(game.poster_image):
            pm = QPixmap(game.poster_image).scaled(144, 175, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            # Crop to exact dimensions
            self.lbl_art.setPixmap(pm.copy(0, 0, 144, 175))
        else:
            # Stylized Fallback Art
            pix = QPixmap(144, 175)
            pix.fill(QColor("#131720"))
            p = QPainter(pix)
            p.setPen(QColor("#E01E37"))
            p.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))
            p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, game.name)
            p.end()
            self.lbl_art.setPixmap(pix)

        layout.addWidget(self.lbl_art)

        # Title & Launch Row
        info_row = QHBoxLayout()
        info_row.setContentsMargins(2, 2, 2, 2)
        info_row.setSpacing(6)

        self.lbl_name = QLabel(game.name)
        self.lbl_name.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFFFFF;")
        self.lbl_name.setWordWrap(False)
        # Elide text if too long
        metrics = self.lbl_name.fontMetrics()
        elided = metrics.elidedText(game.name, Qt.TextElideMode.ElideRight, 105)
        self.lbl_name.setText(elided)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(26, 26)
        self.btn_play.setToolTip(f"{game.name} starten")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B81327);
                color: #FFFFFF;
                border: none;
                border-radius: 13px;
                font-size: 10px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #D1152E);
            }
        """)
        self.btn_play.clicked.connect(lambda: self.play_requested.emit(self.game.app_id))

        info_row.addWidget(self.lbl_name)
        info_row.addStretch()
        info_row.addWidget(self.btn_play)
        layout.addLayout(info_row)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.game.app_id)
        super().mouseReleaseEvent(event)
