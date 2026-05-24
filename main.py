"""Entry point: PyQt6 GUI or headless agent/CLI API."""

from __future__ import annotations

import argparse
import sys

from physics_model import MATERIALS
from presenter import RefractionPresenter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Snell's Law optics simulator (GUI or headless API).",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run headless simulation (no GUI).",
    )
    parser.add_argument(
        "--angle",
        type=float,
        default=30.0,
        help="Incident angle in degrees (0–90).",
    )
    parser.add_argument(
        "--medium1",
        default="Air",
        choices=list(MATERIALS.keys()),
        help="Incident medium.",
    )
    parser.add_argument(
        "--medium2",
        default="Glass",
        choices=list(MATERIALS.keys()),
        help="Transmitted medium.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON (CLI mode).",
    )
    return parser


def run_cli(args: argparse.Namespace) -> int:
    output = RefractionPresenter.run_headless(
        args.angle,
        args.medium1,
        args.medium2,
        as_json=args.json,
    )
    if args.json:
        print(output)
    else:
        result = output
        assert not isinstance(result, str)
        print(f"θ₁ = {result.incident_angle_deg:.2f}°  ({result.medium1}, n={result.n1})")
        if result.total_internal_reflection:
            print("Total internal reflection — no transmitted ray.")
            if result.critical_angle_deg is not None:
                print(f"Critical angle θc = {result.critical_angle_deg:.2f}°")
        else:
            print(
                f"θ₂ = {result.refracted_angle_deg:.2f}°  "
                f"({result.medium2}, n={result.n2})"
            )
    return 0


def run_gui() -> int:
    from PyQt6.QtWidgets import QApplication

    from gui_view import RefractionMainWindow
    from presenter import RefractionPresenter

    app = QApplication(sys.argv)
    presenter = RefractionPresenter()
    window = RefractionMainWindow(presenter)
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cli:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
