from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QApplication, QPushButton, QMessageBox

from widgets.app.CursorBar import CursorBar
from widgets.app.AppBar import AppBar
from widgets.SignalManager import SignalManager

from app_functions.app_functions import app_function_map
from services.app_func_executor import AppFuncExecutor


class AppWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._app = QApplication.instance().app

        self._lyt_main = QHBoxLayout(self)
        self._lyt_main.setContentsMargins(0, 0, 0, 0)

        lyt_app = QVBoxLayout()
        self._app_settings_bar = CursorBar()
        lyt_app.addWidget(self._app_settings_bar)
        self._app_bar = AppBar()
        lyt_app.addWidget(self._app_bar)
        self._lyt_main.addLayout(lyt_app)

        self._eval_button = QPushButton("Evaluate")
        self._eval_button.clicked.connect(self._on_evaluate)
        self._lyt_main.addWidget(self._eval_button)

    def _on_evaluate(self) -> None:
        self._evaluate()
        SignalManager.update_graph.emit()

    def _evaluate(self) -> None:
        self._app_settings_bar.set_cursor_ts()
        self._app_settings_bar.turn_bar_off()
        app_func_cluster = app_function_map.get(self._app.type.func_name)
        if app_func_cluster is None:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"No such app function: {self._app.type.func_name}")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.exec()
            return
        app_func = app_func_cluster.get(self._app.func_version)
        if app_func is None:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"No such app function version {self._app.func_version}")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.exec()
            return
        app_func = app_func["function"]

        AppFuncExecutor(self._app, app_func).execute()

        self._app_settings_bar.turn_bar_on()
        self._app_settings_bar.update_cursor_ts_in_line_edit()
        self._app_bar.update_app_values()
