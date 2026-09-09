from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import QBrush, QPainter, QPen, QFont
import re
import shutil
import subprocess

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hardware.profiles import ProfileManager


FREQUENCIES = [
    "32 Hz",
    "64 Hz",
    "125 Hz",
    "250 Hz",
    "500 Hz",
    "1 kHz",
    "2 kHz",
    "4 kHz",
    "8 kHz",
    "16 kHz",
]

PRESETS = [
    "Pure Direct",
    "Movie Theater",
    "FPS Competition",
    "Clear Chat",
    "Bass Boost",
]


class CyberFrame(QFrame):
    """CyberDaemon double-frame panel used by the EQ page."""

    def __init__(self, title, right_text="", parent=None):
        super().__init__(parent)
        self.setObjectName("cyberEqFrame")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(7, 0, 7, 0)
        header.setSpacing(9)

        label = QLabel(title)
        label.setStyleSheet(
            "color: #00e5ff; background: transparent; border: none; "
            "font-size: 11px; font-weight: 900; letter-spacing: 2px;"
        )
        header.addWidget(label)
        header.addStretch()

        if right_text:
            right = QLabel(right_text)
            right.setStyleSheet(
                "color: #a5b5bd; background: transparent; border: none; "
                "font-size: 10px; font-weight: 800; letter-spacing: 1px;"
            )
            header.addWidget(right)

        self.title_label = label
        self.layout.addLayout(header)

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)

        outer_pen = QPen("#d900a6")
        outer_pen.setWidth(2)
        painter.setPen(outer_pen)
        painter.setBrush(QBrush("#050b10"))
        painter.drawRoundedRect(rect, 15, 15)

        inner = rect.adjusted(9.0, 9.0, -9.0, -9.0)
        inner_pen = QPen("#087f9c")
        inner_pen.setWidth(1)
        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)

        cut = 12.0
        path = [
            QPointF(inner.left() + cut, inner.top()),
            QPointF(inner.right() - cut, inner.top()),
            QPointF(inner.right(), inner.top() + cut),
            QPointF(inner.right(), inner.bottom() - cut),
            QPointF(inner.right() - cut, inner.bottom()),
            QPointF(inner.left() + cut, inner.bottom()),
            QPointF(inner.left(), inner.bottom() - cut),
            QPointF(inner.left(), inner.top() + cut),
            QPointF(inner.left() + cut, inner.top()),
        ]

        for first, second in zip(path, path[1:]):
            painter.drawLine(first, second)

        painter.end()


