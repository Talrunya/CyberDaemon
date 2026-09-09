from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
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
    """CyberDaemon double-frame container used for the profile editor."""

    def __init__(self, title=None, accent="#00E5FF", parent=None):
        super().__init__(parent)
        self.setObjectName("cyberCard")
        self.setStyleSheet(
            "QFrame#cyberCard {"
            " background: #090C14;"
            " border: 1px solid #FF00C8;"
            " border-radius: 14px;"
            "}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(0)

        self.inner = QFrame()
        self.inner.setObjectName("cyberCardInner")
        self.inner.setStyleSheet(
            "QFrame#cyberCardInner {"
            " background: #0B0F18;"
            " border: 1px solid #00E5FF;"
            " border-radius: 10px;"
            "}"
        )
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(16, 14, 16, 14)
        self.inner_layout.setSpacing(9)
        outer.addWidget(self.inner)

        if title:
            header = QHBoxLayout()
            header.setSpacing(8)
            label = QLabel(title)
            label.setObjectName("cyberCardTitle")
            font = QFont("Orbitron")
            font.setBold(True)
            font.setPointSize(9)
            label.setFont(font)
            label.setStyleSheet(
                f"color: {accent}; letter-spacing: 1px;"
            )
            header.addWidget(label)
            header.addStretch()
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background: {accent}; border: none;")
            header.addWidget(line, 1)
            self.inner_layout.addLayout(header)

    def add_widget(self, widget, stretch=0):
        self.inner_layout.addWidget(widget, stretch)

    def add_layout(self, layout):
        self.inner_layout.addLayout(layout)

    def add_spacing(self, value):
        self.inner_layout.addSpacing(value)

    def add_stretch(self, stretch=1):
        self.inner_layout.addStretch(stretch)


class ProfilesPage(QWidget):
    """Central editor for complete CyberDaemon software profiles."""

    profile_activated = Signal(object)
    lighting_apply_requested = Signal(int, int, int, int, str)
    surround_changed = Signal(object, bool)

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
        self._selected_profile = None

        self._build_ui()
        self.refresh_profiles()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(7)

        title = QLabel("PROFILES")
        title.setObjectName("pageTitle")
        title_font = QFont("Orbitron")
        title_font.setBold(True)
        title_font.setPointSize(28)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        title.setFont(title_font)
        subtitle = QLabel("SYSTEM // COMPLETE SOFTWARE PROFILE")
        subtitle.setObjectName("eyebrow")
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(14)

        body = QHBoxLayout()
        body.setSpacing(14)

        # --------------------------------------------------------
        # LEFT: saved profiles
        # --------------------------------------------------------
        left_card = CyberCard("PROFILE DATABASE // SAVED CONFIGURATIONS", "#FF00C8")
        left_card.setMinimumWidth(255)
        left_card.setMaximumWidth(330)

        self.profile_list = QListWidget()
        self.profile_list.setObjectName("profileList")
        self.profile_list.setMinimumWidth(230)
        self.profile_list.setStyleSheet(
            "QListWidget { background: #070A11; border: 1px solid #243242; "
            "border-radius: 8px; padding: 5px; outline: none; }"
            "QListWidget::item { padding: 11px 10px; margin: 2px 0; "
            "border-radius: 6px; color: #C8D5E2; }"
            "QListWidget::item:hover { background: #111A26; }"
            "QListWidget::item:selected { background: #171326; color: #00E5FF; "
            "border-left: 2px solid #FF00C8; }"
        )
        self.profile_list.currentRowChanged.connect(self._profile_selected)
        left_card.add_widget(self.profile_list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.new_button = QPushButton("+ NEW")
        self.new_button.clicked.connect(self._new_profile)
        self.rename_button = QPushButton("RENAME")
        self.rename_button.clicked.connect(self._rename_profile)
        self.delete_button = QPushButton("DELETE")
        self.delete_button.clicked.connect(self._delete_profile)
        for button in (self.new_button, self.rename_button, self.delete_button):
            button.setMinimumHeight(34)
            buttons.addWidget(button)
        left_card.add_layout(buttons)
        body.addWidget(left_card, 0)

        # --------------------------------------------------------
        # CENTER: complete profile editor
        # --------------------------------------------------------
        center = CyberCard("ACTIVE PROFILE // CONFIGURATION MATRIX", "#00E5FF")
        center_layout = center.inner_layout

        header = QHBoxLayout()
        self.profile_name = QLabel("PROFILE")
        self.profile_name.setObjectName("pageTitle")
        self.active_label = QLabel("● ACTIVE")
        self.active_label.setStyleSheet("color: #39FF88; font-size: 10px; font-weight: 800;")
        self.set_active_button = QPushButton("SET ACTIVE")
        self.set_active_button.setObjectName("nav")
        self.set_active_button.clicked.connect(self._set_active)
        header.addWidget(self.profile_name)
        header.addStretch()
        header.addWidget(self.active_label)
        header.addWidget(self.set_active_button)
        center_layout.addLayout(header)

        # RGB
        rgb_card = CyberCard("LIGHTING // RGB MATRIX", "#FF00C8")
        rgb_row = QHBoxLayout()
        rgb_row.setSpacing(10)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(58, 38)
        self.color_button.clicked.connect(self._choose_color)
        self.color_hex = QLabel("#000000")
        self.color_hex.setMinimumWidth(90)
        self.color_hex.setStyleSheet("color: #00E5FF; font-weight: 800;")
        rgb_row.addWidget(self.color_button)
        rgb_row.addWidget(self.color_hex)
        effect_label = QLabel("EFFECT")
        effect_label.setObjectName("eyebrow")
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(EFFECTS)
        self.effect_combo.currentTextChanged.connect(self._effect_changed)
        rgb_row.addSpacing(12)
        rgb_row.addWidget(effect_label)
        rgb_row.addWidget(self.effect_combo, 1)
        rgb_card.add_layout(rgb_row)

        brightness_row = QHBoxLayout()
        brightness_label = QLabel("BRIGHTNESS")
        brightness_label.setObjectName("eyebrow")
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.valueChanged.connect(self._brightness_changed)
        self.brightness_value = QLabel("100 %")
        self.brightness_value.setMinimumWidth(55)
        self.brightness_value.setStyleSheet("color: #00E5FF; font-weight: 800;")
        brightness_row.addWidget(brightness_label)
        brightness_row.addWidget(self.brightness_slider, 1)
        brightness_row.addWidget(self.brightness_value)
        rgb_card.add_layout(brightness_row)
        center_layout.addWidget(rgb_card)

        # EQ
        eq_card = CyberCard("AUDIO // 10-BAND EQUALIZER", "#00E5FF")
        eq_row = QHBoxLayout()
        preset_label = QLabel("PRESET")
        preset_label.setObjectName("eyebrow")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        eq_row.addWidget(preset_label)
        eq_row.addWidget(self.preset_combo, 1)
        self.eq_summary = QLabel("10-BAND EQ // EDIT ON EQUALIZER PAGE")
        self.eq_summary.setStyleSheet("color: #8092A5; font-size: 10px; font-weight: 700;")
        eq_row.addWidget(self.eq_summary)
        eq_card.add_layout(eq_row)

        eq_grid = QGridLayout()
        eq_grid.setHorizontalSpacing(7)
        eq_grid.setVerticalSpacing(1)
        self.eq_sliders = []
        self.eq_value_labels = []
        frequencies = ["32", "64", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
        for index, frequency in enumerate(frequencies):
            column = QWidget()
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(1)
            value_label = QLabel("0 dB")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("color: #00E5FF; font-size: 8px; font-weight: 800;")
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setSingleStep(1)
            slider.setPageStep(3)
            slider.setMinimumHeight(92)
            slider.valueChanged.connect(lambda value, idx=index: self._profile_eq_band_changed(idx, value))
            freq_label = QLabel(frequency)
            freq_label.setAlignment(Qt.AlignCenter)
            freq_label.setStyleSheet("color: #6E8194; font-size: 8px; font-weight: 800;")
            column_layout.addWidget(value_label)
            column_layout.addWidget(slider, 1, Qt.AlignHCenter)
            column_layout.addWidget(freq_label)
            eq_grid.addWidget(column, 0, index)
            self.eq_sliders.append(slider)
            self.eq_value_labels.append(value_label)
        eq_card.add_layout(eq_grid)
        center_layout.addWidget(eq_card)

        # AUDIO / SURROUND
        audio_card = CyberCard("AUDIO // MONITORING & SURROUND", "#FF00C8")
        sidetone_row = QHBoxLayout()
        sidetone_label = QLabel("SIDETONE")
        sidetone_label.setObjectName("eyebrow")
        self.sidetone_slider = QSlider(Qt.Horizontal)
        self.sidetone_slider.setRange(0, 100)
        self.sidetone_slider.valueChanged.connect(self._sidetone_changed)
        self.sidetone_value = QLabel("0 %")
        self.sidetone_value.setMinimumWidth(55)
        self.sidetone_value.setStyleSheet("color: #00E5FF; font-weight: 800;")
        sidetone_row.addWidget(sidetone_label)
        sidetone_row.addWidget(self.sidetone_slider, 1)
        sidetone_row.addWidget(self.sidetone_value)
        audio_card.add_layout(sidetone_row)

        surround_row = QHBoxLayout()
        self.surround_button = QPushButton("7.1 SURROUND: OFF")
        self.surround_button.setCheckable(True)
        self.surround_button.clicked.connect(self._surround_changed)
        surround_info = QLabel("PROFILE AUDIO STATE")
        surround_info.setStyleSheet("color: #6E8194; font-size: 10px; font-weight: 700;")
        surround_row.addWidget(self.surround_button)
        surround_row.addWidget(surround_info)
        surround_row.addStretch()
        audio_card.add_layout(surround_row)
        center_layout.addWidget(audio_card)

        footer = QLabel("PROFILE STORAGE // EVERY CHANGE IS WRITTEN TO profiles.json")
        footer.setObjectName("eyebrow")
        center_layout.addWidget(footer)

        body.addWidget(center, 1)
        root.addLayout(body, 1)

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

        profile = self.profile_manager.profiles[row]
        self._selected_profile = profile

        self._load_profile_into_editor(
            profile
        )

    def _load_current_profile(self):
        if not self.profile_manager.profiles:
            return

        self._selected_profile = self.profile_manager.current_profile
        self._load_profile_into_editor(
            self._selected_profile
        )

    # ============================================================
    # PROFILE EDITOR
    # ============================================================

    def _load_profile_into_editor(
        self,
        profile,
    ):
        self._selected_profile = profile
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
            if is_active:
                self.active_label.setText("● ACTIVE")
                self.active_label.setStyleSheet(
                    "color: #39FF88; font-size: 10px; font-weight: 900;"
                )
            else:
                self.active_label.setText("○ NOT ACTIVE")
                self.active_label.setStyleSheet(
                    "color: #6E8194; font-size: 10px; font-weight: 900;"
                )

            self.set_active_button.setEnabled(not is_active)
            self.set_active_button.setStyleSheet(
                "QPushButton { color: #00E5FF; border: 1px solid #087F9C; "
                "background: #071016; padding: 6px 12px; }"
                "QPushButton:hover { border-color: #00E5FF; background: #0B1820; }"
                "QPushButton:disabled { color: #4E5964; border-color: #26313A; "
                "background: #080C11; }"
            )

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
            self._selected_profile.rgb.color
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
            self._selected_profile
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
            self._selected_profile
        )

        self.profile_manager.update_rgb(
            effect=effect
        )

        profile = (
            self._selected_profile
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
            self._selected_profile
        )

        self.profile_manager.update_rgb(
            brightness=value
        )

        self.brightness_value.setText(
            f"{value} %"
        )

        profile = (
            self._selected_profile
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

        profile = self._selected_profile
        if profile is None:
            return

        try:
            index = self.profile_manager.profiles.index(profile)
        except ValueError:
            return

        self.profile_manager.current_index = index
        self.profile_manager.save()

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
            self._selected_profile
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

        # Edit only the profile currently selected in the editor.
        # Selecting a profile must not activate it.
        self._selected_profile.eq.preset = str(preset)
        self.profile_manager.save()

        self._update_eq_summary(
            self._selected_profile
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
        self.surround_changed.emit(
            self._selected_profile,
            bool(checked),
        )

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
