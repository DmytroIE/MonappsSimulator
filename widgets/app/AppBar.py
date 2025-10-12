from PySide6.QtWidgets import QApplication, QHBoxLayout, QFrame, QCheckBox, QLineEdit, QLabel


class AppBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setFrameStyle(QFrame.Box | QFrame.Plain)

        self._lyt_main = QHBoxLayout(self)
        self._lyt_main.setContentsMargins(2, 2, 2, 2)

        self._app = QApplication.instance().app

        self._lyt_main.addWidget(QLabel("Health"))
        self._lin_health = QLineEdit()
        self._lin_health.setFixedWidth(100)
        self._lin_health.setDisabled(True)
        self._lyt_main.addWidget(self._lin_health)

        self._lyt_main.addWidget(QLabel("Is catching up"))
        self._cbx_is_catching_up = QCheckBox()
        self._cbx_is_catching_up.setDisabled(True)
        self._lyt_main.addWidget(self._cbx_is_catching_up)

        self.update_app_values()

    def update_app_values(self) -> None:
        self._lin_health.setText(str(self._app.health))
        self._cbx_is_catching_up.setChecked(self._app.is_catching_up)
