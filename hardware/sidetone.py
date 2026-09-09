from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hardware.profiles import ProfileManager
from ui.theme import CYAN, MAGENTA


class CyberCard(QFrame):
    """CyberDaemon double-frame control panel."""

    def __init__(self, title, accent=CYAN, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.setObjectName("cyberCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(19, 17, 19, 17)
        self.layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(7, 0, 7, 0)
        header.setSpacing(9)

        label = QLabel(title)
        label.setStyleSheet(
            f"color: {CYAN}; background: transparent; border: none; font-size: 12px; font-weight: 900; letter-spacing: 2px;"
        )
        header.addWidget(label)

        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background: {accent}; border: none;")
        header.addSpacing(4)
        header.addWidget(line, 1)
        self.layout.addLayout(header)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)

        outer_pen = QPen(MAGENTA)
        outer_pen.setWidth(2)
        painter.setPen(outer_pen)
        painter.setBrush(QBrush("#050b10"))
        painter.drawRoundedRect(rect, 15, 15)

        inner = rect.adjusted(9.0, 9.0, -9.0, -9.0)
        inner_pen = QPen("#087f9c")
        inner_pen.setWidth(1)
        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)

        cut = 13.0
        path = QPainterPath()
        path.moveTo(inner.left() + cut, inner.top())
        path.lineTo(inner.right() - cut, inner.top())
        path.lineTo(inner.right(), inner.top() + cut)
        path.lineTo(inner.right(), inner.bottom() - cut)
        path.lineTo(inner.right() - cut, inner.bottom())
        path.lineTo(inner.left() + cut, inner.bottom())
        path.lineTo(inner.left(), inner.bottom() - cut)
        path.lineTo(inner.left(), inner.top() + cut)
        path.closeSubpath()
        painter.drawPath(path)
        painter.end()


class SidetonePage(QWidget):
    sidetone_apply_requested = Signal(int)

    """CyberDaemon hardware sidetone control for the HS80 MAX."""

    def __init__(self, profile_manager=None, parent=None):
        super().__init__(parent)

        self.profile_manager = (
            profile_manager
            if profile_manager is not None
            else ProfileManager()
        )
        self._loading = False

        self._build_ui()
        self.load_profile(self.profile_manager.current_profile)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self._update_hardware_status)
        self._status_timer.start()
        self._update_hardware_status()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 28)
        root.setSpacing(14)

        title = QLabel("SIDETONE")
        title.setObjectName("pageTitle")

        subtitle = QLabel("AUDIO // HARDWARE SIDETONE CONTROL")
        subtitle.setObjectName("eyebrow")

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(8)

        # ------------------------------------------------------------
        # MAIN SIDETONE CARD
        # ------------------------------------------------------------
        card = CyberCard("SIDETONE // LEVEL", CYAN)
        card_layout = card.layout
        card_layout.addSpacing(18)

        level_row = QHBoxLayout()
        level_row.setContentsMargins(7, 0, 7, 0)

        level_title = QLabel("SIDETONE LEVEL")
        level_title.setStyleSheet(
            f"color: {CYAN}; font-size: 11px; font-weight: 900; letter-spacing: 2px;"
        )

        self.value_label = QLabel("0 %")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setStyleSheet(
            f"color: {CYAN}; font-size: 30px; font-weight: 900; letter-spacing: 1px;"
        )

        level_row.addWidget(level_title)
        level_row.addStretch()
        level_row.addWidget(self.value_label)
        card_layout.addLayout(level_row)
        card_layout.addSpacing(18)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setMinimumHeight(30)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: #071017;
                border: 1px solid #0b5164;
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {CYAN};
                border-radius: 3px;
            }}
            QSlider::add-page:horizontal {{
                background: #071017;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                margin: -6px 0;
                background: {CYAN};
                border: 2px solid #d9ffff;
                border-radius: 8px;
            }}
            """
        )
        self.slider.valueChanged.connect(self._sidetone_changed)
        card_layout.addWidget(self.slider)

        range_row = QHBoxLayout()
        range_row.setContentsMargins(7, 0, 7, 0)
        minimum = QLabel("0 %  //  OFF")
        maximum = QLabel("100 %  //  MAX")
        for label in (minimum, maximum):
            label.setStyleSheet(
                "font-size: 10px; font-weight: 800; letter-spacing: 1px;"
            )
        range_row.addWidget(minimum)
        range_row.addStretch()
        range_row.addWidget(maximum)
        card_layout.addLayout(range_row)
        card_layout.addSpacing(24)

        # ------------------------------------------------------------
        # STATUS / DESCRIPTION
        # ------------------------------------------------------------
        status_row = QHBoxLayout()
        status_row.setContentsMargins(7, 0, 7, 0)

        self.status_label = QLabel("CHECKING HARDWARE ...")
        self.status_label.setStyleSheet(
            f"color: {CYAN}; font-size: 11px; font-weight: 900; letter-spacing: 2px;"
        )
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        card_layout.addLayout(status_row)
        card_layout.addSpacing(8)

        info_panel = QFrame()
        info_panel.setObjectName("sidetoneInfo")
        info_panel.setStyleSheet(
            """
            QFrame#sidetoneInfo {
                background: #03070b;
                border: 1px solid #0b2731;
                border-radius: 5px;
            }
            """
        )
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(14, 12, 14, 12)

        self.info_label = QLabel(
            "Sidetone gibt das Mikrofonsignal direkt über das Headset wieder.\n"
            "Die Hardware-Steuerung erfolgt über ALSA."
        )
        self.info_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; background: transparent; border: none;"
        )
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        card_layout.addWidget(info_panel)
        card_layout.addStretch(1)

        root.addWidget(card, 1)


    # ============================================================
    # PROFILE
    # ============================================================

    def load_profile(self, profile):
        if profile is None:
            return

        self._loading = True
        try:
            value = max(
                0,
                min(
                    100,
                    int(getattr(profile, "sidetone", 0)),
                ),
            )
            self.slider.setValue(value)
            self.value_label.setText(f"{value} %")
        finally:
            self._loading = False

        if profile is self.profile_manager.current_profile:
            self.sidetone_apply_requested.emit(value)

    # ============================================================
    # SIDETONE
    # ============================================================

    def _sidetone_changed(self, value):
        value = max(0, min(100, int(value)))
        self.value_label.setText(f"{value} %")

        if self._loading:
            return

        profile = self.profile_manager.current_profile
        if profile is not None:
            profile.sidetone = value
            self.profile_manager.save()

        self.sidetone_apply_requested.emit(value)

    # ============================================================
    # STATUS
    # ============================================================

    def _update_hardware_status(self):
        self.status_label.setText(
            "HARDWARE SIDETONE // HID READY"
        )
        self.info_label.setText(
            "Sidetone gibt das Mikrofonsignal direkt über das Headset wieder.\n"
            "Die Hardware-Steuerung erfolgt direkt über HID."
        )
