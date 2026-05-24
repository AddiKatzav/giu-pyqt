"""MVP presenter: orchestrates model, view, and headless outputs."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from physics_model import MATERIALS, PhysicsModel, RefractionResult, simulate_refraction


@dataclass(frozen=True, slots=True)
class RaySegment:
    """Line segment for the view to draw (scene coordinates)."""

    x1: float
    y1: float
    x2: float
    y2: float
    color: str
    width: float = 2.5
    dashed: bool = False


@dataclass(frozen=True, slots=True)
class RenderState:
    """Passive drawing instructions — no physics in the view."""

    rays: tuple[RaySegment, ...]
    labels: tuple[str, ...]
    medium1_label: str
    medium2_label: str
    tir_active: bool


@runtime_checkable
class IRefractionView(Protocol):
    """View contract: emit inputs, accept render commands."""

    def set_material_choices(self, materials: list[str]) -> None: ...
    def show_render_state(self, state: RenderState) -> None: ...
    def show_status_message(self, message: str) -> None: ...


class RefractionPresenter:
    """Consumes user or API input, updates the model, pushes render state."""

    # Ray length in scene units
    _RAY_LEN = 220.0
    _ORIGIN_X = 400.0
    _ORIGIN_Y = 280.0

    def __init__(self, model: Optional[PhysicsModel] = None) -> None:
        self._model = model or PhysicsModel()
        self._view: Optional[IRefractionView] = None

    @property
    def model(self) -> PhysicsModel:
        return self._model

    def attach_view(self, view: IRefractionView) -> None:
        """Wire passive view signals to presenter handlers."""
        self._view = view
        view.set_material_choices(list(MATERIALS.keys()))
        view.angle_changed.connect(self.on_angle_changed)
        view.medium1_changed.connect(self.on_medium1_changed)
        view.medium2_changed.connect(self.on_medium2_changed)
        self._sync_view()

    def on_angle_changed(self, degrees: float) -> None:
        self._model.set_incident_angle(degrees)
        self._sync_view()

    def on_medium1_changed(self, material: str) -> None:
        self._set_medium(material, self._model.set_medium1)

    def on_medium2_changed(self, material: str) -> None:
        self._set_medium(material, self._model.set_medium2)

    def _set_medium(self, material: str, apply_material: Callable[[str], None]) -> None:
        if not material or material not in MATERIALS:
            return
        apply_material(material)
        self._sync_view()

    def _sync_view(self) -> None:
        if self._view is not None:
            self.render_to_view(self._view)

    def compute(self) -> RefractionResult:
        return self._model.compute()

    def build_render_state(self, result: Optional[RefractionResult] = None) -> RenderState:
        """Map physics result to scene geometry for the view."""
        result = result or self._model.compute()
        ox, oy = self._ORIGIN_X, self._ORIGIN_Y
        length = self._RAY_LEN

        theta1_rad = math.radians(result.incident_angle_deg)
        # Incident ray in medium 1 (above interface, coming toward origin).
        inc_x2 = ox - length * math.sin(theta1_rad)
        inc_y2 = oy - length * math.cos(theta1_rad)

        rays: list[RaySegment] = [
            RaySegment(inc_x2, inc_y2, ox, oy, "#4fc3f7", width=3.0),
            RaySegment(ox, oy, ox, oy - 90, "#90a4ae", width=1.5, dashed=True),
        ]

        labels = [
            f"θ₁ = {result.incident_angle_deg:.1f}°",
            f"n₁ = {result.n1:.2f} ({result.medium1})",
            f"n₂ = {result.n2:.2f} ({result.medium2})",
        ]

        if result.total_internal_reflection:
            # Reflect specularly about the normal (angle equals incident).
            ref_x2 = ox + length * math.sin(theta1_rad)
            ref_y2 = oy + length * math.cos(theta1_rad)
            rays.append(RaySegment(ox, oy, ref_x2, ref_y2, "#ff7043", width=3.0))
            labels.append("TIR — reflected ray")
            if result.critical_angle_deg is not None:
                labels.append(f"θc = {result.critical_angle_deg:.1f}°")
        elif result.refracted_angle_deg is not None:
            theta2_rad = math.radians(result.refracted_angle_deg)
            ref_x2 = ox + length * math.sin(theta2_rad)
            ref_y2 = oy + length * math.cos(theta2_rad)
            rays.append(RaySegment(ox, oy, ref_x2, ref_y2, "#81c784", width=3.0))
            labels.append(f"θ₂ = {result.refracted_angle_deg:.1f}°")

        return RenderState(
            rays=tuple(rays),
            labels=tuple(labels),
            medium1_label=result.medium1,
            medium2_label=result.medium2,
            tir_active=result.total_internal_reflection,
        )

    def render_to_view(self, view: IRefractionView) -> None:
        result = self.compute()
        view.show_render_state(self.build_render_state(result))
        if result.total_internal_reflection:
            view.show_status_message("Total internal reflection")
        else:
            view.show_status_message(
                f"Refracted at {result.refracted_angle_deg:.1f}°"
                if result.refracted_angle_deg is not None
                else "Ready"
            )

    @staticmethod
    def run_headless(
        incident_angle_deg: float,
        medium1: str,
        medium2: str,
        *,
        as_json: bool = False,
    ) -> RefractionResult | str:
        """Agent/CLI entry: no GUI."""
        result = simulate_refraction(incident_angle_deg, medium1, medium2)
        if as_json:
            return json.dumps(result.as_dict(), indent=2)
        return result
