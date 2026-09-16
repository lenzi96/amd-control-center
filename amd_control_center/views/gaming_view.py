"""Gaming View (Spiele & Profile) with FSR 4 Injection & DLSS Swapper for AMD Control Center."""

import os
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QScrollArea, QFrame, QStackedWidget,
    QGridLayout, QMessageBox, QApplication, QCheckBox, QButtonGroup
)

from ..backend.game_scanner import GameInfo
from ..backend.game_profiles import ProfileManager, GameGraphicProfile
from ..backend.fsr4_injector import (
    inject_fsr4_files_into_game, remove_fsr4_files_from_game,
    detect_game_upscaler_support
)
from ..backend.fsr4_dll_updater import (
    get_local_version, check_for_dll_updates, download_and_update_dlls,
    get_game_dll_status, deploy_fsr4_dlls_to_game, restore_original_game_dlls,
    detect_game_upscalers, list_available_versions
)
from ..backend.gpu_detector import detect_amd_gpus
from ..widgets.game_card import GameCard
from ..widgets.toggle_switch import ToggleSwitch
from ..widgets.styled_slider import StyledSlider
from ..widgets.mangohud_editor import MangoHudSettingsDialog


class SwapperGameCard(QFrame):
    """Card item in DLSS Swapper tab representing a single game with upscaler badges, FSR 4 tuning drawer and 1-click swap."""
    swapped = pyqtSignal(str)              # app_id
    restored = pyqtSignal(str)             # app_id
    detail_requested = pyqtSignal(object)  # game

    def __init__(self, game: GameInfo, upscaler_info: Dict[str, Any], available_versions: List[str], default_arch: str, profile_mgr: Optional[ProfileManager] = None, parent=None):
        super().__init__(parent)
        self.game = game
        self.upscaler_info = upscaler_info
        self.available_versions = available_versions
        self.profile_mgr = profile_mgr
        self.setObjectName("swapperCard")
        self.setStyleSheet("""
            QFrame#swapperCard {
                background-color: #171B23;
                border: 1px solid #28303F;
                border-radius: 8px;
            }
            QFrame#swapperCard:hover {
                border-color: #3D4A5E;
                background-color: #1C212B;
            }
        """)

        # Fetch profile defaults if available
        if profile_mgr:
            prof = profile_mgr.get_profile(game.app_id)
            init_fg = prof.fsr4_frame_gen
            init_ind = prof.fsr4_indicator
            init_sharp = prof.fsr4_sharpness
            init_qual = prof.fsr4_quality
        else:
            init_fg = upscaler_info.get("frame_gen", True)
            init_ind = upscaler_info.get("indicator", True)
            init_sharp = upscaler_info.get("sharpness", 70)
            init_qual = upscaler_info.get("quality_mode", "Quality")

        card_vbox = QVBoxLayout(self)
        card_vbox.setContentsMargins(14, 10, 16, 10)
        card_vbox.setSpacing(8)

        # Top row: Cover + Info + Controls
        top_l = QHBoxLayout()
        top_l.setSpacing(16)

        # 1. Cover / Art thumbnail (56x78 px)
        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(56, 78)
        self.lbl_cover.setStyleSheet("border-radius: 6px; background-color: #0E1116; border: 1px solid #28303F;")
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_cover()
        top_l.addWidget(self.lbl_cover)

        # 2. Middle Info
        mid_l = QVBoxLayout()
        mid_l.setSpacing(4)

        # Title
        self.lbl_title = QLabel(game.name)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        mid_l.addWidget(self.lbl_title)

        # Badges row
        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)

        if upscaler_info.get("has_dlss"):
            b_dlss = QLabel("DLSS 2/3")
            b_dlss.setStyleSheet("background-color: rgba(0, 230, 118, 0.15); border: 1px solid #00E676; color: #00E676; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
            badges_row.addWidget(b_dlss)

        if upscaler_info.get("has_dlss_fg"):
            b_fg = QLabel("DLSS-G FrameGen")
            b_fg.setStyleSheet("background-color: rgba(0, 229, 255, 0.15); border: 1px solid #00E5FF; color: #00E5FF; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
            badges_row.addWidget(b_fg)

        if upscaler_info.get("has_fsr"):
            b_fsr = QLabel("FSR")
            b_fsr.setStyleSheet("background-color: rgba(255, 152, 0, 0.15); border: 1px solid #FF9800; color: #FF9800; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
            badges_row.addWidget(b_fsr)

        if upscaler_info.get("has_xess"):
            b_xess = QLabel("XeSS")
            b_xess.setStyleSheet("background-color: rgba(33, 150, 243, 0.15); border: 1px solid #2196F3; color: #2196F3; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
            badges_row.addWidget(b_xess)

        if not (upscaler_info.get("has_dlss") or upscaler_info.get("has_fsr") or upscaler_info.get("has_xess")):
            b_none = QLabel("DirectX / Vulkan")
            b_none.setStyleSheet("background-color: #202632; color: #7E8D9F; font-size: 10px; border-radius: 4px; padding: 2px 6px;")
            badges_row.addWidget(b_none)

        badges_row.addStretch()
        mid_l.addLayout(badges_row)

        # Status text
        self.lbl_status = QLabel()
        mid_l.addWidget(self.lbl_status)

        # Path snippet
        p_str = upscaler_info.get("target_dir") or game.install_dir
        if len(p_str) > 75:
            p_str = "..." + p_str[-72:]
        lbl_path = QLabel(f"📂 {p_str}")
        lbl_path.setStyleSheet("color: #556272; font-size: 10px;")
        mid_l.addWidget(lbl_path)

        top_l.addLayout(mid_l, stretch=1)

        # 3. Right Controls
        ctrl_l = QVBoxLayout()
        ctrl_l.setSpacing(6)
        ctrl_l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)

        # Arch selector
        self.combo_arch = QComboBox()
        self.combo_arch.setFixedWidth(195)
        self.combo_arch.addItems([
            "RX 7000 (RDNA 3 WMMA)",
            "RX 9000 (RDNA 4 AI)"
        ])
        if "9000" in default_arch or "RDNA4" in default_arch:
            self.combo_arch.setCurrentIndex(1)
        else:
            self.combo_arch.setCurrentIndex(0)
        sel_row.addWidget(self.combo_arch)

        # Version selector
        self.combo_ver = QComboBox()
        self.combo_ver.setFixedWidth(85)
        self.combo_ver.addItems(self.available_versions)
        sel_row.addWidget(self.combo_ver)

        ctrl_l.addLayout(sel_row)

        # Action Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_swap = QPushButton("⚡ AUF FSR 4 TAUSCHEN")
        self.btn_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_swap.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B31227);
                border: none;
                border-radius: 4px;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 11px;
                padding: 7px 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #CC172F);
            }
            QPushButton:pressed {
                background-color: #8B1020;
            }
        """)
        self.btn_swap.clicked.connect(self._on_swap_clicked)
        btn_row.addWidget(self.btn_swap)

        self.btn_restore = QPushButton("↺ ORIGINAL")
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                font-size: 11px;
                padding: 7px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #15181F;
                border-color: #242934;
                color: #495466;
            }
        """)
        self.btn_restore.clicked.connect(self._on_restore_clicked)
        btn_row.addWidget(self.btn_restore)

        self.btn_tuning = QPushButton("⚙ Tuning ▾")
        self.btn_tuning.setToolTip("FSR 4 Qualität, AFMF 2 & Schärfegrad anpassen")
        self.btn_tuning.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tuning.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                font-size: 11px;
                padding: 7px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        self.btn_tuning.clicked.connect(self._toggle_tuning)
        btn_row.addWidget(self.btn_tuning)

        self.btn_detail = QPushButton("🎮")
        self.btn_detail.setToolTip("Allgemeines Spiel-Profil (FPS-Begrenzer, Anti-Lag) öffnen")
        self.btn_detail.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detail.setFixedSize(30, 30)
        self.btn_detail.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        self.btn_detail.clicked.connect(lambda: self.detail_requested.emit(self.game))
        btn_row.addWidget(self.btn_detail)

        ctrl_l.addLayout(btn_row)
        top_l.addLayout(ctrl_l)
        card_vbox.addLayout(top_l)

        # Bottom expandable drawer: FSR 4 Quality, AFMF 2 & Sharpness
        self.tuning_drawer = QFrame()
        self.tuning_drawer.setStyleSheet("""
            QFrame {
                background-color: #12151B;
                border: 1px solid #232A37;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        td_l = QVBoxLayout(self.tuning_drawer)
        td_l.setContentsMargins(6, 6, 6, 6)
        td_l.setSpacing(8)

        dr1 = QHBoxLayout()
        dr1.setSpacing(14)

        lbl_q = QLabel("FSR 4 Qualität:")
        lbl_q.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["Ultra Quality", "Quality", "Balanced", "Performance", "Ultra Performance"])
        self.combo_quality.setCurrentText(init_qual)
        self.combo_quality.setFixedWidth(150)
        dr1.addWidget(lbl_q)
        dr1.addWidget(self.combo_quality)

        self.chk_fg = QCheckBox("✦ AFMF 2 Frame Generation")
        self.chk_fg.setChecked(init_fg)
        self.chk_fg.setStyleSheet("font-size: 11px; font-weight: bold; color: #00D2FF;")
        dr1.addWidget(self.chk_fg)

        self.chk_ind = QCheckBox("✦ Status-Wasserzeichen")
        self.chk_ind.setChecked(init_ind)
        self.chk_ind.setStyleSheet("font-size: 11px; font-weight: bold; color: #A8B2C4;")
        dr1.addWidget(self.chk_ind)
        dr1.addStretch()

        td_l.addLayout(dr1)

        self.slider_sharpness = StyledSlider("FSR 4 AI Schärfegrad", 0, 100, init_sharp, "%", step=5)
        td_l.addWidget(self.slider_sharpness)

        self.tuning_drawer.setVisible(False)
        card_vbox.addWidget(self.tuning_drawer)

        self._update_status_label()

    def _toggle_tuning(self):
        vis = not self.tuning_drawer.isVisible()
        self.tuning_drawer.setVisible(vis)
        self.btn_tuning.setText("⚙ Tuning ▴" if vis else "⚙ Tuning ▾")

    def _load_cover(self):
        img_path = self.game.poster_image or self.game.banner_image
        if img_path and os.path.exists(img_path):
            pix = QPixmap(img_path)
            if not pix.isNull():
                self.lbl_cover.setPixmap(pix.scaled(56, 78, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                return
        init = self.game.name[:2].upper() if self.game.name else "🎮"
        self.lbl_cover.setText(init)
        self.lbl_cover.setStyleSheet("border-radius: 6px; background-color: #12151B; border: 1px solid #28303F; color: #E01E37; font-weight: 900; font-size: 16px;")

    def _update_status_label(self):
        is_swapped = self.upscaler_info.get("is_fsr4_swapped", False)
        ver = self.upscaler_info.get("swapped_version") or "v0.9.4"
        arch = self.upscaler_info.get("swapped_arch") or "RX 7000 (RDNA 3)"
        fg = self.chk_fg.isChecked()
        qual = self.combo_quality.currentText()

        if is_swapped:
            self.lbl_status.setText(f"✓ FSR 4 {ver} AKTIV ({arch} • {qual} • AFMF 2: {'Ein' if fg else 'Aus'})")
            self.lbl_status.setStyleSheet("color: #2ECC71; font-size: 11px; font-weight: bold;")
            self.btn_restore.setEnabled(True)
            self.btn_swap.setText("⚡ FSR 4 AKTUALISIEREN")
        else:
            if self.upscaler_info.get("has_dlss"):
                self.lbl_status.setText("○ Originalzustand (NVIDIA DLSS vorhanden - Bereit für FSR 4)")
                self.lbl_status.setStyleSheet("color: #00E676; font-size: 11px; font-weight: 600;")
            else:
                self.lbl_status.setText("○ Originalzustand (Nicht getauscht)")
                self.lbl_status.setStyleSheet("color: #7E8D9F; font-size: 11px;")
            self.btn_restore.setEnabled(False)
            self.btn_swap.setText("⚡ AUF FSR 4 TAUSCHEN")

    def _on_swap_clicked(self):
        arch_sel = "RDNA3" if "7000" in self.combo_arch.currentText() else "RDNA4"
        ver_sel = self.combo_ver.currentText()
        fg = self.chk_fg.isChecked()
        ind = self.chk_ind.isChecked()
        sharpness = self.slider_sharpness.value()
        quality = self.combo_quality.currentText()

        ok, msg = deploy_fsr4_dlls_to_game(
            self.game.install_dir,
            frame_gen=fg,
            indicator=ind,
            sharpness=sharpness,
            gpu_arch=arch_sel,
            target_version=ver_sel,
            quality_mode=quality
        )
        if ok:
            self.upscaler_info["is_fsr4_swapped"] = True
            self.upscaler_info["swapped_version"] = ver_sel
            self.upscaler_info["swapped_arch"] = "RX 7000 (RDNA 3 WMMA)" if arch_sel == "RDNA3" else "RX 9000 (RDNA 4 AI)"
            self.upscaler_info["frame_gen"] = fg
            self.upscaler_info["indicator"] = ind
            self.upscaler_info["sharpness"] = sharpness
            self.upscaler_info["quality_mode"] = quality

            if self.profile_mgr:
                prof = self.profile_mgr.get_profile(self.game.app_id)
                prof.fsr4_enabled = True
                prof.fsr4_frame_gen = fg
                prof.fsr4_indicator = ind
                prof.fsr4_sharpness = sharpness
                prof.fsr4_quality = quality
                self.profile_mgr.save()

            self._update_status_label()
            self.swapped.emit(self.game.app_id)
        return ok, msg

    def _on_restore_clicked(self):
        ok, msg = restore_original_game_dlls(self.game.install_dir)
        if ok:
            self.upscaler_info["is_fsr4_swapped"] = False
            self.upscaler_info["swapped_version"] = None
            self.upscaler_info["swapped_arch"] = None
            self._update_status_label()
            self.restored.emit(self.game.app_id)
        return ok, msg


class GamingView(QWidget):
    play_game_requested = pyqtSignal(str)

    def __init__(self, games: List[GameInfo], profile_mgr: ProfileManager, parent=None):
        super().__init__(parent)
        self.games = games
        self.profile_mgr = profile_mgr
        self.active_game: Optional[GameInfo] = None
        self.max_display = 36
        self.last_subtab = 0
        self.swapper_filter_type = "dlss"  # default filter in Swapper tab: DLSS games!
        self.swapper_cards: List[SwapperGameCard] = []
        self._upscaler_cache: Dict[str, dict] = {}

        # Determine default architecture from GPU
        gpus = detect_amd_gpus()
        if gpus and "9000" in gpus[0].generation_name:
            self.default_arch = "RX 9000 Serie (RDNA 4)"
        else:
            self.default_arch = "RX 7000 Serie (RDNA 3)"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(14)

        # Top Bar: Subtabs & Search
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.btn_all_games = QPushButton(f"ALLE SPIELE ({len(games)})")
        self.btn_swapper = QPushButton("⚡ FSR 4 SWAPPER (DLSS-TAUSCHER)")
        self.btn_global = QPushButton("GLOBALE GRAFIK & EINSTELLUNGEN")

        for b in [self.btn_all_games, self.btn_swapper, self.btn_global]:
            b.setCheckable(True)
            b.setProperty("class", "subnav-tab")
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_all_games.setChecked(True)
        self.btn_all_games.clicked.connect(lambda: self._switch_subtab(0))
        self.btn_swapper.clicked.connect(lambda: self._switch_subtab(1))
        self.btn_global.clicked.connect(lambda: self._switch_subtab(2))

        top_bar.addWidget(self.btn_all_games)
        top_bar.addWidget(self.btn_swapper)
        top_bar.addWidget(self.btn_global)
        top_bar.addStretch()

        # Search Bar
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Spiel suchen...")
        self.search_box.setFixedWidth(240)
        self.search_box.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_box)

        layout.addLayout(top_bar)

        # Stack: 0 -> Games Grid, 1 -> DLSS Swapper, 2 -> Global Graphics, 3 -> Game Profile Detail
        self.stack = QStackedWidget()
        self.games_grid_page = self._create_games_grid_page()
        self.swapper_page = self._create_swapper_page()
        self.global_page = self._create_global_page()
        self.detail_page = self._create_detail_page()

        self.stack.addWidget(self.games_grid_page)
        self.stack.addWidget(self.swapper_page)
        self.stack.addWidget(self.global_page)
        self.stack.addWidget(self.detail_page)

        layout.addWidget(self.stack)

    def _get_upscaler_info(self, game: GameInfo) -> dict:
        if game.app_id not in self._upscaler_cache:
            self._upscaler_cache[game.app_id] = detect_game_upscalers(game.install_dir)
        return self._upscaler_cache[game.app_id]

    def _has_upscaler(self, game: GameInfo) -> bool:
        u = self._get_upscaler_info(game)
        return bool(u.get("has_dlss") or u.get("has_dlss_fg") or u.get("has_fsr") or u.get("has_xess") or u.get("is_fsr4_swapped"))

    def _switch_subtab(self, idx: int):
        self.btn_all_games.setChecked(idx == 0)
        self.btn_swapper.setChecked(idx == 1)
        self.btn_global.setChecked(idx == 2)
        self.stack.setCurrentIndex(idx)
        self.search_box.setVisible(idx in (0, 1))
        if idx in (0, 1):
            self.last_subtab = idx
        if idx == 1 and not self.swapper_cards:
            self._populate_swapper()

    def _on_search_changed(self, text: str):
        if self.stack.currentIndex() == 0:
            self._filter_games(text)
        elif self.stack.currentIndex() == 1:
            self._filter_swapper_cards()

    def _create_games_grid_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.grid_container = QWidget()
        self.outer_vbox = QVBoxLayout(self.grid_container)
        self.outer_vbox.setContentsMargins(4, 10, 4, 16)
        self.outer_vbox.setSpacing(16)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.outer_vbox.addLayout(self.grid_layout)

        # Load More Button
        self.btn_load_more = QPushButton(f"Weitere Spiele laden ({len(self.games) - self.max_display} verbleibend)")
        self.btn_load_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_more.setStyleSheet("""
            QPushButton {
                background-color: #171B23;
                border: 1px solid #28303F;
                border-radius: 6px;
                padding: 10px;
                color: #C5CFDC;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid #E01E37;
                color: #FFFFFF;
            }
        """)
        self.btn_load_more.clicked.connect(self._load_all_games)
        self.outer_vbox.addWidget(self.btn_load_more)

        self.game_cards: List[GameCard] = []
        self._populate_grid(self.games[:self.max_display])

        scroll.setWidget(self.grid_container)
        return scroll

    def _load_all_games(self):
        self.btn_load_more.setVisible(False)
        self._populate_grid(self.games)

    def _populate_grid(self, games: List[GameInfo]):
        for c in self.game_cards:
            self.grid_layout.removeWidget(c)
            c.deleteLater()
        self.game_cards.clear()

        columns = 6
        for idx, g in enumerate(games):
            card = GameCard(g)
            card.clicked.connect(self._open_game_detail)
            card.play_requested.connect(self.play_game_requested.emit)
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            self.game_cards.append(card)

    def _filter_games(self, query: Optional[str] = None):
        if query is None:
            query = self.search_box.text()
        query = query.strip().lower()
        if not query:
            self.btn_load_more.setVisible(len(self.games) > self.max_display)
            self._populate_grid(self.games[:self.max_display])
        else:
            self.btn_load_more.setVisible(False)
            filtered = [g for g in self.games if query in g.name.lower()]
            self._populate_grid(filtered[:60])

    def _create_swapper_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 10, 0, 20)
        vbox.setSpacing(14)

        # 1. Header Banner & Global Presets
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #181423, stop:1 #11141B);
                border: 1px solid #372A4B;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        b_layout = QVBoxLayout(banner)
        b_layout.setSpacing(12)

        # Title Row
        title_row = QHBoxLayout()
        title_lbl = QLabel("⚡ AMD FSR 4 SWAPPER (DLSS-TAUSCHER)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 900; color: #FFFFFF; letter-spacing: 0.8px;")

        cur_v = get_local_version()
        self.lbl_swapper_repo_ver = QLabel(f"DLL-Repository: {cur_v}")
        self.lbl_swapper_repo_ver.setStyleSheet("background-color: rgba(224, 30, 55, 0.15); color: #FF4256; border: 1px solid #E01E37; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;")

        title_row.addWidget(title_lbl)
        title_row.addWidget(self.lbl_swapper_repo_ver)
        title_row.addStretch()

        btn_check_updates = QPushButton("🔄 Online-Updates suchen")
        btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_check_updates.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E01E37;
                border-color: #FF2E47;
            }
        """)
        btn_check_updates.clicked.connect(self._check_swapper_updates)
        title_row.addWidget(btn_check_updates)
        b_layout.addLayout(title_row)

        desc_lbl = QLabel(
            "Tauscht proprietäres NVIDIA DLSS 2/3 & DLSS-G Frame Generation automatisch gegen AMD FSR 4 Neural Edition (OptiScaler) aus.\n"
            "Vollständig optimiert für AMD Radeon RX 7000 (RDNA 3 WMMA Dual-Issue & FP16) sowie Radeon RX 9000 (RDNA 4 AI Matrix Cores)."
        )
        desc_lbl.setStyleSheet("color: #C5CFDC; font-size: 12px; line-height: 1.4;")
        b_layout.addWidget(desc_lbl)

        # Global Preset Controls
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet("""
            QFrame {
                background-color: #151922;
                border: 1px solid #242B38;
                border-radius: 6px;
                padding: 10px 14px;
            }
        """)
        cf_vbox = QVBoxLayout(ctrl_frame)
        cf_vbox.setSpacing(10)

        # Row 1: Arch, Version, Quality
        r1 = QHBoxLayout()
        r1.setSpacing(14)

        lbl_arch = QLabel("Standard-Architektur:")
        lbl_arch.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        self.swapper_global_arch = QComboBox()
        self.swapper_global_arch.addItems([
            "RX 7000 Serie (RDNA 3 - Dual-Issue WMMA AI & FP16)",
            "RX 9000 Serie (RDNA 4 - Neural Matrix Cores FP8)"
        ])
        if "9000" in self.default_arch:
            self.swapper_global_arch.setCurrentIndex(1)
        else:
            self.swapper_global_arch.setCurrentIndex(0)
        self.swapper_global_arch.setFixedWidth(310)
        self.swapper_global_arch.currentIndexChanged.connect(self._on_global_arch_changed)

        lbl_ver = QLabel("FSR 4 Version:")
        lbl_ver.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        self.swapper_global_ver = QComboBox()
        self.swapper_global_ver.addItems(list_available_versions())
        self.swapper_global_ver.setFixedWidth(90)
        self.swapper_global_ver.currentTextChanged.connect(self._on_global_ver_changed)

        lbl_qual = QLabel("Qualitätsmodus:")
        lbl_qual.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFFFFF;")
        self.swapper_global_quality = QComboBox()
        self.swapper_global_quality.addItems(["Ultra Quality", "Quality", "Balanced", "Performance", "Ultra Performance"])
        self.swapper_global_quality.setCurrentText("Quality")
        self.swapper_global_quality.setFixedWidth(140)
        self.swapper_global_quality.currentTextChanged.connect(self._on_global_quality_changed)

        r1.addWidget(lbl_arch)
        r1.addWidget(self.swapper_global_arch)
        r1.addWidget(lbl_ver)
        r1.addWidget(self.swapper_global_ver)
        r1.addWidget(lbl_qual)
        r1.addWidget(self.swapper_global_quality)
        r1.addStretch()
        cf_vbox.addLayout(r1)

        # Row 2: AFMF 2, Watermark, Sharpness & Apply Button
        r2 = QHBoxLayout()
        r2.setSpacing(16)

        self.swapper_global_fg = QCheckBox("✦ AFMF 2 Frame Generation")
        self.swapper_global_fg.setChecked(True)
        self.swapper_global_fg.setStyleSheet("font-size: 11px; font-weight: bold; color: #00D2FF;")
        self.swapper_global_fg.toggled.connect(self._on_global_fg_changed)

        self.swapper_global_ind = QCheckBox("✦ Status-Wasserzeichen")
        self.swapper_global_ind.setChecked(True)
        self.swapper_global_ind.setStyleSheet("font-size: 11px; font-weight: bold; color: #A8B2C4;")
        self.swapper_global_ind.toggled.connect(self._on_global_ind_changed)

        btn_apply_presets = QPushButton("⚙ Auf alle Spiele übertragen")
        btn_apply_presets.setToolTip("Überträgt gewählte Architektur, Version, Qualität, AFMF 2 und Schärfe auf alle Spielekarten")
        btn_apply_presets.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_presets.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E01E37;
                border-color: #FF2E47;
            }
        """)
        btn_apply_presets.clicked.connect(self._apply_global_presets_to_cards)

        r2.addWidget(self.swapper_global_fg)
        r2.addWidget(self.swapper_global_ind)
        r2.addStretch()
        r2.addWidget(btn_apply_presets)
        cf_vbox.addLayout(r2)

        # Row 3: Sharpness slider
        self.swapper_global_sharpness = StyledSlider("Standard AI Schärfegrad", 0, 100, 70, "%", step=5)
        self.swapper_global_sharpness.valueChanged.connect(self._on_global_sharpness_changed)
        cf_vbox.addWidget(self.swapper_global_sharpness)

        b_layout.addWidget(ctrl_frame)
        vbox.addWidget(banner)

        # 2. Batch Operations & Filters Bar
        bar_frame = QFrame()
        bar_frame.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 6px; padding: 10px 14px;")
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(12)

        # Filter Chips
        lbl_filter = QLabel("Filter:")
        lbl_filter.setStyleSheet("font-weight: bold; color: #7E8D9F; font-size: 11px;")
        bar_layout.addWidget(lbl_filter)

        self.btn_chip_dlss = QPushButton("⚡ DLSS Erkannt (0)")
        self.btn_chip_upscaler = QPushButton("✦ Alle mit Upscaler (0)")
        self.btn_chip_swapped = QPushButton("✔ FSR 4 Aktiv (0)")
        self.btn_chip_all = QPushButton("Alle Spiele (0)")
        self.btn_chip_original = QPushButton("📦 Original (0)")

        self.chips = [self.btn_chip_dlss, self.btn_chip_upscaler, self.btn_chip_swapped, self.btn_chip_all, self.btn_chip_original]
        chip_style = """
            QPushButton {
                background-color: #12151B;
                border: 1px solid #28303F;
                color: #A8B2C4;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: rgba(224, 30, 55, 0.15);
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """
        for chip in self.chips:
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(chip_style)

        self.btn_chip_dlss.setChecked(True)
        self.btn_chip_dlss.clicked.connect(lambda: self._set_swapper_filter("dlss"))
        self.btn_chip_upscaler.clicked.connect(lambda: self._set_swapper_filter("upscaler"))
        self.btn_chip_swapped.clicked.connect(lambda: self._set_swapper_filter("swapped"))
        self.btn_chip_all.clicked.connect(lambda: self._set_swapper_filter("all"))
        self.btn_chip_original.clicked.connect(lambda: self._set_swapper_filter("original"))

        bar_layout.addWidget(self.btn_chip_dlss)
        bar_layout.addWidget(self.btn_chip_upscaler)
        bar_layout.addWidget(self.btn_chip_swapped)
        bar_layout.addWidget(self.btn_chip_all)
        bar_layout.addWidget(self.btn_chip_original)

        # Checkbox: Spiele ohne Upscaler ausblenden
        self.chk_swapper_hide_no_upscaler = QCheckBox("Spiele ohne Upscaler ausblenden")
        self.chk_swapper_hide_no_upscaler.setChecked(True)
        self.chk_swapper_hide_no_upscaler.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_swapper_hide_no_upscaler.setStyleSheet("""
            QCheckBox {
                color: #C8D1DC;
                font-weight: bold;
                font-size: 11px;
                padding-left: 8px;
            }
            QCheckBox:hover {
                color: #FFFFFF;
            }
        """)
        self.chk_swapper_hide_no_upscaler.toggled.connect(lambda: self._filter_swapper_cards())
        bar_layout.addWidget(self.chk_swapper_hide_no_upscaler)
        bar_layout.addStretch()

        # Batch buttons
        self.btn_batch_swap = QPushButton("⚡ Alle DLSS-Spiele auf FSR 4 tauschen")
        self.btn_batch_swap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_swap.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B31227);
                border: none;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 7px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #CC172F);
            }
        """)
        self.btn_batch_swap.clicked.connect(self._batch_swap_dlss)
        bar_layout.addWidget(self.btn_batch_swap)

        self.btn_batch_restore = QPushButton("↺ Alle auf Original")
        self.btn_batch_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_restore.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                font-size: 11px;
                padding: 7px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        self.btn_batch_restore.clicked.connect(self._batch_restore_all)
        bar_layout.addWidget(self.btn_batch_restore)

        btn_rescan = QPushButton("🔄 Neu scannen")
        btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rescan.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #A8B2C4;
                font-weight: bold;
                font-size: 11px;
                padding: 7px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        btn_rescan.clicked.connect(self._populate_swapper)
        bar_layout.addWidget(btn_rescan)

        vbox.addWidget(bar_frame)

        # 3. Cards List Container
        self.swapper_list_container = QWidget()
        self.swapper_list_layout = QVBoxLayout(self.swapper_list_container)
        self.swapper_list_layout.setContentsMargins(0, 0, 0, 0)
        self.swapper_list_layout.setSpacing(10)
        vbox.addWidget(self.swapper_list_container)
        vbox.addStretch()

        scroll.setWidget(container)
        return scroll

    def _set_swapper_filter(self, filter_type: str):
        self.swapper_filter_type = filter_type
        self.btn_chip_dlss.setChecked(filter_type == "dlss")
        self.btn_chip_upscaler.setChecked(filter_type == "upscaler")
        self.btn_chip_swapped.setChecked(filter_type == "swapped")
        self.btn_chip_all.setChecked(filter_type == "all")
        self.btn_chip_original.setChecked(filter_type == "original")
        self._filter_swapper_cards()

    def _on_global_arch_changed(self, idx: int):
        for c in self.swapper_cards:
            c.combo_arch.setCurrentIndex(idx)

    def _on_global_ver_changed(self, ver: str):
        for c in self.swapper_cards:
            c.combo_ver.setCurrentText(ver)

    def _on_global_quality_changed(self, qual: str):
        for c in self.swapper_cards:
            c.combo_quality.setCurrentText(qual)

    def _on_global_fg_changed(self, state: bool):
        for c in self.swapper_cards:
            c.chk_fg.setChecked(state)

    def _on_global_ind_changed(self, state: bool):
        for c in self.swapper_cards:
            c.chk_ind.setChecked(state)

    def _on_global_sharpness_changed(self, val: int):
        for c in self.swapper_cards:
            c.slider_sharpness.setValue(val)

    def _apply_global_presets_to_cards(self):
        arch_idx = self.swapper_global_arch.currentIndex()
        ver = self.swapper_global_ver.currentText()
        qual = self.swapper_global_quality.currentText()
        fg = self.swapper_global_fg.isChecked()
        ind = self.swapper_global_ind.isChecked()
        sharp = self.swapper_global_sharpness.value()

        for c in self.swapper_cards:
            c.combo_arch.setCurrentIndex(arch_idx)
            c.combo_ver.setCurrentText(ver)
            c.combo_quality.setCurrentText(qual)
            c.chk_fg.setChecked(fg)
            c.chk_ind.setChecked(ind)
            c.slider_sharpness.setValue(sharp)

        QMessageBox.information(
            self,
            "FSR 4 DLSS Swapper",
            f"Voreinstellungen erfolgreich auf alle {len(self.swapper_cards)} Spielekarten übertragen:\n\n"
            f"• FSR 4 Version: {ver}\n"
            f"• Qualitätsmodus: {qual}\n"
            f"• AFMF 2 Frame-Gen: {'Aktiviert' if fg else 'Deaktiviert'}\n"
            f"• Status-Overlay: {'Aktiviert' if ind else 'Deaktiviert'}\n"
            f"• AI Schärfegrad: {sharp}%"
        )

    def _populate_swapper(self):
        for c in self.swapper_cards:
            self.swapper_list_layout.removeWidget(c)
            c.deleteLater()
        self.swapper_cards.clear()

        available_versions = list_available_versions()
        current_arch = self.swapper_global_arch.currentText()

        dlss_count = 0
        swapped_count = 0
        upscaler_count = 0
        orig_count = 0

        for g in self.games:
            uinfo = self._get_upscaler_info(g)
            has_up = bool(
                uinfo.get("has_dlss") or
                uinfo.get("has_dlss_fg") or
                uinfo.get("has_fsr") or
                uinfo.get("has_xess") or
                uinfo.get("is_fsr4_swapped")
            )
            if has_up:
                upscaler_count += 1
            if uinfo.get("has_dlss"):
                dlss_count += 1
            if uinfo.get("is_fsr4_swapped"):
                swapped_count += 1
            else:
                orig_count += 1

            card = SwapperGameCard(g, uinfo, available_versions, current_arch, self.profile_mgr)
            card.swapped.connect(self._on_card_swapped_or_restored)
            card.restored.connect(self._on_card_swapped_or_restored)
            card.detail_requested.connect(self._open_game_detail)

            self.swapper_list_layout.addWidget(card)
            self.swapper_cards.append(card)

        self.btn_chip_all.setText(f"Alle Spiele ({len(self.games)})")
        self.btn_chip_dlss.setText(f"⚡ DLSS Erkannt ({dlss_count})")
        self.btn_chip_upscaler.setText(f"✦ Alle mit Upscaler ({upscaler_count})")
        self.btn_chip_swapped.setText(f"✔ FSR 4 Aktiv ({swapped_count})")
        self.btn_chip_original.setText(f"📦 Original ({orig_count})")

        self._filter_swapper_cards()

    def _on_card_swapped_or_restored(self, app_id: str):
        dlss_count = sum(1 for c in self.swapper_cards if c.upscaler_info.get("has_dlss"))
        swapped_count = sum(1 for c in self.swapper_cards if c.upscaler_info.get("is_fsr4_swapped"))
        upscaler_count = sum(1 for c in self.swapper_cards if (
            c.upscaler_info.get("has_dlss") or
            c.upscaler_info.get("has_dlss_fg") or
            c.upscaler_info.get("has_fsr") or
            c.upscaler_info.get("has_xess") or
            c.upscaler_info.get("is_fsr4_swapped")
        ))
        orig_count = len(self.swapper_cards) - swapped_count

        self.btn_chip_dlss.setText(f"⚡ DLSS Erkannt ({dlss_count})")
        self.btn_chip_upscaler.setText(f"✦ Alle mit Upscaler ({upscaler_count})")
        self.btn_chip_swapped.setText(f"✔ FSR 4 Aktiv ({swapped_count})")
        self.btn_chip_original.setText(f"📦 Original ({orig_count})")

    def _filter_swapper_cards(self):
        query = self.search_box.text().strip().lower()
        ft = self.swapper_filter_type
        hide_no_upscaler = self.chk_swapper_hide_no_upscaler.isChecked() if hasattr(self, 'chk_swapper_hide_no_upscaler') else True

        for c in self.swapper_cards:
            matches_search = not query or (query in c.game.name.lower())
            has_up = bool(
                c.upscaler_info.get("has_dlss") or
                c.upscaler_info.get("has_dlss_fg") or
                c.upscaler_info.get("has_fsr") or
                c.upscaler_info.get("has_xess") or
                c.upscaler_info.get("is_fsr4_swapped")
            )

            if hide_no_upscaler and not has_up:
                c.setVisible(False)
                continue

            matches_filter = True
            if ft == "dlss":
                matches_filter = bool(c.upscaler_info.get("has_dlss"))
            elif ft == "upscaler":
                matches_filter = has_up
            elif ft == "swapped":
                matches_filter = bool(c.upscaler_info.get("is_fsr4_swapped"))
            elif ft == "original":
                matches_filter = not bool(c.upscaler_info.get("is_fsr4_swapped"))

            c.setVisible(matches_search and matches_filter)

    def _batch_swap_dlss(self):
        dlss_cards = [c for c in self.swapper_cards if c.upscaler_info.get("has_dlss")]
        if not dlss_cards:
            QMessageBox.information(self, "DLSS Swapper", "Keine DLSS-Spiele in der Bibliothek gefunden.")
            return

        arch_name = self.swapper_global_arch.currentText()
        ver_name = self.swapper_global_ver.currentText()
        qual_name = self.swapper_global_quality.currentText()
        fg_status = "Aktiviert" if self.swapper_global_fg.isChecked() else "Deaktiviert"

        ret = QMessageBox.question(
            self,
            "FSR 4 Batch-Tausch bestätigen",
            f"Möchten Sie FSR 4 für alle {len(dlss_cards)} erkannten DLSS-Spiele aktivieren?\n\n"
            f"• Ziel-Architektur: {arch_name}\n"
            f"• FSR 4 Version: {ver_name}\n"
            f"• Bildqualität: {qual_name}\n"
            f"• AFMF 2 Frame-Gen: {fg_status}\n\n"
            f"Alle Original-DLLs (nvngx.dll / dxgi.dll) werden vor dem Tausch automatisch gesichert (.bak).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        success_count = 0
        for c in dlss_cards:
            ok, _ = c._on_swap_clicked()
            if ok:
                success_count += 1

        self._on_card_swapped_or_restored("")
        self._filter_swapper_cards()
        QMessageBox.information(
            self,
            "FSR 4 DLSS Swapper",
            f"Erfolgreich {success_count} von {len(dlss_cards)} Spielen auf FSR 4 ({arch_name}) getauscht!"
        )

    def _batch_restore_all(self):
        swapped_cards = [c for c in self.swapper_cards if c.upscaler_info.get("is_fsr4_swapped")]
        if not swapped_cards:
            QMessageBox.information(self, "DLSS Swapper", "Keine modifizierten Spiele vorhanden.")
            return

        ret = QMessageBox.question(
            self,
            "Wiederherstellung bestätigen",
            f"Möchten Sie alle {len(swapped_cards)} modifizierten Spiele auf ihren Originalzustand zurücksetzen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        success_count = 0
        for c in swapped_cards:
            ok, _ = c._on_restore_clicked()
            if ok:
                success_count += 1

        self._on_card_swapped_or_restored("")
        self._filter_swapper_cards()
        QMessageBox.information(
            self,
            "Originalzustand",
            f"Erfolgreich {success_count} Spiele wiederhergestellt."
        )

    def _check_swapper_updates(self):
        res = check_for_dll_updates()
        if res.get("has_update"):
            ret = QMessageBox.question(
                self,
                "FSR 4 Update verfügbar!",
                f"Eine neuere Version ({res['latest_version']}) von FSR 4 / OptiScaler ist verfügbar!\n\n"
                f"Installierte Version: {res['current_version']}\n"
                f"Neueste Version: {res['latest_version']}\n\n"
                f"Möchten Sie das Update jetzt herunterladen und installieren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                ok, msg = download_and_update_dlls(res.get("download_url"), res.get("latest_version"))
                if ok:
                    QMessageBox.information(self, "Update abgeschlossen", msg)
                    self._populate_swapper()
                else:
                    QMessageBox.critical(self, "Update fehlgeschlagen", msg)
        elif res.get("success"):
            QMessageBox.information(
                self,
                "Kein Update verfügbar",
                f"Sie verwenden bereits die neueste FSR 4 Version ({res['current_version']})."
            )
        else:
            QMessageBox.warning(
                self,
                "Update-Prüfung",
                f"Konnte GitHub Releases nicht abfragen:\n{res.get('error', 'Unbekannter Fehler')}"
            )

    def _create_global_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(18)

        # Global FSR 4 Card
        card_fsr4 = QFrame()
        card_fsr4.setStyleSheet("background-color: #171B23; border: 1px solid #9B59B6; border-radius: 8px; padding: 18px;")
        cf4_layout = QVBoxLayout(card_fsr4)

        f4_header = QHBoxLayout()
        lbl_f4_t = QLabel("AMD FSR 4 (AI NEURAL SUPER RESOLUTION) - GLOBALE INJEKTION")
        lbl_f4_t.setStyleSheet("font-size: 11px; font-weight: 900; color: #FFFFFF; letter-spacing: 1.5px;")
        
        badge_ai = QLabel("RDNA 3 / RDNA 4 WMMA AI")
        badge_ai.setStyleSheet("background-color: rgba(224, 30, 55, 0.15); border: 1px solid #E01E37; color: #FF4256; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 10px;")

        f4_header.addWidget(lbl_f4_t)
        f4_header.addStretch()
        f4_header.addWidget(badge_ai)
        cf4_layout.addLayout(f4_header)

        glob_prof = self.profile_mgr.get_profile("global")

        r_f4 = QHBoxLayout()
        r_f4.setContentsMargins(0, 8, 0, 8)
        v_f4 = QVBoxLayout()
        l1 = QLabel("FSR 4 KI-Upscaling standardmäßig für alle Spiele aktivieren")
        l1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l2 = QLabel("Nutzt die AI Matrix Cores (WMMA) der RX 7000 / RX 9000 Serie zur Rekonstruktion und DLSS-Übersetzung")
        l2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_f4.addWidget(l1)
        v_f4.addWidget(l2)
        sw_f4 = ToggleSwitch(checked=glob_prof.fsr4_enabled)
        sw_f4.toggled.connect(lambda c: self._set_glob("fsr4_enabled", c))
        r_f4.addLayout(v_f4)
        r_f4.addStretch()
        r_f4.addWidget(sw_f4)
        cf4_layout.addLayout(r_f4)

        # Global FSR 4 Frame Gen
        r_fg = QHBoxLayout()
        r_fg.setContentsMargins(0, 4, 0, 8)
        v_fg = QVBoxLayout()
        l_fg1 = QLabel("FSR 4 Fluid Motion Frames (AFMF 2 / AI Frame Generation)")
        l_fg1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_fg2 = QLabel("Generiert KI-Zwischenbilder für bis zu doppelte Bildraten mit optimierter Latenz")
        l_fg2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_fg.addWidget(l_fg1)
        v_fg.addWidget(l_fg2)
        sw_fg = ToggleSwitch(checked=glob_prof.fsr4_frame_gen)
        sw_fg.toggled.connect(lambda c: self._set_glob("fsr4_frame_gen", c))
        r_fg.addLayout(v_fg)
        r_fg.addStretch()
        r_fg.addWidget(sw_fg)
        cf4_layout.addLayout(r_fg)

        # Global FSR 4 Indicator
        r_ind = QHBoxLayout()
        r_ind.setContentsMargins(0, 4, 0, 8)
        v_ind = QVBoxLayout()
        l_ind1 = QLabel("FSR 4 Status-Indikator im Spiel anzeigen")
        l_ind1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_ind2 = QLabel("Blendet ein dezentes On-Screen-Wasserzeichen zur visuellen Bestätigung von KI-Upscaling und Frame Gen ein")
        l_ind2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_ind.addWidget(l_ind1)
        v_ind.addWidget(l_ind2)
        sw_ind = ToggleSwitch(checked=glob_prof.fsr4_indicator)
        sw_ind.toggled.connect(lambda c: self._set_glob("fsr4_indicator", c))
        r_ind.addLayout(v_ind)
        r_ind.addStretch()
        r_ind.addWidget(sw_ind)
        cf4_layout.addLayout(r_ind)

        layout.addWidget(card_fsr4)

        # Global FSR 4 DLL Updater Card
        card_dll = QFrame()
        card_dll.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        cdll_layout = QVBoxLayout(card_dll)
        cdll_layout.setSpacing(12)

        dll_head = QHBoxLayout()
        lbl_dll_t = QLabel("FSR 4 DLL-VERWALTUNG & ONLINE-UPDATES")
        lbl_dll_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #FFFFFF; letter-spacing: 1.5px;")
        
        cur_dll_ver = get_local_version()
        badge_dll = QLabel(f"Version: {cur_dll_ver}")
        badge_dll.setStyleSheet("background-color: rgba(46, 204, 113, 0.15); border: 1px solid #2ECC71; color: #2ECC71; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 10px;")

        dll_head.addWidget(lbl_dll_t)
        dll_head.addStretch()
        dll_head.addWidget(badge_dll)
        cdll_layout.addLayout(dll_head)

        lbl_dll_desc = QLabel(
            "Verwaltet die universellen DLL-Bibliotheken für neuronales FSR 4 KI-Upscaling und Frame Generation (OptiScaler & FidelityFX). "
            "Überprüft GitHub automatisch auf neue Releases und aktualisiert die lokalen Bibliotheken."
        )
        lbl_dll_desc.setStyleSheet("font-size: 11px; color: #A8B2C4; line-height: 1.4;")
        lbl_dll_desc.setWordWrap(True)
        cdll_layout.addWidget(lbl_dll_desc)

        dll_actions = QHBoxLayout()
        dll_actions.setSpacing(10)

        lbl_check_status = QLabel(f"Installierte DLLs: {cur_dll_ver} (Bereit zur Injektion)")
        lbl_check_status.setStyleSheet("color: #C5CFDC; font-size: 11px; font-weight: 600;")

        btn_check_update = QPushButton("🔄 Nach Updates suchen")
        btn_check_update.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)

        btn_dl_update = QPushButton("⬇️ Neueste FSR 4 DLLs herunterladen")
        btn_dl_update.setEnabled(False)
        btn_dl_update.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B31227);
                border: none;
                color: #FFFFFF;
                font-weight: bold;
                padding: 7px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #CC172F);
            }
            QPushButton:disabled {
                background: #1A1F29;
                border: 1px solid #28303F;
                color: #556272;
            }
        """)

        def _do_check():
            lbl_check_status.setText("Prüfe GitHub auf Updates...")
            QApplication.processEvents()
            res = check_for_dll_updates()
            if res.get("success"):
                if res.get("has_update"):
                    lbl_check_status.setText(f"Neues Update gefunden: {res['latest_version']} (Aktuell: {res['current_version']})")
                    lbl_check_status.setStyleSheet("color: #F39C12; font-weight: bold;")
                    btn_dl_update.setEnabled(True)
                    btn_dl_update.setText(f"⬇️ Update auf {res['latest_version']} herunterladen")
                else:
                    lbl_check_status.setText(f"✓ DLLs sind auf dem neuesten Stand ({res['current_version']})")
                    lbl_check_status.setStyleSheet("color: #2ECC71; font-weight: bold;")
                    btn_dl_update.setEnabled(False)
            else:
                lbl_check_status.setText(f"Konnte Updates nicht prüfen ({res.get('error', '')[:40]})")
                lbl_check_status.setStyleSheet("color: #E01E37;")

        def _do_download():
            lbl_check_status.setText("Lade neueste FSR 4 DLLs herunter...")
            btn_dl_update.setEnabled(False)
            QApplication.processEvents()
            ok, msg = download_and_update_dlls()
            lbl_check_status.setText(msg)
            lbl_check_status.setStyleSheet("color: #2ECC71; font-weight: bold;" if ok else "color: #E01E37; font-weight: bold;")
            if ok:
                badge_dll.setText(f"Version: {get_local_version()}")

        btn_check_update.clicked.connect(_do_check)
        btn_dl_update.clicked.connect(_do_download)

        dll_actions.addWidget(lbl_check_status)
        dll_actions.addStretch()
        dll_actions.addWidget(btn_check_update)
        dll_actions.addWidget(btn_dl_update)
        cdll_layout.addLayout(dll_actions)

        layout.addWidget(card_dll)

        # Global FPS Limiter Card
        card_fps = QFrame()
        card_fps.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        cfps_layout = QVBoxLayout(card_fps)

        lbl_fps_t = QLabel("FPS-BEGRENZER (RADEON CHILL / FRAME RATE TARGET CONTROL)")
        lbl_fps_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        cfps_layout.addWidget(lbl_fps_t)

        r_fps = QHBoxLayout()
        r_fps.setContentsMargins(0, 6, 0, 6)
        v_fps = QVBoxLayout()
        l_fps1 = QLabel("Globales FPS-Limit aktivieren")
        l_fps1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_fps2 = QLabel("Begrenzt die Bildrate zur Senkung der Leistungsaufnahme, Lüfterlautstärke und für perfekte Frametimes (DXVK, VKD3D & Gamescope)")
        l_fps2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_fps.addWidget(l_fps1)
        v_fps.addWidget(l_fps2)
        sw_fps = ToggleSwitch(checked=glob_prof.fps_limit_enabled)
        sw_fps.toggled.connect(lambda c: self._set_glob("fps_limit_enabled", c))
        r_fps.addLayout(v_fps)
        r_fps.addStretch()
        r_fps.addWidget(sw_fps)
        cfps_layout.addLayout(r_fps)

        sl_fps = StyledSlider("Maximale Bildrate", 30, 360, glob_prof.fps_limit, " FPS", step=1)
        sl_fps.valueChanged.connect(lambda v: self._set_glob("fps_limit", v))
        cfps_layout.addWidget(sl_fps)

        layout.addWidget(card_fps)

        # Global Profile Presets
        card_profile = QFrame()
        card_profile.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        cp_layout = QVBoxLayout(card_profile)

        lbl_t = QLabel("GRAFIK-PROFIL")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        cp_layout.addWidget(lbl_t)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(12)
        presets = [("GAMING", "Maximale Performance mit Anti-Lag"), ("ESPORTS", "Minimale Latenz & Framerate-Fokus"), ("POWER SAVING", "Optimiert für Energieeffizienz"), ("STANDARD", "Standard Radeon Einstellungen")]

        for title, desc in presets:
            btn = QPushButton(f"{title}\n{desc}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1A1F2A;
                    border: 1px solid #2B3444;
                    border-radius: 6px;
                    padding: 12px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: bold;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    border: 1px solid #E01E37;
                }
                QPushButton:checked {
                    border: 2px solid #E01E37;
                    background-color: rgba(224, 30, 55, 0.12);
                }
            """)
            if title == "GAMING":
                btn.setChecked(True)
            presets_row.addWidget(btn)

        cp_layout.addLayout(presets_row)
        layout.addWidget(card_profile)

        # Additional Features
        card_feat = QFrame()
        card_feat.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 16px;")
        cf_layout = QVBoxLayout(card_feat)

        lbl_ft = QLabel("WEITERE RADEON SYSTEM-FEATURES")
        lbl_ft.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        cf_layout.addWidget(lbl_ft)

        def _make_feat_row(name: str, desc: str, checked: bool, on_toggled):
            r = QHBoxLayout()
            r.setContentsMargins(0, 6, 0, 6)
            v = QVBoxLayout()
            l1 = QLabel(name)
            l1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
            l2 = QLabel(desc)
            l2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
            v.addWidget(l1)
            v.addWidget(l2)
            sw = ToggleSwitch(checked=checked)
            sw.toggled.connect(on_toggled)
            r.addLayout(v)
            r.addStretch()
            r.addWidget(sw)
            cf_layout.addLayout(r)

        _make_feat_row("Radeon Anti-Lag", "Reduziert die Eingabelatenz in Spielen dynamisch (Mesa Vulkan WSI Mailbox)", glob_prof.anti_lag, lambda c: self._set_glob("anti_lag", c))
        _make_feat_row("Radeon Boost (VRS)", "Variable Rate Shading zur Beschleunigung von schnellen Kamerabewegungen", glob_prof.radeon_boost, lambda c: self._set_glob("radeon_boost", c))
        # MangoHud Row with Configuration Button
        r_hud = QHBoxLayout()
        r_hud.setContentsMargins(0, 6, 0, 6)
        v_hud = QVBoxLayout()
        l_h1 = QLabel("MangoHud Overlay")
        l_h1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_h2 = QLabel("Hardware-Telemetrie direkt in Spielen anzeigen (FPS, Latenz, Temperaturen, Taktraten & VRAM)")
        l_h2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_hud.addWidget(l_h1)
        v_hud.addWidget(l_h2)
        r_hud.addLayout(v_hud)
        r_hud.addStretch()

        btn_cfg_hud = QPushButton("⚙ Overlay-Einstellungen")
        btn_cfg_hud.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cfg_hud.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E01E37;
                border-color: #FF2E47;
                color: #FFFFFF;
            }
        """)
        btn_cfg_hud.clicked.connect(self._open_mangohud_dialog)
        r_hud.addWidget(btn_cfg_hud)

        sw_hud = ToggleSwitch(checked=glob_prof.mangohud)
        sw_hud.toggled.connect(lambda c: self._set_glob("mangohud", c))
        r_hud.addWidget(sw_hud)
        cf_layout.addLayout(r_hud)

        layout.addWidget(card_feat)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _open_mangohud_dialog(self):
        dlg = MangoHudSettingsDialog(self)
        dlg.exec()

    def _set_glob(self, key: str, val):
        prof = self.profile_mgr.get_profile("global")
        setattr(prof, key, val)
        self.profile_mgr.save()

    def _create_detail_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.detail_content = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_content)
        self.detail_layout.setContentsMargins(10, 10, 10, 16)
        self.detail_layout.setSpacing(16)

        scroll.setWidget(self.detail_content)
        return scroll

    def _open_game_detail(self, target):
        if isinstance(target, str):
            app_id = target
            game = next((g for g in self.games if g.app_id == app_id), None)
        else:
            game = target
            app_id = game.app_id if game else None

        if not game:
            return

        self.active_game = game
        self.profile_mgr.register_game_directory(app_id, game.install_dir)
        prof = self.profile_mgr.get_profile(app_id)
        upscalers = detect_game_upscaler_support(game.install_dir)

        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Top Navigation / Breadcrumb
        top_nav = QHBoxLayout()
        btn_back = QPushButton("← Zurück zur Übersicht")
        btn_back.setProperty("class", "ghost-button")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self._switch_subtab(self.last_subtab))
        top_nav.addWidget(btn_back)
        top_nav.addStretch()
        self.detail_layout.addLayout(top_nav)

        # Hero Banner
        hero = QFrame()
        hero.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 20px;")
        h_layout = QHBoxLayout(hero)
        h_layout.setSpacing(20)

        lbl_p = QLabel()
        lbl_p.setFixedSize(140, 190)
        lbl_p.setStyleSheet("background-color: #0E1015; border-radius: 6px;")
        if game.poster_image and os.path.isfile(game.poster_image):
            pm = QPixmap(game.poster_image).scaled(140, 190, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            lbl_p.setPixmap(pm.copy(0, 0, 140, 190))
        h_layout.addWidget(lbl_p)

        info_col = QVBoxLayout()
        info_col.setSpacing(8)

        lbl_title = QLabel(game.name)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #FFFFFF;")

        lbl_dir = QLabel(f"Pfad: {game.install_dir or 'System'}")
        lbl_dir.setStyleSheet("font-size: 11px; color: #7E8D9F;")

        badges_row = QHBoxLayout()
        lbl_plat = QLabel(f"Plattform: {game.platform.upper()}")
        lbl_plat.setStyleSheet("font-size: 12px; color: #E01E37; font-weight: bold;")
        badges_row.addWidget(lbl_plat)

        if upscalers.get("has_dlss"):
            b_dlss = QLabel("DLSS Erkannt")
            b_dlss.setStyleSheet("background: #1B382B; color: #2ECC71; border: 1px solid #2ECC71; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            badges_row.addWidget(b_dlss)
        if upscalers.get("has_fsr"):
            b_fsr = QLabel("FSR Erkannt")
            b_fsr.setStyleSheet("background: #361E24; color: #FF4256; border: 1px solid #FF4256; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            badges_row.addWidget(b_fsr)
        badges_row.addStretch()

        btn_launch = QPushButton("▶  SPIEL JETZT STARTEN (MIT FSR 4)")
        btn_launch.setProperty("class", "primary-red")
        btn_launch.setFixedHeight(42)
        btn_launch.setFixedWidth(280)
        btn_launch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_launch.clicked.connect(lambda: self.play_game_requested.emit(game.app_id))

        info_col.addWidget(lbl_title)
        info_col.addLayout(badges_row)
        info_col.addWidget(lbl_dir)
        info_col.addStretch()
        info_col.addWidget(btn_launch)

        h_layout.addLayout(info_col)
        self.detail_layout.addWidget(hero)

        # ---------------- HYPR-RX PROFILE SELECTOR (ADRENALIN STYLE) ----------------
        profile_card = QFrame()
        profile_card.setStyleSheet("background-color: #141822; border: 1px solid #202838; border-radius: 8px; padding: 12px 16px;")
        pc_layout = QVBoxLayout(profile_card)
        pc_layout.setSpacing(10)

        pc_head = QHBoxLayout()
        lbl_pc_title = QLabel("GRAFIKPROFIL (HYPR-RX)")
        lbl_pc_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        lbl_pc_desc = QLabel("Wähle ein vordefiniertes Radeon-Leistungsprofil oder passe Einstellungen individuell an.")
        lbl_pc_desc.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        pc_head.addWidget(lbl_pc_title)
        pc_head.addSpacing(10)
        pc_head.addWidget(lbl_pc_desc)
        pc_head.addStretch()
        pc_layout.addLayout(pc_head)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)

        btn_prof_hypr = QPushButton("⚡ HYPR-RX")
        btn_prof_qual = QPushButton("💎 QUALITÄT")
        btn_prof_perf = QPushButton("🚀 LEISTUNG")
        btn_prof_custom = QPushButton("⚙ BENUTZERDEFINIERT")

        prof_group = QButtonGroup(self)
        prof_group.setExclusive(True)

        for idx, chip in enumerate([btn_prof_hypr, btn_prof_qual, btn_prof_perf, btn_prof_custom]):
            chip.setCheckable(True)
            chip.setProperty("class", "profile-chip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            prof_group.addButton(chip, idx)
            chips_row.addWidget(chip)
        chips_row.addStretch()
        pc_layout.addLayout(chips_row)

        btn_prof_custom.setChecked(True)
        self.detail_layout.addWidget(profile_card)

        # ---------------- FSR 4 LINK BANNER (SETTINGS MANAGED IN SWAPPER) ----------------
        swapper_banner = QFrame()
        swapper_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #181C26, stop:1 #11141B);
                border: 1px solid #28303F;
                border-left: 3px solid #E01E37;
                border-radius: 8px;
            }
        """)
        sb_layout = QHBoxLayout(swapper_banner)
        sb_layout.setContentsMargins(18, 14, 18, 14)
        sb_layout.setSpacing(16)

        sb_info = QVBoxLayout()
        sb_info.setSpacing(3)
        lbl_sb_t = QLabel("⚡ AMD FSR 4 NEURAL UPSCALER & DLSS SWAPPER")
        lbl_sb_t.setStyleSheet("font-size: 13px; font-weight: 800; color: #FFFFFF;")
        lbl_sb_d = QLabel("FSR 4 Einstellungen, Fluid Motion Frames (AFMF 2), Schärfegrad und DLL-Tausch werden zentral im FSR 4 Swapper verwaltet.")
        lbl_sb_d.setStyleSheet("font-size: 11px; color: #A8B2C4;")
        sb_info.addWidget(lbl_sb_t)
        sb_info.addWidget(lbl_sb_d)
        sb_layout.addLayout(sb_info, stretch=1)

        btn_go_swapper = QPushButton("⚡ Zum FSR 4 Swapper für dieses Spiel")
        btn_go_swapper.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_go_swapper.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E01E37, stop:1 #B31227);
                border: none;
                border-radius: 4px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF334B, stop:1 #CC172F);
            }
        """)
        btn_go_swapper.clicked.connect(lambda: self._jump_to_swapper_for_game(game.name))
        sb_layout.addWidget(btn_go_swapper)

        self.detail_layout.addWidget(swapper_banner)

        # ---------------- OTHER GRAPHICS SETTINGS ----------------
        sett_card = QFrame()
        sett_card.setStyleSheet("background-color: #171B23; border: 1px solid #28303F; border-radius: 8px; padding: 20px;")
        s_layout = QVBoxLayout(sett_card)
        s_layout.setSpacing(14)

        lbl_s_title = QLabel("WEITERE GRAFIK- UND LEISTUNGSEINSTELLUNGEN")
        lbl_s_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #E01E37; letter-spacing: 1.5px;")
        s_layout.addWidget(lbl_s_title)

        # FPS Limiter (Radeon Chill / FRTC)
        r_fps = QHBoxLayout()
        r_fps.setContentsMargins(0, 4, 0, 4)
        v_fps = QVBoxLayout()
        l_fps1 = QLabel("🎯 FPS-Begrenzer (Radeon Chill / FRTC)")
        l_fps1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_fps2 = QLabel("Begrenzt die maximale Bildrate zur Senkung der Leistungsaufnahme, Hitze und für perfekte Frametimes (DXVK, VKD3D & Gamescope)")
        l_fps2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_fps.addWidget(l_fps1)
        v_fps.addWidget(l_fps2)
        sw_fps = ToggleSwitch(checked=prof.fps_limit_enabled)
        sw_fps.toggled.connect(lambda c: self._update_prof(prof, "fps_limit_enabled", c))
        r_fps.addLayout(v_fps)
        r_fps.addStretch()
        r_fps.addWidget(sw_fps)
        s_layout.addLayout(r_fps)

        sl_fps = StyledSlider("Maximale Bildrate (FPS)", 30, 360, prof.fps_limit, " FPS", step=1)
        sl_fps.valueChanged.connect(lambda v: self._update_prof(prof, "fps_limit", v))
        s_layout.addWidget(sl_fps)

        def _add_setting_row(name: str, desc: str, checked: bool, on_toggled):
            r = QHBoxLayout()
            r.setContentsMargins(0, 4, 0, 4)
            v = QVBoxLayout()
            l1 = QLabel(name)
            l1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
            l2 = QLabel(desc)
            l2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
            v.addWidget(l1)
            v.addWidget(l2)
            sw = ToggleSwitch(checked=checked)
            sw.toggled.connect(on_toggled)
            r.addLayout(v)
            r.addStretch()
            r.addWidget(sw)
            s_layout.addLayout(r)

        # Anti-Lag Row
        r_al = QHBoxLayout()
        r_al.setContentsMargins(0, 4, 0, 4)
        v_al = QVBoxLayout()
        l_al1 = QLabel("⚡ Radeon Anti-Lag")
        l_al1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_al2 = QLabel("Optimiert die Render-Pipeline zur Minimierung von Eingabelatenz")
        l_al2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_al.addWidget(l_al1)
        v_al.addWidget(l_al2)
        sw_anti_lag = ToggleSwitch(checked=prof.anti_lag)
        sw_anti_lag.toggled.connect(lambda c: self._update_prof(prof, "anti_lag", c))
        r_al.addLayout(v_al)
        r_al.addStretch()
        r_al.addWidget(sw_anti_lag)
        s_layout.addLayout(r_al)

        # MangoHud Row with Configuration Button
        r_mgh = QHBoxLayout()
        r_mgh.setContentsMargins(0, 4, 0, 4)
        v_mgh = QVBoxLayout()
        l_m1 = QLabel("📊 MangoHud In-Game Overlay")
        l_m1.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        l_m2 = QLabel("Aktiviert das Telemetrie-Overlay beim Spielstart (FPS, Frametime, GPU/CPU Stats)")
        l_m2.setStyleSheet("font-size: 11px; color: #7E8D9F;")
        v_mgh.addWidget(l_m1)
        v_mgh.addWidget(l_m2)
        r_mgh.addLayout(v_mgh)
        r_mgh.addStretch()

        btn_game_hud = QPushButton("⚙ Overlay-Einstellungen")
        btn_game_hud.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_game_hud.setStyleSheet("""
            QPushButton {
                background-color: #1F242F;
                border: 1px solid #3A4456;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: #E01E37;
                color: #FFFFFF;
            }
        """)
        btn_game_hud.clicked.connect(self._open_mangohud_dialog)
        r_mgh.addWidget(btn_game_hud)

        sw_mgh = ToggleSwitch(checked=prof.mangohud)
        sw_mgh.toggled.connect(lambda c: self._update_prof(prof, "mangohud", c))
        r_mgh.addWidget(sw_mgh)
        s_layout.addLayout(r_mgh)

        def _apply_preset(mode: str):
            if mode == "hypr":
                sw_anti_lag.setChecked(True)
                sw_fps.setChecked(True)
                sl_fps.setValue(144)
                sw_mgh.setChecked(True)
            elif mode == "qual":
                sw_anti_lag.setChecked(True)
                sw_fps.setChecked(False)
                sw_mgh.setChecked(False)
            elif mode == "perf":
                sw_anti_lag.setChecked(True)
                sw_fps.setChecked(True)
                sl_fps.setValue(120)
                sw_mgh.setChecked(True)

        btn_prof_hypr.clicked.connect(lambda: _apply_preset("hypr"))
        btn_prof_qual.clicked.connect(lambda: _apply_preset("qual"))
        btn_prof_perf.clicked.connect(lambda: _apply_preset("perf"))

        _add_setting_row("Gamescope Wrapper", "Isolierter Wayland Micro-Compositor mit FSR & Upscaling", prof.gamescope, lambda c: self._update_prof(prof, "gamescope", c))

        ppm_row = QHBoxLayout()
        ppm_lbl = QLabel("GPU DPM Power Profile:")
        ppm_lbl.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        ppm_combo = QComboBox()
        ppm_combo.addItems(["3D_FULL_SCREEN", "BOOTUP_DEFAULT", "COMPUTE", "VR", "POWER_SAVING"])
        ppm_combo.setCurrentText(prof.power_profile)
        ppm_combo.currentTextChanged.connect(lambda t: self._update_prof(prof, "power_profile", t))
        ppm_row.addWidget(ppm_lbl)
        ppm_row.addStretch()
        ppm_row.addWidget(ppm_combo)
        s_layout.addLayout(ppm_row)

        self.detail_layout.addWidget(sett_card)
        self.detail_layout.addStretch()

        self.stack.setCurrentIndex(3)

    def _jump_to_swapper_for_game(self, game_name: str):
        self._switch_subtab(1)
        self.search_box.setText(game_name)

    def _update_prof(self, prof: GameGraphicProfile, attr: str, val):
        setattr(prof, attr, val)
        if self.active_game and self.active_game.app_id == prof.app_id:
            self.profile_mgr.register_game_directory(prof.app_id, self.active_game.install_dir)
        self.profile_mgr.save()

