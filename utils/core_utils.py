import configparser
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PACKAGE_ROOT / "config" / "core_config.ini"

load_dotenv(Path.cwd() / ".env", override=False)
load_dotenv(PACKAGE_ROOT / ".env", override=False)


@lru_cache(maxsize=1)
def get_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    return config


def get_setting(
    section: str,
    key: str,
    default: Optional[str] = None,
    env_name: Optional[str] = None,
) -> str:
    env_key = env_name or key.upper()
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value

    config = get_config()
    if config.has_option(section, key):
        return config.get(section, key)

    return "" if default is None else default


def get_int_setting(section: str, key: str, default: int) -> int:
    value = get_setting(section, key, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