class EqualizerPage(QWidget):
    """CyberDaemon 10-band software EQ editor.

    The page owns the EQ values stored in the active CyberDaemon profile.
    Actual PipeWire DSP application is deliberately kept separate from
    the UI/profile layer.
    """

    eq_changed = Signal(str, list)

    def __init__(self, profile_manager=None, parent=None):
        super().__init__(parent)

        self.profile_manager = (
            profile_manager
            if profile_manager is not None
            else ProfileManager()
        )

        self._loading = False
        self.sliders = []
        self.value_labels = []

        self._engine_timer = QTimer(self)
        self._engine_timer.setInterval(500)
        self._engine_timer.timeout.connect(self._update_engine_status)

        self._build_ui()
        self.load_profile(self.profile_manager.current_profile)
        self._update_engine_status()
        self._engine_timer.start()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 28)
        root.setSpacing(12)

        title = QLabel("EQUALIZER")
        title.setObjectName("pageTitle")
        title_font = QFont("Orbitron")
        title_font.setBold(True)
        title_font.setPointSize(28)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.4)
        title.setFont(title_font)
        title.setStyleSheet(
            "color: #eafaff; background: transparent;"
        )

        subtitle = QLabel(
            "AUDIO // 10-BAND SOFTWARE EQUALIZER"
        )
        subtitle.setObjectName("eyebrow")
        subtitle.setStyleSheet(
            "color: #00e5ff; font-size: 11px; font-weight: 900; "
            "letter-spacing: 3px;"
        )

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(10)

        # ========================================================
        # PRESET CONTROL
        # ========================================================
        preset_card = CyberFrame("EQ CONTROL", "PRESET / PROFILE")
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(6, 2, 6, 2)
        preset_row.setSpacing(12)

        preset_label = QLabel("EQ PRESET")
        preset_label.setStyleSheet(
            "color: #00e5ff; font-size: 11px; font-weight: 900; "
            "letter-spacing: 2px; background: transparent;"
        )

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.setMinimumHeight(40)
        self.preset_combo.setStyleSheet(
            """
            QComboBox {
                background: #071016;
                color: #eafaff;
                border: 1px solid #087f9c;
                border-radius: 7px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QComboBox:hover {
                border: 1px solid #00e5ff;
            }
            QComboBox::drop-down {
                width: 30px;
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background: #050b10;
                color: #eafaff;
                border: 1px solid #087f9c;
                selection-background-color: #073b50;
                selection-color: #00e5ff;
                padding: 4px;
            }
            """
        )
        self.preset_combo.currentTextChanged.connect(
            self._preset_changed
        )

        self.reset_button = QPushButton("RESTORE FLAT")
        self.reset_button.setMinimumHeight(40)
        self.reset_button.setStyleSheet(
            """
            QPushButton {
                background: #071016;
                color: #00e5ff;
                border: 1px solid #087f9c;
                border-radius: 7px;
                padding: 0 18px;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                border: 1px solid #00e5ff;
                background: #0a1720;
            }
            QPushButton:pressed {
                background: #0d222d;
            }
            """
        )
        self.reset_button.clicked.connect(self._restore_flat)

        preset_row.addWidget(preset_label)
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.reset_button)
        preset_card.layout.addLayout(preset_row)
        root.addWidget(preset_card)

        # ========================================================
        # 10-BAND EQ
        # ========================================================
        card = CyberFrame("PROFILE // ACTIVE", "GAIN  -12 dB  ...  +12 dB")
        self.profile_label = card.title_label
        card.layout.setSpacing(8)

        eq_grid = QGridLayout()
        eq_grid.setContentsMargins(5, 0, 5, 2)
        eq_grid.setHorizontalSpacing(14)
        eq_grid.setVerticalSpacing(4)

        for index, frequency in enumerate(FREQUENCIES):
            column = QWidget()
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(4)

            value = QLabel("0.0 dB")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet(
                "color: #00e5ff; background: transparent; "
                "font-size: 11px; font-weight: 900;"
            )

            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setSingleStep(1)
            slider.setPageStep(3)
            slider.setTickPosition(QSlider.TicksBothSides)
            slider.setTickInterval(3)
            slider.setMinimumHeight(285)
            slider.setMinimumWidth(42)
            slider.setStyleSheet(
                """
                QSlider:vertical {
                    background: transparent;
                }
                QSlider::groove:vertical {
                    background: #07151d;
                    border: 1px solid #164654;
                    width: 6px;
                    border-radius: 3px;
                }
                QSlider::sub-page:vertical {
                    background: #00a8c2;
                    border-radius: 3px;
                }
                QSlider::add-page:vertical {
                    background: #07151d;
                    border-radius: 3px;
                }
                QSlider::handle:vertical {
                    background: #050b10;
                    border: 2px solid #00e5ff;
                    width: 18px;
                    height: 18px;
                    margin: 0 -7px;
                    border-radius: 9px;
                }
                QSlider::handle:vertical:hover {
                    background: #09202a;
                    border: 2px solid #ffffff;
                }
                """
            )
            slider.valueChanged.connect(
                lambda value, idx=index:
                self._band_changed(idx, value)
            )

            freq = QLabel(frequency)
            freq.setAlignment(Qt.AlignCenter)
            freq.setStyleSheet(
                "color: #a5b5bd; background: transparent; "
                "font-size: 10px; font-weight: 900;"
            )

            column_layout.addWidget(value, 0, Qt.AlignHCenter)
            column_layout.addWidget(slider, 1, Qt.AlignHCenter)
            column_layout.addWidget(freq)

            eq_grid.addWidget(column, 0, index)
            self.sliders.append(slider)
            self.value_labels.append(value)

        card.layout.addLayout(eq_grid, 1)
        root.addWidget(card, 1)

        # ========================================================
        # STATUS PANELS
        # ========================================================
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        info = CyberFrame("PROFILE STORAGE", "LIVE / AUTO SAVE")
        info_text = QLabel(
            "Änderungen werden direkt im aktiven "
            "CyberDaemon-Profil gespeichert."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet(
            "color: #eafaff; background: transparent; "
            "font-size: 11px; font-weight: 700;"
        )
        info.layout.addWidget(info_text)

        status = CyberFrame("AUDIO ENGINE", "PIPEWIRE DSP")
        self.engine_status = QLabel(
            "PIPEWIRE DSP // NOT CONNECTED YET"
        )
        self.engine_status.setWordWrap(True)
        self.engine_status.setStyleSheet(
            "color: #eafaff; background: transparent; "
            "font-size: 11px; font-weight: 900;"
        )
        status.layout.addWidget(self.engine_status)

        bottom.addWidget(info, 1)
        bottom.addWidget(status, 1)
        root.addLayout(bottom)

    # ============================================================
    # AUDIO ENGINE STATUS
    # ============================================================

    def _update_engine_status(self):
        """Reflect the actual CyberDaemon PipeWire graph in the UI."""
        if shutil.which("pw-cli") is None:
            self.engine_status.setText(
                "PIPEWIRE DSP // NOT AVAILABLE"
            )
            return

        try:
            result = subprocess.run(
                ["pw-cli", "ls", "Node"],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            self.engine_status.setText(
                "PIPEWIRE DSP // NOT CONNECTED"
            )
            return

        nodes = set(
            re.findall(
                r'node\.name = "([^"]+)"',
                result.stdout,
            )
        )

        if "cyberdaemon-surround" in nodes:
            self.engine_status.setText(
                "PIPEWIRE DSP // 7.1 SURROUND ACTIVE"
            )
        elif "cyberdaemon-eq" in nodes:
            self.engine_status.setText(
                "PIPEWIRE DSP // CONNECTED"
            )
        else:
            self.engine_status.setText(
                "PIPEWIRE DSP // NOT CONNECTED"
            )

    def closeEvent(self, event):
        self._engine_timer.stop()
        super().closeEvent(event)

    # ============================================================
    # PROFILE
    # ============================================================

    def load_profile(self, profile=None):
        """Load the EQ state of a complete headset profile."""
        if profile is None:
            profile = self.profile_manager.current_profile

        bands = list(profile.eq.bands[:10])
        bands += [0.0] * (10 - len(bands))

        self._loading = True

        try:
            preset = profile.eq.preset
            if preset not in PRESETS:
                preset = "Pure Direct"

            self.preset_combo.setCurrentText(preset)

            for index, value in enumerate(bands):
                value = max(-12.0, min(12.0, float(value)))
                integer_value = int(round(value))

                self.sliders[index].setValue(
                    integer_value
                )
                self.value_labels[index].setText(
                    self._format_gain(value)
                )

            self.profile_label.setText(
                f"PROFILE // {preset.upper()}"
            )
        finally:
            self._loading = False

    # ============================================================
    # EDITING
    # ============================================================

    def _band_changed(self, index, value):
        if self._loading:
            return

        self.value_labels[index].setText(
            self._format_gain(value)
        )

        bands = [
            float(slider.value())
            for slider in self.sliders
        ]

        self.profile_manager.update_eq(
            bands=bands
        )

        profile = self.profile_manager.current_profile

        self.preset_combo.blockSignals(True)
        try:
            # Once a slider is changed, the profile is a custom
            # curve even if it started from a named preset.
            profile.eq.preset = "Custom"
            self.preset_combo.setCurrentText(
                "Pure Direct"
            )
        finally:
            self.preset_combo.blockSignals(False)

        self.profile_manager.save()

        self.eq_changed.emit(
            "Custom",
            bands,
        )

    def _preset_changed(self, preset):
        if self._loading:
            return

        profile = self.profile_manager.current_profile
        self.profile_label.setText(
            f"PROFILE // {preset.upper()}"
        )

        # We know from Corsair documentation that Pure Direct is
        # flat. We deliberately do not invent the undocumented
        # dB curves for the other four Corsair presets here.
        if preset == "Pure Direct":
            bands = [0.0] * 10

            self._loading = True
            try:
                for index, slider in enumerate(
                    self.sliders
                ):
                    slider.setValue(0)
                    self.value_labels[index].setText(
                        "0.0 dB"
                    )
            finally:
                self._loading = False

            self.profile_manager.update_eq(
                preset="Pure Direct",
                bands=bands,
            )

            self.eq_changed.emit(
                "Pure Direct",
                bands,
            )
            return

        # Keep the currently stored curve while recording
        # the selected named preset. This lets us preserve the
        # user's profile data until the exact Corsair curves are
        # reproduced instead of silently inventing values.
        bands = [
            float(slider.value())
            for slider in self.sliders
        ]

        self.profile_manager.update_eq(
            preset=preset,
            bands=bands,
        )

        self.eq_changed.emit(
            preset,
            bands,
        )

    def _restore_flat(self):
        self.preset_combo.blockSignals(True)

        try:
            self.preset_combo.setCurrentText(
                "Pure Direct"
            )
        finally:
            self.preset_combo.blockSignals(False)

        bands = [0.0] * 10

        self._loading = True
        try:
            for index, slider in enumerate(
                self.sliders
            ):
                slider.setValue(0)
                self.value_labels[index].setText(
                    "0.0 dB"
                )
        finally:
            self._loading = False

        self.profile_manager.update_eq(
            preset="Pure Direct",
            bands=bands,
        )

        self.eq_changed.emit(
            "Pure Direct",
            bands,
        )

    @staticmethod
    def _format_gain(value):
        value = float(value)

        if value > 0:
            return f"+{value:.1f} dB"

        return f"{value:.1f} dB"

