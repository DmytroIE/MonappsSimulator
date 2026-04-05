from app_functions.helpers.classes.app_function import AppFunction

from .schemas import AppFuncSettingsModel as AfsModel


class MonitoringAppFunction(AppFunction[AfsModel]):

    def __init__(self):
        super().__init__(AfsModel)


function = MonitoringAppFunction()
