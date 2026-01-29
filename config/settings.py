import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
import logging

# Загружаем переменные окружения из .env
load_dotenv()

logger = logging.getLogger(__name__)

# ==================== PATHS ====================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
SCREENSHOT_PATH = BASE_DIR / "screenshots"
LOGS_PATH = BASE_DIR / "logs"

# Создаем необходимые директории
SCREENSHOT_PATH.mkdir(exist_ok=True)
LOGS_PATH.mkdir(exist_ok=True)

# ==================== DATABASE ====================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "parser_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# SQLAlchemy async connection string
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ==================== TELEGRAM ====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv(
    "TELEGRAM_ADMIN_ID"
)  # Опционально: для уведомлений админу

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

# ==================== CAPMONSTER CLOUD ====================
CAPMONSTER_URL = "https://api.capmonster.cloud"
CAPMONSTER_URL_CREATE = CAPMONSTER_URL + "/createTask"
CAPMONSTER_URL_RESULT = CAPMONSTER_URL + "/getTaskResult"
CAPMONSTER_KEY = os.getenv("CAPMONSTER_KEY")

# ==================== PARSER SETTINGS ====================
PARSE_INTERVAL_HOURS = int(os.getenv("PARSE_INTERVAL_HOURS", "1"))
SCREENSHOT_RETENTION_DAYS = int(os.getenv("SCREENSHOT_RETENTION_DAYS", "30"))
DB_RETENTION_DAYS = int(os.getenv("DB_RETENTION_DAYS", "90"))


HEADLESS_MODE = os.getenv("HEADLESS_MODE", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--lang=ru-RU",
]

CONTEXT_PARAMS = {
    "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
    "viewport": {"width": 412, "height": 915},
    "screen": {"width": 412, "height": 915},
    "device_scale_factor": 2.625,
    "is_mobile": True,
    "has_touch": True,
    "locale": "ru-RU",
    "timezone_id": "Europe/Moscow",
    "extra_http_headers": {
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-CH-UA": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-CH-UA-Platform": '"Android"',
    },
}

# ==================== LOGGING ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_PATH / "parser.log"


def setup_logging():
    """Настройка логирования для всего приложения"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Уменьшаем verbose библиотек
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("playwright").setLevel(logging.WARNING)


# ==================== SITES CONFIG ====================
def load_sites_config() -> List[Dict]:
    """Загружает конфигурацию сайтов из YAML"""
    config_file = CONFIG_DIR / "sites_config.yaml"

    if not config_file.exists():
        raise FileNotFoundError(f"Sites config not found: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        sites = config.get("sites", [])

        # Подставляем credentials из .env
        for site in sites:
            if "credentials" in site:
                # Заменяем ${VAR_NAME} на значения из .env
                for key, value in site["credentials"].items():
                    if (
                        isinstance(value, str)
                        and value.startswith("${")
                        and value.endswith("}")
                    ):
                        env_var = value[2:-1]  # Убираем ${ и }
                        env_value = os.getenv(env_var)

                        if not env_value:
                            logger.warning(
                                f"Environment variable {env_var} not set for {site['id']}"
                            )

                        site["credentials"][key] = env_value

        logger.info(f"Loaded {len(sites)} sites from config")
        return sites

    except Exception as e:
        logger.error(f"Error loading sites config: {e}")
        raise


def load_config() -> Dict:
    """Загружает полную конфигурацию приложения"""
    return {
        "database_url": DATABASE_URL,
        "telegram_bot_token": TELEGRAM_BOT_TOKEN,
        "telegram_admin_id": TELEGRAM_ADMIN_ID,
        "parse_interval_hours": PARSE_INTERVAL_HOURS,
        "screenshot_retention_days": SCREENSHOT_RETENTION_DAYS,
        "db_retention_days": DB_RETENTION_DAYS,
        "screenshot_path": str(SCREENSHOT_PATH),
        "headless_mode": HEADLESS_MODE,
        "browser_timeout": BROWSER_TIMEOUT,
        "sites": load_sites_config(),
    }


# ==================== VALIDATE SETTINGS ====================
def validate_settings():
    """Проверяет, что все необходимые настройки заданы"""
    errors = []

    # Проверяем обязательные переменные
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")

    if not DB_PASSWORD or DB_PASSWORD == "your_password":
        errors.append("DB_PASSWORD is not set or using default value")

    # Проверяем, что файл конфигурации существует
    config_file = CONFIG_DIR / "sites_config.yaml"
    if not config_file.exists():
        errors.append(f"Sites config file not found: {config_file}")

    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    logger.info("✅ All settings validated successfully")


# ==================== EXPORT ====================
__all__ = [
    "BASE_DIR",
    "CONFIG_DIR",
    "SCREENSHOT_PATH",
    "LOGS_PATH",
    "DATABASE_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ADMIN_ID",
    "CAPMONSTER_URL",
    "CAPMONSTER_URL_CREATE",
    "CAPMONSTER_URL_RESULT",
    "CAPMONSTER_KEY",
    "PARSE_INTERVAL_HOURS",
    "SCREENSHOT_RETENTION_DAYS",
    "DB_RETENTION_DAYS",
    "HEADLESS_MODE",
    "BROWSER_TIMEOUT",
    "BROWSER_ARGS",
    "CONTEXT_PARAMS",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_FILE",
    "setup_logging",
    "load_config",
    "load_sites_config",
    "validate_settings",
]
