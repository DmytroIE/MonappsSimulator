from PySide6.QtWidgets import QHBoxLayout, QWidget, QLineEdit, QPushButton
from datetime import datetime, timezone
from typing import Literal

from utils.ts_utils import create_ts_ms_from_iso_str


class NoDataMarkerInput(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._lyt_main = QHBoxLayout(self)
        self._lyt_main.setContentsMargins(0, 0, 0, 0)
        self._lin_datetimestr = QLineEdit()
        self._lin_datetimestr.setPlaceholderText("Input ISO-string...")
        self._lin_datetimestr.setFixedWidth(150)
        self._lyt_main.addWidget(self._lin_datetimestr)

        self._btn_autofill = QPushButton("Auto")
        self._btn_autofill.clicked.connect(self.set_input_with_iso_str)
        self._btn_autofill.setFixedWidth(50)
        self._lyt_main.addWidget(self._btn_autofill)

    def set_input_with_iso_str(self) -> None:
        dt = datetime.now(tz=timezone.utc)
        self._lin_datetimestr.setText(dt.isoformat(timespec="milliseconds"))

    def get_collected_data(self) -> int | Literal[""] | None:
        iso_str = self._lin_datetimestr.text()
        if iso_str == "":
            ts = iso_str
        else:
            try:
                ts = create_ts_ms_from_iso_str(iso_str.strip())
            except Exception:
                return None
        self._lin_datetimestr.setText("")
        return ts
