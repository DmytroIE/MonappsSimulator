import matplotlib
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QApplication, QSpinBox, QLabel, QPushButton, QComboBox
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
)
from matplotlib.backends.backend_qt import (
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from itertools import cycle

from widgets.SignalManager import SignalManager
from classes.dfreading import DfReading
from classes.dsreading import (
    DsReading,
    UnusedDsReading,
    InvalidDsReading,
    NonRocDsReading,
    NoDataMarker,
)
from common.constants import settings, STATUS_FIELD_NAME, CURR_STATE_FIELD_NAME
from utils.ts_utils import create_grid, ceil_timestamp

matplotlib.use("Qt5Agg")

Y_MAX = 250
Y_MIN = -50
DEFAULT_Y_MAX = 150
DEFAULT_Y_MIN = 50
DEFAULT_NUM_GRID_COUNTS = 50

line_colours = cycle(
    [
        "tab:blue",
        "tab:orange",
        "tab:green",
        "tab:red",
        "tab:cyan",
        "tab:purple",
        "tab:olive",
    ]
)


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=6, height=4, dpi=100) -> None:
        fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        axes = fig.subplots(2, 1, sharex=True, height_ratios=[5, 2])
        self._axes_vals = axes[0]
        self._axes_sts = axes[1]

        super().__init__(fig)


