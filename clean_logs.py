import logging
import os
from datetime import datetime
from clickhouse_driver import Client


# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("info")

# Параметры подключения к ClickHouse
CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 9000
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = "rabbit_logger"

# Периоды хранения данных
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", 30))  # Дни для logs
APM_RETENTION_DAYS = int(os.getenv("APM_RETENTION_DAYS", 30))  # Дни для apm

def clean_logs():
    """Очистка старых данных из таблицы logs."""
    query = f"""
        ALTER TABLE {CLICKHOUSE_DB}.logs DELETE WHERE created_dt < toDateTime(now() - toIntervalDay({LOG_RETENTION_DAYS}));
    """
    client.execute(query)
    logger.info(f"[{datetime.now()}] Logs older than {LOG_RETENTION_DAYS} days deleted.")

def clean_apm():
    """Очистка старых данных из таблицы apm."""
    query = f"""
        ALTER TABLE {CLICKHOUSE_DB}.apm DELETE WHERE created_dt < toDateTime(now() - toIntervalDay({APM_RETENTION_DAYS}));
    """
    client.execute(query)
    logger.info(f"[{datetime.now()}] APM data older than {APM_RETENTION_DAYS} days deleted.")


def delete_one_log():
    """Удаляет одну запись из таблицы logs для тестирования."""
    # Укажите конкретное условие для удаления, например, uuid или ограничение по дате
    query = f"""
        ALTER TABLE {CLICKHOUSE_DB}.logs DELETE WHERE uuid = (
            SELECT uuid FROM {CLICKHOUSE_DB}.logs LIMIT 1
        );
    """
    client.execute(query)
    logger.info("One log entry deleted for testing.")


if __name__ == "__main__":
    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB,
    )

    clean_logs()
    clean_apm()
