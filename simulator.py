import logging.config
import sys
import logging

from PySide6 import QtWidgets
from PySide6.QtCore import QLocale

from widgets.MainWidget import MainWidget
from create_app import app

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["OnlyLocalModulesFilter"],
        },
    },
    "formatters": {
        "simple": {"format": "|%(levelname)s|\t|%(asctime)s|\t|%(module)s|\t'%(message)s'"},
    },
    "filters": {
        "OnlyLocalModulesFilter": {
            "()": "utils.log_filters.OnlyLocalModulesFilter",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

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
    window = MainWindow()
    window.show()
    sys.exit(q_app.exec())
