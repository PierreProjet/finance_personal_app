from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class LineChart(QWidget):
    """Dependency-free chart supporting line, area and bar representations."""

    def __init__(self, points: list[tuple[str, Decimal]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points = points
        self._chart_type = "line"
        self._show_axes = True
        self._chart_color = "#6C63FF"
        self._value_mode = "absolute"
        self.setMinimumHeight(190)
        self.setToolTip("Évolution calculée à partir des points enregistrés.")

    def set_points(self, points: list[tuple[str, Decimal]]) -> None:
        self._points = points
        self.update()

    def set_options(
        self,
        chart_type: str = "line",
        show_axes: bool = True,
        color: str = "#6C63FF",
        value_mode: str = "absolute",
    ) -> None:
        self._chart_type = chart_type if chart_type in {"line", "area", "bar"} else "line"
        self._show_axes = show_axes
        self._chart_color = color
        self._value_mode = value_mode if value_mode in {"absolute", "percent"} else "absolute"
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(42 if self._show_axes else 12, 12, -12, -30)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        if len(self._points) < 2:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Pas encore assez d'historique")
            return

        values = [float(value) for _, value in self._points]
        if self._value_mode == "percent" and values and values[0] != 0:
            first_value = values[0]
            values = [((value / first_value) - 1.0) * 100.0 for value in values]
        low, high = min(values), max(values)
        spread = high - low or 1.0
        step = rect.width() / max(1, len(values) - 1)
        points = [
            QPointF(
                rect.left() + index * step,
                rect.bottom() - ((value - low) / spread) * rect.height(),
            )
            for index, value in enumerate(values)
        ]
        color = QColor(self._chart_color)
        if not color.isValid():
            color = self.palette().highlight().color()

        if self._show_axes:
            self._draw_axes(painter, rect, low, high)
        if self._chart_type == "bar":
            self._draw_bars(painter, rect, values, low, spread, color)
        elif self._chart_type == "area":
            self._draw_area(painter, rect, points, color)
        else:
            self._draw_line(painter, points, color)

        painter.setPen(self.palette().text().color())
        painter.drawText(rect.left(), self.height() - 8, self._points[0][0])
        end_label = self._points[-1][0]
        painter.drawText(rect.right() - 85, self.height() - 8, end_label)

    def _draw_axes(self, painter: QPainter, rect: QRectF, low: float, high: float) -> None:
        muted = self.palette().mid().color()
        painter.setPen(QPen(muted, 1))
        painter.drawLine(rect.bottomLeft(), rect.topLeft())
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawText(3, int(rect.top()) + 8, self._format_axis_value(high))
        painter.drawText(3, int(rect.bottom()), self._format_axis_value(low))

    def _draw_line(self, painter: QPainter, points: list[QPointF], color: QColor) -> None:
        painter.setPen(QPen(color, 3))
        for first, second in zip(points, points[1:], strict=False):
            painter.drawLine(first, second)
        painter.setBrush(color)
        for point in points:
            painter.drawEllipse(point, 3.5, 3.5)

    def _draw_area(
        self,
        painter: QPainter,
        rect: QRectF,
        points: list[QPointF],
        color: QColor,
    ) -> None:
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        fill = QColor(color)
        fill.setAlpha(70)
        area = QPainterPath(path)
        area.lineTo(points[-1].x(), rect.bottom())
        area.lineTo(points[0].x(), rect.bottom())
        area.closeSubpath()
        painter.fillPath(area, fill)
        painter.setPen(QPen(color, 3))
        painter.drawPath(path)

    def _draw_bars(
        self,
        painter: QPainter,
        rect: QRectF,
        values: list[float],
        low: float,
        spread: float,
        color: QColor,
    ) -> None:
        slot = rect.width() / max(1, len(values))
        width = max(4.0, slot * 0.62)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for index, value in enumerate(values):
            normalized = (value - low) / spread
            height = max(2.0, normalized * rect.height())
            left = rect.left() + index * slot + (slot - width) / 2
            painter.drawRoundedRect(
                QRectF(left, rect.bottom() - height, width, height),
                3,
                3,
            )

    @staticmethod
    def _format_axis_value(value: float) -> str:
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"{value / 1_000_000:.1f} M"
        if absolute >= 1_000:
            return f"{value / 1_000:.1f} k"
        return f"{value:.0f}"
