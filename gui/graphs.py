from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont

from gui.theme import GRAPH_BG, ACCENT, GREEN, YELLOW, RED


class LiveGraph(QWidget):
    def __init__(self, title="Graph", color=GREEN, max_points=60, max_value=100.0,
                 graph_height=100, parent=None):
        super().__init__(parent)
        self.title_text = title
        self._color = QColor(color)
        self.max_points = max_points
        self.max_value = max_value
        self._data = deque(maxlen=max_points)
        self._dirty = True
        self._last_size = (0, 0)

        self.setMinimumHeight(graph_height + 40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._title_label = QLabel(title, self)
        self._title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._title_label.setStyleSheet(f"color: {color};")
        self._title_label.move(8, 4)

        self._value_label = QLabel("--", self)
        self._value_label.setFont(QFont("Consolas", 11))
        self._value_label.setStyleSheet("color: #aaa;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value_label.move(8, 4)

    def update_value(self, value):
        self._data.append(value)
        self._dirty = True

        pct = min(value / self.max_value, 1.0) if self.max_value > 0 else 0
        self._value_label.setText(f"{value:.1f}%")

        if pct > 0.85:
            self._title_label.setStyleSheet("color: #ef4444;")
        elif pct > 0.65:
            self._title_label.setStyleSheet("color: #f59e0b;")
        else:
            self._title_label.setStyleSheet(f"color: {self._color.name()};")

        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._value_label.move(w - self._value_label.width() - 12, 4)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        header_h = 24
        graph_y = header_h
        graph_h = h - header_h - 4

        painter.setBrush(QColor(GRAPH_BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(4, graph_y, w - 8, graph_h), 6, 6)

        if len(self._data) < 2 or graph_h < 10 or w < 20:
            painter.end()
            return

        points = list(self._data)
        pad = 8
        draw_w = w - 2 * pad
        draw_h = graph_h - 8
        step_x = draw_w / (self.max_points - 1) if self.max_points > 1 else draw_w

        coords = []
        for i, val in enumerate(points):
            x = pad + i * step_x
            ratio = min(val / self.max_value, 1.0) if self.max_value > 0 else 0
            y = graph_y + draw_h - (ratio * (draw_h - 4)) + 2
            coords.append(QPointF(x, y))

        fill_color = QColor(self._color.red() // 3, self._color.green() // 3, self._color.blue() // 3, 180)
        fill_path = QPainterPath()
        fill_path.moveTo(coords[0].x(), graph_y + graph_h - 2)
        for pt in coords:
            fill_path.lineTo(pt)
        fill_path.lineTo(coords[-1].x(), graph_y + graph_h - 2)
        fill_path.closeSubpath()
        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)

        pen = QPen(self._color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        line_path = QPainterPath()
        line_path.moveTo(coords[0])
        for pt in coords[1:]:
            line_path.lineTo(pt)
        painter.drawPath(line_path)

        lx, ly = coords[-1].x(), coords[-1].y()
        painter.setBrush(QBrush(self._color))
        painter.setPen(QPen(QColor("#fff"), 1))
        painter.drawEllipse(QPointF(lx, ly), 3, 3)

        painter.end()

    def clear(self):
        self._data.clear()
        self._value_label.setText("--")
        self._dirty = True
        self.update()


class MiniGraphSet(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.cpu_graph = LiveGraph("CPU Usage", color=GREEN)
        self.gpu_graph = LiveGraph("GPU Usage", color=ACCENT)
        self.ram_graph = LiveGraph("RAM Usage", color=YELLOW)

        layout.addWidget(self.cpu_graph)
        layout.addWidget(self.gpu_graph)
        layout.addWidget(self.ram_graph)

    def update_from_snapshot(self, snap):
        if snap.cpu_usage is not None:
            self.cpu_graph.update_value(snap.cpu_usage)
        if snap.gpu_usage is not None:
            self.gpu_graph.update_value(snap.gpu_usage)
        self.ram_graph.update_value(snap.ram_percent)

    def clear_all(self):
        self.cpu_graph.clear()
        self.gpu_graph.clear()
        self.ram_graph.clear()
