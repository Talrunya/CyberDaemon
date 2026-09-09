from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hardware.profiles import ProfileManager


EFFECTS = [
    "Static",
    "Breathing",
    "Color Shift",
    "Color Pulse",
    "Rainbow",
    "Watercolor",
    "Spiral",
]

PRESETS = [
    "Pure Direct",
    "Movie Theater",
    "FPS Competition",
    "Clear Chat",
    "Bass Boost",
    "Custom",
]



class CyberCard(QFrame):
    """CyberDaemon double-frame profile panel."""

    def __init__(
        self,
        title,
        accent="#00E5FF",
        parent=None,
    ):
        super().__init__(parent)

        self.accent = accent
        self.setObjectName("cyberCard")
        self.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            19,
            17,
            19,
            17,
        )
        self.layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(
            7,
            0,
            7,
            0,
        )
        header.setSpacing(9)

        label = QLabel(title)
        label.setStyleSheet(
            """
            QLabel {
                color: #00E5FF;
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 2px;
            }
            """
        )

        header.addWidget(label)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(
            f"""
            QFrame {{
                background: {accent};
                border: none;
            }}
            """
        )

        header.addSpacing(4)
        header.addWidget(
            line,
            1,
        )

        self.layout.addLayout(header)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def add_layout(self, layout):
        self.layout.addLayout(layout)

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing
        )

        rect = QRectF(
            self.rect()
        ).adjusted(
            1.0,
            1.0,
            -1.0,
            -1.0,
        )

        outer_pen = QPen(
            QColor("#FF00C8")
        )
        outer_pen.setWidth(2)

        painter.setPen(outer_pen)
        painter.setBrush(
            QBrush("#050B10")
        )

        painter.drawRoundedRect(
            rect,
            15,
            15,
        )

        inner = rect.adjusted(
            9.0,
            9.0,
            -9.0,
            -9.0,
        )

        inner_pen = QPen(
            QColor("#087F9C")
        )
        inner_pen.setWidth(1)

        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)

        cut = 13.0

        path = [
            QPointF(
                inner.left() + cut,
                inner.top(),
            ),
            QPointF(
                inner.right() - 42,
                inner.top(),
            ),
            QPointF(
                inner.right(),
                inner.top() + 18,
            ),
            QPointF(
                inner.right(),
                inner.bottom() - cut,
            ),
            QPointF(
                inner.right() - cut,
                inner.bottom(),
            ),
            QPointF(
                inner.left() + 42,
                inner.bottom(),
            ),
            QPointF(
                inner.left(),
                inner.bottom() - 18,
            ),
            QPointF(
                inner.left(),
                inner.top() + cut,
            ),
            QPointF(
                inner.left() + cut,
                inner.top(),
            ),
        ]

        for index in range(
            len(path) - 1
        ):
            painter.drawLine(
                path[index],
                path[index + 1],
            )

        accent_pen = QPen(
            QColor("#00E5FF")
        )
        accent_pen.setWidth(2)
        painter.setPen(accent_pen)

        painter.drawLine(
            QPointF(
                inner.right() - 65,
                inner.top(),
            ),
            QPointF(
                inner.right() - 20,
                inner.top(),
            ),
        )

        painter.end()


