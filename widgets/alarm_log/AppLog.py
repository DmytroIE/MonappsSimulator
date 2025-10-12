from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QPushButton,
)

from utils.ts_utils import create_dt_from_ts_ms
from widgets.SignalManager import SignalManager


class AppLog(QWidget):

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._records = {}

        layout = QVBoxLayout(self)

        self._txt_field = QTextEdit()
        self._txt_field.setReadOnly(True)
        self._txt_field.setGeometry(0, 0, 600, 400)
        layout.addWidget(self._txt_field)

        self._btn_clear_log = QPushButton("Clear")
        self._btn_clear_log.clicked.connect(self._clear_log)
        layout.addWidget(self._btn_clear_log)

        self._line_colours = {}

        SignalManager.add_to_app_log.connect(self._update_log)

    def _update_log(self, record: dict) -> None:
        key = (record["ts"], record["instance"], record["msg"])
        dt_str = create_dt_from_ts_ms(record["ts"]).isoformat(timespec="milliseconds")
        full_msg = f"[{record['type']}]\t[{record['status']}]\t{dt_str}\t{record['instance']}\t{record['msg']}"
        self._records[key] = full_msg
        self._records = dict(sorted(self._records.items(), key=lambda x: x[0][0]))

        new_text = "\n".join([f"{v}" for v in self._records.values()])
        self._txt_field.setText(new_text)

    def _clear_log(self) -> None:
        self._records = {}
        self._txt_field.setText("")
