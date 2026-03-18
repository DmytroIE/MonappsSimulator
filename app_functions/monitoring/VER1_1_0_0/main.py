import logging

from app_functions.helpers.classes.app_function import AppFunction

from .schemas import AppFuncSettingsModel as AfsModel

logger = logging.getLogger("#mon_VER1_1_0_0")


class MonitoringAppFunction(AppFunction[AfsModel]):

    def __init__(self):
        super().__init__(AfsModel, logger)


function = MonitoringAppFunction()