class GraphWidget(QWidget):

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._canvas = MplCanvas(self, width=25, height=5, dpi=100)
        self._app = QApplication.instance().app
        # self._first_grid_count_ts = None

        self._sbx_y_min = QSpinBox()
        self._sbx_y_min.setRange(Y_MIN, Y_MAX)
        self._sbx_y_min.setValue(DEFAULT_Y_MIN)
        self._sbx_y_min.setFixedWidth(80)
        self._sbx_y_max = QSpinBox()
        self._sbx_y_max.setRange(Y_MIN, Y_MAX)
        self._sbx_y_max.setValue(DEFAULT_Y_MAX)
        self._sbx_y_max.setFixedWidth(80)
        self._sbx_grid_counts = QSpinBox()
        self._sbx_grid_counts.setRange(5, 200)
        self._sbx_grid_counts.setValue(DEFAULT_NUM_GRID_COUNTS)
        self._sbx_grid_counts.setFixedWidth(80)
        self._cmb_time_unit = QComboBox()
        self._cmb_time_unit.addItems(["1 sec", "1 min"])
        self._cmb_time_unit.setCurrentIndex(1)
        self._cmb_time_unit.setFixedWidth(80)

        self._btn_update_graph = QPushButton("Update graph")
        self._btn_update_graph.clicked.connect(self._update_graph)
        self._btn_update_graph.setFixedWidth(200)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Y min"))
        ctrl_layout.addWidget(self._sbx_y_min)
        ctrl_layout.addWidget(QLabel("Y max"))
        ctrl_layout.addWidget(self._sbx_y_max)
        ctrl_layout.addWidget(QLabel("Grid counts"))
        ctrl_layout.addWidget(self._sbx_grid_counts)
        ctrl_layout.addWidget(QLabel("Time unit"))
        ctrl_layout.addWidget(self._cmb_time_unit)
        ctrl_layout.addWidget(self._btn_update_graph)

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(self._canvas, self)

        layout = QVBoxLayout(self)
        layout.addLayout(ctrl_layout)
        layout.addWidget(toolbar)
        layout.addWidget(self._canvas)

        self._line_colours = {}

        SignalManager.update_graph.connect(self._update_graph)
        self._update_graph()

    def _update_graph(self) -> None:
        time_resample = self._app.time_resample
        self._canvas._axes_vals.cla()
        self._canvas._axes_sts.cla()
        first_grid_count_ts = settings.MAX_TS_MS

        y_max = self._sbx_y_max.value()
        y_min = self._sbx_y_min.value()
        if y_max - y_min < 1:
            y_max = y_min + 1
            self._sbx_y_max.setValue(y_max)
        num_grid_counts = self._sbx_grid_counts.value()

        divider = 1000 if self._cmb_time_unit.currentIndex() == 0 else 60000

        # find the horizontal boundaries of the grid
        first_grid_count_ts = settings.MAX_TS_MS
        last_grid_count_ts = 0
        for df in self._app.datafeeds.all():

            if df.pk not in self._line_colours:
                self._line_colours[df.pk] = next(line_colours)

            dfreadings = list(DfReading.objects.filter(datafeed__id=df.pk).order_by("time"))
            dsreadings = []
            if (ds := df.datastream) is not None:
                dsreadings = list(DsReading.objects.filter(datastream__id=ds.pk).order_by("time"))

            if len(dfreadings) > 0:
                ts = dfreadings[0].time - time_resample
                if ts < first_grid_count_ts:
                    first_grid_count_ts = ts
                ts = dfreadings[-1].time
                if ts > last_grid_count_ts:
                    last_grid_count_ts = ts
            elif len(dsreadings) > 0:  # if there are only datastream readings
                ts = ceil_timestamp(dsreadings[0].time - time_resample, time_resample)
                if ts < first_grid_count_ts:
                    first_grid_count_ts = ts
                ts = ceil_timestamp(dsreadings[-1].time, time_resample)
                if ts > last_grid_count_ts:
                    last_grid_count_ts = ts

        if first_grid_count_ts == settings.MAX_TS_MS or last_grid_count_ts == 0:  # no data
            grid = create_grid(0, time_resample * num_grid_counts / divider, time_resample / divider)
            self._canvas._axes_vals.vlines(grid, y_max, y_min, "m", linewidth=0.5)
            self._canvas._axes_sts.vlines(grid, 0, 4, "m", linewidth=0.5)
            self._canvas.draw()
            return

        if (last_grid_count_ts - first_grid_count_ts) / time_resample < num_grid_counts:
            # extend the grid if there are few readings
            last_grid_count_ts = first_grid_count_ts + time_resample * num_grid_counts

        grid = create_grid(
            0,
            (last_grid_count_ts - first_grid_count_ts) / divider,
            time_resample / divider,
        )
        if grid is None:  # it shouldn't be None after adding at least NUM_GRID_COUNTS new points, but just in case
            return

        self._canvas._axes_vals.vlines(grid, y_min, y_max, "m", linewidth=0.5)
        self._canvas._axes_sts.vlines(grid, 0, 4, "m", linewidth=0.5)

        artists_vals = [None for _ in range(8)]
        artists_sts = [None for _ in range(2)]

        for df in self._app.datafeeds.all():
            name = df.name
            ds = df.datastream
            dfreadings = list(DfReading.objects.filter(datafeed__id=df.pk).order_by("time"))
            dsreadings = []
            unused_dsreadings = []
            invalid_dsreadings = []
            non_roc_dsreadings = []

            dsr_tss = []
            dsr_vals = []
            dsr_unused_tss = []
            dsr_unused_vals = []
            dsr_invalid_tss = []
            dsr_invalid_vals = []
            dsr_non_roc_tss = []
            dsr_non_roc_vals = []

            nodata_marker_tss = []

            if ds is not None:
                dsreadings = list(DsReading.objects.filter(datastream__id=ds.pk).order_by("time"))
                unused_dsreadings = list(UnusedDsReading.objects.filter(datastream__id=ds.pk).order_by("time"))
                invalid_dsreadings = list(InvalidDsReading.objects.filter(datastream__id=ds.pk).order_by("time"))
                non_roc_dsreadings = list(NonRocDsReading.objects.filter(datastream__id=ds.pk).order_by("time"))
                nodata_markers = list(NoDataMarker.objects.filter(datastream__id=ds.pk).order_by("time"))

                for dsr in dsreadings:
                    dsr_tss.append((dsr.time - first_grid_count_ts) / divider)
                    dsr_vals.append(dsr.value)

                for dsr in unused_dsreadings:
                    dsr_unused_tss.append((dsr.time - first_grid_count_ts) / divider)
                    dsr_unused_vals.append(dsr.value)

                for dsr in non_roc_dsreadings:
                    dsr_non_roc_tss.append((dsr.time - first_grid_count_ts) / divider)
                    dsr_non_roc_vals.append(dsr.value)

                for dsr in invalid_dsreadings:
                    dsr_invalid_tss.append((dsr.time - first_grid_count_ts) / divider)
                    dsr_invalid_vals.append(y_max)

                for ndm in nodata_markers:
                    nodata_marker_tss.append((ndm.time - first_grid_count_ts) / divider)

            dfr_tss = []
            dfr_vals = []
            dfr_null_tss = []
            dfr_null_vals = []
            dfr_res_tss = []
            dfr_res_vals = []

            for idx, dfr in enumerate(dfreadings):
                t = (dfr.time - first_grid_count_ts) / divider
                v = dfr.value

                dfr_tss.append(t)
                dfr_vals.append(v)

                if idx + 1 < len(dfreadings) and dfreadings[idx + 1].time - dfr.time > time_resample:
                    dfr_tss.append(t + time_resample / divider)
                    dfr_vals.append(None)
                    dfr_null_tss.append(t + time_resample / divider)
                    dfr_null_vals.append(y_min)

                if dfr.restored and v is not None:
                    dfr_res_tss.append(t)
                    dfr_res_vals.append(v)

            color = self._line_colours[df.pk]
            (artists_vals[0],) = self._canvas._axes_vals.plot(dsr_tss, dsr_vals, "x", color=color, label="dsr")
            (artists_vals[1],) = self._canvas._axes_vals.plot(
                dsr_unused_tss, dsr_unused_vals, "X", color=color, label="dsr-unused"
            )
            (artists_vals[2],) = self._canvas._axes_vals.plot(
                dsr_invalid_tss, dsr_invalid_vals, "v", color=color, label="dsr-invalid"
            )
            (artists_vals[3],) = self._canvas._axes_vals.plot(
                dsr_non_roc_tss, dsr_non_roc_vals, "+", color=color, label="dsr-non-roc"
            )
            self._canvas._axes_vals.vlines(nodata_marker_tss, y_min, y_max, color=color, linewidth=1.0)

            if name == STATUS_FIELD_NAME:
                (artists_sts[0],) = self._canvas._axes_sts.plot(
                    dfr_tss,
                    dfr_vals,
                    marker=".",
                    linestyle="solid",
                    color="red",
                    label="status",
                )
            elif name == CURR_STATE_FIELD_NAME:
                (artists_sts[1],) = self._canvas._axes_sts.plot(
                    dfr_tss,
                    dfr_vals,
                    marker=".",
                    linestyle="solid",
                    color="blue",
                    label="curr state",
                )
            else:
                (artists_vals[4],) = self._canvas._axes_vals.plot(
                    dfr_tss,
                    dfr_vals,
                    marker="o",
                    linestyle="solid",
                    color=color,
                    label="dfr-all",
                )
                (artists_vals[5],) = self._canvas._axes_vals.plot(dfr_res_tss, dfr_res_vals, "*k", label="dfr-restored")
                (artists_vals[6],) = self._canvas._axes_vals.plot(
                    dfr_null_tss, dfr_null_vals, "*", color=color, label="dfr-null"
                )

        # if self._app.cursor_ts >= self._first_grid_count_ts:
        (artists_vals[7],) = self._canvas._axes_vals.plot(
            [(self._app.cursor_ts - first_grid_count_ts) / divider],
            [y_min],
            "^g",
            label="app cursor",
        )

        if (last_grid_count_ts - first_grid_count_ts) / time_resample > num_grid_counts:
            self._canvas._axes_vals.set_xlim(
                [
                    (last_grid_count_ts - first_grid_count_ts - time_resample * (num_grid_counts + 1)) / divider,
                    (last_grid_count_ts - first_grid_count_ts + time_resample) / divider,
                ]
            )
        else:
            self._canvas._axes_vals.set_xlim(
                [
                    -time_resample / divider,
                    (last_grid_count_ts - first_grid_count_ts + time_resample) / divider,
                ]
            )

        artists_filtered = list(filter(lambda x: x is not None, artists_vals))
        self._canvas.figure.axes[0].legend(handles=artists_filtered)
        artists_filtered = list(filter(lambda x: x is not None, artists_sts))
        self._canvas.figure.axes[1].legend(handles=artists_filtered)
        self._canvas.draw()
