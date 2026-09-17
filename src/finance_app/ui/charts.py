from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget


class LineChart(QWidget):
    """Small dependency-free line chart used for local financial history."""

    def __init__(
        self,
        points: list[tuple[str, Decimal]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._points = points
        self.setMinimumHeight(190)
        self.setToolTip("Cliquez sur un point pour afficher sa valeur.")

    def set_points(self, points: list[tuple[str, Decimal]]) -> None:
        self._points = points
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -28)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        if len(self._points) < 2:
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "Pas encore assez d'historique",
            )
            return
        values = [float(value) for _, value in self._points]
        low, high = min(values), max(values)
        spread = high - low or 1.0
        step = rect.width() / (len(values) - 1)
        points = [
            QPointF(
                rect.left() + index * step,
                rect.bottom() - ((value - low) / spread) * rect.height(),
            )
            for index, value in enumerate(values)
        ]
        pen = QPen(self.palette().highlight().color(), 3)
        painter.setPen(pen)
        for first, second in zip(points, points[1:], strict=False):
            painter.drawLine(first, second)
        painter.setPen(self.palette().text().color())
        painter.drawText(rect.left(), self.height() - 8, self._points[0][0])
        painter.drawText(rect.right() - 70, self.height() - 8, self._points[-1][0])
