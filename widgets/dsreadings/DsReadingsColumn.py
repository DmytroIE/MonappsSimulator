from PySide6.QtWidgets import (
    QVBoxLayout,
    QApplication,
    QFrame,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QLabel,
    QPushButton,
)
import csv
from common.constants import VariableTypes
from classes.datastream import Datastream
from classes.dsreading import (
    DsReading,
    InvalidDsReading,
    NonRocDsReading,
    UnusedDsReading,
    NoDataMarker,
    UnusedNoDataMarker,
)
from widgets.dsreadings.DsReadingInput import DsReadingInput
from widgets.dsreadings.NoDataMarkerInput import NoDataMarkerInput
from widgets.SignalManager import SignalManager

from utils.dsr_utils import create_ds_readings, create_nodata_markers
from utils.ts_utils import create_ts_ms_from_iso_str, create_now_ts_ms
from utils.sequence_utils import find_max_ts
from utils.update_utils import set_attr_if_cond


class DsReadingsColumn(QFrame):
    def __init__(self, ds: Datastream) -> None:
        super().__init__()

        self._ds = ds

        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self._lyt_main = QVBoxLayout(self)
        self._lyt_main.setContentsMargins(2, 2, 2, 2)
        self._lyt_main.addWidget(QLabel(ds.name))

        self._gbx_readings = QGroupBox("Readings")
        # self._gbx_readings.setStyleSheet('background-color: #dadada')
        self._lyt_readings = QVBoxLayout(self._gbx_readings)
        self._lyt_readings.setContentsMargins(2, 2, 2, 2)
        for _ in range(3):
            min_v = ds.min_plausible_value
            max_v = ds.max_plausible_value
            if ds.data_type.var_type == VariableTypes.CONTINUOUS:
                box_type = "double"
                dsr_widget = DsReadingInput(box_type, min_v - abs(min_v * 0.2), max_v + abs(max_v * 0.2))
            else:
                box_type = "int"
                dsr_widget = DsReadingInput(box_type, min_v, max_v)
            self._lyt_readings.addWidget(dsr_widget)
        self._lyt_main.addWidget(self._gbx_readings)

        self._gbx_nodatamarkers = QGroupBox("NoData markers")
        # self._gbx_readings.setStyleSheet('background-color: #dadada')
        self._lyt_nodatamarkers = QVBoxLayout(self._gbx_nodatamarkers)
        self._lyt_nodatamarkers.setContentsMargins(2, 2, 2, 2)
        for _ in range(2):
            self._lyt_nodatamarkers.addWidget(NoDataMarkerInput())
        self._lyt_main.addWidget(self._gbx_nodatamarkers)

        btn_save_readings = QPushButton("Save")
        btn_save_readings.clicked.connect(self._save_new_ds_readings)
        self._lyt_main.addWidget(btn_save_readings)

        btn_from_file = QPushButton("From CSV")
        btn_from_file.clicked.connect(self._save_new_ds_readings_from_csv)
        self._lyt_main.addWidget(btn_from_file)

    def _save_new_ds_readings(self) -> None:
        pairs = {}
        nodata_marker_tss = []
        num_err_readings = 0
        num_ok_readings = 0

        now_ts = create_now_ts_ms()

        for dsr in self._gbx_readings.children():
            if type(dsr) is DsReadingInput:
                ts_val_tuple = dsr.get_collected_data()
                if ts_val_tuple is None:
                    num_err_readings += 1
                else:
                    ts, val = ts_val_tuple
                    if ts != "":
                        pairs[ts] = val
                        num_ok_readings += 1
        for dsr in self._gbx_nodatamarkers.children():
            if type(dsr) is NoDataMarkerInput:
                ts = dsr.get_collected_data()
                if ts is None:
                    num_err_readings += 1
                elif ts != "":
                    nodata_marker_tss.append(ts)
                    num_ok_readings += 1

        dlg = QMessageBox(self)
        message = ""
        if num_err_readings > 0:
            if num_ok_readings > 0:
                message = "Some readings were not created\nErrors in the data"
                dlg.setWindowTitle("Warning")
                dlg.setIcon(QMessageBox.Icon.Warning)
            else:
                message = "Readings were not created\nErrors in the data"
                dlg.setWindowTitle("Error")
                dlg.setIcon(QMessageBox.Icon.Critical)
        if message != "":
            dlg.setText(message)
            dlg.exec()
        if num_ok_readings > 0:
            ds_readings, unused_ds_readings, invalid_ds_readings, non_roc_ds_readings = create_ds_readings(
                pairs, self._ds, now_ts
            )
            DsReading.objects.bulk_create(ds_readings)
            UnusedDsReading.objects.bulk_create(unused_ds_readings)
            InvalidDsReading.objects.bulk_create(invalid_ds_readings)
            NonRocDsReading.objects.bulk_create(non_roc_ds_readings)
            nd_markers, unused_nd_markers = create_nodata_markers(nodata_marker_tss, self._ds, now_ts)
            NoDataMarker.objects.bulk_create(nd_markers)
            UnusedNoDataMarker.objects.bulk_create(unused_nd_markers)

            # update 'ts_to_start_with' and 'last_reading_ts'
            ts_to_start_with = max(find_max_ts(ds_readings), find_max_ts(nd_markers))
            set_attr_if_cond(ts_to_start_with, ">", self._ds, "ts_to_start_with")

            last_reading_ts = find_max_ts(ds_readings)  # ds_readings - only valid readings
            set_attr_if_cond(last_reading_ts, ">", self._ds, "last_reading_ts")

            SignalManager.update_graph.emit()

    def _save_new_ds_readings_from_csv(self) -> None:
        q_app = QApplication.instance()
        csv_file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", q_app.last_path, "CSV files (*.csv);;All files (*)"
        )
        if not csv_file_path:
            return
        q_app.last_path = csv_file_path
        pairs = {}
        nodata_marker_tss = []
        num_err_readings = 0
        num_ok_readings = 0
        try:
            with open(csv_file_path, "r") as csv_file:
                reader = csv.reader(csv_file, delimiter="\t")
                for row in reader:
                    try:
                        ts = create_ts_ms_from_iso_str(row[0])
                        val = None
                        try:
                            val = row[1]
                            if self._ds.is_value_interger:
                                pairs[ts] = int(val)
                            else:
                                pairs[ts] = float(val)
                        except IndexError:
                            nodata_marker_tss.append(ts)
                    except Exception:
                        num_err_readings += 1
                    else:
                        num_ok_readings += 1
                dlg = QMessageBox(self)
                message = ""
                if num_err_readings > 0:
                    if num_ok_readings > 0:
                        message = "Some readings were not created\nErrors in the data"
                        dlg.setWindowTitle("Warning")
                        dlg.setIcon(QMessageBox.Icon.Warning)
                    else:
                        message = "Readings were not created\nErrors in the data"
                        dlg.setWindowTitle("Error")
                        dlg.setIcon(QMessageBox.Icon.Critical)
                if message != "":
                    dlg.setText(message)
                    dlg.exec()
                if num_ok_readings > 0:
                    now_ts = create_now_ts_ms()
                    ds_readings, unused_ds_readings, invalid_ds_readings, non_roc_ds_readings = create_ds_readings(
                        pairs, self._ds, now_ts
                    )
                    DsReading.objects.bulk_create(ds_readings)
                    UnusedDsReading.objects.bulk_create(unused_ds_readings)
                    InvalidDsReading.objects.bulk_create(invalid_ds_readings)
                    NonRocDsReading.objects.bulk_create(non_roc_ds_readings)
                    nd_markers, unused_nd_markers = create_nodata_markers(nodata_marker_tss, self._ds, now_ts)
                    NoDataMarker.objects.bulk_create(nd_markers)
                    UnusedNoDataMarker.objects.bulk_create(unused_nd_markers)

                    # update 'ts_to_start_with' and 'last_reading_ts'
                    ts_to_start_with = max(find_max_ts(ds_readings), find_max_ts(nd_markers))
                    set_attr_if_cond(ts_to_start_with, ">", self._ds, "ts_to_start_with")

                    last_reading_ts = find_max_ts(ds_readings)  # ds_readings - only valid readings
                    set_attr_if_cond(last_reading_ts, ">", self._ds, "last_reading_ts")

                    SignalManager.update_graph.emit()

        except Exception as e:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Error")
            dlg.setText(f"Something is wrong with the CSV-file, {e}")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.exec()
