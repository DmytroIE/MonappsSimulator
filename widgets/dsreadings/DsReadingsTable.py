from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

from widgets.dsreadings.DsReadingsColumn import DsReadingsColumn


class DsReadingsTable(QWidget):
    def __init__(self):
        super().__init__()
        self._lyt_main = QHBoxLayout(self)
        self._lyt_main.setContentsMargins(2, 2, 2, 2)
        app = QApplication.instance().app
        for df in app.datafeeds.all():
            if df.datastream is not None:
                ds_readings_column = DsReadingsColumn(ds=df.datastream)
                self._lyt_main.addWidget(ds_readings_column)
