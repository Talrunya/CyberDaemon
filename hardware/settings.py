from __future__ import annotations

import webbrowser

from PySide6.QtCore import QSettings, Signal, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


CYAN = "#00E5FF"
MAGENTA = "#FF2BD6"
GREEN = "#39FF88"
TEXT_SECONDARY = "#8FA8B5"

CORSAIR_FIRMWARE_UPDATER_URL = (
    "https://www.corsair.com/firmware-updater"
)


class CyberCard(QFrame):
    """CyberDaemon double-frame settings panel."""

    def __init__(
        self,
        title: str,
        accent: str = CYAN,
        parent=None,
    ):
        super().__init__(parent)

        self._title = title
        self._accent = accent

        self.setObjectName("settingsCyberCard")
        self.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            22,
            38,
            22,
            16,
        )
        self.layout.setSpacing(10)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing,
            True,
        )

        rect = QRectF(
            1.0,
            1.0,
            self.width() - 2.0,
            self.height() - 2.0,
        )

        painter.fillRect(
            rect,
            self.palette().window(),
        )

        outer = rect.adjusted(
            0.5,
            0.5,
            -0.5,
            -0.5,
        )

        painter.setPen(
            QPen(
                QColor(MAGENTA),
                1.2,
            )
        )
        painter.setBrush(
            self.palette().window(),
        )
        painter.drawRoundedRect(
            outer,
            8,
            8,
        )

        inner = outer.adjusted(
            8.0,
            8.0,
            -8.0,
            -8.0,
        )

        path = QPainterPath()
        path.moveTo(
            inner.left() + 12,
            inner.top(),
        )
        path.lineTo(
            inner.right() - 12,
            inner.top(),
        )
        path.lineTo(
            inner.right(),
            inner.top() + 12,
        )
        path.lineTo(
            inner.right(),
            inner.bottom() - 12,
        )
        path.lineTo(
            inner.right() - 12,
            inner.bottom(),
        )
        path.lineTo(
            inner.left() + 12,
            inner.bottom(),
        )
        path.lineTo(
            inner.left(),
            inner.bottom() - 12,
        )
        path.lineTo(
            inner.left(),
            inner.top() + 12,
        )
        path.closeSubpath()

        painter.setPen(
            QPen(
                QColor(CYAN),
                1.0,
            )
        )
        painter.setBrush(
            self.palette().window(),
        )
        painter.drawPath(path)

        painter.setPen(
            QPen(
                QColor(self._accent),
                1.0,
            )
        )

        title_x = inner.left() + 18
        title_y = inner.top() + 25

        title_font = QFont("Orbitron")
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_font.setLetterSpacing(
            QFont.AbsoluteSpacing,
            1.1,
        )
        painter.setFont(title_font)

        painter.drawText(
            int(title_x),
            int(title_y),
            self._title,
        )

        line_x = inner.left() + 185
        line_y = inner.top() + 4

        painter.drawLine(
            int(line_x),
            int(line_y),
            int(inner.right() - 18),
            int(line_y),
        )


