"""Passive PyQt6 view — input events and rendering only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional, cast

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from presenter import RenderState, RefractionPresenter, ViewSignal

_SCENE_W = 800
_SCENE_H = 560
_MATERIAL_COMMIT_DELAY_MS = 75


class MaterialSelector(QWidget):
    """In-window material selector that avoids fragile WSL popup windows."""

    material_committed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_text = ""
        self._materials: list[str] = []
        self._options: Optional[QListWidget] = None
        self._options_parent: Optional[QWidget] = None
        self._event_filter_installed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button = QPushButton()
        self._button.setObjectName("materialSelector")
        self._button.setCheckable(True)
        self._button.clicked.connect(self._set_options_visible)
        layout.addWidget(self._button)

    def clear_materials(self) -> None:
        self._materials.clear()
        if self._options is not None:
            self._options.clear()
            self._options.hide()
        self._current_text = ""
        self._button.setText("")

    def set_materials(self, materials: list[str]) -> None:
        self._materials.extend(materials)
        if self._options is not None:
            self._options.addItems(materials)

    def select_material(self, material: str) -> None:
        self._current_text = material
        self._button.setText(material)
        if self._options is None:
            return
        matches = self._options.findItems(material, Qt.MatchFlag.MatchExactly)
        if matches:
            self._options.setCurrentItem(matches[0])

    def _set_options_visible(self, visible: bool) -> None:
        if visible:
            self._show_options()
        else:
            self._hide_options()

    def _show_options(self) -> None:
        options = self._ensure_options()
        row_height = options.sizeHintForRow(0) if options.count() else 26
        list_height = min(150, max(1, options.count()) * max(26, row_height) + 6)
        parent = self._options_parent or self.window()
        top_left = self.mapTo(parent, QPoint(0, self.height() + 2))
        options.setGeometry(top_left.x(), top_left.y(), self.width(), list_height)
        options.raise_()
        options.show()
        options.setFocus(Qt.FocusReason.PopupFocusReason)
        self._install_event_filter()

    def _ensure_options(self) -> QListWidget:
        parent = self.window()
        if self._options is not None and self._options_parent is parent:
            return self._options

        if self._options is not None:
            self._options.deleteLater()

        self._options_parent = parent
        self._options = QListWidget(parent)
        self._options.setObjectName("materialOptions")
        self._options.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self._options.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._options.setMouseTracking(False)
        self._options.setUniformItemSizes(True)
        self._options.addItems(self._materials)
        self._options.hide()
        self._options.itemClicked.connect(self._on_option_clicked)
        self.select_material(self._current_text)
        return self._options

    def _hide_options(self) -> None:
        self._button.setChecked(False)
        if self._options is not None:
            self._options.hide()
        self._remove_event_filter()

    def _install_event_filter(self) -> None:
        app = QApplication.instance()
        if app is not None and not self._event_filter_installed:
            app.installEventFilter(self)
            self._event_filter_installed = True

    def _remove_event_filter(self) -> None:
        app = QApplication.instance()
        if app is not None and self._event_filter_installed:
            app.removeEventFilter(self)
            self._event_filter_installed = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Qt event-filter override; delegates to the snake_case handler."""
        return self._event_filter(watched, event)

    def _event_filter(self, watched: QObject, event: QEvent) -> bool:
        """Close the material options list on outside clicks or geometry changes."""
        if self._options is None or not self._options.isVisible():
            return super().eventFilter(watched, event)

        if (
            isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Escape
        ):
            self._hide_options()
            return True

        if watched is self.window() and event.type() in {
            QEvent.Type.Move,
            QEvent.Type.Resize,
        }:
            self._hide_options()
            return False

        if isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonPress:
            global_pos = event.globalPosition().toPoint()
            clicked_button = self._button.rect().contains(
                self._button.mapFromGlobal(global_pos)
            )
            clicked_options = self._options.rect().contains(
                self._options.mapFromGlobal(global_pos)
            )
            if not clicked_button and not clicked_options:
                self._hide_options()

        return super().eventFilter(watched, event)

    def _on_option_clicked(self, item: QListWidgetItem) -> None:
        material = item.text()
        self.select_material(material)
        self._hide_options()
        QTimer.singleShot(
            _MATERIAL_COMMIT_DELAY_MS,
            lambda: self.material_committed.emit(material),
        )


