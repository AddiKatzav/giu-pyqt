#!/usr/bin/env bash
# Recreate the virtualenv (needed after renaming the project folder).
set -euo pipefail
cd "$(dirname "$0")"
rm -rf .pyqt-venv
python3 -m venv .pyqt-venv
.pyqt-venv/bin/pip install -U pip
.pyqt-venv/bin/pip install -r requirements.txt
.pyqt-venv/bin/python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 ready')"
