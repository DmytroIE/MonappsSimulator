from PySide6.QtWidgets import QApplication, QHBoxLayout, QFrame, QCheckBox, QMessageBox, QLineEdit, QPushButton
from PySide6.QtCore import QTimer
from datetime import datetime, timezone

from widgets.SignalManager import SignalManager
from classes.dfreading import DfReading
from utils.ts_utils import floor_timestamp, create_ts_ms_from_iso_str


class CursorBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setFrameStyle(QFrame.Box | QFrame.Plain)

        self._lyt_main = QHBoxLayout(self)
        self._lyt_main.setContentsMargins(2, 2, 2, 2)

        self._lin_app_cursor = QLineEdit()
        self._lin_app_cursor.setFixedWidth(200)

        self._btn_set_cursor_ts = QPushButton("Set new cursor")
        self._btn_set_cursor_ts.clicked.connect(self._on_cursor_update)

        self._lyt_main.addWidget(self._lin_app_cursor)
        self._lyt_main.addWidget(self._btn_set_cursor_ts)

        self._app = QApplication.instance().app

        self.update_cursor_ts_in_line_edit()

        self._cbx_exec = QCheckBox("App func execution")
        self._app.is_enabled = True
        self._cbx_exec.setChecked(self._app.is_enabled)
        self._cbx_exec.stateChanged.connect(self._on_exec_state_change)
        self._lyt_main.addWidget(self._cbx_exec)

    def _on_exec_state_change(self) -> None:
        self._app.is_enabled = self._cbx_exec.isChecked()

    def _on_cursor_update(self) -> None:

        self.set_cursor_ts()
        SignalManager.update_graph.emit()
        self.update_cursor_ts_in_line_edit()

        # print(f'stylesheet,\n {self._lin_app_cursor.styleSheet()}')
        self._lin_app_cursor.setStyleSheet("background-color: rgb(225, 235, 235)")
        QTimer.singleShot(300, lambda: self._lin_app_cursor.setStyleSheet(""))

    def update_cursor_ts_in_line_edit(self) -> None:
        dt = datetime.fromtimestamp(self._app.cursor_ts / 1000, tz=timezone.utc)
        self._lin_app_cursor.setText(dt.isoformat(timespec="milliseconds"))

    def set_cursor_ts(self) -> None:
        new_ts_str = self._lin_app_cursor.text()
        if new_ts_str != "":
            try:
                new_cursor_ts = floor_timestamp(create_ts_ms_from_iso_str(new_ts_str), self._app.time_resample)
                if new_cursor_ts != self._app.cursor_ts:
                    self._app.cursor_ts = new_cursor_ts
                    DfReading.objects.filter(time__gt=new_cursor_ts).delete()
                    for df in self._app.datafeeds.all():
                        df.ts_to_start_with = new_cursor_ts
                        df.save()
                    dlg = QMessageBox(self)
                    dlg.setWindowTitle("Info")
                    dlg.setText(f"App cursor position has been changed, {new_cursor_ts}\nAlarm log was not cleared, sorry")
                    dlg.setIcon(QMessageBox.Icon.Information)
                    dlg.exec()
            except Exception as e:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Error")
                dlg.setText(f"Can't change app cursor position, {e}")
                dlg.setIcon(QMessageBox.Icon.Critical)
                dlg.exec()

    def turn_bar_off(self):
        self._lin_app_cursor.setEnabled(False)
        self._btn_set_cursor_ts.setEnabled(False)

    def turn_bar_on(self):
        self._lin_app_cursor.setEnabled(True)
        self._btn_set_cursor_ts.setEnabled(True)
