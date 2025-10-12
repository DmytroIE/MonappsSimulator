from PySide6.QtWidgets import QHBoxLayout, QWidget, QDoubleSpinBox, QSpinBox, QLineEdit, QPushButton
from datetime import datetime, timezone
from typing import Literal, Tuple

from utils.ts_utils import create_ts_ms_from_iso_str


class DsReadingInput(QWidget):
    def __init__(
        self,
        box_type: Literal["int", "double"],
        min: int | float,
        max: int | float,
    ) -> None:
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

        if box_type == "int":
            self._spb_value = QSpinBox()
            self._spb_value.setRange(int(min), int(max))
            self._spb_value.setValue(int((min + max) / 2))
        else:
            self._spb_value = QDoubleSpinBox()
            self._spb_value.setSingleStep(0.1)
            self._spb_value.setRange(min, max)
            self._spb_value.setValue(int((min + max) / 2))

        self._spb_value.setFixedWidth(80)
        self._lyt_main.addWidget(self._spb_value)

    def set_input_with_iso_str(self):
        dt = datetime.now(tz=timezone.utc)
        self._lin_datetimestr.setText(dt.isoformat(timespec="milliseconds"))

    def get_collected_data(self) -> Tuple[int | Literal[""], int | float] | None:
        val = self._spb_value.value()
        iso_str = self._lin_datetimestr.text()
        if iso_str == "":
            ts = iso_str
        else:
            try:
                ts = create_ts_ms_from_iso_str(iso_str.strip())
            except Exception:
                return None
        self._lin_datetimestr.setText("")
        self._spb_value.setValue(int((self._spb_value.minimum() + self._spb_value.maximum()) / 2))
        return (ts, val)
