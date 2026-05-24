"""Headless Snell's Law physics engine (no GUI dependencies)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Mapping, Optional

# Refractive indices at standard conditions (dimensionless).
MATERIALS: Final[Mapping[str, float]] = {
    "Air": 1.0,
    "Water": 1.33,
    "Glass": 1.5,
    "Diamond": 2.42,
    "Ice": 1.31,
    "Sapphire": 1.77,
}


@dataclass(frozen=True, slots=True)
class RefractionResult:
    """Outcome of a single Snell's Law calculation."""

    incident_angle_deg: float
    refracted_angle_deg: Optional[float]
    total_internal_reflection: bool
    critical_angle_deg: Optional[float]
    n1: float
    n2: float
    medium1: str
    medium2: str

    def as_dict(self) -> dict[str, object]:
        """Serialize for JSON APIs and agent tooling."""
        return {
            "incident_angle_deg": self.incident_angle_deg,
            "refracted_angle_deg": self.refracted_angle_deg,
            "total_internal_reflection": self.total_internal_reflection,
            "critical_angle_deg": self.critical_angle_deg,
            "n1": self.n1,
            "n2": self.n2,
            "medium1": self.medium1,
            "medium2": self.medium2,
        }


@dataclass(slots=True)
class SimulationState:
    """Mutable simulation parameters held by the model."""

    incident_angle_deg: float = 30.0
    medium1: str = "Air"
    medium2: str = "Glass"

    def copy(self) -> SimulationState:
        return SimulationState(
            incident_angle_deg=self.incident_angle_deg,
            medium1=self.medium1,
            medium2=self.medium2,
        )


def refractive_index(material: str) -> float:
    """Return the refractive index for a named material."""
    if material not in MATERIALS:
        raise ValueError(
            f"Unknown material '{material}'. "
            f"Choose from: {', '.join(sorted(MATERIALS))}"
        )
    return MATERIALS[material]


def compute_critical_angle_deg(n1: float, n2: float) -> Optional[float]:
    """
    Critical angle (degrees) when light travels from denser to rarer medium.

    Returns None when n1 <= n2 (no TIR possible at the interface).
    """
    if n1 <= n2:
        return None
    ratio = n2 / n1
    if ratio >= 1.0:
        return None
    return math.degrees(math.asin(ratio))


def snells_law(
    incident_angle_deg: float,
    n1: float,
    n2: float,
    *,
    medium1: str = "medium1",
    medium2: str = "medium2",
) -> RefractionResult:
    """
    Apply Snell's Law: n1 * sin(theta1) = n2 * sin(theta2).

    Angles are measured from the surface normal. Total internal reflection
    is reported when the transmitted ray cannot exist (sin(theta2) > 1).
    """
    theta1 = max(0.0, min(90.0, incident_angle_deg))
    critical = compute_critical_angle_deg(n1, n2)

    sin_theta2 = (n1 / n2) * math.sin(math.radians(theta1))
    if abs(sin_theta2) > 1.0:
        return RefractionResult(
            incident_angle_deg=theta1,
            refracted_angle_deg=None,
            total_internal_reflection=True,
            critical_angle_deg=critical,
            n1=n1,
            n2=n2,
            medium1=medium1,
            medium2=medium2,
        )

    theta2 = math.degrees(math.asin(sin_theta2))
    return RefractionResult(
        incident_angle_deg=theta1,
        refracted_angle_deg=theta2,
        total_internal_reflection=False,
        critical_angle_deg=critical,
        n1=n1,
        n2=n2,
        medium1=medium1,
        medium2=medium2,
    )


def simulate_refraction(
    incident_angle_deg: float,
    medium1: str,
    medium2: str,
) -> RefractionResult:
    """
    High-level API for agents and CLI: run one refraction simulation.

    Example:
        >>> r = simulate_refraction(45.0, "Air", "Water")
        >>> r.refracted_angle_deg is not None
        True
    """
    n1 = refractive_index(medium1)
    n2 = refractive_index(medium2)
    return snells_law(
        incident_angle_deg,
        n1,
        n2,
        medium1=medium1,
        medium2=medium2,
    )


class PhysicsModel:
    """Encapsulates simulation state and delegates to pure physics functions."""

    def __init__(self, state: Optional[SimulationState] = None) -> None:
        self._state = state or SimulationState()

    @property
    def state(self) -> SimulationState:
        return self._state

    def set_incident_angle(self, degrees: float) -> None:
        self._state.incident_angle_deg = max(0.0, min(90.0, degrees))

    def set_medium1(self, material: str) -> None:
        self._set_medium("medium1", material)

    def set_medium2(self, material: str) -> None:
        self._set_medium("medium2", material)

    def _set_medium(self, field_name: str, material: str) -> None:
        refractive_index(material)  # validate
        setattr(self._state, field_name, material)

    def compute(self) -> RefractionResult:
        """Calculate refraction for the current simulation state."""
        return simulate_refraction(
            self._state.incident_angle_deg,
            self._state.medium1,
            self._state.medium2,
        )