class ProfilesPage(QWidget):
    """Central editor for complete CyberDaemon software profiles."""

    profile_activated = Signal(object)
    lighting_apply_requested = Signal(int, int, int, int, str)

    def __init__(
        self,
        profile_manager=None,
        parent=None,
    ):
        super().__init__(parent)

        self.profile_manager = (
            profile_manager
            if profile_manager is not None
            else ProfileManager()
        )

        self._loading = False

        self._build_ui()
        self.refresh_profiles()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.setContentsMargins(
            30,
            28,
            30,
            28,
        )

        root.setSpacing(8)

        # -----------------------------------------------------
        # PAGE HEADER
        # -----------------------------------------------------

        title = QLabel("PROFILES")
        title.setObjectName(
            "pageTitle"
        )
        title.setStyleSheet(
            """
            QLabel {
                font-size: 39px;
                font-weight: 900;
                letter-spacing: 1px;
                background: transparent;
            }
            """
        )

        subtitle = QLabel(
            "SYSTEM // COMPLETE SOFTWARE PROFILE"
        )
        subtitle.setObjectName(
            "eyebrow"
        )

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(14)

        body = QHBoxLayout()
        body.setSpacing(14)

        # =====================================================
        # LEFT // PROFILE LIBRARY
        # =====================================================

        left_card = CyberCard(
            "PROFILE // LIBRARY"
        )

        left_title = QLabel(
            "SAVED PROFILES"
        )
        left_title.setObjectName(
            "eyebrow"
        )

        left_card.add_widget(
            left_title
        )

        self.profile_list = QListWidget()
        self.profile_list.setObjectName(
            "profileList"
        )
        self.profile_list.setMinimumWidth(
            255
        )
        self.profile_list.setStyleSheet(
            """
            QListWidget {
                background: #02070B;
                color: #DCEFF5;
                border: 1px solid #087F9C;
                border-radius: 6px;
                padding: 5px;
                outline: none;
                font-size: 12px;
                font-weight: 700;
            }

            QListWidget::item {
                padding: 11px 12px;
                margin: 2px 0;
                border: 1px solid transparent;
                border-radius: 4px;
            }

            QListWidget::item:hover {
                background: #081820;
                border: 1px solid #14586B;
            }

            QListWidget::item:selected {
                background: #0A2029;
                color: #00E5FF;
                border: 1px solid #00E5FF;
            }
            """
        )

        self.profile_list.currentRowChanged.connect(
            self._profile_selected
        )

        left_card.add_widget(
            self.profile_list
        )

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.new_button = QPushButton(
            "+ NEW"
        )

        self.rename_button = QPushButton(
            "RENAME"
        )

        self.delete_button = QPushButton(
            "DELETE"
        )

        for button in (
            self.new_button,
            self.rename_button,
            self.delete_button,
        ):
            button.setMinimumHeight(34)
            button.setStyleSheet(
                """
                QPushButton {
                    background: #071117;
                    color: #B8D0D9;
                    border: 1px solid #087F9C;
                    border-radius: 5px;
                    padding: 6px 9px;
                    font-size: 10px;
                    font-weight: 900;
                    letter-spacing: 1px;
                }

                QPushButton:hover {
                    color: #00E5FF;
                    border: 1px solid #00E5FF;
                    background: #0A1D25;
                }

                QPushButton:pressed {
                    background: #102B35;
                }

                QPushButton:disabled {
                    color: #40545D;
                    border: 1px solid #23343A;
                }
                """
            )

        self.new_button.clicked.connect(
            self._new_profile
        )
        self.rename_button.clicked.connect(
            self._rename_profile
        )
        self.delete_button.clicked.connect(
            self._delete_profile
        )

        buttons.addWidget(
            self.new_button
        )
        buttons.addWidget(
            self.rename_button
        )
        buttons.addWidget(
            self.delete_button
        )

        left_card.add_layout(
            buttons
        )

        body.addWidget(
            left_card,
            0,
        )

        # =====================================================
        # CENTER // PROFILE EDITOR
        # =====================================================

        center = CyberCard(
            "PROFILE // CONFIGURATION"
        )

        header = QHBoxLayout()
        header.setSpacing(10)

        self.profile_name = QLabel(
            "PROFILE"
        )
        self.profile_name.setObjectName(
            "pageTitle"
        )
        self.profile_name.setStyleSheet(
            """
            QLabel {
                font-size: 27px;
                font-weight: 900;
                letter-spacing: 1px;
                background: transparent;
            }
            """
        )

        self.active_label = QLabel(
            "● ACTIVE"
        )
        self.active_label.setStyleSheet(
            """
            QLabel {
                color: #52E38A;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
                background: transparent;
            }
            """
        )

        self.set_active_button = QPushButton(
            "SET ACTIVE"
        )
        self.set_active_button.setObjectName(
            "nav"
        )
        self.setMinimumHeight(34)
        self.setStyleSheet(
            """
            QPushButton {
                background: #071117;
                color: #00E5FF;
                border: 1px solid #00E5FF;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }

            QPushButton:hover {
                background: #0A2029;
                border: 1px solid #FF00C8;
            }

            QPushButton:disabled {
                color: #4D626B;
                border: 1px solid #26363C;
            }
            """
        )
        self.set_active_button.clicked.connect(
            self._set_active
        )

        header.addWidget(
            self.profile_name
        )
        header.addStretch()
        header.addWidget(
            self.active_label
        )
        header.addWidget(
            self.set_active_button
        )

        center.add_layout(
            header
        )

        # =====================================================
        # RGB
        # =====================================================

        rgb_title = QLabel(
            "LIGHTING // RGB"
        )
        rgb_title.setObjectName(
            "eyebrow"
        )
        center.add_widget(
            rgb_title
        )

        rgb_row = QHBoxLayout()
        rgb_row.setSpacing(10)

        self.color_button = QPushButton()
        self.color_button.setFixedSize(
            56,
            36,
        )
        self.color_button.clicked.connect(
            self._choose_color
        )

        self.color_hex = QLabel(
            "#000000"
        )
        self.color_hex.setMinimumWidth(
            85
        )

        effect_label = QLabel(
            "EFFECT"
        )
        effect_label.setObjectName(
            "eyebrow"
        )

        self.effect_combo = QComboBox()
        self.effect_combo.addItems(
            EFFECTS
        )
        self.effect_combo.setMinimumHeight(
            34
        )
        self.effect_combo.setStyleSheet(
            """
            QComboBox {
                background: #070D11;
                color: #DCEFF5;
                border: 1px solid #087F9C;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }

            QComboBox:hover {
                border: 1px solid #00E5FF;
            }

            QComboBox QAbstractItemView {
                background: #070D11;
                color: #DCEFF5;
                border: 1px solid #00E5FF;
                selection-background-color: #0A2029;
                selection-color: #00E5FF;
            }
            """
        )
        self.effect_combo.currentTextChanged.connect(
            self._effect_changed
        )

        rgb_row.addWidget(
            self.color_button
        )
        rgb_row.addWidget(
            self.color_hex
        )
        rgb_row.addSpacing(12)
        rgb_row.addWidget(
            effect_label
        )
        rgb_row.addWidget(
            self.effect_combo,
            1,
        )

        center.add_layout(
            rgb_row
        )

        # =====================================================
        # BRIGHTNESS
        # =====================================================

        brightness_row = QHBoxLayout()

        brightness_label = QLabel(
            "BRIGHTNESS"
        )
        brightness_label.setObjectName(
            "eyebrow"
        )

        self.brightness_slider = QSlider(
            Qt.Horizontal
        )
        self.brightness_slider.setRange(
            0,
            100,
        )
        self.brightness_slider.setMinimumHeight(
            24
        )
        self.brightness_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                height: 6px;
                background: #061018;
                border: 1px solid #0B5364;
                border-radius: 3px;
            }

            QSlider::sub-page:horizontal {
                background: #00E5FF;
                border-radius: 3px;
            }

            QSlider::add-page:horizontal {
                background: #071017;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                width: 15px;
                height: 15px;
                margin: -5px 0;
                background: #00E5FF;
                border: 2px solid #D9FFFF;
                border-radius: 8px;
            }
            """
        )
        self.brightness_slider.valueChanged.connect(
            self._brightness_changed
        )

        self.brightness_value = QLabel(
            "100 %"
        )
        self.brightness_value.setMinimumWidth(
            48
        )

        brightness_row.addWidget(
            brightness_label
        )
        brightness_row.addWidget(
            self.brightness_slider,
            1,
        )
        brightness_row.addWidget(
            self.brightness_value
        )

        center.add_layout(
            brightness_row
        )

        # =====================================================
        # EQ
        # =====================================================

        eq_title = QLabel(
            "AUDIO // EQUALIZER"
        )
        eq_title.setObjectName(
            "eyebrow"
        )
        center.add_widget(
            eq_title
        )

        eq_row = QHBoxLayout()

        preset_label = QLabel(
            "PRESET"
        )
        preset_label.setObjectName(
            "eyebrow"
        )

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            PRESETS
        )
        self.preset_combo.setMinimumHeight(
            34
        )
        self.preset_combo.setStyleSheet(
            """
            QComboBox {
                background: #070D11;
                color: #DCEFF5;
                border: 1px solid #087F9C;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
            }

            QComboBox:hover {
                border: 1px solid #00E5FF;
            }

            QComboBox QAbstractItemView {
                background: #070D11;
                color: #DCEFF5;
                border: 1px solid #00E5FF;
                selection-background-color: #0A2029;
                selection-color: #00E5FF;
            }
            """
        )
        self.preset_combo.currentTextChanged.connect(
            self._preset_changed
        )

        eq_row.addWidget(
            preset_label
        )
        eq_row.addWidget(
            self.preset_combo,
            1,
        )

        center.add_layout(
            eq_row
        )

        self.eq_summary = QLabel(
            "10-BAND EQ // EDIT ON EQUALIZER PAGE"
        )
        self.eq_summary.setStyleSheet(
            """
            QLabel {
                color: #8FA8B5;
                font-size: 10px;
                font-weight: 700;
                background: transparent;
            }
            """
        )
        center.add_widget(
            self.eq_summary
        )

        # =====================================================
        # 10-BAND EQ EDITOR
        # =====================================================

        eq_editor = QFrame()
        eq_editor.setObjectName(
            "profileEqEditor"
        )
        eq_editor.setStyleSheet(
            """
            QFrame#profileEqEditor {
                background: #02070B;
                border: 1px solid #087F9C;
                border-radius: 6px;
            }
            """
        )

        eq_editor_layout = QVBoxLayout(
            eq_editor
        )
        eq_editor_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        eq_editor_layout.setSpacing(2)

        eq_grid = QGridLayout()
        eq_grid.setHorizontalSpacing(8)
        eq_grid.setVerticalSpacing(2)

        self.eq_sliders = []
        self.eq_value_labels = []

        frequencies = [
            "32",
            "64",
            "125",
            "250",
            "500",
            "1k",
            "2k",
            "4k",
            "8k",
            "16k",
        ]

        for index, frequency in enumerate(
            frequencies
        ):
            column = QWidget()

            column_layout = QVBoxLayout(
                column
            )
            column_layout.setContentsMargins(
                0,
                0,
                0,
                0,
            )
            column_layout.setSpacing(1)

            value_label = QLabel(
                "0 dB"
            )
            value_label.setAlignment(
                Qt.AlignCenter
            )
            value_label.setStyleSheet(
                """
                QLabel {
                    color: #B9D7E0;
                    font-size: 8px;
                    font-weight: 800;
                    background: transparent;
                }
                """
            )

            slider = QSlider(
                Qt.Vertical
            )
            slider.setRange(
                -12,
                12,
            )
            slider.setSingleStep(1)
            slider.setPageStep(3)
            slider.setMinimumHeight(
                125
            )
            slider.setStyleSheet(
                """
                QSlider::groove:vertical {
                    width: 5px;
                    background: #061018;
                    border: 1px solid #0B5364;
                    border-radius: 2px;
                }

                QSlider::sub-page:vertical {
                    background: #00E5FF;
                    border-radius: 2px;
                }

                QSlider::add-page:vertical {
                    background: #071017;
                    border-radius: 2px;
                }

                QSlider::handle:vertical {
                    height: 13px;
                    width: 13px;
                    margin: 0 -4px;
                    background: #00E5FF;
                    border: 2px solid #D9FFFF;
                    border-radius: 7px;
                }
                """
            )
            slider.valueChanged.connect(
                lambda value, idx=index:
                self._profile_eq_band_changed(
                    idx,
                    value,
                )
            )

            freq_label = QLabel(
                frequency
            )
            freq_label.setAlignment(
                Qt.AlignCenter
            )
            freq_label.setStyleSheet(
                """
                QLabel {
                    color: #8FA8B5;
                    font-size: 8px;
                    font-weight: 800;
                    background: transparent;
                }
                """
            )

            column_layout.addWidget(
                value_label
            )
            column_layout.addWidget(
                slider,
                1,
                Qt.AlignHCenter,
            )
            column_layout.addWidget(
                freq_label
            )

            eq_grid.addWidget(
                column,
                0,
                index,
            )

            self.eq_sliders.append(
                slider
            )
            self.eq_value_labels.append(
                value_label
            )

        eq_editor_layout.addLayout(
            eq_grid
        )

        center.add_widget(
            eq_editor
        )

        # =====================================================
        # AUDIO // SIDETONE + SURROUND
        # =====================================================

        audio_title = QLabel(
            "AUDIO // MONITORING & SURROUND"
        )
        audio_title.setObjectName(
            "eyebrow"
        )
        center.add_widget(
            audio_title
        )

        sidetone_row = QHBoxLayout()

        sidetone_label = QLabel(
            "SIDETONE"
        )
        sidetone_label.setObjectName(
            "eyebrow"
        )

        self.sidetone_slider = QSlider(
            Qt.Horizontal
        )
        self.sidetone_slider.setRange(
            0,
            100,
        )
        self.sidetone_slider.setMinimumHeight(
            24
        )
        self.sidetone_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                height: 6px;
                background: #061018;
                border: 1px solid #0B5364;
                border-radius: 3px;
            }

            QSlider::sub-page:horizontal {
                background: #00E5FF;
                border-radius: 3px;
            }

            QSlider::add-page:horizontal {
                background: #071017;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                width: 15px;
                height: 15px;
                margin: -5px 0;
                background: #00E5FF;
                border: 2px solid #D9FFFF;
                border-radius: 8px;
            }
            """
        )
        self.sidetone_slider.valueChanged.connect(
            self._sidetone_changed
        )

        self.sidetone_value = QLabel(
            "0 %"
        )
        self.sidetone_value.setMinimumWidth(
            48
        )

        sidetone_row.addWidget(
            sidetone_label
        )
        sidetone_row.addWidget(
            self.sidetone_slider,
            1,
        )
        sidetone_row.addWidget(
            self.sidetone_value
        )

        center.add_layout(
            sidetone_row
        )

        surround_row = QHBoxLayout()

        self.surround_button = QPushButton(
            "7.1 SURROUND: OFF"
        )
        self.surround_button.setCheckable(
            True
        )
        self.surround_button.setMinimumHeight(
            34
        )
        self.surround_button.setStyleSheet(
            """
            QPushButton {
                background: #071117;
                color: #8FA8B5;
                border: 1px solid #087F9C;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }

            QPushButton:hover {
                color: #00E5FF;
                border: 1px solid #00E5FF;
            }

            QPushButton:checked {
                color: #00E5FF;
                background: #0A2029;
                border: 1px solid #00E5FF;
            }
            """
        )
        self.surround_button.clicked.connect(
            self._surround_changed
        )

        surround_info = QLabel(
            "PROFILE AUDIO STATE"
        )
        surround_info.setStyleSheet(
            """
            QLabel {
                color: #8FA8B5;
                font-size: 10px;
                font-weight: 700;
                background: transparent;
            }
            """
        )

        surround_row.addWidget(
            self.surround_button
        )
        surround_row.addWidget(
            surround_info
        )
        surround_row.addStretch()

        center.add_layout(
            surround_row
        )

        center.add_layout(
            QVBoxLayout()
        )

        footer = QLabel(
            "PROFILE STORAGE // "
            "EVERY CHANGE IS WRITTEN TO profiles.json"
        )
        footer.setObjectName(
            "eyebrow"
        )

        center.add_widget(
            footer
        )

        body.addWidget(
            center,
            1,
        )

        root.addLayout(
            body,
            1,
        )

    # ============================================================
    # PROFILE LIST
    # ============================================================

    def refresh_profiles(
        self,
        select_current=True,
    ):
        self._loading = True

        try:
            self.profile_list.clear()

            for profile in (
                self.profile_manager.profiles
            ):
                item = QListWidgetItem(
                    profile.name
                )

                item.setToolTip(
                    f"EQ: {profile.eq.preset}\n"
                    f"RGB: {profile.rgb.effect} "
                    f"{profile.rgb.color}\n"
                    f"7.1: "
                    f"{'ON' if profile.surround.enabled else 'OFF'}"
                )

                self.profile_list.addItem(
                    item
                )

            if self.profile_manager.profiles:
                row = (
                    self.profile_manager.current_index
                    if select_current
                    else 0
                )

                self.profile_list.setCurrentRow(
                    row
                )

        finally:
            self._loading = False

        self._load_current_profile()

    def _profile_selected(self, row):
        if self._loading:
            return

        if row < 0 or row >= len(
            self.profile_manager.profiles
        ):
            return

        profile = (
            self.profile_manager.select_profile(
                row
            )
        )

        self._load_profile_into_editor(
            profile
        )

        self.profile_activated.emit(
            profile
        )

    def _load_current_profile(self):
        if not self.profile_manager.profiles:
            return

        self._load_profile_into_editor(
            self.profile_manager.current_profile
        )

    # ============================================================
    # PROFILE EDITOR
    # ============================================================

    def _load_profile_into_editor(
        self,
        profile,
    ):
        self._loading = True

        try:
            self.profile_name.setText(
                profile.name
            )

            color = QColor(
                profile.rgb.color
            )

            if not color.isValid():
                color = QColor(
                    "#00E5FF"
                )

            self.color_hex.setText(
                color.name().upper()
            )

            self._set_color_button(
                color
            )

            self.effect_combo.setCurrentText(
                profile.rgb.effect
                if profile.rgb.effect
                in EFFECTS
                else "Static"
            )

            self.brightness_slider.setValue(
                max(
                    0,
                    min(
                        100,
                        int(
                            profile.rgb.brightness
                        ),
                    ),
                )
            )

            preset = profile.eq.preset

            if preset not in PRESETS:
                preset = "Custom"

            self.preset_combo.setCurrentText(
                preset
            )

            bands = list(profile.eq.bands[:10])
            bands += [0.0] * (10 - len(bands))
            for index, value in enumerate(bands):
                integer_value = max(-12, min(12, int(round(float(value)))))
                self.eq_sliders[index].setValue(integer_value)
                self.eq_value_labels[index].setText(
                    self._format_eq_value(integer_value)
                )

            is_active = (
                self.profile_manager.profiles.index(profile)
                == self.profile_manager.current_index
            )
            self.active_label.setText(
                "● ACTIVE" if is_active else "○ NOT ACTIVE"
            )
            self.set_active_button.setEnabled(not is_active)

            self._update_eq_summary(
                profile
            )

            self.sidetone_slider.setValue(
                max(
                    0,
                    min(
                        100,
                        int(
                            profile.sidetone
                        ),
                    ),
                )
            )

            self.surround_button.setChecked(
                bool(
                    profile.surround.enabled
                )
            )

            self._update_surround_button()

            self.active_label.setText(
                "● ACTIVE"
            )

        finally:
            self._loading = False

        self._update_value_labels(
            profile
        )

    def _update_value_labels(
        self,
        profile,
    ):
        self.brightness_value.setText(
            f"{profile.rgb.brightness} %"
        )

        self.sidetone_value.setText(
            f"{profile.sidetone} %"
        )

    def _update_eq_summary(
        self,
        profile,
    ):
        bands = list(
            profile.eq.bands[:10]
        )

        nonzero = sum(
            1
            for value in bands
            if abs(float(value)) > 0.001
        )

        self.eq_summary.setText(
            f"PRESET // {profile.eq.preset.upper()}    "
            f"•    {nonzero}/10 CUSTOM BANDS"
        )

    # ============================================================
    # RGB
    # ============================================================

    def _choose_color(self):
        if self._loading:
            return

        current = QColor(
            self.profile_manager.selected_profile.rgb.color
        )

        color = QColorDialog.getColor(
            current,
            self,
            "CyberDaemon // RGB COLOR",
        )

        if not color.isValid():
            return

        self._set_color(
            color
        )

    def _set_color_button(
        self,
        color,
    ):
        self.color_button.setStyleSheet(
            "QPushButton {"
            f"background: {color.name()};"
            "border: 1px solid #4A5568;"
            "border-radius: 5px;"
            "}"
        )

    def _set_color(
        self,
        color,
    ):
        profile = (
            self.profile_manager.selected_profile
        )

        hex_color = color.name().upper()

        self.profile_manager.update_rgb(
            color=hex_color
        )

        self.color_hex.setText(
            hex_color
        )

        self._set_color_button(
            color
        )

        self._apply_lighting(
            profile
        )

    def _effect_changed(
        self,
        effect,
    ):
        if self._loading:
            return

        profile = (
            self.profile_manager.selected_profile
        )

        self.profile_manager.update_rgb(
            effect=effect
        )

        profile = (
            self.profile_manager.selected_profile
        )

        self._apply_lighting(
            profile
        )

    def _brightness_changed(
        self,
        value,
    ):
        if self._loading:
            return

        profile = (
            self.profile_manager.selected_profile
        )

        self.profile_manager.update_rgb(
            brightness=value
        )

        self.brightness_value.setText(
            f"{value} %"
        )

        profile = (
            self.profile_manager.selected_profile
        )

        self._apply_lighting(
            profile
        )

    def _apply_lighting(
        self,
        profile,
    ):
        color = QColor(
            profile.rgb.color
        )

        if not color.isValid():
            return

        self.lighting_apply_requested.emit(
            color.red(),
            color.green(),
            color.blue(),
            profile.rgb.brightness,
            profile.rgb.effect,
        )

    # ============================================================
    # PROFILE ACTIVE STATE
    # ============================================================

    def _set_active(self):
        if self._loading:
            return

        profile = self.profile_manager.activate_selected()
        self.refresh_profiles(select_current=True)
        self._select_profile_by_object(profile)
        self.profile_activated.emit(profile)

    # ============================================================
    # PROFILE EQ
    # ============================================================

    def _profile_eq_band_changed(self, index, value):
        if self._loading:
            return

        self.eq_value_labels[index].setText(
            self._format_eq_value(value)
        )

        bands = [float(slider.value()) for slider in self.eq_sliders]
        self.profile_manager.update_eq(
            preset="Custom",
            bands=bands,
        )

        self.preset_combo.blockSignals(True)
        try:
            self.preset_combo.setCurrentText("Custom")
        finally:
            self.preset_combo.blockSignals(False)

        self._update_eq_summary(
            self.profile_manager.selected_profile
        )

    @staticmethod
    def _format_eq_value(value):
        value = int(value)
        if value > 0:
            return f"+{value} dB"
        return f"{value} dB"

    # ============================================================
    # EQ
    # ============================================================

    def _preset_changed(
        self,
        preset,
    ):
        if self._loading:
            return

        # The actual band curve remains owned by the profile.
        # We only change the selected preset name here.
        self.profile_manager.update_eq(
            preset=preset
        )

        self._update_eq_summary(
            self.profile_manager.selected_profile
        )

    # ============================================================
    # SIDETONE / SURROUND
    # ============================================================

    def _sidetone_changed(
        self,
        value,
    ):
        if self._loading:
            return

        self.profile_manager.update_sidetone(
            value
        )

        self.sidetone_value.setText(
            f"{value} %"
        )

    def _surround_changed(
        self,
        checked,
    ):
        if self._loading:
            return

        self.profile_manager.update_surround(
            checked
        )

        self._update_surround_button()

    def _update_surround_button(self):
        enabled = (
            self.surround_button.isChecked()
        )

        self.surround_button.setText(
            "7.1 SURROUND: ON"
            if enabled
            else "7.1 SURROUND: OFF"
        )

    # ============================================================
    # PROFILE MANAGEMENT
    # ============================================================

    def _new_profile(self):
        # A new profile starts from the currently visible complete
        # configuration. This makes it easy to create variants.
        base = (
            self.profile_manager.current_profile
        )

        profile = (
            self.profile_manager.create_profile(
                "New Profile",
                source_profile=base,
            )
        )

        self.refresh_profiles(
            select_current=True
        )

        self._select_profile_by_object(
            profile
        )

        self.profile_activated.emit(
            profile
        )

    def _rename_profile(self):
        row = (
            self.profile_list.currentRow()
        )

        if row < 0:
            return

        self.profile_list.editItem(
            self.profile_list.item(row)
        )

    def _delete_profile(self):
        row = (
            self.profile_list.currentRow()
        )

        if row < 0:
            return

        was_active = (
            row == self.profile_manager.current_index
        )

        self.profile_manager.delete_profile(
            row
        )

        self.refresh_profiles(
            select_current=True
        )

        if was_active:
            profile = self.profile_manager.current_profile
            self.profile_activated.emit(profile)

    def _select_profile_by_object(
        self,
        profile,
    ):
        try:
            index = (
                self.profile_manager.profiles.index(
                    profile
                )
            )
        except ValueError:
            return

        self._loading = True

        try:
            self.profile_list.setCurrentRow(
                index
            )
        finally:
            self._loading = False

        self._load_profile_into_editor(
            profile
        )

    def keyPressEvent(self, event):
        # Inline rename handling for the profile list.
        if (
            event.key() == Qt.Key_F2
            and self.profile_list.hasFocus()
        ):
            self._rename_profile()
            event.accept()
            return

        super().keyPressEvent(event)
