from pydantic import BaseModel, ConfigDict


df_schema = {}


class AppFuncSettingsModel(BaseModel):

    model_config = ConfigDict(title="'Monitoring VER1 1.0.0' app function settings", extra="allow")
