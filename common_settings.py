import logging
import os

from dotenv import load_dotenv

load_dotenv()

current_model_name = os.getenv("AI_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "render_standard": {
            # Формат оптимізовано під Render: виводимо ім'я модуля, де стався запис, та рядок коду
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",  # Вивід у консоль (stdout/stderr)
            "formatter": "render_standard",    # Використовуємо твій форматер вище
            "level": "DEBUG",                  # Мінімальний рівень, який пропускає цей handler
        },
    },
    "loggers": {
        "": {  # Корневий логер для всього проєкту
            "handlers": ["console"],           # Тепер цей обробник існує!
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}


def setup_logging():
    """Ініціалізація конфігурації логування."""
    logging.config.dictConfig(LOGGING_CONFIG)
