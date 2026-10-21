import logging
import configparser
from pathlib import Path

from utils.core_utils import PACKAGE_ROOT, get_setting


LOGGER_CONFIG_PATH = PACKAGE_ROOT / "config" / "logger.ini"


def _get_logger_setting(key: str, default: str) -> str:
    config = configparser.ConfigParser()
    config.read(LOGGER_CONFIG_PATH)
    if config.has_option("logger", key):
        return config.get("logger", key)
    return get_setting("logger", key, default)


def _create_logger() -> logging.Logger:
    logger_name = _get_logger_setting("name", "negotiation_fail")
    level_name = get_setting(
        "logger",
        "level",
        _get_logger_setting("level", "INFO"),
        env_name="LOG_LEVEL",
    )
    log_file = _get_logger_setting("file", "logs/negotiation_fail_api.log")
    console_enabled = _get_logger_setting("console", "true").lower() == "true"

    api_logger = logging.getLogger(logger_name)
    api_logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    api_logger.propagate = False

    if api_logger.handlers:
        return api_logger

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    log_path = Path(log_file)
    if not log_path.is_absolute():
        log_path = PACKAGE_ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    api_logger.addHandler(file_handler)

    if console_enabled:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        api_logger.addHandler(stream_handler)

    return api_logger


logger = _create_logger()
