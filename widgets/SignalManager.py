from PySide6.QtCore import QObject, Signal


class SignalExchanger(QObject):
    update_graph = Signal()
    evaluate = Signal()
    add_to_alarm_log = Signal(dict)
    add_to_app_log = Signal(dict)


SignalManager = SignalExchanger()
