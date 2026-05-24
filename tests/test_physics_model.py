"""Unit tests for the headless Snell's Law engine."""

import math
import unittest

from physics_model import (
    PhysicsModel,
    compute_critical_angle_deg,
    simulate_refraction,
    snells_law,
)


class TestSnellsLaw(unittest.TestCase):
    def test_normal_incidence_air_to_glass(self) -> None:
        r = simulate_refraction(0.0, "Air", "Glass")
        self.assertFalse(r.total_internal_reflection)
        self.assertAlmostEqual(r.refracted_angle_deg or 0.0, 0.0, places=5)

    def test_oblique_air_to_water(self) -> None:
        r = simulate_refraction(30.0, "Air", "Water")
        self.assertFalse(r.total_internal_reflection)
        assert r.refracted_angle_deg is not None
        n1, n2 = 1.0, 1.33
        expected = math.degrees(
            math.asin((n1 / n2) * math.sin(math.radians(30.0)))
        )
        self.assertAlmostEqual(r.refracted_angle_deg, expected, places=4)

    def test_total_internal_reflection(self) -> None:
        r = simulate_refraction(50.0, "Glass", "Air")
        self.assertTrue(r.total_internal_reflection)
        self.assertIsNone(r.refracted_angle_deg)

    def test_critical_angle_glass_to_air(self) -> None:
        critical = compute_critical_angle_deg(1.5, 1.0)
        assert critical is not None
        r = simulate_refraction(critical + 0.1, "Glass", "Air")
        self.assertTrue(r.total_internal_reflection)
        r2 = simulate_refraction(critical - 0.1, "Glass", "Air")
        self.assertFalse(r2.total_internal_reflection)

    def test_angle_clamped_to_90(self) -> None:
        r = snells_law(120.0, 1.0, 1.5)
        self.assertEqual(r.incident_angle_deg, 90.0)

    def test_physics_model_mutators(self) -> None:
        model = PhysicsModel()
        model.set_incident_angle(45.0)
        model.set_medium1("Water")
        model.set_medium2("Glass")
        r = model.compute()
        self.assertEqual(r.medium1, "Water")
        self.assertEqual(r.medium2, "Glass")
        self.assertAlmostEqual(r.incident_angle_deg, 45.0)

    def test_unknown_material_raises(self) -> None:
        with self.assertRaises(ValueError):
            simulate_refraction(30.0, "Unobtanium", "Air")


if __name__ == "__main__":
    unittest.main()
