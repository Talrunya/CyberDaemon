import subprocess
import math

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QPixmap, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .theme import CYAN, GREEN, MAGENTA, TEXT_SECONDARY
from .cyberdaemon_logo import asset


# ============================================================
# SYSTEM VOLUME
# ============================================================

def get_system_volume():
    """Read the real system volume from the default PipeWire/PulseAudio sink."""
    try:
        result = subprocess.run(
            [
                "wpctl",
                "get-volume",
                "@DEFAULT_AUDIO_SINK@",
            ],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )

        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split()

        if not parts:
            return None

        value = float(parts[-1])
        percent = round(value * 100)

        return max(0, min(100, percent))

    except (
        FileNotFoundError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return None


# ============================================================
# CYBER WAVEFORM
# ============================================================

class WaveformWidget(QWidget):
    """Layered neon cyberpunk audio waveform."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumHeight(82)
        self.setMaximumHeight(92)

        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

    def _animate(self):
        self._phase += 0.075
        if self._phase > math.tau:
            self._phase -= math.tau

        self.update()

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        try:
            painter.setRenderHint(
                QPainter.Antialiasing,
                True,
            )

            width = float(self.width())
            height = float(self.height())

            if width <= 10 or height <= 10:
                return

            center = height / 2.0
            left = 5.0
            right = width - 5.0

            # ----------------------------------------------------
            # Faint horizontal energy line
            # ----------------------------------------------------
            beam = QPen("#5C246D")
            beam.setWidth(1)
            painter.setPen(beam)
            painter.drawLine(
                QPointF(left, center),
                QPointF(right, center),
            )

            # ----------------------------------------------------
            # Reference-inspired envelope.
            # Several broad, organic peaks instead of triangles.
            # ----------------------------------------------------
            def envelope(x):
                return (
                    0.12
                    * math.exp(
                        -((x - 0.20) / 0.12) ** 2
                    )
                    + 0.46
                    * math.exp(
                        -((x - 0.34) / 0.075) ** 2
                    )
                    + 0.74
                    * math.exp(
                        -((x - 0.49) / 0.095) ** 2
                    )
                    + 0.53
                    * math.exp(
                        -((x - 0.63) / 0.085) ** 2
                    )
                    + 0.68
                    * math.exp(
                        -((x - 0.78) / 0.11) ** 2
                    )
                )

            # ----------------------------------------------------
            # 21 fine layered traces.
            # The traces are deliberately very close together,
            # producing the dense neon-wire look of the reference.
            # ----------------------------------------------------
            trace_count = 21
            samples = max(
                110,
                int(width / 2),
            )

            for trace_index in range(trace_count):
                layer = (
                    trace_index
                    - (trace_count - 1) / 2.0
                )

                path = QPainterPath()

                for sample in range(samples):
                    x_norm = sample / (samples - 1)
                    x = (
                        left
                        + x_norm * (right - left)
                    )

                    env = envelope(x_norm)

                    # Moving phase makes the signal feel alive
                    # without changing the surrounding UI.
                    phase = (
                        x_norm * 8.0
                        - self._phase
                        + layer * 0.16
                    )

                    wave = (
                        math.sin(phase)
                        * 0.34
                        + math.sin(
                            phase * 1.73 + 0.8
                        )
                        * 0.11
                    )

                    # Narrow central core plus broad outer movement.
                    amplitude = (
                        env
                        * height
                        * 0.47
                        * (1.0 + layer * 0.018)
                    )

                    # Tiny layered separation.
                    y = (
                        center
                        + wave * amplitude
                        + layer * 0.62
                    )

                    point = QPointF(x, y)

                    if sample == 0:
                        path.moveTo(point)
                    else:
                        path.lineTo(point)

                pen = QPen()

                if trace_index < 7:
                    pen.setColor("#4A35FF")
                elif trace_index < 14:
                    pen.setColor("#267CFF")
                else:
                    pen.setColor("#C52DFF")

                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawPath(path)

            # ----------------------------------------------------
            # Bright central filament.
            # ----------------------------------------------------
            core = QPainterPath()

            for sample in range(samples):
                x_norm = sample / (samples - 1)
                x = (
                    left
                    + x_norm * (right - left)
                )

                env = envelope(x_norm)

                wave = (
                    math.sin(
                        x_norm * 11.0
                        - self._phase * 1.35
                    )
                    * 0.22
                    + math.sin(
                        x_norm * 23.0
                        + self._phase
                    )
                    * 0.06
                )

                y = (
                    center
                    + wave * env * height * 0.34
                )

                point = QPointF(x, y)

                if sample == 0:
                    core.moveTo(point)
                else:
                    core.lineTo(point)

            core_pen = QPen("#DFFFFF")
            core_pen.setWidth(1)
            painter.setPen(core_pen)
            painter.drawPath(core)

        finally:
            painter.end()


# ============================================================
# CYBER CARD
# ============================================================

class CyberCard(QFrame):
    """
    CyberDaemon card.

    The target design deliberately uses TWO frames:
      1. rounded magenta outer frame
      2. cyan/angular inner frame

    The inner frame is painted instead of using a normal stylesheet
    so the corners and cut-outs stay visually consistent.
    """

    def __init__(
        self,
        title,
        accent=CYAN,
        icon="",
        parent=None,
    ):
        super().__init__(parent)

        self.accent = accent
        self.setObjectName("cyberCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            19,
            17,
            19,
            17,
        )
        self.layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(7, 0, 7, 0)
        header.setSpacing(9)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(
                f"""
                QLabel {{
                    color: {CYAN};
                    background: transparent;
                    border: none;
                    font-size: 22px;
                    font-weight: 400;
                }}
                """
            )
            header.addWidget(icon_label)

        label = QLabel(title)
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {CYAN};
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 2px;
            }}
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
        header.addWidget(line, 1)

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

        # ----------------------------------------------------
        # OUTER MAGENTA FRAME
        # ----------------------------------------------------

        outer_pen = QPen(MAGENTA)
        outer_pen.setWidth(2)
        painter.setPen(outer_pen)
        painter.setBrush(QBrush("#050b10"))
        painter.drawRoundedRect(
            rect,
            15,
            15,
        )

        # ----------------------------------------------------
        # INNER ANGULAR FRAME
        # ----------------------------------------------------

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

        path = [
            QPointF(inner.left() + cut, inner.top()),
            QPointF(inner.right() - 42, inner.top()),
            QPointF(inner.right(), inner.top() + 18),
            QPointF(inner.right(), inner.bottom() - cut),
            QPointF(inner.right() - cut, inner.bottom()),
            QPointF(inner.left() + 42, inner.bottom()),
            QPointF(inner.left(), inner.bottom() - 18),
            QPointF(inner.left(), inner.top() + cut),
            QPointF(inner.left() + cut, inner.top()),
        ]

        for index in range(len(path) - 1):
            painter.drawLine(
                path[index],
                path[index + 1],
            )

        # Small cyan technical accent on upper-right edge.
        accent_pen = QPen(CYAN)
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

        # Small magenta glow-like lower edge.
        glow_pen = QPen(MAGENTA)
        glow_pen.setWidth(1)
        painter.setPen(glow_pen)

        painter.drawLine(
            QPointF(
                inner.left() + 22,
                inner.bottom(),
            ),
            QPointF(
                inner.left() + 75,
                inner.bottom(),
            ),
        )

        painter.end()


# ============================================================
# OVERVIEW
# ============================================================

class OverviewPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            32,
            27,
            28,
            27,
        )
        root.setSpacing(13)

        # ====================================================
        # HEADER
        # ====================================================

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        titles = QVBoxLayout()
        titles.setSpacing(2)

        title = QLabel("DEVICE OVERVIEW")
        title.setObjectName("pageTitle")
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
            "H S 8 0   M A X   / /   S Y S T E M   S T A T U S"
        )
        subtitle.setStyleSheet(
            f"""
            QLabel {{
                color: {CYAN};
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 3px;
                background: transparent;
            }}
            """
        )

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles)
        header.addStretch()

        marketing = QVBoxLayout()
        marketing.setSpacing(5)

        premium = QLabel(
            "P R E M I U M   W I R E L E S S   G A M I N G   H E A D S E T"
        )
        premium.setAlignment(Qt.AlignRight)
        premium.setStyleSheet(
            f"""
            QLabel {{
                color: {CYAN};
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 2px;
                background: transparent;
            }}
            """
        )

        marketing_sub = QLabel(
            "S O U N D   / /   C O N T R O L   / /   Y O U R   W A Y"
        )
        marketing_sub.setAlignment(Qt.AlignRight)
        marketing_sub.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 8px;
                font-weight: 800;
                letter-spacing: 2px;
                background: transparent;
            }}
            """
        )

        marketing.addWidget(premium)
        marketing.addWidget(marketing_sub)

        header.addLayout(marketing)

        root.addLayout(header)

        # ====================================================
        # GRID
        # ====================================================

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        # Width proportions match the target:
        # device ~= 1.35x each right-hand card.
        grid.setColumnStretch(0, 135)
        grid.setColumnStretch(1, 100)
        grid.setColumnStretch(2, 100)

        # ====================================================
        # DEVICE CARD
        # ====================================================

        headset = CyberCard(
            "DEVICE // HS80 MAX",
            CYAN,
            "◇",
        )

        visual = QLabel()
        visual.setAlignment(Qt.AlignCenter)
        visual.setMinimumHeight(360)
        visual.setMaximumHeight(380)

        headset_pixmap = QPixmap(
            str(asset("hs80_max.png"))
        )

        if not headset_pixmap.isNull():
            visual.setPixmap(
                headset_pixmap.scaled(
                    335,
                    370,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        headset.add_widget(visual)

        device_name = QLabel(
            '<span style="color:#00eaff;">HS80</span> '
            '<span style="color:#ff00b8;">MAX</span>'
        )
        device_name.setAlignment(Qt.AlignCenter)
        device_name.setStyleSheet(
            """
            QLabel {
                font-size: 31px;
                font-weight: 900;
                letter-spacing: 2px;
                background: #02070b;
                border-radius: 4px;
                padding: 4px;
            }
            """
        )

        headset.add_widget(device_name)

        model = QLabel(
            "W I R E L E S S   G A M I N G   H E A D S E T"
        )
        model.setAlignment(Qt.AlignCenter)
        model.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 8px;
                font-weight: 900;
                letter-spacing: 2px;
                background: #02070b;
                padding: 6px;
            }}
            """
        )

        headset.add_widget(model)

        corsair = QLabel("◢  C O R S A I R")
        corsair.setAlignment(Qt.AlignCenter)
        corsair.setStyleSheet(
            """
            QLabel {
                color: #edfaff;
                font-size: 9px;
                font-weight: 900;
                letter-spacing: 3px;
                background: transparent;
                padding: 1px;
            }
            """
        )

        headset.add_widget(corsair)

        receiver_row = QHBoxLayout()
        receiver_row.setSpacing(6)

        receiver_label = QLabel(
            "▣  USB RECEIVER"
        )
        receiver_label.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 9px;
                font-weight: 800;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 4px;
                padding: 7px;
            }}
            """
        )

        self.receiver_overview = QLabel(
            "●  CONNECTED"
        )
        self.receiver_overview.setAlignment(Qt.AlignCenter)
        self.receiver_overview.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 9px;
                font-weight: 900;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 4px;
                padding: 7px;
            }}
            """
        )

        self.receiver_link = QLabel("2.4 GHz")
        self.receiver_link.setAlignment(Qt.AlignCenter)
        self.receiver_link.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 9px;
                font-weight: 800;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 4px;
                padding: 7px;
            }}
            """
        )

        receiver_row.addWidget(receiver_label, 1)
        receiver_row.addWidget(
            self.receiver_overview,
            1,
        )
        receiver_row.addWidget(
            self.receiver_link,
            1,
        )

        headset.layout.addLayout(receiver_row)

        grid.addWidget(
            headset,
            0,
            0,
            2,
            1,
        )

        # ====================================================
        # BATTERY CARD
        # ====================================================

        battery = CyberCard(
            "POWER // BATTERY",
            CYAN,
            "▣",
        )

        self.battery_value = QLabel("--%")
        self.battery_value.setStyleSheet(
            f"""
            QLabel {{
                color: {CYAN};
                font-size: 43px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

        self.battery_bar = self._make_progress_bar()

        battery_status_title = QLabel(
            "BATTERY STATUS"
        )
        battery_status_title.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 800;
                background: transparent;
            }}
            """
        )

        self.battery_status = QLabel(
            "ONLINE"
        )
        self.battery_status.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 12px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

        battery.add_widget(self.battery_value)
        battery.add_widget(self.battery_bar)
        battery.layout.addSpacing(7)
        battery.add_widget(battery_status_title)
        battery.add_widget(self.battery_status)

        grid.addWidget(
            battery,
            0,
            1,
        )

        # ====================================================
        # VOLUME CARD
        # ====================================================

        volume = CyberCard(
            "AUDIO // VOLUME",
            CYAN,
            "◖",
        )

        self.volume_value = QLabel("--%")
        self.volume_value.setStyleSheet(
            f"""
            QLabel {{
                color: {CYAN};
                font-size: 43px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

        self.volume_bar = self._make_progress_bar()

        volume_status_title = QLabel(
            "SYSTEM AUDIO"
        )
        volume_status_title.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 800;
                background: transparent;
            }}
            """
        )

        self.volume_status = QLabel(
            "ACTIVE"
        )
        self.volume_status.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 12px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

        volume.add_widget(self.volume_value)
        volume.add_widget(self.volume_bar)
        volume.layout.addSpacing(7)
        volume.add_widget(volume_status_title)
        volume.add_widget(self.volume_status)

        grid.addWidget(
            volume,
            0,
            2,
        )

        # ====================================================
        # MICROPHONE CARD
        # ====================================================

        microphone = CyberCard(
            "MIC // FLIP TO MUTE",
            CYAN,
            "♧",
        )

        self.mic_status = QLabel(
            "●  WAITING"
        )
        self.mic_status.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 27px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

        waveform_frame = QFrame()
        waveform_frame.setStyleSheet(
            """
            QFrame {
                background: #02070b;
                border: 1px solid #087f9c;
                border-radius: 8px;
            }
            """
        )

        waveform_layout = QVBoxLayout(
            waveform_frame
        )
        waveform_layout.setContentsMargins(
            9,
            5,
            9,
            5,
        )

        waveform = WaveformWidget()
        waveform_layout.addWidget(waveform)

        mic_detail_title = QLabel(
            "MICROPHONE BOOM STATUS"
        )
        mic_detail_title.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 800;
                background: transparent;
            }}
            """
        )

        mic_detail = QLabel(
            "FLIP-TO-MUTE // DETECTED"
        )
        mic_detail.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 700;
                background: transparent;
            }}
            """
        )

        microphone.add_widget(self.mic_status)
        microphone.add_widget(waveform_frame)
        microphone.layout.addSpacing(1)
        microphone.add_widget(mic_detail_title)
        microphone.add_widget(mic_detail)

        grid.addWidget(
            microphone,
            1,
            1,
        )

        # ====================================================
        # SYSTEM DEVICE CARD
        # ====================================================

        device = CyberCard(
            "SYSTEM // DEVICE",
            CYAN,
            "▣",
        )

        self.firmware_value = self._make_value_box(
            "--"
        )
        self.connection_value = self._make_value_box(
            "USB RECEIVER"
        )
        self.device_status_value = self._make_value_box(
            "●  CONNECTED",
            green=True,
        )

        self._add_device_row(
            device,
            "FIRMWARE",
            self.firmware_value,
        )

        self._add_device_row(
            device,
            "CONNECTION",
            self.connection_value,
        )

        self._add_device_row(
            device,
            "STATUS",
            self.device_status_value,
        )

        grid.addWidget(
            device,
            1,
            2,
        )

        root.addLayout(grid, 1)

        # ====================================================
        # LIVE VOLUME
        # ====================================================

        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(250)
        self.volume_timer.timeout.connect(
            self.update_system_volume
        )
        self.volume_timer.start()

        self.update_system_volume()

    # ========================================================
    # HELPERS
    # ========================================================

    def _make_progress_bar(self):
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(29)

        bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: #02070b;
                border: 1px solid #087f9c;
                border-radius: 7px;
            }}

            QProgressBar::chunk {{
                background: {CYAN};
                border-radius: 5px;
                margin: 2px;
            }}
            """
        )

        return bar

    def _make_value_box(
        self,
        text,
        green=False,
    ):
        color = GREEN if green else "#e9f7ff"

        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                font-weight: 900;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 7px;
                padding: 9px 13px;
            }}
            """
        )

        return label

    def _add_device_row(
        self,
        card,
        name,
        value_widget,
    ):
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel(name)
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 10px;
                font-weight: 800;
                background: transparent;
            }}
            """
        )

        row.addWidget(label)
        row.addStretch()
        row.addWidget(value_widget)

        card.layout.addLayout(row)

    # ========================================================
    # LIVE SYSTEM VOLUME
    # ========================================================

    def update_system_volume(self):
        """Update the volume display from the real system volume."""

        volume = get_system_volume()

        if volume is None:
            self.volume_value.setText("--%")
            self.volume_bar.setValue(0)
            self.volume_status.setText(
                "UNAVAILABLE"
            )
            self.volume_status.setStyleSheet(
                f"""
                QLabel {{
                    color: {MAGENTA};
                    font-size: 12px;
                    font-weight: 900;
                    background: transparent;
                }}
                """
            )
            return

        self.volume_value.setText(
            f"{volume}%"
        )

        self.volume_bar.setValue(volume)

        self.volume_status.setText(
            "ACTIVE"
        )
        self.volume_status.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 12px;
                font-weight: 900;
                background: transparent;
            }}
            """
        )

    # ========================================================
    # LIVE HARDWARE STATUS
    # ========================================================

    def update_status(self, status):
        """Update the overview with live HS80 MAX data."""

        if status.battery is not None:
            self.battery_value.setText(
                f"{status.battery}%"
            )

            self.battery_bar.setValue(
                status.battery
            )

            self.battery_status.setText(
                "ONLINE"
            )

        if status.microphone_muted is not None:
            if status.microphone_muted:
                self.mic_status.setText(
                    "●  MUTED"
                )
                self.mic_status.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {MAGENTA};
                        font-size: 27px;
                        font-weight: 900;
                        background: transparent;
                    }}
                    """
                )
            else:
                self.mic_status.setText(
                    "●  ACTIVE"
                )
                self.mic_status.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {GREEN};
                        font-size: 27px;
                        font-weight: 900;
                        background: transparent;
                    }}
                    """
                )

        if status.firmware:
            self.firmware_value.setText(
                status.firmware
            )

        self.receiver_overview.setText(
            "●  CONNECTED"
        )

        self.receiver_overview.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 9px;
                font-weight: 900;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 4px;
                padding: 7px;
            }}
            """
        )

        self.device_status_value.setText(
            "●  CONNECTED"
        )

        self.device_status_value.setStyleSheet(
            f"""
            QLabel {{
                color: {GREEN};
                font-size: 13px;
                font-weight: 900;
                background: #061118;
                border: 1px solid #087f9c;
                border-radius: 7px;
                padding: 9px 13px;
            }}
            """
        )

    # ========================================================
    # CONNECTION
    # ========================================================

    def set_connection_status(self, connected):
        """Update connection indicators."""

        if connected:
            self.receiver_overview.setText(
                "●  CONNECTED"
            )

            self.receiver_overview.setStyleSheet(
                f"""
                QLabel {{
                    color: {GREEN};
                    font-size: 9px;
                    font-weight: 900;
                    background: #061118;
                    border: 1px solid #087f9c;
                    border-radius: 4px;
                    padding: 7px;
                }}
                """
            )

            self.receiver_link.setText(
                "2.4 GHz"
            )

            self.device_status_value.setText(
                "●  CONNECTED"
            )

            self.device_status_value.setStyleSheet(
                f"""
                QLabel {{
                    color: {GREEN};
                    font-size: 13px;
                    font-weight: 900;
                    background: #061118;
                    border: 1px solid #087f9c;
                    border-radius: 7px;
                    padding: 9px 13px;
                }}
                """
            )

        else:
            self.receiver_overview.setText(
                "●  OFFLINE"
            )

            self.receiver_overview.setStyleSheet(
                f"""
                QLabel {{
                    color: {MAGENTA};
                    font-size: 9px;
                    font-weight: 900;
                    background: #061118;
                    border: 1px solid #087f9c;
                    border-radius: 4px;
                    padding: 7px;
                }}
                """
            )

            self.receiver_link.setText(
                "OFFLINE"
            )

            self.device_status_value.setText(
                "●  OFFLINE"
            )

            self.device_status_value.setStyleSheet(
                f"""
                QLabel {{
                    color: {MAGENTA};
                    font-size: 13px;
                    font-weight: 900;
                    background: #061118;
                    border: 1px solid #087f9c;
                    border-radius: 7px;
                    padding: 9px 13px;
                }}
                """
            )
