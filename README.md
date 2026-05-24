# Snell's Law Optics Simulator

PyQt6 Snell's Law optics simulator with a tested headless physics core and an interactive refraction visualizer.

## Features

- Simulate refraction between common materials.
- Detect total internal reflection and show the critical angle.
- Run the same physics from the GUI, CLI, or Python API.
- Keep physics logic independent from PyQt6 for easier testing.

## Setup

```bash
./setup_venv.sh
source .pyqt-venv/bin/activate
```

## Run The GUI

```bash
python main.py
```
<img width="426" height="240" alt="Video Project- gif" src="https://github.com/user-attachments/assets/bc799fbd-5e2c-4f24-b3d6-58f386982b36" />

## Run Headless

```bash
python main.py --cli --angle 45 --medium1 Air --medium2 Water
python main.py --cli --angle 50 --medium1 Glass --medium2 Air --json
```

## Run Tests

```bash
source .pyqt-venv/bin/activate
python -m unittest discover -s tests
```

## Project Layout

- `physics_model.py` contains the Snell's Law calculations and material data.
- `presenter.py` maps model results into render instructions.
- `gui_view.py` contains the PyQt6 widgets and canvas rendering.
- `main.py` provides the GUI and CLI entry points.
- `tests/` covers the headless physics behavior.
