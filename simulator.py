import logging.config
import sys
import logging

from PySide6 import QtWidgets
from PySide6.QtCore import QLocale

from widgets.MainWidget import MainWidget
from create_app import app, graph_settings
from logger_settings import build_logging_config

LOGGING = build_logging_config(app_level="DEBUG", root_level="WARNING")

logging.config.dictConfig(LOGGING)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, **kwargs) -> None:
        QLocale.setDefault(QLocale("en"))
        QtWidgets.QMainWindow.__init__(self)
        self.setWindowTitle(f"{app.name} {app.func_version}")
        # self.setGeometry(0, 0, 640, 640)

        wdg_main = MainWidget()
        self.setCentralWidget(wdg_main)


if __name__ == "__main__":
    q_app = QtWidgets.QApplication(sys.argv)
    q_app.last_path = "/home"
    q_app.app = app
    q_app.graph_settings = graph_settings
    window = MainWindow()
    window.show()
    sys.exit(q_app.exec())
