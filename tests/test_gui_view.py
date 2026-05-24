"""Widget tests for the PyQt6 view components."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

from gui_view import MaterialSelector


class TestMaterialSelector(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_select_material_updates_label(self) -> None:
        selector = MaterialSelector()
        selector.set_materials(["Air", "Glass", "Ice"])
        selector.select_material("Glass")

        self.assertEqual(selector._current_text, "Glass")
        self.assertEqual(selector._button.text(), "Glass")

    def test_option_click_commits_material_after_hiding_options(self) -> None:
        selector = MaterialSelector()
        selector.set_materials(["Air", "Glass", "Ice"])
        selector.select_material("Air")
        committed: list[str] = []
        selector.material_committed.connect(committed.append)

        selector._show_options()
        assert selector._options is not None
        ice_item = selector._options.item(2)
        assert ice_item is not None
        selector._on_option_clicked(ice_item)

        self.assertFalse(selector._options.isVisible())
        self.assertEqual(selector._button.text(), "Ice")

        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec()

        self.assertEqual(committed, ["Ice"])


if __name__ == "__main__":
    unittest.main()
