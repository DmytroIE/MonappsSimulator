from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QPushButton

from widgets.app.AppWidget import AppWidget
from widgets.dsreadings.DsReadingsWidget import DsReadingsWidget
from widgets.graph.GraphWidget import GraphWidget
from widgets.alarm_log.AlarmLog import AlarmLog
from widgets.alarm_log.AppLog import AppLog


class MainWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._lyt_main = QVBoxLayout(self)
        self._lyt_main.setContentsMargins(0, 0, 0, 0)

        self._app_widget = AppWidget()
        self._lyt_main.addWidget(self._app_widget)

        self._ds_readings_widget = DsReadingsWidget()
        self._lyt_main.addWidget(self._ds_readings_widget)

        lyt_buttons = QHBoxLayout()

        self._wdg_graph = GraphWidget()
        self._wdg_graph.setWindowTitle("Graph")
        self._btn_show_graph = QPushButton("Graph")
        self._btn_show_graph.setFixedWidth(150)
        self._btn_show_graph.setCheckable(True)
        self._btn_show_graph.clicked.connect(self.toggle_graph)
        lyt_buttons.addWidget(self._btn_show_graph)

        self._wdg_alarm_log = AlarmLog()
        self._wdg_alarm_log.setWindowTitle("Alarm log")
        self._btn_show_alarm_log = QPushButton("Alarm log")
        self._btn_show_alarm_log.setFixedWidth(150)
        self._btn_show_alarm_log.setCheckable(True)
        self._btn_show_alarm_log.clicked.connect(self.toggle_alarm_log)
        lyt_buttons.addWidget(self._btn_show_alarm_log)

        self._wdg_app_log = AppLog()
        self._wdg_app_log.setWindowTitle("App log")
        self._btn_show_app_log = QPushButton("App log")
        self._btn_show_app_log.setFixedWidth(150)
        self._btn_show_app_log.setCheckable(True)
        self._btn_show_app_log.clicked.connect(self.toggle_app_log)
        lyt_buttons.addWidget(self._btn_show_app_log)

        self._lyt_main.addLayout(lyt_buttons)

    def toggle_graph(self, checked: bool) -> None:
        if not self._btn_show_graph.isChecked() and self._wdg_graph.isVisible():
            self._wdg_graph.hide()
        elif self._btn_show_graph.isChecked() and not self._wdg_graph.isVisible():
            self._wdg_graph.show()

    def toggle_alarm_log(self, checked: bool) -> None:
        if not self._btn_show_alarm_log.isChecked() and self._wdg_alarm_log.isVisible():
            self._wdg_alarm_log.hide()
        elif self._btn_show_alarm_log.isChecked() and not self._wdg_alarm_log.isVisible():
            self._wdg_alarm_log.show()

    def toggle_app_log(self, checked: bool) -> None:
        if not self._btn_show_app_log.isChecked() and self._wdg_app_log.isVisible():
            self._wdg_app_log.hide()
        elif self._btn_show_app_log.isChecked() and not self._wdg_app_log.isVisible():
            self._wdg_app_log.show()
