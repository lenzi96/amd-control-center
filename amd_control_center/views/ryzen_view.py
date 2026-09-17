"""AMD Ryzen Master View for AMD Control Center."""

from typing import Dict, Any, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QComboBox, QMessageBox,
    QProgressBar, QStackedWidget
)
from PyQt6.QtGui import QColor, QFont

from ..backend.cpu_detector import CpuDevice, detect_cpu
from ..backend.cpu_tuner import (
    CpuTuningProfile, PRESET_PROFILES,
    apply_cpu_tuning_direct, execute_cpu_tuner_pkexec,
    apply_curve_optimizer, load_co_cache, has_ryzen_smu
)
from ..widgets.metric_card import MetricCard
from ..widgets.styled_slider import StyledSlider
from ..widgets.toggle_switch import ToggleSwitch
from ..widgets.cpu_chart import CpuChartWidget
from ..styles import AdrenalinColors


class CoreCard(QFrame):
    """Card displaying a single physical CPU core, its CPPC star rank or P/E type, clock, power, and load."""
    def __init__(self, core_id: int, is_gold: bool = False, is_silver: bool = False, cppc_rank: int = 0, core_type: str = "standard", parent=None):
        super().__init__(parent)
        self.core_id = core_id
        self.is_gold = is_gold
        self.is_silver = is_silver
        self.cppc_rank = cppc_rank
        self.core_type = core_type

        self.setProperty("class", "adrenalin-card")
        
        # Determine border color based on CPPC star ranking or core type
        if is_gold:
            border_css = "border: 1px solid #FFD700; background-color: #1A1812;"
        elif is_silver:
            border_css = "border: 1px solid #B0B8C4; background-color: #161A22;"
        elif core_type == "p-core":
            border_css = "border: 1px solid #1E3A5F; background-color: #111824;"
        elif core_type == "e-core":
            border_css = "border: 1px solid #1B3D2B; background-color: #101B18;"
        else:
            border_css = "border: 1px solid #222938; background-color: #141822;"

        self.setStyleSheet(f"""
            CoreCard {{
                {border_css}
                border-radius: 8px;
                padding: 4px;
            }}
            CoreCard:hover {{
                border: 1px solid #FF5500;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Core Name & Star / Core-Type Badge
        hdr_row = QHBoxLayout()
        self.lbl_title = QLabel(f"CORE {core_id + 1:02d}")
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #8E9BAE; letter-spacing: 1px;")
        hdr_row.addWidget(self.lbl_title)

        hdr_row.addStretch()

        if is_gold:
            lbl_star = QLabel("⭐ GOLD")
            lbl_star.setStyleSheet("font-size: 10px; font-weight: 900; color: #FFD700; background-color: #382F05; padding: 2px 6px; border-radius: 4px;")
            hdr_row.addWidget(lbl_star)
        elif is_silver:
            lbl_star = QLabel("🥈 SILBER")
            lbl_star.setStyleSheet("font-size: 10px; font-weight: 900; color: #D0D8E4; background-color: #262E3B; padding: 2px 6px; border-radius: 4px;")
            hdr_row.addWidget(lbl_star)
        elif core_type == "p-core":
            lbl_type = QLabel("⚡ P-CORE")
            lbl_type.setStyleSheet("font-size: 10px; font-weight: 900; color: #00D2FF; background-color: #0E2945; padding: 2px 6px; border-radius: 4px;")
            hdr_row.addWidget(lbl_type)
        elif core_type == "e-core":
            lbl_type = QLabel("🌱 E-CORE")
            lbl_type.setStyleSheet("font-size: 10px; font-weight: 900; color: #00E676; background-color: #0E2E1E; padding: 2px 6px; border-radius: 4px;")
            hdr_row.addWidget(lbl_type)
        elif cppc_rank > 0:
            lbl_rank = QLabel(f"#{cppc_rank}")
            lbl_rank.setStyleSheet("font-size: 9px; font-weight: 700; color: #5B6A80;")
            hdr_row.addWidget(lbl_rank)

        layout.addLayout(hdr_row)

        # Main Clock display
        clk_row = QHBoxLayout()
        clk_row.setSpacing(4)
        self.lbl_clock = QLabel("--")
        self.lbl_clock.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF;")
        lbl_mhz = QLabel("MHz")
        lbl_mhz.setStyleSheet("font-size: 11px; font-weight: 700; color: #FF5500; margin-bottom: 3px;")
        clk_row.addWidget(self.lbl_clock)
        clk_row.addWidget(lbl_mhz, alignment=Qt.AlignmentFlag.AlignBottom)
        clk_row.addStretch()

        # Core Power (W)
        self.lbl_power = QLabel("-- W")
        self.lbl_power.setStyleSheet("font-size: 11px; font-weight: 800; color: #00E676; margin-bottom: 3px;")
        clk_row.addWidget(self.lbl_power, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(clk_row)

        # Progress bar for utilization
        self.prog_usage = QProgressBar()
        self.prog_usage.setRange(0, 100)
        self.prog_usage.setValue(0)
        self.prog_usage.setTextVisible(False)
        self.prog_usage.setFixedHeight(4)
        self.prog_usage.setStyleSheet("""
            QProgressBar {
                background-color: #0E1118;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #FF5500;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.prog_usage)

        # Bottom sub text: Usage % and Status
        bot_row = QHBoxLayout()
        self.lbl_usage = QLabel("0.0% Last")
        self.lbl_usage.setStyleSheet("font-size: 10px; font-weight: 600; color: #727F93;")
        self.lbl_status = QLabel("Aktiv")
        self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #00E676;")
        bot_row.addWidget(self.lbl_usage)
        bot_row.addStretch()
        bot_row.addWidget(self.lbl_status)
        layout.addLayout(bot_row)

    def update_metrics(self, freq_mhz: float, power_w: float, usage_pct: float, online: bool = True):
        self.lbl_clock.setText(f"{int(freq_mhz)}" if freq_mhz > 0 else "--")
        self.lbl_power.setText(f"{power_w:.1f} W" if power_w > 0 else "<0.1 W")
        self.prog_usage.setValue(int(min(100, max(0, usage_pct))))
        self.lbl_usage.setText(f"{usage_pct:.1f}%")

        if not online:
            self.lbl_status.setText("Geparkt")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #8A96A6;")
            self.lbl_clock.setStyleSheet("font-size: 20px; font-weight: 900; color: #5D6D82;")
        else:
            self.lbl_status.setText("Aktiv")
            self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #00E676;")
            self.lbl_clock.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF;")


class RyzenMasterView(QWidget):
    """Full Ryzen Master view integrated into AMD Control Center."""

    def __init__(self, cpu: Optional[CpuDevice] = None, parent=None):
        super().__init__(parent)
        self.cpu = cpu or detect_cpu()
        self.current_profile = PRESET_PROFILES["Balanced"]

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        # 1. Hero Header Banner
        header = self._create_header_banner()
        layout.addWidget(header)

        # 2. KPI Metrics Grid (5 Metric Cards)
        kpi_grid = self._create_metrics_grid()
        layout.addLayout(kpi_grid)

        # 3. Active Cores Matrix (CPPC Preferred Cores)
        cores_section = self._create_cores_section()
        layout.addWidget(cores_section)

        # 4. Tuning & Profiles Section
        tuning_section = self._create_tuning_section()
        layout.addWidget(tuning_section)

        # 5. Curve Optimizer (PBO Undervolting) Section
        co_section = self._create_curve_optimizer_section()
        layout.addWidget(co_section)

        # 6. Realtime Telemetry Graph
        chart_section = self._create_chart_section()
        layout.addWidget(chart_section)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _create_header_banner(self) -> QFrame:
        banner = QFrame()
        banner.setProperty("class", "adrenalin-card")
        
        accent_color = "#FF5500" if self.cpu.is_amd else "#0099FF"
        grad_start = "#1E1614" if self.cpu.is_amd else "#101926"
        border_color = "#33221C" if self.cpu.is_amd else "#1B2A40"

        banner.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {grad_start}, stop:0.5 #161A24, stop:1 #11141B);
                border: 1px solid {border_color};
                border-left: 4px solid {accent_color};
                border-radius: 8px;
                padding: 16px 20px;
            }}
        """)
        h_layout = QHBoxLayout(banner)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(18)

        # Left Info
        left_v = QVBoxLayout()
        left_v.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        
        if self.cpu.is_amd:
            brand_name = "AMD RYZEN™ MASTER"
        elif self.cpu.is_intel:
            brand_name = "INTEL® CORE™ PERFORMANCE"
        else:
            brand_name = f"{self.cpu.vendor.upper()} CPU PERFORMANCE"

        lbl_brand = QLabel(brand_name)
        lbl_brand.setStyleSheet(f"font-size: 13px; font-weight: 900; color: {accent_color}; letter-spacing: 2px;")
        
        lbl_edition = QLabel("[LINUX EDITION]")
        lbl_edition.setStyleSheet("font-size: 11px; font-weight: 800; color: #8A96A6;")
        
        title_row.addWidget(lbl_brand)
        title_row.addWidget(lbl_edition)
        title_row.addStretch()
        left_v.addLayout(title_row)

        lbl_cpu = QLabel(self.cpu.model_name)
        lbl_cpu.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF;")
        left_v.addWidget(lbl_cpu)

        # Badges Row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)

        # Core topology badge
        if self.cpu.is_hybrid:
            core_badge_text = f"🧮 {self.cpu.p_core_count}P + {self.cpu.e_core_count}E ({self.cpu.physical_cores}C / {self.cpu.logical_threads}T)"
        else:
            core_badge_text = f"🧮 {self.cpu.physical_cores}C / {self.cpu.logical_threads}T"

        l3_text = f"💾 L3 Cache: {self.cpu.cache_l3_kb // 1024} MB"
        if self.cpu.has_3d_vcache:
            l3_text += " (3D V-Cache)"

        badges = [
            (f"⚡ {self.cpu.architecture}", accent_color),
        ]
        if self.cpu.socket and self.cpu.socket != "Unknown":
            badges.append((f"📌 Socket {self.cpu.socket}", "#00D2FF"))
        badges.extend([
            (core_badge_text, "#C8D1DC"),
            (l3_text, "#00E676" if self.cpu.has_3d_vcache else "#C8D1DC"),
            (f"⚙️ {self.cpu.scaling_driver}", "#A0AEC0"),
        ])

        for text, col in badges:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: #0E121A;
                    border: 1px solid #232B3B;
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 700;
                    color: {col};
                }}
            """)
            badge_row.addWidget(lbl)

        badge_row.addStretch()
        left_v.addLayout(badge_row)
        h_layout.addLayout(left_v, stretch=3)

        # Right Summary Pill
        right_f = QFrame()
        right_f.setStyleSheet("background-color: #12151D; border: 1px solid #202737; border-radius: 8px; padding: 12px;")
        rf_layout = QVBoxLayout(right_f)
        rf_layout.setContentsMargins(10, 6, 10, 6)
        rf_layout.setSpacing(4)

        if self.cpu.is_amd:
            lbl_status_title = QLabel("PRECISION BOOST")
            lbl_status_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93;")
            self.lbl_boost_status = QLabel("● Aktiviert (Auto-Boost)" if self.cpu.boost_enabled else "○ Deaktiviert")
            self.lbl_boost_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #00E676;" if self.cpu.boost_enabled else "font-size: 12px; font-weight: 800; color: #F39C12;")

            lbl_cppc_title = QLabel("CPPC PREFERRED CORES")
            lbl_cppc_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93; margin-top: 4px;")
            gold_text = f"⭐ Kern {self.cpu.gold_core_id + 1}" if self.cpu.gold_core_id >= 0 else "N/A"
            silver_text = f"🥈 Kern {self.cpu.silver_core_id + 1}" if self.cpu.silver_core_id >= 0 else "N/A"
            self.lbl_cppc_status = QLabel(f"{gold_text} • {silver_text}")
            self.lbl_cppc_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #FFD700;")
        elif self.cpu.is_hybrid:
            lbl_status_title = QLabel("INTEL TURBO BOOST")
            lbl_status_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93;")
            self.lbl_boost_status = QLabel("● Aktiviert (Turbo Max 3.0)" if self.cpu.boost_enabled else "○ Deaktiviert")
            self.lbl_boost_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #00E676;" if self.cpu.boost_enabled else "font-size: 12px; font-weight: 800; color: #F39C12;")

            lbl_cppc_title = QLabel("THREAD DIRECTOR HYBRID")
            lbl_cppc_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93; margin-top: 4px;")
            self.lbl_cppc_status = QLabel(f"⚡ {self.cpu.p_core_count} P-Cores • 🌱 {self.cpu.e_core_count} E-Cores")
            self.lbl_cppc_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #00D2FF;")
        else:
            lbl_status_title = QLabel("CPU BOOST FREQUENCY")
            lbl_status_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93;")
            self.lbl_boost_status = QLabel("● Aktiviert" if self.cpu.boost_enabled else "○ Deaktiviert")
            self.lbl_boost_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #00E676;" if self.cpu.boost_enabled else "font-size: 12px; font-weight: 800; color: #F39C12;")

            lbl_cppc_title = QLabel("CPU ARCHITEKTUR")
            lbl_cppc_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #727F93; margin-top: 4px;")
            self.lbl_cppc_status = QLabel(f"{self.cpu.architecture}")
            self.lbl_cppc_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #C8D1DC;")

        rf_layout.addWidget(lbl_status_title)
        rf_layout.addWidget(self.lbl_boost_status)
        rf_layout.addWidget(lbl_cppc_title)
        rf_layout.addWidget(self.lbl_cppc_status)

        h_layout.addWidget(right_f, stretch=1)
        return banner

    def _create_metrics_grid(self) -> QHBoxLayout:
        grid = QHBoxLayout()
        grid.setSpacing(14)

        # 1. Temperature Card
        self.card_temp = MetricCard("CPU Temperatur", unit="°C", max_val=95.0)
        self.card_temp.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F39C12, stop:1 #FF5500); border-radius: 2px; }
        """)
        grid.addWidget(self.card_temp)

        # 2. Package Power (PPT / RAPL)
        power_title = "Package Power (PPT)" if self.cpu.is_amd else "Package Power (RAPL)"
        self.card_power = MetricCard(power_title, unit="W", max_val=150.0)
        self.card_power.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00B0FF, stop:1 #00E676); border-radius: 2px; }
        """)
        grid.addWidget(self.card_power)

        # 3. Peak Core Speed
        self.card_clock = MetricCard("Peak Takt", unit="MHz", max_val=self.cpu.boost_clock_mhz + 200.0)
        self.card_clock.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7928CA, stop:1 #FF0080); border-radius: 2px; }
        """)
        grid.addWidget(self.card_clock)

        # 4. CPU Auslastung
        self.card_usage = MetricCard("CPU Auslastung", unit="%", max_val=100.0)
        grid.addWidget(self.card_usage)

        # 5. Memory / DDR5 Temps
        self.card_ram = MetricCard("DDR5 Speicher", unit="°C", max_val=85.0)
        self.card_ram.progress.setStyleSheet("""
            QProgressBar { background-color: #10131A; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #008080, stop:1 #00D2FF); border-radius: 2px; }
        """)
        grid.addWidget(self.card_ram)

        return grid

    def _create_cores_section(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "adrenalin-card")
        panel.setStyleSheet("""
            QFrame {
                background-color: #131720;
                border: 1px solid #1E2534;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header with legend
        top_h = QHBoxLayout()
        lbl_sec = QLabel("ACTIVE CORES & TOPOLOGY")
        lbl_sec.setStyleSheet("font-size: 13px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        top_h.addWidget(lbl_sec)

        top_h.addStretch()

        if self.cpu.is_hybrid:
            legend_p = QLabel("⚡ P-Core (Performance)")
            legend_p.setStyleSheet("font-size: 11px; font-weight: 700; color: #00D2FF;")
            top_h.addWidget(legend_p)

            top_h.addSpacing(12)

            legend_e = QLabel("🌱 E-Core (Efficient)")
            legend_e.setStyleSheet("font-size: 11px; font-weight: 700; color: #00E676;")
            top_h.addWidget(legend_e)
        elif self.cpu.is_amd:
            legend_gold = QLabel("⭐ Bester Kern (Höchster Boost)")
            legend_gold.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFD700;")
            top_h.addWidget(legend_gold)

            top_h.addSpacing(12)

            legend_silver = QLabel("🥈 Zweitbester Kern")
            legend_silver.setStyleSheet("font-size: 11px; font-weight: 700; color: #C0C8D8;")
            top_h.addWidget(legend_silver)

        layout.addLayout(top_h)

        # Cores Grid (4 columns or 8 columns depending on core count)
        cols = 4 if self.cpu.physical_cores >= 8 else max(1, self.cpu.physical_cores)
        grid = QGridLayout()
        grid.setSpacing(10)

        self.core_cards: Dict[int, CoreCard] = {}
        for idx, c in enumerate(self.cpu.cores):
            row = idx // cols
            col = idx % cols
            card = CoreCard(
                core_id=c.core_id,
                is_gold=c.is_gold_star,
                is_silver=c.is_silver_star,
                cppc_rank=c.cppc_rank,
                core_type=c.core_type,
                parent=panel
            )
            grid.addWidget(card, row, col)
            self.core_cards[c.core_id] = card

        layout.addLayout(grid)
        return panel

    def _create_tuning_section(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "adrenalin-card")
        panel.setStyleSheet("""
            QFrame {
                background-color: #131720;
                border: 1px solid #1E2534;
                border-radius: 8px;
                padding: 18px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        # Section Title
        lbl_t = QLabel("TUNING & PROFILES")
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        layout.addWidget(lbl_t)

        # Preset Quick Switch Buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(12)

        self.btn_presets = {}
        presets = [
            ("🎮 Gaming Boost", "Gaming Boost"),
            ("⚖️ Balanced", "Balanced"),
            ("🌱 Eco Mode", "Eco Mode"),
            ("🎯 Pure Cores (SMT Aus)", "Pure Cores (SMT Aus)"),
        ]

        for label, p_key in presets:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #171C26;
                    border: 1px solid #252D3D;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 700;
                    color: #C8D1DC;
                }
                QPushButton:hover {
                    background-color: #202736;
                    border: 1px solid #FF5500;
                    color: #FFFFFF;
                }
                QPushButton:checked {
                    background-color: #B83B00;
                    border: 1px solid #FF5500;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(lambda _, k=p_key: self._on_preset_clicked(k))
            preset_row.addWidget(btn)
            self.btn_presets[p_key] = btn

        self.btn_presets["Balanced"].setChecked(True)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1F2736; background-color: #1F2736;")
        layout.addWidget(sep)

        # Controls Grid
        controls_layout = QGridLayout()
        controls_layout.setSpacing(16)

        # 1. EPP Preference
        lbl_epp = QLabel("Energy-Performance-Preference (EPP)")
        lbl_epp.setStyleSheet("font-weight: 700; color: #E1E7EE;")
        self.combo_epp = QComboBox()
        epp_opts = ["performance", "balance_performance", "balance_power", "power"]
        for opt in epp_opts:
            self.combo_epp.addItem(opt.replace("_", " ").title(), opt)
        self.combo_epp.setCurrentIndex(1) # balance_performance
        self.combo_epp.setStyleSheet("""
            QComboBox {
                background-color: #161A22;
                border: 1px solid #262E3E;
                border-radius: 4px;
                padding: 6px 12px;
                color: #FFFFFF;
                font-weight: bold;
                min-width: 180px;
            }
            QComboBox QAbstractItemView {
                background-color: #161A22;
                color: #FFFFFF;
                selection-background-color: #FF5500;
            }
        """)
        controls_layout.addWidget(lbl_epp, 0, 0)
        controls_layout.addWidget(self.combo_epp, 0, 1)

        # 2. Scaling Governor
        lbl_gov = QLabel("CPU Scaling Governor")
        lbl_gov.setStyleSheet("font-weight: 700; color: #E1E7EE;")
        self.combo_gov = QComboBox()
        gov_opts = self.cpu.available_governors or ["powersave", "performance"]
        for g in gov_opts:
            self.combo_gov.addItem(g.capitalize(), g)
        self.combo_gov.setStyleSheet("""
            QComboBox {
                background-color: #161A22;
                border: 1px solid #262E3E;
                border-radius: 4px;
                padding: 6px 12px;
                color: #FFFFFF;
                font-weight: bold;
                min-width: 180px;
            }
            QComboBox QAbstractItemView {
                background-color: #161A22;
                color: #FFFFFF;
                selection-background-color: #FF5500;
            }
        """)
        controls_layout.addWidget(lbl_gov, 1, 0)
        controls_layout.addWidget(self.combo_gov, 1, 1)

        # 3. Precision / Turbo Boost Switch
        boost_title = "Precision Boost (AMD Core Performance Boost)" if self.cpu.is_amd else ("Intel Turbo Boost" if self.cpu.is_intel else "CPU Turbo Boost")
        lbl_boost = QLabel(boost_title)
        lbl_boost.setStyleSheet("font-weight: 700; color: #E1E7EE;")
        self.sw_boost = ToggleSwitch(checked=self.cpu.boost_enabled)
        controls_layout.addWidget(lbl_boost, 0, 2)
        controls_layout.addWidget(self.sw_boost, 0, 3)

        # 4. SMT / Hyper-Threading Switch
        if self.cpu.is_amd:
            smt_title = f"SMT (Simultaneous Multithreading / {self.cpu.logical_threads} Threads)"
        elif self.cpu.is_intel:
            smt_title = f"Hyper-Threading (Intel HT / {self.cpu.logical_threads} Threads)"
        else:
            smt_title = f"Multithreading ({self.cpu.logical_threads} Threads)"
        lbl_smt = QLabel(smt_title)
        lbl_smt.setStyleSheet("font-weight: 700; color: #E1E7EE;")
        self.sw_smt = ToggleSwitch(checked=self.cpu.smt_active)
        controls_layout.addWidget(lbl_smt, 1, 2)
        controls_layout.addWidget(self.sw_smt, 1, 3)

        layout.addLayout(controls_layout)

        # Frequency Slider
        max_boost = int(self.cpu.boost_clock_mhz + 200)
        self.slider_max_freq = StyledSlider(
            title="Maximaler CPU Takt (Scaling Max Frequency)",
            min_val=2000,
            max_val=max_boost,
            current_val=int(self.cpu.boost_clock_mhz),
            unit="MHz",
            step=50
        )
        layout.addWidget(self.slider_max_freq)

        # Actions Row
        act_row = QHBoxLayout()
        act_row.setSpacing(12)

        self.lbl_status_msg = QLabel("")
        self.lbl_status_msg.setStyleSheet("font-weight: 700; font-size: 12px;")
        act_row.addWidget(self.lbl_status_msg)

        act_row.addStretch()

        self.btn_reset = QPushButton("Standard Wiederherstellen")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #181C26;
                border: 1px solid #283244;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                color: #C8D1DC;
            }
            QPushButton:hover {
                background-color: #242B3A;
                color: #FFFFFF;
            }
        """)
        self.btn_reset.clicked.connect(self._reset_to_defaults)
        act_row.addWidget(self.btn_reset)

        self.btn_apply = QPushButton("Profil Übernehmen")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D83B00, stop:1 #FF5500);
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 800;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5500, stop:1 #FF7722);
            }
        """)
        self.btn_apply.clicked.connect(self._apply_current_tuning)
        act_row.addWidget(self.btn_apply)

        layout.addLayout(act_row)
        return panel

    def _co_tab_style(self) -> str:
        return """
            QPushButton {
                background-color: #171C26;
                border: 1px solid #252D3D;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
                color: #C8D1DC;
            }
            QPushButton:hover {
                background-color: #202736;
                border: 1px solid #FF5500;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #B83B00;
                border: 1px solid #FF5500;
                color: #FFFFFF;
            }
        """

    def _create_curve_optimizer_section(self) -> QFrame:
        if not self.cpu.is_amd:
            # Informational card for non-AMD (Intel / generic) CPUs
            panel = QFrame()
            panel.setProperty("class", "adrenalin-card")
            panel.setStyleSheet("""
                QFrame {
                    background-color: #131720;
                    border: 1px solid #1E2534;
                    border-left: 4px solid #0099FF;
                    border-radius: 8px;
                    padding: 16px;
                }
            """)
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(10)

            hdr = QHBoxLayout()
            lbl_title = QLabel("⚡ CURVE OPTIMIZER (AMD RYZEN™ EXKLUSIV)")
            lbl_title.setStyleSheet("font-size: 13px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
            hdr.addWidget(lbl_title)
            hdr.addStretch()

            lbl_badge = QLabel("○ Nicht verfügbar für " + ("Intel CPUs" if self.cpu.is_intel else "diese CPU"))
            lbl_badge.setStyleSheet("font-size: 11px; font-weight: 800; color: #8A96A6; background-color: #161A22; border: 1px solid #283244; border-radius: 10px; padding: 2px 10px;")
            hdr.addWidget(lbl_badge)
            layout.addLayout(hdr)

            lbl_desc = QLabel(
                "Curve Optimizer (Precision Boost Overdrive Undervolting) ist ein exklusives Hardware-Feature von AMD Ryzen Prozessoren (Zen 3, Zen 4, Zen 5) über die AMD SMU.<br><br>"
                "Auf Intel-Prozessoren erfolgt Spannungsanpassung / Undervolting über das Intel MSR 0x150 Interface (z. B. via <code>intel-undervolt</code> oder Intel XTU / BIOS). "
                "Taktraten, CPU Scaling Governor und Energy-Performance-Preference (EPP) können oben für alle Kerne frei konfiguriert werden."
            )
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #8C9CAE; font-size: 11px; line-height: 1.5;")
            layout.addWidget(lbl_desc)

            # Keep dummy references so callbacks and preset switching don't throw AttributeError
            self.slider_all_co = None
            self.per_core_sliders = {}
            self.btn_co_all = None
            self.btn_co_per = None
            self.chips_widget = None
            self.co_stack = None
            self.lbl_co_status = QLabel("")
            return panel

        panel = QFrame()
        panel.setProperty("class", "adrenalin-card")
        panel.setStyleSheet("""
            QFrame {
                background-color: #131720;
                border: 1px solid #1E2534;
                border-left: 4px solid #FF5500;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # Header Row
        hdr = QHBoxLayout()
        lbl_title = QLabel("⚡ CURVE OPTIMIZER (PBO & UNDERVOLTING)")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        hdr.addWidget(lbl_title)

        hdr.addStretch()

        # Driver status badge
        if self.cpu.has_ryzen_smu:
            self.lbl_drv = QLabel("● ryzen_smu SMU-Treiber aktiv")
            self.lbl_drv.setStyleSheet("font-size: 11px; font-weight: 800; color: #00E676; background-color: #0E1A14; border: 1px solid #1B4D2E; border-radius: 10px; padding: 2px 10px;")
        else:
            self.lbl_drv = QLabel("○ ryzen_smu Treiber nicht geladen (Profil-Cache aktiv)")
            self.lbl_drv.setStyleSheet("font-size: 11px; font-weight: 800; color: #F39C12; background-color: #1A160E; border: 1px solid #4D3D1B; border-radius: 10px; padding: 2px 10px;")
            self.lbl_drv.setToolTip("Für Live-Übernahme zur Laufzeit: yay -S ryzen_smu-dkms-git && sudo modprobe ryzen_smu")
        hdr.addWidget(self.lbl_drv)
        layout.addLayout(hdr)

        # Info text
        lbl_info = QLabel("Curve Optimizer passt die V/F-Spannungskurve an. Negative Counts (Undervolting) senken Temperatur & Verbrauch, sodass die Kerne länger ihren Maximaltakt halten können (1 Count ≈ 3–5 mV).")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #8C9CAE; font-size: 11px; line-height: 1.4;")
        layout.addWidget(lbl_info)

        # Mode Selection: All-Core vs Per-Core
        mode_box = QHBoxLayout()
        mode_box.setSpacing(10)
        lbl_m = QLabel("Modus:")
        lbl_m.setStyleSheet("font-weight: 700; color: #C8D1DC;")
        mode_box.addWidget(lbl_m)

        self.btn_co_all = QPushButton("All-Core (Gleichmäßig)")
        self.btn_co_all.setCheckable(True)
        self.btn_co_all.setChecked(True)
        self.btn_co_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_co_all.setStyleSheet(self._co_tab_style())

        self.btn_co_per = QPushButton("Per-Core (Individuell)")
        self.btn_co_per.setCheckable(True)
        self.btn_co_per.setChecked(False)
        self.btn_co_per.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_co_per.setStyleSheet(self._co_tab_style())

        self.btn_co_all.clicked.connect(lambda: self._set_co_mode("All-Core"))
        self.btn_co_per.clicked.connect(lambda: self._set_co_mode("Per-Core"))

        mode_box.addWidget(self.btn_co_all)
        mode_box.addWidget(self.btn_co_per)
        mode_box.addSpacing(14)

        # Quick chips for All-Core
        self.chips_widget = QWidget()
        chips_layout = QHBoxLayout(self.chips_widget)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)

        lbl_quick = QLabel("Schnellwahl:")
        lbl_quick.setStyleSheet("font-size: 11px; color: #727F93;")
        chips_layout.addWidget(lbl_quick)

        chips = [("0 (Stock)", 0), ("-10 (Leicht)", -10), ("-20 (Empfohlen)", -20), ("-30 (Max)", -30)]
        for c_lbl, c_val in chips:
            btn_c = QPushButton(c_lbl)
            btn_c.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_c.setStyleSheet("""
                QPushButton {
                    background-color: #161A24;
                    border: 1px solid #283244;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: 700;
                    color: #C8D1DC;
                }
                QPushButton:hover {
                    border-color: #FF5500;
                    color: #FFFFFF;
                }
            """)
            btn_c.clicked.connect(lambda _, v=c_val: self.slider_all_co.spin.setValue(v))
            chips_layout.addWidget(btn_c)

        mode_box.addWidget(self.chips_widget)
        mode_box.addStretch()
        layout.addLayout(mode_box)

        # Container for All-Core vs Per-Core (QStackedWidget)
        self.co_stack = QStackedWidget()

        # Page 0: All-Core Slider
        all_page = QWidget()
        all_layout = QVBoxLayout(all_page)
        all_layout.setContentsMargins(0, 4, 0, 0)

        self.slider_all_co = StyledSlider(
            title="All-Core Curve Optimizer Offset",
            min_val=-30,
            max_val=10,
            current_val=-20,
            unit="Counts",
            step=1
        )
        all_layout.addWidget(self.slider_all_co)
        self.co_stack.addWidget(all_page)

        # Page 1: Per-Core Grid
        per_page = QWidget()
        per_layout = QGridLayout(per_page)
        per_layout.setContentsMargins(0, 4, 0, 0)
        per_layout.setSpacing(12)

        self.per_core_sliders: Dict[int, StyledSlider] = {}
        for idx, c in enumerate(self.cpu.cores):
            star_label = ""
            if c.is_gold_star:
                star_label = " (⭐ Gold)"
            elif c.is_silver_star:
                star_label = " (🥈 Silber)"

            def_val = -15 if (c.is_gold_star or c.is_silver_star) else -20
            sl = StyledSlider(
                title=f"Core {c.core_id + 1:02d}{star_label}",
                min_val=-30,
                max_val=10,
                current_val=def_val,
                unit="Counts",
                step=1
            )
            r = idx // 2
            col = idx % 2
            per_layout.addWidget(sl, r, col)
            self.per_core_sliders[c.core_id] = sl

        self.co_stack.addWidget(per_page)
        layout.addWidget(self.co_stack)

        # Recommendation Banner
        rec_box = QFrame()
        rec_box.setStyleSheet("background-color: #12151D; border: 1px solid #1E2433; border-radius: 6px; padding: 8px 12px;")
        rec_l = QHBoxLayout(rec_box)
        rec_l.setContentsMargins(4, 2, 4, 2)
        if self.cpu.has_3d_vcache:
            tip_txt = f"💡 <b>Tipp für {self.cpu.model_name}:</b> Starte mit All-Core <b>-20 Counts</b>. Der 3D V-Cache bleibt dadurch spürbar kühler und taktet stabiler an der {int(self.cpu.boost_clock_mhz)} MHz Grenze. Gold/Silber-Kerne boosten werkseitig bereits am höchsten; passe diese bei Bedarf individuell an."
        elif self.cpu.generation in ("Zen 4", "Zen 5"):
            tip_txt = f"💡 <b>Tipp für {self.cpu.model_name} ({self.cpu.architecture}):</b> Starte mit All-Core <b>-20 bis -30 Counts</b> für spürbar niedrigere Temperaturen und anhaltend hohe All-Core Boost-Taktraten."
        else:
            tip_txt = f"💡 <b>Tipp für {self.cpu.model_name}:</b> Starte mit All-Core <b>-15 bis -20 Counts</b> und teste die Systemstabilität unter Last."
        lbl_tip = QLabel(tip_txt)
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet("font-size: 11px; color: #B0BCCB;")
        rec_l.addWidget(lbl_tip)
        layout.addWidget(rec_box)

        # Actions & Status
        bot_row = QHBoxLayout()
        bot_row.setSpacing(12)

        self.lbl_co_status = QLabel("")
        self.lbl_co_status.setStyleSheet("font-size: 11px; font-weight: 700;")
        bot_row.addWidget(self.lbl_co_status)
        bot_row.addStretch()

        btn_co_reset = QPushButton("CO Auf 0 Zurücksetzen")
        btn_co_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_co_reset.setStyleSheet("""
            QPushButton {
                background-color: #181C26;
                border: 1px solid #283244;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 700;
                color: #C8D1DC;
            }
            QPushButton:hover {
                background-color: #242B3A;
                color: #FFFFFF;
            }
        """)
        btn_co_reset.clicked.connect(self._reset_curve_optimizer)
        bot_row.addWidget(btn_co_reset)

        btn_co_apply = QPushButton("Curve Optimizer Übernehmen")
        btn_co_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_co_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D83B00, stop:1 #FF5500);
                border: none;
                border-radius: 6px;
                padding: 7px 18px;
                font-size: 11px;
                font-weight: 800;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5500, stop:1 #FF7722);
            }
        """)
        btn_co_apply.clicked.connect(self._apply_curve_optimizer)
        bot_row.addWidget(btn_co_apply)

        layout.addLayout(bot_row)
        return panel

    def _set_co_mode(self, mode: str):
        if getattr(self, "btn_co_all", None) is None:
            return
        self.btn_co_all.setChecked(mode == "All-Core")
        self.btn_co_per.setChecked(mode == "Per-Core")
        if getattr(self, "co_stack", None) is not None:
            self.co_stack.setCurrentIndex(0 if mode == "All-Core" else 1)
        if getattr(self, "chips_widget", None) is not None:
            self.chips_widget.setVisible(mode == "All-Core")

    def _apply_curve_optimizer(self):
        if not self.cpu.is_amd or getattr(self, "slider_all_co", None) is None:
            return
        co_mode = "All-Core" if self.btn_co_all.isChecked() else "Per-Core"
        all_co = self.slider_all_co.spin.value()
        per_co = {str(cid): sl.spin.value() for cid, sl in self.per_core_sliders.items()}

        prof = CpuTuningProfile(
            name="Curve Optimizer",
            co_mode=co_mode,
            co_all_core=all_co,
            co_per_core=per_co
        )
        ok, msg = apply_curve_optimizer(prof, core_count=self.cpu.physical_cores)
        if ok:
            self.lbl_co_status.setText("✓ " + msg)
            self.lbl_co_status.setStyleSheet("color: #00E676; font-weight: 800;")
        else:
            self.lbl_co_status.setText("✕ " + msg)
            self.lbl_co_status.setStyleSheet("color: #FF4256; font-weight: 800;")

    def _reset_curve_optimizer(self):
        if getattr(self, "slider_all_co", None) is None:
            return
        self.slider_all_co.spin.setValue(0)
        for sl in self.per_core_sliders.values():
            sl.spin.setValue(0)
        self._apply_curve_optimizer()

    def _create_chart_section(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "adrenalin-card")
        panel.setStyleSheet("""
            QFrame {
                background-color: #131720;
                border: 1px solid #1E2534;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl = QLabel("LIVE TELEMETRIE VERLAUF (ECHTZEIT-GRAPH)")
        lbl.setStyleSheet("font-size: 13px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        layout.addWidget(lbl)

        self.chart = CpuChartWidget(panel)
        layout.addWidget(self.chart)

        return panel

    def _on_preset_clicked(self, p_key: str):
        for k, btn in self.btn_presets.items():
            btn.setChecked(k == p_key)

        prof = PRESET_PROFILES.get(p_key)
        if not prof:
            return
        self.current_profile = prof

        # Update UI Controls to match preset
        idx_epp = self.combo_epp.findData(prof.epp)
        if idx_epp >= 0:
            self.combo_epp.setCurrentIndex(idx_epp)

        idx_gov = self.combo_gov.findData(prof.governor)
        if idx_gov >= 0:
            self.combo_gov.setCurrentIndex(idx_gov)

        self.sw_boost.setChecked(prof.boost)
        self.sw_smt.setChecked(prof.smt_enabled)
        self.slider_max_freq.spin.setValue(prof.max_freq_mhz)

        # Update Curve Optimizer controls to match preset if supported
        if getattr(self, "slider_all_co", None) is not None:
            self.slider_all_co.spin.setValue(prof.co_all_core)
        if getattr(self, "btn_co_all", None) is not None:
            self._set_co_mode(prof.co_mode)

        self.lbl_status_msg.setText(f"Preset '{p_key}' ausgewählt. Klicke 'Profil Übernehmen' zum Anwenden.")
        self.lbl_status_msg.setStyleSheet("color: #00D2FF; font-weight: 700;")

    def _apply_current_tuning(self):
        if getattr(self, "slider_all_co", None) is not None and getattr(self, "btn_co_all", None) is not None:
            co_mode = "All-Core" if self.btn_co_all.isChecked() else "Per-Core"
            all_co = self.slider_all_co.spin.value()
            per_co = {str(cid): sl.spin.value() for cid, sl in self.per_core_sliders.items()}
        else:
            co_mode = "All-Core"
            all_co = 0
            per_co = {}

        prof = CpuTuningProfile(
            name="Benutzerdefiniert",
            governor=self.combo_gov.currentData() or "powersave",
            epp=self.combo_epp.currentData() or "balance_performance",
            boost=self.sw_boost.isChecked(),
            smt_enabled=self.sw_smt.isChecked(),
            min_freq_mhz=400,
            max_freq_mhz=self.slider_max_freq.spin.value(),
            co_mode=co_mode,
            co_all_core=all_co,
            co_per_core=per_co
        )

        # Try direct write first
        ok, msg = apply_cpu_tuning_direct(prof, core_count=self.cpu.physical_cores)
        if not ok:
            # Requires elevation via pkexec
            ok, msg = execute_cpu_tuner_pkexec(prof, core_count=self.cpu.physical_cores)

        if ok:
            self.lbl_status_msg.setText("✓ " + msg)
            self.lbl_status_msg.setStyleSheet("color: #00E676; font-weight: 800;")
            self.lbl_boost_status.setText("● Aktiviert (Auto-Boost)" if prof.boost else "○ Deaktiviert (Base Clock)")
            self.lbl_boost_status.setStyleSheet("font-size: 12px; font-weight: 800; color: " + ("#00E676" if prof.boost else "#F39C12"))
        else:
            self.lbl_status_msg.setText("✕ " + msg)
            self.lbl_status_msg.setStyleSheet("color: #FF4256; font-weight: 800;")

    def _reset_to_defaults(self):
        self._on_preset_clicked("Balanced")
        self._apply_current_tuning()

    def update_telemetry(self, data: dict):
        """Called by MainWindow with fresh CPU telemetry dict."""
        tctl = data.get("temp_tctl", 0.0)
        tccd1 = data.get("temp_tccd1", 0.0)
        pkg_w = data.get("package_power_w", 0.0)
        peak_mhz = data.get("peak_freq_mhz", 0.0)
        peak_cid = data.get("peak_core_id", -1)
        cpu_usage = data.get("cpu_usage_pct", 0.0)
        ram_temps = data.get("ram_temps", [])

        # Update KPI cards
        self.card_temp.set_value(tctl, sub_str=f"CCD1: {tccd1:.1f}°C" if tccd1 > 0 else "")
        self.card_power.set_value(pkg_w, sub_str="Socket Power")
        self.card_clock.set_value(peak_mhz, sub_str=f"Core {peak_cid + 1}" if peak_cid >= 0 else "")
        self.card_usage.set_value(cpu_usage, sub_str=f"{self.cpu.logical_threads} Threads")
        
        if ram_temps:
            dimm_str = " / ".join(f"{t:.1f}°C" for t in ram_temps)
            self.card_ram.set_value(ram_temps[0], sub_str=dimm_str)
        else:
            self.card_ram.set_value(0.0, display_str="--", sub_str="Kein Sensor")

        # Update Core Matrix
        core_freqs = data.get("core_freqs_mhz", {})
        core_powers = data.get("core_power_w", {})
        core_usages = data.get("core_usage_pct", {})
        core_onlines = data.get("core_online", {})

        for cid, card in self.core_cards.items():
            f = core_freqs.get(cid, 0.0)
            p = core_powers.get(cid, 0.0)
            u = core_usages.get(cid, 0.0)
            on = core_onlines.get(cid, True)
            card.update_metrics(f, p, u, online=on)

        # Update Chart
        self.chart.update_telemetry(data)
