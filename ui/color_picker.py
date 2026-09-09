from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ColorPicker(QWidget):
    """Cyberpunk RGB color picker."""

    color_changed = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._hue = 180
        self._saturation = 255
        self._value = 255

        self._field_rect = QRect()
        self._hue_rect = QRect()

        self.setMinimumSize(420, 320)
        self.setMouseTracking(True)

    # =========================================================
    # COLOR
    # =========================================================

    def color(self):
        return QColor.fromHsv(
            int(self._hue),
            int(self._saturation),
            int(self._value),
        )

    def set_color(self, color):
        if not color.isValid():
            return

        hsv = color.toHsv()

        self._hue = hsv.hue()

        if self._hue < 0:
            self._hue = 0

        self._saturation = hsv.saturation()
        self._value = hsv.value()

        self.update()

    # =========================================================
    # PAINT
    # =========================================================

    def paintEvent(self, event):
        painter = QPainter(self)
        print(
            "[PICKER PAINT]",
            "hue=", self._hue,
            "sat=", self._saturation,
            "value=", self._value,
            "color=", self.color().name().upper(),
        )
        painter.setRenderHint(
            QPainter.Antialiasing,
            True,
        )

        width = self.width()
        height = self.height()

        margin = 18
        hue_height = 28
        gap = 14

        field_width = width - (margin * 2)

        field_height = (
            height
            - (margin * 2)
            - hue_height
            - gap
        )

        if field_width <= 0 or field_height <= 0:
            painter.end()
            return

        self._field_rect = QRect(
            margin,
            margin,
            field_width,
            field_height,
        )

        self._hue_rect = QRect(
            margin,
            margin + field_height + gap,
            field_width,
            hue_height,
        )

        painter.fillRect(
            self.rect(),
            QColor("#080B12"),
        )

        base_color = QColor.fromHsv(
            int(self._hue),
            255,
            255,
        )

        horizontal = QLinearGradient(
            self._field_rect.left(),
            0,
            self._field_rect.right(),
            0,
        )

        horizontal.setColorAt(
            0.0,
            QColor("#FFFFFF"),
        )

        horizontal.setColorAt(
            1.0,
            base_color,
        )

        painter.fillRect(
            self._field_rect,
            horizontal,
        )

        vertical = QLinearGradient(
            0,
            self._field_rect.top(),
            0,
            self._field_rect.bottom(),
        )

        vertical.setColorAt(
            0.0,
            QColor(0, 0, 0, 0),
        )

        vertical.setColorAt(
            1.0,
            QColor("#000000"),
        )

        painter.fillRect(
            self._field_rect,
            vertical,
        )

        painter.setPen(
            QPen(
                QColor("#00E5FF"),
                1,
            )
        )

        painter.drawRect(
            self._field_rect
        )

        saturation_ratio = (
            self._saturation / 255.0
        )

        value_ratio = (
            self._value / 255.0
        )

        selector_x = (
            self._field_rect.left()
            + int(
                saturation_ratio
                * self._field_rect.width()
            )
        )

        selector_y = (
            self._field_rect.top()
            + int(
                (1.0 - value_ratio)
                * self._field_rect.height()
            )
        )

        selector = QPoint(
            selector_x,
            selector_y,
        )

        painter.setPen(
            QPen(
                QColor("#000000"),
                3,
            )
        )

        painter.drawEllipse(
            selector,
            8,
            8,
        )

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                2,
            )
        )

        painter.drawEllipse(
            selector,
            7,
            7,
        )

        hue_gradient = QLinearGradient(
            self._hue_rect.left(),
            0,
            self._hue_rect.right(),
            0,
        )

        hue_colors = [
            QColor("#FF0000"),
            QColor("#FFFF00"),
            QColor("#00FF00"),
            QColor("#00FFFF"),
            QColor("#0000FF"),
            QColor("#FF00FF"),
            QColor("#FF0000"),
        ]

        for index, color in enumerate(
            hue_colors
        ):
            hue_gradient.setColorAt(
                index / (len(hue_colors) - 1),
                color,
            )

        painter.fillRect(
            self._hue_rect,
            hue_gradient,
        )

        painter.setPen(
            QPen(
                QColor("#00E5FF"),
                1,
            )
        )

        painter.drawRect(
            self._hue_rect
        )

        hue_ratio = (
            self._hue / 360.0
        )

        hue_x = (
            self._hue_rect.left()
            + int(
                hue_ratio
                * self._hue_rect.width()
            )
        )

        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                3,
            )
        )

        painter.drawLine(
            hue_x,
            self._hue_rect.top() - 3,
            hue_x,
            self._hue_rect.bottom() + 3,
        )

        painter.end()

    # =========================================================
    # MOUSE
    # =========================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._handle_mouse(
                event.position().toPoint()
            )

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._handle_mouse(
                event.position().toPoint()
            )

    def _handle_mouse(self, position):
        if self._field_rect.contains(position):
            x = (
                position.x()
                - self._field_rect.left()
            )

            y = (
                position.y()
                - self._field_rect.top()
            )

            self._saturation = max(
                0,
                min(
                    255,
                    int(
                        (
                            x
                            / self._field_rect.width()
                        )
                        * 255
                    ),
                ),
            )

            self._value = max(
                0,
                min(
                    255,
                    int(
                        (
                            1.0
                            - (
                                y
                                / self._field_rect.height()
                            )
                        )
                        * 255
                    ),
                ),
            )

            self._emit_color()
            return

        if self._hue_rect.contains(position):
            x = (
                position.x()
                - self._hue_rect.left()
            )

            self._hue = max(
                0,
                min(
                    359,
                    int(
                        (
                            x
                            / self._hue_rect.width()
                        )
                        * 359
                    ),
                ),
            )

            self._emit_color()

    # =========================================================
    # SIGNAL
    # =========================================================

    def _emit_color(self):
        color = self.color()

        self.update()

        self.color_changed.emit(
            color
        )

    # =========================================================
    # SIZE
    # =========================================================

    def sizeHint(self):
        return QSize(
            520,
            360,
        )
