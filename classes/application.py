from typing import Dict, Self
from classes.object_manager import ObjectManager
from common.constants import (
    StatusTypes,
    CurrStateTypes,
    HealthGrades,
)
from utils.ts_utils import create_now_ts_ms


class AppType:
    objects = ObjectManager["AppType"]()
    id_counter = 0

    def __init__(self: Self, name: str, func_name: str) -> None:

        self.name = name
        self.func_name = func_name

        AppType.id_counter += 1
        self.id = AppType.id_counter
        self.pk = self.id

    def save(self, update_fields=None) -> None:
        AppType.objects.add_item(self)


class Application:
    objects = ObjectManager["Application"]()
    id_counter = 0

    def __init__(
        self: Self,
        type: AppType,
        app_settings: Dict,
        time_resample: int,
        func_version: str,
        cursor_ts: int,
        time_status_stale: int = 86400000 * 15,
        time_curr_state_stale: int = 600000,
        time_health_error: int = 600000,
    ) -> None:

        self.type = type
        self.time_resample = time_resample
        self.settings = app_settings
        self.state = {}  # For retaining the state between calculations
        self.errors = {}
        self.warnings = {}
        self.cursor_ts = cursor_ts
        self.is_enabled = False
        self.func_version = func_version

        self.status = StatusTypes.UNDEFINED
        self.curr_state = CurrStateTypes.UNDEFINED
        self.last_status_update_ts: int | None = None
        self.last_curr_state_update_ts: int | None = None
        self.time_status_stale = time_status_stale
        self.time_curr_state_stale = time_curr_state_stale
        self.is_status_stale = False
        self.is_curr_state_stale = False
        self.health = HealthGrades.UNDEFINED
        self.is_catching_up = False
        self.created_ts = create_now_ts_ms()

        self.time_health_error = time_health_error  # if the cursor is older than this, the health is set to ERROR

        Application.id_counter += 1
        self.id = Application.id_counter
        self.pk = self.id
        self.update_fields = set()

        self.datafeeds = ObjectManager["Datafeed"]()  # imitation of the backward relation

    @property
    def name(self) -> str:
        return self.type.name

    def __repr__(self):
        return f"Application {self.pk} '{self.type.name}'"

    def save(self, update_fields=None) -> None:
        Application.objects.add_item(self)
        self.update_fields = set()

    def get_native_df_qs(self):
        return self.datafeeds.filter(datastream__isnull=False)

    def get_derived_df_qs(self):
        return self.datafeeds.filter(datastream__isnull=True)