class SettingsPage(QWidget):
    """CyberDaemon HS80 MAX hardware settings and firmware interface."""

    sleep_timer_changed = Signal(int)

    # These signals prepare the firmware workflow without performing
    # any firmware flashing yet. The actual updater can be attached later.
    firmware_check_requested = Signal()
    firmware_update_requested = Signal(str, str)

    OPTIONS = {
        0: "Disabled",
        1: "1 Minute",
        5: "5 Minutes",
        10: "10 Minutes",
        15: "15 Minutes",
        30: "30 Minutes",
        60: "1 Hour",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings(
            "CyberDaemon",
            "HS80MAX",
        )

        self._loading = False

        self._firmware_current = None
        self._firmware_latest = None
        self._receiver_current = None
        self._receiver_latest = None

        self._build_ui()
        self._load_settings()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.setContentsMargins(
            30,
            28,
            30,
            28,
        )

        root.setSpacing(6)

        title = QLabel("SETTINGS")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "DEVICE // HS80 MAX HARDWARE SETTINGS"
        )
        subtitle.setObjectName("eyebrow")

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(18)

        # -----------------------------------------------------
        # Power card
        # -----------------------------------------------------

        power_card = CyberCard(
            "HEADSET POWER // AUTO POWER-OFF",
            MAGENTA,
        )

        section = QLabel("HEADSET POWER")
        section.setObjectName("eyebrow")
        power_card.add_widget(section)

        row = QHBoxLayout()
        row.setSpacing(18)

        label_layout = QVBoxLayout()
        label_layout.setSpacing(4)

        label = QLabel("Auto Power-Off")
        label.setStyleSheet(
            "font-size: 15px;"
            "font-weight: 800;"
        )

        description = QLabel(
            "Automatically power off the headset "
            "when inactive."
        )
        description.setStyleSheet(
            f"color: {TEXT_SECONDARY};"
            "font-size: 11px;"
            "font-weight: 600;"
        )
        description.setWordWrap(True)

        label_layout.addWidget(label)
        label_layout.addWidget(description)

        self.sleep_combo = QComboBox()

        for minutes, text in self.OPTIONS.items():
            self.sleep_combo.addItem(
                text,
                minutes,
            )

        self.sleep_combo.setMinimumWidth(150)
        self.sleep_combo.setMinimumHeight(38)

        self.sleep_combo.setStyleSheet(
            f"""
            QComboBox {{
                background: #070D11;
                color: #E8F7FF;
                border: 1px solid {CYAN};
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
            }}

            QComboBox:hover {{
                border: 1px solid {MAGENTA};
            }}

            QComboBox::drop-down {{
                width: 28px;
                border: none;
            }}

            QComboBox QAbstractItemView {{
                background: #070D11;
                color: #E8F7FF;
                border: 1px solid {CYAN};
                selection-background-color: #10252D;
                selection-color: {CYAN};
            }}
            """
        )

        self.sleep_combo.currentIndexChanged.connect(
            self._sleep_timer_changed
        )

        row.addLayout(
            label_layout,
            1,
        )
        row.addWidget(
            self.sleep_combo
        )

        row_widget = QWidget()
        row_widget.setLayout(row)
        power_card.add_widget(row_widget)

        self.status_label = QLabel(
            "HEADSET POWER // READY"
        )
        self.status_label.setObjectName("eyebrow")
        power_card.add_widget(self.status_label)

        info_frame = QFrame()
        info_frame.setStyleSheet(
            """
            QFrame {
                background: #03070A;
                border: 1px solid #16252C;
                border-radius: 4px;
            }
            """
        )

        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        info = QLabel(
            "This setting is stored directly on the HS80 MAX "
            "and is not run as a Linux timer."
        )
        info.setStyleSheet(
            f"color: {TEXT_SECONDARY};"
            "font-size: 12px;"
            "font-weight: 600;"
        )
        info.setWordWrap(True)

        info_layout.addWidget(info)
        power_card.add_widget(info_frame)

        root.addWidget(power_card)

        # -----------------------------------------------------
        # Firmware card
        # -----------------------------------------------------

        firmware_card = CyberCard(
            "FIRMWARE // DEVICE UPDATE",
            CYAN,
        )

        firmware_header = QLabel(
            "HS80 MAX FIRMWARE"
        )
        firmware_header.setObjectName("eyebrow")
        firmware_card.add_widget(firmware_header)

        firmware_progress_label = QLabel(
            "FIRMWARE UPDATE // IN PROGRESS"
        )
        firmware_progress_label.setObjectName("eyebrow")
        firmware_card.add_widget(firmware_progress_label)

        self.headset_current_label = QLabel(
            "CURRENT VERSION    —"
        )
        self.headset_latest_label = QLabel(
            "LATEST VERSION     —"
        )

        self._style_firmware_value(
            self.headset_current_label,
            "current",
        )
        self._style_firmware_value(
            self.headset_latest_label,
            "latest",
        )

        firmware_card.add_widget(
            self.headset_current_label
        )
        firmware_card.add_widget(
            self.headset_latest_label
        )

        self.headset_status_label = QLabel(
            "STATUS // NOT CHECKED"
        )
        self.headset_status_label.setObjectName(
            "eyebrow"
        )
        firmware_card.add_widget(
            self.headset_status_label
        )
        firmware_card.layout.addSpacing(1)

        headset_buttons = QHBoxLayout()
        headset_buttons.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        headset_buttons.setSpacing(10)

        self.firmware_check_button = QPushButton(
            "CHECK FOR UPDATES"
        )
        self._style_firmware_button(
            self.firmware_check_button,
            primary=True,
        )
        self.firmware_check_button.clicked.connect(
            self._firmware_check_clicked
        )

        self.firmware_update_button = QPushButton(
            "UPDATE NOW"
        )
        self._style_firmware_button(
            self.firmware_update_button,
            primary=False,
        )
        self.firmware_update_button.setEnabled(False)
        self.firmware_update_button.clicked.connect(
            self._firmware_update_clicked
        )

        headset_buttons.addWidget(
            self.firmware_check_button,
            1,
        )
        headset_buttons.addWidget(
            self.firmware_update_button,
            1,
        )

        headset_button_widget = QWidget()
        headset_button_widget.setLayout(
            headset_buttons
        )
        firmware_card.add_widget(
            headset_button_widget
        )

        receiver_separator = QFrame()
        receiver_separator.setFixedHeight(1)
        receiver_separator.setStyleSheet(
            f"background: {MAGENTA}; border: none;"
        )
        firmware_card.add_widget(
            receiver_separator
        )

        receiver_header = QLabel(
            "WIRELESS RECEIVER"
        )
        receiver_header.setObjectName("eyebrow")
        firmware_card.add_widget(receiver_header)

        self.receiver_current_label = QLabel(
            "CURRENT VERSION    —"
        )
        self.receiver_latest_label = QLabel(
            "LATEST VERSION     —"
        )

        self._style_firmware_value(
            self.receiver_current_label,
            "current",
        )
        self._style_firmware_value(
            self.receiver_latest_label,
            "latest",
        )

        firmware_card.add_widget(
            self.receiver_current_label
        )
        firmware_card.add_widget(
            self.receiver_latest_label
        )

        self.receiver_status_label = QLabel(
            "STATUS // NOT CHECKED"
        )
        self.receiver_status_label.setObjectName(
            "eyebrow"
        )
        firmware_card.add_widget(
            self.receiver_status_label
        )

        receiver_info = QLabel(
            "The headset and wireless receiver are handled separately. "
            "The actual flash procedure remains disabled "
            "until the firmware updater "
            "is fully integrated."
        )
        receiver_info.setStyleSheet(
            f"color: {TEXT_SECONDARY};"
            "font-size: 11px;"
            "font-weight: 600;"
        )
        receiver_info.setWordWrap(True)
        firmware_card.add_widget(receiver_info)

        # -----------------------------------------------------
        # Official Corsair updater
        # -----------------------------------------------------

        updater_button = QPushButton(
            "OPEN CORSAIR FIRMWARE UPDATER"
        )

        updater_button.setMinimumHeight(40)
        updater_button.setCursor(
            Qt.PointingHandCursor
        )
        updater_button.setStyleSheet(
            f"""
            QPushButton {{
                background: #050B10;
                color: {MAGENTA};
                border: 1px solid {MAGENTA};
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1px;
            }}

            QPushButton:hover {{
                background: #0A1820;
                color: #FFFFFF;
            }}

            QPushButton:pressed {{
                background: #10252D;
            }}
            """
        )

        updater_button.clicked.connect(
            self._open_corsair_firmware_updater
        )

        firmware_card.add_widget(
            updater_button
        )

        root.addWidget(
            firmware_card,
            1,
        )

    def _style_firmware_value(
        self,
        label,
        kind: str,
    ):
        if kind == "current":
            color = "#E8F7FF"
        else:
            color = CYAN

        label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            """
        )

    def _style_firmware_button(
        self,
        button,
        primary: bool,
    ):
        border = CYAN if primary else MAGENTA
        text = CYAN if primary else MAGENTA

        button.setMinimumHeight(38)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(
            f"""
            QPushButton {{
                background: #050B10;
                color: {text};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1px;
            }}

            QPushButton:hover:enabled {{
                background: #0A1820;
            }}

            QPushButton:pressed:enabled {{
                background: #10252D;
            }}

            QPushButton:disabled {{
                background: #06090C;
                color: #3B4D57;
                border: 1px solid #1B2930;
            }}
            """
        )

    def _open_corsair_firmware_updater(self):
        """Open Corsair's official firmware updater in the browser."""

        try:
            webbrowser.open(
                CORSAIR_FIRMWARE_UPDATER_URL
            )
        except Exception as exc:
            print(
                "[CyberDaemon] Could not open "
                "Corsair Firmware Updater:",
                exc,
            )

    # =========================================================
    # Settings
    # =========================================================

    def _load_settings(self):
        self._loading = True

        value = self.settings.value(
            "sleep_timer",
            15,
            type=int,
        )

        if value not in self.OPTIONS:
            value = 15

        index = self.sleep_combo.findData(
            value
        )

        if index >= 0:
            self.sleep_combo.setCurrentIndex(
                index
            )

        self._loading = False

    # =========================================================
    # Public API
    # =========================================================

    def current_sleep_timer(self) -> int:
        """Return the currently selected timer in minutes."""

        return int(
            self.sleep_combo.currentData()
        )

    def set_firmware_versions(
        self,
        current: str | None = None,
        latest: str | None = None,
        receiver_current: str | None = None,
        receiver_latest: str | None = None,
    ):
        """Update firmware information shown by the page."""

        if current is not None:
            self._firmware_current = str(current)
            self.headset_current_label.setText(
                f"CURRENT VERSION    {self._firmware_current}"
            )

        if latest is not None:
            self._firmware_latest = str(latest)
            self.headset_latest_label.setText(
                f"LATEST VERSION     {self._firmware_latest}"
            )

        if receiver_current is not None:
            self._receiver_current = str(
                receiver_current
            )
            self.receiver_current_label.setText(
                "CURRENT VERSION    "
                f"{self._receiver_current}"
            )

        if receiver_latest is not None:
            self._receiver_latest = str(
                receiver_latest
            )
            self.receiver_latest_label.setText(
                "LATEST VERSION     "
                f"{self._receiver_latest}"
            )

        self._refresh_firmware_state()

    def set_firmware_status(
        self,
        status: str,
        receiver_status: str | None = None,
    ):
        """Set the visible updater status without performing an update."""

        self.headset_status_label.setText(
            f"STATUS // {status.upper()}"
        )

        if receiver_status is not None:
            self.receiver_status_label.setText(
                f"STATUS // {receiver_status.upper()}"
            )

    def _refresh_firmware_state(self):
        if (
            self._firmware_current
            and self._firmware_latest
        ):
            if (
                self._firmware_current
                == self._firmware_latest
            ):
                self.headset_status_label.setText(
                    "STATUS // UP TO DATE"
                )
                self.firmware_update_button.setEnabled(
                    False
                )
            else:
                self.headset_status_label.setText(
                    "STATUS // UPDATE AVAILABLE"
                )
                self.firmware_update_button.setEnabled(
                    True
                )

    # =========================================================
    # Events
    # =========================================================

    def _sleep_timer_changed(self, index):
        if self._loading:
            return

        minutes = int(
            self.sleep_combo.itemData(index)
        )

        self.settings.setValue(
            "sleep_timer",
            minutes,
        )

        self.status_label.setText(
            "HEADSET POWER // APPLYING"
        )

        self.sleep_timer_changed.emit(
            minutes
        )

    def _firmware_check_clicked(self):
        self.firmware_check_button.setEnabled(False)
        self.firmware_check_button.setText(
            "CHECKING..."
        )
        self.set_firmware_status(
            "CHECKING",
            "NOT CHECKED",
        )
        self.firmware_check_requested.emit()

    def _firmware_update_clicked(self):
        if not (
            self._firmware_current
            and self._firmware_latest
        ):
            return

        if (
            self._firmware_current
            == self._firmware_latest
        ):
            return

        self.firmware_update_button.setEnabled(
            False
        )

        self.set_firmware_status(
            "UPDATE REQUESTED",
            "READY",
        )

        self.firmware_update_requested.emit(
            self._firmware_current,
            self._firmware_latest,
        )

    def finish_firmware_check(
        self,
        success: bool,
        status: str = "",
    ):
        """Finish the visual check state."""

        self.firmware_check_button.setEnabled(True)
        self.firmware_check_button.setText(
            "CHECK FOR UPDATES"
        )

        if status:
            self.set_firmware_status(
                status,
            )
        elif success:
            self.set_firmware_status(
                "CHECK COMPLETE",
            )
        else:
            self.set_firmware_status(
                "CHECK FAILED",
            )

        self._refresh_firmware_state()

    def finish_firmware_update(
        self,
        success: bool,
        status: str = "",
    ):
        """Finish the visual update state."""

        self.firmware_update_button.setEnabled(
            bool(
                self._firmware_current
                and self._firmware_latest
                and self._firmware_current
                != self._firmware_latest
            )
        )

        self.firmware_check_button.setEnabled(
            True
        )
        self.firmware_check_button.setText(
            "CHECK FOR UPDATES"
        )

        if status:
            self.set_firmware_status(
                status,
            )
        elif success:
            self.set_firmware_status(
                "UPDATE COMPLETE",
            )
        else:
            self.set_firmware_status(
                "UPDATE FAILED",
            )

    # =========================================================
    # Hardware status
    # =========================================================

    def set_status(
        self,
        success: bool,
        minutes: int,
    ):
        """Update the hardware application status."""

        if success:
            if minutes == 0:
                text = (
                    "HEADSET POWER // "
                    "AUTO POWER-OFF DISABLED"
                )
            else:
                text = (
                    "HEADSET POWER // "
                    f"AUTO POWER-OFF {minutes} MIN"
                )

            self.status_label.setText(
                text
            )

        else:
            self.status_label.setText(
                "HEADSET POWER // APPLY FAILED"
            )

