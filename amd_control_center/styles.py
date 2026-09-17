"""Radeon Software (AMD Software: Adrenalin Edition) Style Sheets and Theme Constants."""

class AdrenalinColors:
    BG_DARKEST = "#090B0E"
    BG_DARK = "#0E1117"
    BG_PANEL = "#131720"
    BG_CARD = "#171B24"
    BG_CARD_HOVER = "#1E2430"
    BG_INPUT = "#10141C"
    
    BORDER_SUBTLE = "#202735"
    BORDER_HOVER = "#2F3A4E"
    BORDER_ACTIVE = "#E01E37"
    
    ACCENT_RED = "#E01E37"
    ACCENT_RED_HOVER = "#FF2E47"
    ACCENT_RED_MUTED = "#8B1020"
    ACCENT_RED_GLOW = "rgba(224, 30, 55, 0.35)"
    
    ACCENT_CYAN = "#00D2FF"
    ACCENT_GREEN = "#00E676"
    ACCENT_YELLOW = "#F39C12"
    ACCENT_RYZEN_ORANGE = "#FF5500"
    STAR_GOLD = "#FFD700"
    STAR_SILVER = "#C0C0C0"
    
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#C8D1DC"
    TEXT_MUTED = "#727F93"
    TEXT_RED = "#FF4256"


ADRENALIN_STYLESHEET = f"""
/* Global Reset & Base */
QWidget {{
    background-color: transparent;
    color: {AdrenalinColors.TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, "Cantarell", "Helvetica Neue", sans-serif;
    font-size: 13px;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {AdrenalinColors.BG_DARK};
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {AdrenalinColors.BG_DARK};
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {AdrenalinColors.BORDER_HOVER};
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {AdrenalinColors.ACCENT_RED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: {AdrenalinColors.BG_DARK};
    height: 6px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {AdrenalinColors.BORDER_HOVER};
    min-width: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {AdrenalinColors.ACCENT_RED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Cards & Frames */
QFrame.adrenalin-card {{
    background-color: {AdrenalinColors.BG_CARD};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 8px;
}}

QFrame.adrenalin-card:hover {{
    border: 1px solid {AdrenalinColors.BORDER_HOVER};
}}

QFrame.adrenalin-panel {{
    background-color: {AdrenalinColors.BG_PANEL};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 6px;
}}

/* Buttons */
QPushButton {{
    background-color: {AdrenalinColors.BG_CARD};
    color: {AdrenalinColors.TEXT_PRIMARY};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: {AdrenalinColors.BG_CARD_HOVER};
    border: 1px solid {AdrenalinColors.BORDER_HOVER};
}}

QPushButton:pressed {{
    background-color: {AdrenalinColors.BG_PANEL};
}}

QPushButton.primary-red {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B81327);
    color: #FFFFFF;
    border: 1px solid #E01E37;
    border-radius: 5px;
    font-weight: 800;
    letter-spacing: 0.8px;
    padding: 8px 18px;
}}

QPushButton.primary-red:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #D1152E);
    border: 1px solid #FF334B;
}}

QPushButton.primary-red:pressed {{
    background-color: {AdrenalinColors.ACCENT_RED_MUTED};
}}

QPushButton.ghost-button {{
    background-color: transparent;
    border: none;
    color: {AdrenalinColors.TEXT_SECONDARY};
    padding: 6px 12px;
}}

QPushButton.ghost-button:hover {{
    background-color: {AdrenalinColors.BG_CARD};
    color: {AdrenalinColors.TEXT_PRIMARY};
    border-radius: 4px;
}}

QPushButton.profile-chip {{
    background-color: {AdrenalinColors.BG_CARD};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 6px;
    padding: 8px 16px;
    color: {AdrenalinColors.TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.6px;
}}

QPushButton.profile-chip:hover {{
    background-color: {AdrenalinColors.BG_CARD_HOVER};
    border-color: {AdrenalinColors.ACCENT_RED};
    color: #FFFFFF;
}}

QPushButton.profile-chip:checked {{
    background-color: rgba(224, 30, 55, 0.16);
    border: 1px solid {AdrenalinColors.ACCENT_RED};
    color: #FFFFFF;
}}

/* Tab Buttons */
QPushButton.nav-tab {{
    background-color: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0px;
    color: {AdrenalinColors.TEXT_MUTED};
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.2px;
    padding: 16px 20px;
}}

QPushButton.nav-tab:hover {{
    color: {AdrenalinColors.TEXT_PRIMARY};
    background-color: rgba(255, 255, 255, 0.03);
}}

QPushButton.nav-tab:checked, QPushButton.nav-tab.active {{
    color: {AdrenalinColors.TEXT_PRIMARY};
    border-bottom: 3px solid {AdrenalinColors.ACCENT_RED};
    background-color: rgba(224, 30, 55, 0.08);
}}

/* Sub-Navigation Tabs */
QPushButton.subnav-tab {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    color: #7E8D9F;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.8px;
    padding: 8px 16px;
}}

QPushButton.subnav-tab:hover {{
    color: #FFFFFF;
    background-color: rgba(255, 255, 255, 0.04);
}}

QPushButton.subnav-tab:checked {{
    color: #FFFFFF;
    border-bottom: 2px solid {AdrenalinColors.ACCENT_RED};
    background-color: rgba(224, 30, 55, 0.08);
}}

/* Banners */
QFrame.adrenalin-banner {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #181C26, stop:1 #11141B);
    border: 1px solid #28303F;
    border-radius: 8px;
    padding: 16px;
}}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {AdrenalinColors.BG_INPUT};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 5px;
    padding: 6px 10px;
    color: {AdrenalinColors.TEXT_PRIMARY};
    selection-background-color: {AdrenalinColors.ACCENT_RED};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {AdrenalinColors.ACCENT_RED};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {AdrenalinColors.BG_CARD};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    selection-background-color: {AdrenalinColors.ACCENT_RED};
    color: {AdrenalinColors.TEXT_PRIMARY};
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {AdrenalinColors.BG_INPUT};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {AdrenalinColors.ACCENT_RED};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {AdrenalinColors.ACCENT_RED};
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: #FFFFFF;
    border: 2px solid {AdrenalinColors.ACCENT_RED_HOVER};
    box-shadow: 0 0 6px {AdrenalinColors.ACCENT_RED};
}}

/* Group Boxes / Accordions */
QGroupBox {{
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: {AdrenalinColors.BG_CARD};
    font-weight: 700;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {AdrenalinColors.TEXT_PRIMARY};
}}

/* Badges */
QLabel.badge-green {{
    background-color: rgba(46, 204, 113, 0.15);
    border: 1px solid {AdrenalinColors.ACCENT_GREEN};
    color: {AdrenalinColors.ACCENT_GREEN};
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}

QLabel.badge-red {{
    background-color: rgba(224, 30, 55, 0.15);
    border: 1px solid {AdrenalinColors.ACCENT_RED};
    color: {AdrenalinColors.TEXT_RED};
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}

QLabel.badge-gray {{
    background-color: {AdrenalinColors.BG_PANEL};
    border: 1px solid {AdrenalinColors.BORDER_SUBTLE};
    color: {AdrenalinColors.TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}

QLabel.badge-cyan {{
    background-color: rgba(0, 210, 255, 0.15);
    border: 1px solid #00D2FF;
    color: #00D2FF;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}

QLabel.badge-orange {{
    background-color: rgba(255, 152, 0, 0.15);
    border: 1px solid #FF9800;
    color: #FF9800;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}}
"""
