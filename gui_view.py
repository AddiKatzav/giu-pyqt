"""Passive PyQt6 view — input events and rendering only."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from presenter import RenderState, RefractionPresenter

_SCENE_W = 800
_SCENE_H = 560


class OpticsCanvas(QGraphicsView):
    """Billiard-style ray canvas using QGraphicsScene."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(0, 0, _SCENE_W, _SCENE_H, self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#1a1d23"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._interface_line: Optional[QGraphicsLineItem] = None
        self._ray_items: list[QGraphicsLineItem] = []
        self._label_items: list[QGraphicsSimpleTextItem] = []
        self._draw_interface()

    def _draw_interface(self) -> None:
        pen = QPen(QColor("#eceff1"), 2)
        y = 280
        self._interface_line = self._scene.addLine(80, y, 720, y, pen)
        self._scene.addRect(80, 40, 640, 240, QPen(Qt.PenStyle.NoPen), QColor("#252a33"))
        self._scene.addRect(80, 280, 640, 240, QPen(Qt.PenStyle.NoPen), QColor("#1e2329"))

    def apply_render_state(self, state: RenderState) -> None:
        for item in self._ray_items:
            self._scene.removeItem(item)
        for item in self._label_items:
            self._scene.removeItem(item)
        self._ray_items.clear()
        self._label_items.clear()

        for ray in state.rays:
            pen = QPen(QColor(ray.color), ray.width)
            if ray.dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
            line = self._scene.addLine(ray.x1, ray.y1, ray.x2, ray.y2, pen)
            self._ray_items.append(line)

        font = QFont("Segoe UI", 10)
        for i, text in enumerate(state.labels):
            label = self._scene.addSimpleText(text, font)
            label.setBrush(QColor("#cfd8dc"))
            label.setPos(90, 48 + i * 22)
            self._label_items.append(label)

        m1 = self._scene.addSimpleText(state.medium1_label, QFont("Segoe UI", 11, QFont.Weight.Bold))
        m1.setBrush(QColor("#4fc3f7"))
        m1.setPos(620, 120)
        self._label_items.append(m1)

        m2 = self._scene.addSimpleText(state.medium2_label, QFont("Segoe UI", 11, QFont.Weight.Bold))
        m2.setBrush(QColor("#81c784" if not state.tir_active else "#ff7043"))
        m2.setPos(620, 360)
        self._label_items.append(m2)


class RefractionMainWindow(QMainWindow):
    """Passive view: emits signals, renders presenter commands."""

    angle_changed = pyqtSignal(float)
    medium1_changed = pyqtSignal(str)
    medium2_changed = pyqtSignal(str)

    def __init__(self, presenter: RefractionPresenter) -> None:
        super().__init__()
        self._presenter = presenter
        self.setWindowTitle("Snell's Law — Optics Simulator")
        self.resize(900, 700)
        self._build_ui()
        self._apply_stylesheet()
        presenter.attach_view(self)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("controls")
        ctrl_layout = QVBoxLayout(controls)

        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Incident angle θ₁"))
        self._angle_slider = QSlider(Qt.Orientation.Horizontal)
        self._angle_slider.setRange(0, 900)
        self._angle_slider.setValue(300)
        self._angle_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._angle_slider.setTickInterval(90)
        self._angle_slider.valueChanged.connect(self._on_angle_slider)
        angle_row.addWidget(self._angle_slider, stretch=1)
        self._angle_value = QLabel("30.0°")
        self._angle_value.setMinimumWidth(56)
        self._angle_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        angle_row.addWidget(self._angle_value)
        ctrl_layout.addLayout(angle_row)

        media_row = QHBoxLayout()
        media_row.addWidget(QLabel("Medium 1 (incident)"))
        self._medium1 = QComboBox()
        self._medium1.currentTextChanged.connect(self.medium1_changed.emit)
        media_row.addWidget(self._medium1, stretch=1)
        media_row.addWidget(QLabel("Medium 2 (transmitted)"))
        self._medium2 = QComboBox()
        self._medium2.currentTextChanged.connect(self.medium2_changed.emit)
        media_row.addWidget(self._medium2, stretch=1)
        ctrl_layout.addLayout(media_row)
        root.addWidget(controls)

        self._canvas = OpticsCanvas()
        root.addWidget(self._canvas, stretch=1)

        self.setStatusBar(QStatusBar())

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #12151a; color: #eceff1; }
            QFrame#controls {
                background-color: #1e2329;
                border: 1px solid #2c333d;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel { color: #b0bec5; font-size: 13px; }
            QComboBox {
                background: #252a33; color: #eceff1; border: 1px solid #3d4654;
                border-radius: 4px; padding: 6px; min-width: 120px;
            }
            QComboBox:hover { border-color: #4fc3f7; }
            QSlider::groove:horizontal {
                height: 6px; background: #2c333d; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px; margin: -5px 0; background: #4fc3f7;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal { background: #1565c0; border-radius: 3px; }
            QStatusBar { background: #1a1d23; color: #90a4ae; }
            """
        )

    def _on_angle_slider(self, value: int) -> None:
        degrees = value / 10.0
        self._angle_value.setText(f"{degrees:.1f}°")
        self.angle_changed.emit(degrees)

    def set_material_choices(self, materials: list[str]) -> None:
        self._medium1.blockSignals(True)
        self._medium2.blockSignals(True)
        self._medium1.clear()
        self._medium2.clear()
        self._medium1.addItems(materials)
        self._medium2.addItems(materials)
        self._medium1.setCurrentText("Air")
        self._medium2.setCurrentText("Glass")
        self._medium1.blockSignals(False)
        self._medium2.blockSignals(False)

    def show_render_state(self, state: RenderState) -> None:
        self._canvas.apply_render_state(state)

    def show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message)
