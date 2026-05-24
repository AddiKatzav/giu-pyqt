---
name: snells-law-optics
description: Run headless Snell's Law refraction simulations (incident angle, two media). Use when calculating refraction angles, total internal reflection, or critical angle without a GUI.
---

# Snell's Law Optics (Headless)

The physics core lives in `physics_model.py` with **zero GUI dependencies**.

## Quick CLI

From the project root:

```bash
python main.py --cli --angle 45 --medium1 Air --medium2 Water
python main.py --cli --angle 50 --medium1 Glass --medium2 Air --json
```

## Python API (for agents)

```python
from physics_model import simulate_refraction, MATERIALS

result = simulate_refraction(45.0, "Air", "Water")
print(result.refracted_angle_deg)
print(result.total_internal_reflection)
print(result.as_dict())  # JSON-serializable
```

## Materials

`Air` (1.0), `Water` (1.33), `Glass` (1.5), `Diamond` (2.42), `Ice` (1.31), `Sapphire` (1.77)

## GUI

```bash
python main.py
```

Interactive PyQt6 visualization uses MVP (`presenter.py`, `gui_view.py`); physics never imports Qt.
