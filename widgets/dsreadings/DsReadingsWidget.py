from PySide6.QtWidgets import QVBoxLayout, QWidget, QScrollArea

from widgets.dsreadings.DsReadingsTable import DsReadingsTable


class DsReadingsWidget(QWidget):
    def __init__(self):
        super().__init__()

        self._lyt_main = QVBoxLayout(self)
        self._lyt_main.setContentsMargins(0, 0, 0, 0)

        self._ds_readings_table = DsReadingsTable()

        self._scr_area = QScrollArea()
        self._scr_area.setWidget(self._ds_readings_table)
        self._lyt_main.addWidget(self._scr_area)
