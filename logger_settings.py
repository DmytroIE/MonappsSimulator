# Keep format strings and logger names as constants so they are easy to reuse and maintain.
import logging


DEFAULT_LOG_FORMAT = "|%(levelname)s|\t|%(asctime)s|\t|%(name)s|\t'%(message)s'"
LOCAL_APP_LOGGER_PREFIX = "#"


def build_logging_config(
    app_level: str = "INFO",
    root_level: str = "WARNING",
) -> dict:
    """
    Build the logging dictionary used by logging.config.dictConfig.

    Notes about levels:
    - handler level controls what reaches the output destination (console here)
    - logger/root level controls what each logger emits into handlers
    - effective level is the stricter one between logger/root and handler

    app_level:
        Main threshold for your own application loggers (the ones named with '#...').
    root_level:
        Fallback threshold for third-party or uncategorized loggers.
    """

    def _to_levelno(level: str | int) -> int:
        if isinstance(level, int):
            return level

        if isinstance(level, str):
            normalized = level.upper()
            mapping = logging.getLevelNamesMapping()
            if normalized in mapping:
                return mapping[normalized]

        raise ValueError(f"Unsupported logging level: {level}")

    app_levelno = _to_levelno(app_level)
    root_levelno = _to_levelno(root_level)

    class OnlyLocalModulesFilter(logging.Filter):
        """Apply separate thresholds for local (#...) and non-local loggers."""

        def __init__(
            self,
            app_levelno: int,
            root_levelno: int,
            local_prefix: str = LOCAL_APP_LOGGER_PREFIX,
        ) -> None:
            super().__init__()
            self.app_levelno = app_levelno
            self.root_levelno = root_levelno
            self.local_prefix = local_prefix

        def filter(self, record):
            if record.name.startswith(self.local_prefix):
                return record.levelno >= self.app_levelno
            return record.levelno >= self.root_levelno

    return {
        "version": 1,
        # Keep existing 3rd-party loggers alive unless you explicitly want to disable them.
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": DEFAULT_LOG_FORMAT,
            },
        },
        "filters": {
            "OnlyLocalModulesFilter": {
                "()": OnlyLocalModulesFilter,
                "app_levelno": app_levelno,
                "root_levelno": root_levelno,
                "local_prefix": LOCAL_APP_LOGGER_PREFIX,
            },
        },
        "handlers": {
            "console": {
                # Handler level should usually be low (DEBUG) so logger levels decide verbosity.
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["OnlyLocalModulesFilter"],
            },
        },
        "root": {
            # Keep root permissive and let OnlyLocalModulesFilter enforce split thresholds.
            "handlers": ["console"],
            "level": "DEBUG",
        },
    }
