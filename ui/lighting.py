from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
from hardware.profiles import ProfileManager
from .color_picker import ColorPicker
from .theme import CYAN, MAGENTA


DEFAULT_LIGHTING_COLOR = "#FF0000"



class CyberCard(QFrame):
    """CyberDaemon double-frame control panel."""

    def __init__(self, title, accent=CYAN, right_text="", parent=None):
        super().__init__(parent)

        self.accent = accent
        self.setObjectName("cyberCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(19, 16, 19, 16)
        self.layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(7, 0, 7, 0)
        header.setSpacing(9)

        label = QLabel(title)
        label.setStyleSheet(
            f"color: {CYAN}; background: transparent; border: none; "
            "font-family: Orbitron; font-size: 11px; font-weight: 900; letter-spacing: 2px;"
        )
        header.addWidget(label)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(
            f"background: {accent}; border: none;"
        )

        header.addSpacing(4)
        header.addWidget(line, 1)

        self.right_label = QLabel(right_text)
        self.right_label.setStyleSheet(
            "color: #a5b5bd; background: transparent; border: none; "
            "font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        header.addWidget(self.right_label)

        self.layout.addLayout(header)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(
            1.0,
            1.0,
            -1.0,
            -1.0,
        )

        outer_pen = QPen(MAGENTA)
        outer_pen.setWidth(2)

        painter.setPen(outer_pen)
        painter.setBrush(QBrush("#050b10"))

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

        inner_pen = QPen("#087f9c")
        inner_pen.setWidth(1)

        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)

        cut = 13.0

        path = QPainterPath()

        path.moveTo(
            inner.left() + cut,
            inner.top(),
        )
        path.lineTo(
            inner.right() - cut,
            inner.top(),
        )
        path.lineTo(
            inner.right(),
            inner.top() + cut,
        )
        path.lineTo(
            inner.right(),
            inner.bottom() - cut,
        )
        path.lineTo(
            inner.right() - cut,
            inner.bottom(),
        )
        path.lineTo(
            inner.left() + cut,
            inner.bottom(),
        )
        path.lineTo(
            inner.left(),
            inner.bottom() - cut,
        )
        path.lineTo(
            inner.left(),
            inner.top() + cut,
        )
        path.closeSubpath()

        painter.drawPath(path)
        painter.end()


class LightingPage(QWidget):
    """
    HS80 MAX RGB / Lighting control.

    The page has two real UI states:

    1. Picker view
       Large color picker + controls.

    2. Compact view
       Current applied color + lighting controls.

    The ColorPicker itself is never modified.
    """

    rgb_apply_requested = Signal(
        int,
        int,
        int,
        int,
        str,
    )

    def __init__(self, parent=None, profile_manager=None):
        super().__init__(parent)

        # Lighting is part of the active device profile.
        # MainWindow may inject the shared ProfileManager so wheel-based
        # profile switching and this page always use the same state.
        self.profile_manager = profile_manager or ProfileManager()
        profile = self.profile_manager.current_profile

        self.current_color = QColor(profile.rgb.color)
        if not self.current_color.isValid():
            self.current_color = QColor(DEFAULT_LIGHTING_COLOR)

        self.current_brightness = max(
            0,
            min(100, int(profile.rgb.brightness)),
        )

        self.current_effect = str(
            profile.rgb.effect or "Static"
        )

        self._build_ui()

        self.color_picker.set_color(
            self.current_color
        )

        self._update_color_values(
            self.current_color
        )

        # Start with the large picker.
        self.view_stack.setCurrentIndex(0)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 28)
        root.setSpacing(12)

        title = QLabel("LIGHTING")
        title.setObjectName("pageTitle")
        title.setStyleSheet(
            "font-family: Orbitron; font-size: 30px; font-weight: 900; letter-spacing: 1.5px;"
        )

        subtitle = QLabel("DEVICE // RGB CONTROL")
        subtitle.setObjectName("eyebrow")
        subtitle.setStyleSheet(
            f"color: {CYAN}; font-size: 11px; font-weight: 900; "
            "letter-spacing: 3px;"
        )

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(10)

        # ========================================================
        # MAIN LIGHTING CARD
        # ========================================================
        card = CyberCard(
            "LIGHTING // RGB MATRIX",
            CYAN,
            "ACTIVE COLOR",
        )

        # Keep the existing two Lighting UI states untouched.
        # Only their container changes to the proven CyberCard.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.view_stack = QStackedLayout()
        content_layout.addLayout(self.view_stack)

        self.picker_page = self._create_picker_page()
        self.compact_page = self._create_compact_page()

        self.view_stack.addWidget(self.picker_page)
        self.view_stack.addWidget(self.compact_page)

        card.add_widget(content)

        self._lighting_card = card

        root.addWidget(card, 1)

        # CyberDaemon visual styling only. The existing picker, signals,
        # profile handling and hardware API remain untouched.
        self.setStyleSheet(self.styleSheet() + """
            QLabel#eyebrow {
                color: #00e5ff;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 2px;
            }
            QFrame#colorPreview {
                border: 2px solid #00e5ff;
                border-radius: 10px;
            }
            QFrame#valuePanel {
                background: #050b10;
                border: 1px solid #087f9c;
                border-radius: 8px;
            }
            QSlider#cyberSlider::groove:horizontal {
                height: 6px;
                background: #07151d;
                border: 1px solid #164654;
                border-radius: 3px;
            }
            QSlider#cyberSlider::sub-page:horizontal {
                background: #00e5ff;
                border-radius: 3px;
            }
            QSlider#cyberSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                background: #00e5ff;
                border: 1px solid #dfffff;
                border-radius: 7px;
            }
            QComboBox#effectCombo {
                min-height: 34px;
                min-width: 150px;
                padding: 0 10px;
                color: #d9e7ed;
                background: #071016;
                border: 1px solid #087f9c;
                border-radius: 7px;
                font-size: 11px;
                font-weight: 700;
            }
            QComboBox#effectCombo:hover {
                border: 1px solid #00e5ff;
            }
            QPushButton#presetButton, QPushButton#applyButton {
                min-height: 34px;
                color: #00e5ff;
                background: #071016;
                border: 1px solid #087f9c;
                border-radius: 7px;
                padding: 0 12px;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QPushButton#presetButton:hover, QPushButton#applyButton:hover {
                background: #0a1720;
                border: 1px solid #00e5ff;
            }
            QPushButton#applyButton {
                border: 1px solid #d900a6;
            }
            QPushButton#applyButton:hover {
                border: 1px solid #ff29cf;
            }
        """)

    # =========================================================
    # PICKER VIEW
    # =========================================================

    def _create_picker_page(self):
        page = QWidget()

        layout = QHBoxLayout(page)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(22)

        # -----------------------------------------------------
        # COLOR PICKER
        # -----------------------------------------------------

        picker_column = QVBoxLayout()

        picker_column.setSpacing(8)

        picker_title = QLabel(
            "COLOR MATRIX"
        )

        picker_title.setObjectName(
            "eyebrow"
        )

        picker_column.addWidget(
            picker_title
        )

        self.color_picker = ColorPicker()

        self.color_picker.color_changed.connect(
            self._color_changed
        )

        picker_column.addWidget(
            self.color_picker,
            1,
        )

        layout.addLayout(
            picker_column,
            2,
        )

        # -----------------------------------------------------
        # CONTROL COLUMN
        # -----------------------------------------------------

        control_column = self._create_control_column(
            include_change_button=False
        )

        layout.addLayout(
            control_column,
            1,
        )

        return page

    # =========================================================
    # COMPACT VIEW
    # =========================================================

    def _create_compact_page(self):
        page = QWidget()

        layout = QVBoxLayout(page)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(16)

        # -----------------------------------------------------
        # CURRENT COLOR
        # -----------------------------------------------------

        current_label = QLabel(
            "CURRENT COLOR"
        )

        current_label.setObjectName(
            "eyebrow"
        )

        layout.addWidget(
            current_label
        )

        color_row = QHBoxLayout()

        color_row.setSpacing(14)

        self.color_preview = QFrame()

        self.color_preview.setFixedSize(
            64,
            64,
        )

        self.color_preview.setObjectName(
            "colorPreview"
        )

        self.compact_color_preview = self.color_preview

        color_row.addWidget(
            self.color_preview
        )

        color_text = QVBoxLayout()

        color_text.setSpacing(4)

        self.color_name = QLabel(
            "CYAN"
        )

        self.color_name.setObjectName(
            "valueLarge"
        )

        self.picker_color_name = self.color_name

        self.hex_value = QLabel(
            "#00FFFF"
        )

        self.hex_value.setObjectName(
            "valueMono"
        )

        self.picker_hex_value = self.hex_value

        color_text.addWidget(
            self.color_name
        )

        color_text.addWidget(
            self.hex_value
        )

        color_text.addStretch()

        color_row.addLayout(
            color_text
        )

        color_row.addStretch()

        layout.addLayout(
            color_row
        )

        # -----------------------------------------------------
        # CHANGE COLOR
        # -----------------------------------------------------

        self.change_color_button = QPushButton(
            "CHANGE COLOR"
        )

        self.change_color_button.setObjectName(
            "presetButton"
        )

        self.change_color_button.setCursor(
            Qt.PointingHandCursor
        )

        self.change_color_button.clicked.connect(
            self._open_color_picker
        )

        layout.addWidget(
            self.change_color_button
        )

        # -----------------------------------------------------
        # RGB
        # -----------------------------------------------------

        rgb_frame = self._create_rgb_frame()

        layout.addWidget(
            rgb_frame
        )

        # -----------------------------------------------------
        # BRIGHTNESS
        # -----------------------------------------------------

        self._add_brightness_controls(
            layout
        )

        # -----------------------------------------------------
        # EFFECT
        # -----------------------------------------------------

        self._add_effect_controls(
            layout
        )

        # -----------------------------------------------------
        # QUICK COLORS
        # -----------------------------------------------------

        self._add_quick_colors(
            layout
        )

        layout.addStretch()

        return page

    # =========================================================
    # CONTROL COLUMN
    # =========================================================

    def _create_control_column(
        self,
        include_change_button=False,
    ):
        column = QVBoxLayout()

        column.setSpacing(16)

        # -----------------------------------------------------
        # CURRENT COLOR
        # -----------------------------------------------------

        current_label = QLabel(
            "CURRENT COLOR"
        )

        current_label.setObjectName(
            "eyebrow"
        )

        column.addWidget(
            current_label
        )

        color_preview_row = QHBoxLayout()

        color_preview_row.setSpacing(
            14
        )

        self.color_preview = QFrame()

        self.color_preview.setFixedSize(
            64,
            64,
        )

        self.color_preview.setObjectName(
            "colorPreview"
        )

        self.picker_color_preview = self.color_preview

        color_preview_row.addWidget(
            self.color_preview
        )

        color_text = QVBoxLayout()

        color_text.setSpacing(4)

        self.color_name = QLabel(
            "CYAN"
        )

        self.color_name.setObjectName(
            "valueLarge"
        )

        self.compact_color_name = self.color_name

        self.hex_value = QLabel(
            "#00FFFF"
        )

        self.hex_value.setObjectName(
            "valueMono"
        )

        self.compact_hex_value = self.hex_value

        color_text.addWidget(
            self.color_name
        )

        color_text.addWidget(
            self.hex_value
        )

        color_text.addStretch()

        color_preview_row.addLayout(
            color_text
        )

        color_preview_row.addStretch()

        column.addLayout(
            color_preview_row
        )

        # -----------------------------------------------------
        # CHANGE COLOR
        # -----------------------------------------------------

        if include_change_button:
            self.change_color_button = QPushButton(
                "CHANGE COLOR"
            )

            self.change_color_button.setObjectName(
                "presetButton"
            )

            self.change_color_button.clicked.connect(
                self._open_color_picker
            )

            column.addWidget(
                self.change_color_button
            )

        # -----------------------------------------------------
        # RGB
        # -----------------------------------------------------

        rgb_frame = self._create_rgb_frame()

        column.addWidget(
            rgb_frame
        )

        # -----------------------------------------------------
        # BRIGHTNESS
        # -----------------------------------------------------

        self._add_brightness_controls(
            column
        )

        # -----------------------------------------------------
        # EFFECT
        # -----------------------------------------------------

        self._add_effect_controls(
            column
        )

        # -----------------------------------------------------
        # QUICK COLORS
        # -----------------------------------------------------

        self._add_quick_colors(
            column
        )

        column.addStretch()

        # -----------------------------------------------------
        # APPLY
        # -----------------------------------------------------

        self.apply_button = QPushButton(
            "USE COLOR"
        )

        self.apply_button.setObjectName(
            "applyButton"
        )

        self.apply_button.setCursor(
            Qt.PointingHandCursor
        )

        self.apply_button.clicked.connect(
            self._apply_to_headset
        )

        column.addWidget(
            self.apply_button
        )

        return column

    # =========================================================
    # RGB FRAME
    # =========================================================

    def _create_rgb_frame(self):
        rgb_frame = QFrame()

        rgb_frame.setObjectName(
            "valuePanel"
        )

        rgb_layout = QVBoxLayout(
            rgb_frame
        )

        rgb_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        rgb_layout.setSpacing(6)

        rgb_title = QLabel(
            "RGB CHANNELS"
        )

        rgb_title.setObjectName(
            "eyebrow"
        )

        rgb_layout.addWidget(
            rgb_title
        )

        self.rgb_value = QLabel(
            "R 000   G 255   B 255"
        )

        self.rgb_value.setObjectName(
            "valueMono"
        )

        self.picker_rgb_value = self.rgb_value

        rgb_layout.addWidget(
            self.rgb_value
        )

        return rgb_frame

    # =========================================================
    # BRIGHTNESS
    # =========================================================

    def _add_brightness_controls(self, layout):
        brightness_header = QHBoxLayout()

        brightness_label = QLabel(
            "BRIGHTNESS"
        )

        brightness_label.setObjectName(
            "eyebrow"
        )

        self.brightness_value = QLabel(
            "100 %"
        )

        self.brightness_value.setObjectName(
            "valueMono"
        )

        brightness_header.addWidget(
            brightness_label
        )

        brightness_header.addStretch()

        brightness_header.addWidget(
            self.brightness_value
        )

        layout.addLayout(
            brightness_header
        )

        self.brightness_slider = QSlider(
            Qt.Horizontal
        )

        self.brightness_slider.setRange(
            0,
            100,
        )

        self.brightness_slider.setValue(
            100
        )

        self.brightness_slider.setObjectName(
            "cyberSlider"
        )

        self.brightness_slider.valueChanged.connect(
            self._brightness_changed
        )

        layout.addWidget(
            self.brightness_slider
        )

    # =========================================================
    # EFFECT
    # =========================================================

    def _add_effect_controls(self, layout):
        effect_header = QHBoxLayout()

        effect_label = QLabel(
            "EFFECT"
        )

        effect_label.setObjectName(
            "eyebrow"
        )

        effect_header.addWidget(
            effect_label
        )

        effect_header.addStretch()

        effect_combo = QComboBox()

        effect_combo.setObjectName(
            "effectCombo"
        )

        effect_combo.addItems(
            [
                "Static",
                "Breathing",
                "Color Shift",
                "Color Pulse",
                "Rainbow",
                "Watercolor",
                "Spiral",
            ]
        )

        effect_combo.setCurrentText(
            self.current_effect
        )

        effect_combo.currentTextChanged.connect(
            self._effect_changed
        )

        # This method is used by both Lighting pages.
        if not hasattr(self, "picker_effect_combo"):
            self.picker_effect_combo = effect_combo
        else:
            self.compact_effect_combo = effect_combo

        effect_header.addWidget(
            effect_combo
        )

        layout.addLayout(
            effect_header
        )

    # =========================================================
    # QUICK COLORS
    # =========================================================

    def _add_quick_colors(self, layout):
        preset_label = QLabel(
            "QUICK COLORS"
        )

        preset_label.setObjectName(
            "eyebrow"
        )

        layout.addWidget(
            preset_label
        )

        preset_layout = QHBoxLayout()

        preset_layout.setSpacing(6)

        presets = [
            ("CYAN", "#00FFFF"),
            ("RED", "#FF0000"),
            ("GREEN", "#00FF00"),
            ("BLUE", "#0088FF"),
            ("PURPLE", "#AA44FF"),
            ("WHITE", "#FFFFFF"),
        ]

        for name, hex_color in presets:
            button = QPushButton(
                name
            )

            button.setObjectName(
                "presetButton"
            )

            button.setCursor(
                Qt.PointingHandCursor
            )

            button.clicked.connect(
                lambda checked=False,
                value=hex_color:
                self._set_preset(value)
            )

            preset_layout.addWidget(
                button
            )

        layout.addLayout(
            preset_layout
        )

    # =========================================================
    # COLOR
    # =========================================================

    def _color_changed(self, color):
        if not color.isValid():
            return

        self.current_color = QColor(color)

        self.profile_manager.update_rgb(
            color=self.current_color.name().upper(),
        )

        self._update_color_values(
            self.current_color
        )

    def _update_color_values(self, color):
        hex_name = color.name().upper()

        rgb_text = (
            f"R {color.red():03d}   "
            f"G {color.green():03d}   "
            f"B {color.blue():03d}"
        )

        # Keep both real UI states synchronized. The picker and compact
        # page have separate widgets and must never display stale values.
        self.picker_hex_value.setText(hex_name)
        self.picker_rgb_value.setText(rgb_text)

        self.compact_hex_value.setText(hex_name)

        self.rgb_value.setText(rgb_text)

        preview_style = f"""
            QFrame#colorPreview {{
                background-color: {color.name()};
                border: 2px solid #00E5FF;
                border-radius: 10px;
            }}
        """

        self.picker_color_preview.setStyleSheet(
            preview_style
        )
        self.compact_color_preview.setStyleSheet(
            preview_style
        )

        # Exact presets keep their explicit names. For arbitrary picker
        # colors, classify by hue so a green selection such as #42D42C
        # is shown as GREEN instead of incorrectly remaining CYAN.
        names = {
            "#FF0000": "RED",
            "#00FF00": "GREEN",
            "#0000FF": "BLUE",
            "#0088FF": "BLUE",
            "#00FFFF": "CYAN",
            "#FFFF00": "YELLOW",
            "#FF00FF": "MAGENTA",
            "#AA44FF": "PURPLE",
            "#FFFFFF": "WHITE",
            "#000000": "OFF",
        }

        color_name = names.get(hex_name)

        if color_name is None:
            hue = color.hsvHue()

            if hue < 0:
                color_name = "CUSTOM"
            elif hue < 15 or hue >= 345:
                color_name = "RED"
            elif hue < 45:
                color_name = "ORANGE"
            elif hue < 75:
                color_name = "YELLOW"
            elif hue < 165:
                color_name = "GREEN"
            elif hue < 195:
                color_name = "CYAN"
            elif hue < 255:
                color_name = "BLUE"
            elif hue < 285:
                color_name = "PURPLE"
            elif hue < 345:
                color_name = "MAGENTA"

        self.picker_color_name.setText(color_name)
        self.compact_color_name.setText(color_name)

        if hasattr(self, "_lighting_card"):
            self._lighting_card.right_label.setText(
                color_name
            )

    # =========================================================
    # QUICK COLOR
    # =========================================================

    def _set_preset(self, hex_color):
        color = QColor(
            hex_color
        )

        if not color.isValid():
            return

        self.current_color = color

        self.profile_manager.update_rgb(
            color=color.name().upper(),
        )

        self.color_picker.set_color(
            color
        )

        self._update_color_values(
            color
        )

        # In compact mode a quick color is a live hardware change.
        if self.view_stack.currentIndex() == 1:
            self._emit_current_lighting()

    # =========================================================
    # BRIGHTNESS
    # =========================================================

    def _brightness_changed(self, value):
        self.current_brightness = int(
            value
        )

        self.profile_manager.update_rgb(
            brightness=self.current_brightness,
        )

        self.brightness_value.setText(
            f"{value} %"
        )

        if self.view_stack.currentIndex() == 1:
            self._emit_current_lighting()

    # =========================================================
    # EFFECT
    # =========================================================

    def _effect_changed(self, effect):
        self.current_effect = effect

        self.profile_manager.update_rgb(
            effect=self.current_effect,
        )

        print(
            "[HS80 RGB] Effect:",
            effect,
        )

        if hasattr(self, "picker_effect_combo"):
            if self.picker_effect_combo.currentText() != effect:
                self.picker_effect_combo.blockSignals(True)
                self.picker_effect_combo.setCurrentText(effect)
                self.picker_effect_combo.blockSignals(False)

        if hasattr(self, "compact_effect_combo"):
            if self.compact_effect_combo.currentText() != effect:
                self.compact_effect_combo.blockSignals(True)
                self.compact_effect_combo.setCurrentText(effect)
                self.compact_effect_combo.blockSignals(False)

        if self.view_stack.currentIndex() == 1:
            self._emit_current_lighting()

    # =========================================================
    # HARDWARE APPLY
    # =========================================================

    def _emit_current_lighting(self):
        """Send the complete current lighting state to MainWindow."""
        self.rgb_apply_requested.emit(
            self.current_color.red(),
            self.current_color.green(),
            self.current_color.blue(),
            self.current_brightness,
            self.current_effect,
        )

    # =========================================================
    # OPEN PICKER
    # =========================================================

    def _open_color_picker(self):
        """
        Open the same large picker again.

        The picker is positioned at the currently selected color.
        """

        self.color_picker.set_color(
            self.current_color
        )

        self.view_stack.setCurrentIndex(
            0
        )

    # =========================================================
    # APPLY
    # =========================================================

    def _apply_to_headset(self):
        # When the large picker is visible, use its actual QColor as the
        # authoritative selection. This prevents a stale page value from
        # ever overwriting what the user sees in the picker.
        picker_color = self.color_picker.color()
        if picker_color.isValid():
            self.current_color = QColor(picker_color)
            self.profile_manager.update_rgb(
                color=self.current_color.name().upper(),
            )
            self._update_color_values(self.current_color)

        # Persist the complete lighting state once more before applying it.
        self.profile_manager.update_rgb(
            color=self.current_color.name().upper(),
            brightness=self.current_brightness,
            effect=self.current_effect,
        )

        red = self.current_color.red()
        green = self.current_color.green()
        blue = self.current_color.blue()
        brightness = self.current_brightness

        print(
            "[HS80 RGB] APPLY:",
            f"R={red}",
            f"G={green}",
            f"B={blue}",
            f"Brightness={brightness}",
            f"Effect={self.current_effect}",
        )

        # Send the complete lighting state to MainWindow.
        self._emit_current_lighting()

        # IMPORTANT:
        # After Apply we switch to the compact view.
        # The picker itself remains alive and keeps the color.
        self.view_stack.setCurrentIndex(
            1
        )

    # =========================================================
    # PROFILE
    # =========================================================

    def load_profile(self, profile=None):
        """Load RGB settings from the active profile into the UI."""
        if profile is None:
            profile = self.profile_manager.current_profile

        color = QColor(profile.rgb.color)
        if not color.isValid():
            color = QColor(DEFAULT_LIGHTING_COLOR)

        self.current_color = color
        self.current_brightness = max(
            0,
            min(100, int(profile.rgb.brightness)),
        )
        self.current_effect = str(profile.rgb.effect or "Static")

        self.color_picker.set_color(self.current_color)
        self.brightness_slider.blockSignals(True)
        self.brightness_slider.setValue(self.current_brightness)
        self.brightness_slider.blockSignals(False)
        if hasattr(self, "picker_effect_combo"):
            self.picker_effect_combo.blockSignals(True)
            self.picker_effect_combo.setCurrentText(
                self.current_effect
            )
            self.picker_effect_combo.blockSignals(False)

        if hasattr(self, "compact_effect_combo"):
            self.compact_effect_combo.blockSignals(True)
            self.compact_effect_combo.setCurrentText(
                self.current_effect
            )
            self.compact_effect_combo.blockSignals(False)
        self.brightness_value.setText(f"{self.current_brightness} %")
        self._update_color_values(self.current_color)

        # A profile switch is a real hardware change.
        # load_profile() must therefore send the newly loaded RGB state
        # through the same signal path used by the normal Apply button.
        print(
            "[HS80 RGB] PROFILE APPLY:",
            f"R={self.current_color.red()}",
            f"G={self.current_color.green()}",
            f"B={self.current_color.blue()}",
            f"Brightness={self.current_brightness}",
            f"Effect={self.current_effect}",
        )
        self._emit_current_lighting()

    # =========================================================
    # PUBLIC API
    # =========================================================

    def get_rgb(self):
        return (
            self.current_color.red(),
            self.current_color.green(),
            self.current_color.blue(),
            self.current_brightness,
        )

    def get_lighting(self):
        return {
            "red": self.current_color.red(),
            "green": self.current_color.green(),
            "blue": self.current_color.blue(),
            "brightness": self.current_brightness,
            "effect": self.current_effect,
        }

    def set_rgb(
        self,
        red,
        green,
        blue,
        brightness=100,
    ):
        color = QColor(
            max(
                0,
                min(
                    255,
                    int(red),
                ),
            ),
            max(
                0,
                min(
                    255,
                    int(green),
                ),
            ),
            max(
                0,
                min(
                    255,
                    int(blue),
                ),
            ),
        )

        self.current_color = color

        brightness = max(
            0,
            min(
                100,
                int(brightness),
            ),
        )

        self.current_brightness = brightness

        self.profile_manager.update_rgb(
            color=self.current_color.name().upper(),
            brightness=self.current_brightness,
        )

        self.brightness_slider.setValue(
            brightness
        )

        self.color_picker.set_color(
            color
        )

        self._update_color_values(
            color
        )

    def set_lighting(
        self,
        red,
        green,
        blue,
        brightness=100,
        effect="Static",
    ):
        self.current_effect = effect

        self.profile_manager.update_rgb(
            effect=self.current_effect,
        )

        if hasattr(self, "picker_effect_combo"):
            self.picker_effect_combo.blockSignals(True)
            self.picker_effect_combo.setCurrentText(effect)
            self.picker_effect_combo.blockSignals(False)

        if hasattr(self, "compact_effect_combo"):
            self.compact_effect_combo.blockSignals(True)
            self.compact_effect_combo.setCurrentText(effect)
            self.compact_effect_combo.blockSignals(False)

        self.set_rgb(
            red,
            green,
            blue,
            brightness,
        )