class OpticsCanvas(QGraphicsView):
    """Optics ray canvas using QGraphicsScene."""

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
            if line is not None:
                self._ray_items.append(line)

        font = QFont("Segoe UI", 10)
        for i, text in enumerate(state.labels):
            label = self._add_simple_text(text, font)
            label.setBrush(QColor("#cfd8dc"))
            label.setPos(90, 48 + i * 22)
            self._label_items.append(label)

        m1 = self._add_simple_text(
            state.medium1_label,
            QFont("Segoe UI", 11, QFont.Weight.Bold),
        )
        m1.setBrush(QColor("#4fc3f7"))
        m1.setPos(620, 120)
        self._label_items.append(m1)

        m2 = self._add_simple_text(
            state.medium2_label,
            QFont("Segoe UI", 11, QFont.Weight.Bold),
        )
        m2.setBrush(QColor("#81c784" if not state.tir_active else "#ff7043"))
        m2.setPos(620, 360)
        self._label_items.append(m2)

    def _add_simple_text(self, text: str, font: QFont) -> QGraphicsSimpleTextItem:
        """Add text to the scene and narrow PyQt's optional stub return type."""
        item = self._scene.addSimpleText(text, font)
        assert item is not None
        return item


class RefractionMainWindow(QMainWindow):
    """Passive view: emits signals, renders presenter commands."""

    angle_changed = cast(ViewSignal, pyqtSignal(float))
    medium1_changed = cast(ViewSignal, pyqtSignal(str))
    medium2_changed = cast(ViewSignal, pyqtSignal(str))

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
        self._medium1 = self._build_material_selector(self.medium1_changed.emit)
        media_row.addWidget(self._medium1, stretch=1)
        media_row.addWidget(QLabel("Medium 2 (transmitted)"))
        self._medium2 = self._build_material_selector(self.medium2_changed.emit)
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
            QPushButton#materialSelector {
                background: #252a33; color: #eceff1; border: 1px solid #3d4654;
                border-radius: 4px; padding: 6px; min-width: 120px; text-align: left;
            }
            QPushButton#materialSelector:hover,
            QPushButton#materialSelector:checked { border-color: #4fc3f7; }
            QListWidget#materialOptions {
                background: #252a33; color: #eceff1; border: 1px solid #3d4654;
                border-radius: 4px; padding: 2px; outline: none;
            }
            QListWidget#materialOptions::item { padding: 5px; }
            QListWidget#materialOptions::item:selected { background: #1565c0; }
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

    def _build_material_selector(self, on_commit: Callable[[str], None]) -> MaterialSelector:
        selector = MaterialSelector()
        selector.material_committed.connect(on_commit)
        return selector

    def set_material_choices(self, materials: list[str]) -> None:
        self._set_material_choices(self._medium1, materials, "Air")
        self._set_material_choices(self._medium2, materials, "Glass")

    def _set_material_choices(
        self,
        selector: MaterialSelector,
        materials: list[str],
        selected_material: str,
    ) -> None:
        selector.blockSignals(True)
        selector.clear_materials()
        selector.set_materials(materials)
        selector.select_material(selected_material)
        selector.blockSignals(False)

    def show_render_state(self, state: RenderState) -> None:
        self._canvas.apply_render_state(state)

    def show_status_message(self, message: str) -> None:
        self._status_bar().showMessage(message)

    def _status_bar(self) -> QStatusBar:
        status_bar = self.statusBar()
        assert status_bar is not None
        return status_bar
